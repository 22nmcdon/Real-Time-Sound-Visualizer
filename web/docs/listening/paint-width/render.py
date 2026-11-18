"""Paint width: the study's four phrases painted by the core at three base
brush widths, sound and picture together, for the owner to choose between.

The owner's rule (18 Nov): the picture must be true to the sound. The look and
the paint map Scan reads are the same strokes, the same positions and widths;
the look may render them finer, with texture and light, but never wider or
narrower. So a wider brush is wider for the sound too: neighbouring notes share
more paint, and a note's tone is coloured by its register.

The widths are PaintParams::width, an internal parameter over the brush step 2
shipped (a brush one to four of the map's 128 cells across by its pressure):

  today    1     as step 2 painted
  medium   2
  wide     3.5   near the study's physical brush, whose strokes were fitted
                 per phrase (the study's pad: about 7 per cent of the canvas
                 across); here one width for any phrase on the round canvas

The phrases are painting-step1's (the study's), played by render.cpp beside
this file, the instrument itself. For each phrase and width this writes:

  audio/NAME-WIDTH.mp3       what the core plays
  pictures/NAME-WIDTH-map.png    the map at the phrase's end (thickness grey, wet blue)
  pictures/NAME-WIDTH-look.jpg   the live look at the phrase's end: the page's own
                             paintView, in headless Chromium's WebGL 2 (SwiftShader),
                             painting the core's stamps a sixtieth of a second at a
                             time, as the face is served them, so the pacing is the
                             instrument's and not the software renderer's
  results.json               Scan's measures (centroid, movement, as painting-step1),
                             the Picture amount's reads, and how much paint each
                             note's ring shares with its neighbours'

and, for the run at today's width, the look painted at four frames a second
from the same stamps, to show the strokes hold together at any frame rate.

A melody is one stroke (PaintParams::chain, 0.45 s): a note struck alone that
soon after the hand's last takes up its stroke. Since that changes how a run
sounds, the run and Crossed hands are rendered at the width picked both ways,
"-separate" being every note a stroke of its own as step 2 painted; and a slow
melody, a note a second, is rendered both ways at that width, to hear what the
threshold does to a melody slower than it.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/listening/paint-width/render.py [NAME ...]
"""
import base64, importlib.util, io, json, math, os, subprocess, sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CORE = os.path.join(ROOT, "core")
BUILD = os.path.join(CORE, "build", "listening", "paint-width")
PAGE = os.path.join(ROOT, "web", "scope.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
GL = ["--autoplay-policy=no-user-gesture-required", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
N = 128

_spec = importlib.util.spec_from_file_location("step1", os.path.join(HERE, "..", "painting-step1", "render.py"))
step1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(step1)

WIDTHS = {"today": 1.0, "medium": 2.0, "wide": 3.5}


def slow_melody():
    """A melody at one note a second, legato (each held 0.95 s): slower than
    the 0.45 s within which a note struck alone takes up the last one's
    stroke, to hear and see what that threshold does to it."""
    notes = [(0.3 + k, n, 80, 0.95) for k, n in enumerate((60, 64, 67, 72, 71, 67, 64, 62, 60))]
    return notes, 10.0


PHRASES = dict(step1.PHRASES, slow=("Slow melody", "Tine piano", slow_melody))
# What is rendered: each of the study's phrases at the three widths with a melody one stroke (the default), and
# at the width picked with every note a stroke of its own (chain 0, as step 2 painted), for the phrases with a
# melody in them; the slow melody at the width picked, both ways.
PICK = "medium"
JOBS = [(name, w, WIDTHS[w], None) for name in step1.PHRASES for w in WIDTHS]
JOBS += [(name, PICK + "-separate", WIDTHS[PICK], 0.0) for name in ("crossed", "run")]
JOBS += [("slow", PICK, WIDTHS[PICK], None), ("slow", PICK + "-separate", WIDTHS[PICK], 0.0)]


def build():
    os.makedirs(BUILD, exist_ok=True)
    inc = os.path.join(CORE, "include")
    for src, out in ((os.path.join(HERE, "render.cpp"), "render"),
                     (os.path.join(CORE, "tests", "tools", "instrument_cpp.cpp"), "instrument_cpp")):
        subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", inc, src, "-o",
                        os.path.join(BUILD, out)], check=True)


def preset_code(name):
    return subprocess.run([os.path.join(BUILD, "instrument_cpp"), "--code", name], capture_output=True, text=True,
                          check=True).stdout.strip()


def render(name, key, width, chain):
    _, preset, make = PHRASES[name]
    code = step1.CROSSED if preset is None else preset_code(preset)
    notes, length = make()
    path = os.path.join(BUILD, name + ".script")
    with open(path, "w") as f: f.write(step1.script(code, notes, length))
    prefix = os.path.join(BUILD, "%s-%s" % (name, key))
    subprocess.run([os.path.join(BUILD, "render"), path, prefix, str(width)] + ([] if chain is None else [str(chain)]), check=True)
    return prefix, length, sorted({n for _, n, _, _ in notes})


def stamps_of(prefix):
    raw = open(prefix + ".stamps", "rb").read()
    frames, rows, i = [], [], 0
    while i < len(raw):
        f, n = np.frombuffer(raw[i:i + 8], np.int32); i += 8
        rows.append(np.frombuffer(raw[i:i + n * 80], np.float32).reshape(n, 20)); i += n * 80
        frames += [f] * n
    return np.array(frames, np.int32), (np.concatenate(rows) if rows else np.zeros((0, 20), np.float32))


def radius_cells(note):
    hz = 440 * 2 ** ((note - 69) / 12)
    u = min(1, max(0, math.log2(hz / 27.5) / math.log2(4186.009044809578 / 27.5)))
    return 0.47 * (1 / 3 + 2 / 3 * u) * N


def bilinear(g, x, y):
    x = np.clip(x - 0.5, 0, N - 1.001); y = np.clip(y - 0.5, 0, N - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x - x0; fy = y - y0
    return (g[y0, x0] * (1 - fx) * (1 - fy) + g[y0, x0 + 1] * fx * (1 - fy) + g[y0 + 1, x0] * (1 - fx) * fy
            + g[y0 + 1, x0 + 1] * fx * fy)


def ring(field, note):
    """What a note's ring reads off the map, as the core reads it: the field at
    256 points round its radius, a quarter, a half and a quarter three quarters
    of a cell apart across it (paint.h, readRing, before the Softness)."""
    th = 2 * np.pi * np.arange(256) / 256
    r = radius_cells(note)
    out = 0
    for dr, w in ((-0.75, 0.25), (0, 0.5), (0.75, 0.25)):
        out = out + w * bilinear(field, N / 2 + (r + dr) * np.sin(th), N / 2 - (r + dr) * np.cos(th))
    return out


def shares(prefix, notes):
    """How much of a note's ring's paint its neighbours' rings read too: for
    each note played and each map (every sixth frame) where its ring has paint,
    the paint its ring and the ring a semitone away have in common, over the
    paint either has (sum of the smaller over sum of the larger: one, the same
    paint; nought, none in common), up and down; and the same a fifth away. The
    median over notes and moments."""
    _, thick, wet = step1.maps_of(prefix)
    semi, fifth = [], []
    for k in range(len(thick)):
        field = thick[k] * (1 + 0.4 * wet[k])
        cache = {}
        def rd(n):
            if n not in cache: cache[n] = ring(field, n)
            return cache[n]
        for n in notes:
            a = rd(n)
            if a.sum() < 1e-3: continue
            for d, into in ((1, semi), (-1, semi), (7, fifth), (-7, fifth)):
                b = rd(n + d)
                into.append(float(np.minimum(a, b).sum() / max(np.maximum(a, b).sum(), 1e-9)))
    med = lambda v: round(float(np.median(v)), 3) if v else 0.0
    return dict(semitone=med(semi), fifth=med(fifth))


class Looks:
    """The page's own paintView, painting a phrase's stamps a sixtieth of a second at a time."""

    def __init__(self):
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(executable_path=CHROME, args=GL)

    def look(self, prefix, out, fps=60):
        frames, S = stamps_of(prefix)
        p = self.browser.new_page(viewport={"width": 1400, "height": 900})
        p.goto("file://" + PAGE); p.wait_for_timeout(1500); p.keyboard.press("Escape")
        p.evaluate("(b64) => { const s = atob(b64), u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i);"
                   " window.__stamps = new Float32Array(u.buffer); }", base64.b64encode(S.astype(np.float32).tobytes()).decode())
        per = max(1, round(60 / fps))
        bounds, i, last = [], 0, int(frames.max()) if len(frames) else 0
        for f0 in range(0, last + 1, per):
            j = i
            while j < len(frames) and frames[j] < f0 + per: j += 1
            bounds.append((i, j, (f0 + per) * 1000 / 60)); i = j
        url = p.evaluate("""(bounds) => { paintView.setOn(true); paintView.clear();
          for (const [a, b, ms] of bounds) {
            if (b > a) paintView.take({ on: true, from: a, count: b - a, stamps: window.__stamps.subarray(a * 20, b * 20) });
            paintView.draw(ms);
          }
          return { mode: paintView.mode, url: paintView.canvas.toDataURL('image/png') }; }""", bounds)
        p.close()
        if url["mode"] != "gpu": raise SystemExit("the look needs WebGL 2: " + url["mode"])
        img = Image.open(io.BytesIO(base64.b64decode(url["url"].split(",")[1]))).convert("RGB")
        img.save(out, quality=88)

    def close(self):
        self.browser.close(); self.pw.stop()


def main(names):
    build()
    for d in ("audio", "pictures"): os.makedirs(os.path.join(HERE, d), exist_ok=True)
    path = os.path.join(HERE, "results.json")
    results = json.load(open(path)) if os.path.exists(path) else {}
    looks = Looks()
    try:
        for name, key, width, chain in JOBS:
            if name not in names: continue
            prefix, length, notes = render(name, key, width, chain)
            m = step1.measures(prefix)
            r = step1.reads_of(prefix)
            spent, samples = map(float, open(prefix + ".cost").read().split())
            landed = r[:, 9:12].sum(axis=0); total = max(landed.sum(), 1e-12)
            times, thick, wet = step1.maps_of(prefix)
            frames, S = stamps_of(prefix)
            row = dict(scan=m, glow=round(float(np.median(r[:, 1])), 3), glow_p90=round(float(np.percentile(r[:, 1], 90)), 3),
                       motion=round(float(np.median(r[:, 2])), 3), memory=round(float(np.median(r[:, 3])), 3),
                       covered_p90=round(float(np.percentile(r[:, 8], 90)), 3),
                       into_wet=round(float(landed[0] / total), 3), onto_dry=round(float(landed[1] / total), 3),
                       onto_bare=round(float(landed[2] / total), 3), shares=shares(prefix, notes),
                       brush_cells=round(float(np.median(S[:, 4]) * N), 2) if len(S) else 0,
                       strokes=int(len(np.unique(S[:, 16]))) if len(S) else 0,
                       realtime=round(spent / (samples / step1.RATE), 4))
            step1.picture(thick[-1], wet[-1]).save(os.path.join(HERE, "pictures", "%s-%s-map.png" % (name, key)), optimize=True)
            looks.look(prefix, os.path.join(HERE, "pictures", "%s-%s-look.jpg" % (name, key)))
            if name == "run" and key == "today":
                looks.look(prefix, os.path.join(HERE, "pictures", "run-today-look-4fps.jpg"), fps=4)
            step1.mp3(prefix, os.path.join(HERE, "audio", "%s-%s.mp3" % (name, key)), length)
            results.setdefault(name, {})[key] = row
            print(name, key, json.dumps(row), flush=True)
            with open(path, "w") as f: json.dump(results, f, indent=1, sort_keys=True)
    finally:
        looks.close()


if __name__ == "__main__":
    main(sys.argv[1:] or list(PHRASES))
