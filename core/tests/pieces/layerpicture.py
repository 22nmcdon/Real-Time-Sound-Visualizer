"""Each layer's picture, and whose sound it moves: layerpicturetest.py's
numbers, on the core alone.

These were layerpicturetest.py's on ?brain=js until stage 5, step 3, batch 2
(13 Nov): there the page's own layer screens (layerPictures) ran over three
real seconds of a split, their stages were written by hand
(Object.assign(layerPictures.stages[l], ...)), the page's route compiler was
stepped (stepRoutes, genRoutes) and layerPush called directly, and a frame
hook filled B's screen every frame for seven seconds. Here
scope::LayerPictures through picture_cpp, the tool parity's "picture's
sources" section drives: each layer's figure laid into its own grid a frame
at a time (lpoly), its stage put in (lput) or reached by its own meter and
governor (lstep), and the pushes each sound hears (push) - the core's
layerPush - read back. Frames are made-up time, so the governor's seven
seconds are 140 frames of 50 ms and not a timer. Each check has its null.
"""
import math

PLOT = "plot 40 30 600 450"
# What each layer's figure is, for its meter's frames (parity's LPC): A's an
# ellipse turning, B's a still dot; swapped where the other layer moves.
TURNING, STILL = "ellipse 0.8 0.5 3 400 0.3", "ellipse 0.02 0.02 1 400 0"
def split(a=TURNING, b=STILL): return [PLOT, "persist 0.12", "lframe 0 " + a, "lframe 1 " + b, "lon 1 1"]


def ellipse(layer, cx, cy, rx, ry, n=48, turn=0.0):
    return "lpoly %d " % layer + ";".join("%.4f,%.4f" % (cx + rx * math.cos(2 * math.pi * k / n + turn),
                                                        cy + ry * math.sin(2 * math.pi * k / n + turn)) for k in range(n + 1))


def turning(layer): return lambda i: ellipse(layer, 340, 255, 200, 120, 48, i * 0.07)
def dot(layer): return lambda i: ellipse(layer, 340, 255, 3, 3, 8)


def frames(count, a, b, elapsed=16):
    out = []
    for i in range(count): out += ["lfade", a(i), b(i), "lstep %d" % elapsed]
    return out


def lines(kit, *commands):
    return kit.run("picture_cpp", "run\n%s\nend\n" % "\n".join(commands)).strip().split("\n")


# A layer's section of a line is its grid, values, raw, verdict and stage
# (parity's lpw, from picture_cpp's own printing); the pushes are A's sound's
# glow, motion and memory, then B's.
RAW = {"cover": 1, "change": 2}
def part(line, layer, what, k=0):
    w = line.split()
    return w[w.index("L%d" % layer) + {"grid": 2, "raw": 12, "verdict": 19, "stage": 21}[what] + k]
def raw(line, layer, key): return float(part(line, layer, "raw", RAW[key]))
def hold(line, layer): return float(part(line, layer, "stage", 3))
def pushes(line):
    w = line.split()
    at = w.index("pushes")
    return [float(w[at + 1]), float(w[at + 4])]   # each sound's glow


def run(kit):
    check, null = kit.check, kit.null
    near = lambda x, y: abs(x - y) < 1e-12

    # --- unsplit, nothing changes ---
    # Was: the page's own layer screens never made (layerPictures.engines
    # null) and every loop route's heldB the shared push, after two seconds of
    # a fifth on ?brain=js. Here, the layers not on: no grid of either is made
    # or measured, and both sounds hear exactly the shared stage's push.
    un = lines(kit, PLOT, "persist 0.12", "sput 0.7 0.1 0.35 0.5", *frames(20, turning(0), dot(1)), "push")
    made = lambda out: any(" L0 grid - - " not in l for l in out if " layers " in l)
    check("unsplit, the layer screens are never made and both sounds carry the one shared push, which moves",
          not made(un) and pushes(un[-1]) == [0.7 * 0.5, 0.7 * 0.5], un[-1][-120:])
    own = lines(kit, *split(), *frames(20, turning(0), dot(1)), "push")
    null("split, the screens are made", made(own))

    # --- each layer's screen measures its own figure ---
    # Was: three real seconds of A's fifth turning and B silent, then the
    # other way round, read off layerPictures.values[l].raw. Activity is
    # coverage times change; what moves is how much lit screen changes (the
    # suite's floors, which it measured: twenty times the still layer's
    # activity, five times its coverage).
    act = lambda line, l: raw(line, l, "cover") * raw(line, l, "change")
    def follows(line, moving, still):
        return (raw(line, moving, "change") > 0.01 and act(line, moving) > 20 * act(line, still)
                and raw(line, moving, "cover") > 5 * raw(line, still, "cover"))
    def last_step(a, b, kinds):
        out = lines(kit, *split(*kinds), *frames(150, a, b))
        return [l for l in out if l.startswith("lstep")][-1]
    a_moves, b_moves = last_step(turning(0), dot(1), (TURNING, STILL)), last_step(dot(0), turning(1), (STILL, TURNING))
    say = lambda line: "A cover %.4f change %.3f, B cover %.4f change %.3f" % (
        raw(line, 0, "cover"), raw(line, 0, "change"), raw(line, 1, "cover"), raw(line, 1, "change"))
    check("with B still, A's screen moves and B's does not", follows(a_moves, 0, 1), say(a_moves))
    check("and with A still, B's moves and A's does not", follows(b_moves, 1, 0), say(b_moves))
    null("the still layer's screen read as the moving one fails", not follows(a_moves, 1, 0) and not follows(b_moves, 0, 1))

    # --- whose sound each picture moves ---
    # Was: the page's stages written by hand and its routes stepped. Here the
    # stages put in (glow, motion, memory, hold) and each sound's push read.
    base = [PLOT, "lon 1 1", "lfade", "lput 0 0.8 0.6 0.4 1", "lput 1 0.2 0.1 0.3 1", "moves A B", "push",
            "lput 1 0.9 0.9 0.9 1", "push", "moves A both", "push"]
    p = [pushes(l) for l in lines(kit, *base) if l.startswith("push")]
    before, b_changed, a_hears_both = p
    check("each picture moving its own sound: B's stage changing moves B's push and not A's",
          before[0] == b_changed[0] and abs(before[1] - b_changed[1]) > 0.01, "%r then %r" % (before, b_changed))
    check("and with A's sound hearing B's picture as well, it moves A's push too - the check can see it",
          abs(a_hears_both[0] - b_changed[0]) > 0.01, "%r" % a_hears_both)
    null("with A's sound hearing both, B's change is not A's same push", a_hears_both[0] != before[0])

    # --- layerPush: averaged, own, crossed, held ---
    # Was: layerPush('glow', layer) called on the page after stages written by
    # hand. The same numbers, from the core's push.
    def at(stage_b_hold, *moves):
        cmds = [PLOT, "lon 1 1", "lfade", "lput 0 0.8 0 0 1", "lput 1 0.2 0 0 %r" % stage_b_hold]
        for a, b in moves: cmds += ["moves %s %s" % (a, b), "push"]
        return [pushes(l) for l in lines(kit, *cmds) if l.startswith("push")]
    both, own, swapped, none = at(1, ("both", "both"), ("A", "B"), ("B", "A"), ("B", "B"))
    check("a sound that hears both pictures takes their average", near(both[0], 0.5) and near(both[1], 0.5), str(both))
    null("and not their sum, which the check would read as wrong", not near(both[0], 1.0))
    check("own, crossed and neither: each sound hears exactly the pictures its menu sends it",
          near(own[0], 0.8) and near(own[1], 0.2) and near(swapped[0], 0.2) and near(swapped[1], 0.8)
          and near(none[0], 0) and near(none[1], 0.5), "own %r, crossed %r, neither %r" % (own, swapped, none))
    null("crossed is not own", not (near(swapped[0], 0.8) and near(swapped[1], 0.2)))
    # B's hold at a quarter: in the crossed pair each cross term carries the
    # lower hold, while A's own term keeps A's hold of one. One way only (A's
    # picture to both, B's to B alone) is not a crossed pair.
    held_both, held_cross, held_one_way = at(0.25, ("both", "both"), ("B", "A"), ("both", "B"))
    check("a crossed pair is held by the lower governor in its cross terms, and an own term by its own",
          near(held_both[0], (0.8 + 0.2 * 0.25) / 2) and near(held_both[1], (0.2 * 0.25 + 0.8 * 0.25) / 2)
          and near(held_cross[0], 0.2 * 0.25) and near(held_cross[1], 0.8 * 0.25) and near(held_one_way[1], (0.8 + 0.2 * 0.25) / 2),
          "both %r, crossed %r, one way %r" % (held_both, held_cross, held_one_way))
    null("and the check fails on a cross term that ignored the hold", not near(held_cross[1], 0.8), str(held_cross))

    # --- a layer's own governor ---
    # Was: the page's frame hook filling B's screen (engines[1].cells.fill(1))
    # every frame for seven real seconds. Here B's grid is filled every frame
    # by a serpentine down the graticule, persistence held, 140 frames of 50
    # ms: B's meter reads running away and its governor holds B at the floor,
    # and A's figure, untouched, keeps its hold of one.
    fill = lambda layer: lambda i: "lpoly %d " % layer + ";".join(
        "%d,%d" % (x, 30 + y) for y in range(0, 452, 4) for x in ((40, 640) if (y // 4) % 2 == 0 else (640, 40)))
    def governed(a, b):
        out = lines(kit, *split(), "persist -1", "moves A B", *frames(140, a, b, 50))
        last = [l for l in out if l.startswith("lstep")][-1]
        return part(last, 0, "verdict"), part(last, 1, "verdict"), hold(last, 0), hold(last, 1)
    va, vb, ha, hb = governed(turning(0), fill(1))
    holds = lambda va, vb, ha, hb: vb == "running_away" and hb == 0.25 and ha == 1
    check("a layer whose screen runs away is held to the floor by its own governor, and the other layer is not",
          holds(va, vb, ha, hb), "A %s, B %s, holds A %g, B %g" % (va, vb, ha, hb))
    flipped = governed(fill(0), turning(1))
    null("with A's screen the one filled, B is not the one held", not holds(*flipped), "A %s, B %s, holds A %g, B %g" % flipped)
