# Making it one instrument

A plan, not built. It comes before any new feature, because every stage since the
layout revamp has added to an instrument that no longer says what it is.

## The goal

In the owner's words: *"Right now I never feel like I should use this synth, and that is
the main issue with it. I want it to be something cool and interesting that sounds good,
looks good, and isn't impossible to use, so I can use it properly."*

And, earlier: *a sound visualizer that alters and plays its sound based on the picture,
with the picture affecting the sound always, not as a setting that is allowed.*

So the measure of success is not a feature list. It is whether it gets reached for. Three
tests, each one checkable:

1. **It works in the first minute.** Open it, hold a chord: within ten seconds you hear
   and see the picture changing the sound, having touched nothing else.
2. **It sounds good and looks good by default.** The first sound and the first picture,
   and every preset, are ones you would keep, not demonstrations of a mechanism.
3. **It is not impossible to use.** What is on show is what you play. Nothing has to be
   routed by hand before the instrument does its one thing.

## Decisions

| Decision | Where it stands |
|---|---|
| The plugin is the product; the site is its interface and a free demo | **Taken** |
| The desktop build (`oscilloscope-poc/`) is retired | **Taken** |
| What the instrument *is* | **Proposed** below: the sound is made from what the screen remembers |
| Where the sound comes from: its oscillator, the track it sits on, or both | **Largely answered** by the proposal: both are *ink* (see Question 1) |
| What "the picture always affects the sound" means | **Proposed:** the picture *steers* the sound, by reading back the phosphor; the picture-is-the-sound rule is kept, as coherence rather than identity (see Question 2) |

---

## Why nobody reaches for it

### It is three instruments sharing a screen

- **A synth.** Fourteen waveforms, drawbars, a morph, a wavetable and a drawn cycle; a
  second oscillator with FM, ring, sync, sub and unison; drive, fold and crush; a filter
  in every note; poly voices, splits and layers, an arpeggiator, a voice budget. Two of the
  six Bench tabs, Shape and Effects, are a synth's panel.
- **An image generator.** A harmonograph, thirteen figures (text, SVG paths and your own
  drawing among them), wireframe solids, a second generator. One preset menu says it
  outright: *"Nothing you play changes these."*
- **A visualizer with some crossover.** The scope, the spectrogram, racks of stems, a band
  split; and the parts where the picture reaches the sound: the photocell, the picture
  meter, the score, crossings, the plane's operations.

### The crossover is optional at every step

- **The generator is silent until asked.** *Hear the generator* is off by default
  (`genSound: false`).
- **The picture's sources need a switch.** The Picture family reads *"Turn on the
  Photocell, above the screen."*
- **Some sounds are heard and never drawn.** The core's block is
  `block(outL, outR, n, heardL, heardR)`: a picture pair and a heard pair. Poly notes the
  draw rule leaves out, the score's voice and the crossings' plucks are heard only.
- **Picture to sound is routed by hand.** 45 destinations, seven source families, and
  `state.modRoutings` starts empty. By default the picture affects nothing.

### And when it is switched on, it does almost nothing

Measured on the page, the photocell on, each picture source read for four seconds across
nine presets:

| Preset | What moved |
|---|---|
| Default tone, *Harmonic tone*, *Square wave* | Nothing structural. Coverage stuck at 0.42 (0.33 for the square); roundness and signed area exactly constant. The photocell read **0 to 0.025**. |
| *Pulse-width sweep*, *Morphing shape* | Coverage 0.20–0.34; roundness and signed area moved. |
| The picture-loop presets | The photocell swung fully (0.03–0.99 in *The knot leans into the light*), because those presets park it on the figure. |
| All nine | `edge` read **0.000** every time. |

Four causes, and they compound:

1. **The reach is set for proving safety, not for being heard.** A new picture route
   starts at 20% of its control (`PHOTO_START = 0.2`, "enough to see, no more"), can never
   pass 50% (`PHOTO_REACH`), and every picture route on one control together is capped at
   50% (`LOOP_TOTAL`). These were set while the loop was being shown stable; `looptest.py`
   now proves it at those limits, and they stayed there.
2. **A still picture gives constants.** The picture's readings measure how the picture
   *changes*, and the default picture does not change. Routing a constant moves a knob
   once and leaves it. (Rescaling each reading to its recent range, the obvious fix, has
   nothing to stretch on a still picture, and on a nearly still one turns jitter into full
   swings. It needs a minimum span, and helps only where something moves.)
3. **The photocell is switched on in the dark.** It reads one spot (five samples within
   a cell of a point), and its default spot, three-quarters across the screen, is off the
   default figure. Switched on, it reads about 0.02.
4. **One reading is dead by design.** `edge` is how much of the figure touches the edge
   of the screen, and the code notes it sits at nought for most pictures.

The lesson under all four is the one scanned synthesis learned in 1999: a frozen shape
read as sound goes dull within seconds. **An always-on picture stage over a still picture
is an always-on constant.** Something has to keep the picture moving: the playing, a
drift, the figure's own motion.

---

## What the instrument is

> **The sound is made from what the screen remembers.**

The first version of this plan proposed *every sound it makes passes through the picture*,
and with it a rule that the picture *is* the sound: nothing heard that is not drawn. That
rule is worth keeping, but it is not an identity. In X–Y the drawing already *is* the
signal, so turning or folding it is a stereo effect with a picture attached, and an effect
on an incoming track is the same. The picture only *does* something to the sound when the
screen holds something the signal does not, and that is read back.

The screen holds exactly that: **the phosphor.** A 64×64 grid of light that keeps the
brighter of what it held and what the beam lays on, fading by the persistence each frame,
with the beam's brightness going as one over its speed. It is a memory of many cycles,
where slow parts glow and fast parts barely mark it. The signal has none of that.

So the instrument reads the phosphor back, at three rates, which is what unifies the
crossover features that are already built:

| Rate | Reading | What it does | Built? |
|---|---|---|---|
| **Audio** (every sample) | **Scan:** brightness along a closed path, as the waveform, pitched by the held note | Sets the timbre | No: the new spine (below) |
| **Control** (each frame) | **The picture stage:** a few readings of the phosphor | Moves the sound's controls | The readings exist; the stage does not |
| **Tempo** (each step) | **The score:** a playhead across the grid's columns | Plays notes | Yes |

Everything else is **ink**: what the beam draws with, which lays light on the phosphor.
The oscillator and its shapes, sync and fold, your drawing, a line input, a track the
plugin sits on. Ink is played; the phosphor remembers; the readings make the sound.

> **The loop sentence:** you play → the beam draws → the phosphor remembers → it is read
> back → you hear it → the beam draws.

A feature stays if it acts on one of those arrows, and moves to a drawer or goes if it
does not.

### Question 1, answered by ink

The first version asked whether this is an instrument, an effect, or both, and set out
each side. With the phosphor as the instrument, the question mostly dissolves: the
oscillator and an incoming track are two kinds of ink, and everything after the beam is
the same. The instrument plays from the keyboard; a line input, or the host's input bus,
is another ink to draw with.

What remains open is only packaging. A music program treats instruments and effects
differently, so "the track as ink" may need its own build later. It is not a reason to
keep two products inside one panel.

### Question 2, answered

The picture **steers** the sound, by being read back. The picture-is-the-sound rule is
kept as **coherence**: nothing is heard that is not drawn (so every poly note is drawn,
the score's voice and the crossings' plucks with it, and *Hear the generator* goes because
the instrument is always heard). It stops being presented as the reason the instrument
exists.

---

## The picture stage

The control-rate reading, made structural: fixed, always on, and visible. It replaces
routing the picture by hand.

- **Three reads, each driving a bundle of controls**, instead of seven sources to route.
  Chosen for moving, not for existing:
  - **Motion** (how much the picture changed since the last frame)
  - **Memory** (novelty and boredom: whether it is repeating itself, and for how long)
  - **Glow** (coverage, which moves whenever anything morphs or sweeps)

  The controls each one drives are chosen *after* the cuts below, so no bundle points at
  something that is about to go. `edge` is dropped; signed area probably too.
- **One amount**, *Picture*, ideally on the Nord's expression pedal, and at most one knob
  per read. On by default, at a level where the effect is obvious rather than just
  visible.
- **Stronger defaults, re-proved.** The reach and the per-control total rise until the
  effect is plainly heard, and `looptest.py` is re-run at the new limits. The slew, the
  per-control total and the limiter-last stay; the classifier's *running away* can pull
  the amount down, so it governs as well as reports.
- **A minimum span on any rescaling**, so a still picture stays still rather than its
  jitter being amplified.
- **Seen working.** The three reads as meters beside the screen, and each control
  highlighted while the picture is moving it.
- **A ring instead of a point.** The photocell becomes a ring dropped *on the figure*,
  centred on it when switched on so it never reads darkness, and the reads come from inside
  it. The same ring is the path Scan reads along later, so the photocell and Scan are one
  control.
- **The routing matrix moves to an Advanced drawer**, for LFOs and controllers. The
  picture no longer depends on it, and the default view loses its biggest piece of clutter
  without the engine losing anything.

## Scan

The audio-rate reading: the instrument's spine, and the part no other instrument has.

Each frame, the phosphor's brightness is read along a closed path into a single-cycle
table, played at the held note's pitch. Pitch comes only from the read rate, as in
scanned synthesis, so the picture can never put you out of tune; the timbre is whatever
the screen remembers. Scanned synthesis (Verplank, Mathews and Shaw, 1998–2000) is the
precedent; wave terrain synthesis, with a time-varying terrain, is its two-dimensional
cousin.

What is already in place, so Scan is not starting from nothing:

- **The phosphor already runs in the C++ core, on the audio clock.** Since stage 4d the
  plugin lays its own grid and steps the picture's sources at sixty frames a second of
  audio time, with its window closed (`Phosphor` in `core/include/scope/picture.h`). Scan
  lives beside it in the core and needs no transport between threads.
- **Band-limited tables by octave** exist for the drawn cycle and the wavetable.
- **The loop's safety layer** exists: the slew, `LOOP_TOTAL`, the limiter last, the
  classifier.
- **The grid cannot run away by itself.** Each cell keeps the brighter of its faded value
  and the new stroke, so no cell passes full brightness. Runaway can only come through
  loudness and coverage, which the existing defences watch.

What has to be solved first, and the reason Scan begins as an experiment:

- **A raw scan will sound spiky.** The phosphor is mostly dark with thin lit lines. A
  circle crosses a figure at a few points, so the raw table is a handful of narrow spikes:
  buzzy, and normalising makes it louder rather than rounder. It needs a **softness**
  control (the grid blurred before it is read), or a path along the figure itself.
- **A circle cannot hear rotation.** With the path centred on the figure, turning the
  picture only rotates where the read starts, which is a phase you cannot hear. Scaling,
  shearing and folding would be heard; rotation needs an off-centre or non-circular path.
  (The same blind spot CLAUDE.md warns about for test fixtures.)
- **It must neither collapse nor run away.** Normalise inside the loop, keep a floor of
  the ink oscillator so the pitch never vanishes, freeze the table across preset changes,
  count Scan's depth inside `LOOP_TOTAL`, and slew the table's harmonics rather than its
  samples so the timbre glides.
- **Persistence becomes the Memory knob**, in seconds: a short half-life tracks the
  current cycle (near the signal, so near boring), a long one makes the timbre remember the
  phrase.

The experiment: scan the real grid offline across the presets with a few paths and
softness settings, render the tables as sound, and listen. If no setting sounds good, Scan
does not go in, and the picture stage carries the identity alone.

---

## What goes

### Whatever is decided

- **The desktop build.** `oscilloscope-poc/` is deleted (it stays in history), with its
  tests and the parts of `designtest.py`, `DESIGN.md`, `CLAUDE.md` and the README that
  hold it in step. `docs/z-axis-lane.md` moves into `web/docs/` as an idea for the plugin,
  or goes.
- **The stem rack.** Up to six lanes from files, the rack's generator and live lanes,
  alignment for playing along. In a music program the host plays files and each track is
  its own instance.
- **Recording a clip.** The host records. Kept only if the demo needs a way to share.
- **File playback** shrinks to one demo file on the site, or goes.
- **`edge`**, the dead reading.

### By the loop sentence

| Area | What is in it | Verdict |
|---|---|---|
| The screen | Y–T and X–Y, Lag X–Y, trigger, timebase, persistence, phosphor, cursors, the picture filter | **Keep:** the instrument's body. Persistence becomes Memory |
| The phosphor's readings | Photocell, picture meter, shape measures, Boredom, the loop | **Keep, and promote** to the picture stage; the classifier becomes a governor |
| Score | A playhead across the grid, rows as scale degrees, out as MIDI | **Keep:** the phosphor read at tempo |
| Crossings, thresholds, Pluck | Notes from the figure's geometry, not from the phosphor | **Cut**, or fold what is good into the score |
| Waveforms | Fourteen shapes, drawbars, morph, wavetable, drawn cycle, noises | **Reframe as ink.** Fewer on show; morph as the one knob; drawbars stay for the Nord |
| The voice | Second oscillator (FM, ring, sync, sub, unison), drive, fold, crush, voice filter, the budget | **Ink modifiers.** Sync and fold up front (the strongest change to the picture); the rest trimmed hard or in a fold-out. Unison is why the budget exists |
| The plane | Nine X–Y operations, rotation, layer B's plane, delay and chorus on the pair | **Keep, as Space:** transforms of the picture change what the phosphor holds, so with Scan they change the sound twice |
| Figures | Harmonograph, thirteen figures, text, SVG, your drawing, solids, a second generator | **Keep what draws while you play.** Generators that ignore the keyboard are the image-generator product: cut or drawer. Your drawing becomes drawing onto the phosphor |
| Grab, drawn cycle | A cycle from the input's audio; a cycle drawn by hand | **Keep as ink tools.** (Grab reads audio, not the picture; it is not a scan) |
| Playing | MIDI in, on-screen keys, poly, mono, the dyad, pedal, learned controllers | **Keep.** Scan starts mono or dyad: one phosphor, a read rate per voice |
| Splits, layers, arpeggiator, macros | Multi-timbral and hands-free performance | **Drawer, or cut** if unused |
| Time and key | Key and scale, quantiser, clock, MIDI clock | **Keep only what the score needs** |
| Modulation matrix | LFOs, seven families, fades, morphing between setups | **Advanced drawer.** Picture sources leave it for the stage |
| Input sources | Mic or line in, file, rack, band split, input into the generator | **A line in stays, as ink.** The rack goes; the band split goes unless it earns a place |
| Spectrogram, measurements | THD, harmonics, readouts | **Drawer.** They also verify Scan's band-limiting |
| Presets | 31 sections in three menus | **Rebuilt** by what the loop does (below) |
| Root README | Still says "two implementations", "MIDI when that lands", band-limiting "not built" | **Rewritten** around the loop sentence |

## Using it

What makes it possible to use is mostly what is on show, not what exists.

- **Four tabs, along the loop**, instead of six by task:
  1. **Play:** the keyboard, voices, envelope, filter.
  2. **Ink:** morph, sync, fold, the oscillator, the figures. *What the beam draws with.*
  3. **Space and Memory:** the plane, rotation, persistence, X–Y and Lag. *What the screen
     does to the drawing.*
  4. **Picture:** the ring, the three reads and their meters, the amount; Scan's path,
     softness and depth when it lands.

  A drawer holds the rest: the routing matrix, measurements, inputs, the arpeggiator,
  splits, macros, the clock.
- **The loop on the screen.** The ring with a moving read-head over the phosphor; the
  current table as a thumbnail beside the scope; the classifier's state as a small badge
  on the ring.
- **Presets by what the loop does**, replacing *Pictures and sounds / Answering your
  playing / Playing live*:
  - **Settled:** short memory, low depth. Timbre follows the playing.
  - **Breathing:** medium memory. The sound moves between notes.
  - **Wandering:** long memory, high depth. The instrument registers itself.
  - **Open:** the loop off, a small honest bank for the plain sound, labelled as the loop
    open rather than as another product.

  Every preset passes the first-minute test, and every one but the Open bank has the
  picture moving the sound.

## Removing things properly

Each removal runs through five places, and the house rules apply to all of them.

1. **The page and the C++ core together**, with `core/tests/parity.py` still passing.
2. **Setup codes:** a version-tagged decode pass in `migrateSetup` drops removed fields or
   maps them to their nearest survivor.
3. **The plugin's saved state and host parameters.** If nobody has saved a project yet,
   now is the cheapest time to change it.
4. **Tests:** a removed feature's suite goes with it; a suite that tested two things is
   rewritten, not left asserting less.
5. **The words:** the cheat sheet, the presets' lines, `DESIGN.md`, the README.

## Stages

Lettered **P**, so they cannot be confused with the earlier plans'. Ordered so each one is
audible on its own: the first thing worth playing arrives at P2, not at the end.

- **P0 — The front door.** Retire the desktop build. Rewrite the root README around the
  loop sentence.
- **P1 — Quick wins.** The photocell lands on the figure when switched on. `edge` goes.
- **P2 — The picture stage.** Three reads, one amount on by default, meters on screen,
  stronger limits re-proved by `looptest.py`, the routing matrix to a drawer. After P2 the
  first-minute test should pass on the default sound.
- **P3 — Coherence.** One pair out of the core; the generator always heard; every drawn
  note heard and every heard note drawn.
- **P4 — Cuts**, by the table, area by area, each its own commit with its migration.
- **P5 — The Scan experiment**, offline. Go or no-go on whether a scanned phosphor can
  sound good.
- **P6 — Scan**, if P5 says go: in the core, with parity, the ring as its path, softness,
  Memory in seconds, under the loop's defences.
- **P7 — The Bench along the loop** (four tabs and a drawer) and **presets rebuilt** by
  what the loop does.

## What does not change

The C++ core and its parity harness; the brand (`DESIGN.md`); the house rules on testing,
null tests and mutation; and CLAUDE.md's *Layout decisions already made*, unless P7 brings
a reason to revisit one.
