# Working in this repository

One instrument, two faces. `web/scope.html` is the live one and where work
lands first; `plugin/` is the instrument as a JUCE plugin with the page as its
UI, over `core/`, the C++ core shared by the plugin and (as WebAssembly) the
site - read `plugin/PLAN.md` before touching either. The plugin is the
product and the site its interface and demo. Where it is going is
`web/docs/making-it-one-instrument.md`: read that before adding anything,
because its first rule is that a feature has to act on the loop it describes.
(A native Python/PyQt6 build, `oscilloscope-poc/`, was retired in that plan's
P0; it is in the history.) The core is a port held to the page sample for sample by
`core/tests/parity.py`; a ported piece is not done until it passes that, with
its nulls. How it looks is `DESIGN.md`: which parts are the brand it shares with the
jazz and guitar learning apps (not this repository's to change alone) and which
are the oscilloscope's own. A new colour token goes into one of its tables, or
`designtest.py` fails. Read `web/README.md` before changing the web build — most of it is a list
of things this page has already got wrong once, each with the reason, and it
will save you rediscovering them.

## Always

**Run the tests.** Not a subset at the end — the suite is fast enough to run
while you work, and it is the only thing standing between a subtle change and a
silently broken instrument.

```
python3 web/extract.py && node --check web/tests/check.js   # syntax, seconds
python3 web/tests/run.py                                    # everything, ~37 min
python3 web/tests/run.py lane patch                         # just those
python3 web/tests/run.py -j1                                # one at a time, ~43 min
python3 core/tests/parity.py                                # the C++ core against the page
python3 core/wasm/build.py                                  # after any change to core/: the page carries it compiled
python3 core/tests/tools/write_schema.py                    # after any change to SETUP_FIELDS: the core reads setups by it
```

Every suite in `run.py` says whether it is `parallel` or `serial - why`. The
serial ones judge time and run first, alone; the rest run three at a time
after. A new suite that measures anything over real seconds, a cost in
milliseconds or a rate is serial; when in doubt, serial.

`web/scope.html` is one file with the script inline. `extract.py` lifts the
script out so `node --check` can parse it; do that after every edit, because a
syntax error in a 350 KB single-file app is otherwise found by a blank page.

## Editing an 8,000-line single file

Large edits are usually easiest as a small Python script doing exact string
replacements with an assertion that each anchor appears exactly once.

**If you write one, write the file after every replacement, or make the script
idempotent.** A script that does ten replacements and writes at the end loses
all ten when the seventh assertion fails — which looks exactly like the edit
having been applied, because the earlier ones printed "ok". That happened three
times in one session and shipped a bug: the edit that made `trig.position`
actually move the window was lost this way and nobody noticed for two releases,
because the test only asserted the offset was *written*.

Watch for two more:

- An anchor string ending in a space, or containing `*/` inside a `/* */`
  comment you are inserting. Both fail silently or break the parse.
- Index-based splices computed from `s.index("/* --- section")` when that
  comment appears twice — once in the stylesheet and once in the script. Check
  which one you found.

## Tests

The rule that matters: **write the test against the failure, not the happy
path.** A test that passes whatever the code does is worse than no test, because
it is believed. This repository has shipped eight of them, and each is now
commented at the site with what it used to assert and why that was not enough:

- Asserting a modulation offset was *set*, while nothing read it.
- Comparing rendered output between two runs that differed for reasons of their
  own — twice, two different ways.
- Reading a verdict from a *stopped* scope, which reports "held" before it has
  looked at a sample, so no assertion about clipping could fail.
- Comparing a ring buffer against a snapshot 600 ms later, on a 220 Hz tone —
  132 whole cycles, so the two windows were identical by construction.
- Turning the captured lanes by the rotation *itself* before measuring the
  angle, which answers 45 degrees for any two arrays and never reads the app.
- Indexing rendered audio from `frames / 2` — 5512.5, so every read was
  `undefined`, every difference `NaN`, and `Math.max` carried the NaN to the
  end while the code under test behaved perfectly.
- Judging each waveform shape on one output block that was never cleared
  between shapes, so a shape whose branch threw was judged on the previous
  shape's samples, and a drawbars branch missing its table passed as a saw.

### Null-test every new assertion

The last four of those were found by luck rather than by method, and two of them
in consecutive stages. So: **before trusting a new check, feed it one
known-wrong value on purpose and watch it fail.** Not "break the code
eventually" — do it as the check is written, the way a null test proves an
instrument can read non-zero before its zero reading is believed. The cheapest
form is usually a literal: assert against `0`, or the unrotated array, or the
value from the other branch, and confirm the check goes red. A check that has
never been seen to fail is a check whose failure mode is unknown.

Mutation testing the *code* is still required before saying a piece is done,
and it is what catches the rest. But a mutation pass only proves the suite as a
whole is sensitive; it does not prove that the check you just wrote is the one
doing the work, and twice now a passing check has been carried along by its
neighbours.

### Fixtures have to be able to show the effect

A test signal that is symmetric under the transform being tested cannot see it.
Discovered twice, independently, for the same transform: **a fixture for a
rotation-sensitive check must be asymmetric — never a circle and never a
quadrature pair.** Rotating a circle leaves every statistic of it unchanged:
peak, RMS, correlation, principal axis, spectrum. The default `b:Circle` preset
and a sine-against-cosine stand-in are both invisible to rotation, so those
checks use a diagonal line (both channels the same signal) or two copies of one
signal at 45 degrees, where the effect is 41 per cent and obvious.

The general rule behind it: before writing the fixture, ask what the transform
leaves alone, and make sure the signal is not that.

Prefer numerical assertions to visual ones. "50 ms is 2205 samples at 44.1 kHz",
"the JS biquad matches Web Audio to 0.0001 dB", "the limiter turns 17.26 into
0.961" — these survive a redesign; a screenshot does not.

### A field that stops having one answer becomes a structure, with a migration

Three times now a single stored value has turned out to be answering a question
that had grown a second answer, and each time the fix was the same shape:

- The modulation destination was an **integer index** into an array, which is
  fine until the array is reordered and every saved setup means something else.
  It became a string id and a matrix.
- The trigger level was an **absolute amplitude**, which stops meaning anything
  once full scale is a continuous, modulatable gain. It became a fraction of
  full scale, with a version-2 decode pass for codes that stored the old thing.
- `state.source.kind === "tone"` asked **which one of four** the source is,
  which stops being answerable once the generator can be one lane of a rack. It
  became `genSettings` / `genSet` / `genReswing` — where does the generator
  live, rather than what is the source.

So: **when a field can no longer answer its own question with one value, widen
the representation and write the migration, rather than widening the `if`.** The
tell is a condition growing an `||`, or a call site asking "which kind is it"
in order to work out where to write. Both are the field having become a
structure without anyone saying so.

Two parts to doing it properly. The *representation* changes — a new field, an
id, a helper that answers the real question — and anything already stored in
the old shape gets a **version-tagged decode pass**, not a value that is
interpreted two ways depending on its magnitude. `migrateSetup` runs them in
order and `SETUP_VERSION` names where you are; a purely additive field needs no
bump, because `Object.assign` over the defaults already gives an old code the
new default.

The third of these needed no stored-format migration, and it is worth saying
why so nobody goes looking for one: a setup code has never recorded which
source is loaded — it stores the generator's *mode* and the trigger lane, and a
preset lands on whatever you are playing. So the remaining selector work is a
change to the interface, not to anything saved.

## House style

Comments explain **why**, not what, and are written in prose. British spelling
in prose (`colour`), CSS keywords unchanged (`color:`). ASCII hyphens rather
than em-dashes inside code comments; real punctuation in Markdown.

When a decision could reasonably have gone the other way, say which way it went
and what it cost. When something is a known limitation, say so where a reader
will hit it rather than in a changelog.

Commit subjects are a sentence in the imperative, no prefix or ticket, naming
the change in the instrument's own terms rather than the code's — "Put a backing
track and your playing on one graticule", not "feat: add rack live lane". The
body is prose, and it is the right place for the reasoning, the alternatives
rejected and the bugs found on the way.

## Git

Work on the branch you were given and push there. Do not open a pull request
unless asked. The default branch is currently the working branch, so a push
publishes: GitHub Pages serves `web/scope.html` straight from it.

## Layout decisions already made

Do not re-litigate these without a reason; each replaced something that failed.

- **The bench body uses real column elements, not CSS `columns`.** Multi-column
  re-balances the whole flow when any section's height changes, which moved a
  control out from under the pointer mid-drag.
- **A control's appearance must not depend on how many modulation sources are on
  it.** Two designs failed here. `patchtest.py` measures the knob's cell - its
  box, and where its face and reading sit - with nought, one, two and three
  sources and requires all four identical; the editor's button sits at the
  face's shoulder, out of the flow.
- **The Bench's controls are knobs over their range inputs** (P8c, from the
  owner's Headroom). The input stays the value, the keyboard and what every
  test and host knob writes; the face follows it through a setter on the
  input, so a value written from code turns the face with no event. Knobs
  that come together are cells read down - setting, knob, name - and a knob
  alone among menu rows is one line, since as a cell it stood taller than the
  slider it replaced. The drawbars, the setup morph's crossfader, the strip
  under the screen and the editor's depths stay sliders. `knobtest.py` holds it.
- **No Bench tab may scroll.** The Bench is three tabs along the loop - Play,
  Ink, Space & Memory, in the order the sound goes round it (the Picture tab
  went in F2: its knobs are the Picture section along the bottom) - and the
  drawer's Sources, Inputs and Perform, and one tab at a time must
  fit. `patchtest.py` measures every tab across every generator mode;
  `fittest.py` does it in every combination of generator kind, tone or band
  split, keyboard and Photocell, and the Sources tab with each family on show.
  This replaced "every section on show at once, and neither panel scrolls",
  which held for the tone and never for a rack of six (cut in P5), and then
  five tabs by task (Play, Picture, Shape, Effects, Measure), which existed
  because Shape overflowed into Effects; after P5's cuts and the drawer they
  were a third full in places, so P8 (`making-it-one-instrument.md`) put them
  back in the loop's order. A section that would crowd a tab still goes to
  another one. The Picture section along the bottom of the window (F2) holds
  the Amount, Scan, Strike, Softness, the one Persistence and the three reads,
  in either view and on every tab; what Scan reads, the photocell and the
  score are behind its *Advanced*, with the loop overlay and the panes, which
  only change the look (home `picture`). The display and Clear are above the
  screen.
- **What is not the loop goes in the drawer.** *Advanced*, under the rail,
  opens it; shut, it takes its tabs, the source chips beside the screen and a
  control's hollow ring with it, and leaves everything patched playing and
  shown. It is a view, remembered per viewer and never in a setup, and going
  to one of its tabs opens it, so `showControl` and the search need nothing
  new. The routing matrix went first (P3); in P5 the arpeggiator and the
  clock went to Perform, and the drawings - the harmonograph, the figures, the
  solids and the second generator - behind it in their menus, offered only
  while it is open unless one is already chosen (`syncDrawerMenus`); in P8
  the scope's own instruments (lanes, vertical, trigger, trace filter,
  cursors) and the setup morph to Measure (the macros beside it were cut in
  P8d, the host's knobs having replaced them), the microphone and input into the
  generator to Inputs, and the key and tempo to Perform beside the clock. F1 of
  `web/docs/redesigning-the-face.md` (7 Nov) took Measure's sections to
  *Scope & measure* (below) and the morph to Perform. Add
  a tab to it by naming it in `BENCH_DRAWER`. A tab remembered from before a
  rename lands where its sections went (`BENCH_TAB_RENAMED`). `benchtest.py`
  holds it.
- **The Sources tab shows one family at a time.** Families, the chosen
  family's sources as rows with meters, the chosen source - in that order, one
  column each. A grid of every source at once was forty chips of one weight
  and read as a wall. The list has a fixed height and scrolls inside itself,
  so what is plugged in cannot put the tab over.
- **Every section has one home.** `data-home` is `settings` (set once and left:
  MIDI, Audio, Presets, Beam), `bench` (everything played or tuned) or, since
  F1, `measure`, or since F2 `picture` (the Picture section's Advanced) - `measure` is the oscilloscope's own tools: *Scope & measure*, a panel over
  the screen opened from the toolbar above it, which also holds run, mode,
  Autoset, the trigger, timebase and zoom and the readouts' switch; shut by
  default, the readouts off by default, and nothing in it scrolls down to the
  plugin's 960x600 - `benchtest.py`), and a
  section stays in its home in both views. Settings and the Bench used to hold
  the same sections, which made neither a place for anything. To reach a
  control from code - a search result, a test - use `showControl(id)`; do not
  assume the Settings popover holds it.
- **Presets are a small bank under two headings, by what the loop does with
  a held chord** (P8g and P8h, `making-it-one-instrument.md`): *Settled* (a
  note moves the sound as it strikes the screen, and it comes to rest while
  held) and *Breathing* (it moves while held and stops when let go, or goes
  on under the sustain pedal). One menu a heading in the browser, Saved last,
  a section rail only when a heading has more than one section. The plain
  sound is not a preset: the page and the plugin open on the base
  (`BASE_SETUP`, a still sine) and *New* goes back to it. It replaced 268
  presets in three menus, which the owner liked none of, and then four
  headings, of which Wandering rested on a latch (cut: arpeggiated chords
  defeat any rule for when a latched chord gives way, and the pedal is told)
  and Open was the base dressed as a preset. `honestytest.py` measures every
  preset's sound against its heading and requires it to fail the other, and
  the base to be still; `presettest.py` requires every field a preset names
  to come back out of the setup it makes, the bank's shape (a split under
  each heading, Settled at Picture nought, Breathing with the loop at work)
  and every preset to name the Picture amount. Add a preset under the
  heading it measures as, with a line that says what to listen for and what
  to look at, then write `presets.h` (and the base) out with
  `core/tests/tools/write_presets.py`. The old library is kept whole as a
  test corpus (`core/tests/scenarios/library-p8f.json`,
  `web/tests/corpus.py`): a suite that wants a known sound under a check
  opens it from there, and one testing the preset mechanism picks a bank
  preset by what it needs, never by name - the bank is meant to change by ear.
- **Controls are moved, never copied.** Between a tab and the hidden store,
  into a section's detail overlay and back. Two elements with one id is how the
  dock's readout line silently stopped displaying for weeks.

## Before saying you are done

- The full suite passes, and you have said so with the number of checks.
- `web/README.md` gained an entry if you learned something a future reader would
  otherwise rediscover.
- The cheat sheet inside `scope.html` still describes what the app does. It is
  user-facing documentation and it goes stale first.
