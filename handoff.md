# Handoff

Where the instrument stands, what is decided, what is open, and how to work on
it without rediscovering the last month. Written at the end of P8f
(`2f2165a`, 5 November 2026), and brought up to date at the end of P8g. The plan itself is
`web/docs/making-it-one-instrument.md`; this is the short version and the
loose ends.

## Where it stands

The plan's stages, all on `claude/cool-fermat-t0spde`, which is also the
branch GitHub Pages serves, so a push publishes the site.

| Stage | What | State |
|---|---|---|
| P0–P3 | Desktop build retired; photocell; Scan experiment; the picture stage (Glow, Motion, Memory) and the drawer | Done |
| P4 | One pair: what is heard is what is drawn; the generator always heard | Done |
| P5 | Cuts: edge, crossings, thresholds, Pluck, recording, file playback, the rack; arpeggiator, clock and drawings to the drawer | Done |
| P6 | Each layer's own picture; harmony as geometry; Bend (knob and drag on the figure) | Done |
| P7a | Scan: the screen read back as the voice's wave, 60 tables a second, inside the voice | Done, page and core |
| P7b | Strike (notes light the screen), cross-scan, self-sustaining presets | Done, page and core |
| P7c | Drawing the score's voice | Tried, failed its criteria; stays heard and not drawn |
| P8a | Host knobs: Picture, Scan, Persistence, Bend, Cutoff, Level, Echo, Phaser; Morph as 9th | Done |
| P8b | Bench as four tabs along the loop (Play, Ink, Space & Memory, Picture) + drawer (Sources, Inputs, Measure, Perform) | Done |
| P8c | Sliders became knobs (from the owner's Headroom repo) | Done |
| P8d | Macros removed (setup codes v6 migrate them) | Done |
| P8e | Phaser: four all-passes a channel, channels in quadrature, steered by Memory | Done, page and core |
| P8f | Loop overlay on a switch (ring, read-head, table thumbnail, state badge) | Done |
| P8g | Preset rework: the bank rebuilt and measured on the sound | Done |
| P8h | First listening round: quarter turn, Picture amount in every code, latch and Wandering cut, the base sound, Tine piano, saw bass | Done; **the owner's next round** |
| P9 | The effect build | Not started |

Also done along the way: sound now starts from a tap on phones (`5d4e85f`,
confirmed by the owner on an iPhone), and `run.py` runs timing suites first
and alone, the rest three at a time (`4a815e5`).

## Next: the owner's next listening round

After P8h (see its bullet in `web/docs/making-it-one-instrument.md`):

- **The bank:** Settled - Tine piano, Drawbar organ, Bass under the tine piano;
  Breathing - Harmonic tone, Slow pad, Turning fifths, Bass under the pad,
  Crossed hands. The owner has heard only Settled closely; Breathing had
  "glaring things" fixed (Harmonic tone, the pad split's bass) and is next.
- **The base:** a still plain sine (`BASE_SETUP`), what the page and the
  plugin open on and what *New* in the preset browser returns to.
- **The quarter turn** is a switch on Play so the owner can hear the
  difference; whether it stays a switch, or becomes how poly always draws, is
  his call after listening.
- **Not built from the draft:** a mono lead for Bend, a pluck, a bell, a
  hammered screen, more splits.

To change or add a preset: edit `PRESETS` (or `BASE_SETUP`), run
`presettest.py` and `honestytest.py`, then `core/tests/tools/write_presets.py`,
`core/wasm/build.py` and parity. The suites that test the preset mechanism
pick bank presets by what they need, never by name.

Known about the bank, for whoever tunes it:

- Bright, beating sounds hide the loop; unison and chorus do too. None is used.
- Scan depth has a knife edge between settling and moving for good, and it
  depends on the sound and on the quarter turn: 50 for the tine piano, 14 for
  the drawbars (17 moves on some notes), 20 for the bass under the piano.
- The old library (268) is a test corpus: `core/tests/scenarios/
  library-p8f.json`, `web/tests/corpus.py`, the shell test's `corpusSetup`.

## The plan after the second round and the outside review (agreed 6 Nov)

An outside review against standard synths (Serum, Vital, Pigments, Phase
Plant) was checked in the code; what it found and the owner and Claude agreed
is below, in order. The listening notes this plan refers to follow it.

1. **The plugin's state, and the audio thread.** *Done 6 Nov except the
   bookkeeping's allocations, which moved to step 3 (plugin/PLAN.md, after
   5v, has the measurements).* Before anyone uses it in a project. Tests
   first, each seen to fail on today's code:
   - A second `prepareToPlay` (a host's sample-rate or device change, a
     reactivation) rebuilds on the base sine and loses the preset, routings
     and learned controllers. Re-prepare from the current state. The shell
     test's re-prepare check only asserts `drawsInput` survives; it must
     assert the setup does.
   - `getStateInformation` before the first block writes nothing, ignoring a
     state waiting in `pending_`: a frozen or inactive track saves empty.
   - A save holds the lock `processBlock` try-locks, so that block is silent
     and its MIDI dropped - a lost note-off sticks the note. Return the code
     already published without the audio lock.
   - Off the audio thread: `publish()`'s encode, a preset load (about 25 ms a
     drawn-cycle table), host automation's strings and JSON per parameter,
     and a new MIDI controller's first message allocating.
   - One-liners: `NEEDS_MIDI_OUTPUT` (the arpeggiator's MIDI out), a tail that
     follows the echo's feedback, the bank as host programs, the cheat
     sheet's "Settled and Open" line (3814), a default window that fits a
     1366x768 laptop and a remembered size, and something better than a
     blank editor when the WebView fails.
2. **The owner's broken sounds:** the delay's Sync and the quarter turn's pop
   (notes 5 and 1 below). *Done 6 Nov.* Sync: a MIDI clock's jittering
   tempo re-sent the delay time every tick and the read head never stopped;
   it now waits for a 2 per cent move and a beat of ticks. The quarter turn:
   the ring is written whenever the switch is on (it was stale, hence the
   pop, on the right in the core's channels - the owner heard it on the
   left; worth asking how the outputs are wired), and the glide holds a
   sine's level (it dipped 2.2 dB). No lasting level drop was measured when a
   note is added; what changes is that two held notes lean one to each ear,
   switch on or off, and a lone turned note is wide.
3. **Playing basics** (and, with the fixed steps, the state's bookkeeping
   off the audio thread: the encode at a changed block's end, 1 to 4 us, and
   a host parameter's hand - small, but allocating): pitch bend with a range, renaming the geometry's
   *Bend*, a default target for the mod wheel, channel pressure; then
   parameter smoothing **and** stepping the core in fixed 128-sample pieces,
   together, since smoothing is designed around the control rate. Parity run
   at 128, 512 and 2048 frame host blocks, which should fail today.
   *Done 6 Nov, but for the bookkeeping, which stays on the audio thread
   (1 to 4 us; the snapshot design is in plugin/PLAN.md).* The core steps
   every 128 frames whatever the host's block, the same samples at 128, 512,
   2048 and sizes that change every block (the shell test, not parity: parity
   compares the page with the core at 128, which never differed); a host's
   parameter is walked across its block's steps. Bend is Warp on the face (ids
   kept). Pitch bend with a range, the wheel's vibrato by default, pressure as
   a source and off by default (the owner chose these over the face brief's
   Picture amount and Scan depth), each a menu kept with the setup
   (`bendRange`, `wheelTo`, `pressureTo`), for now under the Keyboard
   section's ⋯ - the face's F3 gives Expression its own section on Play.
   Velocity's menu is the face's, not built.
4. **The removals:** Kaleidoscope, Snap below 5 bits (notes 2 and 3).
   *Done 7 Nov.* The kaleidoscope is gone from the page, the core, the
   plugin's controls and the host's menus; Snap offers Off, 6 bits and 5.
   A version-8 decode pass (`SETUP_VERSION` 8, page and core alike) drops
   `planeKaleido` and `bKaleido` and lifts a stored snap of 1 to 4 bits to
   5, the nearest one left, rather than to off: a code that asked for a
   crushed plane still gets one. Six old presets in the corpus used the
   kaleidoscope and two a snap under 5 bits; the corpus keeps them as
   written and they load without the one and at 5 bits for the other.
   The voice's Crush (the same quantiser, down to 1 bit) is untouched - the
   owner was not asked about it, and it is the next question.
5. **The face, as a design stage from mockups.** *Designed with the owner,
   6 Nov:* the brief is `web/docs/redesigning-the-face.md`, stages F1-F8,
   with pictures of every region. For the plugin window from its minimum
   (960x600) up; the site on a phone stacks and scrolls and does not shape
   it. It supersedes the direction first written here: no strip of host
   knobs (it would have copied controls), no drawer, three tabs and the
   Picture along the bottom, and it says which CLAUDE.md layout rules it
   retires. First, check the audit's claim that automation makes the face reload its
   whole setup four times a second (`hostVersion_` and `hostPull`); fixing it
   may change how the face feels more than a layout does. *Checked and fixed
   7 Nov:* it did, and it also put back any of the page's own hands the plugin
   had not yet heard. The state now says how many of its changes were loads
   and which knobs the host moved since; between loads the page moves those
   knobs and restores nothing (`hosttest.py`, the shell test).
   *F1 done 7 Nov:* Scope & measure, a panel over the screen from a toolbar
   above it, holds the scope's tools and the readouts' switch (home
   `measure`); the Measure tab is gone, the morph is on Perform. *F2 done
   7 Nov:* the Picture section along the bottom (Amount, Scan, Strike,
   Softness, one Persistence, the three reads), its Advanced holding what
   Scan reads, the photocell and the score beside the loop overlay and the
   panes (home `picture`); the Picture tab is gone. Not yet: Level and the
   output meter in that section (Level is a layer control, the amplitude,
   and the bar would have to follow layer B's editing as the panel does),
   the beam's ink, and the brief's own open questions, which are the
   owner's: the drawings (cut, or back in Kind) decide F3.
   *The owner's answers, 7 Nov:* the drawings (harmonograph, figures,
   solids, the second generator) are neither put on the face nor cut: made
   unreachable for now - no menu offers them, the code and the decode stay -
   so the owner can see whether they are missed. And Level goes to the
   bottom only: the generator's amplitude leaves Play and becomes Level in
   the Picture section, with the output meter, following layer B while B is
   on the panel.
   *F3a done 7 Nov:* the inputs in Settings, Perform a menu in the header
   (home `perform`), the amplitude and filter envelopes and the glide on show
   on Play. The drawer holds only Sources until F4. *F3b done 7 Nov:* the
   screen on the left as the largest square that leaves the tabs three
   columns, the tabs as cards with a line each of what that stage is doing,
   search and *Advanced* beside the cards. Still F8's: at the plugin's
   960x600 the tabs overflow (by less than before F3b), and the header is
   unchanged until F7.
   *The owner's answers on F4, 7 Nov:* Velocity offers Level and strike, or
   FM (so the Tine piano keeps its bark); MIDI learn is cut; the hearing
   family is parked like the drawings - not offered, still played by a setup
   that routes it.
   *F4a done 7 Nov:* LFO 1, LFO 2 and the Envelope as cards under the screen
   (under the screen rather than under the tabs as drawn, since the screen's
   column had height to spare and the tabs none), their editor over the
   tabs, the Sources tab and the drawer gone, the fade in Settings, Velocity
   in Expression as a view of its routing, and the empty ring transparent
   until pointed at. Nothing stored changed. *F4b done 7 Nov:* the cut -
   learned controllers and the keyboard's sources but Key (pedal, pressure
   as a source, the notes' count, spread, melody and inner voices) and the
   Level source - with a version-9 decode pass in the page and the core.
   *F5a done 7 Nov:* the rack on Space & Memory - Plane (with the screen's
   rotation as its Turn), Phaser, Chorus, Delay (renamed from Echo, host
   knob "Delay mix") and a Reverb slot, in the engine's order, each a line
   with icon, switch, summary and its main knobs, Mix first; one open at a
   time, an off module folds to its line, and while one is open the others
   fold too (to fit at 1400x900; F7/F8 should give that height back). The
   switch is a view over the values (`switchFx`), so nothing stored changed.
   Numbers read went to Scope & measure's Measure, which moved to the
   Vertical column to fit 960x600. `racktest.py` is new. *F5b done 8 Nov:*
   the phaser, chorus and delay run in the setup's `fxOrder` (six orders,
   default the old one, so no code changed meaning and no version bump),
   page, core and parity; a handle drags a module, the arrow keys move it,
   Escape puts a drag back. One order for both layers, the Plane fixed
   first. *F6 done 8 Nov:* the preset browser as the mockup draws it -
   headings with a line each, cards with thumbnails, the chosen sound on the
   right with Load (choosing loads nothing; Load leaves it open), and a
   footer with save, delete and the setup code, which left Settings. The
   thumbnails are the instrument's own figures, written by
   `core/tests/tools/write_figures.py` and hash-checked by `presettest.py`.
   Not built, and the owner's: short *listen for / watch for* lines (the
   cards show each description's first sentence) and hearing a preset by
   holding a key. Next is F7, the header and Settings. *F7a done 8 Nov:*
   the header - the preset between arrows that step the bank, its heading
   above it, Browse, Save, A/B and undo/redo (`headertest.py`). *F7b and
   F7c done 8 Nov:* Settings as drawn - two columns, notes behind dots, This
   window with the first-time help, placed against the window (which fixed
   F7a's Settings opening off the left at 960 wide); the Beam to the
   Picture's Advanced; the host's parameters strike, softness and twist
   (twelve now, in the doc's order) and a gold dot on every host parameter.
   Size is F8's. Next is F8, the window.
6. **The schema:** *the table done 7 Nov* (`SETUP_FIELDS`, `schema.h`,
   `schematest.py`; web/README.md has what it does not cover). One table that generates the setup field lists (DEFAULTS,
   snapshot, restore, the generator table, layer B's keys, the ranges,
   `panel_controls.h`, `restore.h`); and the worklet stops loading the
   JavaScript generator when the compiled one plays. The JavaScript engine
   stays: it is parity's reference, the fallback, and forty suites run on it.

Later: reverb in P9, made so the screen hears it; undo and A/B; CLAP; MPE.
Unverified from the audit: the picture's copies to the face (64-128 KB twice
a frame), the capture allocating each frame, zipper noise under automation.

## The owner's notes from the second round (1, 2, 3 and 5 done; 4 not started)

Heard after P8h; written down before any work, with a first read of the code.

1. **The quarter turn pops in the left ear going from two notes to one, and
   some of the sound in an ear drops when a note is added.** Only with the
   switch on. First read: a voice writes its quarter-period ring only while
   its turn is above nought, so a note that was one of two and becomes the
   lone note starts reading a ring last written whenever it was last alone,
   and the turn comes up in 4 ms (`roleGlide`) - a step, i.e. a click. And
   the turn is a straight crossfade between the wave and itself a quarter
   later, two signals 90 degrees apart, which dips about 3 dB halfway (only
   while it glides). A drop that lasts would be something else - measure each
   ear one note to two, switch on and off. Likely fix: write the ring always
   (it is cheap), and crossfade with a sine/cosine law, which holds a sine's
   level exactly because the two are in quadrature. Page, then core, parity.
2. **Kaleidoscope sounds terrible; remove it.** It folds every point's angle
   into a wedge: a hard reflection at each wedge edge, so harsh, aliasing
   harmonics on anything that turns. Removal is a cut like P5's: the menu,
   page and core, a version-8 decode pass dropping `planeKaleido`, parity's
   and the corpus's users (six old presets used it, the corpus keeps them as
   they were).
3. **Snap at 6 and 5 bits is good; below that silent or terrible.** Snap
   rounds both channels to a step of full scale (`Math.round(x / step)`), a
   mid-tread quantiser: anything under half a step rounds to nought, so a
   signal below full scale goes silent at 1 and 2 bits, and 3 and 4 are a few
   levels of a sine - square, harsh. Remove 4 and below as asked. Worth asking
   whether the voice's Crush (8, 6, 4, 3, 2, 1 bits, the same quantiser) wants
   the same; and later, maybe, a quantiser that never goes silent.
4. **Radial at radius 0.2 has a good, quieter, distorted character.** Keep;
   a candidate for a preset, and perhaps the radius's range or default should
   make 0.2 easy to land on.
5. **The delay's Sync, anything but Free, sounds distorted, flangery and
   harsh. Broken.** First read: synced, the delay time is worked out from the
   tempo every clock step and re-sent when it changes, and the delay read
   head glides over 50 ms to each new time. A read head kept moving is a
   flanger, which is the sound described; so something is changing the time
   over and over - two writers disagreeing (the page's tempo against the
   instrument's own), or a tempo that wobbles. Measure the delay time and
   read position on the site's instrument with Sync on before guessing
   further. Eight old presets used a synced delay.

## Decisions to keep

- Score voice heard, never drawn (P4, re-measured in P7c). The one untried
  idea is drawing it as a third figure in lanes of its own, as layer B is: a
  new design, not a defence.
- Layer B keeps its own voice; splits stay on Play. Per-layer pictures: one
  menu per layer (own / other / both, both is the average), own by default.
- Scan inside the voice; tables at a fixed 60 Hz of audio time (exact in the
  core, approximate on the page, which follows screen frames).
- The phaser stays pushed by Memory, so a still picture gets phased on the
  default sound (owner, 5 Nov).
- Strike is not a host parameter. Morph is host parameter 9, in its own
  "Setups" group; every knob has a stable string id so automation survives
  reordering.
- The owner has no saved plugin projects, so host-parameter changes need no
  automation mapping (yet - that changes once projects exist).
- MIDI clock: settled, nothing to build. The plugin takes the host's tempo, the
  page follows a MIDI clock.
- Arpeggiator, clock, drawings, measurements, inputs, key and tempo live in
  the drawer.

## Open, deferred

- **The bent sine's DC.** Bending a sine leaves an offset (up to about 0.41 of
  the amplitude at full Bend). Owner: leave it for now. Candidate fix: subtract
  it exactly per voice for the sine, a gentle DC blocker for other shapes,
  measured in the app first.
- **The band split:** deferred by the owner ("we'll see on the band splits
  later").
- **Strike from the arpeggiator and the score:** they reach the generator
  another way and do not strike.
- **Scan:** no Scan on noise or the drawings; its cost is not counted in the
  voice budget; depth is not a modulation destination.
- **A picture per note** and **drawings as a Scan source:** deferred in P7.
- **P9, the effect:** whether the hearing listens to the open input while the
  generator plays; the effect's build, ink panel, presets, a second JUCE
  target; the sidechain drawn onto the phosphor (moved here from P7).
- **iPhone use:** the site needs a Web MIDI browser app on iOS (Safari has no
  Web MIDI); the owner uses one and it works. An AUv3 build of the plugin
  would take MIDI from iOS directly - not on the plan.

## How to work here

Read `CLAUDE.md` first; it is current. The habits that mattered most:

- **Tests:** `CHROME=/opt/pw-browsers/chromium` must be set; the suites'
  default path does not exist in this container.
  - `python3 web/extract.py && node --check web/tests/check.js` after every
    edit to `web/scope.html`.
  - `python3 web/tests/run.py` is about 32–37 minutes. Run it in the
    background with a long timeout; the default 30-minute background limit
    kills it.
  - `python3 core/tests/parity.py` alone, never beside a browser suite.
  - `python3 core/wasm/build.py` after any change to `core/`, then `--check`.
  - The plugin: `cmake -S plugin -B <build> -G Ninja`, build, then
    `xvfb-run -a <build>/ScopeShellTest_artefacts/Release/ScopeShellTest`.
    The build directory lived in the session scratchpad and does not survive
    a new container.
- **Never two browser runs at once**, or parity beside one: it produces false
  failures.
- **Known timing flakes** (re-run alone before believing them): mod's octave
  sweep, Scan's held-still check, the loop energy check, budget, the pitch
  tuner's cost, `layerpicture`, `fade`, `strike`'s weak signal on the site.
- **Every suite launches Chromium with the autoplay rule off**, except
  `soundstarttest.py`. Anything about starting sound must be tested there.
- **Null-test every new check and mutation-test the code** before calling a
  piece done; several stages found tests that could not fail.
- **Page first, then the core with parity.** Push page and core together, so
  the branch never carries a page the core does not match.
- **A push publishes the site.** Push only after the full suite (and parity
  and ShellTest when the core or plugin changed) pass.
- **House style:** British spelling, comments that say why, ASCII hyphens in
  code comments, imperative commit subjects in the instrument's own terms,
  prose bodies, and the session's attribution trailer.
- **Scratchpad gotcha:** a stray `bisect.py` in the scratchpad shadows the
  standard library for scripts run from there. Run probes from another
  directory.

## Where things are

- `web/scope.html`: the instrument, one file, script inline.
- `core/include/scope/`: the C++ core (Scan in `scan.h`, the phaser in
  `plane.h`, setup codes in `setup.h`, presets mirrored in `presets.h`).
- `plugin/`: the JUCE plugin; host knobs are `kKnobs` in
  `plugin/src/PluginProcessor.h`. `plugin/PLAN.md` is its history and build
  notes.
- `web/docs/making-it-one-instrument.md`: the plan, with every stage's
  decisions and numbers.
- `web/README.md`: what the page has got wrong before, and why.
- `DESIGN.md`: the brand (shared with the jazz and guitar apps) and the
  oscilloscope's own visuals, the knob included.
- The owner's Headroom repository (`22nmcdon/headroom`), source of the knob
  design (`src/lib/knob.js`, `styles.css`).
