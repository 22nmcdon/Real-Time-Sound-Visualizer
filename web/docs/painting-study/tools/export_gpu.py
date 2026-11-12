"""Export Crossed hands in Cycles as a stroke stream for the graphics-card
test (`../gpu/index.html`), and the CPU render of the same moments beside it.

The brush's own state - each bristle group's load and the brush's mixture
of pigments - does not depend on the canvas in oilpaint.cpp except through
paint it picks up, so it is replayed here, step by step, by the same rules
(loading, the exponential spend along the stroke, the seeded share each
group takes of a dip), and written out per step. What the page computes on
the graphics card is everything per pixel. The pick-up is the one thing cut:
it needs the canvas under the brush read back every step; the page smudges
wet paint along the stroke instead.

File `gpu/strokes.bin`, little-endian:
  'PNT1', uint32 steps, float32 length, ref (canvas size the coordinates are
  in, as fractions), tau, thick;
  float32 ground[3], ink[7][3]                   linear reflectances
  per step, float32[12]: t, stroke, x, y, dx, dy, w, p, stiff, dry, per, span
      (x, y, w, span as fractions of the canvas)
  per step, uint8[7]: the brush's mixture, x255
  per step, uint8[32]: each bristle group's load, x100 (loads run 0 to 2.5)

    python3 export_gpu.py
"""
import math, os, shutil, struct, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import features, palettes, physical  # noqa: E402
from colour import hex_rgb, lin  # noqa: E402

STUDY = os.path.dirname(HERE)
GPU = os.path.join(STUDY, "gpu")
REF = 1000
LAYOUT = "cycles"
K_BINS, K_REACH = 32, 7.0


def hash32(x):
    """oilpaint.cpp's hash, to the bit."""
    x &= 0xffffffff
    x ^= x >> 16; x = (x * 0x7feb352d) & 0xffffffff
    x ^= x >> 15; x = (x * 0x846ca68b) & 0xffffffff
    x ^= x >> 16
    return (x & 0xffffff) / float(0xffffff)


def main():
    os.makedirs(GPU, exist_ok=True)
    a = features.analyse("crossed")
    pal = palettes.PALETTES["brand"]
    lines = physical.strokes(a, LAYOUT, REF, REF)
    lines.sort(key=lambda l: (l[0], 0 if l[1].startswith("load") else 1))
    brushes = {}
    steps, mixes, bins = [], [], []
    for _, text in lines:
        p = text.split()
        if p[0] == "load":
            s, t, role, amount = int(p[1]), float(p[2]), int(p[3]), float(p[4])
            white = float(p[5]) if len(p) > 5 else 0.0
            b = brushes.setdefault(s, dict(load=np.zeros(K_BINS), mix=np.zeros((K_BINS, 7)), last=None, span=0.0,
                                           share=np.array([0.45 + 0.55 * hash32(s * 977 + k * 31 + 7) for k in range(K_BINS)])))
            add = amount * b["share"]
            total = b["load"] + add
            dip = np.zeros(7); dip[role] = 1 - white; dip[6] += white
            b["mix"] = (b["mix"] * b["load"][:, None] + add[:, None] * dip[None, :]) / np.maximum(total, 1e-6)[:, None]
            b["load"] = np.minimum(total, 2.5)
        else:
            s = int(p[1]); t, x, y, dx, dy, w, pr = map(float, p[2:9])
            stiff, splay, dry = (float(v) for v in p[9:12]) if len(p) > 11 else (0.5, 0.0, 0.0)
            b = brushes[s]
            moved = 1.0 if b["last"] is None else math.hypot(x - b["last"][0], y - b["last"][1])
            b["last"] = (x, y)
            hw = max(0.8, w * 0.5 * (0.4 + 0.6 * min(pr, 1.0)) * (1 + 0.4 * splay))
            b["span"] = max(b["span"], hw)
            hl = max(1.2, 0.12 * w)
            per = min(max(moved / (1.4 * hl), 0.02), 1.0)
            ln = math.hypot(dx, dy) or 1.0
            steps.append([t, s, x / REF, y / REF, dx / ln, dy / ln, w / REF, pr, stiff, dry, per, b["span"] / REF])
            # The brush's mixture, averaged over its groups by their loads.
            m = (b["mix"] * b["load"][:, None]).sum(axis=0) / max(b["load"].sum(), 1e-6)
            mixes.append(np.clip(np.round(m * 255), 0, 255))
            bins.append(np.clip(np.round(b["load"] * 100), 0, 255))
            if pr > 0: b["load"] = b["load"] * math.exp(-moved / (K_REACH * w) * pr)
    steps = np.array(steps, np.float32)
    head = b"PNT1" + struct.pack("<I4f", len(steps), a["length"], REF, physical.DRY, physical.THICK)
    g = lin(hex_rgb(pal["ground"]))
    inks = [lin(hex_rgb(pal["inks"][r])) for r in physical.ROLES] + [lin(hex_rgb(physical.WHITE))]
    col = np.array(list(g) + [c for ink in inks for c in ink], np.float32)
    with open(os.path.join(GPU, "strokes.bin"), "wb") as f:
        f.write(head); f.write(col.tobytes()); f.write(steps.tobytes())
        f.write(np.array(mixes, np.uint8).tobytes()); f.write(np.array(bins, np.uint8).tobytes())
    shutil.copy(os.path.join(STUDY, "audio", "crossed.mp3"), os.path.join(GPU, "crossed.mp3"))
    # The CPU render of the same moments, at 1000 square, for comparison.
    moments = [7.5, a["length"] + 0.5]
    shots = []
    physical.run(a, LAYOUT, REF, REF, pal, moments, lambda rgb, cov: shots.append(rgb.copy()))
    for m, img in zip(("mid", "end"), shots):
        Image.fromarray(img).save(os.path.join(GPU, f"cpu-{m}.jpg"), quality=88, optimize=True)
    print(len(steps), "steps,", os.path.getsize(os.path.join(GPU, "strokes.bin")), "bytes; max steps in a sixtieth:",
          int(np.bincount((steps[:, 0] * 60).astype(int)).max()))


if __name__ == "__main__":
    main()
