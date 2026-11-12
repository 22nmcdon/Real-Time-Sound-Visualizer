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
`study.py`, then `page.py`; about four minutes, and the same pictures every time). Nothing
in the instrument was changed. It answers the first question - does it look like art and
stay true to the sound - and gives a first, rough answer to the second, what Scan would
hear.

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

So: **ink and wash for calm sounds, gestural for busy ones, geometric as the clearest to
read**, and none of the three is wrong for every phrase. The erratic phrase did not turn
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

1. Which style, or which for which sound? The study's view: ink and wash for calm,
   gestural for busy, and geometric if legibility matters more than painterliness.
2. Is Layered's turn (time round the canvas, pitch outward) the right composition, or
   should a Layered canvas have no time in it at all? The keyboard-across version was not
   kept; it is a few lines of `Layout.at` to bring back if you want to see it.
3. Is a dark ground (Night) welcome in an instrument whose brand has one light?
4. Earth only just clears the bars; should a palette be allowed to trade separation for
   character, with the quiet warning a player's own palette would get?
5. Should Fade be the instrument's default, with Accumulate as the way to keep a painting,
   since Fade is what keeps Scan answering the hands?

### What to try next

Per-hand brightness and level from the core (a log of each layer's own figure), so the two
hands' marks answer their own sound; a style blending ink and wash's washes with
gestural's flung lines, which the comparisons suggest is the strongest pair; the
instrument's real phosphor grid read beside the painting's density, to see how far apart
the two are before anything is built; and, cheaply, Scroll with pitch as the radius of a
spiral, so a long piece reads in time and still fills the canvas.
