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

**Run the tests.** While building, run the suites near the change, as often as
you like. Before anything reaches the working branch - a push there publishes the
site - run the whole web suite **and** parity, once per batch of stages rather
than once per stage (the owner's call, 10 Nov: a batch costs one wait, and the
cost is that a failure has more candidates). Changes that cannot alter behaviour
- docs, design notes, the info line's words, whose own suite checks them - merge
after the suites that read them. Any change to `core/`, or to anything the core
shares with the page (a setup field, a slot, a slider's place in the markup),
runs parity before it merges, however small: twice in one day the web suite was
green while parity was not, because the web suite runs the page whole and the
page agrees with itself. And do not narrow the full run to the suites you think
are affected: on this one-file page that guess was wrong about half the time on
9 Nov (a layout change broke the plugin's checks; a glide change exposed a
harness the wash fix had broken a day earlier).

```
python3 web/extract.py && node --check web/tests/check.js   # syntax, seconds
python3 web/tests/run.py                                    # everything, ~37 min
python3 web/tests/run.py lane patch                         # just those
python3 web/tests/run.py -j1                                # one at a time, ~43 min
python3 core/tests/parity.py                                # the C++ core against the page
python3 core/wasm/build.py                                  # after any change to core/: the page carries it compiled
python3 core/tests/tools/write_schema.py                    # after any change to SETUP_FIELDS: the core reads setups by it
python3 web/tools/write_words.py                            # after any change to web/docs/what-each-control-says.md: the info line's words
```

In a cloud session, set `CHROME=/opt/pw-browsers/chromium` for every browser
suite and parity: the path the suites default to does not exist there, and a
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
  sources and requires all four identical; the ring, its ticks and its dot
  are drawn outside the face's box, out of the flow, and the way in is the
  control's right-click menu (G5b).
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
  went in F2: its knobs are the Picture section along the bottom; the
  drawer's Sources went in F4) - and one tab at a time must fit. `patchtest.py` measures every tab across every shape;
  `fittest.py` does it in every combination of shape, tone or band
  split, keyboard and Photocell, and the modulation editor with a source on a dozen controls,
  at five windows: 1400x900, 1100x860, 1200x680, 1100x680 and the plugin's
  960x600 at Auto's 90 per cent (see the minimum window, below).
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
  the tabs, its source drawn large and *Where it goes* in a second column
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
  cut or parked. Cut in F4b, with a version-9 decode pass on both sides
  that drops their routings (`CUT_SOURCE`) and the `cc` field: the learned
  controllers (the wheel, the swell, the pedal and the panics still act),
  the keyboard's pedal, pressure and four readings of the notes, and the
  level, which is the output meter now. Parked: the hearing family is
  offered nowhere but still plays when a setup routes it, and keeps its ink
  on the knob it is on, so the owner can find out whether it is missed. The
  drawings (the harmonograph, the figures, the solids and the second
  generator) and their readings were parked here too, and went in G2 (10
  Nov, the owner did not miss them), with a version-10 decode pass on both
  sides that loads a drawing's code as the waveform and drops its fields and
  routings (`CUT_DRAWING`); the generator's slots they used stay unnumbered
  rather than renumbered (`GEN_SLOTS`).
  Velocity's FM is Expression's menu on Play, reading and writing the one
  routing it stands for rather than a field. The Envelope follows Play's amp
  envelope unless its editor's switch gives it its own four times (8 Nov),
  once a phrase or again on every note (`noteDown`, page and core):
  those controls are written once in the page, outside the editor, and moved
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
- **Space & Memory is a rack of effect modules** (F5, 7 Nov), one wide
  column top to bottom in the order the engine runs them - Plane (its Turn
  is the screen's rotation), Phaser, Chorus, Delay, then the Reverb (9
  Nov; a dashed slot until then) - each a line of icon, name, switch, what it is doing and its
  main knobs, Mix first. Its arrow opens the rest under it, one module at a
  time, and while one is open the others fold to their lines only if the
  tab would scroll with their knobs showing (`fitRack`, F8): at 1400x900 they
  keep them, as drawn, with one layer (two fold since G5a's row), and on the
  compact face they fold. Decided by room,
  not by window size, so it is right at sizes nobody measured.
  The switch is a view over values, not a field: off takes the Mix (the
  Plane's shaping and turn) to rest and keeps what it had, on puts it back
  (`switchFx`, `fxKept`), so a setup, a host knob or a code that moves a
  Mix switches the module with it, and a module saved off comes back off
  with nothing to put back. Lines and switches are read off the values a
  few times a second (`paintRack`). It replaced the Display, Plane and
  "Delay, chorus and phaser" sections; the Numbers read switch went to
  Scope & measure's Measure. Since F5b the order of the phaser, chorus and
  delay is the setup's `fxOrder` (one of six, by letters; the engines get an
  index into one table, `FX_ORDER_STAGES` and `kFxOrders`, never stored),
  one order for both layers, the Plane always first and the Reverb always
  last: a tail smeared over seconds is the end of the chain, and a delay or
  chorus after it would repeat the cloud rather than the figure. The Reverb
  is two identical networks, one per channel with nothing crossing, so at
  Spread nought the channels are the same to the bit and the figure survives
  its own tail; Spread reads the second channel from other taps of the same
  network (the owner's call over a Width that mixes the channels). A loud reverb keeps a
  Settled sound moving, as the Delay at full does, and that is accepted
  rather than defended (9 Nov, the owner's call: a defence would make Scan's
  knob lie): its switch gives a Mix of 0.15, which `honestytest.py` requires
  to leave every preset under its heading, its line says *keeps a held chord
  moving* past a fifth, and the full setting is bounded, not forbidden. A handle drags a module
  or the arrow keys move it, through the hidden `#fxOrder` menu, so the
  plugin's core hears it as any menu; the modules themselves move, which the
  morph survives only because `MORPH_IDS` is read once from the markup, so
  the markup stays in the default order. `racktest.py` and `fittest.py`
  hold it, and parity the six orders.
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
  preset's sound against its heading and requires it to fail the other, and
  the base to be still; `presettest.py` requires every field a preset names
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
  undo step or morph moves it (`outputtest.py`, parity). `headertest.py` holds it, with real mouse and keys, since a
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
  Additive throughout, no version bump. `handstest.py` holds it, parity the
  core.
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
