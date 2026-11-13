"""What the picture says, on the core: roundness, coverage, change, novelty,
direction and the verdict, on made-up fixtures, and the slew on the
picture's sources.

These were shapetest.py's on ?brain=js until stage 5, step 3, batch 2 (13
Nov): there the page's own makeMoments, makePictureMeter and shapeOfPair were
called on grids and paths built in the page's JavaScript (shapetest's
HELPERS). Here the same fixtures, built line for line by picture_cpp's `m`
commands, go through the core's Moments, PictureMeter and shapeOfPair
(scope/picture.h), and the slew through its PictureSources at made-up frames.
The claims are shapetest's, each with the same bound; what each used to read
is said at the check.

Every check is written as a predicate with the reading it should pass and a
known-wrong reading it must fail (the null, beside it). PIECES_SWAP=1 feeds
each main check its null's reading instead, so every one of them can be seen
red at once - the way they were seen red as they landed.
"""
import math, os

SWAP = os.environ.get("PIECES_SWAP") == "1"
N = 64                       # kPhosphorN
SLEW = 2                     # kPhotoSlew: two whole swings a second
CHANGE_FLOOR = 0.02          # kChangeFloor
NOVELTY_FLOOR = 0.2          # kNoveltyFloor


def run(kit):
    def held(name, pred, right, wrong, show=str):
        """The check on `right`, and its null: `wrong` fails the same predicate."""
        kit.check(name, bool(pred(wrong if SWAP else right)), show(right))
        kit.null(name, not pred(wrong), "against " + show(wrong))

    def picture(*commands):
        """picture_cpp on one run; each line's words after the `|`."""
        out = kit.run("picture_cpp", "run\n%s\nend\n" % "\n".join(commands))
        return [l.split(" | ", 1)[1].split() for l in out.split("\n") if " | " in l]

    def after(words, key, k=0):
        return words[words.index(key) + 1 + k]

    # --- roundness, from the path ---
    def roundness(*commands):
        return [float(after(w, "moments")) for w in picture(*commands)]
    def segs(points, levels=None):
        return "msegs " + ";".join("%r,%r,%r,%r" % (x0, y0, x1, y1) + ("" if levels is None else ",%r" % levels[i])
                                   for i, ((x0, y0), (x1, y1)) in enumerate(zip(points, points[1:])))
    box = lambda h, w=None: segs([(-(w or h), -h), (w or h, -h), (w or h, h), (-(w or h), h), (-(w or h), -h)])
    # One circle cut into six hundred segments on its left half and twelve on
    # its right, as the beam cuts it: short where it is slow, long where fast.
    cuts = [math.pi / 2 + k / 600 * math.pi for k in range(601)] + [3 * math.pi / 2 + k / 12 * math.pi for k in range(1, 13)]
    at = [(0.5 * math.cos(t), 0.5 * math.sin(t)) for t in cuts]
    seglen = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(at, at[1:])]
    circle, square, line, flat, turned, flat32, empty, uneven, per_segment, rect = roundness(
        "mring 0.5 0.5 0", box(0.4), "mring 0.7 0 0", "mring 0.6 0.3 0", "mring 0.6 0.3 0.7", "mring 0.6 0.32 0.7",
        "mempty", segs(at), segs(at, [1 / l for l in seglen]), box(0.2, 0.4))
    print("    circle %.3f, square %.3f, line %.3f, 2:1 ellipse %.3f and turned %.3f, empty %r; uneven %.3f, per segment %.3f"
          % (circle, square, line, flat, turned, empty, uneven, per_segment))
    # shapetest :147 - the same bounds, on the page's makeMoments. Null: the two the other way round.
    held("a circle is round and a line is not", lambda v: v[0] > 0.97 and v[1] < 0.05, (circle, line), (line, circle))
    # :151 - measured from the path it reads the same at any angle (from the
    # grid's cells it read 0.557 upright and 0.610 turned). Null: a slightly
    # different ellipse turned, 0.6 by 0.32, so the 1e-6 is seen to bite.
    held("a 2:1 ellipse reads the same whichever way it is turned",
         lambda v: 0.45 < v[0] < 0.65 and abs(v[1] - v[0]) < 1e-6, (flat, turned), (flat, flat32))
    # :153 - weighted by length the unevenly cut circle is still a circle. Null:
    # the same strokes weighted by segment (each drawn at one over its length),
    # which leans left and reads flatter - the fault the length weighting prevents.
    held("a circle is a circle however unevenly the beam divides it into strokes", lambda v: v > 0.97, uneven, per_segment,
         lambda v: "%.3f" % v)
    # :155 - the measure's blind spot, kept so that a change to it changes the plan's sentence. Null: a 2:1 box.
    held("its blind spot, asserted so a change to the measure changes the plan's sentence: a square is as round as a circle",
         lambda v: v > 0.97, square, rect, lambda v: "%.3f" % v)
    # :157 - nought, not 0/0. Null: NaN, which a ratio with nothing under it gives.
    held("and a dark screen is nought, not 0/0", lambda v: v == 0, empty, float("nan"))
    # :169 - a circle shrinking a hundredth of the screen at a time. Null: the
    # same series with the floor's work undone at the end, a perfect tiny
    # circle until the frame it vanished (one, then nought).
    shrink = roundness(*["mring %r %r 0" % (k / 60, k / 60) for k in range(30, -1, -1)])
    steepest = lambda xs: max(abs(b - a) for a, b in zip(xs, xs[1:]))
    print("    shrinking a circle to nothing: largest step %.3f, the last few %s" % (steepest(shrink), [round(v, 3) for v in shrink[-4:]]))
    held("fading to nothing is a slope, not a cliff", lambda xs: steepest(xs) < 0.35, shrink, shrink[:-2] + [1.0, 0.0],
         lambda xs: "%.3f" % steepest(xs))

    # --- coverage, change and novelty, on made-up grids ---
    def meter(*frames, dt=1 / 60):
        """A fresh meter fed each fixture in turn; its reading after each."""
        rows = picture("mnew", *["mupd %r %s" % (dt, f) for f in frames])[1:]
        return [dict(zip(("coverage", "lit", "change", "novelty", "drift"), map(float, w[-6:-1])), verdict=w[-1]) for w in rows]
    faded, nudged = meter("ellipse 0.6 0.4 0.49 0")[0], meter("ellipse 0.6 0.4 0.49 0 nudged")[0]
    same = meter("ellipse 0.6 0.4 1 0", "ellipse 0.6 0.4 1 0")[1]["change"]
    near = meter("ellipse 0.6 0.4 1 0", "ellipse 0.6 0.41 1 0")[1]["change"]
    far = meter("ellipse 0.6 0.4 1 0", "dot 0.9 0.1")[1]["change"]
    print("    coverage %.4f -> %.4f when every lit cell moves 0.49 -> 0.51; change: same %.3f, nudged %.3f, different %.3f"
          % (faded["coverage"], nudged["coverage"], same, near, far))
    # :189 - every lit cell of a faded figure crosses one half. Null: the same
    # two pictures as a count of cells over a half would read them, nought and
    # then every lit cell at once (the count taken from the soft sum: each lit
    # cell is 0.49, so lit x 4096 / 0.49 cells).
    cells = round(faded["lit"] * N * N / 0.49)
    held("coverage moves a little when every cell crosses one half - it is not a count over a threshold",
         lambda v: abs(v[1] - v[0]) < 0.02, (faded["coverage"], nudged["coverage"]), (0.0, min(1.0, 4 * cells / (N * N))))
    # :191 - nought and one. Null: the two the other way round.
    held("change is nought for the same picture and one for a different one",
         lambda v: v[0] == 0 and v[1] > 0.95, (same, far), (far, same))
    # :193 - small for a small difference. Null: the different picture's change.
    held("and small for a small difference", lambda v: v < 0.5, near, far, lambda v: "%.3f" % v)
    # :213 - fifteen seconds of one ellipse, then the ellipse opening up a
    # hundredth at a time. Null: the same readings as a yes-or-no against the
    # floor, which is the jump the continuous reading exists not to make.
    opened = meter(*(["ellipse 0.6 0.3 1 0"] * 900 + ["ellipse 0.6 %r 1 0" % (0.3 + k * 0.01) for k in range(21) for _ in range(15)]))
    novel = [opened[900 + 15 * k + 14]["novelty"] for k in range(21)]
    print("    an ellipse opening up a hundredth at a time: novelty %.3f -> %.3f, largest step %.3f"
          % (novel[0], novel[-1], steepest(novel)))
    held("novelty rises with how far the picture has gone from before, a step at a time",
         lambda xs: xs[-1] > xs[0] + 0.2 and steepest(xs) < 0.25, novel, [1.0 if v >= NOVELTY_FLOOR else 0.0 for v in novel],
         lambda xs: "%.3f -> %.3f, step %.3f" % (xs[0], xs[-1], steepest(xs)))

    # --- direction, the drawn pair's ---
    def direction(*pairs):
        return [float(after(w, "signed")) for w in picture(*["mpair %r 0.5 %r" % p for p in pairs])]
    ccw, cw, flat_line, offset, nudge_line = direction((-math.pi / 2, 0), (math.pi / 2, 0), (0, 0), (-math.pi / 2, 0.3), (0.1, 0))
    across = direction(*[(k / 100, 0) for k in range(-10, 11)])
    print("    one way %.3f, the other %.3f, a line %.3f; largest step across the line %.3f" % (ccw, cw, flat_line, steepest(across)))
    # :236 - on the page this wrote state.xyPair and read shapeOfPair through
    # the page's pairOfFrame; here the pair goes to the core's shapeOfPair at
    # the unit gains, as pairOfFrame hands it for the default lanes. Null: the other way round.
    held("a circle travelled one way reads one, the other way minus one", lambda v: v[0] > 0.95 and v[1] < -0.95, (ccw, cw), (cw, ccw))
    # :238 - Null: the pair a tenth of a radian off a line, which has a way round.
    held("a line has no direction", lambda v: abs(v) < 1e-6, flat_line, nudge_line)
    # :239 - Null: the readings as a sign, which is a yes-or-no across the line.
    held("and it passes through nought smoothly as the travel reverses", lambda xs: steepest(xs) < 0.1, across,
         [math.copysign(1, v) if v else 0 for v in across], lambda xs: "%.3f" % steepest(xs))
    # :241 - on the page, state.channels[0].offset written to 0.3; here the
    # offset handed to shapeOfPair as pairOfFrame hands it. Null: the other way round's reading.
    held("wherever on the screen the figure sits", lambda v: abs(v[0] - v[1]) < 1e-6, (offset, ccw), (cw, ccw),
         lambda v: "%.4f against %.4f" % v)

    # --- the verdict, on constructed sequences ---
    def verdict_run(grid, every=1, step=1 / 60):
        frames = round(10 / step)
        specs, shown = [], None
        for f in range(frames):
            # `every`: the picture moves on only every so many frames and is held between, as one heard from the audio thread arrives.
            if f % every == 0 or shown is None: shown = grid(f * step)
            specs.append(shown)
        rows = meter(*specs, dt=step)
        first = next((f * step for f, r in enumerate(rows) if r["verdict"] != "listening"), None)
        tail = rows[-240:]
        changes = sorted(r["change"] for r in tail)
        return {"verdict": rows[-1]["verdict"].replace("_", " "), "from": first, "mean": sum(changes) / len(changes),
                "median": changes[len(changes) >> 1], "drift": sum(r["drift"] for r in tail) / len(tail)}
    # An ellipse turning once in eight seconds, which overlaps itself from
    # frame to frame as a real figure does (a dot jumping round a circle
    # saturates its distance at one a step, and cannot show a rate).
    turning = lambda t: "ellipse 0.6 0.25 1 %r" % (t * 2 * math.pi / 8)
    still = "ellipse 0.5 0.3 1 0"
    v = {
        "frozen": verdict_run(lambda t: still),
        "repeating": verdict_run(lambda t: "dot %r %r" % (0.5 + 0.35 * math.cos(t * 2 * math.pi), 0.5 + 0.35 * math.sin(t * 2 * math.pi))),
        "turning": verdict_run(turning),
        "bursts": verdict_run(turning, 3),
        "fast": verdict_run(turning, 1, 1 / 120),
        # A path that never comes back: a spiral out, then across the rest.
        "never": verdict_run(lambda t: "dot %r %r" % (0.5 + 0.45 * (t / 10) * math.cos((t / 10) * 9 * math.pi),
                                                       0.5 + 0.45 * (t / 10) * math.sin((t / 10) * 9 * math.pi))),
        "full": verdict_run(lambda t: "full %r" % t),
    }
    early = meter(*[still] * 60)[-1]["verdict"]
    for k in ("frozen", "repeating", "never", "full"): print("    %-9s %s" % (k, v[k]))
    print("    after one second: %s" % early)
    want = {"frozen": "settled", "repeating": "cycling", "never": "wandering", "full": "running away"}
    got = {k: v[k]["verdict"] for k in want}
    # :293 - each verdict its fixture's and no other fixture's (the
    # classifier's own null). Null beside it: the frozen and repeating
    # fixtures' verdicts exchanged, as a classifier that confused them would give.
    swapped = dict(got, frozen=got["repeating"], repeating=got["frozen"])
    for k, w in want.items():
        held("a %s picture is %s, and no other fixture is" % (k, w),
             lambda g, k=k, w=w: g[k] == w and all(g[o] != w for o in want if o != k), got,
             dict(swapped) if k in ("frozen", "repeating") else dict(got, **{k: "listening"}))
    # :296 - Null: the frozen fixture's verdict after ten seconds.
    held("and nothing is said until there is history to say it from", lambda g: g == "listening", early, got["frozen"])
    # :307 - the same motion arriving every third frame and held between.
    # Null: the bursts judged frame by frame, the old reading (settled when
    # the median per-frame change is under the floor), which P4b found wrong.
    bursts, even, fast = v["bursts"], v["turning"], v["fast"]
    print("    in bursts: %s, median per-frame change %.4f, rate %.4f against %.4f evenly"
          % (bursts["verdict"], bursts["median"], bursts["drift"], even["drift"]))
    old_reading = dict(bursts, verdict="settled" if bursts["median"] < CHANGE_FLOOR else bursts["verdict"])
    held("the same motion in bursts is judged as it is evenly, and not as settled",
         lambda b: b["verdict"] == even["verdict"] != "settled" and abs(b["drift"] - even["drift"]) < 0.15 * even["drift"],
         bursts, old_reading, lambda b: "%s, rate %.4f" % (b["verdict"], b["drift"]))
    # :310 - the fixture's own median is the null of the line above. Its null: the even motion's median.
    held("where its median per-frame change, the old reading, is under the floor", lambda m: m < 0.02,
         bursts["median"], even["median"], lambda m: "%.4f" % m)
    # :318 - the rate's unit is per sixtieth of a second. Null: the rate taken
    # per frame, which at a hundred and twenty is the frame's mean.
    print("    evenly at 60 a second: rate %.4f, mean per frame %.4f; at 120: rate %.4f, mean per frame %.4f"
          % (even["drift"], even["mean"], fast["drift"], fast["mean"]))
    held("the rate is the change per sixtieth of a second: a frame's mean at sixty, the same at a hundred and twenty",
         lambda r: abs(even["drift"] - even["mean"]) < 0.02 * even["mean"] and abs(r - even["drift"]) < 0.15 * even["drift"],
         fast["drift"], fast["mean"], lambda r: "%.4f against %.4f" % (r, even["drift"]))
    # :321 - Null: the even run's own mean.
    held("and at a hundred and twenty a frame does change about half as much, so per frame would not do",
         lambda m: m < 0.65 * even["mean"], fast["mean"], even["mean"], lambda m: "%.4f against %.4f" % (m, even["mean"]))

    # --- the slew on the picture's sources ---
    # :375 and :377 - on the page, genSet('phase', 0) turned the generator's
    # circle into a line and real frames were read for 2.5 s (picture.round
    # and picture.raw.round), with 0.07 of slack for the frames' timing. Here
    # the core's PictureSources at made-up frames of 16 ms with Persistence
    # off: a circle drawn until the slewed value has caught up, then a line,
    # and the slewed and raw roundness read every frame - so the bound is
    # exact, a fall of no more than two whole swings a second.
    # A circle on the screen, so wider in pixels by the graticule's 600 by 450.
    def circle_poly(r):
        return "poly " + ";".join("%.4f,%.4f" % (340 + 600 * r * math.cos(2 * math.pi * k / 96), 255 + 450 * r * math.sin(2 * math.pi * k / 96))
                                  for k in range(97))
    frames = ["plot 40 30 600 450", "persist 0", "pair ellipse 0.5 0.5 4 2048 1.5707963267948966"]
    for i in range(60): frames += ["fade", circle_poly(0.3), "step 16"]
    for i in range(156): frames += ["fade", "poly 190,255;490,255", "step 16"]
    steps = [w for w in picture(*frames) if "values" in w]
    vals = [float(after(w, "values")) for w in steps]
    raws = [float(after(w, "raw")) for w in steps]
    top, end, end_raw = vals[59], vals[-1], raws[-1]
    over = lambda xs: max((a - b) - SLEW * 0.016 for a, b in zip(xs[59:], xs[60:]))
    print("    circle to line: roundness %.3f (raw %.3f) -> %.3f (raw %.3f); fastest fall over the slew by %.4f" % (top, raws[59], end, end_raw, over(vals)))
    # Null: a value that never followed, held at the circle's.
    held("roundness follows the picture as the screen forgets the old one",
         lambda xs: xs[59] > 0.9 and end_raw < 0.1 and xs[-1] < 0.15, vals, [top] * len(vals),
         lambda xs: "%.3f -> %.3f" % (xs[59], xs[-1]))
    # Null: the raw roundness, which with Persistence off falls in a frame.
    held("and no faster than two full swings a second", lambda xs: over(xs) <= 1e-12, vals, raws, lambda xs: "%.4f" % over(xs))

    survey(kit)


# --- the survey that chose the sixth source (shapetest :387, :389), batch 5 ---

def survey(kit):
    """web/tests/survey.js on the core. Five kinds of picture with the loop
    closed - the old library's setups, each under a note held in Mono (A3 at
    full velocity, the Frequency put back), the photocell on, the Picture held
    at nought (shapetest opened ?picture=0), two routings at a half - read
    every sixtieth of a second for four seconds after eight tenths' settling:
    the photocell's raw reading and the picture's raw roundness, coverage,
    change, novelty and signed area. Then, as survey.js: each variable binned
    in eight over its own range, and for each candidate its entropy less the
    most it shares with any one of the other five. Direction (signed) has to
    add half a bit or more; a copy of roundness has to add none.

    It ran on `?brain=js` until batch 5: real animation frames, the page's
    own photocell and picture sources. Here render_cpp, the instrument's own,
    the same every run."""
    import base64, json
    from pieces.perform import library

    def corpus(name):
        return next(dict(e[1]) for s in library() for e in s[1] if e[0] == name)

    def code(setup):
        return base64.b64encode(json.dumps(setup).encode()).decode().rstrip("=")

    configs = [
        ("lag X-Y, roundness on the lag", {"timebase": 3}, {"lagOn": True, "display": "xy"},
         [("picture.round", "view.lag"), ("photo.1", "view.rotate")]),
        ("equal fifth drifting", corpus("Tumbling"), {"just": False}, [("photo.1", "view.zoom"), ("picture.cover", "view.rotate")]),
        ("supersaw fifth", corpus("Supersaw"), {}, [("photo.1", "view.zoom"), ("picture.novelty", "view.rotate")]),
        ("wavetable pad", corpus("Wavetable pad"), {}, [("picture.novelty", "view.rotate"), ("picture.round", "view.zoom")]),
        ("folded third", corpus("Coverage folds the sound"), {}, [("photo.1", "view.rotate"), ("picture.change", "view.zoom")]),
    ]
    rows = []
    for name, setup, more, routes in configs:
        patch = dict(more, photoOn=True, pictureAmount=0, midiMode="mono", mod=";".join("%s>%s@0.500" % r for r in routes))
        freq = str(setup.get("freq", 220))
        lines = [["make", 48000, code(dict(setup, v=7)), patch], ["midi", 0x90, 57, 127], ["slider", "freq", freq],
                 ["reset", "meter"], ["to", 0.8], ["every", 1 / 60, "sources"], ["to", 4.8]]
        for r in kit.render(lines):
            w = [float(x) for x in r["sources"]]
            rows.append([w[0]] + w[2:7] + [w[2]])   # photo raw; round cover change novelty signed raw; a copy of round
    BINS = 8

    def binned(k):
        v = [r[k] for r in rows]
        lo, hi = min(v), max(v)
        return [0 if hi - lo < 1e-9 else min(BINS - 1, math.floor((x - lo) / (hi - lo) * BINS)) for x in v]

    def H(a):
        counts = {}
        for x in a: counts[x] = counts.get(x, 0) + 1
        return -sum(n / len(a) * math.log2(n / len(a)) for n in counts.values())

    def I(a, b):
        return H(a) + H(b) - H([x * BINS + y for x, y in zip(a, b)])

    names = ["photo", "round", "cover", "change", "novelty", "signed", "copy of round"]
    cols = [binned(k) for k in range(len(names))]
    result = {}
    for cand in (5, 6):
        shared = [I(cols[cand], cols[j]) for j in range(5)]
        result[names[cand]] = {"entropy": H(cols[cand]), "adds": H(cols[cand]) - max(shared),
                               "shared": dict(zip(names[:5], (round(x, 3) for x in shared)))}
    for name, r in result.items():
        print("    %-13s entropy %.2f bits; shares %s; adds %.2f bits" % (name, r["entropy"], r["shared"], r["adds"]))
    print("    %d readings over five pictures" % len(rows))
    # Direction is the instrument's own source, under the name the page's
    # SIXTH gives it: registered, by the routed reading's flag. Its null, a
    # name the instrument has not got.
    flags = kit.render([["make", 48000, code({"v": 11, "mod": "picture.signed>view.zoom@0.500;picture.sign>view.zoom@0.500"})],
                        ["to", 0.1], ["read", "routed"]])[-1]["routed"]
    kit.check("the sixth slot is the instrument's own Direction, picture.signed, registered", flags[1] == "1", " ".join(flags))
    kit.null("a source it has not got is not", flags[5] == "0", " ".join(flags))
    kit.check("the source in the sixth slot adds what the other five do not hold, half a bit or more",
              result["signed"]["adds"] > 0.5 and len(rows) >= 5 * 230, "%.2f bits" % result["signed"]["adds"])
    kit.check("and a copy of roundness, the null, adds nothing", abs(result["copy of round"]["adds"]) < 0.01,
              "%.3f bits" % result["copy of round"]["adds"])
    kit.null("and Direction's, which the same bound would call nothing, is not", not (abs(result["signed"]["adds"]) < 0.01))
    # The null of the first: roundness itself put up as the sixth adds what its copy does, nothing.
    kit.null("roundness itself in the sixth slot would add nothing", not (result["copy of round"]["adds"] > 0.5))
