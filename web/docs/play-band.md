# The Keyboard band with room, and Wave as the Generator

The build's spec for the owner's notes on testing (19 Nov, a screenshot at about 1700x1035, Two
hands on, split by notes, shape S&H). The mockup is `web/docs/mockups/play-band/` (live, with its
screenshots and `checks/play_band_checks.py`). It changes the band, the row under it and Wave's
header; the figures are `play-figures.md`'s, as built, and unchanged.

It acts on the loop (`making-it-one-instrument.md`) as the band always has: which hand a note goes
to is which figure it draws. The owner could not see that by notes, because the keys were replaced
by boxes; now the keys say it.

## The owner's notes, and the answers

1. **The Generator into Wave.** Shape, Glide, Interval and Level are Wave's header, each name
   beside its control on one line, with the link pill and the dots (Tuning, Reset, Copy to the
   other hand) at its end. The header is no taller than Amp's and Filter's, so the cycle keeps its
   size. Then the cycle, then the shape's own band (78 px), as built. Wave's summary is unchanged:
   the shape and its main setting (*pulse 25%*, *drawbars 008740000*).
2. **The band's two-hands area.**
   - *Key · Notes · Layer* was clipped by the strip's top edge. It now leads a **split row** of its
     own over the strip, the right column's first row. Nothing is laid over the keys in any state.
   - By notes the keys were replaced by six places. **The keys stay**, and each held note is
     numbered from the counted end on its own key (below).
   - *low · high* was a squeezed pill at the strip's left. It is *Lowest · Highest*, a two-way
     switch in the split row, each button one width.
   - The hint and *Chord window … in Settings* crowded one line. The line is one sentence now;
     *Learn* and the *Chord window* have places in the split row.
3. **The room under the keyboard.** The band is taller and the keys take all of it.

## The band

A grid of two columns and three rows, at **one height in every state**: 150 px on the full face,
130 compact (from 122 and 117). Columns 216 px and the rest, 16 apart (196 and 12 compact); the
left column was 236, and the 20 px it gave are what let the split row fit at 1100x860.

| | Left column | Right column |
|---|---|---|
| Row 1, 24 px (22 compact) | *Keyboard*, the *Two hands* pill, the dots | **The split row** |
| Row 2, the rest | Dyad · Mono · Poly, then what the mode uses: Hold (Dyad); a line (Mono); Outline, *Tune a chord* and with two hands the pairing (Poly) | **The keys**, three octaves, the column's whole width |
| Row 3, 18 px (16 compact) | (the left column runs on) | **The line**: one sentence, and the strip's octave, *‹ C3 – B5 ›*, at its right end |

- **The split row** is kept, unseen (`visibility: hidden`), with one hand and in Dyad and Mono, so
  choosing Two hands moves nothing. Its contents never shrink: what does not fit is seen not to.
  - *Key · Notes · Layer*, then the chosen way's own:
  - **Key**: *Split at C4*, in a box one width (C4 and C♯4 differ, and the check caught Learn moving
    with it), then *learn from a key* (*now play a key* while it waits, in the same width; the
    plugin's way from a host's note).
  - **Notes**: *Lowest · Highest*; how many, six numbered places, 1 to 6, so the count can be
    chosen with nothing held; and at the row's right end *Chord window 10 ms*, which says it is
    Settings' (MIDI) and goes there.
  - **Layer**: *Both hands, every note*.
  - The small switch size at every window (2 px by 8, 9.5 px type), as `.switch.mini` is.
- **The keys** are drawn at the strip's own size (a stretched viewBox squashed the names), the same
  36 keys in the same places in every way of sharing:
  - one hand: plain, the notes held in the lower hand's ink;
  - Key: each side washed in its hand's ink, the point a rule, the notes held in their hand's ink;
    pressing a key splits there;
  - **Notes: plain keys** (no key belongs to a hand by notes), each held note in the ink of the hand
    it was dealt to, **numbered from the counted end** (1 the lowest, or the highest; to 6), the
    counted ones' numbers on a paper disc in their hand's ink, and a dashed rule at the first
    uncounted note's edge;
  - Layer: faintly washed, a note held half in each hand's ink.
- **The octave buttons stay in every way of sharing**, in the line. By notes they used to give way
  to *low · high*, which cost 40 px of keys in every split; the keys are scrolled by notes too now.
- **The line's sentence fits on one line at every window** (`hintText`): *Under C4 the lower hand,
  C4 and up the upper. Press a key to split there.*; *The highest 6 notes held: the upper hand; the
  rest the lower.*; *One sound. Two hands, in the heading, gives a second.*; and Dyad's, Mono's and
  Layer's. The tightest is 71 px to spare at 1100x860.
- **No “to the lower hand” in the split row.** It repeated the line, and it was the 115 px the row
  did not have.

In the build the menus that hold the values (`midiLayers`, `midiSplitBy`, `midiSplitEnd`,
`midiSplitCount`) stay out of sight, driven by the switches' change events, as now.
`stripPlacesSvg` goes; `stripKeysSvg` gains the numbers and the rule by notes.

## Expression, alone

One row under the band: its title (and dots) in the band's left column with a line of what it is
(not compact), its four menus across the right, each name in small type over its control. 47 px
tall (40 compact), from 67 (60). Its menus have far more room than in half a row; the shortened
values (`play-figures.md`) stay.

## Measured

In the page's own pixels, in the brand's webfonts, two hands by notes with a chord held.

| Window | Band | Keys | Split row spare | Line spare | Expression | Figure area | Amp | Filter's two | Wave's cycle |
|---|---|---|---|---|---|---|---|---|---|
| 1660x1050 | 150 | 598x84 | 99.5 | 194.9 | 47 | 830x493 | 802x359 | stacked 802x124, 802x120 | 802x339 |
| 1400x900 | 150 | 598x84 | 99.5 | 194.9 | 47 | 830x343 | 802x209 | 384x189, 384x185 | 802x189 |
| 1100x860 | 150 | 510x84 | 11.5 | 106.9 | 47 | 742x359 | 714x225 | 340x205, 340x201 | 714x205 |
| 1200x680 | 130 | 622x75 | 156.8 | 181.4 | 40 | 830x285 | 810x166 | 394x151, 394x143 | 810x144 |
| 1100x680 | 130 | 534x75 | 68.8 | 160.9 | 40 | 742x285 | 722x166 | 350x151, 350x143 | 722x144 |
| 960x600 | 130 | 501x75 | 35.8 | 127.9 | 40 | 709x271 | 689x152 | 333x137, 333x129 | 689x130 |

Testing's keys are 44 px tall (36 compact). The figure area is within 8 px of `play-figures.md`'s
on the full face and 7 larger compact. Every drawing holds the floors: 1.5:1 to 7:1, the amp's 2:1
or wider, none under 120 px. **The tightest is the filter's envelope stacked at 1660x1050, 120 px
exactly**; 10 px less band would buy it back. Play does not scroll at any window; 960x600 needed
nothing to give.

## Nothing moves

`play_band_checks.py` compares every box on Play to half a pixel (the band, its heading, the split
row and each thing in it, the keys, the line, the octave; Expression and each field; the figure
area, its bar, subtabs and the view's header, tools, drawings and knobs) across: Poly, Dyad, Mono;
one hand; two by Key, Notes and Layer; each count 1 to 6 from either end, a chord held or none;
Learn waiting; the split moved; an octave up; all fourteen Wave shapes; and the subtabs, at all six
windows. Its nulls, each seen to fail: the band 6 px taller with two hands; the octave buttons taken
out by notes; *Key · Notes · Layer* on the strip's edge; testing's Notes row and testing's line put
back; places drawn off their keys; a Wave band sized to its shape; Wave's names over their controls.
249 checks.

`striptest.py`, `patchtest.py`, `fittest.py` and `msegtest.py` take the same: the keys shown by
notes and numbered on held keys; the split row and the line not cut; the band's one height; Wave's
header holding the Generator.

## As built (19 Nov)

Built as the mockup shows, with the owner's three leans: the keys 10 px shorter than mocked (a band of
140 px, 120 compact), the six numbered places, and the Chord window in the split row by Notes.
Measured on the page in the brand's webfonts, two hands by notes with a chord held:

| Window | Band | Keys | Split row spare | Line spare | Expression | Figure area | Amp | Filter's two | Wave's cycle |
|---|---|---|---|---|---|---|---|---|---|
| 1660x1050 | 140 | 596x74 | 97.6 | 194.7 | 47 | 830x503 | 802x375 | stacked 802x128, 802x128 | 802x350 |
| 1400x900 | 140 | 596x74 | 97.6 | 194.7 | 47 | 830x353 | 802x225 | 384x197, 384x197 | 802x200 |
| 1100x860 | 140 | 508x74 | 9.6 | 106.7 | 47 | 742x369 | 714x241 | 340x213, 340x213 | 714x216 |
| 1200x680 | 120 | 620x65 | 155.2 | 248.8 | 40 | 830x295 | 810x186 | 394x158, 394x154 | 810x155 |
| 1100x680 | 120 | 532x65 | 67.2 | 160.8 | 40 | 742x295 | 722x186 | 350x158, 350x154 | 722x155 |
| 960x600 | 120 | 498x65 | 33.7 | 99.0 | 40 | 709x281 | 688x171 | 333x143, 333x139 | 688x140 |

So the 10 px bought the stacked filter back 8 px over its 120 px floor at 1660x1050, and every other
drawing 10 px; the keys are 74 tall (65 compact), from testing's 44 (36). Play does not scroll at any
window. Where the build differs from the mockup, and why:

- **The keys are C3 to B5**, thirty-six, as mocked; testing drew the C above as well.
- **Key · Notes · Layer and Lowest · Highest are mixed case**, as mocked. In the page's capitals the
  split row was 13 px wider and cut at 1100x860.
- **The pairing menu says *each* and *A vs B*** (its options' titles the full names), as mocked; its
  long names wrapped *Tune a chord* in the compact left column.
- **The Generator is moved into the Wave view, not rewritten into it.** It keeps its section, its
  title (words unseen), its link and its dots; the Wave figure's own title and its second link
  (`linkGenWave`) stand aside, and what its dots said is in the Generator's.
- **The numbers on the keys are each note's place by pitch, in the ink of the hand it was dealt
  to.** The two agree once a chord has landed; for a Chord window while it lands they can differ.

`patchtest.py` holds every box on Play to half a pixel across 42 states of the band at each of the
six windows, and in each the line on one line, the split row uncut and nothing over the keys, with
testing's ways as its nulls (the octave buttons taken out by notes, Key · Notes · Layer on the keys'
edge, the split row narrower than it holds, testing's line, the split point's reading at its own
width, a Wave band sized to its shape, the Generator's names over their controls); and every Wave
shape. `striptest.py` holds the places, the numbers on their keys and the rule, with theirs.
