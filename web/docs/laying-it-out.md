# Laying it out

A plan for the layout, which has stopped being navigable. It comes before
`shaping-the-sound.md` because that plan adds dozens of controls, and the layout
they would land in could not already fit a rack of three lanes.

Stages here are **R1–R5**, so they cannot be confused with the lettered stages of
the two sound plans.

## Where the current design fights you

Three older decisions explain it.

- **The rail is not a set of tabs; it is a table of contents.** Every section is
  shown at once, dealt into columns, and "neither panel may scroll" is held
  together by hiding the prose behind ⋯. It holds for the tone. It has never held
  for a rack: the generator and the live input alone scrolled the Bench by 52 px
  at 1400×900 until the last stage trimmed it, and a rack of files still does.
- **Only the oscillators are in the side column.** `SIDE_GROUPS = ["lfoGroup"]`
  gives the LFOs a permanent place. Every other source is a chip with no
  explanation of what it is or where it can go.
- **The same sections appear in both views.** `setView` moves every group between
  `#menuPanel` and the Bench, so Settings and the Bench always have identical
  contents, and Settings cannot be opened from the Bench at all.

CLAUDE.md's *layout decisions already made* ask for evidence before any of these
is changed. This is it: the page is hard to find your way around, and it cannot
fit what Stage D made possible.

## Decisions

| # | Question | Answer | Why |
|---|---|---|---|
| R-a | What is Scope for? | **Watching and playing.** Its top strip keeps what it has (trigger level, timebase, zoom, persistence, Photocell, Clear); the Generator, Filter and Trigger sections live on the Bench only. | Frequency means nothing while a keyboard is playing, and the Bench is one key away (B), or one search away (/). |
| R-b | One tab per section, or per task? | **Per task: Play, Picture, Shape, Sources, Measure.** | A tab per section would split things used together — moving a generator slider while watching the trigger and the vertical scale. Five tabs, each short enough to fit. |
| R-c | Is the Keyboard a setting? | **Half of it.** The port, *Connect* and the learned-controller list are set once and live in Settings, as **MIDI**. Dyad / Mono / Poly, Draw, Layers, Edit A/B, *Show keys* and the note checkboxes are played and stay on the Bench. | A setting is something you set and leave. |
| R-d | Where does *Hear the generator* go? | **The Generator section, on the Bench.** The device picker, *microphone or line* and line monitoring go to a new **Audio** section in Settings. | The first is toggled all the time. The last is the feedback-risk switch, and being out of the way is a feature. |
| R-e | Does dragging a chip onto a control survive? | **Yes.** The mini scope and a compact chip strip stay in the side column on every tab; the Sources tab is where a source is explained and edited. | The drag is an accelerator, and an accelerator that only works on one tab is not one. |
| R-f | When is the search index built? | **When a search starts.** It is a few hundred rows; reading them from the page each time is cheap. | An index rebuilt on `midiLearn` or `setPhoto` misses the triggers nobody listed — the layer rows, poly's Draw row, rack lanes, the band split — and a stale index is the duplicated-id readout bug in another form. |

## R1 · every section has a home

Each `.menu-group` gets `data-home="settings"` or `data-home="bench"`. `setView`
moves only the bench groups; the settings groups stay in `#menuPanel` for good,
so *moved, never copied* still holds, and `#menuButton` is shown in both views.

- **Settings:** MIDI (connect, status, learned controllers, the Nord note),
  Audio (device, microphone or line, monitoring), Presets, Beam.
- **Bench:** Input, Lanes, Keyboard, Generator, Vertical, Display, Filter,
  Trigger, Measure, and the Sources tab.

In Settings the device row stays visible whatever is loaded, greyed with a
reason when the source is not a live input, rather than hidden: a setting that
vanishes cannot be found.

## R2 · the Bench becomes tabs

`#benchRail` becomes `role="tablist"`. The active tab is remembered next to
`VIEW_KEY`, and `layoutBenchBody` deals only that tab's sections into columns.

| Tab | Sections |
|---|---|
| Play | Input, Lanes, Keyboard, Generator |
| Picture | Display, Vertical, Trigger |
| Shape | Filter — and, later, the voice's drive and fold and the plane's operations |
| Sources | the source grid and the selected source's detail |
| Measure | Measure |

One tab at a time fits: the heaviest, Play with a rack of six, is about 1,050 px
against the 1,350 px three columns hold. On a narrow screen the rail already
scrolls sideways, which works unchanged as a tab strip.

## R3 · the Sources tab

A grid of every source, **grouped by family**, and a detail panel for the one
selected. `registerSource` gains `family` and `description`. A family with
nothing registered shows a one-line hint ("Connect a keyboard", "Turn on the
photocell") instead of disappearing.

Selecting a source sets `focusSource`, which already makes every patched control
on every tab draw that source's lane.

The detail panel (`buildSourceDetail(id)`):

1. Name, ink, description, and a live meter of `value()`.
2. The source's own controls: an LFO's shape and rate (moved out of
   `#lfoRows`, which with `lfoGroup` and `SIDE_GROUPS` goes away); a
   controller's name and *forget*, with ids prefixed `srcDetail-`.
3. **Destinations**: a row per routing with its depth and a remove button.
4. **Add destination**, from `destOptions()` filtered by `routingAllowed`.

This replaces the one-destination dropdown, so `syncLfoRows`'s "N destinations"
workaround goes. `setLfoDest` and `setLfoDepth` stay as functions.

Descriptions, checked against the code (the first draft had Direction missing,
and Boredom not at all):

| Family | Source | Description |
|---|---|---|
| Oscillators | LFO 1, LFO 2 | A repeating wave that sweeps whatever it is on back and forth by itself. Rate is how fast, depth is how far. |
| Signal | Level | How loud the signal on screen is right now. |
| Signal | Envelope | Where the generator's attack, decay, sustain and release have got to — in poly, the loudest note's. |
| Keyboard | Key | How hard you struck the last key. |
| Keyboard | Notes, Spread, Melody, Inner | How many keys are held, how far apart, how high the top one is, and how hard the notes the picture is not drawing were played. |
| Controllers | CC *n* | A drawbar, pedal or switch on your keyboard, learned the first time it moved. |
| Picture | Photocell | How bright the screen is under the reticle. |
| Picture | Roundness, Coverage, Change, Novelty | How spread the figure is, how much of the screen is lit, how much it moved, how unlike the last fifteen seconds it is. |
| Picture | Direction | Which way round the beam travels: plus one way, minus the other. |
| Picture | Boredom | Climbs while the picture is stuck and drains when it moves, at most a quarter a second. |

## R4 · search

A box above the tabs, focused with `/` (B is the view shortcut). The index is
read from the page when a search starts: every `.menu-row` and `.check` in every
section, including those behind ⋯, plus each source's label, family and
description, with a small synonym map (lfo → Oscillators, adsr → Envelope,
midi → Keyboard, cc or drawbar → Controllers).

Results carry a breadcrumb — *Generator › Attack (behind ⋯)* — and choosing one:

- a Bench row switches tab, unfolds the section, opens its detail if the row is
  behind ⋯, scrolls to it and highlights it for a moment;
- a Settings row opens Settings and scrolls to it;
- a source opens the Sources tab with it selected.

## R5 · what has to be rewritten

- CLAUDE.md's *layout decisions already made*: the no-scroll rule becomes "one
  tab fits", and a fixed home per section replaces "the same groups in both
  views".
- `benchtest.py`: *every body section is on show at once*, *Modulation is not
  one of the rail's sections* and the `lfoDest0` checks; `patchtest.py`'s
  no-scroll and width checks, per tab; `racktest.py`'s Bench check;
  `modtest.py` and `lanetest.py` where they reach the LFO rows.
- The README, and the help sheet's entry on Scope and the Bench being the same
  instrument, which stops being true.
