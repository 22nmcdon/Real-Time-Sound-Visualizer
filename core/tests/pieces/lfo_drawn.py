"""The drawn LFOs (19 Nov), on the core: web/docs/lfo-drawn.md's tests.

Today's five shapes play through lfoStep's old path, untouched, and each has
a drawn twin the editor adopts on its first edit. The twins are held to that
path here, sample for sample, at three rates and two sample rates, each LFO
from its own Random stream of one seed (core/tests/tools/lfo_cpp.cpp runs the
two side by side): the saws, the square and Random to the bit, the sine
within 1e-12, the triangle within the core's asin error. Then the rest of the
design: a random point's reach, a drawn shape's lines changing at the sample,
Phase, the three ways of starting again through the instrument whole, the
adoption with no step, and the shape's text read and written back. Each check
has its null, a known-wrong value seen red.
"""
import json, math

TWINS = {
    "sine": "1;.25,1,s;.75,-1,s",
    "triangle": "1;.25,1,l;.75,-1,l",
    "ramp": "1;0,-1,l;1,1,l",
    "square": "1;0,.9,l;.5,.9,l;.5,-.9,l;1,-.9,l",
    "random": "1;0,1,h,r",
}
# How near each twin must be: the saws, the square and Random are the same arithmetic; the
# sine's S is a cosine, not a sine; the triangle's asin(sin) is off a straight line at its peaks.
WITHIN = {"sine": 1e-12, "triangle": 1e-7, "ramp": 0, "square": 0, "random": 0}
RATES = (0.01, 0.37, 7.9)
SAMPLE_RATES = (44100, 48000)


def scenario(**kw):
    return "\n".join("%s %s" % (k, v) for k, v in kw.items())


def run(kit):
    check, null = kit.check, kit.null

    def pair(shape, text, hz, rate, phase=0, seed=7):
        # Two and a bit cycles, and at least ten seconds, so Random crosses its wrap.
        n = int(max(10, 2.2 / hz) * rate) if hz >= 0.05 else int(1.2 / hz * rate)
        w = kit.run("lfo_cpp", scenario(shape=shape, text=text, hz=hz, rate=rate, n=n, seed=seed, phase=phase), "pair").split()
        return float(w[1]), int(w[2])

    def values(text, hz=0.37, rate=48000, n=48000, shape="drawn", seed=7, **kw):
        out = kit.run("lfo_cpp", scenario(shape=shape, text=text, hz=hz, rate=rate, n=n, seed=seed, **kw), "run").split("\n")
        segs = [int(v) for v in out[0].split()[1:]]
        return [float.fromhex(v) for v in out[1:] if v], segs

    # --- today's five through lfoStep, beside their twins through the drawn path ---
    worst, wrong = {}, []
    for shape, text in TWINS.items():
        for hz in RATES:
            for rate in SAMPLE_RATES:
                d, at = pair(shape, text, hz, rate)
                worst[shape] = max(worst.get(shape, 0), d)
                if not d <= WITHIN[shape]: wrong.append("%s at %r Hz, %d: %r at sample %d" % (shape, hz, rate, d, at))
    check("today's five beside their drawn twins, at 0.01, 0.37 and 7.9 Hz and 44.1 and 48 kHz: the saw, square and Random "
          "to the bit, the sine within 1e-12, the triangle within 1e-7",
          not wrong and worst["ramp"] == 0 and worst["square"] == 0 and worst["random"] == 0,
          "; ".join(wrong[:3]) or ", ".join("%s %.3g" % kv for kv in worst.items()))
    # The nulls the design names: the sine drawn straight, the random point rolled a line
    # early (its line a curve, so the level is drawn as the line towards it starts), and a
    # quarter of Phase on the twin alone.
    straight, _ = pair("sine", "1;.25,1,l;.75,-1,l", 0.37, 48000)
    early, _ = pair("random", "1;0,1,s,r", 0.37, 48000)
    quarter, _ = pair("sine", TWINS["sine"], 0.37, 48000, phase=0.25)
    null("the sine drawn straight is off by more than a fifth", straight > 0.2, "%.3f" % straight)
    null("the random point rolled a line early is not today's Random", early > 0.1, "%.3f" % early)
    # pair() gives the Phase to both; the twin alone at a quarter is the legacy sine against a cosine.
    alone, _ = pair("sine", "1;.5,1,s;1,-1,s", 0.37, 48000)
    null("a quarter of a cycle off is off by more than one", alone > 1, "%.3f" % alone)
    check("Phase moves today's sine and its twin alike: a quarter on both is still within 1e-12", quarter <= 1e-12, "%.3g" % quarter)

    # --- reach: a random point's height is how far it lands, either way of nought ---
    legacy, _ = values("", shape="random", n=480000, hz=7.9)
    full, _ = values("1;0,1,h,r", n=480000, hz=7.9)
    part, _ = values("1;0,.3,h,r", n=480000, hz=7.9)
    none, _ = values("1;0,0,h,r", n=480000, hz=7.9)
    levels = sorted(set(legacy))
    check("full reach is today's Random to the bit, %d levels over ten seconds" % len(levels), full == legacy and len(levels) > 50)
    check("a reach of 0.3 is today's levels times 0.3, to the bit, and never past it",
          part == [v * 0.3 for v in legacy] and max(abs(v) for v in part) <= 0.3 and max(abs(v) for v in part) > 0.25)
    null("a reach of nought is still, and so is not today's Random", all(v == 0 for v in none) and none != legacy)
    # The sign of a random point's height is kept in its text, and its reach is the size alone.
    neg, _ = values("1;0,-.3,h,r", n=480000, hz=7.9)
    check("a random point drawn below nought lands as one drawn above it", neg == part)

    # --- a drawn shape's lines, to the sample ---
    # 5 Hz at 48 kHz is 9600 samples a cycle; the points sit between samples, so which
    # sample first passes each is not a matter of rounding: 0.2501 (2400.96 steps) is passed
    # by sample 2400, the 2401st step; 0.50006 by 4800, and 0.75005 by 7200.
    shape = "1;0,-1,l;.2501,1,h;.50006,.5,s;.75005,0,m.8"
    v, segs = values(shape, hz=5, rate=48000, n=9599)
    changes = [i for i in range(1, len(segs)) if segs[i] != segs[i - 1]]
    held = v[2400:4800]
    check("each line starts at the sample its point is passed: 2400, 4800 and 7200 of a 9600-sample cycle",
          changes == [2400, 4800, 7200] and segs[0] == 0, str(changes))
    check("a held line holds its point's level to the next point, and the straight one before it rises to it",
          all(x == 1 for x in held) and len(held) == 2400 and v[1199] < 0.01 and v[1199] > -0.01 and v[2399] < 1,
          "%r %r" % (v[1199], v[2399]))
    # The curve by its midpoint: half-way along (sample 8400) it is 0.8 of the way from 0 to -1.
    check("a curve with its midpoint at 0.8 is 0.8 of the way down half-way along", abs(v[8399] - (-0.8)) < 1e-3, "%r" % v[8399])
    _, shifted = values("1;0,-1,l;.2499,1,h;.50006,.5,s;.75005,0,m.8", hz=5, rate=48000, n=9599)
    moved = [i for i in range(1, len(shifted)) if shifted[i] != shifted[i - 1]]
    null("a point two ten-thousandths earlier is passed at another sample", moved[0] != 2400, str(moved))

    # --- adopting: today's shape swapped for its twin mid-cycle, with no step ---
    steps = {}
    # At 7.9 Hz, so Random has drawn a dozen levels before it is adopted, and holds one then.
    for shape in ("sine", "ramp", "square", "random"):
        base, _ = values("", shape=shape, hz=7.9, n=96000)
        took, _ = values(TWINS[shape], shape=shape, hz=7.9, n=96000, adopt=50000)
        steps[shape] = max(abs(a - b) for a, b in zip(base, took))
    check("the twin taken up mid-cycle carries on as today's would have: no step over 1e-12, Random's held level kept",
          max(steps.values()) <= 1e-12, str(steps))
    base, _ = values("", shape="sine", hz=0.37, n=96000)
    wrong_twin, _ = values(TWINS["triangle"], shape="sine", hz=0.37, n=96000, adopt=50000)
    null("the triangle's twin taken up while the sine plays steps", max(abs(a - b) for a, b in zip(base, wrong_twin)) > 0.05)

    # --- starting again, through the instrument whole ---
    def code(starts, extra=None):
        import base64
        fields = {"l0s": "drawn", "l0m": TWINS["ramp"], "l0r": 37, "midiMode": "mono"}
        if starts: fields["l0t"] = starts
        if extra: fields.update(extra)
        return base64.b64encode(json.dumps(fields).encode()).decode().rstrip("=")

    def phases(starts, notes, extra=None):
        # Half a second, then each of `notes` (on, or off) at the top of a block of 128.
        lines = [["make", 48000, 128, code(starts, extra)]] + [["block", 4800, 100000]] * 5
        for n in notes:
            lines += [["midi", 0x90 if n > 0 else 0x80, abs(n), 100 if n > 0 else 0], ["block", 128, 100000], ["lfos"]]
            lines += [["block", 4800, 100000]] * 3
        out = [l.split() for l in kit.instrument(lines) if l.startswith("lfos")]
        return [float.fromhex(w[1]) for w in out], [int(w[3]) for w in out]

    one = 2 * math.pi * 0.37 * 128 / 48000 * 1.0000001  # where 128 samples from nought leave the phase
    each, drawn = phases("n", [60, 64, -60, -64, 67])
    phrase, _ = phases("p", [60, 64, -60, -64, 67])
    free, _ = phases("", [60, 64, -60, -64, 67])
    check("Each note starts it again on every key: the phase is 128 samples on at each of three notes", all(p < one for p in [each[0], each[1], each[4]])
          and all(drawn), str(each))
    check("Each phrase starts it again on the first key of a phrase and not on a key struck while one is held",
          phrase[0] < one and phrase[1] > one and phrase[4] < one, str(phrase))
    null("Free never starts again", all(p > one for p in free), str(free))

    # --- the text, read and written back ---
    texts = ["1;.25,1,s;.75,-1,s", "1;0,-.6,m.78;.125,.85,l;.375,.85,m.3;.75,-.2,s;.875,-.8,h,r", "1;0,1,h,r",
             "1;0,.9,l;.5,.9,l;.5,-.9,l;1,-.9,l", "1;" + ";".join("%s,%s,l" % (("%g" % (k / 32)).lstrip("0") or "0", "1" if k % 2 else "-1") for k in range(32))]
    bad = ["", "1", "2;0,1,l", "1;0,1,q", "1;0,1", "1;0,1,l,x", "1;0,1,l;", "1;a,1,l",
           "1;" + ";".join("0,0,l" for _ in range(33))]
    out = kit.run("lfo_cpp", "\n".join(texts + bad), "text").split("\n")
    read = [l.split(" ", 2) for l in out if l]
    good, refused = read[:len(texts)], read[len(texts):]
    # The empty text is no line to the tool; the eight others are its eight lines.
    check("every shape text the editor writes reads back as itself, 32 points the most",
          all(w[0] == "ok" and w[2] == t for w, t in zip(good, texts)) and good[-1][1] == "32", str(good[:2]))
    check("a text that does not read is refused whole: no version, another version, an unknown law, a missing level, a fifth field, an empty point, a number that is not one, 33 points",
          len(refused) == len(bad) - 1 and all(w[0] == "no" and w[1] == "0" for w in refused), str(refused))
    padded = kit.run("lfo_cpp", "1;.250,1,s;.75,-1,s", "text").split()
    null("a text written another way reads as the same shape but does not write back as itself",
         padded[0] == "ok" and padded[2] != "1;.250,1,s;.75,-1,s", str(padded))
