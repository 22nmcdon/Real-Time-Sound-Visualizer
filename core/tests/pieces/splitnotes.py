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


def split(kit, end, count, *commands):
    out, ch = keyboard(kit, "mode poly", "layers split", "splitby notes", "splitcount %s %d" % (end, count), *commands)
    return out, ch


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
    _, ch = split(kit, "lower", 1, *cmds)
    third = hands(ch[-1])
    check("the arpeggio's third step, C4, is C3 an octave up and plays in the lower hand", third == ([C4], []), str(third))
    null("dealt by its own pitch over G3 it would be the upper hand's", third != ([], [C4]))
    # And the fourth, G4, is G3's, so the upper hand's: a step that dropped
    # its note's hand would land every step in the lower hand.
    _, ch = split(kit, "lower", 1, *cmds, "at %r" % (25 + 3 * 250 + 1), "tick")
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
