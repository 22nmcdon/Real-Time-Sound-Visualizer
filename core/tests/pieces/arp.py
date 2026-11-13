"""The arpeggiator on the core (K5): its order, the gather, each step
struck, the tempo, the dyad's intervals, its MIDI out, letting go and
switching off - arptest.py's numbers rows.

These were arptest.py's on `?brain=js` until stage 5, step 3, batch 4 (13
Nov): there the page's own `arpTick` at synthetic times, its `src.gate`
wrapped by hand, `genSettings().voices` and `.interval`, `midi.notes` and a
stubbed port's bytes. On the default site every one of those is the page's
brain beside the instrument (the inventory's `arpTick.step` counter: the
page's arpeggio steps there too, guarded from the port, and the face's notes
follow it), so here they are the core keyboard's, through keyboard_cpp: the
same synthetic times (`at` then `tick`, as the page's frame calls arpTick),
the generator's calls written down as it makes them (`gate`, `set voices`,
`set interval`) and the MIDI out's (`out`, `outoff`). And one render of the
instrument whole (instrument_cpp), where the arpeggiator steps on the audio
clock and its notes go out as bytes, timed by the block they leave in. The
setup code's row and the level a held key reaches through an arpeggiated
setup stay in arptest.py, on the default page. Each check has its null.
"""
from pieces.pulse import setup_code

C, E, G = 60, 64, 67


def parse(out):
    """keyboard_cpp's lines: (command, calls made of the generator and the out, state words)."""
    rows = []
    for line in out.strip().split("\n"):
        head, state = line.split(" | ")
        parts = head.split(" :: ")
        rows.append((parts[0], parts[1:], state.split()))
    return rows


def voices(calls, layer=0):
    """The last voices the generator was given on a layer, as note numbers, or None if it was given none."""
    got = None
    for c in calls:
        w = c.split()
        if w[:2] == ["set", "voices"] and w[3] == str(layer):
            got = [] if w[2] in ("none", "null") else [int(v.split("/")[0]) for v in w[2].split("+")]
    return got


def arp_state(state):
    a = state[state.index("arp") + 1:]
    return {"mode": a[0], "index": int(a[1]), "start": a[2], "steps": float(a[3])}


def run(kit):
    check, null = kit.check, kit.null

    def kb(cmds):
        return parse(kit.run("keyboard_cpp", "run\n" + "\n".join(cmds) + "\nend"))

    STEP = 250   # a quaver at 120

    def walk(mode, octaves, keys, steps, notemode="poly", rate="1/8", bpm=120, extra=()):
        """Keys down at nought, then each step's time and a frame's tick, as
        arptest's __walk did on the page: what the generator was given each step."""
        step = {"1/8": 0.5, "1/16": 0.25}[rate] * 60000 / bpm
        cmds = ["mode " + notemode, "bpm %r" % bpm, "arp %s %s %d" % (mode, rate, octaves)] + ["on %d 100" % k for k in keys]
        for i in range(steps): cmds += ["at %r" % (25 + i * step + 1), "tick"]
        rows = kb(cmds + list(extra))
        early = [voices(r[1]) for r in rows[3:3 + len(keys)]]
        seen = []
        for i in range(steps):
            a, t = rows[3 + len(keys) + 2 * i], rows[4 + len(keys) + 2 * i]
            seen.append(voices(a[1] + t[1]))
        return seen, early, rows

    flat = lambda w: [None if x is None else x[0] if len(x) == 1 else tuple(x) for x in w]

    # --- the gather (:120) ---
    up, early, _ = walk("up", 1, [C, E, G], 6)
    check("the first key waits for the rest of the chord rather than striking alone: no voices until 25 ms on",
          early == [None, None, None] and up[0] == [C], str(early))
    plain = kb(["mode poly", "on 60 100"])
    null("with the arpeggiator off the first key sounds at once", voices(plain[1][1]) == [C], str(plain[1][1]))

    # --- the order (:123 to :132) ---
    down = walk("down", 1, [C, E, G], 6)[0]
    updown = walk("updown", 1, [C, E, G], 8)[0]
    played = walk("played", 1, [G, C, E], 6)[0]
    two = walk("up", 2, [C, E, G], 7)[0]
    rnd = walk("random", 1, [C, E, G], 40)[0]
    check("up is C E G and round again, one note at a time", flat(up) == [C, E, G, C, E, G], str(up))
    check("down is G E C", flat(down) == [G, E, C, G, E, C], str(down))
    null("down is not up", flat(down) != [C, E, G, C, E, G])
    check("up-down goes up and back without playing either end twice in a row",
          flat(updown) == [C, E, G, E, C, E, G, E], str(updown))
    check("as played is the order the keys went down", flat(played) == [G, C, E, G, C, E], str(played))
    null("as played is not the sorted order", flat(played) != [C, E, G, C, E, G])
    check("two octaves climb the chord and the same an octave up",
          flat(two) == [C, E, G, C + 12, E + 12, G + 12, C], str(two))
    r = flat(rnd)
    check("random plays only what is held, and more than one of it", None not in r and set(r) <= {C, E, G} and len(set(r)) > 1,
          str(sorted(set(r), key=str)))

    # --- each step struck, and the hands kept (:151, :154) ---
    _, _, rows = walk("up", 1, [C, E, G], 2, extra=["at 400", "tick"])
    second = rows[8][1] + rows[9][1]   # the second step's calls: its time, then the frame's tick that takes it
    gates = [c.split()[1] for c in second if c.startswith("gate ")]
    check("each step closes the gate and opens it again, so every note is struck", gates[-2:] == ["0", "1"], str(second))
    between = rows[-1][1]
    null("a frame between steps strikes nothing", "gate 0 0" not in between and len(between) == 0, str(between))
    held = rows[9][2]
    notes = held[held.index("notes") + 1].split("+")
    check("and the hands are still the whole chord: three held", len(notes) == 3, held[held.index("notes") + 1])

    # --- the tempo (:181, :183, :184) ---
    def counted(bpm, until, far=None):
        cmds = ["mode poly", "bpm %r" % bpm, "arp up 1/8 1"] + ["on %d 100" % k for k in (C, E, G)]
        for t in range(0, until + 1, 10): cmds += ["at %r" % (25 + t), "tick"]
        if far: cmds += ["at %r" % (25 + far), "tick"]
        rows = kb(cmds)
        return arp_state(rows[3 + 3 + 2 * (until // 10 + 1) - 1][2])["steps"], arp_state(rows[-1][2])["steps"]
    first, far = counted(120, 1000, 60000 + 5)
    slow, _ = counted(90, 1000)
    check("120 BPM in quavers is a step every 250 ms: five in the first second, counting the first", first == 5, str(first))
    check("and a minute on the step count is the clock's, 241, not a drifted one", far == 241, str(far))
    check("and at 90 BPM a quaver is 333 ms, four steps in the first second", slow == 4, str(slow))
    null("and 90 is not 120's count", slow != 5)

    # --- the dyad draws the chord's intervals (:199) ---
    _, _, rows = walk("up", 1, [C, E, G], 3, notemode="dyad")
    def interval(calls):
        got = [int(c.split()[2]) for c in calls if c.startswith("set interval ")]
        return got[-1] if got else None
    dy = [interval(rows[6 + 2 * i][1] + rows[7 + 2 * i][1]) for i in range(3)]
    check("in the dyad each step pairs the lowest held note with the arpeggio's: unison, major third, fifth",
          dy == [0, 4, 7], str(dy))
    _, _, rows = walk("off", 1, [C, E, G], 1, notemode="dyad")
    null("without the arpeggiator the dyad is the top pair's third", interval(rows[5][1]) == 3, str(rows[5][1]))

    # --- MIDI out, letting go, switching off (:227, :229, :231) ---
    _, _, rows = walk("up", 1, [C, E, G], 2, extra=["off 60", "off 64", "off 67"])
    outs = []
    for r in rows[:-3]:
        for c in r[1]:
            w = c.split()
            if w[0] in ("out", "outoff"): outs.append((w[0], int(w[1])))
    rows_out = parse(kit.run("keyboard_cpp", "run\nout 1\nmode poly\nbpm 120\narp up 1/8 1\non 60 100\non 64 100\non 67 100\n"
                                              "at 26\ntick\nat 276\ntick\noff 60\noff 64\noff 67\nend"))
    sent = [(c.split()[0], int(c.split()[1])) for r in rows_out[:-3] for c in r[1] if c.split()[0] in ("out", "outoff")]
    after = [(c.split()[0], int(c.split()[1])) for r in rows_out[-3:] for c in r[1] if c.split()[0] in ("out", "outoff")]
    check("its notes go out as MIDI, each ended as the next begins", sent == [("out", C), ("outoff", C), ("out", E)], str(sent))
    null("with the out shut nothing goes", outs == [], str(outs))
    check("letting go stops it, and the note that went out is ended",
          after == [("outoff", E)] and arp_state(rows_out[-1][2])["start"] == "-", "%s, %s" % (after, rows_out[-1][2][-6:]))
    off = kb(["mode poly", "arp up 1/8 1", "on 60 100", "on 64 100", "on 67 100", "at 26", "tick", "arp off 1/8 1"])
    check("switched off with keys down, the generator has the whole chord again",
          sorted(voices(off[-1][1]) or []) == [C, E, G], str(off[-1][1]))

    # --- the layers changed mid-arpeggio (:252) ---
    lay = kb(["mode poly", "arp up 1/8 1", "on 60 100", "on 64 100", "on 67 100", "at 26", "tick", "layers layer"])
    check("when the layers change mid-arpeggio the generator is still given the step, not the whole chord",
          voices(lay[-3][1]) == [C] and voices(lay[-1][1]) == [C], "%s then %s" % (voices(lay[-3][1]), lay[-1][1]))
    nolay = kb(["mode poly", "on 60 100", "on 64 100", "on 67 100", "layers layer"])
    null("without the arpeggiator the layers' change gives the whole chord", sorted(voices(nolay[-1][1]) or []) == [C, E, G],
         str(nolay[-1][1]))

    # --- switched off once it has stepped (:274, :276) ---
    stepped = off[-1][1]
    g = [c.split()[1] for c in stepped if c.startswith("gate ")]
    check("switched off after a step, the held chord is struck: the gate closes and opens, and the generator has all of it",
          g[-2:] == ["0", "1"] and sorted(voices(stepped) or []) == [C, E, G], str(stepped))
    gather = kb(["mode poly", "arp up 1/8 1", "on 60 100", "on 64 100", "on 67 100", "arp off 1/8 1"])
    calls = gather[-1][1]
    null("switched off inside the gather, before any step, the chord it never took is not struck again",
         "0" not in [c.split()[1] for c in calls if c.startswith("gate ")] and sorted(voices(calls) or []) == [C, E, G],
         str(calls))

    # --- on the audio clock, the instrument whole (:181, :227) ---
    # The arpeggiator steps on the instrument's own frames there, and its notes
    # leave as bytes from the block they fall in: at 120 in quavers, a note-on
    # every 250 ms from the gather's 25, each within a block of its time.
    code = setup_code({"midiMode": "poly", "arpMode": "up", "arpRate": "1/8", "arpOctaves": 1, "bpm": 120})
    lines = [["make", 48000, 128, code], ["midi", 0x90, C, 100], ["midi", 0x90, E, 100], ["midi", 0x90, G, 100]]
    lines += [["block", 128, 1000]] * 400
    out = kit.instrument(lines)
    ons, k = [], -1
    for l in out:
        if l.startswith("block"): k += 1
        elif l.startswith("out "):
            for m in l[4:].split(";"):
                b = [int(x) for x in m.split()]
                if b and b[0] == 0x90: ons.append((k * 128 / 48, b[1], b[2]))
    times = [t for t, _, _ in ons]
    want = [25 + 250 * i for i in range(len(times))]
    check("on the instrument a note-on goes out each quaver at 120 from the gather, C E G and round, as bytes at velocity 100",
          len(ons) == 5 and [n for _, n, _ in ons] == [C, E, G, C, E] and all(v == 100 for _, _, v in ons)
          and all(abs(t - w) < 128 / 48 * 2 for t, w in zip(times, want)), str(ons))
    # The blocks' starts, against when each step was due: within a frame
    # either side (the first is a wake at its sample, the rest a frame's tick).
    null("and not on a crotchet's grid", not all(abs(t - w) < 128 / 48 * 2 for t, w in zip(times, [25 + 500 * i for i in range(len(times))])))
