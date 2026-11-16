# Play, redesigned: three mockups

Asked for by the owner on 16 November, after the split by notes landed: the Play tab's
Keyboard section is cramped, you cannot see what the split does, and choosing feels off,
with menus inside menus. This is a mockup to look at and click, not a change to the
instrument. Nothing in `scope.html` or the core has been touched.

**The page:** [`mockups/play/index.html`](mockups/play/index.html), one self-contained
file. It opens on round 4's layout F (below); round 1's Today, A, B and C, round 2's D and
round 3's E are kept beside it for reference. Open it in a browser, choose a layout along the top, and play it with the computer
keys (A to K, W E T Y U, Z and X for the octave, Space for the pedal) or the keys under
the mockup. The pictures beside it (`00-today.png` to `14-f-by-notes-at-960x600.png`) are the same
layouts, for reading this without opening the page.

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
- The Chord window was built at **25 ms** (`kArpGather`, `MIDI_GATHER`) when round 1 was
  drawn; it is now the look-ahead, 0 to 15 ms, default 10, which the mockup deals with
  since round 2 (below).

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

## Recommendation (round 1; the owner's verdict on it is under Round 2)

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

## Round 2: the owner's verdict, and D

### The verdict on round 1 (16 Nov)

- **Keep:** A is the right idea in general, with B's rule (only what applies) inside it.
  The Notes switch, Dyad · Mono · Poly, as C has it, always on Play at the top of the
  Keyboard section - but not Split and Layered in it. The keyboard strip always visible
  in Poly (the room A frees), live, and a control as C's is: press a key to split there,
  press a place to set the count.
- **What was wrong with A**, all three: too many clicks; the editor covers too much,
  hiding the Generator, envelope and filter; and the editor's own layout, wordy option
  cards and the options-left, diagram-right split. The owner's suggestion, not certain:
  "a toggle overlay instead of a popup menu, then you can toggle to access different
  things" - read as the deeper settings opening inside the Keyboard's column, chosen by a
  small toggle, never covering the other columns, compact switches rather than cards,
  one click to anything common.

### D, the mix

The Notes switch on top; under it the strip, always there, live, and a control; under
that the deeper settings, in column 1 only. Two choices on the page, independent of each
other, for the owner to feel:

**How the settings open**

1. **Switch**: a small segmented switch, *Hands · Figure · Expression* (no Hands outside
   Poly), swapping one panel in place under the strip.
2. **Accordion**: each group's header is a line with its value (A's summary line, opened
   in place), one open at a time.
3. **Drawer**: *More: Hands · Figure* under the strip; the drawer slides over column 1
   only, from under the strip, with its own switch and a close; Expression stays in the
   column under it when shut.

**Where the hands choice, One · Key · Notes · Layer, lives**

- **(a) Above the strip**, a small switch, Poly only.
- **(b) In the strip's corner**: the strip is a box with the choice in its head, so they
  read as one object.
- **(c) In the Hands panel**, the strip only showing the result (and no longer a control).

What each panel holds, only what applies: Hands - the split point and Learn by key; by
notes, Counted (lowest · highest), How many (only in (c), since otherwise the strip sets
it) and the Chord window. Figure - Outline (count and which), with two hands *Each* or *A
vs B*, and Tune a chord in Poly; Hold the interval in Dyad; nothing in Mono. Expression -
its four menus.

**The Chord window as now built** is the look-ahead: by notes, every note waits the window
(0 to 15 ms, default 10), and the notes within it are dealt together, by pitch, before any
sounds, so nothing is ever moved and there is no "moved in its gather". At 0 there is no
wait and dealing is strict. The mockup shows a waiting note grey, and the strike lane under
the strip shows the window against where your notes landed. (A note let go before its
window closes is dropped unheard in the mockup; what the instrument does with it is the
core's.)

### Fit, every combination

The page's *Measure every combination* runs D at both windows, each toggle and each place
of the hands choice, through Dyad, Mono, Poly alone and Poly with each hands choice, with
every panel open in turn, and reports column 1 at its tightest (always Poly split by
notes, with the most open). Columns 2 and 3 are as today in every case (185 and 413 px
spare at 1400x900, 141 and 323 at 960x600).

| Column 1, tightest, px spare | Switch | Accordion | Drawer (column; drawer itself) |
|---|---|---|---|
| 1400x900, (a) above | 145 | 66 | 105; fits |
| 1400x900, (b) corner | 138 | 59 | 98; fits |
| 1400x900, (c) panel | 180 | 101 | 139; fits |
| 960x600 at 90%, (a) above | 89 | 3 | 58; fits |
| 960x600 at 90%, (b) corner | 80 | **over by 7** | 49; fits |
| 960x600 at 90%, (c) panel | 120 | 34 | 89; fits |

Against Today's 63 and 30. The accordion pays a line per header whether open or not, and
at the plugin's minimum with the corner box it does not fit.

### The three toggles, each in three lines

**Switch.** *Answers:* one press reaches anything, nothing is covered, columns 2 and 3
never move. *Costs:* one panel at a time, so the Chord window is out of sight while you
set the outline; what sits under the panel changes height with it (here nothing does).
*Elsewhere:* the tab cards one level down - Ink's oscillator extras (FM · Sync · Noise),
the Picture's Advanced (Reads · Responds · Score); not where two panels are wanted at once.

**Accordion.** *Answers:* every group says its value in its header while one is open, one
press for anything. *Costs:* a line per header always, the least room (over at 960x600
with the corner box); opening one moves the headers under it, the movement under the
pointer the Bench's real columns were built to avoid, though here it follows the
pointer's own press. *Elsewhere:* sections whose groups are worth naming with their
values - Routings, a brush's settings; a long list runs out first in a column that may
not scroll.

**Drawer.** *Answers:* the strip and Expression stay the column's resting face; the
settings slide over column 1 only and the Generator, envelope and filter stay in view.
*Costs:* two presses (the word, then the drawer's own switch), Expression hidden while it
is open, and a second place with a close. *Elsewhere:* the modulation editor a column
wide - good for settings visited in a sitting (the Brushes panel, the score), poor for
something tweaked while playing.

**The hands choice:** (a) above reads as two rows that belong together and keeps the
strip a control; (b) the corner makes strip and choice one object for a box's border and
a row inside it, and is the tightest; (c) in the panel is the quietest column (most room)
but puts choosing a split one press away and stops the strip being a control.

### My lean, for the owner to overrule by feel

**The switch, with the hands choice above the strip (1a).** It is the one press the owner
asked for, it fits everywhere with room (145 and 89 px), and it keeps the strip a control
with its choice next to it. (1b) if the strip and its choice should read as one object;
it costs 7 to 9 px. The accordion is out at the plugin's minimum unless its headers lose
their values.

### What building D would touch, beyond A's list above

The same moves as A, without the editor: the Keyboard section's controls stay in its
column and are shown or hidden by the toggle (moved into the panel's place while it is
the open one, never copied); the strip is the face's mirror of the dealing (`midiDealt`),
drawn and pressed; `fittest.py` measures every panel open at the five windows;
`patchtest.py` gets the switch's rows; `layertest.py` presses the strip; the info line
gets the strip's and the toggle's words.

## Round 3: E, the strip is the Hands section

The owner's call on D (16 Nov): the switch (1), with the hands choice in the strip's box
(b), and six changes. E is D with them:

1. **The strip is the Hands section.** No Hands panel. The hands choice sits in the
   strip's box, in its top edge, centred.
2. **Octave buttons** ‹ › at the strip's two ends, so any key can be the split point;
   the strip keeps its width and shows two octaves at a time (the line under it names
   them, *C3–C5*), and a gold dot on a button says a held note is out of view that way.
3. **One sound is not in line with Key · Notes · Layer.** Two treatments, selectable on
   the page:
   - **(i) Two hands, on or off**: a small pill in the strip's head; off is one sound and
     the strip shows plain held notes; on reveals *Key · Notes · Layer* beside it.
   - **(ii) Only Key · Notes · Layer**: none lit is one sound, and pressing the lit one
     again goes back to it; the line under the strip says so while none is lit ("One
     sound. Press Key, Notes or Layer for two hands; the lit one again for one").
   Either way, choosing two hands from Dyad or Mono plays Poly.
4. **Which end is counted** is on the strip, by notes only: a small *low · high* toggle
   at the strip's edge, on the counted side. Chosen over pressing the end you want
   counted from, because a press on a place already means *how many*: a press on an end
   would mean two things, and the second (which end) would be invisible until it
   happened. The toggle also says, where the count starts, what the places alone do not.
5. **The Chord window is not on Play.** By notes, one line under the strip: *Chord window:
   10 ms, in Settings* (Settings › MIDI). In the mockup *in Settings* opens a stand-in
   slider so the dealing can still be played with; the fit is measured with it shut,
   since it is not a row of the face.
6. **The panel switch is Figure · Expression only** (Figure: outline count and which,
   *Each · A vs B* with two hands, Tune a chord; Hold in Dyad. Expression: bend, wheel,
   pressure, velocity). Where Expression lives is selectable, and measured.

### Fit, every combination

Columns 1 and 3 at their tightest across Dyad, Mono, Poly alone and each hands choice,
each panel open (column 2 is today's: 185 px spare at 1400x900, 141 at 960x600). The
two treatments of one sound measure the same: both are one row in the strip's head.

| | Expression in the switch | under Figure | in column 3 |
|---|---|---|---|
| 1400x900, column 1 | 132 | **over by 6** | 191 |
| 1400x900, column 3 | 413 | 413 | 216 |
| 960x600 at 90%, column 1 | 69 | **over by 47** | 119 |
| 960x600 at 90%, column 3 | 323 | 323 | 157 |

So Expression **in column 3**, under the Voice filter: it is the only home where
everything on Play is on show at once and fits with room at both sizes. Column 1 then
holds only the keyboard's three questions, and the Figure · Expression switch goes - no
switch is left on Play but the Notes switch and the hands choice. Under Figure does not
fit. The switch fits too, if the owner would rather keep Expression next to the keyboard
and pay a press for it. E opens with Expression in column 3.

### The three lines, for E as drawn (Two hands, Expression in column 3)

**Answers:** every common thing is one press - the strip is the Hands section, its
choice in its head, ‹ › for any split point, the counted end at its edge, the places for
how many; the Chord window is a note, since it is set once. Nothing opens over anything.
**Costs:** (i) is one more press from one sound to a split, and two controls in the head
while on; (ii) makes one sound no button's state, which its line has to teach. The strip
shows two octaves, so a split point or held note elsewhere is behind ‹ ›. Expression
moves away from the keyboard it describes.
**Elsewhere:** a drawing that is its section, with its choices on its edges, fits
wherever the thing has a picture - the Amp envelope's curve, the drawn cycle, the Plane,
a brush - and a switch over one panel the plain values (Ink's extras, the Picture's
Advanced).

### My lean

(i) **Two hands** on or off: one sound is a named state and the three kinds only appear
when they mean something, and it costs nothing in height. (ii) is quicker by one press
and the owner may prefer it by feel; its hint is the cost. Expression in column 3.

### What building E would touch, beyond A's and D's lists

The strip replaces `midiLayersRow` and `midiLayerRow`: the hands choice drives
`midiLayers` and `midiSplitBy` (one, split by key, split by notes, layered) as a view, the
octave buttons are the strip's own view state (not stored), the end toggle drives
`midiSplitEnd`, and the places `midiSplitCount`. The Chord window moves to Settings ›
MIDI (`data-home="settings"`), which `benchtest.py` checks; Expression's
`data-col` moves to 3, and the Play fit in `patchtest.py` and `fittest.py` changes with it.
Learn goes: a press on the strip is the learn, and ‹ › reach any key, though playing the
split key on a keyboard was Learn's one advantage and could stay as a long press.

## Round 4: F, the Keyboard as a band

The owner on E (16 Nov): "E is definitely the right move." F is E with four changes.

1. **The Keyboard is a band** across the top of the tab's body, a row of its own over
   all three columns, as C's was, so the strip is wide. In it: the Keyboard's name, the
   Dyad · Mono · Poly switch and *keys on screen*, stacked on the left; on the right the
   strip's box with the hands choice centred in its top edge and ‹ › at its ends, the
   line under it, and by notes the *Chord window: 10 ms, in Settings* note on the same
   line, right-aligned; the low · high toggle at the counted edge and the places for how
   many as in E.
   A first band put the Keyboard's title on a row of its own, the switch under it beside
   the strip and the line under both: 209 px tall at 1400x900, and the Voice filter's
   column 25 px over at 960x600. Stacking the name, the switch and the keys link in the
   left column, which the strip's height leaves empty anyway, took 31 px off.
2. **How many octaves.** Beside the switch the strip has 586 px at 1400x900 and 494 at
   960x600. Four octaves are 29 white keys: 20 px each at 1400x900, 17 px at 960x600.
   Three are 22 keys, 22 px at 960x600. So **four at 1400x900, three at 960x600**, the
   keys never under 20 px, with ‹ › for the rest and the range named in the line.
   (Across the band's whole width, five would fit at 1400x900, but the switch beside the
   strip is worth more than a fifth octave.)
3. **Two hands only in Poly.** In Dyad and Mono the box has no head: the strip shows what
   is held, the two newest ringed in Dyad (X and Y, named in the line with their
   interval), the newest in Mono.
4. **Expression is column 1.** Figure (outline count and which, Each · A vs B with two
   hands, Tune a chord; Hold in Dyad) has two homes, selectable: (a) a line under the
   strip in the band; (b) column 1, a section under Expression. The Amp envelope's home
   is selectable too: under the Generator as today, or under the Voice filter.

### Fit, every combination

The band's height (its tallest, over every mode and hands choice) and each column's
tightest spare, in px:

| | Band | Column 1 | Column 2 | Column 3 |
|---|---|---|---|---|
| 1400x900, Figure in the band, Amp under the Generator | 178 | 183 | **over by 9** | 219 |
| 1400x900, Figure in the band, Amp under the Voice filter | 178 | 183 | 171 | 39 |
| 1400x900, **Figure in column 1, Amp under the Generator** | 139 | 74 | 30 | 258 |
| 1400x900, Figure in column 1, Amp under the Voice filter | 139 | 74 | 210 | 78 |
| 960x600 at 90%, Figure in the band, Amp under the Generator | 158 | 131 | **over by 28** | 154 |
| 960x600 at 90%, Figure in the band, Amp under the Voice filter | 158 | 131 | 125 | 2 |
| 960x600 at 90%, **Figure in column 1, Amp under the Generator** | 125 | 36 | 5 | 187 |
| 960x600 at 90%, Figure in column 1, Amp under the Voice filter | 125 | 36 | 158 | 35 |

The tightest state is always Poly with two hands (the box's head and the longest line).

### My lean: Figure in column 1 (b)

With Figure in column 1 nothing else moves: the Generator and Amp envelope keep column 2
and the Voice filter column 3, as today, and everything fits at both sizes. The band is
39 px shorter, and column 1 holds the two sections about how the notes are played and
drawn, Expression and Figure, where the owner said there was room. Figure in the band
keeps everything about the notes in one place across the top, but only fits if the Amp
envelope leaves the Generator for the Voice filter's column, and then with 2 px at the
plugin's minimum.

The tightest number in the lean is column 2's 5 px at 960x600, and the mock is within
about a dozen pixels of the face. If the built face comes out over there, the smallest
change is the Amp envelope moving under the Voice filter (35 px spare in every column
at 960x600), which is the selector's other setting. The next smallest is the strip's
height at the compact size (40 px now; 34 takes 6 px off every column).

### The three lines, for F as leaned (Figure in column 1)

**Answers:** the strip is the width of the tab less the switch, four octaves at once with
keys a fingertip wide, so a split point is one press; the hands choice is Poly's only,
so Dyad and Mono show only what is held; every column keeps today's sections or gains
room. **Costs:** the band's 125 to 139 px come out of all three columns; Expression and
Figure, which a player sets and leaves, are the column nearest the keyboard, while the
Generator they used to sit beside is the middle. **Elsewhere:** a band is the shape for a
thing played across - the keys now, a score or a step row later - with the sections of
plain values as columns under it.

### What building F would touch, beyond E's list

`#midiGroup` leaves the column flow for a row of its own over the Bench's three columns on
Play (`data-col` gives way to a band), which `layouttest.py`, `patchtest.py` and
`fittest.py` read; Expression keeps `data-col="1"` and a Figure section (the Draw menus,
the pairing and Tune a chord, out of `#midiGroup`) joins it. The strip's octave count
follows the compact face (`setCompact`).

## How the mockup was checked

The dealing is the instrument's rules (`split-by-notes.md`), held by
`mockups/play/check-dealing.js` (`node web/docs/mockups/play/check-dealing.js`): eleven
cases - rank against fill (A2 under C3 E3 G3), fixed at start against re-sorting, a chord
struck top first within the window, the same with a window of nought, the window half open
at 10 ms and timed from the first note, the look-ahead (nothing dealt before the window
closes), the pedal, Highest and the key split. Seen red against three mutants of the
mockup: fill in place of rank (five cases fail), a window sliding with each note (one
fails) and dealing each note as it lands (the look-ahead's case fails). Opened in Chromium at both sizes in every layout, with
each editor open, D in every toggle and place of the hands choice, E in both treatments
of one sound and every home for Expression, F with both homes for Figure and for the Amp
envelope, in the page's dark
light, and at 375 px wide (no sideways scroll; the
mockup scales down). `designtest.py` reads only `scope.html` and `DESIGN.md`, neither
changed, so it has nothing new to read; the mockup uses DESIGN.md's tokens hex for hex.
