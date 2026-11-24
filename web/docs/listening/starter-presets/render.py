"""The starter candidates heard and seen: each candidate's performance played
by the core from the setup code the page made for it (measure.py keeps it in
measured.json), and the same performance seen on the page.

For each candidate this writes, beside itself:

  audio/NAME.mp3                 the core's render_cpp playing the performance
                                 from the code alone, 64 kbps, at the
                                 instrument's own level (nothing normalised)
  pictures/NAME-xy-K.jpg         the page's screen at each of the performance's
  pictures/NAME-yt-K.jpg         moments, the performance played into the page in
                                 real time as a port's MIDI; X-Y as the preset
                                 ships, and Y-T the same setup with the display
                                 switched (which changes what Scan reads, so the
                                 Y-T run sounds a little different - only its
                                 look is kept)
  results.json                   per section of the performance: the heard
                                 brightness (spectral centroid), how far it is
                                 from the first section, RMS and peak; and, for
                                 the candidates and the bank alike, one C4 held
                                 three seconds: its brightness and its grit

Grit is the share of a held note's heard power that is not on the note's
harmonics (more than a fortieth of a semitone, or three bins, from every
multiple of half the fundamental - so a sub an octave down is the note's - between 2.5 and 3 s after the key): aliasing,
crushing, folding and the picture's noise all land there, and a clean tone
has almost none. Top is the share of the power above 2 kHz, at the strike
(the first 0.3 s) and held (2.5 to 3 s): a stepped or crushed wave is
harmonic, so grit misses it, and top does not. Both are here because the owner hears the bank converging on
one gritty sound, so the candidates are measured against it on that.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/listening/starter-presets/render.py [NAME ...] [--no-pictures]
"""
import importlib.util, json, os, subprocess, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CORE = os.path.join(ROOT, "core")
BUILD = os.path.join(CORE, "build", "listening", "starter-presets")
RENDER = os.path.join(BUILD, "render_cpp")
PAGE = "file://" + os.path.join(ROOT, "web", "scope.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
RATE = 48000

_spec = importlib.util.spec_from_file_location("candidates", os.path.join(HERE, "candidates.py"))
cand = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cand)


def slug(name): return name.lower().replace(" ", "-")


def build():
    os.makedirs(BUILD, exist_ok=True)
    subprocess.run(["g++", "-std=c++17", "-O2", "-I", os.path.join(CORE, "include"),
                    os.path.join(CORE, "tests", "tools", "render_cpp.cpp"), "-o", RENDER], check=True)


def events_of(notes, events):
    ev = []
    for t, n, v, d in notes:
        ev.append((t, [0x90, n, v])); ev.append((t + d, [0x80, n, 0]))
    ev += events
    ev.sort(key=lambda e: (e[0], e[1][0] == 0x90))   # an off before an on at the same moment
    return ev


def play(code, ev, length, out):
    """render_cpp playing `ev` on the code, the heard pair recorded into `out` (float32, interleaved)."""
    lines = [["make", RATE, code], ["record", "heard", out]]
    for t, msg in ev: lines += [["to", round(t, 6)], ["midi"] + msg]
    lines += [["to", length], ["record", "heard"]]
    script = out + ".script"
    with open(script, "w") as f: f.write("\n".join(json.dumps(l) for l in lines) + "\n")
    subprocess.run([RENDER, script], check=True, capture_output=True)
    return np.fromfile(out, np.float32).reshape(-1, 2).astype(np.float64)


# honestytest's bands (see measure.py), on the heard left channel, windows of 4096 half overlapped.
W = 4096
HANN = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(W) / (W - 1))
_f = np.arange(W // 2) * RATE / W
BAND = np.where(_f >= 40, np.minimum(47, np.floor(np.log2(np.maximum(_f, 1e-9) / 40) * 5)), -1).astype(int)


def heard(x, sections):
    out = []
    for label, t0, t1 in sections:
        seg = x[int(t0 * RATE):int(t1 * RATE), 0]
        specs, cens, pows = [], [], []
        for i in range(0, len(seg) - W, W // 2):
            p = np.abs(np.fft.rfft(seg[i:i + W] * HANN)[:W // 2]) ** 2
            if p.sum() <= 1e-12: continue
            b = np.bincount(BAND[BAND >= 0], weights=p[BAND >= 0], minlength=48)
            specs.append(np.sqrt(b / b.sum())); cens.append(float((p * _f).sum() / p.sum())); pows.append(float(p.sum()))
        both = x[int(t0 * RATE):int(t1 * RATE)]
        out.append(dict(label=label, t0=round(t0, 2), t1=round(t1, 2), spec=np.mean(specs, axis=0),
                        hz=round(float(np.average(cens, weights=pows))), rms=round(float(np.sqrt(np.mean(both ** 2))), 3),
                        peak_db=round(float(20 * np.log10(max(np.abs(both).max(), 1e-9))), 1)))
    for row in out:
        row["changed"] = round(float(np.sqrt(((row["spec"] - out[0]["spec"]) ** 2).sum())), 3)
    for row in out: del row["spec"]
    return out


def held_c4(code, tag):
    """One C4 at velocity 100 held three seconds from 0.9 s after the load: its brightness and grit 2.5 to 3 s in."""
    x = play(code, [(0.9, [0x90, 60, 100]), (3.9, [0x80, 60, 0])], 4.0, os.path.join(BUILD, tag + "-c4.f32"))
    seg = x[int(3.4 * RATE):int(3.9 * RATE), 0]
    n = len(seg)
    p = np.abs(np.fft.rfft(seg * np.hanning(n))) ** 2
    f = np.arange(len(p)) * RATE / n
    # The note's own fundamental, found near C4 (the setup tunes it just or equal), refined between bins; and the grid
    # its half, so a sub an octave down (a bass's sub, the drawbars' 16') counts as the note's, not as grit. What
    # that costs: a partial at an odd half-multiple is counted as the note's too.
    lo, hi = int(250 * n / RATE), int(275 * n / RATE)
    k = lo + int(np.argmax(p[lo:hi]))
    a_, b_, c_ = np.log(p[k - 1:k + 2] + 1e-30)
    f0 = (k + 0.5 * (a_ - c_) / (a_ - 2 * b_ + c_)) * RATE / n
    base = f0 / 2
    h = f / base
    near = np.abs(h - np.round(h)) * base < np.maximum(f * (2 ** (1 / 480) - 1), 3 * RATE / n)
    on = (np.round(h) >= 1) & near & (f < 20000)
    audible = (f >= 30) & (f < 20000)
    grit = float(p[audible & ~on].sum() / max(p[audible].sum(), 1e-20))
    def top(t0, t1):
        w = x[int(t0 * RATE):int(t1 * RATE), 0]
        q = np.abs(np.fft.rfft(w * np.hanning(len(w)))) ** 2
        g = np.arange(len(q)) * RATE / len(w)
        return round(100 * float(q[(g >= 2000) & (g < 20000)].sum() / max(q[(g >= 30) & (g < 20000)].sum(), 1e-20)), 2)
    return dict(hz=round(float((p * f)[audible].sum() / p[audible].sum())), grit=round(100 * grit, 2),
                rms=round(float(np.sqrt(np.mean(seg ** 2))), 3), top_strike=top(0.95, 1.25), top_held=top(3.4, 3.9))


def mp3(raw, out, length):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "2", "-i", raw,
                    "-af", "afade=t=out:st=%g:d=0.3" % (length - 0.3), "-ar", "44100", "-b:a", "64k", out], check=True)


# --- the page's look -----------------------------------------------------------

LOAD = r"""async ([name, setup]) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  setScreenKeys(false);
  PRESETS.push(["Candidates", [[name, setup, "", ["", ""]]], "generator"]);
  applyPreset('b:' + name);
  await wait(1500);
  return { display: snapshot().display, hears: midiCoreHears() };
}"""

# The performance as a port's bytes, each at its moment after the start, on the page's own clock.
PERFORM = r"""(ev) => { const t0 = performance.now(); window.__t0 = t0;
  for (const [t, msg] of ev) setTimeout(() => midiBytes(msg), Math.max(0, t * 1000 - (performance.now() - t0))); }"""


def looks(browser, name, setup, ev, moments, view):
    page = browser.new_page(viewport={"width": 1400, "height": 900}, device_scale_factor=2)
    bad = []
    page.on("pageerror", lambda e: bad.append(str(e)))
    page.goto(PAGE); page.wait_for_timeout(1500)
    if page.locator("#helpClose").is_visible(): page.locator("#helpClose").click()
    page.locator("#trace").click(position={"x": 5, "y": 5}); page.wait_for_timeout(500)
    got = page.evaluate(LOAD, [name + " " + view, dict(setup, display=view)])
    if got["display"] != view or not got["hears"]: raise SystemExit("%s: the page is not ready %s" % (name, got))
    page.evaluate(PERFORM, [[t, m] for t, m in ev])
    start = time.monotonic()
    took = []
    for k, m in enumerate(moments):
        while time.monotonic() - start < m: time.sleep(0.005)
        took.append(round(page.evaluate("() => (performance.now() - window.__t0) / 1000"), 2))
        page.locator("#trace").screenshot(path=os.path.join(HERE, "pictures", "%s-%s-%d.jpg" % (slug(name), view, k)), type="jpeg", quality=82)
    page.close()
    if bad: raise SystemExit("%s: page errors %s" % (name, bad[:2]))
    return took


def main(args):
    names = [a for a in args if not a.startswith("--")]
    build()
    measured = json.load(open(os.path.join(HERE, "measured.json")))
    for d in ("audio", "pictures"): os.makedirs(os.path.join(HERE, d), exist_ok=True)
    path = os.path.join(HERE, "results.json")
    results = json.load(open(path)) if os.path.exists(path) else {}
    results.setdefault("candidates", {}); results.setdefault("bank", {})
    todo = [n for n in cand.ALL if not names or n in names]
    for name in todo:
        c = cand.ALL[name]
        notes, events, length, sections, moments = c["play"]()
        ev = events_of(notes, events)
        raw = os.path.join(BUILD, slug(name) + ".f32")
        x = play(measured[name]["code"], ev, length, raw)
        mp3(raw, os.path.join(HERE, "audio", slug(name) + ".mp3"), length)
        row = dict(sections=heard(x, sections), c4=held_c4(measured[name]["code"], slug(name)),
                   peak_db=round(float(20 * np.log10(np.abs(x).max())), 1), length=length)
        results["candidates"].setdefault(name, {}).update(row)
        print(name, json.dumps(row), flush=True)
    # The bank as shipped, on the same held C4, for the comparison of grit.
    if not names:
        codes = bank_codes()
        for bname, code in codes.items():
            results["bank"][bname] = held_c4(code, "bank-" + slug(bname))
            print("bank", bname, results["bank"][bname], flush=True)
    with open(path, "w") as f: json.dump(results, f, indent=1, sort_keys=True)
    if "--no-pictures" in args: return
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
        for name in todo:
            c = cand.ALL[name]
            notes, events, length, sections, moments = c["play"]()
            ev = events_of(notes, events)
            took = {view: looks(browser, name, c["setup"], ev, moments, view) for view in ("xy", "yt")}
            results["candidates"][name]["moments"] = took
            print(name, "pictured at", took, flush=True)
            with open(path, "w") as f: json.dump(results, f, indent=1, sort_keys=True)
        browser.close()


BANK_NAMES = "() => PRESETS.flatMap(([, entries]) => entries.map(([n]) => n))"
# Each preset from a fresh page, as honestytest loads them, so nothing carries over from the one before.
BANK_CODE = "(n) => { setScreenKeys(true); applyPreset('b:' + n); return encodeSetup(snapshot()); }"


def bank_codes():
    from playwright.sync_api import sync_playwright
    out = {}
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
        names = None
        while names is None or len(out) < len(names):
            p = b.new_page(viewport={"width": 1400, "height": 900})
            p.goto(PAGE); p.wait_for_timeout(1200)
            if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
            if names is None: names = p.evaluate(BANK_NAMES)
            n = names[len(out)]
            out[n] = p.evaluate(BANK_CODE, n)
            p.close()
        b.close()
    return out


if __name__ == "__main__":
    main(sys.argv[1:])
