# Painting the sound

Agreed with the owner on 12 November, to study after the constellation prototype
(`ways-to-draw.md`, step 2). Nothing here is built yet; this is what to try and why, so the
idea is not lost.

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

## How it is to be studied

A study and a mockup before anything is built: a held pad, the owner's Crossed hands solo,
a fast run and a chord change, rendered offline with the instrument's own core, each
painted with a first version of the vocabulary in both layouts and both memories and in
two or three palettes, shown as stills and short animations, with what Scan would make of
each played back. Then the owner judges whether it looks like art and sounds like the
instrument.
