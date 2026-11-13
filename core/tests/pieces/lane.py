"""The zoom and the trigger position as destinations, on the core: lanetest.py's
eight numbers rows.

These were lanetest.py's on a `?brain=js` page of their own until stage 5,
step 3, batch 3 (13 Nov): LFO 1 held at one or nought by hand
(`lfos[0].value`), the page's `applyModMatrix` stepped on a capture, and
`state.zoomMod`, `state.zoom`, `state.positionMod` and the capture's `pre`
read back - the page's own visual matrix. Here the core's: matrix_cpp's
scripted source held at a value, routed to the destinations the instrument's
own screen registers (its `screen` command builds scope::PictureRun on the
matrix, so the spans, ranges and bases are screen.h's and not written here),
and the offset the matrix wrote handed to capture_cpp's capture, which reads
it. Which matrix the face's screen follows on the site - the page's, as
today, or the instrument's - is step 5's to decide; scaletest.py's three
for the full scales, which batch 1 moved to the default page as the face's,
should follow lane's when it is. Each check has its null beside it.
"""


def views(kit, lines):
    """matrix_cpp on one run; each `view` line as (zoomStep, zoomMod, zoom, position, positionMod, level,
    rotateMod, lagMod)."""
    out = kit.run("matrix_cpp", "run\n" + "\n".join(lines) + "\nend")
    return [tuple(float(x) for x in l.split("| view ")[1].split(" amounts")[0].split()) for l in out.split("\n") if l.startswith("view ")]


def pre(kit, posmod):
    """The capture's samples before the trigger, as a share of its window, at a trigger position of a tenth."""
    out = kit.run("capture_cpp", "\n".join(["run", "signal 48000", "add 0 sine 0.5 220 0", "add 1 sine 0.5 220 1", "tb 3",
                                            "pos 0.1", "posmod %r" % posmod, "cap", "end"]))
    w = [l for l in out.split("\n") if l.startswith("cap ")][0].split()
    return float(w[w.index("pre") + 1]), float(w[w.index("len") + 1])


def run(kit):
    check, null = kit.check, kit.null

    # --- zoom is a destination ---
    held = lambda v: ["value lfo1 %r" % v, "frame", "view"]
    z = views(kit, ["screen", "source lfo1", "route lfo1 view.zoom 1", "vset zoomStep 0"] + held(1) + held(0) + held(0.5))
    up, rest, half = z
    check("full depth is the eight steps it declares", up[1] == 8, str(up[1]))
    null("and half the source is four, not eight", half[1] == 4 and half[1] != 8, str(half[1]))
    check("and it magnifies", up[2] > rest[2] * 1.5, "%.2f vs %.2f" % (up[2], rest[2]))
    null("at rest it does not", not (rest[2] > rest[2] * 1.5))
    check("with the offset back to nothing at rest", rest[1] == 0, str(rest[1]))
    null("the offset at full is not nothing", up[1] != 0)

    # --- the trigger position slides the window, not the trigger ---
    # The first version of this, on the page, asserted that `positionMod`
    # held 0.5 and stopped there - and passed for two releases while NOTHING
    # READ IT. So the window is read off the capture, given the offset the
    # matrix wrote.
    t = views(kit, ["screen", "source lfo1", "route lfo1 trig.position 1", "vset position 0.1", "vset level 0.3",
                    "value lfo1 0", "frame", "view"] + held(1) + held(0))
    before, up, rest = t
    check("full depth moves the offset half a window", up[4] == 0.5, str(up[4]))
    null("and the knob's own place is not the offset", up[3] != up[4], str(up[3]))
    check("and nothing at rest", rest[4] == 0, str(rest[4]))
    (p0, n0), (p1, n1) = pre(kit, rest[4]), pre(kit, up[4])
    moved = (p1 - p0) / n1
    check("and the window actually slides by that much", abs(moved - 0.5) < 0.02,
          "%.3f of the window (%d -> %d samples of %d)" % (moved, p0, p1, n1))
    np0, _ = pre(kit, 0.25)
    null("half the offset slides it half as far", abs((np0 - p0) / n0 - 0.5) > 0.2, "%.3f" % ((np0 - p0) / n0))
    check("the trigger level is untouched", up[5] == before[5] == 0.3, "%s -> %s" % (before[5], up[5]))
    check("and so is the knob it is offset from", up[3] == before[3] == 0.1, str(up[3]))
    null("the same reads see a knob moved: a position of 0.2 is not the tenth",
         views(kit, ["screen", "vset position 0.2", "view"])[0][3] != 0.1)
