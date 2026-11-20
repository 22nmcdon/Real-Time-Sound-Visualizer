# Scope & measure, by subject

The build's spec for the first item of the owner's UI review (19 Nov). The mockup is
`web/docs/mockups/scope-measure/` (live, with four screenshots and `checks/measure_checks.py`,
41 checks with their nulls). It changes the panel's layout and labels. No control is added or
removed, every id stays with its type, range, step, options and role, and nothing the plugin or a
setup reads changes.

It acts on the loop (`making-it-one-instrument.md`) the way the panel always has: almost every
control in it changes what Scan reads, and the info line now says so for each one, because the
long labels were the only place some of that was written.

## What the owner saw

A wall: about 30 controls in three columns, fourteen of them sliders where the rest of the face
has knobs, and checkbox labels that wrapped (*Take the lag and the tuner from the note played*,
then an orphan *… and the timebase*). It was 564 px tall, and at 960 × 600 it ran 5 px over the
Picture strip.

## The panel

- **The head never changes**: the name, **Run** (`run`), **Mode** Auto · Normal · Single, and
  **Autoset**, then the close. They are in view on every subtab (checked).
- **Four subtabs** in the figure-area bar Play and Ink use (`.fig-bar`). Each shows its name and a
  summary read from the values:
  - *Trigger*: `Rising · Left · +0.250 fs · 30%`
  - *Time*: `1 ms/div · 1.0×`, with `· lag` when it is on
  - *Vertical*: `Left, Right · no filter` (or the filter's type)
  - *Measure*: `Readouts off · cursors off`
- **One view at a time, in one box.** The panel is one height at each window: 520 px, or 469 at
  1200 × 680 and 1100 × 680. It always ends above the Picture strip, because the info line there
  now holds the long explanations. The views are laid on top of one another, so choosing a
  subtab moves nothing.
- **Each view has a drawing on the left and its controls on the right.**

| Subtab | Drawing | Controls |
|---|---|---|
| Trigger | The source lane's trace on a 10 × 8 graticule with the level dashed (`--blush-deep`, marker *T*), the position as a dotted line and a marker under it, the crossing as a ring, and the holdoff washed after it. The other lane is faint. Past the trace's peak the trace goes `--unresolved`, as free run does, and the caption says *Free run*. | **Edge** Rising · Falling; **Source** Left · Right (`trigSources`); knobs **Level** (bipolar), **Position**, **Holdoff**. |
| Time | The window with time labels every two divisions, and Zoom's slice outlined around the trigger, with the rest shaded. The caption says how much time is across, how many cycles, and what the zoom keeps. | *Window*: knobs **Timebase**, **Zoom**. *From the keys*: **Pitch** (`midiTruth`), **Timebase** (`midiFollow`, dimmed while Pitch is off). *Lag X–Y*: **Lag X–Y** (`lagOn`), **Delay** Auto · Set, knobs **Delay** (`lag`, live only on Set) and **Heard** (`lagMix`, tagged *speakers*). The lag's controls dim while it is off and keep their place. |
| Vertical | The two lanes at their full scale and offset, each with a marker at its offset in its ink (L/R, or M/S under mid / side). | *Lanes*: per lane, its ink and name, **Show**, **AC**, knobs **Full scale** and **Offset**; **Mid / side**; knob **AC corner**. `laneGroup` (Stacked · Overlaid, the X–Y pair) is kept, hidden as on testing until there are more lanes. *Trace filter*: **Filter on**, **Type** (the menu), its response on a log axis with the cutoff marked, knobs **Cutoff** and **Resonance**, **Screen reads** Input · Shaped and **Speakers get** Input · Shaped (tagged *speakers*). All of it dims while the filter is off. |
| Measure | A Y–T screen with the readouts table under it (faint while off) and the gold cursors when on. | *Show*: **Readouts**, **Cursors**; **Numbers read** Signal · Turned; *Reference*: **Save**, **Clear**, and whether one is saved. |

- **The trace filter is Vertical's**, beside the lanes. A bench scope keeps its bandwidth limit
  on the channel menu, and the filter shapes what the lanes draw. It could have been a fifth
  subtab. That would cost the bar a fifth of its width and leave Measure as thin as it is.
- **The lag and *from the keys* are Time's**, because both are about the window's time: the
  lag's delay, and the note setting the timebase.

## Knobs, labels, words

- **All fourteen ranges are knobs**, drawn as the face draws them: the setting over the knob, the
  name under it, and the page's range input under the face as the value. No slider is left in the
  panel.
- **The checkboxes are drawn as switches** (a pill with a lamp, sage when on). Each one is still
  its checkbox, so `checked` and the `change` event are what they were.
- **Every label is three words or fewer and on one line** (checked on every subtab, at every
  window). The panel's note, *For reading the screen. Two rows reach the speakers, and say so*,
  is gone from the head. The two rows still carry their *speakers* tag.
- **The long explanation is each control's info line**, taken from `CONTROL_WORDS` unchanged.
  Where a label changed, the line names the control by the new label. Two names need changing
  in `what-each-control-says.md`: `midiTruth` becomes *Pitch from the keys* and `midiFollow`
  becomes *Timebase from the keys*. Their lines need no change.

## For the build

- Keep the ids. The panel's markup moves inside `#measurePanel` into the four views. The
  sections that come in by `data-place` (`measureTrigger`, `measureBody`, `measureSide`) become
  the views' homes (`data-place` per view), so `showControl(id)` chooses the subtab that holds a
  control. That is how Play's and Ink's subtabs already work.
- The subtab chosen is a view and never stored, as on Play.
- The knobs use the Bench's knob (`knobtest.py`'s rules). Timebase and Full scale are stepped
  (0 to 8): they turn in detents.
- The drawings are the page's own arithmetic over the values (the trigger's crossing, the
  zoom's slice, the lanes' gain and offset, a biquad's magnitude). Nothing in them reaches the
  sound or what Scan reads.
- Tests: `benchtest.py`'s Scope & measure block (it measures the panel shut by default, the
  readouts off, and no scrolling to 960 × 600), `fittest.py`, `knobtest.py`, `wordstest.py`
  (the two names) and the tests that reach these controls by id, which should pass unchanged.

## Measured

At every window, on every subtab, in 20 states of the controls: no scroll, inside the window,
above the strip (the panel ends at 562 px at 960 × 600, with the strip at 587), and nothing in the
panel moves by half a pixel. The nulls that fail as they should: testing's wall laid out at
960 × 600, a knob cell sized to its reading, and the filter's knobs taken out while it is off.
The full list is in `checks/results.json`.
