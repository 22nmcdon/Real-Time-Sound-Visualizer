"""Two layers from one core, and which layer a note goes to: layertest.py's
numbers, on the core alone.

These were layertest.py's on ?brain=js until stage 5, step 3, batch 2 (13
Nov): there the page's makeGeneratorCore was built and run in the browser, and
the page's own keyboard (setMidiMode, midi.layers.point, midi.draws written by
hand, genSettings(layer).voices read back) decided where each note went. Here
the generator is scope::Generator through generator_cpp, which hands back the
six lanes a sample (A's picture pair, the heard pair, B's picture pair) and,
after the last, the envelope and each layer's voice count; and the keyboard is
scope::Keyboard through keyboard_cpp, which writes down every chord it hands
each layer. Each check has its null beside it.
"""
import math

import numpy as np

RATE = 44100.0
HZ = lambda n: 440 * 2 ** ((n - 69) / 12)
AMP, TWIST = 1, 18
TRAILER = 17   # generator_cpp's values after the last sample


def voices(*ns):
    return "+".join("%d/%r/1/%s" % (n, HZ(n), role) for n, role in ns) if ns else "none"


def gen(kit, events, samples, lfo0="sine,1", lfo1="sine,1"):
    """The six lanes as arrays, and the trailer."""
    text = "run rate=%r slots=40 seed=3 samples=%d lfo0=%s lfo1=%s\n%s\nend" % (
        RATE, samples, lfo0, lfo1, "\n".join("at %d %s" % e for e in events))
    v = kit.floats("generator_cpp", text)
    body, tail = np.array(v[:-TRAILER]), v[-TRAILER:]
    return [body[k::6] for k in range(6)], {"envelope": tail[0], "voices": tail[10], "voicesB": tail[11]}


def bin_at(x, f, rate=RATE):
    """A Hann-windowed single bin, as the suite's __bin: a chord crosses nought at the rate of none of its notes."""
    i = np.arange(len(x))
    w = 0.5 - 0.5 * np.cos(2 * np.pi * i / (len(x) - 1))
    return abs(np.sum(x * w * np.exp(-2j * np.pi * f * i / rate))) / len(x)


def keyboard(kit, *commands):
    """keyboard_cpp's lines for one run, and the last chord each layer was handed after each command."""
    out = kit.run("keyboard_cpp", "run\n%s\nend" % "\n".join(commands)).strip().split("\n")
    chords, now = [], {0: [], 1: []}
    for line in out:
        for part in line.split(" | ")[0].split(" :: ")[1:]:
            w = part.split()
            if w[:2] == ["set", "voices"]:
                now[int(w[3])] = [] if w[2] in ("none", "null") else [
                    (int(x.split("/")[0]), x.split("/")[3]) for x in w[2].split("+")]
        chords.append({k: list(v) for k, v in now.items()})
    return out, chords


def run(kit):
    check, null = kit.check, kit.null

    # --- one step of the oscillators a sample, however many layers ---
    # Was: lfos[0].phase read after a quarter-second block of the page's core,
    # one layer and two. The core hands no phase out, so the oscillator is
    # heard instead: a 4 Hz square on A's amplitude toggles A's level eight
    # times a second, sixteen if a second layer stepped it again.
    def toggles(layered):
        ev = [(0, "voices 0 " + voices((48, "x"))), (0, "routes 0/0/0/%d/0.5/0.5/0" % AMP)]
        if layered: ev.append((0, "voices 1 " + voices((72, "xy"))))
        lanes, _ = gen(kit, ev, 44032, lfo0="square,4")
        peaks = [float(np.max(np.abs(lanes[0][k:k + 128]))) for k in range(0, len(lanes[0]), 128)]
        lo, hi = min(peaks[8:]), max(peaks[8:])
        level = [p > (lo + hi) / 2 for p in peaks[8:]]
        return sum(a != b for a, b in zip(level, level[1:])), lo, hi
    one, two = toggles(False), toggles(True)
    check("two layers step the oscillators once a sample, not twice: a 4 Hz square on A's level toggles it about eight times a second either way",
          one[0] == two[0] and 7 <= two[0] <= 8 and one[2] > 1.5 * one[1],
          "one layer %d toggles, two %d (levels %.3f to %.3f)" % (one[0], two[0], two[1], two[2]))
    null("a doubled step, sixteen toggles, is not what two layers give", not (14 <= two[0] <= 17))

    # --- each layer's picture, and one sound ---
    # Was: the page's core, A a sine fifth (C3 on X, G3 on Y), B a square E5
    # on both axes, A quick to speak and B slow, 0.8 s, bins on the last 16384.
    n = int(RATE * 0.8) // 128 * 128
    base = [(0, "set shape sine"), (0, "set shape square 1"), (0, "set attackMs 2"), (0, "set attackMs 400 1"),
            (0, "voices 0 " + voices((48, "x"), (55, "y"))), (0, "voices 1 " + voices((76, "xy")))]
    (al, ar, hl, hr, bl, br), _ = gen(kit, base, n)
    tail = lambda x: x[-16384:]
    c, g, e = HZ(48), HZ(55), HZ(76)
    aX = [bin_at(tail(al), f) for f in (c, g, e)]
    aY = [bin_at(tail(ar), f) for f in (c, g, e)]
    bX = [bin_at(tail(bl), f) for f in (c, g, e)]
    heard = [bin_at(tail(hl), f) for f in (c, g, e)]
    top = max(aX[0], 1e-9)
    a_has = lambda X, Y: X[0] > 0.05 and Y[1] > 0.05 and X[2] < top * 0.01 and Y[2] < top * 0.01
    check("layer A's picture has A's notes and not B's", a_has(aX, aY), "A's X %s, Y %s" % (np.round(aX, 4), np.round(aY, 4)))
    null("B's picture read as A's has not A's notes", not a_has(bX, bX))
    b_has = lambda X: X[2] > 0.05 and X[0] < top * 0.01 and X[1] < top * 0.01
    check("layer B's picture has B's note and not A's", b_has(bX), "B's X %s" % np.round(bX, 4))
    null("A's picture read as B's has not B's note", not b_has(aX))
    check("and the heard pair has all three", min(heard) > 0.03, str(np.round(heard, 4)))
    null("A's picture alone, read as heard, has not all three", not min(aX) > 0.03)
    worst = float(max(np.max(np.abs(hl - al - bl)), np.max(np.abs(hr - ar - br))))
    check("because it is A's lanes and B's summed, sample for sample", worst < 1e-6, "worst %.3g" % worst)
    without = float(np.max(np.abs(hl - al)))
    null("the comparison fails with B left out", without > 0.05, "%.3g" % without)
    # "A caller that asks for no lanes of B's hears exactly the same" was the
    # page's core, whose B lanes were optional arguments. It goes: the core
    # computes B whether or not its lanes are asked for (generator.h, "Layer
    # B through its plane whether or not its lanes were asked for"), and the
    # instrument asks for them whenever it asks for the heard pair.
    third = lambda x, f: bin_at(tail(x), 3 * f) / max(1e-9, bin_at(tail(x), f))
    b3, a3 = third(bl, e), third(al, c)
    check("layer B plays its own shape - a square under A's sine", 0.25 < b3 < 0.4 and a3 < 0.02, "B %.3f, A %.3f" % (b3, a3))
    null("A's picture has no square's third", not (0.25 < a3 < 0.4))
    peak = lambda x, a, b: float(np.max(np.abs(x[int(RATE * a):int(RATE * b)])))
    a_early, b_early, b_late = peak(al, 0.03, 0.05), peak(bl, 0.03, 0.05), float(np.max(np.abs(bl[-4096:])))
    check("and speaks with its own envelope - slow where A's is quick",
          a_early > 0.3 and b_early < b_late * 0.4, "40 ms in: A %.3f, B %.3f; B at the end %.3f" % (a_early, b_early, b_late))
    (_, _, _, _, bl2, _), _ = gen(kit, [x for x in base if x[1] != "set attackMs 400 1"], n)
    null("B given A's quick attack is not slow to speak", not (peak(bl2, 0.03, 0.05) < float(np.max(np.abs(bl2[-4096:]))) * 0.4))

    # --- the envelope a source reads, and B's voices let go ---
    # Was: core.envelope and core.voicesB.length read off the page's core; the
    # core's are generator_cpp's trailer, read where each run ends.
    life = [(0, "set releaseMs 50 1"), (0, "voices 0 none"), (0, "voices 1 " + voices((76, "xy")))]
    half = int(RATE / 2) // 128 * 128
    _, held = gen(kit, life, half)
    _, released = gen(kit, life + [(half, "voices 1 none")], 2 * half)
    check("the envelope a source reads includes layer B's notes", held["envelope"] > 0.5 and held["voicesB"] == 1, str(held))
    check("and layer B's voices are let go once their release is over",
          released["voicesB"] == 0 and released["envelope"] < 1e-3, str(released))
    _, early = gen(kit, life + [(half, "voices 1 none")], half + 256)
    null("a few milliseconds into the release B's voice is still there", early["voicesB"] == 1, str(early))

    # --- which layer a note goes to ---
    # Was: setMidiMode('poly'), the split menu, midi.layers.point = 60 and
    # notes played on the page's keyboard, then genSettings(layer).voices.
    # Here scope::Keyboard, its point at 60 as it starts; out of pitch order,
    # and 60, the point itself, among them, so `>` and `>=` disagree.
    _, ch = keyboard(kit, "mode poly", "layers split", "on 72 100", "on 59 100", "on 60 100", "on 48 100", "layers layer")
    notes = lambda chord: sorted(n for n, _ in chord)
    split, layered = ch[-2], ch[-1]
    check("a split sends notes below the point to A and the point upwards to B",
          notes(split[0]) == [48, 59] and notes(split[1]) == [60, 72], str(split))
    null("the point itself is not A's", 60 not in notes(split[0]))
    check("layered sends every note to both",
          notes(layered[0]) == [48, 59, 60, 72] and notes(layered[1]) == [48, 59, 60, 72], str(layered))
    null("the split's chords are not the layered ones", notes(split[0]) != notes(layered[0]))

    # --- each layer its own draw rule ---
    # Was: midi.draws written by hand on the page. Three notes a layer, so
    # lowest-two and highest-two pick different ones; a note not drawn is
    # handed over with the role u.
    _, ch = keyboard(kit, "mode poly", "layers split", "draw 0 2 lowest", "draw 1 2 highest",
                     *["on %d 100" % k for k in (52, 48, 55, 79, 72, 76)])
    drawn = lambda chord: sorted(n for n, role in chord if role != "u")
    check("layer A draws by its rule and layer B by its own", drawn(ch[-1][0]) == [48, 52] and drawn(ch[-1][1]) == [76, 79],
          str(ch[-1]))
    _, same = keyboard(kit, "mode poly", "layers split", "draw 0 2 lowest", "draw 1 2 lowest",
                       *["on %d 100" % k for k in (52, 48, 55, 79, 72, 76)])
    null("with B given A's rule, B draws its lowest two", drawn(same[-1][1]) == [72, 76], str(same[-1][1]))

    # --- A against B ---
    # Was: the page's lanes on ?brain=js after genSet and the pairing menu.
    # Here the instrument, natively: poly by its button, split, A against B,
    # C3 and G3 below the point and E5 above, X and Y read by their bins.
    # On a plain sine with the picture still (a code as icode_of writes one),
    # not Harmonic tone: its partials put a little of A's lane at E5, five
    # times C3 less a few hertz, over the suite's one-per-cent floor.
    import base64, json
    sine = base64.b64encode(json.dumps({"v": 4, "shape": "sine", "pictureAmount": 0}).encode()).decode().rstrip("=")
    def against(pair):
        lines = [["make", 48000, 128, sine], ["click", "midiPoly"], ["click", "tuneEqual"],
                 ["control", "midiLayers", "split"], ["control", "midiLayerPair", pair]] \
            + [["midi", 0x90, k, 100] for k in (48, 55, 76)] + [["block", 128]] * 160
        blocks = [l for l in kit.instrument(lines) if l.startswith("block ")][-128:]
        lane = lambda k: np.array([float(v) for l in blocks for v in l.split()[1:][(2 + k) * 128:(3 + k) * 128]])
        x, y, bx = lane(0), lane(1), lane(2)
        return ([bin_at(x, f, 48000) for f in (c, g, e)], [bin_at(y, f, 48000) for f in (c, g, e)], float(np.max(np.abs(bx))))
    x, y, beyond = against("against")
    xtop = max(x[0], 1e-9)
    ok = lambda x, y: x[0] > 0.03 and x[1] > 0.03 and x[2] < xtop * 0.01 and y[2] > 0.03 and y[0] < xtop * 0.01 and y[1] < xtop * 0.01
    check("A against B is one pair: both of A's drawn notes on X, B's on Y, and nothing past it",
          ok(x, y) and beyond == 0, "X %s, Y %s, past it %g" % (np.round(x, 4), np.round(y, 4), beyond))
    ex, ey, _ = against("each")
    null("drawn a figure each, A's pair is not A against B", not ok(ex, ey), "X %s, Y %s" % (np.round(ex, 4), np.round(ey, 4)))
