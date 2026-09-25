# Shaping the sound, and playing the picture

A plan. It follows `playing-it-and-hearing-it.md` and assumes Stages A–F as they
stand: the generator is an `AudioWorkletNode`, the filter / AC / rotation / lag
are in the speakers as well as on the screen, the photocell and its picture
sources are in the matrix, the loop is bounded by `LOOP_TOTAL`, the slew and the
limiter, and a keyboard can be split into two layers. **Built so far:** G0,
G1's drawbars and morph (see *Built so far* under Stage G), S5, most of S6, and
K2 (see *Built so far* under Stage K). Nothing else here is.
Stage letters continue from F so that a reference like "Stage H2" is never
ambiguous across the two documents.

It comes after `laying-it-out.md`, the layout revamp, and on purpose: this plan
adds dozens of controls, and the layout they would have landed in could not fit
a rack of three lanes.

### Reviewed before writing in

The first draft was checked against the code and six things changed:

- **The letters.** It began at F, which is now the keyboard split. Everything
  moved up one: shapes are G, the voice H, the plane I, sound driving the
  drawings J, the picture playing music K, breadth L.
- **G0 is right.** `ramp` is band-limited in `waveAt` and offered as an LFO
  shape, and missing from the generator's Shape menu.
- **Crossings are counted from the beam, not the grid** (K1). The photocell
  reads the phosphor grid at the frame rate, sixty times a second, and a 220 Hz
  figure passes the reticle hundreds of times in that second. And at audio
  pitch "three against two" is a tone, not a rhythm: crossings are rhythm on
  the slow drawings, or through a divider to the clock.
- **The plane operations meet poly** (Stage I). In poly the heard pair is not
  the picture pair; see *I0*.
- **S1 is smaller.** New processing goes into the generator's core first,
  where seen-is-heard is free; the effects worklet for every source waits until
  something asks to fold the Nord.
- **S10 counts layers**: up to eight voices a layer, so sixteen.

What is being planned, in the order it was asked for:

1. **More ways to shape the sound**, as DSP rather than as pitch and level — and
   a picture that changes the sound *musically*, not only continuously.
2. **More waveform shapes.**
3. **Harmonograph, figure and wireframe driven by sound, and driving it.**
4. **Breadth**: whatever else makes the instrument wider rather than taller.

---

## The reframe: the missing thing is not DSP, it is events

Look at what the picture can say today. Every picture source — brightness,
Roundness, Coverage, Change, Novelty, Direction — is a *continuous number*, and
the continuity gate exists to keep it that way. Every destination it reaches is
a continuous parameter: a cutoff, a frequency, a spin rate. A continuous number
into a continuous parameter is a sweep. Sweeps are sound design; they are not
yet music.

Music is mostly **discrete**: a note starts, a pitch belongs to a scale, a beat
lands. So the plan splits in two, and the halves need different machinery:

- **More timbre** (Stages G, H, I). New oscillators, new processing inside the
  voice, and new operations on the stereo pair. This is DSP in the usual sense.
- **More music** (Stage K). Events, scales and a clock — a way for the picture
  to *play notes* rather than turn knobs. This is almost no DSP at all, and it
  is the part that answers "more musical" most directly.

Stage J, sound driving the drawn generators and back, sits between them and
borrows from both.

### Where new DSP should live

The generator's worklet already has the property every earlier transform had to
earn with a test: *the trace is the waveform that went to the speakers, sample
for sample.* Anything added inside `makeGeneratorCore` inherits that for free —
one implementation, seen and heard identically, no agreement test.

Anything added to the **monitor chain** for live inputs does not. The filter
needed `biquadCoefficients` in two places and `filtertest.py` to 0.0001 dB; the
lag needed a `DelayNode` against an interpolated read. Every new chain effect
built that way costs a second implementation and a test that they agree, and
most of the effects below (folders, clippers, polar warps) have no Web Audio
node to be the second implementation at all.

Hence S1, below: new processing is written once, as a per-sample JS function,
and runs in a worklet for every source.

---

## 0 · Decisions this plan takes

Marked **proposed** until confirmed, as before.

| # | Question | Proposed answer | Why |
|---|---|---|---|
| S1 | Where does new processing run? | **In the generator's core first.** A second, general-purpose *effects worklet* for live inputs and files — whose output would be what `capture` reads — is built only when an effect is wanted on something that is not the generator. | One implementation per effect instead of two plus an agreement test, and inside the core the trace is the sound by construction. The effects worklet changes the capture path for every live lane and costs up to six copies; that is worth paying for a reason, not in advance. |
| S2 | Oversampling for the non-linear stages? | **Yes, 2× by default, 4× selectable,** around the non-linear stages only (drive, fold, clip, sync, polar ops). Linear stages run at the base rate. | The drawn generators were measured and needed none. Folders and FM will not pass `aliastest.py` without it; measure 2× first and only default to 4× if it fails. |
| S3 | Discrete sources and the continuity gate | **Discrete sources are a second kind, with their own gate.** An *event* source (a trigger, a note) may only reach *event* destinations (gate, note, scale degree, interval menu, reswing). Its gate is a **rate limit and hysteresis**, not continuity. | A trigger is discontinuous by definition, so it cannot pass the existing gate; letting it reach a cutoff would be exactly the jump the gate exists to stop. |
| S4 | Do new energy-adding destinations join the loop? | **Drive, fold and resonance: yes, inside `LOOP_TOTAL`. Delay feedback: never.** `routingAllowed` classifies them. | A feedback coefficient near 1 is a loop inside the loop. Drive is bounded by the limiter; feedback is not bounded by anything but itself. |
| S5 | Global key and scale | **One key and scale for the page,** default *chromatic* (i.e. no quantising), used by the quantiser, the score and the arpeggiator. | Three features each with their own scale setting would disagree within a week. |
| S6 | A clock | **An internal transport (BPM, tap, start/stop),** with MIDI clock in when a device sends it. LFOs gain a *sync* option. | The score, the arpeggiator, delay times and synced LFOs all need one; none should own it. |
| S7 | Live audio into the generator | **Control-rate first** (per 128-sample block, analysis values posted in), **audio-rate second** (the worklet gains an input port). | Control rate covers every "sound drives the picture" idea except FM and warping by the input, which genuinely need samples. |
| S8 | Are drawn modes gated by the envelope? | **Opt-in, per mode: *Play the figure*.** Off, they draw continuously as now. On, a note sets the trace rate to the note's pitch and the envelope gates the amplitude. | The earlier decision not to blank the screen between phrases stays the default; this adds the instrument without taking the drawing away. |
| S9 | Does anything send MIDI out? | **Yes, opt-in, one port and channel,** rate-limited, all-notes-off on stop and on page hide. | The picture playing the Nord is the most literal "image alters sound" this project can do. |
| S10 | CPU budget | **Stated and measured**: voices × unison × oversampling must hold under a stated worklet load on a mid-range laptop. The UI reduces unison before it drops a voice. | Voices means both layers: up to eight each, so sixteen. Unison 7 × 16 × 4× is 448 oscillators a sample; this needs a number, not a hope. |

---

## Stage G — more shapes

Independent of everything else. Could ship first.

### G0 · a finding first

`waveAt` and the worklet harness both know `ramp`, and the LFOs offer it as a
shape, but the generator's Shape menu lists only five entries (Sine + 3rd, Sine,
Square, Triangle, Noise). Checked: the band-limited saw is built, tested and
unreachable. One `<option>`.

### G1 · the shapes

| Shape | What it is | Band-limiting | Parameter (modulatable) |
|---|---|---|---|
| Saw | `ramp`, exposed | polyBLEP, built | — |
| Pulse | variable-width square | polyBLEP at both edges | **Width** (`gen.width`), 5–95% — PWM is the classic reason to have an LFO |
| Drawbars | additive, nine partials at the Hammond footages (16′ 5⅓′ 8′ 4′ 2⅔′ 2′ 1⅗′ 1⅓′ 1′ → 0.5, 1.5, 1, 2, 3, 4, 5, 6, 8) | inherent: drop any partial above Nyquist | nine levels, 0–8 like the real bars |
| Supersaw | *n* detuned saws summed | polyBLEP per saw | **Spread**, voice count |
| Morph | a continuous position through sine → triangle → saw → square | crossfade of band-limited shapes | **Morph** (`gen.morph`) |
| Wavetable | a bank of single cycles, scanned | mip-mapped by octave, built by FFT once per table | **Position** (`gen.table`) |
| Pink / brown noise | filtered white | not needed | — |
| Stepped (S&H) | noise held for *n* samples | the steps alias; polyBLEP on each | **Rate** |

**Drawbars are the one to build first.** They are the Nord's own synthesis
method, an additive voice is band-limited by construction, and the nine levels
are exactly what the learned CCs already carry: a drawbar on the organ can be
routed to the same drawbar here. It also draws beautifully in X–Y against a
second channel at an interval, because the figure then shows the partials'
phase relationships.

**Morph matters more than its size suggests.** Today the shape is a menu, so
nothing can modulate it. A continuous morph is the first time a picture source
could change the *timbre* of the waveform rather than its pitch or level.

### G2 · shapes you make

- **Draw a cycle.** A pane where one period is drawn with the pointer, stored as
  a 2048-point table and band-limited like any wavetable. The picture literally
  becomes the sound.
- **Grab a cycle.** With a MIDI note held the input's period is *known*, not
  estimated — the note-as-truth work already exists. One period of the Nord,
  captured at a zero crossing, becomes a wavetable. Resynthesis in one button.

### Built so far

**G0**: the saw is on the Shape menu. **Drawbars**, with these decisions taken
on the way:

- **The levels are about 3 dB a step**, as on the organ, not a straight line from
  nought to eight.
- **The weights sum to at most one.** One bar at eight is full scale, and
  pulling out more changes the colour, not the level. That is unlike the
  organ, and it is deliberate: here full scale is the edge of the screen.
- **The bars are on the Shape tab**, nine patchable rows. Play shows the
  registration under the Shape menu, and pressing it goes to the bars.
- **Each layer has its own registration**, which makes layer B seven fields.
- **The default is 00 8740 000, not 88 8000 000.** With the 16' out, the
  readout's frequency is the sound's rather than the key's, and it wanders
  (see the README).

`drawbartest.py` holds them.

**Morph**: one position, 0 to 3, through sine, triangle, saw and square.
- It crossfades between the band-limited shapes, and is exact on each station.
- It is a destination, and full depth on it is a station and a half.
- Each layer has its own position, which makes layer B eight fields.
- Its saw is the menu's half a cycle later, or the triangle-to-saw crossfade
  cancels the fundamental.

`morphtest.py` holds it. Pulse, the supersaw, the wavetable, the noises, the
stepped shape and G2 are not built.

### G · verification

- `aliastest.py` gains every new shape at 440, 2000 and 4000 Hz with the same
  measured-then-pinned floors.
- Pulse at 50% width is the existing square to within the floor.
- Drawbars: with one bar out, the output is that partial and nothing else; a
  partial above Nyquist is silent rather than folded.
- Morph at its detents equals the named shape; between detents it is continuous
  (the continuity gate applies to destinations too).
- `workletharness.mjs` loops every shape for finiteness and peak, as it does now.

---

## Stage H — inside the voice

Needs nothing but the worklet. Everything here is in `makeGeneratorCore`, so it
is seen and heard identically without an agreement test.

Order within a voice, pinned now so nobody has to decide it later:

```
oscillator(s) → FM / sync → sub + unison sum → drive / fold → voice filter → envelope (VCA)
```

### H1 · a second oscillator, and what it is for

- **FM (two-operator).** A modulator at a ratio of the carrier, with an index.
  This is worth building here specifically because *the FM ratio is the same
  thing as the Lissajous ratio*: a 3:2 modulator produces a harmonic spectrum
  exactly when a 3:2 figure closes. The interval menu and the FM ratio can share
  the just-intonation table.
- **Hard sync.** A slave oscillator reset by the master. Needs polyBLEP at the
  reset, and the reset is at a known phase, so it can have it.
- **Ring / AM.** Carrier times modulator; almost free once FM exists.
- **Sub-oscillator.** One or two octaves down, square or sine.
- **Unison.** *n* copies, detuned by *Spread*, panned across the pair. In X–Y
  this is a figure that visibly thickens and shimmers, which is the right
  picture of what it sounds like.

### H2 · shaping

- **Drive** — `tanh` with a gain before and a compensating gain after.
- **Fold** — a wavefolder (sine fold, not reflection, for fewer corners).
  Folding is the most visual distortion there is: on Y–T the peaks fold back
  into the wave; in X–Y the figure grows petals.
- **Crush** — bit depth and sample-rate reduction.

All three are non-linear and run inside the S2 oversampling.

### H3 · a filter per voice

The page's filter is on the lane, after the mix. A played instrument wants a
filter per voice that follows the key and has its own envelope, so a low note
and a high note are equally bright and each note opens as it starts.

- A **state-variable filter** (low, band, high, notch from one structure; stable
  under fast modulation, which a biquad with recomputed coefficients is not).
- **Key tracking** 0–100%, and a **filter envelope** — a second ADSR — with an
  amount.
- The lane filter stays as it is. It is the measuring filter; this one is the
  instrument's.

### H · verification

- A new `voicefxtest.py`: FM at ratio 1:1, index 0 equals the carrier exactly;
  FM spectra land on the predicted sidebands; sync's reset is band-limited
  (floors pinned as in `aliastest.py`).
- Drive at unity gain in the linear region is transparent to 0.01 dB; fold with
  threshold above the peak changes nothing.
- The SVF against `getFrequencyResponse` of an equivalent biquad at static
  settings, and stable under a cutoff swept at audio rate.
- The worklet still passes `worklettest.py`: nothing new reaches a main-thread
  name.

---

## Stage I — the X–Y plane as an effects rack

The best result of Stage C was that **rotation turned out to be real DSP**:
turning a figure and rotating a stereo image are the same 2×2 matrix. That was
found by accident. This stage looks for more on purpose — operations that are
natural things to do to a *picture* of a stereo pair and turn out to be
musical things to do to its *sound*.

Each is a pure function of one sample pair `(x, y) → (x′, y′)`: one
implementation, in the S1 worklet, for every source.

| Operation on the picture | The same thing as audio | Linear? |
|---|---|---|
| Rotate (built) | stereo rotation; mid/side at 45° | yes |
| Scale X and Y separately | balance and width | yes |
| Shear | partial crossfeed of one channel into the other | yes |
| **Mirror** (x → \|x\|) | **full-wave rectification**: an octave up, all even harmonics | no |
| **Radial clip** (keep \|v\| ≤ r) | a stereo-linked soft clipper that preserves the image's direction | no |
| **Radial fold** (reflect past r) | a stereo-linked wavefolder | no |
| **Twist** (θ += k·r) | *level-dependent stereo rotation*: loud parts swirl, quiet ones stay put | no |
| **Snap** (quantise x and y to a grid) | a bitcrusher on both channels; pixelation on the screen | no |
| **Kaleidoscope** (fold θ into 1/n of a turn) | a new non-linearity; generates harmonics related to *n* | no |

The mirror is the headline. A rectifier is a guitar-pedal octave effect, and on
the screen it is the figure folded onto one half of itself — the same operation,
recognisable in both places. *Twist* is the one that probably does not exist
anywhere else as a sound: it only makes sense if you were looking at the stereo
pair as a picture first.

### I0 · the plane in poly

In every mode but poly the heard pair is the picture pair, and an operation on
the picture is the same operation on the sound. In poly it is not: every note is
heard in both ears, so the heard pair is nearly mono, while the picture puts the
bass on X against the rest on Y. Tying the two back together is the bug Stage F's
first version had, which split a chord across the ears.

**Proposed:** the operation is one function, applied to *both* pairs - the
picture pair and the heard pair - each as it is. Outside poly the two pairs are
identical, so nothing changes. In poly the per-channel non-linearities (mirror,
snap, radial clip on a near-mono pair) still do to the sound what they are named
for, while the stereo ones (rotate, twist, kaleidoscope) do little to a pair
whose channels are the same - which is the truth about a mono signal, and the
readout says so rather than the page pretending. Layers take the same rule, one
operation across both layers' pairs.

### I1 · time, which the plane does not have

Two classic effects are worth adding because they have honest pictures:

- **Delay**, tempo-synced (S6), with ping-pong. In X–Y the echoes are ghost
  figures trailing the live one. Feedback is clamped below 1 in the core and is
  never loop-reachable (S4).
- **Chorus / flanger.** A short modulated delay; the figure breathes and turns.
  The generator has no chorus of its own, which is noticeable next to the Nord.

Reverb is left out on purpose. On the screen it is a cloud that hides the
figure, and the monitor chain can take a convolver later, speakers-only, if it
is wanted.

### I2 · the taps

Every H operation sits inside the existing `analyseAt` / `monitorAt` block, so
*screen dry, speakers shaped* and the other combinations keep working and
`contracttest.py`'s four-way tap check extends to each.

### I · verification

A new `planetest.py`:

- Each linear op matches its matrix to float precision.
- Mirror on a sine at *f* has its fundamental at 2*f* and no odd harmonics.
- Radial clip never produces a sample pair with magnitude above *r*, and leaves
  the angle of every pair unchanged.
- Twist with k = 0 is identity; with a signal of constant magnitude it equals a
  plain rotation by k·r (the fixture that proves the law).
- Each non-linear op, run through S2, meets a pinned aliasing floor.
- And — as with rotation — a check that the op is applied **once**: in the
  worklet and not again in `drawXY`. Rotation's double application was only
  caught because a circle cannot witness it; the fixtures here must not be
  circles.

---

## Stage J — sound drives the drawn generators, and back

### J1 · the sound as a source

Today a live input reaches the matrix as *Level* and *Envelope*, and the Nord
as notes and CCs. Add analysis sources, all under the continuity gate:

| Source | From | Range |
|---|---|---|
| Pitch | the note if one is held, else the estimator (behind its confidence gate) | octaves around a reference |
| Brightness | spectral centroid | 0–1, log-frequency |
| Band 1–4 | the band-split filters that already exist | 0–1 each |
| Width | the goniometer's correlation | −1…1 |
| Flux | frame-to-frame spectral change | 0–1 |

And one event source (S3): **Onset**, from flux with hysteresis and a minimum
gap. It is the drum hit that can restart a harmonograph.

If any of these measures the generator's own output, it is a loop and goes
through `routingAllowed` and `LOOP_TOTAL` exactly as a picture source does.

### J2 · per mode

| | Sound → the drawing | The drawing → sound |
|---|---|---|
| **Harmonograph** | *Onset* reswings it: a hit restarts the drawing. *Level* drives the pendulums (energy in) instead of letting them only run down. Input *Pitch* sets the ratio. | **Pitched harmonograph** (below). Its envelope and swing phase become sources. |
| **Figure** | *Brightness* on detail (more points on the star as the tone opens). A played dyad's p:q sets a rose's k = p/q — so consonance closes the rose the way it closes a Lissajous. | *Play the figure* (S8): a note sets the trace rate to its pitch, the envelope gates it. The figure's shape is the timbre. |
| **Wireframe** | *Onset* is an angular impulse with friction — hits spin it and it coasts down, which reads as physical in a way a modulated spin rate does not. Bands 1–3 onto the X, Y and Z spin. *Level* pushes the vertices out from the centre. | Its attitude (three angles) and facing become sources; *Play the figure* applies as for figures. |

**The pitched harmonograph is the natural one.** A harmonograph is a sum of
damped sinusoids, and a sum of damped sinusoids is a struck or plucked tone. At
2.1 Hz it is a drawing and inaudible; with the swing rate following the note
and a note-on reswinging it, it is a plucked voice whose decay is the drawing
running down, and whose detune is the beating between strings. The relet fade
that fixed the click is already the right tool for a retrigger.

### J3 · audio rate (S7, second half)

Give the generator worklet an input. Then:

- **Input as FM.** The Nord frequency-modulates the figure's trace.
- **Input as displacement.** The path plus *k* times the input: the figure is
  drawn with the organ riding on its outline.
- **Input as clock.** The figure is traced at the *input's* phase rather than
  its own, so it is phase-locked to whatever is playing — the organ holds the
  picture still.

### J · verification

A new `hearingtest.py`: each analysis source against a known fixture (a sine
sweep for Pitch and Brightness; a click train for Onset with its count
asserted); each passes the continuity gate or is declared an event; a source
reading the generator's own output is refused past `LOOP_TOTAL`; the pitched
harmonograph's fundamental matches the note within a stated cents tolerance and
a retrigger produces no step above the relet floor.

---

## Stage K — the picture plays music

This is the direct answer to "alter the sound in a more musical way". Needs S3,
S5 and S6.

### K1 · events from the picture

- **Crossings.** A photocell fires when the beam passes it, with hysteresis and
  a rate limit. Put two on a Lissajous figure and the interval becomes a
  rhythm: a 3:2 figure fires **three against two**. The consonance the screen
  already draws becomes a polyrhythm you hear. A tempered fifth drifts in and out
  of phase, which is audible as the pattern slipping.

  Two things this needs, found when the draft was checked. **The crossing is
  detected from the beam's samples**, in the worklet or in capture, as the path
  passing within a radius of the reticle - not from the phosphor grid, which is
  read sixty times a second while a 220 Hz figure passes the reticle hundreds
  of times. And **it is rhythm only when the drawing is slow**: at audio pitch
  three against two is 330 against 220 Hz, a tone. The harmonograph at 2 Hz, a
  figure traced a few times a second, or any figure through a divider locked to
  the clock (S6) are where crossings are a rhythm; the harmonograph and figure
  modes are their natural home.
- **Thresholds.** Any continuous picture source can be turned into an event by
  crossing a level (with hysteresis), so *Change spikes* or *Coverage fills*
  can gate a note.

### K2 · the quantiser

A matrix stage between any source and a pitch destination: snap to the page's
scale (S5), with a *slew* for portamento between steps. A photocell on a
figure, quantised to D dorian, plays a melody instead of a siren. Quantised
values are events (S3), so they obey the rate limit.

### K3 · the score

The phosphor grid read as a graphical score, in the line of Daphne Oram's
Oramics and the ANS synthesiser: a **playhead** scans the 64 columns at the
clock's tempo; rows map to scale degrees, low at the bottom; the brightest *n*
rows in a column become the chord, brightness the velocity. Draw a figure, and
it plays itself; rotate it and the melody inverts. It needs nothing new to read
from — the grid already exists and is already bounded.

### K4 · out to the Nord (S9)

Every event in this stage can also go out as MIDI. With the Nord on *Local
Off*, the picture plays the organ, the organ comes back in on its line inputs,
and the loop closes through a real instrument. Rate-limited, all-notes-off on
stop and on `visibilitychange`, and the readout says when notes are being sent.

### K5 · the arpeggiator

Cheap once the clock exists, and it earns its place because of the picture:
each step of an arpeggio over a held dyad or chord redraws the figure, so the
screen cycles through the shapes of the chord's intervals in time.

### Built so far

**S5**: one key and scale for the page, C chromatic by default, in a *Key and
tempo* section on the Sources tab.

**S6**, all but an internal start and stop:
- a tempo slider;
- tap tempo, which also restarts the locked oscillators;
- MIDI clock in, read as a mean over two dozen ticks, with Start restarting the
  locked oscillators and Continue not;
- a *Sync* on each oscillator, from four bars to a semiquaver, with triplets.

**K2**, the quantiser, which takes the pitch after modulation to the key.
- It has hysteresis of a tenth of a semitone and a rate limit of forty steps a
  second, which is the S3 gate for this one event source.
- It has a glide of its own.
- It is page-wide, applying to both layers and every poly voice. Not per
  routing: the plan's "a stage between any source and a pitch destination" would
  need a note to count steps from, and the README says why that was not the
  choice.

`keytest.py` and `clocktest.py` hold them. K1's crossings, K3 to K5, and S3 in
general are not built.

### K · verification

`eventtest.py`: two crossings on a just 3:2 figure fire in a 3:2 ratio over ten
seconds, exactly; on the equal-tempered figure the phase between them drifts at
the beat rate; the rate limit is never exceeded under a noise fixture; the
quantiser only ever outputs scale degrees. `scoretest.py`: a single lit row
plays one repeated note; a diagonal plays a scale; an empty grid plays nothing
and sends nothing. MIDI out: all-notes-off is sent on stop, and on page hide.

---

## Stage L — breadth

Smaller things, each worth doing on its own and none blocking the others.

- **Record.** `MediaRecorder` on the canvas stream plus the output audio: a clip
  of the scope and its sound, which is what someone will want to share first.
- **Morph between setups.** Two setup codes and a crossfader over every
  continuous field — a macro that the matrix can also drive.
- **Macros.** User-named sources with no oscillator behind them: one knob, many
  destinations. The matrix already does the fan-out.
- **More figures and solids.** Butterfly curve, Lissajous knot, *n*-gon; the
  dodecahedron, icosahedron and a torus. **Text**: single-stroke (Hershey-style)
  glyph paths, so the scope can write a word. **Import**: an SVG path as a
  figure. Each needs an entry in the worklet harness's figure loop and a
  finiteness check; any with a jump in its path re-runs `aliastest.py`'s
  statement about the drawn generators.
- **Draw a figure**, the X–Y sibling of G2's drawn cycle.
- **A second generator lane.** A waveform and a figure together, one of them
  modulating the other at audio rate once J3 exists. Costs a lane of the six.
  Half of this exists as Stage F's layers, which are two sets of voices from one
  core; what is not there is a *drawn* mode beside a waveform, since layer B is
  always a waveform.

---

## Dependencies

```
laying-it-out.md (the layout) ─► everything below
G (shapes) ───────────────────────────────┐
H (voice) ── S2 oversampling ─────────────┤
I (plane) ── S2 (S1 only for live inputs) ┼──► L
J1 (sources) ─► J2 (per mode) ─► J3 (S7) ─┤
S5 scale + S6 clock ─► K1 … K5 ───────────┘
```

**Suggested order**, by value against cost:

1. **The layout revamp** (`laying-it-out.md`), because everything here adds
   controls.
2. **G0** and **G1's drawbars** — hours, not days, and immediately audible.
3. **G1's morph**, the first shape a source can move.
4. **S5/S6 with K1's crossings**, counted from the beam on the slow drawings,
   and **K2's quantiser** — which is where "more musical" actually lives.
5. **J2's pitched harmonograph and *Play the figure*** — they turn two drawings
   into instruments with very little new code.
6. **I**, mirror and radial clip first, in the generator's core; then **H**,
   then **J3**, then **K3**, **K4** and L as wanted.

The piece of invisible work to size first is S2: most of I and all of H2 wait
on it. S1 is only needed once an effect is wanted on a live input.
