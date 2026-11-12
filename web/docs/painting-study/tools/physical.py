"""The physical paint style: the sound as brushwork for oilpaint.cpp.

The marks follow the same vocabulary as the other styles, translated into
what a painter does with a loaded brush:

  - A melody, or a held note, is one stroke along its path (`paint.path_of`,
    in the same layouts), its pressure the core's level for the note
    sounding, so a loud note presses the brush wider and lays more paint and
    a fading one lifts off. A held note's brush broadens as it is held, and
    is dipped again every two seconds of holding, so a long note deepens.
  - Every strike dips the brush in that note's ink (its hand and its
    harmony, as elsewhere), by as much as it was hard, without wiping it:
    what was on the brush stays in it, so colour changes along a phrase are
    carried and mixed, not cut.
  - A sharp, hard attack presses the brush: the stroke bulges wider and
    heavier for its first 60 ms, from a brush dipped deeper, which is the
    impasto of the attack; the hardest also flick flecks off the brush.
    (A separate short stab for each strike was tried first and read as
    sticks poking out of the strokes.)
  - The brush itself (cycle 2, the owner: strokes looked too alike) is set
    by the spectrum as the stroke goes: brightness (centroid against the
    pitch) makes the bristles stiff - streakier, harder-edged, ploughing
    more and blending less - and darkness soft; spectral spread splays
    them wider with gaps; noisiness drags the brush dry; roughness (beating
    partials, Plomp and Levelt) shakes the line; harmonic richness loads
    the brush; the attack's rise time shapes the start. Each stroke adds its
    own small seeded variation, so the same performance paints the same
    picture.
  - Drying (oilpaint.cpp's `dry`): paint's wetness falls to 1/e in
    DRY * (1 + THICK * thickness) seconds, so thin paint dries first and a
    heavy stroke stays wet longest, and the playing's timing decides whether
    a stroke merges into the last or sits on it.

The canvas, its paint and its light are oilpaint.cpp's.
"""
import math, os, subprocess, time
import numpy as np

from colour import hex_rgb, lin
import paint

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(os.path.dirname(HERE), "build")
# Drying (cycle 2, the owner: a little too fast, and thin paint should dry
# before thick): wetness falls to 1/e in DRY * (1 + THICK * a) seconds, a the
# paint's thickness - 1.5 s for a scumble, about 3.5 s for an ordinary
# stroke, 6 s or more for a heavy, hard-struck one. (Cycle 1: 1.2 s for all.)
DRY = 1.5
THICK = 3.0
ROLES = paint.ROLES


def build():
    subprocess.run(["g++", "-std=c++17", "-O3", "-Wall", "-Wextra", os.path.join(HERE, "oilpaint.cpp"), "-o",
                    os.path.join(BUILD, "oilpaint")], check=True)


def _steps(sid, ts, pts, widths, press, brush=None):
    """A stroke's steps, resampled evenly along its length (a fifth of the
    brush's width apart, so the bristles draw unbroken streaks), each with
    the time it was reached, its width and its pressure; nothing where the
    brush is lifted."""
    ts, pts, widths, press = map(np.asarray, (ts, pts, widths, press))
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    arc = np.concatenate([[0], np.cumsum(seg)])
    if arc[-1] < 0.5:
        arc = np.linspace(0, 1, len(ts)); pts = pts + np.outer(arc, [0.5, 0])
        arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    spacing = max(0.6, 0.05 * float(np.median(widths[widths > 0])) if (widths > 0).any() else 1.0)
    s = np.arange(0, arc[-1], spacing)
    x = np.interp(s, arc, pts[:, 0]); y = np.interp(s, arc, pts[:, 1])
    t = np.interp(s, arc, ts); w = np.interp(s, arc, widths); p = np.interp(s, arc, press)
    q = [np.interp(s, arc, np.asarray(b)) for b in brush] if brush is not None else None
    if len(s) < 2:
        d = pts[-1] - pts[0]
        dx, dy = np.full(len(s), d[0] if abs(d).sum() else 1.0), np.full(len(s), d[1])
    else:
        # The brush's heading from the path smoothed over about a brush
        # width: a tremor moves the brush sideways without turning it, where
        # following every shake swung a slow stroke's footprint from side to
        # side and laid it in scales.
        k = max(3, int(float(np.median(w)) / spacing) | 1)
        if len(s) > k:
            ker = np.hanning(k + 2)[1:-1]; ker /= ker.sum()
            xs = np.convolve(np.pad(x, k // 2, mode="edge"), ker, mode="valid")
            ys = np.convolve(np.pad(y, k // 2, mode="edge"), ker, mode="valid")
            dx, dy = np.gradient(xs), np.gradient(ys)
        else:
            dx, dy = np.gradient(x), np.gradient(y)
    out = []
    for k in range(len(s)):
        if w[k] < 0.8 or p[k] <= 0.02: continue
        extra = f" {q[0][k]:.3f} {q[1][k]:.3f} {q[2][k]:.3f}" if q is not None else ""
        out.append((float(t[k]), f"step {sid} {t[k]:.4f} {x[k]:.2f} {y[k]:.2f} {dx[k]:.3f} {dy[k]:.3f} {w[k]:.2f} {p[k]:.3f}{extra}"))
    return out


def slow_noise(n, rng, every=120):
    """A smooth noise between -1 and 1 over n samples, a new value every
    `every` (a quarter second at the path's 2 ms)."""
    k = max(2, n // every + 2)
    v = rng.uniform(-1, 1, k)
    return np.interp(np.linspace(0, k - 1, n), np.arange(k), v)


def tremor(ctx, ts, pts, rough, rng):
    """Roughness shakes the line: beating partials as a hand's tremor, a few
    pixels to fifteen across the stroke, at about six a second; nought for a
    smooth sound, so its line is steady."""
    n = len(ts)
    if n < 3: return pts
    d = np.gradient(pts, axis=0)
    nrm = np.stack([-d[:, 1], d[:, 0]], axis=1)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-6)
    shake = slow_noise(n, rng, every=80) * (1.5 + 13 * rough) * ctx.unit()
    return pts + nrm * shake[:, None]


def strokes(a, layout, w, h, seed=0):
    """The script's lines (time, text), unsorted."""
    ctx = paint.Ctx(a, paint.layout_of(layout, a, w, h), "physical", w, h)
    u = ctx.unit()
    rng = np.random.default_rng(seed + 4000 + (0 if layout == "layered" else 500))
    lines, sid = [], 0
    # Every note gets the brush: the melody's chains go through each strike's
    # top note, so the other notes of a chord are strokes of their own.
    chains = paint.phrases(a["events"])
    used = {id(e) for ch in chains for e in ch}
    chains += [[e] for e in a["events"] if id(e) not in used]
    for chain in chains:
        ts, pts, lev, vel = paint.path_of(ctx, chain, dt=0.002)
        srng = np.random.default_rng(seed * 7919 + sid * 104729 + 17)   # this stroke's own variation
        feat = lambda name: np.array([ctx.f(name, t) for t in ts])
        bright, splay, grain, rough, rich = (feat(n) for n in ("bright", "splay", "grain", "rough", "rich"))
        pts = tremor(ctx, ts, pts, rough, srng)
        since = np.array([t - max(e["t0"] for e in chain if e["t0"] <= t) for t in ts])
        widths = u * (16 + 60 * np.power(np.clip(lev, 0, 1), 0.7)) * (1 + 0.8 * np.minimum(1, np.sqrt(since / 2.5)))
        # The brush's own small variation: its width breathes a little along
        # the stroke, slowly, by this stroke's seed.
        widths = widths * (1 + 0.08 * slow_noise(len(ts), srng))
        # The start's shape is the attack's: a slow attack tapers the brush
        # in over the time the core's envelope took to rise; a sharp one
        # lands at full width (and presses, below).
        for e in chain:
            ramp = max(e["rise"], 0.01) * 1.5
            dt_ = ts - e["t0"]
            if e is chain[0]:
                widths = widths * np.where(dt_ < ramp, 0.25 + 0.75 * paint.smooth(0, ramp, dt_), 1.0)
        press = np.power(np.clip(lev / 0.6, 0, 1), 0.8)
        # A hard, sharp strike presses the brush down at the attack: for 60 ms
        # the stroke bulges, wider and heavier - the impasto of the attack.
        for e in chain:
            force = e["vel"] * max(0.0, 1 - e["rise"] / 0.12)
            dt = np.maximum(ts - e["t0"], 0)
            # Rising over 15 ms and falling over 60: a sudden jump in width
            # read as a square notch cut in the stroke.
            bump = (1 - np.exp(-dt / 0.015)) * np.exp(-dt / 0.06) * (ts >= e["t0"]) * force * 1.6
            press = press * (1 + 0.6 * bump)
            widths = widths * (1 + 0.06 * bump)
        press = np.clip(press, 0, 1.4)
        press[lev < 0.015] = 0
        for j, e in enumerate(chain):
            # Each strike dips the brush in its note's ink, as deep as the
            # strike was hard and sharp (a hard attack is a loaded brush),
            # and as the sound is rich in partials (a full sound, a full brush).
            force = e["vel"] * max(0.0, 1 - e["rise"] / 0.12)
            richness = ctx.f("rich", e["t0"] + 0.05)
            amount = ((1.0 if j == 0 else 0.4) + 0.6 * e["vel"] + 0.8 * force ** 1.5) * (0.6 + 0.8 * richness)
            lines.append((e["t0"] - 1e-4, f"load {sid} {e['t0']:.4f} {ROLES.index(ctx.role(e))} {amount:.3f}"))
            # Re-dipped every two seconds a note is held.
            end = chain[j + 1]["t0"] if j + 1 < len(chain) else e["t1"]
            t = e["t0"] + 2.0
            while t < end - 0.3:
                lines.append((t - 1e-4, f"load {sid} {t:.4f} {ROLES.index(ctx.role(e))} 0.35"))
                t += 2.0
        # Bristles: stiff as the sound is bright (a dark sound, a soft
        # blending brush), splayed as its spectrum is wide, dragged dry as it
        # is noisy - each with the brush's own small offset.
        stiff = np.clip((bright + 0.3) / 1.6 + srng.normal(0, 0.06), 0, 1)
        spl = np.clip(splay + srng.normal(0, 0.05), 0, 1)
        dry = np.clip(1.4 * grain, 0, 1)
        lines += _steps(sid, ts, pts, widths, press, (stiff, spl, dry))
        sid += 1
    # Flecks for the hardest, sharpest strikes: paint flicked off the brush.
    for e in a["events"]:
        force = e["vel"] * max(0.0, 1 - e["rise"] / 0.12)
        if force < 0.55: continue
        x, y = ctx.lay.at(e["t0"], e["note"])
        f = np.linspace(0, 1, 6)
        for _ in range(int(round(6 * force ** 2))):
            ang = rng.uniform(0, 2 * math.pi); dist = u * (25 + rng.pareto(2.5) * 40) * e["vel"]
            fx, fy = x + math.cos(ang) * dist, y + math.sin(ang) * dist
            r = u * rng.uniform(2, 6) * e["vel"]
            pts = np.stack([fx + math.cos(ang) * r * f, fy + math.sin(ang) * r * f], 1)
            lines.append((e["t0"] + 0.02 - 1e-4, f"load {sid} {e['t0'] + 0.02:.4f} {ROLES.index(ctx.role(e))} 1.6"))
            lines += _steps(sid, e["t0"] + 0.02 + 0.005 * f, pts, np.full(6, r), np.full(6, 1.0))
            sid += 1
    return lines


def script(a, layout, w, h, palette, frame_times):
    lines = strokes(a, layout, w, h)
    lines += [(t, f"frame {t:.4f}") for t in frame_times]
    lines.sort(key=lambda l: (l[0], 0 if l[1].startswith("load") else 1 if l[1].startswith("step") else 2))
    g = lin(hex_rgb(palette["ground"]))
    head = [f"canvas {w} {h}", "ground %.5f %.5f %.5f" % tuple(g), f"dry {DRY} {THICK}"]
    for i, r in enumerate(ROLES):
        head.append("ink %d %.5f %.5f %.5f" % ((i,) + tuple(lin(hex_rgb(palette["inks"][r])))))
    return "\n".join(head + [l[1] for l in lines]) + "\n"


def run(a, layout, w, h, palette, frame_times, on_frame):
    """Paint, calling on_frame(rgb, coverage) at each frame time. Returns the
    cost line oilpaint.cpp prints."""
    text = script(a, layout, w, h, palette, frame_times)
    proc = subprocess.Popen([os.path.join(BUILD, "oilpaint")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    import threading
    feeder = threading.Thread(target=lambda: (proc.stdin.write(text.encode()), proc.stdin.close()))
    feeder.start()
    nbytes = w * h * 3
    for _ in frame_times:
        rgb = proc.stdout.read(nbytes)
        cov = proc.stdout.read(w * h * 4)
        on_frame(np.frombuffer(rgb, np.uint8).reshape(h, w, 3), np.frombuffer(cov, np.float32).reshape(h, w))
    feeder.join()
    err = proc.stderr.read().decode()
    proc.wait()
    return err.strip().splitlines()[-1] if err.strip() else ""
