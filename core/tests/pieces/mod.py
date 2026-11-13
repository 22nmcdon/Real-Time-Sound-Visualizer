"""The matrix's sums, its ranges and the rotation, on the core: modtest.py's
numbers rows from :157 to :378.

These were modtest.py's on `?brain=js` until stage 5, step 3, batch 3 (13
Nov): the page's LFOs held still by hand (`lfos[0].value = 0.9`), its
`genRoutes` summed in the test itself, its `applyModMatrix` read back, and
its `capture()` read for the rotation. Here the core's: matrix_cpp's
scripted sources held at a value (and the instrument's own screen
destinations, its `screen` command), the routes the matrix hands the
generator played by generator_cpp, and capture_cpp's capture turned and its
lanes read whole (`dump`). The rest of modtest.py - the codec, the editor and
the face - is the face's and stays in the suite. Each check has its null.
"""
import math

import numpy as np

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
