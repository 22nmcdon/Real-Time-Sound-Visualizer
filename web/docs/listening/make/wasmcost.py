"""Each feature's cost in the core as WebAssembly (node, blocks of 128), against the model:
budget.py's CASES and method (as many voices a layer as the model leaves whole, both layers),
timed by a WASI build of budget_cpp."""
import json, os, subprocess, sys
sys.path.insert(0, "/home/user/Real-Time-Sound-Visualizer/core/tests/pieces")
import budget as B
HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE, WASM = os.path.join(HERE, "bin", "budget_cpp"), os.path.join(HERE, "bin", "budget.wasm")
def go(lines, wasm=False):
    p = os.path.join(HERE, "script-%d.txt" % os.getpid())
    open(p, "w").write("\n".join(lines) + "\n")
    cmd = ["node", "--no-warnings", os.path.join(HERE, "runwasm.mjs"), WASM, p] if wasm else [NATIVE, p]
    return B.Read(subprocess.run(cmd, check=True, capture_output=True, text=True).stdout)
def per_layer(cfg, k):
    b = go(["gen 44100"] + B.setall(cfg) + ["voices 0 " + B.chord(48, n=k), "voices 1 " + B.chord(48, n=k), "run 128", "budget"]).budgets[0]
    return b, not B.thinned(b)
out = {}
for name, cfg in B.CASES.items():
    per = 1
    for k in range(1, 9):
        if not per_layer(cfg, k)[1]: break
        per = k
    lines = ["gen 44100"] + B.setall(cfg) + ["voices 0 " + B.chord(48, n=per), "voices 1 " + B.chord(48, n=per), "run 4410", "budget", "time 5"]
    r = go(lines, wasm=True)
    out[name] = {"per": per, "ms": r.times[0], "units": r.budgets[0]["units"]}
ratios = {k: v["ms"] / v["units"] for k, v in out.items()}
mid = sorted(ratios.values())[len(ratios) // 2]
for k, v in out.items():
    print("%-16s %d a layer %8.2f ms model %6.1f  %.2f of the median" % (k, v["per"], v["ms"], v["units"], ratios[k] / mid))
print("unit %.3f ms" % mid)
json.dump({"cases": out, "unit": mid}, open(os.path.join(HERE, "wasmcost-%s.json" % sys.argv[1]), "w"))
