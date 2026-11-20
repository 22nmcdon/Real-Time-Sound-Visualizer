"""The Slow pad against Breathing's floor (20 Nov), and two re-voicings for the owner's ear.

web/tests/honestytest.py judges every preset offline with the key at 0.9, 1.0,
1.25, 1.5 and 2.0 s after it loads, by its worst moment against its heading.
The Slow pad as shipped reads 0.019 late with the key at 1.0 s, under
Breathing's 0.02, so it fails its heading on one landing of five. Two
candidates, each one field, a touch more of what already makes it breathe:

  swell   Swell on: the push breathes at the Persistence's period while the
          chord is held (the Bass under the pad, its neighbour, has it on).
  scan    Scan 60 to 75: more of its wave read back off its own figure, the
          loop it already turns over by.

Each is judged exactly as honestytest judges the bank (its own functions,
imported), and the limiter's chord with it. Writes results.json beside this
file and, with --audio, audio/slow-pad-NAME.mp3 for each, C4 held 10 s and
4.5 s after, the key at 0.9 s, all at one gain so their loudness compares,
64 kbps as the other pages' (ffmpeg); they are committed for the owner.

    python3 web/docs/listening/slow-pad/render.py [--audio]
"""
import json, os, subprocess, sys, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.join(HERE, "..", "..", "..", "tests")
CANDIDATES = [("shipped", "As shipped", {}), ("swell", "Swell on", {"pictureSwell": True}), ("scan", "Scan 75", {"oscScan": 75})]

# honestytest's own measure and rules, without its browser run.
src = open(os.path.join(TESTS, "honestytest.py")).read()
h = {"__file__": os.path.abspath(os.path.join(TESTS, "honestytest.py")), "__name__": "slowpad"}
exec(src[:src.index("with sync_playwright() as pw:")], h)
INSTRUMENT = os.path.join(h["BUILD"], "instrument_cpp")
subprocess.run(["g++", "-std=c++17", "-O2", "-I", os.path.join(h["CORE"], "include"),
                os.path.join(h["CORE"], "tests", "tools", "instrument_cpp.cpp"), "-o", INSTRUMENT], check=True)
CODE = subprocess.run([INSTRUMENT, "--code", "Slow pad"], check=True, capture_output=True, text=True).stdout.strip()

def over(patch):
    """honestytest's render with the candidate's fields laid over the code, as a host's state is."""
    real = h["render"]
    def render(lines, record=None):
        if lines and lines[0][0] == "make" and patch: lines = [lines[0] + [patch]] + lines[1:]
        return real(lines, record)
    return render

results = {}
for key, label, patch in CANDIDATES:
    h["render"], real = over(patch), h["render"]
    try:
        ms, verdicts = h["judged"](CODE, [60])
        limit = h["limiter_on_chord"](CODE, [48, 55, 60, 64])
    finally: h["render"] = real
    results[key] = {"label": label, "patch": patch, "moments": list(h["MOMENTS"]),
                    "early": [round(m["early"], 4) for m in ms], "late": [round(m["late"], 4) for m in ms],
                    "afterRms": round(max(m["afterRms"] for m in ms), 5), "limiter": round(limit, 2),
                    "headings": [k for k, v in verdicts.items() if v]}
    print("%-10s early %s  late %s  %s" % (label, results[key]["early"], results[key]["late"], results[key]["headings"] or "none"))
with open(os.path.join(HERE, "results.json"), "w") as f: json.dump(results, f, indent=1)

if "--audio" in sys.argv:
    out = os.path.join(HERE, "audio")
    os.makedirs(out, exist_ok=True)
    takes = {}
    for key, label, patch in CANDIDATES:
        path = os.path.join(h["BUILD"], "heard-%s.f32" % key)
        script = os.path.join(h["BUILD"], "heard-%s.txt" % key)
        lines = [["make", 48000, CODE] + ([patch] if patch else []), ["record", "heard", path], ["to", 0.9], ["midi", 0x90, 60, 100],
                 ["to", 10.9], ["midi", 0x80, 60, 0], ["to", 15.4], ["record", "heard"]]
        with open(script, "w") as f: f.write("\n".join(json.dumps(l) for l in lines) + "\n")
        subprocess.run([h["RENDER"], script], check=True, capture_output=True)
        takes[key] = np.fromfile(path, dtype=np.float32).reshape(-1, 2)
    gain = 0.9 / max(float(np.abs(t).max()) for t in takes.values())
    for key, t in takes.items():
        wav = os.path.join(h["BUILD"], "slow-pad-%s.wav" % key)
        with wave.open(wav, "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
            w.writeframes((np.clip(t * gain, -1, 1) * 32767).astype("<i2").tobytes())
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-codec:a", "libmp3lame", "-b:a", "64k",
                        os.path.join(out, "slow-pad-%s.mp3" % key)], check=True)
    print("MP3s in", out)
