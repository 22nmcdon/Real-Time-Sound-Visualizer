# Play with its figures full width

The build's spec for Play after the drawn envelopes (18 Nov). The owner
approved the direction from the mockup, `web/docs/mockups/play-figures/`
(live, with its screenshots and checks), and this is what the build must do.
It replaces the small blocks and the popover of `mseg-design.md` ("The chosen
design"). The drawing, the curve law and the stored shape are unchanged.

It acts on the loop (`making-it-one-instrument.md`'s first rule) the way the
drawn envelopes do: the amp envelope is how a note strikes the screen and
comes to rest. This only gives that drawing the room to be read, so an 8 ms
attack is a slope 62 to 74 px wide again rather than the popover's 17 px wall.

## What Play is

Three things, top to bottom, in a column. Nothing is dealt into columns any
more, so nothing can stretch between them.

1. **The Keyboard band**, as built (17 Nov, `play-redesign.md`), at one
   height whatever the mode or the hands (below).
2. **The settings row**, 8 px under the band (6 on the compact face): two
   sections side by side. On the left, *Expression*'s four menus (Pitch bend,
   Mod wheel, Pressure, Velocity). On the right, the *Generator*'s Shape,
   Glide, Interval and Level. Each control has its name in small type over it.
   The columns are weighted to what they hold: Expression 0.86 · 0.9 · 0.9 ·
   1.34, Generator 1.3 · 0.75 · 1.3 · 0.75. The row is 67 px tall (60
   compact). Each section keeps its dots menu at the right of its title, and
   the Generator keeps its link pill after its name.
3. **The figure area**: the rest of the tab, a paper sheet with a bar of two
   subtabs along its top, **Amp** and **Filter**. The chosen one's view is
   shown under the bar, and the two views stack in the same place.
   - **Each subtab's label is its name and a one-line summary**: *Amp · 8 ms
     · 120 ms · −3.1 dB · 180 ms* (attack, decay, sustain, release; *one
     shot* for the sustain of a one-shot) and *Filter · low pass 1.6 kHz ·
     +1.5 oct* (*off* when off). Shorter forms are ready: drop the decay, then
     the sustain; for the filter, drop the sweep, then the type. The first
     that fits is shown. At the six windows below none was needed.
   - **Amp**: a header with *Shape…*, *Loop* and *Hold a note* on the left,
     and the link pill and the dots at its right end. Under it, the drawing
     across the full width, then the six knobs in one row (Delay, Attack,
     Hold, Decay, Sustain dB, Release; the gold dot on Attack and Release, the
     host knobs). On the full face a line of the gestures sits beside the
     knobs.
   - **Filter**: a header with the type switch (Off · Low · Band · High ·
     Notch) and *Hold a note*, and the pill and dots at the right end. The
     response with its four knobs (Cutoff, Resonance, Key track, Amount) and
     its envelope with its six, **side by side, unless stacking them leaves
     each drawing at least 120 px tall**. That is decided by room, as
     `fitRack` folds the rack, not by window size. Of the six windows only
     1660x1050 stacks (802x128 each). Stacked anywhere else, the drawings are
     30 to 61 px tall and Play scrolls at 960x600.

The drawing is round 3's as chosen and as built: straight amplitude,
square-root time, three level lines, round handles, the soft fill, the
dotted sustain run to a *key up* tick, Delay and Hold as gold rings, and the
right-click menu with *Sustain here*, *No sustain: play through*, *Sustain at
the decay's end*, *Loop from here while held* and *No loop*. In the mockup
its level matches round 3's to 1e-12 for every shape whose sustain was not
moved.

### The Envelope is a modulation source, not a subtab

The Envelope card's editor opens **over the tabs**, as the LFOs' do. It
covers the bench from the tab cards to the tab's foot, at its full width, and
is drawn in the same style as the figures.
- **Along the top**: the head (its sage dot, *Envelope*, a line of what it
  is, *Close*), then a line of tools: whether it follows the amp envelope,
  *Follow*, *Each phrase · Every note*, *Shape…*, *Loop*, *Hold a note*.
- **The drawing** is the editor's width and held at 2.4:1 (2.6:1 compact),
  with its six knobs under it.
- ***Where it goes*** takes the rest of the height and scrolls inside itself
  past what fits.

It follows the amp envelope until edited (`menvAdopt`, `knobShows`, as
built): dashed and grey while following, solid in sage once its own.

Its two columns, as the LFOs' editors are laid out, were measured and
rejected: at the bench's height the drawing beside *Where it goes* is a tower
again (588x630 at 1660x1050). If the owner wants the four cards' editors
alike, the cost is that, or a capped drawing with empty paper under it.

Pressing the card again, *Close* or Esc shuts it. Play under it does not
move.

## Nothing moves when anything is selected

The owner's rule (18 Nov), stated generally: selecting something must not
shift the view. On Play that means:

- **Two hands is the pill in the Keyboard heading**, beside the name, as
  `play-redesign.md` describes. On testing it is not inside the pill. It
  shows in Poly only; in Dyad and Mono it keeps its place unseen
  (`visibility: hidden`, not `hidden`), so the heading does not reflow.
  Choosing two hands from Dyad or Mono plays Poly, as before.
- **The band is one height**: the page's one-hand height (122 px, 117
  compact). On testing it grows from 122 to 128 with two hands and moves
  everything under it. The room is **reserved** rather than laid over the
  strip:
  - *Key · Notes · Layer* sits centred on the strip's top edge, in a 12 px
    margin that is there either way.
  - The hint under the strip always has two lines' room.
  - With those, the tallest state (Poly with two hands, the pairing menu
    beside *Tune a chord*) fits the one-hand height, with 1.3 px to spare on
    the full face and 8.3 compact.
  - The cost is a blank second line under the strip with one sound.
  - The other way, *Key · Notes · Layer* and the hint over the top of the
    strip, would give that line to the figures and cover the keys' tops.
- **The link pills are one width (98 px)** whatever they say (*Same in both*,
  *Lower's own*, *Upper's own*). They sit at the right end of each view's
  header beside the dots, so appearing with Two hands moves nothing else.
  Put before the tools, a pill moved them; that is the check's null.
- **The subtabs' boxes stay put on a switch.** In the mockup the chosen
  subtab covered the bar's rule with `margin-bottom: -1px`, so both subtabs
  changed height by a pixel on every switch. The check caught it, and it is a
  shadow now (`0 1px 0` in paper). The build must not use a negative margin
  for that either.
- **The words that change keep their boxes.** These all live in boxes that
  do not size to their text:
  - the summaries;
  - *sweeps +1.5 oct* and *the filter is off*;
  - the Envelope's *follows* line.
  The Shape menu in the filter envelope's title is pushed right
  (`margin-left: auto`), so the words before it can change length.

Checked over every box on Play, to half a pixel, at all six windows (about
40 boxes with the amp shown: the band, its strip, hint and mode switch; the
settings row and each field and control; the figure area, its bar and both
subtabs; the view's header, each tool, the drawing and every knob cell). The
states compared:
- Two hands on and off, in Dyad, Mono and Poly;
- Loop, Sustain here, No sustain, and a note held;
- each filter type, and the filter envelope's Loop;
- both link pills, linked and not;
- Amp and Filter (everything outside the view);
- the Envelope's editor open over the tabs.

## The settings row's menus, shortened

Every value of the six menus fits its menu at all six windows, measured in
Jost at 12 px against the menu's width less 20 px for the arrow. The
tightest is *Level, strike, FM* at 1100x860, with 2.8 px to spare. The full
names do not fit at 960x600 in any of the six.

The full name is the option's `title`, and the menu's own while it is
chosen. It stays the name everywhere else: the info line, the search, and a
host's parameter text.

| Menu | Shown | Full name |
|---|---|---|
| Pitch bend | ±1 st … ±24 st | ±1 semitone … ±24 semitones |
| Mod wheel, Pressure | Picture · Scan | Picture amount · Scan depth (Vibrato and Nothing as they were) |
| Velocity | Level + strike · Level, strike, FM | Level and strike · Level, strike and FM |
| Shape | Sine + 3rd · Drawn · Noise · Pink · Brown · S&H | Sine + 3rd harmonic · Drawn cycle · White noise · Pink noise · Brown noise · Stepped (S&H) (the other eight as they were) |
| Interval | Unison 1:1 · Min 2nd 16:15 · Maj 2nd 9:8 · Min 3rd 6:5 · Maj 3rd 5:4 · 4th 4:3 · Tritone 45:32 · 5th 3:2 · Min 6th 8:5 · Maj 6th 5:3 · Min 7th 16:9 · Maj 7th 15:8 · Octave 2:1 | `INTERVALS`' names with their ratios (*Minor 2nd · 16:15*, …) |

The band's Outline menu (*bass and melody*) is cut at 960x600, as it is on
testing. It was outside this round; *bass + melody* would fit.

Open for the build: the Generator's rows that only some shapes have (Morph,
Width, Position, Cycle, Drawbars) and Tuning have no place in a row of four.
They want a home, the Ink tab or the Generator's dots menu, before the
section is cut down to its four.

## The gap on testing, and its fix

Between the band and the columns there is a gap: 124 px at 1660x1050 and 49
at 1400x900, open or shut. The owner saw about 250 on a larger window.

It is **not** the hidden knob stores or the popover: both are out of the
flow, and the gap stays with them removed.

- **The cause.** Since the band (17 Nov), `.bench-body` is a wrapping flex
  row (`flex-wrap: wrap`, `scope.html` line 1630). The band is its first
  line and the columns its second. A wrapping flex container with
  `align-content: normal` stretches its lines to fill its height. So the
  spare height under the columns is shared between the two lines, and the
  band has half of it under it. The gap therefore grows with the window's
  height.
- **The fix**: `.bench-body { align-content: flex-start; }`. That leaves the
  12 px row gap and nothing more.
- **Where it applies.** The new Play is a column with nothing to stretch, but
  every other tab still deals into the same body, so set it there anyway.
- **The proof** is `web/docs/mockups/play-figures/checks/gap_cause.py`,
  against `scope.html`: the gap equals the row gap plus half the spare height
  to a pixel, and is the row gap with the fix. Each has a null.

The popover's drawing at 1660x1050 is 254x427. Its running past the window I
could not reproduce headless (it ended 8 px above the modulation row, its
knobs in one row). It goes with this design.

## Measured sizes

These are in the page's own pixels, in the brand's webfonts, at the five
windows `fittest.py` uses and at 1660x1050. The plugin's 960x600 at Auto's
90 per cent is 1067x667 of them. The window's boxes (header, tabs, the tab's
own area, the modulation row, the Picture) are `scope.html`'s at d5c2928,
read by `checks/real_boxes.py`.

| Window | Band | Settings | Figure area | Amp drawing | Filter's two | Envelope editor, its drawing |
|---|---|---|---|---|---|---|
| 1660x1050 | 122 | 67 | 830x501 | 802x367, 2.2:1 | stacked 802x128, 802x124 | 830x779, 796x332 |
| 1400x900 | 122 | 67 | 830x351 | 802x217, 3.7:1 | 384x197, 384x193 | 830x629, 796x332 |
| 1100x860 | 122 | 67 | 742x367 | 714x233, 3.1:1 | 340x213, 340x209 (1.6:1) | 742x645, 708x295 |
| 1200x680 | 117 | 60 | 830x278 | 810x159, 5.1:1 | 394x144, 394x136 | 830x510, 804x309 |
| 1100x680 | 117 | 60 | 742x278 | 722x159, 4.5:1 | 350x144, 350x136 | 742x510, 716x275 |
| 960x600 | 117 | 60 | 709x264 | 689x145, 4.8:1 | 333x130, 333x122 | 709x495, 683x263 |

Two hands changes none of these.

At every window:
- nothing sits between the band and the settings row;
- Play does not scroll;
- nothing covers the modulation row or the Picture section;
- every knob row and both settings rows are one row.

The rules the build holds:
- every drawing between 1.5:1 and 7:1;
- the amp's and the Envelope's at 2:1 or wider;
- no drawing under 120 px tall.

If 960x600 proves too short, Expression's four folding behind its dots gives
about 30 px.

## What replaces msegtest's popover checks

`msegtest.py` keeps everything about the drawing: the maths against the
core's, the gestures, the menu, the knobs' laws, undo, the hands, the
Envelope following, and the morph. What goes and what replaces it:

| msegtest today | Replaced by |
|---|---|
| The amp's block is just the shape, its four readings under it; the filter's block says *does nothing* at amount nought and *sweeps* otherwise | The subtab summaries: each label's text against the values, the shortest form used only when the longer does not fit (null: a summary three times as long does not fit); the filter envelope's title words, as the block's were |
| The popover beside its block, not over it, the band or the screen, all in, its knobs in one row, Play not scrolled, at five windows (null: moved over its block) | At the six windows: nothing between the band and the settings row (null: a 250 px block there); Play not scrolled and the view's content inside it (null: a figure area 2000 px tall); clear of the modulation row and the Picture (null: the tab moved down 120 px); every knob row and settings row one row (null: a row squeezed to 120 px); the drawings' aspect and height as above (null: the area squeezed to the popover's 254 px) |
| Its six knobs move in while open and back on Close; a press outside closes it, a press inside does not | The knobs live in their view; nothing moves in or out. The subtab chosen is a view state, not stored. For the Envelope's editor: its knobs move in and back (*controls are moved, never copied*), and Close, Esc and pressing the card shut it |
| `showControl` on an envelope knob opens its editor with the knob in it | `showControl` on an amp or filter knob chooses its subtab; on an Envelope knob it opens the card's editor |
| (new) | **Nothing moves**: every box on Play, to half a pixel, across the states above (nulls: the band 6 px taller with two hands, as testing has it; the link pill before the tools) |
| (new) | The band's content inside its one height in every mode and hands state (null: a band 90 px tall) |
| (new) | Every value of the settings row's menus fits its menu, in the menu's font (null: the full names at 960x600) |
| (new) | The Envelope's editor over the tabs at the six windows: its content inside it, clear of the modulation row, its drawing 2:1 to 7:1 and 120 px tall, its knobs one row (null: its drawing beside *Where it goes* at the bench's height is a tower) |

`fittest.py`, `striptest.py` and `patchtest.py` gain the same:
- `fittest.py` the six windows' fit;
- `striptest.py` the pill in the heading and the band's one height;
- `patchtest.py`'s cell invariance extended to the whole tab, as above.

Measure in the brand's webfonts. Headless Chromium in the cloud sessions
cannot fetch them itself, and a fallback face moved every width by a pixel
or two in the mockup. `checks/webfonts.py` routes the requests through
Python.
