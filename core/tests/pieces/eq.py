"""The EQ (17 Nov), on the core: its three bands against Web Audio's own
BiquadFilterNode, where it sits in the plane, a line kept a line, an EQ at
nought the same to the bit as none, and each hand's own.

The bands are the node's (the Audio EQ Cookbook, the shelves' slope one), so
the node is the reference, as it was for the page's old biquad: the core's
coefficients (functions_cpp's `eqBand`) are turned into a response here and
held to the node's `getFrequencyResponse` in the browser to a ten-thousandth
of a decibel, at every band, gains from -12 to +12 dB, frequencies across
each knob's range and two rates. The mid's width is in octaves on the knob
and Q to the node, by the analog relation (functions_cpp's `eqQ`); the null
is the width handed to the node as Q unconverted.

Where it sits, by `planeRun eqat=` (functions_cpp): the same three bands put
outside the plane, before it or after it, with the plane's own EQ at nought.
With the phaser sweeping, the chorus and the delay on, the plane's own EQ is
the bands before them, under each of the six orders, and not after them;
with the Plane's twist on, it is the bands after the twist and not before.
Each "not" is the null of its check, and each holds only because the
modules around it are not linear and time-invariant together - which is why
the phaser sweeps and the twist bends.
"""
import json, math, os

import numpy as np

CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

# The node's response, every case at once, in an offline context of each rate.
NODE = """async (cases) => {
  const out = [];
  for (const c of cases) {
    const ctx = new OfflineAudioContext(1, 128, c.rate);
    const f = ctx.createBiquadFilter();
    f.type = c.type; f.frequency.value = c.hz; f.gain.value = c.db; f.Q.value = c.q;
    const hz = new Float32Array(c.probes), mag = new Float32Array(hz.length), ph = new Float32Array(hz.length);
    f.getFrequencyResponse(hz, mag, ph);
    out.push(Array.from(mag));
  }
  return out;
}"""


def response(c, hz, rate):
    z = np.exp(-1j * 2 * np.pi * np.asarray(hz, dtype=float) / rate)
    b0, b1, b2, a1, a2 = c
    return np.abs((b0 + b1 * z + b2 * z * z) / (1 + a1 * z + a2 * z * z))


def node_responses(cases):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=CHROME)
        p = b.new_page()
        p.goto("about:blank")
        out = p.evaluate(NODE, cases)
        b.close()
    return out


# Every field planeRun reads, at the plane's defaults (core_tests.py's
# PLANE_DEFAULTS): a field left out reads as nought, which for a scale is a
# plane that silences everything - how this file's first draft passed every
# check against itself and failed every null.
DEFAULTS = dict(rate=44100.0, samples=6000, planeMirror=0, planeRadius=0.4, planeOS=2, planeLimit=0,
                planeScaleX=1, planeScaleY=1, planeShear=0, planeTwist=0, planeSnap=0,
                delayMix=0, delayMs=375, delayFeedback=0.35, delayPingPong=0, chorusMix=0, chorusRate=0.6,
                delayTone=1, delayLowCut=0, delayWidth=1, delayWow=0,
                bDelayTone=1, bDelayLowCut=0, bDelayWidth=1, bDelayWow=0,
                chorusDepthMs=3, chorusMs=12, chorusFeedback=0, inp=0, bown=0, bRadius=0.4, bScaleX=1, bScaleY=1,
                bDelayMs=375, bDelayFeedback=0.35, bChorusRate=0.6, bChorusDepthMs=3, bChorusMs=12,
                phaserRate=0.3, phaserDepth=0.7, phaserFeedback=0.3, bPhaserRate=0.3, bPhaserDepth=0.7,
                bPhaserFeedback=0.3, reverbSize=0.4, reverbTone=0.6, reverbPreMs=10, bReverbSize=0.4,
                bReverbTone=0.6, bReverbPreMs=10, eqLowHz=160, eqMidHz=1000, eqMidWidth=1, eqHighHz=4000,
                bEqLowHz=160, bEqMidHz=1000, bEqMidWidth=1, bEqHighHz=4000, ev="",
                # The EQ's switch (17 Nov), on here so the bands are what is under test; off is tested below.
                eqOn=1, bEqOn=1)


def plane_run(kit, **p):
    """planeRun with every field named, so a band not given is out (gain nought)."""
    base = dict(DEFAULTS)
    base.update(p)
    v = kit.floats("functions_cpp", "planeRun " + " ".join("%s=%s" % (k, v if isinstance(v, str) else repr(v))
                                                          for k, v in base.items()))
    return np.array(v).reshape(-1, 4)


def run(kit):
    check, null = kit.check, kit.null
    db = lambda m: 20 * np.log10(np.maximum(1e-12, np.asarray(m, dtype=float)))
    types = ["lowshelf", "peaking", "highshelf"]
    ranges = [(40, 640), (125, 8000), (1000, 16000)]

    # --- the bands against the node ---
    cases = []
    for rate in (44100, 48000):
        for band in range(3):
            lo, hi = ranges[band]
            for hz in (lo, math.sqrt(lo * hi), hi):
                for gain in (-12, -6, -1.5, 0.1, 3, 12):
                    for width in ((0.2, 1, 4) if band == 1 else (1,)):
                        cases.append((band, gain, hz, width, rate))
    calls = ["eqBand %d %r %r %r %r" % c for c in cases] + ["eqQ %r" % c[3] for c in cases]
    v = kit.floats("functions_cpp", "\n".join(calls))
    coefs = [v[5 * i:5 * i + 5] for i in range(len(cases))]
    qs = v[5 * len(cases):]
    probes = [20, 50, 100, 160, 300, 700, 1000, 2000, 4000, 8000, 12000, 16000, 20000]
    want = node_responses([{"type": types[b], "hz": hz, "db": g, "q": q, "rate": r, "probes": probes}
                           for (b, g, hz, w, r), q in zip(cases, qs)])
    worst = max(float(np.abs(db(response(c, probes, r)) - db(m)).max()) for (_, _, _, _, r), c, m in zip(cases, coefs, want))
    check("each band is Web Audio's own filter, to 0.0001 dB: %d filters at %d frequencies, two rates"
          % (len(cases), len(probes)), worst < 1e-4, "worst %.2e dB" % worst)
    # The null: the mid's width given to the node as its Q, unconverted.
    mids = [(i, c) for i, c in enumerate(cases) if c[0] == 1 and c[3] != 1]
    wrong = node_responses([{"type": "peaking", "hz": hz, "db": g, "q": w, "rate": r, "probes": probes}
                            for _, (b, g, hz, w, r) in mids])
    off = max(float(np.abs(db(response(coefs[i], probes, c[4])) - db(m)).max()) for (i, c), m in zip(mids, wrong))
    null("the same comparison fails against the width handed to the node as Q", off > 0.01, "%.3f dB" % off)
    # And what each band does, by its own numbers: the shelf's full gain far
    # past its corner and half of it at the corner, the mid's at its centre.
    low = coefs[cases.index((0, 12, 160.0, 1, 44100))] if (0, 12, 160.0, 1, 44100) in cases else None
    c160 = kit.floats("functions_cpp", "eqBand 0 12 160 1 44100\neqBand 1 6 1000 1 44100\neqBand 2 -6 4000 1 44100")
    lowc, midc, highc = c160[0:5], c160[5:10], c160[10:15]
    reads = (float(db(response(lowc, [20], 44100))[0]), float(db(response(lowc, [160], 44100))[0]),
             float(db(response(midc, [1000], 44100))[0]), float(db(response(highc, [16000], 44100))[0]))
    check("a low shelf of +12 dB at 160 Hz gives about +12 at 20 Hz and +6 at its corner; a mid of +6 gives +6 at its "
          "centre; a high shelf of -6 at 4 kHz about -6 at 16 kHz", abs(reads[0] - 12) < 0.5 and abs(reads[1] - 6) < 0.1
          and abs(reads[2] - 6) < 1e-9 and abs(reads[3] + 6) < 0.6, "%.3f %.3f %.3f %.3f" % reads)
    null("and the low shelf is not the high: +12 at 160 Hz reads near nought at 16 kHz",
         abs(float(db(response(lowc, [16000], 44100))[0])) < 0.5)

    # --- where it sits in the plane ---
    eq = dict(eqLow=4, eqLowHz=200, eqMid=-5, eqMidHz=900, eqMidWidth=0.8, eqHigh=6, eqHighHz=3000)
    outside = dict(xLow=4, xLowHz=200, xMid=-5, xMidHz=900, xMidWidth=0.8, xHigh=6, xHighHz=3000)
    trio = dict(phaserMix=0.8, phaserRate=5, phaserDepth=0.6, phaserFeedback=0.5, chorusMix=0.5, chorusRate=2,
                chorusDepthMs=3, chorusMs=12, delayMix=0.4, delayMs=20, delayFeedback=0.5)
    before, after = [], []
    for order in range(6):
        own = plane_run(kit, fxOrder=order, **trio, **eq)
        pre = plane_run(kit, fxOrder=order, eqat="pre", **trio, **outside)
        post = plane_run(kit, fxOrder=order, eqat="post", **trio, **outside)
        before.append(float(np.abs(own - pre).max()))
        after.append(float(np.abs(own - post).max()))
    check("with the phaser, chorus and delay on, the EQ is before all three, under every one of the six orders",
          max(before) < 1e-9, "worst %.2e" % max(before))
    null("and not after them, under any order", min(after) > 1e-3, "nearest %.2e" % min(after))
    tw = dict(planeTwist=1.5, planeOS=1)
    own = plane_run(kit, **tw, **eq)
    pre = plane_run(kit, eqat="pre", **tw, **outside)
    post = plane_run(kit, eqat="post", **tw, **outside)
    a, b = float(np.abs(own - post).max()), float(np.abs(own - pre).max())
    check("with the Plane's twist on, the EQ is after the Plane", a < 1e-9, "%.2e" % a)
    null("and not before it", b > 1e-3, "%.2e" % b)

    # --- an EQ at nought is no EQ, to the bit ---
    plain = plane_run(kit, **trio)
    zeros = plane_run(kit, **trio, **dict(eq, eqLow=0, eqMid=0, eqHigh=0))
    check("an EQ with its gains at nought, its frequencies and width set, is the same to the bit as none",
          np.array_equal(plain, zeros))
    tenth = plane_run(kit, **trio, **dict(eq, eqLow=0, eqMid=0, eqHigh=0.1))
    null("and a tenth of a decibel on one band is not", not np.array_equal(plain, tenth),
         "%.2e" % float(np.abs(plain - tenth).max()))
    # --- its switch, a field (17 Nov): off is no EQ, to the bit, whatever its curve keeps ---
    off = plane_run(kit, **trio, **dict(eq, eqOn=0))
    check("an EQ switched off with its curve kept - every band set - is the same to the bit as none, with the trio on",
          np.array_equal(plain, off))
    alone = plane_run(kit, **dict(eq, eqOn=0)), plane_run(kit)
    check("and alone, the same to the bit as the plane with nothing on", np.array_equal(alone[0], alone[1]))
    on = plane_run(kit, **trio, **eq)
    null("and the same curve switched on is not", not np.array_equal(plain, on), "%.2e" % float(np.abs(plain - on).max()))
    # The upper hand's own switch: its own EQ off while the lower's is on - its pair as with B's own bands at nought.
    beq_off = plane_run(kit, bown=1, town=16, **eq, bEqLow=-6, bEqLowHz=300, bEqOn=0)
    beq_flat = plane_run(kit, bown=1, town=16, **eq, bEqLow=0, bEqLowHz=300, bEqOn=1)
    beq_in = plane_run(kit, bown=1, town=16, **eq, bEqLow=-6, bEqLowHz=300, bEqOn=1)
    a_ref = plane_run(kit, eqat="pre", **outside)
    check("the upper hand's own switched off is no EQ on its pair, to the bit, the lower's still in on its own",
          np.array_equal(beq_off[:, 2:], beq_flat[:, 2:]) and float(np.abs(beq_off[:, :2] - a_ref[:, :2]).max()) < 1e-9,
          "%.2e %.2e" % (float(np.abs(beq_off[:, 2:] - beq_flat[:, 2:]).max()), float(np.abs(beq_off[:, :2] - a_ref[:, :2]).max())))
    null("and its own switched on is its bands", float(np.abs(beq_in[:, 2:] - beq_flat[:, 2:]).max()) > 1e-3)

    # --- a line stays a line ---
    line = plane_run(kit, inp=3, **eq)[:, :2]
    check("the same bands on both channels: a line (the same burst in X and Y) stays a line, to the bit",
          np.array_equal(line[:, 0], line[:, 1]) and float(np.abs(line[:, 0]).max()) > 0.1)
    opened = plane_run(kit, inp=3, phaserMix=1, phaserRate=3, phaserDepth=0.7, phaserFeedback=0.3, **eq)[:, :2]
    null("where the phaser, in quadrature, opens it", not np.array_equal(opened[:, 0], opened[:, 1]))
    # And the bands moved it at all: the line through the EQ is not the line without it.
    bare = plane_run(kit, inp=3, phaserMix=0)[:, :2]
    null("and the EQ changed the line it kept", float(np.abs(bare[:, 0] - line[:, 0]).max()) > 1e-3)

    # --- each hand's own ---
    beq = dict(bEqLow=-6, bEqLowHz=300, bEqMid=3, bEqMidHz=2000, bEqMidWidth=2, bEqHigh=-3, bEqHighHz=6000)
    bout = dict(xLow=-6, xLowHz=300, xMid=3, xMidHz=2000, xMidWidth=2, xHigh=-3, xHighHz=6000)
    mine = plane_run(kit, bown=1, town=16, **eq, **beq)
    ref_b = plane_run(kit, eqat="pre", **bout)
    ref_a = plane_run(kit, eqat="pre", **outside)
    shared = plane_run(kit, bown=1, town=15, **eq, **beq)
    e_own = float(np.abs(mine[:, 2:] - ref_b[:, 2:]).max())
    e_a = float(np.abs(mine[:, :2] - ref_a[:, :2]).max())
    e_sh = float(np.abs(shared[:, 2:] - ref_a[:, 2:]).max())
    check("with the EQ the upper hand's own (timeOwn 16), its pair goes through its own bands and the lower's through A's",
          e_own < 1e-9 and e_a < 1e-9, "%.2e %.2e" % (e_own, e_a))
    check("and with every other module its own but not the EQ, the upper hand's pair goes through A's bands",
          e_sh < 1e-9, "%.2e" % e_sh)
    null("which are not B's", float(np.abs(shared[:, 2:] - ref_b[:, 2:]).max()) > 1e-3)
