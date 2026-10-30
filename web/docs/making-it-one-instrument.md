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
| Where the sound comes from: its oscillator, the track it sits on, or both | **Taken:** both, as **two plugins from one codebase**: an effect whose ink is the track, and a synth whose ink is its own oscillator (see *Two plugins, one instrument*). **The synth ships first**; the effect follows |
| What makes the synth worth having | **Proposed:** only what needs an ink the loop can reach; the synth is the effect plus those (see *What only the synth can do*) |
| What the plugin's host parameters become | **Rule:** none is removed until its replacement exists, and saved automation maps across (see *Removing things properly*) |
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
   of the screen, and the code notes it sits at nought for most pictures. (Found in P1:
   it was never offered as a source either. It lost the survey for the sixth slot to
   signed area and is still computed and passed between the page and the core, so it
   costs a little and does nothing, but it was not one of the reasons the photocell felt
   inert. Removing it is cleanup, and moves to P5.)

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

### Two plugins, one instrument

The first version asked whether this is an instrument, an effect, or both. The answer is
both, as **two plugins**:

- **The effect.** Its ink is the track it sits on: a vocal, drums, the Nord's own audio, a
  mix. Notes into it are optional, and only set the pitch Scan reads at, as a vocoder takes
  notes. With no notes held, the picture stage still shapes the input, so it works on drums
  too.
- **The synth.** Its ink is its own oscillator, played from the keys.

They are two plugins rather than one with a switch for three reasons. The effect never
carries the synth's panel, presets or state, which a switch would only hide. A music
program loads instruments and effects in different slots, and each lands in the right one.
And each gets its own first minute: *put it on a track* for one, *hold a chord* for the
other.

They are **one codebase**, not two:

- **One C++ core.** Both builds compile the same engine, wired to a different ink. The
  instrument already draws either its generator or its input (5g), so the split is mostly
  packaging.
- **One page.** The plugin tells the page which build it is, and the page shows that
  build's ink panel and preset bank. Two copies of `scope.html` would drift apart within a
  month: controls are moved, never copied.
- **One setup format.** A setup from either loads in the other, which ignores the ink
  fields it does not have.
- **Two JUCE targets** from one project.

**The synth ships first, and the effect after it.** Two builds double the presets, the
tests and the first-minute work; the synth-only features below are where the instrument is
most distinctive; the site's demo is the synth; and whether real audio *looks* good in the
effect is still untested. So the split is late in the stages. What is decided now is only
what keeps the effect cheap to add later: one codebase, and no cut that breaks the input
path the effect will need.

The website has no track to process, so by default it is the synth's demo; a couple of
bundled loops can let it show the effect too.

**The rule that keeps it from sprawling: the synth is the effect plus whatever needs an
ink the loop can reach.** Everything the effect shows, the synth shows. The synth adds only
its ink panel, its preset bank, and a named list of features that act on its own
oscillator (*What only the synth can do*). Anything else that differs between the builds
is the old synth panel coming back. Because the difference is a build flag, the rule is a
test, not an intention: load the page as each build, list every control on show, and fail
unless the effect's set is contained in the synth's and the synth's extras are all on the
named list.

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

## What only the synth can do

The synth must not feel like the effect with an oscillator bolted on. What justifies it is
one difference, and everything below follows from it: **in the synth, the picture can
change the thing that is drawing it.**

The effect's ink is a track. The picture can reshape what is heard, but it cannot change
the vocal that went in, so the effect is an open chain: input, screen, output. The synth
owns its ink, so its loop closes all the way round: the oscillator draws, the screen
remembers, the reading changes the oscillator, the oscillator draws something new. And
because it is the synth's own oscillator, the synth knows exactly what it is doing, to the
sample and the phase. Anything that needs either of those can exist only in the synth.

The test for a proposed synth feature: **does it need to change the ink, or to know
exactly what the ink is doing?** If so, it belongs in the synth. If it is another way to
make a sound (more waveforms, more voice tricks, more unison), it is the old synth panel,
and it fails. The current Shape and Effects tabs mostly fail it.

Seven features pass, ranked by what to build first:

1. **Harmony as geometry.** The synth knows its notes' exact ratios and controls their
   phase, so a fifth draws a closed, still figure and a slightly detuned chord *turns*:
   the beat rate becomes the rotation speed. Consonance looks still and dissonance
   restless, reliably; real audio drifts too much for that. This is what makes the synth
   look good by construction. *Partly built: a held interval's ratio closes the rose, and
   Play the figure locks the trace to the note.*
2. **Touch the picture to change the sound.** Every point of the figure is a pair of
   sample values, so dragging the figure is editing the waveform: grab part of the shape,
   bend it, and hear the oscillator change. A recording cannot be edited by dragging its
   picture. The most immediately striking thing to show anyone. *Partly built: your
   drawing and the drawn cycle; bending a live figure is new.*
3. **The picture plays the oscillator back.** The picture stage's reads drive the
   oscillator's own shape (morph, fold, sync), so the figure reshapes itself and the sound
   moves under one held chord. In the effect the same reads can only shape the output.
   *Partly built: the loop presets, through routing by hand; the picture stage makes it
   the default.*
4. **It keeps going on its own.** With Scan reading the screen and that reading also
   feeding the ink, the loop sustains itself: the *Breathing* and *Wandering* presets. When
   the effect's input stops, the effect stops. *New, with Scan.*
5. **Each note, and each layer, draws its own picture.** The synth knows which voice laid
   which light, and which notes went to which layer. So a split or a layer draws two
   figures at once, or A against B, and each held note can be read back on its own: a
   chord stays a chord rather than smearing into one scan. The effect only ever sees the
   mix. *Partly built: two figures and A against B exist, with B's own plane and turn;
   reading notes back separately is new.*
6. **Notes strike the screen.** The synth knows the exact moment and velocity of every
   note, so a note can hit the phosphor with light, as the hammers did in scanned
   synthesis. The effect can only guess at onsets, and late. *New.*
7. **The picture writes the oscillator's tune.** The score reads the screen and plays the
   synth's own voice, whose figure is drawn back onto the screen it reads. *Built: "The
   rose writes its own tune".*
8. **Cross-scan.** With two layers drawing, each one's Scan reads the *other's* picture:
   A's timbre is made from what B drew, and B's from A. *New, with Scan.*
9. **A sidechain drawn onto the screen.** Another track, fed in as a sidechain, draws onto
   the same phosphor the synth reads, so its picture bends the synth's sound through the
   picture stage and Scan. *Partly built: "input into the generator" brings a live input
   to the oscillator today, but directly (FM, ride, clock), not through the screen. Its
   final form is decided after the Scan experiment.*

Harmony as geometry and touching the picture come first: one is mostly built and makes the
synth beautiful by construction, the other is the thing nobody else does. The
self-sustaining loop, cross-scan and the sidechain through the screen all wait on the Scan
experiment.

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
- **`edge`**, the reading that is computed and never offered (in P5, as cleanup).

### By the loop sentence

| Area | What is in it | Verdict |
|---|---|---|
| The screen | Y–T and X–Y, Lag X–Y, trigger, timebase, persistence, phosphor, cursors, the picture filter | **Keep:** the instrument's body. Persistence becomes Memory |
| The phosphor's readings | Photocell, picture meter, shape measures, Boredom, the loop | **Keep, and promote** to the picture stage; the classifier becomes a governor |
| Score | A playhead across the grid, rows as scale degrees, out as MIDI | **Keep:** the phosphor read at tempo |
| Crossings, thresholds, Pluck | Notes from the figure's geometry, not from the phosphor | **Cut.** They read the beam, not the phosphor; what is good in them folds into the score |
| Waveforms | Fourteen shapes, drawbars, morph, wavetable, drawn cycle, noises | **Reframe as ink.** Fewer on show; morph as the one knob; drawbars stay for the Nord |
| The voice | Second oscillator (FM, ring, sync, sub, unison), drive, fold, crush, voice filter, the budget | **Ink modifiers.** Sync and fold up front (the strongest change to the picture); the rest trimmed hard or in a fold-out. Unison is why the budget exists |
| The plane | Nine X–Y operations, rotation, layer B's plane, delay and chorus on the pair | **Keep, as Space:** transforms of the picture change what the phosphor holds, so with Scan they change the sound twice. **One addition, after the cuts: a phaser.** It turns different harmonics by different amounts, so on X–Y the figure twists unevenly and lines open into loops, which nothing in the plane does; steered by the picture stage |
| Figures | Harmonograph, thirteen figures, text, SVG, your drawing, solids, a second generator | **Keep what draws while you play.** Generators that ignore the keyboard are the image-generator product: cut or drawer. Your drawing becomes drawing onto the phosphor |
| Grab, drawn cycle | A cycle from the input's audio; a cycle drawn by hand | **Keep as ink tools.** (Grab reads audio, not the picture; it is not a scan) |
| Playing | MIDI in, on-screen keys, poly, mono, the dyad, pedal, learned controllers | **Keep in the synth.** Scan starts mono or dyad: one phosphor, a read rate per voice. In the effect, notes only set Scan's pitch |
| Layers | Layer B, split or layered over A: its own voice, envelope, figure, plane, turn and echo | **Keep their pictures, in the synth:** two figures at once, A against B, B's own plane and turn (*What only the synth can do*, 5). **Trim** what only makes B a second synth: its separate voice settings and envelope |
| Splits as two sounds, arpeggiator | Multi-timbral and hands-free performance | **Drawer, or cut** if unused |
| Macros | Four knobs fanning out to many controls | **Kept until replaced.** Macro 1-4 are four of the plugin's eight host parameters (`kKnobs` in `plugin/src/PluginProcessor.h`), so removing them removes a project's automation. The Picture amount and the three reads replace them, with saved automation mapped across |
| Time and key | Key and scale, quantiser, clock, MIDI clock | **Keep only what the score needs** |
| Modulation matrix | LFOs, seven families, fades, morphing between setups | **Advanced drawer.** Picture sources leave it for the stage. The setup morph's fader is a host parameter too, and goes only with a replacement |
| Input sources | Mic or line in, file, rack, band split, input into the generator | **The effect's ink:** the host's input in the plugin; the microphone and a couple of bundled loops on the site. The synth takes no input as ink, but keeps a sidechain: *input into the generator* stays, its final form (drawing onto the phosphor rather than reaching the oscillator directly) decided after the Scan experiment. The rack goes; the band split goes unless it earns a place. Cuts here must leave the input path the effect will need |
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
  splits, macros, the clock. In the effect, Ink is the input (its level, Lag X–Y, a
  band split if one survives) and Play holds only the notes that set Scan's pitch.
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

  Each build has its own bank under those four headings: the effect's are about what
  happens to a sound, the synth's have to *be* sounds. Every preset passes its build's
  first-minute test, and every one but the Open bank has the picture moving the sound.

## Removing things properly

Each removal runs through five places, and the house rules apply to all of them.

1. **The page and the C++ core together**, with `core/tests/parity.py` still passing.
2. **Setup codes:** a version-tagged decode pass in `migrateSetup` drops removed fields or
   maps them to their nearest survivor.
3. **The plugin's saved state and host parameters.** If nobody has saved a project yet,
   now is the cheapest time to change the state. The host parameters have a stricter rule:
   **none is removed until its replacement exists, and saved automation maps across.**
   Today they are Macro 1-4, the setup morph, Level, Cutoff (the voice filter's) and Echo
   (`kKnobs`), so the macros, the morph and the voice filter cannot be cut as plain
   removals.
4. **Tests:** a removed feature's suite goes with it; a suite that tested two things is
   rewritten, not left asserting less.
5. **The words:** the cheat sheet, the presets' lines, `DESIGN.md`, the README.

## Stages

Lettered **P**, so they cannot be confused with the earlier plans'. Ordered so each one is
audible on its own: the first thing worth playing arrives at P3, not at the end. And the
Scan experiment runs from the start, beside the first stages, because the identity stands
or falls on it: if it fails, the instrument is the picture stage alone, and the cuts and
the synth's features should be chosen knowing that.

- **P0 — The front door. Built.** The desktop build is retired (it is in the history), the
  root README says what the instrument is and where it is going, and `designtest.py`
  holds `DESIGN.md` to the page alone.
- **P1 — Quick wins. Built.** Switched on by hand, the photocell lands on the nearest
  bright part of the figure, where it used to read about 0.02 at its default spot; a
  setup's own placement is kept. `edge` moved to P5 (see cause 4 above).
- **P2 — The Scan experiment. Run; waiting on the listening.** Six presets' phosphor
  recorded from the page, scanned four ways at three softnesses, rendered and measured:
  `scan-experiment/README.md`. Softness turns buzzy tables warm; a centred path plays a
  symmetric figure out of tune (the three-petalled rose three times too high), and an
  off-centre path fixes that for five of the six. The go or no-go is the owner's ears on
  the renders, recorded here when they have been heard.
- **P3 — The picture stage. Built but for its polish.** Three reads, one amount on by default, meters on
  screen, stronger limits re-proved by `looptest.py`, the routing matrix to a drawer. After
  P3 the first-minute test should pass on the default sound.
  - *Built:* Glow (coverage), Motion (change) and Memory (boredom), on the fold, the echo,
    and the twist and right channel's phase, under one *Picture* amount at 60 per cent by
    default, with three bars beside it; in the page and in the core, held together by
    parity, so the plugin and the site's instrument play it. The amount is the
    player's, as a pedal's would be: a setup that names it sets it, and a preset, which
    does not, leaves it where the hand put it. The picture's readings no
    longer wait for the photocell, which is now only the reticle's switch. Glow and Motion
    are rescaled to their recent range with a least span. `stagetest.py` is the
    first-minute test, run on the site as a visitor opens it, and it passes: a held chord's
    brightness moves between 0.06 and 0.27 within the first second, where the same chord
    at nought stays within 1 per cent.
  - *Found on the way:* the range has to close back quickly. At an eighth a second a
    struck chord held Glow at the top for eleven seconds, and the default sound became a
    bright tone that stood still, which the first-minute test failed. At a half a second,
    a strike blooms and lets go, and the fold, the coverage and Glow make a slow loop of
    their own, about every four or five seconds on the default tone. That is the first
    thing to listen to: it may be too much, or the wrong control, and the amount and the
    bundles are where to change it.
  - *Not changed:* the reach and the per-control total. Rescaling made the effect plainly
    heard at the old limits (the fold alone made the default tone four times brighter),
    so nothing was raised; `looptest.py`'s stability run now has the stage at its top
    beside every picture source, and every bound held.
  - *The drawer, built:* *Advanced*, under the Bench's rail, opens it. Shut - as a first
    visit finds it - the Bench is the loop's five tabs, with no source chips beside the
    screen and no hollow ring on every control; whatever is patched still plays, and a
    control with something on it keeps its dots. Open, the Sources tab, the chips and the
    rings come back. It is a view, remembered per viewer and never stored in a setup, and
    built to take P8's other residents by naming their tabs. The stage's three reads are
    never offered by hand: they were leaking into the chips, the editor and the search as
    three inkless sources.
  - *Left:* each control lit while the picture moves it; *running away* pulling the amount
    down; Memory taking novelty as well as boredom; the amount on the expression pedal;
    and the ring, which is P7's path as much as P3's. And the Photocell's button: its
    reading reaches the sound only through a routing, which now lives in the drawer, so
    on the top bar it is a switch that does nothing until the drawer is opened - until
    the ring replaces it.
- **P4 — Coherence.** One pair out of the core; the generator always heard; every drawn
  note heard and every heard note drawn.
- **P5 — Cuts**, by the table, area by area, each its own commit with its migration, the
  host parameters replaced before any is removed, and the input path left whole.
- **P6 — The synth's first two:** harmony as geometry and touching the picture. Both
  buildable without Scan, and the first reasons to choose the synth.
- **P7 — Scan**, if P2 said go: in the core, with parity, the ring as its path, softness,
  Memory in seconds, under the loop's defences, pitched by the keys. Then the synth's loop
  on its own ink: the self-sustaining loop, a picture per note, notes striking the screen,
  cross-scan, and the sidechain's final form.
- **P8 — The Bench along the loop** (four tabs and a drawer), the synth's presets rebuilt
  by what the loop does, and the phaser.
- **P9 — The effect.** The build flag, the page asking which build it is, the effect's ink
  panel and preset bank, a second JUCE target, Scan pitched by the effect's notes, and the
  test that the effect's controls are contained in the synth's and the synth's extras are
  all on the named list.

## What does not change

The C++ core and its parity harness; the brand (`DESIGN.md`); the house rules on testing,
null tests and mutation; and CLAUDE.md's *Layout decisions already made*, unless P8 brings
a reason to revisit one.
