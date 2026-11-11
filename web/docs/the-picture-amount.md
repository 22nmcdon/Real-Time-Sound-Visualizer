# The Picture amount

A study, not a change (11 November). The owner, testing the site: *"I think we definitely
need to look into how the picture amount is actually calculated and functioning right now.
Because currently I don't see any good visual and audible use for it. Scan however does
seem good."* And then, having played it more: *"there are sometimes where it is very cool,
it just isn't consistent in how it feels when playing"*; on *Crossed hands*, with the
delay, phaser and reverb on, playing harder and faster makes the sound swell, louder and a
little harsher, *"which is really cool - but sometimes it does it for seemingly small
things"*; and, having made it repeatable, *"the initial flare is really cool and
interesting, it just needs to be consistent."* With the amount at nought the flare does
not happen at all.

This is what the Picture amount does, measured on the compiled core, why it feels the way
it does, and what could be done about it. Nothing in the instrument was changed to write
it. The test the recommendation is held to is the owner's: in their own sequence, the soft
notes at the end swell no more than the same soft notes played first from a fresh start,
while the first swell keeps its character.

## In short

- **The swell is the picture stage's Glow on the fold, and the inconsistency is a loop that
  oscillates by itself.** Each hand's picture moves its own sound. Glow is the hand's
  coverage against its own recent range; the fold makes the hand's figure larger, which
  raises its coverage, which holds Glow at the top of a range whose top follows a rise at
  once. So the left hand's held chord swells, saturates, collapses as the range catches up,
  and swells again every four to eight seconds. **In the owner's sequence the same swells
  come at the same moments with the soft notes left out** (section 2, *The owner's
  repeatable case*): the soft notes do not cause them, they land on them.
- **The relative rescaling sets how small a thing can tip it.** Once the loop has collapsed,
  the range closes on the reading at half a second until it is only its least span (0.1 of
  coverage) wide, and the loop's gain climbs with it: the narrower the range, the smaller
  the nudge that sends Glow to one. The same gesture reads as half a swing or a whole one
  according to what came in the seconds before.
- **Motion on the echo is a switch any note throws.** The picture's change is measured over
  the light present, so a faint note on a dark screen reads as much change as a loud one,
  and Motion's least span is 0.05. Every soft note of the owner's put the right hand's echo
  at its top. It carries none of the swell (+0.4 dB alone).
- **Not the causes:** the loop's runaway governor never engaged (the hold stayed at one; the
  meter never said *running away*), Memory alone moves the level by under a decibel, and the
  delay's feedback and the reverb's tail change nothing in kind (the same swells with the
  three effects off). Scan's crossed reading is the path a soft note reaches the left hand
  by, but at Picture 0 nothing swells.
- **Two things fix it in the owner's preset, both reading only the picture.** Let each hand's
  sound be moved by the *other* hand's picture, as *Crossed hands* already reads the other
  hand's for Scan (a menu that exists today), which breaks the self-loop; and read Glow
  against a range that adapts slowly and is never narrower than 0.4 of coverage. With
  Motion's echo route taken out as well, the fast run swells by +6.3 dB on average (+4.5 as
  it is) and is as harsh (5.4 per cent of its energy above 1 kHz, against 4.7 as it is and
  0.8 at Picture 0), and the soft notes swell by +0.1 dB in sequence against 0.0 from a
  fresh start (as it is, +2.6 and +2.6: the soft notes swell both times).
  **Recommended** (option 3 below), with the knob made to reach its top at 100.
- **Elsewhere the stage is loud and arbitrary, not weak.** At 60 it moves a held sound's
  spectrum by a median 0.18 (one note) to 0.34 (a phrase) on the honesty test's scale, as
  far as Scan does. Played 2.7 ms later, the same note at 60 comes out as different from
  itself as from the note with the stage off; at nought the two takes are identical. The
  knob is a switch: everything is clamped by 75, and the fold's threshold falls between 30
  and 60. And any heard amount makes every Settled preset measure as Breathing, while four
  of the five Breathing presets breathe without it.
- **Reading velocity or note density directly was considered and is ruled out** by the
  owner: *"that seems disingenuous to the goal of this synthesiser, having the image be the
  synth."* Every option below reads only the picture.

## How it was measured

The plugin's instrument (`scope::Instrument`, the core the site runs compiled) rendered
offline at 48 kHz, natively, through a copy of `core/tests/tools/instrument_cpp.cpp` that
writes the heard pair to a file, logs the picture stage once per 128-frame step (every
read, its hold, the meter's verdict and the five routes' held values) and saves the
phosphor every quarter second. The copy was built against a copy of `core/include` in
which `kStageBundles` is not `constexpr`, so one route at a time could be left on. Parity
holds the page and the core together to the bit, so these are the site's numbers too; the
page's frames come from the screen rather than the audio clock, which changes when a frame
lands and not what it computes.

Seventeen sounds: the nine presets of the bank, seven from the old library
(`core/tests/scenarios/library-p8f.json`: *Jazz organ*, *Warm pad*, *FM electric piano*,
*Perfect fifth, just*, *Supersaw*, *Scan breathes*, *Scan remembers*, with the Picture
amount added since none of them names it) and the base, the plain sine the instrument
opens on. Each played three ways: **one note** held for ten seconds (C4; a note a hand in
a split; a fifth for *Turning fifths*), **a chord** held for ten seconds (C3 G3 C4 E4; two
notes a hand in a split), and **a phrase** (C, F, G, A minor, 1.25 s each, twice). Each at
Picture 0, 30, 60 and 100, and again at 0 and 60 with Scan's depth at nought.

The measures:

- **Distance** is `honestytest.py`'s: 4096 samples, Hann-windowed, in forty-eight bands a
  fifth of an octave wide from 40 Hz, each band's share of the whole as an amplitude, so
  loudness drops out; the Euclidean distance between two renders at the same quarter
  second, averaged over the held window (1.0 to 10.5 s). On this scale the honesty test's
  Settled ceiling is 0.015 a quarter second, its Breathing floor 0.02, and a chorus at
  full moves a held note 0.4 to 0.6.
- **Movement** is the same distance between successive quarter seconds of one render:
  the honesty test's own measure of how much a held sound moves. *Late* is the last three
  seconds held.
- **Picture distance** is the picture meter's: the L1 distance between two grids over
  their summed light, nought for the same picture and one for two with nothing in common.

For the owner's cases the log also took each hand's coverage, change and the range each of
its reads is measured against, each hand's hold and verdict, Scan's depth, hold and path
for each hand, and the heard level in quarter seconds. The fixes in section 2 were tried
in the same way, each a copy of the core's headers changed in one place and nowhere else:
the stage's relax rate and least spans, Glow read absolutely (coverage over 0.35, rising
in 80 ms and falling in 600), and the routes' weights; the *Picture moves* menus are the
setup's own fields. None of it is in the repository, which has the method here and not the
scaffolding.

Every number is from the left channel unless it says mono, which matters for one route.
The null for every "it moves" below is the same sound at Picture 0 with Scan off, which
reads exactly 0.000 wherever the sound is a held tone with no modulation of its own (the
base, *Harmonic tone*, *Jazz organ*, the just fifth, *FM electric piano*).

---

## 1. What it does, exactly

### The chain

| Step | What | Constants | Rate |
|---|---|---|---|
| Phosphor | A 64×64 grid. Each cell keeps the brighter of what it held and what the beam lays on it, fading by the Persistence once a frame. Brightness goes as one over the beam's speed. | `PHOSPHOR_N` 64 | each frame, 60 a second (the core: of audio time) |
| Coverage | The mean of every cell capped at one, times four, capped at one: a quarter of the screen lit reads one | | each frame |
| Change | The L1 distance between this frame's grid and the last, over their summed light | `CHANGE_FLOOR` 0.02 | each frame |
| Novelty | The grid at a sixteenth (16×16) against every snapshot of the last fifteen seconds bar the last two; the distance to the nearest | `METER_EVERY` 0.25 s, `METER_DEPTH` 60, `METER_RECENT` 8, `NOVELTY_FLOOR` 0.2 | four times a second |
| Boredom | Rises at 0.25 a second while both the change over a quarter second and novelty are far under their floors; leaks at 0.2 a second | `BORED_RISE`, `BORED_LEAK` | each frame |
| Slew | Every value moves at most two of its range a second | `PHOTO_SLEW` 2 | each frame |
| **Glow** | Coverage against its own recent range: the top follows a rise at once and relaxes back at half a second, the bottom likewise; Glow is where coverage sits between them, over a span of at least 0.1 | `STAGE_RELAX` 0.5, `STAGE_MIN_SPAN.glow` 0.1 | each frame |
| **Motion** | Change against its own range, the same way, over at least 0.05 | `STAGE_MIN_SPAN.motion` 0.05 | each frame |
| **Memory** | The larger of boredom and *familiar*, which climbs at boredom's rate while raw novelty is under its floor and leaks at boredom's | | each frame |
| Hold | Falls at 0.5 a second to a floor of a quarter while the meter says *running away* (more than 0.35 of the screen lit, or the limiter past 6 dB), comes back at 0.1 a second. The core has no limiter to read, so only the light can trip it | `STAGE_HOLD_*` | each frame |
| Routes | Amount × weight, **clamped to the source's reach** (0.5 for Glow and Motion, 0.3 for Memory), summed with any other picture source on the control and clamped to `LOOP_TOTAL` 0.5 | `STAGE_BUNDLES`, `PHOTO_REACH`, `BORED_REACH` | rebuilt when the amount moves; read each 128-frame step |
| Destination | The held value, constant across each 128-frame step, through the destination's law | see below | per step, no further smoothing |

Page: `pictureStageStep`, `stageRescale`, `stageRoutings` and `stagePush` in
`web/scope.html` (around line 17300 to 17490); the meter is `makePictureMeter`, the engine
`makePictureEngine`. Core: `PictureStage` and `LayerPictures` in
`core/include/scope/picture.h`, `kStageBundles` and `Matrix::setStageAmount` in
`core/include/scope/matrix.h`, `StageSource` and `PictureRun` in
`core/include/scope/screen.h`. In a split whose hands draw a figure each, each hand has its
own grid, meter and stage, and each hand's sound hears its own picture (or the other's,
or both, by the Reads menus); Crossed hands hears the other's.

### The five routes, and where the knob stops mattering

| Route | Weight | Clamped by reach at | Destination's law | Most at Picture 100 |
|---|---|---|---|---|
| Glow → fold | 0.8 | 62.5 | fold travel + push × 0.5; the voice computes `sin(6π·f·x)` | +0.25 of the travel: a full-scale sine folded back about one and a half times |
| Motion → echo | 0.8 | 62.5 | delay mix + push × 0.5, the line running though its knob is at nought (375 ms, feedback 0.35 by default) | +0.25 mix: an echo 12 dB down |
| Memory → twist | 0.6 | 50 | twist + push × π radians per unit of radius | 0.3π: the figure's rim turned 54° against its centre |
| Memory → phase | 0.4 | 75 | right channel's phase + push × π | 54° on the right channel |
| Memory → phaser | 0.5 | 60 | phaser mix + push × 0.5, mixed as `x·(1−m/2) + wet·m/2` | +0.15 mix: 7.5 per cent wet |

So from 62.5 up the fold and the echo cannot be pushed further, and from 75 nothing can.
Measured: on *Harmonic tone*, *Slow pad* and the just fifth, Picture 80, 90 and 100 give the
same sound to three decimals of every measure (the routes' held values are identical), and
70 differs from them only in the phase route. The fold has a threshold of its own at the
other end: below a twelfth of its travel it is a gentle saturation, normalised back to full
level, and above it a fold. At Picture 30 the fold's push only passes that when Glow is
above 0.69; at 60, above 0.35. That is why the measured effect jumps between 30 and 60
and is flat above 70 (section 2).

### What each destination does to the sound and to the picture

In X–Y the drawing is the signal, so every one of the five changes both.

- **The fold** adds harmonics, many of them: the centroid of a plain sine chord at 60 swings
  between 200 Hz and 600 Hz. On the screen the figure's edges fold back into petals. This
  is the route a listener hears as the stage.
- **The echo** adds a copy of the sound from 375 ms ago. On a held tone that is the same
  pitch, so it changes only each partial's amplitude and phase, which the spectrum barely
  sees (0.03 to 0.05 alone on a note) and the picture sees as a slight thickening; on a
  phrase it is the last chord's ghost on the screen and in the ear. Driven by Motion, its
  level steps by a median 0.05 to 0.09 of its travel from one frame to the next (section
  2), which is heard as a flutter on the repeats rather than as an echo coming and going.
- **The phase** turns the right channel against the left: a line opens into an ellipse, a
  ring narrows. It does nothing to the left channel's spectrum (0.000 alone) and is heard
  only as width, or in mono, as a change of level and colour (0.14 to 0.15 alone, mono).
- **The twist** turns each point by an angle in proportion to its distance from the centre:
  the figure swirls, and since it mixes the channels non-linearly it adds distortion. It
  does turn the figure; on a centred circle Scan cannot hear the turn, only the swirl.
- **The phaser**, at the most 7.5 per cent wet, opens a line slightly and notches the
  spectrum slightly.

### Feedback

Every route is feedback: each destination changes the drawing it is read from.

- The fold makes the figure larger and more tangled, so it lights more of the screen, so
  Glow rises, so the fold rises. The rescaling breaks the loop: Glow's range opens to the
  new coverage at once and closes back at half a second, so Glow falls even if the
  coverage stays up. What comes out is a relaxation oscillation: on a held plain-sine chord
  at 60 the tone is bright for four seconds, dark for three, bright again (the centroid
  590, 590, 300, 199, 190, 199, 591, 608 Hz at 0.75, 3.25, 4.75, 5.25, 6.75, 8.25, 9.25, 9.75 s).
  On *Drawbar organ* chords it lights the screen past the meter's 0.35, and the hold
  engages, the only run of the 204 where it did.
- The echo puts the last 375 ms on the screen, which changes the picture, which is Motion.
  After the keys come up, the echo's own fading tail is still read as motion and keeps the
  echo's level moving (0.15 to 0.25 for three seconds after a chord, at 60 to 90 dB
  down).
- Memory's routes are the designed negative feedback: they move a repeating picture
  somewhere new, which raises novelty, which drains Memory.

### Two smaller things on the way

- The routes are rebuilt whenever the amount moves (`stageRoutings` on the page,
  `Matrix::setStageAmount` in the core, recompiled on the audio thread), and a route's
  value reaches its destination as a step once a 128-frame step with no smoothing. That
  is the wheel's crackle, being fixed separately; it also means the echo and fold steps
  measured below reach the sound unsmoothed in normal playing, not only under the wheel.
- The info line says *"its memory turns it"* and the cheat sheet that Memory *"twists the
  figure"*. On a chord, Memory's push is a median 0.04 of a span at 60 (twist, phaser) and
  0.03 (phase): it barely runs, because a chord's figure precesses and never comes back
  close enough for novelty to fall under its floor.

---

## 2. What it does in practice

### How far it moves the sound

The distance from the same performance at Picture 0, the movement late in the hold at each
amount, and Scan's own size: the distance between Scan as the preset has it and Scan at
nought, both with the stage at nought. One note held:

| Sound | 30 | 60 | 100 | moves at 0 | at 60 | at 100 | Scan's size | brightness at 60 |
|---|---|---|---|---|---|---|---|---|
| *Tine piano* (Settled) | 0.031 | 0.072 | 0.060 | 0.002 | 0.067 | 0.058 | 0.163 | −12% |
| *Tines at the radius* (Settled) | 0.023 | 0.040 | 0.046 | 0.002 | 0.044 | 0.053 | 0.038 | −4% |
| *Drawbar organ* (Settled) | 0.041 | 0.333 | 0.380 | 0.004 | 0.225 | 0.271 | 0.058 | +29% |
| *Bass under the tine piano* (Settled) | 0.041 | 0.281 | 0.356 | 0.035 | 0.207 | 0.218 | 0.156 | +37% |
| *Harmonic tone* (Breathing, 60) | 0.071 | 0.178 | 0.239 | 0.000 | 0.207 | 0.101 | none | +31% |
| *Slow pad* (Breathing, 100) | 0.081 | 0.152 | 0.155 | 0.035 | 0.086 | 0.059 | 0.197 | −4% |
| *Turning fifths* (Breathing, 30) | 0.101 | 0.140 | 0.150 | 0.111 | 0.126 | 0.150 | 0.261 | −3% |
| *Bass under the pad* (Breathing, 80) | 0.130 | 0.180 | 0.201 | 0.025 | 0.081 | 0.095 | 0.134 | +11% |
| *Crossed hands* (Breathing, 60) | 0.479 | 0.654 | 0.689 | 0.066 | 0.325 | 0.394 | 0.915 | +13% |
| *Jazz organ* | 0.064 | 0.330 | 0.371 | 0.001 | 0.350 | 0.203 | none | +31% |
| *Warm pad* | 0.019 | 0.034 | 0.036 | 0.247 | 0.262 | 0.264 | none | −1% |
| *FM electric piano* | 0.022 | 0.053 | 0.060 | 0.000 | 0.056 | 0.064 | none | 0% |
| *Perfect fifth, just* | 0.017 | 0.040 | 0.046 | 0.000 | 0.023 | 0.024 | none | 0% |
| *Supersaw* | 0.027 | 0.049 | 0.049 | 0.522 | 0.530 | 0.531 | none | −1% |
| *Scan breathes* | 0.321 | 0.391 | 0.511 | 0.102 | 0.390 | 0.280 | 0.376 | +41% |
| *Scan remembers* | 0.402 | 0.602 | 0.649 | 0.175 | 0.035 | 0.202 | 0.685 | +40% |
| The base | 0.024 | 0.274 | 0.352 | 0.000 | 0.046 | 0.215 | none | +33% |

Medians across the seventeen:

| Played as | distance at 30 | 60 | 100 | 100 below 60 | Scan's size (ten sounds with Scan) |
|---|---|---|---|---|---|
| One note | 0.041 | 0.178 | 0.201 | 1 of 17 | 0.180 |
| A chord | 0.081 | 0.295 | 0.281 | 5 of 17 | 0.194 |
| A phrase | 0.109 | 0.341 | 0.365 | 2 of 17 | 0.213 |

The level moves less than the colour: at 60 the held level rises by a median 0.7 dB on a
note and 2.2 dB on a chord (as much as 6.2 dB on *Turning fifths* chords), and the
brightness (the spectral centroid) by tens of per cent where the fold engages, as much as
+108 per cent on the base's chord. The picture moves more than the sound: at 60 the grid is
a median 0.43 from its unstaged twin on one note (0.14 to 0.70), against Scan's 0.68 where
Scan is used.

So **the stage is audible on most sounds, at 60 and above.** The exceptions are telling:
on *Warm pad*, *Supersaw* and *FM electric piano* a note moves 0.03 to 0.06, under the
sound's own movement (a chorused, detuned pad already moves 0.25 to 0.52 a quarter second),
and on the just fifth the sound moves 0.04 while its picture moves 0.61: the echo on a
steady interval changes the figure and leaves the spectrum almost where it was.

### The amount's curve

On one note held, each amount from nought to a hundred in tens, the distance from Picture 0:

| Picture | 0 | 10 | 20 | 30 | 40 | 50 | 60 | 70 | 80 | 90 | 100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| *Harmonic tone* | 0 | 0.015 | 0.039 | 0.071 | 0.083 | 0.110 | 0.178 | 0.227 | 0.239 | 0.239 | 0.239 |
| *Slow pad* | 0 | 0.048 | 0.086 | 0.081 | 0.055 | 0.093 | 0.152 | 0.155 | 0.155 | 0.155 | 0.155 |
| *Perfect fifth, just* | 0 | 0.004 | 0.009 | 0.017 | 0.023 | 0.031 | 0.040 | 0.042 | 0.046 | 0.046 | 0.046 |

The top quarter of the knob is dead, and on *Slow pad* (which ships at 100) the middle is
not monotonic: 40 moves it less than 20.

### Which route does the work

Each route alone at its weight for Picture 60, the others at nought, as distance from 0
(left channel / mono):

| Sound, played as | all five | Glow → fold | Motion → echo | Memory → twist | → phase | → phaser |
|---|---|---|---|---|---|---|
| *Harmonic tone*, note | 0.178 / 0.195 | 0.109 / 0.109 | 0.049 | 0.017 | 0.000 / 0.139 | 0.010 |
| *Harmonic tone*, chord | 0.161 / 0.204 | 0.202 | 0.050 | 0.089 | 0.000 | 0.009 |
| *Slow pad*, chord | 0.295 | 0.269 | 0.103 | 0.070 | 0.050 | 0.053 |
| *Turning fifths*, chord | 0.346 | 0.334 | 0.167 | 0.085 | 0.079 | 0.080 |
| *Jazz organ*, chord | 0.593 | 0.774 | 0.053 | 0.067 | 0.000 | 0.015 |
| *Warm pad*, chord | 0.353 | 0.271 | 0.061 | 0.021 | 0.007 | 0.011 |
| *Crossed hands*, note | 0.654 | 0.438 | 0.559 | 0.571 | 0.336 | 0.521 |
| *Perfect fifth, just*, note | 0.040 / 0.089 | 0.004 | 0.029 | 0.010 / 0.032 | 0.000 | 0.000 |

**The fold carries the timbre**: alone it is most of the whole on every chord, and more
than the whole on *Jazz organ*, where the other routes' changes to the picture keep Glow
lower. The echo is second. The phase route is invisible in either channel's spectrum and
appears only in mono. Memory's routes matter only on *Crossed hands*, where each hand's
sound is read from the other's picture, so any change to either figure is heard at once
through Scan. The movement a held note keeps is not any one route's: on *Harmonic tone*'s
note all five together move it 0.207 late, and no route alone more than 0.034.

### The reads over a held chord

At Picture 0, the stage still computes its reads (nothing hears them), so they show what
the stage would act on with nothing acting back. On the base's chord, a sound whose
spectrum does not move at all (its centroid 200 Hz at every quarter second, its level
within 0.4 dB):

| Time (s) | 0.75 | 2.25 | 4.25 | 5.25 | 6.75 | 8.25 | 9.75 |
|---|---|---|---|---|---|---|---|
| coverage | 0.053 | 0.174 | 0.244 | 0.209 | 0.234 | 0.233 | 0.218 |
| Glow | 0.46 | 1.00 | 0.89 | 0.28 | 0.32 | 0.42 | 0.06 |
| change | 0.217 | 0.253 | 0.251 | 0.251 | 0.213 | 0.266 | 0.230 |
| Motion | 0.93 | 0.74 | 0.65 | 0.49 | 0.00 | 0.76 | 0.14 |
| novelty | 1.00 | 1.00 | 0.61 | 0.57 | 0.45 | 0.47 | 0.31 |
| Memory | 0 | 0 | 0 | 0 | 0 | 0.006 | 0.030 |

Three things show.

- **Glow is the onset, then the wobble.** Coverage climbs for four seconds as persistence
  fills the chord's figure in; Glow follows the climb to one, and then, the range closing
  on the reading at half a second, falls back. After that coverage moves between 0.21 and
  0.24, under Glow's least span of 0.1, so Glow is that 0.03 wobble scaled by ten, plus
  whatever is left of the onset. On one note of *Harmonic tone*, Glow's range of readings
  is 0.004 wide (5th to 95th percentile) and Glow still spends a fifth of the time at one.
- **Motion is the chord's precession, not anything played.** A chord's X–Y figure is not
  periodic within a frame, so the grid changes by 0.21 to 0.27 every frame however still
  the sound is: twelve times `CHANGE_FLOOR`. Motion is that, against its own range, and
  swings across its whole travel: its median rate of change is 80 full ranges a second on
  a chord, 54 on a note.
- **Memory never starts on a chord.** Novelty stays above its floor of 0.2 for the whole
  hold, because the precessing figure is never close to where it was fifteen seconds
  before. Memory reaches 0.03 by ten seconds. On one held note in X–Y it climbs steadily
  (to 0.4 or 0.5 by ten seconds), so the twist, phase and phaser are a slow ramp on a
  note and nothing on a chord.

And they do not saturate in the sense of sticking: Glow sits at its top 0 to 25 per cent of
the time and at its floor 20 to 50 per cent, Motion jitters across the middle. What they do
is move without the sound giving them a reason.

### Does the rescaling make it act on noise

Two measurements say yes.

**Still sounds, read.** *Jazz organ* is drawn in Y–T with the persistence off, as most of
the old library was. Its sound does not move (0.001 a quarter second at Picture 0), and
its coverage, read every tenth of a second, dithers between 0.512 and 0.533 as the trace
lands on slightly different cells from frame to frame. Glow turns that 0.02 into swings
between 0.3 and 1.0; change dithers between 0.000 and 0.109, and Motion goes nought, 0.4,
one, nought, a cycle every three frames or so. At Picture 60 this is the sound: the echo's
level is stepped by a median 0.09 of a span every frame, and the fold flares (0.350 late
movement against 0.001).

**The same note, a little later.** One note held, then the same note one 128-frame step
(2.7 ms) later, and two steps later, aligned and compared:

| Sound | Picture 0: one step | two steps | Picture 60: one step | two steps | the stage's own size at 60 |
|---|---|---|---|---|---|
| *Harmonic tone* | 0.000 | 0.000 | 0.183 | 0.232 | 0.178 |
| The base | 0.000 | 0.000 | 0.098 | 0.140 | 0.274 |
| *Perfect fifth, just* | 0.000 | 0.000 | 0.390 | 0.036 | 0.040 |
| *Tine piano* | 0.004 | 0.007 | 0.047 | 0.039 | 0.072 |
| *Slow pad* | 0.052 | 0.065 | 0.187 | 0.124 | 0.152 |
| *Warm pad* | 0.002 | 0.005 | 0.015 | 0.018 | 0.034 |

At nought a note played 2.7 ms later is the same sound (Scan's presets differ a little,
since where the strike lands depends on it). At 60 it is **as different from itself as it
is from the note with the stage off**: on *Harmonic tone* 0.18 to 0.23 against 0.18; on the
just fifth one take flared the fold and the other did not, 0.39 against a stage that
otherwise moves it 0.04. Motion's reading in the two takes differs by 0.26 to 0.31 on
average at either amount, as much as it varies at all: two takes of one note give two
uncorrelated Motions. That is the definition of reading noise.

### The owner's scenario: Crossed hands, with the effects on

The owner, having played it more: *"there are sometimes where it is very cool, it just
isn't consistent in how it feels when playing. My go-to preset is Crossed hands, then I add
reverb, phaser and delay. When I hold a chord in my left hand and play quiet short notes,
then transition to pressing a little harder and playing faster, the sound level etc. all
flares in response, which is really cool - but sometimes it does it for seemingly small
things."*

The hypothesis to test, not assume: after a stretch of quiet or steady playing the
rescaling's range has shrunk, so a small change reads as full scale, and the same gesture
reads differently according to what came before it.

Rendered as played: *Crossed hands* (split at C4, each hand's Scan reading the other's
picture, each hand's picture moving its own sound) at Picture 60, with the delay, phaser
and reverb at their switches' mixes (35, 30 and 15). The left hand holds C2 G2 C3 from
0.5 s. The right hand plays short notes (150 ms) at velocity 35 every 1.5 s from 4 to 16
s; then at velocity 110 every quarter second, 120 ms each, from 16 to 26 s; then soft and
sparse again to 35.5 s. Logged every 2.7 ms: each hand's coverage, change and the range
each read is measured against, the three reads and the five routes' depths for each
hand. Separately, one note at 22 s, soft (velocity 30) or hard (110), either after 21.5 s
of the left-hand chord alone or after busy playing (velocity 110 every quarter second)
that stops two seconds before it.

**Phase by phase**, at Picture 60 (the routes' mean depth, as a share of the most a route
can push, which is 0.48 at 60):

| Right hand | fold, left hand's sound | fold, right hand's | echo, left | echo, right | the stage's distance from Picture 0 |
|---|---|---|---|---|---|
| Soft and sparse | 0.20 | 0.01 | 0.06 | 0.05 | 0.261 |
| Hard and dense | 0.23 | 0.23 | 0.07 | 0.08 | 0.394 |
| Soft and sparse again | 0.23 | 0.01 | 0.06 | 0.04 | 0.360 |

The flare the owner likes is there, and it is one route: **the right hand's fold**,
driven by the right hand's Glow, goes from 0.01 to 0.23 and back as the playing goes from
soft and sparse to hard and dense and back. Glow does this because the right hand's
screen is nearly dark between soft notes, so its range has collapsed to nothing and Glow
is the coverage over its least span of 0.1: in effect an absolute reading of how much is
lit, which goes up with how hard and how often the keys are struck. The left hand's fold
does not follow the playing at all (0.20, 0.23, 0.23): its Glow reads the left hand's own
picture, which changes because its Scan reads the right hand's, and sits wherever its own
range has wandered to.

**Note by note**, each soft note in the sparse stretches:

- The right hand's coverage goes from 0.005 to 0.009 (a hundredth of the screen), its
  change from about nought to 0.05, and **its Motion to 0.86 to 1.00 on every one, so the
  right hand's echo goes to its top, 0.48, on every soft note**. The meter's change is the
  distance between two frames over their summed light, so a faint stroke on a dark screen
  is as much change as a bright one: on one note after a steady hold, change rose to 0.046
  for a soft note and 0.064 for a hard one. Motion's least span is 0.05. Together they make
  the echo a switch that any note at all throws fully.
- The **first** soft notes after the hard stretch were read against the range the hard
  stretch had opened: at 26 and 27.5 s Motion rose by −0.06 and +0.44 and the echo by
  −0.03 and +0.21. By 29 s the range had closed again (its top relaxing at half a second)
  and every soft note threw the echo to 0.48 once more. The same gesture read as half a
  swing or a full one according to what came three seconds before it: **the hypothesis
  holds**.
- The left hand's reads answered each soft note by anything from −0.13 to +0.24 (Glow) and
  +0.16 to +0.56 (Motion), its fold by −0.06 to +0.11 and its echo by +0.07 to +0.27, with
  no relation to the note, since what changed was the left hand's own picture through its
  Scan, read against a range that had wandered.

**One note after a steady hold, and after busy playing.** The distance between the
spectrum just before the note and half a second after it:

| One note at 22 s | Picture 0 | Picture 60 |
|---|---|---|
| Soft, after 21.5 s of the chord alone | 0.156 | **0.640** |
| Hard, after 21.5 s of the chord alone | 0.374 | 0.678 |
| Soft, after busy playing | 0.203 | 0.287 |
| Hard, after busy playing | 0.471 | 0.648 |

Without the stage the sound tells a soft note from a hard one (0.156 against 0.374, after
a steady hold). With it, it hardly does (0.640 against 0.678), and the soft note's effect
depends on what came before more than on how it was played (0.640 after stillness, 0.287
after busy playing). Before the note, after the steady hold, the left hand's Glow read
against a range 0.11 wide and the right hand's against one of width nought; after busy
playing, 0.14 and 0.33. That is "it does it for seemingly small things", measured: a small
thing after stillness gets the stage's whole reaction.

The effects at their switch-on mixes feed the picture too (the delay's repeats, the
phaser's sweep and the reverb's tail are drawn, and the delay is also where Motion's route
lands), but they do not change the picture of this: with the three switched off the phase
table and the note-by-note behaviour come out the same in kind (the right hand's fold
0.01, 0.26, 0.01; every sparse soft note throwing the right hand's echo to its top).

### The owner's repeatable case

The owner made the over-reaction repeatable, with this setup code:

`eyJ2IjoxMCwic2hhcGUiOiJzaW5lIiwib3NjU2NhbiI6MTAwLCJzY2FuUmVhZHNBIjoiQiIsInNjYW5SZWFkc0IiOiJBIiwiZnJlcSI6MTEwLCJjeWNsZXMiOiIiLCJkaXNwbGF5IjoieHkiLCJwZXJzaXN0ZW5jZSI6IjAuMDI1NSIsIm1pZGlNb2RlIjoicG9seSIsInBvbHlSb3VuZCI6dHJ1ZSwibGF5ZXJzIjoic3BsaXQiLCJwaWN0dXJlQW1vdW50Ijo0NywiZGVsYXlNaXgiOjM1LCJkZWxheUZlZWRiYWNrIjo0NywicGhhc2VyTWl4IjozMCwicmV2ZXJiTWl4IjoyNn0`

which is *Crossed hands* at Picture 47 with the delay at 35 (feedback 47), the phaser at 30
and the reverb at 26, split at C4. Their sequence, rendered in time through the core
(events at their own moments, a 128-frame step at a time, every read, range, hold, verdict,
Scan's depth and hold and path, and the five routes logged at every step):

| Time (s) | What is played |
|---|---|
| 0.5 | The left hand holds D♭2 A♭2 C3 |
| 2 to 4 | The right hand runs up and down D♭ major pentatonic with C (D♭4 to F5), five notes a second, velocity 55 |
| 4 to 9 | Faster and harder: eight a second, velocity 95 |
| 6.5 | The left hand changes to G♭2 D♭3 F3, the right hand still running |
| 9 | The right hand stops; the chord is held |
| 15 | Soft (velocity 40): a B♭4 grace note into C5 |
| 16.8 | A G♭4 grace note into A♭4, held to 20 s |
| 21.5, 22.5 | A soft F4; a soft D♭5 held to 25 s |
| 27 | The chord let go |

And a control the owner asked for: the same soft notes **from a fresh start**, the second
chord struck at 0.5 s and held, the soft notes from 6.5 s on the same spacing.

**The trace.** The left hand's sound, every half second around the soft notes, at Picture
47 (*A* is the left hand's picture and sound; the level is the heard pair, both hands):

| Time (s) | 13.0 | 14.0 | 14.5 | 14.75 | 15.0 | 15.5 | 16.0 | 16.5 | 17.0 | 18.0 | 19.0 | 20.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Level (dB) | −18.0 | −16.8 | −16.1 | −14.8 | −10.6 | −11.1 | −10.0 | −9.6 | −9.9 | −9.9 | −14.4 | −15.0 |
| Level at Picture 0 | −16.2 | −14.4 | −14.9 | −15.1 | −14.9 | −16.0 | −16.8 | −15.4 | −14.2 | −14.9 | −16.0 | −14.7 |
| A's coverage | 0.316 | 0.258 | 0.264 | 0.307 | 0.523 | 0.582 | 0.624 | 0.874 | 1.000 | 0.962 | 0.811 | 0.485 |
| A's range | 0.32–0.55 | 0.25–0.44 | 0.25–0.40 | 0.25–0.38 | 0.27–0.52 | 0.34–0.59 | 0.39–0.62 | 0.47–0.87 | 0.58–1.00 | 0.74–0.99 | 0.81–0.96 | 0.49–0.82 |
| A's Glow | 0.00 | 0.04 | 0.10 | 0.41 | 1.00 | 0.97 | 1.00 | 1.00 | 1.00 | 0.88 | 0.00 | 0.00 |
| A's fold push | 0.00 | 0.02 | 0.04 | 0.15 | 0.38 | 0.37 | 0.38 | 0.38 | 0.38 | 0.33 | 0.00 | 0.00 |
| The right hand's coverage | 0.007 | 0.005 | 0.004 | 0.004 | 0.009 | 0.016 | 0.024 | 0.015 | 0.039 | 0.024 | 0.019 | 0.025 |

The swell begins at 14.5 s, half a second *before* the first soft note, and the right
hand's picture never lights more than four hundredths of the screen during it. What drives
it is the left hand's own loop: the fold enlarges the chord's figure, the coverage rises,
the top of Glow's range rises with it at once, so Glow is pinned at one and the fold at its
top, until the coverage saturates (one, a quarter of the screen lit) and the range's
bottom, relaxing upwards at half a second, overtakes it at 19 s. Then Glow is nought, the
fold lets go, the figure shrinks and the coverage falls, and the range closes on it again.
At Picture 0 the left hand's coverage stays between 0.27 and 0.42 through all of this.

**Without the soft notes.** The same sequence with the soft notes left out, at Picture 47:
the left hand's Glow passes 0.9 at 9.5, 10.9, 14.8, 17.7 and 23.4 s, against 9.5, 10.9,
14.8, 17.7 and 23.2 s with them, and the level a second apart from 9.5 to 26.5 s reads
−11 −10 −11 −17 −17 −16 −11 −10 −10 −10 −15 −14 −15 −16 −10 −10 −12 −14 dB, against −11 −10
−11 −17 −17 −16 −11 −10 −10 −10 −15 −14 −15 −16 −10 −11 −12 −15 with them. **The swells
need no notes.** The left hand's loop is a relaxation oscillator with a period of four to
eight seconds; the soft notes land on its swells and are heard as their cause. (In the
owner's own session the notes may also have nudged when a swell came; the render cannot
say, and it does not need to: a loop that swells by itself will be heard as answering
whatever was played just before.)

**The causes asked about, one by one:**

| Suspected cause | What the log says |
|---|---|
| The range relaxed, so a small change reads as full scale | **Yes, as the loop's gain.** Before each swell the range has closed to near its least span (0.25–0.40 at 14.5 s, 0.15 wide), where a rise of 0.04 in coverage is 0.4 of Glow. It is what lets the loop tip, with or without a note |
| The runaway rein engaged in the first swell and has since let go | **No.** Both hands' holds stayed at 1.00 for the whole sequence and neither meter's verdict was ever *running away* (wandering, cycling and settled only): coverage was capped at one with at most a quarter of the screen lit, under the 0.35 the verdict needs, and the core has no limiter to read. Scan's hold stayed at one |
| The familiar and boredom integrator left high | **High, but not the cause.** The left hand's Memory climbed to 0.76; Memory's three routes alone move the level by −0.5 to +0.2 dB |
| The crossed reading makes the loop's gain depend on the left chord's figure | **It is the path, not the swell.** The right hand's notes reach the left hand's sound through its Scan, but at Picture 0 the left hand's coverage barely moves (0.371 to 0.374 across the first soft note) and nothing swells |
| The delay's feedback and the reverb's tail keep Motion alive | **No.** With all three effects off the soft notes swell by +2.8 dB in sequence against +2.3 from a fresh start, as with them on (+2.6 and +2.6) |

**Route by route.** The stage's swell, the heard level against the same performance at
Picture 0, as a mean over each stretch (and its most), each route alone at its weight:

| | The fast run (4–9 s) | After it (9–14.5 s) | Soft notes, in sequence | The same, from a fresh start |
|---|---|---|---|---|
| All five, as it is | +4.5 dB (+7.1) | +2.1 (+6.1) | **+2.6 (+6.7)** | **+2.6 (+5.9)** |
| Glow on the fold alone | +4.0 (+6.7) | +2.3 (+6.0) | +3.0 (+6.6) | +2.7 (+6.0) |
| Motion on the echo alone | +0.4 (+1.3) | 0.0 (+0.2) | +0.1 (+0.9) | +0.1 (+0.9) |
| Memory's three alone | +0.2 (+0.9) | −0.4 (+0.1) | −0.5 (+0.5) | −0.3 (+0.5) |

The swell is Glow on the fold, entirely. And by the owner's test as it stands, the soft
notes swell no more in sequence than from a fresh start (+2.6 both times), because they do
not cause the swell in either: the left hand's loop swells from a fresh start too, about
four seconds after the chord's own first swell has collapsed. So the test has to be read
with its other half: **the soft notes should not swell at all** next to a fast run that
does.

**Which notes jump out.** Each note of the scale in two octaves, alone, soft, over the second
chord, three seconds apart. With the stage at nought, Scan alone, a note changes the left
hand's tone by 0.17 (B♭4) to 0.35 (D♭4) in the spectrum. At 47, the left hand's fold went to
its top on F4, G♭4, B♭4, C5, E♭5 and A♭5 and stayed under 0.05 on D♭4, E♭4, A♭4, D♭5, F5 and
C6 (B♭5 between, at 0.16): not a pattern of register or of chord tones, but of where in its four-to-eight-second
cycle the left hand's loop was when each note arrived. What makes notes differ under Scan
alone is not where they fall on the reading circle either: the circle follows the figure it
reads (its centre the light's centre, its radius the light's spread, following at a second),
and a soft right-hand note draws a ring whose radius is two or three hundredths of the screen's width, so
every note is read round its own rim. Chord tones jumping out of a solo, which the owner
finds an interesting idea, would want the circle fixed while the notes land in different
places on it: the *Clock* placement of `ways-to-draw.md`, where each note's figure sits on
Scan's circle by pitch class.

**Fixes tried, each on the owner's sequence and the fresh start** (the stage's swell in dB,
mean and most; how much of the fast run's energy lies above 1 kHz, as a measure of the
harshness the owner likes, is 4.7 per cent as it is and 0.8 at Picture 0):

| Variant | Fast run | After it | Soft, in sequence | Soft, fresh | Passes |
|---|---|---|---|---|---|
| As it is | +4.5 (+7.1) | +2.1 (+6.1) | +2.6 (+6.7) | +2.6 (+5.9) | No: soft notes swell |
| Today's code, each hand's picture moving the *other* hand's sound (the Reads menus, no code) | +3.4 (+7.3) | −0.3 (+0.5) | +0.5 (+3.2) | −0.1 (+1.2) | Nearly: the self-loop is gone, but a soft note in sequence still reaches +3.2 against +1.2 fresh: the relative range still lets what came before in |
| Glow read slowly (its range relaxing at a twentieth a second, not a half) and never narrower than 0.4 of coverage (0.3 for Motion) | +6.7 (+7.7) | +0.3 (+5.4) | +4.0 (+5.8) | +4.5 (+6.9) | No: consistent, but the self-loop still swells on its own |
| Glow absolute (coverage over 0.35), quick up, slow down, no Motion | +6.5 (+7.5) | +5.2 (+6.1) | +4.8 (+6.8) | +5.0 (+7.0) | No: always swollen; the chord alone fills the scale |
| Glow absolute, crossed | +6.7 (+8.1) | +1.1 (+5.3) | +0.8 (+2.5) | +0.5 (+1.9) | Nearly |
| **Slow and wide, crossed, no Motion** | **+6.3 (+7.9)** | **−0.6 (+4.7)** | **+0.1 (+1.6)** | **0.0 (+1.7)** | **Yes**, and the fast run is as harsh: 5.4 per cent above 1 kHz |
| Slow and wide, crossed, Motion kept | +6.4 (+7.6) | −0.7 (+4.8) | +0.1 (+1.4) | −0.1 (+2.1) | Yes |

Crossing breaks the self-loop: the left hand's sound is moved by the right hand's
picture, whose coverage goes from four thousandths with soft notes to one in the fast run,
so it reads how hard and how much the right hand is playing; and the right hand's sound by
the left chord's picture, which it does not draw. There is still a loop (each picture
reaches the other hand's sound through Scan), but it runs through both hands and has not
been seen to tip. The slow, wide range then keeps a soft note after a fast run from being
read against a range that has just closed. On the plain sounds of the bank, the slow, wide
range alone also makes the stage much less sensitive to a note played 2.7 ms later
(*Harmonic tone* 0.18 to 0.08, the base's chord 0.17 to 0.09, the just fifth 0.39 to 0.01,
*Jazz organ* 0.18 to 0.04, *Drawbar organ* 0.26 to 0.01); it does not stop a held Settled
note breathing at 60 (*Tine piano* moves 0.039 late).

### Scan beside it

Scan's size on the ten sounds that use it is a median 0.18 to 0.21, the stage's at 60
0.18 to 0.34, so in raw size they are alike. They differ in what the size is made of:

- **Scan's change follows the playing.** The strike flares the timbre where the note lands
  on the reading circle and fades with the Persistence: on the Settled presets, 0.04 to
  0.07 a quarter second early in the note and nought by the end (*The headings without
  it*, below). Two takes of one note at Picture 0 differ by 0.000 to 0.065. What it reads is
  drawn as the ring over the screen.
- **The stage's change follows its own clock.** The onset and the half-second relaxation
  of its ranges, and the meter's jitter. Two takes differ by as much as the effect.

Where both run, the stage adds little movement Scan had not already given. *Turning fifths*
moves 0.111 late on one fifth at Picture 0, by Scan reading the figure turn at the beat
rate, and 0.113 at its own 30. *Slow pad* moves 0.036 at 0 and 0.057 at its own 100.

### The headings without it

`honestytest.py`'s probes and rules (Settled: early at least 0.008, late at most 0.015 and
at most half the early; Breathing: late at least 0.02 and silent after), run on the core at
Picture 0, at each preset's own amount, and at 60:

| Preset | Heading | Picture 0 | its own | 60 |
|---|---|---|---|---|
| *Tine piano* | Settled | Settled (late 0.000) | | Breathing (late 0.053) |
| *Tines at the radius* | Settled | Settled (0.002) | | Breathing (0.044) |
| *Drawbar organ* | Settled | Settled (0.004) | | Breathing (0.221) |
| *Bass under the tine piano*, low hand | Settled | Settled (0.010) | | Breathing (0.128) |
| *Bass under the tine piano*, high hand | Settled | Settled (0.001) | | Breathing (0.050) |
| *Harmonic tone* | Breathing | **neither (0.000: still)** | Breathing (0.135) | |
| *Slow pad* | Breathing | Breathing (0.036) | Breathing (0.057, at 100) | Breathing (0.066) |
| *Turning fifths* | Breathing | Breathing (0.118) | Breathing (0.113, at 30) | Breathing (0.123) |
| *Bass under the pad*, low hand | Breathing | Breathing (0.020, on the line) | Breathing (0.077, at 80) | Breathing (0.057) |
| *Bass under the pad*, high hand | Breathing | Breathing (0.036) | Breathing (0.069, at 80) | Breathing (0.046) |
| *Crossed hands* | Breathing | Breathing (0.070) | Breathing (0.429, at 60) | |

(The probe here starts at 0.9 s and the windows are honestytest's; the sample rate is 48 kHz
rather than the page's 44.1, which changes the window's length by a tenth and nothing
else that matters. *Harmonic tone* at Picture 0 reading exactly nought is this table's
null: the rule can fail.)

So **Breathing does not need the stage**: Scan with Strike and Persistence, a figure that
turns (the narrow fifth), or each hand reading the other makes all of it but *Harmonic
tone*, which is the only Breathing preset with no Scan. And **the stage does not respect
Settled**: any amount that is heard turns every Settled preset into Breathing. Its own
comment says why: the reads are rescaled to their own range, so a held picture keeps them
stirring. That makes the amount a switch between the headings, not a control within one.

---

## 3. Why it feels inconsistent

The owner's words are the right frame: the flare is good, and it is not consistent. In
order of how much of the inconsistency each explains:

1. **A sound moved by its own picture through Glow and the fold is an oscillator.** The
   fold enlarges the figure, the larger figure raises the coverage, and Glow's range top
   follows a rise at once, so Glow stays pinned at one while the coverage climbs; when it
   stops climbing, the range bottom (relaxing upwards at half a second) overtakes it, Glow
   falls to nought, the fold lets go and the figure collapses. On the owner's left-hand chord
   this repeats every four to eight seconds with nothing played (*The owner's repeatable
   case*); on the base's plain sine chord at 60 the brightness cycles 590, 300, 190, 600 Hz
   over eight seconds (*Feedback*, section 1). Whatever is played just before a swell is
   heard as its cause.
2. **The relative rescaling is what lets it tip, and lets history in.** After a collapse the
   range closes on the reading until it is only its least span wide, and there a coverage
   rise of a few hundredths reads as half of Glow. So the loop's gain depends on how long it
   has been since the last swell, and the same soft note is read against a range a fast run
   opened (half a swing) or one that has closed again (a whole one) according to the three
   seconds before it.
3. **Motion is scale-free, so any note throws the echo.** The picture's change is measured
   over the light there is, so a stroke a hundredth of the screen in size on a dark screen
   reads as much change as a loud one, and Motion's least span (0.05) is the size of that
   change. On every soft note of the owner's first scenario the right hand's echo went to its
   top. It adds a flutter, not the swell.
4. **On sounds that are not split, the reads act on the meter's noise.** Motion follows the
   frame-to-frame jitter of the trace (a still Y–T tone) or a chord's precession (any chord
   in X–Y), and Glow multiplies a coverage wobble of 0.02 by ten. Two takes of one note 2.7
   ms apart differ as much as the stage is large.
5. **The knob is a switch with a dead top.** Clamped by reach above 62.5 and 75, with the
   fold's threshold between 30 and 60, it does little below 30, almost all between 30 and
   60, and nothing above 75.
6. **It is the fold.** Glow on the fold carries the timbre and all of the owner's swell; the
   echo carries the flutter; Memory's three routes, which the info line and the cheat sheet
   lead with (*"its memory turns it"*), barely run on a chord and move the level by under a
   decibel.
7. **It erases the bank's distinction.** At any amount that is heard, every Settled preset
   breathes; and four of the five Breathing presets breathe without it.
8. **What the face shows does not help.** The meters show Glow and Motion against their own
   recent range, so they swing on a still sound too, and on many notes the picture *"just
   looks like a jumbled mess"* (the owner), so the coverage the fold follows is not
   something the player can see rising.
9. **It is unsmoothed at the destination.** The echo's level steps by a median 0.05 to 0.09
   of its travel at each picture frame; the fold by up to 0.08. And the amount, moved by the
   wheel, rebuilds the routes: the crackle, being fixed separately.

**On a constellation.** `ways-to-draw.md`'s constellation draws each note as its own figure,
as large as it is loud, so a fast run scatters rings rather than tangling one figure. That
would make a hand's coverage a much better measure of how much and how hard it is playing:
roughly the sum of its notes' sizes, rather than whatever a tangle of incommensurate
frequencies happens to light. It is the read the recommended fix depends on, so it would
help it. It would not fix the inconsistency by itself: the self-loop (the fold enlarges
every ring as it enlarges one figure) and the relative ranges are the same on any drawing,
and Motion would still measure change over the light present. And *Clock* placement, which
puts each note's figure on Scan's circle by pitch class, is what would make some notes jump
out of a solo by where they land, which the owner liked the thought of.

---

## 4. Options

Every option reads only the picture. **Rejected: reading the playing directly** (velocity
and note density from the keys, which would give the most exact *harder and faster*):
the owner, *"that seems disingenuous to the goal of this synthesiser, having the image be
the synth."*

### Option 1: cut it, and let Scan be the one way the picture reaches the sound

**What it sounds and looks like.** A held chord on a sound with Scan moves as the strikes
light the ring and fade; a sound without Scan is a plain synthesiser. Four Breathing
presets keep breathing by Scan; *Harmonic tone* becomes still. **The flare the owner likes
goes with it**: at Picture 0 nothing swells, measured and by the owner's own diagnostic.

**The knob.** The `picture` host knob (in the plugin's `kKnobs`), the expression pedal
(CC 11) and the wheel's and pressure's *Picture amount* would become Scan's depth, so saved
automation still means "how much the picture plays the sound", as the rule in
`making-it-one-instrument.md` requires.

**What it costs.** Mostly deletion, on both sides: `STAGE_*` and the stage's step, routes,
sources and meters on the page; `PictureStage`, the stage half of `LayerPictures`,
`StageSource`, `kStageBundles` and `setStageAmount` in the core (the meter's verdict stays,
since it reins Scan in); a version-11 decode pass that drops `pictureAmount` and
`bPictureAmount`; `stagetest.py` rewritten round Scan, `looptest.py` run with Scan at its top,
`?picture=0` gone from thirty suites and `unstaged` from the shell test, parity's staged runs
gone; *Harmonic tone* given Scan or let go. The headings keep their meaning, made by Scan,
Strike and Persistence.

**Weighed.** It was this study's recommendation before the owner's second and third reports.
It is still the cheapest way to an instrument with no arbitrary behaviour, and Scan is
measurably the more legible path. But it removes the one thing the owner has found *"really
cool"* about the stage, which option 3 keeps.

### Option 2: keep it, and set *Crossed hands* to cross its stage too

**What it sounds and looks like.** No code: on *Crossed hands*, each hand's *Picture moves*
menu set to the other hand, as its Scan reads the other hand's picture. The left hand's chord
swells with the right hand's playing and no longer by itself. Measured: the fast run +3.4 dB
(up to +7.3), nothing after it (−0.3), the soft notes +0.5 (up to +3.2) in sequence against
−0.1 (up to +1.2) fresh.

**What it costs.** One preset's two fields, the preset's thumbnail and its honesty probe
(`write_presets.py`, `write_figures.py`, `honestytest.py`).

**What it does not fix.** It nearly passes the owner's test and does not: a soft note soon
after a fast run is still read against a range that is closing, and peaks at +3.2 dB against
+1.2 from a fresh start. Every unsplit sound keeps the self-loop, the noise and the switch-like
knob. A stopgap worth trying by ear today.

### Option 3: fix how the picture is read (recommended)

**What it sounds and looks like.** The swell the owner likes, from how much a hand's picture
is lit, the same for the same playing whatever came before. Four changes, page and core
alike:

1. **A sound's stage reads a picture its own push does not draw.** In a split whose hands draw
   a figure each, each hand's sound is moved by the other hand's picture by default (the
   *Picture moves* menus' cross, which exists), as *Crossed hands* already crosses Scan. This
   breaks the self-loop, which is the main cause. On a split whose Scan is not crossed (the
   bank's two others) it means the bass swells with the right hand's playing and the right
   hand with the bass's figure, which is a choice to hear before it is a default; it was
   measured only on *Crossed hands*.
2. **Glow is read against a range that adapts slowly and is never narrow.** The range's ends
   relax at a twentieth a second rather than a half (twenty seconds rather than two), and the
   least span is 0.4 of coverage rather than 0.1 (0.3 rather than 0.05 for Motion, if it is
   kept). A fast run opens it and a quiet minute closes it; a soft note is read against what
   the hand has been doing over the last half minute, not the last two seconds. Rising at
   once is kept, so the first swell still answers the first fast run.
3. **Motion's echo route goes,** or Motion is measured as change in light rather than change
   over the light present (not built here). With the route kept or taken out, the owner's
   case came out the same; it carried none of the swell and all of the flutter.
4. **The routes reach their tops at 100** (each weight at most its source's reach), and the
   push is smoothed at the destination over a few tens of milliseconds, so the knob is graded
   and the fold does not step sixty times a second.

Measured on the owner's sequence with 1 to 3 (4 changes the knob's curve and the steps, not
the swell's shape): the fast run +6.3 dB on average (up to +7.9), as harsh as it is now (5.4
per cent of its energy above 1 kHz against 4.7, and 0.8 at Picture 0); nothing after it
(−0.6); the soft notes **+0.1 dB in sequence against 0.0 from a fresh start**, up to +1.6
against +1.7. It passes the owner's test both ways: the soft notes swell no more in sequence
than fresh, and do not swell beside a fast run that does.

**For a sound that is not split** there is one picture and one sound, so step 1 cannot apply,
and with step 2 alone the left-hand loop still swelled by itself (+4.0 dB in sequence, +4.5
fresh: consistent, but swelling with nothing played). An unsplit sound needs its stage's read
held under unit gain against its own push: Glow on a scale fixed wide enough that the fold
cannot raise the coverage it reads by more than it was pushed by, or the fold's own
enlargement of the figure discounted from the coverage before it is read. Neither was built
for this study; both are reads of the picture, and both should be measured by the same test
(a held chord with nothing played must not swell) before the defaults change. Until then
the default for an unsplit sound can stay where it is, and the bank's Settled presets at
nought.

**What it costs.** Page and core: two constants, a default for the *Picture moves* menus in a
split, the bundles and their weights, a one-pole on the stage's pushes; parity's staged runs
recorded again; `stagetest.py` and `looptest.py` run at the new values; and a new check in
the spirit of the owner's: a scripted split sequence, fast run then soft notes, against the
same soft notes from a fresh start, failing if the second differs from the first by more than
a decibel, with its null (today's constants) seen to fail. The host knob keeps its id and its
meaning. *Harmonic tone* and the unsplit Breathing presets re-chosen by ear; `honestytest.py`
re-run, where the Settled presets stay at nought because any heard amount still makes them
breathe.

**For the headings.** Unchanged in meaning: Settled is still at Picture nought; Breathing is
still the loop at work, which for a split now includes a stage the other hand drives.

### Option 4: redesign it as one visible gesture the player starts

**What it sounds and looks like.** One read and one destination, each of which can be seen:
how long the held picture has stayed put, absolute and reset by a new note, winding the
figure's twist, which Scan hears because the twist changes where the rim crosses its circle.
Hold a chord and the figure winds; strike a note and it unwinds.

**What it costs.** Glow and Motion and their rescaling go; Memory rewritten as a clock with a
reset; presets, parity and `stagetest.py` redone.

**Weighed.** It is legible and consistent by construction, and it is not the flare the owner
likes, which is louder and harsher as they play harder: the twist is a slow winding, not a
swell. It could sit beside option 3 later, as the stage's second read, once option 3 has been
heard.

### Recommendation

**Option 3**, starting with steps 1 and 2 on splits, where the owner plays and where they
were measured to pass, and trying option 2 by ear today as its cheapest part.

The owner's goal is the first swell, consistently. The measurements say what the swell is (a
hand's Glow on the fold), what makes it inconsistent (a sound moved by its own picture through
a range that closes in two seconds is an oscillator, and any note lands on one of its swells),
and that reading the other hand's picture against a slow, wide range keeps the swell (+6.3 dB,
as harsh as now) and removes the over-reaction (the soft notes +0.1 dB in sequence, 0.0 from a
fresh start). Cutting the stage would remove the over-reaction too, and the swell with it.

## What this did not measure

- **Listening.** Every number here is a spectrum, a level or a grid. Whether the recommended
  swell sounds as good as today's first one is the owner's to hear; the harshness measure
  (energy above 1 kHz) says it is as bright, not that it is as good.
- **The page in a browser, with real MIDI.** The core was rendered offline with timed events,
  where the picture frame is sixty a second of audio time. The page's frames follow the
  screen, which only adds timing jitter to what the reads see.
- **The owner's own tempo and touch.** The sequence was reconstructed from their description;
  the swells' timing in their session will differ, and the loop's own period of four to eight
  seconds is why the notes and the swells seemed to line up.
- **The sustain pedal**, which the owner has not got.
- **Option 3 on unsplit sounds**, beyond the slow, wide range alone, and option 4 at all.
- **The effect build's input,** and most of the old library: seven of its 268 presets.
