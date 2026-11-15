"""honesty_cpp over 16 key times, summarised as honestytest.py's summary and RULES."""
import base64, json, subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(HERE, "bin", "honesty_cpp")
HOLD, AFTER = 10.0, 4.5
PRES = [0.9 + k * 0.25 / 16 for k in range(16)]   # the key at sixteen places across a quarter second
def code(setup): return base64.b64encode(json.dumps(setup, separators=(",", ":")).encode()).decode().rstrip("=")
def decode(c): return json.loads(base64.b64decode(c + "=" * (-len(c) % 4)))
def mean(xs): return sum(xs) / len(xs) if xs else 0.0
def summary(out):
    held = [s for s in out if s["phase"] == "held"]
    after = [s for s in out if s["phase"] == "after" and s["t"] >= HOLD + 2.5]
    return {"early": mean([s["move"] for s in held if 0.3 <= s["t"] < 2.0]),
            "late": mean([s["move"] for s in held if s["t"] >= HOLD - 3.0]),
            "afterRms": mean([s["rms"] for s in after])}
RULES = {"Settled": lambda m: m["early"] >= 0.008 and m["late"] <= 0.015 and m["late"] <= m["early"] / 2,
         "Breathing": lambda m: m["late"] >= 0.02 and m["afterRms"] < 0.005}
def one(c, notes, pre, rate):
    out = subprocess.run([EXE, c, str(rate), ",".join(map(str, notes)), "%.6f" % pre, str(HOLD), str(AFTER)],
                         check=True, capture_output=True, text=True).stdout
    rows = []
    for l in out.split("\n"):
        w = l.split()
        if w and w[0] == "read": rows.append({"t": float(w[1]), "phase": w[2], "move": float(w[3]), "rms": float(w[4])})
    m = summary(rows); m["v"] = {h: r(m) for h, r in RULES.items()}; return m
def sweep(setup, notes, rate=48000):
    c = code(setup)
    with ThreadPoolExecutor(8) as ex:
        return list(ex.map(lambda p: one(c, notes, p, rate), PRES))
if __name__ == "__main__":
    setup = json.loads(sys.argv[1]); notes = [int(n) for n in sys.argv[2].split(",")]
    rate = int(sys.argv[3]) if len(sys.argv) > 3 else 48000
    ms = sweep(setup, notes, rate)
    print("late %.4f..%.4f early %.4f..%.4f settled %d/16 breathing %d/16" % (
        min(m["late"] for m in ms), max(m["late"] for m in ms), min(m["early"] for m in ms), max(m["early"] for m in ms),
        sum(m["v"]["Settled"] for m in ms), sum(m["v"]["Breathing"] for m in ms)))
