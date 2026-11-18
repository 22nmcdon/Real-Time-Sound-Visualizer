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

## What step 1 built (18 Nov)

The core paints; nothing on the page has changed. `core/include/scope/paint.h` is four
pieces, each swappable without touching the next: **layout → strokes → paint map → reads**.
Painting is an internal switch, `Instrument::setPainting`, with its settings in
`PaintParams` (defaults below); the Trace · Paint switch and its setup field are step 2's.
Off, none of it runs, and the core's recordings are unchanged to the bit.

- **The layout** (`PaintLayout`) answers two questions: where a brush sounding a pitch is at
  a time, and which ring a note at a pitch reads. `RoundLayout` is the owner's of 18 Nov:
  clockwise from the top, one turn in 8 s, pitch outward on a log scale with A0 a third of
  the way to the outermost radius (0.47 of the canvas: the record's hole) and C8 at it.
  **A new layout is a class with those two answers, handed to `Painter::setLayout`**;
  nothing else changes. The brushwork asks it where, and the reads ask it which ring. A
  layout whose notes should read something other than a circle would widen `PaintRing` into
  a path, which the reads already take point by point. The pieces hold that a second
  layout (round turned a quarter) moves only where paint lands: the map turned back
  matches to 1.4 per cent of its paint, from where stamps meet the cells, and the reads and
  every note's table agree to 0.004.
- **The strokes.** Each sounding voice is a brush with eight bristle groups. Striking the
  note dips it, by more for velocity times the hand's Strike, and presses it wider for
  60 ms. While the key is down the brush is fed by the voice's level, so a held note paints
  an unbroken arc; once the key is let go it runs dry. It spends its load as it lays and
  feathers as it lifts, a nearly empty group catches only on high paint, and it **picks wet
  paint up and carries it on**. That is the pick-up the graphics-card test cut, here kept on
  the bristles' tips apart from the load (web/README.md says why). Width and pressure are
  the voice's level to the 0.7. Each frame's stamps, with the hand that made them, are kept
  for step 2's look (`Painter::stamps`).
- **The map** is 128 cells square, so a semitone is about half a cell, holding thickness
  and wetness. Paint dries smoothly by thickness: to a tenth wet in 2 s thin and in 6 s
  thick (a loud, loaded stroke, about one unit), smoothstep between. It **fades by a
  half-life of 16 s** (`fade`, two turns), which is what step 2 shows as Persistence while
  Paint is chosen. A half-life, because the Persistence knob already reads in one. Over
  wet paint new paint mixes; over dry it covers by its opacity, as in the study.
- **The reads.** Each voice reads the ring at its own pitch into a table of its own: the
  field there (thickness, wet paint 1.4 times dry, `wetRead`), a little across the ring,
  smoothed *along* it by Scan's Softness. Along and not across, because across is the next
  register: the trace's blur, applied here, would read a note's neighbours a fifth away.
  The voice plays its own table where it played the layer's, at the layer's depth and
  hold. Until its brush has read once (a frame or two) it plays its ink, which is a short
  attack of plain tone. The Picture amount's three reads come off the map: Glow from wet
  coverage (a quarter of the canvas wet reads one, as the trace's cover does), Motion
  from paint laid, and Memory from the share of it landing on paint already there (not
  its own stroke). They go through the picture stage's own Responds to, Rise and Fall,
  Swell and hold (`PictureStage::stepPaint`). Running away is paint covering more than
  0.35 of the canvas, the trace's saturation. One canvas: while painting, the hands' own
  pictures are not used.
- **Known limits.** Only Poly's voices paint; Mono and Dyad play through the generator's
  own path, which has no voices to give brushes, and stay plain while painting. Up to 32
  voices paint at once; past that a voice plays its ink. The settings are not stored and
  not on any control.
- **Cost.** A held chord of sixteen costs 0.168 s of a core a second on the trace and 0.185
  painting, natively (`paint_cpp cost`): about 0.35 microseconds a sample more, inside the
  core's budget with room. The governor's model does not count painting yet. At under
  2 per cent of a core for sixteen voices it need not, but step 2 should time it as
  WebAssembly in the plugin's webview before calling that settled.
- **Heard.** `web/docs/listening/painting-step1/` has the study's four phrases on the
  trace, painting, and painting with drying three times slower (6 s and 18 s: the setting
  that crosses the turn, so a held note's next lap lands in wet paint). Through Scan,
  painting reads brighter than the trace (centroid 1.7 to 3.0 against about 1.13) and
  steadier note by note (movement about 0.005 against 0.02). The slower drying is heard
  mostly through Glow, which it doubles on Crossed hands.

Still open, for when the first build is seen: the drying time (the study used 1.2 s; the
owner wanted it slower, drying smoothly from thin to thick), whether a dark ground is
allowed, and whether a palette may trade separation for character.
