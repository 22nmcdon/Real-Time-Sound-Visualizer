"""The picture's filter, on the core: its law against the cookbook's response,
Butterworth at resonance nought, a low pass rounding a square, primed at the
window's left edge, the lag lane filtered too, a hidden lane left alone, and
a source sweeping the cutoff.

These were filtertest.py's on ?brain=js until stage 5's step 3, batch 4 (13
Nov): there the page's own `biquadCoefficients` against the browser's
BiquadFilterNode (`getFrequencyResponse`), and the page's `capture()` over the
page's own generator and a stubbed source, with LFO 1 held by hand and the
page's `applyModMatrix` stepped for the sweep. Here the core's: capture.h's
`biquadCoefficients` (functions_cpp's `biquad`) against the Audio EQ
Cookbook's response written out below, as the Web Audio specification states
it - Q in decibels for the low and high pass, linear for the band pass and
notch - since there is no browser to ask; capture_cpp's capture of the same
signals, read whole (`dump`, `lane`); and matrix_cpp's scripted source held
at a value on the screen's own `filter.cutoff` (screen.h), read back through
filterNow (its `filter` command).

The page's capture() is the face and stays after the engine goes; parity's
capture section holds it to capture.h, so these checks bind what the site
draws through that.
"""
import math
import numpy as np

RATE = 48000


def step_for(hz):
    """A cutoff slider step from hertz: cutoffHz is 20 * 1000^(step / 1000)."""
    return 1000 * math.log(hz / 20) / math.log(1000)


def response(c, hz, rate):
    """|H| of a biquad b0 b1 b2 a1 a2 at a frequency."""
    z = np.exp(-1j * 2 * np.pi * np.asarray(hz) / rate)
    b0, b1, b2, a1, a2 = c
    return np.abs((b0 + b1 * z + b2 * z * z) / (1 + a1 * z + a2 * z * z))


def cookbook(kind, hz, q, rate, probes, q_in_db=None):
    """The Web Audio specification's BiquadFilterNode response, written out:
    the Audio EQ Cookbook with Q in decibels for lowpass and highpass."""
    if q_in_db is None: q_in_db = kind in ("lowpass", "highpass")
    Q = 10 ** (q / 20) if q_in_db else q
    w0 = 2 * math.pi * min(hz, rate / 2 * 0.9999) / rate
    alpha, cw = math.sin(w0) / (2 * Q), math.cos(w0)
    if kind == "lowpass": b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
    elif kind == "highpass": b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
    elif kind == "bandpass": b = [alpha, 0, -alpha]
    else: b = [1, -2 * cw, 1]
    a = [1 + alpha, -2 * cw, 1 - alpha]
    return response([b[0] / a[0], b[1] / a[0], b[2] / a[0], a[1] / a[0], a[2] / a[0]], probes, rate)


def run(kit):
    check, null = kit.check, kit.null
    db = lambda m: 20 * np.log10(np.maximum(1e-9, m))

    def coefficients(calls):
        v = kit.floats("functions_cpp", "\n".join(calls))
        return [v[i:i + 5] for i in range(0, len(v), 5)]

    # filtertest :116: every type, five cutoffs, four resonances, seven probes.
    rate = 44100
    probes = np.array([30, 100, 440, 1000, 3000, 9000, 18000], dtype=float)
    cases = []
    for kind in ("lowpass", "highpass", "bandpass", "notch"):
        for step in (100, 300, 566, 800, 980):
            for res in (0, 25, 60, 100):
                hz = 20 * 1000 ** (step / 1000)
                q = -3.0103 + res / 100 * 27 if kind in ("lowpass", "highpass") else 0.5 + res / 100 * 19.5
                cases.append((kind, hz, q))
    got = coefficients(["biquad %s %r %r %r" % (k, hz, q, rate) for k, hz, q in cases])
    worst = max(np.abs(db(response(c, probes, rate)) - db(cookbook(k, hz, q, rate, probes))).max()
                for (k, hz, q), c in zip(cases, got))
    check("agreement with the cookbook's response within a tenth of a decibel, %d points" % (len(cases) * len(probes)),
          worst < 0.1, "%.2e dB" % worst)
    # The null: the same response with the low and high pass's Q read
    # linearly, the trap this page's band crossovers sat in.
    linear = max(np.abs(db(response(c, probes, rate)) - db(cookbook(k, hz, q, rate, probes, q_in_db=False))).max()
                 for (k, hz, q), c in zip(cases, got) if k == "lowpass")
    null("the low pass's Q read linearly disagrees", linear > 0.1, "%.1f dB" % linear)

    # :129, :131: the corner of a 1 kHz low pass at resonance nought, and with
    # a linear 0.707 put into the decibel slot.
    good, wrong = coefficients(["biquad lowpass 1000 -3.0103 44100", "biquad lowpass 1000 0.707 44100"])
    g, w = float(db(response(good, 1000, rate))), float(db(response(wrong, 1000, rate)))
    check("resonance nought is maximally flat: -3.01 dB at the corner", abs(g + 3.0103) < 0.01, "%.3f dB" % g)
    check("and the linear value in a dB slot would not be: +0.71", abs(w - 0.71) < 0.05, "%.3f dB" % w)
    null("the two are not the same", abs(g - w) > 1)

    def capture(lines, lane=None):
        out = kit.run("capture_cpp", "\n".join(["run", "rate %d" % RATE, "signal %d" % RATE] + lines
                                               + ["cap", "lane %d" % lane if lane is not None else "dump", "end"]))
        row = [l for l in out.split("\n") if l.startswith("lane " if lane is not None else "dump")][0]
        v = np.array([float(x) for x in row.split()[1:]])
        return v if lane is not None else (v[:len(v) // 2], v[len(v) // 2:])

    # :170, :175: a square at 220 Hz, 50 ms a division (`tb 6` is 10 ms; the
    # page's state.timebase = 6), its steepest sample step open and under a
    # 200 Hz low pass. Not total variation: smoothing a step spreads it out
    # without changing how far it travels.
    steepest = lambda x: float(np.abs(np.diff(x)).max())
    square = ["add 0 square 0.8 220 0", "add 1 square 0.8 220 0", "tb 6"]
    open_edge = steepest(capture(square)[0])
    closed_edge = steepest(capture(square + ["filter lowpass %r 0" % step_for(200)])[0])
    check("the signal really is a square", open_edge > 0.5, "steepest sample step %.3f" % open_edge)
    sine_edge = steepest(capture(["add 0 sine 0.8 220 0", "add 1 sine 0.8 220 0", "tb 6"])[0])
    null("a sine is not", sine_edge <= 0.5, "%.3f" % sine_edge)
    check("a low pass really rounds the corners off it", closed_edge < open_edge * 0.1,
          "steepest edge %.4f -> %.4f" % (open_edge, closed_edge))
    wide = steepest(capture(square + ["filter lowpass %r 0" % step_for(20000)])[0])
    null("a low pass at 20 kHz does not", wide >= open_edge * 0.1, "%.4f" % wide)

    # :195, :198: a resonant low pass at 300 Hz on a 220 Hz sine, primed at
    # the window's left edge. The null is the same coefficients run from
    # silence over the unfiltered window, here: it rings while it settles.
    # The source holds the window and no more (`cap 4800`), so the fetch
    # starts where the window does: with the search span in front of it, as
    # the page's check ran, the ringing settled off screen and a filter left
    # unprimed passed (the mutation pass found it). And the sine stands on an
    # offset of a half: a pure sine starting near nought gives a filter
    # started from silence nothing to ring at, so that passed too. Each is
    # read about where it settles (the mean of its last 2000 samples), over
    # a period and more of 220 Hz at each end.
    sine = ["add 0 sine 0.3 220 0", "add 0 dc 0.5", "add 1 sine 0.3 220 0", "tb 6", "cap 4800"]
    lp = "filter lowpass %r 80" % step_for(300)
    x = capture(sine + [lp])[0]
    peak = lambda a: float(np.abs(a).max())
    ends = lambda a: (peak(a[:256] - a[-2000:].mean()), peak(a[-256:] - a[-2000:].mean()))
    head, tail = ends(x)
    check("the first samples are not louder than the rest", head < tail * 1.3, "head %.4f against %.4f" % (head, tail))
    check("and nothing is NaN", bool(np.isfinite(x).all()) and len(x) > 1000, "%d samples" % len(x))
    raw = capture(sine)[0]
    c = coefficients(["biquad lowpass %r %r %r" % (20 * 1000 ** (step_for(300) / 1000), -3.0103 + 0.8 * 27, RATE)])[0]
    y, s1, s2 = np.zeros(len(raw)), 0.0, 0.0
    for i, v in enumerate(raw):     # transposed direct form II from silence
        out = c[0] * v + s1
        s1 = c[1] * v - c[3] * out + s2
        s2 = c[2] * v - c[4] * out
        y[i] = out
    null("the same filter started from silence over the window rings at its edge", ends(y)[0] >= ends(y)[1] * 1.3,
         "head %.4f against %.4f" % ends(y))

    # :215: the lag lane read from the buffer the filter wrote. A sine at 220
    # Hz under a 120 Hz low pass, with a lag of a millisecond.
    lag = ["add 0 sine 0.5 220 0", "add 1 sine 0.5 220 0", "tb 6", "lag 1"]
    sig, delayed = capture(lag + ["filter lowpass %r 0" % step_for(120)])
    # The page asked only that the two lanes agree, which two unfiltered lanes
    # also do (a filter skipped whenever there is a lag passed it, in the
    # mutation pass): so the signal lane is required to be filtered as well,
    # under half the 0.5 put in.
    _, plain_delayed = capture(lag)
    check("the lag lane is filtered too", abs(peak(sig) - peak(delayed)) < peak(sig) * 0.25 + 1e-6
          and peak(sig) < 0.25, "%.4f against %.4f, from 0.5" % (peak(sig), peak(delayed)))
    null("the filtered signal against the unfiltered lag lane differs", abs(peak(sig) - peak(plain_delayed)) >= peak(sig) * 0.25,
         "%.4f against %.4f" % (peak(sig), peak(plain_delayed)))

    # :300, :301: four lanes (the band split's), a square on each, a low pass
    # at 200 Hz, lane 1 hidden: the shown lanes filtered, the hidden one the
    # raw signal to the bit. On the page this stubbed the source's window; here
    # capture_cpp's own buffers, the same fixed signal. Triggered on the
    # hidden lane, so the hidden and raw windows start at the same sample:
    # the page compared one sample of windows whose trigger read a filtered
    # lane 0, which a change to the cutoff's law moved under it (the mutation
    # pass); the lanes are compared whole now.
    four = ["chans 4", "lanes 1", "trig 1"] + ["add %d square 0.8 %r 0" % (k, RATE / (2 * math.pi * 50)) for k in range(4)] + ["tb 6"]
    f200 = "filter lowpass %r 0" % step_for(200)
    lit = [capture(four + [f200], k) for k in (0, 1)]
    dark = [capture(four + [f200, "on 1 0"], k) for k in (0, 1)]
    bare = [capture(four, k) for k in (0, 1)]
    apart = lambda a, b: float(np.abs(a - b).max()) if len(a) == len(b) and len(a) else float("inf")
    check("a shown lane is filtered", 1e-6 < apart(dark[0], bare[0]) < float("inf"), "%.4f at most" % apart(dark[0], bare[0]))
    check("a hidden lane is not filtered at all", apart(dark[1], bare[1]) < 1e-9, "%.2e at most, %d samples" % (apart(dark[1], bare[1]), len(bare[1])))
    null("the same lane shown is filtered", apart(lit[1], bare[1]) > 1e-6, "%.4f" % apart(lit[1], bare[1]))

    # :323: LFO 1 on the cutoff, held at one and minus one, the cutoff's base
    # at step 500 (632 Hz); filterNow's hertz after the screen's matrix.
    out = kit.run("matrix_cpp", "\n".join(["run", "screen", "source lfo1", "vset cutoff 500", "route lfo1 filter.cutoff 1",
                                           "value lfo1 1", "frame", "filter", "value lfo1 -1", "frame", "filter",
                                           "unroute lfo1 filter.cutoff", "frame", "filter",
                                           "route lfo1 filter.cutoff 1", "value lfo1 0", "frame", "filter", "end"]))
    hz = [float(l.split("| filter ")[1].split()[1]) for l in out.split("\n") if l.startswith("filter ")]
    up, down, rest, held0 = hz
    check("a source sweeps the cutoff", up > rest * 3 and down < rest / 3,
          "%.0f Hz -> %.0f Hz, at rest %.0f Hz" % (down, up, rest))
    null("held at nought it does not", not (held0 > rest * 3), "%.0f Hz" % held0)
    # New with the move: the slider's law itself. On the page every cutoff
    # here was found by bisecting the page's own cutoffHz, so no check could
    # see that law change (the mutation pass: a thousand steps read as eleven
    # hundred passed everything). A thousand steps from 20 Hz to 20 kHz, three
    # decades, so step 500 is 20 * sqrt(1000), and the LFO's full swing of 400
    # steps each way (screen.h's span) is 1.2 decades: 40 Hz and 10 kHz.
    want = 20 * math.sqrt(1000)
    check("the cutoff's law: step 500 is %.1f Hz, and a swing of 400 steps each way is 40 Hz to 10 kHz" % want,
          abs(rest - want) < 0.01 and abs(up - 20 * 1000 ** 0.9) < 0.01 and abs(down - 20 * 1000 ** 0.1) < 0.01,
          "%.2f, %.2f, %.2f" % (down, rest, up))
    null("and not step 500 as eleven hundredths of the way", abs(rest - 20 * 1000 ** (500 / 1100)) >= 0.01)
