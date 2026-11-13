"""G1's pulse, on the core: the wave, its harmonics, the width the generator
reads, a source moving it, hard sync and each layer its own.

These were pulsetest.py's on ?brain=js until stage 5's step 3, batch 2 (13
Nov): there the page's own JavaScript `waveAt` and a `makeGeneratorCore`
built in the page, with routes put on its width and sync slots by hand. Here
the core's `scope::waveAt` (functions_cpp) and the core's generator
(generator_cpp: the same `set`, `routes` with the source held at a value, and
the layer argument), and for the one claim about a real source, the whole
instrument (instrument_cpp: a key at full velocity routed to the width). The
spectra are numpy's, on windows a whole number of hertz wide, as they were.
"""
import base64, json, math, os, re
import numpy as np

RATE = 44100
BH = [0.35875, 0.48829, 0.14128, 0.01168]
WIDTH, SYNC = 27, 20      # the generator's slots (scope/generator.h, slot::Width and slot::Sync)


def spectrum(x, rate=RATE):
    x = np.asarray(x, dtype=float)
    n = len(x)
    i = np.arange(n)
    w = (BH[0] - BH[1] * np.cos(2 * np.pi * i / n)
         + BH[2] * np.cos(4 * np.pi * i / n) - BH[3] * np.cos(6 * np.pi * i / n))
    spec = np.abs(np.fft.rfft(x * w))
    return spec, np.arange(len(spec)) * rate / n


def level_at(spec, hz, f):
    return spec[np.abs(hz - f) < 4 * RATE / (2 * (len(spec) - 1))].max()


def db(a, b):
    return 20 * math.log10(max(float(a), 1e-15) / max(float(b), 1e-15))


def harmonics(x, f0, count):
    spec, hz = spectrum(x)
    ref = level_at(spec, hz, f0)
    return [db(level_at(spec, hz, n * f0), ref) for n in range(1, count + 1)]


def formula(w, count):
    ref = abs(math.sin(math.pi * w))
    return [db(abs(math.sin(math.pi * n * w)) / n, ref) for n in range(1, count + 1)]


def duty(x):
    return float((np.asarray(x) > 0).mean())


def route(slot, held, amount=1.0):
    return "-1/%r/%r/%d/%r/%r/0" % (held, held, slot, amount, amount)


def setup_code(fields):
    """A setup code stamped with the core's version, so no decode pass moves it."""
    v = int(re.search(r"kSetupVersion = (\d+)", open(os.path.join(os.path.dirname(__file__), "..", "..", "include",
                                                                  "scope", "setup.h")).read()).group(1))
    return base64.b64encode(json.dumps(dict({"v": v}, **fields)).encode()).decode().rstrip("=")


def run(kit):
    def core(tone=None, toneB=None, voices=None, routes=None, n=44100, skip=0):
        """The page's CORE harness on the core: amp 0.9, interval and phase
        nought, the fields given, and lanes A (picture left) and B's left."""
        blocks = -(-(n + skip) // 128) * 128
        ev = ["at 0 set amp 0.9", "at 0 set interval 0", "at 0 set phase 0"]
        ev += ["at 0 set %s %s" % (k, v) for k, v in (tone or {}).items()]
        ev += ["at 0 set %s %s 1" % (k, v) for k, v in (toneB or {}).items()]
        if voices: ev += ["at 0 voices 0 %s" % voices, "at 0 voices 1 %s" % voices]
        if routes: ev += ["at 0 routes %s" % routes]
        out = kit.floats("generator_cpp", "run rate=%r slots=32 seed=3 samples=%d lfo0=sine,0.2 lfo1=sine,0.2\n%s\nend"
                         % (float(RATE), blocks, "\n".join(ev)))
        return out[skip * 6:(skip + n) * 6:6], out[skip * 6 + 4:(skip + n) * 6:6]

    def calls(lines):
        return kit.floats("functions_cpp", "\n".join(lines))

    # pulsetest :135: at a half, the page's waveAt('pulse') against
    # waveAt('square') at 2 kHz, step and all. The null: at a quarter, not.
    def apart(width):
        p = kit.run("functions_cpp", "waveRun pulse 2000 4410 44100 1 %r -" % width).split()
        q = kit.run("functions_cpp", "waveRun square 2000 4410 44100 1 0 -").split()
        return max(abs(float(a) - float(b)) for a, b in zip(p, q))
    kit.check("at a half the pulse is the square, sample for sample, band-limiting included", apart(0.5) == 0,
              "worst %.2e" % apart(0.5))
    kit.null("at a quarter it is not the square", apart(0.25) > 0.1)

    # :138: the mean and peak over a cycle, uncorrected, at 20000 phases.
    def mean_peak(w):
        v = calls(["waveAt pulse %r 0 - %r" % (2 * math.pi * (i + 0.5) / 20000, w) for i in range(20000)])
        raw = [0.9 if x > 0 else -0.9 for x in v]     # the same pulse with its middle left in
        uncentred[w] = (sum(raw) / len(raw), max(abs(x) for x in raw))
        return sum(v) / len(v), max(abs(x) for x in v)
    uncentred = {}
    shape = [(w,) + mean_peak(w) for w in (0.05, 0.1, 0.25, 0.5, 0.75, 0.95)]
    kit.check("at every width from 5 to 95 per cent its middle is nought and its larger excursion 0.9",
              all(abs(m) < 1e-3 and abs(k - 0.9) < 1e-12 for _, m, k in shape),
              str([[w, round(m, 6), round(k, 6)] for w, m, k in shape]))
    # The null: the same samples as a pulse with its middle left in, high
    # at 0.9 and low at -0.9, which has a DC at every width but a half.
    kit.null("the same pulse with its middle left in fails it",
             not all(abs(m) < 1e-3 and abs(k - 0.9) < 1e-12 for m, k in uncentred.values()),
             str({w: round(m, 3) for w, (m, _) in uncentred.items()}))

    # :141: a width past either end plays that end.
    def ends(past, end):
        a = calls(["waveAt pulse %r 0.01 - %r" % (ph, past) for ph in (0.3, 1.1, 2.9, 4.4, 6.0)])
        b = calls(["waveAt pulse %r 0.01 - %r" % (ph, end) for ph in (0.3, 1.1, 2.9, 4.4, 6.0)])
        return a == b
    kit.check("and a width past either end is that end", ends(0.01, 0.05) and ends(0.99, 0.95))
    kit.null("and 0.2 is not 0.05's", not ends(0.2, 0.05))

    # :158, :161, :164: the generator's pulse at 220 Hz against |sin(pi n w)| / n.
    got = {w: harmonics(core({"shape": "pulse", "width": w, "freq": 220}, n=44100, skip=4410)[0], 220, 12)
           for w in (0.25, 1 / 3, 0.1)}
    def matches(w, against=None):
        want = formula(against if against is not None else w, 12)
        present = [abs(g - f) for g, f in zip(got[w], want) if f > -60]
        absent = [g for g, f in zip(got[w], want) if f <= -60]
        return max(present) < 0.3 and (not absent or max(absent) < -60), max(present), absent
    q, off_q, gone_q = matches(0.25)
    kit.check("a quarter: every harmonic |sin(pi n / 4)| / n to 0.3 dB, and no fourth, eighth or twelfth",
              q and len(gone_q) == 3, "worst %.2f dB off; absent at %s dB" % (off_q, [round(v) for v in gone_q]))
    t, off_t, gone_t = matches(1 / 3)
    kit.check("a third: the same, with no third, sixth, ninth or twelfth",
              t and len(gone_t) == 4, "worst %.2f dB off; absent at %s dB" % (off_t, [round(v) for v in gone_t]))
    n10, off_n, _ = matches(0.1)
    kit.check("a tenth: the first dozen falling as a narrow pulse's do", n10, "worst %.2f dB off" % off_n)
    kit.null("the quarter's harmonics read against a third's formula fail", not matches(0.25, 1 / 3)[0])

    # :173 and :179: the duty the generator plays, set and not.
    widths = {w: duty(core({"shape": "pulse", "width": w, "freq": 220})[0]) for w in (0.25, 0.7)}
    bare = duty(core({"shape": "pulse", "freq": 220})[0])
    kit.check("a core built with no width plays a quarter, as the panel starts", abs(bare - 0.25) < 0.01, "%.3f" % bare)
    kit.check("the output is high for the width set: a quarter and seven tenths of the time",
              abs(widths[0.25] - 0.25) < 0.01 and abs(widths[0.7] - 0.7) < 0.01, str(widths))
    kit.null("the seven tenths is not a quarter", abs(widths[0.7] - 0.25) >= 0.01)

    # :181: a route on the width slot with its source held at one or minus one.
    pushed = duty(core({"shape": "pulse", "width": 0.25, "freq": 220}, routes=route(WIDTH, 1))[0])
    pulled = duty(core({"shape": "pulse", "width": 0.5, "freq": 220}, routes=route(WIDTH, -1))[0])
    past = duty(core({"shape": "pulse", "width": 0.8, "freq": 220}, routes=route(WIDTH, 1))[0])
    kit.check("a source at full pushes a quarter to seven tenths, pulls a half to 5 per cent, and stops at 95",
              abs(pushed - 0.70) < 0.01 and abs(pulled - 0.05) < 0.01 and abs(past - 0.95) < 0.01,
              "%.3f, %.3f, %.3f" % (pushed, pulled, past))
    still = duty(core({"shape": "pulse", "width": 0.25, "freq": 220}, routes=route(WIDTH, 0))[0])
    kit.null("the source held at nought leaves a quarter, not seven tenths", abs(still - 0.70) >= 0.01, "%.3f" % still)

    # :193: sync at ratio one, switched on by a routing of nought, is the plain
    # pulse one sample late.
    plain = np.array(core({"shape": "pulse", "width": 0.3, "freq": 1234.5}, n=4410)[0])
    synced = np.array(core({"shape": "pulse", "width": 0.3, "freq": 1234.5}, n=4410, routes=route(SYNC, 0))[0])
    late = float(np.abs(synced[1:] - plain[:-1]).max())
    kit.check("hard sync at ratio one is the plain pulse one sample late - its reset corrected by its own jump",
              late < 1e-5, "%.1e" % late)
    kit.null("and not on time", float(np.abs(synced - plain).max()) > 1e-5)

    # :201: two layers, each its own width, a note on both.
    voices = "57/220.0/1.0/xy"
    a, b = core({"shape": "pulse", "width": 0.25}, {"shape": "pulse", "width": 0.5}, voices=voices, n=44100, skip=8192)
    second_a, second_b = harmonics(a, 220, 2)[1], harmonics(b, 220, 2)[1]
    kit.check("A at a quarter has its second harmonic at -3.0 dB, B at a half none: B plays its own",
              abs(second_a - db(0.5, math.sin(math.pi / 4))) < 0.3 and second_b < -60,
              "A %.1f dB, B %.1f dB" % (second_a, second_b))
    _, b_same = core({"shape": "pulse", "width": 0.25}, {"shape": "pulse", "width": 0.25}, voices=voices, n=44100, skip=8192)
    kit.null("B at A's quarter has the second harmonic", harmonics(b_same, 220, 2)[1] > -60)

    # :257, the sound half: a key at full velocity routed to the width, in the
    # instrument whole. On the page it was midiNoteOn on the page's brain and
    # its routing compiled by the page; here the keyboard, the matrix and the
    # generator of the core, read off the heard pair. The slider's half stayed
    # in pulsetest.py, on the default page.
    code = setup_code({"shape": "pulse", "width": 25, "freq": 220})
    def heard(depth):
        lines = [["make", 48000, 128, code], ["click", "midiMono"], ["routings", "midi.key>gen.width@%r" % depth],
                 ["midi", 0x90, 57, 127]] + [["block", 128]] * 100
        blocks = [l for l in kit.instrument(lines) if l.startswith("block ")][30:]
        return duty([float(v) for l in blocks for v in l.split()[1:129]])
    down, up = heard(0), heard(1)
    kit.check("a key on Width at full velocity moves the instrument's sound, a quarter to seven tenths",
              abs(down - 0.25) < 0.02 and abs(up - 0.70) < 0.02, "%.3f, %.3f" % (down, up))
    kit.null("the routing at nought is not seven tenths", abs(down - 0.70) >= 0.02)
