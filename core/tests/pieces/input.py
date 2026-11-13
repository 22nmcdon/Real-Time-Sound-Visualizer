"""Live audio into the generator, on the core: off is off, the ride scales
every sample, FM is a factor on the rate, and the clock locks and lets go -
inputtest.py's numbers rows (:102 to :152).

These were inputtest.py's on `?brain=js` until stage 5, step 3, batch 5 (13
Nov): the page's own `makeGeneratorCore` built in the browser and handed an
input a block at a time with `setInput`. Here the core's Generator through
generator_cpp, which parity already drives with an input (`input HZ AMP
[DC]`, a sine with an offset, or a steady value at an amplitude of nought):
two still oscillators, the level at 0.4, a sine at one interval, 44.1 kHz.
The input the core was handed is made here by the same arithmetic, to the
float, for the checks that compare against it. Each check has its null.
"""
import math

import numpy as np

RATE = 44100
TRAILER = 17
BLOCK = 128
N = 8832  # 69 blocks: the page's 8820, rounded up to the block generator_cpp steps by


def core(kit, steps):
    """generator_cpp on one run: each step `(tone, n, input)` with `input` a
    dict of hz and amp, a steady value, or None; the left channel and the
    input as handed over."""
    events, at, xs = [], 0, []
    events += ["at 0 set amp 0.4", "at 0 set shape sine", "at 0 set interval 0"]
    for tone, n, given in steps:
        for k, v in (tone or {}).items(): events.append("at %d set %s %s" % (at, k, v))
        if given is None: events.append("at %d input 0 0" % at)
        elif "hz" in given: events.append("at %d input %r %r" % (at, given["hz"], given["amp"]))
        else: events.append("at %d input 1 0 %r" % (at, given["value"]))
        t = np.arange(at, at + n)
        if given is None: xs.append(np.zeros(n))
        elif "hz" in given: xs.append(np.float32(given["amp"] * np.sin(2 * math.pi * given["hz"] * t / RATE)))
        else: xs.append(np.full(n, np.float32(given["value"])))
        at += n
    text = "run rate=%r slots=40 seed=3 samples=%d lfo0=sine,0.2 lfo1=sine,0.2\n%s\nend" % (float(RATE), at, "\n".join(events))
    body = np.array(kit.floats("generator_cpp", text)[:-TRAILER])
    return body[0::6], np.concatenate(xs).astype(float)


def most(a, b):
    return float(np.max(np.abs(np.asarray(a) - np.asarray(b))))


def run(kit):
    check, null = kit.check, kit.null
    wave = {"freq": 220}
    sine7 = {"hz": 7, "amp": 0.5}

    # --- off is off ---
    plain, _ = core(kit, [(wave, N, None)])
    off, _ = core(kit, [(dict(wave, inputMode=0), N, sine7)])
    nought, _ = core(kit, [(dict(wave, inputMode=2, inputDepth=0), N, sine7)])
    check("with the mode off, or a ride at a depth of nought, the input changes nothing at all",
          most(plain, off) == 0 and most(plain, nought) == 0, "%.2e, %.2e" % (most(plain, off), most(plain, nought)))
    ride, x = core(kit, [(dict(wave, inputMode=2, inputDepth=0.5), N, sine7)])
    null("a ride at a half does change it", most(plain, ride) > 0.1, "%.3f" % most(plain, ride))

    # --- ride ---
    want = plain * (1 + 2 * 0.5 * x)
    gap = most(ride, want)
    print("    the ride against the plain wave times (1 + 2 depth x): %.2e; against the plain wave: %.3f" % (gap, most(ride, plain)))
    check("a ride scales every sample by (1 + 2 depth x): the sound rides on the outline", gap < 1e-6 and most(ride, plain) > 0.1,
          "%.2e" % gap)
    shifted = plain + 2 * 0.5 * x * 0.4
    null("a ride that shifted the figure rather than scaling it is told apart", most(ride, shifted) > 1e-3, "%.3f" % most(ride, shifted))

    # --- FM ---
    fast, _ = core(kit, [(dict(wave, freq=440), N, None)])
    fm, _ = core(kit, [(dict(wave, inputMode=1, inputDepth=1), N, {"value": 0.25})])
    print("    a steady quarter at full depth against twice the pitch: %.2e" % most(fm, fast))
    check("FM is a factor on the rate: a steady quarter at full depth draws what twice the pitch draws",
          most(fm, fast) < 1e-9 and most(fm, plain) > 0.1, "%.2e, against the plain wave %.3f" % (most(fm, fast), most(fm, plain)))
    half, _ = core(kit, [(dict(wave, inputMode=1, inputDepth=0.5), N, {"value": 0.25})])
    null("at half the depth it is not twice the pitch", most(half, fast) > 0.1, "%.3f" % most(half, fast))
    stop, _ = core(kit, [(dict(wave, inputMode=1, inputDepth=1), N, {"value": -1})])
    span = float(np.max(stop[100:]) - np.min(stop[100:]))
    check("and a deep enough negative input stops the waveform rather than running it backwards", span < 1e-9, "%.2e" % span)
    back, _ = core(kit, [(dict(wave, inputMode=1, inputDepth=1), N, {"value": -0.125})])
    null("an eighth below, half the rate, slows it and it still moves", float(np.max(back[100:]) - np.min(back[100:])) > 0.1)

    # --- clock ---
    hundred = {"hz": 100, "amp": 0.5}
    P = 441
    free, _ = core(kit, [(dict(wave, freq=330), N * 2, None)])
    loose = most(free[4410:-P], free[4410 + P:])
    cw, _ = core(kit, [(dict(wave, freq=330, inputMode=3), N * 2, hundred), (None, N * 2, {"value": 0})])
    lock = most(cw[4410:N * 2 - P], cw[4410 + P:N * 2])
    tail = cw[N * 2 + 2000:]
    ups = int(np.sum((tail[:-1] <= 0) & (tail[1:] > 0)))
    hz = ups * RATE / len(tail)
    print("    a 330 Hz waveform clocked by 100 Hz repeats every 441 samples to %.2e (unclocked %.3f); input gone, it runs at %.1f Hz"
          % (lock, loose, hz))
    check("a waveform clocked by the input plays at the input's pitch, and runs free at its own when the input stops",
          lock < 1e-6 and loose > 0.1 and abs(hz - 330) < 5, "%.2e against %.3f, %.1f Hz" % (lock, loose, hz))
    null("unclocked, 330 Hz does not repeat every 441 samples", not (loose < 1e-6), "%.3f" % loose)
    # A stalled waveform - the FM run held still above - read by the same count is no 330 Hz.
    stalled = int(np.sum((stop[100:-1] <= 0) & (stop[101:] > 0))) * RATE / len(stop[100:])
    null("a clock that stalled when the input stopped would read no pitch", not (abs(stalled - 330) < 5), "%.1f Hz" % stalled)

    al, x = core(kit, [(dict(wave, shape="sine", freq=330, inputMode=3), N, hundred)])
    up = lambda xs: [i for i in range(4410, len(xs) - 1) if xs[i] <= 0 < xs[i + 1]]
    ins, outs = up(x), up(al)
    off_by = max(min(abs(o - i) for o in outs) for i in ins) if ins and outs else 999
    check("and each of the input's upward crossings restarts the cycle: the clocked sine rises where the input does",
          off_by <= 1 and len(outs) >= len(ins), "worst %d samples, %d crossings against %d" % (off_by, len(outs), len(ins)))
    unclocked, _ = core(kit, [(dict(wave, shape="sine", freq=330), N, None)])
    outs_free = up(unclocked)
    worst_free = max(min(abs(o - i) for o in outs_free) for i in ins)
    null("unclocked, the sine does not rise where the input does", worst_free > 1, "worst %d samples" % worst_free)
