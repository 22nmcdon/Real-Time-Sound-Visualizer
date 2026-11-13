"""The keyboard on the core: its parser, the dyad, Hold, mono, tuning, the
wheel and the note as the lag's truth - miditest.py's numbers rows.

These were miditest.py's on `?brain=js` until stage 5, step 3, batch 4 (13
Nov): there they read `state.source.settings` (the page's generator's freq,
interval and octaves), `intervalRatio` in the page, the page's own
generator's samples, `genSettings().vibrato` and the page's `lagLock`. On
the default site every one of those is the face's mirror, written by the
page's own MIDI apply, so moved unchanged they would have passed on the
page's arithmetic. Here the instrument whole (instrument_cpp: the port's
bytes in at the top of a block, the panel's clicks and switches as the page
sends them, the generator's tone and the keyboard's notes read back by its
`tone` command, and the heard pair), the core's keyboard on raw bytes
(keyboard_cpp's `bytes`), and the core's `intervalRatio` (functions_cpp).
The face's rows - the panel, the credit line, the timebase, the tuner, the
codec - stay in miditest.py, on the default page. Each check has its null.
"""
import math

from pieces.pulse import setup_code

RATE = 48000
HZ = lambda note: 440 * 2 ** ((note - 69) / 12)


def hz_of(x, rate=RATE):
    """A sine's frequency by its rising zero crossings, each placed between
    its two samples: good to a part in a million over a second."""
    ups = [i + x[i] / (x[i] - x[i + 1]) for i in range(len(x) - 1) if x[i] < 0 <= x[i + 1]]
    return (len(ups) - 1) * rate / (ups[-1] - ups[0]) if len(ups) > 2 else None


def run(kit):
    check, null = kit.check, kit.null

    def play(steps, code=None):
        """The instrument through `steps`: ("on", n[, vel]), ("off", n), ("cc", n, v),
        ("click", id), ("control", id, v), ("slider", id, v), ("tone",) or
        ("hear", frames). Each message is followed by a block, so it has landed
        before the next; what comes back is a list of the tone readings and the
        heard pairs, in order."""
        lines = [["make", RATE, 128, code or setup_code({"shape": "sine"})]]
        for s in steps:
            if s[0] == "on": lines += [["midi", 0x90, s[1], s[2] if len(s) > 2 else 100], ["block", 128, 1000]]
            elif s[0] == "off": lines += [["midi", 0x80, s[1], 0], ["block", 128, 1000]]
            elif s[0] == "cc": lines += [["midi", 0xB0, s[1], s[2]], ["block", 128, 1000]]
            elif s[0] in ("click", "control", "slider"): lines += [list(s), ["block", 128, 1000]]
            elif s[0] == "tone": lines.append(["tone"])
            elif s[0] == "hear": lines += [["block", s[1]]]
            elif s[0] == "wait": lines += [["block", 4800, 1000]] * s[1]
        out, hears = [], [i for i, s in enumerate(steps) if s[0] == "hear"]
        it = iter(kit.instrument(lines))
        for s in steps:
            if s[0] == "tone":
                line = next(l for l in it if l.startswith("tone "))
                w = line.split()
                notes = w[w.index("notes") + 1:w.index("A")]
                out.append({"freq": float(w[1]), "interval": int(w[2]), "octaves": float(w[3]), "just": w[4] == "1",
                            "vibrato": float(w[5]), "notes": [int(n) for n in notes],
                            "lag": None if w[-1] == "-" else float(w[-1])})
            elif s[0] == "hear":
                v = [float(x) for x in next(l for l in it if l.startswith("block ") and len(l) > 200000).split()[1:]]
                out.append((v[:s[1]], v[s[1]:2 * s[1]]))
        return out

    def is_unison(t, note):
        return abs(t["freq"] - HZ(note)) < 0.01 and t["interval"] == 0 and t["octaves"] == 0

    # --- the core's parser, on the bytes a port hands it whole (miditest :116 to :155) ---
    # On the default page these rows read `midi.notes`, the face's stack; what
    # the instrument plays is the core keyboard's, read here off keyboard_cpp.
    def notes(cmds):
        lines = kit.run("keyboard_cpp", "run\n" + "\n".join(cmds) + "\nend").strip().split("\n")
        return [l.split(" notes ")[1].split(" ")[0] for l in lines]
    held = lambda s: [] if s == "-" else [int(h.split("/")[0]) for h in s.split("+")]
    r = [held(s) for s in notes(["bytes 0x90,60,100", "bytes 0x90,60,0", "bytes 0x90,60,100,64,100,67,100",
                                 "bytes 0x80,60,0,64,0,67,0", "bytes 0x90,60,100", "bytes 0x90,60,100", "bytes 0x80,60,0",
                                 "bytes 0xF8,0x90,62,100,0xF8", "cc 123 0",
                                 # A clock byte between two notes under one running status, and one
                                 # inside a note: the clock must leave the running status standing
                                 # (a parser that cancelled it lost the 64 here, which the line above,
                                 # its clock before the status byte, could not see - the mutation pass).
                                 "bytes 0x90,60,100,0xF8,64,100", "bytes 0x90,0xF8,65,100", "cc 123 0"])]
    check("the core's keyboard: a note-on holds the note, and at velocity nought lets it go", r[0] == [60] and r[1] == [], str(r[:2]))
    check("running status: one status byte, three notes, on and off", r[2] == [60, 64, 67] and r[3] == [], str(r[2:4]))
    check("the same note twice does not stack, so one release ends it", r[5] == [60] and r[6] == [], str(r[5:7]))
    check("a clock byte is not mistaken for a note, between messages, inside one, or under running status",
          r[7] == [62] and r[9] == [60, 64] and r[10] == [60, 64, 65], str([r[7], r[9], r[10]]))
    check("and all-notes-off, which the page's panic sends the instrument, releases everything", r[8] == [], str(r[8]))
    null("the same bytes with the running status cut after the first note hold one", held(notes(["bytes 0x90,60,100"])[0]) != [60, 64, 67])
    null("and a note held with no all-notes-off is still held", held(notes(["bytes 0x90,62,100", "bytes 0xB0,7,0"])[1]) == [62])

    # --- the dyad (miditest :171 to :201) ---
    t = play([("click", "midiDyad"), ("click", "tuneJust"), ("tone",),
              ("on", 60), ("tone",), ("on", 67), ("tone",),
              ("off", 67), ("off", 60), ("on", 67), ("on", 60), ("tone",),
              ("cc", 123, 0), ("on", 60), ("on", 67), ("on", 64), ("tone",),
              ("off", 67), ("tone",),
              ("cc", 123, 0), ("on", 60), ("on", 67), ("off", 67), ("tone",)])
    rest, one, up, down, three, after, lone = t
    check("nothing held, the keyboard holds nothing", rest["notes"] == [], str(rest["notes"]))
    check("one note is a unison at its own pitch", is_unison(one, 60), str(one))
    check("two notes are the lower pitch and the interval above it",
          abs(up["freq"] - HZ(60)) < 0.01 and up["interval"] == 7 and up["octaves"] == 0, str(up))
    null("and the pair is not a unison", not is_unison(up, 60))
    check("and the press order does not turn the figure over",
          abs(down["freq"] - up["freq"]) < 1e-9 and down["interval"] == up["interval"], "%s vs %s" % (down, up))
    check("a third note displaces the older of the pair",
          abs(three["freq"] - HZ(64)) < 0.01 and three["interval"] == 3, str(three))
    null("the third note's pair is not the first pair", not (abs(three["freq"] - HZ(60)) < 0.01 and three["interval"] == 7))
    check("releasing one of the pair promotes what was under it",
          abs(after["freq"] - HZ(60)) < 0.01 and after["interval"] == 4, str(after))
    check("back to one note is back to a unison", lone["interval"] == 0 and is_unison(lone, 60), str(lone))

    # --- Hold (:210, :212): the switch as the page sends it ---
    kept, walked = play([("click", "midiDyad"), ("control", "midiHold", True),
                         ("on", 60), ("on", 67), ("off", 67), ("tone",), ("off", 60), ("on", 62), ("tone",)])
    unheld, = play([("click", "midiDyad"), ("on", 60), ("on", 67), ("off", 67), ("tone",)])
    check("with Hold on the interval stays above the one note",
          kept["interval"] == 7 and abs(kept["freq"] - HZ(60)) < 0.01, str(kept))
    check("and walks with it", walked["interval"] == 7 and abs(walked["freq"] - HZ(62)) < 0.01, str(walked))
    null("Hold off, the same hand is back to a unison", unheld["interval"] != 7, str(unheld))

    # --- wider than an octave, and the ratios (:219, :232, :234, :249, :251) ---
    wide, = play([("click", "midiDyad"), ("on", 60), ("on", 79), ("tone",)])
    check("nineteen semitones is a fifth plus an octave", wide["interval"] == 7 and wide["octaves"] == 1, str(wide))
    null("and not a fifth alone", not (wide["interval"] == 7 and wide["octaves"] == 0))
    def ratio(t, just):
        return kit.floats("functions_cpp", "intervalRatio %d %d" % (t["interval"], 1 if just else 0))[0] * 2 ** t["octaves"]
    check("a wide dyad is 3:1 in just tuning", abs(ratio(wide, True) - 3) < 1e-12, "%r" % ratio(wide, True))
    check("and 2^(19/12) in equal", abs(ratio(wide, False) - 2 ** (19 / 12)) < 1e-12, "%r" % ratio(wide, False))
    null("the just ratio is not the equal one", abs(ratio(wide, True) - 2 ** (19 / 12)) > 1e-3)
    fifth, = play([("click", "midiDyad"), ("on", 57), ("on", 64), ("tone",)])
    check("a played fifth is exactly 3:2 in just tuning", ratio(fifth, True) == 1.5, "%r" % ratio(fifth, True))
    check("and the tempered ratio in equal", abs(ratio(fifth, False) - 2 ** (7 / 12)) < 1e-12, "%r" % ratio(fifth, False))

    # --- the note in the samples (:263, :290, :293, :296): the heard pair ---
    n = RATE
    just, = play([("click", "midiDyad"), ("click", "tuneJust"), ("on", 57), ("on", 64), ("wait", 4), ("hear", n)])
    tempered, = play([("click", "midiDyad"), ("click", "tuneEqual"), ("on", 57), ("on", 64), ("wait", 4), ("hear", n)])
    jl, jr = hz_of(just[0]), hz_of(just[1])
    el_, er = hz_of(tempered[0]), hz_of(tempered[1])
    check("and the note is in the samples: A3 on the left, a just fifth above it on the right",
          abs(jl - HZ(57)) < 2 and abs(jr / jl - 1.5) < 0.01, "%.4f, %.4f" % (jl, jr))
    null("the samples are not a fourth", abs(jr / jl - 4 / 3) > 0.01)
    claimed = abs(2 * HZ(57) * 2 ** (7 / 12) - 3 * HZ(57))
    beat = abs(2 * er - 3 * el_)
    check("in equal the samples carry the tempered ratio", abs(er / el_ - 2 ** (7 / 12)) < 1e-4, "%.7f" % (er / el_))
    check("and the figure turns at the rate a tempered fifth beats at, 0.745 Hz at A3",
          abs(beat - claimed) < 0.05, "%.3f Hz measured, %.3f claimed" % (beat, claimed))
    check("in just it is 3:2 and stands still", abs(jr / jl - 1.5) < 1e-4 and abs(2 * jr - 3 * jl) < 0.05,
          "%.7f, %.4f Hz" % (jr / jl, abs(2 * jr - 3 * jl)))
    null("the just pair does not beat at the tempered rate", abs(abs(2 * jr - 3 * jl) - claimed) > 0.05)

    # --- mono (:309, :311, :324) ---
    mono, = play([("control", "interval", "4"), ("click", "midiMono"), ("on", 60), ("on", 67), ("tone",)])
    check("mono takes the newest note as the pitch", abs(mono["freq"] - HZ(67)) < 0.01, str(mono))
    check("and leaves the interval to the menu", mono["interval"] == 4, str(mono))
    null("the dyad's pitch for the same keys is the older", abs(up["freq"] - HZ(67)) > 1)
    dy, mo = play([("control", "interval", "4"), ("click", "midiDyad"), ("on", 48), ("on", 76), ("tone",),
                   ("click", "midiMono"), ("tone",)])
    check("and does not inherit the dyad's octaves",
          dy["octaves"] == 2 and mo["octaves"] == 0 and mo["interval"] == 4, "%s then %s" % (dy, mo))

    # --- the wheel (:355): the null of miditest's "controllers moved are learned as nothing" ---
    rest, moved, other = play([("tone",), ("cc", 1, 127), ("tone",), ("cc", 1, 0), ("cc", 16, 127), ("tone",)])
    check("the wheel still sets the vibrato, on the instrument", moved["vibrato"] > 0.3 and rest["vibrato"] == 0,
          "%r from %r" % (moved["vibrato"], rest["vibrato"]))
    null("and a controller that is not the wheel sets none", other["vibrato"] == 0, str(other["vibrato"]))

    # --- the note as ground truth (:390, :402): the automatic lag ---
    # A held A4, then the frequency moved off it to 100 Hz, as the page's
    # check did: with the note as the truth the lag is the note's quarter
    # period, exactly; without, the estimator's on what sounds.
    lag = setup_code({"shape": "sine", "lagOn": True, "lagAuto": True})
    def locked(truth):
        return play([("click", "midiDyad"), ("control", "midiTruth", truth), ("on", 69), ("slider", "freq", "100"),
                     ("wait", 30), ("tone",)], lag)[0]["lag"]
    on, off = locked(True), locked(False)
    check("with a note held the lag is a quarter period of the note, exactly", on == 0.25 / 440, "%r vs %r" % (on, 0.25 / 440))
    check("and without it the estimator is back, on the signal that is there",
          off is not None and abs(off - 0.25 / 100) < 0.25 / 100 * 0.05, str(off))
    null("the estimator's lag is not the note's", off != 0.25 / 440)
