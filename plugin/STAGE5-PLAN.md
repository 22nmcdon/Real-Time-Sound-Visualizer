# Finishing stage 5: one engine

A plan, for the owner to read before anything is built. Nothing here has been
changed yet. The question it answers: what does it take to retire the page's
own JavaScript engine and brain, so that the C++ core is the only thing that
makes the sound and the picture, on the site and in the plugin?

## In short

The site already plays the compiled core by default. What keeps the
JavaScript engine alive is not the site; it is **the tests**. Parity holds the
core to the page's JavaScript sample for sample, and 47 of the web
suites open the page on `?brain=js` to read that JavaScript directly. So the
work is mostly test work: give every check something else to stand on, then
switch the old engine off, then delete it. About 8 to 15 working sessions,
in six steps, each of which leaves the site and the plugin shippable.

## 1. What is left

The page's script is 25,195 lines. Measured by its own section markers:

| Area | Lines | Runs on the site today? |
|---|---|---|
| The sound engine: the envelope and the generator's per-sample loop (`makeEnvelope`, `makeGeneratorCore`, with its voices, effects, reverb, delay, phaser) | 2,936 | Only on `?brain=js` with `?core=js`, or in a browser with no WebAssembly |
| The wrappers that let the page's brain drive the compiled engine (`makeWasmCore`, `makeWorkletCore`, `makeMainCore`) | 267 | Only on `?brain=js` |
| The page brain's audio plumbing: its generator and effects worklets, its generator "voice", its live-input insert | about 1,000 | Only on `?brain=js` |
| The picture engine's JavaScript (`makePictureEngine`) and the setup codec's (`encodeSetupHere`, `decodeSetupHere`) | about 200 | Only as fallbacks |
| **Engine code that goes whole** | **about 4,400** | |
| The page's brain: keyboard and voices, the matrix and its fades, the clock, the arpeggiator, the score, the hearing, Scan, the morph, the picture's sources and stage | about 4,400, interleaved with the controls that show them | Partly - see below |

So retiring the engine removes about a sixth of the script outright, and
up to a third once the brain's half is done.

The brain is the harder half, for a reason that was not obvious until the frame loop was
read. On the default site the page **still steps its own brain every
frame, beside the instrument's**: `applyModMatrix` calls the hearing, the
score, the arpeggiator, the photocell, the picture's sources and Scan on every
frame whatever is playing. Some of that is needed - the fade's dot and the
modulation cards' moving dots follow the page's own reckoning of the routes
(5m, "the fade's dot stood still"), and the page still runs a picture
engine of its own on the main thread, which looks like a second grid beside
the instrument's, not yet confirmed - and some of it returns at once because the source is the
instrument (`scanStep` asks for a tone and leaves). Nobody has listed which is
which. That list is step 1.

What already runs only in the core: the sound on the site (since 5m), the
plugin entirely, the instrument's own picture grid and Scan (5p, 5u), the
hearing on the audio thread (5t), the arpeggiator on the audio clock, MIDI
out, the morph's walk and the host's parameters (5v), and the setup codec
(5e, with the page's kept as a fallback).

One prototype runs *only* on the page's brain: the constellation (ways to
draw, step 2, 12 Nov). On the default site it links to
`?brain=js&draw=constellation`, because what it lays in the grid is the
page's and the instrument never sees it. It has to have a home before the
switch can go (step 4).

## 2. What parity becomes

Parity (`core/tests/parity.py`, 6,791 lines, 26 sections, 928 checks, 22 minutes on this container) does two
different jobs today, and only one of them needs the JavaScript:

- **The port is the same as the original.** The envelope, the generator, the
  keyboard, the matrix, the clock, the level, the capture, the beam's walk,
  the picture's sources, Scan, the hearing, the score, setup codes. Each runs
  a scenario through the page's function (lifted by name, 2,534 lines of
  JavaScript harness) and through the C++ (3,409 lines), and compares.
- **The face and the core agree.** The page's `restore` against the core's,
  every menu, slider and switch against the core's panel, the hands' links,
  the view, the compiled module being the one the page carries, the bridge.
  These compare the page's *face* with the core, not its engine, and they stay
  whatever happens.

Once there is no JavaScript engine, the first job has nothing to compare
with. The options:

| Option | What it is | For | Against |
|---|---|---|---|
| **Golden renders** | Record what the JavaScript produces for every parity scenario today, check it in, and compare the core with the file instead of the page | Keeps every scenario parity has; catches any change to the sound you did not mean, to the same 1e-12; needs no JavaScript | A file only says "this changed", never "this is wrong". Every intended change to the sound means regenerating it, and a regenerated file is believed, so the review moves to the diff of a number dump |
| **Freeze the JavaScript as an oracle** | Copy the engine out of the page into `core/tests/oracle/` and keep lifting from there | Nothing to build; parity unchanged | A second copy that nobody changes is the drift parity was built to prevent, the other way round: every new feature in the core has no reference, so the oracle covers less each week. Worth it only as a bridge |
| **The core's own tests** | Checks written against what the sound should be - "Spread nought is the same to the bit", "Size's T60 by its law", "the limiter turns 17.26 into 0.961" - run on offline renders of the core | These are the checks that say *wrong*, not *different*; most already exist in the web suites, against the page in a browser | They have to be written, one property at a time; a property nobody thought to state is not held |
| **A mix** | Golden renders for regressions, the core's own tests for meaning, the face-and-core checks as they are | Each covers the other's blind spot | Two kinds of test to keep, though both are smaller than parity is now |

**Recommendation: the mix**, with the frozen oracle only for the days between
steps 2 and 5, so that the golden files are checked against the live
JavaScript before the JavaScript goes.

What would still catch the bugs parity has caught? Reading its record in
`PLAN.md`, they were of three kinds:

1. *The port differs from the original* - the drawing's readings, the lane
   order, the bank arriving a slot short. Golden renders catch every one of
   these, and after retirement there is no port to differ.
2. *Both differ from what was meant* - the comparison that skipped NaN, a run
   the page answered with NaN and the core with memory read past a vector.
   Parity caught these by accident of having two implementations; golden
   renders would have frozen them in. These are the core's own tests' job, and
   the NaN rule (`worst()`) goes with the golden comparison.
3. *The face and the core disagree* - a hosted page with no generator, a menu
   only the page has, the panel at the wrong detent. These are the second job,
   which stays.

The honest loss is kind 2. Two implementations written apart disagree where
one of them is wrong; one implementation and a file agree with themselves.
The null tests (CLAUDE.md) and mutation passes are what replace it, and they
are already the house rule.

## 3. The tests

Of the 95 suites in `run.py`, 47 open the page on `?brain=js`
(33 wholly, the rest for one leg). By what they check:

- **About two dozen check numbers the engine makes** - the alias, the
  drawbars, the filter, the plane, the pulse, the envelope, the layers, the
  matrix, the clock, the morph, Scan and the strike, the loop. Their
  assertions are worth keeping; the browser is not. They move to offline
  renders of the core, as `responsetest.py` already does (`response_cpp`: a
  setup code and timed MIDI in, numbers out, at 48 kHz, no browser). A check
  that took a page, a worklet and real seconds then takes a fraction of a
  second.
- **About ten check the page's brain as a page** - its keyboard, its gate
  flag, its LFOs set by hand, `genSet` and `restore()` called directly. Each
  check either becomes a click on the default (the README's rule: "a check
  meant for the instrument clicks the button") or goes, because it tested
  something only the page's brain had.
- **Two exist only to compare the two engines**: `wasmtest.py` and
  `worklettest.py`. They go, and with them the `?core=js` fallback's checks
  in `braintest.py`.
- **About a dozen have one `?brain=js` leg** beside a default one (the fade,
  Enlarge, the overlay, the photocell, the modulation row, the constellation).
  The leg goes or moves to the default.

Time, measured on this container today (`run.py`, three at a time):


| | Minutes |
|---|---|
| Web suite, whole (12 Nov, this container) | 55.9 |
| - the 39 serial suites, alone | 44.2 |
| - of which the 33 suites wholly on `?brain=js` | 15.0 |
| - and the serial suites with one `?brain=js` leg | 11.6 |
| - the 56 parallel suites, three at a time | 11.7 |
| Parity | 22.2 |
| **A full check before a push** | **78** |

(The README's 36 to 37 minutes for the web suite is from before the last
week's suites; it takes 56 now. The run went 92 suites green and 3 red -
`picturepresets`, `loop` and `honesty`, each a judgement over real seconds
on a plan that changed no code, so the timing flakes those suites are
marked serial for.)

What would go: the 33 whole `?brain=js` suites' checks move to offline
renders, which run in seconds rather than minutes, so most of their 15
minutes (and about 4 of the pool's) goes; `wasmtest.py` alone is 6.6
minutes of suite time and goes entirely. The one-leg suites lose a leg, a
few minutes. Parity loses its JavaScript runs but keeps the browser it
needs for the page's `restore`; what that saves was not measured and is part
of step 1. A fair estimate: **from about 78 minutes to about 55 to 60.**

That is a real saving but not the big one, and it should not be oversold.
The longest suites are on the default already and listen over real seconds:
`honesty` alone is 10.3 minutes, `picturepresets` 4, `loop` 4, `perform` 3.2,
`noise` 2.9. Once the offline render exists (step 3), the same move -
judging a preset's sound from the core rendered offline rather than a page
playing in real time - would take most of those too, and would end the
timing flakes with them. That is the larger lever on the suite's time, and a
natural next stage after this one.

## 4. The order

Each step is shippable on its own: the site and the plugin work after it, and
the full suite and parity pass.

1. **The inventory** (no behaviour change). Record which of the page brain's
   per-frame functions do anything on the default site, with a counter each,
   over the full suite; and sort every `?brain=js` check into *numbers*,
   *page* and *engines compared*. *Removes:* nothing. *Checked by:* the list,
   which the next steps are measured against. **Done (13 Nov):
   `STAGE5-INVENTORY.md`** - the counters (`brainCount`, `braincounts.py`,
   `run.py --brain-counts`), what works on the default site (the page's own
   picture grid on every frame, the face reading it), 1,165 checks sorted, and
   what it changes in steps 3 and 5.
2. **Golden renders.** Parity writes what the JavaScript produced for each
   scenario into `core/tests/golden/`, and gains a mode that compares the core
   with the files. For as long as both exist, it compares all three, so the
   files are proven against the JavaScript before they replace it. *Removes:*
   nothing yet. *Checked by:* the files agreeing with the live page, and a
   null - one value in a file changed - failing. **Done (13 Nov):
   `core/tests/golden_runs.py` and `core/tests/golden/` (README there).** What
   was decided, below.
3. **The suites, one batch at a time.** The *numbers* checks go to offline
   renders of the core (a general `render_cpp` grown from `response_cpp`); the
   *page* checks to clicks on the default; the *engines compared* checks go.
   Each moved check is null-tested as it lands. *Removes:* `?brain=js` from
   each suite in the batch. *Checked by:* every moved check seen to fail on a
   known-wrong value, and a mutation pass on the core per batch.
   **Batch 1 done (13 Nov): `cap`, `scale`, `schema`, `hands`, `hand`, `keys`,
   `lane`, `contract`, and the Enlarge and overlay legs** - `?brain=js` page
   opens from 11 to 1 (lane's eight numbers rows wait for `render_cpp`), 344
   checks to 318 and parity +5; six kinds of check found passing on the
   default for the page's reason (or reading silence on both), each rewritten. `STAGE5-INVENTORY.md` section 6 and its
   "Batch 1" columns.
   **Batch 2 done (13 Nov): `alias`, `drawbar`, `pulse`, `score`, `shape`,
   `clock`, `layer`, `layerplane`, `layerpicture`** - their numbers rows as
   assertions on the core alone in `core/tests/pieces/` (parity's last
   section, or `pieces/run.py` in a minute), 304 checks with their nulls;
   web checks 290 to 122, `?brain=js` opens 9 to 4 (the clock's and score's
   panels, which draw the page's own brain, shape's survey and layer's
   learned split point). No `render_cpp` was needed. Two site defects found,
   not fixed: the learned split point reaches only the face, and a clock byte
   inside a port's note-on loses the note. `STAGE5-INVENTORY.md` section 7.
   **Batch 3 done (13 Nov): `scan`, `strike`, and the rows held for "a source
   held at a value" in `lane`, `mod`, `photo` and `loop`** - 135 piece checks
   with their nulls (scan, strike, lane, mod, photo, loop), web checks 285 to
   176 over the six, `?brain=js` pages 9 to 5 (scan's held run, and mod's,
   photo's and loop's pages for rows outside the batch); a source is held at
   a value in `matrix_cpp`, on the instrument's own screen destinations, so
   still no `render_cpp`. 37 core mutations each seen red, after four checks
   carried from the page were found unable to fail. One site defect found,
   not fixed: Stop does not reach the instrument, so Scan keeps moving under
   a stopped screen. `STAGE5-INVENTORY.md` section 8.
   **Batch 4 done (13 Nov): `env`, `filter`, `harmony`, `midi`, `morph`,
   `onset`, `arp`, `perform`, `plane`, `picturepresets`, and the single legs in
   `fade`, `host`, `menv`, `modrow` and `soundstart`** - 221 piece checks with
   their nulls (env, filter, plane, morph, midi, arp, harmony, onset,
   perform), web checks 496 to 351 over the fifteen, `?brain=js` opens 18 to
   3 (picturepresets' run rows, `render_cpp`'s; harmony's meter rows, below;
   perform's microphone rows, input samples). Still no `render_cpp`. 77 core
   mutations seen red, after nine checks carried from the page were found
   unable to fail. One site defect found, not fixed: a port's notes under one
   running status lose the third. `STAGE5-INVENTORY.md` section 9.
   **Batch 5 done (13 Nov): `render_cpp`, and `loop`, `shape`'s survey,
   `picturepresets`' runs, `input`, `livefx` and `perform`'s microphone** -
   `core/tests/tools/render_cpp.cpp`, grown from `response_cpp` (which it
   replaced, byte for byte) and `instrument_cpp` (whose readings both print
   from `instrument_reads.h`): a setup code, the hands, MIDI at its sample,
   an input, readings at an interval of audio and files of the heard pair,
   lanes and grid; the same to the bit run twice, and reading moves nothing,
   each with its null. 127 piece checks with their nulls (loop's seven
   stability seeds among them), web checks 120 to 36 over the six,
   `?brain=js` opens 7 to 0. 22 core mutations seen red. Every page bound
   held offline, unmoved; the fold's "saturated" exemption, which the page
   leaned on, is not needed. The instrument puts an input through its
   effects; it has no limiter, so the plugin hands a host up to 3.2 times
   full scale. `STAGE5-INVENTORY.md` section 10.
   **Batch 6 done (14 Nov), and with it step 3: `live` whole, the rest of
   `mod` and `photo`, and `budget`** - their numbers in `core/tests/pieces/`
   (live, mod, photo, budget, on a new `budget_cpp`), 80 piece checks with
   their nulls, web checks 168 to 147 over the seven suites looked at,
   `?brain=js` opens 7 to 3. 41 core mutations, 40 red. The core's governor
   gives up exactly what the page's did on every case and every setup, so
   budget moved and nothing heard changes; its cost fit does not carry over
   (WebAssembly's drawbars with seven copies cost 1.7 times the model,
   `web/docs/budget-on-the-core.md`), and nothing was refitted. Two site
   defects found, not fixed: a band split keeps the wish to monitor, and the
   credit no longer says whether an input is monitored. `STAGE5-INVENTORY.md`
   section 11.
   **What is left on `?brain=js` after step 3**, each waiting on a later
   step: the constellation (step 4); scan's held run (Stop), harmony's two
   meter rows (the meter's verdict), layer's learned split point (a site
   defect), clock's LFO card, tempo row and Bar row and score's Stop, hidden
   page and playhead (the page's own lfos, transport and score, which the
   instrument has no reading of), and braintest's own legs with the
   counters' null (step 5); and wasm and worklet, which hold the two engines
   together and go with them (step 5, or 6).
4. **The constellation, and anything else only the page's brain does.** Port
   it to the core (ways-to-draw's own step 3), or keep it as a look-only
   drawing on the page, seen and not heard, until it is ported. The owner's
   call; see section 5. *Removes:* the last reason to open `?brain=js`.
   **Done 14 Nov: removed**, by the owner's decision below. Draw's way, Place,
   Hands and Reseed went from the Keyboard's Draw row, and `drawConstellation`
   and its helpers from the frame loop; the core never had a side of it, and it
   stored nothing, so no setup needed a decode pass (`SETUP_VERSION` is
   unchanged). `constellationtest.py` became `drawgonetest.py`: a code made on
   the prototype's page loads unchanged and the address it handed out opens on
   the one figure, on both brains. The design waits in `ways-to-draw.md`,
   "Removed, 14 Nov". Nothing else was found that only the page's brain does
   and no suite reaches; `STAGE5-INVENTORY.md` section 12 has the counts.
5. **Switch the page's brain off.** `?brain=js` and `?core=js` go; the page
   stops stepping its brain beside the instrument, and the face reads what it
   shows (the dots, the readouts, the photocell's numbers) from the
   instrument's readings. A browser without WebAssembly gets a line saying
   so, as it would from the plugin, instead of the JavaScript engine.
   *Removes:* the switch, the per-frame duplicate work. *Checked by:* the full
   suite on the default, and the step 1 counters at nought.
   **To decide before it, found by step 3's batches:**
   - *Stop* (batch 3): the face's Stop holds the face's screen and tells the
     instrument nothing, so Scan goes on reading a moving grid under a
     stopped screen; whether Stop freezes the instrument's grid or its
     reading, and what the plugin, which has no Stop, does. scantest's held
     run waits on it.
   - *The visual matrix* (step 1): which matrix moves the screen's own
     destinations on the site. scale's three, lane's eight and (batch 4)
     filtertest's sweep of the cutoff follow the answer together.
   - *The picture meter's verdict* (batch 4): the instrument's meter calls a
     still figure with detail "cycling" (0.02 to 0.05 change a frame for a
     held just fifth of the Harmonic tone, where the page's meter reads
     0.0055 and "settled"), because the core's grid flickers frame to frame.
     Pointing the face's verdict at the instrument as it is would show still
     figures as cycling. harmonytest's two meter rows wait on it.
   - *The interval readout* (batch 4): `harmonySaid` reads the face's mirror
     of the generator; it should read the instrument's (`instrument_cpp`'s
     `tone` shows what that reading carries).
   - *The limiter and the meter* (batch 5): the instrument has no limiter
     and hands its meter no limiting, so its "running away" comes only from
     a screen lit past a third, and the plugin's output is unlimited (3.2
     times full scale with the reverb in the loop at full). On the site the
     face's monitor chain limits and clamps the sound and the face's meter
     reads that limiter. When the face's verdict reads the instrument's,
     either the site's limiter reading is handed to the instrument's meter,
     or the instrument gets a limiter of its own (which the plugin wants
     anyway), or the rule is let go. `web/docs/after-stage-5.md`.
   - *The clock's and the score's panels* (batch 2, confirmed by batch 6):
     the LFO card's rate reading, the tempo row and the Bar row draw the
     page's own `lfos` and `transport`, and the score's playhead, Stop and
     hidden page its own `score` and MIDI out, beside the instrument's. The
     instrument posts its oscillators' phase and value but no rate, no tempo
     and no playhead, so either it posts them and the panels read them, or
     the page keeps a clock of its own for the face only. clocktest's seven
     rows and scoretest's three wait on it.
   - *The voices' budget's fit* (batch 6): the governor is the page's to the
     bit, but its costs were fitted to JavaScript; in WebAssembly the
     drawbars with seven copies cost 1.7 to 1.8 times the model (the side
     that glitches) and noise and the filter under half. Whether to refit
     it to the core is the owner's, by ear (`web/docs/budget-on-the-core.md`);
     it does not block step 5.
   - *`syncMonitor` stays* (answered by batch 4): the instrument's sound
     reaches the speakers through the page's own monitor chain, so it is the
     face's audio and not a second brain.
   **5a done (14 Nov): the instrument given what the owner decided it must do
   before the brain goes**, the brain itself untouched (`?brain=js` stays, the
   face still reads the page's own). `STAGE5-INVENTORY.md` section 12.
   - *The limiter* is in the core (`scope/limiter.h`): Chromium's
     DynamicsCompressor and WaveShaper ported in floats, with glibc's `log10f`
     and `powf` carried along so the compiled and native instruments agree;
     last on the heard pair, after the Output and the Width. Parity renders
     the page's own chain in an OfflineAudioContext on the loop's worst
     (reverb full, crossed split at Scan's top, phaser at its top): the same
     to the bit, 576,000 samples each, the reductions to the nine figures
     read. The plugin's output peaks at 0.961 on all seven loop seeds (2.02
     to 3.24 with it off, the nulls), and the host is told its 6 ms. The
     site sounds the same: the instrument's chain has no limiter and a
     backstop for its clamp, which moves a tenth of the samples by one float
     step (1.2e-7, -138 dB); the page's limiter in series was measured and
     refused (its make-up gain, an error 24 to 28 dB under the signal). The
     meter is handed the reduction: a chord of six at -10.1 dB runs away, the
     same with the limiter off wanders, a sine does not.
   - *Stop* holds the picture the instrument reads (`scopeRunning`, sent by
     setRunning on the site only): no capture, fade or strike, the frame
     held. A scanned fifth's table moves 0.00003 a quarter-second stopped,
     0.109 running; on the site scantest's held run reads 0.0001 against
     0.0066 never stopped (the page's own brain: 0.0001 to 0.0002).
   - *The meter* was not flickering more than the page's: at the same
     persistence the grids change alike (0.0064 and 0.0054 a frame); the
     piece had loaded none. The cause is the verdict reading frame against
     frame, each frame one trigger-placed window; it reads change against
     the grid of 45 ms ago now (`METER_EYE`, page and core), which leaves
     what is heard alone. Still figures settle at both persistences, turning
     ones cycle; harmonytest's two rows read the instrument's meter on the
     default.
   - *The clock* is posted (`Instrument::clockServed`, after the readings):
     both rates, the tempo and the slider's, its source, running, the beat,
     the score's on, column and steps, and the limiter's reduction; and the
     meter's verdict. clocktest holds them to the page's own. The bars are
     1.9 beats apart, since the transport's Start is the face's alone - for
     5b, with the plugin's page, which is served none of this yet
     (`web/docs/after-stage-5.md`).
   **5b, first half, done (14 Nov): the face reads the instrument**, the
   switch still in place (`?brain=js` and `?core=js` work as before, and
   every suite that opens them is unchanged). `STAGE5-INVENTORY.md` section 14.
   - *The picture.* The instrument posts what the face shows of its picture
     (`Instrument::faceServed`, 24 values: the meter's verdict, change and
     eye's rate; the photocell's value and reading; the shared stage's Glow,
     Motion, Memory and hold; the picture's six sources; the offsets its
     matrix wrote on the screen's own destinations; the figures laid out),
     published with the oscillators. The page writes it into its own
     `photo`, `pictureStage` and `picture` as the readings arrive
     (`takeFace`), and with it in hand steps neither `pictureStep` nor
     `photoStep`: the Picture section's bars and held loop, the photocell's
     card and reticle and the readout's and overlay's verdict (`loopVerdict`)
     are the instrument's. The page's grid is still faded and deposited (the
     score, the overlay's tests and Scan's tone source read it); it goes in
     the second half.
   - *The visual matrix* is the instrument's: the turn, the lag, the trace
     filter, the zoom, the trigger point and the first two lanes' full scale
     are drawn at the offsets it posts; the morph's fader and a lane past the
     second are not posted and the page still sums them.
   - *The clock.* The LFO cards' rates, the tempo row, the Bar row and the
     score's playhead read `source.clock` (`instrumentClock`); the page's
     transport, locks, delay-follow and score do not step while it is there.
     The Bar row's Start and Stop reach the instrument (`transportPlay`, a
     press the core handles and does not keep), and so does a tap: the tempo
     as the slider, then `tempoTap` (the locked oscillators restarted, the
     one), which until now reached the page's clock alone.
   - *The plugin's page* is served the same: `lfos.bin` carries the clock's
     twelve and the face's twenty-four after the envelope, read by the same
     `servedReadings` as the site's `brain_readings`.

   **Left for 5b's second half:** the boot (the page's ~20 frames on its tone
   source), the page's grid and its remaining per-frame steps (`hearingStep`,
   `arpTick` with the face reading the instrument's notes, `morphStep`, the
   fade and its dot, which need the instrument's fade state posted),
   `harmonySaid` from the instrument's tone and `sourceFigures` from its
   figures; then the switches themselves, the suites' last `?brain=js` legs,
   braintest :175/:178, the counters at nought with a standing check, and the
   line for a browser without WebAssembly.
6. **Delete.** The engine, the wrappers, the page's worklets, the fallback
   codec and picture engine, parity's JavaScript harness (`*_js.mjs`,
   `js_core.mjs`), and the README's and PLAN's paragraphs about two brains.
   Parity is renamed for what it is now (the core's tests, with the golden
   files and the face's agreement). *Removes:* about 4,400 lines of the page
   and 2,500 of harness. *Checked by:* the full suite, the core's tests, and
   `extract.py` plus `node --check`.

**The riskiest is step 5.** Not because the sound changes - it does not; the
site already plays the core - but because the face quietly leans on the
page's brain for things it shows. That is how 5m went: flipping the default
turned up 109 failures, of which the fade's dot, the cards' readouts, layer B
not drawn and the quiet screen's explanation were all the face reading the
wrong brain. Step 1's counters exist to find those before step 5, not during
it. The second riskiest is step 3, by volume: it is most of the work, and a
moved check that passes for the wrong reason is exactly the kind of test this
repository has shipped eight times.

## 5. How new work is prototyped afterwards

Today a new idea is cheapest as page JavaScript on `?brain=js`, heard at
once, ported later. After this, there are three ways, by what the idea is:

- **It only changes what you see** (a way of drawing that Scan does not read,
  a readout, a panel). Write it in the page, as now. The face stays
  JavaScript; nothing here touches that.
- **It changes the sound, and you want to know if it is worth having.** An
  offline sketch: render the core with a setup and a performance (the same
  `render_cpp` as step 3), dump the phosphor grid frame by frame and the
  sound, and try the idea in Python on those files, as the Scan experiment
  did (`web/docs/scan-experiment/`). Seconds to rerun, a WAV to listen to, no
  build. This is how Scan itself was decided.
- **It is worth having, and you want to play it.** Write it in the core, behind
  a field the setup does not store, build the module (`core/wasm/build.py`)
  and play it on the site. That is a C++ edit and a rebuild where it used to
  be a page edit and a reload, but there is no port afterwards, no parity
  scenario to write against a second copy, and the plugin has it the same day.

The constellation would have been the second, then the third.

## 6. Risks and what it costs

What the page's engine does better today, honestly:

- **Debugging.** A breakpoint in `makeGeneratorCore` stops in the browser's
  devtools with every variable in view; the compiled core is a black box from
  the page, debugged natively under `g++` and `gdb` through the offline
  render instead. For sound bugs that is fine; for a bug that shows only live,
  in a browser, it is slower.
- **Iteration speed for heard experiments.** A page edit is heard on reload.
  A core edit needs the wasm build: 21 seconds here, for an 836 KB module, before the page is reloaded. Small, but not nothing, and it
  needs the toolchain (the cloud setup installs it; a laptop needs clang's
  wasm32 target and the WASI libraries).
- **Browsers without WebAssembly in an AudioWorklet.** Every current
  Chrome, Edge, Firefox and Safari has both; the JavaScript fallback serves
  only very old browsers. After step 5 they get a message instead of a sound.
- **Latency.** No loss: notes reach the instrument at the top of the next
  128-sample block (under 3 ms), which `?brain=js` did not beat, and the
  arpeggiator moves from the page's timers to the audio clock.
- **Kind 2 bugs** (section 2), which two independent implementations caught
  by disagreeing. The replacement is discipline - nulls and mutation - rather
  than structure.

What the owner gets: one engine; a change made once, in C++, with no port and
no parity scenario against a second copy; roughly a quarter of an hour off a full run; about
7,000 fewer lines between the page and the harness; and the README's
"two brains" sections gone, which are a fair share of why the repository is
hard to read.

## 7. Recommendation and size

Do it, in the order above, with golden renders plus the core's own tests
replacing parity's comparison, and decide the constellation's home (port it,
or keep it look-only) before step 5.

| Step | Sessions |
|---|---|
| 1. The inventory | 0.5 |
| 2. Golden renders | 1 |
| 3. The suites | 4 to 8 |
| 4. The constellation | 0.5 (look-only) to 3 (ported) |
| 5. The brain off | 1 to 2 |
| 6. Delete, and the docs | 1 |
| **Total** | **8 to 15** |

A session here is a few hours with one full run at the end. The uncertainty is
almost all in step 3: two dozen suites whose checks move one by one, each with
its null, and some will turn up a check that was passing for a reason of its
own. If step 1 finds the face leaning on the page's brain in many places, step
5 grows by a session or two.

## Decided (the owner, 12 Nov)

- **Go ahead**, in the order above, with golden renders plus the core's own tests
  replacing parity's comparison.
- **The constellation is removed for now** (step 4), not kept look-only: as built it
  draws each note from a description rather than its sound, which is the real fault
  (`web/docs/ways-to-draw.md`, "The prototype's shortcut"). It comes back after this
  stage, built on each voice's real cycle sent from the core, with the painting's brush.
- Step 1 starts once the note-click fix and the picture's swell have landed, so this
  stage does not collide with them.

## Step 5 decided (the owner, 14 Nov)

The questions step 3's batches left for step 5 (its list, above), answered
before it starts:

- **The limiter goes into the core.** The page's limiter is ported to the
  instrument, so the plugin and the site share one: the site sounds as it does
  now, the plugin stops handing its host up to ten decibels over full scale,
  and the picture meter's rule that a strained limiter means running away works
  on the instrument's own meter. Held by parity against the page's limiter
  while both exist, and by a check that the plugin's output never passes full
  scale on the loop's worst renders.
- **Stop freezes the picture the instrument reads.** Scan then plays a held
  picture, so what is seen is what is heard; notes still sound, and only the
  timbre stops moving until Run. The plugin, which has no Stop, is unchanged.
  scantest's held run moves to the default on it.
- **The core's picture meter is fixed, not worked round.** Find why the core's
  grid changes frame to frame on a still figure with detail, measure change as
  the eye sees it, and hold the instrument's verdicts to the page's on the test
  sounds, so a still figure reads settled. harmonytest's two meter rows follow.
- **The instrument reports its clock.** The core posts its LFO rates, the
  tempo and the score's playhead, and the clock's and the score's panels read
  them, so there is one clock and the plugin's panels follow the host's tempo.
  clocktest's seven rows and scoretest's three follow.

Settled without asking, since each has one sensible answer; the owner can
overrule any of them:

- **The visual matrix is the instrument's.** The face follows the destinations
  the core's own matrix moves on the screen (`screen.h`, which batch 3 found
  enough), and the page's second matrix goes with its brain. scale's three,
  lane's eight and filtertest's cutoff sweep follow together.
- **The interval readout reads the instrument** (`harmonySaid` from the
  instrument's tone, not the face's mirror).
- **The voices' budget is not refitted in step 5.** Its governor is the page's
  to the bit; refitting its costs to the core changes what thins under load,
  which the owner hears first, after this stage
  (`web/docs/budget-on-the-core.md`, `web/docs/after-stage-5.md`).

## Step 2 settled (13 Nov)

The golden layer is `core/tests/golden_runs.py`; the files are
`core/tests/golden/*.json.gz` with a `README.md` beside them. Parity is
unchanged but for a `golden.section(...)` call in place of each section's
`print`, which names the file a port-is-the-original section's runs belong to.
What was decided, and the cost:

- **Which sections get a file.** The thirteen port-is-the-original sections
  only: the envelope, the waveforms and functions, the generator, the keyboard,
  the matrix, setup codes, the clock, the level, the capture, the beam, the
  picture's sources, Scan, the hearing, the score. The face-and-core sections
  (restore, the morph, the menus and switches, the hands' and the rack's
  panels, the fade, the view, the WebAssembly and compiled-instrument checks)
  get none and are untouched: they compare the page's face with the core, not
  an engine, and stay whatever happens to the JavaScript.

- **Format and size.** One gzipped JSON file a section, keyed by tool and a
  hash of the scenario (paths removed, so it travels between checkouts). A run
  is kept whole where that is cheap, and as a *sketch* where it is not - per
  line, the text with numbers removed, and per block of 64 numbers the sum, the
  position-weighted sum and the largest, with any non-finite value kept in
  place. The sketch names the line, block, moved value and gap on a mismatch,
  to the same `1e-12`; what it cannot catch is two values moved within one
  block so both sums cancel, which only the large bulk renders are sketched and
  no plausible port fault produces. Kept whole the files were 75 MB; the sketch
  for the large renders brings the total to **5.3 MB** (5,540,975 bytes across
  fourteen files; the generator and the functions are 1.9 MB and 1.5 MB of it,
  the picture 0.8 MB, Scan 0.4 MB). The existing tolerance and the `worst()` NaN
  rule are carried in unchanged.

- **Regeneration.** `parity.py --write-golden`, one command, which **refuses to
  overwrite a section unless the page and the core agreed on it** that run, and
  rewrites nothing for a section whose runs did not move (so an unrelated change
  leaves the files and the diff alone). Documented in the README and in a
  CLAUDE.md line under the command list.

- **Running time.** Parity was 22.3 minutes with the golden layer off
  (`GOLDEN_OFF=1`, the baseline). The default three-way run - the page's
  JavaScript, the core, the two compared, *and* each run against its golden file
  and the core against the file directly - is **25.9 minutes** (+3.5, about 16
  per cent), the cost of reading the files and the extra section of core-vs-file
  checks. `--golden`, which does not run the JavaScript at all, is **23.0
  minutes**: close to the baseline because the page runs dominate and are gone,
  but the core still renders everything and is compared against the files. Check
  counts: 999 in the three-way run, 985 in `--golden` (the fourteen fewer are
  the JS-vs-core comparisons that have no page under them in `--golden`), 0
  failures either way.

- **Nulls seen red** (plan's three, by hand, plus the standing ones parity now
  runs every time): one value changed in a file - golden mode red, naming the
  scenario, line, value and gap, for a file kept whole and one kept as a sketch;
  the core mutated - both the JS-vs-core comparison and the core-vs-file
  comparison red; a NaN fed into a file - red, whole and sketch.

- **No surprise for the later steps.** The read path (`--golden`) and the write
  guard are in place and exercised; step 3 can move a suite's numbers checks to
  offline core renders against these files as the plan has it, and step 5's
  switch is unaffected. The one thing worth noting for step 6: `--golden` hands
  parity's own comparison the file's text for a whole run, but for a *sketched*
  run it compares the core against the sketch here and lets parity's comparison
  see the core against itself - so when the JavaScript harness is deleted, the
  sketched sections rest entirely on the core-against-file check, which is why
  that check is a section of its own and null-tested.
