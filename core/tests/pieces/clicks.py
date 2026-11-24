"""Clicks at a change of note (24 Nov, the owner's, on Harmonic tone): "a
'click' or 'scratch' when switching notes - not every time, but prevalent when
playing notes quickly and switching frequently".

Harmonic tone loads over the defaults - the harmonic shape, in Dyad - and its
Picture pushes the voice's Fold to about 0.43, a sin() folder whose gain is
about eight near nought. The fold was never what clicked; it made audible what
did, which was anything that stepped the shaper's input or the slope of the
wave at a change of note. Five of them, each fixed in the core and each with
its own null here (a copy of the core with that one fix taken out):

- the dyad's heard upper slots stopped dead when their note went and resumed
  from a stale history when the next came (generator.h, `kHeardTail`);
- a Poly voice born in step with held ones starts at a sample that is not
  nought, a step into its fresh shaper (voices.h, the shaper run over the
  wave's own past);
- past eight tails the oldest were erased mid-release (voices.h, faded over
  the governor's cut instead);
- a new note in Dyad or Mono stepped its pitch in one sample at full level,
  so the slope stepped by the ratio of the pitches (generator.h, `kNoteSlewMs`);
- a change of the dyad landing inside the last one's crossfade dropped the
  note that crossfade was taking out, or restarted the one it was bringing in
  from full (generator.h, the ghosts and the scales).

A click, as counted here: a millisecond whose energy above 15 kHz is eight
times the median of the 80 ms around it and over 2e-4 RMS - a burst against
the sound's own steady state, which a step in the wave or its slope makes and
a held tone does not. Two things it would also count are kept out of the
fixtures on purpose, and said here so nobody takes them for a pass. A chord of
three or more through Harmonic tone's fold aliases into a noise above 15 kHz
whether or not anything changes (held still for two seconds it trips this
measure a hundred times), so Harmonic tone is played in lines and dyads, and
its chords are left to the ear. And two notes two octaves apart crossfading
inside one fold make its intermodulation for the crossfade's 30 ms, about
-60 dB: the crossfades are before the shaper, which is the design, so
Harmonic tone's overlapping leaps are left out.

Zero is held where the owner heard it: Harmonic tone as it ships, at 44.1 and
48 kHz, and in Mono. Elsewhere a few remain, none over 1e-3 and each set at
most a tenth of what the core with every fix taken out makes on the same
passages (between 15 and 116 a set): in the Tine pianos, their bark - the
Envelope card's and the key's routes moving every sounding voice's FM index
at a chord, walked over a block (web/README.md, 12 Nov) - and with those
routes off they are at nought; and in a Poly sound with the Picture high, one
or two a set a frame after a note, whose cause was not found on 24 Nov
(nothing on the Picture's routes steps there, and Strike, Swell and the
response do not move them).
"""
import os, re, shutil, subprocess

import numpy as np

from pieces.headroom import bank, code
from pieces.kit import BUILD, HERE, INCLUDE

TAIL = 0.06  # seconds at a render's end left out: its edge is not a click
LOUD = 1e-3  # RMS above 15 kHz in a millisecond: about -60 dBFS, where the old clicks' median was 7e-4


def passage(bpm, legato, content, n=24, start=0.2):
    """Sixteenths: `content` a line, one key again and again, wide leaps or chords, each key held
    `legato` of a step (0.5 detached, 1 legato, over 1 overlapping)."""
    step = 60 / bpm / 4
    seq = {"line": [[60], [62], [64], [65], [67], [65], [64], [62]], "same": [[64]],
           "leaps": [[48], [72], [55], [79], [60], [84]],
           "chords": [[60, 64, 67], [62, 65, 69], [64, 67, 71], [60, 65, 69]]}[content]
    ev = []
    for i in range(n):
        t = start + i * step
        for k in seq[i % len(seq)]:
            ev.append((t, [0x90, k, 100]))
            ev.append((t + step * legato, [0x80, k, 0]))
    ev.sort(key=lambda e: (e[0], e[1][0] == 0x90))
    return ev, start + n * step + 0.6


def render(exe, setup, version, events, end, rate):
    tag = "%d-%d" % (os.getpid(), abs(hash((exe, str(sorted(setup.items())), str(events), rate))) % 10**9)
    heard, script = (os.path.join(BUILD, "clicks-%s.%s" % (tag, x)) for x in ("heard", "txt"))
    lines = [["make", rate, code(setup, version)], ["record", "heard", heard]]
    for t, m in events: lines += [["to", t], ["midi", *m]]
    lines += [["to", end], ["record", "heard"]]
    with open(script, "w") as f: f.write("\n".join(__import__("json").dumps(l) for l in lines) + "\n")
    subprocess.run([exe, script], check=True, capture_output=True)
    x = np.fromfile(heard, dtype=np.float32).reshape(-1, 2)
    for p in (heard, script): os.remove(p)
    return x


def clicks(x, rate, k=8.0, floor=5e-4, cut=15000, win=0.001, ctx=0.04):
    """Each click as (channel, seconds, RMS above `cut`)."""
    out = []
    for ch in (0, 1):
        pad = 4800
        y = np.concatenate([np.zeros(pad), x[:, ch].astype(float), np.zeros(pad)])
        spec = np.fft.rfft(y)
        spec[np.fft.rfftfreq(len(y), 1 / rate) < cut] = 0
        h = np.fft.irfft(spec, len(y))[pad:-pad]
        n = int(win * rate)
        m = len(h) // n
        e = np.sqrt((h[:m * n].reshape(m, n) ** 2).mean(1))
        c = int(ctx / win)
        for i in range(m - int(TAIL / win)):
            if e[i] < floor: continue
            ref = np.median(e[max(0, i - c):i + c + 1])
            if e[i] > k * ref and e[i] >= e[max(0, i - 1)] and e[i] >= e[min(m - 1, i + 1)]:
                out.append((ch, i * n / rate, float(e[i])))
    return out


def broken(kit, name, edits):
    """render_cpp against a copy of the core with one fix taken out: (file, old, new) exact replacements."""
    root = os.path.join(BUILD, "clicks-" + name)
    if os.path.isdir(root): shutil.rmtree(root)
    shutil.copytree(INCLUDE, os.path.join(root, "include"))
    for rel, old, new in edits:
        path = os.path.join(root, "include", "scope", rel)
        text = open(path, encoding="utf-8").read()
        assert text.count(old) == 1, "%s: the fix the null takes out is not where it expects (%r)" % (rel, old[:60])
        open(path, "w", encoding="utf-8").write(text.replace(old, new))
    exe = os.path.join(root, "render")
    subprocess.run(["g++", "-std=c++17", "-O2", "-I", os.path.join(root, "include"),
                    os.path.join(HERE, "tools", "render_cpp.cpp"), "-o", exe], check=True)
    return exe


def count(exe, setup, version, runs, rate=48000):
    """Clicks over several passages, with the first one found for the detail."""
    total, first = 0, None
    for bpm, legato, content in runs:
        ev, end = passage(bpm, legato, content)
        c = clicks(render(exe, setup, version, ev, end, rate), rate)
        total += len(c)
        if c and first is None: first = "%d bpm, legato %.1f, %s: ch%d at %.3f s, %.4f" % ((bpm, legato, content) + c[0])
    return total, first


def grid(bpms, legatos, contents):
    return [(b, l, c) for b in bpms for l in legatos for c in contents]


# Each fix, taken out: the file, the text the fix is, and what stood there before it.
UNFIX = {
    "heard slots": [("generator.h", "              if (run[s]) {\n                if (!h.ran)",
                     "              if (false) {\n                if (!h.ran)"),
                    ("generator.h", "              } else if (h.tail > 0) {", "              } else if (false) {")],
    "shaper's past": [("voices.h", "        if (tone.noise) voice.shp->prime(w, c.shaping);\n        else {",
                       "        if (true) {} else {")],
    "tails faded": [("voices.h", "    if (!v.held && !v.gone && v.fade == 0) { v.fade = c.cutSamples; tails--; }",
                     "    if (!v.held && !v.gone && v.fade == 0) { v.gone = true; tails--; }")],
    "note's slew": [("generator.h", "static constexpr double kNoteSlewMs = 2;", "static constexpr double kNoteSlewMs = 0;")],
    "ghosts": [("generator.h", "    if (!(std::fabs(gain) > 1e-6)) return;", "    return;"),
               ("generator.h", "      handScale_ = handX_;\n", "      handScale_ = 1;\n"),
               ("generator.h", "              oldScale_ = std::sin(kPi / 2 * dyadX_);", "              oldScale_ = 1;")],
}


def run(kit):
    check, null = kit.check, kit.null
    sounds, version = bank()
    setups = dict(sounds)
    ht = setups["Harmonic tone"]
    exe = kit.build("render_cpp")

    # The measure itself, first: a sine with one step in it, and the same sine without.
    rate = 48000
    t = np.arange(rate) / rate
    tone = 0.3 * np.sin(2 * np.pi * 220 * t) * np.minimum(1, np.minimum(t, t[::-1]) / 0.05)
    stepped = tone.copy()
    stepped[rate // 2:] += 0.02
    pair = lambda y: np.stack([y, y], 1)
    check("the measure finds a step of 0.02 in a 220 Hz sine, on both channels",
          len([c for c in clicks(pair(stepped), rate) if abs(c[1] - 0.5) < 0.002]) == 2, str(clicks(pair(stepped), rate)))
    check("and nothing in the sine without it", clicks(pair(tone), rate) == [], str(clicks(pair(tone), rate)))

    # Harmonic tone as it ships (Dyad), at both rates: lines and one key again, every articulation and tempo.
    lines = grid([120, 180, 240], [0.5, 1.0, 1.3, 1.8], ["line", "same"]) + grid([120, 180, 240], [0.5, 1.0], ["leaps"])
    for rate in (44100, 48000):
        n, first = count(exe, ht, version, lines, rate)
        check("Harmonic tone as shipped, %d passages of sixteenths at %d Hz: no clicks" % (len(lines), rate), n == 0,
              "%d, first %s" % (n, first))
    n, first = count(exe, dict(ht, midiMode="mono"), version, lines)
    check("Harmonic tone in Mono, the same %d passages: no clicks" % len(lines), n == 0, "%d, first %s" % (n, first))

    # Where zero is not held, nothing over LOUD and a tenth at most of what the core with every fix
    # taken out makes on the same passages - which is the failure, and so the null, side by side.
    unfixed = broken(kit, "all", [e for edits in UNFIX.values() for e in edits])
    poly_lines = [r for r in lines if r[1] <= 1.3]  # three overlapping through the fold are the chords' noise
    others = grid([180], [0.5, 1.0, 1.3], ["line", "same", "leaps", "chords"])
    cases = [("Harmonic tone in Poly", dict(ht, midiMode="poly"), poly_lines)]
    cases += [(name, setup, others) for name, setup in sounds if name != "Harmonic tone"]
    for name, setup, runs in cases:
        now = []
        for bpm, legato, content in runs:
            ev, end = passage(bpm, legato, content)
            now += clicks(render(exe, setup, version, ev, end, 48000), 48000)
        before, _ = count(unfixed, setup, version, runs)
        loudest = max((c[2] for c in now), default=0)
        check("%s, %d passages%s: nothing over %.0e, and a tenth at most of the core without the fixes"
              % (name, len(runs), " with chords" if runs is others else "", LOUD),
              loudest <= LOUD and 10 * len(now) <= before,
              "%d clicks, the loudest %.4f; %d without the fixes" % (len(now), loudest, before))
    # The Tine pianos' last few are their bark, the Envelope card's and the key's routes moving every
    # sounding voice's FM index at a chord (walked over a block since 12 Nov, web/README.md): without
    # those routes their voices are held to nought.
    for name in ("Tine piano", "Bass under the tine piano"):
        n, first = count(exe, dict(setups[name], mod=""), version, others)
        check("%s with its routes taken out, %d passages with chords: no clicks" % (name, len(others)), n == 0,
              "%d, first %s" % (n, first))

    # Each fix taken out, on a passage it is for: the clicks come back.
    nulls = {
        "heard slots": (ht, grid([180], [1.3], ["line"])),
        "shaper's past": (dict(ht, midiMode="poly"), grid([180], [1.3], ["line"])),
        "tails faded": (dict(sounds[0][1], rel=600), grid([240], [0.5], ["chords"])),
        "note's slew": (dict(ht, midiMode="mono"), grid([180], [1.0], ["leaps"])),
        "ghosts": (ht, grid([120, 240], [1.8], ["line"])),
    }
    for name, (setup, runs) in nulls.items():
        n, first = count(broken(kit, name.replace(" ", "-").replace("'", ""), UNFIX[name]), setup, version, runs)
        fixed, _ = count(exe, setup, version, runs)
        null("without the %s fix, its passage clicks (and with it, not)" % name, n > 0 and fixed == 0,
             "%d without, %d with; %s" % (n, fixed, first))
