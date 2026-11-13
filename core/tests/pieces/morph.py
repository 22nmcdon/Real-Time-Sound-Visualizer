"""The waveform morph, on the core: the stations are the shapes, the walk
between them is continuous, the fundamental survives it, it is band-limited
moved or still, a key on it moves the sound, and B plays its own position.

These were morphtest.py's on ?brain=js until stage 5's step 3, batch 4 (13
Nov): there the page's own JavaScript `waveAt`, and a `makeGeneratorCore`
built in the page with an LFO and a route put on its morph slot by hand, and
a key held on the page's brain read off the page's generator's window. Here
the core's `scope::waveAt` (functions_cpp), the core's generator
(generator_cpp: `set`, a route from LFO 1 on the morph slot, two layers) and,
for the key, the whole instrument (instrument_cpp). The panel, the hands'
editing, codes and search stayed in morphtest.py, on the default page.
Spectra are numpy's, on windows a whole number of hertz wide.
"""
import base64, json, math, os, re
import numpy as np

RATE = 44100
N = 44100
BH = [0.35875, 0.48829, 0.14128, 0.01168]
MORPH = 16      # the generator's slot (scope/generator.h, slot::Morph)


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


def setup_code(fields):
    v = int(re.search(r"kSetupVersion = (\d+)", open(os.path.join(os.path.dirname(__file__), "..", "..", "include",
                                                                  "scope", "setup.h")).read()).group(1))
    return base64.b64encode(json.dumps(dict({"v": v}, **fields)).encode()).decode().rstrip("=")


def run(kit):
    check, null = kit.check, kit.null

    def calls(lines):
        return kit.floats("functions_cpp", "\n".join(lines))

    def gen(events, n, lanes=(0,), skip=0, lfo0="sine,0.2"):
        blocks = -(-(n + skip) // 128) * 128
        out = kit.floats("generator_cpp", "run rate=%r slots=32 seed=3 samples=%d lfo0=%s lfo1=sine,0.2\n%s\nend"
                         % (float(RATE), blocks, lfo0, "\n".join(events)))
        return [out[skip * 6 + k:(skip + n) * 6:6] for k in lanes]

    def core(morph, freq, n=N, routes=None, lfo0="sine,0.2"):
        """morphtest's CORE: the morph at a position, the frequency, amp 0.9, unison."""
        ev = ["at 0 set shape morph", "at 0 set morph %r" % morph, "at 0 set freq %r" % freq,
              "at 0 set amp 0.9", "at 0 set interval 0"]
        if routes: ev.append("at 0 routes %s" % routes)
        return gen(ev, n, lfo0=lfo0)[0]

    # morphtest :107: at 2 kHz, so the band-limiting does something at every
    # edge, each whole station against the shape itself, sample for sample:
    # the saw a half-cycle on, as the morph turns it to the others' sense.
    step = 2000 / RATE
    phases = [(2 * math.pi * i * step) % (2 * math.pi) for i in range(4410)]
    want = {0: ["waveAt sine %r %r - 0" % (ph, step) for ph in phases],
            1: ["waveAt triangle %r %r - 0" % (ph, step) for ph in phases],
            2: ["waveAt ramp %r %r - 0" % (ph + math.pi, step) for ph in phases],
            3: ["waveAt square %r %r - 0" % (ph, step) for ph in phases]}
    shapes = {k: calls(v) for k, v in want.items()}
    morphs = {k: calls(["waveAt morph %r %r - %d" % (ph, step, k) for ph in phases]) for k in range(4)}
    worst = [max(abs(a - b) for a, b in zip(morphs[k], shapes[k])) for k in range(4)]
    check("at 0, 1, 2 and 3 the morph is the sine, the triangle, the saw and the square, exactly", worst == [0, 0, 0, 0],
          str(worst))
    # The null: the saw station against the saw not turned round, the fault
    # the docstring names.
    upright = calls(["waveAt ramp %r %r - 0" % (ph, step) for ph in phases])
    null("the saw station against the saw not turned round differs",
         max(abs(a - b) for a, b in zip(morphs[2], upright)) > 0.5)

    # :126: every phase a cycle visits, the position walked in thousandths.
    lines, grid = [], []
    for i in range(64):
        ph = 2 * math.pi * i / 64 + 0.013
        lines += ["waveAt morph %r 0 - %r" % (ph, m / 1000) for m in range(3001)]
    v = np.array(calls(lines)).reshape(64, 3001)
    sweep = float(np.abs(np.diff(v, axis=1)).max())
    check("a thousandth of a station moves no sample by more than two thousandths", sweep < 0.002, "%.5f" % sweep)
    # The null: the same samples read at the nearest whole station - a morph
    # that steps rather than crossfades - move by far more where a station turns.
    stepped = v[:, [round(m / 1000) * 1000 for m in range(3001)]]
    null("a morph that steps between stations fails it", float(np.abs(np.diff(stepped, axis=1)).max()) >= 0.002,
         "%.3f" % float(np.abs(np.diff(stepped, axis=1)).max()))

    # :137, :139: the generator's fundamental at 220 Hz against the sine's.
    fund = {}
    for m in [i / 4 for i in range(13)]:
        spec, hz = spectrum(core(m, 220))
        fund[m] = level_at(spec, hz, 220)
    rel = {m: round(f / fund[0], 3) for m, f in fund.items()}
    check("it never falls below the saw's own, 0.64 of the sine's - the lowest station",
          min(rel.values()) >= 0.63, "%s" % rel)
    check("and between the triangle and the saw it goes smoothly from one to the other",
          rel[1.25] > rel[1.5] > rel[1.75] and abs(rel[1.5] - (rel[1.0] + rel[2.0]) / 2) < 0.01,
          "%s, %s, %s" % (rel[1.25], rel[1.5], rel[1.75]))
    # The null: half-way from the core's triangle to its saw *not* turned
    # round, the upside-down saw the docstring names, cancels the note.
    tri = np.array(kit.run("functions_cpp", "waveRun triangle 220 44100 44100 1 0 -").split(), dtype=float)
    saw = np.array(kit.run("functions_cpp", "waveRun ramp 220 44100 44100 1 0 -").split(), dtype=float)
    sin = np.array(kit.run("functions_cpp", "waveRun sine 220 44100 44100 1 0 -").split(), dtype=float)
    spec, hz = spectrum((tri + saw) / 2)
    sspec, shz = spectrum(sin)
    flipped = level_at(spec, hz, 220) / level_at(sspec, shz, 220)
    null("half-way to a saw not turned round falls under the bound", flipped < 0.63, "%.3f of the sine's" % flipped)

    # :156, :165: aliasing, still and swept, below 10 kHz at 4 kHz.
    def floor(x, f0, near=None):
        spec, hz = spectrum(x)
        near = near or 4 * RATE / len(x)
        grid = np.zeros(len(spec), dtype=bool)
        grid[:6] = True
        k = 1
        while k * f0 < RATE / 2:
            grid |= np.abs(hz - k * f0) < near
            k += 1
        return db(spec[~grid & (hz < 10000)].max(), level_at(spec, hz, f0))
    still = {m: round(floor(core(m, 4000), 4000), 1) for m in (0.5, 1.5, 2.5)}
    check("half-way between each pair, at 4 kHz, nothing folds back above -45 dB",
          all(x <= -45 for x in still.values()), str(still))
    # An oscillator at 3 Hz on the position, the whole range (route from LFO 1
    # at depth one; a station and a half each way from 1.5). Its sidebands sit
    # at multiples of three hertz either side of each harmonic, so the grid is
    # 40 Hz wide; folding from 4 kHz lands 100 Hz off a harmonic.
    moved = floor(core(1.5, 4000, routes="0/0/0/%d/1/1/0" % MORPH, lfo0="sine,3"), 4000, near=40)
    check("and with an oscillator sweeping it end to end, still nothing above -45 dB", moved <= -45, "%.1f dB" % moved)
    # The nulls: the same stations with no band-limiting (waveRun at step
    # nought) fold back far above it, still and swept.
    raw = np.array(kit.run("functions_cpp", "waveRun morph 4000 44100 44100 0 1.5 -").split(), dtype=float)
    null("the same position without band-limiting folds back above -45 dB", floor(raw, 4000) > -45,
         "%.1f dB" % floor(raw, 4000))
    swept = floor(core(1.5, 4000, routes="0/0/0/%d/1/1/0" % MORPH, lfo0="sine,3"), 4000)
    null("and the swept sound read on a grid with no room for its sidebands has them above -45 dB", swept > -45,
         "%.1f dB" % swept)

    # :236, :238: a key at full velocity routed to Morph, from the sine. On
    # the page midiNoteOn on the page's brain, its routing compiled by the
    # page; here the instrument whole, its heard pair at 48 kHz.
    def second(depth, at=0):
        code = setup_code({"shape": "morph", "morph": at, "freq": 220})
        lines = [["make", 48000, 128, code], ["click", "midiMono"], ["routings", "midi.key>gen.morph@%r" % depth],
                 ["midi", 0x90, 57, 127]] + [["block", 128]] * 420
        blocks = [l for l in kit.instrument(lines) if l.startswith("block ")][45:420]
        x = [float(v) for l in blocks for v in l.split()[1:129]][:48000]
        spec, hz = spectrum(x, 48000)
        return db(level_at(spec, hz, 440, 48000), level_at(spec, hz, 220, 48000))
    down, up = second(0), second(1)
    # From the sine full depth is a station and a half: half-way from the
    # triangle to the saw. On the page's bare core that read the half-saw's
    # -13.2 dB exactly (only the saw has even harmonics, half of its 1/2
    # against a fundamental of (0.81 + 0.64) / 2). The instrument's heard
    # sound is not flat between 220 and 440 Hz (drawbar.py found the same, 2.8
    # dB), so "the half-saw" is restated as the morph set at 1.5 in the setup
    # itself, to the page's 0.3 dB (they read 0.12 apart) - and the bare generator at 1.5 is held
    # to the formula below, so the station is still the half-saw.
    set15 = second(0, 150)
    check("a key on Morph moves the sound: a sine with none of the saw's second harmonic", down < -80, "%.1f dB" % down)
    check("and at full, a station and a half on: as the morph set at 1.5 in the setup, to 0.3 dB", abs(up - set15) < 0.3,
          "%.2f dB against %.2f" % (up, set15))
    x15 = core(1.5, 220)
    spec, hz = spectrum(x15)
    bare = db(level_at(spec, hz, 440), level_at(spec, hz, 220))
    want = 20 * math.log10(0.5 * (2 / math.pi) * 0.5 / (0.5 * (8 / math.pi ** 2 + 2 / math.pi)))
    check("and 1.5 is the half-saw: the generator's second harmonic there is %.1f dB" % want, abs(bare - want) < 0.3,
          "%.2f dB" % bare)
    nearly = second(0.9)
    null("at nine tenths of the depth it is not where 1.5 is", abs(nearly - set15) >= 0.3, "%.2f dB" % nearly)
    null("and 1.25 is not the half-saw", abs(db(*(lambda s, h: (level_at(s, h, 440), level_at(s, h, 220)))(*spectrum(core(1.25, 220)))) - want) >= 0.3)

    # :292: A at the square, B at the sine, a note on both layers.
    def layered(b_morph):
        a, b = gen(["at 0 set shape morph", "at 0 set morph 3", "at 0 set shape morph 1", "at 0 set morph %r 1" % b_morph,
                    "at 0 set amp 0.9 1", "at 0 voices 0 57/220.0/1.0/xy", "at 0 voices 1 57/220.0/1.0/xy"],
                   44100, lanes=(0, 4), skip=8192)
        third = []
        for x in (a, b):
            spec, hz = spectrum(x)
            third.append(db(level_at(spec, hz, 660), level_at(spec, hz, 220)))
        return third
    ta, tb = layered(0)
    check("and B sounds its own: A's square has its third harmonic at -9.5 dB, B's sine none",
          abs(ta - 20 * math.log10(1 / 3)) < 0.3 and tb < -100, "A %.1f dB, B %.1f dB" % (ta, tb))
    null("B at A's square has the third harmonic", layered(3)[1] > -100)
