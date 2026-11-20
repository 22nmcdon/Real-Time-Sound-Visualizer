"""Paint width: the study's four phrases painted by the core at three base
brush widths, sound and picture together, for the owner to choose between.

The owner's rule (18 Nov): the picture must be true to the sound. The look and
the paint map Scan reads are the same strokes, the same positions and widths;
the look may render them finer, with texture and light, but never wider or
narrower. So a wider brush is wider for the sound too: neighbouring notes share
more paint, and a note's tone is coloured by its register.

The widths are PaintParams::width over the brush step 2 shipped (a brush one
to four of the map's 128 cells across by its pressure); the owner chose
medium (19 Nov), now the default:

  today    1     as step 2 painted
  medium   2     the default since 19 Nov
  wide     3.5   near the study's physical brush

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

A note struck alone goes on with the last one's stroke while that one still
sounds above -24 dB of its peak, or while the sustain pedal is down
(PaintParams::join, the owner's rule of 19 Nov). Since that changes what Scan
reads, the fast run and a slow melody - on Tine piano, a long pad, a short
pluck, and the pluck under the pedal - are rendered at medium both ways,
"-separate" being every note a stroke of its own as step 2 painted.

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
    """A melody at one note a second, legato (each held 0.95 s): the case the
    join's rule is about - joined while a note still sounds at the next
    strike, or under the pedal, and not by the clock."""
    notes = [(0.3 + k, n, 80, 0.95) for k, n in enumerate((60, 64, 67, 72, 71, 67, 64, 62, 60))]
    return notes, 10.0


# A short pluck: Tine piano's settings with its envelope cut to a quarter-second decay to nothing.
PLUCK = {"shape": "sine", "midiMode": "poly", "oscScan": 50, "pictureAmount": 0, "atk": 1, "dec": 250, "sus": 0, "rel": 150}

# Each phrase: its title, what it plays on (a preset's name, or a setup), how its notes go, and whether the pedal is down.
PHRASES = {k: (title, preset, make, False) for k, (title, preset, make) in step1.PHRASES.items()}
PHRASES.update({
    "slow-tine": ("Slow melody, Tine piano", "Tine piano", slow_melody, False),
    "slow-pad": ("Slow melody, Slow pad", "Slow pad", slow_melody, False),
    "slow-pluck": ("Slow melody, a short pluck", PLUCK, slow_melody, False),
    "slow-pluck-pedal": ("Slow melody, the pluck under the pedal", PLUCK, slow_melody, True),
})
# What is rendered: the study's four phrases at the three widths, joined as the instrument now joins; and at the
# width chosen, joined against separate ("-separate", every note a stroke of its own as step 2 painted), the fast run
# and the slow melody on Tine piano, a long pad, a short pluck, and the pluck under the pedal.
PICK = "medium"
JOBS = [(name, w, WIDTHS[w], None) for name in step1.PHRASES for w in WIDTHS]
JOBS += [("run", PICK + "-separate", WIDTHS[PICK], 0)]
for name in ("slow-tine", "slow-pad", "slow-pluck", "slow-pluck-pedal"):
    JOBS += [(name, PICK, WIDTHS[PICK], None), (name, PICK + "-separate", WIDTHS[PICK], 0)]


def script(code, notes, length, pedal):
    """painting-step1's script, and the sustain pedal down from the start to the end if asked."""
    text = step1.script(code, notes, length)
    if not pedal: return text
    lines = text.splitlines()
    return "\n".join(lines[:1] + ['["midi",176,64,127]'] + lines[1:]) + "\n"


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


def render(name, key, width, join):
    _, preset, make, pedal = PHRASES[name]
    code = step1.CROSSED if preset is None else json.dumps(preset) if isinstance(preset, dict) else preset_code(preset)
    notes, length = make()
    path = os.path.join(BUILD, name + ".script")
    with open(path, "w") as f: f.write(script(code, notes, length, pedal))
    prefix = os.path.join(BUILD, "%s-%s" % (name, key))
    subprocess.run([os.path.join(BUILD, "render"), path, prefix, str(width)] + ([] if join is None else [str(join)]), check=True)
    return prefix, length, sorted({n for _, n, _, _ in notes})


def stamps_of(prefix, floats=20):
    """A render's stamps: `floats` a row, twenty as this page's render.cpp writes them (step 2), twenty-three as
    the instrument serves them since step 3's drops and pull (the controllers' render.cpp)."""
    raw = open(prefix + ".stamps", "rb").read()
    frames, rows, i = [], [], 0
    while i < len(raw):
        f, n = np.frombuffer(raw[i:i + 8], np.int32); i += 8
        rows.append(np.frombuffer(raw[i:i + n * 4 * floats], np.float32).reshape(n, floats)); i += n * 4 * floats
        frames += [f] * n
    return np.array(frames, np.int32), (np.concatenate(rows) if rows else np.zeros((0, floats), np.float32))


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

    def look(self, prefix, out, fps=60, floats=20, crop=None):
        frames, S = stamps_of(prefix, floats)
        # The page takes its own width of row (PAINT_STAMP): a narrower render's rows are widened with noughts, a brush's kind.
        S = np.pad(S, ((0, 0), (0, max(0, 23 - S.shape[1]))))
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
            if (b > a) paintView.take({ on: true, from: a, count: b - a, stamps: window.__stamps.subarray(a * 23, b * 23) });
            paintView.draw(ms);
          }
          return { mode: paintView.mode, url: paintView.canvas.toDataURL('image/png') }; }""", bounds)
        p.close()
        if url["mode"] != "gpu": raise SystemExit("the look needs WebGL 2: " + url["mode"])
        img = Image.open(io.BytesIO(base64.b64decode(url["url"].split(",")[1]))).convert("RGB")
        img.save(out, quality=88)
        # And a close-up, `crop` a box in the canvas's unit square (left, top, right, bottom), at the look's own pixels doubled, smoothly (nearest-neighbour doubling drew every edge in steps).
        # `crop` may be one (box, path) or a list of them.
        for box, path in ([crop] if crop and not isinstance(crop, list) else crop or []):
            n = img.size[0]
            box = tuple(int(round(v * n)) for v in box)
            img.crop(box).resize(((box[2] - box[0]) * 2, (box[3] - box[1]) * 2), Image.LANCZOS).save(path, quality=92)

    def close(self):
        self.browser.close(); self.pw.stop()


def main(names):
    build()
    for d in ("audio", "pictures"): os.makedirs(os.path.join(HERE, d), exist_ok=True)
    path = os.path.join(HERE, "results.json")
    results = json.load(open(path)) if os.path.exists(path) else {}
    looks = Looks()
    try:
        for name, key, width, join in JOBS:
            if name not in names: continue
            prefix, length, notes = render(name, key, width, join)
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
