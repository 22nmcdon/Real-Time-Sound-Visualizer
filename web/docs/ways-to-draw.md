# Ways to draw

Agreed with the owner on 10 November, to build **after the redesign** (the second pass's
G6 and G7, and the silent start). This is what to build and why, so the ideas are not lost.
**Step 2 is built** (12 Nov): a page-only prototype of the constellation, *Note* figures on
the three places, still, behind a switch - see *The prototype*, below. Nothing else is.

## The problem

Today every note in a sound merges into one figure: the outline notes lean to X and Y and
the rest are drawn along the diagonal (*Draw*, on Play). That makes strong pictures for a
dyad or a triad, and the loop reads them well. With many notes in a chord, or notes played
fast, the one figure turns to a tangle: you can no longer see the notes in it, and Scan
reads a blur.

## The rule it has to follow

The first rule of `making-it-one-instrument.md` is that a feature acts on the loop: the
screen is what Scan reads back as sound. A way to draw is therefore a way the instrument
*sounds*, not a skin. Two consequences shape everything below:

- **Where a note lands decides what it does to the tone.** A note drawn across Scan's
  reading circle brightens the voice; one drawn away from it does little. Placement is
  part of the sound.
- **What a note draws should mean something musical,** so that the picture teaches what is
  being played, as the dyad's 2:3 figure does now.

## The modes

A *Draw* choice, beside today's (which stays the default):

1. **One figure** - today's: every note merged, the outline notes on X and Y.
2. **A figure each note** - the *constellation*. Each held note draws its own figure,
   the one it would draw alone: a sine with Quarter turn is a ring, and another shape its
   own closed curve. It is not an interval figure: a figure of two notes is a dyad's, one
   on each axis, and has no place in a constellation (the owner's correction, 10 Nov, to a
   first draft that drew each note against the bass; the interval figures are *Pairs*,
   below). A note's figure is as large as it is loud, so it grows on the attack and fades
   with its envelope, and Persistence decides how long the constellation lingers. A fast
   run scatters a trail of rings rather than smearing one figure.
3. **Clock**, **Helix**, **Pairs**, **Ripples** and **Split screen**, sketched live with
   these (`https://claude.ai/artifact/J8CE64RxhCoSybijwxN2Bc`, drawn from the notes' real
   equal-tempered frequencies and the instrument's own roles): each note's ring round
   Scan's circle by pitch class (Clock, the strongest tie to the loop) or on a spiral by
   octave (Helix); every pair of notes as the dyad it makes (Pairs); each note's ring
   spreading from where it lands (Ripples); each hand's figure on its own half (Split).
4. Later, perhaps: **a trail** - notes laid across the screen in the order they are
   played, so a fast line reads as a line of figures in time.

**Chosen (the owner, 10 Nov):** *One figure* stays the default, and the four to build
beside it are **Constellation**, **Clock**, **Pairs** and **Ripples**. Helix and Split
screen were sketched and not chosen. The trail stays a maybe.

**Restructured (the owner, 11 Nov):** looking at the mockup, the owner saw that Clock,
Pairs and Ripples are not modes beside Constellation but settings of it - Clock is a
constellation placed by pitch class on Scan's circle, Pairs one with a dyad for each
figure, Ripples one whose figures move - and agreed to build it that way. So there are
two ways to draw, and the second has three settings:

| Draw | Setting | Choices |
|---|---|---|
| **One figure** (today's, the default) | - | - |
| **Constellation** | **Figure** - what each figure is | *Note* (the figure it would draw alone) · *Pair* (the dyad two notes make, between their places) |
| | **Place** - where it lands | *Pitch* (pitch class round a clock face, octave as distance from the middle) · *Clock* (pitch class on Scan's circle, octave ignored) · *Seeded* (the scatter below) |
| | **Motion** - how it moves | *Still* · *Ripple* (each strike sends the figure outward; a held note sends one again) |

The settings are not cosmetic, because Scan reads the screen back as sound. Place decides
which notes are read at all: on Clock every note crosses Scan's circle, by Pitch a
middle-register chord can sit just clear of it. A ripple reaches the circle a moment
after the strike, so the note brightens late, like an echo in the timbre, and a held note
pulses. Pair draws the intervals rather than the notes - the only setting that shows the
harmony - and costs most: n notes make n(n-1)/2 figures, fifteen for six, so it needs a
limit (neighbouring notes only, or a cap). What the structure gains: fewer top-level
choices, and combinations four modes did not allow (Pairs on the Clock, seeded Ripples).
What it costs: the combinations multiply what parity and `honestytest.py` must cover.

## Where a note lands: Scatter

The owner asked whether placement could be truly random, against the repeatable
pseudo-randomness proposed first. The answer is both, as a choice, with the costs said:

| Scatter | How a note's place is chosen | Repeats? |
|---|---|---|
| **Fixed** | From the note itself: by pitch (pitch class round a clock face, octave as distance from the middle), or a scatter seeded by the note number | Always: a chord is a recognisable shape, and learnable |
| **Seeded** (the default) | Looks random, from a seed stored in the setup; *New seed* deals a fresh layout. In a host the seed can advance with the song position, so each pass differs but a bar always matches its own bounce | Yes, once saved: presets, bounces and undo are honest |
| **Free** | A new random place for every note, never stored | No - and its info line says so |

What Free costs, so it stays a choice and not the default:

- **A preset cannot promise its sound,** so `honestytest.py` cannot hold it to Settled or
  Breathing, and no bank preset uses Free.
- **In a DAW a bounce would not match playback** - a frozen or exported track would be a
  different performance from the one approved. Seeded with the song position fixes this
  for anyone who wants variety and a faithful bounce.
- **Comparing by ear stops being fair:** a knob turned and undone sounds different for a
  reason that is not the knob.
- **The loop's character is left to luck:** whether a note lands on Scan's circle decides
  whether it flares, so *settles while held* stops being a property of the sound. The
  existing limits still stop a runaway.
- **Parity still holds,** but only because Free is a seeded stream inside, as the noise
  shapes and the LFO's Random already are, with the seed taken fresh rather than stored.

## How it is to be built

1. A mockup on the design canvas (`https://claude.ai/artifact/C7EtMKWiMK6LXo4ZKRuyBz`):
   first the four modes side by side (10 Nov), then, after the owner's restructuring, one
   board per setting (11 Nov) - Draw on a sine, a triangle and a saw; Place on a triad and
   a run; Figure on a triad and six notes; Motion at three moments after a strike; and a
   split's two layouts. A gold dot marks where a figure crosses Scan's circle.
2. A page-only prototype behind a switch, to hear what Scan makes of a constellation
   before anything is ported. **Built 12 Nov** - *The prototype*, below.
3. Then the core, with parity; a voice budget for many small figures; and new honesty
   measurements for any preset that uses it.
4. In order: Constellation with *Note* and the three places first; *Pair* and *Ripple*
   once the first has been heard.

## Open

- Whether *Fixed* places by pitch (a clock face) or by a scatter seeded by the note - the
  mockup should show both.
- How the two hands of a split draw in constellation mode: one constellation each, or one
  shared.

## The prototype (step 2, built 12 Nov)

**Where:** Play, the Keyboard's *Draw* row, in Poly: the way - *one figure* (the default) or
*constellation (a prototype)* - on the label's line, and while the constellation is chosen
its *Place* (by pitch, clock, seeded), *Hands* (with two) and *Reseed* (when seeded) take the
line where the outline's two menus were (they keep their values, and still lean the heard
notes). Heard only on the page's own brain, **`?brain=js`**: on the site's default, the
instrument draws and reads its own screen in the core, which nothing the page draws reaches,
so choosing it there says so and links to `?brain=js&draw=constellation`; in the plugin it is
not offered. Not a setup field: not in a preset, a code, undo, the morph or a host's
parameters, not remembered by the browser; the address can ask for it (`?draw=constellation`).

**What it draws.** Each note the generator is playing (each hand's voice list) draws the
figure it would draw alone with the quarter turn - one cycle of the hand's shape against
itself a quarter-cycle late: a sine a ring, a triangle a diamond, a saw its own shape - at
its place, as large as it is loud: an envelope per note, run against the hand's own times,
times its velocity, times the hand's Level over Level's default. It grows on the attack,
shrinks with the release and goes when the release ends, as the voice does; Persistence
decides how long the light stays. Laid into the phosphor grid at the beam's full level, as
the one figure is with the Beam off. Drawn on the main thread from what the page knows, not
from the voice's samples: the page's brain runs its generator in a worklet, compiled unless
`?core=js`, and reaching for a voice's output would have been a change to the core. What
that costs: the filter, the drive, the crush and Scan itself do not reshape a note's figure.

**The lanes and the sound are untouched.** The generator still makes the one pair and is
heard as it was; only the screen draws the constellation instead of it. So while it is on,
what is heard is not what is drawn, except through Scan, which reads the constellation -
that is the experiment. The readouts, the tuner and the picture stage's reads go on reading
the lanes.

**Radii and sizes** (half-widths of the screen at zoom one; held sizes are at the default
Level and sustain, struck from the screen's keys):

| Place | Where | A figure, full / held |
|---|---|---|
| Clock | pitch class round a circle of 0.4, C at the top, clockwise; octave ignored | 0.58 / 0.32 |
| Pitch | the same clock face; octave 2 at 0.14, out 0.17 an octave to 0.82 at octave 6 (beyond: the end rings) | 0.09 / 0.05 |
| Seeded | a place per note dealt from the seed within 0.72 of the middle | 0.2 / 0.11 |

Scan's circle is not a fixed circle: it follows the picture's centre and spread and is read
off-centre, so "on Scan's circle" could not mean placed on it (placed there, the centre
would walk off by the offset every second). It means laid out so the circle Scan finds
crosses every note. The numbers were found by simulating Scan's follow and read on the
64-cell grid: on Clock, with a figure at 0.8 of the ring's radius (held), every
root-position triad, seventh and six-note chord tried has every note crossed; by Pitch, C,
E and G in octave 4 sit just clear of it, and every root-position triad there has a note
clear. Pitch's figures were 0.12 at first, and a chromatic run's figures, a quarter apart
on the middle ring, touched and lit four patches of light rather than twelve.

**Two hands, both prototyped:** *one each* lays each hand out by pitch class alone (Pitch on
its middle ring, Seeded by a seed of its own), so the lower hand's G3 and the upper's G5
land on one place; *shared* lays every note out by its place, octave and all. Each hand in
its figure's ink. It is one screen: both hands' Scan read it (the layer pictures, each
hand's own grid, belong to the picture stage and were left alone).

**Measured** (`web/tests/constellationtest.py`, on the page's brain, a C major triad at
velocity 100, Scan at 60, Strike off, after Scan's path had followed for 4.5 s):

| | Clock | Pitch |
|---|---|---|
| Notes Scan's circle crosses | 3 of 3 | 0 of 3 |
| Light Scan reads, mean round the circle | 0.135 | 0.013 |
| Light one figure gives the read, taken out | 0.027 to 0.070 | 0.0002 to 0.008 |
| The table's change with one figure taken out (mean, of a peak of one) | 0.33 to 0.51 | 0.008 to 0.25 |

So by Pitch Scan reads a tenth of the light, but the table changes nearly as much for two of
the three figures: Scan evens every table to a peak of one, so the faint light at the edge
of the blur is played as a shape as loud as a figure across the circle. Whether a chord
placed clear of the circle *sounds* quieter in the timbre, or only different, is for the
owner to hear; a darkness floor above the blur's tails would make "clear" mean clear.

A fast run (thirteen notes, C4 to C5, 70 ms each, Persistence at 0.02 a frame) leaves light
at the places of eleven of the thirteen notes half a second later, in twelve patches (C4
and C5 run together); the one figure leaves one smear at none of them.

Cost of a frame, drawing and laying into the grid (`drawMain` and the constellation, on this
machine, headless): one figure, six notes 0.20 ms, the constellation's six figures 0.08 ms;
one figure on two layers of eight 0.43 ms, sixteen figures 0.19 ms. A figure is 96 segments
against the one figure's beam of up to 6000 points, so many small figures cost less than one
large one here. The voice budget step 3 needs is the core's: its walk of the grid per
segment, and a sixteen-voice layered chord's tails.

**Left:** *Pair* and *Ripple* (step 4, once this has been heard); the core port with parity
(step 3), which would draw from each voice's own output and let the plugin and the site's
default play it; honesty (`honestytest.py`) for any preset that uses it; the Beam's
speed-shading, the Turn and zoom on the constellation (it is drawn in the screen's own
units, unturned); a darkness floor for Scan, if clear should mean silent; whether *Fixed*
places by pitch or by a scatter seeded by the note, and which of *one each* and *shared*
the owner wants.

## The prototype's shortcut, and what fixes it (the owner, 12 Nov)

Played on the site, every constellation looked still and alike whatever the sound. Part of
that is the idea: a steady note drawn alone repeats exactly each cycle, so its figure is
still, where One figure moves because its notes drift against each other. The rest is a
shortcut, and **the shortcut is the real problem**: on the site the voices run in the
compiled core in the worklet and their samples never reach the page, so the prototype draws
each note from a description - its pitch, its waveform's shape, its level and envelope -
and not from its sound. The filter, the FM's bark decaying, drive, unison and Scan itself
never reshape a figure, which breaks the rule that the picture is true to the sound.

**The fix, decided to wait until after stage 5** (the page's own engine retired): the core
sends the page one cycle of each sounding voice every frame (sixteen voices of about 256
samples, a few kilobytes), and each note's figure is drawn from its own real cycle. A tine's
figure then changes as its bark fades, a filtered pad's softens as the filter closes, and
Scan's effect on a note shows in its figure; a note moves when its sound moves and is still
only when its sound is. The painting's brush wants the same per-voice data, so it is built
once for both. Ripples and Pairs, which add motion and interaction between notes, come
after it.
