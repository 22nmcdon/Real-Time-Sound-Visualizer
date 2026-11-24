"""The sound audit's analysis: each control's effect, the groups they fall into, the gaps.

Reads results.json (render.py) and writes analysis.json, which the page reads.

The space. Every render is a point in the features render.py measures, each
scaled by its spread over every render made (no smaller than a difference an ear
would notice, JND below, so a feature that hardly moves is not blown up into a
dimension). Loudness is left out of the space, since nearly every control changes
it on the way to doing something else, and it is reported beside it.

A control's effect from a base is its path through that space: its places in
order, from where the base has it (its rest). Its direction is the mean of where
the places land less the rest; its reach the farthest one. A control that goes
both ways from its rest (an EQ gain, Warp, Twist) is two effects, its + and its -;
a menu whose options are different things (the filter's type, the Plane's
Mirror, the rack's order) is an effect an option. An effect is active from a base
where its reach is at least one unit.

Similarity is the cosine between two effects' directions from the same base,
averaged over the bases where both are active. Groups are average-linkage
clusters of 1 - similarity, cut at 0.8.

With --followup (the follow-up, follow.py), the same with two features more in the
space - Stair, the step error locked to the note's cycle, and Chord, what a held
chord has off both notes' harmonics - read from followup.json for the same renders,
and written to analysis-followup.json. The smooth Scan prototypes are left out of it:
the owner heard no benefit from them.
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "results.json")))
FOLLOW = "--followup" in sys.argv
SPACE = ["bright", "noise", "flat", "alias", "shimmer", "inharm", "under", "bloom", "attack", "sustain", "tail", "width", "move", "wobble", "evenodd", "artic"]
JND = {"bright": 0.1, "noise": 3, "flat": 3, "alias": 3, "shimmer": 3, "inharm": 3, "under": 3, "bloom": 0.1, "attack": 0.15, "sustain": 2, "tail": 2, "width": 2,
       "move": 0.005, "wobble": 0.5, "evenodd": 2, "artic": 2}
NAMES = {k: n for k, n, _ in R["features"]}
if FOLLOW:
    F = json.load(open(os.path.join(HERE, "followup.json")))
    for i, r in enumerate(R["renders"]):
        if str(i) in F["first"]: r["f"].update(F["first"][str(i)])
    R["renders"] = [r for r in R["renders"] if r["kind"] != "smooth"]
    SPACE += ["stair", "chord"]
    JND.update({"stair": 3, "chord": 3})
    NAMES.update({"stair": "Stair (locked steps)", "chord": "Chord grit"})
CATEGORICAL = {"vcfType", "planeMirror", "planeLimit", "fxOrder", "pictureResponds", "oscRatio", "screenDraws", "display",
               "just", "delayPingPong", "pictureSwell", "planeSnap", "persistence"}
CONTROL = {c[0]: c for c in R["controls"]}
# The shape menu, measured as points from the sine (render.py's SHAPES): an effect an option.
CONTROL["shape"] = ["shape", "Generator", "Shape", [], "sine", {}, False]
BASES = list(R["bases"])

renders = R["renders"]
allv = np.array([[r["f"][k] for k in SPACE] for r in renders])
SCALE = np.maximum(allv.std(axis=0), [JND[k] for k in SPACE])
def vec(r): return np.array([r["f"][k] for k in SPACE]) / SCALE

# ---------------------------------------------------------------- effects

def label_of(cid, opt=None, sign=None):
    name = CONTROL[cid][2]
    if opt is not None: return "%s: %s" % (name, opt)
    if sign: return "%s %s" % (name, sign)
    return name

OPTION_NAMES = {
    "vcfType": {1: "Low pass", 2: "Band pass", 3: "High pass", 4: "Notch"},
    "planeMirror": {1: "1", 2: "2", 3: "3"}, "planeLimit": {1: "radial", 2: "square"}, "planeSnap": {5: "5", 6: "6"},
    "oscRatio": {0.5: "1:2", 1: "1:1", 1.25: "5:4", 4 / 3: "4:3", 1.5: "3:2", 5 / 3: "5:3", 2: "2:1", 2.5: "5:2", 3.5: "7:2", 7: "7:1"},
    "persistence": {"0": "Off", "0.3": "Short", "0.12": "Medium", "0.04": "Long", "-1": "Infinite"},
    "just": {False: "equal"}, "delayPingPong": {True: "on"}, "pictureSwell": {True: "on"},
    "display": {"yt": "Y-T"}, "screenDraws": {"paint": "Paint"}, "pictureResponds": {"level": "level", "both": "both"},
}

effects = {}   # key -> {"id","label","group","base":{b: {...}}}
def add(key, cid, label, b, rest, pts):
    e = effects.setdefault(key, {"key": key, "id": cid, "label": label, "group": CONTROL[cid][1], "base": {}})
    d = np.mean([p - rest for _, p in pts], axis=0)
    far = max(pts, key=lambda vp: np.linalg.norm(vp[1] - rest))
    e["base"][b] = {"dir": d, "reach": float(np.linalg.norm(far[1] - rest)), "far": far[1] - rest, "farValue": far[0],
                    "path": [v for v, _ in pts]}

by = {}
for i, r in enumerate(renders):
    if r["kind"] == "sweep": by.setdefault((r["base"], r["control"]), []).append(i)
base_sine = next(r for r in renders if r["kind"] == "base" and r["base"] == "sine")
for r in renders:
    if r["kind"] == "shape" and r["value"] != "sine":
        add("shape=" + r["value"], "shape", "Shape: " + r["value"], "sine", vec(base_sine), [(r["value"], vec(r))])
for (b, cid), idx in by.items():
    c = CONTROL[cid]; places, rest, two = c[3], None, c[6]
    rr = [renders[i] for i in idx]
    restv = rr[0]["rest"]
    restr = [r for r in rr if r["value"] == restv]
    if not restr: continue
    rvec = vec(restr[0])
    order = {json.dumps(v): k for k, v in enumerate(places)}
    pts = sorted([(r["value"], vec(r)) for r in rr if r["value"] != restv], key=lambda vp: order.get(json.dumps(vp[0]), 99))
    if not pts: continue
    if cid in CATEGORICAL:
        for v, p in pts:
            add("%s=%s" % (cid, json.dumps(v)), cid, label_of(cid, OPTION_NAMES.get(cid, {}).get(v, v)), b, rvec, [(v, p)])
    elif two:
        up = [(v, p) for v, p in pts if v > restv]; dn = [(v, p) for v, p in pts if v < restv]
        if up: add(cid + "+", cid, label_of(cid, sign="+"), b, rvec, up)
        if dn: add(cid + "-", cid, label_of(cid, sign="-"), b, rvec, dn)
    else:
        # a knob whose base rests mid-range (a pluck's Decay, a pad's Attack): up and down as two
        up = [(v, p) for v, p in pts if not isinstance(v, (str, bool)) and v > restv]
        dn = [(v, p) for v, p in pts if not isinstance(v, (str, bool)) and v < restv]
        if up and dn and isinstance(restv, (int, float)):
            add(cid + "+", cid, label_of(cid, sign="up"), b, rvec, up)
            add(cid + "-", cid, label_of(cid, sign="down"), b, rvec, dn)
        else:
            add(cid, cid, label_of(cid), b, rvec, pts)

# Each base's floor: what the null (the key a moment later, no control at all) reaches
# from it, doubled, and never under one unit. A loop-heavy base is chaotic - where in
# its state a note lands changes how it goes on - so an effect from it has to clear
# that before its direction means anything.
NULL = {b: effects["_land"]["base"][b]["reach"] if "_land" in effects and b in effects["_land"]["base"] else 0 for b in BASES}
FLOOR = {b: max(1.0, 2 * NULL[b]) for b in BASES}
def active(e, b): return b in e["base"] and e["id"] != "_land" and e["base"][b]["reach"] >= FLOOR[b]
def unit(v):
    n = np.linalg.norm(v); return v / n if n > 0 else v

def sim(a, b):
    cs = [float(unit(a["base"][x]["dir"]) @ unit(b["base"][x]["dir"])) for x in BASES if active(a, x) and active(b, x)]
    return (float(np.mean(cs)), len(cs)) if cs else (None, 0)

live = [e for e in effects.values() if any(active(e, b) for b in BASES)]
dead = [e for e in effects.values() if e["id"] != "_land" and not any(active(e, b) for b in BASES)]
live.sort(key=lambda e: (e["group"], e["label"]))
n = len(live)
S = np.full((n, n), np.nan); SH = np.zeros((n, n), int)
for i in range(n):
    for j in range(n):
        S[i, j], SH[i, j] = sim(live[i], live[j])

# ---------------------------------------------------------------- groups

def cluster(cut=0.8):
    groups = [[i] for i in range(n)]
    def link(a, b):
        v = [S[i, j] for i in a for j in b if not np.isnan(S[i, j])]
        return np.mean(v) if len(v) == len(a) * len(b) else -1  # every pair must share a base
    while True:
        best, bi, bj = -2, -1, -1
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                s = link(groups[i], groups[j])
                if s > best: best, bi, bj = s, i, j
        if best < cut: break
        groups[bi] = groups[bi] + groups[bj]; del groups[bj]
    return groups

groups = cluster(0.8)
def within(g):
    v = [S[i, j] for i in g for j in g if i < j]
    return float(np.mean(v)) if v else 1.0

def where(e):
    """In words, where an effect goes: its three largest moves, averaged over the bases it acts from."""
    acts = [b for b in BASES if active(e, b)]
    d = np.mean([e["base"][b]["dir"] for b in acts], axis=0)
    top = np.argsort(-np.abs(d))[:3]
    return [(SPACE[k], round(float(d[k]), 2)) for k in top if abs(d[k]) >= 0.3]

def mean_dir(e):
    acts = [b for b in BASES if active(e, b)]
    return np.mean([unit(e["base"][b]["dir"]) for b in acts], axis=0)

out_groups = []
for g in sorted(groups, key=lambda g: -len(g)):
    if len(g) < 2: continue
    cen = unit(np.mean([mean_dir(live[i]) for i in g], axis=0))
    out_groups.append({"members": [live[i]["key"] for i in g], "labels": [live[i]["label"] for i in g],
                       "groupsOf": sorted(set(live[i]["group"] for i in g)), "within": round(within(g), 3),
                       "where": [(SPACE[k], round(float(cen[k]), 2)) for k in np.argsort(-np.abs(cen))[:4] if abs(cen[k]) >= 0.2]})

# Pairs across sections: near-duplicates that live in different places on the face.
pairs = []
for i in range(n):
    for j in range(i + 1, n):
        if np.isnan(S[i, j]) or S[i, j] < 0.85 or live[i]["id"] == live[j]["id"]: continue
        a, b = live[i], live[j]
        shared = [x for x in BASES if active(a, x) and active(b, x)]
        ra = np.mean([a["base"][x]["reach"] for x in shared]); rb = np.mean([b["base"][x]["reach"] for x in shared])
        # what the cosine misses: the harmonic pattern, and the features they part on most
        pairs.append({"a": a["key"], "b": b["key"], "la": a["label"], "lb": b["label"], "ga": a["group"], "gb": b["group"],
                      "sim": round(float(S[i, j]), 3), "bases": shared, "reachA": round(float(ra), 2), "reachB": round(float(rb), 2)})
pairs.sort(key=lambda p: -p["sim"])

# ---------------------------------------------------------------- the hypothesis

def find(key): return next((e for e in live if e["key"] == key), None)
HYP = ["shpDrive", "shpFold", "shpBits", "shpRate", "planeSnap=5", "planeSnap=6", "oscScan", "pictureAmount", "pictureSwell=true"]
if FOLLOW: HYP += ["planeMirror=1", "planeMirror=3", "planeLimit=1", "planeLimit=2", "planeRadius-", "oscBend+"]
hyp = [k for k in HYP if find(k)]
hyp_matrix = [[None if np.isnan(S[live.index(find(a)), live.index(find(b))]) else round(float(S[live.index(find(a)), live.index(find(b))]), 2)
               for b in hyp] for a in hyp]

def per_base(e):
    return {b: {"reach": round(e["base"][b]["reach"], 2), "active": active(e, b),
                "far": {SPACE[k]: round(float(e["base"][b]["far"][k] * SCALE[k]), 3) for k in range(len(SPACE))},
                "farValue": e["base"][b]["farValue"]} for b in e["base"]}

# Which effects take brightness away (by at least a fifth of an octave at their far end, from any base)
darken = []
for e in live:
    got = [(b, e["base"][b]["far"][0] * SCALE[0]) for b in e["base"] if active(e, b)]
    worst = min(got, key=lambda x: x[1]) if got else None
    if worst and worst[1] <= -0.2: darken.append({"key": e["key"], "label": e["label"], "group": e["group"], "base": worst[0], "octaves": round(float(worst[1]), 2)})
darken.sort(key=lambda d: d["octaves"])

# ---------------------------------------------------------------- the gaps

# Each direction is the features that define it, nothing else: a control from a base already
# at the floor of grit cannot take grit away, so "inharmonic and clean" asked of it scores the
# cleanliness it could not have. Cleanliness is reported instead - what the best control does
# to grit on the way - and the reading is judged on the page.
DIRECTIONS = [
    ("darker", {"bright": -1}),
    ("brighter", {"bright": 1}),
    ("grit: stepped and aliased (the bitcrusher's)", {"alias": 1}),
    ("noisier: breath and air", {"noise": 1}),
    ("inharmonic: a bell, a gong", {"inharm": 1}),
    ("an octave under", {"under": 1}),
    ("shimmer: sidebands round each partial", {"shimmer": 1}),
    ("a bloom: bright on the strike, darker after", {"bloom": 1}),
    ("percussive: dying away while held", {"sustain": -1}),
    ("articulate: each note standing out", {"artic": 1}),
    ("a slower onset", {"attack": 1}),
    ("wider", {"width": 1}),
    ("moving while held", {"move": 1}),
    ("a tail after the key", {"tail": 1}),
    ("fuller: even harmonics", {"evenodd": 1}),
    ("hollow: odd harmonics", {"evenodd": -1}),
    ("rough: tremolo, beating", {"wobble": 1}),
]
GRIT = SPACE.index("alias")
gaps = []
for name, want in DIRECTIONS:
    u = unit(np.array([want.get(k, 0) for k in SPACE], float))
    best = []
    for e in live:
        for b in BASES:
            if not active(e, b): continue
            far = e["base"][b]["far"]
            along = float(far @ u)
            if along <= 0: continue
            best.append((float(unit(far) @ u), along, e["key"], e["label"], b, float(far[GRIT] * SCALE[GRIT]), float(np.linalg.norm(far))))
    # the controls that go furthest that way, among those for which it is a main part of what they do
    best.sort(key=lambda x: -(x[1] if x[0] >= 0.5 else x[1] / 10))
    seen, top = set(), []
    for c, along, key, label, b, grit, size in best:
        if key in seen: continue
        seen.add(key); top.append({"key": key, "label": label, "base": b, "cos": round(c, 2), "along": round(along, 2), "grit": round(grit, 1)})
        if len(top) == 5: break
    gaps.append({"name": name, "want": want, "best": top})

# ---------------------------------------------------------------- smooth Scan

crusher = [find(k) for k in ("shpBits", "shpRate") if find(k)]
smooth = {}
for variant in ([] if FOLLOW else ["core"] + sorted(set(r["variant"] for r in renders if r["kind"] == "smooth"))):
    smooth[variant] = {}
    for b in BASES:
        if variant == "core":
            rr = [r for r in renders if r["kind"] == "sweep" and r["base"] == b and r["control"] == "oscScan"]
        else:
            rr = [r for r in renders if r["kind"] == "smooth" and r["variant"] == variant and r["base"] == b]
        rest = next(r for r in rr if r["value"] == 0)
        pts = sorted([r for r in rr if r["value"] != 0], key=lambda r: r["value"])
        d = np.mean([vec(r) - vec(rest) for r in pts], axis=0)
        cr = [unit(c["base"][b]["dir"]) for c in crusher if active(c, b)]
        cdir = unit(np.mean(cr, axis=0)) if cr else None
        far = pts[-1]
        smooth[variant][b] = {"cosToCrusher": None if cdir is None else round(float(unit(d) @ cdir), 2),
                              "reach": round(float(np.linalg.norm(vec(far) - vec(rest))), 2),
                              "at100": {k: round(far["f"][k], 2) for k in SPACE + ["loud"]},
                              "at0": {k: round(rest["f"][k], 2) for k in SPACE + ["loud"]},
                              "path": [{k: round(r["f"][k], 2) for k in ("bright", "alias", "flat", "move", "inharm")} | {"value": r["value"]} for r in [rest] + pts]}

# ---------------------------------------------------------------- the maps

# The sound space, two dimensions: PCA of every render's scaled features.
X = np.array([vec(r) for r in renders]); mu = X.mean(axis=0)
U, s, Vt = np.linalg.svd(X - mu, full_matrices=False)
P = (X - mu) @ Vt[:2].T
explained = (s[:2] ** 2 / (s ** 2).sum()).round(3).tolist()
loadings = [{SPACE[k]: round(float(Vt[i, k]), 2) for k in range(len(SPACE))} for i in range(2)]

# The effect map: each effect's mean direction, PCA to two dimensions.
D = np.array([mean_dir(e) for e in live])
U2, s2, Vt2 = np.linalg.svd(D - D.mean(axis=0), full_matrices=False)
Q = (D - D.mean(axis=0)) @ Vt2[:2].T
explained2 = (s2[:2] ** 2 / (s2 ** 2).sum()).round(3).tolist()
loadings2 = [{SPACE[k]: round(float(Vt2[i, k]), 2) for k in range(len(SPACE))} for i in range(2)]
gid = {}
for gi, g in enumerate(out_groups):
    for k in g["members"]: gid[k] = gi

out = {
    "null": {b: round(NULL[b], 2) for b in BASES}, "floor": {b: round(FLOOR[b], 2) for b in BASES},
    "space": SPACE, "names": NAMES, "scale": {k: round(float(SCALE[i]), 4) for i, k in enumerate(SPACE)},
    "renders": [{"i": i, "kind": r["kind"], "base": r.get("base"), "control": r.get("control"), "value": r.get("value"),
                 "rest": r.get("rest"), "variant": r.get("variant"), "name": r.get("name"), "section": r.get("section"),
                 "x": round(float(P[i, 0]), 3), "y": round(float(P[i, 1]), 3),
                 "f": {k: round(r["f"][k], 3) for k in SPACE + ["loud"]}} for i, r in enumerate(renders)],
    "pca": {"explained": explained, "loadings": loadings},
    "effects": [{"key": e["key"], "id": e["id"], "label": e["label"], "group": e["group"], "where": where(e),
                 "x": round(float(Q[i, 0]), 3), "y": round(float(Q[i, 1]), 3), "cluster": gid.get(e["key"]),
                 "bases": per_base(e)} for i, e in enumerate(live)],
    "effectPca": {"explained": explained2, "loadings": loadings2},
    "dead": [{"key": e["key"], "label": e["label"], "group": e["group"],
              "reach": {b: round(e["base"][b]["reach"], 2) for b in e["base"]}} for e in dead],
    "groups": out_groups, "pairs": pairs, "hypothesis": {"keys": hyp, "labels": [find(k)["label"] for k in hyp], "matrix": hyp_matrix},
    "darken": darken, "gaps": gaps, "smooth": smooth,
    "sim": {"keys": [e["key"] for e in live], "matrix": [[None if np.isnan(v) else round(float(v), 2) for v in row] for row in S]},
}
json.dump(out, open(os.path.join(HERE, "analysis-followup.json" if FOLLOW else "analysis.json"), "w"))
print("null reach", {b: round(NULL[b], 2) for b in BASES})
print("effects %d live, %d dead; %d groups of two or more; %d cross-section pairs >= 0.85" % (len(live), len(dead), len(out_groups), len(pairs)))
for g in out_groups: print(" %.2f  %s   -> %s" % (g["within"], " | ".join(g["labels"]), g["where"]))
print("dead:", ", ".join(e["label"] for e in dead))
print("hypothesis:", hyp)
for k, row in zip(hyp, hyp_matrix): print("  %-18s %s" % (k, row))
print("darken:", [(d["label"], d["octaves"]) for d in darken])
for g in gaps: print(" gap %-38s %s" % (g["name"][:38], [(t["label"], t["base"], t["cos"], t["along"], t["grit"]) for t in g["best"][:4]]))
for v, bs in smooth.items(): print(" smooth %-7s %s" % (v, {b: (x["cosToCrusher"], x["reach"], x["at100"]["alias"], x["at100"]["bright"]) for b, x in bs.items()}))
