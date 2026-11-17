# Painting: the design to build

Agreed with the owner on 16 November, after the painting study
(`painting-the-sound.md`; the study's cycles, the graphics-card test and the owner's
measurements are on the branch `claude/painting-study`). This is the brief the build
starts from. Where the owner chose, it says so; the rest are leans the owner accepted
as a start and may change by eye and ear.

## The shape

- **The screen draws a trace or a painting**: *Trace · Paint* (and the constellation
  again later, on each voice's real cycle). Scan, the Picture amount and the whole loop
  read whichever is shown, so the painting is in the loop the moment it is chosen.
- **The core paints; the page shows it.** The core decides the brushwork from the sound
  - where each stroke goes, how wide, how wet, which ink, which tool - and keeps a map
  of how much paint is where. That map is what Scan and the Picture amount read, so the
  sound is the same on every machine and in the plugin, and is held by the core's tests
  like everything else. The page paints the look on the graphics card from the same
  strokes (the study's physical paint, WebGL 2): the palette, the light and the weave
  are the look only and never reach the sound. Rejected: Scan reading the paint back
  from the graphics card, which would make the same performance sound different on two
  machines and could not be tested.
- **A browser or plugin view without the graphics it needs** still plays: the core's
  map is the sound, and the face can draw a plain rendering of it.

## Memory and composition

- **Fade by default** (the owner, 16 Nov): marks fade by the Persistence, so the
  painting keeps answering the hands. **Accumulate** keeps a painting; even then Scan
  reads only the recent layer, since a finished canvas stops answering.
- **Layered round** (the owner, 16 Nov): time goes round the canvas, one turn in eight
  seconds clockwise from the top, and pitch goes outward. A held note is an arc, a
  chord concentric arcs, a run a line in and out across the turn.
- **Physical paint first**, with the brush's pick-up (carrying colour on) restored,
  which the graphics-card test cut. Ink and wash and gestural come later as styles of
  the same engine.

## What Scan and the Picture amount read (the owner, 16 Nov)

- **Each note reads the ring at its own pitch's radius.** That ring holds the last turn
  of everything painted in its register, so a note's timbre is the painting of its own
  part of the keyboard; a note in an empty register sounds plainer until it is painted
  there. Rejected for now: one shared circle for every note.
- **Scan reads how much paint is where** - its thickness, never its colour - and **wet
  paint reads a little stronger than dry**, so fresh strokes shape the tone more than
  old ones.
- **The Picture amount's three reads:**
  - *Glow* is **wet coverage**: how much of the canvas is fresh, wet paint.
  - *Motion* is **paint being laid**: how fast new paint is going on.
  - *Memory* is **repainting**: how much new paint lands on old.
  How the picture responds (Responds to, Rise and Fall, Swell) works as now on these.

## Controllers on the brush (the owner, 16 Nov)

| Control | On the brush |
|---|---|
| Sustain pedal | The brush stays on the canvas: strokes do not lift between notes and the paint stays wet, so new notes blend in; let go and they lift and dry |
| Mod wheel | Brush load and pressure, from a dry scratchy brush to a heavy loaded one |
| Pitch wheel | The stroke bends with the pitch, since pitch is the radius |
| Velocity | Impact: spatter, and how far it flies |
| Aftertouch | Pressing in: the stroke widens and smears while the key is leaned on |
| Expression (CC 11) | The Picture amount, as now |

A gesture that changes the brush changes the map, so it reaches the sound through Scan.

## Brush tools (the owner, 16 Nov)

Abstract painting mixes techniques, so the brush has tools, each a way of putting paint
down or moving it: **Stroke** (the default), **Smear** (no new paint; drags and blends
what is there, so it reshapes the sound from the painting's history), **Splatter**,
**Wash**, **Knife** (scrapes or flattens, revealing older layers) and **Drip**.

- **Played as a mix** (the lean): each tool has an amount from nought to one, and any
  tool can be given a MIDI CC, so they layer; a pad pushing one tool to full covers the
  switch.
- **A Brushes panel** in the painting's settings: a row per tool, its amount, its CC
  with a Learn button, and a small drawing of the mark it makes. The amounts can be set
  on screen too.
- **Stored:** the CC assignments are the player's (Settings, with MIDI); each tool's
  starting amount is the sound's (the setup and presets).

## The order of the build

1. **The core's brushwork and paint map, and Scan and the Picture amount reading it.**
   Offline renders of the study's four phrases, sound with picture, for the owner to
   judge before anything is live.
2. **The live painting on the page**, the graphics card painting from the core's
   strokes, behind *Trace · Paint*, on the testing site.
3. **Controllers on the brush.**
4. **Brush tools and the Brushes panel.**
5. **Palettes** (made ones in a product table in `DESIGN.md`, and the player's own),
   **saving a painting and loading one as a sound**, and **Colour heard**.

Still open, for when the first build is seen: the drying time (the study used 1.2 s; the
owner wanted it slower, drying smoothly from thin to thick), whether a dark ground is
allowed, and whether a palette may trade separation for character.
