"""Layer B's own plane, turn and echo: layerplanetest.py's numbers, on the core
alone.

These were layerplanetest.py's on ?brain=js until stage 5, step 3, batch 2
(13 Nov): an offline makeGeneratorCore built in the page, A a sine fifth (C3
on X, G3 on Y) and B one sine A4 drawn on both axes, set by `core.set` and
routed by `setRoutes` with the held values put in, eight blocks of 4096 at
44.1 kHz and the last 8192 samples of each lane read. Here the same, through
generator_cpp (blocks of 128, the six lanes a sample: A's picture, the heard
pair, B's picture), with the routes in its own form - index, held, heldB,
slot, amount, amountB, flags - so a route's held value is put in as the page's
was. And the screen's rotation against B's own turn, which the suite read
off the page's beam, is read off the instrument's own grid. Each check has
its null beside it.
"""
import base64, json, math

import numpy as np

RATE = 44100.0
HZ = lambda n: 440 * 2 ** ((n - 69) / 12)
TWIST, ECHO, TURN = 18, 24, 32   # GEN_DESTS slots, as generator.h numbers them
TRAILER = 17


def core(kit, sets=(), routes=None):
    """The six lanes' last 8192 samples, after 32768, for one setup."""
    ev = ["at 0 set shape sine", "at 0 set shape sine 1",
          "at 0 voices 0 48/%r/1/x+55/%r/1/y" % (HZ(48), HZ(55)), "at 0 voices 1 69/%r/1/xy" % HZ(69)]
    for field, value, layer in sets:
        ev.append("at 0 set %s %s %d" % (field, ("true" if value else "false") if isinstance(value, bool) else repr(value), layer))
    if routes:
        ev.append("at 0 routes " + "+".join("%d/%r/%r/%d/%r/%r/0" % (r.get("index", -1), r.get("held", 0), r.get("heldB", 0),
                                                                      r["slot"], r["amount"], r["amountB"]) for r in routes))
    text = "run rate=%r slots=40 seed=3 samples=32768 lfo0=sine,0.9 lfo1=sine,0.9\n%s\nend" % (RATE, "\n".join(ev))
    body = np.array(kit.floats("generator_cpp", text)[:-TRAILER])
    return [body[k::6][-8192:] for k in range(6)]


def bin_at(x, f):
    i = np.arange(len(x))
    w = 0.5 - 0.5 * np.cos(2 * np.pi * i / (len(x) - 1))
    return abs(np.sum(x * w * np.exp(-2j * np.pi * f * i / RATE))) / len(x)


peak = lambda x: float(np.max(np.abs(x)))
same = lambda a, b: bool(np.array_equal(a, b))
apart = lambda a, b: float(np.max(np.abs(a - b)))


def run(kit):
    check, null = kit.check, kit.null

    # --- off is the old arithmetic, on is B's own ---
    junk = [("planeMirror", 3, 1), ("planeTurn", 1.1, 1), ("planeTwist", 2, 1), ("planeLimit", 2, 1),
            ("planeRadius", 0.2, 1), ("planeSnap", 3, 1)]
    a_plane = [("planeTwist", 0.7, 0), ("delayMix", 0.3, 0), ("delayMs", 9, 0)]
    rest, off, on = core(kit, a_plane), core(kit, a_plane + junk), core(kit, a_plane + junk + [("planeOwn", True, 1)])
    check("with B's own off, B's fields set to junk change not one sample of any pair", all(same(rest[k], off[k]) for k in range(6)))
    check("and with it on the same junk changes B's picture and the sound, and not A's picture",
          not same(rest[4], on[4]) and not same(rest[2], on[2]) and same(rest[0], on[0]) and same(rest[1], on[1]))
    null("with B's own on, the junk is not the rest's samples", not all(same(rest[k], on[k]) for k in range(6)))

    # --- B's mirror is B's ---
    mir = core(kit, [("planeOwn", True, 1), ("planeMirror", 1, 1)])
    mir_off = core(kit, [("planeMirror", 1, 1)])
    folds = lambda m: float(np.min(m[4])) > -1e-3 and float(np.min(m[0])) < -0.1 and peak(m[4]) > 0.1
    check("B's own mirror folds B's X onto its right half, and A's X keeps its left", folds(mir),
          "lowest X: A %.3f, B %.3f" % (np.min(mir[0]), np.min(mir[4])))
    check("and the same field with B's own off folds nothing", float(np.min(mir_off[4])) < -0.1, "%.4f" % np.min(mir_off[4]))
    null("B's own off is not folded", not folds(mir_off))

    # --- B's turn ---
    flat = core(kit, [("planeOwn", True, 1)])
    turned = core(kit, [("planeOwn", True, 1), ("planeTurn", math.pi / 4, 1)])
    back = core(kit, [("planeOwn", True, 1), ("planeTurn", -math.pi / 4, 1)])
    check("unturned, B's one note is a diagonal: X and Y the same", peak(flat[4]) > 0.1 and apart(flat[4], flat[5]) < 1e-6)
    on_y = lambda t: peak(t[4]) < 1e-3 * peak(flat[4]) and abs(peak(t[5]) / peak(flat[4]) - math.sqrt(2)) < 0.01
    check("an eighth of a turn lays it on the Y axis: X nought, Y the diagonal's length", on_y(turned),
          "X %.5f, Y %.4f of the diagonal" % (peak(turned[4]), peak(turned[5]) / peak(flat[4])))
    null("unturned is not on the Y axis", not on_y(flat))
    check("and the other way lays it on the X axis instead, the same length",
          peak(back[5]) < 1e-3 * peak(flat[4]) and apart(back[4], turned[5]) < 1e-4, "%.5f %.5f" % (peak(back[5]), peak(back[4])))
    null("the eighth one way is not on the X axis", not peak(turned[5]) < 1e-3 * peak(flat[4]))

    # --- each layer's share of the sound through its own plane ---
    # A mirror on X rectifies the left channel, which puts the note's octave
    # there; read on the heard left.
    fa, fb = HZ(48), HZ(69)
    octaves = lambda m: (bin_at(m[2], 2 * fa), bin_at(m[2], 2 * fb))
    own_b = octaves(mir)
    both = octaves(core(kit, [("planeMirror", 1, 0)]))
    own_none = octaves(core(kit, [("planeOwn", True, 1), ("planeMirror", 1, 0)]))
    b_alone = lambda o: o[1] > 0.01 and o[0] < 0.1 * o[1]
    check("with B's own mirror and none of A's, B's octave is heard and A's is not", b_alone(own_b), str(np.round(own_b, 4)))
    check("Together, the mirror is both layers' and both octaves are heard", both[0] > 0.01 and both[1] > 0.01, str(np.round(both, 4)))
    check("and with the mirror A's alone, A's octave is heard and B's is not",
          own_none[0] > 0.01 and own_none[1] < 0.1 * own_none[0], str(np.round(own_none, 4)))
    null("Together is not B's octave alone", not b_alone(both))

    # --- a routing reaches B's own twist through B's fade ---
    # LFO 1 (sine, 0.9 Hz) on the twist, at A's depth and B's.
    route = lambda a, b: core(kit, [("planeOwn", True, 1)], [{"index": 0, "slot": TWIST, "amount": a, "amountB": b}])
    q = [route(0.9, 0), route(0.1, 0), route(0.1, 0.6)]
    check("B's picture with A's depth on the twist changed and B's still nothing is the same picture",
          same(q[0][4], q[1][4]) and same(q[0][5], q[1][5]))
    check("and given a depth of its own, it moves", not same(q[1][4], q[2][4]), "%.4f" % apart(q[1][4], q[2][4]))
    null("A's depth changed does move A's picture", not same(q[0][0], q[1][0]))

    # --- B's turn as a destination ---
    # A held value of one, so the push is the depth: B's depth a quarter is an
    # eighth of a turn. A's depth on it is a different number, and is nothing.
    turn = lambda own, b: core(kit, [("planeOwn", own, 1)], [{"held": 1, "heldB": 1, "slot": TURN, "amount": 0.9, "amountB": b}])
    t_on, t_none, t_off = turn(True, 0.25), turn(True, 0), turn(False, 0.25)
    check("a routing on Turn at B's depth of a quarter turns B an eighth: its diagonal on the Y axis",
          peak(t_on[4]) < 1e-3 * peak(t_on[5]) and abs(peak(t_on[5]) / peak(flat[4]) - math.sqrt(2)) < 0.01,
          "%.5f %.4f" % (peak(t_on[4]), peak(t_on[5])))
    check("and at B's depth of nought, whatever A's, B is not turned", apart(t_none[4], t_none[5]) < 1e-6 and peak(t_none[4]) > 0.1)
    flat_off = core(kit)
    check("and with B's own plane off the routing turns nothing", same(t_off[4], flat_off[4]) and same(t_off[5], flat_off[5]))
    null("at A's depth, 0.9 for B too, B is turned", apart(turn(True, 0.9)[4], turn(True, 0.9)[5]) > 0.01)

    # --- B's own echo and chorus ---
    # B's note is 440 Hz: an echo half a period late, at half level, is the
    # note less half of itself. A's chord, 131 and 196 Hz, it moves rather than cancels.
    half = 1000 / (2 * fb)
    b_echo = [("delayMix", 0.5, 1), ("delayMs", half, 1), ("delayFeedback", 0, 1)]
    a_echo = [("delayMix", 0.5, 0), ("delayMs", half, 0), ("delayFeedback", 0, 0)]
    dry = core(kit)
    e_own = core(kit, [("timeOwn", 4, 1)] + b_echo)   # B's own delay is its bit of timeOwn since G6
    e_off = core(kit, b_echo)
    e_both = core(kit, a_echo)
    ratio = lambda m, k: peak(m[k]) / peak(dry[k])
    check("B's own echo half a period late cancels half of B's picture, and leaves A's the same samples",
          abs(ratio(e_own, 4) - 0.5) < 0.02 and same(e_own[0], dry[0]) and same(e_own[1], dry[1]), "%.4f" % ratio(e_own, 4))
    check("and with B's own off its echo's fields do nothing", same(e_off[4], dry[4]) and same(e_off[2], dry[2]))
    check("Together, the same echo as A's halves B's picture as well, and moves A's",
          abs(ratio(e_both, 4) - 0.5) < 0.02 and not same(e_both[0], dry[0]), "%.4f" % ratio(e_both, 4))
    null("B's own echo off leaves B's picture whole, not halved", abs(ratio(e_off, 4) - 0.5) > 0.4)
    hb = lambda m, f: bin_at(m[2], f) / bin_at(dry[2], f)
    check("in the heard pair B's own echo halves B's note and leaves A's",
          abs(hb(e_own, fb) - 0.5) < 0.03 and abs(hb(e_own, fa) - 1) < 1e-3, "B %.3f, A %.4f" % (hb(e_own, fb), hb(e_own, fa)))
    check("and Together the echo, A's, moves A's note too",
          abs(hb(e_both, fb) - 0.5) < 0.03 and abs(hb(e_both, fa) - 1) > 0.1, "B %.3f, A %.3f" % (hb(e_both, fb), hb(e_both, fa)))
    null("Together is not A's note left alone", not abs(hb(e_both, fa) - 1) < 1e-3)
    # The echo's level routed, with nothing of its own: a held value of one, so
    # B's depth of one is a push of half - the same half-level echo.
    eroute = lambda a, b: core(kit, [("timeOwn", 4, 1), ("delayMs", half, 1), ("delayFeedback", 0, 1)],
                               [{"held": 1, "heldB": 1, "slot": ECHO, "amount": a, "amountB": b}])
    r_b, r_a = eroute(0, 1), eroute(1, 0)
    check("a routing on the echo's level through B's fade gives B's own echo its level", abs(ratio(r_b, 4) - 0.5) < 0.02,
          "%.4f" % ratio(r_b, 4))
    check("and through A's fade alone it leaves B's picture as it was", abs(ratio(r_a, 4) - 1) < 1e-3, "%.4f" % ratio(r_a, 4))
    null("through A's fade it is not B's halved", abs(ratio(r_a, 4) - 0.5) > 0.4)

    # --- the screen's rotation, and B turning itself ---
    # Was: the page's beamX/beamY after state.rotate = 0.125 set by hand, B's
    # one note on both axes - kept a diagonal with the Plane the upper's own,
    # laid on the Y axis linked. Here the instrument's own grid, natively: its
    # rotation moved on the panel (the Turn's slider, 12.5 per cent, an eighth),
    # the link pressed as a hand presses it, and B's figure read off the grid
    # by its spread across and up from its centre of light.
    code = base64.b64encode(json.dumps({"v": 4, "shape": "sine", "pictureAmount": 0}).encode()).decode().rstrip("=")
    def grid(*hands):
        lines = [["make", 48000, 128, code], ["click", "dispXY"], ["click", "midiPoly"],
                 ["control", "midiLayers", "split"], *hands, ["midi", 0x90, 72, 100]] + [["block", 128]] * 60 + [["grid"]]
        out = kit.instrument(lines)
        assert not any(l == "no" for l in out), "a move refused"
        return tuple(float(v) for v in [l for l in out if l.startswith("grid ")][-1].split()[1:])
    OWN = (["click", "editHandB"], ["click", "linkPlane"])
    own_still, own_turned = grid(*OWN), grid(*OWN, ["slider", "rotate", "12"])
    linked_still, linked_turned = grid(), grid(["slider", "rotate", "12"])
    check("with the Plane the upper's own, the screen's rotation leaves B's figure as it was", own_turned == own_still,
          "%r against %r" % (own_turned, own_still))
    check("and linked turns it, as it turns A", linked_turned != linked_still and linked_still == own_still,
          "%r against %r" % (linked_turned, linked_still))
    null("linked, the turned grid is not the unturned", linked_turned != own_still)

    # --- B's own echo synced to the tempo ---
    # Was: genSettings(1).delayMs after setTempo and clockStep(performance.now())
    # called by hand on the page - the page's clock and its mirror. Here the
    # instrument, natively: B's Delay its own by the link, synced to a
    # crotchet, no feedback, at half mix; B's note held 53 ms with the
    # shortest release, then the echo found in B's lanes - its first block
    # loud again after the note has gone quiet - at the tempo the panel's
    # slider gives. The null is the same echo unsynced, at its own 375 ms.
    def echo_at(tempo, sync="1/4"):
        lines = [["make", 48000, 128, code], ["click", "dispXY"], ["click", "midiPoly"], ["control", "midiLayers", "split"],
                 ["slider", "envRelease", "1"], ["click", "editHandB"], ["click", "linkDelay"], ["slider", "delayFeedback", "0"],
                 ["slider", "delayMix", "50"], ["control", "delaySync", sync], ["slider", "tempo", str(tempo)],
                 ["midi", 0x90, 72, 100]] + [["block", 128]] * 20 + [["midi", 0x80, 72, 0]] + [["block", 128]] * 450
        out = kit.instrument(lines)
        assert "no" not in out, "a move refused"
        b = [max(abs(float(v)) for v in l.split()[1:][4 * 128:5 * 128]) for l in out if l.startswith("block ")]
        gone = next(k for k in range(20, len(b)) if b[k] < 1e-4)
        back = next((k for k in range(gone, len(b)) if b[k] > 0.01), None)
        return None if back is None else back * 128 / 48   # ms from the note
    at120, at60, free = echo_at(120), echo_at(60), echo_at(60, "")
    near = lambda ms, want: ms is not None and want - 128 / 48 <= ms <= want + 1e-9
    check("B's own echo synced to a crotchet follows the tempo: 500 ms at 120, 1000 at 60",
          near(at120, 500) and near(at60, 1000), "the echo %r ms and %r ms after the note" % (at120, at60))
    null("unsynced, B's echo keeps its own 375 ms whatever the tempo", near(free, 375) and not near(free, 1000), "%r ms" % free)
