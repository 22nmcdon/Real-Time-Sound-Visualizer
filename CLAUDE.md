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
it is believed. This repository has shipped three of them, and each is now
commented at the site with what it used to assert and why that was not enough:

- Asserting a modulation offset was *set*, while nothing read it.
- Comparing rendered output between two runs that differed for reasons of their
  own — twice, two different ways.

Before trusting a new test, **break the code and watch it fail.** If it does not
name the fault, it is not testing it.

Prefer numerical assertions to visual ones. "50 ms is 2205 samples at 44.1 kHz",
"the JS biquad matches Web Audio to 0.0001 dB", "the limiter turns 17.26 into
0.961" — these survive a redesign; a screenshot does not.

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
- **Neither bench panel may scroll.** Also a test, across every generator mode.
- **Controls are moved between views, never copied.** Two elements with one id
  is how the dock's readout line silently stopped displaying for weeks.

## Before saying you are done

- The full suite passes, and you have said so with the number of checks.
- `web/README.md` gained an entry if you learned something a future reader would
  otherwise rediscover.
- The cheat sheet inside `scope.html` still describes what the app does. It is
  user-facing documentation and it goes stale first.
