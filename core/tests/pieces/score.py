"""The picture as a score and its notes as MIDI out, on the core alone.

These were scoretest.py's on ?brain=js until stage 5, step 3, batch 2 (13
Nov): there the page's own scoreColumn, scorePitches and keyMask were called
on grids written by hand, its scoreTick stepped at made-up times with the
page's phosphor.grid lit by hand and its source's strike intercepted, its
makeGeneratorCore built for the struck voice, and its midiOutNote fed a
stubbed port. Here the same claims are asserted on the core's score
(scope/score.h), its MidiOut and its generator, through score_cpp and
generator_cpp, with no page under them: the grid, the clock and the port are
the run's. Each check has a null beside it, a known-wrong reading seen red.

What stayed in scoretest.py: Stop's and a hidden page's all-notes-off, and
the box ticked on the page with real frames, which are the page's events.
"""
import math

E = math.e


def _said(line):
    """What a command logged: the text between its `::` and the state after `|`."""
    head = line.split(" | ")[0]
    return [p.strip() for p in head.split(" :: ")[1:]]


def _run(kit, *commands):
    return kit.run("score_cpp", "run\n%s\nend\n" % "\n".join(commands)).strip().split("\n")


def _chord(word):
    """`column 56/0.8 ...` as [(56, 0.8), ...]."""
    return [(int(t.split("/")[0]), float(t.split("/")[1])) for t in word.split()[1:]]


def _field(line, name):
    t = line.split(" | ", 1)[1].split()
    return t[t.index(name) + 1]


def run(kit):
    # --- reading a column (scoretest :87 to :103) ---------------------------
    # On ?brain=js these called the page's scoreColumn(grid, N, col, pitches,
    # voices) on a Float32Array written in the page. Here score_cpp's
    # `column`, which is scope::scoreColumn over scorePitches in a key, on a
    # grid its `cell` commands write: row 0 is the top of the screen.
    CHROM = "48 3 0 chromatic"
    one = _run(kit, *["cell 48 %d 0.8" % c for c in range(64)],
               *["column %d 2 %s" % (c, CHROM) for c in (0, 17, 63)])
    row = [_chord(_said(l)[0]) for l in one if l.startswith("column")]
    # Row 48 from the top is 15 rows up from the bottom; 36 pitches over 64
    # rows puts it on the eighth above C3, which is 56, G#3. Written out, not
    # asked of the core: asked, a reading upside down agrees with itself.
    def one_row(want):
        return len(row) == 3 and all(len(c) == 1 and c[0][0] == want and abs(c[0][1] - 0.8) < 1e-6 for c in row)
    kit.check("a single lit row is one note in every column, the one its height names, at its brightness",
              one_row(56), str(row))
    # The row read from the bottom instead would name 48 + floor(48 * 36 / 64), 75.
    kit.null("the same columns against the note the row would name read upside down", not one_row(75))

    diag = ["cell %d %d 1" % (63 - c, c) for c in range(64)]
    lines = _run(kit, *diag, *["column %d 1 %s" % (c, CHROM) for c in range(64)],
                 *["column %d 1 50 2 2 dorian" % c for c in range(64)], "pitches 50 2 2 dorian", "pitches 50 2 0 chromatic")
    cols = [_chord(_said(l)[0]) for l in lines if l.startswith("column")]
    rising = [c[0][0] if c else None for c in cols[:64]]
    dor = [c[0][0] if c else None for c in cols[64:]]
    dorian_set = [int(x) for x in _said(lines[-2])[0].split()[1:]]
    chrom_set = [int(x) for x in _said(lines[-1])[0].split()[1:]]
    def climbs(xs):
        return None not in xs and all(b >= a for a, b in zip(xs, xs[1:])) and xs[0] == 48 and xs[-1] == 83 \
            and sorted(set(xs)) == list(range(48, 84))
    kit.check("a diagonal is a rising scale, every note from C3 to B5 and none twice out of order",
              climbs(rising), "%s ... %s" % (rising[:5], rising[-3:]))
    kit.null("the reading fails on the diagonal read the other way, falling", not climbs(rising[::-1]))
    # Written out here, as the web check had it: checked against the core's
    # own list, a key that was ignored would agree with itself.
    DORIAN = [50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71, 72]
    kit.check("and in D dorian every note of it is in D dorian, the whole scale climbed",
              dorian_set == DORIAN and sorted(set(dor)) == DORIAN, str(sorted(set(dor))))
    kit.null("the key ignored - two chromatic octaves from D - is not D dorian", chrom_set != DORIAN and len(chrom_set) == 24)

    four = ["cell %d 5 %r" % rg for rg in ((10, 0.9), (20, 0.3), (30, 0.7), (40, 0.5))]
    lines = _run(kit, *four, "column 5 2 %s" % CHROM, "column 5 3 %s" % CHROM, "clear",
                 "cell 30 5 0.1", "column 5 4 %s" % CHROM, "cell 30 5 0.2", "column 5 4 %s" % CHROM,
                 "clear", "column 5 4 %s" % CHROM)
    two, three, smudge, over, empty = [_chord(_said(l)[0]) for l in lines if l.startswith("column")]
    kit.check("with two voices the chord is the two brightest, loudest first",
              len(two) == 2 and abs(two[0][1] - 0.9) < 1e-6 and abs(two[1][1] - 0.7) < 1e-6, str(two))
    kit.null("three voices take the third brightest too, so the two are a choice", len(three) == 3 and abs(three[2][1] - 0.5) < 1e-6)
    kit.check("and a smudge under the floor plays nothing, as an empty column plays nothing",
              smudge == [] and empty == [], "%s, %s" % (smudge, empty))
    kit.null("the same cell a little over the floor plays", len(over) == 1, str(over))

    # --- the playhead (scoretest :131 to :134) ------------------------------
    # On ?brain=js: the page's scoreTick every 10 ms of made-up time for a
    # second from the bar's start, phosphor.grid lit by hand, strikes counted
    # by wrapping the page's source. Here the core's scoreTick, its strikes
    # logged by score_cpp. Row 40 is 23 rows up: the twelfth pitch, C4.
    def playhead(bpm, lit=True):
        cmds = (["cell 40 %d 0.9" % c for c in range(64)] if lit else []) + \
            ["tempo %r" % bpm, "score on 1/16 1 48 3", "at 100000", "start"]
        for t in range(0, 1001, 10): cmds += ["at %d" % (100000 + t), "frame"]
        out = _run(kit, *cmds)
        strikes = [float(s.split()[1]) for l in out for s in _said(l) if s.startswith("strike")]
        return strikes, int(_field(out[-1], "col"))
    fast, fast_col = playhead(120)
    slow, _ = playhead(60)
    ninety, _ = playhead(90)
    none, _ = playhead(120, lit=False)
    c4 = 440 * 2 ** ((60 - 69) / 12)
    kit.check("at 120 BPM in semiquavers a second from nought is nine steps, each striking the lit row's note",
              len(fast) == 9 and fast_col == 8 and all(abs(h - c4) < 1e-9 for h in fast), "%d strikes, column %d" % (len(fast), fast_col))
    kit.check("and at 60 BPM it is five: the playhead keeps the tempo", len(slow) == 5, str(len(slow)))
    kit.null("at 90 it is neither, so the count is the tempo's", len(ninety) not in (5, 9), str(len(ninety)))
    kit.check("and an empty grid strikes nothing", none == [], str(none))

    # --- the voice (scoretest :168 to :173) ---------------------------------
    # On ?brain=js the page's makeGeneratorCore, struck at 1000 Hz and full
    # velocity and rendered a second at 44.1 kHz beside the same core
    # unstruck. Here the core's generator through generator_cpp, the same
    # two runs; its lanes are the picture pair, the heard pair and B's.
    def voice(strike):
        text = ("run name=voice rate=44100.0 slots=48 seed=3 samples=44160 lfo0=sine,0.2 lfo1=sine,0.2\n"
                "at 0 set amp 0.3\nat 0 set freq 110\n%send\n" % ("at 0 strike 1000 %r\n" % strike if strike else ""))
        v = kit.floats("generator_cpp", text)
        n = 44160
        return [v[c:6 * n:6] for c in range(4)]
    a, b, half = voice(None), voice(1), voice(0.5)
    picture = max(max(abs(x - y) for x, y in zip(b[c], a[c])) for c in (0, 1))
    misread = max(abs(x - y) for x, y in zip(b[2], a[0]))
    beyond = max(abs(x - y) for x, y in zip(b[2], b[0]))
    ears = max(abs((b[2][i] - b[0][i]) - (b[3][i] - b[1][i])) for i in range(44100))
    early = max(abs(b[2][i] - a[2][i]) for i in range(200, 2400))
    early_half = max(abs(half[2][i] - a[2][i]) for i in range(200, 2400))
    late = max(abs(b[2][i] - a[2][i]) for i in range(17640, 17640 + 441))
    sooner = max(abs(b[2][i] - a[2][i]) for i in range(8820, 8820 + 441))
    kit.check("a struck note is heard at its level, 0.4 times its velocity over two", abs(early - 0.2) < 0.005, "%.4f" % early)
    kit.null("at half the velocity it is half as loud, so the level is the velocity's", abs(early_half - 0.2) >= 0.005,
             "%.4f" % early_half)
    kit.check("and it is not drawn: the picture is untouched, and what is heard beyond it is the note, in both ears alike",
              picture == 0 and beyond > 0.15 and ears < 1e-6, "picture %.2e, beyond %.4f, ears %.2e" % (picture, beyond, ears))
    kit.null("the picture check fails with the heard pair read as the picture", misread > 0.15, "%.4f" % misread)
    kit.check("and it dies away to 1/e over its 400 ms", abs(late - 0.2 / E) < 0.006, "%.4f, want %.4f" % (late, 0.2 / E))
    kit.null("at 200 ms it is not yet 1/e", abs(sooner - 0.2 / E) >= 0.006, "%.4f" % sooner)

    # --- MIDI out (scoretest :228, :233, :240, :242) ------------------------
    # On ?brain=js the page's scoreTick and midiOutNote with a stubbed port
    # on channel 2. Here the core's MidiOut, whose bytes score_cpp logs as
    # `send`, the channel chosen as the menu's value 2 is (0x92 a note-on).
    def sends(*cmds):
        return [[int(x) for x in s.split()[1].split(",")] for l in _run(kit, *cmds) for s in _said(l) if s.startswith("send")]
    lit = ["cell 40 %d 1" % c for c in range(64)]
    played = sends("port 1 2", *lit, "tempo 120", "score on 1/16 1 48 3", "at 200000", "start", "frame", "at 200130", "frame")
    n = played[0][1] if played else -1
    want = [[0x92, n, 127], [0x82, n, 0], [0x92, n, 127]]
    kit.check("the score's notes go out on the chosen channel, the last one ended before the next begins",
              played == want and n == 60, str(played))
    kit.null("the same bytes on the first channel are not what was sent", played != [[0x91, n, 127], [0x81, n, 0], [0x91, n, 127]])
    turns = sends("port 1 2", *["cell %d %d 1" % (10 if c % 2 else 50, c) for c in range(64)], "tempo 120",
                  "score on 1/16 1 48 3", "at 210000", "start", "frame", "at 210130", "frame")
    def ended_first(t):
        return len(t) == 3 and t[0][0] == 0x92 and t[1] == [0x82, t[0][1], 0] and t[2][0] == 0x92 and t[2][1] != t[0][1]
    kit.check("and when the next step's note is another, the last is ended before it begins", ended_first(turns), str(turns))
    kit.null("the reading fails with the note-off sent after the next note-on", not ended_first([turns[0], turns[2], turns[1]] if len(turns) == 3 else []))
    burst = _run(kit, "port 1 2", "at 1000", *["note %d 0.5" % (40 + i % 40) for i in range(100)])
    ons = sum(1 for l in burst for s in _said(l) if s.startswith("send 146,"))
    dropped = int(_field(burst[-1], "dropped"))
    kit.check("a hundred note-ons at once are forty sent and sixty dropped", ons == 40 and dropped == 60, "%d sent, %d dropped" % (ons, dropped))
    spread = [c for i in range(100) for c in ("at %d" % (1000 + 30 * i), "note %d 0.5" % (40 + i % 40))]
    spread_out = _run(kit, "port 1 2", *spread)
    spread_ons = sum(1 for l in spread_out for s in _said(l) if s.startswith("send 146,"))
    kit.null("the same hundred thirty milliseconds apart, 33 a second, are all sent: the limit is a rate", spread_ons == 100,
             "%d sent" % spread_ons)
    def quiet(cmds):
        return sum(1 for m in sends("port 1 2", *cmds, "tempo 120", "score on 1/16 1 48 3", "at 300000", "start",
                                    *[c for k in range(20) for c in ("at %d" % (300000 + 60 * k), "frame")]) if (m[0] & 0xF0) == 0x90)
    kit.check("and an empty grid sends nothing at all", quiet([]) == 0)
    kit.null("the same playing with a row lit sends", quiet(lit) > 0)
