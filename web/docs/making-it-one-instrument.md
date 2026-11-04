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
  count Scan's depth inside `LOOP_TOTAL`. (This said "slew the table's harmonics so the
  timbre glides"; the experiment tried exactly that, and it took the interest out of the
  best picture. A new table each frame, crossfaded, is the character; a glide is at most
  a control.)
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
   look good by construction. *Built in P6: a chord draws one figure, the same however it
   was played into, and the readout names the outline's interval and how fast it turns.
   Before that, a held interval's ratio closed the rose, and Play the figure locked the
   trace to the note.*
2. **Touch the picture to change the sound.** Every point of the figure is a pair of
   sample values, so dragging the figure is editing the waveform: grab part of the shape,
   bend it, and hear the oscillator change. A recording cannot be edited by dragging its
   picture. The most immediately striking thing to show anyone. *Partly built: your
   drawing and the drawn cycle; bending a live figure is new.* An idea from the owner, to
   think through before it is built: the bend on a knob as well as under the hand - turning
   it alters the picture, and so the sound - which a host could automate, and which may be
   one of the knobs that replace the macros. *Decided in P6 (the owner chose the knob
   first, the drag second, both setting one control): the knob is built. Bend and Bend at,
   on the Shape tab, bend the voice's wave at one point of its cycle. The drag is built
   too: grab the figure in X-Y and pull, and Bend at goes to the moment of the cycle you
   took hold of and Bend to whatever brings the figure nearest your hand - the same two
   sliders, moved as a hand moves them. Bend became a host parameter in P8a, in place of
   a macro, so a host can automate the bend as the hand and the knob move it.*
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
  its own instance. *Cut in P5, with file playback.*
- **Recording a clip.** The host records. Kept only if the demo needs a way to share.
  *Cut in P5, by the owner's decision.*
- **File playback** shrinks to one demo file on the site, or goes. *Cut in P5, with no
  demo file: the owner's call - a player of the synth has a keyboard.*
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
| Figures | Harmonograph, thirteen figures, text, SVG, your drawing, solids, a second generator | **Keep what draws while you play.** Generators that ignore the keyboard are the image-generator product: cut or drawer. Your drawing becomes drawing onto the phosphor. *Done in P5: all of them to the drawer, nothing deleted, by the owner's choice - a drawing is picture first and plays one note; P7 decides whether Scan wants one as a picture source* |
| Grab, drawn cycle | A cycle from the input's audio; a cycle drawn by hand | **Keep as ink tools.** (Grab reads audio, not the picture; it is not a scan) |
| Playing | MIDI in, on-screen keys, poly, mono, the dyad, pedal, learned controllers | **Keep in the synth.** Scan starts mono or dyad: one phosphor, a read rate per voice. In the effect, notes only set Scan's pitch |
| Layers | Layer B, split or layered over A: its own voice, envelope, figure, plane, turn and echo | **Keep, whole, in the synth** (the owner, in P5, over this table's first verdict, which trimmed B's own voice): a split with two sounds is how the instrument is played, and two sounds draw two figures, one in each colour (*What only the synth can do*, 5). Its loops grow defences of their own: see *Each layer's picture, and whose sound it moves* in P6 |
| Splits as two sounds, arpeggiator | Multi-timbral and hands-free performance | **Splits stay on Play**, with the layers. **The arpeggiator goes to the drawer** (done in P5) |
| Macros | Four knobs fanning out to many controls | **Kept until replaced.** Macro 1-4 are four of the plugin's eight host parameters (`kKnobs` in `plugin/src/PluginProcessor.h`), so removing them removes a project's automation. The Picture amount and the three reads replace them, with saved automation mapped across. *Done in P8a: the macros are no longer host parameters. The bank is Picture, Scan, Persistence, Bend, Cutoff, Level and Echo, the phaser's amount taking the eighth place when it is built, and the morph after them in a group of its own; nothing was mapped across, since the owner had no saved projects. The page's Macros section stays until the tab rework decides it* |
| Time and key | Key and scale, quantiser, clock, MIDI clock | **Keep only what the score needs** *Done in P5: key, scale, the quantiser and its glide, the tempo and Tap stay on Measure - the quantiser keeps a picture-pushed pitch in key, which is the loop's; the clock's source and the bar go to the drawer, on Perform. Settled after P6: the plugin takes its tempo from the host and the page from a MIDI clock when one is sent, both already built, and nothing more is wanted* |
| Modulation matrix | LFOs, seven families, fades, morphing between setups | **Advanced drawer.** Picture sources leave it for the stage. The setup morph's fader is a host parameter too, and goes only with a replacement |
| Input sources | Mic or line in, file, rack, band split, input into the generator | **The effect's ink:** the host's input in the plugin; the microphone and a couple of bundled loops on the site. The synth takes no input as ink, but keeps a sidechain: *input into the generator* stays, its final form (drawing onto the phosphor rather than reaching the oscillator directly) decided after the Scan experiment. The rack goes; the band split goes unless it earns a place. Cuts here must leave the input path the effect will need. *In P5 the rack and file playback went, with no bundled loop; mic and line input, the host's input, input into the generator and the band split stay, the split deferred by the owner* |
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
   They were Macro 1-4, the setup morph, Level, Cutoff (the voice filter's) and Echo
   (`kKnobs`); since P8a they are Picture, Scan, Persistence, Bend, Cutoff, Level and
   Echo, then Morph, with the phaser's amount to come eighth. The voice filter and the
   morph still cannot be cut as plain removals.
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
- **P2 — The Scan experiment. Go, on motion.** Six presets' phosphor recorded from the
  page, scanned four ways at three softnesses, rendered, measured and heard over two
  rounds: `scan-experiment/README.md`. What the owner heard:
  - Raw and centred readings are jarring and never reach a player. The off-centre,
    softened reading has the right feel.
  - **The morphing rose is by far the best, and its round-one take the favourite of
    all**: a picture that never repeats, read sixty times a second, each frame's table
    crossfaded into the next.
  - **The still pictures sound alike**, and nothing done to them changes that much: the
    just fifth eased is almost identical to the just fifth as it was, and gentler is
    only softer. A still picture gives a still table, which is an ordinary tone.
  - **Easing the table took the interest out of the morphing rose.** The frame-rate
    step that round two measured as grain, and set out to remove, is part of what makes
    it good.

  So Scan goes in (P7), and what it is for is settled: it turns the picture's *motion*
  into timbre, and it is worth having only where the picture moves. That is the picture
  stage's job already - Memory exists to unstick a still or cycling picture - and it
  points the synth at ink that keeps changing. Its defaults come from the listening: the
  off-centre path, softness about three cells, a new table every frame crossfaded into
  the next as round one made it, and no easing; a glide may be offered as a control, at
  nought.
- **P3 — The picture stage. Built.** Three reads, one amount on by default, meters on
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
  - *The polish, built:* Memory hears novelty as well as boredom, so a figure that goes
    round and round is remembered as one that stands still is; *running away* holds the
    stage's push down to a quarter, its bars rust while it holds, and lets go slowly;
    each control's name lights with how far the picture is moving it; and the expression
    pedal (controller 11, the Nord's swell) is the amount - though in the plugin the
    page's slider does not follow the pedal, which `instrument.h` says why. The
    Photocell's switch goes with the drawer while it is off, by the rings' rule.
  - *Moved to P7:* the ring. It is Scan's path before it is the photocell's, and the
    reads coming from inside it only mean something once P2's verdict says what the path
    is; until then the stage reads the whole screen, and the photocell stays a point
    that lands on the figure.
- **P4 — Coherence.** One pair out of the core; the generator always heard; every drawn
  note heard and every heard note drawn.
  - *One pair, built:* what is heard is the lanes summed, layer A's and B's, sample for
    sample, in the page and the core alike, and parity holds it over every generator run.
    In poly every held note is drawn: the two the draw rule picks lean onto X and Y - full
    on their side, half on the other - and the rest are inner voices in the middle, along
    the diagonal, at the same power. The crossings' notes are drawn on the axis whose line
    fired them, and the second generator, when it is drawn in B's lanes, is heard with
    them. The score's voice is the one exception, heard and not drawn (below). Nothing is clamped any more; the screen clips where it
    draws and the limiter holds the speakers.
  - *Decided, and what it cost:* the lean rather than a hard split, because the first poly
    split the outer notes hard and a chord came apart across the ears; leaning keeps the
    root in both ears and draws the old figure under one linear map, a little narrower.
    *A against B* stays hard - A's notes on X alone, B's on Y alone - because that mode is
    asked for to draw one figure, and what comes apart there is two layers, not a chord.
    In a rack every note is in the middle, since a lane is the left channel alone and a
    note leaning right would be heard there at half.
  - *Found on the way:* fourteen checks in six suites asserted the gap between the two
    pairs, each correctly; all were rewritten to the one pair, with nulls, and none was
    dropped.
  - *Always heard, built:* *Hear the generator* is gone. Whatever generator is playing -
    the site's instrument, the page's own, a rack's lane - asks for its sound as it
    arrives, and a press anywhere asks again, since a browser starts sound only after one.
    What is left of the switch is a line that says why the generator is not heard, when it
    cannot be. It was off on purpose, so that nothing made a noise unasked; that is the
    decision reversed, and what it cost is an off: the level, a lane's *Mute*, or the
    browser's own.
  - *Found on the way:* the site's instrument was never asked for its sound at all - it
    arrives after the last time a page opening reads the generator - so the asking moved
    to where every source change passes.
  - *The score's voice, heard and not drawn:* drawn, a note alone is the same signal on
    both axes, a diagonal through the middle of the screen, and the score reads that
    diagonal as every row it crosses. Once the generator was always heard, "The rose writes
    its own tune" lit 1,489 cells where the rose alone lit 140, struck its full chord every
    step, and read "settled" with its photocell loop on or off. Lowering the score's level
    did not cure it. So the score's voice is heard in the middle and not drawn, as before
    P4, the one named exception to the rule. A drawn score - this plan's seventh idea, the
    score writing into the picture it reads - comes back in P7, with the loop defences Scan
    needs as much.
  - *And the meter, which had misread every heard picture:* a picture that is heard
    reaches the screen in bursts from the audio thread, and the picture meter judged
    motion by the median of the change from one frame to the next, so most frames read
    still and a moving picture read *settled* - on the site since the compiled instrument
    became its default, unseen because the suites drew on the page's own thread. The
    verdict and boredom now judge change as a rate, all of it over a stretch of time per
    sixtieth of a second, which is the same however the motion is split between frames
    and at any frame rate. The *Motion* read keeps the frame's own.
  - *Coherence, done:* nothing is heard that is not drawn but the score's voice, nothing
    drawn is silent, and the generator is always heard. The words that said otherwise - the cheat sheet, the
    *Chords drawn* presets, the readout, the generator's input line, the clip's note - were
    rewritten with the code that made them false.
- **P5 — Cuts**, by the table, area by area, each its own commit with its migration, the
  host parameters replaced before any is removed, and the input path left whole.
  - *Edge contact, cut:* the reading that was computed and never offered, in the page,
    the core and the compiled engine's readings. It had been kept so the survey that
    chose Direction for the sixth source could ask again; the survey now asks whether
    Direction still earns its slot - 1.29 bits the other five do not hold - beside a copy
    of roundness that has to add nothing. With it went the only place the screen's turn
    and zoom showed in what the picture says, since direction does not change with
    either. No setup ever stored it, so no code needs a decode pass.
  - *Crossings, thresholds and Pluck, cut:* the two lines that played a note when the
    beam crossed them, the Threshold that turned any value into an event, and Pluck, the
    note it struck - in the page, the core, the compiled engine (which reads back two
    numbers fewer) and the plugin. They read the beam, not the phosphor. Four presets
    went with them (*Pendulums ring a bell*, *Three against two*, *Four against three*,
    *Drifting fifth*), and the Effects tab lost its Crossings section. Setup codes are
    version 5: the pass deletes the ten fields and drops any route from the threshold or
    to the pluck, which the routing list would otherwise have kept, inert, in every code
    saved after. The score's voice kept the struck sine they shared, and the parity run
    that shows it heard beyond the picture strikes it directly. None of the three was a
    host parameter, so nothing in a saved session moves.
  - *The arpeggiator, into the drawer:* its row leaves the Keyboard section on Play for a
    section of its own on a new drawer tab, *Perform*, which P8 means for the splits and
    the clock too. A running arpeggio keeps running with the drawer shut, by the drawer's
    rule that what is patched still plays. Decided by the owner, as were the two that
    follow: clip recording is cut, and file playback shrinks to one demo file.
  - *Clip recording, cut:* the Record button along the top, the Clip popover with its
    preview, Save and Discard, the recorder that mixed the speakers with any input drawn
    and not heard, and the code that wrote a webm's length into it after the fact.
    `recordtest.py` went with it, and every source's `unheard`, which only the recorder
    read. The instrument's always-there monitor chain keeps its `silent` hook: the
    readout's note on what the speakers get still asks it. Nothing about a clip was ever
    in a setup, so there is no decode pass.
  - *The rack and file playback, cut:* the File source with its picker, transport and
    drag-and-drop; Lanes, Stems and Play along; the rack with its generator lane, live
    lane, mixer, lane budget and the alignment that held a backing track back to meet
    your playing - in the page, the core (`srcLanes`, `laneDelay`, the instrument's rack
    and its delay lines), the compiled engine and the plugin. Owner's decisions: no demo
    file ("if somebody plugs into the synth, they can just use their keyboard"), and the
    rack goes with the files. What stays whole is every input: mic and line, the host's
    input, the input into the generator (FM, ride, clock, the second generator), and the
    band split, deferred - which is now the only source with lanes, so the lane panel
    (show, solo, mute, layout) is on Picture for it rather than for the rack.
    `racktest.py`, `alongtest.py` and `voicetest.py` went; the suites that borrowed a file
    or a rack as a fixture use the microphone, faked, a stand-in source or the generator
    built afresh. No setup stored the rack or a file - its membership, alignment and files
    were state only - so there is no decode pass. *Drawn by your playing* went after it,
    by the owner's decision: those presets drew the generator while its hearing heard
    your input, which only a rack with the trigger on your lane could do, and on the tone
    they heard the generator itself, with a hit refused. The other way - the hearing
    listening to the open input while the generator plays - is the effect in miniature,
    and is revisited in P9, when the effect build exists.
  - *The drawings and the clock, into the drawer:* the harmonograph, the figures (text, a
    path and your drawing among them) and the solids, and the second generator, by the
    owner's choice of "all to the drawer" over cutting text, SVG and the solids outright.
    Each draws a picture first and makes a sound of it, and plays one note - harsh with
    more, as the owner found - so the generator's *Kind* offers the waveform alone while
    the drawer is shut, and *Input into the generator* your input alone; open, they come
    back. By the drawer's rule a drawing already chosen, or loaded by a preset, stays
    chosen, offered and drawn with it shut, and a search for one opens it. The clock's
    source and the bar move to a *Clock* section on *Perform*; the tempo and *Tap* stay on
    Measure with the key and the quantiser. Nothing stored changes, so no decode pass. P7
    decides whether Scan wants a drawing as a picture source.
- **P6 — The synth's first two:** harmony as geometry and touching the picture. Both
  buildable without Scan, and the first reasons to choose the synth. And first, from the
  owner in P5: **each layer's picture, and whose sound it moves.** Split into two sounds,
  the keyboard draws two figures, one in each colour, and today the picture stage reads
  the whole screen, both of them, and pushes one set of controls. Each layer's picture
  becomes its own read, and a choice per layer says whose sound it moves - its own, the
  other's, or both - with the defences two loops need: each bounded by the loop's total
  on its own, and a pair that moves each other held so that it cannot chase itself (the
  governor's *running away* per layer, or a cap on the cross term). It needs no Scan, and
  it gives Scan two pictures to read when cross-scan comes in P7.
  - *Decided (the owner, at the start of P6):* one menu per layer - "A's picture moves:
    A / B / both", and B's likewise - so any combination is open, crossed included; a
    sound that hears both pictures takes their average, so it never gets more than one
    picture's worth of push; and a split starts with each picture moving its own sound.
    Each layer's picture is its own screen behind the one shown - the photocell and the
    eye still see both figures on one - measured with its own meter, ranges and governor;
    a crossed pair's cross push is held whenever either layer's governor holds. Unsplit,
    nothing changes. Built on the page first, then ported to the core under parity.
  - *On the page, built:* while the layers draw a figure each in X-Y, each figure is also
    laid into a screen of its own (two more picture engines, of the shown screen's kind,
    made the first time a split needs them), faded with the shown one and measured on
    its own - meter, stage, hold. The stage's reads answer per layer (`layerPush`), the
    loop's combined route asks its parts per layer, and the layers' pushes reach the
    generator through the route's two held values, which were already there. The two
    screens cost about 0.2 ms a frame together. *Pictures*, a row of two menus in the
    Keyboard section where the arpeggiator's row was, sets it, and a setup carries it
    (two additive fields, own and own by default, so no version pass). A against B and
    Y-T keep the one shared picture. `layerpicturetest.py` holds it.
  - *In the core, built:* `LayerPictures` (`core/include/scope/picture.h`) is the page's
    `layerPictures` and `layerPush`, its two grids made up front rather than on the first
    split, since the audio thread may not allocate. The instrument's own walk lays each
    figure into its layer's grid, the picture run steps them after the shared one, the
    stage's sources answer per layer, and the matrix asks per layer for the loop's route
    and for any source that answers - so the site's compiled instrument and the plugin
    have it too, with no window open. The two fields have core defaults, so
    `SETUP_AHEAD_OF_CORE` is empty, and the two menus are hands the page sends.
    Parity holds the grids, meters, stages, holds and pushes to the page's through every
    pair of menus, a crossed pair with one governor running away, unsplit, the second
    generator's two figures with no layers, and the codec; `layerpicturetest.py` reads
    each layer's screen back from the compiled instrument on the default page, and the
    shell test hears B's sound moved by B's picture in the plugin.
  - *Harmony as geometry, built:* a chord now draws one figure. A note joining notes
    already held used to start its cycle at nought wherever the others were, so the same
    chord drew a different figure each time it was built up; now it is born at the phase it
    would have had if struck with them - the lowest held voice's phase since it began,
    scaled by the two pitches' ratio - in the page and the core alike, on both layers, each
    against its own lowest voice. Unison copies keep their detune spread. What it costs is
    a peakier entrance: a triad built a note at a time now peaks where the triad struck at
    once always did (a sine 1.10 where it was 1.03, a saw 1.07 where it was 0.95), and the
    limiter is there for it. The dyad is left as it was: its two phases run on through a
    change of interval, so the same dyad reached two ways draws two figures, and lining
    them up legato would click. The readout says what the outline is and how fast it
    turns - "fifth, still", "fifth, turning 0.74 a second", "no simple ratio" for a tritone,
    each layer's with a split and A against B as one - from the nearest ratio of numbers to
    eight, within one per cent, and the rate |q·f_high − p·f_low|, where it used to say
    only "beating", only for the dyad, only in equal tuning. `harmonytest.py` holds it,
    with the loop: a held just fifth reads settled to the picture and an equal third does
    not. Parity holds the joining voices to the page's.
  - *Touching the picture, step 1, built: the Bend knob.* Two controls in the
    Oscillator section, per layer: *Bend*, the whole travel either way with nought off,
    and *Bend at*, where in the cycle it centres. The voice's phase is pushed on by
    Bend times the sine of how far it is past Bend at, so the wave runs fastest there
    (pinched) for a positive bend and slowest (swollen) for a negative one, and a
    negative bend is a positive one half a cycle on. That is the voice's FM at one to one
    with the modulator locked to the voice and turned: at a centre of nought it is FM at
    ratio one, to rounding, and it shares FM's band-limiting, which asks every shape
    about the frequency the bend has taken it to, up to 1.9 times the note. So it stays
    in tune and harmonic on every shape, chords, the dyad and layer B, each channel of
    a dyad bent at that point of its own cycle, which is what makes a circle stop being
    one. Held under 0.9 radians, where the phase never runs backwards. What it costs: a
    bent sine carries DC, since a pinched peak and a swollen trough no longer balance
    (at full bend and a quarter cycle, 0.41 of the amplitude; the limiter and the
    picture take it as an offset). *The owner left the DC as it is after P6c, to come back to: subtracting it exactly per voice for the sine, with a gentle DC blocker for the other shapes, is the candidate, measured in the app first.* *gen.bend* and *gen.bendAt* are destinations, not in
    the picture stage's bundles: whether the loop turns the bend as well as the hand is
    P7's and P8's question. `bendtest.py` holds it, and parity the core's.
  - *Touching the picture, step 2, built: the drag.* In X-Y, a press within 16 pixels of
    the figure takes hold of it, and a pull of more than 3 sets the two sliders through
    their own input events, so the hand and the knob are one control and the site's
    instrument and the plugin follow by the path a hand takes; no core change. Bend at is
    the grabbed sample's moment in its lane's cycle, measured: the fundamental's phase
    there, less the phase the shape's own fundamental has at the top of its cycle - exact
    for one voice of a plain shape on any figure, the dyad's included, where the angle
    about the centre would only have been right for a one-to-one ellipse. With notes held
    the cycle is the voice the lane leans onto (the lowest for X, the highest for Y),
    found by fitting every held note's frequency to the lane at once, since a chord's
    common period seldom fits in the window.
    Bend is solved rather than scaled: every value is tried on the figure as it would be,
    each lane read again at the time the bend moves it to, and the one whose cycle of
    figure around the grab passes nearest the pointer wins, so the figure follows the
    hand on any shape and a pull it cannot follow does nothing. What that costs is
    honesty about the bend itself: it moves the wave in time and never in level, so the
    figure cannot be pulled past its own extremes - a circle bulges on its diagonals and
    not at its four ends - and a diagonal line bends only along itself. On a chord the
    figure follows approximately, since each voice is bent in its own cycle and the
    solution reads the lanes as one. In a split the nearest figure's layer is bent and the
    panel goes to it; otherwise A. Drawing on the screen, the cursors (now only in Y-T,
    where they are drawn) and the photocell's reticle keep their presses; a double-click
    on the figure puts Bend to nought; a finger on the figure grabs rather than scrolls,
    and scrolls everywhere else. A gold ring marks the grabbed moment while held.
    `handtest.py` holds it, with real presses, on the page's brain and the compiled one.
- **P7 — Scan** (P2 said go, on motion): in the core, with parity, the ring as its path,
  softness, a table a frame as round one made them, Memory in seconds, under the loop's
  defences, pitched by the keys. Its first-minute test is a moving picture, the morphing
  rose's, since a still one gives an ordinary tone by design. Then the synth's loop
  on its own ink: the self-sustaining loop, a picture per note, notes striking the screen,
  cross-scan, and the sidechain's final form. And the score's voice drawn again, under the
  same defences: P4 found it filling the screen it reads.
  - *Decided before it was built (the owner):* Scan lives **inside the voice**, mixed under
    its shape, so it works with the bend, layers, splits and chords, rather than as a
    generator kind of its own; and its table changes at a **fixed sixty a second of audio
    time**, never at the screen's rate, so the plugin and the site match and a render
    repeats. P7 goes in three steps: **P7a**, Scan and its defences; **P7b**, notes striking
    the screen, cross-scan and the self-sustaining presets; **P7c**, the score's voice drawn
    again, kept only if it behaves. A picture per note and the drawings as a picture for
    Scan are deferred (the owner agreed: one is the biggest unknown here, and P2 found still
    pictures sound alike), and the sidechain's final form moves to P9, which has to take an
    outside input anyway.
  - *P7a, built on the page:* a Scan section on the Picture tab - *Depth*, per layer, of
    which 80 per cent is the most, *Softness*, three cells to start, and *Persistence* in
    seconds. Sixty times a second of the generator's own samples (`scanAdvance`, a sixtieth
    apart however the blocks fall, so at 22.05 kHz a tick lands part-way through a sample)
    each layer's table moves on to the latest the page has read, crossfaded across the tick;
    the reading is P2's off-centre circle round the figure's centre of brightness, which
    follows the figure over about a second, from the grid blurred by the softness, as 64
    harmonics in halving levels read like the drawn cycle's. The defences: every table
    evened to a peak of one, darkness holding the last table, a fifth of the shape always
    under Scan, the picture stage's running-away hold on the depth, and nothing read for a
    quarter of a second while a setup lands. `scantest.py` holds it and `looptest.py` runs
    Scan at its top beside everything else the loop has.
  - *What it costs, and what is approximate:* the page reads its phosphor once a screen
    frame and hands the table over, so the tick is exact on the page but which picture a
    tick plays is whichever frame arrived last; and the page's phosphor fades once a frame,
    so Persistence in seconds is seconds at sixty frames. A table is 64 harmonics at 512 points, where the drawn cycle's is
    128 at 2048, because a table a tick at that size would be most of a frame and three
    cells of softness leave almost nothing above the 30th. Noise shapes and the drawings
    have no Scan. The voice budget (S10) does not cost it yet.
  - *Found on the way:* the loop closes. A just fifth, which stands still open-loop and
    which P2 heard as an ordinary tone, wanders under Scan, because the wave it reads is the
    wave it draws: with the picture stage at nought its brightness swings by a sixth of itself where without
    Scan it moves by a three-hundredth. So the null of the first-minute test is not a still
    figure but a still screen - stopped, the screen held, Scan is an ordinary tone - and
    the self-sustaining loop P7b was to build is partly here already. The first-minute test
    itself is the turning fifth P2 measured second-most moving, not the morphing rose: the
    rose is a drawing, and the drawings as Scan's picture are deferred. *Memory* became
    *Persistence*: the picture stage has had a read called Memory since P3, and two controls
    of one name doing two things is a trap.
  - *P7a, ported to the core:* Scan plays in the compiled generator, the site's instrument
    and the plugin. The voice's half - the tick, the crossfade, the depth under the hold
    with a fifth of the shape kept, on the dyad, under the oscillator and sync, on chords
    and on both layers - is in `generator.h`, `osc.h` and `voices.h`, held to the page's
    generator to the bit, in JavaScript and in WebAssembly. The reading's half is
    `scope/scan.h`: the path, the blur, the circle and the tables, and the page's
    `scanStep` as `ScanReader::frame`, which the instrument runs at its picture frame on
    the grid it draws for itself - each layer's own while the layers draw one each. The
    frame is a sixtieth of a second of audio, so in the instrument what a tick plays depends
    on nothing but the sound, and Persistence is in seconds of it: the timing the page can
    only approximate, the core has. What cannot be held sample for sample is therefore the
    page's frames against the instrument's, so parity feeds both the same grids frame by
    frame and holds what each does with them, to 1e-12 (`exp`, `sin` and `cos` are each
    library's own). The reading allocates nothing once made, since it runs on the audio
    thread: each layer has four tables, so the one written is never one the generator reads.
    The page's brain on the compiled generator hands it each table as numbers, as the
    drawn cycle goes. Found on the way: a slider the page had and the core did not yet -
    Scan's three, between the page stage and this one - crashed the core in the middle of
    the morph's walk, because the panel used whatever its lookup returned; it is refused
    now, and parity holds that it does nothing.
  - *P7b, built on the page:* notes strike the screen, cross-scan, and loops that keep
    going. **The strike**: every note lays light as it starts - a short arc of the circle
    Scan reads, a twelfth of the lap, at the note's place round it (C at the reading's
    start, a semitone a twelfth on), as bright as its velocity times *Strike* (under Scan,
    half to start) - so it is in the very next table. It is light laid once into the
    phosphor, the picture each layer reads and the shown screen, and fades by Persistence
    exactly as a stroke does; no envelope of its own. Laid only where Scan is on, since
    the path is Scan's, so with Scan off or Strike at nought nothing changes at all. A
    harder note moves the timbre further, but not always brighter: a plateau on the read
    adds harmonics where the circle was dark and smooths them away where it crossed
    bright lines, and which way depends on the picture. The meters and the running-away
    hold see it as they see the figure. **Cross-scan**: a *Reads* menu per layer, in P6's
    shape and shown on the same condition - what that layer's Scan reads: its own picture
    (the default), the other's, or both averaged. A crossed pair has both depths held by
    the lower of the two pictures' holds, as P6's crossed pictures are; a layer reading
    both, uncrossed, takes the lower of the two it reads. **The self-sustaining loop**:
    *Scan breathes* and *Scan remembers*, in the Scanned presets, leave the waveform out
    of what notes drive, so the fifth sounds whether a key is down or not and the keys
    strike the screen rather than start the sound: let go and the loop goes on. Stop holds
    the screen and so the tone, and Depth at nought takes Scan out. *Crossed hands* is
    the split with each hand reading the other's picture. `striketest.py` holds it all,
    and `looptest.py` runs Scan with every note striking at full during fast repeated
    notes, and a split at Scan's top crossed both ways.
  - *What it costs:* nothing beyond presets was needed for the loop to keep going, but
    what those presets do is change what the keys are: there they hammer the screen and
    no longer play the note. A loop that keeps going after you let go of a note that the
    keys *did* play would need the voice to go on sounding after release - a latch, or a
    drone the keys pitch without gating - and that is a control of its own, not built,
    for the owner to decide. The plan's *Wandering* became *Scan remembers*: with two
    seconds of Persistence the screen changes slowly enough that the meter reads it
    settled while the sound never stops moving, and a preset named for wandering that the
    readout calls settled would contradict itself. Notes the arpeggiator and the score play
    reach the generator without passing `midiNoteOn`, so they do not strike.
  - *P7b, in the core:* the site's instrument and the plugin strike and cross-read too.
    `ScanReader` keeps its paths per picture, reads each picture once, and makes each
    layer's table from the reading it hears or the two averaged, with the holds as the
    page picks them; `ScanReader::strike` is the page's `scanStrike`, which the keyboard's
    note-on calls with the note's layers, and the instrument lays the arc at once into the
    grids its next frame fades and reads, through the last frame's graticule. The three
    setup fields have core defaults, so `SETUP_AHEAD_OF_CORE` is empty again, and the
    three presets are in `presets.h`. Parity feeds both sides the same grids and strikes
    and compares the segments laid, to the bit; natively, a real note in the instrument
    brightens its own screen where Scan is on, a softer one less, Scan off nothing, and
    in a split the note's layer's picture or, crossed, the other's. On the site the
    strike can only be seen through the per-layer readings the instrument hands back, so
    `striketest.py` reads it there, in a split.
  - *P7c, the score's voice drawn again: what passing means, written before measuring.*
    Five presets that use the score (*The rose writes its own tune*, *The tune you play
    into*, *The star plays itself*, *The pendulums' score*, *A sine, sung*), each run for
    twenty seconds, heard, on the page's own brain with the JavaScript generator so a
    change to the block is what plays; the first quarter is the picture filling and is
    not counted. Every number is set against the same run with the score undrawn, as it
    has been since P4, measured the same day: the README's 140 cells for the rose alone
    were counted under P4 and the rose undrawn lights a median of about 1,270 cells over
    0.05 now. A design passes only if, on every one of the five presets:
    1. *Coverage:* the median count of cells over 0.05 is at most 1.5 times the null's
       (P4's failure was about ten times), and the meter says *running away* no more than
       a tenth of the time more than the null does.
    2. *Chords:* the share of steps that strike the full chord is at most the null's plus
       0.15 (P4's failure was a full chord every step).
    3. *Variety:* the distinct chords and distinct pitches played are each at least half
       the null's, so the score has not collapsed onto the rows its own light crosses.
    4. *The meter:* the share of the time it says *settled* is at most the null's plus 0.2.
    5. *Bounded:* `looptest.py`'s run at the stage's top holds every bound with the score
       drawn (measured only for a design that passes the first four).
    Passing on some presets and not others, or on all but one criterion, is borderline,
    and goes to the owner with the numbers rather than being shipped as a judgement.
  - *P7c, measured: none passes, and the score's voice stays heard and not drawn.* Four
    designs against the null, lit cells as a multiple of the null's (the criterion is 1.5),
    for the rose writes its own tune / the tune you play into / the star / the pendulums /
    a sine, sung:
    - *Drawn unchanged* (the score in A's lanes, on both axes): 1.77 / 1.74 / 4.43 / 1.30 /
      1.41, the pendulums *running away* the whole run where the null never was, and the
      share of full chords up by 0.14 / 0.17 / 0.29 / 0.03 / 0. Fails coverage on four and
      chords on two. Variety went up rather than down (the rose's distinct chords 27 to
      52), so it is not P4's collapse onto one chord: the screen fills without it.
    - *Drawn, struck at a quarter while the meter says running away* (the picture stage's
      own hold, applied to the score): within a few per cent of drawn unchanged
      everywhere, since the hold engaged only on the pendulums, where it changed nothing.
    - *Drawn, struck in proportion to how much of the screen is dark* (velocity times
      one less the lit share over a quarter): 1.00 / 1.01 / 1.76 / 1.01 / 0.96, which
      reads as four passes and a fail - but the four pass by silence. The presets' own
      pictures light a third of the screen or more, so the governor is at nought: the mean
      velocity struck was 0 / 0 / 0.13 / 0 / 0.06 against the null's 0.95 to 1. The
      criteria had not said the score must still be heard, because it did not occur to
      anyone that a design would pass by not playing; it fails coverage on the star
      either way.
    - *Drawn but kept out of what the score reads* (the score reading a picture without
      its own light, everything else reading the one with it): measured by replaying the
      null's own strikes into the drawn page with the score's reading off, so what it
      plays cannot depend on what it drew. The shown screen still lit 1.70 / 1.74 / 4.04 /
      1.15 / 1.41 times the null's, the pendulums again running away throughout. It would
      also only half meet the seventh idea, the score writing into the picture it reads,
      and would cost a second picture drawn every frame in the page and the core.
    What this shows that P4 did not: the feedback was not the whole of it. A note of the
    score's voice is the same signal added to both lanes, so drawn it does not lay a line
    beside the figure - it moves the whole figure along the diagonal by the score's
    waveform, smearing every figure by up to six-tenths of full scale, and that alone
    fails coverage with nothing fed back. Any design that adds the score to the lanes the
    figure is in will smear it; a level low enough not to smear is a score too quiet to
    hear beside the figure. What was not tried, for whoever comes back to it: the score
    drawn as a figure of its own, in lanes of its own, as layer B is - which needs the
    third figure's place on the screen and the per-layer machinery behind it, and is a
    new design rather than a defence. The cheat sheet already says the score's notes are
    never drawn, and still does; the score's comments in the page now point here.
- **P8 — The Bench along the loop** (four tabs and a drawer), the synth's presets rebuilt
  by what the loop does, and the phaser. The owner's order, after going through it: the
  host knobs first; then knobs in place of sliders on the page, after the owner's
  Headroom (its `styles.css` and `src/lib/knob.js`: a CSS face over the range input,
  which stays the value, the keyboard's and the screen reader's), together with the
  four tabs, which measured at 2.7 tabs' worth of content across today's five; the
  phaser; the loop on the screen as something switched on when wanted rather than
  always shown; and the presets rebuilt from nothing under the four headings, most of
  today's removed, the owner having liked none of them.
  - *P8a, built: the host knobs.* Picture, Scan, Persistence, Bend, Cutoff, Level and
    Echo, the phaser's amount eighth once it exists, and the morph after them in a
    group of its own - automatable without the bank's placement, as the owner put it.
    Strike is not a parameter. The macros stopped being parameters with nothing mapped
    across, since no project had been saved. A layer's controls address the layer the
    panel shows, as their slider does for a hand, and read back when it turns; ids are
    stable strings, so the phaser's arrival moves the morph's index and not its
    automation. `plugin/PLAN.md` has the reasoning and the costs.
- **P9 — The effect.** First, from P5: whether the hearing should listen to the open input
  while the generator plays, which brings back what *Drawn by your playing* did. The build flag, the page asking which build it is, the effect's ink
  panel and preset bank, a second JUCE target, Scan pitched by the effect's notes, and the
  test that the effect's controls are contained in the synth's and the synth's extras are
  all on the named list. And, moved from P7, the sidechain's final form: another track
  drawing onto the screen the synth reads.

## What does not change

The C++ core and its parity harness; the brand (`DESIGN.md`); the house rules on testing,
null tests and mutation; and CLAUDE.md's *Layout decisions already made*, unless P8 brings
a reason to revisit one.
