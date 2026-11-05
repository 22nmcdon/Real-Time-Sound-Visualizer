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
| P8g | Preset rework: eleven under Settled, Breathing, Wandering, Open, measured on the sound; the latch | Done; **now the owner's listening rounds (below)** |
| P9 | The effect build | Not started |

Also done along the way: sound now starts from a tap on phones (`5d4e85f`,
confirmed by the owner on an iPhone), and `run.py` runs timing suites first
and alone, the rest three at a time (`4a815e5`).

## Next: the owner listens to the new bank (P8g)

The owner agreed to every recommendation put to them (5 November): about ten
presets to start, a split under each heading where the loop moves the sound,
sine and saw kept under Open, every preset naming the Picture amount, and the
latch built. What was built, and what the measuring changed, is P8g's bullet in
`web/docs/making-it-one-instrument.md`. In short:

- **The bank:** Settled - Glass keys, Drawbar organ, Bass under glass keys;
  Breathing - Harmonic tone (still the boot sound), Slow pad, Turning fifths,
  Bass under the pad; Wandering - Crossed hands, Pad that keeps going; Open -
  Pure sine, Saw wave.
- **The headings changed in one way from the draft.** Breathing was "moves
  between notes, settles while held"; measured, that was Settled with a longer
  tail. It is now "keeps moving while held, stops when let go", and Wandering
  "goes on after you let go" (latched). Tell the owner; they agreed to the
  draft, not to this.
- **The honesty test** (`honestytest.py`) measures the sound, not the picture
  meter (which said "settled" over a crossed pair whose sound kept moving).
- **The latch** is on Play and in setups (`midiLatch`): a chord let go sounds
  on until the next note struck with no key down replaces it. The screen
  keys' old per-key latch is now "Tap to hold".

What comes next is the owner's ears: play each, say what to change. To change
or add a preset: edit `PRESETS` in the page, run `presettest.py` and
`honestytest.py`, then `core/tests/tools/write_presets.py`, `core/wasm/build.py`
and parity. Not yet built from the draft: a mono lead for riding Bend, a pluck,
a bell (agreed in place of the drone field), a hammered screen; and more
splits once there are more sounds to split.

Known about the bank, for whoever tunes it:

- Bright, beating sounds hide the loop; unison and chorus do too. None is used.
- How deep Scan can go before a held sound keeps moving depends on the sound:
  50 for the glass keys, about 20 for the drawbars, 15 for the C2 bass.
- Six-note chords on the pad hit the limiter; its level is 28 to keep a
  six-note chord under three decibels of limiting.
- The old library (268) is a test corpus now: `core/tests/scenarios/
  library-p8f.json`, `web/tests/corpus.py`, and the shell test's
  `corpusSetup`. Tests open known sounds from there, never from the bank.

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
