# Ink, with its figures

A note for the build, 19 Nov. It goes with the mockup `web/docs/mockups/ink/`
(live, with its screenshots and its checks). It gives Ink the treatment Play
had in `play-figures.md`: a figure area, a drawing you can read, and the
controls in one row under it.

It acts on the loop. Ink is the stage where the figure gets its character:
FM, Warp, Ring, Sync and the shaper are what make a figure bark, tear or
fold. Until now nothing on the tab showed what any of them did.

## What Ink is

Ink is a figure area and nothing else. It has no band and no settings row, so
the area takes the whole tab. Its bar has two subtabs, each label its name and
a summary that shortens as Play's do (none needed to at the six windows):

- *Oscillator · 3:2 · FM 2.0* (*plain* while nothing is turned);
- *Shaping · drive 45% · 4 bits* (*clean*).

### Oscillator

**The drawing** shows both channels over the voice's whole pattern:

- the left channel in charcoal;
- the right in slate (`--ch2`, the right channel's lane ink), offset by Phase;
- the plain shape (no FM, Warp, Ring, Sync, Sub or Unison) dashed in
  `--unresolved`, so what the oscillator adds is the difference you see.

The span is as many of the note's cycles as it takes to repeat. That is the
Ratio's denominator while FM or Ring is on, times the sub's octave, at most 8.
The foot says so: *2 cycles: the pattern repeats every 2 · 9.1 ms*.

Unison is drawn as its copies drift, while the clock runs.

**The controls**, in one row under the drawing: Frequency, Phase, Ratio
(menu), FM, Warp, Warp at, Ring, Sync, Sub, Unison (menu) and Spread.

- Warp at is greyed, not hidden, while Warp is off, and Spread while Unison is
  off.
- The sub's octave and shape go to the section's dots menu.

### Shaping

**The drawings**, side by side:

- **The shaper's curve**: a square of in against out, with the straight line
  dashed behind it. Crush's bits are the steps the curve takes, with the
  smooth curve faint under them.
- **Two cycles of the oscillator, before and after**: the shaper's input
  dashed and its output solid. Rate shows as the holds it puts in at the
  note's Frequency.

**The controls**: Drive, Fold, Crush (menu) and Rate (menu).

### The fit

The drawings are sized by room, never by window size:

- **Oscillator**: the wave takes the area's width and as much height as is
  free, down to 1.5:1.
- **Shaping**: the curve is a square of the row's height. The row is no
  taller than leaves the cycle at 1.5:1.

| Window | Figure area | Oscillator's wave | Shaping: curve, cycle |
|---|---|---|---|
| 1660x1050 | 830x706 | 802x534, 1.5:1 | 329x305, 459x305 |
| 1400x900 | 830x556 | 802x423, 1.9:1 | 329x305, 459x305 |
| 1100x860 | 742x572 | 714x439, 1.6:1 | 294x270, 406x270 |
| 1200x680 | 830x461 | 810x350, 2.3:1 | 332x308, 464x308 |
| 1100x680 | 742x461 | 722x350, 2.1:1 | 297x273, 411x273 |
| 960x600 (at 90%) | 709x447 | 689x336, 2.1:1 | 284x260, 391x260 |

Ink does not scroll at any of the six windows, and nothing covers the
modulation row.

**Nothing moves.** Every box on Ink stays where it is, to half a pixel, across
nine settings, five shapes and both subtabs (outside the view). The check
found one real shift: the key over the wave named the plain shape and changed
width. It is one width now.

## The wave, not the figure

The task allowed the X–Y figure the two channels draw as well as, or instead
of, the wave. Both were measured. Each control was turned from nought, and the
movement of each drawing's outline was measured on a 300 px drawing:

| Control | Wave, Phase 90° | Figure, Phase 90° | Figure, Phase 0° |
|---|---|---|---|
| FM 3.0 | 44 px | 34 | on the diagonal |
| Warp +60 | 14 | 28 | on the diagonal |
| Ring 60% | 18 | 85 | on the diagonal |
| Sync 2.5× | 41 | 40 | on the diagonal |
| Sub 50% | 20 | 65 | on the diagonal |
| Ratio 3:2, FM 1.0 | 21 | 56 | on the diagonal |
| Unison 3 | 26 | 125 | on the diagonal |

At the default Phase of 90° the figure moves as much or more, but the wave is
chosen, for three reasons:

- **The screen beside the tab already draws the figure**, live and large. A
  second copy tells the player nothing the screen does not.
- **At Phase 0° the figure is blind.** The two channels are then one signal,
  so the figure is the diagonal whatever the oscillator does. The checks find
  it exactly on the diagonal for all seven controls, while the wave moves 14
  to 44 px.
- **The wave keeps a before.** With the plain shape drawn behind, Sync's
  restarts, Sub's slow swell and Ring's envelope each read as what that
  control adds.

Putting both in one row costs the wave its width: 441x294 against 689x336 at
960x600.

## The formulas, and where they are in the core

| Drawing | Formula | Source |
|---|---|---|
| FM | `pm = fmI sin(m)`; the second oscillator `m` at the Ratio, started where its channel starts | `osc.h`, `oscStep`; FM is a tenth of the knob (`restore.h`'s table) |
| Warp, Warp at | `pm += warpA sin(master − 2π warpC)`, with `warpA` 0.009 rad a step; the sine's offset `besselJ1(warpA) sin(2π warpC)` added; any other shape's offset taken out by the 5 Hz blocker | `osc.h`; `generator.h` sets `warpA`, `warpC`, `warpDc` |
| Ring | `v × (1 − ring + ring sin m)` | `osc.h` |
| Sync | the shape restarted each note cycle, run at `syncR` | `osc.h` |
| Sub | `(total + sub · s) / (1 + sub)`, with `s` a 0.9 square or a sine, `hz/2` or `hz/4` | `osc.h` |
| Unison | copies at `2^(cents (2k/(n−1) − 1)/1200)`, averaged | `osc.h`, `voiceFxFor` |
| Drive | `tanh(30d² x) / tanh(30d²)` | `voice.h`, `setShaping` and `shapeSample` |
| Fold | `sin(6πf x)`, divided by `sin(6πf)` only while `6πf < π/2` | `voice.h` |
| Crush | `round(x q)/q`, with `q = 2^(bits−1)` and the page's `Math.round` | `voice.h`, `crushStep` |
| Rate | held at `crushHz` | `voice.h`, `crushStep` |

The order is the voice's: the oscillator, then the shaper (oversampled), then
the crush, then the voice filter.

The drawing leaves three things out, each under a pixel:

- the band-limiting (polyBlep and polyBlamp);
- the shaper's oversampling filter;
- the voice filter, which has its own figure on Play.

## How it was checked, and what the build's tests take from it

`checks/core_ref.cpp` builds against `core/include` and runs the real
`oscStep` (at 220 Hz, 901 kHz, after two seconds of settling) and the real
shaper. `checks/ink_checks.py` compares each drawing with it, 512 points a
pattern:

- FM (left and right), Ring, Warp on the sine, Unison and the harmonic at 7:2
  agree within 1e-9;
- Sync and the square agree within 0.0013 away from their edges;
- Warp on the triangle, through the blocker, agrees within 0.002;
- the shaper's curve agrees to the last bit for drive, fold and bits.

The nulls:

- the FM drawing against the core with FM off (1.68);
- the sub against the core's sub two octaves down (0.60);
- drive with a linear law (0.34).

**One finding about the core.** Its sub steps before it reads, so it runs one
sample ahead of the note: 0.0072 rad two octaves down at 48 kHz. It is
inaudible, and the drawing shows the sub on the beat. It is left alone here.
If it is ever fixed, it is a sound change, which means `--write-golden
--because`.

The build's face suite (`web/tests/`) should keep three things:

- the comparison, through the module the page carries rather than a separate
  binary;
- the fit at the six windows, with its nulls (a row given the whole view runs
  over; a control row 300 px wide wraps);
- the no-shift check, with its null (the key sized to its words).

`fittest.py` and `patchtest.py` take Ink as they took Play.

The drawings need nothing from the core. They are the page's arithmetic over
the setup's values, like Play's Wave (`paintCycle`). Using the core's own
module for them would be better, and a small export would let the page ask
for a pattern directly.

**Storage: none.** The subtab chosen is a view, never stored. No field changes.

## Open for the owner

1. **Shaping on a tall window leaves paper** (273 px at 1660x1050). Stacking
   the cycle over the curve when there is the height would use it.
2. **The figure as well**, at Phase 90° on a wide window, for when the screen
   is in Y–T or Spect.
3. **Frequency on Ink.** It does not change the wave's shape, only its
   milliseconds. It may belong on Play with the note's other settings.
