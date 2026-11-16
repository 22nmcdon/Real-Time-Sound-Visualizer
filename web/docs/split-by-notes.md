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
- **A struck chord is ranked as one, by looking ahead 10 ms** (the owner's decisions,
  16 Nov: the gather the same morning, the look-ahead that evening, replacing how the
  gather sounded). A chord struck "at once" reaches the keyboard a millisecond or two
  apart, in whatever order the fingers land, so strictly by the moment each started,
  with Lower: 1, a chord note landing before the bass took the lower hand and the bass
  joined it. So while the split is by notes, **every note waits 10 ms from its own
  arrival before it sounds**, and its release and the pedal wait the same: a fixed
  latency, in that mode only. The order and the gaps between notes are kept to the
  sample - a fast roll, a grace note or a quick run sounds exactly as played, 10 ms
  later - and nothing is gathered into a block or reordered. Because the first note of
  a chord sounds 10 ms after it arrived, every note that arrived within those 10 ms is
  known before it sounds: the notes that arrive within 10 ms of a gather's first are
  dealt together, by pitch, each ranked among the notes held and the rest of its gather
  (a key held and struck again in the gather counted once), and then each sounds at its
  own moment in the hand it was dealt. No note is dealt again once it sounds, so none
  moves and nothing of one is left in the other hand's sound. The window is timed from
  the gather's first note, not sliding (a run of notes 8 ms apart is not one long
  chord), and is half open: 9.9 ms after the first is the same chord, 10 is not.
  Further apart than that, notes are dealt strictly by the rank rule: a note below
  everything held is the lower hand's, so a chord rolled slowly from the top, at 15 ms a
  note, is all bass with Lower: 1, as the owner wants. The strike on the screen is laid
  as each note sounds, in its hand, and restarts that hand's fade once. The key split,
  every other mode and the arpeggiator's own steps play at once, as before, to the bit.
- **Why 10 ms** (the owner's figure). A tight block chord lands within about 10 ms; a
  5-pin MIDI cable takes about 1 ms a note (three bytes at 31 250 baud), so a chord of
  six spreads over 6 ms on the wire alone; a roll a player means as a roll is slower.
  And it is latency on every note in this mode, which a player starts to feel at about
  25. It is `Keyboard::kLookAhead`, its own figure rather than the arpeggiator's 25 ms
  (`kArpGather`, which waits once a phrase for a chord to step from); to gather a wider
  spread, widen it there - one line - at that cost.
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
gather (`Held::gather`). While the split is by notes (`lookingAhead`), a note, a release
or the pedal is kept in `ahead_` with the moment it is due and a wake for it, which the
instrument serves at its sample (`Instrument::play`, as it serves the arpeggiator's first
step); the first note of a gather to come due deals every note waiting undealt
(`dealGather`), which are exactly those that arrived within the window, and each plays
in turn (`playAhead`). Anything that arrives to be played at once - a control has left
the split by notes - first plays what is waiting, in order, so a release never overtakes
its own note (`catchUp`); a panic drops what is waiting. Played at once, a note is still
dealt and gathered, unheard, since a control moved to the split by notes deals what is
held by its gathers (`Keyboard::redeal`). `handOf` is what the layers, the strikes and
Scan's strike read, by key from the pitch as before and by notes from the note. The face
keeps a mirror for what it shows (`midiDealt`, `midiRedeal`, `layerHandOf` in
`scope.html`), held to the instrument by layertest; it does not wait, dealing a gather
again as each note arrives, so it shows a few milliseconds early what the instrument then
plays. The face times a gather by its own clock (`MIDI_GATHER`) and the instrument by the
samples, so a note within a block of the window's edge can be gathered by one and not the
other; the face only shows the hands. What one turn of the page sends the site's worklet
goes together as the turn ends, so a chord the page plays in one turn reaches the
instrument at once however long the page takes over each note (web/README.md says what
broke without it, and the limit left: a Web MIDI port's notes, each in an event of its own).

The instrument places a wake at the first sample at or after its time, and since the clock
is milliseconds summed block by block, a wake due exactly on a sample (480 samples after a
note at 48 kHz) came out a hair past it and played a sample late, or a hair before a
block's end and played before the block's step where a message on that sample plays after
it. So a wake within a millionth of a sample of a whole sample is placed on it
(`placed`, in `Instrument::play`); found by the render check below, which compares to the
bit.

**The plugin does not report the 10 ms to the host as latency.** A host compensates a
reported latency by playing everything that much early, every note in every mode and the
audio beside it; the look-ahead applies in one mode only, and changes as the split is
switched, which a host takes as a reason to rebuild its graph or ignores until playback
restarts. Reported, the key split and every other mode would be shifted to make up a delay
they do not have. Unreported, a player hears 10 ms on notes split by notes, live or from a
track, which is the cost the owner accepted for the dealing; the audio of a host's track
beside it is 10 ms ahead of those notes, as it would be beside any synth with 10 ms more
latency. The limiter's own 6 ms look-ahead is reported as it always was.

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

The look-ahead's own checks are splitnotes.py's too. A roll 3 ms apart sounds with its
gaps kept, each note exactly 10 ms late, and every note keeps its length (null: the
gather released at once as its first note sounds, every gap nought; and a release played
at once, every note 10 ms short); a grace note 4 ms before its note sounds 4 ms before it,
for as long as it was held. A block chord top first at 0, 2, 4 and 6 ms deals by pitch
(null: the strict order without the look-ahead), and Upper mirrors it. A chord rolled from
the top at 15 ms a note is all the lower hand's with Lower: 1 (null: gathered as one). The
window: 9.9 ms after the first is gathered, 10 and 15 are not (null: one that never closes),
timed from the first note (null: one that slides). Over 162 notes struck at random
moments, some within the window of each other and some not, no note changes hand while it
sounds, for Lower 1, Lower 3 and Upper 2 (null: a trace with one note moved, whichever
hand is handed its voices first). The pedal waits with the notes (a key let go 2 ms before
the pedal goes down stops), a held key struck again in a gather is ranked once, the
controls deal a gather again as one, and a control leaving the split by notes plays what
waits before what comes next (null: the release overtaking its note, which is left held
for good). By notes each strike is laid once, as its note sounds, in its hand; by key at
once, and by key every note sounds the moment it arrives (null: by notes, 10 ms later).
And no ghost, on the instrument whole (`render_cpp`): on every bank preset, split by notes,
C5 G4 E4 struck top first 1 ms apart and F#2 at 3 ms (the chord the ghost was measured on,
every chord note one the old gather moved) is heard to the bit as the key split at C4
with every note and release 10 ms later (nulls: the key split not delayed, and the ghost
itself - the chord dealt low and moved high as F#2 arrives - neither the same on any
preset). Against mutants of the core each check above goes red: the gather released at
once, no look-ahead, releases or the pedal played at once, no catching up, a repeat
counted twice, the held notes left out of the rank, the gather dealt a note at a time, and
a window of 15.5 ms. Against the 25 ms gather this replaced (its keyboard, from the commit
before) fifteen go red, among them the timing, the random notes' moves in all three
settings, the strikes and the render to the bit.

On the site, layertest strikes G3 E3 C3 at once and reads the lower hand's lanes 80 ms
after, where the old gather's ghost rang: E3 and G3 there are no more than the key split
at D3 leaves read at the same moment in its notes' lives (null: the three 60 ms apart, all
low, E3 and G3 many times that). And it plays the chord in one turn with the page kept busy
15 ms after each note, which as each note was sent put them further apart in the
instrument than the window: still one chord, since what a turn sends the worklet goes
together as the turn ends (null: a turn ended between the notes, all three low; and the
same row red against the page's old `send`). The plugin's shell test has a host's note
split by notes sound exactly 10 ms of samples after the same note split by key, and the
host told the same latency for both (null: the figure that counted the look-ahead).

## Settled: how the gather sounds (the owner's decision, 16 Nov)

The gather dealt a struck chord right from the morning of 16 November; what it could not
do without one cost or the other was sound a note before it knew the note's hand. As first
built, the first notes of a gather sounded at once in the hand they were first dealt and
moved when a lower note arrived within 25 ms; a note that moved was let go in that hand and
struck in the other, and **letting go is a release**: the moved note rang on in the first
hand for that hand's release. Measured on the bank (render_cpp, every bank preset split
Lower: 1, C5 G4 E4 struck 1 ms apart top first and F#2 at 3 ms, so all three chord notes
moved; the lower hand heard alone with `bAmp` nought, by the energy in the chord notes'
first three harmonics): from 30 to 100 ms the moved notes in the lower hand were 2 to 22 dB
under the chord as heard, and 8 to 46 dB over what the key split leaves at those pitches,
through 300 ms on the Tine piano and Crossed hands - audible wherever the hands' sounds
differ, which is the point of a split. Three ways were put to the owner: as built (no
latency, the ghost); sound at once and cut a moved note in the governor's 10 ms fade (the
ghost -30 to -64 dB after 10 ms in seven presets of nine, but -3 to -10 dB in its first
10 ms, at the chord's own onset); or wait, holding a gather's notes until it closes (no
ghost, up to 25 ms of latency on a gather's first note).

The owner chose to wait, but not as the third way had it: not a gather held and released
as a block, which would have made a roll or a grace note into a chord, but **every note
delayed by the same 10 ms**, so the playing keeps its shape and the dealing gets the time
it needs. 10 rather than 25 because the latency is on every note in the mode and 25 is felt;
the risk the shorter window carries - a chord spread wider than 10 ms dealt as it comes - is
the rule the owner wants for a slow roll anyway (a chord rolled down from the top is all
bass). The re-deal and its release are gone; the render check above holds that nothing of a
moved note is heard, to the bit. Also in `after-stage-5.md`.
