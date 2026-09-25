# Working in this repository

Two builds of one instrument. `web/scope.html` is the live one and where work
lands first; `oscilloscope-poc/` is a native Python/PyQt6 build of the same
thing. Read `web/README.md` before changing the web build — most of it is a list
of things this page has already got wrong once, each with the reason, and it
will save you rediscovering them.

## Always

**Run the tests.** Not a subset at the end — the suite is fast enough to run
while you work, and it is the only thing standing between a subtle change and a
silently broken instrument.

```
python3 web/extract.py && node --check web/tests/check.js   # syntax, seconds
python3 web/tests/run.py                                    # everything, ~6 min
python3 web/tests/run.py lane patch                         # just those
cd oscilloscope-poc && python -m unittest discover -s tests
```

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
it is believed. This repository has shipped seven of them, and each is now
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
  it.** Two designs failed here. `patchtest.py` measures the row's height and
  box with nought, one, two and three sources and requires all four identical.
- **No Bench tab may scroll.** The Bench is five tabs by task (Play, Picture,
  Shape, Sources, Measure), and one tab at a time must fit. `patchtest.py`
  measures every tab across every generator mode; `racktest.py` does it with a
  rack of six lanes. This replaced "every section on show at once, and neither
  panel scrolls", which held for the tone and never for a rack - and is why a
  section that would crowd a tab goes to another one (Lanes is on Picture
  because Play had four sections for three columns).
- **Every section has one home.** `data-home` is `settings` (set once and left:
  MIDI, Audio, Presets, Beam) or `bench` (everything played or tuned), and a
  section stays in its home in both views. Settings and the Bench used to hold
  the same sections, which made neither a place for anything. To reach a
  control from code - a search result, a test - use `showControl(id)`; do not
  assume the Settings popover holds it.
- **Controls are moved, never copied.** Between a tab and the hidden store,
  into a section's detail overlay and back. Two elements with one id is how the
  dock's readout line silently stopped displaying for weeks.

## Before saying you are done

- The full suite passes, and you have said so with the number of checks.
- `web/README.md` gained an entry if you learned something a future reader would
  otherwise rediscover.
- The cheat sheet inside `scope.html` still describes what the app does. It is
  user-facing documentation and it goes stale first.
