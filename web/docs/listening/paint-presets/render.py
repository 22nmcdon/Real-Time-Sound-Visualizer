"""Paint presets: four candidate sounds made for Paint, each played through a
short performance with the painting building, and the same performance on the
nearest bank preset as it ships (on the trace), so the owner hears what Paint
adds. None of them is in the bank; the owner chooses.

The setup codes are the page's own: measure.py loads each candidate as a
player loads a preset and keeps the code the page sends the instrument
(measured.json), and that code is what is rendered here and printed on the
listening page. render.cpp beside this file is the instrument itself, never
told to paint from outside, so it paints because the code says
`screenDraws: "paint"` - as the testing site does when the code is pasted.

For each candidate and way (`paint`, the candidate; `bank`, the nearest
preset) this writes, beside itself:

  audio/NAME-WAY.mp3              what the core plays, 64 kbps
  pictures/NAME-look-K.jpg        the live look at each of the performance's
                                  moments: the page's own paintView in headless
                                  Chromium's WebGL 2, fed the core's stamps a
                                  sixtieth of a second at a time (paint-width's way)
  pictures/NAME-map-K.png         the map Scan reads at the same moments
                                  (thickness grey, wet paint blue)
  results.json                    per section of the performance: Scan's table
                                  (its centroid, a sine 1, and how far it moves frame
                                  to frame), the Picture amount's three reads, and
                                  the paint on the canvas at the section's end

    CHROME=/opt/pw-browsers/chromium python3 web/docs/listening/paint-presets/measure.py
    CHROME=/opt/pw-browsers/chromium python3 web/docs/listening/paint-presets/render.py [NAME ...]
"""
import base64, importlib.util, io, json, os, subprocess, sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CORE = os.path.join(ROOT, "core")
BUILD = os.path.join(CORE, "build", "listening", "paint-presets")
PAGE = os.path.join(ROOT, "web", "scope.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
GL = ["--autoplay-policy=no-user-gesture-required", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
RATE, BLOCK, N, FLOATS = 48000, 128, 128, 23


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cand = load("candidates", os.path.join(HERE, "candidates.py"))
step1 = load("step1", os.path.join(HERE, "..", "painting-step1", "render.py"))


def script(code, notes, events, length):
    ev = []
    for t, n, v, d in notes:
        ev.append((t, [0x90, n, v])); ev.append((t + d, [0x80, n, 0]))
    ev += events
    ev.sort(key=lambda e: e[0])
    lines = [json.dumps(["make", RATE, BLOCK, code])]
    blocks, k = int(length * RATE / BLOCK), 0
    for b in range(blocks):
        top = (b + 1) * BLOCK / RATE
        while k < len(ev) and ev[k][0] < top:
            lines.append(json.dumps(["midi"] + ev[k][1])); k += 1
        lines.append('["block",128]')
    return "\n".join(lines) + "\n"


def build():
    os.makedirs(BUILD, exist_ok=True)
    subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(CORE, "include"),
                    os.path.join(HERE, "render.cpp"), "-o", os.path.join(BUILD, "render")], check=True)


def render(name, way, code):
    notes, events, length, _ = cand.ALL[name]["play"]()
    path = os.path.join(BUILD, "%s-%s.script" % (slug(name), way))
    with open(path, "w") as f: f.write(script(code, notes, events, length))
    prefix = os.path.join(BUILD, "%s-%s" % (slug(name), way))
    subprocess.run([os.path.join(BUILD, "render"), path, prefix], check=True)
    return prefix, length


def slug(name): return name.lower().replace(" ", "-")


def stamps_of(prefix):
    raw = open(prefix + ".stamps", "rb").read()
    frames, rows, i = [], [], 0
    while i < len(raw):
        f, n = np.frombuffer(raw[i:i + 8], np.int32); i += 8
        rows.append(np.frombuffer(raw[i:i + n * 4 * FLOATS], np.float32).reshape(n, FLOATS)); i += n * 4 * FLOATS
        frames += [f] * n
    return np.array(frames, dtype=np.int64), (np.concatenate(rows) if rows else np.zeros((0, FLOATS), np.float32))


def tables(prefix, reads):
    """Each table read: its time, who (a note, or a layer below nought), and its harmonic powers."""
    rec = np.fromfile(prefix + ".tables", np.float32).reshape(-1, 3 + 512)
    if not len(rec): return np.zeros(0), np.zeros(0, int), np.zeros((0, 64))
    frame = rec[:, 0].astype(int)
    t = reads[np.clip(frame, 0, len(reads) - 1), 0]
    return t, rec[:, 1].astype(int), frame, step1.powers(rec[:, 3:])


# The heard sound's spectrum as honestytest.py reads it: forty-eight bands a fifth of an octave wide from 40 Hz, each
# band's share of the whole as an amplitude, so loudness drops out; windows of 4096, Hann, half overlapped.
W = 4096
HANN = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(W) / (W - 1))
_f = np.arange(W // 2) * RATE / W
BAND = np.where(_f >= 40, np.minimum(47, np.floor(np.log2(np.maximum(_f, 1e-9) / 40) * 5)), -1).astype(int)


def heard(prefix, sections):
    """Each section of what is heard (the left channel): its mean band spectrum, its brightness (the power-weighted
    spectral centroid in Hz) and its RMS."""
    x = np.fromfile(prefix + ".f32", np.float32).reshape(-1, 2)[:, 0].astype(np.float64)
    out = []
    for _, t0, t1 in sections:
        seg = x[int(t0 * RATE):int(t1 * RATE)]
        specs, cens, powers = [], [], []
        for i in range(0, len(seg) - W, W // 2):
            p = np.abs(np.fft.fft(seg[i:i + W] * HANN)[:W // 2]) ** 2
            b = np.bincount(BAND[BAND >= 0], weights=p[BAND >= 0], minlength=48)
            if b.sum() <= 0: continue
            specs.append(np.sqrt(b / b.sum())); cens.append(float((p * _f).sum() / p.sum())); powers.append(float(p.sum()))
        out.append((np.mean(specs, axis=0), float(np.average(cens, weights=powers)), float(np.sqrt(np.mean(seg ** 2)))))
    return out


def section_rows(prefix, sections, painting):
    reads = step1.reads_of(prefix)
    ears = heard(prefix, sections)
    t, who, frame, pw = tables(prefix, reads)
    cen = (pw * np.arange(1, 65)).sum(axis=1) if len(pw) else np.zeros(0)
    move = np.full(len(t), np.nan)
    last = {}
    for i in range(len(t)):
        if who[i] in last and last[who[i]][0] == frame[i] - 1: move[i] = 0.5 * np.abs(pw[i] - pw[last[who[i]][1]]).sum()
        last[who[i]] = (frame[i], i)
    if painting:
        mt, thick, wet = step1.maps_of(prefix)
    rows = []
    for label, t0, t1 in sections:
        sel = (t >= t0) & (t < t1)
        rsel = (reads[:, 0] >= t0) & (reads[:, 0] < t1)
        spec, hz, rms = ears[len(rows)]
        row = dict(label=label, t0=t0, t1=t1, hz=round(hz), rms=round(rms, 3),
                   # How far this section's sound is from the first's, as honestytest's movement measures a quarter second.
                   changed=round(float(np.sqrt(((spec - ears[0][0]) ** 2).sum())), 3),
                   centroid=round(float(np.median(cen[sel])), 2) if sel.any() else None,
                   movement=round(float(np.nanmedian(move[sel])), 4) if sel.any() and np.isfinite(move[sel]).any() else None,
                   glow=round(float(np.median(reads[rsel, 1])), 3), motion=round(float(np.median(reads[rsel, 2])), 3),
                   memory=round(float(np.median(reads[rsel, 3])), 3))
        if painting:
            k = int(np.argmin(np.abs(mt - t1)))
            row["paint"] = round(float(thick[k].sum()), 1)
            row["wet"] = round(float((thick[k] * wet[k]).sum() / max(float(thick[k].sum()), 1e-9)), 2)
        rows.append(row)
    return rows


def series(prefix):
    """The Picture amount's Glow, Motion and Memory a tenth of a second at a time, for the page's drawing."""
    reads = step1.reads_of(prefix)
    out = {"t": [], "glow": [], "motion": [], "memory": []}
    for t0 in np.arange(0, reads[-1, 0], 0.1):
        sel = (reads[:, 0] >= t0) & (reads[:, 0] < t0 + 0.1)
        if not sel.any(): continue
        out["t"].append(round(float(t0), 2))
        for k, key in ((1, "glow"), (2, "motion"), (3, "memory")): out[key].append(round(float(reads[sel, k].mean()), 3))
    return out


def centroid_series(prefix):
    """Scan's table centroid a tenth of a second at a time, the mean over what is sounding."""
    reads = step1.reads_of(prefix)
    t, who, frame, pw = tables(prefix, reads)
    out = {"t": [], "centroid": []}
    if not len(t): return out
    cen = (pw * np.arange(1, 65)).sum(axis=1)
    for t0 in np.arange(0, reads[-1, 0], 0.1):
        sel = (t >= t0) & (t < t0 + 0.1)
        if not sel.any(): continue
        out["t"].append(round(float(t0), 2)); out["centroid"].append(round(float(cen[sel].mean()), 3))
    return out


class Looks:
    """The page's own paintView, painting a render's stamps a sixtieth of a second at a time, kept at moments."""

    def __init__(self):
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(executable_path=CHROME, args=GL)

    def looks(self, prefix, moments, outs):
        frames, S = stamps_of(prefix)
        p = self.browser.new_page(viewport={"width": 1400, "height": 900})
        p.goto("file://" + PAGE); p.wait_for_timeout(1500); p.keyboard.press("Escape")
        p.evaluate("(b64) => { const s = atob(b64), u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i);"
                   " window.__stamps = new Float32Array(u.buffer); }", base64.b64encode(S.astype(np.float32).tobytes()).decode())
        last = max(int(round(max(moments) * 60)), int(frames.max()) if len(frames) else 0)
        bounds, i = [], 0
        for f0 in range(0, last + 1):
            j = i
            while j < len(frames) and frames[j] < f0 + 1: j += 1
            bounds.append((i, j, (f0 + 1) * 1000 / 60)); i = j
        keep = [int(round(m * 60)) for m in moments]
        got = p.evaluate("""([bounds, keep]) => { paintView.setOn(true); paintView.clear(); const out = {};
          bounds.forEach(([a, b, ms], f) => {
            if (b > a) paintView.take({ on: true, from: a, count: b - a, stamps: window.__stamps.subarray(a * 23, b * 23) });
            paintView.draw(ms);
            if (keep.includes(f)) out[f] = paintView.canvas.toDataURL('image/png');
          });
          return { mode: paintView.mode, out }; }""", [bounds, keep])
        p.close()
        if got["mode"] != "gpu": raise SystemExit("the look needs WebGL 2: " + got["mode"])
        for f, path in zip(keep, outs):
            img = Image.open(io.BytesIO(base64.b64decode(got["out"][str(f)].split(",")[1]))).convert("RGB")
            img.resize((512, 512), Image.LANCZOS).save(path, quality=86)

    def close(self):
        self.browser.close(); self.pw.stop()


def mp3(prefix, out, length):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "2", "-i",
                    prefix + ".f32", "-af", "afade=t=out:st=%g:d=0.3" % (length - 0.3), "-ar", "44100", "-b:a", "64k",
                    out], check=True)


def main(names):
    build()
    measured = json.load(open(os.path.join(HERE, "measured.json")))
    for d in ("audio", "pictures"): os.makedirs(os.path.join(HERE, d), exist_ok=True)
    path = os.path.join(HERE, "results.json")
    results = json.load(open(path)) if os.path.exists(path) else {}
    looks = Looks()
    try:
        for name, c in cand.ALL.items():
            if names and name not in names: continue
            _, _, length, sections = c["play"]()
            moments = c["moments"]
            out = {}
            for way, key in (("paint", name), ("bank", "bank: " + c["nearest"])):
                prefix, length = render(name, way, measured[key]["code"])
                painting = way == "paint"
                out[way] = dict(sections=section_rows(prefix, sections, painting), reads=series(prefix),
                                centroid=centroid_series(prefix))
                mp3(prefix, os.path.join(HERE, "audio", "%s-%s.mp3" % (slug(name), way)), length)
                if painting:
                    mt, thick, wet = step1.maps_of(prefix)
                    for k, m in enumerate(moments):
                        i = int(np.argmin(np.abs(mt - m)))
                        step1.picture(thick[i], wet[i], 256).save(os.path.join(HERE, "pictures", "%s-map-%d.png" % (slug(name), k)),
                                                                 optimize=True)
                    looks.looks(prefix, moments, [os.path.join(HERE, "pictures", "%s-look-%d.jpg" % (slug(name), k))
                                                  for k in range(len(moments))])
                print(name, way, json.dumps(out[way]["sections"]), flush=True)
            results[name] = out
            with open(path, "w") as f: json.dump(results, f, indent=1, sort_keys=True)
    finally:
        looks.close()


if __name__ == "__main__":
    main(sys.argv[1:])
