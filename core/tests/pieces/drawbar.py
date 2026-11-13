"""The saw and the drawbars, on the core: a saw's harmonics, each bar's
footage, Nyquist, the level law, a key on a bar, and each layer its own
registration.

These were drawbartest.py's on ?brain=js until stage 5's step 3, batch 2 (13
Nov): there a `makeGeneratorCore` built in the page with oscillators that do
nothing, and the saw and the square from the page's own generator's window
after the menu. Here the core's generator (generator_cpp, with `bars` and the
layer argument, the LFOs at rest) and, for the key on a bar, the whole
instrument (instrument_cpp). The menu offering the saw, the bars' panel and
their codes stayed in drawbartest.py, on the default page. Spectra are numpy's.
"""
import base64, json, math, os, re
import numpy as np

RATE = 44100
N = 44100
BH = [0.35875, 0.48829, 0.14128, 0.01168]
FOOT = ["16'", "5 1/3'", "8'", "4'", "2 2/3'", "2'", "1 3/5'", "1 1/3'", "1'"]
MULT = [0.5, 1.5, 1, 2, 3, 4, 5, 6, 8]


def spectrum(x, rate=RATE):
    x = np.asarray(x, dtype=float)
    n = len(x)
    i = np.arange(n)
    w = (BH[0] - BH[1] * np.cos(2 * np.pi * i / n)
         + BH[2] * np.cos(4 * np.pi * i / n) - BH[3] * np.cos(6 * np.pi * i / n))
    spec = np.abs(np.fft.rfft(x * w))
    return spec, np.arange(len(spec)) * rate / n


def level_at(spec, hz, f, rate=RATE):
    return spec[np.abs(hz - f) < 4 * rate / (2 * (len(spec) - 1))].max()


def db(a, b):
    return 20 * math.log10(max(float(a), 1e-15) / max(float(b), 1e-15))


def partials(x):
    spec, hz = spectrum(x)
    top = int(np.argmax(spec))
    others = spec.copy()
    others[np.abs(hz - hz[top]) < 4 * RATE / len(x)] = 0
    others[:6] = 0
    return float(hz[top]), db(others.max(), spec[top])


rms = lambda x: float(np.sqrt(np.mean(np.asarray(x) ** 2)))


def setup_code(fields):
    v = int(re.search(r"kSetupVersion = (\d+)", open(os.path.join(os.path.dirname(__file__), "..", "..", "include",
                                                                  "scope", "setup.h")).read()).group(1))
    return base64.b64encode(json.dumps(dict({"v": v}, **fields)).encode()).decode().rstrip("=")


def run(kit):
    def gen(events, n, lanes=(0,), skip=0):
        blocks = -(-(n + skip) // 128) * 128
        out = kit.floats("generator_cpp", "run rate=%r slots=32 seed=3 samples=%d lfo0=sine,0.2 lfo1=sine,0.2\n%s\nend"
                         % (float(RATE), blocks, "\n".join(events)))
        return [out[skip * 6 + k:(skip + n) * 6:6] for k in lanes]

    def core(bars, freq, n=N):
        """drawbartest's CORE: drawbars, the bars, the frequency, amp 0.9, unison."""
        return gen(["at 0 set shape drawbars", "at 0 bars 0 %s" % ",".join(map(str, bars)), "at 0 set freq %r" % freq,
                    "at 0 set amp 0.9", "at 0 set interval 0"], n)[0]

    # drawbartest :134 and :137: on the page, the menu chosen and the page's
    # generator's window read; here the core's saw and square at 440.
    def h23(shape):
        x = gen(["at 0 set shape %s" % shape, "at 0 set freq 440", "at 0 set amp 0.9", "at 0 set interval 0"], N, skip=4096)[0]
        spec, hz = spectrum(x)
        one = level_at(spec, hz, 440)
        return db(level_at(spec, hz, 880), one), db(level_at(spec, hz, 1320), one)
    saw2, saw3 = h23("ramp")
    sq2, _ = h23("square")
    saw_is = lambda a, b: abs(a - 20 * math.log10(1 / 2)) < 0.5 and abs(b - 20 * math.log10(1 / 3)) < 0.5
    kit.check("the saw: the second harmonic is half the first, -6.0 dB, and the third -9.5", saw_is(saw2, saw3),
              "%.2f, %.2f" % (saw2, saw3))
    kit.check("which the square has none of", sq2 < -40, "%.1f dB" % sq2)
    kit.null("the square read as the saw fails", not saw_is(*h23("square")))

    # :146, :149, :154: each bar alone.
    found = []
    for k in range(9):
        bars = [0] * 9; bars[k] = 8
        f, rest = partials(core(bars, 220))
        found.append((round(f, 1), round(rest, 1)))
    kit.check("each bar alone is its partial: 110, 330, 220, 440, 660, 880, 1100, 1320, 1760 Hz",
              all(abs(f - 220 * m) < 3 for (f, _), m in zip(found, MULT)), str([f for f, _ in found]))
    kit.null("the partials read in a shifted order fail", not all(abs(f - 220 * m) < 3 for (f, _), m in zip(found[1:] + found[:1], MULT)))
    kit.check("and nothing else, 100 dB under", all(rest < -100 for _, rest in found), str([r for _, r in found]))
    two = partials(core([0, 0, 8, 8, 0, 0, 0, 0, 0], 220))[1]
    kit.null("two bars out is something else at the second's level", two > -100, "%.1f dB" % two)
    spec, hz = spectrum(core([8, 0, 0, 0, 0, 0, 0, 0, 0], 220))
    rect = db(level_at(spec, hz, 220), level_at(spec, hz, 110))
    kit.check("16' is a sine an octave down, not a rectified one an octave up: nothing at 220 Hz", rect < -100,
              "%.1f dB" % rect)
    # The null: a rectified sine an octave up from 110, |sin|, built here, has its strongest component at 220.
    t = np.arange(N) / RATE
    rspec, rhz = spectrum(np.abs(np.sin(2 * np.pi * 110 * t)))
    kit.null("a rectified 110 Hz sine has 220 Hz in it", db(level_at(rspec, rhz, 220), level_at(rspec, rhz, 110)) > -100)

    # :164, :166, :175: at 4 kHz.
    top = {}
    for k in (5, 7, 8):
        bars = [0] * 9; bars[k] = 8
        top[FOOT[k]] = rms(core(bars, 4000, 8192))
    kit.check("at 4 kHz the 1' (32 kHz) and 1 1/3' (24 kHz) are silent rather than folded",
              top["1'"] < 1e-9 and top["1 1/3'"] < 1e-9, str(top))
    kit.check("while the 2', at 16 kHz, is all there", abs(top["2'"] - 0.9 / math.sqrt(2)) < 0.01, str(top["2'"]))
    low1 = rms(core([0, 0, 0, 0, 0, 0, 0, 0, 8], 2000, 8192))
    kit.null("the 1' at 2 kHz, 16 kHz, is not silent", low1 > 1e-9, "%.3f" % low1)
    full = core([8] * 9, 4000)
    spec, hz = spectrum(full)
    def between(spec, hz, step):
        grid = np.zeros(len(spec), dtype=bool)
        grid[:6] = True
        for j in range(1, 12): grid |= np.abs(hz - step * j) < 4 * RATE / N
        return db(spec[~grid].max(), spec.max())
    fold = between(spec, hz, 2000)
    kit.check("every bar out at 4 kHz puts nothing between the partials, 100 dB down", fold < -100, "%.1f dB" % fold)
    kit.null("read on a grid of 4 kHz instead of 2 kHz, the 16' and 5 1/3' are between", between(spec, hz, 4000) > -100)

    # :197: 1' alone sliding from 2.4 to 2.8 kHz across Nyquist; on the page
    # the frequency was set every 64 samples, here every 128, generator_cpp's
    # block, so a block's step in level is twice the page's at most.
    ev = ["at 0 set shape drawbars", "at 0 bars 0 0,0,0,0,0,0,0,0,8", "at 0 set amp 0.9"]
    ev += ["at %d set freq %r" % (b * 128, 2400 + 400 * b / 345) for b in range(345)]
    x = gen(ev, 345 * 128)[0]
    peaks = [max(abs(v) for v in x[b * 128:(b + 1) * 128]) for b in range(345)]
    jump = max(abs(a - b) for a, b in zip(peaks, peaks[1:]))
    kit.check("sliding up past Nyquist, the top bar fades rather than stepping out",
              peaks[0] > 0.85 and peaks[-1] < 1e-9 and jump < 0.05,
              "first %.3f, last %g, largest step %.4f" % (peaks[0], peaks[-1], jump))
    # The null: a bar that stays at full until its partial passes Nyquist and
    # then steps out, made here from the run's first block, steps by more than the bound.
    cliff = [peaks[0] if 8 * (2400 + 400 * b / 345) < RATE / 2 else 0 for b in range(345)]
    kit.null("the slide cut off at Nyquist steps out", max(abs(a - b) for a, b in zip(cliff, cliff[1:])) >= 0.05)

    # :206, :208: the level law.
    at8 = rms(core([0, 0, 8, 0, 0, 0, 0, 0, 0], 220))
    law = {lv: db(rms(core([0, 0, lv, 0, 0, 0, 0, 0, 0], 220)), at8) for lv in (7, 4, 1)}
    at0 = rms(core([0] * 9, 220))
    kit.check("three decibels a step: 8' at 7 is -3, at 4 is -12, at 1 is -21",
              all(abs(law[lv] + 3 * (8 - lv)) < 0.05 for lv in law), str({k: round(v, 2) for k, v in law.items()}))
    kit.null("and not six a step", not all(abs(law[lv] + 6 * (8 - lv)) < 0.05 for lv in law))
    kit.check("and at nought it is silent", at0 == 0, str(at0))
    kit.null("and at one it is not", rms(core([0, 0, 1, 0, 0, 0, 0, 0, 0], 220)) > 0)

    # :214, :216, :221: peaks and shares.
    peaks = {reg: float(np.max(np.abs(core(bars, 220))))
             for reg, bars in (("one at 8", [0, 0, 8, 0, 0, 0, 0, 0, 0]), ("all nine at 8", [8] * 9),
                               ("88 8000 000", [8, 8, 8, 0, 0, 0, 0, 0, 0]))}
    kit.check("one bar at eight is a full-scale sine at the amplitude", abs(peaks["one at 8"] - 0.9) < 0.001, str(peaks))
    kit.check("and every bar out stays inside it, rather than being drawn as the clamp",
              peaks["all nine at 8"] <= 0.9 + 1e-6 and peaks["88 8000 000"] <= 0.9 + 1e-6, str(peaks))
    # The null: the nine at their own weights, unshared, summed here from the core's own single bars, pass the amplitude.
    singles = sum(np.asarray(core([8 if j == k else 0 for j in range(9)], 220)) for k in range(9))
    kit.null("the nine bars summed unshared go past the amplitude", float(np.max(np.abs(singles))) > 0.9 + 1e-6)
    spec1, hz1 = spectrum(core([0, 0, 8, 0, 0, 0, 0, 0, 0], 220))
    spec3, hz3 = spectrum(core([8, 8, 8, 0, 0, 0, 0, 0, 0], 220))
    share = db(level_at(spec3, hz3, 220), level_at(spec1, hz1, 220))
    kit.check("three bars at eight are a third each: the 8' is 9.5 dB under what it is alone",
              abs(share - 20 * math.log10(1 / 3)) < 0.1, "%.2f dB" % share)
    kit.null("and not a half", abs(share - 20 * math.log10(1 / 2)) >= 0.1)

    # :253, :255: a key at full velocity routed to the 4' bar draws it out to
    # eight and, at depth nought, leaves it in. On the page midiNoteOn on the
    # page's brain with its routing compiled there, in a bare core whose 4'
    # at eight was level with its 8'; here the instrument whole, read off its
    # heard pair at 48 kHz on a second of whole hertz. Its base sound is not
    # flat between 220 and 440 Hz (the 4' and 8' both at eight read 2.8 dB
    # apart), so "level with the 8'" is restated as level with the 4' set at
    # eight in the registration itself, to a tenth of a decibel.
    def fourth_against_eighth(bars, depth):
        code = setup_code({"shape": "drawbars", "bars": bars, "freq": 220})
        lines = [["make", 48000, 128, code], ["click", "midiMono"], ["routings", "midi.key>gen.bar3@%r" % depth],
                 ["midi", 0x90, 57, 127]] + [["block", 128]] * 420
        blocks = [l for l in kit.instrument(lines) if l.startswith("block ")][45:420]
        x = [float(v) for l in blocks for v in l.split()[1:129]][:48000]
        spec, hz = spectrum(x, 48000)
        return db(level_at(spec, hz, 440, 48000), level_at(spec, hz, 220, 48000))
    up, down, set8 = fourth_against_eighth("008000000", 1), fourth_against_eighth("008000000", 0), fourth_against_eighth("008800000", 0)
    kit.check("a key on the 4' bar at full draws it out to eight: as the 4' at eight in the registration",
              abs(up - set8) < 0.1, "%.2f dB against %.2f" % (up, set8))
    kit.check("and pushed back in, the 4' is gone", down < -60, "%.1f dB" % down)
    half = fourth_against_eighth("008000000", 0.5)
    kit.null("at half depth the 4' is out, but not at eight", abs(half - set8) >= 0.1 and half > -60, "%.2f dB" % half)

    # :309: B's own registration, a note on both layers.
    a, b = gen(["at 0 set shape drawbars", "at 0 bars 0 0,0,8,0,0,0,0,0,0", "at 0 set shape drawbars 1",
                "at 0 bars 1 8,0,0,0,0,0,0,0,0", "at 0 set amp 0.9 1",
                "at 0 voices 0 57/220.0/1.0/xy", "at 0 voices 1 57/220.0/1.0/xy"], 44100, lanes=(0, 4), skip=8192)
    (fa, ra), (fb, rb) = partials(a), partials(b)
    kit.check("and B sounds its own: B's picture is its 16' at 110 Hz while A's is its 8' at 220, each alone",
              abs(fb - 110) < 3 and abs(fa - 220) < 3 and ra < -100 and rb < -100,
              "A %.1f Hz (rest %.0f dB), B %.1f Hz (rest %.0f dB)" % (fa, ra, fb, rb))
    _, b_a = gen(["at 0 set shape drawbars", "at 0 bars 0 0,0,8,0,0,0,0,0,0", "at 0 set shape drawbars 1",
                  "at 0 set amp 0.9 1", "at 0 voices 0 57/220.0/1.0/xy", "at 0 voices 1 57/220.0/1.0/xy"],
                 44100, lanes=(0, 4), skip=8192)
    kit.null("B given no bars of its own is not at 110 Hz", abs(partials(b_a)[0] - 110) >= 3, "%.1f Hz" % partials(b_a)[0])
