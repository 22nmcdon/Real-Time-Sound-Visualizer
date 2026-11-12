# Painting the sound

Agreed with the owner on 12 November, to study after the constellation prototype
(`ways-to-draw.md`, step 2). Nothing in the instrument is built yet. The study it called
for was made the same day, offline: its page is `painting-study/index.html`, and what it
tried and found is the last section here, *What the study found*.

## The problem

The screen draws the waveform. A simple sound gives a stable figure; a chord, a detuned
sound or anything noisy changes phase every cycle, so a complex sound draws an erratic
tangle that reads as noise rather than as the sound. The owner wants a picture that
looks like abstract art and still holds every nuance of the sound.

## The rule it follows

**The picture is true to the sound.** A calm sound paints a calm picture and a hectic
sound an erratic one: the mode does not calm the sound or the picture down, it changes
what the picture is drawn *with* - a painter's marks rather than a beam - so that an
erratic sound becomes a composition rather than a scramble. And, from
`making-it-one-instrument.md`, it acts on the loop: Scan reads the painting back as sound,
or it is decoration, which is what the drawings cut in G2 were.

## The vocabulary

What the sound does, and the mark it makes:

| The sound | The mark |
|---|---|
| A held, steady tone | A wash: a broad, soft area of pigment that deepens while held |
| A melody | A brush stroke following the pitch, thicker when louder, tapering as the note fades |
| A sharp attack | A splash or spatter, its size how hard it was played |
| Noise and grit | Dry-brush or grain texture |
| Harmony | Colour relationships: consonant intervals in related inks, a dissonance a clash |
| Each hand | Its own ink, as now |

Everything on the canvas comes from the sound; nothing representational (no trees or
faces), because that would be content the sound does not contain. Where a mark lands can
still be chosen for composition.

## The choices (the owner, 12 Nov: offer both of each)

- **Memory:** *Accumulate* - the canvas keeps the whole piece, so a performance ends as a
  painting, which can be saved as an image - or *Fade*, forgetting slowly by the
  Persistence.
- **Layout:** *Layered* - everything on one canvas, built up like an action painting - or
  *Scroll* - the piece painted left to right, so a performance can be read back in time
  (close to the trail in `ways-to-draw.md`).
- **Palette:** a set of palettes made for it, and palettes of the player's own.

## Things to settle when it is studied

- **The palette must not change the sound.** If Scan reads brightness, a palette changes
  what it reads, and choosing colours would change the tone. Scan should read how much
  ink is where - its density - and not its hue or lightness, so the palette is only the
  look, as Which hands and Trail are in Enlarge. To be measured: the read table identical
  under every palette.
- **A full canvas must not turn the tone to mush.** Accumulate keeps everything; Scan
  reading all of it would thicken the tone through a piece. Candidates: Scan reads only
  the recent layer, or the Persistence, while the image keeps the whole.
- **The palettes are product, not brand.** The six lane inks were measured to stay apart
  on the paper, and the brand's colours are shared with the jazz and guitar apps, so not
  this repository's alone to change (`DESIGN.md`). The made palettes go into a product
  table of their own, which `designtest.py` holds. A player's own palette is theirs:
  where it is kept (the browser, the plugin's state, or the setup so a preset carries it)
  is to decide, and a low-contrast one is their choice, perhaps with a quiet warning.

## Colour heard, as a choice (the owner, 12 Nov)

The rule above keeps the palette out of the sound by default: Scan reads density, so
colours are only the look. The owner's idea is a choice beside it, **Colour heard**, in
which the differences between neighbouring colours - not the colours themselves - shape
the tone, for a wider variety of sound. Ways it could sound:

- **Edges as brightness.** Along Scan's path, a jump between unlike colours is a sharp
  step in the wave, so more harmonics; a smooth blend between like ones a soft tone.
  Contrast becomes roughness, which is what the eye already reads as harsh or calm.
- **Adjacency as harmony.** Neighbouring colours that sit close on the wheel read as
  consonant partials, ones far apart as a clash - the same mapping the vocabulary uses
  for drawing harmony, run backwards.

To settle when it is studied: the difference measured in a perceptual colour space (so
"unlike" means unlike to the eye, not to the numbers); what a player with a colour vision
deficiency hears from colours they cannot tell apart (`DESIGN.md` measures the lane inks
under simulated colour blindness for the same reason); and that a saved sound with Colour
heard keeps its palette, since there changing the palette changes the sound - which is the
point of the choice, and why *Ink only* stays the default.

## A painting loaded as a sound (the owner, 12 Nov)

Since Scan reads the canvas, a saved painting can be loaded back onto it and played:
one performance's painting becomes the instrument for the next. Pitch still comes from
the held note, so the painting sets only the timbre, and whatever is played paints over
it. What to settle:

- **What is saved.** The density Scan reads, not only the coloured image, so a painting
  loads back exactly whatever palette it was shown in; the image with its density beside
  it, kept with saved sounds rather than in a setup code, which would grow by the grid.
- **A ground that does not fade.** Loaded as ordinary light it would fade by the
  Persistence and be gone in seconds. As a ground layer under the light - read by Scan,
  never fading, the new strokes fading over it - the painting stays the instrument's body.
- **Where Scan reads it.** On a whole canvas, where the circle sits and how large it is
  decides which part of the painting is heard; moving it explores the painting, as the
  photocell's reticle moves now.
- **A scroll painting replays.** The score already plays notes from a playhead across the
  grid's columns, so a painting in the Scroll layout could be played back as the piece
  it came from, or as a new one.
- **Any image.** Lightness as density makes any picture a ground, which is how image-to-
  sound synthesisers work; Softness rounds what would otherwise buzz, and a photograph is
  likely to read harsh. Worth trying in the study rather than promising.

## What else does this

Parts of it have been done, none of it whole: drawing read as sound (Murzin's ANS
synthesiser and Zolotov's Virtual ANS, Oram's Oramics, Xenakis's UPIC and HighC,
McLaren's drawn sound on film); images played as spectrograms (MetaSynth, Photosounder,
Coagula, Harmor's image resynthesis, the spectral editors); sound composed to draw on an
X-Y scope (Jerobeam Fenderson's oscilloscope music, OsciStudio); the reading itself
(scanned synthesis, wave terrain synthesis); colour as sound (Harbisson's eyeborg, Chrome
Music Lab's Kandinsky); and abstract visuals from music that nothing hears back (VJ tools
such as Synesthesia). None closes the loop - the sound paints, the painting is read back
as the sound, and a painting kept becomes the next instrument. The owner looked at them
(12 Nov) and liked how none of them looks, so the look is this design's to find rather
than to borrow; their sound is still worth hearing, Virtual ANS and MetaSynth first.

## How it is to be studied

A study and a mockup before anything is built: a held pad, the owner's Crossed hands solo,
a fast run and a chord change, rendered offline with the instrument's own core, each
painted with a first version of the vocabulary in both layouts and both memories and in
two or three palettes, shown as stills and short animations, with what Scan would make of
each played back. Then the owner judges whether it looks like art and sounds like the
instrument.

## What the study found (12 Nov)

The study is `painting-study/index.html`, with every painting, animation and sound beside
it, and the scripts that made them in `painting-study/tools/` (`phrases.py`, then
`study.py`, then `page.py`; about seven minutes, and the same pictures every time). Nothing
in the instrument was changed. It answers the first question - does it look like art and
stay true to the sound - and gives a first, rough answer to the second, what Scan would
hear.

### Physical paint, the owner's first ask

*The first cycle, as first shown. The second cycle (below) replaced its layout, its drying
and its brush; what follows is kept as the record of what was tried.*

Asked for mid-study (12 Nov), and the owner's priority: a style that looks and feels like
an actual painting - *"a paintbrush stroke that has its depth and nuance, and how other
strokes hitting the same one will affect it differently by merging and the texture
shifts."* It is a small paint simulation, `tools/oilpaint.cpp`, fed brushwork made from
the sound by `tools/physical.py`.

**The model.**

- **The brush** is 32 bristle groups across its width, each with its own load of paint
  and its own mixture. A dipped brush lays solid paint for several widths and has gone
  to dry brush by about ten. Bristle groups loaded unevenly run dry at different times,
  which makes the streaks.
- **The paint** is pigment amounts per pixel, so its thickness is a height map. Over
  that sits a plain-weave canvas whose threads wander.
- **Light** is a raking light from the top left: thick strokes stand up with ridges at
  their edges, and thin ones sink into the weave. Wet paint glistens and goes matt as
  it dries.
- **Colour** is Kubelka-Munk with one constant per channel. Pigments mix as pigments
  (slate and terracotta make a brown, gold and jade a green), not as an RGB average.
- **Drying.** Paint's wetness falls to 1/e in 1.2 seconds.
  - **Over another stroke's wet paint**, the brush picks some up and carries it on,
    shoves some into ridges at its flanks, and its own paint mixes in.
  - **Over dry paint**, the new coat hides what is under it by its opacity, and a
    nearly empty brush catches only on the high points (the weave and dried ridges),
    which gives broken colour.

**What it took.** Two faults hid the behaviour until the stroke was tested alone on a
synthetic canvas (blue across, red across it while wet, red across it after drying):

- **The brush never ran dry.** It was picking up its own just-laid paint, which
  refilled it. Only another brush's paint, or its own from more than 0.15 s before,
  is picked up now.
- **Nothing merged.** The time-round-the-canvas Layered layout never brings a stroke
  back to a place until eight seconds later, by which time the paint is long dry.
  Physical paint's Layered therefore puts each note round the canvas by its pitch
  class (a turn an octave, so pitch spirals outward) and turns the whole by time only
  once a minute. A note played again lands where it was: a run's next pass goes into
  its own wet paint, and a note after a pause goes onto dry paint.

Further bugs were found by looking:

- The first footprint was a box, which drew bristle marks across the stroke.
- A perfectly periodic weave made dry brush a ruled grid.
- A separate impasto stab for each strike read as sticks poking out of the strokes. A
  strike now presses the stroke itself, wider and heavier for 60 ms from a deeper dip.

**How true to the sound it is.** Each kind of playing paints differently, and the
simulator counts where each phrase's paint landed when it fell on other paint: into wet
paint (merging) or onto dry (layering).

| Phrase | Into wet | What it paints |
|---|---|---|
| Fast run | 98.8 per cent | Three passes over the same notes, each into the last one's wet paint: one heavy worked stroke, ridged where it was dragged |
| Crossed hands | 90.6 per cent | The right hand's run merges into itself and drags the plum through the olive; the grace notes after the pause, and the left hand's chord change, lay over dry paint |
| Chord change | 88.2 per cent | Each chord's notes, laid side by side at once, merge with each other; where the next chord shares a pitch class it lays over the last one, by then dry |
| Held pad | 100 per cent (of very little) | Five broad strokes, each pulled slowly round by time, dense where dipped and breaking to dry brush, re-dipped every two seconds held |

A loud attack is a stroke that starts wider and heavier from a deeper dip, and the
hardest flick flecks. A held tone is a long stroke that broadens as it is held. A fast run
merges, and a phrase after a pause layers.

What is not true to the sound:

- **The re-dip** every two seconds of holding is a painter's rhythm, not the sound's.
- **The drying time** is a choice: 1.2 s makes the study's phrases show both behaviours.
- **The wheel's slow turn** is composition.

**As art.** It is the closest of the four to a painting: the detail crops show bristle
streaks, paint banked at the stroke's edge, colour dragged from one stroke into the next,
and canvas showing through the dry end of a stroke. Two things are not yet right:

- Paint shoved aside by a wet crossing sometimes lands as a boxy patch.
- The merged run has a fine ribbed, slightly tubular look from pushing on every step.

Both are in the push model, which moves paint to a single place at the flank, where a
real brush spreads it.

**What it costs.** Measured on one core of this machine, Crossed hands at 20 frames a
second:

| Canvas | Brushwork per frame | Lighting and mixing the whole canvas per frame |
|---|---|---|
| 512 × 512 | 0.8 ms | 28 ms |
| 1000 × 1000 | 2.5 ms | 103 ms |
| 1600 × 1600 | 6.7 ms | 267 ms |

The brushwork is cheap enough for real time already. The render is not, as written: it
relights and remixes every pixel every frame, single-threaded. It is a per-pixel
computation with no dependencies between pixels, so it is a fragment shader's work, a
few milliseconds on any GPU. On the CPU, only the regions a frame's strokes touched
need redoing, which on these phrases is a few per cent of the canvas. The webview the
plugin uses could run it as WebGL; the page could too.

**Scan.** Physical paint's coverage (how far the paint hides the ground) is identical to
the bit under all three palettes, as the ink density is for the other styles. Read by
Scan, Crossed hands gives a table of harmonic centroid 2.13 finished and 2.07 to 2.28
while being painted. That is steadier than the other styles, because paint does not fade
and a stroke's body is solid.

### The second cycle (12 Nov, after the owner's look)

The owner called the first cycle "a really, really strong start", asked for six things,
and then narrowed the cycle to three, in this order:

1. The sound-driven compositions on all four phrases, each with what Scan reads off it.
2. The stroke ends fixed.
3. A small brush mapping a viewer can actually see.

Left for later: drying, the boxy patches and ribbing, and more work on ink and wash or
geometric. Physical paint is a test of what is possible, not a commitment to run it
live. The page opens with this cycle; `tools/study.py cycle2` remakes it.

**Three compositions, every phrase in each, side by side** (`Composed` in
`tools/paint.py`). In all three the sound decides where marks go; the only randomness is a
brush's own small variation. Each is fitted to the canvas with one scale, so the phrase's
own extent sets the balance. Notes struck together sit beside their hand's leading note
across the brush's direction, so a chord is a band of parallel strokes.

- **Travel.** Each hand's brush travels:
  - each strike turns it by the interval from the hand's last note (up one way, down the
    other, a leap further than a step);
  - how fast the spectrum is changing bends it, brighter one way, darker the other;
  - agitation and level hurry it, so it lingers on a held chord;
  - it drifts towards its register's height (pitch is height);
  - a note struck again within three seconds steers it back to where that note was
    painted, so it comes back over wet paint where the playing returns.

  The pad is one broad straight band, since it has no contour and nothing returns.
  Crossed hands is a wandering right-hand line beside a short left-hand band. The run is
  a meander. The chords are a slightly kinked band.
- **Cycles.** Travel, with a circular gesture only where the sound is cyclic: a hand
  holding without striking circles, and a repeated figure, steered hard back to its own
  marks, loops. The pad coils into one ring whose colour shifts through the chord's inks
  as they mix wet. The four held chords make four arcs of a ring. Crossed hands' run loops
  beside the left hand's circling chord. The run's three passes loop over each other.
- **Clusters.** Time across, warped by how much is happening, pitch up, and each gesture
  (strikes without a pause over 0.35 s) drawn in towards its centre. The pad is five
  horizontal bars, one a note. Crossed hands is two zigzags over the left hand's bands.
  The run is three peaks. The chords are a grid of short strokes. It reads most like a
  score and least like a painting.

**What Scan reads off each.** Where the paint lands against Scan's circle decides the tone,
so every composition is also a sound. Each painting on the page has two sounds under it:
the canvas read as it is painted (built up for physical paint), and the finished painting
held under A3. It is the same first approximation as the first cycle: density on the
64 by 64 grid, the core's own scan functions at Softness 3, a depth of 0.6 against a sine.
Physical paint was read at 512 square, frame by frame; gestural as it fades, by the
Persistence. Both have their audio beside every painting. The first cycle's ring layouts
are the baseline, and their sounds are on the page too, so the old layout can be heard.

The measures:

- **Centroid:** the table's harmonic centroid, in harmonics (a sine is 1).
- **Movement:** the median frame-to-frame change of the table's normalised harmonic
  powers, nought to one.
- **High:** energy above the eighth harmonic (harsh where large).
- **Sine:** energy in the first harmonic (dead where nearly all).

Physical paint, finished painting / median while painting:

| | Pad | Crossed hands | Fast run | Chords |
|---|---|---|---|---|
| Ring (cycle 1) | 2.42 / 2.68 | 2.17 / 2.18 | 1.16 / 1.16 | 3.96 / 3.43 |
| Travel | 1.95 / 1.68 | 2.17 / 2.17 | 1.34 / 1.34 | 2.17 / 1.56 |
| Cycles | 1.81 / 2.02 | 2.35 / 2.37 | 2.26 / 2.19 | 1.69 / 1.92 |
| Clusters | 2.55 / 2.11 | 2.72 / 2.72 | 2.71 / 2.09 | 1.95 / 1.50 |

Movement while painting:

| | Pad | Crossed hands | Fast run | Chords |
|---|---|---|---|---|
| Ring | 0.005 | 0.0015 | 0.001 | 0.008 |
| Travel | 0.003 | 0.005 | 0.012 | 0.003 |
| Cycles | 0.003 | 0.004 | 0.027 | 0.005 |
| Clusters | 0.005 | 0.005 | 0.005 | 0.003 |

What these say:

- **Nothing goes harsh.** Energy above the eighth harmonic stays under 1 per cent in every
  case. The ring's chords were the brightest single read (centroid 3.96).
- **Travel goes dead in places.**
  - The fast run's finished painting reads nearly as a sine (84 per cent of its energy in
    the fundamental, centroid 1.34), as it does on the ring (86 per cent, 1.16). A
    meander or a ring that Scan's circle crosses in only a few places gives it almost
    nothing.
  - In gestural, Travel's pad and chords are sine-like while being painted (median
    1.05 and 1.11): a straight band crosses the circle twice.
  - Travel is the composition most likely to sound dead.
- **Cycles moves most with the playing.** The run's table moves 0.027 a frame, twenty-seven
  times the ring's, and swings between centroid 1.65 and 3.32 as its loops cross the
  circle. Crossed hands moves about three times the ring's. It is the one where the read
  tone follows the hands.
- **Clusters reads brightest and steadiest.** Finished centroids of 2.0 to 2.7 for every
  phrase, and little movement: many separate marks round the circle make a rich table
  that changes slowly.
- **Against the ring,** every new composition evens out what the ring did unevenly:
  - the ring's run was dead and its chords the brightest;
  - in the new compositions, no phrase is both that dull and that bright.

Gestural, read as it fades (audio beside each painting), tells the same story, duller
throughout because a fading canvas holds less ink. Cycles' run moves most (0.030), and Travel's held phrases are
nearest a sine. The full numbers, with the high and sine shares, are in `results.json`
and on the page.

**The judgement: Cycles makes the strongest paintings, and the most alive sound.** Each
phrase comes out as its own picture, a ring appears only where something is held or
repeated, and its read tone moves with the playing most. Clusters is the safest sound and
the least painterly picture. Travel is the next strongest picture but can go dead to Scan.
The other styles are shown in Cycles.

**The stroke ends.** As the level fell, the brush's contact narrowed, and its 32 bristle
groups were mapped across whatever the current contact was. Every streak was squeezed
towards the centre line and ran on past the end as thin hard lines. Now each group keeps
its place on the brush, fewer touch as it lifts, and below half pressure only some
bristle tips touch, scattered, each laying less. The end feathers. It was found on a
synthetic stroke that fades out, which drew the lines before the fix and feathers after
it.

**A brush you can read** (`tools/physical.py`). Four links, chosen from the pairings
people find natural between sound and sight:

| The sound | The brush | Measured as |
|---|---|---|
| Loudness | Size and thickness: wider and heavier | The core's level is the pressure; velocity and attack sharpness load the dip |
| Pitch | Height | The composition's: each hand's brush drifts to its register's height |
| Brightness | Lightness and sharpness: up to three fifths white in the dip; stiff, hard-edged, streaky bristles | Spectral centroid against the sounding pitch, -0.3 to 1.3 octaves as nought to one |
| Roughness | A jagged, broken texture: the line shakes (1.5 to 15 pixels), the brush drags dry | Plomp and Levelt's dissonance, in Sethares's form, over every pair of the spectrum's peaks on a 170 ms window |

Each stroke adds its own seeded variation: its bristles' loads, an 8 per cent breathing of
its width, small offsets to stiffness and dryness. The page's sampler paints one gesture
six times, quiet and loud, dark and bright, smooth and rough, each pair differing in that
one link alone, so each can be seen. White had to be three fifths of the dip at most,
since two fifths hardly lifted charcoal. The dry drag is capped at seven tenths, past
which a stroke all but vanishes.

A longer mapping (spread as splay, richness as load, noise as dry brush) was built first
and dropped when the owner narrowed the cycle. It made strokes vary, but not in ways a
viewer could name.

**Done before the narrowing, and left as it is.**

- **Drying.** Wetness falls to 1/e in 1.5 × (1 + 3 × thickness) seconds, so thin paint
  dries first. Not judged here; the owner will judge it while playing.
- **The push model.** It now ploughs with the leading half into a spread, and a slow
  brush does not plough its own paint.
- **The heading.** A tremor no longer turns the brush.

**Cost per frame** (one core, Crossed hands in Cycles, 20 frames a second):

| Canvas | Brushwork | Render |
|---|---|---|
| 512 × 512 | 0.6 ms (cycle 1: 0.8) | 39 ms (28) |
| 1000 × 1000 | 1.5 ms (2.5) | 126 ms (103) |
| 1600 × 1600 | 4.2 ms (6.7) | 337 ms (267) |

The render is dearer, from the seventh pigment (white) in every pixel's mix and the
thickness-dependent gloss. It is still the part a fragment shader would take.

**Gestural** carried through all three compositions and stays the most immediately
art-like of the styles; Crossed hands and the run in Cycles are its best pieces yet.
**Geometric** no longer looks alike piece to piece, but its held notes still sit in one
place while Cycles' fit spans the orbit, so the pad's circles crowd into a corner.
**Ink and wash** is as it was. Neither was worked on further.

**Questions for the owner, this cycle.**

1. Cycles, Travel or Clusters, judged by eye and by ear? Or a different one for different
   music?
2. Is the brush legible enough at four links, or is any link too weak? Brightness as
   lightness is the subtlest on dark inks.

### The graphics-card test (12 Nov)

Can physical paint run live? `painting-study/gpu/index.html` replays Crossed hands in
Cycles in WebGL 2, in step with its sound. You choose a canvas of 512, 1000 or 1600
square. A frame-time readout shows the mean and worst frame over the last second, and the
GPU time where the browser offers `EXT_disjoint_timer_query_webgl2`. The CPU render of
the same moments sits beside it. A plain message says which is missing if WebGL 2 or
float render targets are not there. Everything is inline except `strokes.bin`,
`crossed.mp3` and the two CPU stills, all in the same folder. Kept a test, not a product.

**What runs where.**

- **On the graphics card,** per pixel, every frame, in fragment shaders over two
  ping-ponged float textures (seven pigment amounts and each pixel's last wet time):
  - stamping each of the frame's brush steps: bristle groups and their loads, the
    feathered lift, dry brush catching on the weave;
  - wet paint smudged along the stroke;
  - covering dry paint;
  - wetness by thickness;
  - then, to the screen: Kubelka-Munk over all seven pigments, the height over the
    weave lit by the raking light, and the wet gloss.

  The weave is computed once per size, from oilpaint.cpp's own function.
- **On the CPU, in the page:** choosing the frame's steps and uploading them, at most
  55 in a sixtieth of a second, a few kilobytes.
- **Precomputed, offline** (`tools/export_gpu.py`, into a 229 KB `strokes.bin`): the
  brushwork itself, 2,633 steps of where each brush is, its width, pressure,
  stiffness, dryness, its mixture and its 32 bristle groups' loads. This replays
  oilpaint.cpp's brush rules, which do not depend on the canvas except through
  pick-up.

**What was cut.**

- **The brush picking paint up and carrying it on.** It needs the canvas under the brush
  read back every step. Here, wet paint is smudged along the stroke instead.
- **The ridges** pushed to a stroke's flanks.
- **The per-brush test** that keeps a brush from dragging its own fresh paint. Here,
  paint younger than 0.15 s is left alone, whoever laid it.
- **One mixture per bristle group.** It is one per step.

All seven pigments fit (two RGBA textures, with the wet time in the eighth channel), so
none was cut. The look is close: at the end of the phrase the two renders match in the
weave, the bristle streaks, the light and the mixes. The visible difference is the left
hand's circling chord, greyer and more striped on the GPU and browner on the CPU, which is
the pick-up's carried colour.

**Measured in headless Chromium, which has no graphics card.** It runs WebGL in software
(SwiftShader, on this machine's four CPU cores), so these are a floor, not the owner's
machine:

| Canvas | Mean frame | 95th percentile | Worst |
|---|---|---|---|
| 512 × 512 | 39 ms | 83 ms | 633 ms |
| 1000 × 1000 | 619 ms | 3.5 s | 4.1 s |
| 1600 × 1600 | 1.8 s | 6.1 s | 6.1 s |

Even in software, 512 square runs at about 26 frames a second. The cost grows faster
than the pixel count because a slow frame has to catch up on more brush steps, and the
stamping shader loops over each of them across the frame's box. At a real 60 frames a
second, a frame carries at most 55 steps.

**An estimate for real hardware, not a measurement.** Each frame reads and writes the
paint state once (64 bytes a pixel) and reads it about five times to light it. At 1000
square that is about 300 MB a frame: about 1 ms on a discrete graphics card (300 GB/s
and more) and 5 to 6 ms on a laptop's integrated one (about 50 GB/s). So 60 frames a
second at 1000 square looks likely, and at 1600 likely on a discrete card. The page's
readout is how to find out: open it on the machine that matters.

**The first measurement on real hardware (the owner's machine, 12 Nov).** It held 60
frames a second at every size: the mean frame time was about 16.7 to 17 ms at 512, 1000 and
1600 square, which is the display's 60 Hz refresh, so the page was waiting on the screen,
not the paint. The graphics card's own time per frame, by `EXT_disjoint_timer_query_webgl2`:

| Canvas | GPU time, mean | Share of a 60 Hz frame (16.7 ms) |
|---|---|---|
| 512 × 512 | 0.7 ms | 4 per cent |
| 1000 × 1000 | 2.3 ms | 14 per cent |
| 1600 × 1600 | 5.8 ms | 35 per cent |

**Against the estimate,** which was about 1 ms at 1000 square on a discrete card and 5 to 6
ms on an integrated one: 2.3 ms sits between the two. It is twice the discrete figure and
under half the integrated one. The time also grows with the pixels almost exactly (0.7,
2.3, 5.8 ms for 1, 3.8 and 9.8 times the pixels), which is what a bandwidth-bound per-pixel
pass predicts. The estimate's model was right in kind, and a little optimistic for this
machine.

**Headroom.** At 1000 square, about 14 ms of every frame is left. That has to hold:

- **the pick-up that was cut.** On the GPU it would be a small brush texture updated
  from the canvas under each step, a few thousand pixels a step, not a full pass, so
  probably well under a millisecond;
- **the scope's own drawing,** the trace and the phosphor the page already draws each
  frame;
- **Scan's 64 by 64 read-back,** reduced on the GPU first;
- **the plugin's webview,** which is a different browser engine on each platform and is
  untested here.

At 1600 square about 11 ms is left, which is still comfortable on this machine. A weaker
integrated card would put 1600 square at risk first, and 1000 square is the sensible
default. The owner's look: it has real potential, and it looks different from the CPU
drawing because of the cut pick-up, which they expect can be fixed.

**What a live version in the instrument would need.**

- **Where the paint state lives:** in the plugin's webview, as these textures, on the
  graphics card. Not in the core.
- **What the core sends each frame:** the brush steps, about 50 at most per frame,
  each about 200 bytes, so about 10 KB a frame, through the bridge that already carries
  the picture to the page. Computing the brushwork live needs only the voices and the
  spectral measures the core already has (levels, envelopes, brightness, roughness).
- **What Scan would read:** the paint's density. That needs a read-back from the
  graphics card at Scan's 60 a second, reduced to 64 by 64 on the GPU first: a few
  kilobytes, but a synchronous read stalls the pipeline unless it is asynchronous and a
  frame late.

The honest risks:

- **Scan's read is a round trip.** The sound would depend on the graphics card, so the
  same performance could sound different on two machines, against the determinism
  parity holds the core to.
- **The plugin's webview may lack float render targets.** That is WebKitGTK on Linux;
  the page detects it, but the instrument would need a fallback.
- **The pick-up is cut.** Carrying colour on a brush wants a read-back or a different
  model.
- **The paint never fades.** A live screen would need to wipe or glaze it, which is the
  Persistence question again.

### What was played

Four phrases through the instrument's own core (`scope::Instrument`, natively, at 48 kHz in
128-frame blocks, a note landing at the top of the block it falls in), by `render.cpp`, a
copy of `core/tests/tools/instrument_cpp.cpp`'s loop that writes the heard pair and a log of
the core's voices - each voice's note, where its glide has got to, its envelope's level and
whether its key is down, every block:

- **A held pad**: *Slow pad*, Cmaj9 (C3 G3 D4 E4 B4) held 9 s, 12 s in all.
- **Crossed hands**: the owner's setup code from `the-picture-amount.md` and their
  sequence, compressed from 27 s to 15.5 so it fits the brief's 8 to 20: every gesture
  kept in its order, the gaps shortened.
- **A fast run**: *Tine piano*, C major C4 to C5 and back three times at nine notes a
  second, velocity swelling to each top and a little louder each pass, 7.2 s.
- **A chord change**: *Drawbar organ*, Dm7 G7 Cmaj7 Am7, 2.5 s each, 11.6 s.

### The mapping

Everything a mark is made from is either the core's voice log or a measure of the heard
pair (`features.py`; 10 ms frames, a 2048-sample Hann FFT):

| The sound | Read from | The mark |
|---|---|---|
| Which note, how loud, still held | The core's voices | Where it lands; a stroke's width, as the level to the power 0.7, so a note tapers as it fades |
| A held tone | A voice above a twelfth of its peak, past its attack | A wash, pool or circle that grows with the square root of the time held and deepens with it |
| A melody | A hand's strikes within 0.45 s of each other, through the top note of each | One stroke, gliding to each next note in the last third of the gap |
| A sharp attack | Velocity, and the core's attack time to 90 per cent | Spatter, drops or rays: as many as velocity squared times sharpness, as far as velocity |
| Agitation | Strikes (a chord is one) in the last half second, four being full, three quarters; spectral change frame to frame, a quarter | How far the brush shakes off its line, as a smooth noise; how far a strike flings |
| Brightness | Spectral centroid against the level-weighted pitch sounding, in octaves | How fast the ink-and-wash brush dries into dry-brush streaks |
| Noise and grit | Spectral flatness, 0.01 to 0.3 on a log scale | Granulation in washes, specks of grain, a grit of small squares |
| Harmony | Each note against the lowest sounding, round the circle of fifths | Its hand's own ink (0 or 1 steps: unison, fifth, fourth), a related ink (2 to 4: seconds, thirds, sixths, minor sevenths), the clash ink (5 or 6: semitone, major seventh, tritone) |
| Each hand | The split | Its own three inks; only Crossed hands has two |

Where a seeded random choice enters, it only chooses where within a mark's reach a drop
lands or which bristle runs dry first: never how many, how far, how wide, how dark or
which ink. The measured phrases order themselves as a listener would: median agitation 0.07
for the pad, 0.18 for the chords, 0.24 for Crossed hands (0.89 at its 95th percentile, in
the fast run) and 0.86 for the run.

### The layouts

**Layered went round.** The first version placed marks across by pitch, as on the keyboard,
and up by brightness. It was true and dull: brightness hardly moves in a held sound, so
every phrase lay in one band and a held chord was a row of blobs. Layered now goes round
the canvas by time, one turn every eight seconds clockwise from the top, and out by pitch:
a held note is an arc, a chord concentric arcs, a run a line in and out across the turn,
and a phrase longer than eight seconds paints over its own beginning, which is what
layered means. It is a composition chosen, as the brief allows, and it has a property
worth keeping: Scan reads a circle about the figure's centre, so on a Layered painting it
reads a ring of the register through the whole piece. **Scroll** is time across and pitch
up, as planned; it reads back like a score, and as a picture it is weaker - a phrase is a
strip with most of the canvas empty above and below.

**Fade** lets each mark fall to a tenth in four seconds, a wash of the paper over it as the
screen's Persistence is. It looks like a comet: the last second's marks bright, a ghost of
the last few behind. It is the better *instrument* display (it shows what is being played)
and Accumulate the better *picture*.

### The styles, judged as art

- **Ink and wash** is the most beautiful on the calm phrases and the most true: the pad is
  five soft concentric rings that look like a sumi-e ensō drawn by a careful hand, and the
  run is a single calligraphic gesture with dry-brush streaks where it got bright. On
  Crossed hands the left hand's washes and the right hand's olive brush hold apart well.
  Its weakness is the one the brief feared: washes add, and the first version's pad was a
  black disc. Thinner coats that thin further as a note is held, and a density that
  saturates softly towards the darkest ink, fixed it - but a long, loud, dense piece in
  Accumulate will still darken towards a ring of grey, and that is the real limit.
- **Gestural** has the most energy and, on Crossed hands and the run, is closest to
  something hung on a wall - the flung skeins and the spatter flying the way the hand
  went do look like the playing. On the pad it is too close to ink and wash (a pad has no
  gesture to fling), and the drips are the least convincing mark: they are placed rather
  than run.
- **Geometric** is the most legible - you can count the notes, see the consonant chord as
  a band round the turn and the tense G7 as a plane across it - and in the Night palette
  it is the single strongest image of the study. It is also the most diagrammatic: on the
  pad it is five circles in a row and on the run a beaded line, closer to a chart than to
  Kandinsky. It needs more composition than the sound gives it.

So: **physical paint is the one that looks like a painting** (above); of the other
three, **ink and wash for calm sounds, gestural for busy ones, geometric as the clearest
to read**, and none of the three is wrong for every phrase. The erratic phrase did not turn
to noise in any style in Layered (the turn separates the run from the chord), but in
Scroll the gestural Crossed hands is close to a scribble, and the wobble's first version, a
pair of sines, read as a machine's zigzag until it became a smooth noise.

### What was hard

- **A full canvas went to mud** (the pad, first try) - fixed as above; the limit stays.
- **Beads**: dabs laid once per sample left gaps on fast moves, and washes laid every 70 ms
  with a strong rim showed as chains of circles. Dabs are now laid along each segment and
  washes every 30 ms with a soft rim.
- **The organ's held chords measured restless**: equal-tempered beating moves the spectrum
  frame to frame as much as a run does. Agitation now weighs strikes three to one over
  spectral change; a listener hears the beating as shimmer, not agitation.
- **Brightness is of the whole sound**, not each hand's: the heard pair is mixed. The core
  could log each hand's own level and brightness if this is built.
- **Harmony is judged against the lowest note sounding in either hand**, so in Crossed
  hands the right hand's notes take their ink from the left hand's bass, which is the
  harmony a listener hears but not each hand's own.

### The palettes

The measure `DESIGN.md` quotes for the lane inks (16.1 and 8.8) is not written down, but
**OKLab distance times a hundred, worst of all pairs, with Machado, Oliveira and Fernandes'
2009 simulation at full severity, gives exactly those figures** (`tools/colour.py` asserts
it), so the palettes are held to the same bars, 15 and 8, and 3:1 contrast on the ground.

| Palette | Ground | Inks (A main, related, clash; B main, related, clash) | Worst normal | Worst simulated | Least contrast |
|---|---|---|---|---|---|
| The house | `#faf6f0` | ch1 `#241f1d`, ch2 `#5c6488`, ch6 `#a6552d`; ch3 `#4c4921`, ch4 `#6f9169`, ch5 `#72245e` | 16.1 | 8.8 (deutan) | 3.29:1 |
| Earth | `#f0e7d6` | umber `#33221a`, sienna `#af3d0b`, smalt `#294e81`; terre verte `#556d50`, ochre `#a87f0f`, madder `#6f2a4a` | 15.3 | 8.2 (deutan) | 3.00:1 |
| Night | `#151a24` | chalk `#ece3d0`, cerulean `#8ba4d6`, vermilion `#e8734f`; gold `#d8b349`, jade `#48c79f`, orchid `#bb65b0` | 15.8 | 8.4 (deutan, tritan) | 4.65:1 |

Earth's and Night's inks were picked by eye and failed (Earth 10.2 and 2.2, Night 12.5 and
3.2); from a second pick for Earth and the first for Night (the starting points in
`tools/tune_palettes.py`) they were moved in OKLCH as little as would clear the bars with a twentieth to spare, each within
20 degrees of hue of its pigment (`tools/tune_palettes.py`). A first search that maximised
separation instead drove every ink to its most saturated and greyed the umber. Earth only
just clears: six earth pigments are close kin, and the ochre sits at exactly 3:1. Two
cautions: a wash is a dilute ink, and dilute inks are closer together than the full ones
the bars measure; and Night is a dark ground, which the brand has never had (its one
light is deliberate, `DESIGN.md` section 3), so it is a product decision as much as a
palette.

**Adding them** would take a product table in `DESIGN.md` section 10 beside the lane inks,
the tokens in `scope.html`'s `:root` (say `--paint-earth-1` to `-6` and `--paint-earth-ground`)
with the comment saying they were measured, and a measurement in `designtest.py` that
repeats this one, since a new token not in a table fails it already.

**The palette does not change what Scan reads.** Each Crossed hands painting was made from
scratch once per palette and its ink density compared: identical to the bit. The null: the
lightness of the coloured images, which is what Scan would read if it read the picture,
differs between palettes by up to 0.35 of full scale on a 64 by 64 grid, so the check can
fail and does for that.

### What Scan would hear (a first approximation)

Each style's Crossed hands painting as a 64 by 64 grid of ink density, read by the core's
own `scanGeometry`, `scanBlur` (Softness 3), `scanRead` and `scanTables` (`tools/scanread.cpp`),
played as a held A3 at a depth of 0.6 against a sine. Not the instrument playing a
painting: nothing puts one on its screen yet, the voice's other stages are left out, and
density as what Scan reads is the study's assumption.

| Style | Finished painting | While painting, faded |
|---|---|---|
| Ink and wash | harmonic centroid 2.51 | 1.66 median (1.18 to 2.22) |
| Gestural | 2.33 | 1.53 (1.10 to 2.03) |
| Geometric | 2.60 | 2.13 (1.29 to 2.76) |

The worry was that a full canvas would turn the tone to mush. On this measure it does the
opposite: the finished, accumulated painting reads *brighter* than the fading one (more
of its circle is crossed by marks, so more edges), and steady. What it loses is motion:
the faded canvas changes as the playing does and the full one does not. So the brief's
candidate holds - Scan reads the recent layer (the Persistence) while the image keeps the
whole - for the reason that a kept painting stops answering the hands, not that it goes
dull. Six of the 310 frames at the start of each phrase were too dark to read, and held
the last table, as the core does.

### Questions for the owner

1. Does physical paint look like the painting you meant? Its detail crops are the place
   to judge it. Is 1.2 seconds the right drying time: long enough for a run to merge,
   short enough for a phrase after a breath to layer?
2. Of the other three, which style for which sound? The study's view: ink and wash for
   calm, gestural for busy, and geometric if legibility matters more than painterliness.
3. Is Layered's turn (time round the canvas, pitch outward) the right composition, or
   should a Layered canvas have no time in it at all? The keyboard-across version was not
   kept; it is a few lines of `Layout.at` to bring back if you want to see it.
4. Is a dark ground (Night) welcome in an instrument whose brand has one light?
5. Earth only just clears the bars; should a palette be allowed to trade separation for
   character, with the quiet warning a player's own palette would get?
6. Should Fade be the instrument's default, with Accumulate as the way to keep a painting,
   since Fade is what keeps Scan answering the hands?

### What to try next

Per-hand brightness and level from the core (a log of each layer's own figure), so the two
hands' marks answer their own sound; a style blending ink and wash's washes with
gestural's flung lines, which the comparisons suggest is the strongest pair; the
instrument's real phosphor grid read beside the painting's density, to see how far apart
the two are before anything is built; and, cheaply, Scroll with pitch as the radius of a
spiral, so a long piece reads in time and still fills the canvas.
