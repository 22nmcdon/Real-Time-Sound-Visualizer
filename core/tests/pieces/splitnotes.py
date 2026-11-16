"""The split by notes (16 Nov, web/docs/split-by-notes.md): which hand a note
goes to when the split counts the notes held rather than reading a key.

scope::Keyboard through keyboard_cpp, poly and split, its chords to each
layer read back from the `set voices` calls it makes (layer.py's way). The
rule is the owner's: a note's hand is fixed when it starts, by its rank among
the notes held at that moment, counted from the end the split counts. Each
check is beside the answer the rule it was chosen over would give - fill the
counted hand first, or re-sort the held notes on every note - which is what
its null feeds it, so a check that cannot tell the rules apart goes red.
"""

from pieces.layer import keyboard

A2, C3, E3, G3, C4, E4 = 45, 48, 52, 55, 60, 64


def hands(chord):
    return sorted(n for n, _ in chord[0]), sorted(n for n, _ in chord[1])


# Since the gather (16 Nov) notes that start within 25 ms of a gather's first
# are one struck chord, ranked together by pitch. The checks of the rule a
# note at a time strike each note 40 ms after the last, as a player playing
# them in turn; the gather's own checks give their times.
APART = 40


def split(kit, end, count, *commands, spaced=True):
    """keyboard_cpp's run split by notes. `spaced` puts each key APART ms after the last."""
    timed, t = [], 0
    for c in commands:
        if spaced and c.split()[0] in ("on", "off"):
            t += APART
            timed.append("at %r" % t)
        timed.append(c)
    out, ch = keyboard(kit, "mode poly", "layers split", "splitby notes", "splitcount %s %d" % (end, count), *timed)
    return out, ch


def screen(kit, end, count, *commands):
    """The strikes the keyboard lays on the screen, as (note, layers), in the order laid, and the
    command each was laid in: keyboard_cpp's `screen=1`."""
    out = kit.run("keyboard_cpp", "run screen=1\n%s\nend" % "\n".join(
        ["mode poly", "layers split", "splitby notes", "splitcount %s %d" % (end, count)] + list(commands))).strip().split("\n")
    laid = []
    for line in out:
        for part in line.split(" | ")[0].split(" :: ")[1:]:
            w = part.split()
            if w[0] == "screen": laid.append((int(w[1]), int(w[3]), line.split(" :: ")[0].split(" | ")[0]))
    return laid


def model(rule, end, count, events):
    """What a rule gives, in Python, for the nulls: a list of (note, hand) held, in the order struck.
    `rank` is the core's; `fill` gives the counted hand the next note while it has fewer than the
    count; `resort` deals every held note again by pitch on every change."""
    held = []   # [note, hand]
    upper = end == "upper"
    for kind, note in events:
        held = [h for h in held if h[0] != note]
        if kind == "off": continue
        if rule == "rank":
            beyond = sum(1 for n, _ in held if (n > note if upper else n < note))
            counted = beyond < count
        else:
            counted = sum(1 for _, h in held if h == (1 if upper else 0)) < count
        held.append([note, (1 if counted else 0) if upper else (0 if counted else 1)])
        if rule == "resort":
            order = sorted(n for n, _ in held)
            if upper: order.reverse()
            counted = set(order[:count])
            for h in held: h[1] = (1 if h[0] in counted else 0) if upper else (0 if h[0] in counted else 1)
    return sorted(n for n, h in held if h == 0), sorted(n for n, h in held if h == 1)


def run(kit):
    check, null = kit.check, kit.null

    # --- a chord, then a note under it: rank, not fill ---
    # C3 E3 G3 with Lower: 1 is C3 low and E3, G3 high. A2 under them while
    # they are held is the lowest note held as it starts, so by rank it is
    # the lower hand's too; filling the counted hand first would send it high,
    # the low slot being taken. C3 keeps its hand either way.
    ev = [("on", C3), ("on", E3), ("on", G3)]
    _, ch = split(kit, "lower", 1, *["on %d 100" % n for _, n in ev])
    check("Lower: 1, C3 E3 G3 struck in turn: C3 is the lower hand, E3 and G3 the upper",
          hands(ch[-1]) == ([C3], [E3, G3]), str(hands(ch[-1])))
    null("the key split at C4 puts all three in the lower hand", hands(ch[-1]) != ([C3, E3, G3], []))
    _, ch = split(kit, "lower", 1, *["on %d 100" % n for _, n in ev], "on %d 100" % A2)
    got = hands(ch[-1])
    check("and A2 added under them is ranked lowest, so it joins the lower hand and C3 stays",
          got == model("rank", "lower", 1, ev + [("on", A2)]) == ([A2, C3], [E3, G3]), str(got))
    null("filling the counted hand first would send A2 high", got != model("fill", "lower", 1, ev + [("on", A2)]),
         str(model("fill", "lower", 1, ev + [("on", A2)])))

    # --- fixed when it starts: nothing re-sorts the held notes ---
    # Lower: 2 over E3 G3 C4 is E3 and G3 low, C4 high; C3 struck under them
    # is low (rank 0), and by rank G3 is now third from the bottom - a re-sort
    # would move it up. It stays.
    ev = [("on", E3), ("on", G3), ("on", C4), ("on", C3)]
    _, ch = split(kit, "lower", 2, *["on %d 100" % n for _, n in ev])
    got = hands(ch[-1])
    check("Lower: 2, C3 struck under E3 G3 C4: C3 joins the lower hand and no held note changes hand",
          got == ([C3, E3, G3], [C4]) == model("rank", "lower", 2, ev), str(got))
    null("re-sorting the held notes would move G3 to the upper hand", got != model("resort", "lower", 2, ev),
         str(model("resort", "lower", 2, ev)))
    # And letting go never deals again: C3 up leaves E3 G3 low and C4 high.
    _, ch = split(kit, "lower", 2, *["on %d 100" % n for _, n in ev], "off %d" % E3, "off %d" % G3)
    got = hands(ch[-1])
    check("letting go of E3 and G3 leaves C4 the upper hand's, though it is now second from the bottom",
          got == ([C3], [C4]), str(got))
    null("dealt again on a release, C4 would be the lower hand's", got != ([C3, C4], []))

    # --- fewer held than the count ---
    _, ch = split(kit, "lower", 3, "on %d 100" % C4, "on %d 100" % E4)
    got = hands(ch[-1])
    check("Lower: 3 with two notes held: both are the lower hand, though they are above the key split's C4",
          got == ([C4, E4], []), str(got))
    null("the key split at C4 would put both in the upper hand", got != ([], [C4, E4]))

    # --- Upper: N mirrors Lower: N ---
    # G3 E3 C3 struck from the top with Upper: 1 is Lower: 1's C3 E3 G3
    # turned over: G3 high, E3 and C3 low; and C4 above them is ranked top.
    ev = [("on", G3), ("on", E3), ("on", C3), ("on", C4)]
    _, ch = split(kit, "upper", 1, *["on %d 100" % n for _, n in ev[:3]])
    got = hands(ch[-1])
    check("Upper: 1, G3 E3 C3 struck from the top: G3 is the upper hand, E3 and C3 the lower",
          got == ([C3, E3], [G3]), str(got))
    null("read as Lower: 1 the hands come out the other way", got != model("rank", "lower", 1, ev[:3]),
         str(model("rank", "lower", 1, ev[:3])))
    _, ch = split(kit, "upper", 1, *["on %d 100" % n for _, n in ev])
    got = hands(ch[-1])
    check("and C4 over them is ranked highest, so it joins the upper hand and G3 stays",
          got == ([C3, E3], [G3, C4]) == model("rank", "upper", 1, ev), str(got))
    null("filling the counted hand first would send C4 low", got != model("fill", "upper", 1, ev))

    # --- the sustain pedal: a key held only by the pedal still counts ---
    out, ch = split(kit, "lower", 1, "pedal 1", "on %d 100" % C3, "off %d" % C3, "on %d 100" % G3)
    got = hands(ch[-1])
    check("Lower: 1, C3 let go under the pedal and G3 struck: C3 still sounds and still holds the lower hand, so G3 is the upper",
          got == ([C3], [G3]), str(got))
    null("a pedal-held key not counted would leave G3 the lowest held, and low", got != ([C3, G3], []))

    # --- a key struck again starts again, so it is ranked again ---
    _, ch = split(kit, "lower", 1, "on %d 100" % G3, "on %d 100" % C3, "on %d 100" % G3)
    got = hands(ch[-1])
    check("Lower: 1, G3 alone (low), C3 under it (low), then G3 struck again: ranked again over C3, G3 is the upper hand",
          got == ([C3], [G3]), str(got))
    null("keeping the first strike's hand would leave G3 low", got != ([C3, G3], []))

    # --- the strike on the screen goes to the hand dealt ---
    out, _ = split(kit, "lower", 1, *["on %d 100" % n for n in (C3, E3, G3)])
    strikes = out[-1].split(" strikes ")[1].split()[:2]
    check("each strike counted for the hand its note was dealt: one low, two high", strikes == ["1", "2"], str(strikes))
    null("by the key split at C4 all three would count low", strikes != ["3", "0"])

    # --- an arpeggio's step keeps the hand of the note it comes from ---
    # Lower: 1 over C3 and G3, two octaves up: the steps C4 and G4 are
    # copies of C3 and G3, so C4 plays in the lower hand, which no key split
    # under C4 would give it. The arpeggio hands each step to the layers.
    cmds = ["arp up 1/8 2", "on %d 100" % C3, "on %d 100" % G3]
    for i in range(3): cmds += ["at %r" % (25 + i * 250 + 1), "tick"]
    _, ch = split(kit, "lower", 1, *cmds, spaced=False)
    third = hands(ch[-1])
    check("the arpeggio's third step, C4, is C3 an octave up and plays in the lower hand", third == ([C4], []), str(third))
    null("dealt by its own pitch over G3 it would be the upper hand's", third != ([], [C4]))
    # And the fourth, G4, is G3's, so the upper hand's: a step that dropped
    # its note's hand would land every step in the lower hand.
    _, ch = split(kit, "lower", 1, *cmds, "at %r" % (25 + 3 * 250 + 1), "tick", spaced=False)
    fourth = hands(ch[-1])
    check("and its fourth, G4, is G3's and plays in the upper hand", fourth == ([], [G3 + 12]), str(fourth))
    null("a step without its note's hand would be the lower hand's", fourth != ([G3 + 12], []))

    # --- the controls deal what is held again, as struck ---
    _, ch = split(kit, "lower", 1, *["on %d 100" % n for n in (C3, E3, G3)], "splitcount lower 2")
    got = hands(ch[-1])
    check("turning the count to 2 with C3 E3 G3 held deals them again in the order struck: C3 and E3 low",
          got == ([C3, E3], [G3]), str(got))
    null("left as they were the count would do nothing until the next note", got != ([C3], [E3, G3]))
    _, ch = split(kit, "lower", 1, *["on %d 100" % n for n in (C3, E3, G3)], "splitby key")
    got = hands(ch[-1])
    check("and back to the key split, the point decides again: all three below C4", got == ([C3, E3, G3], []), str(got))
    null("still by notes, C3 alone would be low", got != ([C3], [E3, G3]))

    # --- a struck chord is ranked as one (the gather, 16 Nov) ---
    # A chord struck at once reaches the keyboard a millisecond or two apart
    # in whatever order the fingers land. Top first, G3 E3 C3 at 0, 1 and 2 ms
    # with Lower: 1 is one chord: C3 is its lowest note and the lower hand's.
    # Dealt strictly in the order they came (the code before the gather), G3
    # was the lowest held as it started, then E3, then C3: all three low.
    top = [("on", G3), ("on", E3), ("on", C3)]
    timed = ["at 0", "on %d 100" % G3, "at 1", "on %d 100" % E3, "at 2", "on %d 100" % C3]
    _, ch = split(kit, "lower", 1, *timed, spaced=False)
    got = hands(ch[-1])
    check("Lower: 1, G3 E3 C3 arriving top first 1 ms apart are one chord, dealt by pitch: C3 low, E3 and G3 high",
          got == ([C3], [E3, G3]), str(got))
    null("dealt strictly in the order they arrived all three would be the lower hand's",
         got != model("rank", "lower", 1, top), str(model("rank", "lower", 1, top)))
    # Upper: 1 is the mirror: C3 E3 G3 from the bottom, one chord, G3 the upper hand's.
    _, ch = split(kit, "upper", 1, "at 0", "on %d 100" % C3, "at 1", "on %d 100" % E3, "at 2", "on %d 100" % G3, spaced=False)
    got = hands(ch[-1])
    check("Upper: 1, C3 E3 G3 arriving bottom first are one chord: G3 high, C3 and E3 low", got == ([C3, E3], [G3]), str(got))
    null("strictly in order all three would be the upper hand's",
         got != model("rank", "upper", 1, [("on", C3), ("on", E3), ("on", G3)]))

    # The window is 25 ms from the gather's first note, the arpeggiator's
    # figure: C3 24.9 ms after G3 is the same chord, at 25 ms and at 40 it is
    # a note of its own, ranked among what is held - and G3 stays low.
    def after(ms):
        _, ch = split(kit, "lower", 1, "at 0", "on %d 100" % G3, "at %r" % ms, "on %d 100" % C3, spaced=False)
        return hands(ch[-1])
    check("C3 24.9 ms after G3 is gathered with it: C3 low, G3 high", after(24.9) == ([C3], [G3]), str(after(24.9)))
    null("strictly in order it would not be", after(24.9) != ([C3, G3], []))
    check("C3 25 ms after G3 is not: both low, G3 kept where it was dealt", after(25) == ([C3, G3], []), str(after(25)))
    got = after(APART)
    check("nor 40 ms after: G3 keeps the lower hand, and C3 ranked lowest joins it", got == ([C3, G3], []), str(got))
    null("a gather that never closed would move G3 up", got != ([C3], [G3]))
    # Timed from the first note, not from the last: G3, E3 20 ms later and C3
    # 20 ms after that is G3 and E3 one chord (E3 low) and C3 a note of its
    # own. A window that slid with each note would make one chord of a run.
    _, ch = split(kit, "lower", 1, "at 0", "on %d 100" % G3, "at 20", "on %d 100" % E3, "at 40", "on %d 100" % C3, spaced=False)
    got = hands(ch[-1])
    check("G3, E3 at 20 ms and C3 at 40: the window is timed from G3, so E3 stays low and C3 joins it",
          got == ([C3, E3], [G3]), str(got))
    null("a window sliding with each note would gather all three and send E3 high", got != ([C3], [E3, G3]))

    # A held note never changes hand once its gather has closed: C3 E3 G3
    # struck top first, then A2 under them 60 ms on. A2 is ranked lowest and
    # joins the lower hand; C3 stays there.
    _, ch = split(kit, "lower", 1, *timed, "at 60", "on %d 100" % A2, spaced=False)
    got = hands(ch[-1])
    check("A2 60 ms after the chord: ranked lowest, it joins the lower hand and C3 keeps it", got == ([A2, C3], [E3, G3]), str(got))
    null("a gather that never closed would deal the chord again with A2 and move C3 up", got != ([A2], [C3, E3, G3]))

    # The pedal: a key let go under it still counts, gathered or not. C3 held
    # by the pedal alone, then G3 and E3 struck top first as one chord: both
    # are above C3, so both are the upper hand's.
    _, ch = split(kit, "lower", 1, "pedal 1", "at 0", "on %d 100" % C3, "at 10", "off %d" % C3,
                  "at 100", "on %d 100" % G3, "at 101", "on %d 100" % E3, spaced=False)
    got = hands(ch[-1])
    check("C3 held by the pedal, then G3 and E3 struck as one: C3 low, both of them high", got == ([C3], [E3, G3]), str(got))
    null("a pedal-held key not counted would leave E3 the gather's lowest, and low", got != ([C3, E3], [G3]))
    # A key struck again inside its own gather is still one note of it.
    _, ch = split(kit, "lower", 1, "at 0", "on %d 100" % G3, "at 1", "on %d 100" % C3, "at 2", "on %d 100" % G3, spaced=False)
    got = hands(ch[-1])
    check("G3, C3 and G3 again inside one gather: C3 low, G3 high", got == ([C3], [G3]), str(got))
    null("strictly in order C3 under the first G3 would have been low with it, and G3 struck again high: the same answer, so"
         " this is the check that a repeat inside a gather is not two notes", len(ch[-1][0]) + len(ch[-1][1]) == 2)

    # The controls deal what is held again by its gathers: the top-first chord
    # with the count turned to 2 is C3 and E3 low. Dealt again strictly in the
    # order struck, G3 came first and all three would be low.
    _, ch = split(kit, "lower", 1, *timed, "at 100", "splitcount lower 2", spaced=False)
    got = hands(ch[-1])
    check("the count turned to 2 over the top-first chord deals it again as one: C3 and E3 low, G3 high",
          got == ([C3, E3], [G3]), str(got))
    null("dealt again strictly in the order struck all three would be low", got != ([C3, E3, G3], []))

    # The screen: split by notes a strike waits for its gather to close and
    # lands in the hand dealt then. G3 then C3 2 ms later: G3 was the lower
    # hand's for 2 ms, and its arc goes to the upper hand's picture. Split by
    # key nothing waits.
    laid = screen(kit, "lower", 1, "at 0", "on %d 100" % G3, "at 2", "on %d 100" % C3, "at 30")
    check("by notes the screen is struck when the gather closes, in the hands dealt: G3 upper, C3 lower",
          [(n, l) for n, l, _ in laid] == [(G3, 2), (C3, 1)] and all(c == "at" for _, _, c in laid), str(laid))
    null("struck at once G3's arc would be laid in the lower hand, where it was first dealt",
         [(n, l) for n, l, _ in laid][:1] != [(G3, 1)])
    out = kit.run("keyboard_cpp", "run screen=1\nmode poly\nlayers split\nat 0\non %d 100\nat 2\non %d 100\nat 30\nend" % (G3, C3))
    laid = [l.split(" :: ")[0].split(" | ")[0] for l in out.strip().split("\n") if " :: screen " in l]
    check("by key the screen is struck at once, as before", laid == ["on", "on"], str(laid))
    null("by key nothing is laid at the gather's close", laid != ["at"])
    # And the hand's fade restarts for a note its gather moved into it.
    out, _ = split(kit, "lower", 1, "at 0", "on %d 100" % G3, "at 2", "on %d 100" % C3, spaced=False)
    strikes = out[-1].split(" strikes ")[1].split()[:2]
    check("G3 moved to the upper hand by C3's arrival restarts the upper hand's fade", strikes[1] == "1", str(strikes))
    null("counted only where it was first dealt the upper hand would never hear it", strikes[1] != "0")

    # --- the count runs to six (the owner's, 16 Nov), and no further ---
    # Seven notes struck from the bottom with Lower: 6: the first six are the
    # lower hand. Asked for seven, the keyboard holds it at six.
    up = [48, 50, 52, 53, 55, 57, 59]
    _, ch = split(kit, "lower", 6, *["on %d 100" % n for n in up])
    got = hands(ch[-1])
    check("Lower: 6 over seven notes struck from the bottom: six are the lower hand, the seventh the upper",
          got == (up[:6], up[6:]), str(got))
    null("held at five, the sixth would be the upper hand's", got != (up[:5], up[5:]))
    _, ch = split(kit, "lower", 7, *["on %d 100" % n for n in up])
    got = hands(ch[-1])
    check("asked for seven, the count stays at six", got == (up[:6], up[6:]), str(got))
    null("unheld, all seven would be the lower hand's", got != (up, []))
