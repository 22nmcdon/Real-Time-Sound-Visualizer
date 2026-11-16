# Play, redesigned: three mockups

Asked for by the owner on 16 November, after the split by notes landed: the Play tab's
Keyboard section is cramped, you cannot see what the split does, and choosing feels off,
with menus inside menus. This is a mockup to look at and click, not a change to the
instrument. Nothing in `scope.html` or the core has been touched.

**The page:** [`mockups/play/index.html`](mockups/play/index.html), one self-contained
file. Open it in a browser, choose a layout along the top, and play it with the computer
keys (A to K, W E T Y U, Z and X for the octave, Space for the pedal) or the keys under
the mockup. The pictures beside it (`00-today.png` to `05-b-at-960x600.png`) are the same
layouts at 1400x900, for reading this without opening the page.

## The three complaints

The Keyboard section grew one control at a time, and it now answers three questions in
one heap:

1. **How the notes sound**: Dyad, Mono or Poly, with Hold the interval (Dyad's), Tune a
   chord (Poly's) and, until it goes, Quarter turn (Poly's).
2. **How the notes are shared between two sounds**: one sound, a split at a key (with
   Learn), a split by notes (the end, the count and, coming, the Chord window), or layered.
3. **How the notes are drawn**: Draw's outline count and which notes, and with two hands
   a figure each or A against B.

So the three complaints, each with what it rests on:

- **Cramped.** Six rows and five menus in a 254 px column. The split row is three menus
  with no label between them - *a figure each*, *lowest*, *1* - two of them answering the
  second question and one the third.
- **You cannot see what the split does.** Nothing on the face shows which hand a note
  went to; the only trace is the info line under the screen in words.
- **Menus inside menus.** Layers is a menu; choose *split* and a second menu appears
  beside it; choose *by notes* and two more replace Learn on the row below.

## What the real tab shows today (found while looking)

Opened at 1400x900 and at the plugin's 960x600 (Auto's 90 per cent), Poly, split by
notes, on `testing` at `58e62c0`:

- **Quarter turn shows in Dyad and Mono**, where it does nothing, and is ticked by
  default. It is going anyway.
- **Hold the interval shows in Mono and Poly**, where it does nothing; it is Dyad's.
- **At 960x600 the Draw menus are cut** to "2 nc" and "bass and me".
- **Tune a chord** is hidden behind the section's dots (`data-more`), so in Poly the one
  tick that acts is the one not shown, and the two that do not act are.
- **Interval** (on the Generator) shows in Poly, where chords ignore it.
- The Chord window is built at **25 ms** (`kArpGather`, `MIDI_GATHER`); the owner's coming
  change makes it 0 to 15, default 10. The mockup deals with the coming one.

## The three layouts

Each is drawn at the tab's real size - its cards and three 254 px columns at 1400x900, or
the compact 224 px columns at 960x600 at 90 per cent - with the Generator, Amp envelope
and Voice filter where they are, and measures what each column has left. The mock's own
Today measures 63 px spare in column 1 at 1400x900 against about 75 on the real face, so
its numbers are within a dozen pixels of the instrument's.

| Spare, px (column 1 · 2 · 3) | 1400x900 | 960x600 at 90% |
|---|---|---|
| Today | 63 · 185 · 413 | 30 · 141 · 323 |
| A, summary lines | 146 · 185 · 413 | 97 · 141 · 323 |
| B, only what applies | 64 · 185 · 216 | 57 · 141 · 157 |
| C, one strip | 32 · 201 · 248 | 9 · 156 · 185 |

### A. Summary lines with editors

The Keyboard section is On screen and three lines, each a button the column's width:
*Notes: Poly · 8 voices a hand*, *Hands: split by notes · lowest 1 · 10 ms*, *Figure:
outline of 2 · bass and melody · a figure each*. While there are two hands, a small live
strip sits under the Hands line: the notes held, coloured by hand. Pressing a line opens
an editor over the tab and its cards, as a modulation card's editor does, with the
question's settings on the left and a large live diagram on the right; a switch in its
head moves between the three questions; Esc or the cross closes it.

- **Notes**: Dyad, Mono, Poly as three choices with a line each, then only the chosen
  one's extra (Hold for Dyad, Tune a chord for Poly, a note that Mono's Interval is the
  Generator's). The diagram is the keys with what is held and, in Poly, eight voices a
  hand.
- **Hands**: One sound, Split at a key, Split by notes, Layered, each with a line, and the
  chosen one's settings under it (the split point and Learn; or Counted, How many as a
  row of six, and the Chord window). By notes, the diagram is the held notes stacked by
  pitch, each in the hand it was dealt, with the line a new note would be dealt by, and
  under it the last strike against time with each gather's window shaded, so a rolled
  chord shows where the window cut it. By key, the keys coloured by hand with the split
  marked: press a key to split there.
- **Figure**: Outline and Which, then a figure each or A against B; the diagram is each
  hand's notes, which make the outline and which way each leans.

Choosing a split or a layer from Dyad or Mono plays Poly. That is the merge the owner
asked about, without a menu of five.

**What it answers:** all three. Column 1 gains 83 px at 1400x900 and 67 at 960x600;
the editor has room for a diagram that plays; the choosing is one level.
**What it costs:** a press before any change, and while an editor is open the Generator
and the rest are covered (not the screen). Poly and the split, which a player might
change mid-phrase, are a press away.
**Elsewhere:** the modulation editor's own pattern, so it generalises without anything
new: Ink's oscillator extras as one line, the Picture's Advanced as three (Scan reads,
Responds to, Score), the painting Brushes panel as a line per brush. The risk is a face
of lines that say what is set and no longer show it.

### B. Only what applies, all on show

The Keyboard section is three labelled groups - *Notes, how they sound*; *Hands, how they
are shared*; *Figure, how they are drawn* - each a switch rather than a menu, and under
each only what the choice uses. Hands is a four-way switch (One, Key, Notes, Layer) with
its settings and an inline diagram beneath. Nothing opens. Expression moves to column 3
under the Voice filter.

**What it answers:** menus inside menus and seeing the split, while playing. The cramp
only partly: column 1 is as full as today (64 px spare), only better ordered.
**What it costs:** height. At 960x600 the split by notes has to fall back to two small
menus for the end and the count to fit; every new keyboard control comes out of the same
column; Expression moves away from the keyboard it describes.
**Elsewhere:** a rule rather than a layout - group by question, show only what applies -
which every dense section could follow without a new mechanism. It runs out where more
applies at once than fits: the Picture's Advanced, and likely the Brushes panel.

### C. One strip (my own)

The mode and the hands are one choice of five - **Dyad · Mono · Poly · Split · Layered** -
in a band across the top of the tab, and beside it a strip that is the diagram and the
control at once: by key, press a key to split there; by notes, the strip is eight places
from the counted end, the counted ones tinted, and pressing a place sets how many. The
hands' settings and the figure's are the band's two short lines under it. The three
columns below: Expression and the Amp envelope, the Generator, the Voice filter.

**What it answers:** menus inside menus most directly, and seeing the split, since
setting it is watching it. The cramp by spreading across the tab's width.
**What it costs:** the band's height out of every column, so the Amp envelope leaves the
Generator for column 1, 9 px from over at 960x600. Five modes hide that a split is Poly
with two hands, which the sections' links (*Same in both*) and the header's *Editing*
still assume. *At a key · by notes* is still a second choice, though on show. A host
sees one parameter where there were two, or the two stay and the five is only the face.
**Elsewhere:** good where a section has a picture that can be its control - the Amp
envelope's drawing, the drawn cycle, the Plane, a brush's stroke; no help for sections of
plain values.

## Recommendation

**A, with B's rule inside each editor and C's strip as the Hands line's drawing.** A is
the only one that frees column 1 at both sizes, it reuses the editor the face already has
(so the fit tests, the right-click menu and the plugin's panel have a precedent to
follow), and it is the one that generalises to the other dense places. B's rule - only
what applies, grouped by question - is what each editor shows. C's strip is right as the
small drawing under the Hands line, and pressing it opens the editor; it is wrong as a
band, which pays for itself out of the Generator and the Voice filter.

Do not merge the mode and the hands into one menu of five. Make choosing a split or a
layer play Poly, as A does: it gives the merge's one click from Dyad to a split, and keeps
the structure the hands' links, the header and the host parameters rest on.

The one thing A gives up is Poly and the split on the face for a mid-phrase change. If
the owner finds that missed, the Notes line can be a three-way switch in place (Dyad ·
Mono · Poly fits a column) with only Hands and Figure as lines.

## What building A would touch

- **`scope.html`, `#midiGroup`**: the rows become three summary buttons and the mini
  strip; the controls themselves (`midiDyad`/`Mono`/`Poly`, `midiLayers`, `midiSplitBy`,
  `midiSplitLearn`, `midiSplitEnd`, `midiSplitCount`, the coming Chord window, `midiLayerPair`,
  `midiDrawCount`, `midiDrawWhich`, `midiPolyJust`, `midiHold`) are written once outside
  the editor and **moved into it while it is open**, as the Envelope's controls are, so
  their ids resolve from the start for the plugin's panel, the morph and every test that
  writes them. Controls are moved, never copied (CLAUDE.md). The editor is the
  `.mod-editor` panel over the tabs, with the question's controls in its first column
  and the diagram in its second. `showControl(id)` opens the editor holding the id.
- **The setup does not change.** `layers`, `splitBy`, `splitEnd`, `splitCount` and the
  rest keep their fields; the four-way Hands choice is a view over `layers` and `splitBy`
  (one, split by key, split by notes, layered), as the rack's switch is a view over its
  Mix. No version bump, no decode pass, nothing in `SETUP_FIELDS` or the core's schema,
  unless the Chord window lands as a field (additive, its own change).
- **The face's mirror of the dealing** (`midiDealt`, `layerHandOf`) already knows each
  note's hand, so the diagrams read it; nothing new is dealt in the page.
- **Tests.** `fittest.py` measures Play with the split by notes and must measure each
  editor open, at the five windows, in each mode (the editor's first column must not
  scroll). `patchtest.py`'s Play-height check and every-tab sweep get the new rows.
  `benchtest.py`: the editor's controls keep `data-home="bench"`. `layouttest.py` and
  `layertest.py` write `midiLayers` and `midiSplitBy` and should keep working through the
  moved selects; `layertest.py` could also read the diagram's hands against the
  instrument's lanes. `ringtest.py`: the right-click menu on a control inside the editor.
  `headertest.py` if the header's *Editing* is linked from the Hands editor.
- **The info line's words** (`what-each-control-says.md`, then `write_words.py`): three new
  rows for the summary lines and one for the editor's question switch; Quarter turn's row
  goes; Draw's line loses "outline notes lean ... and still sound in both ears", since
  Width will set each note's heard width and the lean is only the picture; Layers' line
  becomes the Hands choice's.
- **The cheat sheet** in `scope.html`: the Keyboard paragraph.
- **The plugin face**: the same page, so nothing of its own, but its shell test opens the
  real face under `xvfb-run -a`, and the editor has to fit the plugin's 960x600, which the
  mockup measures as fitting with room (its first column fits at both sizes).

## How the mockup was checked

The dealing is the instrument's rules (`split-by-notes.md`), held by
`mockups/play/check-dealing.js` (`node web/docs/mockups/play/check-dealing.js`): ten cases -
rank against fill (A2 under C3 E3 G3), fixed at start against re-sorting, a chord struck
top first within the window, the same with a window of nought, the window half open at
10 ms and timed from the first note, the pedal, Highest and the key split. Seen red
against two mutants of the mockup: fill in place of rank (five cases fail) and a window
sliding with each note (one fails). Opened in Chromium at both sizes in every layout, with
each editor open, in the page's dark light, and at 375 px wide (no sideways scroll; the
mockup scales down). `designtest.py` reads only `scope.html` and `DESIGN.md`, neither
changed, so it has nothing new to read; the mockup uses DESIGN.md's tokens hex for hex.
