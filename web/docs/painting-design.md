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
- **Known limits (as step 1 left them).** Only Poly's voices painted; step 2 painted
  Mono and Dyad too (below). Up to 32 voices paint at once; past that a voice plays its ink.
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

## What step 2 built (18 Nov)

The owner heard step 1 ("a whole different timbre and texture to the sound and visual ...
heading on the right path"); the two dryings sounded alike to them, so 2 s and 6 s stay.
Step 2 put the painting live on the page, behind *Trace · Paint*.

- **Two setup fields, additive, no version bump.** `screenDraws` (`trace` or `paint`) and
  `paintPersistence`, the painting's half-life in seconds (16 to start, one to 120). A code
  from before them draws the trace and keeps the trace's persistence. The core follows
  `screenDraws` at each picture frame, so Scan and the Picture amount read whichever is
  shown; the painter is made at prepare, so switching makes nothing on the audio thread.
- **Paint is the fourth place in the display switch**: Y–T · X–Y · Spect · Paint. Paint is
  another way the screen shows the sound, and each of the other three pressed is the trace
  again in that view (the core takes the press the same way). The trace's display is kept
  underneath, so the photocell and the score go on reading it. The first try was a Trace ·
  Paint switch of its own beside the display switch; it cost the toolbar a row at every
  window, so it went. In the display switch, with two pixels off each side of its buttons, the
  toolbar is one row at 1400x900 and wider, as it was with three, and the same two rows as
  before at the smaller windows. Switching moves and resizes nothing on the face (the owner's
  rule of 18 Nov), measured by `painttest.py` at 1400x900 and 960x600, every element with an
  id, the only boxes allowed to change those whose own words did - the Persistence's reading.
  The info line is left out of that check: it names whatever was last pressed, so its menu
  and *More* move along after its words on every press of anything, Y–T against X–Y as much
  as Paint, which is the line's behaviour under the owner's rule rather than the switch's.
  The press is a click the instrument keeps as a hand (`drawPaint`, and the views').
- **Persistence in Paint is its own value** on the one knob (the owner's choice over one value
  meaning two things). The knob reads "16 s to half", a log scale from a second to two
  minutes, 16 s at 58 (`paintOfSlider`, `paintSliderOf`, page and core alike). A hand on it
  in Paint is kept as a `paintPersistence` hand, not a slider's, so a later hand on the knob
  in Trace does not take its place among the hands and a reopened state has both. The
  host's Persistence knob follows whichever is shown: the plugin reads it back when Trace or
  Paint is pressed, as it does when the panel turns layer; the shell test holds auval's
  retention with Paint shown.
- **Mono and Dyad paint.** A brush for the lower note and, while the pair is apart, one for
  the upper, each a stroke like any note's; a note struck again is a new brush, so a line's
  notes are strokes of their own rather than one bent through them. The generator plays one
  table for the line or the pair, so it is read off the lower note's ring, the one its phase
  runs at.
- **The face is served every stamp** the core lays, twenty floats each - where, which way,
  its width and pressure, when, how far it went, its eight bristle groups' loads, and its
  brush, hand, ink and note - from a ring of 4096 counted from the first: on the site with
  the worklet's readings (`brain_paint`), in the plugin as `paint/COUNT.bin`, the count in
  the path since not every web view hands a resource provider a query. The map is served
  every third frame (`brain_paint_map`, `paintmap.bin`). Each stamp's ink is its harmony
  against the lowest note sounding, judged by the core as the study judged it.
- **The look on the graphics card** (`paintView` in the page): the study's physical paint in
  WebGL 2 - bristle groups, six pigments mixed by Kubelka-Munk, the weave under a raking
  light, wet paint glistening and drying by its thickness - with **the pick-up put back** as a
  pass of its own: each brush's eight bristle groups take up wet paint from under where they
  pass and carry its colour on to where they lay next, a frame behind at most. The inks are
  the lane inks, by hand and harmony as the study had them (charcoal, slate, terracotta;
  olive, sage, plum) on the paper, so `DESIGN.md` gains nothing. The canvas is 768 square
  whatever the screen, so Enlarge and a resize keep it. **The fade is a gain**: paint is stored
  grown by the half-life and read over the gain, so a frame paints only the box its stamps
  fall in and the screen; the whole canvas is divided back once the gain passes a million.
  Fading every pixel every frame, the first try, held SwiftShader to about five frames a
  second.
- **Without WebGL 2** or a float render target the face draws the core's map plain, ink on
  the paper, and the instrument plays on (`?paint=plain` shows it). The plugin's web view,
  WebKitGTK under the shell test on a virtual display with software GL, has both: it painted
  on the graphics card path, 34 frames a second, 4.5 ms of the page's own time a frame. The
  Mac's WKWebView and Windows' WebView2 are untested here.
- **Two hands:** one canvas and a shared map, each hand's ink the look only. Enlarge and
  Picture only work as on the trace. *Which hands* is hidden in Paint, and the loop
  overlay's rings, which are the trace's Scan path, are not drawn there.
- **Presets.** The owner's rule holds as it stands in CLAUDE.md: a preset answers to its
  heading as shipped, and Paint is a change it does not contain, so no check holds a preset
  to its heading under Paint.
- **Cost.** The core as WebAssembly in Chromium, a chord of eight held (`paintcosttest.py`):
  0.43 ms a block of 128 on the trace, 0.60 painting - 0.18 ms more, 7 per cent of a block
  at 48 kHz, about 1.4 microseconds a sample, under the suite's bound of half a millisecond.
  Natively (`paint_cpp cost`, sixteen voices) about 0.35 microseconds a sample more. The
  ring reads and their tables are most of it: one ring and one table a voice a frame. The
  face's own time painting the look, on the CPU, 0.7 ms a frame with six notes laying
  strokes; the graphics card's work is asynchronous and was SwiftShader's here, about six
  frames a second with a chord - the study measured 0.7 to 2.3 ms a frame on the owner's
  card at 512 to 1000 square. The governor's model still does not count painting; at 7 per
  cent of a block for eight voices it need not yet, but a dense chord in the plugin at
  small blocks is where to look first.
- **Known limits.** The photocell and the score still read the trace's grid in Paint, which
  goes on underneath (the info line on Paint and the cheat sheet say so). The look's drying times are the owner's defaults written into the shader, not read from the
  core, since they are not settings yet.

Still open, for when the first build is seen: the drying time (the study used 1.2 s; the
owner wanted it slower, drying smoothly from thin to thick), whether a dark ground is
allowed, and whether a palette may trade separation for character.
