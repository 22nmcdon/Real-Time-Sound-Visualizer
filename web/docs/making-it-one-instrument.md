# Making it one instrument

A plan, not built. It comes before any new feature, because every stage since the
layout revamp has added to an instrument that no longer says what it is.

The goal, in the owner's words: **a sound visualizer that alters and plays its sound
based on the picture — and the picture affects the sound always, not as a setting that
is allowed.**

Two decisions are taken. Two are open, and this document sets out both sides of each
so they can be decided before anything is cut.

| Decision | Where it stands |
|---|---|
| The plugin is the product; the site is its interface and a free demo | **Taken** |
| The desktop build (`oscilloscope-poc/`) is retired | **Taken** |
| Where the sound the picture is made from comes from: an instrument, an effect, or both | **Open** — Question 1 |
| What "the picture always affects the sound" means: the picture *is* the sound, it *steers* the sound, or both | **Open** — Question 2 |

## Why it has no identity

It is three instruments sharing a screen.

- **A synth.** Fourteen waveforms, drawbars, a morph, a wavetable and a drawn cycle; a
  second oscillator with FM, ring, sync, sub and unison; drive, fold and crush; a filter
  in every note; poly voices, splits and layers, an arpeggiator, a voice budget. Two of the
  six Bench tabs, Shape and Effects, are a synth's panel.
- **An image generator.** A harmonograph, thirteen figures (text, SVG paths and your own
  drawing among them), wireframe solids, a second generator.
- **A visualizer with some crossover.** The scope itself, the spectrogram, racks of stems,
  a band split; and the parts where the picture reaches the sound: the photocell, the
  picture meter, the score, crossings, the plane's operations.

And the crossover is optional at every step. The code says so:

- **The generator is silent until asked.** *Hear the generator* is off by default
  (`genSound: false`). Out of the box the picture makes no sound at all.
- **The picture's sources need a switch.** The Picture family on the Sources tab reads
  *"Turn on the Photocell, above the screen."* Until then the picture affects nothing.
- **Some sounds are heard and never drawn.** The core's block is
  `block(outL, outR, n, heardL, heardR)`: a picture pair and a heard pair, the same samples
  except where they are not. Poly notes that the draw rule leaves out, the score's voice
  and the crossings' plucks are in the heard pair only, by design.
- **Picture to sound is one routing among many.** It goes through the same modulation
  matrix as an LFO onto a filter: seven source families, dozens of destinations, and the
  picture is one family.

So the problem is not that features are missing. It is that the picture sits *beside*
the sound path, as one thing you may patch in, rather than *on* it.

## The identity, as one sentence

A candidate to test the options against:

> **Every sound it makes passes through the picture.**

Whatever the answers to the two open questions, a feature stays if it serves that
sentence and goes if it does not.

---

## Question 1 — where does the sound come from?

### A. An instrument

Your keys play its own oscillator. The figure on the screen is the sound: *Play the
figure* already sets the trace's rate from the note's pitch, so the figure's shape is the
timbre. It goes on an instrument track in a music program.

- **For.** Almost all of it exists. The picture can be generated, so it can always be
  beautiful. The keyboard work (poly, the dyad closing the rose, the pedal, the Nord's
  controllers) is kept.
- **Against.** In a session it is one more synth among many, and the closest existing
  product is already here: **osci-render**, an open-source JUCE plugin that plays SVG,
  text and 3D objects as oscilloscope sound. An instrument version of this would need
  to be different from that, and the difference would have to be the loop (Question 2)
  and how it is played.
- **Removes.** The racks, the band split, and most input handling. The visualizer part
  then only ever shows its own sound.

### B. An effect

It sits on any audio track (drums, a vocal, a whole mix) and draws what comes in. The
picture's transforms are what you hear back: turn the picture and the stereo image turns,
fold it and the sound folds. The instrument already does this: it draws its input, and
the plane's nine operations and the delay and chorus run on a live input.

- **For.** It is literally a sound visualizer, and it is useful on every track rather
  than only on one you play. Picture-shaped *effects* are rarer than oscilloscope synths.
  The lag X–Y, already built, makes a mono source draw a figure instead of a diagonal
  line.
- **Against.** It loses the generator, the keyboard and most of the presets, which is
  most of the work so far. And the picture is only as interesting as the input: a dull
  input draws a dull figure.
- **Removes.** The generator's shapes, the voice, figures, solids, poly, splits and
  layers, the arpeggiator. MIDI stays only for controllers and the score.

### C. Both, on one path

A switch at the top, *Input* or *Oscillator*, and everything after it shared:
**source → picture → the picture's transforms → what you hear.**

- **For.** Keeps the most. One mental model whichever source is chosen.
- **Against.** The largest surface, and it is how the instrument got where it is: C only
  works if the cuts below are made hard, especially to the oscillator, which would draw
  figures and not be a synth voice. Plugin formats also make it awkward: a music program
  treats instruments and effects differently, so C probably ships as two builds from one
  code base, an instrument and an effect, as many plugins do.

### How to decide

The plugin can already do both: it draws its own generator, or its input bus. One evening
each settles it better than this document can:

1. On an **instrument track**: a figure, *Play the figure* on, the Nord through it.
2. On an **audio track**: a drum loop and a vocal, drawn, with the plane turned and
   folded.

Then the question is simply which of the two you kept reaching for.

---

## Question 2 — what does "always" mean?

### Rule 1. The picture is the sound

The beam's two signals are what you hear. Nothing is heard that is not drawn, and nothing
is drawn that is not heard. Turning, folding or mirroring the picture changes the sound
by construction, because they are the same samples.

- **What changes.** The heard pair and the picture pair become one pair, so the core's
  `block` loses its second output. Every poly note is drawn. The score's voice and the
  crossings' plucks are drawn. *Hear the generator* is removed, because it is always
  heard. The plane stops being an effects section and becomes the instrument's core.
- **Cost.** Some pictures sound harsh. A figure retraced with corners buzzes at its
  retrace rate, and text sounds like text. That is the honest consequence: *a square
  sounds like a square.* And a chord drawn whole is a busier picture than one drawn by
  rule.
- **Why it is legible.** You see it, and you hear exactly what you see. No explanation is
  needed.

### Rule 2. The picture steers the sound

Measurements of the picture (coverage, change, novelty, where it sits, the photocell,
Boredom) always drive the sound's controls. The picture and the sound stay two signals,
joined by a stage that is always on.

- **What changes.** The photocell and the picture meter are always running. The Picture
  family stops being a family and becomes a fixed stage, *Picture → sound*, with an
  amount and a small set of targets, on from the first note. The stability work already
  built (the loop's bounds, the limiter, Boredom) becomes load-bearing rather than
  optional.
- **Cost.** It is less legible. You hear the sound move, but why it moved is a number,
  so the stage has to show what it is doing on screen or it reads as random.

### Rule 1 and Rule 2 together

Rule 1 as the path, Rule 2 as a stage on it. The picture is the sound, and how it looks
also shapes how it is played.

### What each combination is

| | Rule 1: the picture is the sound | Rule 2: the picture steers the sound |
|---|---|---|
| **A. Instrument** | An oscilloscope-music synth: osci-render's ground, and needs Rule 2 or the playing to differ from it | A synth with a picture-driven modulator, the nearest to what it is today |
| **B. Effect** | Draw the track, transform the drawing, hear the transform: a visual stereo and wave shaper | A picture-driven modulation effect: the drawing of the track moves a filter, a delay, a level |
| **C. Both** | One path for either source; the cleanest single sentence | The broadest and least focused |

---

## What goes, whatever is decided

These follow from the two decisions already taken.

- **The desktop build.** `oscilloscope-poc/` is deleted (it stays in history), and so are
  its tests and the parts of `designtest.py`, `DESIGN.md`, `CLAUDE.md` and the README
  that hold it in step. `docs/z-axis-lane.md` either moves into `web/docs/` as an idea
  for the plugin or goes with it.
- **The stem rack.** Up to six lanes from files, the rack's generator and live lanes,
  alignment for playing along, the rack's sound. In a music program the host plays files
  and each track is its own instance of the plugin, so the rack is the site doing the
  host's job.
- **Recording a clip.** The host records. This is a site-only feature, kept only if the
  demo needs a way to share a result.
- **File playback** shrinks to one demo file on the site, or goes.

## What goes, depending on the answers

Each area of the instrument today, and its fate under each source option. *Keep* is the
identity, *Trim* is kept smaller, *Cut* is deleted.

| Area | What is in it | A. Instrument | B. Effect | C. Both |
|---|---|---|---|---|
| The screen | Y–T and X–Y, trigger, timebase, persistence, phosphor, cursors, measure, the picture filter, spectrogram | Keep | Keep | Keep |
| The picture's transforms | The plane's nine operations, rotation, layer B's plane, delay and chorus on the pair | Keep (the core under Rule 1) | Keep (the effect itself) | Keep |
| The picture measured | Photocell, picture meter, shape measures, Boredom, the loop through the sound | Keep (the core under Rule 2) | Keep | Keep |
| The picture plays notes | The score, crossings, thresholds and Pluck, *Play the figure*, the pitched harmonograph | Keep; merge score, crossings and thresholds into one section | Keep the score and crossings, out as MIDI | Keep, merged |
| Figures | Harmonograph, thirteen figures, text, SVG, your drawing, wireframe solids, a second generator | Trim: keep the figures and your drawing, cut solids and the second generator | Cut | Trim, as A |
| Waveforms | Fourteen shapes, drawbars, morph, drawn cycle, wavetable, grab, noises | Trim: what makes figures; drawbars stay if the Nord is the instrument | Cut | Trim, as A |
| The voice | Second oscillator (FM, ring, sync, sub, unison), drive, fold, crush, voice filter, the voice budget | Trim hard: a synth does these better, and unison is why the budget exists | Cut | Trim hard |
| Playing | MIDI in, on-screen keys, poly, mono, the dyad, splits and layers, pedal, learned controllers, arpeggiator | Keep MIDI, the dyad and the pedal; cut splits, layers and the arpeggiator | MIDI for controllers only | As A |
| Time and key | Key and scale, the quantiser, the clock, MIDI clock | Keep only what the score needs | Keep only what the score needs | Same |
| Modulation | LFOs, the matrix, seven families, macros, fades, morphing between setups | Trim: fewer families once the picture is a stage; macros become the host's parameters | Trim | Trim |
| Input sources | Mic or line in, file, rack, band split, lag X–Y, input into the generator | Cut, except a line in for the demo | Keep the input and the lag; band split if it earns it | Keep the input and the lag; cut the rack |
| Presets | 31 sections in three menus | Rebuilt around the identity, a fraction of the size | Rebuilt | Rebuilt |
| MIDI out | The score and the crossings to an outside instrument | Keep with the score | Keep with the score | Keep with the score |

## Removing things properly

Deleting a feature here is not deleting a block of code. Each one runs through five
places, and the house rules apply to all of them.

1. **The page and the C++ core together.** Whatever is cut from `scope.html` is cut
   from `core/` in the same stage, and `core/tests/parity.py` still passes with its
   nulls, so the two never disagree about what the instrument is.
2. **Setup codes.** Old codes name fields that will no longer exist. They get a
   version-tagged decode pass in `migrateSetup` that drops them or maps them to their
   nearest survivor, never a decoder that guesses.
3. **The plugin's saved state and host parameters.** A project saved in a music program
   holds the plugin's state. If nobody has saved one yet, now is the cheapest time ever
   to change it; after release, the same migration rule applies to the plugin's state.
4. **Tests.** A removed feature's suite goes with it. A suite that tested two things, one
   cut and one kept, is rewritten rather than left asserting less.
5. **The words.** The cheat sheet, the presets' descriptions, `DESIGN.md` and the README
   entries that describe the cut feature. The cheat sheet goes stale first.

## Stages

Lettered **P**, so they cannot be confused with the earlier plans' stages.

- **P0 — Decide.** The two evenings in Question 1, then Question 2. Record both answers
  at the top of this document.
- **P1 — Retire the desktop build.** Mechanical, and independent of the answers.
- **P2 — Cut what the plugin-first decision already cuts:** the rack, recording, and file
  playback down to the demo.
- **P3 — Make the rule structural.** Under Rule 1: one pair out of the core, the
  generator always heard, every drawn note heard and every heard note drawn. Under Rule 2:
  the photocell always on, and *Picture → sound* as a stage with its amount on screen.
  This is the stage that turns "allowed" into "always".
- **P4 — Cut by the table** above, area by area, each its own commit with its migration.
- **P5 — Lay the Bench out along the path.** The six tabs are by task today (Play,
  Picture, Shape, Effects, Sources, Measure). After the cuts they can follow the signal
  instead: *Source → Picture → Transform → What it plays → Sound*, so the panel reads as
  the sentence.
- **P6 — Presets, rebuilt** around the identity: fewer, each a demonstration of the
  picture changing the sound.
- **P7 — New work, only if it serves the sentence.** From earlier discussion, the
  strongest candidates: **scanned synthesis** (the picture as a force on a virtual string
  whose moving shape is the waveform, picture-driven by nature), **wave terrain** (a path
  orbiting the phosphor grid at the note's pitch), and **a picture from a photo or the
  camera**, so a drawing on paper becomes a score.

## What does not change

The C++ core and its parity harness; the brand (`DESIGN.md`); the house rules on testing,
null tests and mutation; and the decisions in CLAUDE.md's *Layout decisions already
made*, unless P5 brings a reason to revisit one.
