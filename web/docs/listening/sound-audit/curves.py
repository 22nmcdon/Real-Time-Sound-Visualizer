"""The follow-up's curves: each Plane and Shaping control's fine sweep, where it starts to act,
where it turns to stepping or to chord grit, and the stretches of its travel that do nothing.

Reads followup.json (follow.py) and analysis-followup.json (analyse.py --followup, for
the features' units and each base's floor) and writes curves.json, which the page reads.

The distance at each place is how far the sound is from where the control rests (the
base, with what the control needs switched on) in the first study's space with Stair and
Chord added, loudness left out as it was there. A place is dead when that distance is
under the base's floor: twice what the null (the key a moment later) reaches, and never
under one unit. A dead stretch is a run of travel, from the rest outwards, under the
floor; crossings between two places are found by straight lines between them.

Thresholds, each the first place outwards from the rest where it holds:
  acts      the distance reaches the floor
  steps     Stair reaches -45 dB (the validation: smooth references read -60, a sine
            on 32 levels -42)
  chord     Chord grit 15 dB over the rest's and over -35 dB (a crusher on a chord
            reads -20 to -33, a clean chord -60)

    python3 web/docs/listening/sound-audit/follow.py --curves
"""
import json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STEP_ON, CHORD_RISE, CHORD_ON = -45.0, 15.0, -35.0
DEAD_FLAG = 0.30
SHOW = ["stair", "chord", "alias", "bright", "evenodd", "loud", "jumps", "flatrun"]

def interp_cross(xs, ys, level):
    """First x (outwards) where ys reaches level, by straight lines."""
    for i in range(len(xs)):
        if ys[i] >= level:
            if i == 0: return xs[0]
            a, b = ys[i - 1], ys[i]
            return xs[i - 1] + (xs[i] - xs[i - 1]) * (level - a) / (b - a) if b != a else xs[i]
    return None

def dead_share(xs, d, floor):
    """The run of travel from the rest (xs[0]) outwards under the floor, as a share of
    the side's travel, and the total share under it anywhere."""
    span = abs(xs[-1] - xs[0])
    if span == 0: return 0.0, 0.0, None
    first = interp_cross(xs, d, floor)
    run = abs((first if first is not None else xs[-1]) - xs[0]) / span
    tot = 0.0
    for i in range(1, len(xs)):
        a, b, w = d[i - 1] < floor, d[i] < floor, abs(xs[i] - xs[i - 1])
        if a and b: tot += w
        elif a != b:
            t = (floor - d[i - 1]) / (d[i] - d[i - 1]) if d[i] != d[i - 1] else 0.5
            tot += w * (t if a else 1 - t)
    return run, tot / span, first

def main():
    F = json.load(open(os.path.join(HERE, "followup.json")))
    A = json.load(open(os.path.join(HERE, "analysis-followup.json")))
    space, scale, floor = A["space"], A["scale"], A["floor"]
    vec = lambda f: np.array([f[k] / scale[k] for k in space])
    fine = {c[0]: c for c in F["fine"]}
    rows = F["sweeps"]
    out = []
    for cid, label, places, rest, needs, kind in F["fine"]:
        if kind == "null": continue
        entry = {"id": cid, "label": label, "kind": kind, "rest": rest, "bases": {}}
        for b in floor:
            rr = [r for r in rows if r["base"] == b and r["control"] == cid]
            restr = next(r for r in rr if r["value"] == rest)
            r0 = vec(restr["f"])
            pts = [r for r in rr if r["value"] != "off" or rest == "off"]
            def dist(r): return float(np.linalg.norm(vec(r["f"]) - r0))
            if kind == "menu":
                order = {json.dumps(v): i for i, v in enumerate(places)}
                pts.sort(key=lambda r: order[json.dumps(r["value"])])
            else:
                pts = [r for r in pts if r["value"] != "off"]
                pts.sort(key=lambda r: r["value"])
            P = [{"v": r["value"], "d": round(dist(r), 3), **{k: round(r["f"][k], 2) for k in SHOW}} for r in pts]
            if rest == "off": P.insert(0, {"v": "off", "d": 0.0, **{k: round(restr["f"][k], 2) for k in SHOW}})
            fl = floor[b]
            res = {"points": P, "floor": fl, "rest": {k: round(restr["f"][k], 2) for k in SHOW}}
            # the sides: outwards from the rest
            xs = [p for p in P if p["v"] != "off"]
            if kind == "line" and rest == "off":
                # the radius: from its gentle end, 100, inwards, measured against Radial off
                sides = {"": sorted(xs, key=lambda p: -p["v"])}
            elif kind == "line" and rest == min(p["v"] for p in xs):
                sides = {"": sorted(xs, key=lambda p: p["v"])}
            elif kind in ("line", "two"):
                sides = {"+": sorted([p for p in P if p["v"] >= rest], key=lambda p: p["v"]),
                         "-": sorted([p for p in P if p["v"] <= rest], key=lambda p: -p["v"])}
            else:
                sides = {}
            res["sides"] = {}
            for s, side in sides.items():
                if len(side) < 3: continue
                xs = [p["v"] for p in side]; d = [p["d"] for p in side]
                run, tot, acts = dead_share(xs, d, fl)
                steps = interp_cross(xs, [p["stair"] for p in side], STEP_ON)
                base_chord = res["rest"]["chord"]
                ch = interp_cross(xs, [min(p["chord"] - base_chord - CHORD_RISE, p["chord"] - CHORD_ON) for p in side], 0.0)
                res["sides"][s] = {"from": xs[0], "to": xs[-1], "deadRun": round(run, 3), "deadAll": round(tot, 3),
                                   "acts": None if acts is None else round(acts, 2), "steps": None if steps is None else round(steps, 2),
                                   "chord": None if ch is None else round(ch, 2), "flag": run > DEAD_FLAG,
                                   "maxD": round(max(d), 2)}
            if kind == "menu":
                res["options"] = [{"v": p["v"], "d": p["d"], "dead": p["d"] < fl, "stair": p["stair"], "chord": p["chord"]} for p in P]
            entry["bases"][b] = res
        out.append(entry)
    flags = [(e["label"], b, s, x["deadRun"]) for e in out for b, r in e["bases"].items() for s, x in r["sides"].items() if x["flag"]]
    json.dump({"controls": out, "thresholds": {"steps": STEP_ON, "chordRise": CHORD_RISE, "chordOn": CHORD_ON, "dead": DEAD_FLAG},
               "floor": floor, "flags": flags}, open(os.path.join(HERE, "curves.json"), "w"))
    for e in out:
        for b, r in e["bases"].items():
            for s, x in r["sides"].items():
                print("%-22s %-5s %s  dead run %4.0f%% (all %4.0f%%)  acts %-7s steps %-7s chord %-7s max %.1f%s" % (
                    e["label"], b, s or " ", 100 * x["deadRun"], 100 * x["deadAll"], x["acts"], x["steps"], x["chord"], x["maxD"], "  FLAG" if x["flag"] else ""))
            if "options" in r:
                print("%-22s %-5s    %s" % (e["label"], b, "  ".join("%s:d%.1f st%.0f ch%.0f" % (o["v"], o["d"], o["stair"], o["chord"]) for o in r["options"])))

if __name__ == "__main__":
    main()
