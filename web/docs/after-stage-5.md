# After stage 5

Agreed with the owner on 13 November: while stage 5 retires the page's engine
(`plugin/STAGE5-PLAN.md`), anything found along the way that can wait is written
down here instead of fixed, together with whatever the owner finds by playing it.
They are picked up once stage 5 is done, so the stage does not grow sideways and
nothing is lost. Each entry says who found it, when, and what is known so far.

## Defects on the site

- ~~**Learn's split point does not reach the instrument.**~~ Fixed after stage 5 (14 Nov):
  the face sends the learned note as the `splitAt` control before the note itself
  (`hostSendSplit`, `Keyboard::setSplitPoint`), so the key that set the split plays in the
  upper hand there as here, and the instrument keeps it as a hand, so a project reopened
  splits where it was learned. layertest's Learn row reads the instrument's lanes: G3
  learned, A3 is in B's lanes; its null, the send cut, puts A3 in A's. Learn itself stays
  the face's: in the plugin it learns from the screen's keys, since a host's notes go to
  the instrument and not through the face. What was found: On the default page,
  learning a split point moves the face's point only; the core keeps splitting at
  C4. Found by step 3's batch 2 (13 Nov), recorded in `STAGE5-INVENTORY.md`. A
  player would hit this.
- ~~**The morph's two ends live only in the face.**~~ Fixed after stage 5 (14 Nov): the
  face's *A* and *B* are presses the instrument hears (`HOST_CLICKS`), and it stores the
  ends from its own sliders and writes them into the setup its state is made from
  (`Instrument::keepMorph`), so the instrument walks the morph, a host automating the
  fader with the editor shut moves the sound, and a project reopened keeps its ends. The
  page's walk (`morphStep`) stays, as the face's view of the instrument's: it puts the
  face's knobs where the instrument's fader puts them, every handler run and nothing
  sent, since the instrument serves no slider it walked; only the instrument's walk is
  heard. setupmorphtest's new row cuts the face's walk and hears 440 halfway from 220 to
  880; its null, the stores kept from the instrument, stays at 880. The plugin's shell
  test stores by the editor's presses and automates the Morph with no editor (B six times
  A's level), and reopens the project; the nulls are the presses left out and the
  project's ends taken out. What was found: The page stores A and B from
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
- ~~**Stop does not end the instrument's MIDI-out notes.**~~ Fixed after stage 5 (14
  Nov): told of a Stop (`scopeRunning`), the instrument ends its score's notes at the next
  step and then sends every note its MIDI out still has sounding and All Notes Off, in
  that order; the page no longer sends its own All Notes Off on Stop while the instrument
  is told. Measured, the instrument's score had been ending its notes at its next step of
  its own accord, after the page's All Notes Off; what it never sent was the panic.
  scoretest's Stop row requires the note-offs, then All Notes Off, then nothing; its
  nulls are the old order, as a literal, and the instrument never told, which plays on.
  On the way: the site's module empties its list of what the instrument sent at each
  block's top, so anything the instrument sends between blocks, from a control's handler,
  is lost - which is why the panic waits for the next step (below, newly found). What
  was found: Stopping the scope
  ended the sounding note and sent all-notes-off on the page's own score (the
  check scoretest held on `?brain=js`); the instrument's score sends neither
  on Stop. Hiding the page still sends all-notes-off. Found when scoretest was
  moved to the default, 14 Nov.
- ~~**A MIDI clock byte inside a note-on loses the note.**~~ Fixed after stage 5 (14 Nov),
  with the running status below: the page cuts a port's bytes into whole messages
  (`midiPieces`), a real-time byte a message of its own wherever it falls, each note
  under a running status given its status byte, so the core's keyboard, which reads
  whole messages as the plugin's host hands them, hears what the face does. miditest
  reads the instrument's pitch in Mono: `90 3E F8 64` plays D4, where the old cut lost
  the note and the one before sounded on. What was found: The page's `midiBytes`
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
- ~~**A port's notes under one running status lose the third.**~~ Fixed after stage 5 (14
  Nov) by the same cut (`midiPieces`): miditest's running-status row now holds the
  instrument, G4 from `90 3C 64 40 64 43 64` in Mono, and its null, the old cut, plays
  E4. What was found: A message
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
- **The generator still sounding 400 ms after it was set silent.** Looked for after stage
  5 (14 Nov) and not reproduced: striketest run nine times, three at a time on the cloud
  machine, and its nulls at Strike nought and B reading its own stayed under its bound
  every time (A's rise -0.006 to 0.007 against the bound of 0.01; nine of nine passed). The suite no longer calls `genSet("amp", 0)` - since step 6 its
  checks run on the instrument, which `genSet` does not reach - so the race, if it was
  one, was between the page's own generator and its worklet, which are gone. Left listed
  in case strike's null fails again. What was found: Strike's
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

- ~~**A band split keeps the wish to monitor, and gives it back unasked.**~~ Fixed after
  stage 5 (14 Nov): the site's source refuses to monitor a split (`setMonitor`), the split
  asks it again (`hostSplit`, `applyMonitor`), and the box is unavailable over one
  (`syncLive`), so the wish goes with the split and Whole starts from off. livetest's split
  row holds both halves, each against the reading before and the old behaviour as a
  literal; run on the old code the two go red. What was found: On
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
- ~~**The site's credit line no longer says whether a live input is
  monitored.**~~ Fixed after stage 5 (14 Nov): "splitting your input into four bands, not
  monitored" and "drawing your input, monitored" (`makeBrainSource`'s `describe`).
  livetest checks both; on the old words both go red. What was found: The page's own microphone source said "not monitored" over a
  band split and ", monitored" on a monitored line input; the instrument's
  credit (`makeBrainSource`'s `describe`) names the bands or "drawing your
  input" and says nothing of the speakers. The effects' line still says it
  ("On your input, drawn and heard."), and the Monitor box does, so this is a
  wording to put back, low priority. Found by batch 6 (14 Nov).
- ~~**A reticle that is not a number makes the core's photocell climb past
  one.**~~ Fixed after stage 5 (14 Nov): a reading that is not a number is no reading, as
  a reticle off the screen is, and the slewed value falls to nought (`photoStep`) - no
  reading rather than the last good one, since a reticle with no position is not on the
  picture. `core/tests/pieces/photo.py` renders the instrument with `photoReticle` "0.5"
  and requires the value never past one and nought once the slew has run; its nulls are
  the same reticle given as two numbers, which reads 0.34, and the old climb as a literal,
  and with the guard taken out it reads eight. What was found: With the reticle's position not a number (the `photoReticle`
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

- **What the instrument sends to a MIDI port between blocks is lost on the site.** The
  site's module (`core/wasm/scope_wasm.cpp`, `brain_block`) empties its list of what was
  sent at the top of every block, so a MIDI-out message sent from a control's handler,
  which the worklet applies between blocks, never reaches the port: a Stop's panic did
  this until it was moved to the next step (14 Nov), and `MidiOut::choose`'s panic, were
  the port's menu ever the instrument's, would too. Nothing else sends from a handler
  today. The fix is to empty the list after the worklet has read it rather than before
  the block; left, since nothing now hits it. Found by the Stop fix (14 Nov).
- ~~**A host parameter moved to the value the page last gave it is not heard.**~~ Fixed
  with the morph (14 Nov): the plugin's processor noted the page's own move of a parameter
  (`pageSet_`) so that the audio thread would not take it for the host's, and never let
  the note go, so a host that later moved that parameter to the same value moved nothing.
  The morph's store made it plain - storing B puts the fader and its parameter at 100,
  and automating the Morph back to 100 after A was heard as the page's - and the shell
  test's row went red on it before the note was spent once seen. Any of the fifteen
  parameters a player had dragged on the page had it too. Found by the morph fix.
- **Learn in the plugin hears the screen's keys only.** The split point is learned by
  the face from the next key it hears (`midiNoteOn`) and sent to the instrument; in the
  plugin a host's notes go to the instrument and not through the face, so pressing
  *Split point* and playing a key on the controller learns nothing until a key on the
  screen is played. The core's keyboard can learn for itself (`learnSplit`), but the
  learned point would then have to come back to the face and be kept as a hand. Found by
  the Learn fix (14 Nov).

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

  *To listen* (15 Nov): `web/docs/listening/index.html`, its first sheet: each
  preset with its reverb switched on beside candidates, each measured against
  its heading over sixteen key times. The tine piano sits clearly inside at
  the switch's own Mix with a darker tail (Tone 30: late at most 0.0134), and
  the pad's bass with its Scan at 30 rather than 25 (least 0.024); a lower or
  shorter reverb was measured too. The Tine piano alone, dry, is there as well.

- **The voices' budget's costs were fitted to JavaScript.** The governor is
  the page's to the bit, but on the core natively pink noise costs 0.35 to 0.47
  of what the model says and the filter about half (the safe side), and in
  WebAssembly the drawbars with seven copies cost 1.7 to 1.8 times (the side
  that glitches, harmless today only because the core does the same work in
  about half the time). Refitting changes which voices thin under load, so the
  owner hears it first (14 Nov). `web/docs/budget-on-the-core.md`.

  *To listen* (15 Nov): `web/docs/listening/index.html`, its last sheet: the
  costs timed in WebAssembly and fitted (drawbars dearer, pink noise and the
  filter cheaper), in a scratch copy only, and two cases rendered under each
  governor - the drawbars with seven copies under a chord in two hands, which
  keep 5 to 7 copies as it is and 3 to 5 refitted, and pink noise through the
  filter at a lowered budget, which lets five held notes go as it is and one
  refitted.

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
