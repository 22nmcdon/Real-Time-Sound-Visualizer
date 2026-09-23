# Playing it, hearing it, and letting it listen to itself — the plan

**Where this stands.** Stage A is built: MIDI in, CC learn, the dyad, the tuning
switch, and the note as ground truth for the lag, the timebase and the tuner.
**B1 is built too** — the generator is band-limited, ahead of the sound that
needs it. Everything else from Stage B on is still a plan.
`web/tests/miditest.py` and `web/tests/aliastest.py` hold the verification A
and B1 asked for.

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
| D9 | Photocell v1: canvas readback or an intermediate tap? | **A low-resolution shadow phosphor grid** fed by the same segment walk the beam renderer does. Canvas readback only if v1 looks meaningfully wrong. | Nearly free, persistence-aware, and never touches `getImageData`. Measure before paying for the honest version. |

---

## Dependencies

```
            ┌──────────── A · MIDI + Nord audio in ────────────┐
            │  (independent — ships first)                      │
            │                                                   ▼
 B1 band-limit ─► B3 worklet ─► B4 gate/envelope      E · photocell
      │               │                                   ▲
      │               ├──────────► D · overlay (lanes)    │
      │               ▼                                   │
      │         C · transforms in the audio path ─────────┘
      │               ▲
      └── C can start on mic/file/rack before B exists ──┘
```

- **A** needs nothing. It is useful immediately and it is the thing asked for first.
- **B1** (band-limiting) needs nothing and can be verified while the generator is
  still silent — the harmonics pane measures it.
- **C** works today on mic, file and rack sources. Prove it there before the
  worklet exists; B only extends it to the generator.
- **D** is nearly free once B3 lands.
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

### B2 · Sample-rate audit

`const rate = 44100` becomes `ctx.sampleRate` — 48000 on most machines. Audit
every alignment, capacity and span computation that assumed 44100. The
`length + span + LAG_MAX ≤ CAPACITY` assertion from the lag work is the model:
make each assumption an assertion at the point it's used.

### B3 · The worklet

Move the per-sample loop — `waveAt`, `figureAt`, wireframe projection,
harmonograph — into an `AudioWorkletNode`.

**Single-file constraint.** The note's answer is the right one and better than
the build-step alternative raised in review: write the processor as a real
function in the file and `String(fn)` it into a Blob URL. It stays parsed by
`node --check`. Add a test that goes one step further than parsing: evaluate the
stringified source in Node against a stub `AudioWorkletProcessor` /
`registerProcessor` and run one `process()` block — a blob that parses but
references a main-thread identifier fails there instead of in the browser.

**LFO ownership, enforced rather than remembered.** Every oscillator source gets
an `owner` field — `"worklet"` or `"main"` — set once at registration. Both
advance paths check it and **throw in dev** if they are asked to step a source
they don't own. This project has shipped a double-rate LFO once; the second time
should be an exception on first frame, not a wrong rate in production. Plus the
test from the note: a 2 Hz LFO completes two cycles in one second, measured in
the worklet.

**Traffic across the boundary**, one channel each way, both posted on change,
never polled:

- main → worklet: routing list; generator parameters; **main-thread source
  values** (`env.live`, CCs, and later the photocell) in one batched message per
  frame.
- worklet → main: the sample ring the picture reads, replacing today's JS ring.

Main-thread sources arrive once per frame, so inside the worklet they are
**held and ramped across the block**, not stepped — the same one-pole smoothing
CCs get, for the same reason.

### B4 · Gate and envelope

`tone.amp` is a constant today; there is nothing to gate. Keys that sound need an
envelope, and this is new code, not wiring:

- A per-voice ADSR in the worklet, driven by the note stack's gate. In dyad mode
  one envelope covers the pair; whether each channel gets its own is a later
  choice.
- **Legato rule:** a new note while the gate is already open changes pitch
  without retriggering (standard mono behaviour), with an optional glide.
- The envelope is **also registered as a mod source** — `env.note` beside
  `env.live`. Play harder, the figure opens.

### B · verification

- B1: a band-limited square's harmonics pane shows no energy at non-harmonic
  frequencies above a stated floor, at 440 Hz and at 4 kHz; the existing THD
  tests still pass.
- B2: every sample-rate assumption asserted at 44100 and 48000.
- B3: stringified processor runs one block in Node; LFO rate test in the worklet;
  the dev-mode ownership throw fires when both paths claim one source.
- B4: rendered in an `OfflineAudioContext`, a note-on/off produces the expected
  envelope within one block; legato doesn't retrigger; no clicks at gate edges.
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
Worth a listening check before shipping it on by default.

### C2 · Widen the taps

`analyseAt` and `monitorAt` move from straddling the filter to straddling the
whole block. The four combinations keep their meanings; nothing new in the UI
except that the switch labels stop saying "filter".

### C3 · Monitoring a line input (D8)

Hearing the Nord *through* the transforms means monitoring a live input, which
the current rule forbids. The rule was written for microphones. Refine it:

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
- Taps: all four `analyseAt × monitorAt` combinations, on a file source and on
  the generator.
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
