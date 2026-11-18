# Envelopes as drawn shapes (MSEG): a design

17 Nov. The owner's direction: envelopes as versatile as Serum 2's, drawn
multi-segment shapes rather than ADSR with curves; every shaping feature a
small clear **preview block** on its tab that opens a larger editor; and three
complaints fixed - the sustain feels dead for small moves and drastic for
visible ones, there is not enough room to work, and the voice filter cannot be
read (its envelope amount does nothing at nought while the drawing looks live,
and its popover covers its Type menu).

18 Nov, after three rounds of mockups, the owner chose the design below. The
chosen one is `web/docs/mockups/mseg/popover.html` as it opens (take 2,
straight amplitude, small block a, the filter's block with its envelope),
with screenshots and its checks beside it. The earlier rounds stay for the
record and are superseded where they differ: `index.html` (the editor over
the tabs, the level drawn in decibels, Delay and Hold as tabs, a shaded held
band) and `alternatives.html` (four places for the editor). This note is how
it would be built. Nothing in `scope.html` or the core has changed.

It acts on the loop (`making-it-one-instrument.md`'s first rule): the amp
envelope is how a note strikes the screen and comes to rest, which is what
the two preset headings, *Settled* and *Breathing*, are measured on. A loop
held under a key is a new way for a held chord to keep breathing.

## The chosen design (18 Nov)

- **On Play**, the Amp envelope and Voice filter sections become small blocks.
  - **The amp's block** is the shape and nothing else: one line with a faint
    fill, time on the square-root scale (each stretch as wide as the root of
    its time, so an 8 ms attack has a slope), the level in straight amplitude
    (a -3 dB sustain sits at seven tenths, the ADSR anyone knows), the held
    part a short plateau, and a gold dot riding it while a note sounds. No
    grid, letters, values, dots, band or axis words. Its four readings
    (attack, decay, sustain in dB, release) sit in a row under it.
  - **The filter's block** keeps its Type menu, its response from 20 Hz to
    20 kHz with the shaded band its envelope sweeps (no point, no dashed
    edge), the three readings under it, and its envelope small beside the
    words *Its envelope · sweeps +1.5 oct*, in the same plain style, grey
    and saying *does nothing* while the amount is nought.
  - Play keeps room to spare at both windows (measured on the page).
- **The editor is a popover beside its block**, over the neighbouring column
  at the columns' full height, its arrow pointing at the block it came from:
  over Expression for the amp envelope, over the Generator's column for the
  filter. It never covers its own block, the keyboard band or the screen.
  *Esc*, *Close* or a press outside closes it. This replaces the editor over
  the tabs, which the owner found too large.
- **Inside it**: the name and *Close*; a line of tools (the shape presets,
  *Loop*, *Hold a note*; the type switch for the filter); the drawing; and
  **the six knobs always, one row of small knobs at the bottom** (the
  filter's four over its envelope's six). No toggle for the knobs.
- **The drawing is quiet**:
  - Time on the square-root scale, as the block. There is no millisecond
    ruler: the times are in the knobs' readings and in the readout beside the
    handle being dragged.
  - The level in **straight amplitude** (see below), with three level lines
    only, labelled at the left: 0 dB, -6 and silence for the amp envelope;
    100, 50 and 0 per cent for the filter's.
  - No frame and **no held band**: the sustain runs on dotted to a small tick
    on the foot marked *key up*, where the release starts.
  - Round handles for the points and the bends, and a soft fill under the
    curve.
  - **Delay and Hold are rings on the curve**, not labelled tabs: Delay where
    the silence ends, Hold where the peak ends (just right of the peak while
    it is nought). They show while the pointer is over the drawing, while
    one is held or focused, or once its time is not nought.
  - Every gesture of the first round is unchanged: drag a point, double-click
    the line to add one and a point to remove it, drag a bend, right-click or
    long press or Shift+F10 for the menu, the arrows and Delete.
- **The Envelope card's editor** is the same popover, opened from its card;
  dashed and grey while it follows the amp envelope, solid in its sage once
  edited.

## The level axis and the sustain

The drawing shows the amp envelope's level in **straight amplitude**, as
Serum 2 does: a -3.1 dB sustain sits 30 per cent of the way down, the decay is
a visible curve and the release a smooth fall. The first two rounds drew it
in decibels, which put that sustain 6.5 per cent down a 48 dB axis and made
the release drop its last 20 dB in its last eighth of time - a box with one
rounded corner and a cliff, since a decibel drawing of an envelope that ends
at silence always ends in one. What straight amplitude costs: quiet levels
are crushed to the foot (-30 dB is 3 per cent of the height), so a shape that
lives below -20 dB is hard to draw finely. The mockup keeps a switch to the
decibel drawing for comparison; whether the instrument keeps it is open.

**The Sustain knob turns in decibels** (-60 to 0, its bottom silence), so the
top quarter of its travel is the top 15 dB rather than the top quarter of the
amplitude, which is the complaint about it fixed. The readings and the
readout beside a dragged handle are in decibels too. The knob is a loudness
scale; the drawing is a picture of the shape.

**Nothing stored changes.** The sustain stays the linear level the engine
multiplies by (`sus`, percent of full scale, as now); only the knob's law and
the drawing change. So every saved setup loads to the bit, and no decode pass
is needed for it: the field still has one answer, a level. The knob writes the
linear value for the decibels it shows, so a value it writes need not be a
whole percent; the setup field takes a number already.

The filter's envelope and the Envelope card are linear too, nought to the
whole amount: what they move is already on a musical scale (octaves of
cutoff, a modulation depth).

## How a shape is stored

Each envelope keeps its knobs as they are, and gains one field for its shape:

| Envelope | Knobs (macros) | New fields |
|---|---|---|
| Amp | `atk dec sus rel` (as now) | `envDelay`, `envHold`, `envShape` |
| Filter | `vcfAtk vcfDec vcfSus vcfRel` | `vcfDelay`, `vcfHold`, `vcfShape` |
| Envelope card | `menvAttackMs ... menvReleaseMs` | `menvDelay`, `menvHold`, `menvShape` |

and the upper hand's twins of each (`bEnvShape`, `bEnvDelay`, ... as the B
fields are named now), linked and unlinked by `linksSettle` exactly as the
four are.

**The shape is relative to the knobs.** It holds, for each stretch (delay,
attack, hold, decay, release), the points inside it as *share of the stretch's
time, level, bend*, and the bend of the stretch's last segment; the knobs hold
each stretch's length and the sustain level. The anchors - the peak at full
scale, the sustain point at `sus`, silence at the start and the end - are not
stored as points. That is what makes the knobs still mean what hosts, presets,
undo, the morph and modulation think they mean:

- **A time knob** is its stretch's length. Turned, every point inside keeps its
  share of the stretch and its own level.
- **Sustain** moves the sustain point's level and nothing else; points you
  added keep theirs.
- **The points** are reached by a setup, a preset and undo only. No host
  parameter, routing or morph reaches a point.

The field is a short string, so a setup code stays text:

```
1;A>p.2;D>p.2;R>a.2                      the old envelope (the decode pass writes this)
1;A>m.62;D.4,.18,m.72>m.3;R.35,.35,m.65>a.2;L3   points in the decay and release, a loop
```

Version first; then a block per stretch that is not plain (`W` the delay, a
wait, `A` attack, `H` hold, `D` decay, `R` release), its inner points
`u,level,bend` with `level` linear to five significant figures, `>` and the
closing bend; `L<n>` a loop from the shape's n-th point; absent blocks are a
straight segment with no points. Bends: `m<mid>` a drawn midpoint (0.1 to 0.9,
three decimals), `p<rho>` an aim past the end as a share of the drawn fall,
`a<r>` an aim past the end in full scale, `l` straight. At most 32 points an
envelope, so the worst case is under 600 characters, typical well under 100.

### The decode pass, and how it is proved

A purely additive field would need no version bump, since an absent shape could
simply mean the old one. It gets one anyway (`kSetupVersion` 12, in the
core's `migrateSetup`): the pass writes `1;A>p.2;D>p.2;R>a.2` into every older
setup's three shapes and both hands. The reason is to keep the meaning of an
**empty** shape free - a new sound's default bends can then be chosen by ear
later without changing a saved one.

The old curves are exact in the new law (below), so the claim is **every
preset, code and project from before sounds the same to the bit**. It is
proved three ways:

1. **The recordings.** `core_tests.py` without `--write-golden`: every golden
   scenario, recorded from the page's JavaScript and the core since, must pass
   unchanged. No `--because` is written, because nothing is meant to change.
2. **A piece, sample for sample** (`core/tests/pieces/mseg.py`): the old
   `Envelope` class, kept in the tests as the reference, against the new engine
   given the decoded shape, `memcmp` over a grid of the four numbers (each at
   its ends and middle, the sustain at 0 and 1 included), with the key let go
   in each stage, retriggered in the release, a legato note on an open one, a
   knob moved mid-stage, and at 44.1 and 48 kHz. Its nulls: the release's aim
   made relative (`p.2` for `a.2`), which misses as soon as a key comes up
   before the sustain (0.023 of full scale in the mockup's check), and the
   attack's bend as the midpoint 0.710 rather than the exact aim, which misses
   by rounding.
3. **The face.** `core_tests.py`'s face-to-core runs carry a setup with a shape
   through the module the page carries, so the page and the plugin read one
   string one way.

The mockup's own check (`checks/curves_against_core.py`) already holds the
drawing to the core's `Envelope` and found one thing the engine must keep:
the old envelope ends a stage on the first sample at or past its end, which
after rounding is sometimes **one sample after the drawn time**, and a note
let go after that carries the sample's difference into its release (6.4e-5 of
full scale at worst). The new engine therefore runs the same recursion and the
same end test, not the analytic curve the drawing uses.

## The curve law

Every stretch is the core's one-pole, as the envelope is now: it travels from
its start towards an aim a little past its end and arrives on time,
`v += (aim - v) * pole` with `pole = 1 - exp(-span / samples)`. The old
envelope aims a fifth of the attack's and decay's fall past their ends and 0.2
of full scale under silence for the release; those are the `p.2` and `a.2`
bends. A drawn bend is a midpoint `m`, the level reached half-way as a share of
the fall - the fade drawing's rule, *what is dragged and what is stored are one
number* - and becomes an aim by `k = 2 ln(m / (1 - m))`, `rho = 1 / (e^k - 1)`.
The old curves sit at a midpoint of 0.710; `m = 0.5` is straight.

It was chosen over the fade's power law (`fadeTravel`, `t^p`) because the old
four numbers become a shape exactly; it costs what the engine costs now; and
every corner has a finite slope, where a power law starts a slow curve flat and
a quick one vertical, which an amplifier hears as a click. It has a property
the editor uses: a one-pole forgets where it started, so **a point added on the
line changes nothing** if the two halves keep the whole's aim (the mockup does
this, and checks it to 2e-16 with a null that misses by 0.09). Its cost: the
app then has two bend laws at the same midpoint (they differ by up to 0.06 of
the fall at 0.9). Moving the fade to this law is an open question.

**Entered from anywhere else** - a release while the attack is still rising,
the first stretch after a loop's marker, a retrigger during a release - a
stretch keeps its time and its aim and travels from where the level is. That is
the old `enterStage` rule (span recomputed from the current value), generalised,
and it is why a loop never jumps. Two edge cases the old envelope never met:
for a slow-start bend the aim lies *behind* the start, and a level entered from
behind the aim cannot reach the end by the law, so that stretch goes straight
from where it is; and a stretch entered already past its end jumps to it, as
the old one does.

## What the engine needs

A new class beside `Envelope` in `core/include/scope/envelope.h` (`Mseg`), the
old one kept as the tests' reference. Per voice (the amp and filter envelopes
are per voice in `voices.h`, the card's is the generator's own):

- **State:** the stretch and segment it is in, the level, the aim, the span,
  the velocity, whether held, the loop's pass. About 48 bytes a envelope.
- **The shape** is parsed once into a flat table of segments (time share,
  level, aim law) per hand, shared by every voice, rebuilt when the setup
  changes; a voice holds an index into it. Times are read from the knobs per
  sample, as `poleFor(tone_->attackMs)` reads them now, so a knob moved or
  modulated mid-note acts mid-note.
- **Sustain:** the segment index of the sustain point; while held and there,
  the level holds (as `Stage::Sustain`), unless a loop is set.
- **Loop:** at the sustain point while held, back to the marker's segment,
  entered from the current level.
- **Release from any point:** the release's first segment entered from the
  current level, keep-aim.
- **Retrigger and legato:** unchanged - a note on an open envelope changes
  nothing (`gate`'s legato rule); a note in the release restarts the attack
  from where the level is; the card's *Every note* restarts it as `menvGate`
  does now.
- **Delay and hold:** two more stretches, the delay at silence, the hold at the
  peak; at nought they cost a skipped segment.

**Cost:** the same as now in the common case - one multiply-add and the
`exp` in `poleFor` per sample per envelope (the `exp` can be cached while the
knob's time is unchanged, which the old one does not do and could). A
segment change costs a `log` for the span, as a stage change does now. With
16 voices, two envelopes each, 48 kHz, that is the 1.5 million `exp` a second
it already is; a 32-point shape adds only segment changes.

## Modulation, hosts, the plugin

- **Modulation** reaches the six knobs and nothing else, so its routings and
  `modB` depths keep their grammar. A routing on Decay scales the decay
  stretch, points and all; on Sustain moves the sustain point. The new Delay
  and Hold knobs are new destinations, offered where the others are.
- **Hosts** see what they see now (the 15 `kKnobs`, none of them an envelope's).
  Whether Attack and Release should become host knobs is a question for the
  owner, not decided here.
- **The plugin's state** carries the shape inside the setup, as it carries
  every field; nothing beside it (`pluginOutput` and `pluginWindow` stay the
  only things that are not the setup's).
- **Undo** records the setup, so a point's drag is one step on release, as a
  knob's is. **The morph** moves the knobs; between two different shapes the
  points need a rule (open question).
- **The info line and the cheat sheet** gain the editor's words through
  `what-each-control-says.md` and `write_words.py`.

## How it is tested

- **Core pieces** (`core/tests/pieces/mseg.py`), each check with its null:
  the old envelope to the bit (above); a drawn shape's segment times to the
  sample at 44.1 and 48 kHz (null: the end test removed, one sample out); an
  added point changing nothing (null: halves given the whole's midpoint); a
  loop's level continuous across its jump (null: re-entered from the drawn
  start, a step); a release from mid-attack from the current level (null:
  from the sustain); the knob scaling a stretch's inner points (null: points
  stored in milliseconds, which stay put).
- **Golden:** no recording changes for the migration; a new scenario or two
  with a drawn shape and a loop, recorded with `--write-golden --because`.
- **The face:** a suite for the editor in `web/tests/` (points dragged,
  added, removed by real mouse; the right-click menu; the level axis by numbers
  as the mockup's table does; the follow rule); `fittest.py` and `patchtest.py`
  with the blocks in place of the sections at the five windows;
  `designtest.py` (no new colour token: the mockup uses none).

## Later: the LFOs

The same engine with the sustain point at the end, the loop over the whole
shape and no release is Serum's drawn LFO: free-running or restarted by a note,
in hertz or synced. The LFO cards would draw it and open the same editor; the
stored form would be the same string in a new field per LFO (`lfo1Shape`),
additive. Nothing here commits to it, and nothing here closes it off.

## Open questions for the owner

1. **The times' ranges.** Today the attack stops at 200 ms, the decay at 1 s,
   the release at 2 s. A drawn shape wants longer; the mockup uses 20 s for the
   three and 5 s for delay and hold, on the drawing's square-root scale. Widening
   is additive for stored values, but every knob's travel per millisecond
   changes.
2. **The peak:** fixed at full scale (as drawn, so velocity and Level stay the
   loudness), or a point like any other?
3. **The sustain point:** movable to another point, or switchable off so a
   shape plays through regardless of the key (a one-shot)?
4. **The morph** between two different shapes: snap at half-way, or move the
   points when they are as many?
5. **One bend law:** should the fade's drawing take this one?
6. **Host knobs:** should Attack and Release (or the Sustain) join `kKnobs`?
