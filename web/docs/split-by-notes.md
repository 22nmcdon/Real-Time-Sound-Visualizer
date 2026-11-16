# Splitting the hands by notes

Asked for by the owner on 15 November, after playing the site: besides splitting
the keyboard at a key, a split by the notes held - the bottom few notes are the
lower hand and the rest the upper, or the other way round, with the count
chosen. Written down on 15 November, said go on 16 November, and **built on 16
November** on the core's keyboard, so the site and the plugin deal the same
hands. What follows is what was decided, and why where it could have gone the
other way.

## How it behaves

- **A note's hand is fixed when the note starts** (the owner's call, 15 Nov). A
  held note keeps the hand it began in until it is let go, so nothing jumps
  between hands, and between figures, in the middle of a chord. The other way -
  re-sorting the held notes every time one starts or stops - was rejected for
  exactly that jump. Letting a note go deals nothing again either: with Lower: 2
  over E3 G3 C4 and C3 struck under them, G3 stays low, and when E3 and G3 are
  let go C4 stays the upper hand's though it is now second from the bottom.
- **Rank, not fill** (decided 16 Nov). Two readings of "the lowest N go to the
  lower hand" were possible for a note struck while others are held: its *rank*
  among the notes held at that moment (the lower hand's if fewer than N held
  notes are below it), or *filling* the counted hand first (the lower hand's if
  that hand holds fewer than N). They differ when a note arrives under a held
  chord: with Lower: 1 and C3 E3 G3 held, A2 is the lowest note held, so by rank
  it joins the lower hand (which then holds two); by fill the lower hand is full
  and A2 goes high. Rank is the one built, because it is what the brief says ("its
  rank among the notes held at that moment"), and because it is what a bass line
  walking legato under a held chord wants: the new bass note is the bass. Fill would
  hand it to the melody. The cost: the lower hand can hold more than N notes for a
  moment, while one bass note overlaps the next.
- **Which end is counted.** *Lowest* and a count N gives a note the lower hand
  if fewer than N held notes are below it, and the upper otherwise; *highest*
  is the mirror, counted from the top, for the upper hand.
- **Fewer notes held than the count** all go to the counted hand - which rank
  gives without a rule of its own, since every note is within N of the end.
- **The sustain pedal** (decided 16 Nov): a key let go under the pedal is still
  held - it still sounds - so it counts in the rank. With Lower: 1, C3 let go
  under the pedal and G3 struck: G3 is the upper hand's.
- **A key struck again** starts again, so it is ranked again: with Lower: 1, G3
  alone is low, C3 struck under it is low too, and G3 struck again is ranked over
  C3 and goes high. This is the stack's own rule (a repeated key moves to the top
  of the order it was struck in), not one added for the split.
- **The arpeggiator**: a step is a copy of a held note, up to three octaves up,
  and keeps that note's hand, so the arpeggio of a bass note stays in the bass's
  sound however high it climbs. (Before this the step's hand was its pitch's,
  which by key is still the rule.)
- **The controls deal again.** Moving *by key / by notes*, the end or the count,
  or loading a setup over held keys, deals the held notes again as if they had been
  struck in the order they were. Otherwise a count turned with a chord held would
  do nothing until the next note. This is the control acting, never a note: no note
  starting or stopping moves another note's hand.
- **Learn is the key split's.** It is hidden by notes, choosing by notes lets it
  go, and the instrument's keyboard ignores it while splitting by notes.
- **N is one to five**: one hand's fingers. A count past five is a chord in one
  hand that no hand plays; and each hand has eight voices (`kPolyVoices`), so the
  other hand keeps at least three.

## The control

The Layers menu, with *split*, gains *by key · by notes* beside it, so the row
reads "Layers: split, by notes". Under it, beside the pairing menu (*a figure
each · A against B*), is Learn's *at C4* by key, or the end (*lowest · highest*)
and the count (*1* to *5*) by notes. A row of its own was tried first and put
Play 11 px over at 1400x900 (patchtest); beside a label the three menus left the
first 21 px. So a split adds no row. The readout says *split by notes: lowest 1
to the lower hand*.

## Stored

Three fields beside `splitAt`: `splitBy` (`key` or `notes`), `splitEnd`
(`lower` or `upper`) and `splitCount` (1 to 5), all menus in `SETUP_FIELDS`
and the core's schema. The split has become a structure - how it decides, then
the key, or the end and the count - but no field already stored changes meaning:
`layers` is still whether there is a split, and `splitAt` still the key. So the
fields are additive, with defaults (`key`, `lower`, 1) that are the key split,
and every code from before them is the split it was: no version bump and no
decode pass in `migrateSetup`, as CLAUDE.md allows for a purely additive field.
The plugin keeps them in its state, which is the setup it was given and the
hands moved since (`midiSplitBy`, `midiSplitEnd`, `midiSplitCount` are menus the
instrument hears, `HOST_CONTROLS`).

## Where it lives

`core/include/scope/keyboard.h`: each held note carries its hand (`Held::hand`),
dealt as it starts (`Keyboard::dealt`) and again by the controls
(`Keyboard::redeal`); `handOf` is what the layers, the strikes and Scan's strike
read, by key from the pitch as before and by notes from the note. The face keeps
a mirror for what it shows (`midiDealt`, `midiRedeal`, `layerHandOf` in
`scope.html`), held to the instrument by layertest.

## Checks

`core/tests/pieces/splitnotes.py`, on the core's keyboard, each with the other
rule as its null and each also caught by a mutant of the core: rank against fill
(A2 under C3 E3 G3), fixed at start against re-sorting (C3 under E3 G3 C4, and
releases), fewer than N, Upper mirroring Lower, the pedal, a repeated key, the
strikes, the arpeggio's steps and the controls dealing again. `web/tests/layertest.py`
plays the chord on the site's face and reads the instrument's lanes; its null cuts
the face's sends, so the instrument splits at its key. The plugin's shell test has a
host play the chord into a project that splits by notes with the upper hand silent;
its null is the same project split by key. `fittest.py` measures Play with the split
by notes.

## Not settled

Strictly fixed at the start, a chord struck all at once is dealt in the order its
notes happen to arrive, a millisecond or two apart: with Lower: 1, if a chord note
arrives before the bass, it is the lowest held at that moment and takes the lower
hand, and so does the bass after it. Written into `after-stage-5.md` for the owner,
with what a fix would cost.
