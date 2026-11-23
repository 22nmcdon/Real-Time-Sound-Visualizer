"""The headroom (22 Nov, the first release for testers): no sound the
instrument ships comes out over about -3 dBFS true peak at the default
Output, however big the chord.

Until then the base sine's six-note chord came out at the clamp's ceiling -
the owner's bounce peaked at -0.1 dB and distorted a Mac mini's own speaker -
and every bank sound but one met it on a big chord, since the limiter's
make-up gain lifts what it holds back to its ceiling. The instrument now
puts its limiter's output 3.5 dB down (Instrument::kHeadroom,
scope/instrument.h, which says why there and not elsewhere).

What would go wrong, and what is checked for it, each with its null:

- a sound over the line: the base and every bank preset, as the plugin loads
  them (the setup over the defaults, presets.h's own), struck at velocity 127
  with six keys, eight (Poly's voices, kPolyVoices) and sixteen across the
  keyboard (eight a hand in a split), held three seconds and let go, the
  heard pair read to its true peak - four times oversampled, as a meter
  reads between the samples - and required under -3 dBFS. The null: the same
  chord on the base through a core without the headroom (the trim at one, a
  copy of the core built for it), which reads over the line;
- a meter that reads the samples and not between them: a sine at a quarter
  of the rate whose samples all fall 45 degrees off its peaks, 0.9 high,
  reads -0.92 dB true peak where its samples say -3.9. The null is the
  samples' own peak, which is that 3 dB short;
- the headroom changing more than the level: a Breathing preset (the loop at
  work, which a change in what it hears would show at once) and the base
  chord, through the core and the copy without the headroom - the heard pair
  the copy's times the trim, sample for sample, and the picture's lanes the
  same to the bit. The null: the copy's heard pair against the core's
  without the factor, which is 3.5 dB out.
"""
import base64, json, os, re, shutil, subprocess

import numpy as np

from pieces.kit import BUILD, CORE, HERE, INCLUDE

RATE = 48000
CHORDS = {
    "six keys": [48, 52, 55, 60, 64, 67],
    "eight keys": [48, 52, 55, 60, 64, 67, 72, 76],
    "sixteen keys": [36, 40, 43, 48, 52, 55, 57, 59, 60, 64, 67, 72, 76, 79, 81, 84],
}
LINE = -3.0       # dBFS true peak
TRIM_DB = -3.5    # what the core is held to put on (kHeadroom)


def bank():
    """The base and the bank as presets.h holds them: [(name, setup)]."""
    text = open(os.path.join(INCLUDE, "scope", "presets.h"), encoding="utf-8").read()
    pieces = re.findall(r'R"preset\((.*?)\)preset"', text, re.S)
    base = re.search(r'R"base\((.*?)\)base"', text, re.S).group(1)
    version = int(re.search(r"kSetupVersion = (\d+)", open(os.path.join(INCLUDE, "scope", "setup.h")).read()).group(1))
    out = [("the base (Plain sine)", json.loads(base))]
    for section in json.loads("".join(pieces)):
        for entry in section[1]:
            out.append((entry[0], entry[1]))
    return out, version


def code(setup, version):
    return base64.b64encode(json.dumps(dict(setup, v=version)).encode()).decode().rstrip("=")


def bare_render(kit):
    """render_cpp against a copy of the core with the headroom at one."""
    root = os.path.join(BUILD, "headroom-bare")
    if os.path.isdir(root): shutil.rmtree(root)
    shutil.copytree(INCLUDE, os.path.join(root, "include"))
    path = os.path.join(root, "include", "scope", "instrument.h")
    text = open(path, encoding="utf-8").read()
    old = "static constexpr float kHeadroom = 0.66834391756861456f;"
    assert text.count(old) == 1, "instrument.h: kHeadroom is not where the piece expects it"
    open(path, "w", encoding="utf-8").write(text.replace(old, "static constexpr float kHeadroom = 1.0f;"))
    exe = os.path.join(root, "render_bare")
    subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(root, "include"),
                    os.path.join(HERE, "tools", "render_cpp.cpp"), "-o", exe], check=True)
    return exe


def play(exe, setup_code, notes, lanes=False):
    """The heard pair (and the picture's lanes) of a chord struck at 0.9 s, held 3 s, let go and heard 2 s more."""
    tag = "%d-%d" % (os.getpid(), abs(hash((exe, setup_code, tuple(notes)))) % 10**9)
    heard, ring, script = (os.path.join(BUILD, "headroom-%s.%s" % (tag, x)) for x in ("heard", "lanes", "txt"))
    lines = [["make", RATE, setup_code], ["record", "heard", heard]] + ([["record", "lanes", ring]] if lanes else []) \
        + [["to", 0.9]] + [["midi", 0x90, n, 127] for n in notes] + [["to", 3.9]] \
        + [["midi", 0x80, n, 0] for n in notes] + [["to", 5.9]]
    with open(script, "w") as f: f.write("\n".join(json.dumps(l) for l in lines) + "\n")
    subprocess.run([exe, script], check=True, capture_output=True)
    x = np.fromfile(heard, dtype=np.float32).reshape(-1, 2)
    g = np.fromfile(ring, dtype=np.float32) if lanes else None
    for p in (heard, ring, script):
        if os.path.exists(p): os.remove(p)
    return x, g


# Four times oversampled, by the spectrum zero-padded: the signal band-limited and read between its
# samples, as a true-peak meter reads it, exactly where a meter's filter is near enough. Each render starts
# and ends in silence, so treating it as one period puts no edge in it.
def true_peak_db(x):
    peak = 0.0
    for ch in np.atleast_2d(x.T if x.ndim == 2 else x).astype(np.float64):
        n = len(ch)
        spec = np.fft.rfft(ch)
        up = np.fft.irfft(spec, 4 * n) * 4
        peak = max(peak, float(np.max(np.abs(up))))
    return 20 * np.log10(max(peak, 1e-12))


def run(kit):
    check, null = kit.check, kit.null
    sounds, version = bank()
    render = kit.build("render_cpp")

    # The meter itself, before anything is read with it.
    t = np.arange(RATE)
    off = 0.9 * np.sin(2 * np.pi * t / 4 + np.pi / 4)
    tp, sp = true_peak_db(off), 20 * np.log10(np.max(np.abs(off)))
    check("the true-peak meter reads between the samples: a quarter-rate sine 45 degrees off, 0.9 high, reads -0.92 dB",
          abs(tp - 20 * np.log10(0.9)) < 0.05, "%.2f dB" % tp)
    null("its samples alone read it 3 dB short", sp < tp - 2.9, "%.2f dB" % sp)

    worst = []
    for name, setup in sounds:
        c = code(setup, version)
        peaks = {k: true_peak_db(play(render, c, notes)[0]) for k, notes in CHORDS.items()}
        worst.append((max(peaks.values()), name))
        check("%s stays under %.0f dBFS true peak on a big chord at velocity 127" % (name, LINE),
              all(v < LINE for v in peaks.values()), ", ".join("%s %.2f" % kv for kv in peaks.items()))
    print("      the loudest: %s at %.2f dBFS true peak" % (max(worst)[1], max(worst)[0]))

    bare = bare_render(kit)
    base_code = code(sounds[0][1], version)
    over = true_peak_db(play(bare, base_code, CHORDS["six keys"])[0])
    null("the base's six-key chord through a core without the headroom is over the line", over > LINE, "%.2f dB" % over)

    # Only the level: a Breathing preset, where the loop would show any change in what it hears, and the base chord.
    breathing = next(n for n, s in sounds if s.get("pictureAmount", 60) > 0 and s.get("oscScan", 0) > 0)
    trim = 10 ** (TRIM_DB / 20)
    for name, notes in ((breathing, CHORDS["six keys"]), (sounds[0][0], CHORDS["eight keys"])):
        c = code(dict(sounds)[name], version)
        (a, la), (b, lb) = play(render, c, notes, lanes=True), play(bare, c, notes, lanes=True)
        diff = float(np.max(np.abs(a.astype(np.float64) - b.astype(np.float64) * trim)))
        check("%s: the heard pair is the unlimited-headroom core's times %.1f dB, sample for sample" % (name, TRIM_DB),
              len(a) == len(b) and diff < 1e-6, "largest difference %.2e" % diff)
        check("%s: and the picture's lanes are the same to the bit" % name, la is not None and np.array_equal(la, lb),
              "%d samples" % (0 if la is None else len(la)))
        raw = float(np.max(np.abs(a.astype(np.float64) - b.astype(np.float64))))
        null("%s: without the factor the two are not the same" % name, raw > 0.05, "largest difference %.3f" % raw)
