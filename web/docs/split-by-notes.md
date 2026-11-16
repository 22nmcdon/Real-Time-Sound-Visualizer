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
- **Rank, not fill** (the owner's decision, 16 Nov, with fill as the test's null). Two readings of "the lowest N go to the
  lower hand" were possible for a note struck while others are held: its *rank*
  among the notes held at that moment (the lower hand's if fewer than N held
  notes are below it), or *filling* the counted hand first (the lower hand's if
  that hand holds fewer than N). They differ when a note arrives under a held
  chord: with Lower: 1 and C3 E3 G3 held, A2 is the lowest note held, so by rank
  it joins the lower hand (which then holds two); by fill the lower hand is full
  and A2 goes high. Rank is the owner's choice, and it is what the brief said ("its
  rank among the notes held at that moment"), and it is what a bass line
  walking legato under a held chord wants: the new bass note is the bass. Fill would
  hand it to the melody. The cost: the lower hand can hold more than N notes for a
  moment, while one bass note overlaps the next.
- **A struck chord is ranked as one** (the owner's decision, 16 Nov, built the same
  day). A chord struck "at once" reaches the keyboard a millisecond or two apart, in
  whatever order the fingers land, so strictly by the moment each started, with Lower: 1,
  a chord note landing before the bass took the lower hand and the bass joined it. So
  the notes that start within **25 ms** of a gather's first are one chord and are
  ranked together, by pitch, among everything held: the arpeggiator's figure
  (`kArpGather`), so the instrument has one idea of "at once", comfortably wider than
  the few milliseconds a struck chord spreads over and narrower than the quickest grace
  note a player means as a note of its own. The window is timed from the gather's first
  note, not from the last (a run of notes 20 ms apart is not one long chord), and is
  half open: 24.9 ms after the first is the same chord, 25 is not. A note never changes
  hand once its gather has closed - that is the rule bent by the window and no further.
  While the gather is open its notes sound at once, each in the hand it was dealt as it
  arrived, and a later note of the gather can move an earlier one; what that sounds
  like, and what the other way costs, is below, for the owner. The strike on the screen
  waits for the gather to close (25 ms at the most), so its arc lands in the picture of
  the hand the note ends up in; a note moved into a hand restarts that hand's fade, as it
  would have had it arrived there. Only the split by notes is touched: the key split and
  every other mode deal and strike exactly as before.
- **Which end is counted.** *Lowest* and a count N gives a note the lower hand
  if fewer than N held notes are below it, and the upper otherwise; *highest*
  is the mirror, counted from the top, for the upper hand.
- **Fewer notes held than the count** all go to the counted hand - which rank
  gives without a rule of its own, since every note is within N of the end.
- **The sustain pedal** (the owner's decision, 16 Nov): a key let go under the pedal is still
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
  struck in the order they were, a gather again as one chord. Otherwise a count turned with a chord held would
  do nothing until the next note. This is the control acting, never a note: no note
  starting or stopping moves another note's hand.
- **Learn is the key split's.** It is hidden by notes, choosing by notes lets it
  go, and the instrument's keyboard ignores it while splitting by notes.
- **N is one to six** (the owner's call, 16 Nov: "from 1 to about 6"). Each hand
  has eight voices (`kPolyVoices`), so at six the other hand keeps at least two.

## The control

The Layers menu, with *split*, gains *by key · by notes* beside it, so the row
reads "Layers: split, by notes". Under it, beside the pairing menu (*a figure
each · A against B*), is Learn's *at C4* by key, or the end (*lowest · highest*)
and the count (*1* to *6*) by notes. A row of its own was tried first and put
Play 11 px over at 1400x900 (patchtest); beside a label the three menus left the
first 21 px. So a split adds no row. The readout says *split by notes: lowest 1
to the lower hand*.

## Stored

Three fields beside `splitAt`: `splitBy` (`key` or `notes`), `splitEnd`
(`lower` or `upper`) and `splitCount` (1 to 6), all menus in `SETUP_FIELDS`
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

`core/include/scope/keyboard.h`: each held note carries its hand (`Held::hand`) and its
gather (`Held::gather`), dealt as it starts with the rest of its gather
(`Keyboard::dealtAmong`, `kGather`) and again by the controls
(`Keyboard::redeal`); the screen's strikes of a gather wait for its close
(`strikeGathered`, on the keyboard's wakes, which the instrument serves at their
sample); `handOf` is what the layers, the strikes and Scan's strike
read, by key from the pitch as before and by notes from the note. The face keeps
a mirror for what it shows (`midiDealt`, `midiRedeal`, `layerHandOf` in
`scope.html`), held to the instrument by layertest. The face times a gather by its own
clock (`MIDI_GATHER`) and the instrument by the samples, so a note within a block of the
window's edge can be gathered by one and not the other; the face only shows the hands.

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
by notes. The gather's checks are splitnotes.py's too: a chord arriving top first within
the window deals by pitch, for Lower and for Upper (null: the strict order, the code
before it); C3 24.9 ms after G3 is gathered and 25 and 40 ms after are not (null: a window
that never closes); the window is timed from the first note (null: one sliding with each);
a chord's note keeps its hand when a note arrives under it after the gather (null: a
gather that never closes); the pedal and a key struck again within a gather; the controls
dealing a gather again as one; the screen's strikes waiting for the close and landing in
the hand dealt, while by key they land at once; and a moved note restarting its new
hand's fade. Each was also seen red against a mutant of the core: a window of nought, one
that never closes, one that slides, strikes laid at once, no restart for a moved note,
and the controls dealing strictly in order. layertest strikes G3 E3 C3 top first in one
tick on the site's face and reads the instrument's lanes (null: the same three 60 ms
apart, dealt in turn, all low).

## Not settled: what a re-deal sounds like (for the owner)

The gather deals a struck chord right. What it cannot do without one cost or the other
is sound a note before it knows the note's hand. Built, the first notes of a gather
sound at once in the hand they were first dealt and move when a lower note arrives; a
note that moves is let go in that hand and struck in the other, and **letting go is a
release**: the moved note rings on in the first hand for that hand's release. Measured
on the bank (16 Nov, render_cpp, every bank preset split Lower: 1, C5 G4 E4 struck 1 ms
apart top first and F#2 at 3 ms, so all three chord notes move; the lower hand heard
alone with `bAmp` nought, by the energy in the chord notes' first three harmonics): from
30 to 100 ms the moved notes in the lower hand are 2 to 22 dB under the chord as heard
(Tine piano -2.7, Tines at the radius -3.8, Bass under the pad -2.3, Slow pad -20.3), and
8 to 46 dB *over* what the key split leaves at those pitches in the lower hand, through
300 ms on the Tine piano and Crossed hands. That is audible wherever the hands' sounds
differ, which is the point of a split. So it is not settled; three ways, with numbers:

1. **As built: sound at once, release a moved note.** No latency; the ghost above.
2. **Sound at once, cut a moved note** in the governor's 10 ms fade rather than its
   release (measured on a copy of the core that cuts any voice let go within 25 ms of its
   birth). From 10 ms on the ghost falls to 30 to 64 dB under the chord in seven presets
   of nine (Slow pad and Bass under the pad keep -12 and -13 dB), but in the first 10 ms
   it is -3 to -10 dB under the chord, at the chord's own onset: a few milliseconds of
   the chord in the other hand's sound. Not shown inaudible, and not built.
3. **Wait: hold a gather's notes silent until it closes.** No ghost and no strike moved,
   at a cost of up to 25 ms of latency on the first note of every gather in the split by
   notes (and on a single note struck alone, a gather of one), against none by key. A
   player feels 25 ms. A shorter window (10 ms) would shorten the wait, at the risk of a
   chord spread wider than that being dealt in arrival order again.

The owner chooses; until then the branch sounds at once and releases (1). Also in
`after-stage-5.md`.
