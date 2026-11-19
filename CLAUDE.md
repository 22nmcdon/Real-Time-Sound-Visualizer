# Working in this repository

One instrument, two faces. `web/scope.html` is the live one and where work
lands first; `plugin/` is the instrument as a JUCE plugin with the page as its
UI, over `core/`, the C++ core shared by the plugin and (as WebAssembly) the
site - read `plugin/PLAN.md` before touching either. The plugin is the
product and the site its interface and demo. Where it is going is
`web/docs/making-it-one-instrument.md`: read that before adding anything,
because its first rule is that a feature has to act on the loop it describes.
(A native Python/PyQt6 build, `oscilloscope-poc/`, was retired in that plan's
P0; it is in the history.) The core is the only engine: it began as a port of
the page's own JavaScript, which stage 5 retired (`plugin/STAGE5-PLAN.md`), and
it is held by `core/tests/core_tests.py` three ways - to what that JavaScript
answered for every scenario, recorded while it ran (`core/tests/golden/`); the
face to the core, control for control and run for run through the module the
page carries; and each piece of the engine by its own numbers
(`core/tests/pieces/`), each check with its null. A change that means the sound
to change rewrites the recordings with `--write-golden --because "why"`, which
refuses without a reason and logs it (`core/tests/golden/README.md`). How it looks is `DESIGN.md`: which parts are the brand it shares with the
jazz and guitar learning apps (not this repository's to change alone) and which
are the oscilloscope's own. A new colour token goes into one of its tables, or
`designtest.py` fails. Read `web/README.md` before changing the web build — most of it is a list
of things this page has already got wrong once, each with the reason, and it
will save you rediscovering them.

## Always

**Run the tests.** While building, run the suites near the change, as often as
you like. Before anything reaches `testing` - a push there publishes the testing site
(see Git, below) - run the whole web suite **and** the core's tests, once per batch of stages rather
than once per stage (the owner's call, 10 Nov: a batch costs one wait, and the
cost is that a failure has more candidates). Changes that cannot alter behaviour
- docs, design notes, the info line's words, whose own suite checks them - merge
after the suites that read them. Any change to `core/`, or to anything the core
shares with the page (a setup field, a slot, a slider's place in the markup),
runs the core's tests before it merges, however small: twice in one day the web
suite was green while parity (as `core_tests.py` was called then) was not,
because the web suite runs the page whole and the page agrees with itself. And do not narrow the full run to the suites you think
are affected: on this one-file page that guess was wrong about half the time on
9 Nov (a layout change broke the plugin's checks; a glide change exposed a
harness the wash fix had broken a day earlier).

```
python3 web/extract.py && node --check web/tests/check.js   # syntax, seconds
python3 web/tests/run.py                                    # everything, ~40 min
python3 web/tests/run.py lane patch                         # just those
python3 web/tests/run.py -j1                                # one at a time, ~43 min
python3 core/tests/core_tests.py                            # the core: against its recordings, the face, and its own numbers, ~25 min
python3 core/tests/pieces/run.py [name]                     # the engine's pieces by their own numbers, a minute (core_tests.py runs them too)
python3 core/tests/core_tests.py --write-golden --because "why"   # after a change that means the sound to change: rewrite the recordings from the core, the reason logged; core/tests/golden/README.md
python3 core/wasm/build.py                                  # after any change to core/: the page carries it compiled
python3 core/tests/tools/write_schema.py                    # after any change to SETUP_FIELDS: the core reads setups by it
python3 web/tools/write_words.py                            # after any change to web/docs/what-each-control-says.md: the info line's words
```

In a cloud session, set `CHROME=/opt/pw-browsers/chromium` for every browser
suite and the core's tests: the path the suites default to does not exist there, and a
run without it fails in a minute and a half. The cloud environment's setup
script installs the plugin's WebKit and GTK headers and the compiled core's
wasm32 toolchain, and clones JUCE at the plugin's tag into `/opt/juce-<tag>`,
which `plugin/CMakeLists.txt` uses when no `SCOPE_JUCE_DIR` is given - so a
plugin build in a new session needs no fetch.

Every suite in `run.py` says whether it is `parallel` or `serial - why`. The
serial ones judge time and run first, alone; the rest run three at a time
after. A new suite that measures anything over real seconds, a cost in
milliseconds or a rate is serial; when in doubt, serial.

`web/scope.html` is one file with the script inline. `extract.py` lifts the
script out so `node --check` can parse it; do that after every edit, because a
syntax error in a 2.7 MB single-file app (1.2 MB of it the compiled core, as
base64) is otherwise found by a blank page.

## Editing a 26,000-line single file

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
it is believed. This repository has shipped seven kinds of them (the second
twice), and each is now
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
  live, rather than what is the source. (`genReswing` went with the page's
  own tone source in stage 5; the instrument restarts its own phases.)

So: **when a field can no longer answer its own question with one value, widen
the representation and write the migration, rather than widening the `if`.** The
tell is a condition growing an `||`, or a call site asking "which kind is it"
in order to work out where to write. Both are the field having become a
structure without anyone saying so.

Two parts to doing it properly. The *representation* changes — a new field, an
id, a helper that answers the real question — and anything already stored in
the old shape gets a **version-tagged decode pass**, not a value that is
interpreted two ways depending on its magnitude. `migrateSetup` (the core's,
`scope/setup.h`, since stage 5 retired the page's codec) runs them in order and
`kSetupVersion` beside the page's `SETUP_VERSION` names where you are; a purely additive field needs no
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
unless asked.

The site is published twice (12 Nov, `.github/workflows/pages.yml`): **`main`**
is the stable page at the root, for anyone the owner sends the link to, and
**`testing`** is the work in progress under `/testing/`, for the owner to try.
Work lands on `testing` once its full checks pass (the paragraph on running the
tests, above); it reaches `main` only when the owner says so, by fast-forwarding
`main` to a `testing` commit that has passed them. A push to either branch
republishes both. Never push to `main` without the owner's word. The testing page
keeps its browser storage under a prefix of its own (the top of the page's
script), so the two never read each other's settings or saved sounds.

## Layout decisions already made

Do not re-litigate these without a reason; each replaced something that failed.

- **The bench body uses real column elements, not CSS `columns`.** Multi-column
  re-balances the whole flow when any section's height changes, which moved a
  control out from under the pointer mid-drag.
- **A control's appearance must not depend on how many modulation sources are on
  it.** Two designs failed here. `patchtest.py` measures the knob's cell - its
  box, and where its face and reading sit - with nought, one, two and three
  sources and requires all four identical; the ring, its ticks and its dot
  are drawn outside the face's box, out of the flow, and the way in is the
  control's right-click menu (G5b).
- **The Bench's controls are knobs over their range inputs** (P8c, from the
  owner's Headroom). The input stays the value, the keyboard and what every
  test and host knob writes; the face follows it through a setter on the
  input, so a value written from code turns the face with no event. Knobs
  that come together are cells read down - setting, knob, name - and a knob
  alone among menu rows is one line, since as a cell it stood taller than the
  slider it replaced (Wave's header, since 19 Nov the Generator, has the name,
  a small knob and its reading on one line, as tall as the menus beside it). The drawbars (upright, under Play's Wave), the setup morph's crossfader, the strip
  under the screen and the editor's depths stay sliders. `knobtest.py` holds it.
- **No Bench tab may scroll.** The Bench is three tabs along the loop - Play,
  Ink, Space & Memory, in the order the sound goes round it (the Picture tab
  went in F2: its knobs are the Picture section along the bottom; the
  drawer's Sources went in F4) - and one tab at a time must fit. `patchtest.py` measures every tab across every shape;
  `fittest.py` does it in every combination of shape, tone or band
  split, keyboard and Photocell, and the modulation editor with a source on a dozen controls,
  at six windows: 1660x1050 (since 18 Nov, the largest Play's figures were measured at),
  1400x900, 1100x860, 1200x680, 1100x680 and the plugin's
  960x600 at Auto's 90 per cent (see the minimum window, below). Play is not
  dealt since 18 Nov (Play, below): it is a column, the figures take the
  height there is, and its drawings are held to 1.5:1 to 7:1 and 120 px tall.
  Ink was two sections in two columns from then (a tab is never dealt into
  more columns than it has sections, `wantColumns`, since a third left empty
  folded away after the deal and its sections stood shorter than measured)
  until 19 Nov, when it became a figure area (Ink, below), not dealt either.
  The body's lines pack at its top (`align-content: flex-start`): a wrapping
  row with `normal` stretched them, and the band had half the spare height
  under it (124 px at 1660x1050).
  This replaced "every section on show at once, and neither panel scrolls",
  which held for the tone and never for a rack of six (cut in P5), and then
  five tabs by task (Play, Picture, Shape, Effects, Measure), which existed
  because Shape overflowed into Effects; after P5's cuts and the drawer they
  were a third full in places, so P8 (`making-it-one-instrument.md`) put them
  back in the loop's order. A section that would crowd a tab still goes to
  another one. The Picture section along the bottom of the window (F2) holds
  the Amount, Scan, Strike, Softness, the one Persistence and the three reads,
  on every tab (Enlarge covers it); what Scan reads, how the picture responds
  (11 Nov: Responds to, Rise and Fall, Swell, each hand's own on the Picture's
  link), the photocell and the
  score are behind its *Advanced*, with the loop overlay and the choice of
  panes, which only change the look (home `picture`); the panes themselves
  show only in Enlarge. The display, Clear, Scope & measure and Enlarge are
  above the screen. Since F3 the screen is on the left, the largest square the window
  allows less the three columns the tabs need, and the tabs are cards along
  the top of the right column, each with one line of what its stage is doing
  (`TAB_LINES`, read from the values a few times a second, never from the
  readings beside them, which only an input event writes). The cards took
  78 px of the tabs' height at 1400x900, so the fit has less slack than it had.
- **Four modulation sources, a card each, in a row across the window, and
  no drawer** (F4 of `web/docs/redesigning-the-face.md`, 7 Nov; the row and
  the knob G5 of `the-face-second-pass.md`, 10 Nov). LFO 1, LFO 2, the
  Envelope and the Photocell are cards in a row under the screen and the
  tabs, the window's width (`MOD_CARDS`, `offered`, `cardSources`), each
  drawing what its source is doing with a dot where it is now, and
  *Routings* with its count in the corner. Under 900 tall, and on the
  compact face, they are chips with a small drawing each (`CHIPS_H`): the
  cards are 87 px and the tabs had not the difference. The on-screen keys
  cover the row, as they cover the Picture section (the owner's call: hide
  them to patch). Drag a card onto a knob; press one to open its editor over
  the tabs, its source drawn large and *Where it goes* in a second column (the Envelope's under its drawing, since 18 Nov: the envelopes, below)
  scrolling inside itself past a dozen, and `fittest.py` requires a dozen to
  fit. The Photocell's card is there whether or not it is on, and patching
  from it switches it on. On a knob, the selected source (the card or editor
  row last pressed, if it is on the knob, else its first) is a ring from the
  hand's value to its reach, every other a tick at its reach, and a dot the
  control now; Alt-drag (Shift with it finer) or the ring's handle moves the
  selected depth, all through `setDepth`. *Routings* lists every routing by
  source or by destination, and since G6 which hand each moves (*Both*,
  *Lower*, *Upper*: a second depth per routing, `amountB`, stored as `modB`
  in `mod`'s grammar), with a switch per source that silences its
  routings and keeps them, stored as `modSilent` beside `mod` (additive,
  read by the page and the core; the instrument is told `kept|ids`), so a
  silence survives a preset, a code and a plugin project; and it holds the
  modulation fade (`data-home="routings"`). The control's own editor and the
  search offer the four cards' sources and no others. The rest of the twenty-eight are
  cut or parked. Cut in F4b, with a version-9 decode pass (the core's
  `migrateSetup`; the page's own went with its codec in stage 5) that drops
  their routings (the page called its pattern `CUT_SOURCE`) and the `cc` field: the learned
  controllers (the wheel, the swell, the pedal and the panics still act),
  the keyboard's pedal, pressure and four readings of the notes, and the
  level, which is the output meter now. Parked: the hearing family is
  offered nowhere but still plays when a setup routes it, and keeps its ink
  on the knob it is on, so the owner can find out whether it is missed. The
  drawings (the harmonograph, the figures, the solids and the second
  generator) and their readings were parked here too, and went in G2 (10
  Nov, the owner did not miss them), with a version-10 decode pass that
  loads a drawing's code as the waveform and drops its fields and
  routings (`CUT_DRAWING`, as the page called it); the generator's slots they used stay unnumbered
  rather than renumbered (`GEN_SLOTS`).
  Velocity's FM is Expression's menu on Play, reading and writing the one
  routing it stands for rather than a field. The Envelope follows Play's amp
  envelope until it is edited (17 Nov; its own four times since 8 Nov, once
  a phrase or again on every note, `noteDown`, page and core): following,
  its knobs and drawing show the amp's four and take a hand, and the first
  edit copies them into its own and sets `menvOwn`, one step of undo
  (`menvAdopt`); Reset on any of them, or *Follow*, follows again. No switch,
  and nothing stored changed: the knobs hold the stored four, the amp's only
  shown on them (`knobShows`). Its controls
  are written once in the page, outside the editor, and moved
  into it while it is open, so their ids resolve from the start for the
  plugin's panel and the morph. Envelope's ink is sage since G5b, as drawn: on
  slate it was LFO 2's, and a ring and a tick in one ink cannot be told apart.
  This replaced the drawer
  (*Advanced*, P3 to F3, which hid the routing matrix and every tab that was
  not the loop) and the Sources tab, which showed six families one at a time
  because forty chips at once read as a wall; F1 to F3 found each of the
  drawer's other tabs a place of its own. An unpatched control's hollow ring
  stays in its place, transparent until the control is pointed at (faint on
  a touch screen), so the face is quiet at rest and a control still says it
  can take a patch - until G5b, which took the hollow ring and the dots at
  the shoulder away for the right-click menu below. A tab remembered from
  before a rename lands where its sections went (`BENCH_TAB_RENAMED`).
  `layouttest.py`, `benchtest.py`, `patchtest.py`, `modrowtest.py` and
  `ringtest.py` hold it.
- **The right-click menu is the way to a control's modulation and value**
  (G5b, 10 Nov): right-click, Ctrl-click on a Mac, a long press, or Shift+F10
  with it focused. Its modulation first (each source on it opening the
  control's editor over the knob, the others to add, Clear), then Type a
  value, Reset (naming where it starts) and, on a section that is a hand's
  own, Copy to the other hand, then What is this?, the info line's card. Menus and switches have
  it without the modulation. The browser's own menu is never shown but over
  a text box, so Paste still works there. `ringtest.py` holds it, and the
  plugin's shell test right-clicks a knob in the real face under
  `xvfb-run -a`.
- **An envelope is a drawn shape, on Play's figures** (18 Nov,
  `web/docs/mseg-design.md`, and `web/docs/play-figures.md`, which replaced
  its small blocks and popover the same day). The amp's, the filter's and the
  Envelope card's are multi-segment shapes, a string field each (`envShape`,
  `vcfShape`, `menvShape`, with B twins under `linksSettle`), played by the
  core's one segment law (`scope/mseg.h`); the knobs - Delay, Attack, Hold,
  Decay, Sustain in dB, Release, times on the square-root scale to 20 s (5 s
  for Delay and Hold) - write the shape's stretches, and the shape keeps the
  points a hand added. A version-13 decode pass writes an old code's
  envelope as the shape that plays it to the bit. On Play the amp's is the
  Amp figure, drawn the figure area's width with its six knobs in a row under
  it, and the filter's the Filter figure, its response with four and its
  envelope with six (Play, below); nothing opens from them and nothing moves
  in or out (the popover beside a small block, from earlier on 18 Nov, drew an
  8 ms attack as a 17 px wall). The peak is full scale; the sustain point moves
  (*Sustain here*) or goes (*No sustain*, a one-shot); a loop plays only while
  held. The fade's travel is the same bend law. The morph interpolates two
  shapes with as many points and snaps at half-way otherwise (`msegBlend`,
  page and core). The amp's Attack and Release are host knobs 16 and 17, in
  a group of their own after the Setups so no index moved. The Envelope
  card's editor is the same drawing, still following the amp until edited
  (`menvAdopt`, `knobShows`): over the tabs as the LFOs' are, but one column -
  its tools along the top, the drawing the editor's width at 2.4:1 (2.6:1
  compact), its six knobs, then *Where it goes* scrolling inside itself; two
  columns made the drawing a tower again (588x630 at 1660x1050). Its knobs
  move in while it is open and back after. The card's face draws the real
  shape too (`drawEnv`), the dot where the core says it is, as the editor's;
  until 18 Nov it was the old four-corner ADSR. `msegtest.py` holds it (it replaced
  `dragenvtest.py`), the core's `pieces/mseg.py` the law.
- **Space & Memory is a rack of effect modules** (F5, 7 Nov), one wide
  column top to bottom in the order the engine runs them - Plane (its Turn
  is the screen's rotation), the EQ (17 Nov: three bands, the same on both
  channels, its place fixed), Phaser, Chorus, Delay, then the Reverb (9
  Nov; a dashed slot until then) - each a line of icon, name, switch, what it is doing and its
  main knobs, Mix first. Its arrow, shown whether the module is on or off
  (19 Nov: off, only the EQ's showed), opens the rest under it, one module at a
  time, and never switches it on; and while one is open the others fold to their lines only if the
  tab would scroll with their knobs showing (`fitRack`, F8): with every
  effect on they fold at 1400x900 too since the EQ's line (17 Nov; they kept
  their knobs there until then), and folded so their lines are tighter. Decided by room,
  not by window size, so it is right at sizes nobody measured.
  The switch is a view over values, not a field: off takes the Mix (the
  Plane's shaping and turn) to rest and keeps what it
  had, on puts it back (`switchFx`, `fxKept`), so a setup, a host knob or a
  code that moves a Mix switches the module with it, and a module saved off
  comes back off with nothing to put back. With nothing kept, on is the
  module's start: its Mix (`FX_MIX`) or the Plane's Twist of 15
  (`PLANE_START`, chosen by measuring three,
  `web/docs/listening/plane-start/`, held to no heading: 17 Nov, the
  presets, below); `core/tests/pieces/starts.py` holds what it is. **The
  EQ's switch is the exception, a field** (`eqOn`, and `bEqOn` per hand;
  17 Nov, the owner's): a flat EQ that is on means something - ready to
  shape - and one switched off keeps its curve, neither of which a view
  over three gains can say. Off, the core runs no band, the same to the
  bit as no EQ; on from a curve never shaped is flat (no start; `EQ_START`
  went) and opens the editor; a point or a gain moved by a hand while off
  switches it on (`eqHand`, trusted events on the EQ's line, editor or a
  menu over them - a setup, the morph or a host moving a gain leaves it
  off). A code from before the field (version 11) is on where any gain was
  off nought: a version-12 decode pass in the core's `migrateSetup`, not a
  default read two ways, since a code leaves an off switch out. The EQ is
  drawn as its response (17 Nov, the owner's mockup, `web/docs/mockups/eq/`):
  its line has the curve with three points in place of its gain knobs, a
  button, smaller on a folded line, flat and grey while off, both hands'
  when they differ; the curve, its arrow or its switch on open its editor
  over the tabs where a card's editor opens (`openEqEditor`), each point on
  the drawn total curve at its band's frequency, its seven knobs moved in
  under it as the values the points write (`setControl`, a knob's path), and
  the Spect view's analysis faint behind it, smoothed, only while open
  (`eqSpectrumStep`, about 0.2 ms a frame). `eqeditortest.py` holds it. Lines and switches are read off the values a
  few times a second (`paintRack`). It replaced the Display, Plane and
  "Delay, chorus and phaser" sections; the Numbers read switch went to
  Scope & measure's Measure. Since F5b the order of the phaser, chorus and
  delay is the setup's `fxOrder` (one of six, by letters; the engines get an
  index into one table, `FX_ORDER_STAGES` and `kFxOrders`, never stored),
  one order for both layers, the Plane always first, the EQ always after
  it and the Reverb always last: a tail smeared over seconds is the end of the chain, and a delay or
  chorus after it would repeat the cloud rather than the figure. The Reverb
  is two identical networks, one per channel with nothing crossing, so at
  Spread nought the channels are the same to the bit and the figure survives
  its own tail; Spread reads the second channel from other taps of the same
  network (the owner's call over a Width that mixes the channels). A loud reverb keeps a
  Settled sound moving, as the Delay at full does, and that is accepted
  rather than defended (9 Nov, the owner's call: a defence would make Scan's
  knob lie): its switch gives a Mix of 0.15, chosen (9 Nov) because it left
  the Settled presets settled, though since 17 Nov nothing requires that; its
  line says *keeps a held chord moving* past a fifth, which is information,
  not a rule; and the full setting is bounded, not forbidden (`honestytest.py`,
  no more than 0.10 late). A handle drags a module
  or the arrow keys move it, through the hidden `#fxOrder` menu, so the
  plugin's core hears it as any menu; the modules themselves move, which the
  morph survives only because `MORPH_IDS` is read once from the markup, so
  the markup stays in the default order. `racktest.py` and `fittest.py`
  hold it, and the core's tests the six orders.
- **Every section has one home.** `data-home` is `settings` (set once and left:
  MIDI, Audio, the inputs, the modulation fade, This window; two columns by
  `data-place` since F7b, notes behind each section's dots, the panel under
  the header on the window's right), `bench` (everything played or tuned),
  since G5a `routings` (the modulation fade, in Routings), or, since
  F1, `measure`, since F2 `picture` (the Picture section's Advanced, with the
  Beam since F7b) or since F3 `perform` (the header's Perform menu: the arpeggiator, the clock, the key and tempo, the morph) - `measure` is the oscilloscope's own tools: *Scope & measure*, a panel over
  the screen opened from the toolbar above it, which also holds run, mode,
  Autoset, the trigger, timebase and zoom and the readouts' switch; shut by
  default, the readouts off by default, and nothing in it scrolls down to the
  plugin's 960x600 - `benchtest.py`), and a
  section stays in its home; only the screen, its toolbar and the verdict move,
  into Enlarge and back. Settings and the Bench used to hold
  the same sections, which made neither a place for anything. To reach a
  control from code - a search result, a test - use `showControl(id)`; do not
  assume the Settings popover holds it.
- **Presets are a small bank under two headings, by what the loop does with
  a held chord** (P8g and P8h, `making-it-one-instrument.md`): *Settled* (a
  note moves the sound as it strikes the screen, and it comes to rest while
  held) and *Breathing* (it moves while held and stops when let go, or goes
  on under the sustain pedal). The browser (F6) is three columns: the
  headings down the left, each with what it means in a line, Saved last;
  the heading's sounds, each with a thumbnail of its figure; and the chosen
  one, larger, with what to listen for and what to watch for (two short
  lines, the first also its card's), its whole description and *Load*, which loads it and
  leaves the browser open (choosing a card loads nothing). A section rail
  only when a heading has more than one section. No search. Its footer took
  Settings' Presets section: save (with the figure of what is sounding),
  delete, and the setup code with Copy and Paste. The thumbnails are the
  instrument's own figures, drawn into the page by
  `core/tests/tools/write_figures.py` with a hash of each preset, which
  `presettest.py` holds them to. The plain
  sound is not a preset: the page and the plugin open on the base
  (`BASE_SETUP`, a still sine) and *New* goes back to it. It replaced 268
  presets in three menus, which the owner liked none of, and then four
  headings, of which Wandering rested on a latch (cut: arpeggiated chords
  defeat any rule for when a latched chord gives way, and the pedal is told)
  and Open was the base dressed as a preset. `honestytest.py` measures every
  preset's sound, as shipped, against its heading and requires it to fail the
  other, and the base to be still. A preset answers to its heading as shipped
  and to nothing else (17 Nov, the owner's rule): a change it does not
  contain - a reverb, a Plane or an EQ switched on - may take it under the
  other heading, which is not a fault, so no check holds a preset to its
  heading under a change, and no setting elsewhere is chosen to fit a preset
  it is not on; `presettest.py` requires every field a preset names
  to come back out of the setup it makes, the bank's shape (a split under
  each heading, Settled at Picture nought, Breathing with the loop at work)
  and every preset to name the Picture amount. Add a preset under the
  heading it measures as, with its description and its two short lines,
  what to listen for and what to watch for (twelve to sixty characters each,
  which `presettest.py` holds), then write `presets.h` (and the base) out with
  `core/tests/tools/write_presets.py` and its thumbnail with
  `core/tests/tools/write_figures.py`. The old library is kept whole as a
  test corpus (`core/tests/scenarios/library-p8f.json`,
  `web/tests/corpus.py`): a suite that wants a known sound under a check
  opens it from there, and one testing the preset mechanism picks a bank
  preset by what it needs, never by name - the bank is meant to change by ear.
- **The header is the preset and what acts on the whole sound** (F7a, 8
  Nov): the title over the line of what is playing; the preset between
  arrows that step the bank in the browser's order, its heading above its
  name; Browse; Save; with two hands, *Editing: Lower · Upper* (A · B
  layered, G6), each in its figure's ink; undo and redo; then the run status, Perform, help and
  Settings, one row above a phone's width with the line under the title or
  without it (G4). Undo records the setup (`snapshot`) once a
  change has held still for 400 ms with no pointer down, and only after a
  trusted event - a host's automation and the plugin's own state moving the
  base, not making steps - a hundred deep, and puts a step back as a preset
  is loaded (`putBack`). One history (`undoHistory`); the versions A and B
  went in G4, since undo, saved presets and the morph's two ends already
  compare.
  The transport row under the header is hidden: it only carries the
  persistence menu the core's panel names. The host's parameters (F7c) are
  marked where they are, a gold dot before the name (`HOST_PARAMS`, in the
  order of the plugin's `kKnobs`, which `headertest.py` reads): the Picture
  section's six (the master Output last, since G7), Level, cutoff, warp, twist, the
  delay's, phaser's and reverb's mix, and the morph. The Output is how loud
  you hear and nothing else - the picture is the same to the bit at any
  setting - and no setup's: the browser keeps it (`scope.output`), the
  plugin's state beside the setup (`pluginOutput`), and no preset, code,
  undo step or morph moves it (`outputtest.py`, the core's tests). `headertest.py` holds it, with real mouse and keys, since a
  dispatched event is rightly no step.
- **The minimum window** (F8, 8 Nov). The plugin opens at 1200x680, will not
  go under 960x600, and remembers its size (`pluginWindow`, which the
  instrument never sees). The page has a *Size* in Settings' This window -
  Auto, 90, 100 or 125 per cent, a CSS zoom on the page, remembered by the
  browser (`scope.size`). Auto, the default and the owner's choice over a
  larger minimum, is 90 under 1100 wide or 680 tall and 100 otherwise, so
  960x600 fits every case unasked and 1200x680 stays at 100. Below 1100 by
  860 in the page's own pixels (so the zoom counts) the face is compact
  (`setCompact`, `body[data-compact]`): the header one row without the line
  of what is playing or Browse, the tabs without their lines, the cards as
  chips, narrower columns (`BENCH_COL_COMPACT`) with labels beside their
  menus, smaller knobs and the keys shorter; the modulation cards are chips
  there and on any window under 900 tall. The verdict and readouts are a
  line in the screen's column, between the screen and the cards, and a line
  under the screen in Enlarge, where Picture only hides them. `windowtest.py` and
  `fittest.py` hold it.
- **One face, and Enlarge** (G4, 10 Nov). The Scope / Bench views went; the
  Bench is the face (`setView` still lays it out and ignores its argument,
  since thirty suites call it). Enlarge, at the end of the screen's toolbar,
  fills the window with the screen (`setEnlarged`, `#screenFrame`); Esc or the
  button again comes back, Esc closing a panel first. Picture only, on there
  by default, hides everything over the trace, the graticule included; Which
  hands (Both · Lower · Upper, or A · B layered, while each hand draws a figure) and the Trail (As heard
  · Half · Short, the owner's choice over a knob) are only the look. None of
  it is in a setup, a step in undo or remembered, and none reaches what Scan
  reads: the grid fades by the Persistence and is kept across Enlarge's
  resize, and a hidden hand is drawn at alpha nought. The panes show only
  here, with Picture only off (the owner's call over beside the screen on the
  face, which has no height to spare). `enlargetest.py` holds it.
- **The hands** (G6, 10 Nov). With two hands, a link on the Generator, Amp
  envelope, Voice filter, Oscillator, Shaping, each rack module and the
  Picture's Amount, Scan and Strike (and since 11 Nov how the picture
  responds, which is each hand's picture's, not its sound's): *Same in both* or the hand's own (*Both*
  or the hand's name in the rack and the Picture). Linked writes both hands
  (`handSet`); unlinking copies the edited hand into the other; linking copies
  it back and drops the other hand's own routing depths there. A link is never
  stored: a section is linked while a setup has none of its B fields, and
  with any it is the hand's own only where a B value, as restore makes it,
  differs from A's or a routing on it has its own upper-hand depth
  (`linksSettle`, page and core), so a code from before G6 loads linked
  wherever the hands were one; links survive the layers going off. The Picture amount and Strike
  are per hand (`bPictureAmount`, `bScanStrike`); the rack's Together · A · B
  rows and B's Turn row went, each module's own state is a bit in `timeOwn`,
  and a module the hands share beside one that is B's own plays A's state, as
  Together did. Frequency, Phase, Glide, Interval and Tuning stay shared.
  Additive throughout, no version bump. `handstest.py` holds it, the core's tests the
  core.
- **The Keyboard is a band across Play** (17 Nov, `web/docs/play-redesign.md`,
  the owner's G after five rounds of mockups; with room since 19 Nov,
  `web/docs/play-band.md`, the owner's "much much better"). A row of its own
  across Play's top (`data-band`, `.bench-band`, not dealt), a grid of two
  columns and three rows at one height in every mode and hands state (140 px,
  120 compact; the owner's lean was 10 px under the mockup's, which leaves the
  stacked filter 8 px over its floor at 1660x1050). Its left column: the name
  with the *Two hands* pill in it (seen in Poly on the generator only, and in
  Dyad and Mono keeping its place unseen, so the heading never reflows) and the
  dots, then Dyad · Mono · Poly, and under them only what the mode uses of how
  the notes are drawn - Hold in Dyad, a line in Mono, Outline, Tune a chord and
  with two hands the pairing (*each*, *A vs B*) in Poly. Its right column: the
  **split row**, kept unseen with one hand so choosing Two hands moves nothing,
  holding Key · Notes · Layer and then that way's own: by key *Split at C4* in
  a reading of one width (the mockup found Learn moving when the name changed
  width) and *learn from a key* (the plugin's way from a host's note, one width
  waiting or not); by notes *Lowest · Highest*, six numbered places for how
  many, and *Chord window 10 ms*, which is Settings' (MIDI) and goes there; by
  layer its line. Then **the keys**, three octaves (thirty-six keys, C3 to B5
  to begin with) taking the rest of the height and the column's whole width in
  every way of sharing: by notes they stay (they were eight places until 19
  Nov, and the owner could not see which hand a note went to), each held note
  in its hand's ink and numbered on its own key from the counted end, the
  counted ones on a paper disc, a dashed rule at the first uncounted note's
  edge. Then **one line**: one sentence that fits at every window, and the
  strip's octave buttons and span (a view, never stored) at its end, in every
  way. Nothing is laid over the keys; nothing in the split row shrinks, so
  what does not fit is seen not to. The menus that hold the values
  (`midiLayers`, `midiSplitBy`, `midiSplitEnd`, `midiSplitCount`) are kept out
  of sight and the switches drive them by their change events, so the plugin,
  undo and the setup hear what they always heard. The on-screen keys, beside
  the Chord window in Settings' MIDI, open with **M** and are the site's only:
  in the plugin their row is hidden and M does nothing, since a host has its
  own keys and musical typing. `striptest.py`, `patchtest.py`, `fittest.py`
  and the plugin's shell test hold it.
- **Play is the band, Expression and its figures** (18 Nov,
  `web/docs/play-figures.md`, the owner's; Expression alone and the Generator
  in Wave since 19 Nov, `play-band.md`). A column of three, nothing dealt, so
  nothing can stretch between them. Under the band, one row: Expression, its
  title and a line of what it is in the band's left column and its four menus
  across the rest, each name in small type over its control (47 px, 40
  compact). The menus' values are shortened to fit at 960x600 (*±2 st*,
  *Level + strike*, *Sine + 3rd*, *Maj 3rd 5:4*) with the full name each
  option's title and the menu's own while chosen, and still the name in the
  info line and the search. Then the figure area, the rest of the tab, with
  three subtabs, each its name and a summary that shortens only where it must
  (`figSummaries`): *Amp* (the drawing and six knobs), *Filter* (the type as a
  switch driving the hidden menu, the response with four knobs and the
  envelope with six, side by side or stacked when each drawing would still be
  120 px tall - by room, as the rack folds, `fitFilter`) and *Wave*, whose
  header is **the Generator**: Shape, Glide, Interval and Level on one line,
  each name beside its control, the readings in boxes of one width, the link
  pill and the dots (Tuning, and what the Wave figure's dots said) at its end.
  The Generator stays a section of its own, moved into the Wave view as Play
  is laid out (`data-play="head"`, `data-fig="wave"`), never copied, so
  `showControl` on Shape chooses Wave; Wave's own tools and title stand aside
  for it (`linkGenWave` is kept, unseen, for the checks that read it). Under
  the header, one cycle of what the generator plays (`paintCycle`), drawn on
  with the Drawn cycle and the Wavetable, and under it a band one height for
  every shape, the drawbars' 78 px: Width, Morph, Position and its slots, the
  Drawn cycle's Sine, Smooth and Grab, the nine drawbars upright, or the
  shape's one line. The Drawn cycle and the Drawbars were Ink's sections until
  18 Nov; they moved here, ids and all. The subtab chosen is a view, never
  stored; `showControl` chooses it. **Nothing moves when something is
  chosen** (the owner's general rule): the pills are one width at the right of
  each header, the words that change keep their boxes, the chosen subtab
  covers the bar's rule with a shadow (a negative margin moved both by a
  pixel), a pressed link button keeps its height, the filter's envelope keeps
  its knobs while it is off, and the info line's menu note and More sit in a
  column of their own, so pressing a control and changing the line moves
  neither. `patchtest.py` measures every box on Play to half a pixel across
  the modes, one hand and two, Key, Notes and Layer, the split moved, Learn
  waiting, each count from either end with a chord held and without, an octave
  up, every Wave shape, Loop, Sustain here, No sustain, a note held, every
  filter type, the link pills, the subtabs and the Envelope's editor at six
  windows, and in each state of the band the line on one line, the split row
  uncut and nothing over the keys, with its nulls; `msegtest.py` the
  summaries, the fit, the knobs' homes, `showControl` and Wave across all
  fourteen shapes; `fittest.py` and `striptest.py` the fit and the band.
- **Ink is a figure area** (19 Nov, `web/docs/ink-figures.md`, the owner's). No band and no
  settings row: the area takes the tab, its bar Play's (`.fig-bar`), with two subtabs, *Oscillator*
  and *Shaping*, each its name and a summary (`inkSummaries`); the sections are the views
  (`data-ink`), moved in as the tab is laid out, ids and markup order kept (`MORPH_IDS`). The
  Oscillator draws both channels over the voice's whole pattern - the left charcoal, the right
  slate, offset by Phase - with the plain shape dashed behind, the span as many of the note's
  cycles as it takes to repeat (at most 8); its eleven controls in one row under it, Warp at and
  Spread greyed while Warp and Unison are off, the sub's octave and shape behind the dots. *Wave ·
  Figure* in its header draws the X–Y figure instead, a square of the wave's height, centred: only
  the look, never in a setup, undo or the morph, kept by the browser (`scope.inkDraws`). Shaping draws
  the shaper's curve with Crush's steps beside two cycles before and after with Rate's holds,
  stacked (the cycle over the curve) by room where that gives the curve more and leaves the cycle
  120 px tall - 1660x1050 alone of the six (`fitInk`). **Ink draws the settings, still**: a drawing
  changes when a control does and at no other time, Unison frozen 4.33 of the note's cycles in
  (`INK_STILL_CYCLES`), and *Hold to watch it drift* runs it only while held, its place kept unseen
  while Unison is off. The drawings are the page's arithmetic over the hand's tone, the core's
  formulas line for line; `inkfigtest.py` holds them to the core itself built from `core/include`,
  the fit and nothing moving at six windows, the stillness with a clock as its null, and the
  choice kept across a reload; the plugin's shell test holds Ink in WebKit.
- **Trace · Paint, and the painting's own Persistence** (painting, step 2, 18 Nov;
  `web/docs/painting-design.md`). The screen draws the trace or the painting the core keeps
  (`core/include/scope/paint.h`), a setup field (`screenDraws`), and Scan and the Picture
  amount read whichever is shown. Paint is the fourth place in the display switch (Y–T ·
  X–Y · Spect · Paint), each other view pressed the trace again: a switch of its own beside it
  cost the toolbar a row at every window. Switching moves nothing on the face (the owner's
  rule, 18 Nov; `painttest.py` measures it). The photocell and the score still read the
  trace's grid underneath.
  Persistence on the Picture section is the painting's own half-life in seconds while Paint
  is shown (`paintPersistence`, 16 to start), kept apart from the trace's - the owner's
  choice over one value meaning two things - and the instrument keeps a hand on it in Paint
  as a `paintPersistence` hand, so a hand in Trace does not replace it. The look is painted on
  the graphics card from the core's stamps and never reaches the sound; without WebGL 2 the
  face draws the core's map plain. *Which hands* is hidden in Paint. Each note reads the ring
  at its own pitch; Mono and Dyad read the lower note's. `painttest.py`, `paintcosttest.py`,
  `core/tests/pieces/painting.py` and the plugin's shell test hold it.
- **Controls are moved, never copied.** Between a tab and the hidden store,
  into a section's detail overlay and back, and the screen, its toolbar and
  the dock into Enlarge's frame and back. Two elements with one id is how the
  dock's readout line silently stopped displaying for weeks.

## Before saying you are done

- The full suite passes, and you have said so with the number of checks.
- `web/README.md` gained an entry if you learned something a future reader would
  otherwise rediscover.
- The cheat sheet inside `scope.html` still describes what the app does. It is
  user-facing documentation and it goes stale first.
