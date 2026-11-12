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

## How it is to be studied

A study and a mockup before anything is built: a held pad, the owner's Crossed hands solo,
a fast run and a chord change, rendered offline with the instrument's own core, each
painted with a first version of the vocabulary in both layouts and both memories and in
two or three palettes, shown as stills and short animations, with what Scan would make of
each played back. Then the owner judges whether it looks like art and sounds like the
instrument.
