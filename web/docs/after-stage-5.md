# After stage 5

Agreed with the owner on 13 November: while stage 5 retires the page's engine
(`plugin/STAGE5-PLAN.md`), anything found along the way that can wait is written
down here instead of fixed, together with whatever the owner finds by playing it.
They are picked up once stage 5 is done, so the stage does not grow sideways and
nothing is lost. Each entry says who found it, when, and what is known so far.

## Defects on the site

- **Learn's split point does not reach the instrument.** On the default page,
  learning a split point moves the face's point only; the core keeps splitting at
  C4. Found by step 3's batch 2 (13 Nov), recorded in `STAGE5-INVENTORY.md`. A
  player would hit this.
- **The morph's two ends live only in the face.** The page stores A and B from
  its own sliders and walks them itself, sending each slider as a hand's; the
  instrument has a morph of its own (`morphStore`, `Instrument::storeMorph`)
  that neither the site nor the plugin's editor ever stores into. So in the
  plugin a host automating the morph fader with the editor shut moves nothing,
  and a project reopened has no ends. Found by step 5b's second half (14 Nov),
  which kept the page's walk for that reason (`morphStep`). The fix is to send
  the stores and let the instrument walk, which the core can already do.
- **Lanes three to six have no full scale in the instrument.** The core
  registers `view.scale1` and `view.scale2` as destinations and no others
  (`screen.h`), so a routing onto lane three or four's full scale, which a
  split drawing a figure a hand offers, is heard by nothing. Until 5b's second
  half the page scaled the face's lanes alone; since then the face shows what
  the instrument does, which is nothing. Registering them in the core would
  change what Scan reads for a setup that routes them, so it was left for a
  decision. Found 14 Nov.
- **Stop does not end the instrument's MIDI-out notes.** Stopping the scope
  ended the sounding note and sent all-notes-off on the page's own score (the
  check scoretest held on `?brain=js`); the instrument's score sends neither
  on Stop. Hiding the page still sends all-notes-off. Found when scoretest was
  moved to the default, 14 Nov.
- **A MIDI clock byte inside a note-on loses the note.** The page's `midiBytes`
  cuts at every status byte and the core's keyboard drops the half message.
  Web MIDI and the plugin's host hand over whole messages, so in practice this
  can hardly happen; low priority. Found by batch 2 (13 Nov).
- ~~**Stop does not hold the instrument's picture, so Scan goes on moving with the
  screen stopped.**~~ Fixed in step 5a (14 Nov), as the owner decided: Stop tells the
  instrument (`scopeRunning`), which holds the picture it reads; scantest's held run is
  on the default page and reads 0.0001 held against 0.0066 running. What was found: On the default page Stop (`setRunning(false)`) holds the
  face's screen and stops what the score and the arpeggiator sent, and tells
  the instrument nothing: it goes on drawing its own grid and Scan goes on
  reading it, so a scanned fifth's timbre keeps wandering under a stopped
  screen (0.0084 held against 0.0079 running, where the page's own brain
  holds still at 0.0001-0.0002). Scan's docstring, the first-minute test and
  striketest's description of Stop ("which holds the screen and so the
  tone") all say it should hold. Whether Stop should reach the instrument -
  freeze its grid, or its reading - is the owner's call, and the plugin,
  which has no Stop, may want the same answer. Found by step 3's batch 3 (13
  Nov); scantest.py's held run stays on `?brain=js&core=js` until then.
- **A port's notes under one running status lose the third.** A message
  carrying several notes under one status byte (`90 3C 64 40 64 43 64`) is cut
  by the page's `midiBytes` into three-byte pieces, and the core's keyboard
  drops the half message: in Mono the face holds 60, 64 and 67 and the
  instrument plays E4 (329.6 Hz). The same mechanism as the clock byte above;
  low priority, since Web MIDI hands over whole messages. Found by step 3's
  batch 4 (13 Nov); miditest's running-status row reads the face's stack and
  says so.
- ~~**The instrument's picture meter calls a still figure "cycling".**~~ Fixed in step 5a
  (14 Nov): the grid was not at fault - at the same persistence the two grids change
  alike, 0.0064 and 0.0054 a frame, and the piece had loaded none where the page loaded
  the old library's 0.12 - but the verdict read change frame against frame, and each frame
  is one trigger-placed window that a figure with detail lands in a little differently.
  The verdict reads change over the eye's time now (`METER_EYE`), page and core;
  harmonytest's rows are on the default. What was found: A held
  just fifth of the Harmonic tone reads 0.02 to 0.05 change a frame on the
  instrument's own meter (the page's meter, on the page's own grid: 0.0055,
  "settled"); a still unison of the same tone 0.058; a plain sine's unison
  nought. So the core's grid flickers frame to frame on a figure with detail.
  Nothing heard reads the verdict (the stage uses only "running away"), but
  once the face's verdict reads the instrument (step 5), still figures would
  say "cycling". Whether the grid or the meter is at fault is not known.
  Found by batch 4 (13 Nov); harmonytest's two meter rows stay on
  `?brain=js` until it is decided.
- **The generator still sounding 400 ms after it was set silent.** Strike's
  null once failed with readings reproduced exactly by a generator left
  audible, as if `genSet("amp", 0)` had not landed. It could be a race between
  the page and the audio engine; it did not recur in four runs alone. Found by
  the flaky-test pass (13 Nov).

- ~~**The plugin's output is not limited, and the instrument's meter never
  hears a limiter.**~~ Fixed in step 5a (14 Nov): the page's limiter and clamp are
  ported to the instrument (`scope/limiter.h`), the same to the bit as the browser's
  nodes, and its reduction is the meter's. What was found: The instrument (`scope/instrument.h`) has no limiter of
  its own: on the site the face's monitor chain (limiter and clamp,
  `syncMonitor`) holds what the speakers get, but the plugin hands its host
  the heard pair as the core makes it. Rendered offline with the loop at its
  top (`core/tests/pieces/loop.py`), it peaks at 0.94 to 1.09 plain, 2.02
  with the phaser at its top, 2.74 with a crossed split at Scan's top and
  3.24 with the reverb at full - ten decibels over full scale into a DAW.
  And since the instrument hands its picture meter no limiting, the meter's
  rule that a strained limiter means running away never fires there.
  Found by step 3's batch 5 (13 Nov); step 5's list has the decision.

- **A band split keeps the wish to monitor, and gives it back unasked.** On
  the default page, a declared line input monitored, then split into bands,
  is taken off the speakers (the level in front of the monitor chain shuts),
  but the wish survives: the Monitor box stays ticked and enabled over a split
  nobody can hear, and pressing Whole again monitors the input at once,
  without being asked. The page's own brain dropped the wish with the split
  and greyed the box, and its rule ("calling it a line input again starts
  from off rather than resuming") is written against exactly this. Nothing
  unsafe is heard - a microphone is still never monitored - but the face says
  monitored over a split, and a player can be put on the speakers by a press
  that was about the picture. Found by step 3's batch 6 (14 Nov);
  livetest.py's split row holds the half that is right and says so.
- **The site's credit line no longer says whether a live input is
  monitored.** The page's own microphone source said "not monitored" over a
  band split and ", monitored" on a monitored line input; the instrument's
  credit (`makeBrainSource`'s `describe`) names the bands or "drawing your
  input" and says nothing of the speakers. The effects' line still says it
  ("On your input, drawn and heard."), and the Monitor box does, so this is a
  wording to put back, low priority. Found by batch 6 (14 Nov).
- **A reticle that is not a number makes the core's photocell climb past
  one.** With the reticle's position not a number (the `photoReticle`
  control without a comma, or a value that does not read), the core's
  photocell reads NaN and its slewed value, `std::fmin` dropping the NaN,
  climbs by the slew limit every frame - past one, to eight in four seconds.
  The page's JavaScript goes to NaN there instead (`Math.min` keeps it), so
  this is also a place the two disagree that no golden file holds. The page
  only ever sends two numbers, so on the site it cannot happen; low priority.
  Found by batch 6 (14 Nov), when a piece of mine sent numpy's repr of a
  float and a check went red on it.

- ~~**The bar's Start and Stop reach the face's clock only.**~~ Fixed in step 5b (14 Nov),
  since the switch could not be made without it: the Bar row reads the instrument's clock
  now, so Start and Stop go to it (`transportPlay`, a press the core handles and does not
  keep in a state), and so does a tap, which reached the page's clock alone too: its tempo
  as the slider, then `tempoTap` (the locked oscillators restarted and the one). What was
  found: `transportPlay` is not a
  hand the instrument is sent (it is in neither HOST_CONTROLS nor HOST_CLICKS), so the
  instrument's bar runs from when the instrument was made and the face's from its own
  Start: clocktest's new rows found them 1.9 beats apart, going at the same tempo. Until
  5b nothing heard reads the face's bar (the instrument's score and arpeggiator play on
  its own), but once 5b points the Bar row at the instrument's posted beat, the face's
  Start must reach it or the button will appear to do nothing. Found by step 5a (14 Nov).
- **What Scope & measure's "Speakers get: Shaped" adds after the instrument is not
  limited.** Since 5a the instrument limits its own output and the page's chain for it has
  no limiter, only a backstop that is the identity up to 0.995 and holds anything above
  under one. With the speakers on the shaped side, the trace filter (up to 18 dB of
  resonance), the coupling, the lag and the rotation still act after the instrument, and a
  resonant peak there is caught by the backstop rather than compressed. Default is *Input*,
  where the chain is the identity. Whether those belong in the instrument (they are the
  face's measuring tools) is a question for after stage 5. Found by step 5a (14 Nov).
- ~~**The plugin's page is not served the instrument's clock or meter.**~~ Fixed in step 5b
  (14 Nov): `lfos.bin` carries the clock and what the face shows of the picture after the
  envelope, read as the site's are (`servedReadings`). What was found: 5a posts them on
  the site (`brain_readings`); the plugin's page has `lfos.bin` and gets neither, so 5b
  must serve `Instrument::clockServed` and the meter's verdict there too before its panels
  read them. Found by step 5a (14 Nov).

- **A browser that will not make the module on the main thread now waits.**
  The worklet makes the instrument from the module, and the main thread makes
  its own copy for the setup codec the face reads the instrument's state by.
  Until stage 5's step 6 a main thread that refused (`new WebAssembly.Module`
  throwing) fell back to the page's JavaScript codec and the site played on;
  that codec went with the page's engine, so such a page now waits and says
  why (wasmtest.py). Every current Chromium, Firefox and Safari makes it, so
  nobody is known to hit this; a codec that took the module from the worklet,
  or decoded there, would remove the case. Found by step 6 (14 Nov).

## Sounds and presets

- **The plugin is 1.7 dB louder since 5a, and limited.** The page's limiter has a make-up
  gain (Chromium's, at -3 dB and 20:1: 1.218 on everything), and the site has always had
  it; the plugin now does too, so a quiet sound in a DAW is 1.7 dB louder than before
  5a, and the loudest are held under 0.99 where they reached 3.2. The owner may want to
  hear it in a host; nothing on the site changed. Found by step 5a (14 Nov).

- **Bass under the tine piano and Bass under the pad sit on their headings'
  edges with the reverb switched on.** Rendered offline through the core, the
  tine piano reads 0.009 to 0.019 against Settled's 0.015 depending only on
  where the key lands, and the pad 0.020 to 0.025 against Breathing's 0.02
  floor. The test measures truly; the presets are the question. Parked with the
  owner's decision on the Tine piano (12 Nov). `core/tests/tools/honesty_cpp.cpp`
  measures it.

- **The voices' budget's costs were fitted to JavaScript.** The governor is
  the page's to the bit, but on the core natively pink noise costs 0.35 to 0.47
  of what the model says and the filter about half (the safe side), and in
  WebAssembly the drawbars with seven copies cost 1.7 to 1.8 times (the side
  that glitches, harmless today only because the core does the same work in
  about half the time). Refitting changes which voices thin under load, so the
  owner hears it first (14 Nov). `web/docs/budget-on-the-core.md`.

- **The old library's Glass pad gives up a copy a hand under a full chord.**
  budgettest's "no preset gives anything up" copied each setup's generator
  fields and left its routings out; with them counted, Glass pad's
  `env.note>gen.fm` costs FM and under eight notes a hand its unison goes
  from five copies to four, on the page's governor as on the core's. The
  bank gives nothing up either way, and the old library is a test corpus,
  not something offered, so this matters only if Glass pad comes back. Found
  by batch 6 (14 Nov); `core/tests/pieces/budget.py` counts the routings now.

## Tests

- **The loop suite's fold check** passed only through its "saturated"
  exemption on the crossed split and the reverb at full, reading 0.032 to 0.043
  against a 0.05 bound, and went red when a run missed saturation. It needs a
  better rule for what passing means, not a moved bound. Its Scan read-count
  check counted timer reads in real seconds and once failed at exactly its
  bound. Since batch 5 (13 Nov) both are `core/tests/pieces/loop.py`'s,
  rendered offline and the same every run: every seed moves the fold by 0.30
  to 0.50 and passes without the exemption, Scan's table moves by a median of
  0.082 to 0.335 a tenth against the 0.02 bound, and the read count is always
  297 of 300. The exemption and the bounds are kept as they were, the owner's
  to change.
- **`corpus.held_tone` leaves the site's instrument at the note's pitch.**
  It presses A3 and puts the Frequency slider back in the same tick, and on
  the default page the slider's message reaches the instrument before the
  note-on, which then plays its own 220 Hz: the face says 440 and the
  instrument plays 220. modtest's octave sweep went red on it once it moved
  to the default (110 to 438 Hz); it moves the slider again once the note
  has landed. Other suites that read the pitch after `held_tone` on the
  default have not been looked at for it. Found by batch 6 (14 Nov); batch 2
  found the same race in aliastest.
- **The hand suite's split fit** does not go red for the lower hand with the
  bass a semitone off (the upper hand's does): at 131 Hz a semitone moves the
  fit too little in a 10 ms window. Noted at the site by batch 1.

- **Two checks that failed under load in step 4's full run (14 Nov) and
  passed alone twice each**, neither on the known-flaky list: scan's *on the
  site's instrument, the turning fifth read back moves its timbre* (0.0038)
  and arp's *a key held through an arpeggiated setup and into a plain one
  sounds at the plain one's level* (0.4172 against 0.3850). Neither suite
  touches anything step 4 changed. Worth watching for a second time before
  either is added to the list, or made to tolerate a loaded machine.
- ~~**Hearing's *all of it costs under two milliseconds a frame on average***~~
  Gone with the page's hearing in step 6 (14 Nov): the hearing is the
  instrument's, whose cost is the core's budget's. What was found:
  has no headroom on the cloud machine: alone, the commit before stage 5,
  step 5b measured 1.59, 2.00 and 2.04 ms, and 5b's first half 1.74 to 2.16
  (14 Nov). `hearingStep` is unchanged by 5b, so it is the machine's main
  thread, not the hearing, that moves it. It goes with the page's hearing in
  5b's second half or step 6; until then it is a timing check that fails
  about half the time alone, and is not loosened here.
- **A suite that sets the page's state by hand** - a routing list filtered or
  assigned, `state.persistence`, `state.beamXY`, `setMidiMode` without its
  button - tells only the page. Since 5b's second half the face draws and
  reads the instrument's grid, gains and voices, so such a suite reads an
  instrument that never heard it: phototest, hearingtest, layertest and
  facetest's first drafts were caught this way and fixed with the controls or
  `hostRoutings()`/`hostSendSetup()`. The others have not all been looked at.
- **A suite that drops a routing by filtering `state.modRoutings`** tells
  only the page, while `addRouting` told the instrument too. Before 5b the
  face drew the page's matrix and nothing showed; since, the instrument's
  routings move the figure. phototest's eight photocell routings were found
  this way (14 Nov, fixed with `hostSendSetup()`); other suites that filter
  the list by hand have not been looked at for it.

- **Three meaning checks rest on the recordings alone since step 6.** A note
  added to a chord does not restart the others' envelopes (polytest read the
  page's generator's voices stage by stage), a routing arriving after a rest
  hears the sound as it is (hearingtest read the page's hearing; the core's
  "hear-rest" run holds it too), and the page's fade landing a sound by every
  way it can be loaded (fadetest, on the page's own fade). Each is held by
  core_tests.py's recordings of what the page answered, which say "the same
  as it was", not "right"; each would be worth a piece of its own in
  `core/tests/pieces/`. Found by step 6 (14 Nov).
- **The compiled module carries the generator's bridge for the tests alone.**
  `gen_*` in `core/wasm/scope_wasm.cpp` was the page's worklets' way to the
  core's generator; since step 6 only `web/tests/compiled_core.js` (eighteen
  suites that render the generator in a page) and core_tests.py's "generator
  in WebAssembly" use it. Trimming it would shrink the page and change the
  module's bytes; left for a decision. Found by step 6 (14 Nov).
- **The page still keeps a clock of its own for the tempo slider, a tap and a
  MIDI clock's ticks** (`transport`, `clockTap`, `clockTick`). The face shows
  the instrument's clock since 5b; what is left on the page is the slider's
  value a setup stores, the tap's arithmetic before it is sent, and the
  bookkeeping of a MIDI clock the instrument also hears. Not stepped, and not
  shown; a candidate for the instrument to serve its tap and to drop the rest.
  Also the fade's drawing of a stepped source under the fade (`sourceNow`,
  `stepFade`): a knob's ring for a Key routing is the page's reckoning of the
  fade, where its gain is the instrument's. Found by step 6 (14 Nov).

## Owner's list

- A few minor things from trying the click, swell and Width fixes on the testing
  site (13 Nov), to be written here.
- Offered and not yet answered: a small "Testing" label in the header shown only
  on the testing site, so the two pages can be told apart without reading the
  address.

## Already planned for after stage 5

- Each voice's real cycle sent from the core to the page, which is what brings
  the constellation back honestly (`ways-to-draw.md`, "The prototype's
  shortcut, and what fixes it"). The prototype was removed in step 4 (14 Nov),
  its design kept in `ways-to-draw.md`, "Removed, 14 Nov".
- Closing the painting loop: Scan reading the painting live while the phrase
  plays, and the painting painted from the changed sound
  (`painting-the-sound.md`).
