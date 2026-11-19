# The LFOs, drawn

A note for the build, 19 Nov. It goes with the mockup
`web/docs/mockups/lfo/` (live, with its screenshots and its checks). It takes up
"Later: the LFOs" from `mseg-design.md`: the envelopes' drawing, run as a
repeating shape.

It acts on the loop (`making-it-one-instrument.md`'s first rule). An LFO is how
a held chord keeps moving on its own, and a *Breathing* preset is measured on
exactly that. The drawn shape lets a player make that movement into whatever
gesture they want: a quick rise and a slow fall, a stutter, or a wander. They
draw it and watch it land on the screen.

## The editor

### Where it opens

It opens over the tabs, at the bench's size, where the Envelope card's editor
opens. It has one column, top to bottom:

1. **The head**: the LFO's dot, its name, its reading (the hertz, and the note
   value while the rate is in tempo) and *Close*.
2. **The tools**:
   - the seven starting shapes, as small drawings;
   - what the shape is (*Sine · as today*, or *Drawn · 5 points, 1 random*);
   - the Grid (4 · 8 · 16 · 32 to the cycle);
   - *Hold a note*.
3. **The drawing**, the editor's width.
4. **The foot**: Rate and Phase as knobs, *Rate in* Hz · Tempo, and *Starts
   again* Free · Each note · Each phrase.
5. **Where it goes**, which scrolls inside itself past what fits.

The drawing's height is set by room, never by window size. It is 2.4:1 of its
width (2.6:1 compact), shortened only as far as *Where it goes* needs to show
three routings and Add, and never under 120 px tall. That gives the six
windows these sizes:

| Window | Editor | Drawing | Routings in sight (of 8) |
|---|---|---|---|
| 1660x1050 | 838x779 | 804x335, 2.4:1 | 8 |
| 1400x900 | 838x629 | 804x328, 2.5:1 | 6 |
| 1100x860 | 750x645 | 716x298, 2.4:1 | 8 |
| 1200x680 | 838x510 | 812x240, 3.4:1 | 6 |
| 1100x680 | 750x510 | 724x240, 3.0:1 | 6 |
| 960x600 (at 90%) | 717x495 | 691x225, 3.1:1 | 6 |

Today's drawing is 428x150 on the full face and 365x96 at 960x600, so this is
3.8 to 4.7 times its area.

Two columns, as today's editor is laid out, were measured and rejected:

- the drawing beside *Where it goes* is a tower (486x634 at 1660x1050, and
  1.5:1 at best);
- its own column is too narrow for the tools, which wrap at 1100x860.

The Envelope's editor found the same thing (`play-figures.md`). The two
editors are now alike.

### The drawing

- **One cycle**, with **the level straight from −1 to +1**. It has three level
  lines (+1, 0, −1) and a soft fill to the 0 line, in the LFO's ink (LFO 1
  `--ch1`, LFO 2 `--ch2`, as their cards).
- **Bipolar because the core's LFO is.** `lfoStep` gives −1 to +1, and a
  routing moves its knob both ways round where it was set. So 0 is the knob
  as you left it.
  - A 0..1 drawing would say the LFO only pushes upwards, which it never has.
    Making that true would change every saved patch.
  - The envelopes are drawn 0..1 because they are 0..1.
- **The grid in time** is faint, at the Grid's step, with the quarters
  stronger. The foot says *one cycle · 5.0 s* in hertz, or *one cycle · 1/4*
  in tempo.
- **The gold dot** is where the LFO is now, with a faint gold upright through
  it. It is read from the instrument's served phase and value, as the cards
  read them today (`lfosServed`).
- **Points** are round, filled in the ink. A random point is a hollow diamond
  at this pass's level. A dashed upright with a tick at each end shows its
  reach, the range it may land in, and dragging the point up or down sets the
  reach (decided, below).
- **Bends** are a hollow round half-way along each line that is not held or
  flat.

### The gestures

They are the envelopes', unchanged:

- drag a point;
- press the line twice to add a point (at the level the line has there, so
  nothing moves), and a point twice to take it away;
- drag a bend's round;
- the arrows move a focused point and Delete takes it away;
- right-click, Ctrl-click, a long press or Shift+F10 opens a point's menu:
  - its line: *Straight · Curve · S-curve · Hold*;
  - *A new level each pass*;
  - *Remove the point*;
  - a line saying what a point is, as the info card would.

Points snap to the Grid, and Shift drags freely. A point stays between its
neighbours, and may sit on one: two points at one place are a jump.

### The starting shapes

**Sine, Triangle, Saw up, Saw down, Square, Random steps, Smooth random.**

The first five are today's five (`LFO_SHAPES`: sine, triangle, ramp, square,
random). Choosing one sets `l<i>s` exactly as the Shape menu does now, and the
core plays it through `waveAt`, so it is the same to the bit. The drawing shows
the shape's drawn twin. The first edit adopts the twin, the way `menvAdopt`
adopts the amp's envelope:

- `l<i>s` becomes `drawn`;
- `l<i>m` gets the twin's text;
- the engine changes path mid-cycle without a step. The twins equal the core
  to 1e-15 or better, and the triangle to 2e-11 (see the tests).

Saw down and Smooth random are new, and are drawn from the start.

| Shape | Its drawn twin | Against `lfo.h` |
|---|---|---|
| Sine | `1;.25,1,s;.75,-1,s` (two points, S-curves; the wrap line crosses 0 at phase 0) | 1.4e-15 |
| Triangle | `1;.25,1,l;.75,-1,l` (the same points, straight) | 2.3e-11: `asin(sin)` is off a straight line at its peaks |
| Saw up | `1;0,-1,l;1,1,l` | 0 |
| Saw down | `1;0,1,l;1,-1,l` | new |
| Square | `1;0,.9,l;.5,.9,l;.5,-.9,l;1,-.9,l` (±0.9, as `waveAt`'s square) | 0 |
| Random steps | `1;0,1,h,r` (one random point at full reach, held) | 0, from the same Random stream |
| Smooth random | `1;0,1,s,r` | new |

### The knobs and switches

- **Rate**: 0.01 to 8 Hz on a log law (today a linear slider over the same
  range). While *Rate in* is Tempo it turns through the nine note values of
  `LFO_SYNC`.
  - What is stored is unchanged: `l<i>r` stays Hz×100 and `l<i>y` the note
    value.
  - Tempo restarts the LFO on the beat, as Sync does now.
- **Phase** (new): 0 to 355° in 5° steps. It is where in the cycle the shape
  is read from, so a restart begins there. Free, it is the offset between LFO
  1 and LFO 2 and the beat.
- **Starts again** (new):
  - **Free** runs as now;
  - **Each note** restarts on every note-on;
  - **Each phrase** restarts on a note-on with no other key down (the
    Envelope's *Each phrase*, `noteDown`).

### Where it goes

Each routing is a row, which is the depth row the page already writes
(`depthRowHTML`): the control and its tab, a depth slider (the editor's
depths stay sliders), the depth typed, and ×. With two hands, the hand's tag.

- *Add a destination* is grouped by tab: Play, Ink, Space & Memory, Scope &
  measure.
- *Silence* is the Routings switch, here too.
- Pressing a row's name could `showControl` it. The mockup does not.

### The card

The card draws the real shape over two cycles, as today's cards draw two, with
the gold dot. On the chip (compact, or under 900 tall) its reading is one width
(the hertz, or the note value), so changing it never moves the other cards.

### Nothing moves

The checks compare every box in the editor and the cards to half a pixel at
the six windows. That is 38 boxes, across:

- the seven shapes;
- Hz and tempo;
- the three starts;
- Silence;
- the clock;
- a note held;
- a point selected;
- LFO 1 against LFO 2.

The build has to keep three things the check found:

- the name is one width (Playfair's *1* is narrower than its *2*);
- the head's reading and the chip's reading are each one width;
- the drawing's fit is measured after the knobs' readings are written. An
  empty reading stood 7 px shorter, and the next paint took the 7 px back.

## Storage

The change is additive. **No version bump.** Today an LFO is `l<i>s` (shape),
`l<i>r` (free rate ×100), `l<i>y` (sync) and the legacy `l<i>a` and `l<i>d`.
This adds:

| Field | Default | What |
|---|---|---|
| `l<i>s` | `sine` | gains one value, `drawn`: read `l<i>m`. An old setup never has it, so it plays as it did |
| `l<i>m` | `""` | the drawn shape, read only while `l<i>s` is `drawn` |
| `l<i>p` | `0` | Phase, in degrees, 0 to 355 |
| `l<i>t` | `""` | when it starts again: `""` free, `n` each note, `p` each phrase |

The new fields are written only away from their defaults, so a setup whose LFOs
were never touched is the same text as today. The mockup's checks hold that.
`Object.assign` over the defaults gives an old code the new defaults, so no
decode pass is needed.

**Why `l<i>s` gains `drawn`** rather than a non-empty `l<i>m` meaning drawn:

- `l<i>s` is the question "which shape plays". Once a shape can be drawn, that
  question has a sixth answer.
- Leaving `l<i>s` saying `sine` while a drawing plays would be one field
  answering two ways (CLAUDE.md, *A field that stops having one answer*).
- It also keeps the drawing while today's sine is chosen again, so a player
  can go back to it.

**The core must learn the word.** `Lfo::setShape("drawn")` would fall through
`shapeNamed` to the harmonic. `restore.h` reads `l<i>s` in two places, both
listed under "What the core needs" below.

### The text of `l<i>m`

`l<i>m` uses the envelope string's grammar, in its own form for one repeating
cycle:

```
1;x,level,law[,r];x,level,law[,r];...
1;.25,1,s;.75,-1,s                 the sine's twin
1;0,-.6,m.78;.125,.85,l;.375,.85,m.3;.75,-.2,s;.875,-.8,h,r
```

- Version first.
- Then a point at a time, sorted by `x`, each with three or four fields:
  - `x`, 0 to 1, as a share of the cycle;
  - `level`, −1 to 1, five significant figures. For a random point it is the
    reach, 0 to 1;
  - the law of the line to the next point;
  - `r` if the point is random.
- The laws:
  - `l` straight;
  - `m<mid>` a curve by its midpoint, the envelopes' one-pole law
    (`msegRho`), clamped 0.1 to 0.9;
  - `s` an S, half a cosine. It is new, because no one-pole curve makes a
    sine;
  - `h` held at the point's level until the next point.
- At most 32 points, so under 600 characters.
- The last point's line runs to the first point of the next pass. Two points
  at one `x` are a jump.

## What the core needs

### `scope/lfo_shape.h` (new)

- **The parse**: `msegParse`'s rules for checking the text, kept apart from
  the envelope's stretches.
- **The flat table of points**, parsed once per setup change.

### `Lfo` (`lfo.h`)

- `bool drawn` and the parsed shape, or an index into it;
- `double phase0`;
- `char starts`;
- the drawn engine's state: `lv[32]`, the levels of the random points this
  pass, `segI` and `segA`.

### `lfoStep`

**Unchanged when `!drawn`.** That is the whole of the claim that old setups
load unchanged: the path they take is the same code.

**When drawn**, the phase runs exactly as now (the same increment and the same
wrap at 2π). The shape is read at `u = cycleOf(phase) + phase0`, less 1 at or
past 1.

Do not compute it as `fmod(t + p, 1) + 1` and so on. That adds 1 and loses a
small `t`'s low bits. The mockup's saw twin was 2.2e-16 off until this was
changed, and the check caught it.

Each sample:

1. Find the points passed since the last sample. Across the wrap, that is
   those after the old `u` and then those up to the new one.
2. For each point passed, in order:
   - a random point **after a hold or a jump** takes its new level now:
     `(random() * 2 - 1) * reach`. The draw is `lfoStep`'s and the reach
     multiplies it after, so at a reach of 1 it is exact. A random point sits
     at nought until its first level is drawn, as today's `held` does;
   - the line from the point starts at the point's level (`segA`);
   - if the next point is random and the line to it is a curve or straight,
     the next point takes its new level now, so the line aims at where it will
     land.
3. Read the level by the law.

Under this rule one random point, held, draws from `Random` at the same sample
as `lfoStep` draws `held`. So a drawn Random steps is today's Random to the
bit. Rolling one line early is the null, and differs by 0.16. A reach of 0.3
is today's levels times 0.3, to the bit, and never past ±0.3. A reach of
nought, the null, is still.

**Cost.** A segment change costs a short scan of at most 32 points. A read
costs one `cos`, for an S, or one `exp` (`pow`), for a curve. That is per
sample, for two LFOs: well under a voice's envelope.

### Retriggering

- **Each note**: on note-on, `phase = 0`, then the drawn state is
  re-initialised from the drawn levels at `u = phase0`.
- **Each phrase**: the same, only when no other key is down.
- **Tempo**: restarts on the beat through `Clock::locks`, as now.

### `restore.h`

- `moveSlider` and `controlChange` for `lfoShape<i>` learn `drawn`.
- The Phase knob and the Starts switch are new controls.
- The routing grammar does not change, because nothing routes to a point.
- `MORPH_SKIP` should take `l<i>m` and `l<i>t`.
  - The morph should walk Phase as a knob.
  - For two shapes it should do what `msegBlend` does: blend point by point
    when they have as many points with the same laws, and snap at half-way
    otherwise.

### The schema and the hosts

- `write_schema.py` after `SETUP_FIELDS` gains the three fields.
- No host parameter changes. Whether LFO 1's Rate should be one is a question
  for the owner, not decided here.

## How it is tested

### `core/tests/pieces/lfo_drawn.py`

Each check with its null:

- **Today's five through `lfoStep` beside their twins through the drawn path**,
  over a grid of rates (0.01, 0.37 and 7.9 Hz) at 44.1 and 48 kHz:
  - the saws, the square and Random equal to the bit;
  - the sine within 1e-12;
  - the triangle within 1e-7.
  - Nulls:
    - the sine drawn straight (off by 0.21);
    - the random point rolled a line early (0.16);
    - a quarter of Phase (1.41).

  The mockup runs this check in the page's JavaScript against `lfo.h`'s
  arithmetic, ported line for line with the core's `Random`. It found the
  0.21, the 0.16 and the 2.2e-16 above.
- **A random point after a curve** reaches its level on time.
- **Phase** reads where it says. Its null: Phase not added.
- **Each note** restarts on every note and **Each phrase** on the first of a
  legato run. The null: free never restarts.
- **Adopting** is continuous: the twin swapped in mid-cycle, with no step
  over 1e-12.

### `golden`

- **No recording changes.** Nothing old takes the new path, so
  `core_tests.py` runs without `--write-golden`.
- One new scenario, a drawn LFO with a random point on a routing, recorded with
  `--because`.

### The face (`web/tests/`)

A suite for the editor, by real mouse:

- drag, add and remove;
- the menu;
- the twin adopted on the first drag (null: before it, the shape is today's);
- the card's path against the shape (null: the saw down's card against the
  saw up's levels);
- the dot on the line (null: half a cycle on);
- the fit at the six windows (nulls: two columns are a tower; a drawing held
  at 2.4:1 regardless leaves no routing in sight at 1200x680);
- nothing moves across the states above (null: a reading sized to its words).

`fittest.py`, `modrowtest.py` and `patchtest.py` gain the editor. The words go
through `what-each-control-says.md` and `write_words.py`.

### `designtest.py`

No new colour token: the mockup uses the inks, gold, blush and the line, as
they are.

## Decided (19 Nov, the owner)

The build follows these:

1. **Random has a reach.** A random point's drawn height sets how far it may
   land, either way of nought. A reach of 0.2 is a gentle wander.
   - Full reach must reproduce today's Random to the bit. The mockup's checks
     hold it, from the same seed at three rates and two sample rates, with a
     reach of nought as the null.
   - The build's `pieces/lfo_drawn.py` keeps that check.
2. **The square stays at ±0.9**, today's, as preset and twin.
3. **The S-curve stays a law of its own** (half a cosine), beside the
   envelopes' one-pole curve. It is not moved into the envelopes.

## Open for the owner

1. **LFO 1's Rate as a host knob.**
