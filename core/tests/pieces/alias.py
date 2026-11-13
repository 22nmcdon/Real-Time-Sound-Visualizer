"""Band-limiting, on the core: what waveAt folds back, with the correction and
without it, and that the generator passes its own step.

These were aliastest.py's on ?brain=js until stage 5's step 3, batch 2 (13
Nov): there the page's own JavaScript `waveAt`, `cycleTables` and `lfoStep`
were called from the page, and the generator's window was the page's own
generator's. Here the same loops run through the core's `scope::waveAt`
(functions_cpp's `waveRun` and `waveAt`, `lfoRun`) and the core's generator
(generator_cpp), and the analysis is numpy's, as it was. The floors are the
ones measured when band-limiting landed on the page, with the same 3 dB of
slack; the core met them to the decibel, since it is the page's arithmetic.
The harmonics pane's four checks are the face's, and stayed in aliastest.py,
on the default page, over the instrument.
"""
import math
import numpy as np

RATE = 44100
N = 32768
BH = [0.35875, 0.48829, 0.14128, 0.01168]


def window(n):
    i = np.arange(n)
    return (BH[0] - BH[1] * np.cos(2 * np.pi * i / n)
            + BH[2] * np.cos(4 * np.pi * i / n) - BH[3] * np.cos(6 * np.pi * i / n))


def alias_floors(samples, f0, rate=RATE):
    """Everything that is not a harmonic of f0, in dB below the fundamental:
    the worst anywhere, and the worst below 10 kHz (aliastest.py's)."""
    x = np.asarray(samples, dtype=float)
    n = len(x)
    spec = np.abs(np.fft.rfft(x * window(n)))
    hz = np.arange(len(spec)) * rate / n
    near = 4 * rate / n
    harmonic = np.zeros(len(spec), dtype=bool)
    harmonic[:6] = True
    k = 1
    while k * f0 < rate / 2:
        harmonic |= np.abs(hz - k * f0) < near
        k += 1
    ref = spec[np.abs(hz - f0) < near].max()
    db = lambda v: 20 * math.log10(max(float(v), 1e-12) / ref)
    return db(spec[~harmonic].max()), db(spec[~harmonic & (hz < 10000)].max())


WANT = {
    ("square", 440): -62.1, ("square", 2000): -58.5, ("square", 4000): -46.2,
    ("ramp", 440): -61.1, ("ramp", 2000): -52.4, ("ramp", 4000): -46.2,
    ("triangle", 440): -99.5, ("triangle", 2000): -84.1, ("triangle", 4000): -65.2,
}
PULSE_WANT = {(0.25, 440): -58.1, (0.25, 2000): -49.4, (0.25, 4000): -46.2,
              (0.1, 440): -55.5, (0.1, 2000): -46.8, (0.1, 4000): -46.2,
              (0.05, 440): -55.2, (0.05, 2000): -44.4, (0.05, 4000): -30.1}
DRAWN_SQUARE = ",".join("0.9" if i < 128 else "-0.9" for i in range(256))


def run(kit):
    def wave(shape, f0, corrected, n=N, amount=0, points="-"):
        return kit.floats("functions_cpp", "waveRun %s %r %d %r %d %r %s"
                          % (shape, f0, n, RATE, 1 if corrected else 0, amount, points))

    # aliastest :119 and :122, x9: the page's waveAt with its step and with
    # nought, the uncorrected control. The null beside them: the control read
    # as the corrected wave fails the floor at every pitch the floor is under
    # -40 dB, so the floor is something the uncorrected code does not meet.
    naive_fails = []
    for shape in ("square", "ramp", "triangle"):
        for f0 in (440, 2000, 4000):
            peak, audible = alias_floors(wave(shape, f0, True), f0)
            _, naive = alias_floors(wave(shape, f0, False), f0)
            want = WANT[(shape, f0)]
            kit.check("%s at %d Hz folds back at %.0f dB or less" % (shape, f0, want), audible <= want + 3,
                      "%.1f dB below 10 kHz, %.1f dB anywhere" % (audible, peak))
            kit.check("%s at %d Hz is at least 20 dB better than uncorrected" % (shape, f0), audible - naive <= -20,
                      "was %.1f dB, now %.1f" % (naive, audible))
            naive_fails.append(naive > want + 3)
    kit.null("the uncorrected wave read as the corrected one fails the floor at all nine", all(naive_fails))

    # aliastest :145, x3: the page's cycleTables of a square drawn at 0.9, its
    # richest table read at every pitch (step nought) the control.
    for f0 in (440, 2000, 4000):
        peak, audible = alias_floors(wave("drawn", f0, True, points=DRAWN_SQUARE), f0)
        npeak, naudible = alias_floors(wave("drawn", f0, False, points=DRAWN_SQUARE), f0)
        kit.check("a drawn square at %d Hz folds back at -90 dB or less, fifty better than its richest table" % f0,
                  peak <= -90 and audible - naudible <= -50,
                  "%.1f dB anywhere, %.1f below 10 kHz; the richest table %.1f" % (peak, audible, naudible))
        if f0 == 4000:
            kit.null("the richest table at 4 kHz fails the -90", npeak > -90, "%.1f dB" % npeak)

    # aliastest :171, x9: the pulse, both edges corrected.
    pulse_naive = []
    for (w, f0), want in PULSE_WANT.items():
        _, audible = alias_floors(wave("pulse", f0, True, amount=w), f0)
        _, naudible = alias_floors(wave("pulse", f0, False, amount=w), f0)
        kit.check("a pulse of %d%% at %d Hz folds back at %.0f dB or less, 20 better than uncorrected" % (w * 100, f0, want),
                  audible <= want + 3 and audible - naudible <= -20,
                  "%.1f dB below 10 kHz; uncorrected %.1f" % (audible, naudible))
        pulse_naive.append(naudible > want + 3)
    kit.null("the uncorrected pulse fails its floor at all nine", all(pulse_naive))

    # aliastest :192 and :194: waveAt with no step, as an LFO calls it, over
    # a thousand phases of a cycle - the square two values, the ramp and the
    # triangle bit for bit their formulas.
    phases = [i * 2 * math.pi / 1000 for i in range(1000)]
    def shape_at(shape, step=0):
        return kit.floats("functions_cpp", "\n".join("waveAt %s %r %r - 0" % (shape, ph, step) for ph in phases))
    sq = sorted(set(shape_at("square")))
    def t_of(ph):
        t = (ph / (2 * math.pi)) % 1
        return t + 1 if t < 0 else t
    ramp_off = max(abs(v - (t_of(ph) * 2 - 1)) for v, ph in zip(shape_at("ramp"), phases))
    tri_off = max(abs(v - (2 / math.pi) * math.asin(math.sin(ph))) for v, ph in zip(shape_at("triangle"), phases))
    kit.check("a square with no step given is still two values", sq == [-0.9, 0.9], str(sq))
    kit.check("and the ramp and triangle are bit for bit what they were", ramp_off == 0 and tri_off == 0,
              "%r, %r" % (ramp_off, tri_off))
    stepped = sorted(set(shape_at("square", 0.05)))
    kit.null("a square given a step of a twentieth is more than two values, so the two values are the no-step path's",
             len(stepped) > 2, "%d values" % len(stepped))

    # aliastest :215 and :217: a 2 Hz square LFO stepped at 1000 a second for
    # a second. The page stepped a hand-built LFO object with its lfoStep;
    # here the core's Lfo through lfoStep (functions_cpp's lfoRun).
    def lfo(hz):
        vals = kit.floats("functions_cpp", "lfoRun square %r 1 1000 1000" % hz)
        ups = sum(1 for a, b in zip(vals, vals[1:]) if b > 0 and a <= 0)
        return ups, sorted(set(vals))
    ups, seen = lfo(2)
    kit.check("a 2 Hz square LFO still completes two cycles a second", ups == 2, "%d cycles" % ups)
    kit.check("and steps between two values, with no correction in it", seen == [-0.9, 0.9], str(seen))
    ups1, _ = lfo(1)
    kit.null("a 1 Hz one is not counted as two", ups1 != 2, "%d" % ups1)

    # aliastest :235: the generator's own samples at 4 kHz, square, which
    # tests that the generator hands waveAt its step. On the page a Mono note
    # held on the page's own generator; here the core's generator, the dyad
    # at unison sounding with no gate (generator_cpp, as parity's dyad runs).
    s = 34 * 1024
    out = kit.floats("generator_cpp", "run rate=%r slots=32 seed=3 samples=%d\nat 0 set shape square\nat 0 set freq 4000\n"
                     "at 0 set amp 1\nat 0 set interval 0\nend" % (float(RATE), s))
    lane = out[0:s * 6:6][-N:]
    peak, audible = alias_floors(lane, 4000)
    kit.check("the generator's own samples are band-limited, not just waveAt", audible <= -40,
              "%.1f dB below 10 kHz, %.1f dB anywhere" % (audible, peak))
    _, naive = alias_floors(wave("square", 4000, False), 4000)
    kit.null("the square uncorrected at 4 kHz, what a generator passing no step would play, fails the -40",
             naive > -40, "%.1f dB" % naive)

    # aliastest :263: one sample either side of each edge moves, and no other.
    lim, nai = wave("square", 220, True, n=8192), wave("square", 220, False, n=8192)
    moved = sum(1 for a, b in zip(lim, nai) if abs(a - b) > 1e-12)
    worst = max((abs(a - b) for a, b in zip(lim, nai) if abs(a - b) <= 1e-12), default=0)
    cycles = 8192 * 220 / RATE
    kit.check("the correction touches four samples a cycle and no others", abs(moved - 4 * cycles) <= 4 and worst == 0,
              "%d samples over %.1f cycles" % (moved, cycles))
    lim2k = wave("square", 2000, True, n=8192)
    moved2k = sum(1 for a, b in zip(lim2k, wave("square", 2000, False, n=8192)) if abs(a - b) > 1e-12)
    kit.null("the count is the pitch's: at 2 kHz it is not 220 Hz's four a cycle",
             abs(moved2k - 4 * cycles) > 4, "%d" % moved2k)
