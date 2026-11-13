"""The loop's total, boredom and the photocell reaching the sound, on the core:
looptest.py's rows from :92 to :276.

These were looptest.py's on `?brain=js` until stage 5, step 3, batch 3 (13
Nov): the page's picture sources held at a value by hand
(`MOD_SOURCES.get(id).value = () => 1`), the page's `applyModMatrix` and
`compileRoutes` read back, the page's generator heard through its worklet,
and boredom read off the page's own picture over eleven real seconds. Here
the core's: matrix_cpp's scripted sources held at a value, marked as the
picture's and given the core's own reaches (`reach=photo`, `reach=bored`:
kPhotoReach and kBoredReach, not numbers written here), the route the matrix
hands the generator played by generator_cpp, and boredom read off
picture_cpp's picture sources fed a figure frame by frame - stuck, and then
moving. Each check has its null beside it.

The stability runs (looptest :523 on: seven seeds, the reverb in the loop,
Scan's table moving, the crossed pair, the holds) followed in batch 5, once
render_cpp could play them: there they were thirty real seconds a seed on
`?brain=js` (the Scan seeds on `?brain=js&core=js`, the only page that handed
its tables out), read every tenth of a second of wall time, and the flakiest
rows in the suite. Here each seed is the instrument rendered offline for
thirty seconds of audio and read every tenth of a second of it, so a run is
the same every time (pieces/render.py proves it). The bounds are the page's,
unmoved. And the meter's rule that a picture under ten decibels of limiting
is running away (:310), which needs no render: picture_cpp's meter.
"""
import base64, json, math

import numpy as np

RATE = 44100
TRAILER = 17


def matrix(kit, lines):
    """matrix_cpp on one run: each frame's visual offsets, and the routes it
    hands the generator (`lroutes`, after each frame, with the loop's flag)."""
    out = kit.run("matrix_cpp", "run\n" + "\n".join(l for x in lines for l in ([x, "lroutes"] if x == "frame" else [x])) + "\nend")
    frames = []
    for l in out.split("\n"):
        if l.startswith("frame"):
            visual = {w.split()[1]: float(w.split()[2]) for w in l.split(" | ")[0].split(" :: ")[1:] if w.startswith("visual")}
        elif l.startswith("lroutes"):
            routes = l.split("| routes ")[1].split(" amounts")[0].strip()
            frames.append((visual, [] if routes == "-" else [r.split("/") for r in routes.split("+")]))
    return frames


def sources(ids, level, reach="photo", flag="picture"):
    return [l for i in ids for l in ("source %s %s reach=%s" % (i, flag, reach), "value %s %r" % (i, level))]


def play(kit, routes, seconds=0.8):
    """A sine at 220 with the matrix's routes held as it hands them (`u` is
    a held route, -1 in the generator's form, and the loop's flag the
    generator's 2); the left lane's last 16384 samples."""
    form = []
    for index, held, held_b, slot, amount, amount_b, unipolar, loop in routes:
        flags = (1 if unipolar == "1" else 0) | (2 if loop == "1" else 0)
        form.append("%s/%s/%s/%s/%s/%s/%d" % ("-1" if index == "u" else index, held, held_b, slot, amount, amount_b, flags))
    samples = int(RATE * seconds) // 128 * 128
    ev = ["at 0 set shape sine", "at 0 set freq 220", "at 0 set interval 0", "at 0 set amp 0.5",
          "at 0 routes " + ("+".join(form) if form else "none")]
    text = "run rate=%r slots=40 seed=3 samples=%d\n%s\nend" % (float(RATE), samples, "\n".join(ev))
    body = np.array(kit.floats("generator_cpp", text)[:-TRAILER])
    return body[0::6][-16384:]


def bin_at(x, f):
    i = np.arange(len(x))
    w = 0.5 - 0.5 * np.cos(2 * np.pi * i / (len(x) - 1))
    return abs(np.sum(x * w * np.exp(-2j * np.pi * f * i / RATE))) / len(x)


rms = lambda x: float(np.sqrt(np.mean(np.asarray(x) ** 2)))


def run(kit):
    check, null = kit.check, kit.null
    LOOP = ["photo.1", "picture.round", "picture.cover"]

    # --- one total per destination ---
    # The view's rotation as a stand-in destination of screen.h's span and
    # range (one, -2 to 2), resting at nought.
    f = matrix(kit, sources(LOOP, 1) + ["visual view.rotate 1 -2 2 0"] + ["route %s view.rotate 0.5" % i for i in LOOP]
               + ["frame", "source test.one reach=1", "value test.one 1", "route test.one view.rotate 0.3", "frame"])
    loop_only, with_other = f[0][0]["view.rotate"], f[1][0]["view.rotate"]
    check("three picture sources at full move a destination by the loop's total, not three times it",
          abs(loop_only - 0.5) < 1e-9, "%.3f" % loop_only)
    plain = matrix(kit, sources(["test.a", "test.b", "test.c"], 1, "1", "") + ["visual view.rotate 1 -2 2 0"]
                   + ["route %s view.rotate 0.5" % i for i in ("test.a", "test.b", "test.c")] + ["frame"])[0][0]["view.rotate"]
    null("three sources that are not the picture's are three times it", not (abs(plain - 0.5) < 1e-9), "%.3f" % plain)
    check("and a source that is not the loop is not caught in the loop's bound", abs(with_other - 0.8) < 1e-9, "%.3f" % with_other)
    null("without it, the loop's total alone", with_other != loop_only)

    # The generator: what the matrix hands it, and what it plays.
    g = matrix(kit, sources(LOOP, 1) + ["route %s gen.freq 0.5" % i for i in LOOP] + ["frame"])[0][1]
    o = matrix(kit, sources(["test.a", "test.b", "test.c"], 1, "1", "") + ["route %s gen.freq 0.5" % i
                                                                           for i in ("test.a", "test.b", "test.c")] + ["frame"])[0][1]
    check("the loop's routes into a generator parameter cross into the generator as one, the loop's",
          len(g) == 1 and g[0][0] == "u" and g[0][7] == "1", str(g))
    null("three sources that are not the picture's are three routes, none the loop's", len(o) == 3 and all(r[7] == "0" for r in o), str(o))
    check("carrying the bounded total", len(g) == 1 and float(g[0][1]) == 0.5, str(g))
    bounded, unbounded = 220 * 2 ** 0.5, 220 * 2 ** 1.5
    x = play(kit, g)
    a, u, b0 = bin_at(x, bounded), bin_at(x, unbounded), bin_at(x, 220)
    says = lambda at, off, base: at > 0.05 and off < at * 0.01 and base < at * 0.01
    check("and the generator plays the bounded pitch, not three sources' worth", says(a, u, b0),
          "energy at 220 x 2^0.5 %.4f, at 2^1.5 %.4f, at 220 %.4f" % (a, u, b0))
    y = play(kit, [["u", "1.5", "1.5", g[0][3], "1", "1", "0", "1"]])
    null("three sources' worth would say the other", says(bin_at(y, unbounded), bin_at(y, bounded), bin_at(y, 220)))

    # Amplitude only ducks, and the combined route carries each part's law.
    amp = {}
    for level in (1, 0):
        r = matrix(kit, sources(LOOP[:2], level) + ["route %s gen.amp 0.5" % i for i in LOOP[:2]] + ["frame"])[0][1]
        amp[level] = (r, rms(play(kit, r)))
    check("two on amplitude at full ask for no duck, through the combined route",
          len(amp[1][0]) == 1 and abs(float(amp[1][0][0][1])) < 1e-9, str(amp[1][0]))
    check("and at nought they duck, by no more than the loop's total",
          len(amp[0][0]) == 1 and 0.2 < float(amp[0][0][0][1]) <= 0.5 + 1e-9, str(amp[0][0]))
    check("and the generator is quieter at nought than at full", amp[0][1] < amp[1][1] * 0.9 and amp[1][1] > 0.05,
          "%.4f against %.4f" % (amp[0][1], amp[1][1]))
    null("a total that forgot the law would duck at full", float(amp[1][0][0][1]) != float(amp[0][0][0][1]))

    # --- boredom ---
    # picture_cpp's picture sources, fed a fifth's figure each frame on a
    # screen persisting at 0.12: held still (a just fifth, its phase fixed)
    # for ten seconds, then drifting (an equal fifth's phase walking) for
    # five. The page's run did the same with the generator drawing.
    def lissajous(phase, n=600):
        t = np.linspace(0, 2 * np.pi, n)
        return ";".join("%r,%r" % (32 + 22 * math.sin(3 * s + phase), 32 + 22 * math.sin(2 * s)) for s in t)
    lines = ["run", "plot 0 0 64 64", "persist 0.12", "pair ellipse 0.5 0.3 4 1024 0.4"]
    still = lissajous(0.3)
    for k in range(600):
        lines += ["fade 0", "poly %s" % still, "step 16.67"]
    for k in range(300):
        lines += ["fade 0", "poly %s" % lissajous(0.3 + 0.02 * (k + 1)), "step 16.67"]
    lines.append("end")
    steps = [l.split() for l in kit.run("picture_cpp", "\n".join(lines)).strip().split("\n") if l.startswith("step")]
    bored = [float(w[w.index("values") + 6]) for w in steps]
    raw = [float(w[w.index("raw") + 6]) for w in steps]
    t = [(k + 1) * 16.67 / 1000 for k in range(len(steps))]
    at = lambda series, s: series[min(range(len(t)), key=lambda k: abs(t[k] - s))]
    print("    stuck: %.2f after 2 s, %.2f after 5 s, %.2f after 10 s; moving again: %.2f after 5 s"
          % (at(bored, 2), at(bored, 5), at(bored, 10), at(bored, 15)))
    check("boredom rises while the picture is stuck", at(bored, 10) > 0.7, "%.3f" % at(bored, 10))
    null("before the meter has its history it is nought", at(bored, 0.5) == 0, "%.3f" % at(bored, 0.5))
    # The steepest the raw level climbs over any quarter second, as the page read it.
    q = 15
    steepest = max((raw[k + q] - raw[k]) / (t[k + q] - t[k]) for k in range(0, 600 - q))
    check("no faster than a quarter a second - it cannot slam", steepest <= 0.25 * 1.15, "%.3f a second at the steepest" % steepest)
    null("and it does climb", steepest > 0.05, "%.3f" % steepest)
    check("and never past one", max(bored) <= 1, "%.3f" % max(bored))
    check("and it drains when the picture moves again", at(bored, 15) < 0.45, "%.2f after 5 s" % at(bored, 15))
    null("before it moved it was high", at(bored, 10) > 0.45)

    # Its reach, through the matrix: picture.bored at a value routed at full.
    rb = matrix(kit, sources(["picture.bored"], 0.8, "bored") + ["visual view.rotate 1 -2 2 0", "route picture.bored view.rotate 1", "frame"])
    rp = matrix(kit, sources(["photo.1"], 0.8, "photo") + ["visual view.rotate 1 -2 2 0", "route photo.1 view.rotate 1", "frame"])
    applied, photo = rb[0][0]["view.rotate"] / 0.8, rp[0][0]["view.rotate"] / 0.8
    check("routed at full it moves a destination by its own reach, lower than the photocell's",
          abs(applied - 0.3) < 1e-6 and photo > applied, "%.4f, the photocell's %.4f" % (applied, photo))
    null("the photocell's is not boredom's", abs(photo - 0.3) > 1e-6)

    # --- the loop reaches the sound ---
    # The photocell held at 0.6, routed to pitch at a half: the route the
    # matrix hands the generator, and the pitch it plays.
    r = matrix(kit, sources(["photo.1"], 0.6) + ["route photo.1 gen.freq 0.5", "frame"])[0][1]
    x = play(kit, r)
    want = 220 * 2 ** 0.3
    w, b0 = bin_at(x, want), bin_at(x, 220)
    check("the photocell moves the pitch you hear", w > 0.03 and b0 < w * 0.05, "energy at 220 x 2^0.3 %.4f, at 220 %.4f" % (w, b0))
    z = play(kit, [])
    null("unrouted, it is 220", bin_at(z, 220) > 0.03 and bin_at(z, want) < bin_at(z, 220) * 0.05)


    stability(kit)


# --- the stability runs (looptest :523 on), batch 5 ---

SECONDS = 30
# Everything the picture has, at the most it is allowed, onto the destinations
# that can do the most - two of them onto resonance at once, so the total is
# what holds it: looptest's plan.
PLAN = [("photo.1", "filter.res"), ("picture.bored", "filter.res"), ("picture.cover", "gen.freq"), ("picture.round", "view.lag"),
        ("picture.novelty", "view.rotate"), ("picture.change", "filter.cutoff"), ("picture.signed", "view.zoom")]
SEEDS = [("silence", None), ("full scale", None), ("full scale, with Scan at its top", None),
         ("full scale, Scan at its top, every note striking at full", "strike"),
         ("full scale, a split at Scan's top, each layer reading the other's picture", "cross"),
         ("full scale, the phaser at its top with its resonance at its most", "phaser"),
         ("full scale, the reverb at full Mix, Spread and Size", "reverb")]


def code(setup):
    return base64.b64encode(json.dumps(setup).encode()).decode().rstrip("=")


def script(seed, mode, scan, seconds=SECONDS, plan=PLAN, amount=100, extra=None):
    """The page's RUN as the instrument hears it: the old opening (the
    defaults and a timebase, X-Y, the photocell on) under a note held in Mono,
    then the run's setup - the Harmonic tone's fifth tempered at 220, the
    filter on and resonant at 80, the lag on but crossed, every routing at
    full and the Picture at 100 - as one setup, which is what the page's
    controls hand the instrument one by one; the note struck at full. The
    hammer is a note every ninety milliseconds round the twelve places, each
    let go sixty after; silence brings the Level up to 30 at two seconds."""
    s = {"v": 11, "timebase": 3, "display": "xy", "photoOn": True, "midiMode": "mono", "shape": "harmonic", "interval": 7,
         "just": False, "freq": 220, "amp": 0 if seed == "silence" else 100, "persistence": "0.04", "fOn": True, "fRes": 80,
         "lagOn": mode != "cross", "mod": ";".join("%s>%s@1.000" % r for r in plan), "pictureAmount": amount}
    if scan: s["oscScan"] = 100
    if mode == "strike": s["scanStrike"] = 100
    if mode == "phaser": s.update(phaserMix=100, phaserDepth=100, phaserFeedback=75, phaserRate=300)
    if mode == "reverb": s.update(reverbMix=100, reverbSpread=100, reverbSize=100)
    if mode == "cross": s.update(midiMode="poly", layers="split", bScan=100, scanReadsA="B", scanReadsB="A")
    s.update(extra or {})
    lines = [["make", 48000, code(s)]] + [["midi", 0x90, n, 127] for n in ([48, 55, 79, 84] if mode == "cross" else [57])]
    lines.append(["every", 0.1, "heard", "stage", "meter", "loop", "scan", "table", "gridstat", "settings", "sources"])
    if seed == "silence": lines += [["to", 2.0], ["slider", "amp", "30"]]
    if mode == "strike":
        events, t, k = [], 0.0, 0
        while t < seconds:
            n = 60 + (k * 7) % 12
            events += [(t, [0x90, n, 127]), (t + 0.06, [0x80, n, 0])]
            k += 1; t += 0.09
        for when, m in sorted(events, key=lambda e: e[0]):
            if when < seconds: lines += [["to", when], ["midi"] + m]
    lines.append(["to", seconds])
    return lines


def measure(kit, lines, slots, split=False):
    """A run's readings, reduced as the page reduced its tenths."""
    rows = kit.render(lines)
    w = {"post": 0.0, "res": 0.0, "rot": 0.0, "zoom": 0.0, "total": 0.0, "grid": 0.0, "nan": False}
    moved = {k: [math.inf, -math.inf] for k in ("res", "rot", "freq", "fold")}
    verdicts, least, motion, motionB, scan_hold, layer_hold, live = {}, 1.0, [], [], 1.0, 1.0, 0
    last = {"A": None, "B": None}
    for r in rows:
        heard = [float(x) for x in r["heard"]]
        w["post"] = max(w["post"], heard[0], heard[1])
        if heard[3] > 0: w["nan"] = True
        loop = r["loop"]
        i = loop.index("visual")
        routes = {int(a): float(b) for a, b, _ in (x.split(":") for x in loop[:i])}
        res, rot, zoom = (float(x) for x in loop[i + 1:i + 4])
        w["res"], w["rot"], w["zoom"] = max(w["res"], abs(res)), max(w["rot"], abs(rot)), max(w["zoom"], abs(zoom))
        w["total"] = max([w["total"]] + [abs(v) for v in routes.values()])
        grid = [float(x) for x in r["gridstat"]]
        w["grid"] = max(w["grid"], grid[0])
        values = [res, rot, zoom] + list(routes.values()) + [float(x) for x in r["sources"]] + grid[:2]
        if grid[2] > 0 or not all(math.isfinite(v) for v in values): w["nan"] = True
        f, fold = routes.get(slots["freq"], 0.0), routes.get(slots["fold"], 0.0)
        for k, v in (("res", res), ("rot", rot), ("freq", f), ("fold", fold)):
            moved[k] = [min(moved[k][0], v), max(moved[k][1], v)]
        m = r["meter"]
        verdict = " ".join(m[1:3]) if m[1] == "running" else m[1]
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
        st = [float(x) for x in r["stage"]]
        least = min(least, st[4])
        sc = r["scan"]
        # Scan's hold each layer last sent: B's only counts where B reads, the split.
        scan_hold = min(scan_hold, float(sc[1]), float(sc[2]) if split else 1)
        if st[0] == 1:
            live += 1
            layer_hold = min(layer_hold, st[10], st[16])
        for layer, out in (("A", motion), ("B", motionB)):
            table = r.get("table" + layer)
            if table and last[layer]: out.append(float(np.mean(np.abs(np.array(table) - np.array(last[layer])))))
            last[layer] = table
    end = [float(x) for x in rows[-1]["settings"]]
    return {"worst": w, "moved": moved, "verdicts": verdicts, "leastHold": least, "motion": motion, "motionB": motionB,
            "leastScanHold": scan_hold, "leastLayerHold": layer_hold, "liveReads": live, "reads": len(rows),
            "reverbHeld": {"mix": end[0], "size": end[1], "spread": end[2]}}


# Each row's judgement, as looptest's, so a null can be put through the same one.
def inside(w):
    return w["res"] <= 0.5 * 50 + 1e-6 and w["rot"] <= 0.5 + 1e-9 and w["zoom"] <= 0.5 * 8 + 1e-9 and w["total"] <= 0.5 + 1e-9


def held_right(run):
    running, least = run["verdicts"].get("running away", 0), run["leastHold"]
    return (least == 0.25 if running > 30 else least == 1 if running == 0 else 1 - 0.5 * running / 10 - 0.1 <= least < 1)


def running_loop(run, mode):
    w, mv = run["worst"], run["moved"]
    running, tenths = run["verdicts"].get("running away", 0), sum(run["verdicts"].values())
    saturated = mode in ("strike", "reverb", "cross") and w["grid"] >= 1 - 1e-9 and tenths > 0 and running >= 0.9 * tenths
    pinned = lambda r: saturated and r[0] >= 0.5 - 1e-9
    ok = ((mv["res"][1] - mv["res"][0]) > 1 and ((mv["freq"][1] - mv["freq"][0]) > 0.01 or pinned(mv["freq"]))
          and ((mv["fold"][1] - mv["fold"][0]) > 0.05 or pinned(mv["fold"]) or (saturated and mv["fold"][1] < 0.05)))
    # Whether it passed only by the exemption, which the page's runs leaned on (after-stage-5.md).
    plain = (mv["res"][1] - mv["res"][0]) > 1 and (mv["freq"][1] - mv["freq"][0]) > 0.01 and (mv["fold"][1] - mv["fold"][0]) > 0.05
    return ok, plain


def median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else 0


def stability(kit):
    check, null = kit.check, kit.null
    slots = kit.slots()

    print("\n    running away, as the limiter sees it (looptest :310)")
    # picture_cpp's meter fed a sparse fixed picture for ten seconds under ten
    # decibels of limiting, and the same unlimited: the page's makePictureMeter
    # fixture, line for line. (The instrument itself hands its meter no
    # limiting - it has no limiter; the face's monitor chain has - so in the
    # instrument only a screen lit past saturation runs away.)
    fixture = "sparse 300 7"
    strained = kit.run("picture_cpp", "run\nmnew\nmlimit -10\n" + "\n".join("mupd %r %s" % (1 / 60, fixture) for _ in range(600)) + "\nend")
    calm = kit.run("picture_cpp", "run\nmnew\n" + "\n".join("mupd %r %s" % (1 / 60, fixture) for _ in range(600)) + "\nend")
    last = lambda out: [l for l in out.split("\n") if l.startswith("step") or " meter " in l][-1].split()[-1]
    check("a picture held under ten decibels of limiting is running away, and the same picture unlimited is not",
          last(strained) == "running_away" and last(calm) != "running_away", "%s, %s" % (last(strained), last(calm)))
    gentle = kit.run("picture_cpp", "run\nmnew\nmlimit -2\n" + "\n".join("mupd %r %s" % (1 / 60, fixture) for _ in range(600)) + "\nend")
    null("two decibels of limiting is not running away", last(gentle) != "running_away", last(gentle))

    print("\n    the stability runs, %d s from each seed, read every tenth of a second" % SECONDS)
    runs = {}
    for seed, mode in SEEDS:
        scan = 100 if "Scan" in seed else 0
        run = measure(kit, script("silence" if seed == "silence" else "full", mode, scan), slots, split=mode == "cross")
        runs[seed] = (run, mode)
        w, mv = run["worst"], run["moved"]
        print("    from %s: heard peak %.3f; resonance offset up to %.1f, rotation %.3f, zoom %.2f, generator total %.3f; grid %.2f; verdicts %s"
              % (seed, w["post"], w["res"], w["rot"], w["zoom"], w["total"], w["grid"], run["verdicts"]))
        print("      it moved: resonance %.1f to %.1f, rotation %.3f to %.3f, pitch total %.3f to %.3f, fold total %.3f to %.3f; held to %.3f"
              % (mv["res"][0], mv["res"][1], mv["rot"][0], mv["rot"][1], mv["freq"][0], mv["freq"][1], mv["fold"][0], mv["fold"][1],
                 run["leastHold"]))
        check("from %s, nothing goes NaN or infinite" % seed, not w["nan"] and run["reads"] == SECONDS * 10, str(run["reads"]))
        # What reaches the speakers passing full scale was the page's monitor
        # chain's to hold - its limiter and clamp, which on the site are the
        # face's (syncMonitor) and stay: looptest holds them on the default
        # page. The instrument has no limiter; its heard peak is reported.
        check("from %s, and the instrument was heard" % seed, w["post"] > 0.1, "peak %.4f" % w["post"])
        check("from %s, every destination stays inside the loop's total" % seed, inside(w), str(w))
        check("from %s, and the grid stays inside the phosphor's range" % seed, w["grid"] <= 1, str(w["grid"]))
        check("from %s, running away holds the stage's push down, to a quarter at most, and nothing else holds it" % seed,
              held_right(run), "%d tenths running away, the hold down to %.3f" % (run["verdicts"].get("running away", 0), run["leastHold"]))
        ok, plain = running_loop(run, mode)
        check("from %s, and the loop was really running - it moved what it drives, the stage's fold too" % seed, ok,
              "resonance range %.2f, pitch total %r to %r, fold total %r to %r%s" % (
                  mv["res"][1] - mv["res"][0], mv["freq"][0], mv["freq"][1], mv["fold"][0], mv["fold"][1],
                  "" if plain else ", by the saturated exemption"))
        if mode == "reverb":
            rv = run["reverbHeld"]
            check("and the reverb really was in the loop: the generator held Mix, Spread and Size at full to the end",
                  rv["mix"] == 1 and rv["spread"] == 1 and rv["size"] == 1, str(rv))
        if scan:
            mo = run["motion"]
            check("with Scan at its top (%s), its wave was still moving: the table changed by a median of over 0.02 a tenth of a second" % seed,
                  len(mo) > 0.8 * SECONDS * 10 - 10 and median(mo) > 0.02, "median %.3f over %d reads" % (median(mo), len(mo)))
            if mode == "cross":
                check("crossed, the run really had two pictures: the layers drew a figure each throughout",
                      run["liveReads"] > 0.8 * SECONDS * 10 - 10, "%d of the reads" % run["liveReads"])
                check("and B's wave was moving as well as A's", median(run["motionB"]) > 0.02, "median %.3f" % median(run["motionB"]))
                check("and both depths were held by the lower of the two pictures' holds, never less",
                      abs(run["leastScanHold"] - run["leastLayerHold"]) < 0.02,
                      "Scan's holds down to %.3f, the pictures' to %.3f" % (run["leastScanHold"], run["leastLayerHold"]))
            else:
                check("and Scan's depth was held by the stage's own hold, never less (%s)" % seed,
                      abs(run["leastScanHold"] - run["leastHold"]) < 0.02,
                      "Scan's hold down to %.3f, the stage's to %.3f" % (run["leastScanHold"], run["leastHold"]))

    # Not the page's: added in batch 5, when a mutation that put saturation at
    # 0.95 lit left every check above green - a meter that never ran away held
    # nothing, which "nothing else holds it" allows. Struck at full every
    # ninety milliseconds the screen is full throughout (the grid at one), and
    # a full screen is the meter's own case of running away: once the meter
    # has its history, nine tenths of what it says must be that.
    strike = runs["full scale, Scan at its top, every note striking at full"][0]
    said = lambda run: sum(n for v, n in run["verdicts"].items() if v != "listening")
    check("and a screen kept full by the hammer is called running away for nine tenths of what the meter says",
          strike["worst"]["grid"] >= 1 - 1e-9 and strike["verdicts"].get("running away", 0) >= 0.9 * said(strike) > 0,
          "%d of %d" % (strike["verdicts"].get("running away", 0), said(strike)))

    # --- the nulls, each a run or a reading the check above must call wrong ---
    full, silence = runs["full scale"][0], runs["silence"][0]
    nan = dict(full, worst=dict(full["worst"], nan=True))
    null("a reading that went NaN is caught", nan["worst"]["nan"])
    # Silence with its Level never brought up (the slider at two seconds taken out).
    quiet = measure(kit, [l for l in script("silence", None, 0, seconds=6) if l[0] != "slider"], slots)
    null("a run never brought up is not heard", not (quiet["worst"]["post"] > 0.1), "peak %.4f" % quiet["worst"]["post"])
    # An oscillator at full on the rotation beside the loop: no longer inside the loop's total.
    lfo = measure(kit, script("full", None, 0, seconds=6, extra={"mod": ";".join("%s>%s@1.000" % r for r in PLAN) + ";lfo1>view.rotate@1.000"}), slots)
    null("an oscillator at full on the rotation beside the loop breaks the loop's total", not inside(lfo["worst"]), "rotation %.3f" % lfo["worst"]["rot"])
    null("a grid past one is caught", not (1.0001 <= 1))
    null("the full-scale run's verdicts with silence's hold are held wrong", not held_right(dict(full, leastHold=silence["leastHold"])))
    null("and silence's with full scale's", not held_right(dict(silence, leastHold=full["leastHold"])))
    dead = measure(kit, script("full", None, 0, seconds=10, plan=[], amount=0), slots)
    null("a loop with nothing routed and no Picture is not running", not running_loop(dead, None)[0], str(dead["moved"]))
    null("the reverb was not held in the plain run", not (full["reverbHeld"]["mix"] == 1 and full["reverbHeld"]["spread"] == 1))
    # Not a still screen: with nothing routed and no Picture, Scan at its top
    # on a plain sine still moved its table by 0.11 a tenth, since Scan
    # reading a screen its own wave draws is a loop by itself. The page's null
    # for this was the screen held still by Stop (scantest), which is step
    # 5's to decide. Scan at a depth of one in a hundred reads the same
    # screen and its table all but holds still.
    still = measure(kit, script("full", None, 100, seconds=10, plan=[], amount=0, extra={"oscScan": 1}), slots)
    null("Scan at a depth of one hardly moves its table, which the same reading calls still", not (median(still["motion"]) > 0.02),
         "median %.4f" % median(still["motion"]))
    null("the plain full-scale run, whose screen does not stay full, is not", not (full["verdicts"].get("running away", 0) >= 0.9 * said(full)),
         "%d of %d" % (full["verdicts"].get("running away", 0), said(full)))
    null("an unsplit run has no two pictures", not (strike["liveReads"] > 0.8 * SECONDS * 10 - 10), str(strike["liveReads"]))
    null("and no B wave", not (median(strike["motionB"]) > 0.02))
    null("Scan's hold read against the silence's stage is not the stage's", not (abs(strike["leastScanHold"] - silence["leastHold"]) < 0.02))
