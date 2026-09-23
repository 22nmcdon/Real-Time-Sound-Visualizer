# Playing it, and hearing it

A design note. Nothing here is built. It covers three things asked for together,
which turn out to be one thing with a dependency order:

1. **MIDI in**, from a Nord Electro 6D — notes and panel CCs.
2. **The generator makes sound**, and the picture's own settings shape that
   sound, in either order: heard-then-drawn, or drawn-then-heard.
3. **Two visualisers at once**, one from the live audio and one from the
   generator, overlaid.

(2) is the load-bearing one. (3) is nearly free once (2) lands, and (1) is
independent of both and could go first.

---

## The reframe: this is the filter's pre/post pair, widened

"I want the oscilloscope's image to actually alter the sound" sounds like a new
kind of thing. It is not — it is a thing this app already does for exactly one
transform, and the question is how many more to do it for.

The filter already has **two taps**, and they are independent on purpose:

| | |
|---|---|
| `analyseAt` | `pre` \| `post` — does the *screen* read before or after the filter |
| `monitorAt` | `pre` \| `post` — do the *speakers* get before or after the filter |

Three of the four combinations are useful and all three are shipping. "Screen
filtered, speakers dry" is the filter as an instrument for looking. "Both post"
is a filter in the ordinary sense. "Screen dry, speakers filtered" lets you watch
what you are feeding it.

**The ask is that pair, applied to more than the filter.** Both orderings named
in the request are already points in that two-switch space:

- *generator → audio → image → image alters audio → output* is `analyseAt: pre`,
  `monitorAt: post` — you see the raw signal and hear the shaped one.
- *the image settings affect the sound before the image* is both `post` — you
  hear and see the same shaped signal.

So the feature is not a new mechanism. It is **widening the block those two
switches straddle**, from the filter to everything the picture does that is
genuinely a signal transform.

### Where the line already falls

The capture pipeline's order was pinned deliberately when the filter landed:

```
source lanes → AC removal → per-lane filter → derived views (mid/side | lag) → trigger → slice
```

Everything up to and including *derived views* is a transform on a signal.
Everything from *trigger* onward is drawing. The line the request needs is
already drawn through the middle of the pipeline; it just has no switch on it
yet.

Sorting the display controls by which side they fall on:

| Control | A signal transform? | As audio it is |
|---|---|---|
| AC coupling | yes | a DC blocker / high-pass |
| Full scale | yes | a gain |
| Filter (type, cutoff, resonance) | yes | **already both** |
| Mid / side | yes | the standard M/S matrix |
| Lag X–Y | yes | a short delay on one channel — a comb, and audibly a Haas effect |
| X–Y rotation | yes | a rotation of the stereo vector; at 45° it *is* mid/side |
| Zoom | partly | a gain in X–Y; in Y–T it is a time zoom and means nothing |
| Timebase, trigger, position, holdoff | no | framing, not signal |
| Persistence, beam intensity | no | the phosphor. There is no audio analogue |
| Graticule, cursors, panes | no | furniture |

The first six are the ones worth wiring. **Rotation is the surprise**: turning an
X–Y figure and rotating a stereo image are the same 2×2 matrix, so a control
that exists purely to make the picture prettier turns out to be a real and
musical stereo operation. That one is worth building for its own sake.

### The price, and the precedent that sets it

Each transform that wants to be in both places needs **two implementations from
one set of numbers, and a test that they agree.** That is not speculation — it is
what the filter already does: `biquadCoefficients` feeds a JS biquad for the
picture and a `BiquadFilterNode` for the monitor, and `filtertest.py` asserts the
two match to **0.0001 dB** across 560 points. That test is the reason the
`Q`-in-decibels bug could not come back.

Every new shared transform follows it. Rotation and mid/side are a matrix in both
places and will agree exactly; lag is a JS interpolated read against a
`DelayNode`; AC is a mean subtraction against a high-pass, which will *not* agree
exactly and needs its tolerance stated rather than assumed.

### The other reading, named so it can be rejected

"Image alters audio" has a second, wilder reading: the **drawn pixels** feeding
back into the sound — read the canvas, derive something (beam density, how much
of the graticule is lit, the figure's area), and modulate the audio with it.

That is a different feature and a genuinely circular one: a loop with a frame of
delay in it, which will ring or run away without a ceiling on the return path. It
is buildable and it would be unlike anything else, but it is not what Stage C
below describes. Worth deciding which was meant.

---

## Stage A — MIDI in

Independent of the rest. Could ship first, on its own.

### What the Nord actually gives

From the research, and consistent with the Electro 6 manual's appendix:

- **Nine drawbars, CC 16–24.** Nine continuous 0–127 faders — the richest set of
  physical controllers on the instrument.
- **Swell / control pedal, CC 11.** Ranked first here, against the research's
  ordering. It is the only continuous control you can move *while both hands are
  playing*, and on organ programs velocity is fixed, so it — not velocity — is
  the expression source. Every drawbar costs you a hand.
- Sustain CC 64; section levels 13 / 34 / 43; Effect 1/2 Rate 86 / 90; Delay
  Amount 93; Reverb Amount 113; Rotary Speed 108 (switched).
- **No pitch wheel, no mod wheel, no aftertouch, no assignable knobs.**

Per-session setup the app cannot do for the player, and should therefore say on
screen: **Local → Off** to silence the Nord's own engine (reverts to On at every
power cycle), and System Menu 12 → **Send & Receive** so CCs transmit at all.

### Notes: dyad by default, mono as an option

The generator is already two channels derived from one pitch and a ratio:
left is `tone.freq`, right is `tone.freq × intervalRatio(tone.interval)`. That
makes **mono last-note priority the wrong default for this instrument.**

Hold two notes and let them *be* the two channels. Play a fifth and X–Y draws the
2:3 figure of the interval actually under your hands, in the keyboard's own
tuning; walk through thirds and sixths and the figure walks with you. The entire
Lissajous half of this app stops being something you set and becomes something
you play. One held note falls back to a unison.

Both modes come out of one held-note stack, so build the stack and read it two
ways:

- **Dyad** — the two most recent held notes are left and right.
- **Mono** — top of the stack sets `freq`; the interval control stays manual.

Edge cases that have to be in from the start, not added after: note-on with
velocity 0 **is** a note-off; release everything on `blur` and
`visibilitychange`, or a note hangs when the tab loses focus; the same note
arriving twice without a release must not stack twice.

### CCs as modulation sources

This part is genuinely small. `MOD_SOURCES` is a string-keyed registry of
`{id, label, ink, bipolar, value()}`, and a CC is
`{id: "cc.16", value: () => cc[16]}`. Everything downstream already works:
additive summation, the depth editor, the lane, and the `source>dest@amount`
encode format, which takes `cc.16` unchanged.

Two things not to do:

- **Do not register 127 CCs.** MIDI-learn instead: a CC becomes a source the
  first time it moves, auto-named from a built-in Nord map ("Drawbar 1") but
  editable. The chip list stays short and it self-documents the firmware actually
  in front of you — which is also the right answer to the research's warning that
  Nord revises CC behaviour across OS versions.
- **Do not smooth per destination.** 7-bit steps are audible on a slow sweep;
  smooth the CC value *upstream* of `value()` with a one-pole, and both the
  direct `.set()` path and the `setTargetAtTime` path are fixed by one filter
  rather than two that have to agree.

The matrix's additive summation is already better than the tools this would be
copying: in Vital, assigning one CC to several parameters reliably drives only
the last, so users route CC → macro → many. Here many routings can share a source
by construction.

### Where it can run

Web MIDI needs a secure context, and in a **cross-origin iframe it needs the
embedding page to grant `midi` in its permissions policy** — the same shape as
the microphone question. So this very likely cannot work in the published
artifact at all. **Pages stops being a convenience and becomes the only way to
use the feature.** Safari has no Web MIDI on any platform and no announced
roadmap; feature-detect and say so plainly rather than appearing dead.

### Testing it without the keyboard

Stub `navigator.requestMIDIAccess` with a fake port and dispatch synthetic
messages. That covers parsing, the note stack, velocity-0-as-note-off, the blur
panic, dyad vs mono, CC normalisation, smoothing and learn. Only the actual CC
numbers need the Nord — and the app should ship a live MIDI monitor readout so
those can be checked against this document rather than trusted from it.

---

## Stage B — the generator's own audio

The big one, and the one everything else waits on.

Today `makeToneSource` contains **no `AudioContext` at all**. It is a per-sample
JS ring buffer at a hardcoded 44100, filled from `requestAnimationFrame`, feeding
the screen and nothing else. Making it audible means an `AudioWorkletNode` and
moving the per-sample loop — `waveAt`, `figureAt`, the wireframe projection, the
harmonograph — into the worklet.

### Band-limiting is a hard prerequisite, not a nicety

`waveAt` is not band-limited. `square` is `Math.sin(phase) >= 0 ? 0.9 : -0.9` and
`ramp` is a raw sawtooth. Silent, that is correct — it is a *picture* of a square
wave, and a perfect one. Audible, it aliases, and this app **ships a "Harmonics
and THD" preset**: foldover lands at non-harmonic frequencies and the harmonics
pane will report it as content. The instrument would be lying in exactly the
place it claims to measure.

So PolyBLEP for square/saw/PWM comes first. And note what PolyBLEP does *not*
cover: figure, wireframe and harmonograph produce arbitrary geometric paths whose
discontinuities are not at known phase points. Those need oversampling in the
worklet (render at 4× and decimate) or a stated limit. This is the largest single
piece of work in the whole note and it is invisible from the outside.

### Three hazards specific to this codebase

**The LFO double-advance.** The rule today is that every oscillator advances
*exactly once* per elapsed time: per-sample inside `fill()` for the tone source,
per-frame in `applyModMatrix` for everything else, and the two are mutually
exclusive. Move the DSP into a worklet and the per-sample half moves with it,
while the main thread must be stopped from also stepping it. This project has
already shipped a double-rate LFO once. It needs a test that asserts a 2 Hz LFO
completes two cycles in one second *in the worklet*, the way `modtest.py`
asserts it today.

**Two-way traffic.** The worklet needs the routing list (posted on change, not
polled). And `env.live` — the input's RMS, computed on the main thread from an
analyser — has to travel *into* the worklet to stay usable as a source. That is
a message port in both directions and a source of staleness.

**The single-file constraint.** A worklet needs a separate module URL. The trick
is a `Blob` from the source text — but written as a string literal, the DSP stops
being parsed by `node --check` and the extract/check discipline silently stops
covering the most numerically delicate code in the app. Write the worklet as a
real function and `String(fn)` it into the blob, so it is still parsed as part of
the file.

Also: `const rate = 44100` becomes `ctx.sampleRate`, which is 48000 on most
machines. `source.sampleRate` already exists and is mostly honoured, but the
alignment and capacity arithmetic assumes it and wants auditing.

---

## Stage C — the transforms move into the audio path

Needs B for the generator's own sound, but **works today for mic, file and rack
sources**, which already have a monitor chain. Worth doing in that order: prove
rotation-as-audio on a microphone before the worklet exists.

The work is the six transforms in the table above, each implemented twice from
one set of numbers, each with a test that the two agree — following the filter
exactly. Then the two switches widen from "the filter" to "the block", and the
orderings asked for fall out of the existing four combinations.

One rule that must not bend: **the limiter and the hard clamp stay last.** More
nodes in the monitor chain means more ways to make a loud surprise, and the
clamp's guarantee — that nothing can exceed the largest value in its curve — only
holds while it is the final node before the destination.

---

## Stage D — two at once

Today `state.source` is **one** source, and Tone / Mic / File / Stems are
mutually exclusive. That is the only thing standing between here and two
visualisers.

But the machinery for several signals at once already exists: `makeRackSource`
mixes several files as lanes, and play-along already mixes a file *and* a live
stream as lanes. The generator is excluded only because it is not an `AudioNode`.

**Stage B fixes that by construction.** Once the generator is a worklet node it
is just another lane in a rack, and "generator plus live input, overlaid" is the
existing Overlaid layout with no new drawing code at all. Three lanes against a
ceiling of six.

The catch is in the wording. "Two overlapped visualisers, one with a transparent
background" can mean two things:

- **Two lanes on one graticule** — free once B lands, different inks, one clock,
  one timebase.
- **Two independent scopes composited** — each with its own timebase, display
  mode and persistence. That is a real piece of work: the draw path reads one
  `state` for display settings throughout, so this means a second set of them and
  two render contexts.

These are not the same feature, and the second breaks something deliberate: rack
lanes share one clock *on purpose*, because lanes on different timebases cannot
be compared, which is the only reason to put them on one screen. Two independent
timebases means two instruments that happen to overlap — which may be exactly
what is wanted for a clean generator figure behind a messy live one, but it
should be chosen rather than discovered.

---

## Risks, in the order they are likely to bite

1. **Band-limiting is invisible work that gates the visible kind.** It is the
   long pole in Stage B and it produces nothing anyone can see.
2. **The LFO advancing twice.** Already shipped once in this project, and moving
   half the matrix across a thread boundary is the ideal conditions for it.
3. **The worklet source escaping `node --check`.** Mitigated by `String(fn)`, and
   worth a test that asserts the blob actually parses.
4. **Feedback, once the picture's controls reach the speakers.** A resonant
   filter, a rotation and a gain in series is a runaway path. The clamp handles
   the ceiling; the ordering rule handles the rest.
5. **Web MIDI's iframe permission** making the whole of Stage A invisible in the
   artifact, and the feature appearing broken rather than unavailable.
6. **Nord CC numbers** differing from this document on the actual firmware. The
   built-in monitor is the answer; the default map should be a starting point the
   user can correct, never a hardcoded assumption.

## Open questions

- **"Image alters audio": transforms, or pixels?** This note assumes the
  transforms. The pixel-feedback reading is a different and stranger feature.
- **Two visualisers: two lanes, or two scopes?** Free versus a second display
  state.
- **Does a MIDI note change the picture in every generator kind**, or only in
  Waveform? In wireframe, `freq` is the rate the solid is drawn at, so a note
  would change how fast it tumbles. That is interesting rather than wrong, but it
  is a choice.
- **Does zoom join the shared transforms?** It is a gain in X–Y and meaningless
  in Y–T, which makes it the one control in the table that would behave
  differently depending on the display mode.
