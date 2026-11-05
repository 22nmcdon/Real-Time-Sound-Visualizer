# Handoff

Where the instrument stands, what is decided, what is open, and how to work on
it without rediscovering the last month. Written at the end of P8f
(`2f2165a`, 5 November 2026). The plan itself is
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
| **P8g** | **Preset rework** | **Next: needs the owner (below)** |
| P9 | The effect build | Not started |

Also done along the way: sound now starts from a tap on phones (`5d4e85f`,
confirmed by the owner on an iPhone), and `run.py` runs timing suites first
and alone, the rest three at a time (`4a815e5`).

## Next: the preset rework (P8g)

The owner wants a serious rework: there are 268 presets in 30 sections, far
too many, and they liked none of them. They chose the plan's full rename. A
first proposal was put to them and **not yet answered**:

- **Shape:** about 16 presets under four headings named for what the loop
  does: **Settled** (short memory, light Scan, timbre follows the playing),
  **Breathing** (moves between notes, settles while held), **Wandering** (long
  memory, deep Scan, keeps moving on its own), **Open** (loop off, plain
  sounds). Replaces the three menus *Pictures and sounds / Answering your
  playing / Playing live*; CLAUDE.md's "Presets are a library" bullet changes
  with it.
- **An honesty test:** the meter already says settled / moving / running
  away, so a test can require each preset to behave as its heading says.
- **Draft list:** Settled - glass keys (strike-led), round bass with sub,
  drawbar organ, a pluck. Breathing - slow pad opened by Memory's phaser,
  turning fifths (harmony as geometry with a slight detune), a mono lead for
  riding Bend, a bass + keys split. Wandering - crossed hands (split,
  cross-scan), a pad that keeps going after release, a drone field, a
  hammered screen. Open - sine, saw, square, a plain poly synth.
- **What goes:** everything else, drawings, analysis demos, live-input effects
  and Lissajous sets included. Saved presets stay. Tests that open presets by
  name get their setups written out, as P8d did; `presets.h` is regenerated
  from the page library and parity covers it.
- **The limit:** Claude cannot hear. It can make every preset pass the numbers
  (meter verdict, the picture moving the sound, no clipping, the first-minute
  test); whether it sounds good is the owner's call, so expect rounds of
  "play it, say what to change".

Questions the owner still has to answer:

1. Which kinds of sound: does the draft's mix (keys, bass, organ, pad, lead,
   pluck, drone, splits) match, or swap some?
2. How many splits? They are the owner's favourite way to play.
3. About 16, or start with 8–10 and grow?
4. Keep sine, saw and square under Open?
5. **The latch.** Wandering presets keep going after release. Today "Scan
   breathes" and "Scan remembers" do it by making the keys hammer a drone that
   plays its own pitch. The alternative is a latch on Play that keeps the
   owner's own chord sounding while the loop moves it - a new control, not yet
   built. Asked twice, unanswered.

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
