"""What the Plane's switch should give when it has nothing to put back (17 Nov).

Until now its switch, with nothing kept, opened the module to choose a
shaping, so a player who pressed it heard nothing happen. The delay (35),
the chorus (30), the phaser (30) and the reverb (15) each have a Mix to go
to; the Plane has seven shapings and a turn and no Mix, so its start has to
be one of them, chosen here by measuring rather than by taste alone.

Three candidates, each a player would hear and see at once:

  twist   Twist at 15 (54 degrees at full scale): the loud parts swirl and the
          quiet middle stays still, and the knob it moves is on the module's line.
  clip    Radial clip at a radius of 0.30: a stereo-linked soft clipper, the
          figure rounded towards a circle; its knobs are under the arrow.
  turn    Turn at 7 (25 degrees): the figure and the pair turned whole, exact
          and linear, so it changes balance and image and no harmonic.

Each is put over two Settled presets and two Breathing ones with the Plane
off (Tines at the radius has it on, so its switch puts nothing on), and the
third Settled one with it off too, since the rule is about every Settled
preset. Rendered offline by the core (core/tests/tools/honesty_cpp.cpp, the
instrument itself, the key at a stated sample), and measured three ways:

- the heading, as web/tests/honestytest.py measures it, at five key landings
  across half a second, since where the key lands moves the reading
  (web/README.md, 13 Nov): a candidate that takes any Settled probe out of
  Settled on any landing is out;
- heard: the distance between the candidate's spectrum and the preset's own,
  on honestytest's forty-eight bands, held and settled (the last three
  seconds), each channel; and the change in level, in dB, each channel;
- seen: how far the figure moved, the RMS of the difference between the two
  pairs as points, over the RMS of the preset's own, at the lag that best
  lines them up (the bending ones are 31 samples late at 2x).

Writes results.json beside this file and, with --wav DIR, a WAV of each
preset alone and under each candidate, 22.05 kHz 16-bit, 3.5 s held and 1.5 s
after, all at one gain so their loudness compares. The WAVs are not
committed; the owner publishes them.

    python3 web/docs/listening/plane-start/render.py [--wav DIR]
"""
import base64, json, math, os, re, subprocess, sys, wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CORE = os.path.join(ROOT, "core")
EXE = os.path.join(CORE, "build", "listening", "honesty_cpp")
VERSION = 11
RATE = 44100
HOLD, AFTER = 10.0, 4.5

CANDIDATES = {
    "twist": {"planeTwist": 15},
    "clip": {"planeLimit": 1, "planeRadius": 30},
    "turn": {"rotate": 7},
}
WHY = {
    "twist": "Twist 15: the loud parts swirl and the quiet middle stays still; heard as a stereo-linked bend, "
             "and the knob it moves is on the module's line.",
    "clip": "Radial clip at 0.30: a soft clipper that keeps the stereo image, the figure rounded towards a circle; "
            "its knobs are under the arrow, so the line shows nothing moved.",
    "turn": "Turn 25 degrees: the figure turned whole, exact and linear; heard only as balance and image, "
            "never as a harmonic.",
}
# The presets, and each one's probe as honestytest.py gives it.
PRESETS = [
    ("Settled", "Tine piano", [[60]], True),
    ("Settled", "Drawbar organ", [[60]], True),
    ("Settled", "Bass under the tine piano", [[36], [67]], False),
    ("Breathing", "Slow pad", [[60]], True),
    ("Breathing", "Turning fifths", [[48, 55]], True),
]
LANDINGS = [0.9 + 0.11 * k for k in range(5)]


def build():
    os.makedirs(os.path.dirname(EXE), exist_ok=True)
    subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(CORE, "include"),
                    os.path.join(CORE, "tests", "tools", "honesty_cpp.cpp"), "-o", EXE], check=True)


def bank():
    text = open(os.path.join(CORE, "include", "scope", "presets.h")).read()
    lib = json.loads("".join(re.findall(r'R"preset\((.*?)\)preset"', text, re.S)))
    return {e[0]: e[1] for sec in lib for e in sec[1]}


def code(setup):
    return base64.b64encode(json.dumps(dict(setup, v=VERSION)).encode()).decode()


def run(setup, notes, pre, hold, after, heard=None):
    args = [EXE, code(setup), str(RATE), ",".join(map(str, notes)), "%.4f" % pre, str(hold), str(after)]
    if heard: args.append(heard)
    out = subprocess.run(args, check=True, capture_output=True, text=True).stdout
    reads = []
    for line in out.splitlines():
        w = line.split()
        if w and w[0] == "read": reads.append({"t": float(w[1]), "phase": w[2], "move": float(w[3]), "rms": float(w[4])})
    pair = None
    if heard:
        pair = np.fromfile(heard, dtype=np.float32).reshape(-1, 2).astype(np.float64)
    return reads, pair


def mean(xs): return sum(xs) / len(xs) if xs else 0.0


def summary(out):
    """honestytest.py's summary, to the letter."""
    held = [s for s in out if s["phase"] == "held"]
    after = [s for s in out if s["phase"] == "after" and s["t"] >= HOLD + 2.5]
    return {"early": mean([s["move"] for s in held if 0.3 <= s["t"] < 2.0]),
            "late": mean([s["move"] for s in held if s["t"] >= HOLD - 3.0]),
            "most": max([s["move"] for s in held if s["t"] >= 0.5] or [0.0]),
            "afterRms": mean([s["rms"] for s in after])}


RULES = {
    "Still": lambda m: m["most"] < 0.005,
    "Settled": lambda m: m["early"] >= 0.008 and m["late"] <= 0.015 and m["late"] <= m["early"] / 2,
    "Breathing": lambda m: m["late"] >= 0.02 and m["afterRms"] < 0.005,
}


def bands(x):
    """honestytest's spectrum: Hann over n - 1, 48 fifth-octave bands from 40 Hz, amplitude shares."""
    n = len(x)
    w = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / (n - 1))
    p = np.abs(np.fft.rfft(x * w)) ** 2
    out = np.zeros(48)
    for k in range(1, n // 2):
        f = k * 44100 / n
        if f < 40: continue
        out[min(47, int(math.floor(math.log2(f / 40) * 5)))] += p[k]
    t = out.sum()
    return np.sqrt(out / t) if t > 0 else out


def heard_and_seen(dry, wet):
    """Over the held and settled stretch (the last three seconds held)."""
    a, b = int((HOLD - 3) * RATE), int(HOLD * RATE)
    d, w = dry[a:b], wet[a:b]
    spec = []
    for ch in (0, 1):
        dists = []
        for at in range(0, len(d) - 4096, RATE // 4):
            dists.append(float(np.linalg.norm(bands(w[at:at + 4096, ch]) - bands(d[at:at + 4096, ch]))))
        spec.append(mean(dists))
    level = [20 * math.log10(max(1e-12, np.sqrt(np.mean(w[:, ch] ** 2))) / max(1e-12, np.sqrt(np.mean(d[:, ch] ** 2))))
             for ch in (0, 1)]
    ref = np.sqrt(np.mean(np.sum(d ** 2, axis=1)))
    best = None
    for lag in range(0, 65):
        diff = w[lag:] - d[:len(d) - lag]
        r = np.sqrt(np.mean(np.sum(diff ** 2, axis=1))) / ref
        if best is None or r < best[0]: best = (r, lag)
    return {"spectrumL": spec[0], "spectrumR": spec[1], "levelDbL": level[0], "levelDbR": level[1],
            "figure": float(best[0]), "lag": best[1]}


def write_wav(path, pair, gain):
    # 44.1 to 22.05 kHz: a windowed sinc at 10 kHz, 255 taps, then every other sample.
    n = np.arange(-127, 128)
    h = 2 * 10000 / RATE * np.sinc(2 * 10000 / RATE * n) * np.blackman(255)
    out = np.stack([np.convolve(pair[:, ch], h, mode="same")[::2] for ch in (0, 1)], axis=1) * gain
    pcm = np.clip(np.round(out * 32767), -32768, 32767).astype("<i2")
    with wave.open(path, "wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(RATE // 2)
        f.writeframes(pcm.tobytes())


def main():
    wav_dir = sys.argv[sys.argv.index("--wav") + 1] if "--wav" in sys.argv else None
    build()
    presets = bank()
    tmp = os.path.join(os.path.dirname(EXE), "heard.f32")
    results = {"candidates": {k: {"fields": v, "why": WHY[k]} for k, v in CANDIDATES.items()}, "presets": []}
    for heading, name, probes, listened in PRESETS:
        base = presets[name]
        assert not any(k.startswith("plane") and k not in ("planeOS",) for k in base) and "rotate" not in base, name
        entry = {"heading": heading, "name": name, "probes": []}
        for notes in probes:
            probe = {"notes": notes, "runs": {}}
            for cand in [None] + list(CANDIDATES):
                setup = dict(base, **(CANDIDATES[cand] if cand else {}))
                ms = [summary(run(setup, notes, pre, HOLD, AFTER)[0]) for pre in LANDINGS]
                verdicts = [[h for h, rule in RULES.items() if rule(m)] for m in ms]
                probe["runs"][cand or "off"] = {
                    "early": [round(m["early"], 4) for m in ms], "late": [round(m["late"], 4) for m in ms],
                    "verdicts": verdicts,
                    "keeps": all(v == [heading] for v in verdicts)}
            # Heard and seen, at the first landing, the whole pair kept.
            _, dry = run(base, notes, LANDINGS[0], HOLD, AFTER, tmp)
            for cand in CANDIDATES:
                _, wet = run(dict(base, **CANDIDATES[cand]), notes, LANDINGS[0], HOLD, AFTER, tmp)
                probe["runs"][cand].update({k: round(v, 4) if isinstance(v, float) else v
                                            for k, v in heard_and_seen(dry, wet).items()})
            entry["probes"].append(probe)
            print(heading, name, notes, json.dumps({k: {kk: vv for kk, vv in r.items() if kk not in ("verdicts",)}
                                                    for k, r in probe["runs"].items()}))
        results["presets"].append(entry)
    # The choice: every Settled probe kept on every landing, and then the plainest heard and seen.
    def score(cand):
        runs = [p["runs"][cand] for e in results["presets"] for p in e["probes"]]
        return {"keepsEveryHeading": all(r["keeps"] for r in runs),
                "keepsSettled": all(p["runs"][cand]["keeps"] for e in results["presets"] if e["heading"] == "Settled"
                                    for p in e["probes"]),
                "heard": round(mean([(r["spectrumL"] + r["spectrumR"]) / 2 for r in runs]), 4),
                "levelDb": round(mean([abs(r["levelDbL"]) + abs(r["levelDbR"]) for r in runs]) / 2, 2),
                "seen": round(mean([r["figure"] for r in runs]), 4)}
    results["scores"] = {c: score(c) for c in CANDIDATES}
    results["offKeeps"] = all(p["runs"]["off"]["keeps"] for e in results["presets"] for p in e["probes"])
    with open(os.path.join(HERE, "results.json"), "w") as f: json.dump(results, f, indent=1)
    print(json.dumps(results["scores"], indent=1), "off keeps:", results["offKeeps"])
    if wav_dir:
        os.makedirs(wav_dir, exist_ok=True)
        pairs = {}
        for heading, name, probes, listened in PRESETS:
            if not listened: continue
            for cand in [None] + list(CANDIDATES):
                setup = dict(presets[name], **(CANDIDATES[cand] if cand else {}))
                _, pair = run(setup, probes[0], LANDINGS[0], 3.5, 1.5, tmp)
                pairs[(name, cand or "off")] = pair
        peak = max(float(np.max(np.abs(p))) for p in pairs.values())
        gain = min(1.0, 0.95 / peak) if peak > 0 else 1.0
        for (name, cand), pair in pairs.items():
            write_wav(os.path.join(wav_dir, "%s-%s.wav" % (name.lower().replace(" ", "-"), cand)), pair, gain)
        print("wrote %d WAVs to %s at gain %.3f" % (len(pairs), wav_dir, gain))


if __name__ == "__main__":
    main()
