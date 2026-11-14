"""The matrix's sums, its ranges and the rotation, on the core: modtest.py's
numbers rows from :157 to :378, and since batch 6 its octave sweep (:130,
:131), its routing to nowhere (:170) and its oscillator's rate (:429, :436).

These were modtest.py's on `?brain=js` until stage 5, step 3, batch 3 (13
Nov): the page's LFOs held still by hand (`lfos[0].value = 0.9`), its
`genRoutes` summed in the test itself, its `applyModMatrix` read back, and
its `capture()` read for the rotation. Here the core's: matrix_cpp's
scripted sources held at a value (and the instrument's own screen
destinations, its `screen` command), the routes the matrix hands the
generator played by generator_cpp, and capture_cpp's capture turned and its
lanes read whole (`dump`). The rest of modtest.py - the codec, the editor and
the face - is the face's and stays in the suite. Each check has its null.

Batch 6 (14 Nov): the octave sweep was the page's capture of its own
generator, timed in real frames (the suite is serial for it, and it flaked
under load); the routing to nowhere counted the page's `genRoutes` after its
own `compileRoutes`; and the rate counted wraps of the page's `lfos[0].phase`,
set to 2 Hz by hand, over real seconds, on its tone and then its own
microphone (`toMic`), where a per-sample and a per-frame step had once both
run. Here the instrument rendered offline (render_cpp): a note held in Mono
with LFO 1 on the frequency, the pitch read off the heard pair, and the
oscillator's value read as its routing carries it, every 10 ms of audio, on
the generator and on an input drawn; and the core's matrix loading a code
with routings to nothing.
"""
import base64, json, math, os

import numpy as np

from pieces.kit import BUILD

from pieces.lane import views
from pieces.loop import bin_at, matrix, play, sources


def axis(kit, rotate):
    """The principal axis, in degrees, of a diagonal line captured at a rotation, and whether the capture turned it."""
    out = kit.run("capture_cpp", "\n".join(["run", "signal 48000", "add 0 sine 0.5 220 0", "add 1 sine 0.5 220 0", "tb 3",
                                            "rot %r" % rotate, "cap", "dump", "end"]))
    cap = [l for l in out.split("\n") if l.startswith("cap ")][0].split()
    v = np.array([float(x) for x in [l for l in out.split("\n") if l.startswith("dump")][0].split()[1:]])
    x, y = v[:len(v) // 2], v[len(v) // 2:]
    px, py = x - x.mean(), y - y.mean()
    deg = 0.5 * math.degrees(math.atan2(2 * (px * py).sum(), (px * px).sum() - (py * py).sum()))
    return deg, cap[cap.index("turned") + 1] == "1"


def code(setup):
    return base64.b64encode(json.dumps(dict({"v": 11, "pictureAmount": 0, "midiMode": "mono", "shape": "sine",
                                              "interval": 0, "l0s": "sine"}, **setup)).encode()).decode().rstrip("=")


def sweep(kit, depth, mode="mono"):
    """A4 held in Mono with LFO 1 at half a cycle a second on the frequency at
    `depth`: the heard pitch every 50 ms over four seconds, by zero crossings."""
    os.makedirs(BUILD, exist_ok=True)
    path = os.path.join(BUILD, "mod-sweep-%r-%s.f32" % (depth, mode))
    kit.render([["make", 48000, code({"mod": "lfo1>gen.freq@%.3f" % depth, "l0r": 50, "midiMode": mode})], ["midi", 0x90, 69, 127],
                ["to", 0.2], ["record", "heard", path], ["to", 4.2]])
    x = np.fromfile(path, "<f4").reshape(-1, 2)[:, 0].astype(float)
    n = 2400
    out = []
    for k in range(0, len(x) - n, n):
        w = x[k:k + n]
        ups = np.nonzero((w[:-1] <= 0) & (w[1:] > 0))[0]
        if len(ups) >= 3:
            # Interpolated crossings, first to last, over the cycles between.
            at = [i + w[i] / (w[i] - w[i + 1]) for i in ups]
            out.append((len(at) - 1) * 48000 / (at[-1] - at[0]))
    return out


def lfo_values(kit, rate, drawn_input=False):
    """LFO 1's value as its routing carries it, every 10 ms for three seconds."""
    lines = [["make", 48000, code({"mod": "lfo1>gen.freq@0.100", "l0r": round(rate * 100)})], ["midi", 0x90, 69, 127]]
    if drawn_input: lines += [["click", "srcMic"], ["input", "sine", 330, 0.5, 330, 0.5]]
    rows = kit.render(lines + [["every", 0.01, "routed"], ["to", 3.0]])
    return [(r["t"], float(r["routed"][2])) for r in rows if "routed" in r]


def wraps(values):
    return sum(1 for (_, a), (_, b) in zip(values, values[1:]) if a < 0 <= b)


def run(kit):
    check, null = kit.check, kit.null

    # --- contributions add ---
    # Both LFOs held at 0.9 on the frequency, at a half and a quarter: the
    # routes the matrix hands the generator, and the pitch it plays.
    r = matrix(kit, sources(["lfo1", "lfo2"], 0.9, "1", "") + ["route lfo1 gen.freq 0.5", "route lfo2 gen.freq 0.25", "frame"])[0][1]
    x = play(kit, r)
    both, one = 220 * 2 ** (0.9 * 0.5 + 0.9 * 0.25), 220 * 2 ** (0.9 * 0.5)
    check("contributions add", len(r) == 2 and bin_at(x, both) > 0.05 and bin_at(x, one) < 0.01 * bin_at(x, both),
          "energy at the sum's pitch %.4f, at the first alone %.4f" % (bin_at(x, both), bin_at(x, one)))
    y = play(kit, r[:1])
    null("the first alone plays its own pitch", bin_at(y, one) > 0.05 and bin_at(y, both) < 0.01 * bin_at(y, one))

    # --- a rotation really turns the figure ---
    # Both lanes one sine, a diagonal line (a circle would read the same
    # turned, CLAUDE.md's fixtures); the lanes as the capture hands them,
    # not turned here.
    flat, f_turned = axis(kit, 0)
    turned, t_turned = axis(kit, 0.125)
    turn = (turned - flat + 180) % 180
    check("a rotation really turns the figure", t_turned and abs(turn - 45) < 3, "%.1f deg from %.1f to %.1f" % (turn, flat, turned))
    null("unturned it is the diagonal, and not turned", not f_turned and abs(flat - 45) < 1, "%.1f" % flat)

    # --- the screen's offsets, nothing routed and pushed past the range ---
    rest = views(kit, ["screen", "frame", "view"])[0]
    check("with nothing routed every offset is zero", (rest[1], rest[4], rest[6], rest[7]) == (0, 0, 0, 0), str(rest))
    v = views(kit, ["screen", "source lfo1", "vset rotate 0", "route lfo1 view.rotate 99", "value lfo1 1", "frame", "view",
                    "amount lfo1 view.rotate 1", "frame", "view"])
    check("and a source cannot push past the range", v[0][6] == 2, "%.2f against a limit of 2 (screen.h's view.rotate)" % v[0][6])
    null("inside the range it is the depth", v[1][6] == 1, "%.2f" % v[1][6])
    null("and routed, an offset is not zero", v[1][6] != 0)

    # --- one octave each way ---
    hz = sweep(kit, 1.0)
    print("    440 Hz swept by LFO 1 at full depth: %.1f to %.1f Hz over %d reads" % (min(hz), max(hz), len(hz)))
    check("one octave down is reached", 214 < min(hz) < 226, "%.1f Hz" % min(hz))
    check("one octave up is reached", 856 < max(hz) < 904, "%.1f Hz" % max(hz))
    # And in Poly, where a held note is a voice and its pitch is the voices'
    # own path (the mutation pass found Mono alone could not see it).
    poly = sweep(kit, 1.0, "poly")
    print("    the same in Poly: %.1f to %.1f Hz" % (min(poly), max(poly)))
    check("and in Poly, one octave each way", 214 < min(poly) < 226 and 856 < max(poly) < 904,
          "%.1f to %.1f Hz" % (min(poly), max(poly)))
    half = sweep(kit, 0.5)
    null("at half the depth neither is", not (214 < min(half) < 226) and not (856 < max(half) < 904),
         "%.1f to %.1f Hz" % (min(half), max(half)))

    # --- a routing to nowhere ---
    # A code whose second routing goes to a destination that does not exist
    # and whose third comes from a source that does not: only the first
    # reaches the generator. The null, the same code with real ones.
    load = lambda text: matrix(kit, sources(["lfo1"], 0.5, "1", "") + ["load " + text, "frame"])[0][1]
    nowhere = load("lfo1>gen.phase@0.5;lfo1>filter.nothing@0.5;env.nothing>gen.freq@0.5")
    check("an unknown destination, or source, is skipped", len(nowhere) == 1 and nowhere[0][3] == "2", str(nowhere))
    real = load("lfo1>gen.phase@0.5;lfo1>gen.freq@0.5;lfo1>gen.ratio@0.5")
    null("three routings that exist all reach it", len(real) == 3, str(real))

    # --- every oscillator advances exactly once ---
    for drawn, name in ((False, "on the generator"), (True, "with an input drawn")):
        v = lfo_values(kit, 2, drawn)
        worst = max(abs(x - math.sin(2 * math.pi * 2 * t)) for t, x in v)
        print("    LFO 1 at 2 Hz %s: %d cycles in 3 s, %.1e from sin(2 pi 2 t)" % (name, wraps(v), worst))
        check("2 Hz is 2 Hz %s: six cycles in three seconds, on the sine's own times" % name,
              wraps(v) == 6 and worst < 1e-6, "%d, %.1e" % (wraps(v), worst))
    # The null: the same rule on an oscillator going twice as fast, as one
    # stepped twice would.
    double = lfo_values(kit, 4)
    worst = max(abs(x - math.sin(2 * math.pi * 2 * t)) for t, x in double)
    null("an oscillator at 4 Hz fails the same rule", not (wraps(double) == 6 and worst < 1e-6), "%d cycles, %.2f off" % (wraps(double), worst))
