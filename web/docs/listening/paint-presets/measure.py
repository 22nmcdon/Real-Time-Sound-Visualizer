"""Each candidate judged by its heading as honestytest.py judges the bank's.

The same path: the page loads the setup as a player loads a preset (it is put
in the page's PRESETS for the moment and loaded with applyPreset, with the
screen's keys open), hands over the setup code it would send the instrument,
and the core rendered offline (render_cpp) plays one note held ten seconds
from each of five moments after the load. The readings, the windows and the
rules are honestytest's, copied here rather than imported because that suite
runs as it is imported; `RULES` and the rest below are its text. If the suite's
rules change, this page's verdicts are the old ones until it is run again.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/listening/paint-presets/measure.py [NAME ...]

Writes measured.json beside itself: each candidate's moments, its verdicts,
the limiter on honestytest's chord, and the setup code the page made.
"""
import importlib.util, json, os, subprocess, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CORE = os.path.join(ROOT, "core")
PAGE = "file://" + os.path.join(ROOT, "web", "scope.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
BUILD = os.path.join(CORE, "build", "listening", "paint-presets")
RENDER = os.path.join(BUILD, "render_cpp")

_spec = importlib.util.spec_from_file_location("candidates", os.path.join(HERE, "candidates.py"))
cand = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cand)

# --- honestytest.py's, as it stands at 722da4c ---------------------------------
HOLD, AFTER = 10.0, 4.5
RATE, N, GAP = 48000, 4096, 12000
MOMENTS = (0.9, 1.0, 1.25, 1.5, 2.0)
HANN = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(N) / (N - 1))
_f = np.arange(N // 2) * 44100 / N
BAND = np.full(N // 2, -1)
BAND[1:] = np.where(_f[1:] >= 40, np.minimum(47, np.floor(np.log2(np.maximum(_f[1:], 1e-9) / 40) * 5)), -1)
RULES = {
    "Still": lambda m: m["most"] < 0.005,
    "Settled": lambda m: m["early"] >= 0.008 and m["late"] <= 0.015 and m["late"] <= m["early"] / 2,
    "Breathing": lambda m: m["late"] >= 0.019 and m["afterRms"] < 0.005,
}


def render(lines, record=None):
    tag = "%d-%d" % (os.getpid(), abs(hash(json.dumps(lines))) % 10**9)
    script, lanes = os.path.join(BUILD, "s-%s.txt" % tag), os.path.join(BUILD, "l-%s.f32" % tag)
    if record: lines = lines[:1] + [["record", "lanes", lanes]] + lines[1:] + [["record", "lanes"]]
    with open(script, "w") as f: f.write("\n".join(json.dumps(l) for l in lines) + "\n")
    out = subprocess.run([RENDER, script], check=True, capture_output=True, text=True).stdout
    got = np.fromfile(lanes, dtype=np.float32).reshape(-1, 6) if record else None
    for path in (script, lanes):
        if os.path.exists(path): os.remove(path)
    return out, got


def spectrum(x):
    p = np.abs(np.fft.fft(x * HANN)[:N // 2]) ** 2
    bands = np.bincount(BAND[BAND >= 0].astype(int), weights=p[BAND >= 0], minlength=48)
    total = bands.sum()
    return np.sqrt(bands / total) if total > 0 else bands


def held_note(code, notes, at):
    _, lanes = render([["make", RATE, code], ["to", at]] + [["midi", 0x90, n, 100] for n in notes]
                      + [["to", at + HOLD]] + [["midi", 0x80, n, 0] for n in notes] + [["to", at + HOLD + AFTER + 0.1]], record=True)
    l = lanes[:, 0].astype(np.float64) + lanes[:, 2]
    on, out = int(round(at * RATE)), []
    for k in range(1, int(RATE * (HOLD + AFTER)) // GAP + 1):
        end, t = on + k * GAP, k * GAP / RATE
        w = l[end - N - GAP:end]
        move = 0.0 if k == 1 else float(np.sqrt(((spectrum(w[GAP:]) - spectrum(w[:N])) ** 2).sum()))
        out.append({"t": t, "phase": "held" if t <= HOLD else "after", "move": move, "rms": float(np.sqrt((w[GAP:] ** 2).mean()))})
    return out


def mean(xs): return sum(xs) / len(xs) if xs else 0.0


def summary(out):
    held = [s for s in out if s["phase"] == "held"]
    after = [s for s in out if s["phase"] == "after" and s["t"] >= HOLD + 2.5]
    return {
        "early": mean([s["move"] for s in held if 0.3 <= s["t"] < 2.0]),
        "late": mean([s["move"] for s in held if s["t"] >= HOLD - 3.0]),
        "most": max([s["move"] for s in held if s["t"] >= 0.5] or [0.0]),
        "afterRms": mean([s["rms"] for s in after]),
        "afterMove": mean([s["move"] for s in after]),
        "heldRms": mean([s["rms"] for s in held if s["t"] >= 0.5]),
    }


def judged(code, notes):
    ms = [summary(held_note(code, notes, at)) for at in MOMENTS]
    return ms, {h: all(rule(m) for m in ms) for h, rule in RULES.items()}


def limiter_on_chord(code, notes):
    out, _ = render([["make", RATE, code], ["to", 0.9]] + [["midi", 0x90, n, 110] for n in notes]
                    + [["every", 0.125, "limiter"], ["to", 2.9]])
    return min([0.0] + [float(line.split()[2]) for line in out.split("\n") if line.startswith("limiter ")])


def probes(setup):
    if setup.get("layers") == "split": return [[36], [67]]
    return [[60]]


def chord(setup):
    return [36, 43, 64, 67] if setup.get("layers") == "split" else [48, 55, 60, 64]
# -----------------------------------------------------------------------------


LOAD = r"""async ([name, setup]) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  setScreenKeys(true);
  if (setup) PRESETS.push(["Candidates", [[name, setup, "", ["", ""]]], "generator"]);
  applyPreset('b:' + name);
  await wait(300);
  return { code: encodeSetup(snapshot()), draws: state.draws, amount: Number(el.pictureAmount.value), setup: findPreset('b:' + name) };
}"""


def codes(entries):
    """The setup code the page sends the instrument for each (name, setup); setup None for a bank preset."""
    from playwright.sync_api import sync_playwright
    out = {}
    with sync_playwright() as pw:
        for name, setup in entries:
            b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
            p = b.new_page(viewport={"width": 1400, "height": 900})
            bad = []
            p.on("pageerror", lambda e: bad.append(str(e)))
            p.goto(PAGE); p.wait_for_timeout(1200)
            if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
            p.locator("#trace").click(position={"x": 5, "y": 5})
            p.wait_for_timeout(600)
            out[name] = p.evaluate(LOAD, [name, setup])
            if bad: raise SystemExit("page errors loading %s: %s" % (name, bad[:2]))
            b.close()
    return out


def build():
    os.makedirs(BUILD, exist_ok=True)
    subprocess.run(["g++", "-std=c++17", "-O2", "-I", os.path.join(CORE, "include"),
                    os.path.join(CORE, "tests", "tools", "render_cpp.cpp"), "-o", RENDER], check=True)


def verdict_of(v):
    return ",".join(h for h, ok in v.items() if ok) or "none"


def main(names):
    build()
    path = os.path.join(HERE, "measured.json")
    results = json.load(open(path)) if os.path.exists(path) else {}
    todo = [(n, c["setup"]) for n, c in cand.ALL.items() if not names or n in names]
    # The bank presets they are heard beside, by name, as shipped; probed as honestytest probes them.
    todo += [("bank: " + n, None) for n in cand.BANK if not names or "bank: " + n in names]
    got = codes([(n[6:] if s is None else n, s) for n, s in todo])
    for name, setup in todo:
        key = name[6:] if setup is None else name
        if setup is None: setup = got[key]["setup"]
        code = got[key]["code"]
        limit = limiter_on_chord(code, chord(setup))
        row = dict(code=code, draws=got[key]["draws"], limiter=round(limit, 2), probes=[])
        for notes in probes(setup):
            ms, verdicts = judged(code, notes)
            row["probes"].append(dict(notes=notes, verdict=verdict_of(verdicts),
                                      early=[round(m["early"], 4) for m in ms], late=[round(m["late"], 4) for m in ms],
                                      most=round(max(m["most"] for m in ms), 4), after_rms=round(max(m["afterRms"] for m in ms), 4),
                                      held_rms=round(min(m["heldRms"] for m in ms), 4)))
            print("%-26s %-8s %-9s early %s late %s after %.4f limiter %.1f -> %s" % (
                name, row["draws"], notes, "/".join("%.3f" % m["early"] for m in ms), "/".join("%.3f" % m["late"] for m in ms),
                max(m["afterRms"] for m in ms), limit, verdict_of(verdicts)), flush=True)
        results[name] = row
        with open(path, "w") as f: json.dump(results, f, indent=1, sort_keys=True)


if __name__ == "__main__":
    main(sys.argv[1:])
