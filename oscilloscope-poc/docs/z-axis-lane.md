# A Z axis: brightness as a third signal

Not built. This is the design as it stood when stages one and two shipped, written
down so it can be picked up without re-deriving it.

It concerns the **web surface** — `scope.html`, published at
<https://claude.ai/artifact/VjYAQCP19wUryJ9Cpfyakx> — rather than the Python app in
this repository. It lives here because this is the durable half of the project.
Function names below are from version 13; line numbers will have drifted.

---

## What it is

A real scope with a Z input lets a third signal modulate the beam's brightness at
each instant, independently of where the beam is. Vector displays use it for two
things: depth cueing, where nearer lines are brighter, and **blanking**, where the
beam is switched off entirely while it moves between disjoint parts of a figure.

The page already shades the beam by speed (stage one). A Z lane multiplies into that
rather than replacing it: `1 / speed` is what the beam *does*, Z is what it is *told*.

## The DC-coupling question does not arise

This is worth recording because it is the first objection the idea attracts.

DC coupling is a property of an analog **input path** — a series capacitor that blocks
DC — and there is no such capacitor anywhere in this chain. A WAV holds absolute
sample values; `decodeAudioData` → `AudioBufferSourceNode` → `AnalyserNode` high‑passes
nothing; the page's "AC" is an opt‑in per‑lane *display* option that is off by default.
For a file‑sourced Z channel, absolute level is preserved end to end, which is exactly
what brightness needs — "how bright right now", not "how much did brightness wiggle".

Coupling only bites when real analog hardware is in the path: capturing Z from a line
input, where it equally bites X and Y, or driving a physical CRT, where sustained
blanking decays through the interface's output capacitors. That last one is a genuine
constraint for people playing oscilloscope music out to real tubes. It is not a
constraint on a scope that draws to a canvas.

Nor is hardware needed for the channel itself: `makeRackSource` already takes up to six
independent lanes from separate files, so X/Y/Z is three WAVs or one three‑channel WAV.

## Do not give the tone source a third channel

The obvious implementation — have `makeToneSource().channels` return 3 in wireframe
mode — was traced and breaks in about a dozen places. Recording them so the idea is not
revisited:

- `laneCount()` returns 3, but nothing calls `fitChannels` when the generator dropdown
  changes, so `state.channels[2]` is `undefined` and `capture()` throws. **The generator
  dropdown would white‑screen the app.**
- `stacked()` flips true, so Y‑T silently rearranges into three bands.
- `laneName(2)` returns `"Right"`, so the depth lane is labelled Right in the legend,
  the trigger switch and both X‑Y selects.
- Giving the tone source a `lanes` array to fix that makes `buildLaneList` render
  Solo/Mute rows and call `source.remix()` and `lane.gain`, which it does not have.
- `buildTrigSources` offers Depth as a trigger source, which would route
  `computeSpectrum`, the harmonic analysis and the tuner at a non‑audio signal.
- `writeMeasures` prints peak/RMS/frequency/note for it as though it were audio.
- `writeReadout` takes peak across **all** channels, and a depth signal is near ±1 by
  construction — so the verdict pins to **"Clipping."** permanently, in the one colour
  the design reserves for real faults.
- Mid/side dies silently (its guard requires exactly 2 channels) while its checkbox
  stays enabled.
- Preset snapshot/restore only knows two lanes, so the Z lane's settings survive preset
  loads, violating the contract that a preset sets everything.
- `restore` sets the mode but never rebuilds the lane rows, so wireframe → wave leaves a
  third row in the DOM after `fitChannels` has truncated `state.channels` back to two —
  and the next change event writes to `state.channels[2].on` and throws.

## Carry it out of band instead

**`frame.aux`.** The tone source grows a third internal buffer and a `getLatestAux(n)`
beside `getLatestWindow`. It is *not* in `channels`, so no lane plumbing sees it.
`capture()` slices it with the identical `from`/`length` and hangs it on the frame.
Trigger alignment comes free. About six lines, and zero changes to lanes, legend,
measurements, presets, trigger, spectrum or clipping.

**`state.zLane = null | "aux" | 0..5`.** For a rack, "lane 3 as brightness" reads a
*normal* lane — still measured, still legible, still available to the trigger — and only
`drawXY` treats it specially. One state field, one branch, one select. A `role: "z"` flag
on `state.channels[i]` would mean touching eight or more consumers to earn the same thing.

Note that the rack's analyser tap is **pre‑gain** by design, so a lane's mix level and
mute do not reach the trace. Calibrate brightness with the display‑side `gainOf(i)`, not
with the mix.

## Semantics

```
m = clamp((z + 1) / 2, 0, 1)        // intensity multiplier
```

multiplied into the speed term *before* quantising into the ramp's steps, plus a **blank
threshold** below which the segment is skipped outright rather than drawn faintly.

Sample `z` at the segment start for intensity, but use `min(z[i], z[i + stride])` for the
blank decision, so a bright chord cannot leak through a stride window.

Blanking is the honest implementation of flyback. Under `darken` a faint line is
permanent — written once at infinite persistence it never fades — so "draw it dim" is not
a substitute for "do not draw it".

**The mapping convention is not standardised.** Different oscilloscope‑music tools encode
the Z channel differently, and some invert it. Expose the threshold and an invert switch
rather than guessing one.

## What it unlocks

1. **Blanked flyback**, which is the interesting one. Stage two traces solids with
   hand‑built closed routes precisely *because* jumps could not be blanked. With a Z lane
   the beam can lift, and then arbitrary meshes become possible — which is where the
   hand tables stop scaling. That needs Hierholzer's algorithm for the circuit plus
   parity fixing (a minimum‑weight T‑join over the odd‑degree vertices) if you still want
   closed routes, or nothing at all if you are happy to blank between edges.
2. **Depth cueing.** Stage two paces the beam by screen‑space arc length so that
   brightness reports real dwell and says nothing about depth. A Z lane carrying the
   projected `z` restores depth as an explicit term rather than an accident.
3. **Imported oscilloscope music** that ships a brightness channel, played through the
   rack's existing multi‑file transport.

## Why it was deferred

It is additive rather than foundational. Stages one and two are complete and shippable
without it: the beam shading works, and the wireframes trace correctly because the routes
are closed. Stage three improves flyback fidelity and opens the door to imported Z data —
both real, neither blocking.

## Where it plugs in

| what | where |
|---|---|
| the aux buffer | `makeToneSource`, beside the two‑channel ring buffer |
| `frame.aux` | `capture()`, using the same `from` / `length` |
| the lane picker | the rack rows, beside the X‑Y pair selects |
| intensity and blanking | `strokeBeam`, in the per‑segment loop that already exists |
| preset round‑trip | `DEFAULTS` / `snapshot()` / `restore()` |
