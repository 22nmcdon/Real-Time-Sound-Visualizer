"""The voice filter, on the core: at a fixed cutoff its response is Web
Audio's biquad (the Audio EQ Cookbook's, as the specification states it),
all four types at three cutoffs and three resonances; the comparison sees Q;
and swept every sample from 50 Hz to 18 kHz at a Q of twenty it stays finite
and bounded.

These were vcftest.py's until stage 5's step 6: the page's own `svfG` and
`svfStep` run in the page and held to the browser's BiquadFilterNode
(`getFrequencyResponse`). The page's JavaScript filter went with its engine,
so here the core's (scope::svfStep, through functions_cpp's `svfRun` and
`svfSweep`) is held to the cookbook's response written out in filter.py,
which is what the browser's node computes. The voice filter's Q is a ratio
for all four types, so the cookbook is read with it linear throughout - the
browser was handed the low and high pass's in decibels to mean the same.
"""
import math
import numpy as np

from pieces.filter import cookbook

RATE = 44100
TYPES = [(1, "lowpass"), (2, "bandpass"), (3, "highpass"), (4, "notch")]


def run(kit):
    check, null = kit.check, kit.null
    n = 16384
    probes = np.array([20 * 1000 ** (i / 39) * 0.999 for i in range(40)])
    impulse = ",".join(["1"] + ["0"] * (n - 1))

    def magnitude(h):
        k = np.arange(len(h))
        w = 2 * np.pi * probes[:, None] / RATE
        return np.abs((np.asarray(h)[None, :] * np.exp(-1j * w * k[None, :])).sum(axis=1))

    cases = [(t, name, fc, q) for t, name in TYPES for fc in (200, 1000, 5000) for q in (math.sqrt(0.5), 2, 10)]
    gs = kit.floats("functions_cpp", "\n".join("svfG %r %r" % (fc, RATE) for _, _, fc, _ in cases))
    runs = kit.run("functions_cpp", "\n".join("svfRun %r %r %d %s" % (g, 1 / q, t, impulse)
                                             for (t, _, _, q), g in zip(cases, gs))).strip().split("\n")
    worst, at, ours = 0.0, None, {}
    for (t, name, fc, q), line in zip(cases, runs):
        mine = magnitude([float(v) for v in line.split()])
        ours[(name, fc, q)] = mine
        want = cookbook(name, fc, q, RATE, probes, q_in_db=False)
        err = np.where(want > 1e-3, np.abs(20 * np.log10(np.maximum(mine, 1e-30) / want)), np.abs(mine - want) * 1000)
        if err.max() > worst: worst, at = float(err.max()), (name, fc, round(q, 2), float(probes[err.argmax()]))
    check("at a fixed cutoff the voice filter is the cookbook's biquad to 0.01 dB, all four types, three cutoffs, three Qs",
          worst < 0.01, "worst %.5f dB at %s" % (worst, at))
    # Its null: each response held to the next type's cookbook - a low pass
    # read as a band pass and so on round - must miss, or the comparison
    # cannot tell one type from another.
    names = [name for _, name in TYPES]
    missed = min(float(np.abs(20 * np.log10(np.maximum(ours[(name, fc, q)], 1e-30)
                                             / np.maximum(cookbook(names[(names.index(name) + 1) % 4], fc, q, RATE, probes,
                                                                   q_in_db=False), 1e-30))).max())
                 for _, name, fc, q in cases)
    null("each response read against the next type's misses by more than a decibel", missed > 1, "least %.2f dB" % missed)
    # The null: the low pass at a Q of ten read as the specification reads a
    # low pass's Q, in decibels, misses by ten decibels at the cutoff - or the
    # comparison above was never looking at the Q.
    i = int(np.argmin(np.abs(probes - 1000)))
    trap = 20 * math.log10(ours[("lowpass", 1000, 10)][i] / cookbook("lowpass", 1000, 10, RATE, probes, q_in_db=True)[i])
    null("a Q handed to a low pass as decibels, not as a ratio, misses by 10 dB at the cutoff: the comparison sees Q",
         abs(trap) > 5, "%.2f dB" % trap)

    most, finite = kit.floats("functions_cpp", "svfSweep %d 20 %r" % (RATE, RATE))
    check("swept from 50 Hz to 18 kHz three thousand times a second at a Q of 20, it stays finite and bounded",
          finite == 1 and most < 50, "largest %.2f" % most)
    calm, _ = kit.floats("functions_cpp", "svfSweep %d 0.7071 %r" % (RATE, RATE))
    null("and the bound can be told from its swing: at a Q of 0.71 the same sweep peaks lower", calm < most,
         "%.2f against %.2f" % (calm, most))
