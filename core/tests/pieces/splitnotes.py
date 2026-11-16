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

import os

import numpy as np

from pieces.kit import BUILD
from pieces.layer import keyboard

A2, C3, E3, G3, C4, E4 = 45, 48, 52, 55, 60, 64


def hands(chord):
    return sorted(n for n, _ in chord[0]), sorted(n for n, _ in chord[1])


# The checks of the rule a note at a time strike each note 40 ms after the
# last, as a player playing them in turn; the gather's own checks give their
# times. Split by notes every note waits the look-ahead (10 ms, 16 Nov) before
# it sounds, so every run ends with an `at` past the last command, which
# serves the wakes the waiting notes sound at.
APART = 40
AHEAD = 10   # the Chord window's default, kChordWindowDefault


def timeline(commands, spaced):
    """The commands with their times: spaced, each APART ms after the last; and an `at` past the end."""
    timed, t = [], 0.0
    for c in commands:
        if spaced:
            t += APART
            timed.append("at %r" % t)
        elif c.split()[0] == "at":
            t = max(t, float(c.split()[1]))
        timed.append(c)
    return timed + ["at %r" % (t + APART)]


def split(kit, end, count, *commands, spaced=True):
    """keyboard_cpp's run split by notes. `spaced` puts each command APART ms after the last."""
    return keyboard(kit, "mode poly", "layers split", "splitby notes", "splitcount %s %d" % (end, count),
                    *timeline(commands, spaced))


def sounded(kit, setup, commands):
    """When each note sounds and stops, and in which hand: keyboard_cpp's run with its wakes logged,
    read as a list of (ms, note, hand, "on"|"off") in the order they happened, a note starting where
    it first appears in a layer's voices and stopping where it leaves them."""
    sent = setup + timeline(commands, False)
    out = kit.run("keyboard_cpp", "run wakes=1\n%s\nend" % "\n".join(sent))
    now, voices, events = 0.0, {0: set(), 1: set()}, []
    for command, line in zip(sent, out.strip().split("\n")):
        head = line.split(" | ")[0].split(" :: ")
        stamp = float(command.split()[1]) if command.split()[0] == "at" else None
        for part in head[1:]:
            w = part.split()
            if w[0] == "wake": now = float(w[1])
            elif w[:2] == ["set", "voices"]:
                layer = int(w[3])
                notes = set() if w[2] in ("none", "null") else {int(x.split("/")[0]) for x in w[2].split("+")}
                for n in sorted(notes - voices[layer]): events.append((now, n, layer, "on"))
                for n in sorted(voices[layer] - notes): events.append((now, n, layer, "off"))
                voices[layer] = notes
        if stamp is not None: now = stamp
    return events


def by_notes(end="lower", count=1, window=None):
    return ["mode poly", "layers split", "splitby notes", "splitcount %s %d" % (end, count)] + (
        ["splitwindow %r" % window] if window is not None else [])


def played(timed):
    """`at T` / `on N 100` / `off N` lines from (ms, "on"|"off", note)."""
    out = []
    for t, kind, n in timed: out += ["at %r" % t, ("on %d 100" if kind == "on" else "off %d") % n]
    return out


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
    for i in range(3): cmds += ["at %r" % (AHEAD + 25 + i * 250 + 1), "tick"]
    _, ch = split(kit, "lower", 1, *cmds, spaced=False)
    third = hands(ch[-1])
    check("the arpeggio's third step, C4, is C3 an octave up and plays in the lower hand", third == ([C4], []), str(third))
    null("dealt by its own pitch over G3 it would be the upper hand's", third != ([], [C4]))
    # And the fourth, G4, is G3's, so the upper hand's: a step that dropped
    # its note's hand would land every step in the lower hand.
    _, ch = split(kit, "lower", 1, *cmds, "at %r" % (AHEAD + 25 + 3 * 250 + 1), "tick", spaced=False)
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

    # --- the look-ahead (the owner's decision, 16 Nov) ---
    # Split by notes every note, release and pedal waits AHEAD ms from its
    # own arrival, so the notes that arrive within the window of a gather's
    # first are known before the first sounds and are dealt together by pitch,
    # and then each sounds at its own moment, in its hand, never moved.

    # Timing first: a fast roll, notes 3 ms apart, comes out with the gaps it
    # went in with, each AHEAD late, and each note's length kept (its release
    # waits alike). The null is the gather released at once, as its first note
    # sounds - every gap nought - which is what holding a chord until it closes
    # would do to a roll.
    roll = [(0, "on", C3), (3, "on", E3), (6, "on", G3), (9, "on", C4),
            (50, "off", C3), (57, "off", E3), (61, "off", G3), (70, "off", C4)]
    ev = sounded(kit, by_notes(), played(roll))
    starts = {n: t for t, n, _, k in ev if k == "on"}
    stops = {n: t for t, n, _, k in ev if k == "off"}
    went = {n: t for t, k, n in roll if k == "on"}
    gone = {n: t for t, k, n in roll if k == "off"}
    late = sorted(round(starts[n] - went[n], 9) for n in went) if set(starts) == set(went) else None
    check("a roll 3 ms apart sounds with its gaps kept, every note exactly %d ms late" % AHEAD,
          late == [AHEAD] * 4, str(ev))
    gaps = lambda at: [round(at[(C3, E3, G3, C4)[i + 1]] - at[(C3, E3, G3, C4)[i]], 9) for i in range(3)]
    check("its gaps between notes are 3, 3 and 3 ms, as played", gaps(starts) == [3, 3, 3], str(gaps(starts)))
    at_once = {n: AHEAD for n in went}   # the gather let go as its first note sounds
    null("a gather released at once makes every gap nought", gaps(at_once) != [3, 3, 3], str(gaps(at_once)))
    lengths = {n: round(stops.get(n, -1) - starts[n], 9) for n in went}
    check("and every note keeps its length: each release waits the same %d ms" % AHEAD,
          lengths == {n: gone[n] - went[n] for n in went}, str(lengths))
    null("a release played at once would shorten every note by the look-ahead",
         {n: round(gone[n] - starts[n], 9) for n in went} != {n: gone[n] - went[n] for n in went})
    # And the roll's hands: all four within 10 ms of C3, so one gather, C3 the lower hand's.
    check("the roll, all within the window of its first note, is dealt by pitch: C3 low, the rest high",
          sorted((n, h) for _, n, h, k in ev if k == "on") == [(C3, 0), (E3, 1), (G3, 1), (C4, 1)], str(ev))

    # A grace note 4 ms before its main note: both sound, 4 ms apart, as played.
    grace = [(0, "on", 61), (4, "on", 62), (3, "off", 61), (300, "off", 62)]
    ev = sounded(kit, by_notes(), played(sorted(grace)))
    at = {(n, k): t for t, n, _, k in ev}
    got = (at.get((61, "on")), at.get((61, "off")), at.get((62, "on")))
    check("a grace note 4 ms before its note sounds 4 ms before it, for the 3 ms it was held, %d ms late" % AHEAD,
          got == (AHEAD, AHEAD + 3, AHEAD + 4), str(ev))
    null("released at once with its gather, the grace note and its note would start together",
         (AHEAD, AHEAD + 3, AHEAD) != (AHEAD, AHEAD + 3, AHEAD + 4))

    # A block chord whose top note lands first, 0, 2, 4 and 6 ms: dealt by
    # pitch, C3 the lower hand's. The null is the strict order without the
    # look-ahead, each note the lowest held as it starts, so all four low.
    block = [(0, "on", C4), (2, "on", G3), (4, "on", E3), (6, "on", C3)]
    _, ch = split(kit, "lower", 1, *played(block), spaced=False)
    got = hands(ch[-1])
    check("a block chord top first at 0, 2, 4 and 6 ms is dealt by pitch: C3 low, E3 G3 C4 high",
          got == ([C3], [E3, G3, C4]), str(got))
    strict = model("rank", "lower", 1, [("on", n) for _, _, n in block])
    null("dealt strictly in the order it arrived, all four would be the lower hand's", got != strict, str(strict))
    # Upper: 1 is the mirror: C3 E3 G3 from the bottom, one chord, G3 the upper hand's.
    _, ch = split(kit, "upper", 1, "at 0", "on %d 100" % C3, "at 1", "on %d 100" % E3, "at 2", "on %d 100" % G3, spaced=False)
    got = hands(ch[-1])
    check("Upper: 1, C3 E3 G3 arriving bottom first are one chord: G3 high, C3 and E3 low", got == ([C3, E3], [G3]), str(got))
    null("strictly in order all three would be the upper hand's",
         got != model("rank", "upper", 1, [("on", C3), ("on", E3), ("on", G3)]))

    # Notes further apart than the window are dealt strictly by rank: a chord
    # rolled from the top at 15 ms a note is all bass with Lower: 1, each note
    # the lowest held as it starts - the owner's wish. Gathered, only its
    # lowest note would be.
    down = [G4 := 67, E4, C4, G3, E3, C3]
    rolled = [(15 * i, "on", n) for i, n in enumerate(down)]
    _, ch = split(kit, "lower", 1, *played(rolled), spaced=False)
    got = hands(ch[-1])
    check("a chord rolled from the top at 15 ms a note is all in the lower hand with Lower: 1",
          got == (sorted(down), []), str(got))
    gathered = (sorted(down)[:1], sorted(down)[1:])
    null("gathered as one chord only C3 would be", got != gathered, str(gathered))

    # The window is counted from the gather's first note, and half open: C3
    # 9.9 ms after G3 is the same chord; at 10 and at 15 it is a note of its
    # own, ranked among what is held, and G3 stays low.
    def after(ms):
        _, ch = split(kit, "lower", 1, "at 0", "on %d 100" % G3, "at %r" % ms, "on %d 100" % C3, spaced=False)
        return hands(ch[-1])
    check("C3 9.9 ms after G3 is gathered with it: C3 low, G3 high", after(9.9) == ([C3], [G3]), str(after(9.9)))
    null("strictly in order it would not be", after(9.9) != ([C3, G3], []))
    check("C3 10 ms after G3 is not: both low, G3 kept where it was dealt", after(10) == ([C3, G3], []), str(after(10)))
    got = after(15)
    check("nor 15 ms after: G3 keeps the lower hand, and C3 ranked lowest joins it", got == ([C3, G3], []), str(got))
    null("a gather that never closed would move G3 up", got != ([C3], [G3]))
    # Timed from the first note, not from the last: G3, E3 8 ms later and C3
    # 8 ms after that is G3 and E3 one chord (E3 low) and C3 a note of its
    # own. A window that slid with each note would make one chord of a run.
    _, ch = split(kit, "lower", 1, "at 0", "on %d 100" % G3, "at 8", "on %d 100" % E3, "at 16", "on %d 100" % C3, spaced=False)
    got = hands(ch[-1])
    check("G3, E3 at 8 ms and C3 at 16: the window is timed from G3, so E3 stays low and C3 joins it",
          got == ([C3, E3], [G3]), str(got))
    null("a window sliding with each note would gather all three and send E3 high", got != ([C3], [E3, G3]))

    # A held note never changes hand: the top-first chord, then A2 under it
    # 60 ms on. A2 is ranked lowest and joins the lower hand; C3 stays there.
    timed = ["at 0", "on %d 100" % G3, "at 1", "on %d 100" % E3, "at 2", "on %d 100" % C3]
    _, ch = split(kit, "lower", 1, *timed, "at 60", "on %d 100" % A2, spaced=False)
    got = hands(ch[-1])
    check("A2 60 ms after the chord: ranked lowest, it joins the lower hand and C3 keeps it", got == ([A2, C3], [E3, G3]), str(got))
    null("a gather that never closed would deal the chord again with A2 and move C3 up", got != ([A2], [C3, E3, G3]))

    # No note ever changes hand once it sounds, over a few hundred notes at
    # random moments and pitches, some within the window of each other and
    # some not, each key let go the next time it comes up: each note is in one layer from its start to its
    # stop. The null is a trace with one note moved, which the reading must see.
    import random
    rnd, cmds, t, down_now = random.Random(16), [], 0.0, set()
    for _ in range(300):
        t += rnd.choice([0.5, 1, 2, 3, 4, 7, 9.5, 12, 20, 45])
        n = rnd.randint(36, 84)
        # A key down is let go rather than struck again: a key struck again is a note starting
        # again, ranked again (the stack's rule, checked above), not a note moving.
        if n in down_now:
            cmds += ["at %r" % t, "off %d" % n]; down_now.discard(n)
        else:
            cmds += ["at %r" % t, "on %d %d" % (n, rnd.randint(30, 127))]; down_now.add(n)
    def moved(events):
        """Each note that arrives in one hand while it is in the other, or at the moment it left the
        other: since no key here is struck again while held, either is a note moved, whichever of the
        two hands' voices the keyboard happened to hand over first."""
        where, left, bad = {}, {}, []
        for when, n, h, k in events:
            if k == "on":
                if (n in where and where[n] != h) or left.get(n) == (when, 1 - h): bad.append((when, n))
                where[n] = h
            else:
                left[n] = (when, h)
                if where.get(n) == h: del where[n]
        return bad
    for end, count in (("lower", 1), ("lower", 3), ("upper", 2)):
        ev = sounded(kit, by_notes(end, count), cmds)
        check("no note changes hand while it sounds, %s %d, %d notes struck at random moments" % (end, count, sum(1 for c in cmds if c.startswith("on"))),
              ev and not moved(ev), str(moved(ev)[:5]))
    null("a note moved while it sounds is seen, whichever hand is handed its voices first",
         moved([(0, C3, 0, "on"), (2, C3, 1, "on")]) == [(2, C3)] == moved([(0, C3, 0, "on"), (2, C3, 0, "off"), (2, C3, 1, "on")]))

    # The pedal: a key let go under it still counts, gathered or not. C3 held
    # by the pedal alone, then G3 and E3 struck top first as one chord: both
    # are above C3, so both are the upper hand's.
    _, ch = split(kit, "lower", 1, "pedal 1", "at 0", "on %d 100" % C3, "at 10", "off %d" % C3,
                  "at 100", "on %d 100" % G3, "at 101", "on %d 100" % E3, spaced=False)
    got = hands(ch[-1])
    check("C3 held by the pedal, then G3 and E3 struck as one: C3 low, both of them high", got == ([C3], [E3, G3]), str(got))
    null("a pedal-held key not counted would leave E3 the gather's lowest, and low", got != ([C3, E3], [G3]))
    # The pedal waits with the notes, so a key let go 2 ms before the pedal
    # goes down is let go, as played; the pedal played at once would catch it.
    _, ch = split(kit, "lower", 1, "at 0", "on %d 100" % C3, "at 50", "off %d" % C3, "at 52", "pedal 1", spaced=False)
    check("a key let go 2 ms before the pedal goes down stops, as played", hands(ch[-1]) == ([], []), str(hands(ch[-1])))
    null("the pedal played at once, ahead of the waiting release, would hold C3", hands(ch[-1]) != ([C3], []))
    # A key struck again inside its own gather is still one note of it.
    _, ch = split(kit, "lower", 1, "at 0", "on %d 100" % G3, "at 1", "on %d 100" % C3, "at 2", "on %d 100" % G3, spaced=False)
    got = hands(ch[-1])
    check("G3, C3 and G3 again inside one gather: C3 low, G3 high", got == ([C3], [G3]), str(got))
    null("a repeat counted as two notes would hold three", len(got[0]) + len(got[1]) == 2)
    # And a key held and struck again in a gather is ranked once: Lower: 2, C3
    # held, then E3 and C3 again within the window. Below E3 is C3 alone, so
    # E3 is the lower hand's; C3 counted twice, once held and once gathered,
    # would put two notes under E3 and send it high.
    _, ch = split(kit, "lower", 2, "at 0", "on %d 100" % C3, "at 40", "on %d 100" % E3, "at 41", "on %d 100" % C3, spaced=False)
    got = hands(ch[-1])
    check("Lower: 2, C3 held, then E3 and C3 again as one: C3 and E3 low", got == ([C3, E3], []), str(got))
    null("C3 counted twice would send E3 high", got != ([C3], [E3]))

    # The controls deal what is held again by its gathers: the top-first chord
    # with the count turned to 2 is C3 and E3 low. Dealt again strictly in the
    # order struck, G3 came first and all three would be low.
    _, ch = split(kit, "lower", 1, *timed, "at 100", "splitcount lower 2", spaced=False)
    got = hands(ch[-1])
    check("the count turned to 2 over the top-first chord deals it again as one: C3 and E3 low, G3 high",
          got == ([C3, E3], [G3]), str(got))
    null("dealt again strictly in the order struck all three would be low", got != ([C3, E3, G3], []))
    # A control that leaves the split by notes with notes waiting plays them,
    # in order, before anything played at once: a release arriving after the
    # switch must not overtake its own note and leave it held.
    _, ch = split(kit, "lower", 1, "at 0", "on %d 100" % C3, "at 2", "splitby key", "at 3", "off %d" % C3, spaced=False)
    check("by notes, C3 struck, the split turned to key 2 ms later and C3 let go: nothing is left held",
          hands(ch[-1]) == ([], []), str(hands(ch[-1])))
    null("C3 still waiting as its release played would be held for good", hands(ch[-1]) != ([C3], []))

    # The screen: by notes a strike is laid as its note sounds, in the hand it
    # sounds in. G3 then C3 2 ms later: G3 the upper hand's, laid at 10 ms, C3
    # the lower's at 12. By key nothing waits.
    out = kit.run("keyboard_cpp", "run screen=1 wakes=1\n%s\nend" % "\n".join(
        by_notes() + ["at 0", "on %d 100" % G3, "at 2", "on %d 100" % C3, "at 40"]))
    laid, now = [], 0.0
    for line in out.strip().split("\n"):
        for part in line.split(" | ")[0].split(" :: ")[1:]:
            w = part.split()
            if w[0] == "wake": now = float(w[1])
            if w[0] == "screen": laid.append((int(w[1]), int(w[3]), now))
    check("by notes each strike is laid once, as its note sounds, in its hand: G3 upper at 10 ms, C3 lower at 12",
          laid == [(G3, 2, AHEAD), (C3, 1, AHEAD + 2)], str(laid))
    null("laid as it arrived G3's arc would be in the lower hand, where it was alone", laid[:1] != [(G3, 1, 0)])
    out = kit.run("keyboard_cpp", "run screen=1\nmode poly\nlayers split\nat 0\non %d 100\nat 2\non %d 100\nat 30\nend" % (G3, C3))
    laid = [l.split(" :: ")[0].split(" | ")[0] for l in out.strip().split("\n") if " :: screen " in l]
    check("by key the screen is struck at once, as before", laid == ["on", "on"], str(laid))
    null("by key nothing is laid at a wake", laid != ["at"])
    # And by key nothing waits: the voices are set at the note's own command.
    ev = sounded(kit, ["mode poly", "layers split"], played(block))
    check("by key every note sounds the moment it arrives", [(t, n) for t, n, _, k in ev if k == "on"] == [(t, n) for t, _, n in block],
          str(ev))
    null("by notes the same chord sounds %d ms later" % AHEAD,
         [(t, n) for t, n, _, k in sounded(kit, by_notes(), played(block)) if k == "on"] != [(t, n) for t, _, n in block])
    # Each note restarts its hand's fade once, in the hand it sounds in.
    out, _ = split(kit, "lower", 1, "at 0", "on %d 100" % G3, "at 2", "on %d 100" % C3, spaced=False)
    strikes = out[-1].split(" strikes ")[1].split()[:2]
    check("G3 then C3 2 ms later: one strike in each hand, G3's in the upper", strikes == ["1", "1"], str(strikes))
    null("dealt strictly in order both would strike the lower hand", strikes != ["2", "0"])

    # --- no ghost: what the instrument plays is the key split, 10 ms later ---
    # The 25 ms gather this replaced sounded a chord's first notes at once and
    # dealt them again as a lower note arrived; a note moved was let go in the
    # hand it began in, and rang on there for that hand's release (the ghost,
    # after-stage-5.md). So: on every bank preset, split by notes, C5 G4 E4
    # struck top first 1 ms apart and F#2 at 3 ms - the chord the ghost was
    # measured on, every chord note one the old gather moved - rendered whole
    # by the instrument. The hands it deals (F#2 low, the chord high) are
    # those a key split at C4 gives, so what is heard must be that key split
    # with every note and release played 10 ms later, to the bit: nothing of a
    # moved note can be in it. Both runs stop at the same moments with a
    # message the keyboard ignores (polyphonic pressure) where the other has a
    # note, since render_cpp starts a host block at each stop and the generator
    # retires a finished voice at the end of a block; the instrument plays it
    # at the same sample either way. The nulls: the key split not delayed, which
    # the comparison must see, and the ghost itself - the key split with the
    # chord dealt low first and moved high as F#2 arrives, as the gather did.
    rate = 48000
    on, off, nop = (lambda n: [0x90, n, 100]), (lambda n: [0x80, n, 0]), (lambda n: [0xA0, n, 0])
    C5, G4_, E4_, FS2 = 72, 67, 64, 42
    struck = [(0, on(C5)), (1, on(G4_)), (2, on(E4_)), (3, on(FS2)),
              (300, off(G4_)), (350, off(FS2)), (420, off(C5)), (421, off(E4_))]
    def heard(code, patch, events, tag):
        path = os.path.join(BUILD, "splitnotes-%s.f32" % tag)
        lines = [["make", rate, code, patch], ["to", 0.2], ["record", "heard", path]]
        for t, m in sorted(events, key=lambda e: e[0]):
            lines += [["to", 0.2 + t / 1000], m if m[0] == "control" else ["midi", *m]]
        kit.render(lines + [["to", 0.8], ["record", "heard"]], raw=True)
        return np.fromfile(path, "<f4")
    later = [(t + AHEAD, m) for t, m in struck]
    stops = [(t, nop(m[1])) for t, m in struck] + [(t + AHEAD, nop(m[1])) for t, m in struck]
    split_by = {"midiMode": "poly", "layers": "split", "splitBy": "notes", "splitEnd": "lower", "splitCount": 1}
    by_key = {"midiMode": "poly", "layers": "split", "splitAt": 60}
    same, unshifted, ghosts = [], [], []
    for name, code in kit.preset_codes().items():
        notes = heard(code, split_by, struck + stops[len(struck):], "notes")
        key = heard(code, by_key, later + stops[:len(struck)], "key")
        same.append((name, bool(np.array_equal(notes, key))))
        unshifted.append(bool(np.array_equal(notes, heard(code, by_key, struck + stops[len(struck):], "now"))))
        moved = [(t + AHEAD, m) for t, m in struck[:3]] + [(3 + AHEAD, ["control", "splitAt", "60"])] + later[3:]
        ghost = heard(code, dict(by_key, splitAt=84), moved + stops[:len(struck)], "ghost")
        ghosts.append(bool(np.array_equal(ghost, key)))
    check("split by notes, every bank preset plays C5 G4 E4 F#2 struck top first as the key split does 10 ms later, to the bit",
          all(ok for _, ok in same), str([n for n, ok in same if not ok]))
    null("the key split played at once is not the same", not any(unshifted))
    null("the chord dealt low and moved high as F#2 arrives (the gather's ghost) is not the same, on any preset", not any(ghosts))

    # --- the Chord window is a setting (the owner's, 16 Nov): 0 to 15 ms ---
    # At nought nothing waits and the dealing is the strict rank rule, each
    # note ranked among those held as it arrives, whatever landed first. Over
    # the random notes above: every note sounds at the command that played it
    # (no wake), and each in the hand the rank rule gives it. The null is a
    # window of 1 ms, the least that waits, which sounds every note late.
    def strict(cmds, end, count):
        """The rank rule's hand for each note struck, in Python, as (time, note, hand), at the moment it was played."""
        held, out, t = [], [], 0.0
        upper = end == "upper"
        for c in cmds:
            w = c.split()
            if w[0] == "at": t = float(w[1]); continue
            n = int(w[1])
            held = [h for h in held if h != n]
            if w[0] == "off": continue
            beyond = sum(1 for h in held if (h > n if upper else h < n))
            counted = beyond < count
            out.append((t, n, (1 if counted else 0) if upper else (0 if counted else 1)))
            held.append(n)
        return out
    for end, count in (("lower", 1), ("lower", 3), ("upper", 2)):
        ev = sounded(kit, by_notes(end, count, 0), cmds)
        got = [(t, n, h) for t, n, h, k in ev if k == "on"]
        # A note can drop out of its hand's eight voices and come back; only the moments notes are played are read.
        want = strict(cmds, end, count)
        played_at = [(t, n, h) for t, n, h in got if (t, n) in {(a, b) for a, b, _ in want}][:len(want)]
        woken = any(" :: wake" in l for l in kit.run("keyboard_cpp", "run wakes=1\n%s\nend" % "\n".join(by_notes(end, count, 0) + cmds)).split("\n"))
        check("Chord window 0, %s %d: every one of %d notes sounds the moment it is played, in the hand the strict rank gives it"
              % (end, count, len(want)), played_at == want and not woken,
              "woken %s, differing %s" % (woken, [x for x in zip(played_at, want) if x[0] != x[1]][:3]))
    late = [(t, n) for t, n, h, k in sounded(kit, by_notes("lower", 1, 1), cmds) if k == "on"][:5]
    null("a window of 1 ms sounds every note a millisecond late", late != [(t, n) for t, n, _ in strict(cmds, "lower", 1)][:5], str(late))
    # And the block chord top first at 0, 2, 4 and 6 ms, at nought, is dealt
    # as it arrives - all four the lower hand's - where 10 deals it by pitch.
    _, ch = split(kit, "lower", 1, "splitwindow 0", *played(block), spaced=False)
    got = hands(ch[-1])
    check("at 0 the top-first block chord is dealt strictly, as it arrives: all four low", got == (sorted(n for _, _, n in block), []), str(got))
    null("at the default 10 it is dealt by pitch, C3 alone low", got != ([C3], [E3, G3, C4]))
    # Fifteen gathers what ten does not: C3 12 ms after G3.
    def window_of(ms):
        _, ch = split(kit, "lower", 1, "splitwindow %d" % ms, "at 0", "on %d 100" % G3, "at 12", "on %d 100" % C3, spaced=False)
        return hands(ch[-1])
    check("a Chord window of 15 gathers C3 12 ms after G3 into one chord: C3 low, G3 high", window_of(15) == ([C3], [G3]), str(window_of(15)))
    null("at 10, C3 12 ms after G3 is a note of its own: both low", window_of(10) == ([C3, G3], []), str(window_of(10)))
    # And to the bit on the instrument: at nought, split by notes, F#2 struck
    # and then C5 G4 E4 1 ms apart (strictly F#2 low and the chord high, as
    # the key split at C4 has them) is heard as the key split at once, with no
    # wait, on every bank preset - the window read from the setup code, as a
    # project or a preset carries it. The null is the default window, 10 ms late.
    first = [(0, on(FS2)), (1, on(C5)), (2, on(G4_)), (3, on(E4_)), (300, off(G4_)), (350, off(FS2)), (420, off(C5)), (421, off(E4_))]
    at_once, waited = [], []
    for name, code in kit.preset_codes().items():
        strict_heard = heard(code, dict(split_by, splitWindow=0), first, "w0")
        key = heard(code, by_key, first, "w0key")
        at_once.append((name, bool(np.array_equal(strict_heard, key))))
        waited.append(bool(np.array_equal(heard(code, split_by, first, "w10"), key)))
    check("a Chord window of 0, every bank preset: F#2 then C5 G4 E4 split by notes is the key split at once, to the bit",
          all(ok for _, ok in at_once), str([n for n, ok in at_once if not ok]))
    null("the default window of 10 is not: it waits", not any(waited))
    # And the window as the face sets it, by the instrument's control rather
    # than a setup: nought there is nought, not the default a menu's nought
    # would read as if taken for unset. The null is the control set to 10.
    code = kit.preset_codes()["Tine piano"]
    by_control = heard(code, split_by, [(-100, ["control", "midiSplitWindow", "0"])] + first, "w0c")
    same_as_key = bool(np.array_equal(by_control, heard(code, by_key, first, "w0ckey")))
    check("the Chord window set to 0 by the instrument's control plays at once, as the key split, to the bit", same_as_key)
    ten = heard(code, split_by, [(-100, ["control", "midiSplitWindow", "10"])] + first, "w10c")
    null("set to 10 by the control it waits", not np.array_equal(ten, heard(code, by_key, first, "w0ckey")))
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
