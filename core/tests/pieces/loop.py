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

What is not here: the stability runs and Scan's tables in the loop (looptest
:523 on), which play corpus setups with the loop closed over seconds and read
the stage's holds and the meter's verdicts - render_cpp's.
"""
import math

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
