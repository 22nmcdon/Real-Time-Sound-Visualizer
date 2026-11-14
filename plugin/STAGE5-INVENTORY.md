# Stage 5, step 1: the inventory

Step 1 of `STAGE5-PLAN.md`, with no behaviour change. It answers two
questions the later steps are measured against:

- which of the page brain's per-frame steps still do something on the
  default site, where the compiled instrument is the brain; and
- what every check that opens the page on `?brain=js` or `?core=js` is
  checking - *numbers*, *page* or *engines compared* - and so where each one
  goes in step 3.

It was taken on 13 Nov at `testing` e59179a plus the counters. The full web
suite ran once with them, through `braincounts.py`: 97 suites, everything
passes, 3,042 checks, in 53.3 minutes. Parity passed as well, 947 checks
(the last section says how it was red first).

## In short

- **Seven of the page brain's per-frame steps work on the default, after the
  instrument has taken over.** Four run on every frame in every suite: the page's own picture grid is
  faded and deposited into (`phosphorFade`, `phosphorDeposit`), the page's
  picture engine and stage step on that grid (`pictureStep`), the level
  follower runs (`updateEnvelope`) and the speakers' monitor chain glides
  (`syncMonitor`). Three more run whenever a suite asks for them: the
  modulation fade and its dot (`fadeStep`, `stepRoutes`, `fadeDotStep`), the
  page's photocell (`photoStep`), and the matrix on the view's destinations
  (`view.rotate`, `view.zoom`, `trig.position`, `morph.pos`). Five more run
  and do nothing anyone receives, because their output is cut off further
  on: the hearing, the score, the arpeggiator, the morph's walk and the
  clock's tempo-following.
- **What matters for step 5 is the second grid.** The plan suspected it
  ("looks like a second grid beside the instrument's, not yet confirmed").
  It is confirmed: on 106,544 of 106,612 default frames the page fed and read
  a picture of its own, and the face shows that grid's readings, not the
  instrument's. These all come from it: the Picture section's three read
  bars, the photocell card's number, the loop's verdict in the readout
  (`pictureMeter.verdict()`), and the running-away rule in the stage's hold.
- **The page also starts on its own brain.** In every suite, the default
  page's first frames - 1,290 in all, about twenty a page - run on the page's
  own tone source until the instrument answers. Scan's page step and the gate
  count only there. Step 5 has to change how the page starts, not only stop
  the per-frame work.
- **1,165 checks open the page on `?brain=js` or `?core=js`**, in 48 suites:
  464 *numbers*, 654 *page*, 47 *engines compared*. The plan expected page
  checks to be the small part ("about ten" suites). They are the large part,
  but cheap: perhaps half read only the face and move by dropping
  `&brain=js` from the address. The numbers checks are the expensive part,
  and most of them are below the level of a setup code (next point).
- **Step 3 needs two targets, not one.** About 120 of the 170 numbers checks
  in one quarter of the suites, and a similar share elsewhere, call engine
  pieces directly - `makeGeneratorCore` with a raw `set`, `waveAt` with the
  correction off, `scanRead` on a hand-made grid, `clockTap` at made-up
  times. A `render_cpp` that takes a setup code and timed MIDI cannot express
  them. They belong in parity's C++ tools (`core/tests/tools/*_cpp.cpp`),
  which already drive those pieces. What is left for `render_cpp` needs more
  than the plan gave it: input samples, a source held at a value, the
  per-layer lanes, and readings from inside the brain.

## 1. The counters

### What was added

`brainCount(name)` at the top of the page's script, and one call in each
per-frame step of the page's brain, placed after that step's own early
return so that it counts work rather than calls. Where a step has more than
one kind of work, each kind is named: `clockStep.lfoSync`,
`clockStep.delayFollow` and so on. The counts are in
`globalThis.__brainCounts`. Nothing reads them but a test. The cost is one
property increment per step per frame, and the full suite and parity
passed with them in.

Every call is `globalThis.__brainCount?.(...)`, optional, rather than a
plain call. Parity's harness evaluates the page's own text - whole functions
by name (`core/tests/tools/js_core.mjs`), and spans of `applyModMatrix` (the
matrix's visual loop, in `matrix_js.mjs`) - and has no counters. The first
version called `brainCount` directly at call sites thought to be the page's
alone. The web suite passed all 97 suites over it, because it runs the page
whole. Parity's matrix runner then threw on the visual loop. That is the
CLAUDE.md rule about running parity on anything the core shares with the
page, met on the first try. The optional call is a no-op in the harness and
in the worklets.

- **`frames.<kind>` records which source each frame ran on**: `host` for the
  instrument, `tone` for the page's own generator. That is how the boot
  frames were found.

The harness is `web/tests/braincounts.py`. It runs a suite unchanged, with
Playwright's sync API wrapped so that a page is asked for its counts before
it navigates, reloads or closes, and before its context, browser or
Playwright goes. Taking the counts clears them, so every record is a delta
and nothing is counted twice. `run.py --brain-counts DIR` runs every Python
suite through it. `braincounts.py --sum DIR` adds the records up by address:
the default site, `?brain=js`, `?brain=js&core=js` or `?core=js`.

Its known gap is a navigation made from inside the page: a
`location.reload()` in an evaluate, or a click on a link. That loses the
counts since the last record. Six suites reload this way (`bench`, `brain`,
`fade`, `header`, `overlay`, `words`). This is a gap in coverage, never a
count made up, and every step it might hide is also seen in other suites.

### Its nulls

The checks are the counters' section at the end of `braintest.py`. On the
default site, with Scan at 60 and a note held for a second and a half, the
check reads the difference of two snapshots, never clearing the counts so
the harness still sees them. It finds:

- 90 frames, all of them on the instrument;
- the page's grid fed and read (`pictureStep` and `phosphorDeposit` 90 each);
- Scan's page step at nought.

The checks have two nulls:

- **The "ran" test, asked of Scan's step on the default, fails.**
- **The "never ran" test, asked of `?brain=js`, fails too:** there the same
  step ran on 88 of 88 frames and made a table on each.

The counter was also flipped on purpose: moving Scan's count above its own
early return turned both of the default's Scan checks red (seen, then put
back).

### What does work on the default

These are summed over the full run, from 106,612 default frames in 63 suites
(1,290 of them on the page's own tone source at boot), against 79,199 on
`?brain=js` and 18,849 on `?brain=js&core=js`. The full sums are in the
appendix's first table.

| Step | Default frames it worked on | Suites (the largest) | What it is, and what step 5 must do with it |
|---|---|---|---|
| `pictureStep` | 106,544 | 63 (honesty, noise, modrow, fade, brain, stage) | The page's picture engine - its meter, its six readings and the stage's Glow, Motion, Memory and hold - stepped on the page's own grid. The instrument has its own (5p, 5u). The Picture section's read bars (`paintStage` reads `pictureStage`), the readout's "loop ..." (`pictureMeter.verdict()`) and shapetest's settled check read this one. **The largest single lean of the face on the page's brain.** It moves to the instrument's readings, which carry the stage's values already (the instrument steps them); the page's engine then goes. |
| `phosphorFade`, `phosphorDeposit` | 106,622 and 106,995 | 63 | The page's grid itself, deposited from the lanes the instrument posts. It is what `pictureStep` and the photocell read, and what the score's playhead and the constellation draw over. It goes with them; the instrument's cells are already read for the overlay and Scan. |
| `updateEnvelope` | 106,614 | 63 | `envLive`, the level of the drawn signal. It feeds the output meter beside the Output (G7) and nothing else that is heard. The face can keep it: it is arithmetic over the lanes the page draws, not a second brain. Listed so that step 5 does not require it at nought. |
| `syncMonitor` | 106,719 | 63 | The page's speaker-side monitor chain, glided every frame. `monitorChains` is not empty on the default site (`scope.html` builds the chain on the site's path too). What it carries there needs looking at before step 5: if it is only the live input's monitor, it is the face's audio and stays; if it is anything the instrument also does, it goes. `monitorLimiting()`, which feeds the running-away rule, reads it. |
| `photoStep` | 2,093 | 9 (fit, modrow, patch, enlarge, layout, photo) | The page's photocell, reading the page's grid. The photocell card's number and trail (`paintModLive`) show it, while the photocell that is heard is the instrument's. This is the kind of lean 5m found (the cards' readouts). |
| `fadeStep`, `stepRoutes` (host), `fadeDotStep` | 4,349; 4,327; 3,078 | 4 (fade, brain, host, modrow) | The modulation fade's dot, which follows the page's own reckoning of the routes (5m). Known; the dot moves to the instrument's fade state. |
| the matrix on visual destinations | `view.rotate` 7,121 in 9 suites; `trig.position` 498; `morph.pos` 53; `view.zoom` 2 | 11 | The page applies routings to the view's own destinations (the screen's turn, zoom, the trigger point, the morph fader) from the sources the instrument posts back. The LFOs are the instrument's (`absorb`). The view is the page's, so this may be the face's business - but the routings' depths and the fade on them are the brain's, so the offsets should come back with the readings rather than be worked out twice. **To decide in step 5.** |
| `hearingStep` | 1,609 | 4 (hearing 1,589) | The page's hearing runs whenever a routing comes from `hear.*`, beside the instrument's own on the audio thread (5t). Nothing heard reads the page's copy on the default. It is about 2 ms a frame of dead work, and goes. |
| `scoreTick` | 10 steps, 10 strikes | 2 (fade, regress) | The page's score steps on the default. Its strike is a no-op on the instrument (`genStrike` asks for a tone) and its MIDI out is guarded (`midiCoreHears`), so only its playhead is drawn from it - and that is the page's column, not the instrument's. The playhead moves to the instrument's score state; the page's tick goes. |
| `arpTick` | 17 steps | 2 (brain, arp) | The page's arpeggiator steps on the default too, writing its step into the page's notes (`arpApply`), beside the instrument's arpeggiator on the audio clock (5v). Its MIDI out is guarded and arptest's default leg hears one arpeggio, not two; but the page's notes, which the face reads, follow the page's arpeggio. It goes in step 5, with the face reading the instrument's. |
| `morphStep` | 25 applies | 1 (setupmorph) | The page's morph walk moves the face's sliders on the default. 5v moved the walk to the core, so this is either the face following a fader that a routing moves - the face's, and harmless - or a second walk. `visualMatrix.morph.pos` in the same suite says a source on the fader is computed by the page. To check in step 5. |
| `clockStep` | `delayFollow` 69, `lfoSync` 5 | 5 (fade, regress, rotate, brain, time) | The page follows the tempo for the delay's note values and the LFOs' sync, and writes the result into the setup (`genSet("delayMs")`). The instrument does the same on its own clock. It goes, once the face reads the delay time back. |
| `standIn.tick` | 1,340 | 4 (soundstart, brain, enlarge, note) | The instrument itself, on the page's thread before the first press (makeBrainHost's stand-in). This is the core, not the page's brain. It stays. |
| `lfoStep` (main) | 2,087 | 1 (host) | The plugin's page, whose host names no LFOs (`postsLfos` false), steps the page's own. It does not happen on the site. In the plugin's shell test it is the page's LFOs driving the view; it goes when the plugin posts its LFOs as the site's worklet does. |
| at boot only: `scanStep`, `midiApplyGate`, the tone source's `tick` | 1,290 frames | 63 | The page starts on `makeToneSource` and hands over to the instrument once it answers - about twenty frames a page. Step 5 must start the page on the instrument, or its counters cannot be at nought. |

These worked on the default **never**, over the whole suite:

- the constellation (`drawConstellation`: 2,549 frames, all on `?brain=js`);
- each layer's own picture (`layerPicturesStep`: 7,083 frames, all on
  `?brain=js`);
- Scan's tables (`scanStep.table`: 17,678, all on `?brain=js`);
- the events (`fireEvents.fire`: 15, `?brain=js`);
- the gate after boot;
- the page's LFOs on the site.

So what step 5's counters must reach is this. At nought: `pictureStep`,
`phosphorFade`, `phosphorDeposit`, `photoStep`, `fadeStep`, `stepRoutes.host`,
`fadeDotStep.shown`, `hearingStep`, `scoreTick.*`, `arpTick.step`,
`clockStep.*`, every `frames.tone` and `sourceTick.tone`, and `lfoStep.main`.
To be decided: the visual matrix, `morphStep.apply` and `syncMonitor`. Allowed:
`updateEnvelope` and `standIn.tick`.

## 2. The checks, sorted

Every `check(...)` call (and `null(...)`, where a suite wraps `check` in one)
that reads a page opened on `?brain=js` or `?core=js` was given one of three
kinds:

- **numbers**: the engine's or brain's arithmetic, whose assertion is kept
  in C++;
- **page**: the page's brain as a page; it becomes a click on the default,
  or goes;
- **engines compared**: it exists to hold the two engines together, and
  goes.

A check in a loop is one row. The sort was made by reading the suites, and
every row is in the appendix with its line and one line on why.

| Suite | How it opens the page's brain | numbers | page | engines compared | on the default, not listed |
|---|---|---|---|---|---|
| alias | wholly | 10 | 5 | 0 | 0 |
| arp | wholly, with a loop over both brains at the end | 18 | 3 | 2 | 0 |
| brain | the way back, and the counters' null | 0 | 1 | 3 | 72 |
| budget | wholly | 21 | 5 | 0 | 0 |
| cap | wholly | 0 | 11 | 0 | 0 |
| clock | wholly | 27 | 9 | 0 | 0 |
| constellation | 39 of 42 (opened() defaults to it) | 0 | 39 | 0 | 3 |
| contract | wholly | 0 | 7 | 0 | 0 |
| drawbar | wholly | 17 | 16 | 0 | 0 |
| enlarge | one leg | 0 | 21 | 0 | 20 |
| env | wholly | 19 | 14 | 0 | 0 |
| fade | one leg of a loop | 0 | 1 | 3 | 50 |
| filter | wholly | 11 | 21 | 0 | 0 |
| hands | wholly | 4 | 35 | 0 | 0 |
| hand | two legs (desktop, phone) | 0 | 39 | 0 | 5 |
| harmony | wholly | 6 | 14 | 0 | 0 |
| host | one check, a null | 0 | 1 | 0 | 49 |
| input | wholly | 6 | 5 | 0 | 0 |
| keys | wholly | 0 | 37 | 0 | 0 |
| lane | wholly | 8 | 26 | 0 | 0 |
| layerpicture | one leg | 12 | 3 | 0 | 4 |
| layerplane | one leg | 25 | 20 | 0 | 4 |
| layer | wholly | 15 | 21 | 0 | 0 |
| livefx | wholly | 6 | 11 | 0 | 0 |
| live | wholly | 5 | 35 | 0 | 0 |
| loop | wholly (and `&core=js` for Scan's tables) | 24 | 6 | 0 | 0 |
| menv | one leg | 0 | 1 | 0 | 22 |
| midi | wholly | 23 | 27 | 0 | 0 |
| modrow | one leg | 0 | 3 | 0 | 43 |
| mod | wholly | 7 | 23 | 1 | 0 |
| morph | wholly | 9 | 13 | 0 | 0 |
| onset | wholly | 4 | 8 | 0 | 0 |
| overlay | one pass of two | 0 | 21 | 0 | 6 |
| perform | wholly | 4 | 8 | 0 | 0 |
| photo | 30 of 37 | 13 | 17 | 0 | 7 |
| picturepreset | wholly | 5 | 5 | 0 | 0 |
| plane | wholly | 26 | 11 | 0 | 0 |
| pulse | wholly | 12 | 12 | 0 | 0 |
| rotate | none (a comment only) | 0 | 0 | 0 | 40 |
| scale | wholly | 0 | 24 | 0 | 0 |
| scan | wholly | 43 | 10 | 2 | 2 |
| schema | wholly, with no reason given | 0 | 14 | 0 | 0 |
| score | wholly | 16 | 4 | 0 | 0 |
| shape | wholly | 24 | 5 | 0 | 0 |
| soundstart | legs of two loops, and `&core=js` | 0 | 11 | 3 | 7 |
| strike | wholly | 26 | 6 | 0 | 4 |
| wasm | wholly (the two engines) | 1 | 7 | 33 | 1 |
| worklet | wholly | 17 | 18 | 0 | 0 |
| **48 suites** | | **464** | **654** | **47** | **339** |

About seventy of the 654 page rows are "no page errors" and the like, which
go with their legs. Of the rest, roughly half read only the face - `restore`
and `snapshot`, panels, the keyboard's own stack, browser storage, the
display's `capture()` and `measure()` - and move to the default by dropping
`&brain=js`. These suites are almost wholly of that kind: `cap`, `scale`,
`schema`, `hands`, `hand`, `keys`, `lane`, `contract`, and the Enlarge and
overlay legs. The other half test a path only the page's brain has, and go:
its worklet plumbing, its live-input insert, its stand-in sources, its own
Mic lanes, `toTone`, and the gate handed between brains.

### Where the numbers checks go

The plan sends the numbers checks to "offline renders of the core (a general
`render_cpp` grown from `response_cpp`)". Read check by check, they split
three ways:

- **Engine pieces, driven directly.** These are most of them: `waveAt` with
  the correction off (alias), `cycleTables` (drawbar), `makeGeneratorCore`
  with a raw `set("voices")` or routes on a slot (pulse, voicefx-like checks
  in plane and layerplane), `scanRead` and `scanTables` on hand-made grids
  (scan, strike), `scoreColumn` (score), `makePictureMeter` fed made-up
  grids (shape), `clockTap` and `transportBeat` at synthetic times (clock),
  and `core.budget` with each voice's flags (budget). These belong in
  parity's own tools - `generator_cpp`, `scan_cpp`, `score_cpp`,
  `picture_cpp`, `clock_cpp` - which already drive the same pieces in C++.
  Each moves as an assertion against the C++ output alone, written with its
  null. The JavaScript twin goes in step 6.
- **A sound from a setup and a performance**: the generator's band-limit,
  the envelope's timing, layers, the morph, the loop's verdicts. These are
  `render_cpp`, but it needs more than a setup code and timed MIDI:
  - input samples (input, livefx);
  - a source held at a value (loop :92-:276, photo :338, mod :157-:378 set a
    source's value by hand);
  - per-layer lanes kept apart from the heard pair (layer, layerplane);
  - readings from inside the brain: an LFO's phase, the envelope, the
    voices, the stage's holds, the per-slot loop totals and the meter's
    verdicts. Loop's thirteen stability checks read all of those.
- **Not the core's at all**: alias's harmonics pane, harmony's interval text
  and the display's measurement, which are the face's and move to the
  default; and a few that read only the corpus or preset data (perform :96
  to :100, picturepreset :128 to :137), which need no browser.

So step 3 is two pieces of work. One is a batch of C++ unit assertions in
parity's tools, which is the larger and the easier. The other is a
`render_cpp` with a wider input, which is the harder and the smaller. That
probably makes step 3 cheaper than the plan's 4 to 8 sessions at the top,
and the design of `render_cpp` larger than "grown from `response_cpp`".

## 3. Only the page's brain does it

- **The constellation**: 39 of constellation's 42 checks, and
  `drawConstellation`'s 2,549 frames, all on `?brain=js`. Removed in step 4,
  by the owner's decision: gone from the page on 14 Nov (section 12), with
  `constellationtest.py`.
- **Each layer's own picture, on the page** (`layerPicturesStep`, never on the
  default). The instrument has its own per-layer pictures, so the
  layer-picture checks are numbers about the core, not a page-only feature.
- **Scan's tables in the page's generator**. Loop opens
  `?brain=js&core=js`, not to compare engines, but because only the
  JavaScript generator hands out `genSettings().scanTable` (looptest :453,
  :463). The instrument's tables reach the page only as the overlay's
  thumbnails, so a check of the table itself needs `render_cpp` or
  `scan_cpp`.
- **The live-input effects insert** (livefx) and **the input opened only
  while heard** (input :189, :196): the instrument hears its input always, so
  these go rather than move. Before livefx's six numbers checks are ported,
  someone should confirm that the default site puts a microphone through the
  instrument's effects at all.
- **The onset's events on stand-in destinations** (onset :184 to :188): the
  suite registers destinations of its own on the page, which the core's
  matrix has no counterpart for. The detector itself is ported
  (`Hearing::onsetStep`), so its checks move. The firing checks go, unless
  the core gets a test destination - the owner's call.

## 4. Surprises that change the later steps

1. **The plan's time table puts suites in the wrong rows.** The plan says
   `loop` (4 min) and `perform` (3.2 min) are "on the default already". Both
   are wholly on `?brain=js` (looptest :58, performtest :69), so their
   minutes belong with the whole-`?brain=js` suites. That makes the saving
   from step 3 larger than the plan's estimate. `phototest` is listed as
   one-leg but is 30 of 37 on `?brain=js`. `constellationtest` is listed as
   one-leg but is 39 of 42.
2. **`worklettest` compares no engines**, although the plan says it exists only
   to compare. Its module text holds the default's `scope-brain` processor,
   so three of its checks must move to the default rather than go: the
   module evaluates and registers (:76), a data URL loads (:209), and a blob
   from `file://` does not (:216). The message shown when the module cannot
   load (:378, :380) also wants a default version.
3. **`wasmtest` does not go whole.** `build.py --check` (:63) is the only guard
   that the page carries the current core, and it opens no page; it moves to
   parity or the build. The compiled codec's own checks (:579, :588) stay,
   since that codec stays.
4. **The face leans on the page's brain in more places than 5m found.**
   The counters confirm the second grid (section 1). The check sort adds:
   - the interval readout (`harmonySaid`, harmony :160 to :167);
   - the bend reading (hand :102);
   - a split's voices (hand :440);
   - the lane's live tick, driven by the page's `lfos` (lane :234);
   - rows shown or hidden by the page's layer state (scan :362, strike
     :266 and :332);
   - Stop's all-notes-off (score :236).

   Each is a place step 5 has to point at the instrument's readings. With
   the grid, the photocell, the fade's dot, the visual matrix and the boot,
   that is about a dozen. The plan expected "a few". **Step 5 grows by the
   session or two the plan held in reserve: 2 to 3 sessions, not 1 to 2.**
5. **Two checks lean on `?brain=js` for their reference.** braintest :175 and
   its null :178 run on the default, but take `site_skew` from a `?brain=js`
   page (:95). When that page goes, half of each condition drops out without
   a word. Both need restating against the quarter cycle alone.
6. **One null cannot fail.** scantest :325 subtracts `plainB["BL"]` from itself,
   so it reads nought whatever the code does. It should be fixed when the
   check moves (step 3).
7. **Some pins were measured on the JavaScript engine**: plane's alias pins
   (:250 to :252), plane's cost (:324), and budget's cost checks (:119,
   :171). The governor's cost model was fitted to JavaScript milliseconds.
   Moved to C++, the costs need measuring again, and the model may need
   fitting again, which could change what the instrument gives up under
   load. That is a sound change, so it is the owner's to hear.
8. **Several legs can simply go**, because their default twins already hold
   the same claims: menv :170, modrow's leg (:593 to :602), overlay's whole
   second pass (21 checks), soundstart's `?brain=js` loop entries (11), and
   hand's two legs beside its default one. Overlay and modrow are serial
   suites, so this is real time saved. It is cheap and can come first in
   step 3.

## 5. Checks

- The full web suite, with the counters and through `braincounts.py`: 97
  suites in 53.3 minutes, everything passes, 3,042 checks. That includes
  braintest's new section, its six checks and their nulls.
- `extract.py` and `node --check`: clean.
- Parity: red on its first run, because `matrix_js.mjs` threw on a direct
  `brainCount` in the lifted visual loop (section 1). Every call was made
  optional, then parity was run again, whole: 947 checks, every one passes
  ("the C++ core is the page's, sample for sample"). Since then the page has changed only in that spelling, and
  braintest and the matrix's runner were run again over it.

## 6. Step 3, batch 1 (13 Nov)

The first batch of step 3: the suites whose `?brain=js` checks were almost
wholly *page* rows reading the face - `cap`, `scale`, `schema`, `hands`,
`hand`, `keys`, `lane`, `contract`, and the Enlarge and overlay legs. Every
row in their appendix tables below has a "Batch 1" column saying what became
of it. In short: 247 listed rows; 208 moved to the default page (9 of them
rewritten to read the instrument), 27 gone, 4 gone to parity as assertions on
the core's own output, and 8 left on `?brain=js`. Nothing in `scope.html` or
`core/include` changed.

| Suite | Checks before | after | `?brain=js` opens | What happened |
|---|---|---|---|---|
| cap | 11 | 12 | 1 to 0 | Moved; the Mic pressed, not `toMic()` (below). +1 null |
| contract | 7 | 8 | 1 to 0 | Moved; Mic and Bands pressed. +1 null |
| schema | 14 | 15 | 1 to 0 | Moved as it was. +1 null on restore |
| scale | 24 | 25 | 1 to 0 | Moved; the lanes-untouched pair given a note. +1 fixture check |
| keys | 37 | 40 | 1 to 0 | Moved; pitch and interval read off the instrument's lanes. +3 nulls |
| lane | 34 | 35 | 1 to 1 | 26 rows moved; the 8 numbers rows left on a `?brain=js` page of their own. +1 null |
| hands | 39 | 35 | 1 to 0 | 35 moved (routings rewritten); the 4 numbers rows to parity (+5 there) |
| hand | 68 | 68 | 2 to 0 | Both legs moved; the split's fixture clicks Poly, its frequencies from the notes |
| enlarge | 48 | 45 | 1 to 0 | Leg moved; the grid-to-the-bit comparisons gone, for "sends the instrument nothing" |
| overlay | 62 | 35 | 1 to 0 | The `?brain=js` pass gone (21 checks, 7 nulls); its default pass holds each claim |
| **ten suites** | **344** | **318** | **11 to 1** | and parity +5 |

### Checks that passed on the default for the wrong reason

Dropping `&brain=js` from the ten suites, unchanged, left 3 checks red
(`hands` 1, `hand` 3, all in fixtures the instrument never heard) and every
other check green. The green was the warning. Comparing what each check
printed on both brains, and reading what each reads on the default, found
these, each fixed where it stands:

1. **`toMic()` leaves the instrument.** Called directly, as `cap` and
   `contract` did, it swaps the default page's source for the page's own
   Mic - the very source they read on `?brain=js` - so both suites passed
   unchanged and tested nothing of the site. The Mic and Bands buttons keep
   the instrument (`hostToMic`, `hostSplit`); both suites press them now, and
   check `kind` is `host` and `drawsInput`. The old path, put back by hand,
   fails them.
2. **The mirror is the page's MIDI arithmetic.** `keys` read
   `state.source.settings.freq` for "the generator plays it" and
   `settings.interval` for the dyad. On the default those are the page's
   mirror of the setup, written by the page's own MIDI apply
   (`midiApplyNotesTo`), not anything the instrument did, so they passed
   unchanged. Both now read the lanes the instrument drew: the pitch of a
   held E3 by its zero crossings, and the ratio of a latched fifth's two
   lanes, with nulls against D#3 and a fourth.
3. **The page's route compiler.** `hands` read each hand's routing depth off
   `workletRoutes()`, the page's compiler for its own worklet, which runs on
   any page but feeds nothing on the default. It reads the routing the face
   stores and sends (`mod`, `modB`) now; the core's per-hand depth is the
   matrix's (`loopValue`), which parity's native checks below reach.
4. **The page's second grid.** `enlarge` compared `phosphor.grid` and Scan's
   table to the bit with Picture only on and off, and with Which hands on one
   hand and both. On the default that grid is the face's copy (section 1),
   which nothing heard reads, and the page's Scan has no table: the grid
   comparison would pass and mean nothing about the sound. Replaced by every
   message to the instrument counted while Enlarge, Picture only, the Trail
   and Which hands are pressed - none - with a knob turned as the null. The
   Trail's and the resize's grid checks moved, said at the site to be the
   face's grid, the Persistence's reference, not what Scan reads.
5. **A check that read silence on both brains.** `scale`'s "a modulated full
   scale does not touch the captured samples" and its dBFS twin compared two
   captures of nothing - the page waits for a note since 10 Nov - and so
   passed whatever capture did. Found by the move, not caused by it: it was
   hollow on `?brain=js` too. A note is held now, with a fixture check that
   the lane is sounding; scaling the samples by hand turns both red.
6. **Unheard fixture calls.** `hand`'s split and `enlarge`'s Which hands set
   Poly with `setMidiMode('poly')`, which the instrument does not hear: it
   stayed in the Mono clicked earlier and drew no upper hand, so on the
   default these failed rather than passed. They click Poly now. In doing so
   `enlarge` turned up a lean for step 5: with the instrument drawing one
   hand, `sourceFigures()` still said two, because it is the page's.
   Its check now reads whether each hand draws its own picture off the
   instrument (`state.source.layerPictures.live`), which goes red there.
7. **Two of my own, caught by their nulls.** The first parity strike check
   ran on `SPLIT`, whose `bScan` loads the Picture as the upper hand's own
   already, so the click meant to unlink it linked it, and every write went
   to the wrong hand; the main check went red and its null passed
   regardless. It runs on `SPLIT` without `bScan` now, said at the site. And
   a first null for `keys` assumed the gate flag meant "shut now"; it is the
   generator's mode (waits for notes) on both sides, and the null was
   replaced by reading the lane's silence.

### Nulls seen red

Each moved or rewritten check was fed a known-wrong value as it landed: the
old `toMic()` path (cap, contract: red); a ring not yet written back (cap:
flatline red); no note held, and the scaled capture multiplied by its gain
(scale: fixture red, then both untouched checks red); no routing on full
scale (scale: two red); D#3, a fourth, a held note's sound (keys: standing
nulls); a source at rest on the live tick (lane: standing null); restore with
the table's reader loosened (schema: standing null); the bass a semitone off
(hand: B's red, A's not - at 131 Hz a semitone moves the fit's moment too
little in a 10 ms window); `setMidiMode` put back (enlarge: three red); a
knob turned while counting messages (enlarge: standing null). On the core,
for the four rows that went to parity: the strike's per-hand amount made A's
for both layers in `scan.h`, and the fold's per-hand depth made A's in
`matrix.h` - each red, then put back (no diff left in `core/include`).

### What it changes for the rest of step 3

- **Every page call a suite makes has to be read for whether the instrument
  hears it.** `toMic()`, `setMidiMode()`, `genSet()` (the mirror only),
  `midi.layers.point = ...`, `pictureStage.glow = ...`: each either leaves the
  instrument or never reaches it. The README already says it of
  `setMidiMode`; the rule is wider (the README entry added with this batch).
  A suite that reads the mirror (`genSettings`, `state.source.settings`) after
  notes reads the page's MIDI apply.
- **Parity's native instrument tool takes per-hand numbers without
  `render_cpp`.** `instrument_cpp`'s `layers`, `lgrid` and `hold` carried all
  four of `hands`' numbers rows. Other suites' per-layer checks (layer,
  layerplane, layerpicture) may go the same way before `render_cpp` exists.
- **The visual matrix wants one decision.** `scale`'s three checks that hold
  LFO 1 by hand and step the page's matrix on `view.scale1` moved, as the
  face's: on the default site that matrix is what moves the screen's own
  destinations today. `lane`'s eight on `view.zoom` and `trig.position` are
  the same kind of check and were left on `?brain=js`, as this batch was
  told to leave numbers rows needing a source held at a value. Whichever way
  step 5 decides the visual matrix (section 1's table), both sets should
  follow it together.
- **The instrument's published state is not a setup to read fields from.**
  `scopeState` is a base code plus the hand moves since (`pluginHands`), so a
  check cannot read "what bAmp does the instrument hold" from it. `hands` and
  `hand` read the face's mirror and lean on parity's G6 for the core;
  a resolved reading would make them direct.

## 7. Step 3, batch 2 (13 Nov)

The engine pieces the numbers rows drove directly - `waveAt`, `cycleTables`,
`makeGeneratorCore` with raw voices and routes, `scoreColumn`, the picture's
meter, the clock at made-up times - and the three layer suites, which batch 1
found `instrument_cpp` could carry. Every row in their appendix tables has a
"Batch 2" column. In short: 253 listed rows; 151 gone to parity as assertions
on the core's own output, 65 moved to the default page, 16 rewritten to read
the instrument or the setup the face sends, 4 split between the two, 6 gone,
and 11 left on `?brain=js`. Nothing in `scope.html` or `core/include` changed.

The numbers live in `core/tests/pieces/`, a module a suite (`pieces/run.py`
runs them alone, in about a minute; parity runs them all as its last
section). They are assertions on the core alone, so they have no golden file:
they say what the sound should be, not that it is what the page made. Every
check has its null beside it, seen red; `PIECES_INCLUDE` builds the tools
against a scratch copy of `core/include`, which is how each piece was
mutated by hand without a diff left behind. New commands, no existing one
changed: `waveRun` in `functions_cpp`, `play` in `clock_cpp`, `clear`,
`column` and `pitches` in `score_cpp`, and the meter's fixtures in
`picture_cpp` (`mnew`, `mupd`, `mring`, `msegs`, `mempty`, `mpair`).

| Suite | Web checks before | after | pieces checks (nulls) | `?brain=js` opens | Rows: to parity / moved / rewritten / split / gone / left |
|---|---|---|---|---|---|
| alias | 41 | 7 | 43 (7) | 1 to 0 | 10 / 5 / 0 / 0 / 0 / 0 |
| drawbar | 33 | 16 | 30 (13) | 1 to 0 | 17 / 14 / 1 / 0 / 1 / 0 |
| pulse | 24 | 13 | 21 (9) | 1 to 0 | 11 / 11 / 1 / 0 / 1 / 0 |
| score | 20 | 4 | 28 (13) | 1 to 1 | 16 / 0 / 0 / 0 / 0 / 4 |
| shape | 32 | 13 | 50 (25) | 1 to 1 | 22 / 4 / 0 / 1 / 0 / 2 |
| clock | 36 | 14 | 54 (25) | 1 to 1 | 25 / 3 / 2 / 2 / 0 / 4 |
| layer | 36 | 22 | 25 (12) | 1 to 1 | 14 / 14 / 3 / 0 / 4 / 1 |
| layerplane | 49 | 26 | 37 (12) | 1 to 0 | 24 / 12 / 8 / 1 / 0 / 0 |
| layerpicture | 19 | 7 | 16 (7) | 1 to 0 | 12 / 2 / 1 / 0 / 0 / 0 |
| **nine suites** | **290** | **122** | **304 (123)** | **9 to 4** | **151 / 65 / 16 / 4 / 6 / 11** |

The counters over the nine suites (`run.py --brain-counts`, before on
00d51da and after): pages on `?brain=js` 9 to 4; frames the page's brain
stepped there 6,767 to 2,001 (shape's survey 1,490 of them, the clock's 294,
the score's 160, layer's 57); `layerPicturesStep` 1,230 to 3, `scoreTick.step`
51 to 11, `clockStep.lfoSync` 189 to 51. On the default the same suites'
frames went from 892 to 2,772, which is the face's, as section 1 says.

(alias's 41 is its loops' iterations; its pieces count its floors one per
shape and pitch, with the uncorrected control as the null of each.)

What stays on `?brain=js`, and why: score's Stop, hidden page, ticked box
over real frames and its page errors, and clock's LFO card, tempo row and Bar
row - those panels draw the page's own `lfos`, `transport` and `score`, so on
the default they would pass for the page's reason (step 5's, below); shape's
survey (`:387`, `:389`), corpus setups played with the loop closed, which is
`render_cpp`'s; and layer's split point learned, which is a page defect.

### Checks that passed on the default for the wrong reason

1. **`restore()` called directly changes only the face.** Only `loadCode` and
   a preset's load send the instrument a setup (`hostSendSetup`), so a code
   restored by hand leaves the instrument as it was. layerpicture's setup
   check went red once it read the instrument's own moves; all three layer
   suites load codes with `loadCode` now. Batch 1's list of unheard calls
   gains `restore()`.
2. **Two of alias's pane checks passed on nothing, and a third on the wrong
   note.** With no pane reading their partials were empty lists, and `all()`
   of nothing is true; the note let go as a null showed it. They require their
   partials now. And the full run found the fixture racing on the default:
   the Frequency slider's move could reach the instrument before the note-on,
   which then played its own A4. The pane names the bin, 430.66 Hz, which
   440 falls in too, so "it finds the fundamental where it was put" passed at
   440 and the 1/k check failed one load in three. The note sounds before the
   slider moves now, and the fundamental is read off the instrument's lane as
   well, with 440 as its null (red with the note sent after the slider).
3. **The page's mirror again.** pulse's and drawbar's "without writing the
   slider", and the layer suites' panel rows, read `genSettings` or
   `state.source.settings`, which only the face writes on the default. They
   read the instrument's lanes, the sliders and `snapshot()` now.
4. **The split point learned (layer :243).** On the default, Learn and the
   next key move the face's point ("at G3") and not the instrument's: A3 still
   lands in A's lanes. The check read `midi.layers.point`. Left on
   `?brain=js`; only a page change fixes it.
5. **A clock byte inside a note-on, from a real port, is lost on the site.**
   The page's `midiBytes` cuts a port's message at every status byte, real-time
   ones included, and the core's keyboard drops a half message between calls:
   in `instrument_cpp` the note plays at 0.34 sent whole and at nothing sent in
   pieces. clocktest's `:180` passed only because it called `midiBytes`
   directly. The pieces hold the core's parser on whole bytes; the site needs
   a page or core change, the owner's to schedule.
6. **Fixtures the instrument never heard**: `setMidiMode`, `setDisplay`,
   `genSet` and `state.persistence` in shape's live section and the layer
   suites, clicks and input events now. And clock's tap tempo started at 120,
   which is also what the taps make, so "one tap leaves the tempo" could pass
   by coincidence; it starts at 100.

### Nulls and mutations seen red

Every piece check has its null, and each main check was also fed its null's
reading (shape with a swap switch, the others by hand) and seen red. The core
was mutated in scratch copies, each turning the checks it holds red: `wave.h`
seven ways (the square's polyBLEP off, the pulse floor and centring, the
drawbars' Nyquist fade, 2 dB a step, 16' rectified, `cycleRead` always the
richest table); `generator.h` (a step of nought to `waveAt`, the width's push,
B reading A's width, LFOs stepped twice when layered, B's plane step removed,
B's lanes crossed, the score voice's level and decay); `keyboard.h` (the
chord split's `>=`, real-time bytes inside a message); `picture.h` eight ways
for the meter and four for the layers (Both summed, the cross term's hold,
A's meter governing B, A's grid measured for both); `clock.h` ten ways;
`score.h` six; `restore.h` (dorian's ninth, B's synced echo following A's).
`git diff core/include` is empty.

### What it changes for the rest of step 3

- **A route's held value can be put into `generator_cpp` directly** (index
  -1, held, heldB), so many rows left for "a source held at a value" may move
  the way layerplane's did, without `render_cpp`: loop's, photo's and mod's
  rows are worth reading again for it.
- **`restore()` is on the list of unheard calls**, with `toMic()`,
  `setMidiMode()`, `genSet()` and the rest; `loadCode` is the heard one.
- **Step 5 grows by the clock and score panels**: the LFO card's reading,
  the tempo and Bar rows and the score's playhead all draw the page's own
  brain, and on the default site both scores run beside each other.
- **Two defects for the owner**: the split point learned only on the face,
  and the clock byte inside a port's note-on.
- **Time**: the pieces take about a minute, the generator and instrument
  renders most of it; parity grows by that.

## 8. Step 3, batch 3 (13 Nov)

Scan and the strike (their numbers rows to `core/tests/pieces/`, their page
rows to the default), and the rows batches 1 and 2 left for "a source held at
a value": lane's eight, mod's :157 to :378, photo's :338 and loop's :92 to
:276. Every row in those six appendix tables has a "Batch 3" column. Nothing
in `scope.html` or `core/include` changed; `git diff core/include` is empty.

No `render_cpp` was needed. A held value is `matrix_cpp`'s scripted source
(`value ID V`), which with `picture` and `reach=photo`/`reach=bored` is a
picture source at the core's own reach; its new `screen` command builds the
instrument's own `PictureRun` on the matrix, so the visual destinations (the
zoom, the trigger position, the rotation, the full scales) are screen.h's,
spans and bases included; and `lroutes` prints the routes it hands the
generator with the loop's flag, for `generator_cpp` to play. New commands, no
existing one changed: `tables`, `geometry`, `follow`, `read`, `path`, `show`
and `laid` in `scan_cpp`; `screen`, `vset`, `view`, `lroutes` and the two
reach names in `matrix_cpp`; `dump` in `capture_cpp`; `reads` in
`instrument_cpp`.

| Suite | Web checks before | after | pieces checks (nulls) | `?brain=js` opens | Rows: to pieces / moved / rewritten / split / gone / left |
|---|---|---|---|---|---|
| scan | 71 | 15 | 58 (28) | 3 to 1 (`?brain=js&core=js`, the held run alone; the `?brain=js` site legs and the page section's own page gone) | 19 / 4 / 3 / 1 / 4 / 1 |
| strike | 36 | 11 | 27 (13) | 1 to 0 | 15 / 5 / 0 / 0 / 0 / 0 |
| lane | 35 | 27 | 14 (6) | 1 to 0 | 8 / 0 / 0 / 0 / 0 / 0 |
| mod | 31 | 27 | 8 (4) | 1 to 1 | 4 / 0 / 0 / 0 / 0 / 0 |
| photo | 37 | 35 | 4 (2) | 1 to 1 | 2 / 0 / 0 / 0 / 0 / 0 |
| loop | 75 | 61 | 24 (10) | 2 to 2 | 10 / 0 / 4 / 0 / 0 / 0 |
| **six suites** | **285** | **176** | **135 (63)** | **9 to 5** | **58 / 9 / 7 / 1 / 4 / 1** |

(Web counts are checks run, a loop's iterations each. "Rewritten" rows on
loop are its page-compiler rows, :147, :149, :186 and :188, now asked of the
core's matrix in the pieces rather than dropped as the inventory proposed.
mod, photo and loop keep their `?brain=js` pages for the rows outside this
batch.)

The counters over the six suites (`run.py --brain-counts`, before on
6358eb8's parent with the same page, and after): pages on `?brain=js` 9 to
5; frames the page's brain stepped there 31,539 to 25,027, of which loop's
stability runs, outside this batch, are 25,477 and 22,584 (they read the
stage over seconds of real frames and are render_cpp's); scan's 3,430 to
562, strike's 594 to 0, lane's 91 to 0, mod's 871 to 829 and photo's 1,076
to 1,052 (their pages stay for rows outside the batch, so few frames go
with the rows that left). `scanStep` there 31,273 to 24,759. On the default
the six suites' frames went from 2,630 to 3,404: scan's page section and
strike's Reads row moved to the default page, the face's own.

The parent's run failed scan's "the page's brain on the compiled generator
sends it the tables, and it plays them" (0.0035), one of the known flaky
legs; it is one of the `?brain=js` site legs this batch removed.

The full run after (97 suites, 55 minutes, 2,748 checks passed): one
failure, looptest's "with Scan at its top, its wave was still moving" at a
median of 0.043 under three suites at once, a row this batch left on the
page; alone, twice, it passed (0.078 and 0.098 on the same reading).
Parity passed, 1,443 checks.

### Checks that passed on the default for the wrong reason, or could not fail

1. **Stop does not reach the instrument.** Scan's "held still - the screen
   stopped - Scan is an ordinary tone", moved to the default unchanged,
   failed there: the site's Stop holds the face's screen only, and the
   instrument goes on reading its own moving grid (0.0084 held against 0.0079
   running). A site defect, in `web/docs/after-stage-5.md`; the check stays on
   a `?brain=js&core=js` page of its own, judged against its own run before
   the stop now, since the moving run it was judged against went to the site
   legs.
2. **The page's mirror once more.** Scan's Depth and setup-code rows read
   `genSettings().scan` and `scan.soft`; on the default those are the face's.
   They read `snapshot()` and the slider now, and the split's Depth row clicks
   Poly (it called `setMidiMode`, unheard) and reads both hands' depths off
   the setup the face sends.
3. **scantest :325's null could not fail** (section 4, surprise 6): B's lanes
   minus themselves. Two nulls replace it, each able to fail: the table and
   depth given to A move A's lanes, and B's table at B's depth of nought
   leaves B's lanes to the bit.
4. **Four checks the mutation pass found could not see the fault beside
   them**, three of them carried over from the page:
   - a table is evened to its peak, so no check of a reading's shape sees the
     blur's kernel summing to two (new: a figure at the edge of darkness, at a
     fixed level, darkness through the blur and a table at twice);
   - the bend's table has nothing past the 32nd harmonic, where the levels
     part, so it could not see a voice reading the richest level at every
     pitch (new: a rich table at 2 kHz against the hand's reading with the
     step and without);
   - photo's ceiling, held at one, read 0.5 through the loop's total whatever
     the photocell's reach (both are a half): held at a half now;
   - the hold sent back at one: one from a quarter is past 0.005 anyway, so
     the clause for "back to one" was never exercised (0.997 then one now).
   And one of mine: the dim figure's level was first found from a reading
   of the core, so a mutant blur moved it with itself; it is a number now.
5. **A route's loop flag.** The first loop piece marked every held route as
   the loop's, which sent the two LFOs of "contributions add" down the loop's
   path and hid a generator that let the second held route replace the first;
   `lroutes` says which route is the loop's.

### Nulls and mutations seen red

Every piece check has its null beside it, seen red, and every moved web check
was run with a known-wrong fixture (striketest without the Poly click: the
row check red). The core was mutated in scratch copies (`PIECES_INCLUDE`),
37 ways, each turning at least one check red once the four fixes above were
in: `scan.h` fifteen (tables not evened, every level every harmonic, the
darkness threshold, the reading centred, the blur's kernel, the follow's
rate, the hold back to one, the freeze, the strike's level, place, Scan-off
and layer rules, both read as A's, the crossed hold, never crossed);
`generator.h` five (the tick a step, the crossfade half a tick, the hold
ignored, B's depth A's, held routes replacing); `osc.h` (Scan read without
the step); `picture.h` four (the fade, boredom's rise, leak and reach);
`matrix.h` six (the visual and generator loop totals, every source in the
loop, offsets unclamped, no reach ceiling); `loop.h` (the photocell's
reach); `screen.h` five and `capture.h` one (the zoom's and position's
spans, the zoom ignoring its offset, the offset moving the level or the
knob, and the capture ignoring the offset - the bug lane's comment
remembers).

### What still needs `render_cpp`, and with what input

- **scan :539** (held still, the screen stopped): a corpus setup and a held
  note, the loop closed over eight seconds, and a "screen stopped" event at
  two - once the owner decides what Stop does on the instrument.
- **loop :523 on** (the seven seeds' stability runs, the reverb in the loop,
  Scan's table moving, the crossed pair, the holds): corpus setups played
  with the loop closed for thirty seconds, reading the stage's holds, the
  meter's verdicts, per-slot loop totals, each layer's table (`scanTable`,
  which the instrument never hands out) and the phosphor grid frame by frame.
- **shape's survey** (batch 2): corpus setups with the loop closed.
- **budget**, **input** and **livefx**: not this batch's (budget's costs
  were fitted to JavaScript milliseconds; input and livefx need input
  samples and may go rather than move, section 3).
- The visual matrix (lane's eight and scale's three) did not need it: the
  core has its own (screen.h), which lane's now reads. Which matrix the
  face's screen follows on the site is still step 5's to decide, and scale's
  three, moved by batch 1 to the default as the face's, should follow then.

### What it changes for the rest of stage 5

- **Step 5 gains Stop**: what the face's Stop does to the instrument has to
  be decided before the page's brain goes, or the held-still check goes with
  it.
- **The pieces take about three minutes now** (scan 15 s, strike 27 s, loop
  17 s, the rest seconds), on top of batch 2's minute.
- **Matrix questions need no render**: anything that held a source at a
  value and read the matrix or the generator after it can use `matrix_cpp`
  with `screen` and `lroutes`, and `generator_cpp` behind it.

## 9. Step 3, batch 4 (13 Nov)

The plainer suites still on `?brain=js` - `env`, `filter`, `harmony`, `midi`,
`morph`, `onset`, `arp`, `perform`, `plane`, `picturepresets` - and the single
legs in `fade`, `host`, `menv`, `modrow` and `soundstart`. Every row in their
appendix tables has a "Batch 4" column. Nothing in `scope.html` or
`core/include` changed; `git diff core/include` is empty. Still no
`render_cpp`: what needed one stays, listed below.

New commands, no existing one changed: `biquad` in `functions_cpp`; `lane`
in `capture_cpp`; `filter` and `vset cutoff` in `matrix_cpp`; and `tone`,
`meter` and `routed` in `instrument_cpp` (native only, as `grid` is: the
generator's pitch fields, the keyboard's held notes and each layer's voices;
the instrument's own picture meter; each routing in its matrix with its
source's value).

| Suite | Web checks before | after | pieces checks (nulls) | `?brain=js` opens | Rows: to pieces / moved / rewritten / gone / left |
|---|---|---|---|---|---|
| env | 33 | 14 | 30 (10) | 1 to 0 | 19 / 10 / 3 / 1 / 0 |
| filter | 32 | 19 | 21 (9) | 1 to 0 | 11 / 16 / 3 / 2 / 0 |
| plane | 37 | 11 | 46 (20) | 1 to 0 | 26 / 4 / 7 / 0 / 0 |
| morph | 22 | 13 | 18 (8) | 1 to 0 | 9 / 5 / 7 / 1 / 0 |
| picturepresets | 10 | 10 | 0 | 1 to 1 (and a default page) | 0 / 4 / 0 / 0 / 5, one split |
| midi | 50 | 32 | 41 (12) | 1 to 0 | 23 / 26 / 0 / 1 / 0 |
| arp | 25 | 5 | 29 (10) | 2 to 0 | 19 / 2 / 0 / 2 / 0 |
| harmony | 24 | 16 | 12 (6) | 1 to 1 | 4 / 8 / 6 / 0 / 2 |
| onset | 12 | 6 | 18 (8) | 1 to 0 | 8 / 4 / 0 / 0 / 0 |
| perform | 12 | 8 | 6 (3) | 1 to 1 | 4 / 4 / 0 / 0 / 4 |
| fade | 62 | 60 | - | 1 to 0 | 0 / 1 / 1 / 2 / 0 |
| host | 50 | 51 | - | 1 to 0 | 0 / 0 / 1 / 0 / 0 |
| menv | 23 | 22 | - | 1 to 0 | 0 / 0 / 0 / 1 / 0 |
| modrow | 72 | 66 | - | 1 to 0 | 0 / 0 / 0 / 3 / 0 |
| soundstart | 32 | 18 | - | 3 to 0 | 0 / 0 / 0 / 14 / 0 |
| **fifteen suites** | **496** | **351** | **221 (86)** | **18 to 3** | **123 / 84 / 28 / 27 / 11, one split (274 rows)** |

(Web counts are checks run, a loop's iterations each, the "before" from a run
of the fifteen on ca69583: everything passed, 14.2 minutes. The row counts
are rows of the appendix tables, where one row may be several checks.)

What stays on `?brain=js`, and why: picturepresets' five run rows (`:241` to
`:256`, the corpus played with the loop closed over ten seconds, which is
`render_cpp`'s); harmony's two meter rows (`:195`, `:196`), which do not hold
on the instrument's meter (below); and perform's four microphone rows (`:231`
to `:265`), the input through the page's effects insert, which need input
samples and the question of section 3 answered first.

The counters over the fifteen suites (`run.py --brain-counts`, before on
ca69583 and after): frames the page's brain stepped on `?brain=js` 34,426 to
15,574 (`?brain=js&core=js` 253 to nought), of which picturepresets' run
rows are 14,034, perform's microphone rows 846 and harmony's meter rows 694;
perform's went from 9,439, modrow's 3,588 to nought. `arpTick.step` there
114 to nought. On the default the same suites' frames went from 14,992 to
17,305, the face's own. arptest's default page still shows `arpTick.step`
(seven steps): the page's arpeggiator stepping beside the instrument's, as
section 1 found, which is step 5's to stop.

The full run after (97 suites, 50.6 minutes, 2,593 checks passed): two
failures outside the batch - budget's "the model has each feature's cost
right relative to the others" (the filter at 0.48 of the median under three
suites at once; `{}` alone, twice), and honesty's reverb-on pass (Bass under
the tine piano), which failed again alone on Bass under the pad: the two
presets `after-stage-5.md` already names as sitting on their headings' edges
with the reverb on. Nothing honesty runs changed in this batch, and it fails
the same way on ca69583 alone (Bass under the tine piano): in three runs alone
here it failed every time, so on this container it is no longer an
occasional flake but the parked question of those two presets.
Parity passed, 1,664 checks.

### Checks that passed on the default for the wrong reason, or could not fail

1. **The page's arpeggiator still steps on the default** (section 1's
   `arpTick`), so every order row in arptest would have passed on the page's
   arpeggio, not the instrument's. They run on the core's keyboard now, and an
   `instrument_cpp` render holds the steps on the audio clock, as MIDI bytes.
2. **The page's mirror once more.** midi's dyad and mono rows read
   `state.source.settings`, which the page's own MIDI apply writes; morph's
   and plane's rows read `genSettings()`. They read the instrument (`tone`),
   or `snapshot()` for what the face sends. harmony's readout was driven by
   `setMidiMode` and `genSet`, which the instrument never hears; it clicks
   the mode buttons and the menus now, and still reads the face's mirror
   (`harmonySaid`), which is step 5's.
3. **A registry read empty.** On the default the onset hears the generator
   and the registry offers it nothing, so onset's "dropping an event on a
   value makes no routing" passed on an empty list. The Mic is pressed now,
   with a check that the source stays the instrument's and the onset hears
   the input, and a new null.
4. **`toMic()` once more, and a hook too late.** filtertest's chain check,
   moved unchanged, would have measured the page's own Mic and then a page
   tone (`toMic()`, then the old `srcTone` click: two chains on a `tone`
   source, seen red in its null); and its speaker hook, installed after load,
   missed the instrument's chain, which is built as the page starts. The
   Mic and Bands buttons, and the hook at init.
5. **A loose band.** envtest's "a key opens the envelope at the velocity it
   was played" was between 0.5 and 0.85, which a key at full velocity (0.8)
   passed too. It is the sustain times the velocity now, with that key as
   its null. Its fixture set the envelope with `state.source.set`, the page's
   generator; it moves the controls now.
6. **morph's key at full would fail at the page's figure.** The instrument's
   heard pair is not flat between 220 and 440 Hz (drawbar found the same in
   batch 2), so a station and a half reads -17.3 dB against the bare
   generator's -13.2. Restated as the same as Morph at 1.5 in the setup,
   within 0.3 dB, with the bare generator held to the half-saw separately.
7. **Fade's two brains.** "The two brains are the two" goes with the leg;
   what is left, that the leg is the instrument's, is read off the run's own
   source and seen red on the default page's boot frames (`tone`). Host's
   null, which opened `?brain=js` for "tone", is the same reading inside the
   plugin now.

Checks the mutation pass found could not fail, each strengthened:

- the envelope's legato rows read its level, not the samples, so a voice
  dropping the velocity from what is heard passed (a heard-level check now);
- the filter's priming was read behind the search span, on a sine starting
  near nought, where an unprimed filter has nothing to ring at (the source
  holds the window only, the sine on a 0.5 offset);
- two unfiltered lanes agree with each other, so "the lag lane is filtered
  too" could not see the filter skipped (the signal lane must be filtered as
  well);
- the hidden lane was compared at one sample of windows whose trigger moved
  with the cutoff (triggered on the hidden lane, compared whole);
- no check could see the cutoff slider's law, every cutoff found through the
  page's own `cutoffHz` (step 500 is 632.5 Hz, and the swing 40 Hz to 10 kHz);
- a clock byte before a status byte could not catch a parser that cancelled
  running status;
- a chord struck twice with every voice gone could not see a phase taken
  from a voice still releasing;
- the onset's threshold under fixtures whose flux was always about one
  (a smaller rise, 0.57, added);
- an event source with no value could not show the rule keeping it off a
  value.

Two mutations stayed green, as the pieces say: the joining voice's
reference taken from the highest held voice instead of the lowest, which for
voices born in step is the same phase; and the onset's threshold at 0.6,
just above the new fixture's 0.57.

### Nulls and mutations seen red

Every piece check has its null beside it, seen red. Every moved or rewritten
web check was run against a known-wrong fixture and seen red: the default
page's boot frames (fade), `toMic()` put back, a GainNode to the speakers,
the routing removed before the sweep, the slider written without its event
(filter); the hands' link removed, a code field dropped, OS4 unclicked, the
twist on `change` (morph, plane); a key at full velocity (env); the face's
stack cleared alone, which left the instrument at 0.303 (midi's panic);
onset's registry without the Mic; arp's code before the menus moved;
harmony's readout pairs. The core was mutated in scratch copies
(`PIECES_INCLUDE`), 77 ways, each turning at least one check red but the
two above: `envelope.h` and `generator.h` eight (an attack by time
constant, legato restarting, the velocity taken over a held key, a release
short of nought, a gated core open, the glide's pole by the envelope's
stage, the ungated level, the heard level without the velocity); `wave.h`,
`osc.h` and `generator.h` five for the morph and nine for the plane;
`capture.h`, `screen.h` and `functions` seven for the filter (Q linear,
unprimed, skipped under a lag, hidden lanes filtered, the cutoff's span,
`cutoffHz`'s law, the notch's b2); `keyboard.h` 26 for midi and the
arpeggio; `screen.h` two for the lag lock; `wave.h` and `generator.h` two for
just tuning; `voices.h` six; `picture.h` two for the meter; `hearing.h` six
for the onset; `matrix.h` six for the events; and `setup.h`, `sources.h` and
the split one each.

### What it finds about the site and the core

- **A port's notes under one running status lose the third note.** `90 3C
  64 40 64 43 64` is cut by the page's `midiBytes` into three-byte pieces
  and the core's keyboard drops the half message: in Mono the face holds 60,
  64 and 67 and the instrument plays E4. Batch 2's clock byte by the same
  mechanism; low priority, since Web MIDI hands over whole messages. In
  `web/docs/after-stage-5.md`. miditest's running-status row reads the
  face's stack, which parses it right, and says so at the site.
- **The instrument's picture meter calls a still figure "cycling".** A held
  just fifth of the Harmonic tone reads 0.02 to 0.05 change a frame on the
  instrument (the page's meter, on its own grid, 0.0055 and "settled"); a
  still unison of the same tone 0.058; a plain sine's unison nought. The
  core's grid flickers frame to frame on a figure with detail. Nothing heard
  reads the verdict (the stage uses only "running away"), but step 5 points
  the face's verdict at the instrument, and still figures would read
  "cycling". harmony's two meter rows wait on `?brain=js` until it is
  decided; in `after-stage-5.md` and step 5.
- **`syncMonitor` stays** (section 1 asked): on the default the
  instrument's sound reaches the speakers through the page's own Web Audio
  chain - filter, limiter and clamp - so it is the face's audio carrying the
  heard sound.
- **The filter's sweep on the screen rides the page's visual matrix.**
  filtertest's glide check moves `filter.cutoff` through the page's matrix
  (`visualMatrix.filter.cutoff` read nought on the default in section 1 only
  because no default suite routed the cutoff). It joins scale's three and
  lane's eight in following step 5's decision.

### What still needs `render_cpp`, and with what input

- **picturepresets `:241` to `:256`**: the old library's waveform presets in
  its two picture sections (twelve), each loaded with A3 held in Mono at full
  sustain for about ten seconds with the loop closed; the first section again
  with its picture routings removed, the photocell at the same cell; readings
  every 150 ms of the photocell's raw reading at its stored cell, each routed
  picture source, `photo.1` and the meter's verdict; the reticle's landing
  rule for a stored cell that reads dark; the meter reset at each start.
- **perform `:231` to `:265`**: a microphone's samples through the
  instrument, once it is confirmed the instrument puts an input through its
  effects at all (section 3); with input and livefx.
- **harmony `:195`, `:196`**: not a render, the meter's question above.

## 10. Step 3, batch 5 (13 Nov)

`render_cpp`, and the rows that waited for it: loop's stability runs and the
rest of loop on `?brain=js`, shape's survey, picturepresets' runs, input,
livefx and perform's microphone rows. Every row in those six appendix tables
has a "Batch 5" column. Nothing in `scope.html` or `core/include` changed;
`git diff core/include` is empty. Budget, the constellation, worklet, wasm,
brain and step 5's decisions are not this batch's.

### render_cpp

`core/tests/tools/render_cpp.cpp`: the instrument (`scope/instrument.h`, as
the plugin and the site play it) rendered offline. It **grew from**
`response_cpp`, whose run it still makes byte for byte (`--response`; the two
were run on responsetest's three performances and on `--decode` and gave the
same bytes, and `response_cpp.cpp` went, responsetest pointing at
`render_cpp --response`), and from `instrument_cpp`, whose script it speaks
and whose native readings both now print from one header,
`core/tests/tools/instrument_reads.h` (instrument_cpp's output on a script
using every reading was the same to the byte before and after). It is built
by the pieces' kit, so by parity's harness; how to use it is in
`core/tests/golden/README.md` and at the top of the file.

It takes a script of JSON lines, time moving only by `to`:

- a setup code with fields laid over it (`make`), and the hands a player has
  - `slider`, `setup`, `control`, `click`, `routings`, `fade` - at the sample
    reached;
- MIDI at its own sample (`midi` after `to`), so held notes, a hammer every
  90 ms, and a chord let go at a stated sample;
- the loop closed for as long as asked (30 s a seed here), with a meter reset
  (`reset meter`) and a layer's hold put in (`hold`) where a run wants them;
- an input, as a host's input bus or the site's microphone hands it over: a
  file of float32, mono or stereo, a sine, or instrument_cpp's saw
  (`input`); drawn whole with `click srcMic` or into the generator's input
  modes. **The instrument does put an input through its effects**, which
  batches 3 and 4 asked: drawing the input, its render runs it through the
  generator's `effect` - the plane and the time effects, phaser, chorus,
  delay and reverb - and what comes out is both drawn and heard (a click
  comes back 150 ms on with the delay at full mix, and not without it;
  pieces/render.py). It has no insert to switch: what the page's livefx rows
  held about its insert's life has no counterpart.
- readings at a stated interval of audio (`every`) or once (`read`): the
  heard pair (peaks, RMS, non-finite count), each stage's reads and hold,
  the meter's verdict and each layer's, the loop's routes per slot and the
  view's offsets, each layer's Scan table whole, the picture's sources raw
  and slewed with the photocell's reading, the grid's statistics, the
  generator's effects settings, which sources count as the loop's
  (`loopof`), and instrument_cpp's `grid`, `lgrid`, `hearing`, `scan`,
  `reads`, `tone`, `routed`, `meter` and `layers`; and files of float32
  (`record`) for the heard pair, the six ring lanes a sample and the grid at
  each reading that asks (`griddump`), per frame or decimated.

**Determinism, proved** (pieces/render.py): twelve seconds of the heaviest
script the batch has - a crossed split at Scan's top, the reverb full, the
picture's sources routed, a random oscillator on the twist, an input ridden
into the generator, every reading every tenth of a second and every record -
run twice: every reading, the heard pair, the lanes and the grid the same to
the bit (SHA-256 of each). The nulls: a note struck at 126 rather than 127,
and one input sample moved by a thousandth three seconds in, each a different
run by the same comparison. Reading moves nothing: read every 7 ms (never on
a step's edge) or never, the heard pair and lanes are the same to the bit,
because the instrument steps every 128 frames whatever block it is handed. A
mutation that stepped at every host block's top turned that red, and one
that seeded the generator from the processor's clock turned the twin-run
check red (it was green until the heavy script had a random source in it:
nothing had drawn on the generator's random numbers).

**Running time:** the heavy twelve seconds render in 1.5 to 1.8 s on this
container (about seven times real time with every reading); a plain loop
seed of 30 s in 1.2 to 2.1 s, the crossed one in 4. The compile is about 15 s,
once a run.

### What moved

| Suite | Web checks before | after | pieces checks (nulls) | `?brain=js` opens | Rows: to pieces / moved / rewritten / gone / left |
|---|---|---|---|---|---|
| loop | 61 | 5 | 67 (14) new, 91 (24) in all | 2 to 0 | 13 / 2 / 1 / 0 / 0 |
| shape | 13 | 10 | 6 (3) new, 56 (28) in all | 1 to 0 | 2 / 0 / 0 / 1 / 0 |
| picturepresets | 10 | 5 | 10 (5) | 1 to 0 | 5 / 0 / 0 / 1 / 0 |
| input | 11 | 5 | 13 (7) | 1 to 0 | 6 / 2 / 1 / 2 / 0 |
| livefx | 17 | 7 | 15 (8) | 1 to 0 | 7 / 4 / 1 / 5 / 0 |
| perform | 8 | 4 | 8 (4) new, 14 (7) in all | 1 to 0 | 4 / 0 / 0 / 1 / 0 |
| render_cpp itself | - | - | 8 (4) | - | - |
| **six suites** | **120** | **36** | **127 (45) new** | **7 to 0** | **37 / 8 / 3 / 10 / 0 (58 rows)** |

(Web counts are checks run, a loop's iterations each. "Moved" includes a
default page's own "no page errors". inputtest's six numbers rows needed no
render: generator_cpp already hands the core's Generator an input, and they
are pieces/input.py.)

The counters (`run.py --brain-counts`, the full run below): the six suites
step the page's brain on `?brain=js` for no frames now, where before they
were the largest share of it - loop's stability runs 22,584 frames
(section 8), picturepresets' runs 14,034 and perform's microphone 846
(section 9) and shape's survey 1,490 (section 7); input's and livefx's were
not counted apart. On the default the six step 1,476 frames, the face's own.
Over the whole run `?brain=js` pages stepped 21,468 frames and
`?brain=js&core=js` 570, from thirteen suites: wasm 9,307, budget 4,603,
constellation 3,058, photo 1,046, mod 819, harmony 769, live 736, scan 570,
brain 339, clock 303, worklet 273, score 155 and layer 60.

The full run after (97 suites, 38.9 minutes, 2,511 checks): everything
passes, honesty's reverb pass included, which failed alone on testing before
this batch (it reads nothing this batch changed). Batch 4's full run was
50.6 minutes; loop and picturepresets alone were about eight of the
difference. Parity passed, 1,791 checks (1,664 after batch 4; the 127 more are this
batch's piece checks), three-way, its pieces section running every module.

### Offline against the page's bounds

Every bound is the page's, unmoved. Offline, each seed is the same every run,
so none of these holds by luck of timing any more; what they read:

- **The fold's "saturated" exemption is no longer used.** On the page the
  loop's "really running" row passed on the crossed split and the full
  reverb only by its exemption, reading 0.032 to 0.043 against 0.05, and
  failed when a run missed saturation (after-stage-5.md). Offline every seed
  moves the fold by 0.30 to 0.50 and passes without it. The exemption is
  kept, as the bound is the owner's; the check says when it was used.
- **Scan's table moves with room.** "With Scan at its top, its wave was
  still moving" read 0.043 under three suites at once and 0.078 to 0.098
  alone on the page, against 0.02; offline 0.082 (full scale), 0.335 (struck)
  and 0.100 (crossed, B's 0.149). It never held by luck so much as by the
  page's load, but the margin was a factor of two at worst there.
- **The holds land exactly.** The stage's hold reaches 0.250 in every seed
  that runs away (52 to 260 tenths of 300), and 1.000 in the silence that
  never does; Scan's hold follows it to 0.250 (0.251 crossed, by its 0.005
  step).
- **What reaches the speakers was never the instrument's to hold.** The
  page's "never passes full scale" read its own monitor chain's clamp. The
  instrument has no limiter: its heard pair peaks at 0.94 to 1.09 in the
  plain seeds, 2.02 with the phaser, 2.74 crossed and 3.24 with the reverb
  at full. On the site the face's chain (limiter and clamp, `syncMonitor`)
  still holds it, and looptest holds that on the default page (fed twelve
  times full scale: 0.96 out of the clamp, 1.12 before it). In the plugin
  nothing does - after-stage-5.md.

### Checks that passed for the wrong reason, or could not fail

1. **My own harness, the ring's width.** pieces/livefx.py first read the
   recorded lanes as eight a sample; the ring has six (`kMaxLanes`). The
   mirror and the angle checks passed on that interleaved garbage; only the
   delay's timing, read off the same lanes, went wrong (a cycle of 0.375 s
   where the bursts were 0.5 s apart). render_cpp's own comment said eight
   too. Both fixed; the delay check is why it was seen.
2. **A still screen that was not still.** The first null for "Scan's table
   is moving" was Scan at its top with nothing routed and no Picture, on a
   sine: its table moved 0.11 a tenth, because Scan reading a screen its own
   wave draws is a loop by itself. The page's null for this was the screen
   held by Stop (scantest), which is step 5's. Scan at a depth of one in a
   hundred, all but still (0.0008), is the null now.
3. **An echo that comes and goes.** perform's "every live-effects preset
   puts the input through the effects" read the page's insert being there;
   read from the samples 1.2 s after a load, Echoes that come and go drew
   the input unchanged - its echo is an oscillator's at a tenth of a hertz,
   away five seconds in ten. Each preset is held ten and a half seconds now.
4. **Two checks the mutation pass found could not see the fault.** A meter
   whose saturation was raised to 0.95 never ran away and so never held the
   stage, which "running away holds the stage down, and nothing else holds
   it" allows: a check is added that a screen the hammer keeps full is
   called running away for nine tenths of what the meter says (260 of 260),
   with the plain run's 52 of 260 as its null. And boredom that never rose
   left picturepresets green, since "the picture's sources move" takes the
   most-moving source, as the page did, and boredom is routed only beside
   livelier ones; batch 3's boredom checks catch it. Making it every source
   would be a new claim the presets do not meet (roundness 0.032, change
   0.048, boredom 0.010 in the presets that route them), so it is left, and
   said here.

The rows the page's brain alone had, which went: input's open-only-while-
heard rule (the instrument hears its input always), and livefx's insert -
no node until an effect, the running worklet told a change, the per-frame
routing message, the lane rows refitted round it, the node let go of with
the source. The site's microphone reaching the instrument's effects at all,
and the face's words for each source, are held on the default page.

### Nulls and mutations seen red

Every piece check has its null beside it, seen red. Every moved or rewritten
web check has one too, seen red: a quiet chain and the sound before the clamp
(loop), the input ridden at a depth of nought and its code (input), the
microphone as it is and the two sources' words (livefx). The core was mutated
in scratch copies (`PIECES_INCLUDE`), 22 ways, each turning at least one
check red: `picture.h` eight (the hold's floor, running away never holding,
saturation at 0.95, strained at -12 dB, the layers never live, Direction read
as roundness, the photocell read across, never wandering; boredom never
rising, red on batch 3's loop rows only, above); `matrix.h` the loop's total;
`scan.h` two (a hold of one sent, the tables never handed over);
`generator.h` six (the reverb's size not set, the ride at 1.9, FM at three,
the clock never restarting, the seed from the processor's clock); `plane.h`
two (Y never mirrored, the delay a hundredth long); `instrument.h` two (a
drawn input skipping the effects, a step at every host block's top);
`hearing.h` one (a hearing source always the loop's). Three were first green
for my harness's sake, not the checks': the floor's mutant did not compile
(an unused name under `-Werror`), two wrote livefx's input files before the
scratch build's directory existed.

### What it finds

- **The instrument has no limiter, so the plugin hands a host whatever the
  loop makes** - 3.2 times full scale with the reverb in the loop at full,
  2.7 crossed. On the site the face's monitor chain limits and clamps it.
  And the instrument's meter is handed no limiting ("with no limiter to
  read, the output being the owner's"), so its "running away" comes only
  from a screen lit past a third; the meter's rule for a strained limiter
  (held by pieces/loop.py on picture_cpp's meter) never fires in the
  instrument. In `web/docs/after-stage-5.md`, and step 5's list: when the
  face's verdict reads the instrument's, the site's limiter reading no
  longer reaches it.
- **Scan alone moves its own table.** With nothing routed and no Picture, a
  sine at Scan's top moves its table by 0.11 a tenth: Scan reading a screen
  its own wave draws is a loop of its own. Not a defect - it is what Scan is
  - but it means Stop (step 5) is the only still screen Scan has, which is
  why scantest's held run waits on it.

### What is left on `?brain=js`

Besides budget, the constellation, worklet, wasm and brain (and braincounts'
own leg), and step 5's decisions (scan's held run for Stop, harmony's two
meter rows): clock's and score's panels, which draw the page's own brain
(batch 2); layer's learned split point (batch 2, a site defect); mod's and
photo's pages for their page rows outside batch 3; and the whole of
`livetest.py`, which no batch has taken (5 numbers, 35 page).

## 11. Step 3, batch 6 (14 Nov)

The last batch of step 3: livetest whole, the rest of modtest and phototest's
`?brain=js` leg, the voices' budget, and a look at what was still left
(layer's learned split point, clock's and score's panels). Every row in those
seven appendix tables has a "Batch 6" column. Nothing in `scope.html` or
`core/include` changed; `git diff core/include` is empty. New: the pieces
`live`, `budget` and the batch's rows in `mod` and `photo`; one tool,
`core/tests/tools/budget_cpp.cpp` (voices laid on the core's generator, each
read back, a second timed natively, a setup restored by the core's own
`restoreSetup`); no existing command changed.

| Suite | Web checks before | after | pieces checks (nulls) | `?brain=js` opens | Rows: to pieces / moved / rewritten / gone / left |
|---|---|---|---|---|---|
| live | 40 | 45 | 11 (5) new | 1 to 0 | 3 / 19 / 17 / 1 / 0 (and four of the rewritten also to pieces) |
| mod | 27 | 28 | 9 (3) new, 17 (7) in all | 1 to 0 | 1 / 17 / 8 / 1 / 0 (three of the rewritten also to pieces) |
| photo | 35 | 27 | 20 (8) new, 24 (10) in all | 1 to 0 | 10 / 16 / 2 / 0 / 0 |
| budget | 26 | 7 | 40 (16) | 1 to 0 | 21 / 2 / 2 / 0 / 0, one kept |
| layer | 22 | 22 | - | 1 to 1 | 0 / 0 / 0 / 0 / 1 |
| clock | 14 | 14 | - | 1 to 1 | 0 / 0 / 0 / 0 / 7 |
| score | 4 | 4 | - | 1 to 1 | 0 / 0 / 0 / 0 / 3 |
| **seven suites** | **168** | **147** | **80 (32) new** | **7 to 3** | **35 / 54 / 29 / 2 / 11** |

(Web counts are checks run, from a run of the six suites on 4a48f14 and
budget's own count. Its "before" ran on `?brain=js` and so on the page's
own brain, as the column says.)

### What moved, and what it reads on the site

- **live.** The Mic and Bands buttons keep the instrument (batch 1): it draws
  the input, splits it into the four bands itself and is told by `srcMic`,
  `srcBands` and `laneMix`, which the suite reads off the worklet's port. On
  the site the speakers are one monitor chain, built at boot and always
  connected, behind a level the page opens or shuts (`state.source.gain`);
  the page's own microphone built a chain only when one was wanted. So "no
  node connected to the destination" became "the level in front of the chain
  shut", with a monitored line input as its null, and the clamp's hook went in
  before the page. The browser's fake microphone clicks about twice a
  second and is silent between; the bands' signal is read on a click, and its
  null is the track disabled (the page hands a stream taken from the source
  straight back). The band split's arithmetic - which band owns each probe,
  20 dB two bands away, each crossover at -3.01 dB through both its band's
  stages, a broadband input in every band, and the heard pair the bands summed
  at the mixer's gains sample for sample - is pieces/live.py, through the
  instrument.
- **mod.** LFO 1's shape and Rate are set in its card's editor, which the
  instrument hears; the phase counted is the instrument's, which the page's
  lfos take from every chunk (written by hand, the page's rate moves nothing,
  now checked). Mic is pressed rather than `toMic()`. The G2 decode rows read
  the site's codec; the row comparing it with the page's fallback went. And a
  new check: every destination's control tells the instrument, by its own id.
  The octave sweep, the routing to nowhere and the rate on each source are
  pieces/mod.py, rendered (Mono and Poly; the mutation pass found Mono alone
  could not see the voices' pitch path).
- **photo.** The figure under each check is set by the Level, Interval, Shape
  and Persistence controls and the display's buttons. What the face draws into
  is its own grid (section 1's second grid), so the rows holding the face to
  its screen stay, and a fixture check now says the X-Y figure is the
  instrument's 2:3 and not its own transpose: with `genSet` put back the
  grid-against-canvas rows stay green on the instrument's diagonal and only
  this goes red. The grid's fade and ends, the compositing, the photocell's
  reading, smoothness and slew are pieces/photo.py on the core's Phosphor and
  PictureSources; the loop is the instrument rendered four seconds with the
  photocell on its own figure, routed past the ceiling.
- **budget.** Section below.

### The budget on the core

Its costs were fitted to the page's JavaScript milliseconds, so before moving
anything the page's governor (`makeGeneratorCore` on a `?brain=js` page) and
the core's were run side by side on every case the suite measures - the
sweep of one to eight notes a layer with everything on, chords over
five-second releases on one layer and on two, the worst case, the caps, the
4 kHz drive, the fade - and on all 277 setups of the old library and the bank,
under a chord of eight a layer and under a chord over releases. **They agree
exactly**: the same units to the last bit, the same copies, factor and held
notes let go, and the same voices cut, voice for voice (the sweep: 209.8
units at one note a layer, 4x and seven copies; two a layer 6 of 7 copies at
2x; three 3 of 3; four 1 of 2; five to eight one copy and 2, 4, 6 and 8 held
notes let go). So the core does not sound different, there was nothing to
record for the owner, and the checks moved to pieces/budget.py.

What does not carry over is the fit. Each feature's cost over its model cost,
as a share of the median (the suite's rule):

| | the page's JavaScript | the core as WebAssembly | the core, native |
|---|---|---|---|
| a model unit, ms of work a second | 0.89 | 0.46 to 0.50 | 0.40 to 0.55 |
| pink noise | 0.71 to 0.73 | 0.58 to 0.69 | 0.35 to 0.47 |
| the filter | 0.66 to 0.67 | 0.57 to 0.58 | 0.40 to 0.50 |
| drawbars, seven copies | 1.00 to 1.13 | **1.68 to 1.78** | 1.03 to 1.27 |

Noise and the filter are costed dearer than the core spends (the safe side:
a copy goes early); the drawbars with seven copies in WebAssembly, which the
site runs, cheaper (the side that glitches), harmless today only because 350
units is now about half the work it was in JavaScript. The governed worst case
runs natively in 150 to 170 ms a second, against the 500 ms bound. Nothing was
refitted: the relative-cost check holds the 1.6 side, natively, and names what
falls under 0.5 rather than failing; it cannot see WebAssembly's drawbars,
which `web/docs/budget-on-the-core.md` sets out for the owner. `budget_cpp`
is the only piece that reads a clock, so its relative cost is the suite's
known flake carried into the pieces.

### Checks that passed for the wrong reason, or could not fail

1. **budget's "and a drawn note only once every undrawn one has gone"** held
   of nothing since P4 drew the inner voices: no voice ever had both gains
   nought, and `all()` over the empty list is true. It is "an outline note only
   once every inner one has gone" now, on a chord where four outline notes go.
2. **budget's preset scan left every routing out.** Counted, the old library's
   Glass pad gives up a copy a hand under eight notes a hand, through its
   `env.note>gen.fm` (after-stage-5.md); the bank gives up nothing either way.
3. **livefx's twist oscillator (batch 5) ran at 0.005 Hz**, its setup's rate
   given as 0.5 where the field is in hundredths of a hertz; the swirl passed
   on a twist all but held. 50 now, and it passes swept (1.600 apart).
4. **heldTone's slider races its note-on on the site**: the instrument plays
   the note's 220 Hz under a face that says 440. modtest's sweep read 110 to
   438 Hz once on the default; the slider is moved again once the note lands.
   Other suites that read a pitch after heldTone have not been looked at.
5. **Checks the mutation pass found could not see a fault**: the octave sweep
   in Mono alone (the voices' pitch path in Poly, now also swept); the loop's
   range bound, with the reading at a half, could not see a reach of 0.9 (a
   per-frame check against half the photocell's value, routed past the
   ceiling); budget's oldest-of-a-rank and what counts as a held note let go
   (a check each).
6. **One of mine**: a piece formatted a numpy float into the reticle's control
   (`np.float64(...)`), which the core reads as no number - and that found a
   core corner: a reticle that is not a number makes the core's photocell
   climb past one at its slew rate, where the page's goes to NaN
   (after-stage-5.md).
7. **On the site, two of livetest's claims are half false.** A band split
   keeps the wish to monitor (the box ticked over a split, and Whole monitors
   again unasked), and the credit no longer says whether the input is
   monitored. Both in after-stage-5.md; the checks hold the half that is right
   and say so at the site.

### Nulls and mutations seen red

Every piece check has its null beside it, seen red. Every moved or rewritten
web check has one too: `toMic()` for the Mic press, the Bands press left out,
the Monitor box ticked without its event, a GainNode to the speakers, the
track silenced (live); half the depth, a slider message withheld, Mic left
unpressed, the slider at 4 Hz (mod); `genSet` put back (photo); `genSet` on
the default, the instrument's budget reading forged (budget). The core was
mutated in scratch copies (`PIECES_INCLUDE`), 41 ways, 40 red: `capture.h`'s
Q in decibels as 0.707 and `instrument.h` five ways for the split (an edge,
a stage skipped, the mixer ignored, a lane doubled, the heard sum ungained);
`lfo.h` stepped twice, `generator.h`'s pitch law in Mono and in Poly,
`matrix.h` taking an unknown source; `picture.h` seven ways (the fade, the
infinite and the off ends, the sum for the maximum, the read's cross, the
slew, u and v swapped) and `loop.h`'s reach; `generator.h` 23 ways for the
governor. Green: noise costed at nothing, which natively is nearer what the
core spends, so a check against the machine cannot call it wrong; parity's
governed runs hold the model's terms.

### What is left on `?brain=js`, and why

Step 3 is done. Left, each for a reason step 3 could not answer:

- **step 4**: the constellation (removed by the owner's decision; done 14 Nov,
  section 12).
- **step 5**: scan's held run (Stop), harmony's two meter rows (the meter's
  verdict), layer's learned split point (a site defect: only the face learns
  it), clock's LFO card, tempo row and Bar row and score's Stop, hidden page
  and playhead (they draw the page's own lfos, transport and score; the
  instrument posts its oscillators' phase and value but no rate, tempo or
  playhead, so the face has nothing of the instrument's to read until step 5
  gives it one); and brain's own legs and the counters' null.
- **step 5 or 6, the engines compared**: wasm and worklet whole, which hold
  the two engines together and go with the switch.

**The runs (14 Nov).** The full web suite, with `--brain-counts`: 97 suites in
41.3 minutes, 2,490 checks passed and one failed - honesty's reverb-on pass,
the known flaky one (*Bass under the pad*, 36 frames), which passed alone twice
(10.3 minutes each). Parity: 1,871 checks, every one passed, in 27 minutes,
the pieces with it. The page's own brain is now opened by 9 suites
(brain, clock, constellation, harmony, layer, scan, score, wasm, worklet), 29
pages in all. Of this batch's seven suites, 3 open it, where 7 did:
livetest, modtest, phototest and budgettest open only the default page
(744, 814, 1,061 frames of the page's brain before, none after), and
layertest, clocktest and scoretest open it once each, as they did.

## 12. Step 4: the constellation removed (14 Nov)

Taken out of the page by the owner's decision (`STAGE5-PLAN.md`, "Decided"):
Draw's way, Place, Hands and Reseed, `drawConstellation` and its helpers (370
lines of `scope.html`), the help sheet's paragraph and the four controls'
words. No core side and no stored field, so no decode pass; `drawgonetest.py`
(14 checks with their nulls, parallel) replaced `constellationtest.py`'s 42.

**The runs.** Parity: 1,871 checks, all passed. The full web suite with
`--brain-counts`: 97 suites in 38.8 minutes, 2,448 checks passed and two
failed under load - scan's turning fifth on the site's instrument and arp's
key held into a plain setup - each of which passed alone twice
(`web/docs/after-stage-5.md`, Tests). The plugin's shell test under
`xvfb-run -a`: 267 passed.

**What the counters say now.** `drawConstellation` is gone with the page's
code, so it is no longer a count. Of the page-brain steps that remain, one
now runs on **no suite at all**: `fireEvents.fire` (15 on `?brain=js` on 13
Nov), whose only caller was onset's stand-in destinations, moved to the
pieces in step 3 - the constellation was not its reason, but step 5 should
know it is unwatched by the web suite. Three run only on `?brain=js`, none of
them for the constellation: `layerPicturesStep` (2,954), `scanStep.table`
(5,998, and 465 on `?brain=js&core=js`) and `clockStep.clockLost` (1). The
constellation was the only reason for none of the counted steps: the page's
grid it drew into (`phosphorDeposit`, `phosphorFade`) is still worked on every
address. The page's own brain is now opened by 9 suites (brain, clock,
drawgone, harmony, layer, scan, score, wasm, worklet): drawgone opens it to
hold the prototype's address, `?brain=js&draw=constellation`, and goes with
the switch in step 5.

## 13. Step 5a (14 Nov)

Step 5 split in two: 5a gives the instrument what the owner decided it must do
before the page's brain is switched off; 5b switches it off. Nothing here
changes which brain a suite opens, and `?brain=js` is untouched.

| What | Built | Held by | Its nulls |
|---|---|---|---|
| The limiter | `scope/limiter.h`: Chromium 153's DynamicsCompressor and WaveShaper in floats, glibc 2.39's `logf`, `log10f`, `powf`; `Instrument::limit`, after the Output and Width; `latency()`; the meter handed `limiting()` | parity's new section, the page's chain in an OfflineAudioContext against the core: 0 apart on 576,000 samples a run, three runs; reductions to 4e-8; pieces/loop.py: every seed under 0.99 (0.922 to 0.961), a chord of six at -10.1 dB running away | release 0.11 s, a sample late, the pair before the limiter (parity); the limiter off on three seeds, 2.02 to 3.24 (loop); the chord with the limiter off (wandering) and a sine (-0.0001 dB) not running away |
| The site with it | the instrument's chain without the page's limiter, a backstop for its clamp (`BACKSTOP_CURVE`); `monitorLimiting` reads the instrument's | parity: the backstop moves 9 to 10 per cent of samples by one float step, 1.2e-7 | the page's limiter in series: -24 to -28 dB of error, -0.3 to +0.1 dB of level |
| Stop | `scopeRunning` (setRunning, the site only); `PictureRun::hold`: capture, draw and readout held; strikes, the score and the hearing stopped | pieces/stop.py: the table 0.00003 against 0.109, the grid's sum and Direction unmoved, the heard pair sounding, Run moving again, a strike laying nothing; scantest's held run on the default, 0.0001 against 0.0066 | never stopped; running grid and Direction moving; a strike running against none |
| The meter | `METER_EYE` (45 ms) and `METER_EYE_KEEP`, page and core: the verdict's rate reads each frame against the grid of the eye's time ago | pieces/harmony.py: at persistence 0 and 0.12 a just fifth, a unison and a sine's unison settled (0.0001 to 0.0072); harmonytest's two rows on the default (0.005 settled, 0.037 cycling) | an equal third and an equal fifth, turning, cycling at both persistences; the fifth's verdict is not the third's |
| The clock | `Instrument::clockServed` (12), posted after the readings, with the meter's verdict, change and eye's rate (3); the bridge's `clock`, `limiter`, `meter` | clocktest: rates, tempo, slider tempo, source and running equal to the page's; the bar at 84.4 BPM; the score on and its playhead moving | a tempo told the page alone; the rates swapped; the bar at the old 96 |

The mutation pass, in scratch copies (`PIECES_INCLUDE`), 13 ways, all red: the
limiter skipped, its clamp's ceiling at 1.2, its threshold at nought (green in
the pieces, red in parity's limiter section, six checks), the meter handed
nought, the limiting not clipped at nought; Stop's draw, strike, capture
(which needed a new check - Direction held - before it went red) and
message dropped; the eye's baseline a frame, the verdict on the raw change,
and the span not shared out.

Found, and written down in `web/docs/after-stage-5.md`: the transport's Start
and Stop reach the face's clock only (the bars 1.9 beats apart); what
"Speakers get: Shaped" adds after the instrument is backstopped, not limited;
the plugin's page is served neither the clock nor the meter; and the plugin
is 1.7 dB louder (the node's make-up gain) and held under full scale.

What 5b must know: the face's verdict can read the instrument's meter
(`state.source.meter`) and its panels the instrument's clock
(`state.source.clock`); the Bar row needs the transport's Start sent first;
the plugin needs both served beside `lfos.bin`.

**The runs (14 Nov).** Parity: 1,919 checks, none failed, in 24 minutes
(three-way, the pieces with it), after one `--write-golden` that rewrote
`picture.json.gz` alone: one run of eleven, thirty verdicts "wandering" now
"settled", every number the same; the other twelve files kept. The full web
suite: 97 suites in 39.1 minutes, 2,499 checks passed and two failed, both on
the known-flaky list - brain's "synced delay's repeats", which passed alone
twice, and honesty's reverb-on pass on *Bass under the pad*, which failed alone
twice more (once its reverb-off pass) and fails the same way, twice, on the
commit before 5a: its late motion reads 0.019 to 0.027 against Breathing's
0.02 floor in every run, either side of 5a, the edge `after-stage-5.md`
already records. The plugin's shell test under `xvfb-run -a`: 273 checks, none
failed. Suites changed for the limiter (each now holds the instrument before
its limiter where it holds the heard pair to the sample, and says so): output,
width, note, brain's band split, filter's and loop's speakers' chain, response
(render_cpp's `--response` with the limiter off, as response_cpp played it),
and in parity the Output, input and band-split runs; in the pieces live,
livefx and render read `prelimit`.

## 14. Step 5b, first half (14 Nov)

The face pointed at the instrument's readings, the switch left in place:
`?brain=js` and `?core=js` behave as before and no suite that opens them
changed. What the instrument posts for the face is one block,
`Instrument::faceServed` (24 values, published with the oscillators), read
by one function on both faces, `servedReadings` - after `brain_readings`' own
on the site, after the envelope in the plugin's `lfos.bin`, which carries
`clockServed` there too.

| Lean | Now reads | Held by | Its null (the page's own value where the two differ) |
|---|---|---|---|
| The Picture section's three bars and its held loop (`paintStage`, `pictureStage`) | the shared stage's reads and hold (`takeFace`) | facetest: the page's stage the instrument's to the bit, the bars its values | the page's stage left holding 0.123, 0.456 and a hold of 0.5: gone at the next reading (a page stepping its own slews from them: 0.576 and 0.515 under the mutant) |
| The photocell's card, reticle and value (`photo.value`) | the instrument's photocell | facetest: aimed at a held fifth, 0.11, the card and the reticle's `--lit` saying so | the page's photocell left at 0.987: gone (0.687, slewing, under the mutant) |
| The readout's "loop ...", the overlay's badge (`pictureMeter.verdict()`) | the instrument's meter (`loopVerdict`) | facetest: "loop settled" on a held fifth; overlaytest's badge | the page's own meter, unfed, says "listening" under it |
| The visual matrix on the screen's own destinations (`view.rotate` and the rest) | the offsets the instrument's matrix wrote (screen.h) | facetest: LFO 1 on the turn, the face's offset the instrument's frame by frame | a routing told to the page alone turns nothing; the page's sum would turn it by 0.64 |
| The LFO cards' rate reading | `clock.rates` | clocktest: 2.00 Hz at 1/4 and 120, 1.50 at 90 by the slider, 0.37 let go | `setTempo(60)` on the page alone: the page's lock would read 1.00 Hz |
| The tempo row | `clock.bpm`, `set`, `from` | clocktest: a MIDI clock's tempo from the instrument, internal half a second after | the page's transport put on a clock at 200 |
| The Bar row, its button and reading | `clock.running`, `beat`; the button a press to the instrument (`transportPlay`) | clocktest: stopped at 1.3, held, a code leaves it stopped, started from the one | the page's own transport still running under a row that says stopped |
| A tap | the slider's tempo and `tempoTap` sent to the instrument | clocktest: its tempo the taps' gaps', and the tap the one on the instrument's bar (7.6 beats, then 0.7) | the click not sent: 10.9 beats on |
| The score's playhead (`drawScorePlayhead`) | `clock.score.col` | clocktest: drawn at the instrument's column | a column given the page's score by hand |
| The plugin's page | `lfos.bin` with the clock and the face | the shell test: the tail equal to `clockServed` and `faceServed`, the rates in their places | read one place off, the rates are a rate and a tempo |

Each null was also seen red with the code mutated: the face back on the
page's picture (`instrumentFace` null, no `takeFace`, the page's meter) turned
eight of facetest's rows red; `syncClockPanel`, `drawScorePlayhead` and the
Bar row's listener on the page's clock turned six of clocktest's; the tap
not sent to the instrument, two; the lock row's null went red with
`instrumentClock` null.

What the counters say on the default, over facetest's held note: 192 frames on
the instrument, `pictureStep`, `photoStep` and `visualMatrix.view.rotate` at
nought, against eight `pictureStep` frames at boot.

Not repointed yet, for the second half: the boot frames, the page's grid
(`phosphorFade`, `phosphorDeposit`), `hearingStep`, `arpTick`, `morphStep` and
the morph's fader, the fade and its dot, `harmonySaid`, `sourceFigures`, and
lanes past the second.

**The runs (14 Nov).** RUNS-HERE

## Appendix: the counters, summed

Over the full run (13 Nov), by the page's address. `frames` is frames the
page's brain was asked to step; every other count is frames, or events, on
which that step did work. The default's 63 suites are those that open a
default page at all.

| Count | default | brain=js | brain=js&core=js | core=js | Default suites (the largest) |
|---|---|---|---|---|---|
| `arpTick.step` | 17 | 114 | 0 | 0 | braintest 10, arptest 7 |
| `clockStep.clockLost` | 0 | 2 | 0 | 0 | - |
| `clockStep.delayFollow` | 69 | 123 | 21 | 0 | fadetest 21, regress 21, rotatetest 21, braintest 4, timetest 2 |
| `clockStep.lfoSync` | 5 | 196 | 1 | 0 | fadetest 2, regress 2, rotatetest 1 |
| `clockStep.rebase` | 0 | 4 | 0 | 0 | - |
| `drawConstellation` | 0 | 2549 | 0 | 0 | - |
| `fadeDotStep.shown` | 3078 | 120 | 0 | 0 | fadetest 3033, braintest 45 |
| `fadeStep` | 4349 | 342 | 0 | 0 | fadetest 4139, braintest 132, hosttest 45, modrowtest 33 |
| `fireEvents.fire` | 0 | 15 | 0 | 0 | - |
| `frames` | 106612 | 79199 | 18849 | 95 | honestytest 32522, noisetest 7729, modrowtest 5668, fadetest 4771, braintest 4643, and 58 more |
| `frames.host` | 105322 | 0 | 0 | 0 | honestytest 32292, noisetest 7722, modrowtest 5661, fadetest 4747, braintest 4589, and 58 more |
| `frames.mic` | 0 | 3964 | 135 | 0 | - |
| `frames.tone` | 1290 | 75235 | 18714 | 95 | honestytest 230, windowtest 150, fittest 93, widthtest 67, stagetest 64, and 58 more |
| `hearingStep` | 1609 | 1916 | 0 | 0 | hearingtest 1589, fadetest 9, regress 9, layouttest 2 |
| `layerPicturesStep` | 0 | 5136 | 1947 | 0 | - |
| `lfoStep.main` | 2087 | 3964 | 135 | 0 | hosttest 2087 |
| `midiApplyGate` | 1857 | 79685 | 20123 | 98 | honestytest 320, windowtest 210, fittest 138, widthtest 94, stagetest 88, and 58 more |
| `morphStep.apply` | 25 | 0 | 0 | 0 | setupmorphtest 25 |
| `phosphorDeposit` | 106995 | 82710 | 20751 | 95 | honestytest 42164, noisetest 7642, modrowtest 5668, braintest 2795, washtest 2695, and 58 more |
| `phosphorFade` | 106622 | 80296 | 18849 | 95 | honestytest 32522, noisetest 7729, modrowtest 5668, fadetest 4762, braintest 4643, and 58 more |
| `photoStep` | 2093 | 33704 | 12168 | 0 | fittest 667, modrowtest 572, patchtest 406, enlargetest 175, layouttest 151, and 4 more |
| `pictureStep` | 106544 | 79055 | 18849 | 95 | honestytest 32522, noisetest 7729, modrowtest 5668, fadetest 4762, braintest 4643, and 58 more |
| `scanStep` | 1290 | 75091 | 18722 | 95 | honestytest 230, windowtest 150, fittest 93, widthtest 67, stagetest 64, and 58 more |
| `scanStep.table` | 0 | 8535 | 9143 | 0 | - |
| `scoreTick.step` | 10 | 84 | 0 | 0 | fadetest 5, regress 5 |
| `scoreTick.strike` | 10 | 45 | 0 | 0 | fadetest 5, regress 5 |
| `sourceTick.host` | 105082 | 0 | 0 | 0 | honestytest 32292, noisetest 7722, modrowtest 5661, fadetest 4747, braintest 4589, and 58 more |
| `sourceTick.mic` | 0 | 3964 | 135 | 0 | - |
| `sourceTick.tone` | 1290 | 74042 | 18343 | 95 | honestytest 230, windowtest 150, fittest 93, widthtest 67, stagetest 64, and 58 more |
| `standIn.tick` | 1340 | 0 | 0 | 0 | soundstarttest 611, braintest 353, enlargetest 291, notetest 85 |
| `stepRoutes.host` | 4327 | 0 | 0 | 0 | fadetest 4123, braintest 126, hosttest 45, modrowtest 33 |
| `syncMonitor` | 106719 | 71823 | 15750 | 92 | honestytest 32604, noisetest 7733, modrowtest 5670, fadetest 5404, braintest 4676, and 58 more |
| `updateEnvelope` | 106614 | 79199 | 18849 | 95 | honestytest 32522, noisetest 7729, modrowtest 5668, fadetest 4771, braintest 4643, and 58 more |
| `visualMatrix.filter.cutoff` | 0 | 7203 | 5177 | 0 | - |
| `visualMatrix.filter.res` | 0 | 14941 | 10354 | 0 | - |
| `visualMatrix.morph.pos` | 53 | 0 | 0 | 0 | setupmorphtest 53 |
| `visualMatrix.trig.position` | 498 | 4 | 0 | 0 | braintest 498 |
| `visualMatrix.view.lag` | 0 | 7476 | 5177 | 0 | - |
| `visualMatrix.view.rotate` | 7121 | 9112 | 5177 | 0 | modrowtest 4515, hearingtest 1430, fadetest 798, patchtest 263, wordstest 42, and 4 more |
| `visualMatrix.view.scale1` | 0 | 2 | 0 | 0 | - |
| `visualMatrix.view.zoom` | 2 | 8617 | 5177 | 0 | fadetest 1, regress 1 |

## Appendix: every listed check

The sort, suite by suite, as the four readers wrote it. A line number is of
the `check(` or `null(` call in `web/tests/<suite>.py` as it stood on 13 Nov.

### aliastest.py - wholly on ?brain=js - 15/15
Docstring: "On ?brain=js (5m): this suite reads the page's own brain - its generator's own samples and reswing - which parity holds the instrument to." It calls `waveAt`, `cycleTables`, `lfoStep` and `analyseHarmonics` directly (page :107).

| Check | Kind | Why | Batch 2 (13 Nov) |
|---|---|---|---|
| `%s at %d Hz folds back at %.0f dB or less` (:119, x9) | numbers | Alias floor of `waveAt` square/ramp/triangle; keep against the C++ oscillator. Needs a unit harness on `wave.h`, not a setup render (no "note at 4 kHz, shape only" readout of the bare oscillator). | gone to parity: pieces/alias.py, each floor on the core's waveAt (functions_cpp `waveRun`), the uncorrected control its null |
| `%s at %d Hz is at least 20 dB better than uncorrected` (:122, x9) | numbers | Compares with `waveAt(..., dt=0)`, the uncorrected control; a render has no such control, so it needs a C++ unit call with step nought. | gone to parity: pieces/alias.py, against the core's waveAt with step nought |
| `a drawn square at %d Hz folds back at -90 dB or less, fifty better than its richest table` (:145, x3) | numbers | `cycleTables` and `waveAt('drawn')`; control is the richest table at every pitch - again a unit-level call into `cycles.h`. | gone to parity: pieces/alias.py, the core's cycleTables and waveAt; the richest table at 4 kHz failing -90 its null |
| `a pulse of %d%% at %d Hz folds back at %.0f dB or less, 20 better than uncorrected` (:171, x9) | numbers | As :122 for the pulse. | gone to parity: pieces/alias.py, the core's pulse, corrected and not; the uncorrected failing every floor its null |
| `a square with no step given is still two values` (:192) | numbers | `waveAt` as an LFO shape; a `wave.h`/`lfo.h` unit check. | gone to parity: pieces/alias.py, the core's waveAt with no step; a step of a twentieth (181 values) its null |
| `and the ramp and triangle are bit for bit what they were` (:194) | numbers | Same, exact LFO shapes. | gone to parity: pieces/alias.py, bit for bit against the formulas, on the core |
| `a 2 Hz square LFO still completes two cycles a second` (:215) | numbers | Borderline: a hand-built LFO object stepped by page `lfoStep`; kept as numbers because the claim (rate) is renderable offline - an LFO on the level, cycles counted. | gone to parity: pieces/alias.py, the core's Lfo through lfoStep (functions_cpp `lfoRun`); 1 Hz its null |
| `and steps between two values, with no correction in it` (:217) | numbers | Same LFO, its values; offline, the level modulation's two plateaus. | gone to parity: pieces/alias.py, the same run's values |
| `the generator's own samples are band-limited, not just waveAt` (:235) | numbers | Real generator window at 4 kHz square, Mono note; the cleanest move to `render_cpp` (setup + note, numpy alias floor). | gone to parity: pieces/alias.py, the core's generator at 4 kHz (generator_cpp); the uncorrected square's -19.5 dB its null |
| `the correction touches four samples a cycle and no others` (:263) | numbers | Corrected vs uncorrected `waveAt` per sample; needs the dt=0 control, so unit-level, not a render. | gone to parity: pieces/alias.py, corrected against uncorrected waveAt on the core; 2 kHz's count its null |
| `it finds the fundamental where it was put` (:291) | page | `analyseHarmonics`, the face's harmonics pane, over `state.source`; the pane runs on the default too - becomes the pane switched on over the instrument at 431 Hz. | moved: the pane over the instrument's lanes (Mono clicked, the note by midiNoteOn, which reaches the instrument); +1 null, the note let go reading no fundamental; without the note the checks go red |
| `the odd harmonics are the textbook 1/k, to a decibel` (:293) | page | Same pane reading. | moved; found passing on nothing: with no pane its list was empty and `all()` of nothing true. Needs its three partials now |
| `and the even ones are not there` (:296) | page | Same pane reading. | moved; the same hollow pass, fixed the same way (four partials) |
| `so the distortion figure is the eight-partial one, 41.4%` (:301) | page | Same pane reading. | moved |
| `no page errors` (:305) | page | Page errors of the ?brain=js page. | moved |

### arptest.py - wholly on ?brain=js, its last two checks a loop over the default and ?brain=js - 23/23
Comment: "On ?brain=js (5m): this suite reads the page's own brain - its sources' functions, bound directly." It drives `arpTick` at synthetic times and reads `genSettings().voices`, `midi.notes`, `src.gate` wrapped by hand (page :103; the loop at :281 opens `""` and `&brain=js`).

| Check | Kind | Why | Batch 4 (13 Nov) |
|---|---|---|---|
| `the first key waits for the rest of the chord rather than striking alone` (:120) | numbers | The 25 ms gather (`keyboard.h:32` has it); offline, no note in the first 25 ms of a render. | to pieces (arp.py, keyboard_cpp at the page's synthetic times) |
| `up is C E G and round again, one note at a time` (:123) | numbers | Step order; offline from the core's `midiOut` hook or the pitch per step. | to pieces (arp.py, keyboard_cpp at the page's synthetic times) |
| `down is G E C` (:124) | numbers | As above. | to pieces (arp.py, keyboard_cpp at the page's synthetic times) |
| `up-down goes up and back without playing either end twice in a row` (:125) | numbers | As above. | to pieces (arp.py, keyboard_cpp at the page's synthetic times) |
| `as played is the order the keys went down` (:127) | numbers | As above. | to pieces (arp.py, keyboard_cpp at the page's synthetic times) |
| `two octaves climb the chord and the same an octave up` (:129) | numbers | As above. | to pieces (arp.py, keyboard_cpp at the page's synthetic times) |
| `random plays only what is held, and more than one of it` (:132) | numbers | The core's seeded walk (`keyboard.h:38`). | to pieces (arp.py, keyboard_cpp at the page's synthetic times) |
| `each step closes the gate and opens it again, so every note is struck` (:151) | numbers | Wraps `src.gate`; offline, an envelope restart per step in the rendered level. | to pieces |
| `and the hands are still the whole chord: three held` (:154) | page | `midi.notes.length`, the page's note stack; no audio consequence a render shows. Goes, or reads the instrument's held count if it publishes one. | to pieces (the core keyboard's notes; was page) |
| `120 BPM in quavers is a step every 250 ms: five in the first second, counting the first` (:181) | numbers | Step times from a render with timed MIDI. | to pieces; and an instrument_cpp render: note-ons every 250 ms on the audio clock, as bytes |
| `and a minute on the step count is the clock's, 241, not a drifted one` (:183) | numbers | Synthetic `arpTick` a minute on; offline, a 60 s render (cheap) counting steps. | to pieces |
| `and at 90 BPM a quaver is 333 ms, four steps in the first second` (:184) | numbers | As :181 at 90. | to pieces |
| `in the dyad each step pairs the lowest held note with the arpeggio's: unison, major third, fifth` (:199) | numbers | `genSettings().interval`; offline, the second lane's pitch ratio per step. | to pieces |
| `its notes go out as MIDI, each ended as the next begins` (:227) | numbers | Bytes to a stubbed port; the core has `hooks.midiOut` (`instrument.h:66`), so a render can return them. | to pieces |
| `letting go stops it, and the note that went out is ended` (:229) | numbers | Note-off bytes (and `arp.start`); via `midiOut`. | to pieces |
| `switched off with keys down, the generator has the whole chord again` (:231) | numbers | Voices after `arpSet` off; offline, the chord's pitches after the switch. | to pieces |
| `and a setup code carries the mode, the step and the octaves` (:233) | page | `snapshot()` of the panel; a face check, moves to the default as is. | moved; null the code before the menus moved |
| `when the layers change mid-arpeggio the generator is still given the step, not the whole chord` (:252) | numbers | Borderline: calls page `syncLayers()` directly; kept as numbers because the core's keyboard does the same reapplication and a render can switch layers mid-run. | to pieces |
| `switched off after a step, the held chord is struck: the gate closes and opens, and the generator has all of it` (:274) | numbers | Gate edges and voices on switching off (`keyboard.h:336`). | to pieces |
| `null: switched off inside the gather, before any step, the chord it never took is not struck again` (:276) | numbers | Its null, same harness. | to pieces |
| `on %s, a key held through an arpeggiated setup and into a plain one sounds at the plain one's level` (:293, x2) | engines compared | The ?brain=js leg of a both-brains loop; the default leg already holds it on the instrument. The leg goes. | the ?brain=js leg gone, the default kept |
| `null: on %s a key struck under a sustain of 0.3 and held into the same setup keeps its lower level` (:295, x2) | engines compared | As above. | the ?brain=js leg gone, the default kept |
| `no page errors` (:298) | page | Errors of both pages. | moved |

### braintest.py - 3 legs on ?brain=js / ?core=js beside the default - 4/76
Docstring: "?core=js turns the switch off - each read from the source the page is drawing"; the loop at :88 opens `?brain=js` and `?brain=core&core=js`, and the ?brain=js leg also records the website's skew for the default to be held to. The stage-5 counters section (:881) opens `?brain=js` on purpose as a null.

| Check | Kind | Why |
|---|---|---|
| `with %s the page is on its own brain and its own generator, its other sources offered` (:98, x2: `?brain=js`, `?brain=core&core=js`) | engines compared | The way back to the JavaScript brain and the `?core=js` fallback; step 5 removes both, so it goes. |
| `and the picture's left is left and right is right: the right a quarter-cycle on, as the website draws it` (:175) | engines compared | Default page, but its reference `site_skew` (:95) is read from the ?brain=js page; the absolute half (0.25 or 0.75) survives alone once that goes. |
| `and the comparison fails against the lanes the wrong way round` (:178) | engines compared | Its null, defined against `site_skew` from ?brain=js; has to be rewritten against 0.25. |
| `null: the same test asked of ?brain=js fails - the step is seen working there` (:892) | page | The stage-5 counters' null: `scanStep` counted on ?brain=js. Opens ?brain=js on purpose; goes at step 5, when the counters' "at nought" is the check and there is no page brain left to see working. |

72 sites read only default pages (or `?brain=core`, the instrument).

### budgettest.py - wholly on ?brain=js - 26/26
Comment: "On ?brain=js (5m): this suite reads the page's own brain - genSet called directly." Most of it builds its own `makeGeneratorCore` (the JavaScript engine) in the page and reads `core.budget`, `core.voices[].cut` and `performance.now()` (page :100).

| Check | Kind | Why | Batch 6 (14 Nov) |
|---|---|---|---|
| `sixteen held notes and sixteen releasing, everything on, run in under half of real time` (:119) | numbers | Milliseconds of the JavaScript engine; to keep it, a C++ benchmark of `generator.h` (serial), not a render. | to pieces: pieces/budget.py (budget_cpp), timed natively, best of three; null, the clock reads the work |
| `and the model says the budget holds` (:121) | numbers | `budget.units <= most`; the core's `budget()` (`generator.h:365`). | to pieces: pieces/budget.py (budget_cpp); null, the same bound at half the budget |
| `every case was measured as asked, the governor leaving it whole` (:163) | numbers | Budget state per case; core `Budget`. | to pieces: pieces/budget.py (budget_cpp); null, a voice past where the probe stopped is thinned |
| `the model has each feature's cost right relative to the others, from half to 1.6 times the median` (:171) | numbers | Measured JS cost over modelled cost; moved, it has to be re-measured on the C++ (whose relative costs differ) - see Surprises. | to pieces: pieces/budget.py (budget_cpp), rewritten: the core's native costs, not the page's milliseconds, are not the fit (pink and the filter under 0.5, wasm's drawbars x7 past 1.6: web/docs/budget-on-the-core.md); the 1.6 side held, under 0.5 named, nothing refitted; the morph-as-saw null kept |
| `one note a layer, everything on, gives up nothing` (:191) | numbers | Budget state. | to pieces: pieces/budget.py (budget_cpp); null, two a layer |
| `unison is only thinned once the four times has gone` (:193) | numbers | Budget state over a sweep. | to pieces: pieces/budget.py (budget_cpp); null |
| `a held note is only let go once unison is down to one on both layers` (:195) | numbers | Budget state. | to pieces: pieces/budget.py (budget_cpp); null |
| `and a drawn note only once every undrawn one has gone` (:197) | numbers | Per-voice `cut` and `gains`; needs the core's voice list, not audio. | to pieces: pieces/budget.py (budget_cpp), rewritten: passed on nothing since P4 (no voice undrawn, all() of an empty list); now an outline note only once every inner one has gone, on a chord where four go; null, swapped |
| `each stage is reached somewhere between one note a layer and eight` (:199) | numbers | The sweep's own non-vacuity. | to pieces: pieces/budget.py (budget_cpp) |
| `releases in flight go first: with some let go, no held note is` (:221) | numbers | Per-voice `held`/`cut`. | to pieces: pieces/budget.py (budget_cpp); null |
| `and a held note goes only once every release has` (:223) | numbers | Same. | to pieces: pieces/budget.py (budget_cpp) |
| `two voices keep the four times and alias as it does, under -44 dB` (:248) | numbers | Rendered driven voices, numpy off-grid; a render plus the budget's factor. | to pieces: pieces/budget.py (budget_cpp), the heard lane off-grid -46.3 dB |
| `twelve are held to twice, and alias as twice does - the governor's choice is the one that runs` (:250) | numbers | Same, twelve voices. | to pieces: pieces/budget.py (budget_cpp), -30.4 dB; null, twelve not under -44 |
| `with releases in flight, the chord has fewer copies than it asked for` (:279) | numbers | `budget.unison`. | to pieces: pieces/budget.py (budget_cpp); null, the releases had gone |
| `and keeps them as the releases die away under the same chord` (:281) | numbers | Same. | to pieces: pieces/budget.py (budget_cpp) |
| `striking the chord again gives them back` (:283) | numbers | Same. | to pieces: pieces/budget.py (budget_cpp) |
| `and so does moving the unison asked for` (:284) | numbers | Same. | to pieces: pieces/budget.py (budget_cpp) |
| `a chord over releases has some let go` (:310) | numbers | Voice `cut` count. | to pieces: pieces/budget.py (budget_cpp) |
| `and the sum never steps as they go: its largest move a sample stays under 0.01` (:313) | numbers | Largest sample step of the rendered sum; a render. | to pieces: pieces/budget.py (budget_cpp), 0.0032; null, a one-sample cut steps 0.835 |
| `it names each thing given up, per layer when there are two` (:323) | page | `budgetSaid`, the readout's words from a budget object; a face function, can be called on the default as is. | moved to the default page; +1 null |
| `and says nothing when nothing is` (:326) | page | Same. | moved |
| `playing a dear chord on the page, the readout says what the budget took` (:343) | page | `genSet` + notes, `el.readoutDetail`; becomes knobs and keys on the default, the readout reading the instrument's budget. | rewritten: a dear chord through the controls and keys the instrument hears (Poly clicked, the menus by their events), the readout read with the instrument's budget (state.source.budget); null, that reading forged to nothing given up. With genSet, on the default, red: the instrument played the base |
| `and a cheap one says nothing about it` (:345) | page | Same. | rewritten, as (343) |
| `the scan read the presets it names: more than a hundred, in more than six shapes` (:377) | numbers | Walks the corpus and bank through `genSettings()` into a JS core; offline, each preset's setup into the C++ core. | to pieces: pieces/budget.py (budget_cpp), 277 setups in 13 shapes through the core's restoreSetup |
| `no preset gives anything up under a chord of eight on each layer it plays` (:379) | numbers | Same scan, budget state. | to pieces: pieces/budget.py (budget_cpp); null, the dearest with seven copies and drive is thinned. +1: with routings counted, the old library's Glass pad gives up a copy a hand (after-stage-5.md) |
| `no page errors` (:382) | page | Page errors. | stays, on the default page |

### captest.py - wholly on ?brain=js - 11/11
Comment: "On ?brain=js (5m): this suite reads the page's own brain - what capture() asks the page's own sources for." The source is the page's own Mic (`kind === "mic"`), and the checks wrap `getLatestWindow` and call the face's `capture()` with `state.timebase`, `state.lagOn` set by hand (page :35).

| Check | Kind | Why | Batch 1 (13 Nov) |
|---|---|---|---|
| `a real graph source is loaded, and its buffer written all the way back` (:61) | page | Asserts `kind == "mic"` and capacity 32768; on the default the Mic is drawn by the instrument (`kind` host). | rewritten: the Mic button, the instrument drawing it (`kind` host, its two-second ring); `toMic()` would have left the instrument |
| `never asks for more than the buffer holds` (:93) | page | `capture()` is the face's and runs every frame on the default (`scope.html:20072`); moves to the default with Mic chosen. | moved; with the ring at two seconds it cannot fail for room, so a null holds the asks to 24000 |
| `no flatline at the left edge` (:95) | page | Same. | moved |
| `no NaN anywhere` (:97) | page | Same. | moved |
| `granted in full when there is room` (:105) | page | `state.lagActual` from `capture()`. | moved; cannot fail for room either (the squeeze below can) |
| `the window is never shortened` (:141) | page | Forced-capacity squeeze of `capture()`; borderline numbers (`capture.h` ports it), page because the code under test is the face's. | moved; the squeeze puts back the instrument's own `capacity` getter after |
| `search headroom gives way first, keeping the lag` (:144) | page | Same. | moved |
| `the lag goes next, rather than starving the trigger` (:147) | page | Same. | moved |
| `a window longer than the buffer is reported, not hidden` (:150) | page | `state.starved`. | moved |
| `still no NaN under the squeeze` (:153) | page | Same. | moved |
| `no page errors` (:155) | page | Page errors. | moved |

### clocktest.py - wholly on ?brain=js - 36/36
Comment: "On ?brain=js (5m): this suite reads the page's own brain - its sources' functions, bound directly." Reads `lfos[]`, `transport`, `score`, calls `clockTap`, `clockStep`, `midiBytes`, `midiRealtime`, `transportBeat`, `scoreTick` at synthetic times, and lights `phosphor.grid` by hand (page :47). The clock is ported whole (`core/include/scope/clock.h`).

Batch 2 (13 Nov): 36 checks to 14 here (a `?brain=js` page for the face's tempo readings, which are the page's own transport and lfos, and a default page for setup codes), and 54 in `core/tests/pieces/clock.py` (29 checks, 25 nulls) on clock_cpp, score_cpp and keyboard_cpp. 25 rows gone to parity, 2 split (numbers to parity, the face left), 4 moved to the default (one rewritten), 5 left on `?brain=js` (one rewritten).

| Check | Kind | Why | Batch 2 (13 Nov) | Batch 6 (14 Nov) |
|---|---|---|---|---|
| `at 120, 1/4 is 2 Hz, a bar 0.5, a quaver triplet 6 and four bars 0.125` (:73) | numbers | `lfos[0].rate` under each lock; a `clock.h`/`lfo.h` unit check or a render with the LFO on the level. | gone to parity: pieces/clock.py, the lock's rate written by the core's clock frame, with a plain quaver as null |  |
| `the reading says so, and the Rate slider stands aside while it is locked` (:75) | page | The LFO card's reading and a disabled slider; moves to the default as is. | left on ?brain=js: the reading and the slider are drawn from the page's own `lfos` (lfoRateReading); on the default that is the page's brain, a step-5 lean | left on ?brain=js, for step 5: the reading is lfoRateReading of the page's own lfos, whose rate the page's clock works out; the instrument posts its oscillators' phase and value, never their rate, so the face has nothing of the instrument's to read until it does |
| `it follows the tempo: 1/4 at 90 is 1.5 Hz` (:77) | numbers | Rate after `setTempo(90)`. | gone to parity: pieces/clock.py, 1/4 at 90, with 1/4 at 120 as null |  |
| `and let go, it is back at the slider's 0.37 Hz` (:78) | numbers | Rate after unlocking (plus the slider enabled). | rewritten, left on ?brain=js: the slider given back and reading 0.37 Hz (face, the page's `lfos`); the rate's half is the core's menu path (restore.h lfoSync), which parity's menus section holds | left on ?brain=js, for step 5: as (75) |
| `and the running oscillator goes round at it: 1/8 at 120, four times a second` (:100) | numbers | Crossings of `lfos[0].value` over two real seconds; offline, an LFO on the level rendered two seconds - and no longer timing-sensitive. | gone to parity: pieces/clock.py, crossings over two seconds of the core's generator stepping the locked oscillator (a new clock_cpp `play`), with the lock at 60 as null; no timers |  |
| `taps half a second apart are 120, and restart the locked oscillator on each` (:119) | numbers | `clockTap` at synthetic times; a tap is not MIDI, so a `clock.h` unit call rather than a setup+MIDI render. | gone to parity: pieces/clock.py, the core's tapTempo at made-up times, with the unrestarted phase before as null |  |
| `and one tap on its own is no tempo: it leaves the tempo where it was` (:121) | numbers | Same harness. | gone to parity: pieces/clock.py, the tempo started at 100, not 120, so one tap cannot pass by the tempo already being the next taps' 120 |  |
| `the tempo is the mean of the last four taps' gaps: 500, 500 and 400 is 129` (:123) | numbers | Same. | gone to parity: pieces/clock.py, with the last gap alone (150) as null |  |
| `after a pause of two seconds it starts again: 400 apart is 150, not a blend with before` (:125) | numbers | Same (plus `el.tempo.value`, the face). | gone to parity: pieces/clock.py, with a pause under two seconds (blended) as null; the slider's `150` gone - syncClockPanel reading the page's own transport, which a direct clockTap set |  |
| `25 ticks at 120, jittered, read as 120 - the mean of the gaps, not the last one` (:168) | numbers | MIDI clock bytes at given times; a render with timed `0xF8`. | gone to parity: pieces/clock.py, ticks at the same jittered times, with the last gap's tempo as null |  |
| `while it runs the locked oscillator follows it and the slider stands aside` (:170) | page | Borderline: rate is numbers, but what this adds over :168 is the tempo slider disabled and two readings' text. | split: the rate to parity (pieces/clock.py); the slider standing aside and the row's readings left on ?brain=js - the page's own `transport` (syncClockPanel), a step-5 lean | left on ?brain=js, for step 5: the tempo row is syncClockPanel's view of the page's own transport; the instrument posts no tempo |
| `half a second after the last tick the tempo is the slider's again` (:174) | numbers | Borderline: tempo handed back (brain), with the panel's text alongside. | split: the tempo handed back to parity (pieces/clock.py); the row's readings left on ?brain=js, as (170) | left on ?brain=js, for step 5: as (170) |
| `Start restarts the locked oscillators, and Continue does not` (:176) | numbers | LFO phase/epoch on `0xFA`/`0xFB`; offline, the LFO's phase in the level. | gone to parity: pieces/clock.py, with a free oscillator left where it was by Start as null |  |
| `a clock byte in the middle of a note-on is a tick, and the note lands with its own velocity` (:180) | numbers | The MIDI parser; a render fed those bytes. | gone to parity: pieces/clock.py, the core's Keyboard::bytes through keyboard_cpp; nulls: velocity 50, and no tick without the byte. Found: on the site a port's bytes reach the instrument cut at every status byte (scope.html's midiBytes `piece`), and the keyboard drops half a message between calls, so these bytes from a real port lose the note there (instrument_cpp: 0.34 whole, 0 in pieces). Not fixed: the page's or the core's to change |  |
| `started, the bar moves at the tempo from nought: a second at 120 is two beats, and 1.5 s is bar 1, beat 4` (:267) | numbers | `transportBeat`/`transportSaid` at synthetic times; `clock.h` unit (`said` is there "because a test reads it"). | gone to parity: pieces/clock.py, beat and said at the run's times, 1.5 s read as two beats as null |  |
| `a tempo change goes on from where the bar is: two beats at the change, three a second later at 60` (:269) | numbers | Same. | gone to parity: pieces/clock.py, with no tempo change (four) as null |  |
| `stopped, it stands where it stopped, and says so` (:271) | numbers | Same. | gone to parity: pieces/clock.py, with no Stop (ten) as null |  |
| `Start is the one again, and the locked oscillators start with it` (:273) | numbers | Same, with LFO restart. | gone to parity: pieces/clock.py, with the bar at 3.5 and phase three before as null |  |
| `the score switched on mid-bar joins the bar where it is, not at its own column nought` (:275) | numbers | `score.col`; lights `phosphor.grid` by hand - in the core the score reads the core's grid, so the moved check needs a figure that lights a row, or a score unit fed a grid. | gone to parity: pieces/clock.py, score_cpp, the core's score on the Brain's clock; column nought as null |  |
| `and Start brings it back to column nought on the downbeat` (:277) | numbers | Same. | gone to parity: pieces/clock.py, score_cpp |  |
| `stopped, the score strikes nothing and lets go of its notes` (:278) | numbers | Wraps `src.strike`; in the core, strikes counted from the voices. | gone to parity: pieces/clock.py, score_cpp, strikes logged; the running frames striking as null |  |
| `a MIDI Start waits for the device's first tick: nothing before it, column nought on it` (:280) | numbers | `midiRealtime` at times; render with timed bytes. | gone to parity: pieces/clock.py, clock_cpp for the bar and score_cpp for the strikes; a Start that did not wait as null |  |
| `under a clock the bar is counted in ticks: 48 jittered ticks on, exactly two beats` (:286) | numbers | Same. | gone to parity: pieces/clock.py, with the bar counted in time from the first tick (2.008) as null |  |
| `and between ticks it never guesses past the next one` (:288) | numbers | Same. | gone to parity: pieces/clock.py, with the bar let go by the frame past the tick as null |  |
| `MIDI Stop stands and Continue goes on from there at the next tick, restarting nothing` (:291) | numbers | Same. | gone to parity: pieces/clock.py, with a Start in Continue's place (nought) as null |  |
| `a clock that stops lets the bar go on to where it would have been, not half a second behind` (:294) | numbers | Same. | gone to parity: pieces/clock.py, with the bar before the frame lets go as null |  |
| `and a Start that no clock follows starts anyway, rather than waiting for ever` (:296) | numbers | Same. | gone to parity: pieces/clock.py, with the bar held at nought until the frame as null |  |
| `a tap is the one while the bar runs` (:298) | numbers | Tap at times; `clock.h` unit. | gone to parity: pieces/clock.py, with no taps (1.2) as null |  |
| `stopped, taps set the tempo and start nothing` (:299) | numbers | Same. | gone to parity: pieces/clock.py, with the tempo before the taps as null |  |
| `the Bar row's button stops the bar, and the reading says where it stood` (:320) | page | `#transportPlay` click and `#transportAt` text; a click on the default. | left on ?brain=js: `#transportPlay` and `#transportAt` are syncClockPanel's view of the page's own transport; a step-5 lean. The panel's evaluate now sets 120 itself, which the removed bar section had left | left on ?brain=js, for step 5: the Bar row is the page's own transport |
| `loading a setup code leaves the bar stopped: the transport is playing, not the patch` (:324) | page | `restore(snapshot())` called directly; becomes a code pasted on the default. | left on ?brain=js: reads the page's `transport.running` after restore(), as (320) | left on ?brain=js, for step 5: as (320) |
| `and started again, it runs from the one: a little over a second at 120 is bar 1, beat 3` (:326) | page | Button and reading. | left on ?brain=js, as (320) | left on ?brain=js, for step 5: as (320) |
| `a code carries the tempo, each lock, and the slider's rate rather than the locked one` (:344) | page | `snapshot()` fields; face. | moved: the tempo slider, LFO 2's Rate and Sync moved by real input events on the default, snapshot() read |  |
| `a code from before the clock is 120 and free` (:346) | page | `restore({})` then page `lfos`/`transport`. | moved: restore({}) then snapshot() on the default (the face's setup); bpm 120 and l1y empty |  |
| `and restored, the lock runs at the code's tempo: 1/2 at 96 is 0.8 Hz, with 0.9 kept for later` (:348) | page | Borderline: `restore()` direct then rate read; the core's restore is parity's, so the page half goes to the default. | rewritten, moved: the code comes back whole through snapshot() on the default, with the old code as a null; the lock's 0.8 Hz to parity (pieces/clock.py, with 1 Hz at 120 as null) |  |
| `no page errors` (:351) | page | Page errors. | moved: no page errors on each page, the ?brain=js one and the default one | the ?brain=js page's no page errors stays with it |

### constellationtest.py - wholly on ?brain=js but for one default leg - 39/42 (27 `check` + 12 `null` of 30 + 12)
Docstring: "Page-only: drawn on the main thread from the voice lists, on the page's own brain, whose Scan reads the screen the page draws." Its `opened()` defaults to `?brain=js` (:61); only :189 opens `""`.

| Check | Kind | Why |
|---|---|---|
| `with the switch at One figure the grid is the one a page without the constellation draws, to the bit` (:175) | page | Page `phosphor.grid` replayed with the feature's entry points taken out; only the page's brain has the constellation. |
| `and so is Scan's table read from it, and what a generator makes of that table: its picture pair and its heard pair...` (:177) | page | Page Scan table and a page generator fed it. |
| `null: the switch on draws a different grid` (:182) | page | Same replay. |
| `null: and so a different table and a different sound` (:184) | page | Same. |
| `no page errors on the page's brain` (:186) | page | Errors. |
| `choosing it with the mouse is no change to the setup's code, no step in undo and nothing in storage` (:224) | page | Face behaviour (code, undo, storage) of a feature live only on ?brain=js; could run on the default today, where the menu is offered. |
| `null: a control that is in the setup, moved by a key the same way, changes the code and makes a step` (:229) | page | Its null. |
| `its menus have no ids, which parity would hold to the core's panel, and the info line still has their words` (:233) | page | Markup; trivially the default. |
| `null: a menu with no id and no data-draw has no words` (:235) | page | Its null. |
| `the address can ask for it, and the page opens on One figure otherwise` (:243) | page | `?draw=constellation` on ?brain=js. |
| `by pitch, each of C3, E4, G4 and D5 is drawn within a cell of its place on the clock face and its octave's ring` (:268) | page | Constellation geometry off the page grid; no core counterpart. |
| `null: the one figure, the same notes, is found at none of those places in that way` (:270) | page | Its null. |
| `on the clock each figure's radius on the grid is its level's: within 15% of 0.58 x sustain x velocity` (:295) | page | Same. |
| `and the note struck twice as hard draws twice as large` (:298) | page | Same. |
| `null: not the same size whatever the velocity` (:299) | page | Same. |
| `and the hand's Level twice as high draws both twice as large` (:301) | page | Same. |
| `null: a Level ignored would leave them as they were` (:303) | page | Same. |
| `a sine's figure is a ring: every lit cell nearly one distance from its centre` (:324) | page | Same. |
| `a triangle's is a diamond: one distance by abs x + abs y` (:325) | page | Same. |
| `null: the ring is not a diamond, nor the diamond a ring` (:326) | page | Same. |
| `a slow attack grows the figure, a release shrinks it, and it goes when the release is over` (:348) | page | Same, in time. |
| `null: not one size from the start: 30 ms into the attack it is under two thirds of the attack's top` (:352) | page | Same. |
| `no page errors placing and sizing` (:354) | page | Errors. |
| `no page errors on %s` (:389, x2) | page | Errors. |
| `the circle Scan reads is the one the constellation puts it at: its path within 0.02 of the figures' own geometry` (:410) | page | Page Scan path over the constellation. |
| `on the clock, Scan's circle crosses every note's figure` (:412) | page | Same. |
| `and taking any one of them out changes the table: by over 0.02 on average across it` (:413) | page | Same. |
| `by pitch, C, E and G in the middle register sit clear of it` (:415) | page | Same. |
| `and Scan reads far less of them: under a fifth of the clock's light in all, and from any one figure under half...` (:416) | page | Same. |
| `null: the clock's crossing judged by the pitch layout's rule fails: not every place crosses` (:426) | page | Same. |
| `and the table Scan sent the generator is its reading of the constellation, place by place different` (:427) | page | Same. |
| `the grid holds a figure at the place of at least ten of the run's thirteen notes` (:456) | page | Trail on the page grid. |
| `null: the one figure, the same run, leaves light at hardly any of those places` (:458) | page | Same. |
| `at %dx%d Play does not scroll with the place, both hands and the seed showing on two hands, keys and Photocell` (:479, x5) | page | Fit of its menus, shown only while live (`constellationLive()`), so only on ?brain=js today. |
| `null: a section 400 px taller scrolls it (%dx%d)` (:481, x5) | page | Its null. |
| `no page errors (%dx%d)` (:482, x5) | page | Errors. |
| `the frame drew the figures it was timed on: six, and sixteen on two layers` (:521) | page | Cost of the page's frame. |
| `and sixteen figures cost a frame under 8 ms, far above what they cost here` (:523) | page | Same. |
| `no page errors timing` (:525) | page | Errors. |

All of it waits on step 4 (port it to the core, or keep it look-only on the page); none has a counterpart in the core today. 3 sites (:199, :203, :205) read the default page.

### contracttest.py - wholly on ?brain=js - 7/7
Comment: "On ?brain=js (5m): this suite reads the page's own brain - its lanes' contract." The page's own Mic split into bands (`state.source.lanes`, `laneMixer`), and a made-up source through `capture()` (page :76).

| Check | Kind | Why | Batch 1 (13 Nov) |
|---|---|---|---|
| `a band split's lanes keep it too` (:91) | page | `source.lanes` of the page's own Mic band split; on the default the instrument splits the bands (braintest :447), so this goes with the page's source in step 6. | rewritten: Mic and Bands pressed, the instrument's band split (`makeHostBandLanes`); null: the input whole has no lanes. `hides` is true of those lanes by construction |
| `and return what was asked for` (:93) | page | Same. | moved |
| `the mixer takes a lane with no gain node` (:180) | page | Page `laneMixer` over hand-made lanes; goes with it. | moved |
| `and mute and solo still mean what they mean` (:182) | page | Same. | moved |
| `capture draws from a lane with no analyser behind it` (:185) | page | Swaps `state.source` for a made-up one and calls the face's `capture()`; does not need ?brain=js at all and can stay as is on the default. | moved |
| `and what it drew is the signal the lane made` (:187) | page | Same. | moved |
| `no page errors` (:192) | page | Errors. | moved |

### drawbartest.py - wholly on ?brain=js - 33/33
Comment: "On ?brain=js (5m): this suite reads the page's own brain - midiControl and genSet called directly." Most numbers come from a `makeGeneratorCore` built in the page (`CORE`, :44), i.e. the JavaScript engine; the rest from `state.source` and the face (page :107).

| Check | Kind | Why | Batch 2 (13 Nov) |
|---|---|---|---|
| `the Shape menu offers the saw and the drawbars` (:132) | page | Menu options; face, trivially the default. | moved |
| `choosing Saw plays one: the second harmonic is half the first, -6.0 dB, and the third -9.5` (:134) | numbers | Spectrum of the generator's window after the menu; render a held note on Saw. | gone to parity: pieces/drawbar.py, the core's saw at 440 (generator_cpp), not the menu; the square read as a saw its null. The menu stays (:132) |
| `which the square it replaced on the menu has none of` (:137) | numbers | Same, square. | gone to parity: pieces/drawbar.py, the core's square |
| `each bar alone is its partial: 110, 330, 220, 440, 660, 880, 1100, 1320, 1760 Hz` (:146) | numbers | JS core rendered per bar; render a setup per registration. | gone to parity: pieces/drawbar.py, generator_cpp per bar; the partials in a shifted order its null |
| `and nothing else, 100 dB under` (:149) | numbers | Same. | gone to parity: pieces/drawbar.py, the same; two bars out its null |
| `16' is a sine an octave down, not a rectified one an octave up: nothing at 220 Hz` (:154) | numbers | Same. | gone to parity: pieces/drawbar.py, the same; a rectified 110 Hz sine its null |
| `at 4 kHz the 1' (32 kHz) and 1 1/3' (24 kHz) are silent rather than folded` (:164) | numbers | Same at 4 kHz. | gone to parity: pieces/drawbar.py, the same at 4 kHz; the 1' at 2 kHz its null |
| `while the 2', at 16 kHz, is all there` (:166) | numbers | Same. | gone to parity: pieces/drawbar.py, the same |
| `every bar out at 4 kHz puts nothing between the partials, 100 dB down` (:175) | numbers | Same. | gone to parity: pieces/drawbar.py, the same; read on a 4 kHz grid its null |
| `sliding up past Nyquist, the top bar fades rather than stepping out` (:197) | numbers | Block peaks while `freq` is set per 64-sample block; offline needs a glide or per-block frequency, which a setup+MIDI render gives as a pitch bend or glide. | gone to parity: pieces/drawbar.py, generator_cpp with the frequency set every 128 samples (the page's 64); a bar that steps out at Nyquist its null |
| `three decibels a step: 8' at 7 is -3, at 4 is -12, at 1 is -21` (:206) | numbers | RMS per level; render. | gone to parity: pieces/drawbar.py, generator_cpp; six decibels a step its null |
| `and at nought it is silent` (:208) | numbers | Same. | gone to parity: pieces/drawbar.py, the same; level one its null |
| `one bar at eight is a full-scale sine at the amplitude` (:214) | numbers | Peaks; render. | gone to parity: pieces/drawbar.py, generator_cpp |
| `and every bar out stays inside it, rather than being drawn as the clamp` (:216) | numbers | Same. | gone to parity: pieces/drawbar.py, the same; the nine summed unshared its null |
| `three bars at eight are a third each: the 8' is 9.5 dB under what it is alone` (:221) | numbers | Same. | gone to parity: pieces/drawbar.py, the same; a half its null |
| `a controller on the 4' bar at full draws it out to eight: level with the 8'` (:253) | numbers | `midi.key -> gen.bar3` routing, window read; render with that `mod` code and a held key. | gone to parity: pieces/drawbar.py, instrument_cpp, a key at full on gen.bar3; restated as level with the 4' at eight in the registration, since the instrument's base sound reads 220 and 440 Hz 2.8 dB apart; half depth its null |
| `and pushed back in, the 4' is gone` (:255) | numbers | Same at depth nought. | gone to parity: pieces/drawbar.py, instrument_cpp at depth nought |
| `the bar's own setting is not written by the controller` (:256) | page | `state.source.settings.bars`, the page source's settings; on the default the panel's bars or the instrument's state. | rewritten: the sliders and the code read while a key holds the routing at full (it was the page source's settings, the mirror on the default); +1 null, the routing present in the code |
| `each bar is a destination named by its footage, and stops at nought and eight` (:258) | page | `MOD_DESTS` label and `reach()`; the face's list, trivially the default. | moved |
| `editing B, the section says so and writes B's bars, leaving A's` (:280) | page | Section title and `genSettings(0/1)`; braintest :603 already holds this on the default. | moved: Poly clicked (setMidiMode is never heard); reads the face's mirror |
| `back on A the sliders are A's again, and the code carries both` (:284) | page | Panel and `snapshot()`; face. | moved |
| `and B sounds its own: B's picture is its 16' at 110 Hz while A's is its 8' at 220, each alone` (:309) | numbers | JS core with two layers' bars; render a layered setup and read each hand's lanes. | gone to parity: pieces/drawbar.py, generator_cpp's two layers; B with no bars of its own its null |
| `a code's registration reaches the sliders and the generator, and B takes A's when it has none` (:337) | page | Borderline: `restore()` called directly, then `genSettings`; the decode is the core's restore (parity's), the slider half the face's. | moved: the face's restore and mirror; the core's restore is parity's |
| `and B its own when it has one` (:339) | page | Same. | moved, as (:337) |
| `a code from before the drawbars loads with the default, not the last one` (:341) | page | Same. | moved, as (:337) |
| `and one that is not nine digits is not read as some other registration` (:343) | page | Same. | moved, as (:337) |
| `a new test tone is built with the sliders' registration, not the core's default, both its layers` (:363) | page | `state.source = null; toTone()` rebuilds the page's own generator; only the page's brain has this, so it goes. | gone: toTone(), a path only the page's brain has |
| `with another shape the registration row is not on Play, and the bars say why they are greyed` (:386) | page | Face; trivially the default. | moved |
| `Use drawbars chooses them, and the row under the menu shows the registration` (:389) | page | Face (with `genSettings().shape`). | moved |
| `pressing it goes to the bars, on the Ink tab` (:392) | page | Face. | moved |
| `hammond finds the drawbars, and a control first rather than a sentence` (:405) | page | Search; trivially the default. | moved |
| `and sawtooth the shape menu` (:408) | page | Search. | moved |
| `no page errors` (:410) | page | Errors. | moved |

### enlargetest.py - 1 leg on ?brain=js beside the default - 21/41 (15 `check` + 6 `null` of 29 + 12)
Docstring: "On the page's own brain (?brain=js), where the phosphor grid the page draws is the one Scan reads ... (The site's instrument and the plugin draw their own grids in the core from the lanes, which nothing here reaches.)" The leg opens at :256 and runs to `p.close()` at :438 - the Scan comparison, and also the Trail, the light kept across Enlarge, and Which hands.

| Check | Kind | Why | Batch 1 (13 Nov) |
|---|---|---|---|
| `with the scope held and the screen cleared, the frame lights the grid and Scan has a table` (:277) | page | Page `phosphor.grid` and `scan.tables`; on the default Scan's page step does not run (braintest :890), so the table half has nothing to read there. | gone: the page's grid and Scan table; on the default the grid is the face's copy and Scan the instrument's. Replaced by: Enlarge, Picture only and the Trail send the instrument nothing (null: a knob sends) |
| `Picture only on and off: the phosphor grid is the same to the bit` (:279) | page | Page grid; still fed on the default (braintest :887), so this half moves as is. | gone, as :277 |
| `and so is the table Scan plays, to the drift of a settled path` (:281) | page | Page Scan table; on the default the claim becomes "the instrument hears the same" - trivially true, since Picture only is in no setup. | gone, as :277 |
| `null: one step of zoom moves the grid and the table, so the comparison can see a change` (:285) | page | Its null. | gone, as :277 |
| `at %s the grid fades by the Persistence, 0.96 a frame` (:346, x3) | page | Page grid and canvas fade; nothing brain-specific, moves to the default. | moved: the grid is the face's reference for the Persistence, no longer what Scan reads |
| `null: the grid's fade is not what Half does to the canvas, 0.9216` (:347) | page | Same. | moved |
| `As heard, the canvas fades as the grid does` (:348) | page | Same. | moved |
| `Half fades it by the square, 0.9216 a frame: half the half-life` (:350) | page | Same. | moved |
| `null: Half's canvas does not fade as the grid does` (:352) | page | Same. | moved |
| `Short fades it at the Persistence menu's Short or faster: 0.7 a frame at most` (:354) | page | Same. | moved |
| `on the face a Trail chosen does nothing: the canvas fades as the grid does` (:357) | page | Same. | moved |
| `%s Enlarge, the light goes on fading at the Persistence: %.3f kept over %d frames, where %.3f is` (:387, x2) | page | Page grid across a resize; moves to the default. | moved |
| `null: Clear wipes it` (:389) | page | Same. | moved |
| `a split draws a figure for each hand, in two inks` (:404) | page | `genSet`, `sourceFigures()`, `layerPictures.live`; on the default via knobs and keys (braintest :608 draws a figure each there). | moved: Poly clicked, and whether each hand draws its own picture read off the instrument (was `layerPictures.live`) |
| `Which hands is offered in Enlarge while there are two figures, and not on the face` (:409) | page | Face. | moved |
| `A draws A's figure and none of B's` (:424) | page | Canvas inks; face. | moved |
| `B draws B's figure and none of A's` (:425) | page | Same. | moved |
| `null: Both draws both` (:426) | page | Same. | moved |
| `with only B drawn, the shared grid and each hand's are the same to the bit as with both` (:432) | page | Page grid and `layerPictures.engines[1].cells`; moves if those are fed on the default (not checked here). | gone: the page's grids. Replaced by: Which hands sends the instrument nothing |
| `null: one step of zoom moves them` (:437) | page | Its null. | gone, as :432 |
| `no page errors` (:440) | page | `bad` gathers every page's errors, the ?brain=js one's included. | moved |

20 sites read only default pages.

### envtest.py - wholly on ?brain=js - 33/33
Comment: "On ?brain=js (5m): this suite reads the page's own brain - its gate and envelope, read and set directly." Its offline renders build the generator worklet from `generatorModuleSource()` with no `wasm` in `processorOptions`, so they render the JavaScript engine; the rest are `makeGeneratorCore` in the page, `state.source.gated`, `MOD_SOURCES` and the readout (page :100).

| Check | Kind | Why | Batch 4 (13 Nov) |
|---|---|---|---|
| `a core nobody has gated is wide open and says so` (:126) | numbers | Borderline: `core.gated`/`core.envelope` of a JS core; the claim (ungated is a multiply by one) is a core unit check. | to pieces (env.py): envelope one and env.note nought, null a core gated with no note |
| `and its amplitude is the slider, from the first sample to the last` (:128) | numbers | Peaks of an ungated core; render or unit. | to pieces |
| `and the page opens with the generator gated before any keyboard is there` (:135) | page | `state.source.gated`, `kind == "tone"`; on the default it is the instrument's gate - braintest :159 holds "silent until a note" there. | rewritten: the default page, the instrument's gate (`kind` host), read off its own reading |
| `and the reading fails against the page as it opened until 10 Nov, ungated` (:137) | page | Its null. | moved (its null) |
| `it starts from nothing` (:197) | numbers | Envelope off an offline render; the model `render_cpp` move, with gate on/off at frames. | to pieces |
| `and is open within the attack it was given` (:203) | numbers | Same. | to pieces |
| `then falls to the sustain it was given` (:206) | numbers | Same. | to pieces |
| `and is gone within the release it was given` (:209) | numbers | Same. | to pieces |
| `the attack takes the time it says, not a time constant` (:230) | numbers | Same. | to pieces; null: the same samples against twice the times |
| `and the decay arrives at the sustain when it said it would` (:233) | numbers | Same. | to pieces |
| `and the release is over when it said it would be` (:237) | numbers | Same. | to pieces |
| `a note-on is doing something inside the block after it` (:250) | numbers | Same, first 128 frames after the gate. | to pieces; null: the block before is silent |
| `the gate opening is not a step` (:267) | numbers | Largest step at the edge; render. | to pieces |
| `nor the gate closing` (:270) | numbers | Same. | to pieces; null: an attack and release of nothing |
| `a second key over a held one does not restart the envelope` (:314) | numbers | `core.envelope` after a second `gate(true)`; render with two note-ons in Mono, envelope read off the level. | to pieces |
| `and does not take its velocity either` (:317) | numbers | Same. | to pieces; null: a key from silence takes its velocity |
| `a release runs all the way out` (:320) | numbers | Same. | to pieces; null: 23 ms into the release |
| `and the next key starts it again, at its own velocity` (:326) | numbers | Same. | to pieces; and new, from the mutation pass: the heard level at a quarter velocity |
| `a glide takes the same time whether a note is holding or not` (:358) | numbers | `estimateFrequency` on two JS cores; render with and without a held note. | to pieces; null: a 100 ms glide under a note |
| `it is registered, and the level is not, since F4b made it the output meter` (:372) | page | `MOD_SOURCES` keys; the face's registry, trivially the default. | moved |
| `and reads nothing while nothing is gated` (:374) | page | `env.note` source's value on the page brain. | moved: the instrument's envelope read back, nought with no note |
| `with no glide the pitch is simply the new one` (:398) | numbers | Pitch after a jump; render. | to pieces |
| `and with a glide it is still on its way there` (:401) | numbers | Same. | to pieces |
| `connecting a keyboard that drives the generator gates it` (:457) | page | `midiConnect`, `state.source.gated`, `env.note` value; on the default the instrument's gate and the Envelope card. | rewritten: gated from the first frame whatever is connected; at nought before a key |
| `a key opens the envelope, at the velocity it was played` (:460) | page | `env.note` value after a port note; braintest :612 holds the envelope source on the default. | rewritten: the controls (heard), not `state.source.set`; tightened to the sustain times the velocity, with a key at full as its null |
| `and letting go closes it` (:464) | page | Same. | moved |
| `a key held while the gate is handed over from an input sounds straight away` (:466) | page | `toMic()` then `toTone()` builds a new page generator under a held key; only the page's brain hands a gate over like this - goes. | gone: only the page's brain hands a gate over from an input |
| `and the keyboard going leaves the generator gated and silent, waiting for a note` (:471) | page | `midi.access = null`, page gate. | moved (`midiPanic` reaches the instrument) |
| `and the trace is silent with it, and a note brings it back` (:489) | page | Window peak with no keyboard; braintest :159 holds the same on the default. | moved |
| `and the silence reading fails on the note's trace` (:491) | page | Its null. | moved |
| `a gate held open with nothing played says why the screen is empty` (:525) | page | Readout line; braintest :651 holds it on the default. | moved |
| `and stops saying it once a note is held` (:527) | page | Same. | moved |
| `no page errors` (:533) | page | Errors. | moved |

### fadetest.py - 1 leg on ?brain=js beside the default - 4/54
A second page `js` opened on `?picture=0&brain=js` (:486) so that "a sound loaded ... heard so on either brain" (docstring); the leg is one loop of two checks over both pages and one check that the two are the two.

| Check | Kind | Why | Batch 4 (13 Nov) |
|---|---|---|---|
| `on %s a held note is steady before, and the tremolo is whole within two seconds of the load, as deep as it settles` (:491, ?brain=js leg) | engines compared | Both-brains loop; the default leg (`p`) already holds it on the instrument, so the leg goes. | gone; the default leg holds it |
| `null: on %s the same routing patched by hand is not whole within two seconds` (:494, ?brain=js leg) | engines compared | Same. | gone; the default leg holds it |
| `and the two brains are the two: the instrument, then the page's own` (:496) | engines compared | Exists only to say the two pages are the two brains. Goes. | rewritten: "what was heard is the instrument's", off the run's own source, seen red on the boot frames |
| `no page errors` (:790) | page | `bad` includes `pageerror (?brain=js)` from the leg; it stays, reading the default alone. | moved: the default page's alone |

50 sites read only default pages.

### filtertest.py - wholly on ?brain=js - 32/32
Lines 8-11: "this suite reads the page's own brain - its oscillators set by hand, and its speakers' graph". It opens once, at `?picture=0&brain=js` (line 71). Most of it is pure page functions (`biquadCoefficients`, `cutoffHz`, `capture()`) and the Web Audio monitor chain. The default site has that chain too: the host path builds one at `scope.html:14971`.

| Check | Kind | Why | Batch 4 (13 Nov) |
|---|---|---|---|
| agreement within a tenth of a decibel (116) | numbers | The page's `biquadCoefficients` checked against Web Audio's `getFrequencyResponse`. It becomes core `biquadCoefficients` (capture.h) against an analytic RBJ response, since Web Audio is not there offline. | to pieces (filter.py): the core's biquad against the Cookbook response as Web Audio's spec writes it, 560 points |
| resonance nought is maximally flat (129) | numbers | -3.01 dB at the corner, from the coefficient law. Core capture.h has the same law. | to pieces (functions_cpp `biquad`) |
| and the linear value in a dB slot would not be (131) | numbers | The trap's null, the same law fed 0.707. | to pieces (functions_cpp `biquad`) |
| the tone source is the silent one (169) | page | Reads `state.source.kind == "tone"`. Only the page's brain has this. Goes. | gone: only the page's brain has a tone source |
| the signal really is a square (170) | numbers | Fixture check on the steepest step of `capture()`. Offline: the core's capture of a held square. | to pieces (capture_cpp, a square under a 200 Hz low pass) |
| a low pass really rounds the corners off it (175) | numbers | Steepest edge of `capture()` with `state.filter` on. Core capture.h `filterInPlace`. | to pieces |
| the first samples are not louder than the rest (195) | numbers | The filter primed at the window's left edge. Core `filterInPlace` primes the same way. | to pieces, strengthened: the source holds the window only and the sine sits on 0.5, so an unprimed filter rings |
| and nothing is NaN (198) | numbers | The same capture, all finite. | to pieces |
| the lag lane is filtered too (215) | numbers | Lag lane peak against signal lane peak, from `capture()`. Core capture has the lag. | to pieces, strengthened: the signal lane must be filtered too (two unfiltered lanes agree) |
| it fits in a frame (239) | page | Milliseconds of the page's own JS `capture()`. A cost, not a number the engine makes. It goes, or becomes a core benchmark. | moved: the face's capture() over the instrument's lanes, the source asserted the instrument's |
| still fits a frame at full width, on the band split's four lanes (264) | page | The same, with a faked microphone (`toMic`, `micBands`). | rewritten: the Mic and Bands buttons, not `toMic()`; four lanes on the instrument |
| a shown lane is filtered (300) | numbers | `getLatestWindow` stubbed on the page's source, then `capture()`. Offline: core capture with a lane's `on` flag. | to pieces |
| a hidden lane is not filtered at all (301) | numbers | The same, with the lane hidden. | to pieces, strengthened: triggered on the hidden lane and compared whole |
| a source sweeps the cutoff (323) | numbers | Borderline. `lfos[0].value` is set by hand, then `applyModMatrix` and `filterNow().hz`. What it holds is the matrix's offset on the cutoff, so it becomes a render with lfo1 routed to `filter.cutoff`, reading the filter's Hz at the LFO's extremes. | to pieces (matrix_cpp `screen` and `filter`); and new, the cutoff slider's law |
| the filter survives a round trip (335) | page | `snapshot`/`restore`/`encodeSetup` called directly. Brain-free; moves to the default as it is. | moved |
| with its type and switch (336) | page | The same round trip. | moved |
| the only thing touching the speakers is the output clamp (369) | page | Hooks `AudioNode.connect` on the page's Web Audio graph. The host has a monitor chain too, so it moves to the default. | rewritten: the hook at init, so the instrument's chain is seen; every node to the speakers a clamp |
| there is exactly one chain for the source (371) | page | `monitorChains.size`. | rewritten: one chain, the source the instrument's |
| with a limiter set as a brickwall, not a compressor (372) | page | The page's DynamicsCompressor settings. | moved |
| and a clamp behind it, because a compressor has no lookahead (375) | page | The page's WaveShaper. | moved |
| and the filter starts out of the monitor path (377) | page | `chain.wet.gain`. | moved |
| picture only leaves the speakers dry (399) | page | `setAnalyseAt`/`setMonitorAt` and the chain's wet gain. | moved |
| both filtered brings the speakers in (402) | page | The same. | moved |
| and the screen can read the input while the ears do not (404) | page | The same. | moved |
| no AudioParam is assigned during a sweep (436) | page | The page's `applyModMatrix`, with LFOs set by hand, driving the monitor chain's AudioParams. Who does this on the default needs step 1's counter. | moved |
| they are all glided (438) | page | The same, counting `setTargetAtTime` calls. | moved, strengthened: the sweep must move the cutoff |
| unlimited it would be far past full scale (485) | page | An OfflineAudioContext render through `makeMonitorChain`: a Web Audio graph, not the engine. Brain-free. | moved |
| the chain holds it under full scale (486) | page | The same render, through the chain. | moved |
| post-filter is stated (493) | page | `el.readoutDetail` text. | moved, with a note held |
| and not when the screen reads the input (496) | page | The same. | moved, with a note held |
| the chain goes when the source does, and only the new source's own is left (509) | page | `el.srcTone`, `kind == "tone"`, chains rebuilt by the page's brain. Goes. | gone: only the page's brain has a source to drop |
| no page errors (512) | page | Housekeeping. | moved |

### handstest.py - wholly on ?brain=js - 39/39 (28 check, 11 null)
Lines 25-26: "the generator's two layers, its routes and Scan's strike are the page's own brain's". It opens at `?picture=0&brain=js` (line 49). Nearly all of it is the face: the selector, the links, the tab cards, and codes through `restore()`.

| Check | Kind | Why | Batch 1 (13 Nov) |
|---|---|---|---|
| the selector is in the header and hidden with one hand (73) | page | DOM `#handsPick`. Moves to the default as it is. | moved |
| shown on a split, naming the hands Lower and Upper, the lower chosen (75) | page | DOM. | moved |
| Upper chosen puts the upper hand on the panel (77) | page | `editLayer()`, `panelLayer`: face state. | moved |
| layered, the hands are A and B (79) | page | DOM. | moved |
| null: the split's names are not the layered names (80) | page | DOM. | moved |
| null: one hand is no hand to edit... (81) | page | `editLayer()`. | moved |
| a link on the Generator, the Amp envelope and the Voice filter on Play, ... and the Picture section (102) | page | DOM placement of the links. | moved |
| and none on the Keyboard, which is both hands by nature (107) | page | DOM. | moved |
| each shown with two hands and saying the same in both (108) | page | DOM text. | moved |
| null: with one hand none is shown (110) | page | DOM. | moved |
| linked, a knob moved on the upper hand moves both, and on the lower both (130) | page | `genSettings(0/1).amp`, the page's per-hand settings. On the default, click and read the setup or the instrument. | moved: reads the page's mirror (the face's per-hand copy); that the core links alike is parity's G6 |
| unlinked, the hand on the face alone (132) | page | The same. | moved, as (130) |
| null: linked and unlinked differ (134) | page | The same. | moved, as (130) |
| unlinking starts the other hand as a copy, and a code then carries it as the hand's own (135) | page | `genSettings` plus `snapshot()`. | moved, as (130) |
| linking again from the upper copies the upper over the lower (137) | page | `genSettings`. | moved, as (130) |
| null: from the lower, the lower over the upper (139) | page | `genSettings`. | moved, as (130) |
| a new split starts with everything linked (164) | page | `linked()`, `HAND_SECTION_IDS`. | moved |
| a code with B values loads the hand's own only where they differ from A's, the rest linked (168) | page | `restore()` called directly, then `linksSettle`. The core has its own. | moved |
| an old code whose every B value is A's loads linked throughout (170) | page | `restore()`. | moved |
| null: one B value a step apart loads that section as the hand's own and the rest linked (171) | page | `restore()`. | moved |
| so moving the upper hand there leaves the lower as the code had it (173) | page | `genSettings` after `restore`. | moved, as (130) |
| null: a code without B values loads linked (175) | page | `restore()`. | moved |
| a rack module's B fields make it the hand's own with bPlane on, and not with it off (176) | page | `restore()`. | moved |
| linked, the stage's routes push both hands at the one Amount (210) | numbers | Borderline. `pictureStage.glow`/`hold` are set by hand, then `compileRoutes`/`workletRoutes()`: the page's route compiler. What is held is the fold's push per hand at one Amount. The core computes routes itself, so it needs a render or hook that reads the core's push per hand. | gone to parity, native: each layer's fold at Amount 100 linked, off the instrument's routes |
| the Picture its own, the upper's Amount at nought: the lower's sound pushed, the upper's not (212) | numbers | The same, with `bPictureAmount` 0. | gone to parity, native: the upper's own Amount at nought, its fold nought |
| null: the upper's at nought is not what linked gave it (214) | numbers | The same. | gone to parity, native: its null, and the linked reading failing on it |
| each hand keeps its own Amount and Strike, the sliders show the hand on the face, and the title says which (215) | page | `pictureHands` and slider values: the face. | moved |
| a note on the lower half lights where Scan reads at the lower's Strike, one on the upper's at its nought lays nothing (218) | numbers | Borderline. Calls `scanStrike(48, 1)` directly with `pictureEngine.segment` hooked. The strike's level per hand is Scan's numbers; the core needs a strike-level reading. | gone to parity, native: each hand's own Strike off the instrument's layer grids, with a null (the upper's left at 50) |
| and a code carries each hand's Amount and Strike (221) | page | `snapshot()`. | moved |
| a routing on a linked control moves both hands at one depth, and its row says Both (247) | page | `workletRoutes()` amounts plus the editor's hand tags: the page's route compiler and the face. | rewritten: the routing the face stores and sends (mod/modB), not the page's worklet route compiler |
| on an unlinked one a depth set with the upper hand on the face is the upper's alone, and its rows say each hand (249) | page | The same. | rewritten, as (247) |
| null: the linked depths are not the unlinked (251) | page | The same. | rewritten, as (247) |
| a routing added to an unlinked control with the upper on the face is the upper's alone, said so, and stored as modB (252) | page | `state.modRoutings`, tags, `snapshot().mod/modB`. | moved |
| and its knob has it on the upper hand and not the lower (256) | page | `routingsFor`. | moved |
| a tab where the hands differ says so first, in the hand on the face's name... (270) | page | `paintTabLines`, card text. | moved |
| and counts what differs (272) | page | Card text. | moved |
| null: linked throughout, no tab says so (273) | page | Card text. | moved |
| null: with one hand, none says so (274) | page | Card text. | moved |
| no page errors (276) | page | Housekeeping. | moved |

### handtest.py - 2 legs on ?brain=js beside the default - 39/44 (5 default sites not listed: 513, 514, 516, 520, 522)
It opens at `?picture=0&brain=js` on the desktop (153) and on a phone (468), and on the default at `?picture=0` (498). The docstring gives no reason for the ?brain=js legs. Every check in them is a real gesture on the face (`page.mouse`, CDP touch), and the default leg already repeats the main one (pulled inward, against the compiled instrument). VALUES (line 102) reads `genSettings(0/1).warp/warpAt`, and the split section uses `genSet` (428) and `polyVoices(layer)` (440).

| Check | Kind | Why | Batch 1 (13 Nov) |
|---|---|---|---|
| grabbed on the %s diagonal, Bend at is that sample's moment (166) x4 | page | A gesture, read from `el.oscBendAt` against the drawn figure. The default leg does the same at 514. | moved |
| null: the angle counted the other way round fails the same tolerance on the %s (169) x4 | page | The same. | moved |
| on the %s, each lane read near the phase found for it is the shape, and the phase found is within 0.05 rad of the best (202) x6 | page | The face's bend estimator (`bendLanes`, `bendModel`, `bendWave`, `genSettings()`) over `xyView`'s lanes. Face code; runs on the default's lanes. | moved |
| null: a phase found 0.1 rad out fails the same reading (the %s) (205) x6 | page | The same. | moved |
| null: half a cycle out, it is not (the %s) (207) x6 | page | The same. | moved |
| pulled inward on the north-east diagonal, Bend moves a long way and the hand's mark has hold (230) | page | Gesture to slider, `bendMark`. | moved |
| and the figure ends at least twice as near the pointer as it began (234) | page | Drawn figure (`xyView`). Duplicates default 516. | moved |
| the sliders' readings say what the hand set (238) | page | Slider text. | moved |
| null: with Bend put back to nought the figure fails the same measure (243) | page | Drawn figure. | moved |
| pulled outward on the same diagonal, where no bend reaches, Bend stays at nought and the mark has no hold (250) | page | Gesture. | moved |
| null: the inward pull's mark, which had hold, fails the same check (252) | page | Gesture. | moved |
| pulled outward at the circle's right-hand extreme, Bend goes positive, the figure reaches out and the mark holds (266) | page | Gesture plus drawn figure. | moved |
| null: the same check against the opposite sign (269) | page | Gesture. | moved |
| the fixture: one signal on both lanes draws a diagonal line (281) | page | Drawn figure. | moved |
| pulled across a line, which no bend can move off itself, Bend stays where it was (282) | page | Gesture. | moved |
| a press at the circle's middle, a radius from the figure, changes nothing (291) | page | Gesture. | moved |
| a press %d px off the line %s (302) x2 | page | Gesture. | moved |
| a click on the figure that wobbles two pixels changes nothing (310) | page | Gesture. | moved |
| null: the same press pulled does (313) | page | Gesture. | moved |
| null: a double-click off the figure leaves Bend where it was (320) | page | Gesture. | moved |
| a double-click on the figure puts Bend to nought, and leaves Bend at (324) | page | Gesture. | moved |
| the pointer shows a hand near the figure and the screen's own cursor away from it (334) | page | CSS cursor. | moved |
| while held, the mark shows at the grabbed moment, on the figure, and the cursor is a closed hand (345) | page | DOM mark. | moved |
| in the marker's gold (348) | page | CSS colour. | moved |
| and let go, the mark goes (349) | page | DOM. | moved |
| the fixture: the reticle sits on the figure, within the grab's reach (361) | page | Photocell reticle position (`photo.u/v`), a face element. | moved |
| the reticle on the figure drags itself and bends nothing (362) | page | Gesture. | moved |
| null: with the reticle's presses passed through to the screen, the same place bends (372) | page | Gesture. | moved |
| in Y-T the time cursor still drags (382) | page | `state.cursor.t1`. | moved |
| null: with the cursors off, the same drag moves nothing (387) | page | The same. | moved |
| in X-Y, where the cursors are not drawn, a press on the figure across a cursor's line bends it and leaves the cursor (397) | page | Gesture. | moved |
| on %s's chord, Bend at is the moment of the bass, the voice X leans onto (449) x2 | page | Gesture on a split. The bass moment is fitted in Python from frequencies read via `polyVoices(layer)`, a page global; the default would take them from the MIDI notes. | moved: Poly clicked (setMidiMode was unheard: no upper hand drawn), the bass's frequency from the notes held, not `polyVoices`; null: the bass a semitone off fails B's (A's 131 Hz fit is not moved enough by a semitone in 10 ms) |
| null: the bass's moment a quarter cycle out... (%s) (451) x2 | page | The same. | moved, as (449) |
| a grab on B's figure (%.0f px from A's) moves B's Bend and Bend at, not A's, and puts the panel on B (454) | page | `genSettings(1)`, `editLayer()`. | moved, as (449) |
| null: a grab on A's figure (%.0f px from B's) moves A's, not B's, and puts the panel back on A (457) | page | The same. | moved, as (449) |
| no page errors on the page's own brain (460) | page | Housekeeping. | moved |
| a finger dragged on the figure bends it and the page does not move (485) | page | Phone leg, CDP touch. | moved |
| null: the same finger dragged where there is no figure scrolls the page (493) | page | Phone leg. | moved |
| no page errors on the phone (494) | page | Housekeeping. | moved |

### harmonytest.py - wholly on ?brain=js - 20/20
Lines 24-26: "The voices are the page's own core here (makeGeneratorCore); the compiled one is held to it by core/tests/parity.py". It opens at `?brain=js&picture=0` (line 75). The first six checks never touch the page's live brain: they build a `makeGeneratorCore` offline in the page.

| Check | Kind | Why | Batch 4 (13 Nov) |
|---|---|---|---|
| layer %s: the chord built a note at a time draws the struck chord's figure, sample for sample (96) x3 | numbers | An offline `makeGeneratorCore` render. Becomes a core render: voices joining in step. | to pieces (harmony.py, generator_cpp); and new: a chord struck while the last rings out is born at nought |
| layer %s: and the comparison fails out of step (98) x3 | numbers | The null of the same render. | to pieces |
| a chord struck twice, with other notes and time between, draws the same figure (106) | numbers | Offline render. | to pieces |
| and the comparison fails with the second strike out of step (107) | numbers | Null. | to pieces |
| a just fifth is a fifth, still (119) | page | `harmonyText`, a pure face function for the readout's words. Brain-free; stays as is. | moved (pure face functions) |
| an equal fifth turns at \|2 f_high - 3 f_low\|, 0.745 a second at A3 (120) | page | `harmonyOf(...).rate`, a face formula. | moved (pure face functions) |
| and not at the rate a wrong ratio would give (122) | page | The same. | moved (pure face functions) |
| an equal third turns nearly nine times a second (123) | page | `harmonyText`. | moved (pure face functions) |
| octaves are counted and the interval named within them (125) | page | `harmonyText`. | moved (pure face functions) |
| a tritone has no simple ratio, and says so (127) | page | `harmonyText`. | moved (pure face functions) |
| the order of the two notes does not matter (128) | page | `harmonyText`. | moved (pure face functions) |
| the dyad's pair: an equal fifth, turning (160) | page | `el.readoutDetail` after `genSet` and `midiNoteOn`. The readout's `harmonySaid` reads `genSettings` and `polyVoices`, which are page-side. | rewritten: the mode buttons, interval menu and tuning switch, not `setMidiMode`/`genSet`; reads the face's mirror (step 5) |
| and just, still - where the readout used to say nothing (161) | page | The same. | rewritten: the mode buttons, interval menu and tuning switch, not `setMidiMode`/`genSet`; reads the face's mirror (step 5) |
| and at unison, nothing (162) | page | The same. | rewritten: the mode buttons, interval menu and tuning switch, not `setMidiMode`/`genSet`; reads the face's mirror (step 5) |
| poly's outline: the lowest note against the highest, the inner one left out (163) | page | The same, through `polyVoices(0)`. | rewritten: the mode buttons, interval menu and tuning switch, not `setMidiMode`/`genSet`; reads the face's mirror (step 5) |
| with a split, each layer's outline: A a fifth, B a minor sixth (165) | page | The same. | rewritten: the mode buttons, interval menu and tuning switch, not `setMidiMode`/`genSet`; reads the face's mirror (step 5) |
| and A against B, A's lowest against B's highest (167) | page | The same. | rewritten: the mode buttons, interval menu and tuning switch, not `setMidiMode`/`genSet`; reads the face's mirror (step 5) |
| a held just fifth reads still to the picture: settled (195) | numbers | `pictureMeter` verdict over 6 s of the page's picture. Becomes the core's picture meter on an offline render. | left on ?brain=js: on the instrument's meter it does not hold (section 9) |
| and an equal third, turning, reads moving, changing more a frame (196) | numbers | `pictureMeter.change` and its verdict. | left on ?brain=js as :195's twin; the core's comparative twin in pieces |
| no page errors (199) | page | Housekeeping. | moved |

### hosttest.py - 1 leg on ?brain=js beside the default - 1/50 (49 default or fake-bridge sites not listed)
Line 131: "with ?brain=js no host at all". The ?brain=js page (134) is used once, as the null half of the first check.

| Check | Kind | Why | Batch 4 (13 Nov) |
|---|---|---|---|
| on its own the page is the website: the site's instrument, not the plugin's, and with ?brain=js its own generator (the null) (136) | page | Reads `state.source.kind == "tone"` and `scopeHost === null` on ?brain=js beside the default's `kind == "host"`. Once ?brain=js goes, the null half goes; the null needs another source, e.g. the bridged page's `rate`/`said` as the contrast. | rewritten: the null is the same reading inside the plugin, which must not be the website's |

### inputtest.py - wholly on ?brain=js - 11/11
Lines 22-26: "this suite reads the page's own brain - its rule that an input opens only while it can be heard, where the instrument hears its input always". It opens at `?brain=js` (line 90). The first six are offline `makeGeneratorCore` renders with `core.setInput(x)`.

| Check | Kind | Why | Batch 5 (13 Nov) |
|---|---|---|---|
| with the mode off, or a ride at a depth of nought, the input changes nothing at all (102) | numbers | Offline core render with input samples. `render_cpp` must take an input lane. | to pieces (input.py: generator_cpp's `input`); null a ride at a half |
| a ride scales every sample by (1 + 2 depth x): the sound rides on the outline (112) | numbers | The same. | to pieces; null a ride that shifts |
| FM is a factor on the rate: a steady quarter at full depth draws what twice the pitch draws (120) | numbers | The same. | to pieces; null at half the depth |
| and a deep enough negative input stops the waveform rather than running it backwards (124) | numbers | The same. | to pieces; null an eighth below |
| a waveform clocked by the input plays at the input's pitch, and runs free at its own when the input stops (141) | numbers | The same. | to pieces; nulls unclocked, and a stalled clock |
| and each of the input's upward crossings restarts the cycle... (152) | numbers | The same. | to pieces; null unclocked |
| not heard, it says so and opens nothing: the input would have nowhere to go (189) | page | The page brain's rule (`liveStreams`, `genVoice().setSound(false)`), which the instrument does not have. Goes. | gone: the page brain's rule |
| heard, the input is opened and connected, and the drawn size swings with it from near nought to twice (191) | page | Mostly the same rule (`inputConnected`, opened streams). The size swing is already held by 112. | rewritten on the default: the site's input reaching the instrument, its figure from 0.003 to 0.77; null at a depth of nought |
| and a setup code carries the mode and the depth (195) | page | `snapshot()`. Brain-free. | moved to the default; null the code at nought |
| switched off, the input is let go of and disconnected (196) | page | The page-only rule. Goes. | gone: the page brain's rule |
| no page errors (199) | page | Housekeeping. | stays, on the default page |

### keystest.py - wholly on ?brain=js - 37/37
Lines 15-18: "this suite reads the page's own brain - its gate, read directly". It opens at `?brain=js` (line 43). Everything is driven by real mouse and keys on the on-screen keyboard and read off `midi.notes` and the lit keys, which are face and page MIDI-stack state that the default has too. Only the gate (`state.source.gated`, lines 76, 87, 294) and the generator's pitch and interval (`state.source.settings.freq/interval`, 113, 151) are the page's brain.

| Check | Kind | Why | Batch 1 (13 Nov) |
|---|---|---|---|
| with no port and no keys there is no keyboard, and the waveform waits for a note all the same (94) | page | `state.source.gated`, the page's gate. On the default, the instrument's gate or a silent render. | moved; also reads silence off the instrument's lane (the gate flag says the generator waits for notes, not that it is silent); null: a held note sounds |
| and the reading fails against an ungated generator (97) | page | Null on the same. | moved |
| opening the keys makes a keyboard present, and the waveform still waits for a note (98) | page | `keyboardPresent()` plus the gate. | moved, as :94 |
| two octaves and the C that closes them, twenty-five keys (100) | page | DOM. | moved |
| and the Playing line shows, as it does for a port (102) | page | DOM. | moved |
| opening it moves no control on the page, and does not resize the trace (104) | page | Layout boxes. | moved |
| pressing E3 puts E3 on the stack at the slider's velocity (117) | page | `midi.notes`. | moved |
| and the generator plays it (119) | page | Borderline. Reads `state.source.settings.freq`, the page brain's setting, not a sound. On the default: a click, then the instrument's pitch (or an offline render of note 52). | rewritten: the pitch off the lane the instrument drew (the mirror's `settings.freq` was the page's MIDI apply, which passed on the default for the old reason); null against D#3 |
| the key is lit, and only that key (122) | page | DOM. | moved |
| and lifting the finger releases it (123) | page | `midi.notes`, DOM. | moved |
| the velocity slider is the velocity (132) | page | `midi.notes`. | moved |
| dragging from C3 to D3 leaves D3 held and C3 released (143) | page | Stack and DOM. | moved |
| and letting go ends it (145) | page | Stack. | moved |
| two taps under latch hold both notes after the mouse is up (158) | page | Stack. | moved |
| and the dyad is the interval between them - seven semitones, a fifth (160) | page | `state.source.settings.interval/octaves`, the brain's setting. | rewritten: the ratio of the latched fifth's two drawn lanes (was the mirror's `settings.interval`); null against a fourth |
| tapping a latched key again lets it go (162) | page | Stack. | moved |
| and turning latch off lets go of the rest (163) | page | Stack. | moved |
| a note held when latch goes on is kept when the finger lifts, then released (172) | page | Stack. | moved |
| S is D3 while the keys are open (181) | page | Stack. | moved |
| and it does not also switch the scope to Single (182) | page | `state.mode`. | moved |
| releasing the letter releases the note (184) | page | Stack. | moved |
| X moves the keys up an octave (199) | page | `screenKeys.base`, DOM. | moved |
| and a letter held across the shift releases the note it started (201) | page | Stack. | moved |
| while the same letter now plays the octave above (204) | page | Stack. | moved |
| a note held by a finger and a letter survives the finger lifting (212) | page | Stack. | moved |
| typing into a text field types, and plays nothing (225) | page | Stack. | moved |
| but a focused checkbox does not stop the letters playing (227) | page | Stack. | moved |
| a note from a port lights the screen's key (234) | page | `midiBytes`, DOM. | moved |
| losing the window darkens the keys and forgets the latch (247) | page | Stack, DOM. | moved |
| so the next tap on that key plays it rather than releasing nothing (249) | page | Stack. | moved |
| a latched note a port released is played again by the next tap (271) | page | Stack. | moved |
| and turning latch off does not cut a C3 the port started since (273) | page | Stack. | moved |
| a finger left down across a panic lets go of nothing when it lifts (287) | page | Stack. | moved |
| closing the keys releases what they held and not what a port holds (298) | page | Stack, `screenKeys.latched`. | moved |
| and the generator goes on waiting for a note with the keys gone (300) | page | The gate again (`state.source.gated`). | moved: the mode flag, now the instrument's |
| with the keys closed, S is Single again (306) | page | `state.mode`. | moved |
| no page errors (313) | page | Housekeeping. | moved |

### lanetest.py - wholly on ?brain=js - 34/34
Lines 18-21: "this suite reads the page's own brain - its oscillators, set by hand between frames". It opens at `?brain=js` (line 57). Most of it is the knob's ring, a face drawing. The brain matters only where `lfos[0].value` or `.rate` is set by hand: the live tick (218), the zoom (258) and the trigger position (292, 296).

| Check | Kind | Why | Batch 1 (13 Nov) | Batch 3 (13 Nov) |
|---|---|---|---|---|
| full depth on frequency is exactly an octave up (79) | page | `destReach`, the face's lane law (`scope.html:30256`). Brain-free, though its claim is to match the engine's law, which only parity relates. | moved |  |
| and full depth the other way is an octave down (81) | page | `destReach`. | moved |  |
| a depth of log2(1.5) is a fifth (83) | page | `destReach`. | moved |  |
| amplitude only ducks, and halves at half depth (85) | page | `destReach`. | moved |  |
| half depth on phase is a quarter turn (88) | page | `destReach`. | moved |  |
| half depth on rotation is an eighth of the slider (92) | page | `destReach`. | moved |  |
| full depth on cutoff is 400 steps, as declared (94) | page | `destReach`. | moved |  |
| the cap sits on the octave, not at the end of the range (122) | page | Knob face CSS properties. | moved |  |
| and the ring runs from the value to it (126) | page | The same. | moved |  |
| a second source does not move the first one's cap (162) | page | Ring. | moved |  |
| and the cap is where the first one's own depth puts it (165) | page | Ring. | moved |  |
| focusing the second shows the second, at its own depth (168) | page | Ring. | moved |  |
| and the one not drawn is a tick (171) | page | DOM. | moved |  |
| an oscillator's bar reaches one way from the value (188) | page | Ring. | moved |  |
| and an envelope's the same, since the bar is the depth you set (196) | page | Ring. | moved |  |
| the cap says it cannot get there (209) | page | DOM class. | moved |  |
| but the depth is kept, not trimmed (211) | page | `state.modRoutings`. | moved |  |
| a patched control shows itself working (234) | page | The `--now` dot driven by the page's `lfos[0]`, rate set by hand. On the default the dot reads the instrument's LFOs (lfos.bin); a step 5 item. | moved: the dot is driven by the instrument's LFO 1 (the rate set by hand was dead there, and went); null: a source at rest |  |
| the tick is on whether or not anything is in focus (235) | page | DOM. | moved |  |
| and the lane has no handle at all (238) | page | DOM. | moved |  |
| nothing on it, nothing drawn (248) | page | DOM. | moved |  |
| but the way in is still there (249) | page | `menuControl`. | moved |  |
| the transport's zoom takes a patch (268) | page | DOM class. | moved |  |
| full depth is the eight steps it declares (269) | numbers | `state.zoomMod` after `applyModMatrix`, with `lfos[0].value = 1` set by hand. The matrix's offset; core matrix.h. | left on ?brain=js: LFO 1 held at a value by hand, which in C++ is render_cpp's wider input | to pieces (lane.py, matrix_cpp `screen`) |
| and it magnifies (271) | numbers | `state.zoom` with the offset applied. | left on ?brain=js, as :269 | to pieces |
| with the offset back to nothing at rest (273) | numbers | The matrix's offset at rest. | left on ?brain=js, as :269 | to pieces |
| full depth moves the offset half a window (312) | numbers | `state.positionMod` from the matrix, LFO set by hand. | left on ?brain=js, as :269 | to pieces |
| and nothing at rest (314) | numbers | The same. | left on ?brain=js, as :269 | to pieces |
| and the window actually slides by that much (317) | numbers | `capture().pre` moved by the offset. Core capture.h. | left on ?brain=js, as :269 | to pieces (capture_cpp, given the matrix's offset) |
| the trigger level is untouched (321) | numbers | `state.level` unchanged by the matrix. | left on ?brain=js, as :269 | to pieces |
| and so is the knob it is offset from (323) | numbers | `state.position` unchanged. | left on ?brain=js, as :269 | to pieces |
| a routing made anywhere is a row on the source's tab, with its depth (341) | page | Editor DOM. | moved |  |
| and two destinations are two rows, each at its own depth (351) | page | Editor DOM. | moved |  |
| no page errors (355) | page | Housekeeping. | moved |  |

### layerpicturetest.py - 1 leg on ?brain=js beside the default - 15/19 (4 default sites not listed: 268, 270, 271, 273)
Lines 27-32: "All of that on ?brain=js, whose page computes the routes itself. The default page plays the site's compiled instrument, which computes its routes in the core ... the last leg reads them back from it". It opens at `?brain=js` (71) and on the default (236). The numbers checks drive the page's own per-layer picture engines and stages by hand (`layerPictures.stages`, `layerPush`, `stepRoutes`, `genRoutes`).

| Check | Kind | Why | Batch 2 (13 Nov) |
|---|---|---|---|
| unsplit, the layer screens are never made and every loop route carries the one shared push to both layers (88) | numbers | `genRoutes` after `stepRoutes()`: held equals heldB. The core computes routes, so it needs the core's push per layer read out. | gone to parity: pieces/layerpicture.py, picture_cpp with the layers off: no grid made, both sounds the shared push |
| with B silent, A's screen moves and B's does not (114) | numbers | `layerPictures.values[i].raw.cover/change`, per-layer picture readings over 3 s. The default leg (268) reads the instrument's. | gone to parity: pieces/layerpicture.py, picture_cpp, A's figure turning and B's a dot, 150 frames |
| and with A silent, B's moves and A's does not (115) | numbers | The same. | gone to parity: pieces/layerpicture.py, the other way round |
| and the check fails on the shared screen read for the still layer (116) | numbers | Null on the same readings. | gone to parity: pieces/layerpicture.py, null: the still layer's reading for the moving one |
| each picture moving its own sound: B's stage changing moves B's push and not A's (142) | numbers | Borderline. Stages set by hand (`Object.assign(stages[l], {glow,...})`), then routes. Core picture.h has `layerPush`, but an offline render cannot set a stage, so it needs a core-level hook. | gone to parity: pieces/layerpicture.py, stages put in (lput), each sound's push |
| and with B's picture heard by A as well, it moves A's push too - the check can see it (144) | numbers | The same. | gone to parity: pieces/layerpicture.py, menus A both |
| a sound that hears both pictures takes their average (161) | numbers | `layerPush` arithmetic (picture.h:595 in the core). | gone to parity: pieces/layerpicture.py, the core's push |
| and not their sum, which the check would read as wrong (163) | numbers | Null. | gone to parity: pieces/layerpicture.py, null |
| own, crossed and neither: each sound hears exactly the pictures its menu sends it (164) | numbers | `layerPush`. | gone to parity: pieces/layerpicture.py, own, crossed, neither |
| a crossed pair is held by the lower governor in its cross terms, and an own term by its own (173) | numbers | `layerPush` with holds. | gone to parity: pieces/layerpicture.py, B's hold at a quarter |
| and the check fails on a cross term that ignored the hold (177) | numbers | Null. | gone to parity: pieces/layerpicture.py, null |
| a layer whose screen runs away is held to the floor by its own governor, and the other layer is not (195) | numbers | Borderline. Injects `engines[1].cells.fill(1)` every frame for 7 s. The governor is a number, but the fixture is a page-only injection; offline it needs a sound that runs away, or a hook. | gone to parity: pieces/layerpicture.py, B's grid filled every frame, 140 frames of 50 ms (made-up time, not a timer); null A's filled instead |
| the menus show while the layers draw a figure each, and not for A against B or with no split (223) | page | DOM row. | moved: the split pressed (setDisplay and setMidiMode were not heard) |
| a setup carries both, an old code is each picture moving its own sound, and nonsense falls back (225) | page | `restore()`/`encodeSetup`, read through `layerPictures.moves`. | rewritten: codes loaded with loadCode (restore() direct changes the face alone on the default), read off the menus and the instrument's own reading of the moves; +1 null |
| no page errors (229) | page | Housekeeping. | moved (one page now) |

### layerplanetest.py - 1 leg on ?brain=js beside the default - 45/49 (4 default sites not listed: 462, 465, 469, 471)
The docstring (lines 34-35) puts the default leg as "the site's default, the instrument: the same hands on its panel". The ?brain=js leg (102) has three parts. The core part is an offline `makeGeneratorCore` render with routes injected (`setRoutes`, with `held`/`heldB` forced to 1). The panel part reads `plane`, `planeB`, `echoB` and `genSettings`. The beam part reads `beamX`/`beamY`. Line 474's "no page errors" reads a `bad` list shared by both pages (line 417 appends to it), so it is listed.

| Check | Kind | Why | Batch 2 (13 Nov) |
|---|---|---|---|
| with B's own off, B's fields set to junk change not one sample of any pair (118) | numbers | Offline core render, 6 lanes. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| and with it on the same junk changes B's picture and the sound, and not A's picture (120) | numbers | The same. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| B's own mirror folds B's X onto its right half, and A's X keeps its left (127) | numbers | The same. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| and the same field with B's own off folds nothing (129) | numbers | The same. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| unturned, B's one note is a diagonal: X and Y the same (137) | numbers | The same. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| an eighth of a turn lays it on the Y axis: X nought, Y the diagonal's length (139) | numbers | The same. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| and the other way lays it on the X axis instead, the same length (143) | numbers | The same. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| with B's own mirror and none of A's, B's octave is heard and A's is not (156) | numbers | Heard lane, single-bin transform. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| Together, the mirror is both layers' and both octaves are heard (158) | numbers | The same. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| and with the mirror A's alone, A's octave is heard and B's is not (160) | numbers | The same. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| B's picture with A's depth on the twist changed and B's still nothing is the same picture (166) | numbers | A route injected with amount/amountB. Needs `render_cpp` to take routings (from a setup's `mod`/`modB`). | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| and given a depth of its own, it moves (168) | numbers | The same. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| a routing on Turn at B's depth of a quarter turns B an eighth: its diagonal on the Y axis (180) | numbers | A route with `held: 1` forced. Offline it needs a source that holds at one, or a hook. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| and at B's depth of nought, whatever A's, B is not turned (183) | numbers | The same. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| and with B's own plane off the routing turns nothing (186) | numbers | The same. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| the Turn row takes a routing like any destination, and it is slot 32, where it was added (197) | page | `MOD_DESTS`, `menuControl`: face and table. Brain-free (the slot is also schema). | moved |
| B's own echo half a period late cancels half of B's picture, and leaves A's the same samples (215) | numbers | Offline core render. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| and with B's own off its echo's fields do nothing (217) | numbers | The same. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| Together, the same echo as A's halves B's picture as well, and moves A's (218) | numbers | The same. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| in the heard pair B's own echo halves B's note and leaves A's (223) | numbers | The same. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| and Together the echo, A's, moves A's note too (225) | numbers | The same. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| a routing on the echo's level through B's fade gives B's own echo its level (234) | numbers | An injected route with held forced to 1. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| and through A's fade alone it leaves B's picture as it was (236) | numbers | The same. | gone to parity: pieces/layerplane.py, generator_cpp, the same fixture and routes in its own form |
| with one layer the link is hidden, the section is the Plane and its Turn the screen's (271) | page | DOM. | moved |
| with two it shows, the same in both, and a menu moved writes both hands' plane (273) | page | DOM plus `planeB`. | moved: Poly pressed (setMidiMode was not heard); +1 null, the setup sent has no plane of B's before the link |
| unlinked with the upper edited, B has a plane of its own that starts as the hand on the face... (275) | page | `planeB`, `genSettings(1)`. | rewritten: 'the generator' is the setup the face sends (snapshot's bPlane), not genSettings |
| a menu and the Turn moved with B's shown are B's, and A's plane is untouched (278) | page | `plane`, `planeB`, `genSettings`. | rewritten, as (275): bMirror, planeMirror and bTurn sent |
| the lower shows A's plane with the screen's Turn, and writes A's alone (281) | page | The same. | moved |
| the upper chosen again shows B's plane (284) | page | DOM. | moved |
| linked again from the upper, B's plane is copied over A's, B's turn goes, and the generator is told (286) | page | `planeB`, `genSettings`. | rewritten, as (275) |
| with the Plane the upper's own, the screen's rotation leaves B's figure a diagonal (317) | numbers | Borderline. Page `beamX`/`beamY` with `state.rotate` set by hand and a note. What is held is whether the screen's turn reaches B: a core render with the Plane's turn and B's own. | gone to parity: pieces/layerplane.py, the instrument's own grid: B's own plane leaves B's figure as it was under the screen's Turn; linked turns it |
| and linked turns it onto the Y axis, as it turns A (320) | numbers | The same. | gone to parity: pieces/layerplane.py, as (317) |
| B's own plane is written into a code and read back as it was (342) | page | `encodeSetup`/`restore`, `planeB`. | moved: codes loaded with loadCode; reads the face's planeB |
| a code of B's own with a field missing takes A's for it (345) | page | `restore()`. | moved, as (342) |
| a code from before it has B following A, and linked nothing of it is written (348) | page | `restore()`, `decodeSetup`. | moved, as (342) |
| with two layers the Delay's link shows, the same in both, and its controls write both hands' echo (390) | page | DOM plus `genSettings`. | rewritten: the setup sent (snapshot), not genSettings |
| unlinked with the upper edited, B has an echo of its own that starts as the hand on the face, and nothing else of its own (392) | page | `echoB`, `genSettings(1).timeOwn`. | rewritten, as (390): B's delay fields in the code and nothing else of B's rack |
| the echo's time moved with B's shown is B's, A's untouched, and the chorus, linked, moves both (395) | page | `echo`, `echoB`, `genSettings`. | rewritten, as (390) |
| the lower shows A's echo and writes A's alone (398) | page | The same. | rewritten, as (390) |
| the upper chosen again shows B's echo (401) | page | DOM. | moved |
| B's own echo synced to a crotchet follows the tempo: 500 ms at 120, 1000 at 60, and A's stays free (403) | numbers | Borderline. `genSettings(1).delayMs` after `setTempo` and `clockStep()` called by hand. The sync arithmetic belongs to the clock (core clock.h); an offline render at two tempos reads the echo time. | split: the time following the tempo gone to parity: pieces/layerplane.py, the instrument's echo found in B's lanes, 500 ms at 120 and 1000 at 60, null unsynced at 375 (setTempo and the page's clockStep were called by hand); here, the face: B's synced and A's free, and the setup sent says so |
| linked again from the upper, B's echo is copied over A's, and the generator is told B has none of its own (405) | page | `genSettings`, `echoB`. | rewritten, as (390) |
| B's own echo is written into a code and read back as it was (408) | page | `encodeSetup`/`restore`. | moved: loaded with loadCode |
| a code of B's own with a field missing takes A's for it, and linked none of it is written (411) | page | `restore()`. | moved, as (408) |
| no page errors (474) | page | Housekeeping over both pages. | moved |

### layertest.py - wholly on ?brain=js - 36/36
Lines 29-32: "this suite reads the page's own brain - its voices and worklet, and setMidiMode called directly". It opens at `?picture=0&brain=js` (line 71). The first ten are offline `makeGeneratorCore` renders. The rest is keyboard routing, the face and the page's worklet.

| Check | Kind | Why | Batch 2 (13 Nov) | Batch 6 (14 Nov) |
|---|---|---|---|---|
| two layers step the oscillators once a sample, not twice (94) | numbers | Offline core. It reads `lfos[0].phase` after the block, an internal value, so `render_cpp` must report LFO phase (or show it through a routed sound). | gone to parity: pieces/layer.py, the oscillator heard, not its phase read: a 4 Hz square on A's level toggles it as often with two layers as with one |  |
| layer A's picture has A's notes and not B's (155) | numbers | Offline core, bin energies. | gone to parity: pieces/layer.py, bins on generator_cpp's A lanes |  |
| layer B's picture has B's note and not A's (158) | numbers | The same. | gone to parity: pieces/layer.py, bins on B's lanes |  |
| and the heard pair has all three (162) | numbers | The same. | gone to parity: pieces/layer.py, bins on the heard pair |  |
| because it is A's lanes and B's summed, sample for sample (164) | numbers | The same. | gone to parity: pieces/layer.py, heard = A + B, sample for sample |  |
| and the comparison fails with B left out (166) | numbers | Null. | gone to parity: pieces/layer.py, its null, B left out |  |
| and a caller that asks for no lanes of B's hears exactly the same (167) | numbers | A second core with only the heard pair asked for. | gone: the page's core took B's lanes as optional arguments; the core computes B whether or not they are asked for (generator.h) and the instrument asks for them with the heard pair |  |
| layer B plays its own shape - a square under A's sine (170) | numbers | Third harmonic ratio. | gone to parity: pieces/layer.py, third harmonic of B's square |  |
| and speaks with its own envelope - slow where A's is quick (173) | numbers | Envelope peaks. | gone to parity: pieces/layer.py, B's slow attack against A's quick |  |
| the envelope a source reads includes layer B's notes (193) | numbers | `core.envelope` and `core.voicesB.length`: internals, which `render_cpp` would have to report. | gone to parity: pieces/layer.py, generator_cpp's trailer (envelope, voicesB) |  |
| and layer B's voices are let go once their release is over (195) | numbers | The same. | gone to parity: pieces/layer.py, the trailer after the release, with a null a few ms into it |  |
| a split sends notes below the point to A and the point upwards to B (221) | numbers | Borderline. Reads `genSettings(layer).voices`, put there by the page's `polyVoices`. The rule is in core keyboard.h, so it becomes a timed-MIDI render with energy per layer. | gone to parity: pieces/layer.py, keyboard_cpp's chords per layer, 60 among the notes |  |
| and offers four lanes, named for their layers, as two figures (224) | page | `laneCount`, `laneName`, `state.source.figures()`: face and source layout. | moved: Poly pressed and the split chosen (setMidiMode was not heard); lanes, names and figures read off the instrument's source |  |
| layered sends every note to both (228) | numbers | As 221. | gone to parity: pieces/layer.py, keyboard_cpp, layered |  |
| the split point is learned from the next key, which still plays (243) | page | The Learn button, `midi.layers.point`, `midi.notes`. | left on ?brain=js, its own page: on the default the Learn button moves the face's point ('at G3') and not the instrument's (A3 still in A's lanes after learning G3) - passed on the default for the page's reason; needs a page change | left on ?brain=js: re-measured on the default, learned at F4 the face says "at F4" and D4 still lands in B's lanes (the instrument splits at C4); passes only once the defect is fixed (after-stage-5.md) |
| layer A draws by its rule and layer B by its own (264) | numbers | Borderline. `midi.draws` set by hand, then voice roles; the drawn-note rule. Offline: a timed-MIDI render with each layer's draw rule in the setup, energies per layer's picture. | gone to parity: pieces/layer.py, keyboard_cpp with each layer's draw rule |  |
| and the readout says each layer's outline (266) | page | `el.readoutDetail`. | moved: each hand's Draw menus changed with that hand on the face (midi.draws was written by hand); the readout is the face's own reckoning |  |
| A against B is one pair: both of A's drawn notes on X, B's on Y (289) | numbers | Bin energies of `getLatestWindow`; an offline render with `layerPair: against`. | gone to parity: pieces/layer.py, the instrument natively, A against B, bins on X and Y, with a null drawn a figure each |  |
| named for the layers, with the X-Y menus back (294) | page | `laneName`, DOM. | moved: the face's names after the pairing menu (genSet dropped); +1 null, a figure each |  |
| layer B's figure is drawn beside A's, not just A's (325) | page | `phosphor.grid` lit fraction: the page's drawing of the lanes. Face; the default draws too. | moved: the face's grid drawing the instrument's lanes; X-Y pressed (setDisplay was not heard), the phase left at the slider's 90 (genSet dropped); +1 null, every note let go |  |
| and the X-Y menus step aside while the layers choose the figures (327) | page | DOM. | moved |  |
| with the lag on the figure is the lag's, not the layers' (354) | page | `lagActive`, `sourceFigures`, `laneCount`: the page's lane layout. | moved: the face's lane layout |  |
| even when a modulation turns the lag on and nothing rebuilds the lanes (358) | page | `state.lagMod` set by hand. | moved: state.lagMod is the page's visual matrix, which moves the screen's own destinations on the default as well |  |
| the worklet sounds both layers (388) | page | Analyser on the page's JS worklet through its monitor chain. It tests the page's own worklet plumbing; goes. The instrument's worklet is braintest's. | gone: the page brain's own worklet and monitor chain; the instrument's worklet is braintest's |  |
| and posts layer B's picture back apart from A's (389) | page | The page worklet's B lanes crossing the thread. Goes. | gone, as (388) |  |
| with B shown and the Generator its own, its link says so and the panel shows only what B has (422) | page | DOM. | moved |  |
| and its controls write layer B, leaving A alone (425) | page | `genSettings(0/1)`. | rewritten: reads the setup the face sends (snapshot) for each hand, not genSettings, the page's mirror on the default |  |
| the lower hand chosen puts A's values back on the controls, and the link names it (429) | page | DOM. | moved |  |
| a code taken with B on screen keeps A's controls as A's (434) | page | `snapshot()`. | moved |  |
| split, point, pairing, B's rule and B's sound survive a setup code (459) | page | `restore()`, `genSettings`, `midi.layers`. | moved: loaded with loadCode (restore() direct changes the face alone on the default); reads the face's copy of the setup; the core's decode is parity's restore |  |
| a code's envelope reaches the generator, not only its sliders (464) | page | `genSettings().releaseMs` after `restore`. | moved, as (459): 'the generator' is the face's copy here |  |
| and a code from before layers has none, with B sounding like A (466) | page | The same. | moved, as (459) |  |
| leaving poly ends layer B and gives the page two lanes and layer A's panel (490) | page | `layersOn`, `state.source.channels/layout`, DOM. | rewritten: Dyad and Poly pressed (setMidiMode was not heard); two lanes read off what the instrument sends |  |
| and coming back to poly splits the held notes again (495) | page | `genSettings().voices`. | rewritten: the held notes found split again in the instrument's A and B lanes, not the page's genSettings voices; +1 null, the lanes swapped |  |
| with the input drawn a split is kept, not applied, and the panel says why (516) | page | A stand-in `state.source` (`Object.create(saved, ...)`), page-only. | gone: a stand-in state.source on the page and the page's own syncMidi, a path only the page's brain has; the instrument's input drawn with layers is parity's 'layered input' |  |
| no page errors (521) | page | Housekeeping. | moved (and a second on the ?brain=js page) |  |

### livefxtest.py - wholly on ?brain=js - 17/17
Lines 29-32: "this suite reads the page's own brain - its live input's insert". It opens at `?picture=0&brain=js` (line 89). The insert (`state.source.fx`, its worklet, `setMonitor`) is the page's. The arithmetic is the generator's, so it moves to a core render only if `render_cpp` takes input samples.

| Check | Kind | Why | Batch 5 (13 Nov) |
|---|---|---|---|
| a microphone with no effect on has no effects node in its path, and draws its input as it is (101) | page | `state.source.fx.active`: the page insert's lifecycle. Goes. | rewritten on the default: the site's Mic drawn by the instrument (`host`), as it is; the insert's part gone |
| mirrored, the input is drawn with no negative half on either axis (134) | numbers | The plane's mirror on input samples. A core render with input in. | to pieces (livefx.py: render_cpp drawing the input) and on the default (the site's mirror reaching the instrument); nulls as it is |
| and a change made while it runs reaches it: X alone folded, Y given back its negative half (136) | page | The page telling its running insert worklet. Goes. | to pieces, as X alone folded; the running worklet's part gone |
| and the speakers are handed the same: what reaches the monitor chain is mirrored too (138) | numbers | Borderline. Read from an analyser on the page's monitor chain. What is held is that the heard pair is mirrored, which is the core's heard output. | to pieces (the heard pair); null unmirrored |
| and the section says it is on your input, drawn and heard (141) | page | `el.planeWhere` text. | moved to the default, the face's words for a microphone |
| the mirror on both folds every angle of the input into 0 to pi/2, as the generator's does (159) | numbers | Angles of the drawn pair. | to pieces; null unfolded |
| and the two channels arrive as two: the folded input fills the quadrant rather than one ray of it (164) | numbers | The same. | to pieces; null one channel in both |
| with the last effect off, the effects node is gone and the input is drawn as it is again (172) | page | `fx.active`. Goes. | gone: the insert's life |
| an oscillator on the twist swirls a mono input's diagonal off itself, from a slider at nought (211) | numbers | lfo1 routed to `gen.twist` (with `lfos[0].depth/rate` written by hand) on input samples. A core render with input and a routing. | to pieces; null routed at nought |
| and a routing turned to nought mid-stream stops swirling it: the worklet follows the page every frame (213) | page | The page's per-frame message to its insert. Goes. | gone: the page's per-frame message |
| a mono input is one lane, two while the effect is on, and one again when the routing goes with the node (218) | page | `state.source.channels`, lane rows. | gone: the lane rows round the insert |
| a delay on a live input puts the repeat 150 ms after the burst, to within 2 samples (260) | numbers | Echo onsets on input samples. A core render with input. | to pieces; nulls no delay, and 160 ms |
| and its effects are drawn (263) | page | Text. | gone: the face's words are :141's |
| a band split gets no effects insert, and the sections say why (284) | page | `'fx' in state.source`, text. | moved to the default, the words and the four lanes; the insert's part gone |
| and the source it replaced has let its effects node go, rather than leave it running on a closed input (286) | page | Insert lifecycle. Goes. | gone: the insert's life |
| and on the tone the effects are the generator's (288) | page | Text. | moved to the default; null the two words differ |
| no page errors (290) | page | Housekeeping. | stays, on the default page |

---

### livetest.py - wholly on ?brain=js - 40/40
Docstring note (:8): it "reads the page's own brain - its microphone and band-split sources, and their graphs". Everything is on the page brain's `mic` source and its Web Audio graph (`monitorChains`, `buildBands`). The default has a counterpart for each feature (`openLiveStream` shared by `hostToMic`, scope.html:25165; the host's `setMonitor`, :15022; `makeHostBandLanes`, :15346), but different evidence.

| Check | Kind | Why | Batch 6 (14 Nov) |
|---|---|---|---|
| two simultaneous opens make one call (:65) | page | `openLiveStream` called directly; the default uses the same function, so this moves to default trivially | moved: openLiveStream is hostToMic's on the site; +1 null (two opens apart counted as two) |
| and both get the same stream (:67) | page | as above | moved |
| voice-call processing is refused (:69) | page | getUserMedia constraints; same function on default | moved |
| the failure is not kept (:95) | page | `liveStreams` cache; trivially to default | moved |
| and the retry really asks again (:96) | page | as above | moved |
| still live while one holder remains (:112) | page | hold count on `liveStreams`; trivially to default | moved |
| stopped once the last lets go (:113) | page | as above | moved |
| and the cache is empty again (:114) | page | as above | moved |
| the shape switch is reachable once Mic is chosen (:133) | page | face: `#micBands` visible after a click; trivially to default | moved |
| a live input opened (:150) | page | `state.source.kind === "mic"`; on default it is `host` with `drawsInput`, so it becomes a click plus that read | rewritten: the source stays the instrument's, told `srcMic` and handed the stream (toMic, batch 1); +1 null, before the press |
| four band lanes (:151) | page | page source's lanes; default has `makeHostBandLanes` | rewritten: the face's four lanes, and the instrument told `srcBands` |
| named as bands (:153) | page | lane names; same on default from BANDS | moved |
| NOTHING reaches the speakers (:155) | page | patches `AudioNode.prototype.connect` on the page's graph; on default the worklet is the speakers' path, so it needs rewriting, not porting | rewritten: the level in front of the one monitor chain, read shut for a second; on the site the chain is always connected, so "no connection to the destination" could not fail or pass for the right reason. Its null is the line input's level opening (:283) |
| the head says so (:158) | page | `el.credit` text | moved |
| and says it is not monitored (:159) | page | `source.describe()` | rewritten: the monitor box unavailable over the split; the instrument's credit does not say "not monitored" (after-stage-5.md) |
| the panel shows the live rows (:164) | page | face rows hidden flags; trivially to default | moved |
| mute still moves the lane gains (:171) | page | page lane `gain.gain.value`; default sends `laneMix` to the instrument instead | rewritten: the mixer's gains reach the instrument as one `laneMix` message, the muted band at nought; +1 null (unmuted, all ones). What the instrument does with them is pieces/live.py's (the heard pair the bands summed at the gains, with its null) |
| audio arrives at every band (:196) | numbers | band RMS of the split signal; becomes an offline render of the core's split (needs an input signal in the render) | rewritten: the instrument's own four lanes of the fake microphone, read on a click of it (every 100 ms for up to 20 s); +1 null, the track silenced. The split's arithmetic to pieces/live.py (a saw through the instrument, with no input as its null) |
| and the bands are not all the same signal (:197) | numbers | as above | rewritten, as (196); and to pieces/live.py |
| switching to whole gives an ordinary mic (:216) | page | `setMicShape` on the page source | rewritten: Whole pressed (setMicShape rebuilt the page's own source); the instrument drawing the input whole, told `srcBands` 0 |
| and back to four bands (:219) | page | as above | rewritten: Bands pressed, the instrument told `srcBands` 1 |
| without asking for the microphone again (:220) | page | getUserMedia count; holds on default too | moved |
| a live input opens as a microphone and is not monitored (:246) | page | `state.liveKind`, `monitorChains.size` | rewritten: the level read shut, not the page's monitorChains |
| and the toggle is unavailable rather than inert (:249) | page | `el.monitorLive.disabled`; face | moved |
| asking for it anyway does nothing at all (:259) | page | `setMonitor` forced past the UI; default has the host's `setMonitor` | rewritten: the level read shut after the forcing |
| a line input can be heard when its toggle is on (:283) | page | `monitorChains` size | rewritten: Line pressed and the box ticked; the level opens to one. Seen red with the box ticked without its event |
| and the last thing before the speakers is the clamp (:286) | page | page graph's last node is a WaveShaperNode; page-only evidence, needs a new form on default | rewritten: the hook installed before the page (INIT), since the instrument's chain is built at boot; every node handed to the speakers the clamp; +1 null, a GainNode connected to the speakers |
| the credit line says it is monitored (:288) | page | `describe()` text | rewritten: the face's own words for what the effects act on (`fxWhereText`), the credit no longer saying it; +1 null, the words before the toggle |
| and the latency is stated rather than left to be discovered (:291) | page | `el.monitorLatency` text | moved |
| calling it a microphone again takes it off the speakers at once (:305) | page | `setLiveKind` and the source's flags | rewritten: Mic pressed; the level read shut |
| and the clamp is unhooked rather than left dangling (:308) | page | disconnect count on the page graph; goes | gone: counted the page's chain disconnected; the site's chain is never unhooked, and the shut level (305) is what takes the input off |
| and calling it a line input again does not resume it (:320) | page | `state.monitorLive`; face rule | moved: Line pressed again; the level read too |
| splitting into bands takes the monitoring with it (:336) | page | page source plus `monitorChains` | rewritten, half: the split shuts the level (+1 null, open before it). The other half - the wish dropped and the box unavailable - fails on the site: the wish survives the split and the input made whole is monitored again unasked. A site defect (after-stage-5.md) |
| every Live preset keeps the live input (:364) | page | `loadCorpus` then `state.source.kind` and lanes; on default it reads `drawsInput` and bands | rewritten: the face's source still the instrument drawing the input in four lanes, and the instrument's own four lanes still carrying a click after the loads; +1 null, the same rule over the tone |
| and each one actually loads (:366) | page | `state.display`; trivially to default | moved |
| a preset can choose which bands are the two axes (:375) | page | `state.xyPair`, the menus; trivially to default | moved |
| each probe is loudest in the band that owns it (:408) | numbers | filter response, but built afresh from the `BANDS` constants in an OfflineAudioContext and never read from the running app; becomes the core's crossovers' response offline | to pieces: pieces/live.py, a probe sine through the instrument's split, each band's lane; null, the lanes read in reverse |
| and at least 20 dB down two bands away (:409) | numbers | as above | to pieces: pieces/live.py; null, each owner within a decibel |
| every crossover is -3.01 dB at its corner (:433) | numbers | as above (core `kButterworthQDb`, capture.h:45) | to pieces: pieces/live.py, each corner through both of its band's stages; null, a tenth past the corner |
| no page errors (:437) | page | page health | moved |

### looptest.py - wholly on ?brain=js (two pages: `?brain=js` :58, and `?brain=js&core=js` :502 for the Scan runs) - 30/30
Docstring note (:31): it "reads the page's own brain - its generator's routes and worklet". The comment at :496 says the Scan runs need `core=js` because "the run reads the tables that brain sends, which the site's instrument reads inside its worklet and never hands out". So the `core=js` page is there to reach page data, not to compare engines. Several checks force a source by hand (`MOD_SOURCES.get(id).value = () => 1`), which an offline render can only do if the core gets a hook for it.

| Check | Kind | Why | Batch 3 (13 Nov) | Batch 5 (13 Nov) |
|---|---|---|---|---|
| three picture sources at full move a destination by the loop's total, not three times it (:92) | numbers | `state.rotateMod` after `applyModMatrix` with sources forced to 1; the core matrix's loop total, given a source-override hook | to pieces (loop.py, matrix_cpp) | - |
| and a source that is not the loop is not caught in the loop's bound (:94) | numbers | as above, with a registered test source | to pieces | - |
| the loop's routes into a generator parameter cross into the audio loop as one (:147) | page | counts `genRoutes` with `loopTotal`, the page brain's hand-over to its engine; goes, since :150 carries the claim | rewritten, to pieces: the core's matrix hands one route, the loop's (`lroutes`) | - |
| carrying the bounded total (:149) | page | `route.source.value()` of the page's combined route; goes | rewritten, to pieces | - |
| and the generator plays the bounded pitch, not three sources' worth (:150) | numbers | DFT energy at 220·2^0.5 vs 2^1.5 in the samples; offline render | to pieces (generator_cpp) | - |
| two on amplitude at full ask for no duck, through the combined route (:186) | page | `genRoutes` held value; goes | rewritten, to pieces | - |
| and at nought they duck, by no more than the loop's total (:188) | page | as above | rewritten, to pieces | - |
| and the generator is quieter at nought than at full (:190) | numbers | RMS of samples; offline render | to pieces | - |
| boredom rises while the picture is stuck (:227) | numbers | `picture.bored` over 10 s; the core's picture reads, rendered offline | to pieces (picture_cpp, a stuck figure then a moving one) | - |
| no faster than a quarter a second - it cannot slam (:234) | numbers | slope of `picture.raw.bored` | to pieces | - |
| and never past one (:236) | numbers | peak of `picture.bored` | to pieces | - |
| routed at full it moves a destination by its own reach, lower than the photocell's (:237) | numbers | `state.rotateMod / picture.bored` | to pieces (`reach=bored`) | - |
| and it drains when the picture moves again (:239) | numbers | `picture.bored` after 5 s of a moving fifth | to pieces | - |
| the photocell moves the pitch you hear, through the worklet (:276) | numbers | DFT of the monitor chain with `photo.1` forced to 0.6; offline render with a source override | to pieces | - |
| a picture held under ten decibels of limiting is running away, and the same picture unlimited is not (:310) | numbers | `makePictureMeter()` fed a fixed grid; the core meter, offline with no render needed |  | to pieces (loop.py: picture_cpp's meter fed looptest's sparse picture under `mlimit -10`); null at -2 dB |
| and the page reads a hot chain's limiter pulling it down (:313) | page | `monitorLimiting()` reads the page's Web Audio limiter in `monitorChains` (scope.html:18027); on default the limiter is the core's |  | moved to the default: the face's chain carrying the instrument's sound, fed twelve times full scale (-23 dB read); null a quiet chain |
| from %s, nothing goes NaN or infinite (:523) x7 seeds | numbers | `state.resMod/rotateMod/zoomMod`, `phosphor.grid`, `picture.raw`; offline, if the render exposes them |  | to pieces (loop.py: render_cpp, 30 s of audio a seed, read every 0.1 s of it); null a reading gone NaN |
| from %s, what reaches the speakers never passes full scale (:524) x7 | numbers | analyser after the page chain's clamp; becomes the core's output peak |  | rewritten: the clamp is the face's, held on the default page (0.96 after the clamp; null 1.12 before it); the instrument's heard peak is reported, 0.94 to 3.24 - it has no limiter (after-stage-5.md) |
| from %s, and the speakers did hear it (:530) x7 | numbers | as above |  | to pieces, as "the instrument was heard"; null the silence never brought up |
| from %s, every destination stays inside the loop's total (:531) x7 | numbers | the mods and `genRoutes` loop totals |  | to pieces; null an oscillator at full on the rotation beside the loop (1.498) |
| from %s, and the grid stays inside the phosphor's range (:534) x7 | numbers | `phosphor.grid` max |  | to pieces; null a grid past one |
| from %s, running away holds the stage's push down, to a quarter at most, and nothing else holds it (:547) x7 | numbers | `pictureMeter.verdict()` count and `pictureStage.hold` |  | to pieces; nulls each run's verdicts with another's hold; strengthened (a mutation): a screen kept full is called running away |
| from %s, and the loop was really running - it moved what it drives, the stage's fold too (:571) x7 | numbers | ranges of resMod, the pitch total, `FOLD_SLOT` total |  | to pieces; null nothing routed and no Picture; every seed passed without the "saturated" exemption (fold 0.30 to 0.50) |
| and the reverb really was in the loop: the generator held Mix, Spread and Size at full to the end (:581) x1 | numbers | `genSettings().reverb*`; the core's generator settings in the render |  | to pieces (`settings`); null the plain run's |
| with Scan at its top, its wave was still moving: the table changed by a median of over 0.02 a tenth of a second (:590) x3 | numbers | `genSettings().scanTable`, which only the JS generator hands out; the core must export its table to the render |  | to pieces (`table`): medians 0.082, 0.335, 0.100 against the page's 0.043 to 0.098; null Scan at a depth of one (0.0008) |
| crossed, the run really had two pictures: the layers drew a figure each throughout (:599) x1 | numbers | `layerPictures.live` |  | to pieces; null the unsplit struck run (0 of 300) |
| and B's wave was moving as well as A's (:601) x1 | numbers | `genSettings(1).scanTable` |  | to pieces; null the unsplit run's B |
| and both depths were held by the lower of the two pictures' holds, never less (:602) x1 | numbers | `scanHold` against `layerPictures.stages[].hold` |  | to pieces (`scan`, `stage`); null against the silence's stage |
| and Scan's depth was held by the stage's own hold, never less (:606) x2 | numbers | `scanHold` against `pictureStage.hold` |  | to pieces; null against the silence's stage |
| no page errors (:610) | page | page health |  | stays, on the default page |

### menvtest.py - 1 leg on ?brain=js beside the default - 1/23
Comment at :153: "On the page's own brain the keyboard is the page's, and a key gone down reaches the audio thread only as the source's own message ... Both, because a message left out on one path passes the other."

| Check | Kind | Why | Batch 4 (13 Nov) |
|---|---|---|---|
| and on the page's own brain, sounding, the same: restarted on Every note, not on Phrase, not on a lift (:170) | page | the page keyboard's message to its own worklet, a path only the page's brain has; goes, and the default leg's :148 and :151 keep the claim | gone; :148 and :151 hold it on the instrument |

### miditest.py - wholly on ?brain=js - 50/50
Docstring note (:13): it "reads the page's own brain - its keyboard's flags, set directly". The parsing and panic checks read `midi.notes`. The default page keeps that stack as well: `midiBytes` runs `midiBytesHere` before forwarding to the core (scope.html:9697). So those checks move by dropping `&brain=js`, though they then test the face's copy, not the core's keyboard.

| Check | Kind | Why | Batch 4 (13 Nov) |
|---|---|---|---|
| a routing from the keyboard made before it was plugged in is heard once it is, and not before (:104) | page | `stepRoutes()` and `genRoutes` of the page brain; goes, or becomes a core render with a `midi.key` routing | gone: the page registers Key when a port opens; the core's matrix has it from the start, so the site has no "before" |
| a port is opened and its messages are listened to (:109) | page | `midi.status`, stub port; trivially to default | moved |
| and it is named in the panel (:111) | page | `midi.ports`; trivially to default | moved |
| a note-on holds the note (:116) | page | `midi.notes`; trivially to default | moved, reading the face's stack (said at the site); the core's parse is in pieces |
| a note-on at velocity zero is a note-off (:118) | page | as above | moved, reading the face's stack (said at the site); the core's parse is in pieces |
| running status: one status byte, three notes (:121) | page | as above | moved, reading the face's stack (said at the site); the core's parse is in pieces |
| and again on the way out (:125) | page | as above | moved, reading the face's stack (said at the site); the core's parse is in pieces |
| the same note twice does not stack twice (:129) | page | as above | moved, reading the face's stack (said at the site); the core's parse is in pieces |
| so one release ends it (:131) | page | as above | moved, reading the face's stack (said at the site); the core's parse is in pieces |
| a clock byte is not mistaken for a note (:135) | page | as above | moved, reading the face's stack (said at the site); the core's parse is in pieces |
| losing the window releases everything (:139) | page | blur panic on `midi.notes`; trivially to default | moved; and new: the instrument hears the panic (silent after, sounding before as its null) |
| and so does being hidden without losing it (:147) | page | visibilitychange panic; trivially to default | moved |
| all-notes-off releases them and does not learn as a controller (:155) | page | `midi.notes`, `MOD_SOURCES` | moved |
| nothing held is a closed gate (:167) | page | `midi.key`, the page's gate flag | moved (the face's gate flag) |
| one note is a unison at its own pitch (:171) | numbers | `state.source.settings.freq/interval/octaves`; core keyboard plus generator, MIDI in and pitch out | to pieces (instrument_cpp `tone`) |
| two notes are the lower pitch and the interval above it (:180) | numbers | as above | to pieces (instrument_cpp `tone`) |
| and the press order does not turn the figure over (:182) | numbers | as above | to pieces (instrument_cpp `tone`) |
| the interval menu says what is being played (:185) | page | `el.interval.value`, face | moved, by clicks, null on one note |
| a third note displaces the older of the pair (:190) | numbers | dyad settings | to pieces (instrument_cpp `tone`) |
| releasing one of the pair promotes what was under it (:195) | numbers | as above | to pieces (instrument_cpp `tone`) |
| back to one note is back to a unison (:201) | numbers | as above | to pieces (instrument_cpp `tone`) |
| with Hold on the interval stays above the one note (:210) | numbers | as above, with `midi.hold` set directly | to pieces (instrument_cpp `tone`) |
| and walks with it (:212) | numbers | as above | to pieces (instrument_cpp `tone`) |
| nineteen semitones is a fifth plus an octave (:219) | numbers | settings.interval/octaves | to pieces (instrument_cpp `tone`) |
| and the credit line says so (:221) | page | `el.credit` text | moved (the face's credit line), null on a fifth |
| a wide dyad is 3:1 in just tuning (:232) | numbers | `intervalRatio()`, a pure page function; becomes the core's tuning ratio (borderline: arithmetic rather than a render) | to pieces (functions_cpp `intervalRatio` over the instrument's interval and octaves) |
| and 2^(19/12) in equal (:234) | numbers | as above | to pieces (functions_cpp `intervalRatio` over the instrument's interval and octaves) |
| a played fifth is exactly 3:2 in just tuning (:249) | numbers | as above | to pieces (functions_cpp `intervalRatio` over the instrument's interval and octaves) |
| and the tempered ratio in equal (:251) | numbers | as above | to pieces (functions_cpp `intervalRatio` over the instrument's interval and octaves) |
| and the note is in the samples, not only in the state (:263) | numbers | `estimateFrequency` on samples; offline render | to pieces (the heard pair's pitch by zero crossings) |
| in equal the samples carry the tempered ratio (:290) | numbers | samples | to pieces (the heard pair's pitch by zero crossings) |
| and the figure turns at the rate a tempered fifth beats at (:293) | numbers | samples | to pieces (the heard pair's pitch by zero crossings) |
| in just it is 3:2 and stands still (:296) | numbers | samples | to pieces (the heard pair's pitch by zero crossings) |
| mono takes the newest note as the pitch (:309) | numbers | settings.freq | to pieces (instrument_cpp `tone`) |
| and leaves the interval to the menu (:311) | numbers | settings.interval | to pieces (instrument_cpp `tone`) |
| and does not inherit the dyad's octaves (:324) | numbers | settings.octaves | to pieces (instrument_cpp `tone`) |
| controllers moved are learned as nothing, and the cards are still the four (:353) | page | `MOD_SOURCES` keys and `.mod-card`; face | moved; its null a source put in the registry by hand |
| null: the wheel still sets the vibrato (:355) | numbers | `genSettings().vibrato` after CC1; the core keyboard's wheel | to pieces (midi.py: the wheel on the instrument; null CC16 sets nothing) |
| an old code's controller routing and names are dropped, and an oscillator's kept (:368) | page | `restore(decodeSetup())` then `state.modRoutings`; trivially to default (decodeSetup is the core's codec there) | moved |
| with a note held the lag is a quarter period of the note, exactly (:390) | numbers | `lagLockUpdate()`, `lagLock`; the core has the lag lock (capture.h:166, instrument.h:464) | to pieces (the instrument's lag lock; each the other's null) |
| and without it the estimator is back, on the signal that is there (:402) | numbers | as above | to pieces (as :390) |
| the timebase follows the note, four periods across (:418) | page | `midiFollowTimebase()`, `state.timebase`: scope display, not in the core | moved |
| and the slider says what the screen is doing (:422) | page | `el.timebase.value` | moved |
| the tuner has a played note to read against, and it is the note (:439) | page | `midiPitch()`, `midiPitchHz()` | moved |
| every keyboard setting comes back, and a code carries no drive or play (:455) | page | snapshot/restore of `midi.*`; trivially to default | moved |
| and the panel says so (:458) | page | `aria-checked` | moved |
| a setup written before the keyboard existed restores the defaults (:464) | page | `restore({})`; trivially to default | moved |
| Velocity reads Level and strike on the base, and FM on a preset that routes velocity to FM (:495) | page | face menu over routings; trivially to default | moved |
| choosing FM adds velocity's routing onto the FM depth beside what is there, and Level and strike takes ... (:497) | page | as above | moved |
| no page errors (:506) | page | page health | moved |

### modrowtest.py - 1 leg on ?brain=js beside the default - 3/46
Docstring note: the Envelope's dot is to hold "over a note held and let go, on both brains". The `js` page (:582) runs the same TRACE as the default, inside a `for label, page` loop (:585).

| Check | Kind | Why | Batch 4 (13 Nov) |
|---|---|---|---|
| on %s in %s, %s: over a note held and let go the dot goes attack, decay, sustain, release, only forward... (:593) x4 on the js page (2 modes × 2 envelopes) | page | the card's `_drawn` dot reading the page brain's envelope stage; goes, the default leg keeps it | gone; the default leg holds it |
| on %s, over notes in a row in Poly, the dot goes back only into a new note's attack, and stays on the curve (:598) | page | as above | gone; the default leg holds it |
| and its height is the source's level, what a routing from it is given (:602) | page | `MOD_SOURCES.get('env.note').value()` against the drawn dot; as above | gone; the default leg holds it |

### modtest.py - wholly on ?brain=js - 31/31
Docstring note (:7): it "reads the page's own brain - its oscillators' shape and rate, set directly". Most of the suite is the setup codec and restore on the face. On default those already run through the core's codec, since `decodeSetup` is the compiled one there.

| Check | Kind | Why | Batch 3 (13 Nov) | Batch 6 (14 Nov) |
|---|---|---|---|---|
| every preset migrates to the same destination (:75) | page | `loadCorpus`/`applyPreset` then `state.modRoutings`; trivially to default |  | moved |
| and the depth comes across with it (:86) | page | as above |  | moved |
| one octave down is reached (:130) | numbers | `estimateFrequency` over an LFO sweep on gen.freq (already sends `hostSendSetup`); offline render |  | rewritten: LFO 1's shape and Rate set in its card's editor, which the instrument hears (the rate was written into the page's lfos and a setup sent); the slider moved again once heldTone's note has landed (heldTone's slider races the note-on on the site, README). And to pieces/mod.py: the instrument rendered, A4 in Mono swept 220.5 to 877.5 Hz, and in Poly; null, half the depth |
| one octave up is reached (:131) | numbers | as above |  | as (130) |
| contributions add (:157) | numbers | the claim is the matrix sum, but the evidence is the test summing `genRoutes` itself with `lfos[].value` set by hand; has to be rewritten as a render of two still LFOs, not ported | to pieces (mod.py: two held sources, the generator's pitch) |  |
| an unknown destination is skipped (:170) | page | `genRoutes.length` after `compileRoutes()`, page brain; goes, or becomes a core matrix check |  | to pieces: pieces/mod.py, the core's matrix loading routings to nothing; null, three that exist |
| but not deleted from the setup (:171) | page | `state.modRoutings.length`; face, trivially to default |  | rewritten: the face keeps all three, and the setup it sends carries them |
| nothing changes through encode and decode (:190) | page | snapshot, encode, decode, restore; trivially to default |  | moved |
| the routings survive as text (:191) | page | as above |  | moved |
| and the code carries the current version (:196) | page | as above |  | moved |
| still loads, and points where it said (:210) | page | legacy decode plus restore; trivially to default |  | moved |
| a version-4 code loads without the routes from the threshold or to the pluck, and saves without them (:233) | page | decode passes; trivially to default |  | moved |
| and the same code marked version 5 keeps them, so the pass is what took them out (:236) | page | as above |  | moved |
| a version-9 code with a drawing loads as the waveform, its shape kept, the drawings' fields gone, and ... (:273) | page | `decodeSetupHere`, the page's own fallback codec, deleted in step 6; the same claim on `decodeSetup` is what stays |  | rewritten: the site's codec (decodeSetup, the compiled core's), not the page's fallback step 6 deletes |
| and one that names no kind at all is given the waveform (:276) | page | as above |  | rewritten, as (273) |
| and the same code marked version 10 keeps everything, so the pass is what took it (:277) | page | as above |  | rewritten, as (273) |
| and the site's codec, the compiled core's, reads all three as the page's does (:281) | engines compared | `decodeSetup` (compiled) against `decodeSetupHere` (JS); goes |  | gone: it compared the two codecs |
| adding a destination makes the routing (:304) | page | the card editor's DOM; trivially to default |  | moved |
| its depth slider sets its amount (:305) | page | as above |  | moved |
| and its cross removes it (:306) | page | as above |  | moved |
| a rotation really turns the figure (:356) | numbers | principal axis of `capture()` lanes at rotate 0 vs 0.125; core capture/plane offline | to pieces (capture_cpp `dump`, a diagonal line) |  |
| with nothing routed every offset is zero (:376) | numbers | `applyModMatrix` offsets; core matrix | to pieces (matrix_cpp `screen`) |  |
| and a source cannot push past the range (:378) | numbers | as above, with `lfos[0].value = 1` set by hand | to pieces |  |
| it rises with the signal (:401) | page | `envLive / ENV_FULL`, the output meter's follower as `paintStage` takes it; a face reading, which on default should read the instrument's level |  | moved |
| and falls when it stops (:402) | page | as above |  | moved |
| but releases slower than it attacks (:403) | page | as above |  | moved |
| 2 Hz is 2 Hz on the tone source (:429) | numbers | `lfos[0].phase` wraps against elapsed time; the core LFO's rate in a render |  | rewritten: LFO 1's Rate slider at 2 Hz, the phase read the instrument's (absorb writes it); +1 check that the page's rate written by hand moves nothing, +1 null, the slider at 4 Hz. And to pieces/mod.py: the oscillator's value every 10 ms, six cycles in three seconds on sin(2 pi 2 t) to 2e-11; null, 4 Hz |
| and 2 Hz on the microphone, not 4 (:436) | page | the per-sample and per-frame double-stepping trap exists only on the page brain (`toMic`); goes |  | rewritten: Mic pressed, the instrument drawing the input (toMic was the page's own microphone); and to pieces/mod.py, with an input drawn |
| every destination's own control drives something (:505) | page | slider moves change `state`/`state.source.settings`; face, becomes a snapshot diff on default |  | moved; +1 check: each control tells the instrument, by its own id |
| and enough of them were reachable to mean it (:507) | page | as above |  | moved |
| no page errors (:510) | page | page health |  | moved |

### morphtest.py - wholly on ?brain=js - 22/22
Docstring note (:23): it "reads the page's own brain - genSet called directly, and its generator's samples". This is the waveform morph, not the setup morph. Its numbers come from `waveAt` and `makeGeneratorCore`, the JavaScript engine called directly.

| Check | Kind | Why | Batch 4 (13 Nov) |
|---|---|---|---|
| at 0, 1, 2 and 3 the morph is the sine, the triangle, the saw and the square, exactly (:107) | numbers | `waveAt()` per sample; core wave offline | to pieces (morph.py, functions_cpp `waveAt`) |
| a thousandth of a station moves no sample by more than two thousandths (:126) | numbers | as above | to pieces |
| it never falls below the saw's own, 0.64 of the sine's - the lowest station (:137) | numbers | `makeGeneratorCore` block spectrum; core render | to pieces (generator_cpp) |
| and between the triangle and the saw it goes smoothly from one to the other (:139) | numbers | as above | to pieces |
| half-way between each pair, at 4 kHz, nothing folds back above -45 dB (:156) | numbers | alias floor; core render | to pieces |
| and with an oscillator sweeping it end to end, still nothing above -45 dB (:165) | numbers | as above, with an LFO route on MORPH_SLOT | to pieces: an LFO 1 route on the morph slot |
| the Morph row is on Play only with Morph chosen (:194) | page | face row hidden; trivially to default | moved |
| it starts half-way from the triangle to the saw, and says where it is (:196) | page | `el.morphValue` text plus `genSettings().morph`; to default via the snapshot | rewritten: snapshot |
| and every reading fits beside the slider, in a Bench column (:200) | page | layout; trivially to default | moved |
| a controller on Morph moves the sound: a sine with none of the saw's second harmonic (:236) | numbers | spectrum of `getLatestWindow` with a `midi.key` route; core render | to pieces (instrument_cpp) |
| and at full, a station and a half on, exactly the half-saw's %.1f dB (:238) | numbers | as above | to pieces, restated: the same as Morph at 1.5 in the setup, within 0.3 dB; the bare half-saw held separately |
| without writing the slider's own position (:240) | page | `genSettings().morph` after modulation; becomes the snapshot on default | rewritten: slider and code, with a null that the routing was there |
| full depth is a station and a half, stopped at both ends (:242) | page | `MOD_DESTS.get('gen.morph').reach()`, the face's reach; trivially to default | moved |
| editing B writes B's position and leaves A's (:267) | page | hands editing; `genSettings(0/1)`, to default via snapshot `morph`/`bMorph` | rewritten: the Poly and Dyad buttons, snapshot `morph`/`bMorph` |
| and back on A the slider is A's, with the code carrying both (:269) | page | slider plus snapshot; trivially to default | rewritten: as :267 |
| and B sounds its own: A's square has its third harmonic at -9.5 dB, B's sine none (:292) | numbers | two-layer `makeGeneratorCore` block; core render | to pieces |
| a code's position reaches the slider and the generator, and B takes A's when it has none (:312) | page | restore, then `genSettings` and slider; to default via snapshot or core | rewritten: snapshot and slider; B taking A's is parity's restore section |
| and B its own when it has one (:314) | page | as above | rewritten: as :312 |
| a code from before the morph loads with the default (:316) | page | as above | rewritten: as :312 |
| a generator built later, from the panel, takes the slider's position on both layers (:328) | page | `toTone()`/`generatorFromPanel`, page brain only; goes | gone: `toTone()` building a generator from the panel is the page's brain only |
| timbre finds it (:337) | page | bench search; trivially to default | moved |
| no page errors (:339) | page | page health | moved |

### onsettest.py - wholly on ?brain=js - 12/12
Docstring note (:20): it "reads the page's own brain - its sources' functions, bound directly". It registers stand-in event destinations on the page, because nothing struck exists since G2.

| Check | Kind | Why | Batch 4 (13 Nov) |
|---|---|---|---|
| the page itself has no event destination left (G2 took Swing again and Kick) (:84) | page | page `MOD_DESTS` registry | moved |
| an onset reaches only what is struck, and only events reach that (:100) | page | `routingAllowed` over page registry with stand-ins; the core matrix's event rule would need a test destination | moved, with the Mic pressed |
| and dropping an event on a value, or a value on an event, makes no routing (:103) | page | `addRouting` on the face | moved, with the Mic pressed and a new null |
| one attack is one onset however long it is held, and a release is none (:149) | numbers | `hear.onset` count on a fake mic; core `Hearing::onsetStep` (hearing.h:347) offline | to pieces (onset.py, hearing_cpp) |
| eight strikes are eight onsets, the click of each cut-off not counted (:151) | numbers | as above | to pieces (onset.py, hearing_cpp) |
| and a flux held high through a 400 ms swell is one onset, and fires again once it has fallen (:154) | numbers | drives `hearing.fluxRaw` and `onsetStep` by hand; the core function directly is a cleaner test | to pieces (onset.py, hearing_cpp) |
| and a flux flickering every millisecond fires no faster than the 80 ms gap allows (:156) | numbers | as above (`kOnsetGap`) | to pieces (onset.py, hearing_cpp) |
| a routing does not fire when it is made, only on a count it has not seen (:184) | page | `fireEvents` with a stand-in source and destinations registered on the page; no real destination exists anywhere | to pieces (matrix_cpp event destinations and counts) |
| then a new count strikes each destination once, at its depth (:186) | page | as above | to pieces (matrix_cpp event destinations and counts) |
| and three counts in one frame are one strike, not three (:188) | page | as above | to pieces (matrix_cpp event destinations and counts) |
| and an onset hearing the generator it would strike is refused (:189) | page | `routingAllowed` on the page registry | to pieces (matrix_cpp event destinations and counts) |
| no page errors (:193) | page | page health | moved |

### overlaytest.py - 1 leg on ?brain=js beside the default - 21/27
Docstring note (:29): it runs "On the site's instrument ... and on the page's own brain". The whole body from :112 to :298 runs once per label (:107). The phone-width section (:301 to :321) is on the default only. The page-brain leg also has 7 `null()` sites (:124, :149, :163, :203, :212, :244, :287), not counted as rows here.

| Check | Kind | Why | Batch 1 (13 Nov) |
|---|---|---|---|
| off by default: hidden, the button not pressed, nothing drawn (:114) | page | `loopOverlay` face state; leg goes (default leg holds it) | gone: the default pass holds the same claim |
| the Loop button shows it (:120) | page | as above | gone: the default pass holds the same claim |
| and it is not in the setup code (:122) | page | snapshot/encode; as above | gone: the default pass holds the same claim |
| a ring is drawn for layer A on its own picture (:132) | page | `loopOverlay.drawn` against `loopView()`, which on this leg is the page brain's reader | gone: the default pass holds the same claim |
| drawn at the reader's own circle, to a hundredth of a pixel (:135) | page | as above | gone: the default pass holds the same claim |
| and that circle follows the figure: its centre within a fifth of the ring's radius of the figure's centre ... (:145) | page | `scanGeometry(pictureEngine.cells)` against the path; leg goes | gone: the default pass holds the same claim |
| the head is drawn on the ring at its phase (:158) | page | drawn head against the ring | gone: the default pass holds the same claim |
| at 240 Hz, four times the tick, the head stands still (:160) | page | `loopView().heads` over time; the numbers it rests on (Scan's head) are the core's on the default leg | gone: the default pass holds the same claim |
| the thumbnail is the newest table, point for point (:201) | page | the tone branch (:167) reads `scan.tables`, page-brain only; goes | gone: the default pass holds the same claim |
| with Scan alone closing the loop, the badge is the meter's verdict (:210) | page | badge against `pictureMeter.verdict()` | gone: the default pass holds the same claim |
| with the stage up, the badge is the readout's word (:224) | page | badge against the readout text | gone: the default pass holds the same claim |
| drawn a hundred times, the phosphor Scan reads is the same to the bit (:243) | page | `pictureEngine.cells` unchanged by `drawLoopOverlay` | gone: the default pass holds the same claim |
| and the overlay calls nothing that reaches the sound (no genSet, scope call or post) (:246) | page | source text of `drawLoopOverlay`; brain-independent, the default leg already proves it | gone: the default pass holds the same claim |
| in Y-T, no ring, but the table and the badge (:252) | page | face | gone: the default pass holds the same claim |
| on the spectrogram, nothing (:256) | page | face | gone: the default pass holds the same claim |
| split, each layer's ring on its own picture (:285) | page | rings against layers | gone: the default pass holds the same claim |
| crossed, each on the other's (:286) | page | as above | gone: the default pass holds the same claim |
| and both layers have a read-head (:288) | page | `loopView().heads` | gone: the default pass holds the same claim |
| reloaded, still on: a view this viewer chose (:293) | page | browser storage; brain-independent | gone: the default pass holds the same claim |
| and off once turned off (:297) | page | as above | gone: the default pass holds the same claim |
| no page errors (:298) | page | page health | gone: the default pass holds the same claim |

### performtest.py - wholly on ?brain=js - 12/12
Docstring note (:27): it "reads the page's own brain - its voices and routes, read directly". The first three checks read only the corpus data and touch no brain at all.

| Check | Kind | Why | Batch 4 (13 Nov) | Batch 5 (13 Nov) |
|---|---|---|---|---|
| the sections for playing, each with a routing a hand moves in every preset (:96) | page | reads `CORPUS` and `decodeRoutings` only; could run with no browser, or trivially on default | moved | - |
| and every preset in Split is a split, and every one in Layer a layer (:99) | page | as above | moved | - |
| and a section of effects for live inputs, landing on whatever is playing (:100) | page | as above | moved | - |
| every routing in them reaches the generator, is still at rest, and moves when played (:166) | numbers | `MOD_SOURCES` values at rest and under a chord, plus `genRoutes` compiled; offline render with the core's source readings out | to pieces (perform.py, instrument_cpp `routed` and `tone`, 70 corpus presets) | - |
| and those whose every routing came from a cut source load with none (:168) | page | `state.modRoutings` after `loadCorpus`; trivially to default | to pieces (perform.py, instrument_cpp `routed` and `tone`, 70 corpus presets) | - |
| and the null: a source spelt wrong is caught by the same measurement (:179) | numbers | the null of :166, same measurement | to pieces (perform.py, instrument_cpp `routed` and `tone`, 70 corpus presets) | - |
| each split and layer sounds both layers from one chord across the keyboard (:185) | numbers | `midi.poly.layers[].sounding`, the page keyboard's voices; the core keyboard's layers in a render | to pieces (perform.py, instrument_cpp `routed` and `tone`, 70 corpus presets) | - |
| every live-effects preset puts the effects insert in a microphone's path, and says so (:231) | page | `state.source.fx.active` on the page's mic source and `el.planeWhere`; on default it becomes a click on the instrument's live input | left on ?brain=js: the microphone through the page's insert; needs input samples | to pieces (perform.py `microphone`: render_cpp, each held 10.5 s, drawn against the input); null the plain preset to the bit |
| and the two whose only effect was cut leave the input alone (:235) | page | as above | left on ?brain=js: the microphone through the page's insert; needs input samples | to pieces; null a preset with an effect |
| the octave-up folds the input's troughs up (:241) | numbers | min of the processed mic samples; offline render with an input | left on ?brain=js: the microphone through the page's insert; needs input samples | to pieces; null the plain input's troughs |
| every Listening preset routes a source that hears, and on a microphone it is live and no loop (:265) | page | registry facts (`family`, `fromPicture`) and `genRoutes`; the hearing family is parked | left on ?brain=js: the microphone through the page's insert; needs input samples | to pieces (`loopof`); null the same on the generator, the loop's |
| no page errors (:268) | page | page health | moved | the ?brain=js page's goes; the default's stays |

### phototest.py - 1 leg on ?brain=js beside the default (the first 30 checks; the same page is re-opened on the default at :501 for the last 7) - 30/37
Docstring note (:20): it "reads the page's own brain - genSet called directly". The `genSet` calls drive the figure under each check.

| Check | Kind | Why | Batch 3 (13 Nov) | Batch 6 (14 Nov) |
|---|---|---|---|---|
| in Y-T every lit cell is on the trace and every inked cell is lit (:103) | page | `phosphor.grid` against canvas pixels: the face's agreement; to default |  | moved: the figure by the Level, Interval, Shape and Persistence controls and the display's buttons (genSet and state.persistence by hand); the face's grid against its screen |
| and in X-Y, on a figure that is not its own transpose (:110) | page | as above |  | moved, as (103); +1 fixture check, the X-Y figure the instrument's 2:3 and not its own transpose, with the unison's diagonal as its null (red with genSet put back, while (103) and (110) stay green) |
| the grid fades by one minus the persistence every frame (:177) | numbers | grid decay per frame; the picture engine's (the core's, as wasm) |  | to pieces: pieces/photo.py, the core's Phosphor faded ten frames, 0.88 to 1e-6; null, 0.2 |
| which is the rate the screen itself fades at (:179) | page | grid rate against canvas ink rate; face agreement |  | moved: the face's grid's rate against the screen's |
| infinite persistence keeps everything, as the screen does (:199) | numbers | grid sum kept |  | to pieces: pieces/photo.py; null, a hundredth |
| and with persistence off nothing is kept but what was just drawn (:201) | numbers | grid outside the dot |  | to pieces: pieces/photo.py; null, 0.12 |
| a cell keeps the brighter of two strokes, never their sum (:218) | numbers | `phosphorSegment` compositing; the core engine's segment offline |  | to pieces: pieces/photo.py (phosphorSegment by hand there, the core's segment here); null, one stroke at the sum |
| on the figure it reads bright (:245) | numbers | `photo.value` |  | to pieces: pieces/photo.py, the core's read on a stroke (on the site photo.value is the face's photocell, what its card shows, not the instrument's) |
| and off it, dark (:246) | numbers | as above |  | to pieces: pieces/photo.py |
| the reading moves smoothly as the reticle does - no jump at a cell edge (:247) | numbers | `phosphorRead` continuity |  | to pieces: pieces/photo.py; null, half-cell steps |
| and it is a source while it is on (:249) | page | `MOD_SOURCES.has('photo.1')` |  | moved |
| it never moves faster than two full swings a second (:283) | numbers | `photo.value` slew over time |  | to pieces: pieces/photo.py, the core's PictureSources stepped at 60 a second; null, the raw reading |
| and still gets there (:286) | numbers | as above |  | to pieces: pieces/photo.py |
| since E3, a source reading the picture may reach any destination (:302) | page | `addRouting` acceptance on the face |  | moved |
| and starts low (:306) | page | the face's starting amount |  | moved |
| an amount past the ceiling is held to it where it is used (:338) | numbers | `applyModMatrix` with `photo.value` forced; core matrix ceiling | to pieces (photo.py; held at a half, since at one the loop's total masks the reach) |  |
| and stored back within it, so the control says what applies (:341) | page | `r.amount` after `touchRoutings`; face |  | moved |
| a routing that arrives in a code past the ceiling moves its destination no further than the ceiling (:343) | numbers | `state.resMod` | to pieces |  |
| everything stays inside its range and nothing goes NaN (:371) | numbers | 4 s loop on rotate/zoom: mods, `photo.value`, grid |  | to pieces: pieces/photo.py, the instrument rendered four seconds with the photocell on its own figure, routed past the ceiling; +1 check, each frame's rotation within half the photocell's value (the mutation pass: a reach of 0.9 passed the range bound); nulls, an oscillator at full depth on the rotation |
| dragging the reticle puts it where it is dropped (:395) | page | real mouse on the reticle; trivially to default |  | moved |
| and does not also drag the trigger level under it (:397) | page | as above |  | moved |
| its arrow keys move it a cell and leave the timebase alone (:399) | page | as above |  | moved |
| over a spectrogram, which no beam draws, it is put away and reads nothing at once (:422) | page | reticle hidden plus `photo.value` zeroed on a display change; face |  | moved: the display's buttons |
| and the phosphor holds nothing there (:425) | numbers | grid sum on spect (borderline: the engine's spect rule) |  | moved: the face's grid |
| with infinite persistence the old figure stays, on the screen and the grid (:461) | page | Clear's fixture, grid and canvas |  | moved: the Level slider |
| Clear wipes both at once (:465) | page | the Clear button; to default |  | moved |
| and leaves persistence as it was set (:467) | page | as above |  | moved |
| off, it is not a source and reads nothing, and its routings wait for it (:489) | page | photo button and registry |  | moved |
| a setup code brings it back where it was (:492) | page | snapshot/restore; trivially to default |  | rewritten: the code loaded with loadCode, which sends it to the instrument (restore() alone changes the face) |
| and a code from before it existed has it off (:494) | page | `restore({})` |  | rewritten, as (492) |

### picturepresettest.py - wholly on ?brain=js - 10/10
Its comment (`:45`): on ?brain=js because it "reads the page's own brain - restore() called directly, which the page sends the instrument nothing of". In fact it also calls `loadCorpus`, `heldTone`, `landPhoto`, `movePhoto` and reads `photo.*`, `MOD_SOURCES.get(id).value()` and `pictureMeter.verdict()` - all page-brain state - over 10 s a preset, twice for each loop.

| Check | Kind | Why | Batch 4 (13 Nov) | Batch 5 (13 Nov) |
|---|---|---|---|---|
| a section of the picture playing itself, and one played with it (`:128`) | page | Counts entries in `CORPUS` on the page; pure data, no brain. Becomes a Python read of `corpus.LIBRARY` (or any page); nothing to render. | moved to a default page: data only | - |
| every preset in them turns the photocell on and routes something the picture says (`:131`) | page | `decodeRoutings` over the corpus setups plus a null on Circle; data only. Moves to Python or the default page trivially. | moved to a default page: data only | - |
| four presets use five sources or more, and two of them the picture's with at least three others (`:134`) | page | Counts distinct sources over `CORPUS` and `PRESETS`; data only, as above. | moved to a default page: data only | - |
| the library uses sources together: thirty with two or more, twelve with three or more (`:137`) | page | Same counting, with its null; data only. | moved to a default page: data only | - |
| at most two presets needed the reticle pressed onto their figure, so the stored placements are read (`:241`) | numbers | Reads `photo.raw` (the photocell's reading at the stored cell) after a load and held note; an offline render of the core's picture with the photocell gives the same number. `landPhoto` is page-side, but only the "dark" test is needed. | left: needs render_cpp | to pieces (picturepresets.py: render_cpp, the landing rule on the instrument's grid; one of twelve pressed); null the stored cells before any note |
| in every one, the picture's sources are there, move, and are routed onto what they alter (`:244`) | numbers | Spread of each picture source's value over 10 s; an offline render's picture-source readings over time. | left: needs render_cpp | to pieces (`routed`); null the same with no note |
| and each loop changes what the picture does, against itself without the loop: the verdicts or the reading (`:249`) | numbers | Picture meter's verdict histogram and photo.1's swing, looped against unlooped (the setup with its picture routings removed); offline renders of two setup codes. | left: needs render_cpp | to pieces; null each loop against itself |
| and none of them ends running away (`:252`) | numbers | `pictureMeter.verdict()` at the end; the core has the meter (`core/include/scope/picture.h`). | left: needs render_cpp | to pieces; null the loop's struck run, which does |
| the wandering preset wanders because of its loop: wandering most with it, and not without it (`:256`) | numbers | Verdict histogram for one preset, looped and not; offline render. | left: needs render_cpp | to pieces; null the other way round |
| no page errors (`:260`) | page | The page's own health on ?brain=js; goes with the leg (the default page has its own). | split: a page each | the ?brain=js page's goes; the default's stays |

### planetest.py - wholly on ?brain=js - 37/37
Its comment (`:26`): "reads the page's own brain - midiControl called directly". In practice the first 23 checks never touch the page's brain at all: they build `makeGeneratorCore(44100, GEN_SLOTS, ...)` - the JavaScript engine itself - inside the page and render blocks from it (`CORE`, `:78`). The rest drive the panel and read `genSettings()`, `state.source.getLatestWindow()`, `restore`/`snapshot`/`migrateSetup`.

| Check | Kind | Why | Batch 4 (13 Nov) |
|---|---|---|---|
| mirroring X makes X its own absolute value, to the last bit, and leaves Y alone (`:116`) | numbers | JS engine block at 1x, a 3:2 figure; the same setup rendered by the core offline. | to pieces (plane.py, generator_cpp) |
| and both folds both (`:120`) | numbers | As above, planeMirror 3. | to pieces (plane.py, generator_cpp) |
| the radial clip makes every pair's length r tanh(\|v\|/r), to float precision (`:131`) | numbers | Rendered clip against the formula. | to pieces (plane.py, generator_cpp) |
| never longer than the radius, from a figure that reaches 1.13 (`:133`) | numbers | Same render. | to pieces (plane.py, generator_cpp) |
| and turns no pair: every one keeps its direction (`:135`) | numbers | Same render. | to pieces (plane.py, generator_cpp) |
| scale and shear are the matrix [sx sx*k; 0 sy], to float precision, with no delay at 2x (`:145`) | numbers | Render at 2x against the matrix. | to pieces (plane.py, generator_cpp) |
| the twist turns each point by k times its length, to float precision (`:160`) | numbers | Render against the per-point rotation. | to pieces (plane.py, generator_cpp) |
| and keeps every length (`:162`) | numbers | Same render. | to pieces (plane.py, generator_cpp) |
| the fold reflects each length at the radius, as often as it takes - 2r - m past it, m inside (`:173`) | numbers | Render against the fold formula. | to pieces (plane.py, generator_cpp) |
| never outside the radius, and every point keeps its direction (`:176`) | numbers | Same render. | to pieces (plane.py, generator_cpp) |
| snap at 5 bits puts both channels on a grid of 1/16 - the nearest point of it (`:185`) | numbers | Render against the grid. | to pieces (plane.py, generator_cpp) |
| all four together are applied in the stated order (`:203`) | numbers | Render against the composed formula. | to pieces (plane.py, generator_cpp) |
| its fundamental is 440 and its odd harmonics of 220 are gone, 100 dB down (`:212`) | numbers | Spectrum of a mirrored sine, 1.1 s render. | to pieces |
| at 2x, the default, mirror, clip and twist clear the square's floor: under -58.5 at 2 kHz and -46.2 at 4 (`:234`) | numbers | Alias floors from 30 renders (op x freq x OS). | to pieces; pins measured again on the core, identical |
| and for those three each doubling is worth at least 10 dB, at both (`:237`) | numbers | Same floors. | to pieces; pins measured again on the core, identical |
| the fold and the snap are no worse than when they were measured (`:252`) | numbers | Same floors against pins; the pins were measured on the JS engine and need re-measuring on the core (parity makes them near-identical). | to pieces; pins measured again on the core, identical |
| and oversampling still buys the fold 20 dB from 1x to 4x, at both (`:255`) | numbers | Same floors. | to pieces; pins measured again on the core, identical |
| outside poly what is heard is exactly what is drawn - the pair is not done twice (`:261`) | numbers | The engine's heard pair (HL/HR) against its picture pair; the offline render must expose both outputs. | to pieces: heard pair against the pictures |
| in poly layer A's picture and layer B's are each mirrored, and so what is heard (`:275`) | numbers | Voices set directly on the engine, two layers; offline render with timed MIDI and the layers' outputs. | to pieces |
| and what is heard is the two mirrored pictures summed, sample for sample (`:284`) | numbers | Same render, heard against A+B. | to pieces |
| and not the sum mirrored, which the comparison tells apart (`:286`) | numbers | Same render, the null. | to pieces |
| 2x and 4x both delay the pair 31 samples, 0.7 ms, as the code says (`:304`) | numbers | Lag between renders at 1x/2x/4x. | to pieces |
| sixteen voices over two layers with both operations at 4x run in under half of real time (`:324`) | numbers | Borderline: a wall-clock cost of the JS engine's `block`. The assertion (cost under half real time) is worth keeping for the core, but as written it times the engine step 6 deletes; offline it becomes a timing of the C++ render, a much easier bar. | to pieces: the core's generator_cpp timed, 89 ms a second against 500 |
| the section is on the Effects tab and its controls reach the generator - the radius shown and used only with the clip on (`:379`) | page | Panel rows plus `genSettings()` (the page brain's settings). Becomes clicks on the default with the instrument's setup read back. | rewritten: `snapshot()`, not `genSettings` |
| on the page the figure is mirrored and clipped once, not twice: longest %.4f (`:383`) | numbers | `getLatestWindow` under `midiNoteOn` on the page's tone; the setup and a held note rendered offline give the same longest radius. | to pieces (instrument_cpp, a key at 127) |
| a source on Clip radius opens it: at full depth the figure is held at 0.75, not 0.25 (`:389`) | numbers | Key velocity routed to gen.radius via `addRouting`; offline render of a setup with that routing and a note at 127. | to pieces (instrument_cpp, a key at 127) |
| twist, snap, scale and shear reach the generator in its own units - a quarter-turn a unit reads 90 degrees (`:436`) | page | Slider to `genSettings()` units and a reading's text; becomes slider moves on the default with the setup read back. | rewritten: the panel's units through `snapshot()`; the generator's units are parity's restore section |
| a source on Twist swirls a figure whose slider is at nought (`:439`) | numbers | Same pattern as `:389`, gen.twist; offline render. | to pieces (instrument_cpp) |
| a code's plane reaches the generator (`:468`) | page | `restore()` then `genSettings()` and the menu's value; becomes a code pasted on the default. | rewritten: snapshot |
| a code carries it, and no box any more (`:470`) | page | `snapshot()` fields; the page's codec, kept after step 5. | moved |
| and a code from before has the plane off, at 2x (`:471`) | page | `restore({})` then `genSettings()`. | rewritten: snapshot |
| a code carries the twist, snap and matrix both ways (`:475`) | page | restore/snapshot/genSettings round trip. | rewritten: snapshot |
| and a code from before has them all at rest (`:479`) | page | As above. | rewritten: snapshot |
| a version-3 code with the clip ticked loads as Clip, at its radius (`:480`) | page | `migrateSetup` v3 pass then `genSettings()`; the core has its own decode pass, which parity holds. | rewritten: snapshot |
| and one without it as off, the box's field gone (`:482`) | page | `migrateSetup` output; page-only function, no brain needed - moves to the default trivially. | moved |
| rectifier finds the mirror (`:491`) | page | The bench search; face only, nothing of the brain - moves to the default as is. | moved |
| no page errors (`:493`) | page | Page health on the leg. | moved |

### pulsetest.py - wholly on ?brain=js - 24/24
Its comment (`:22`): "reads the page's own brain - midiControl and genSet called directly". As in planetest, the spectral checks build `makeGeneratorCore` and call `waveAt` (the JS engine's wave function) directly, with `setRoutes` on `WIDTH_SLOT`/`SYNC_SLOT` (`:79`).

| Check | Kind | Why | Batch 2 (13 Nov) |
|---|---|---|---|
| at a half the pulse is the square, sample for sample, band-limiting included (`:135`) | numbers | `waveAt('pulse')` against `waveAt('square')` per sample; the core's wave function, called by an offline tool. | gone to parity: pieces/pulse.py, the core's waveAt; a quarter against the square its null |
| at every width from 5 to 95 per cent its middle is nought and its larger excursion 0.9 (`:138`) | numbers | `waveAt` mean and peak over a cycle; same. | gone to parity: pieces/pulse.py, the core's waveAt; the same samples with the middle left in its null |
| and a width past either end is that end (`:141`) | numbers | `waveAt` at out-of-range widths; same. | gone to parity: pieces/pulse.py, the core's waveAt; 0.2 against 0.05 its null |
| a quarter: every harmonic \|sin(pi n / 4)\| / n to 0.3 dB, and no fourth, eighth or twelfth (`:158`) | numbers | Spectrum of a 1.1 s engine render. | gone to parity: pieces/pulse.py, the core's generator (generator_cpp); the quarter against a third's formula its null |
| a third: the same, with no third, sixth, ninth or twelfth (`:161`) | numbers | Same. | gone to parity: pieces/pulse.py, the same |
| a tenth: the first dozen falling as a narrow pulse's do (`:164`) | numbers | Same. | gone to parity: pieces/pulse.py, the same |
| a core built with no width plays a quarter, as the panel starts (`:173`) | numbers | Duty of a render with no width set: the engine's own default. Offline, the core's default width. | gone to parity: pieces/pulse.py, generator_cpp with no width set |
| the output is high for the width set: a quarter and seven tenths of the time (`:179`) | numbers | Duty of renders. | gone to parity: pieces/pulse.py, generator_cpp; seven tenths not a quarter its null |
| a source at full pushes a quarter to seven tenths, pulls a half to 5 per cent, and stops at 95 (`:181`) | numbers | Renders with a held routing on the width slot; offline as a setup with a routing and a held source (the raw `setRoutes`/slot form has no setup-code equivalent, so it needs a real source, e.g. key velocity). | gone to parity: pieces/pulse.py, generator_cpp with the width slot's source held at one and minus one; held at nought its null |
| hard sync at ratio one is the plain pulse one sample late - its reset corrected by its own jump (`:193`) | numbers | Render with a routing of nought on the sync slot. Same caveat: "a routing of nought switches sync on" must be expressible in a setup code. | gone to parity: pieces/pulse.py, generator_cpp with a routing of nought on the sync slot; on time its null |
| A at a quarter has its second harmonic at -3.0 dB, B at a half none: B plays its own (`:201`) | numbers | Two-layer render (A and B outputs); offline with a split/layer setup and a note. | gone to parity: pieces/pulse.py, generator_cpp's two layers; B at A's quarter its null |
| the Width row is on Play only with Pulse chosen - not the square, not the morph (`:225`) | page | Panel rows by shape; face only, moves to the default trivially. | moved |
| it starts at a quarter, says so, and the slider writes the generator (`:228`) | page | Reading text plus `genSettings().width`; becomes slider moves on the default with the setup read back. | moved: `genSettings().width` is the face's mirror on the default; that the instrument hears the slider is parity's menus-and-switches check |
| a controller on Width moves the sound, a quarter to seven tenths, without writing the slider (`:257`) | numbers | Duty from `getLatestWindow` under `midiNoteOn(57,127)` and a key-to-width routing; offline render. The "without writing the slider" half is page (`genSettings().width`). | rewritten: the duty read off the instrument's lanes on the default (it was the page generator's), the slider, mirror and code unwritten; +1 null (depth nought). The sound also gone to parity: pieces/pulse.py, a key on Width through instrument_cpp |
| full depth is 45 per cent, stopped at 5 and 95 (`:260`) | page | `MOD_DESTS.get('gen.width').reach(...)`, a page function's arithmetic; can be read on the default page as is (the face draws the ring from it). | moved: the face's arithmetic |
| editing B writes B's width and leaves A's (`:284`) | page | Hand switch and link clicks, `genSettings(0/1)`; becomes clicks on the default reading the setup. | moved: Poly clicked (setMidiMode is never heard); reads the face's mirror |
| and back on A the slider is A's, with the code carrying both (`:286`) | page | Slider value and `snapshot()`; face plus codec, default-ready. | moved |
| a code's width reaches the slider and the generator, and B takes A's when it has none (`:307`) | page | `restore` then `genSettings`; the codec. | moved: the face's restore and mirror; the core's restore is parity's |
| and B its own when it has one (`:309`) | page | As above. | moved, as (:307) |
| a width past the end loads as the end on both layers, and so does any of B's sliders (`:313`) | page | restore clamping, `genSettings(1).morph`; codec. | moved, as (:307) |
| a code from before the pulse loads with a quarter (`:315`) | page | As above. | moved, as (:307) |
| a generator built later, from the panel, takes the slider's width on both layers (`:327`) | page | `state.source.stop(); toTone()` - `generatorFromPanel`, which only the page's brain has. Goes. | gone: toTone()/generatorFromPanel, a path only the page's brain has |
| pwm finds it (`:336`) | page | Bench search; face only. | moved |
| no page errors (`:338`) | page | Page health. | moved |

### rotatetest.py - none on ?brain=js (default only) - 0/40
Opens one page, `scope.html?picture=0` (`:92`), the default. The one mention of ?brain=js (`:198`) is a comment explaining why the key is struck again on the instrument ("on ?brain=js it never was"). Nothing to sort; 40 sites on the default (the formatted one at `:814` runs once per turn).

### scaletest.py - wholly on ?brain=js - 24/24
Its comment (`:16`): "reads the page's own brain - its oscillators, set by hand between frames". That is true of three checks (`:173`-`:179`, `lfos[0].value = ±1` then `applyModMatrix`). The other 21 read the face's own display arithmetic - `gainOf`, `fsDetent`, `fullScaleDb`, `capture()`, `measure()`, `state.channels[i].fsDb/fsMod` set directly - and the codec. `capture()` is the page's, called from the frame loop whatever the source (`scope.html:16035`, `:20072`), so those run on the default as they stand.

| Check | Kind | Why | Batch 1 (13 Nov) |
|---|---|---|---|
| the table itself is unchanged (`:63`) | page | `FULL_SCALE_DB`, a page constant; default-ready as is. | moved |
| every detent gives its old gain to the last bit (`:71`) | page | `gainOf(0)` with `fsDb` written by hand: the display's arithmetic, which the default page runs too (the core's twin is `capture.h`, held by parity). | moved |
| and each one lands back on its own detent (`:73`) | page | `fsDetent`; as above. | moved |
| the control is still nine stepped positions (`:92`) | page | The slider's min, max and step; face. | moved |
| and each one writes its own decibels (`:95`) | page | Slider to `state.channels[0].fsDb`; face, default-ready. | moved |
| a source moves it by the decibels it asks for (`:118`) | page | `fullScaleDb(0)` with `fsMod` written by hand; display arithmetic, default-ready. | moved |
| and between the detents, not only on them (`:121`) | page | As above. | moved |
| pushed past the ends it stops where the knob stops (`:124`) | page | The clamp in `fullScaleDb`; as above (`capture.h:194` is the core's). | moved |
| one destination per lane, and no more (`:134`) | page | `MOD_DESTS` ids; the face's registry, default-ready. | moved |
| named so a reader knows which lane (`:137`) | page | A destination's label; face. | moved |
| a source on full scale moves it (`:173`) | page | `lfos[0].value` set by hand and `applyModMatrix` called: the page brain's matrix stepped by hand. Becomes an offline render of an `lfo1 -> view.scale1` setup (core `screen.h:180` registers the destination), so it could equally be scored numbers. | moved |
| and the trigger follows it within the same capture (`:175`) | page | `capture().levelAt` after the hand-stepped matrix; as above, the trigger's `levelAt` is in `capture.h:408` for an offline version. | moved |
| with the patch taken off, it goes back to the knob (`:179`) | page | `fsMod` after `applyModMatrix` with no routing; as above. | moved |
| what it fires at changes with the gain (`:206`) | page | `capture().levelAt` with `fsMod` written by hand; the face's capture, default-ready. | moved |
| and where that sits on the screen does not (`:209`) | page | As above. | moved |
| a version 1 level is converted with the old table's gain (`:227`) | page | `decodeSetup` migration; the codec, default-ready (the core's passes are parity's). | moved |
| and its full scales become the decibels they stood for (`:230`) | page | As above. | moved |
| a version 2 setup keeps its level and converts its scales (`:233`) | page | As above. | moved |
| a version 3 setup is left alone entirely (`:236`) | page | As above. | moved |
| and everything comes out saying the version the page is on (`:245`) | page | `SETUP_VERSION`; as above. | moved |
| a setup saved now comes back in decibels (`:259`) | page | encode/restore round trip on `state.channels`; codec, default-ready. | moved |
| a modulated full scale does not touch the captured samples (`:283`) | page | `capture()` with `fsDb/fsMod` by hand; face, default-ready. | moved |
| so dBFS and the clipping verdict are still about the input (`:285`) | page | `measure()` on those captures; as above. | moved |
| no page errors (`:289`) | page | Page health. | moved |

### scantest.py - wholly on ?brain=js&core=js, with one ?brain=js leg (`:593`) beside two default legs (`:585`) - 55/57
Sites here count `check(` and its wrapper `null(` (which calls `check("null: " + ...)`): 33 checks and 24 nulls; the `check` inside `def null` (`:52`) is not counted. Its docstring (`:27`): "The core runs on the main thread from `makeGeneratorCore` ... most of the page runs on `?brain=js&core=js`, whose reading and timing are the ones under test, and the C++ port is held to them by parity". The last section opens the default site twice (Scan on/off) and `?brain=js` twice, the latter to prove "the page's own brain on the compiled generator has to send it its tables". Not listed: `:588` (check) and `:590` (null), both default.

| Check | Kind | Why | Batch 3 (13 Nov) |
|---|---|---|---|
| a reading's table is its harmonics, evened to a peak of one, with no DC (`:143`) + null `:146` | numbers | `scanTables` on a synthetic reading; the core's `scan.h`, through `core/tests/tools/scan_cpp.cpp`, not a setup render. | to pieces (scan.py, `tables`) |
| a picture ten times dimmer reads the same table: the picture cannot make the voice quieter (`:148`) + null `:150` | numbers | As above. | to pieces |
| the second level leaves out what the first has past its 32nd harmonic (`:152`) + null `:154` | numbers | As above. | to pieces |
| a flat reading is darkness, and so is one under SCAN_DARK: no table, so the last is held (`:155`) + null `:157` | numbers | As above. | to pieces |
| an off-centre path reads a three-petalled rose at its fundamental (`:170`) + null `:173` | numbers | `scanRead` on a grid drawn in JS; grid-in, table-out through scan_cpp. | to pieces (`geometry`, `read`) |
| three cells of softness take the spikes out: the share above the 16th harmonic falls tenfold (`:184`) + null `:186` | numbers | `scanRead` softness; as above. | to pieces |
| the path follows the figure over about a second: 63 per cent of the way after one (`:197`) + null `:199` | numbers | `scanFollow` over 60 grids; as above. | to pieces (`follow`) |
| and holds where it was over darkness (`:200`) | numbers | `scanFollow` on a dark grid. | to pieces; +1 null |
| at %d Hz a table sent anywhere in a tick lands at the next, to the sample (`:219`), x3 rates | numbers | JS engine blocks with `core.set('scanTable', ...)` mid-run; needs a render that can inject a table at a sample, not a setup code. | to pieces (generator_cpp; tables put at block edges, the page's anywhere) |
| at %d Hz and one sent a tick later lands a tick later: they part at sample %d (`:225`) + null `:227`, x3 | numbers | As above. | to pieces |
| the crossfade is a straight line across one tick, from the last table to the new one (`:242`) + nulls `:245`, `:247` | numbers | As above. | to pieces |
| %s: a table at a depth of nought changes nothing, to the bit, either side (`:263`) + null `:265`, x3 voices | numbers | Engine renders with and without a table at depth 0 and 0.01. | to pieces |
| Scan plays at the note's pitch: the wave repeats every cycle of the note (`:272`) + null `:274` | numbers | Engine render, periodicity. | to pieces |
| depth %.1f under a hold of %.2f keeps %.2f of the shape: the note never loses its fundamental (`:284`) + null `:286`, x3 | numbers | Engine render with `scanHold` set directly; offline needs the hold as an input. | to pieces (`set scanHold`) |
| the bend bends what Scan reads, not only the shape under it (`:313`) + null `:314` | numbers | Engine render against a hand computation that calls the page's `waveAt` and `cycleRead`; offline the expectation must be computed in Python or by the core's own functions. | to pieces (the hand's cycleRead written again in Python); +1 check: the step read at 2 kHz, which the mutation pass found this could not see |
| layer B's depth and table play in B's lanes and leave A's to the bit (`:323`) + null `:325` | numbers | Two-layer engine render. The null is vacuous - see Surprises. | to pieces; its null, which could not fail, replaced by two that can |
| under sync it is bounded and finite, and Scan is in nearly every sample, not only the restarts (`:332`) | numbers | Engine render under sync. | to pieces |
| Depth writes the layer's scan, and says how much of the voice it is (`:362`) | page | Slider to `genSettings().scan` and the reading's text; default with the setup read back. | moved, rewritten: reads `snapshot()`, not `genSettings()` (the page's mirror) |
| Persistence in seconds sets the phosphor's fade, and the menu shows its time when it is not one of the five (`:364`) | page | `state.persistence`, the menu's text; face. | moved |
| a setup code carries the depth, the softness and that persistence, and brings them back (`:368`) + null `:372` | page | snapshot/restore round trip; codec. | moved, rewritten: `snapshot()` for the depth and softness |
| a persistence chosen in the menu moves the slider to its time and hides Memory's own (`:374`) | page | Face only. | moved |
| for a quarter of a second after a setup lands nothing is read (`:391`) + null `:393` | numbers | Borderline: counts the page brain's posts of a table to its source (`src.set` intercepted). The behaviour is in the core (`scan.h:52`, `kScanFreezeMs = 250`, `freeze()`), so an offline render that counts table changes after a setup lands keeps it. | to pieces (scan_cpp `freeze`; the instrument's own freeze is parity's) |
| a voice rebuilt with Scan on is handed its table as tables, every level its full length and finite (`:440`) | page | `AudioWorkletNode` intercepted to read `processorOptions.tone.scanTable` through `genVoice`/`toTone` - the page brain's worklet plumbing. Goes. | gone: the page brain's worklet plumbing |
| and stays finite and sounding (`:442`) + null `:443` | page | Same rebuilt page voice; goes with it (the null is the JSON pitfall of that plumbing). | gone, with :440 |
| a screen full of light is running away, and the hold reins Scan's depth in to a quarter, as the stage's (`:458`) + null `:460` | numbers | `genSettings().scanHold` and `pictureStage.hold` with `phosphor.grid.fill(1)` forced every 5 ms; offline needs a fixture that fills the screen (a loud figure) rather than writing the grid. | to pieces, in two: picture_cpp's stage held to a quarter on a full screen, and scan_cpp's frame sending it |
| with a split, Depth edits the layer on the panel and B reads its own figure's picture (`:489`) + null `:491` | numbers | Borderline: `layerPictures.engines[1].cells` read through `scanRead` against what was posted; the panel half is page. Offline as a split render with each layer's table out. | split: the panel half moved (clicks, `snapshot()`); B reading its own picture is parity's and pieces/strike.py's |
| a turning fifth read back moves its timbre: the brightness wanders (`:534`) + null `:535` | numbers | Brightness of `getLatestWindow` over 6 s, loop closed; offline render of the corpus setup. | gone: the site legs hold it on the instrument |
| and within three seconds it is plainly not the fifth without Scan (`:536`) | numbers | As above. | moved into the site legs, rewritten from their two runs |
| held still - the screen stopped - Scan is an ordinary tone: the brightness stands (`:539`) + null `:541` | numbers | As above, with `setRunning(false)` at 2 s; offline needs a "screen stopped" event in its timeline. | left on ?brain=js&core=js (a page of its own): on the site Stop does not reach the instrument, a defect in after-stage-5.md; judged against its own run before the stop |
| no page errors (`:544`) | page | Page health. | kept, on the default |
| the page's brain on the compiled generator sends it the tables, and it plays them (`:596`) + null `:597` | engines compared | `?brain=js` (default core = wasm): exists to prove the page's brain feeds the compiled generator. Goes; the default legs `:588`/`:590` already hold Scan on the instrument. | gone: engines compared |
| no page errors on the site (`:598`) | page | Mixes the two default and two ?brain=js pages' errors; keeps its default half. | kept, its default half |

### schematest.py - wholly on ?brain=js - 14/14
No stated reason: it has no "On ?brain=js (5m)" comment at all, and nothing in it needs the page's brain. It holds `SETUP_FIELDS` to `snapshot()` and to the markup's controls, and the readers (`setupField`, `setupOwn`, `restore`). Only `:229`/`:231` read the brain's own engine objects (`plane`, `planeB`, `echo`, `echoB`) and the cover (`:151`) toggles `handLinks` and `planeB.own`.

| Check | Kind | Why | Batch 1 (13 Nov) |
|---|---|---|---|
| every field snapshot writes is in the table, with layer B's own plane and echo on (`:151`) | page | `snapshot()` keys against `SETUP_FIELDS`; codec. Default-ready, though `planeB.own` is the brain's flag - on the default the hands' links alone should do it. | moved |
| and every field in the table is written, but those read only from old codes (`:153`) | page | As above. | moved |
| null: a table without planeSnap is caught, and one with the kaleidoscope back (`:160`) | page | The same function fed a wrong table; as above. | moved |
| every default is one its own rule takes (`:166`) | page | Table only; no brain. Could even be Python over the page source. | moved |
| every menu is its control's options (`:167`) | page | Table against the markup's menus; face. | moved |
| every range is its slider's (`:168`) | page | Table against the sliders; face. | moved |
| every ruled field has a control, or a reason it has none (`:169`) | page | As above. | moved |
| null: Snap offering 1 to 4 bits again, a radius to 99, ... are each caught (`:183`) | page | The judge fed a wrong table. | moved |
| a value the rule refuses is the default, and one it takes comes back as given or held (`:209`) | page | `setupField`, a pure page function. | moved |
| a switch is on only for true, or off only for false where its default is on (`:212`) | page | As above. | moved |
| layer B's own is read by A's rule, and is nothing where it is refused or missing (`:214`) | page | `setupOwn`; as above. | moved |
| restore reads A's plane and echo by the table: a cut snap and an unknown sync are the defaults, a radius held (`:229`) | page | `restore()` then the brain's `plane`/`echo` objects. On the default it becomes the instrument's setup read back (or the core's `restore.h`, which parity holds). | moved |
| and B's own falls back to A's as it stands - its snap of 3 bits is A's 5, its unknown sync A's 1/4 (`:231`) | page | As above, `planeB`/`echoB`. | moved |
| no page errors (`:234`) | page | Page health. | moved |

### scoretest.py - wholly on ?brain=js - 20/20
Its comment (`:21`): "reads the page's own brain - its sources' functions, bound directly". It calls `scoreColumn`, `scorePitches`, `keyMask`, `scoreTick`, `transportStart` directly, writes `phosphor.grid` by hand, intercepts `state.source.strike`, and builds `makeGeneratorCore` for the struck voice. The core has all of it (`core/include/scope/score.h`, with `MidiOut` and its forty-a-second limit, and `core/tests/tools/score_cpp.cpp`).

Batch 2 (13 Nov): 20 checks to 4 here, all left on `?brain=js` (the page's own score and MIDI out, which on the default run beside the instrument's), and 28 in `core/tests/pieces/score.py` (15 checks, 13 nulls) on score_cpp and generator_cpp. 16 rows gone to parity.

| Check | Kind | Why | Batch 2 (13 Nov) | Batch 6 (14 Nov) |
|---|---|---|---|---|
| a single lit row is one note in every column, the one its height names, at its brightness (`:87`) | numbers | `scoreColumn` on a hand-made grid; grid-in through score_cpp. | gone to parity: pieces/score.py, score_cpp's new `column` (scoreColumn over scorePitches); the note the row names upside down (75) as null |  |
| a diagonal is a rising scale, every note from C3 to B5 and none twice out of order (`:92`) | numbers | As above. | gone to parity: pieces/score.py, the diagonal read falling as null |  |
| and in D dorian every note of it is in D dorian, the whole scale climbed (`:98`) | numbers | `scorePitches`/`keyMask`; as above. | gone to parity: pieces/score.py, D dorian written out, as it was; two chromatic octaves as null |  |
| with two voices the chord is the two brightest, loudest first (`:101`) | numbers | As above. | gone to parity: pieces/score.py, three voices taking the third as null |  |
| and a smudge under the floor plays nothing, as an empty column plays nothing (`:103`) | numbers | As above (`kScoreFloor`). | gone to parity: pieces/score.py, a cell a little over the floor playing as null |  |
| at 120 BPM in semiquavers a second from nought is nine steps, each striking the lit row's note (`:131`) | numbers | `scoreTick` at fake times with the grid written by hand, strikes counted; an offline run needs a written grid, so score_cpp rather than a setup render. | gone to parity: pieces/score.py, the core's scoreTick at made-up times, strikes logged; 90 BPM's seven as null |  |
| and at 60 BPM it is five: the playhead keeps the tempo (`:133`) | numbers | As above. | gone to parity: pieces/score.py, as (131) |  |
| and an empty grid strikes nothing (`:134`) | numbers | As above. | gone to parity: pieces/score.py, as (131) |  |
| a struck note is heard at its level, 0.4 times its velocity over two (`:168`) | numbers | JS engine `core.strike` then `block`; the core's generator offline. | gone to parity: pieces/score.py, generator_cpp's `strike`, the same two renders at 44.1 kHz; half the velocity as null |  |
| and it is not drawn: the picture is untouched, and what is heard beyond it is the note, in both ears alike (`:170`) | numbers | Same render, picture pair against heard pair. | gone to parity: pieces/score.py, as (168) |  |
| and the picture check fails with the heard pair read as the picture (`:172`) | numbers | Same render, its null. | gone to parity: pieces/score.py, the null, as it was |  |
| and it dies away to 1/e over its 400 ms (`:173`) | numbers | Same render. | gone to parity: pieces/score.py, with 200 ms not yet 1/e as null |  |
| the score's notes go out on the chosen channel, the last one ended before the next begins (`:228`) | numbers | MIDI bytes from the stubbed port; the core's `MidiOut` emits the same bytes through `Instrument::midiOut`, so an offline run with a written grid can collect them. | gone to parity: pieces/score.py, the core's MidiOut's bytes, logged by score_cpp; the first channel as null |  |
| and when the next step's note is another, the last is ended before it begins (`:233`) | numbers | As above. | gone to parity: pieces/score.py, the note-off after the next note-on as null |  |
| stopping the scope ends the sounding note and sends all-notes-off on that channel (`:236`) | page | `setRunning(false)` - a page event; on the default it becomes a click on Stop with the bytes read from the stub. | left on ?brain=js: setRunning and the page's own score and MIDI out; on the default the instrument's score and the page's both run, and which one sends is step 5's (section 4). Its sounding note is read off the stub now, since the run that named it went | left on ?brain=js, for step 5: the page's own score and MIDI out, beside the instrument's; which one sends is step 5's |
| hiding the page does the same (`:238`) | page | `visibilitychange`; page only, default-ready with the stub. | left on ?brain=js: the page's visibilitychange and midiOutPanic, as (236) | left on ?brain=js, for step 5: as (236) |
| a hundred note-ons at once are forty sent and sixty dropped, and none of the note-offs (`:240`) | numbers | `midiOutNote` x100; the core's `MidiOut` (`kMidiOutRate = 40`). | gone to parity: pieces/score.py, the same hundred thirty ms apart all sent (the limit is a rate) as null |  |
| and an empty grid sends nothing at all (`:242`) | numbers | As above. | gone to parity: pieces/score.py, the same playing with a row lit sending as null |  |
| ticked on the page, the playhead moves with the frames and the drawn waveform plays (`:256`) | page | The score box ticked, real frames for 1.2 s, `score.steps` and the intercepted `strike`; becomes a click on the default reading the instrument's strikes. | left on ?brain=js: the page's score.steps and its source's strike wrapped, over real frames; on the default the instrument's score plays, a step-5 lean | left on ?brain=js, for step 5: score.steps and the page's own strike, over real frames |
| no page errors (`:259`) | page | Page health. | left on ?brain=js: page errors | stays with the ?brain=js page |

### shapetest.py - wholly on ?brain=js - 29/29 (batch 2: a default page, and the survey's ?brain=js page)
Its comment (`:23`): "reads the page's own brain - genSet called directly". That applies to the live section; the first twenty checks call `makeMoments`, `makePictureMeter`, `shapeOfPair` on grids built in JS (`HELPERS`), which is what `core/tests/tools/picture_cpp.cpp` already runs against `picture.h` for parity.

| Check | Kind | Why | Batch 2 (13 Nov) | Batch 5 (13 Nov) |
|---|---|---|---|---|
| a circle is round and a line is not (`:147`) | numbers | `makeMoments().roundness()` on built strokes; picture_cpp-style grid/stroke-in run. | gone to parity: pieces/shape.py, the core's `Moments` on the same path (picture_cpp `mring`); null the two the other way round | - |
| a 2:1 ellipse reads the same whichever way it is turned (`:151`) | numbers | As above. | gone to parity: pieces/shape.py, `mring` upright and turned; null a 0.6 by 0.32 ellipse turned | - |
| a circle is a circle however unevenly the beam divides it into strokes (`:153`) | numbers | As above. | gone to parity: pieces/shape.py, the same 612 strokes (`msegs`); null the strokes weighted by segment, which reads 0.497 | - |
| its blind spot, asserted so a change to the measure changes the plan's sentence: a square is as round as a circle (`:155`) | numbers | As above. | gone to parity: pieces/shape.py, `msegs` box; null a 2:1 box | - |
| and a dark screen is nought, not 0/0 (`:157`) | numbers | As above. | gone to parity: pieces/shape.py, `mempty`; null NaN | - |
| fading to nothing is a slope, not a cliff (`:169`) | numbers | As above, shrinking ring. | gone to parity: pieces/shape.py, 31 shrinking rings; null the series with a perfect tiny circle then nought | - |
| coverage moves a little when every cell crosses one half - it is not a count over a threshold (`:189`) | numbers | `makePictureMeter().update(grid)`; grid-in. | gone to parity: pieces/shape.py, the core's `PictureMeter` on picture_cpp's `ellipse ... nudged` fixture; null the two as a count over a half would read them | - |
| change is nought for the same picture and one for a different one (`:191`) | numbers | As above. | gone to parity: pieces/shape.py, `mupd` pairs; null the two exchanged | - |
| and small for a small difference (`:193`) | numbers | As above. | gone to parity: pieces/shape.py, null the different picture's change | - |
| novelty rises with how far the picture has gone from before, a step at a time (`:213`) | numbers | 15 s of grids through the meter; grid-in. | gone to parity: pieces/shape.py, 900 frames then 21 openings; null the readings as a yes-or-no against the novelty floor | - |
| a circle travelled one way reads one, the other way minus one (`:236`) | numbers | `shapeOfPair` with `state.xyPair` and a channel's `offset` written - page display state as inputs; the core's picture source offline. | gone to parity: pieces/shape.py, the core's `shapeOfPair` on `__pair` (`mpair`), at the unit gains `pairOfFrame` hands the default lanes, not `state.xyPair` written; null the two exchanged | - |
| a line has no direction (`:238`) | numbers | As above. | gone to parity: pieces/shape.py, null the pair a tenth of a radian off a line | - |
| and it passes through nought smoothly as the travel reverses (`:239`) | numbers | As above. | gone to parity: pieces/shape.py, null the readings as a sign | - |
| wherever on the screen the figure sits (`:241`) | numbers | As above, with `state.channels[0].offset = 0.3`. | gone to parity: pieces/shape.py, the offset handed to `shapeOfPair` as `pairOfFrame` would (`state.channels[0].offset` on the page); null the other way round's reading | - |
| a %s picture is %s, and no other fixture is (`:293`), x4 | numbers | Meter verdicts on built sequences; grid-in. | gone to parity: pieces/shape.py, the same five sequences, frame by frame through `mupd`; null the frozen and repeating verdicts exchanged, or the one verdict made `listening` | - |
| and nothing is said until there is history to say it from (`:296`) | numbers | As above. | gone to parity: pieces/shape.py, null the frozen fixture's verdict after ten seconds | - |
| the same motion in bursts is judged as it is evenly, and not as settled (`:307`) | numbers | As above. | gone to parity: pieces/shape.py, null the bursts judged by the old per-frame median (settled) | - |
| where its median per-frame change, the old reading, is under the floor (`:310`) | numbers | As above. | gone to parity: pieces/shape.py, null the even motion's median | - |
| the rate is the change per sixtieth of a second: a frame's mean at sixty, the same at a hundred and twenty (`:318`) | numbers | As above. | gone to parity: pieces/shape.py, null the rate taken per frame (the 120 run's mean) | - |
| and at a hundred and twenty a frame does change about half as much, so per frame would not do (`:321`) | numbers | As above. | gone to parity: pieces/shape.py, null the even run's own mean | - |
| the five come with the photocell, under the same rules as it (`:365`) | page | `MOD_SOURCES` registered on the photocell button; the face's registry, a click on the default. | moved: a face registry, the photocell a click; the fixture rewritten as gestures the instrument hears (Mono and X-Y clicked, the Persistence by its input, the note through `midiNoteOn`) where it was `setMidiMode`/`setDisplay`/`genSet`/`state.persistence`; + a check that the source is the host's; null the registry before the photocell | - |
| since E3 a picture source may reach the filter too (`:367`) | page | `addRouting` accepted; face. | moved: the face's rule; null a source the page does not have, refused | - |
| the readout says what the loop is doing (`:368`) | page | `el.readoutDetail` text after 6.5 s; on the default the face reads the instrument's verdict (a step-5 hazard). | moved: reads the page's own `pictureMeter` of the face's grid on both brains (a step-5 lean, section 4); null the readout before any picture routing is heard, which says no loop | - |
| and only the photocell goes when it is switched off: the picture's stay (`:371`) | page | Registry after a second click; face. | moved; null the registry with the photocell still on | - |
| roundness follows the picture as the screen forgets the old one (`:375`) | numbers | `picture.round` and `picture.raw.round` over 2.5 s of frames after `genSet('phase', ...)`; offline render with a phase change mid-run. | gone to parity: pieces/shape.py, restated: the core's `PictureSources` at made-up 16 ms frames with Persistence off, a circle deposited until the value caught up and then a line (picture_cpp `poly`/`step`), where the page did `genSet('phase')` over 2.5 s of real frames; null a value held at the circle's | - |
| and no faster than two full swings a second (`:377`) | numbers | The slew; same run. | gone to parity: pieces/shape.py, the same run, now exact (no fall over two swings a second, where the page allowed 0.07 for frame timing); null the raw roundness, which falls in a frame | - |
| the source in the sixth slot adds what the other five do not hold, half a bit or more (`:387`) | numbers | `survey.js`: corpus setups with loops closed, 4 s each, entropies of the six sources; offline renders of those setups. | left on ?brain=js: corpus setups with the loop closed, the six sources read over 4 s each - needs `render_cpp` with the sources read out; a page of its own | to pieces (shape.py `survey`: render_cpp, the five pictures read every sixtieth of a second for 4 s; 1.40 bits) |
| and a copy of roundness, the null, adds nothing (`:389`) | numbers | Same survey. | left on ?brain=js: as (:387) | to pieces (0.000 bits); null Direction's own |
| no page errors (`:392`) | page | Page health. | split: one for the default page, one for the survey's ?brain=js page | the ?brain=js page's goes with the page; the default's stays |

### soundstarttest.py - 3 legs on ?brain=js beside the default (one `?brain=js&core=js`, two loop iterations `?brain=js`) - 14/21
The docstring: "a finger's tap starts it, on the site's compiled instrument and on the page's own brain", and the silence-until-a-note rule "on both brains". The two loops (`:127`, `:169`) run the same checks once on `""` (host) and once on `?brain=js` (tone); each site below is listed for its ?brain=js iteration and also runs on the default. Not listed: the finger on the default (`:82`, `:88`, `:89`, `:90`) and the mouse (`:108`, `:112`, `:113`).

| Check | Kind | Why | Batch 4 (13 Nov) |
|---|---|---|---|
| before any press the page's own brain is not heard either (`:96`) | engines compared | `?brain=js&core=js`: the JavaScript engine's start under the autoplay rule - a ?core=js fallback check. Goes (step 5 gives such a browser a line instead). | gone: a fallback step 5 replaces with a line |
| one tap starts the page's own brain too (`:101`) | engines compared | As above. | gone: a fallback step 5 replaces with a line |
| no page errors (`:102`) | engines compared | That leg's health; goes with it. | gone: a fallback step 5 replaces with a line |
| opened and unpressed, nothing is drawn and the empty screen says how to play a note, the ways that are true here (`:132`), x2 | page | The ?brain=js iteration reads the page brain's gate (`state.source.gated`, kind `tone`); the default iteration already asserts it on the instrument. The ?brain=js entry of the loop goes. | gone; the default iteration holds it |
| pressed, the sound is on and still nothing sounds, with no keyboard there: no drone before a note (`:142`), x2 | page | As above. | gone; the default iteration holds it |
| and with the keys opened the line names them and still nothing sounds (`:147`), x2 | page | As above. | gone; the default iteration holds it |
| a typed A is C3 and sounds, and the line is gone with it (`:157`), x2 | page | As above. | gone; the default iteration holds it |
| and K is the C above, so the line's A to K is an octave of keys (`:159`), x2 | page | As above. | gone; the default iteration holds it |
| and the line stays gone once the notes are let go (`:160`), x2 | page | As above. | gone; the default iteration holds it |
| and the silence reading fails on the note's window, and the line's on its hidden line (`:162`), x2 | page | As above (the null). | gone; the default iteration holds it |
| no page errors (`:164`), x2 | page | As above. | gone; the default iteration holds it |
| a key as the first press starts the sound, and is heard while it is held (`:181`), x2 | page | As above, second loop. | gone; the default iteration holds it |
| and the reading fails on the page before the press (`:182`), x2 | page | As above. | gone; the default iteration holds it |
| no page errors (`:183`), x2 | page | As above. | gone; the default iteration holds it |

### striketest.py - wholly on ?brain=js&core=js for its first page, then three default pages - 32/36
Sites count `check(` and `null(` (21 and 15; the `check` inside `def null`, `:53`, not counted). Its docstring (`:27`): "Run on the page's own brain (`?brain=js&core=js`), which draws the screen the page shows, and then on the site's instrument, which lays the strike in the core on the grid it draws itself". The first page writes and reads `pictureEngine.cells`, `scan.paths`, `layerPictures.engines/stages` by hand on a stopped screen. Not listed: the site section's `:452`, `:456` (null), `:458` (null), `:460`, all default.

| Check | Kind | Why | Batch 3 (13 Nov) |
|---|---|---|---|
| Strike at nought lays nothing at all (`:125`) | numbers | Growth of `pictureEngine.cells` after `midiNoteOn` with the screen stopped; offline, the core's grid after a timed note. | to pieces (strike.py, scan_cpp `laid`) |
| and neither does a strike with Scan off, since there is no reading for it to be in (`:126`) | numbers | As above. | to pieces |
| null: with Scan on and Strike at half, a note lays light (`:128`) | numbers | As above. | to pieces |
| a note lays light as bright as its velocity times the Strike amount (`:130`) + null `:132` | numbers | Peak of the grid after a note at velocity 100. | to pieces |
| it is laid where Scan reads: the reading, unblurred, rises by over half the light it laid (`:144`) + null `:146` | numbers | `scanRead` on the grid with `scan.paths[0]` written by hand and a stroke laid by `pictureEngine.segment`; offline needs the path as an input. | to pieces |
| each note strikes its own place round the circle: C at the reading's start, F sharp half a lap on (`:149`) + null `:151` | numbers | As above. | to pieces |
| a harder note changes the next table more: over twice what a soft one does (`:154`) + null `:156` | numbers | Tables before and after soft and hard notes. | to pieces |
| the strike's light fades exactly by the screen's Persistence, frame by frame, as a stroke does (`:183`) + null `:186` | numbers | A cell's value over `pictureEngine.frames`; offline, frame by frame. | to pieces (picture_cpp's fade) |
| the picture meter, which the stage and the running-away hold read, lights with what a strike laid (`:223`) + null `:225` | numbers | `pictureMeter.lit` before and after four notes; offline. | to pieces (picture_cpp's meter) |
| in a split a note above the split strikes B's picture and not A's (`:263`) + null `:265` | numbers | Each layer's `layerPictures.engines[l].cells` growth; offline split render with each layer's grid. | to pieces (scan_cpp `strike`; the instrument's split is parity's) |
| the Reads row is shown while the layers draw a figure each (`:266`) | page | `el.scanReadsRow.hidden`; face, a click on the default. | moved (Poly and the split by their controls) |
| crossed, A plays a table made from B's picture, and B from A's (`:316`) + null `:318` | numbers | `genSettings(l).scanTable` against `scanTables(scanRead(e[other].cells, ...))` after `scanStep(16)` by hand; offline needs each layer's table and grid out. | to pieces (scan_cpp frames) |
| reading both, A plays the two pictures' readings averaged (`:319`) + null `:320` | numbers | As above. | to pieces |
| a crossed pair's depths are both held by the lower of the two holds (`:321`) + null `:323` | numbers | Borderline: `layerPictures.stages[l].hold` written by hand (1 and 0.3), then `scanHold` read. The rule is the core's; offline it needs a hold as an input or a fixture that runs away on one layer. | to pieces |
| and a layer reading both, uncrossed, takes the lower of the two it reads (`:324`) | numbers | As above. | to pieces |
| a setup code carries what each layer reads and brings it back (`:326`) + null `:328` | page | snapshot/restore and `scan.reads`; codec, default-ready. | moved; reads the menus and `snapshot()` as well |
| a value a layer's menu does not offer reads its own picture (`:329`) | page | restore's refusal; codec. | moved |
| unsplit, the Reads row is hidden: there is one picture (`:332`) | page | Face. | moved |
| Crossed hands: two figures, Scan on both, and the left hand's wave read from the right hand's picture (`:365`) + null `:368` | numbers | Corpus preset, four notes, table against B's picture; offline render. | to pieces (instrument_cpp `reads`) |
| no page errors (`:370`) | page | Page health. | moved |

### wasmtest.py - wholly on ?brain=js (and ?core=js legs) - 41/42
Every page is opened through `open_page`, which appends `&brain=js` to whatever query it is given (`:221`); its comment (`:216`): "this suite reads which core the page's own two worklets and its main thread run - the page's own brain". The legs are `""` (wasm, `:271`, `:613`, `:657`, `:674`) and `?core=js` (`:600`, `:658`). Not listed: `:63`, which opens no page (`core/wasm/build.py --check`, the module's freshness).

| Check | Kind | Why |
|---|---|---|
| the generator's worklet says it is running the compiled core (`:273`) | engines compared | Which core the page brain's worklet made. Goes. |
| and so does the main thread's generator, which draws while the sound is off (`:274`) | engines compared | As above. |
| and so do the picture's own sources - the grid, the photocell, the meter (`:276`) | engines compared | As above. |
| and so do the setup codes (`:278`) | engines compared | As above. |
| and it plays, and the picture is drawn from what it sends (`:279`) | engines compared | The page brain's generator worklet on wasm playing; goes with the brain (the instrument's playing is braintest/hosttest's). |
| and the oscillators' phases come back from it (`:284`) | engines compared | As above, `lfos[0].phase` from the page brain's worklet. |
| %d generator presets, every one the same to %g in samples and in what comes back (`:293`) | engines compared | wasm against JS, every preset. |
| and they can show it: every one makes a picture, and %d have routes for the oscillators to carry (`:297`) | engines compared | That comparison's sensitivity. |
| and the comparison fails against a route a hundredth stronger, or a tone a cent sharp (`:300`) | engines compared | Its null. |
| %d presets' effects on a live input, every one the same to %g, %d of them changing it (`:304`) | engines compared | wasm against JS effects. |
| and the comparison fails against the twist a hundredth of a radian further (`:307`) | engines compared | Its null. |
| %d scenarios of the picture's sources, the compiled engine the same as the JavaScript to %g after every call (`:477`) | engines compared | wasm against JS picture engine. |
| and the lag's figure is turned by the screen, not the signal, a tenth of a turn (`:482`) | numbers | Borderline: the `spin` the page brain passed to `pictureStep` in the lag scenario. A behaviour of the brain worth keeping; offline it is the instrument's screen turn with the lag lane on. |
| and they can show it: %d walks laid, %d steps, %d scenarios lighting the grid, ... (`:488`) | engines compared | The comparison's sensitivity. |
| and the photocell switched mid-run, the limiters and a still picture: %s then %s ... (`:492`) | engines compared | As above: the scenarios exercise what they compare. |
| and the comparison fails against persistence a thousandth more, or every walk a step brighter (`:496`) | engines compared | Its null. |
| the effects worklet on a microphone says it is running the compiled core, and mirrors the input (`:503`) | engines compared | Which core the effects insert runs; the "mirrors" half is a live-input number that liveinput suites hold on the default. |
| with no errors on the page (`:506`) | page | Page health. |
| %d presets: each codec makes the same code from the snapshot, and reads each code back the same (`:549`) | engines compared | wasm codec against JS codec. |
| and the comparison sees a frequency a hertz higher (`:551`) | engines compared | Its null. |
| every setup field the page is ahead of the core on (%s) is still one the core cannot leave out, ... (`:568`) | engines compared | `SETUP_AHEAD_OF_CORE`, the JS codec's patch list for the wasm one; goes with the JS codec. |
| the compiled codec leaves each layer's picture menus out at their defaults, unhelped, and writes them set (`:579`) | page | The compiled codec's own behaviour (`setupCodec.kind == 'wasm'`), which survives step 6 as the page's only codec. Default-ready. |
| the compiled codec leaves Scan's depth and softness out at their defaults, unhelped, and writes them set (`:588`) | page | As above. |
| %d awkward codes and snapshots, the same outcome from each, a throw as a throw: %s (`:593`) | engines compared | wasm against JS on bad codes. |
| with ?core=js the generator's worklet says it is the JavaScript one (`:602`) | engines compared | The ?core=js switch. |
| and so does the main thread's (`:604`) | engines compared | As above. |
| and the picture's sources (`:605`) | engines compared | As above. |
| and the setup codes (`:606`) | engines compared | As above. |
| and so does the effects worklet (`:608`) | engines compared | As above. |
| with no errors on the page (`:609`) | page | That leg's health; goes with it. |
| the generator's worklet makes the JavaScript core instead, says why, and plays (`:620`) | engines compared | The fallback when the module is refused; step 5 replaces it with a line. |
| and so does the effects worklet (`:624`) | engines compared | As above. |
| with no errors on the page (`:626`) | page | That leg's health. |
| %d presets, the settings the page reads back the same from the compiled core's mirror as from the JavaScript core (`:662`) | engines compared | wasm page against ?core=js page. |
| and they can show it: %d presets leave the settings other than the one before (`:665`) | engines compared | Its sensitivity. |
| with no errors on either page (`:668`) | page | Health of both legs. |
| the main thread makes the JavaScript core instead, says why, and draws (`:681`) | engines compared | Main-thread fallback when `WebAssembly.Module` throws. |
| and the picture's sources are the JavaScript ones, saying why (`:683`) | engines compared | As above. |
| and so are the setup codes (`:685`) | engines compared | As above. |
| and the worklet, which can, still runs the compiled core (`:688`) | engines compared | As above. |
| with no errors on the page (`:689`) | page | That leg's health. |

### worklettest.py - wholly on ?brain=js - 35/35
Its comment (`:30`): "reads the page's own brain - its generator's worklet and who drives the oscillators". It compares no engines: it takes the page's module text (`generatorModuleSource()`, `scope.html:13512`) off a ?brain=js page and runs it in Node (`workletharness.mjs`) for 21 checks, then switches the page brain's generator worklet on and off.

| Check | Kind | Why |
|---|---|---|
| it evaluates and registers a processor (`:76`) | page | The module text evaluated against a worklet's globals. The same text carries the default's `scope-brain` processor (`scope.html:13295`) and is what `makeBrainHost` loads (`:14943`), so this check outlives the JS engine - against the slimmer module, asking for `scope-brain` rather than `generator`. |
| the waveform produces finite samples inside full scale (`:84`) | numbers | The JS generator in Node; offline core render. Largely duplicates the shape suites. |
| and is not silence (`:89`) | numbers | As above. |
| every waveform shape works, band-limited ones included (`:92`) | numbers | As above. |
| and the pulse is a quarter's, neither the square's nor a sine by default (`:99`) | numbers | As above (pulsetest `:173` holds the same default). |
| and the wavetable is its bank, not the drawn cycle nor a sine by default (`:105`) | numbers | As above. |
| and the drawn cycle is its tables, not a sine by default (`:109`) | numbers | As above. |
| and it posts its samples back rather than only playing them (`:114`) | page | The JS worklet's message protocol; goes with it. |
| the quantiser runs in the worklet: 225 Hz to A3, 220 exactly, and left alone when off (`:117`) | numbers | JS engine in Node; offline core. |
| the plane runs in the worklet at 1x, 2x and 4x: mirrored and held inside the radius (`:120`) | numbers | As above (planetest holds the same). |
| the rest of the plane and the time effects run in the worklet, each doing what it alone would (`:125`) | numbers | As above. |
| the voice's oscillator runs in the worklet, everything on at once, inside its amplitude (`:135`) | numbers | As above. |
| and with drive, fold and crush on it too, within the overshoot a band-limited square has (`:141`) | numbers | As above. |
| and through the voice filter, whose resonance lifts the sine: 0.546, not the plain 0.5 (`:148`) | numbers | As above. |
| S10 runs in the worklet: a dear chord gives up four times and some unison, and the posted message says so (`:157`) | numbers | The voice budget; the posted-message half is page. |
| the effects processor is in the module too, and with nothing on it is an exact copy of its input (`:163`) | numbers | The JS effects processor; the core's effects offline on an input. |
| told to mirror, it folds both channels to their absolute values, and silence in is finite (`:167`) | numbers | As above. |
| and a routing on the echo's level turns its delay on from nought: the impulse repeats 96 samples on (`:173`) | numbers | As above. |
| a restart sent by message lands in the worklet's core: both phases back to nought (`:184`) | page | The JS worklet's message protocol. Goes. |
| the generator's worklet reads its input: a ride at half depth on a steady half is 1.5 times the output (`:187`) | numbers | Input ride arithmetic; offline core. |
| a restart reaches the worklet's oscillators, and a repeated count does not restart them again (`:190`) | page | Message protocol. Goes. |
| a data URL loads, which is what makes the single file work at all (`:209`) | page | `addModule` of the module text by data URL in an `OfflineAudioContext`; the default loads the same way, so this moves to the default as is. |
| and from a file the blob does not, which is why there is a fallback (`:216`) | page | As above. |
| the generator says yes, and says how it loaded (`:236`) | page | `applyGeneratorSound` on the page brain's voice. Goes. |
| and the oscillators are now driven by the worklet (`:239`) | page | `lfoDriver()`, the page brain's one-loop rule. Goes. |
| and the picture is being drawn from what it sent (`:266`) | page | `capture()` of the page brain's worklet output. Goes. |
| the samples keep coming when nothing on this thread asks for them (`:296`) | page | Page brain's ring with `state.running = false`. Goes. |
| and neither of the other two may step an oscillator (`:310`) | page | `assertLfoDriver`; page brain only. Goes. |
| a 2 Hz oscillator goes round twice a second, in the worklet (`:336`) | page | `lfos[0]` shape and rate set by hand, read over 1 s of real time. Goes; an LFO's rate is an offline number if wanted. |
| the switch answers with what actually happened (`:347`) | page | Page brain's sound switch. Goes. |
| and this thread has the oscillators back (`:349`) | page | As above. |
| and the picture is still there, drawn on this thread again (`:359`) | page | As above. |
| a generator that cannot be heard says so, and why, where the switch was (`:378`) | page | `loadGeneratorModule` replaced to throw; `el.genFault`. The default's module load can fail the same way, so a default version is worth having (wasmtest `:620` is the nearest). |
| and while it is heard the line is not there (`:380`) | page | As above. |
| no page errors (`:382`) | page | Page health. |
