# Perform, labelled

The build's spec for the second item of the owner's UI review (19 Nov). The mockup is
`web/docs/mockups/perform/`: live, with three screenshots and `checks/perform_checks.py`, which
runs 33 checks, each with its null. It changes the Perform menu's layout and labels and adds one
span to the clock. No control is added or removed, and every id keeps its type, range and option
values.

The arpeggiator, the clock and the tempo act on the loop through the notes the generator plays.
The morph acts on the whole setup. The drawing makes the arpeggiator's effect on the figure
predictable before a chord is held.

## What the owner saw

- The arpeggiator's three menus without names (*off · 1/8 · 1 oct*).
- The clock as *Bar STOP 5.4*.
- Morph, Glide and Tempo as sliders.

## What changes

- **Arpeggiator.** A drawing, then three menus, each with its name over it, as in Play's
  Expression row:
  - **Pattern** (`arpMode`). The option texts are now capitalised and *up-down* reads *Up and
    down*. The values are unchanged.
  - **Step** (`arpRate`).
  - **Octaves** (`arpOctaves`), showing *1 · 2 · 3*, since the name now says octaves.
  - **The drawing** is one bar of what a held C major chord plays: one row per note across the
    octaves and one block per step. 1/4 gives 4 steps, 1/8 gives 8, 1/16 gives 16, 1/8t gives 12
    and 1/16t gives 24. *Up and down* turns at the ends without repeating them. *As played* goes
    in the order the notes were struck (E, C, G here). *Random* is drawn from a fixed seed, since
    it is only a picture of the kind. With the pattern off it draws the chord held. While the
    clock runs, the step it is on is drawn in `--blush-deep`. A caption reads, for example,
    *16 steps of 1/16 over the bar, C4 to G5*.
- **Clock.** One sentence: **Internal · bar 5, beat 4 · Stopped**, with *Running* in sage and
  *Stopped* in rust, as the run button's state is coloured.
  - `clockFrom` holds *Internal* or *Host*.
  - `transportAt` holds *bar 5, beat 4*. Testing wrote *5.4*.
  - `transportState` is the one new span: *Running* or *Stopped*.
  - Under the sentence are four beat dots and the button (`transportPlay`). The button reads
    **Start** or **Stop**, whichever it will do; testing's read *STOP* beside the word *Bar*.
  - The button sits on its own row, so a growing bar count moves nothing a hand is reaching for.
    The check's null puts it back on the line and watches it move.
- **Knobs.** **Glide** (`quantiseGlide`) and **Tempo** (`tempo`) are the Bench's knobs, with
  **Tap** beside Tempo. Glide dims while **Quantise pitch** (`quantise`, drawn as a switch) is
  off, since it acts only then.
- **The morph stays a slider.** It is the setup morph's crossfader, which CLAUDE.md lists among
  the controls that stay sliders: it slides between two ends, and a knob would hide which end it
  is nearer. It is restyled as the face's sliders (a 2px `--line` track and a 13px `--blush-deep`
  thumb). Its ends are named, **A** and **B**, each with **Store** under it (`morphStoreA`,
  `morphStoreB`), and its position is read in per cent over it. If the owner wants a knob anyway,
  that is a change to the layout decision, not to this panel.
- **Labels.** Every menu, switch and knob has a visible name of three words or fewer. *Quantise
  the generator's pitch* is **Quantise pitch**; the rest of it is in the info line.
- **Size.** The panel opens where testing's does and is 640 px wide. It is shorter: 319 px tall
  on the full face (from 332) and 278 compact (from 324), and it ends above the Picture strip at
  every window.

## For the build

- **The clock.** The page's clock paint writes the bar and the beat as *bar N, beat M* into
  `transportAt` and the state into `transportState`. `clocktest.py` and `performtest.py` read
  those spans, so adjust them to the sentence.
- **The menus.** `arpMode`'s and `arpOctaves`' option texts change and their values do not, so
  a setup, the plugin and the core hear what they heard.
- **The drawing** is the arpeggiator's own order (the page's `arpOrder`, or whatever orders the
  held notes), over a held chord or, with none held, over C major. It never reaches the sound.
- **Words.** `what-each-control-says.md` needs these names changed:
  - `arpMode` to *Pattern*;
  - `arpRate` to *Step*;
  - `arpOctaves` to *Octaves*;
  - `transportPlay` to *Start · stop*;
  - `quantise` to *Quantise pitch*;
  - the morph's store buttons to *Store A* and *Store B*.

  It also needs new rows for `clockFrom`, `transportAt` and `transportState`; the mockup's
  `EXTRA_WORDS` has drafts.
- **Tests.** `benchtest.py` (Perform's homes), `knobtest.py` (two more knobs), `morphtest.py`
  (unchanged slider), `headertest.py`, and `fittest.py` at the six windows.

## Measured

At the six windows, in 20 states, the panel never scrolls, opens where testing's does and ends
above the strip. Nothing in it moves by half a pixel; the clock line's words are excluded, since
they are read, not pressed. The states cover every pattern and step, three octaves, the clock
stopped and running at bar 1 and at bar 128, from the host, Quantise with Glide at 300 ms, Tempo
at 30 and 300, the morph at B, and B♭ harmonic minor.

The nulls fail as they should:

- testing's Step and Octaves have no visible name;
- testing's clock reads *From internal Bar STOP 1.1*;
- testing has three sliders;
- down's order read as up's;
- 1/8's eight steps at 1/16;
- the button on the clock line moves when the bar count grows.
