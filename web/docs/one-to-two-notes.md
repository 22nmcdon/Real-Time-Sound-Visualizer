# One note to two: what happens to the first note

The owner, 16 Nov, testing Harmonic tone: *"When going from playing one note to two, the
width and timbre of the notes change pretty dramatically. For example, playing a bass note
in the left, then playing a higher note in the right, then going back to just the bass note
causes the first note to dip in and out of the ears, it doesn't ever disappear fully, but its
width, dB, etc. changes instantly when another note is added."* And: *"I feel like it keeps
showing up and I don't think we've gotten it right so far."* The two fixes before it were the
release fading in one ear (the Key held its velocity, 12 Nov) and Poly's quarter turn going
the other way round from the dyad's (15 Nov).

This is an investigation, with takes for the ear on
[`listening/one-to-two/index.html`](listening/one-to-two/index.html). Nothing in the
instrument has changed: the options are compile-time switches in a scratch copy of
`core/include`, kept with the page's scripts in `listening/one-to-two/make/`.

## How it was measured

The owner's phrase through the core offline (`render_cpp`, 44.1 kHz): C2 alone from 0.2 s,
E4 added at 1.8 s and let go at 3.4 s, C2 alone again until 5.2 s, then its release.
Harmonic tone as the bank has it - `timebase 3`, the Picture at 96, its Swell on, and nothing
else, so it plays in **Dyad**, the mode's default - and the same in Poly (Quarter turn on), in
Mono, and in a split at G3. Each run is read against the same bass held alone through the same
six seconds, since Harmonic tone is a Breathing preset and its bass moves by itself.

What is read: each ear's level, side over mid and the correlation of the whole; and the
**bass's own image**, by lock-in on its harmonics in each ear (the first nine, leaving out the
fifth and its multiples, where the E's harmonics sit): its level in each ear, the phase of its
right ear against its left, and their coherence (0 is the quarter turn, the ring a note alone
draws, as wide as one note can be; 1 is the same in both ears, narrow and centred; -1 opposite).
With the picture off, the notes alone decide the image; with it on, the loop's readings (each
routing's depth) say what the picture does.

## What the instrument does to the first note

### 1. Dyad: the right channel stops being the bass, at the sample the key goes down

A dyad is two phases: the left at the lower note, the right at the interval's ratio over it.
A note alone is a unison, the right the same note a quarter turn on. When the E arrives the
interval becomes a major third two octaves up (ratio 5), and the right channel *is* the E: the
bass is gone from the right ear entirely (its right ear 56 dB under its left, which is the
lock-in's floor) at the sample of the key, since the ratio is not glided. The bass loses 3.0 dB
of its power and all of its width; the left ear does not move by a hundredth of a decibel.

### 2. Dyad: the bass comes back at whatever angle the release caught

The two phases run on through a change of interval (`making-it-one-instrument.md`, harmony
as geometry: *"The dyad is left as it was ... lining them up legato would click"*). While the E
is held the right runs at five times the left's rate, so their difference turns once every 3.8
ms (4 x 65.4 Hz). When the E is let go the right becomes the bass again from wherever that
difference stands. Sixteen releases a quarter of a millisecond apart bring the bass back with a
coherence of

    0.59 0.86 0.99 0.97 0.81 0.51 0.16 -0.25 -0.58 -0.86 -0.99 -0.97 -0.81 -0.52 -0.17 0.24

- every angle there is, from the same in both ears (a narrow, centred line) to opposite (wide
and hollow), and almost never the 0.00 it started at. It stays there until the bass is let go.
This is the *"doesn't come back the same"*, and it is the clearest fault of the four: nothing
about it is chosen.

### 3. Poly: the bass leans and loses its quarter turn

In Poly the lowest and highest held notes are drawn on X and Y and lean to their sides, full
on their own and half on the other (`roleGains`, P4); only a note alone, an inner voice or a
unison gets the quarter turn (`roundsRole`, P8h). So the bass goes from both ears at full, a
quarter apart (coherence 0.00), to its right ear 6.0 dB down and in step with its left
(coherence 1.00): narrower and to the left, 2.0 dB less power, in 4 ms (the roles' one-pole,
90 per cent in 9 ms). It comes back exactly as it started. The figure pays too: the pair draws a
smear along the diagonal, since the bass is in phase on both axes - the same diagonal P8h's
quarter turn was brought in to take away from a note alone.

### 4. The picture, and Scan where it is on: real, slower, and by design

The E doubles what is lit (the picture's cover 0.17 to 0.34), and Harmonic tone's loop (its
picture pushes Fold, Echo, Twist, Phase and the phaser) follows. So the bass's timbre does
wander from where it would have been: the centre of its harmonics, which breathes between about
1.2 and 7 by itself, is on average 0.9 to 1.1 away from the bass held alone, and its level 1.2
to 2.2 dB, in every version below alike. But not instantly: Fold moves 0.02 to 0.03 in the 100
ms after the E, where it moves 0.03 in any 100 ms of its own breathing, and Echo 0.04 to 0.08
against its own 0.19 to 0.24. That is Breathing doing what its heading says.

Harmonic tone has Scan off. On the bank's Poly presets it is on, and there it is a further
cause: on Tine piano the held bass gets up to 6.2 dB louder over the 0.4 s after the E (mean 4.2
dB over 1.2 s), because Scan reads the two-note figure into every voice; with Scan off the same
reads 0.0 dB, and with Strike off it still reads 6.3, so it is the read and not the strike. It
glides with the screen's persistence. It is the picture shaping the sound, so no option below
touches it, and none changes it much (2.0 to 2.2 dB on Tine piano in each).

### Ruled out

- **Level normalisation by voice count:** there is none; voices are summed at their own level
  (`sound`, `scope/voices.h`).
- **The envelope or a voice reborn:** nothing restarts. In Dyad the bass's left ear reads
  -11.22 dB alone, with the E and after it; in Poly the voice is kept by its note and never
  re-phased (a lock-in dip of up to 1.4 dB at the event is the 4 ms change of phase on the
  left inside a 30 ms window, not a change of level).
- **The limiter:** at most 0.06 dB of reduction while the two are held (0.3 dB in the split).
  The reading of 8.5 dB early in each run is its meter recovering from its starting state,
  which reads 14 dB before any note has sounded.
- **The picture's Twist swinging a narrow image between the ears:** a ring is the same at
  any turn and a line is not, so this was a good suspect for *"dips in and out"* after a Dyad
  return; measured, the balance between the ears moves by under 1.5 dB whichever way the bass
  came back (0.7 in phase, 0.6 opposite, 1.1 as a ring).
- **Mono** plays one note: the E replaces the bass while held and the bass returns after,
  by design, with its quarter turn as before.
- **A split** keeps each hand a figure of its own, so the bass stays a ring whatever the
  right hand does (coherence 0.00 throughout, no change in either ear). It is the one setting
  where today's instrument already does what the owner is asking for.

## Options

| | What changes | Bass, right ear against left (alone, with the E, again) | Coherence (alone, with, again) | Bass's power with the E | How fast |
|---|---|---|---|---|---|
| Dyad today | | 0.0, gone, 0.0 | 0.00, -, anywhere | -3.0 dB | one sample |
| **A** | Dyad's right put back in step when the interval changes, the old right crossfaded out over 30 ms | 0.0, gone, 0.0 | 0.00, -, 0.00 every time | -3.0 dB | 30 ms |
| **B** | A, and the dyad leans as Poly does: the bass's own quarter turn kept in the right at half, the upper note's own copy in the left at half | 0.0, -6.0, 0.0 | 0.00, 0.00, 0.00 | -2.0 dB | 30 ms |
| Poly today | | 0.0, -6.0, 0.0 | 0.00, 1.00, 0.00 | -2.0 dB | 4 ms |
| **C** | Poly's quarter turn kept on the outer notes too | 0.0, -6.0, 0.0 | 0.00, 0.00, 0.00 | -2.0 dB | 4 ms, gain only |
| **D** | No lean: every note on both sides with its own quarter turn | 0.0, 0.0, 0.0 | 0.00, 0.00, 0.00 | 0.0 dB | nothing changes |

All with the picture off; with it on, as the takes are, the picture's share is the same in each
(the centre of the bass's harmonics 0.9 to 1.1 from alone, its level 1.2 to 2.2 dB).

- **A** is a fix, not a choice: the bass comes back as the ring it left as, on all sixteen
  release moments (0.00 on each). A dyad reached two ways now draws one figure, which
  `making-it-one-instrument.md` left undone only because lining the phases up would click; the
  crossfade is what stops the click. The right channel's change of note is 30 ms of the two
  crossfaded at equal power instead of a step: on a held dyad changing its upper note that is
  a smooth change of note. Measured alone (no change of phase, the
  crossfade only), the step's sharpness goes but the return is as random as today (coherence
  0.59 on the take), so the crossfade without the re-phasing is not worth having.
- **B** keeps the bass in both ears in Dyad. It costs the Dyad's figure its purity: X is no
  longer the lower note alone and Y the upper, so the 1:5 figure is sheared, with loops at its
  sides. Mixed before the shaping in the prototype, so Fold acts on the two notes together in
  each ear; a build would mix after the shaping instead.
- **C** keeps the bass's width in Poly and only leans it. The pair then draws an open figure
  where today it draws the diagonal smear, which is a gain for the picture rather than a cost.
- **D** takes the change away altogether: a note's image never depends on what else is held.
  It costs the figure of two notes drawn against each other - the figure is the two notes'
  rings summed (the split's two hands drawn on one screen, in effect) - and it undoes P4's lean,
  so a chord's outer notes are no longer where the figure's axes are.
- Measured and not rendered: Poly's roles glided over 30 ms rather than 4. The bass still ends
  6.0 dB down and in step (coherence 0.99); the change only takes longer. A slower glide does
  not answer *"the width changes"*, only *"instantly"*, and the lean is what is heard.
- Not built: gliding Scan's table. It already glides with the screen's persistence (the Tine
  piano bass's rise takes 0.4 s), and holding it back further would make Scan's knob read
  something other than the screen.

## Recommendation

**A in any case; then B with C, unless the ear wants D.** A is the fault the owner heard as
*"doesn't come back the same"*. B and C make Dyad and Poly treat the first note alike: it stays
in both ears and keeps its width, leaning 6 dB to its side while another note is held. What the
owner would lose: with B, Dyad's figure as a pure X against Y; with B and C, nothing of the
bass's width, but it still leans. If a 6 dB lean still reads as the note moving, D is the one
with no change at all, at the cost of two notes drawn against each other.

What building it would take, for whoever does: A and B in `Generator::block`'s Dyad path
(`scope/generator.h`), on the oscillator's path (`oscStep`) as well as the plain wave's, which
is all the prototype covers; C as one line of `roundsRole` (`scope/voices.h`). Each means the
sound to change, so the golden recordings of any dyad changing its interval and any Poly pair
are rewritten with `--write-golden --because`; `core/tests/pieces/modes.py` grows a check that a
Dyad's lone note comes back with its right a quarter ahead after an interval (its null: today's
core, which fails on all but a chance release); `honestytest.py` re-measures every Poly preset,
since C changes the figure Scan reads; and the bank's thumbnails are drawn again
(`write_figures.py`). The controls' words (`what-each-control-says.md`) say what Quarter turn
does and would need a line for the outer notes.
