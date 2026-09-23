# Playing it, hearing it, and letting it listen to itself — the plan

**Where this stands.** Stage A is built: MIDI in, CC learn, the dyad, the tuning
switch, and the note as ground truth for the lag, the timebase and the tuner.
**B1 is built too** — polyBLEP on the square and the ramp, polyBLAMP on the
triangle, and the question B1 left open for the geometric generators settled by
measurement: they alias no worse than the corrected square, so none of them is
oversampled and none needs to be. Everything else from Stage B on is still a
plan. `web/tests/miditest.py` and `web/tests/aliastest.py` hold the
verification A and B1 asked for.

**D8 is built** as well, ahead of the rest of C: an input carries a kind, and a
declared line input can be monitored through the page with the limiter and the
clamp still last. That makes the latency question answerable on real hardware,
which is what decides whether C3 is a browser feature or a JUCE one. What is
*not* built is the block the two taps are meant to straddle — see the note
below on what C0 costs.

**C0, split into four, and two of them taken.** The pinned order puts full
scale and rotation inside the tapped block. Both are display-time operations
today — `gainOf` per lane in the drawing code, rotation only in `drawXY` — so
moving them changes shipped meaning in four separate ways. They were separated
and decided one at a time rather than waved through as a block, on the grounds
that two of them are "does the picture come out the same" and two are "does the
number the instrument reports stay true", and only the first pair can be
settled by comparing pictures.

**Taken: mid/side becomes rotation at 45°.** One matrix, with the ½-against-1/√2
gain and the reflection's sign flip kept explicit. A pure regression risk with a
concrete check, and nothing new to decide. Built; see `rotatetest.py`.

**Taken: the figure is turned before each lane is placed.** Rotation acts on
the pair; full scale and offset put the result on the screen. A preset that used
those knobs to separate two traces would see its separation turned as well, but
that is display cosmetics and nothing the app reports as a measurement. Built,
with the same preset-by-preset check — and it turns out no preset can see it at
all, because all 39 place both lanes alike.

**C1's first row is built: rotation, twice.** The picture's matrix and four
gains in the monitor chain, from one `turnOf`, agreeing to float32's rounding —
so turning the figure turns the stereo image of anything with an audio path.
The Speakers switch says *Shaped* rather than *Filtered* now, because the block
it straddles is no longer only the filter. **C1's AC row is built too**, and the plan's own note was wrong about it: it
paired a mean subtraction against a high pass and conceded they would not agree
exactly. They could never have agreed at all — one is non-causal and
whole-block, the other causal and per-sample, and no tolerance closes that. Both
sides run the same one-pole DC blocker now, from one shared corner (0.5–20 Hz,
ten by default), and they agree bit for bit. The size of the change is measured
in `web/README.md`; the readout names the corner while AC is on.

**C1's last row is built: lag, heard.** A `DelayNode` on the right channel,
between the shaped block and the rotation, agreeing with the picture's
interpolated read to 2.75 × 10⁻⁶ at a fractional τ. It comes with a mix control
(*Heard*, in the Lag section) with a placeholder default and a ceiling, and the
measurement behind the ceiling went the other way from what this plan assumed:
see C1 below. **Full scale as a `GainNode`
is withdrawn rather than deferred** — see the widening below for why a display
magnification should not be a thing the speakers follow.

**Taken: full scale is a continuous gain, and a destination.** Which is what
the trigger work was actually for: a fraction sitting on a table of nine
positions promised safety across nine discrete jumps rather than across a gain.
The lanes are still not scaled — that is the widening below — so this closes
#1's promise without touching what the measurements are about.

**Taken: the trigger level is screen-relative.** Redefined as a fraction of
full scale, converted per capture on the gain in force for that block, with the
real amplitude beside it in the dock and a version-2 setup migration for codes
that stored an amplitude. What is still held is the *reordering* it was blocking
— see below.

**Settled: full scale stays out of the captured block.** The redefinition it
was waiting for is built — the level is a fraction, converted per capture, and
the dock gives the amplitude beside it — and on looking at what moving it in
would actually buy, the answer was nothing it did not already have. It is a
display magnification, and a member of the tapped block is by definition
something the speakers can be sent. So #1 is closed rather than half-closed,
and it closed by dropping a step rather than by taking it.

**Built: rotation reaching Y–T and the measurements, with the tap that makes
it honest.** The objection was never to rotation being a signal transform — it
was to a knob a player reads as "how the Lissajous is oriented" changing the
pitch or the THD in an unrelated pane. Both halves of the fix are in. Rotation
turns the captured lanes on a stereo pair, before the trigger, so Y–T, the
figure and the speakers are one rotation. The per-lane measurements read their
own tap, defaulting to the signal as it arrived, so none of those numbers
moved. On anything that is not a pair — a rack, a band split, a mono input,
the lag lane — it stays a display knob and `syncMonitor` is gated on the same
predicate, so the speakers cannot disagree with the screen about it either.
`rotatetest.py` asserts all of that in both directions, and the checks that
used to say "rotation reaches nothing" were rewritten rather than deleted.

### The measurement tap — built

Written down before it was built, because its whole value is in what it
promises about numbers and that promise is easy to lose in the plumbing. What
follows is that note with the answers filled in.

**What it is.** `capture` produces three views of one block rather than one
array: `channels`, what the screen draws; `signal`, what arrived, shaped by
everything a measurement should be about and by nothing that is only about the
picture; and `measured`, whichever of those the tap points at. Peak, RMS, Vpp,
frequency, period, THD, the tuner and the goniometer's correlation read
`measured`. The switch is *Numbers read* under *Display*, and the readout says
`post-rotation` when it is not at its default.

**Where it defaults.** On `signal`, which is exactly the old behaviour, so the
change shipped with every number unmoved. At rest all three views are the same
arrays rather than copies of each other, so "unmoved" means bit-identical and
not close.

**What had to be true before it landed, and what happened to each.**

- ~~Every reading bit-identical with the tap at its default.~~ **Done**, and
  for the default configuration, where nothing is turning and all three views
  are the same arrays — armed or free running, no exceptions. With the knob
  turned there is a second tier, found on the way. The trigger reads the drawn
  lanes — that is what made its level a fraction of the screen — so turning a
  pair can put the edge on a different sample, and the measurements are then
  over a different *slice* of the same signal. The array comparison therefore
  puts the level out of reach so both captures land on the same offset, and the
  armed case is asserted as an algebraic identity instead: whatever window came
  back, turning the measured pair by the angle in force reproduces the drawn
  pair. No hardware precedent is claimed for the moving window and an earlier
  draft claimed one; an analogue scope has no time base in X–Y and so no
  trigger there to compare against. It is this page's own logic followed
  through, and it is labelled as that.
- ~~The clipping verdict stays about the input.~~ **Done**, reading `signal`
  whatever the tap says. The check that said so was vacuous for its first
  draft — see `web/README.md` on what a stopped scope reports — and now runs
  the scope with a control that proves the verdict can say "Clipping" at all.
- ~~`env.live` stays a source about the signal.~~ **Done**, pinned to `signal`.
- ~~The readout marks the tap when it is not at the default.~~ **Done**, and
  only when it is making a difference: the tap can sit on the turned signal all
  day with nothing turning.
- ~~`rotatetest.py`'s scoping checks rewritten rather than deleted.~~ **Done**.
  They assert the same thing they always did — that no number quietly stops
  describing what its label says — against a rule that is now two rules.
- ~~Full scale becomes a continuous gain before it can be a modulation
  destination.~~ **Built**, ahead of the rest, and the nine table values give
  their old gains to zero difference.

**The two questions, answered.**

*Should full scale be in the block at all?* **No, and C1's `GainNode` row is
withdrawn.** A member of the tapped block is by definition something
`monitorAt: post` can send to the speakers, and full scale is a display
magnification — making it audible means the monitoring level follows a knob
whose job is how big the trace is. Nothing else on this page behaves that way;
zoom was scoped out for a related reason (D6). (An analogue scope has no
monitor output at all, so it is not a precedent either way — this is the
page's own consistency, not hardware fidelity.)
What full scale actually needed was to be continuous, modulatable and tracked
by the trigger, and all three are built without it moving. The second reason
stands as well: the trigger finds its edge on lanes full scale has not touched,
with the threshold converted instead, and moving it onto scaled lanes would be
the same comparison up to floating-point rounding — same arithmetic, possibly a
different sample, and the bit-identity standard broken for nothing.

*Which pair does rotation turn, when there are more than two lanes?* **The
stereo pair, and on anything else it stays a display knob** — mid/side's
existing rule, extended to exclude the lag lane. `rotatesSignal` is the one
predicate, read by `capture` and by `syncMonitor`, so the picture and the
speakers cannot part company over it. On a rack, "rotate the stereo image"
does not describe anything you could do to six stems; the lag lane's second
channel is the first one delayed, so turning that pair would mix a signal with
its own past and call the result stereo. One cost, recorded where someone will
hit it: a monitored mono input no longer pans, which it used to.

**What it turned out to catch.** Two things nothing else would have. Turning
the figure twice — rotation in `capture` and again in `drawXY` — leaves the
captured lanes, the speakers and every number correct with the picture at
double the angle; and a circle, which is what the default preset draws, is the
one figure whose every statistic survives a rotation untouched, so it cannot
witness the tap moving the numbers at all. Both now have their own checks and
both are in `web/README.md`.

**What is left after it.** Lag as a `DelayNode`, the last row of C1's table,
which needs the block to contain it before there is anything to straddle —
since built. Full scale as a `GainNode` is withdrawn, as above. That closes C0
and C1 apart from lag, and the next work is B2 — the sample-rate audit — which nothing here
blocks.

One thing B1 turned up for B4: the harmonograph sets its envelope back to 1 in
a single sample when the pendulums have run down, which is an audible click the
moment the generator has an output.

A plan, built on `docs/midi-and-the-audio-path.md`. That note describes *what*
and *why*; this one turns it into stages with decisions made, dependencies
drawn, and a test for each. Nothing is built yet.

What is being planned, in the order it was asked for:

1. **Nord audio in, MIDI for the picture.** The Nord sounds as itself; its keys
   and panel move the scope.
2. **The generator gets a real audio path**, and the picture's transforms shape
   that sound in either order — seen-then-heard or heard-then-seen.
3. **Two visualisers at once**, one from live audio and one from the generator.
4. **The picture feeds back into the sound** — a virtual photocell reading the
   screen and modulating the audio. Added since the note; Stage E below.

---

## 0 · Decisions this plan takes

Every open question from the design note and the review that followed it, with a
proposed answer. Each is marked **proposed** until confirmed; none of them should
be discovered during implementation.

| # | Question | Proposed answer | Why |
|---|---|---|---|
| D1 | "Image alters audio": transforms or pixels? | **Both, as separate stages.** Transforms are Stage C. Pixels are Stage E. | They share no machinery. C is a widening of the existing taps; E is a new feedback source. |
| D2 | Dyad mode with 0, 1, 2, 3+ notes held | The pair is **the top two of the held-note stack**, ordered **by pitch, not recency**: lower note → left/X, higher → right/Y. A third note displaces the oldest of the pair; releasing one of the pair promotes the next most recent. One note → unison, unless **Hold interval** is on, in which case the last dyad's ratio is kept above the single note. Zero → gate closed. | Pitch ordering keeps the figure's orientation stable no matter which finger landed first. Stack semantics reuse the mono logic exactly. |
| D3 | Equal temperament vs just intonation in dyad mode | A **Tuning** switch: *Equal* (literal key frequencies) and *Just* (snap each played interval to its nearest small-integer ratio). Default **Just**. | See "The temperament problem" in Stage A. An equal-tempered third spins the figure ~9 times a second. |
| D4 | Does a MIDI note drive every generator kind? | **Opt-in per generator.** Waveform and Harmonograph: on by default (the dyad becomes the two pendulum frequencies). Figure: note sets trace rate, on. Wireframe: off by default. | In wireframe `freq` is how fast the solid is drawn, so a note changes the tumble rate. Interesting, but a choice rather than a default. |
| D5 | Two visualisers: two lanes, or two scopes? | **Two lanes on one graticule** first (free after Stage B). Two independently clocked scopes deferred to their own note, and only if lanes turn out not to be enough in use. | Lanes share a clock on purpose. Don't break that until there's evidence it's in the way. |
| D6 | Does zoom join the shared transforms? | **No.** Full scale is the shared gain; zoom stays display-only. | Zoom means different things in X–Y and Y–T; a transform that changes meaning with the display mode can't be heard honestly. |
| D7 | Where does rotation go in the pinned pipeline order? | After lag, and **mid/side becomes a case of rotation** (see Stage C). | Lag builds lane 2 from lane 1, so it must exist before anything rotates it. |
| D8 | May a live input be monitored? | **Yes, for a declared line input; never for a microphone.** An input carries a user-asserted kind: `mic` (default, never monitored) or `line`. | The existing rule exists to stop acoustic feedback. A Nord on a line input has no acoustic path back into itself. |
| D10 | Is a generator *lane* a played voice or a drone? | **A drone that follows pitch.** The envelope belongs to the generator as a source; a lane sets its pitch from the keyboard without starting or stopping. | A lane in a rack is expected to be producing signal the way a live input always is — solo, mute and the mixer assume there is something there. A lane going silent between phrases is a lane the rest of the rack has to be told about. Said in the keyboard panel rather than left to be found. |
| D11 | A generator lane is one signal — which? | **Its left channel.** | A lane is one signal and the generator makes two. D's own verification asks for `generator-L` against `Nord-L`. The cost is that the generator's own figure — and so dyad mode's whole payoff, the interval you can see — is not available while it is a lane. Also said in the keyboard panel. |
| D9 | Photocell v1: canvas readback or an intermediate tap? | **A low-resolution shadow phosphor grid** fed by the same segment walk the beam renderer does. Canvas readback only if v1 looks meaningfully wrong. | Nearly free, persistence-aware, and never touches `getImageData`. Measure before paying for the honest version. |

---

## Dependencies

```
            ┌──────────── A · MIDI + Nord audio in ────────────┐
            │  (independent — ships first)                      │
            │                                                   ▼
 B1 band-limit ─► B3 worklet ─► B4 gate/envelope      E · photocell
      │               │                                   ▲
      │               │        D2 · generator's sound      │
      │               └─────────► reaches a lane's         │
      │                           speakers                 │
      │         C · transforms in the audio path ─────────┘
      │               ▲
      └── C can start on mic/file/rack before B exists ──┘

 D1 · what "the source" is  ──────────────────────────► (needs nothing)
      the Tone/Mic/File/Stems selector becomes rack membership
```

- **A** needs nothing. It is useful immediately and it is the thing asked for first.
- **B1** (band-limiting) needs nothing and can be verified while the generator is
  still silent — the harmonics pane measures it.
- **C** works today on mic, file and rack sources. Prove it there before the
  worklet exists; B only extends it to the generator.
- ~~**D** is nearly free once B3 lands.~~ **Wrong, and the correction matters
  for sequencing.** D splits into two pieces with quite different costs and
  quite different dependencies, and drawing it as one arrow off B3 hid both.

  **D1 — `state.source` stops being one thing.** The mutually exclusive
  Tone / Mic / File / Stems selector becomes "what is in the rack", with the
  generator as a lane type. This is the largest remaining refactor in the plan
  and it **depends on nothing**. It is a statement about how sources are
  selected and represented, not about whether the generator emits audio: a
  silent generator can be a lane today.

  **D1a — the lane contract — is built.** The obstacle was internal rather
  than sequential, and auditing for it found more than expected: not only
  `makeLane` building every lane around an `AnalyserNode`, but three
  near-identical `getLatestWindow` bodies, three capacity expressions reaching
  into `scratch`, and `laneMixer` reaching into a `GainNode`. A lane is now
  `read(n)`, `frames` and `setMix(value)`; `scratch` is a closure variable, so
  going round the contract is a `ReferenceError` rather than a habit. Feeding a
  lane stays outside the contract on purpose. `contracttest.py` puts a lane made
  of three plain functions through the mixer and through `capture` — which is
  the load-bearing claim for everything else in D1.

  The duplication was also a latent bug: `applyAlignment` writes `delay` on
  every lane of any source with lanes, and one reader of three honoured it.

  **D1b — the generator as a lane type — is built.** `makeSynthLane` is the
  generator's own core on a JS ring, satisfying the contract and nothing else:
  no analyser, no gain node, nothing connected. One lane, meaning its left
  channel, which is what D's verification asks for. At most one per rack, first
  one wins, because two would step the shared oscillators twice a sample.
  `lfoDriver` asks whether any lane is one rather than whether the source is a
  tone.

  **D1c — the controls, and the budget — is built.** Thirty places asked
  `state.source.kind === "tone"` before writing to the generator; that is a
  question about what the generator *was*, and `genSettings` / `genSet` /
  `genReswing` are it re-asked. The lane budget is stated before anything is
  decoded — the generator takes one of the six before any file does — and
  ticking the box rebuilds what is loaded, the way the band split already does.

  **D1d — the rack's membership is choosable — is built**, and it turned out
  to matter more than the selector. Stage D's headline is "generator plus Nord,
  overlaid"; that needs a live lane in a rack, and the only thing that made one
  was *Play along*, which always brings a backing track. So the headline case
  could not be built at all. Two checkboxes on the Stems rows — the generator,
  the live input — are what make a rack's membership a choice rather than a
  consequence of which button opened it.

  **What is left of D1: the selector itself, and nothing saved.** Tone / Mic /
  File / Stems is still a mutually exclusive radiogroup. An earlier version of
  this note said the setup code stores one source kind and so needed a
  migration; it does not — `snapshot()` records the generator's mode and the
  trigger lane, never which source is loaded, which is why a preset lands on
  whatever you are playing. So this is interface work only.

  One thing the selector pass should not do without deciding it: collapsing
  *File* into *Stems*. They look like the same thing and are not. A file source
  is **one signal in stereo**, so X–Y plots its own two channels against each
  other; a rack lane is **one mono signal**. Collapsing them costs the
  per-source figure exactly the way a generator lane costs the dyad figure
  (D11). The rack model and the single-source model are both needed, and the
  selector's job is to make that legible rather than to erase it.

  **D2 — the generator's sound reaching a lane's speakers.** This needed B3,
  and calling it "built" was an overclaim that wants correcting: the generator
  sounds when it IS the source, which is what B3 delivered. A generator LANE is
  silent. Giving one an output means a second worklet on the rack's own context
  feeding the rack's mix, with the monitoring rules that go with it, and that
  is not built.

  **"A second worklet" means the same processor on another context, and this is
  a constraint on the work rather than a description of it.** One piece of
  arithmetic called from two places is the rule this whole plan has followed —
  the AC blocker's shared coefficients, the biquad's two implementations from
  one parameter set, `turnOf` for the picture and the graph, and
  `makeGeneratorCore` as literally the same text on the main thread and in the
  worklet. A rack lane's audio must be `generatorModuleSource()` loaded onto the
  rack's own `AudioContext`, not a second thing that produces the same
  waveform. The mechanism for it already exists and was built with this in
  mind: `loadGeneratorModule` is keyed by context in a `WeakMap`, precisely
  because a module added to one context has not been added to another.

  The ownership hazard that comes with it is named too. Two worklets each
  running `makeGeneratorCore` would be two per-sample loops over one set of
  shared oscillators, which is the exact shape `assertLfoDriver` exists for.
  Today they cannot coexist — `state.source` is one thing and adopting a rack
  stops what it replaces — and `contracttest.py` checks that rather than
  assuming it. The day a lane gets its own worklet, that check is the one to
  extend first.

  The practical consequence: D1 can move in parallel with portable-DSP work
  rather than queuing behind the worklet. If the JUCE port is where the
  transforms go next, D1 is the piece of this plan that does not compete with
  it for the same knowledge.
- **E** needs only the mod matrix and the beam renderer. It is *more interesting*
  after C (the loop can then close through audio you hear), but its first
  version can close through picture-only destinations.

---

## Stage A — MIDI in, and the Nord as itself

Two configurations, both usable before the generator makes any sound.

### The setup, stated as hardware

The Nord connects to the computer **twice**:

- **USB → computer**: MIDI only (notes, CCs). As far as I know the Electro 6D's
  USB does not carry audio — verify against the manual before writing the setup
  text.
- **Left/Right line outs → an audio interface's line inputs**: the organ itself.

This is a real setup step, so the app says it on screen, alongside the two
per-session Nord settings: **System Menu 12 → Send & Receive** (so CCs transmit
at all), and **Local** set to match the configuration below.

**The stereo outs are the quiet win here.** The rotary speaker, chorus and
vibrato are genuinely stereo effects. Run both outs into a stereo input and X–Y
draws a *real* moving figure from a single instrument — the problem a mono mic
had (L ≡ R, a diagonal) doesn't exist for this source.

### Configuration A1 — "Nord audio, MIDI moves the picture"

**Local On.** You hear the Nord directly (from the interface's direct monitor or
the Nord's own outs — not through the browser). The scope's source is the line
input. MIDI arrives separately and is used for two things:

**CCs as modulation sources.** Unchanged from the note: MIDI-learn, a CC becomes
a source the first time it moves, auto-named from a built-in Nord map but
editable; smoothed once, upstream of `value()`. Destinations are everything
already in the registry that applies to a live source — rotation, persistence,
lag τ, filter, band crossover.

**Notes as ground truth for the measurement side.** This is the part the note
doesn't have, and it may be the most useful single thing in Stage A. The scope
spends real effort *estimating* pitch: lag X–Y's auto-τ sits behind a confidence
gate and a one-second slow lock because estimates jitter. A MIDI note is not an
estimate. When MIDI is present:

- **Auto-τ from the note** — a quarter period of the played pitch, exact, no
  gate, no lock-in delay. The pitch estimator becomes the fallback.
- **Auto-timebase from the note** — N periods of the lowest held note on screen.
- **The tuner reads the difference** between the MIDI note and the measured
  pitch, which for an organ is a real and interesting number (drawbar tonewheel
  tuning is not equal temperament).

**Expression.** The note ranks the swell pedal (CC 11) first, and that's right —
it is the only continuous control you can move with both hands playing. But
CC 11 **only exists if an expression pedal is plugged into the Electro's control
pedal jack**. If one isn't: velocity is the next candidate, but organ programs
send fixed velocity, so it means switching to a piano or sample-synth program —
which in A1 also changes what you hear. Past that, every expression source costs
a hand. The setup screen should ask whether a pedal is connected rather than
presenting CC 11 as if it were always there.

### Configuration A2 — "Nord as a controller, generator as the picture"

**Local On or Off, player's choice.** The scope's source is the generator,
still silent. MIDI notes drive it:

- **Dyad mode (default)** — two held notes become the two channels (D2).
- **Mono mode** — last-note priority sets `freq`; the interval stays manual.

With Local On you hear the organ while the generator draws the interval under
your hands; with Local Off you get the picture alone. Either works before
Stage B.

### The temperament problem

The note says the dyad draws the interval "in the keyboard's own tuning". Worth
knowing what that looks like before building it.

A Lissajous figure stands still only when the frequency ratio is exactly a
small-integer ratio. Equal temperament's intervals aren't. The figure doesn't
break — it **rotates**, at the rate the ratio misses by:

| Interval (on A3, 220 Hz) | ET ratio | Just ratio | Figure rotates at |
|---|---|---|---|
| Fifth | 1.4983 | 3:2 | 3·220 − 2·329.63 ≈ **0.7 Hz** — a slow, lovely drift |
| Major third | 1.2599 | 5:4 | 5·220 − 4·277.18 ≈ **8.7 Hz** — a blur under persistence |

So *Equal* is honest and shows you temperament beating as motion, which is
genuinely beautiful on fifths and fourths and unreadable on thirds. *Just* snaps
each interval to its nearest ratio and every figure stands still. Hence D3: a
switch, default *Just*. (`describe()` already prints "unison just", which
suggests `intervalRatio` has a tuning concept in it — check before adding a
second one.)

### Where A can run

Unchanged from the note: secure context; in a cross-origin iframe it needs the
embedder to grant `midi`, so **Stage A almost certainly cannot run in the
published artifact** and Pages becomes the only way to use it. Safari has no Web
MIDI at all — feature-detect and say so plainly.

### A · verification

Stub `navigator.requestMIDIAccess` with a fake port; dispatch synthetic messages.

- Parsing: note-on with velocity 0 is a note-off; running status handled.
- The stack: same note twice doesn't stack twice; blur and `visibilitychange`
  release everything.
- **Dyad rules (D2), exhaustively:** 0/1/2/3 notes; release of either pair
  member; pitch ordering independent of press order; Hold interval on and off.
- **Tuning (D3):** in *Just*, a held ET fifth produces a figure whose bucket
  pattern is identical frame to frame; in *Equal*, it measurably rotates at the
  predicted rate.
- CC learn: first movement registers a source; the Nord map names it; renaming
  survives snapshot → encode → decode → restore.
- Smoothing: a 0→127 CC step produces a monotone ramp, not a step, at the
  `value()` boundary.
- **Note-as-ground-truth:** with MIDI present, auto-τ equals a quarter period of
  the note exactly and ignores a deliberately wrong pitch estimate.
- Manual, on the Nord: every CC in the built-in map checked against the live
  MIDI monitor; the stereo outs through a stereo input give an X–Y correlation
  bounded away from ±1 with the rotary on.

---

## Stage B — the generator makes sound

The load-bearing stage. Four parts, in this order.

### B1 · Band-limiting, before anything is audible

`waveAt` is not band-limited, and the app ships a Harmonics and THD preset. The
moment the generator is audible, foldover lands at non-harmonic frequencies and
the harmonics pane reports it as content — the instrument lying in exactly the
place it claims to measure.

- **PolyBLEP** for square, saw and PWM. Done in the existing JS source, while it
  is still silent: the harmonics pane can verify it before any audio exists.
- **Geometric generators** (figure, wireframe, harmonograph) have discontinuities
  at no known phase, so PolyBLEP can't reach them. Two options, decided by
  measurement: render at **4× and decimate** inside the worklet, or leave them
  un-band-limited with the limit **stated in the readouts** (mark THD as
  unreliable for these kinds, the way readouts are already marked post-filter).
  Measure the aliasing first; the answer may differ per generator — the
  harmonograph is smooth and may need nothing.

### B2 · Sample-rate audit — built

`const rate = 44100` is now `deviceRate()`, measured from a context opened and
closed for the purpose and corrected by every source that opens a real one.
The colophon says `(assumed)` when nothing ever measured it. `ratetest.py`
runs the audit at 22.05, 44.1, 48 and 96 kHz — the capture path against a
stand-in source, the audio graph against `OfflineAudioContext` — so the page
meets rates no converter in the container offers.

Three kinds of assumption turned up, and they fail differently.

**Durations written as sample counts** change meaning silently. The trigger's
minimum search room was 512 samples (11.6 ms at 44.1 kHz, 5.3 at 96) and the
lock's probe was 8192 (186 ms, or 85). Both are durations now. The probe
change was justified by sweeping rather than by argument: at 30 Hz the old one
locks fine even at 96 kHz, and the real boundary is 21–25 Hz, where it gets
one gap and `estimatePeriod` honestly reports no confidence.

**A capacity in samples is a time that halves** when the converter doubles.
32768 analyser frames are 743 ms at 44.1 kHz and 341 at 96, against a slowest
sweep of 500 — so `timebaseCeiling` says *past the buffer* on the control
rather than leaving it to be found as a trace that stops early.

**A time constant in the audio graph may be either**, and only rendering says
which. The limiter's lookahead is a time: 264 samples at 44.1 kHz, 576 at 96,
6 ms at both. The figure the panel quotes was right and is now known to be.

One thing the audit corrected about itself: the invariant is not
`length + span + lead ≤ capacity`. The window is the picture and never
shrinks, so it is *everything else gives way first, and when the window alone
is too big the over-ask is exactly its own shortfall* — which is what
`state.starved` has always reported.

### B3 · The worklet — built

The per-sample loop is `makeGeneratorCore`, and it is *one* body of code that
runs in two places: on the main thread while the generator is silent, and in an
`AudioWorkletNode` once it is not. Not two implementations kept in agreement by
a test the way the biquad and the rotation are — the same text, stringified, so
there is nothing to keep in agreement.

**Silent until asked.** *Hear the generator*, off by default. A measuring
instrument that made a noise when it was opened would be wrong in the way a
scope is not allowed to be wrong. What the switch buys besides sound is that
the worklet becomes the only thing producing samples, so the trace is the
waveform that went to the speakers rather than a second run of the same
arithmetic. It goes out through the ordinary monitor chain, which hands the
generator the filter, the AC coupling, the rotation and the limiter that C0/C1
built and had nothing to point at.

**Single-file constraint — the note's answer was half right.** The processor is
a real function in the file, stringified, and `node --check` still parses it.
But a *Blob* URL does not load from `file://`: the origin is opaque, the URL
comes out `blob:null/…`, and `addModule` refuses it. A data URL loads. Both are
tried, in that order, and `worklettest.py` records which one worked.

**The Node-side check earned its place on its first run**, and twice more
after. It caught `cycleOf is not defined` — an arrow constant stringified
without its name — then `MODEL_BY_NAME` coming out of `JSON.stringify` as
`{}`, which made every solid quietly draw the cube. Both were invisible to
`node --check` and would have reached a browser as a generator that said yes
and made no sound. See `web/README.md` for all of it.

**LFO ownership, enforced but derived.** The note said a fixed `owner` field
set at registration. That cannot be right: the same oscillator drives a
generator parameter and a view parameter, and which side steps it depends on
whether the worklet is running — a fact that changes while the page is open.
So `lfoDriver()` is *derived* rather than stored, the same lesson
`rotatesSignal` carries, and both advance paths call `assertLfoDriver`, which
throws. A 2 Hz oscillator measures 1.98 Hz across the boundary.

**Traffic across the boundary**, as planned: parameters posted on change, the
routes and every main-thread source value in one batched message per frame, and
the samples posted back in batches of about forty milliseconds, transferred
rather than copied. A render quantum is 128 frames — posting each one would be
375 messages a second for a picture that wants sixty.

### B4 · Gate and envelope — built

An ADSR in the core, so it runs a sample at a time wherever the core is, with
one envelope over the pair. The gate is the note stack's, the legato rule is
the standard mono one — a second key over a held one changes the pitch and
keeps both the envelope and the velocity of the note that opened it — and
`glideMs` slides between pitches instead of stepping, off by default.
`env.note` is registered beside `env.live`, and the two mean opposite halves of
one word: one is a measurement of what is being drawn, the other is where the
generator's own envelope has got to.

**Gated only in `wave`, which the plan did not say and should have.** There a
note has a pitch, a beginning and an end. In the drawn modes a note is a ratio
applied to the trace rate, so gating them would blank the screen the moment a
keyboard was plugged in and nobody was playing. And where a gate *is* open with
nothing held, the readout says `gated · no note held` — silence is correct
there and a scope that simply went dark would not be.

**The sliders name durations, not time constants.** A one-pole aimed at its own
target never arrives, so each stage works out its own span in time constants
when it is entered, from where the envelope actually is. Attack peaks 47 ms
after a 50 ms attack; sustain is reached at 147 against 50 + 100; silence 200 ms
after a 200 ms release.

**The harmonograph's restart, which B1 flagged for this stage, is a ten
millisecond raised cosine.** Worst step across a second of restarts: 0.0024,
against 0.2709 with the fade removed.

### B · verification

- B1: a band-limited square's harmonics pane shows no energy at non-harmonic
  frequencies above a stated floor, at 440 Hz and at 4 kHz; the existing THD
  tests still pass.
- B2: every sample-rate assumption asserted at 44100 and 48000.
- B3: stringified processor runs one block in Node; LFO rate test in the worklet;
  the dev-mode ownership throw fires when both paths claim one source.
- B4: **done**, and the render needed a trick the plan did not know about — a
  message posted before `startRendering` is never delivered, so both gate edges
  are placed from `suspend(when)` callbacks on 128-frame boundaries. See
  `web/README.md`: the first version of this test measured a second of silence
  and four of its checks passed on the zeros.
- Regression: all 27 presets still apply; the silent-generator picture is
  unchanged when audio output is muted.

---

## Stage C — the picture's transforms in the audio path

The note's reframe stands: this is the filter's `analyseAt` / `monitorAt` pair,
widened from "the filter" to "the block of transforms". Both orderings that were
asked for — seen raw and heard shaped, or heard and seen the same — are points in
that two-switch space. **Start on the line input and file sources**, which
already have monitor chains; the generator joins when B lands.

### C0 · The order, pinned before any code

The existing order was pinned because filter-then-embed and embed-then-filter are
different signals. Rotation raises the same question, so it gets the same
treatment:

```
source lanes → AC removal → full scale → per-lane filter
            → lag (builds lane 2 from lane 1, if on)
            → rotation (includes mid/side)
            ─────────────── the tapped block ends here ───────────────
            → trigger → slice → draw
```

- **Lag before rotation**, because lag creates the second lane; rotating a
  phase-space figure is meaningful, lagging a rotated pair is not.
- **Mid/side is rotation at 45°.** With 1/√2 normalisation, the M/S matrix is a
  45° rotation of the stereo vector (the goniometer convention). Implementing it
  as a case of rotation removes an ordering question instead of answering it,
  and makes "rotation and mid/side are mutually exclusive" disappear. If today's
  mid/side uses ½ scaling rather than 1/√2, it's a rotation plus a fixed gain —
  keep that gain explicit so existing presets draw the same size.
- **Per-lane before stereo.** AC, full scale and filter act on single lanes;
  lag and rotation act on the pair. That's the same boundary the filter placement
  already respected.

### C1 · Each transform twice, from one set of numbers

Following the filter exactly — one parameter set, two implementations, one test
that they agree:

| Transform | Picture (JS) | Monitor (graph) | Agreement |
|---|---|---|---|
| Rotation / M-S | 2×2 matrix | `ChannelSplitter` → four `GainNode`s → `ChannelMerger` | exact |
| Full scale | multiply | `GainNode` | exact |
| Lag | interpolated read | `DelayNode` on one channel | to interpolation error; state the tolerance |
| AC coupling | one-pole DC blocker | the same one-pole as an `IIRFilterNode` | exact, if both use the same coefficients — *better than the note's mean-subtraction pairing, which cannot agree* |
| Filter | already done | already done | 0.0001 dB, existing test |

The AC row is a change from the note: rather than accepting a stated mismatch
between a mean subtraction and a high-pass, use the same one-pole DC blocker in
both places (`IIRFilterNode` takes the coefficients directly), and the two agree
by construction.

**Lag as audio is a comb filter and a Haas effect** — a fine thing to hear, but
at the τ values auto-lag picks it can also be a strong, pitch-tracking comb.

**The decision is the default depth, not whether it exists.** Framing it as a
listening yes-or-no was the wrong shape. A comb that tracks pitch and gets
stronger at exactly the τ auto-lag chooses is a real effect with a real
intensity dial, and full-strength summing of the delayed copy is both the
version most likely to sound bad and the version nobody would choose as a
default even if the effect is worth keeping. So the row becomes: a **mix**
control for the delayed copy into the monitor path, a conservative default —
somewhere well under unity, set by listening — and an explicit ceiling. That is
the move this page already makes for anything with an unpleasant extreme: the
limiter is last and not optional, the photocell's reach is clamped (D9), and
resonance is boosted but never quietly compressed. An on/off switch would be
the one shape inconsistent with all three.

**Built, and the assumption under "more mix, more comb" was wrong.** With mix
*m* the right channel is (1 − *m*) of the signal plus *m* of the delayed copy,
so its notch has depth |1 − 2*m*|: total at *m* = ½, and absent at *m* = 1,
where it is a pure Haas delay and sounds like width rather than a comb. It is
the mono sum — a laptop speaker, a room — that notches to 1 − *m* and is total
at the top. So in headphones the worst setting is in the middle of the range,
and the first draft's ceiling of 0.5 sat exactly on it; `combtest.py` caught it
before it was committed. The ceiling is 0.4 (right channel −14 dB at the notch,
room −4.4 dB) and the default 0.25 (−6 dB and −2.5 dB). Both are placeholders
for a pair of ears; the test asserts the properties — neither null reachable,
default under ceiling — rather than the numbers, so tuning them does not mean
editing a test.

What the ceiling costs: the top of the range, past the null, is a real and
possibly pleasant setting in headphones, and it is out of reach. Getting there
from the default means sweeping through the hole, so it would want a switch
rather than a longer slider; nobody has asked for it yet.

Lag is inside the block the two taps straddle now: with the speakers on the
input it is not heard at all, and switched off the stage is exactly the
identity, including when the delay is still holding the τ it last had.

### C2 · Widen the taps — built

`analyseAt` straddles the filter, the AC coupling and the rotation, which is
what `monitorAt` already did. The asymmetry was real and nothing had noticed
it, because nothing tested the combinations: *Input* took the filter out of the
picture and left the coupling and the rotation in, while taking all three out
of the speakers. `taptest.py` is the suite that would have.

Only `pre` changes meaning — it used to show an AC-coupled, rotated, unfiltered
trace and now shows the signal as it arrived. The default is `post` and is
untouched. The labels say *Shaped* rather than *Filtered*, and the readout
names what is actually in force rather than which switch is thrown.

### C3 · Monitoring a line input (D8) — built

Hearing the Nord *through* the transforms means monitoring a live input, which
the rule as written forbade. The rule was written for microphones, and it is
refined as below: an input carries a user-asserted kind, `mic` is never
connected to the destination, `line` may be behind an explicit toggle, and the
panel gives the browser's own latency figure with the limiter's lookahead added
to it. `livetest.py` holds the rule.

- An input has a user-asserted **kind**: `mic` (default) or `line`.
- `mic` inputs are never connected to the destination — the rule, unchanged.
- `line` inputs may be monitored, behind an explicit toggle, with a headphones
  note and the limiter last.

**Latency is the real cost here, not safety.** Monitoring through the browser adds
the input and output buffers to what the player hears — typically tens of
milliseconds, which a keyboardist will feel. Measure the round trip on the
actual interface; if it's too much, this configuration is where the JUCE port
earns its keep. Until then, A1 (hear the Nord directly, see it transformed) is
the playable version, and C3 is the "hear it shaped" version for when latency
allows.

### C4 · The rule that must not bend

**The limiter and hard clamp stay last**, after every new node. More transforms
in the monitor chain means more ways to build a loud surprise — resonant filter,
rotation and gain in series is a runaway path — and the clamp's guarantee only
holds while it is the final node before the destination.

### C · verification

- Agreement: each row of the C1 table, JS vs rendered graph in an
  `OfflineAudioContext`, at the stated tolerance.
- Order: a test that feeds a known stereo signal through lag + rotation and
  asserts the result matches the pinned order and not the other one.
- Mid/side migration: every preset using mid/side draws the same figure, same
  size, after it becomes rotation.
- Taps: **done** — all four `analyseAt × monitorAt` combinations, the three
  transforms each with a fingerprint of their own, and the drawn figure as well
  as the captured lanes. That last one was added because it was the only
  mutation of the four that survived.
- D8: a `mic` input is never connected to the destination regardless of toggles;
  a `line` input only when its toggle is on.
- Limiter: worst-case resonance + rotation + full-scale gain never exceeds the
  threshold at the destination.

---

## Stage D — two visualisers, as two lanes

Once the generator is an `AudioWorkletNode` it is just another lane, and racks
already mix files and live streams. "Generator plus Nord, overlaid" becomes the
existing Overlaid layout — **three lanes** (generator, Nord L, Nord R) against a
ceiling of six, no new drawing code.

What still needs deciding in the UI:

- **`state.source` stops being one thing.** The mutually exclusive Tone / Mic /
  File / Stems selector becomes "what's in the rack", with the generator as a lane
  type. The lane-budget question from the backing-track work applies: a band-split
  Nord wants four lanes by itself, so band split + generator + backing track does
  not fit, and the UI should say so at selection time.
- **"One with a transparent background"** maps to per-lane draw order and ink,
  which already exist. If that turns out not to be enough — if the generator
  genuinely wants its own timebase and persistence — that is the two-scope
  feature, and it gets its own note first (D5).

### D · verification

Generator + line input as lanes: shared trigger across lanes works; lane inks
remain distinct; X–Y can pair generator-L against Nord-L; removing the generator
lane leaves the Nord lanes untouched.

---

## Stage E — the photocell

The pixels feeding back into the sound. A software version of a real, if
obscure, practice — a light sensor taped to a screen, driving a synth — and as
far as the competitive survey found, not something any oscilloscope tool does.

### What it is

A **draggable reticle** on the screen. It reads brightness at its position and
registers as a mod source, `photo.1`. Park it on the edge of a Lissajous and it
pulses as the beam sweeps past; drop it into the middle of a wireframe and it
reads the density of the solid. Up to a small number of cells (they're sources,
so they take source inks; the six-ink ceiling applies).

A second, aggregate source — **frame brightness** or **frame change** — is cheap
to add alongside and is effectively an envelope follower on the picture. Worth
having, but the reticle is the feature.

### The phosphor grid (D9)

Rather than reading the canvas, keep a **shadow phosphor grid**: a low-resolution
`Float32Array` (say 64 × 64) in screen space. The same segment walk that
buckets the beam renderer's strokes also deposits into the grid — intensity from
the same speed-to-tone value, so it respects beam intensity — and the grid decays
each frame by the same persistence wash the canvas uses. A photocell reads a
small bilinear neighbourhood of it.

- Cost: one extra add per drawn segment and one decay pass over 4096 floats per
  frame. No `getImageData`, no GPU readback stall.
- Honesty: it is "what the phosphor would hold", not "what the screen shows after
  every effect". If that difference turns out to be visible in practice,
  `getImageData` on a tiny rectangle under the reticle is the upgrade — measured,
  not assumed.

### Stability — the real design work

The loop is audio → picture → grid → source → matrix → audio (or → picture
directly). It has at least a frame of delay and, through persistence, memory.
Loops like that ring or run away. Defences, all required:

- **A hard ceiling on the photocell's reach**: its routings' amounts clamp to a
  smaller range than other sources', and the default amount is low.
- **A slew limit on the source itself**, applied where the CC smoothing lives —
  upstream of `value()`. This bounds how fast the loop can move and damps
  frame-rate oscillation.
- **The limiter-last rule** covers the audio side; persistence's own decay
  bounds the picture side.

### Where the loop can close

- **Picture-only destinations** (rotation, persistence, lag τ): works today on any
  source. The loop never touches audio.
- **Audio destinations on a line input or file** (after C): the loop goes through
  what you hear.
- **Generator parameters** (after B): the generator's own figure modulates
  itself — the fullest version of the idea, and the one most likely to find the
  strange, self-organising states that make it worth building.

The photocell value is a main-thread source, so it rides the same batched
per-frame message into the worklet as `env.live` and the CCs (B3). No new
channel.

### E · verification

- Grid agreement: with persistence off, the grid's lit cells match the drawn
  segments' cells for a known figure.
- Decay: with persistence on, the grid decays at the same rate as the canvas
  wash, to a stated tolerance.
- **Stability:** seed the loop from silence and from a full-scale figure, route
  the photocell at maximum allowed amount to the most sensitive destination,
  run for 60 s headless, and assert grid energy and output level stay below a
  bound. The same shape as the worst-case resonance sweep test.
- Performance: the Stage 0 beam configuration with two photocells active, against
  the existing baseline.

---

## Risks, in the order they're likely to bite

1. **Band-limiting is invisible work that gates the visible kind** (B1). It
   produces nothing anyone can see, and everything audible waits on it.
2. **The LFO advancing twice**, now across a thread boundary. Mitigated by
   ownership that throws, not by care.
3. **Monitoring latency** making C3 unplayable. Measure early; it decides whether
   "hear it shaped" is a browser feature or a JUCE feature.
4. **The photocell loop running away.** Ceiling, slew and the limiter, plus a
   test that tries hard to make it diverge.
5. **Web MIDI invisible in the artifact.** Pages only; Safari never.
6. **Nord CC numbers differing on the actual firmware.** The built-in monitor and
   MIDI-learn make the default map a starting point, never an assumption.
7. **The expression pedal not being there.** Ask, don't assume CC 11.

## Suggested order of work

1. **A1 + A2** — MIDI, learn, dyad, tuning, note-as-ground-truth. Immediately
   playable; no audio machinery.
2. **B1** — PolyBLEP in the silent generator, verified by the harmonics pane.
3. **C0 → C2 on the line input** — pinned order, shared transforms, widened taps,
   all proven on the Nord before the worklet exists. **E (picture-only
   destinations)** can slot in here too.
4. **B2 → B4** — sample rate, worklet, envelope.
5. **C3** — line-input monitoring, if the measured latency allows.
6. **D** — generator as a lane.
7. **E, full loop** — photocell into generator and audio destinations.

Each step leaves the app shippable. The cut lines: after (1) you have a playable
instrument-driven scope; after (3) the picture's transforms are audible on real
audio; everything after that is the generator catching up to the Nord.

## Still open

- **Per-channel envelopes in dyad mode** — one envelope for the pair, or two?
  Two lets a held lower note sustain under a restruck upper one.
- **Photocell count** — capped by the six source inks, but is more than two ever
  useful in practice?
- **The two-scope composite** — deferred by D5; revisit only after using the
  two-lane version.
