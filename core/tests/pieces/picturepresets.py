"""The presets where the picture plays itself, played on the core: their
stored reticles read, their picture sources move, each loop changes what the
picture does against itself without the loop, none runs away, and the
wandering one wanders because of its loop - picturepresettest.py's run rows
(:241 to :256).

These ran on `?brain=js` until stage 5, step 3, batch 5 (13 Nov): each
preset loaded on the page with `restore`, held under A3 for ten real seconds,
and the page's own photocell (`photo.raw`, `landPhoto`, `movePhoto`), its
picture sources' values and its picture meter read every 150 ms of wall time
- twice for the first section, the second time with its picture routings
taken out, which the instrument would never have heard. Here render_cpp: the
corpus setup loaded as a code of its own version (7, so the decode passes run
as `loadCorpus` runs them), the Picture held at nought as `?picture=0` held
it, the sustain at full, Mono and the note as `held_tone(57, true)` gives
them, the Frequency put back; the setup without its loop is a setup whose
`mod` has only the other routings; and every reading is the instrument's -
the photocell's raw reading at its stored cell, each routed source's value
(`routed`), the meter's verdict - at 150 ms of audio. The reticle's landing
is the page's `landPhoto` rule, here on the instrument's grid (the page's ran
on its own), and the cell it finds is sent as the face sends a dragged
reticle (`photoReticle`).

The old library is core/tests/scenarios/library-p8f.json, read by
pieces/perform.py's `library`.
"""
import base64, json, math, os, re

import numpy as np

from pieces.kit import BUILD
from pieces.perform import library

SECTIONS = ["The picture plays itself", "Played with the picture"]
WANDERER = "The organ registers itself"
PICTURE = re.compile(r"^(photo\.|picture\.)")
SECONDS = 10
N = 64  # kPhosphorN


def code(setup):
    return base64.b64encode(json.dumps(setup).encode()).decode().rstrip("=")


def phosphor_read(grid, u, v):
    """Phosphor::read: five bilinear reads, the centre and a cross three
    quarters of a cell out."""
    def at(x, y):
        fx, fy = x * N - 0.5, y * N - 0.5
        x0, y0 = math.floor(fx), math.floor(fy)
        tx, ty = fx - x0, fy - y0
        cell = lambda cx, cy: 0.0 if cx < 0 or cy < 0 or cx >= N or cy >= N else float(grid[cy * N + cx])
        return (cell(x0, y0) * (1 - tx) * (1 - ty) + cell(x0 + 1, y0) * tx * (1 - ty)
                + cell(x0, y0 + 1) * (1 - tx) * ty + cell(x0 + 1, y0 + 1) * tx * ty)
    d = 0.75 / N
    return (at(u, v) + at(u - d, v) + at(u + d, v) + at(u, v - d) + at(u, v + d)) / 5


def land(grid, u, v):
    """The page's landPhoto: a cell under a quarter of the brightest is moved
    to the brightest of the nine around the nearest cell at half of it. None
    if it stays."""
    most = float(np.max(grid))
    if not most > 0 or phosphor_read(grid, u, v) >= most / 4: return None
    near, nearest = -1, math.inf
    for i in np.nonzero(grid >= most / 2)[0]:
        d = ((i % N + 0.5) / N - u) ** 2 + ((i // N + 0.5) / N - v) ** 2
        if d < nearest: nearest, near = d, int(i)
    if near < 0: return None
    best, brightest = None, -1
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cx, cy = near % N + dx, near // N + dy
            if cx < 0 or cy < 0 or cx >= N or cy >= N: continue
            uu, vv = (cx + 0.5) / N, (cy + 0.5) / N
            r = phosphor_read(grid, uu, vv)
            if r > brightest: brightest, best = r, (uu, vv)
    return best


def presets():
    for name in SECTIONS:
        section = next(s for s in library() if s[0] == name)
        for preset, setup, _ in section[1]:
            if setup.get("gen", "wave") == "wave": yield name, preset, dict(setup)


def start(setup, patch=None):
    """The preset loaded at version 7 with the Picture at nought, the sustain
    at full, Mono, A3 at full velocity and the Frequency put back."""
    freq = setup.get("freq", 220)
    return [["make", 48000, code(dict(setup, v=7)), dict({"pictureAmount": 0, "midiMode": "mono"}, **(patch or {}))],
            ["slider", "envSustain", "100"], ["midi", 0x90, 57, 127], ["slider", "freq", str(freq)]]


def run_one(kit, setup, routings=None, cell=None, landing=True, note=True):
    """One run as the page's: the photocell's raw reading after a second and
    a half, the reticle landed if its stored cell reads dark, then ten seconds
    from a cleared meter, read every 150 ms. `routings` replaces the setup's
    (the run without its loop), `cell` puts the reticle where the looped run
    landed it."""
    patch = {} if routings is None else {"mod": routings}
    lines = start(setup, patch)
    if not note: lines = [l for l in lines if l[0] != "midi"]
    if cell: lines.append(["control", "photoReticle", "%r,%r" % cell])
    lines.append(["to", 0.3])
    landed, raw = None, None
    t = 0.3
    if setup.get("photoOn") and landing:
        dump = os.path.join(BUILD, "picturepresets-grid.f32")
        probe = lines + [["record", "grid", dump], ["to", 1.8], ["read", "sources", "griddump"]]
        raw = float(kit.render(probe)[-1]["sources"][0])
        if raw < 1e-3:
            grid = np.fromfile(dump, "<f4")
            u, v = setup.get("photoU", 0.75), setup.get("photoV", 0.5)
            landed = land(grid, u, v)
        lines.append(["to", 1.8])
        t = 1.8
        if landed:
            lines += [["control", "photoReticle", "%r,%r" % landed], ["to", 2.1]]
            t = 2.1
    lines += [["reset", "meter"], ["every", 0.15, "sources", "routed", "meter"], ["to", t + SECONDS]]
    rows = kit.render(lines)
    verdicts, lo, hi, known = {}, {}, {}, {}
    photo = []
    for r in rows:
        m = r["meter"]
        v = " ".join(m[1:3]) if m[1] == "running" else m[1]
        verdicts[v] = verdicts.get(v, 0) + 1
        photo.append(float(r["sources"][1]))
        w = r["routed"]
        for i in range(0, len(w), 4):
            source = w[i].split(">")[0]
            if not PICTURE.match(source): continue
            value = float(w[i + 2])
            known[source] = w[i + 1] == "1"
            lo[source], hi[source] = min(lo.get(source, value), value), max(hi.get(source, value), value)
    m = rows[-1]["meter"]
    return {"verdicts": verdicts, "verdict": " ".join(m[1:3]) if m[1] == "running" else m[1], "raw": raw, "landed": landed,
            "compiled": bool(known) and all(known.values()), "moved": max([hi[k] - lo[k] for k in hi] + [0]),
            "swing": max(photo) - min(photo), "reads": len(rows)}


def share(v):
    v = {k: n for k, n in v.items() if k != "listening"}
    total = sum(v.values()) or 1
    return {k: n / total for k, n in v.items()}


def apart(a, b):
    a, b = share(a), share(b)
    return sum(abs(a.get(k, 0) - b.get(k, 0)) for k in set(a) | set(b)) / 2


def run(kit):
    check, null = kit.check, kit.null
    runs = []
    for section, preset, setup in presets():
        row = dict(run_one(kit, setup), preset=preset, section=section)
        if section == SECTIONS[0]:
            kept = ";".join(p for p in (setup.get("mod") or "").split(";") if p.strip() and not PICTURE.match(p.strip()))
            unlooped = run_one(kit, setup, routings=kept, cell=row["landed"], landing=False)
            row.update(open=unlooped["verdicts"], openSwing=unlooped["swing"])
        runs.append(row)
        extra = ("  unlooped %s, apart %.2f, reading %.2f against %.2f" % (row["open"], apart(row["verdicts"], row["open"]), row["swing"],
                                                                         row["openSwing"])) if "open" in row else ""
        print("    %-32s moved %.2f  ends %-12s %s%s" % (preset, row["moved"], row["verdict"], row["verdicts"], extra))
    total = sum(1 for _ in presets())
    loops_n = sum(1 for s, _, _ in presets() if s == SECTIONS[0])
    landed = [r["preset"] for r in runs if r["landed"]]
    print("    pressed onto their figures, their stored cells dark: %s" % (landed or "none"))
    check("at most two presets needed the reticle pressed onto their figure, so the stored placements are read",
          len(landed) <= 2 and len(runs) == total and total >= 10, "%d of %d: %s" % (len(landed), len(runs), landed))
    # Null: the same reading taken before anything is drawn - no note, so every
    # stored cell is dark and every preset would be pressed.
    dark = [p for _, p, s in list(presets())[:4] if s.get("photoOn") and run_one(kit, s, note=False)["raw"] < 1e-3]
    null("with nothing drawn every stored cell reads dark", len(dark) > 2, str(dark))

    dead = [(r["preset"], round(r["moved"], 3)) for r in runs if not (r["compiled"] and r["moved"] >= 0.05)]
    check("in every one, the picture's sources are there, move, and are routed onto what they alter", dead == [], str(dead))
    first = next(presets())
    still = run_one(kit, first[2], note=False, landing=False)
    null("with no note the same sources do not move", not (still["compiled"] and still["moved"] >= 0.05), "%.4f" % still["moved"])

    loops = [r for r in runs if "open" in r]
    def same_as(r, verdicts, swing):
        return apart(r["verdicts"], verdicts) < 0.25 and r["swing"] - swing < 0.2
    same = [(r["preset"], round(apart(r["verdicts"], r["open"]), 2), r["swing"], r["openSwing"]) for r in loops
            if same_as(r, r["open"], r["openSwing"])]
    check("and each loop changes what the picture does, against itself without the loop: the verdicts or the reading",
          same == [] and len(loops) == loops_n and loops_n >= 8, str(same))
    null("each loop against itself with its loop is the same", all(same_as(r, r["verdicts"], r["swing"]) for r in loops))

    away = [r["preset"] for r in runs if r["verdict"] == "running away"]
    check("and none of them ends running away", away == [], str(away))
    from pieces import loop
    runaway = kit.render(loop.script("full", "strike", 100, seconds=6))[-1]["meter"]
    null("the loop's struck run, which does, is caught by the same reading", " ".join(runaway[1:3]) == "running away", " ".join(runaway[1:3]))

    wander = next((r for r in runs if r["preset"] == WANDERER), {})
    def wanders(heard, unheard):
        heard = {k: v for k, v in heard.items() if k != "listening"}
        unheard = {k: v for k, v in unheard.items() if k != "listening"}
        return bool(heard) and max(heard, key=heard.get) == "wandering" and bool(unheard) and max(unheard, key=unheard.get) != "wandering"
    check("the wandering preset wanders because of its loop: wandering most with it, and not without it",
          wanders(wander.get("verdicts", {}), wander.get("open", {})), "%s; without: %s" % (wander.get("verdicts"), wander.get("open")))
    null("the other way round it does not", not wanders(wander.get("open", {}), wander.get("verdicts", {})))
