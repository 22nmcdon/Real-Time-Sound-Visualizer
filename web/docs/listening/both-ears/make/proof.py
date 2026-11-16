"""Way 1 leaves the picture and Scan alone, to the bit: each build against the core on the same performance.
Compared: the drawn lanes (all six, every sample), the shown grid at every reading, and every reading
the loop is made of (Scan's table, the picture's sources and reads, the loop's depths, the stages,
the meters and their verdicts) - and, apart, the heard pair and the limiter. With its nulls: the patch
with every switch off is the core, heard pair included; Way 2 must fail the drawn comparison, and Way 1
must differ in the heard pair (so the comparison can see a difference where there is one)."""
import json, sys, hashlib
import numpy as np
import rend, bank
PICTURE = ("table", "sources", "reads", "loop", "scan", "stage", "lmeter", "eye", "meter", "gridstat", "layers")
TINE = bank.BANK["Tine piano"]
PHRASES = {"owner": (rend.HT, rend.OWNER, rend.END), "chord": (TINE, rend.CHORD, rend.CHORD_END)}
def same(a, b): return open(a, "rb").read() == open(b, "rb").read()
def picture_lines(out):
    return [l for l in out.splitlines() if l.split()[:1] and l.split()[0] in PICTURE + ("at",)]
res = {}
for ph, (fields, ev, end) in PHRASES.items():
    ref = rend.render("render_cpp", fields, ev, end, "proof-%s-core" % ph)
    refpic = picture_lines(ref["out"])
    lim_ref = [float(r[1][0]) for r in rend.readings(ref["out"])["limiter"]]
    for exe in ("r-null", "r-w1a", "r-w1b", "r-w1c", "r-w2"):
        r = rend.render(exe, fields, ev, end, "proof-%s-%s" % (ph, exe))
        lim = [float(x[1][0]) for x in rend.readings(r["out"])["limiter"]]
        pic = picture_lines(r["out"])
        firstdiff = next((i for i, (a, b) in enumerate(zip(refpic, pic)) if a != b), None)
        d = {"lanes": same(ref["base"] + ".lanes", r["base"] + ".lanes"),
             "grid": same(ref["base"] + ".grid", r["base"] + ".grid"),
             "readings": refpic == pic, "n_readings": len(pic), "first_diff": None if firstdiff is None else pic[firstdiff][:80],
             "heard": same(ref["base"] + ".heard", r["base"] + ".heard"),
             "heard_maxdiff": float(max(np.abs(ref["L"] - r["L"]).max(), np.abs(ref["R"] - r["R"]).max())),
             "limiter_same": lim == lim_ref, "limiter_max_gap_db": float(np.max(np.abs(np.array(lim) - np.array(lim_ref)))),
             "limiter_min": min(lim), "limiter_min_ref": min(lim_ref),
             "grid_bytes": len(open(r["base"] + ".grid", "rb").read()), "lane_samples": len(r["X"]),
             "grid_sha": hashlib.sha1(open(r["base"] + ".grid", "rb").read()).hexdigest()[:12]}
        res["%s/%s" % (ph, exe)] = d
        print(ph, exe, json.dumps(d), flush=True)
# The verdicts, as checks with their nulls.
ok = True
def check(name, cond):
    global ok
    ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name)
for ph in PHRASES:
    n = res[ph + "/r-null"]
    check(ph + ": the patch with every switch off is the core, heard pair and all", n["lanes"] and n["grid"] and n["readings"] and n["heard"])
    for w in ("r-w1a", "r-w1b", "r-w1c"):
        d = res[ph + "/" + w]
        check(ph + ": " + w + " draws the same lanes, grid and readings to the bit", d["lanes"] and d["grid"] and d["readings"])
        check(ph + ": null - " + w + "'s heard pair is not the core's", not d["heard"])
    check(ph + ": null - Way 2's drawn lanes are not the core's", not res[ph + "/r-w2"]["lanes"])
json.dump(res, open("proof.json", "w"), indent=1)
print("ALL PASS" if ok else "SOME FAILED")
