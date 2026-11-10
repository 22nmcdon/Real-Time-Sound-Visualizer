# Ways to draw

Agreed with the owner on 10 November, to build **after the redesign** (the second pass's
G6 and G7, and the silent start). Nothing here is built yet; this is what to build and why,
so the ideas are not lost.

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

1. A mockup on the design canvas: a held triad and a fast run, drawn as one figure and
   in each of the four chosen modes, with Constellation's places by pitch and by a
   seeded scatter, side by side.
2. A page-only prototype behind a switch, to hear what Scan makes of a constellation
   before anything is ported.
3. Then the core, with parity; a voice budget for many small figures; and new honesty
   measurements for any preset that uses it.

## Open

- Whether *Fixed* places by pitch (a clock face) or by a scatter seeded by the note - the
  mockup should show both.
- How the two hands of a split draw in constellation mode: one constellation each, or one
  shared.
