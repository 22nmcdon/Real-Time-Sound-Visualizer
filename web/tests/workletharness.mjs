/* Runs the generator's worklet module the way a worklet would, in Node, with
   the three globals a worklet gets and nothing else.

   The point is not that it parses - `node --check` already says that about the
   whole page. The point is that it RUNS. A module built by stringifying a list
   of functions goes wrong by leaving one of them out, or by the core reaching
   for a name that only exists on the main thread, and neither of those is a
   parse error. Both are a `ReferenceError` on the first sample, and this is
   where that happens: in a test, with the name in the message, rather than as
   a generator that is silent in a browser for a reason nobody can see.

   Every mode is driven, because the four of them touch different halves of
   the code - the wireframe is the only thing that reaches for MODELS, and the
   figure is the only thing that calls `figureAt`.

   Usage: node workletharness.mjs <module.js> <slots>
*/
import fs from "node:fs";

const [, , path, slotsText] = process.argv;
const text = fs.readFileSync(path, "utf8");
const slots = Number(slotsText) || 8;

globalThis.sampleRate = 48000;
globalThis.currentFrame = 0;
globalThis.currentTime = 0;

let registered = null;
globalThis.registerProcessor = (name, cls) => { registered = { name, cls }; };
globalThis.AudioWorkletProcessor = class {
  constructor() {
    this.posted = 0;
    this.port = { onmessage: null, postMessage: () => { this.posted++; } };
  }
};

const report = { ok: false };
try {
  // Indirect eval, so the module's own `const`s land in a scope of their own
  // rather than colliding with this file's.
  (0, eval)(text);
  if (!registered) throw new Error("the module registered no processor");
  report.name = registered.name;

  const node = new registered.cls({
    processorOptions: {
      slots,
      lfos: [
        { shape: "sine", rate: 2, depth: 0.5 },
        { shape: "square", rate: 0.5, depth: 0.3 },
      ],
      tone: { freq: 220, amp: 0.55 },
      routes: [{ index: 0, held: 0, slot: 0, amount: 0.5, unipolar: false }],
    },
  });

  const out = [new Float32Array(128), new Float32Array(128)];

  /* Every field set, not just the ones a mode reads.

     The first version of this drove the four modes with `{mode}` alone and
     passed while the real thing threw in its constructor: `set("model", ...)`
     is the only caller of `wire.set`, which is the only caller of
     `MODEL_BY_NAME`, which was the name missing from the module. A setter
     that is never called is a branch that is never checked, so this calls all
     of them with values a panel could actually produce. */
  const everyField = {
    mode: "wave", shape: "harmonic", freq: 220, amp: 0.55, interval: 3,
    octaves: 1, just: false, phase: 1.2, figure: "Spirograph", detail: 7,
    figureRate: 40, swingRate: 2.1, decay: 0.12, detune: 0.004,
    model: "Tetrahedron", spin: [0.11, 0.17, 0], spinRate: 1, depth: 0.45,
  };
  for (const field in everyField) {
    node.port.onmessage({ data: { tone: { [field]: everyField[field] } } });
  }
  node.port.onmessage({ data: { reswing: true } });
  node.port.onmessage({ data: { lfos: [{ shape: "ramp", rate: 3, depth: 1 }] } });

  report.modes = {};
  for (const mode of ["wave", "harmonograph", "figure", "wireframe"]) {
    node.port.onmessage({ data: { tone: { mode } } });
    let worst = 0, energy = 0, finite = true;
    for (let round = 0; round < 60; round++) {
      node.process([], [out], {});
      for (let i = 0; i < 128; i++) {
        for (const channel of out) {
          const v = channel[i];
          if (!Number.isFinite(v)) finite = false;
          worst = Math.max(worst, Math.abs(v));
          energy += v * v;
        }
      }
    }
    report.modes[mode] = { worst, finite, energy: energy / (60 * 128 * 2) };
  }

  // And every shape of the waveform mode, since each is a different branch of
  // `waveAt` and the band-limiting is only on three of them.
  node.port.onmessage({ data: { tone: { mode: "wave" } } });
  report.shapes = {};
  for (const shape of ["sine", "harmonic", "triangle", "square", "ramp", "drawbars", "morph", "noise"]) {
    node.port.onmessage({ data: { tone: { shape } } });
    /* Cleared first. The block is shared between shapes, and a shape whose
       branch throws writes nothing into it - so the samples it was judged on
       were the previous shape's, and a drawbars branch with its table
       missing from the module passed as a saw. */
    for (const channel of out) channel.fill(0);
    let worst = 0, finite = true;
    for (let round = 0; round < 20; round++) {
      node.process([], [out], {});
      for (let i = 0; i < 128; i++) for (const channel of out) {
        if (!Number.isFinite(channel[i])) finite = false;
        worst = Math.max(worst, Math.abs(channel[i]));
      }
    }
    report.shapes[shape] = { worst, finite };
  }

  node.port.onmessage({ data: { tone: { mode: "wireframe" } } });
  report.models = {};
  for (const model of ["Cube", "Tetrahedron", "Octahedron"]) {
    node.port.onmessage({ data: { tone: { model } } });
    node.port.onmessage({ data: { reswing: true } });   // from the same attitude
    let worst = 0, finite = true, fingerprint = 0;
    for (let round = 0; round < 30; round++) {
      node.process([], [out], {});
      for (let i = 0; i < 128; i++) for (const channel of out) {
        if (!Number.isFinite(channel[i])) finite = false;
        worst = Math.max(worst, Math.abs(channel[i]));
        fingerprint += channel[i] * channel[i];
      }
    }
    fingerprint = Math.round(fingerprint * 1e6) / 1e6;
    // A fingerprint rather than a peak. `wire.set` keeps the model it has
    // when the name is not found, so three solids that all quietly drew the
    // cube would every one of them be "finite and not silent" - which is what
    // the missing `MODEL_BY_NAME` actually did, and what the first version of
    // this check could not see.
    report.models[model] = { worst, finite, print: fingerprint };
  }

  node.port.onmessage({ data: { tone: { mode: "figure" } } });
  report.figures = {};
  for (const figure of ["Circle", "Square", "Star", "Rose", "Heart",
                        "Infinity", "Spiral", "Spirograph"]) {
    node.port.onmessage({ data: { tone: { figure } } });
    let worst = 0, finite = true;
    for (let round = 0; round < 20; round++) {
      node.process([], [out], {});
      for (let i = 0; i < 128; i++) for (const channel of out) {
        if (!Number.isFinite(channel[i])) finite = false;
        worst = Math.max(worst, Math.abs(channel[i]));
      }
    }
    report.figures[figure] = { worst, finite };
  }

  /* The quantiser, in the thread it runs in: 225 Hz is 0.39 of a semitone
     above A3, so chromatic takes it to 220 exactly, and off leaves it. */
  node.port.onmessage({ data: { routes: [] } });      // nothing else moving the pitch
  node.port.onmessage({ data: { tone: { mode: "wave", shape: "sine", freq: 225, octaves: 0, qMask: 4095 } } });
  for (let round = 0; round < 20; round++) node.process([], [out], {});
  report.quantised = { on: node.core.pitch };
  node.port.onmessage({ data: { tone: { qMask: 0 } } });
  for (let round = 0; round < 5; round++) node.process([], [out], {});
  report.quantised.off = node.core.pitch;

  /* The pitched harmonograph, and a strike, in the thread they run in: at
     220 Hz it sounds, and a reswing while it sounds is a strike rather than
     a restart from nothing. */
  node.port.onmessage({ data: { tone: { mode: "harmonograph", pitched: true, freq: 220, ringMs: 400,
                                        interval: 0, octaves: 0, crossOn: false } } });
  let pitchedPeak = 0, pitchedFinite = true;
  for (let round = 0; round < 200; round++) {
    if (round === 100) node.port.onmessage({ data: { reswing: true } });
    node.process([], [out], {});
    for (let i = 0; i < 128; i++) {
      if (!Number.isFinite(out[0][i])) pitchedFinite = false;
      pitchedPeak = Math.max(pitchedPeak, Math.abs(out[0][i]));
    }
  }
  report.pitched = { pitch: node.core.pitch, peak: pitchedPeak, finite: pitchedFinite };
  node.port.onmessage({ data: { tone: { mode: "wave", pitched: false } } });

  /* The plane, at each factor, in the thread it runs in: a mirrored sine
     has no negative half left, whatever the filters do to its corners. */
  report.plane = {};
  for (const os of [1, 2, 4]) {
    node.port.onmessage({ data: { tone: { mode: "wave", shape: "sine", freq: 220, amp: 0.5,
                                          planeMirror: 3, planeRadius: 0.3, planeLimit: 1, planeOS: os } } });
    let low = Infinity, high = -Infinity, finite = true;
    for (let round = 0; round < 40; round++) {
      node.process([], [out], {});
      if (round < 5) continue;
      for (let i = 0; i < 128; i++) {
        if (!Number.isFinite(out[0][i])) finite = false;
        low = Math.min(low, out[0][i]); high = Math.max(high, out[0][i]);
      }
    }
    report.plane[os] = { low, high, finite };
  }
  node.port.onmessage({ data: { tone: { planeMirror: 0, planeLimit: 0 } } });

  /* The rest of the plane and the time effects, each on a diagonal - one
     signal in both channels - and each read for what it alone would do:
     the fold holds the pair inside its radius, the snap puts it on a grid,
     the twist, the kaleidoscope and the chorus take it off the diagonal,
     the matrix halves X, and the delay goes on after the tone stops. */
  const PLANE_OFF = { planeTwist: 0, planeKaleido: 0, planeLimit: 0, planeSnap: 0, planeScaleX: 1,
                      chorusMix: 0, delayMix: 0, planeOS: 2, amp: 0.5 };
  const runFor = (tone, rounds) => {
    node.port.onmessage({ data: { tone: Object.assign({ mode: "wave", shape: "sine", freq: 220, interval: 0,
                                                        octaves: 0, phase: 0 }, PLANE_OFF, tone) } });
    // Both oscillators back to nought: earlier here Y ran an octave above
    // X, and the two phases were left apart - no diagonal without this.
    node.port.onmessage({ data: { reswing: true } });
    const r = { finite: true, peak: 0, apart: 0, offGrid: 0, lowY: Infinity, ratio: 0 };
    for (let round = 0; round < rounds; round++) {
      node.process([], [out], {});
      if (round < 5) continue;
      for (let i = 0; i < 128; i++) {
        const x = out[0][i], y = out[1][i];
        if (!Number.isFinite(x) || !Number.isFinite(y)) r.finite = false;
        r.peak = Math.max(r.peak, Math.hypot(x, y));
        r.apart = Math.max(r.apart, Math.abs(x - y));
        r.offGrid = Math.max(r.offGrid, Math.abs(x * 2 - Math.round(x * 2)));
        r.lowY = Math.min(r.lowY, y);
        if (Math.abs(y) > 0.1) r.ratio = Math.max(r.ratio, Math.abs(x / y));
      }
    }
    return r;
  };
  report.planeRest = {
    plain: runFor({}, 40),
    fold: runFor({ planeLimit: 2, planeRadius: 0.2 }, 40),
    snap: runFor({ planeSnap: 2, planeOS: 1 }, 40),
    twist: runFor({ planeTwist: 3 }, 40),
    kaleido: runFor({ planeKaleido: 3 }, 40),
    matrix: runFor({ planeScaleX: 0.5 }, 40),
    chorus: runFor({ chorusMix: 1, chorusDepthMs: 3, chorusMs: 12, chorusRate: 2, chorusFeedback: 0 }, 80),
  };
  // 50 ms at 48 kHz is 2400 samples, under 19 blocks: the tone stops and
  // the repeat is still coming for that long, then nothing.
  runFor({ delayMix: 1, delayMs: 50, delayFeedback: 0 }, 40);
  node.port.onmessage({ data: { tone: { amp: 0 } } });
  let echoed = 0, after = 0;
  for (let round = 0; round < 40; round++) {
    node.process([], [out], {});
    for (let i = 0; i < 128; i++) {
      if (round < 17) echoed = Math.max(echoed, Math.abs(out[0][i]));
      else if (round > 20) after = Math.max(after, Math.abs(out[0][i]));
    }
  }
  report.planeRest.delay = { echoed, after };
  node.port.onmessage({ data: { tone: PLANE_OFF } });

  // The crossings, in the thread they run in: a 4 Hz beam fires both lines.
  node.port.onmessage({ data: { tone: { freq: 4, amp: 0.9, interval: 0, octaves: 0, crossOn: true } } });
  for (let round = 0; round < 800; round++) node.process([], [out], {});
  report.crossings = node.core.crossings;
  node.port.onmessage({ data: { tone: { crossOn: false } } });

  /* A restart counted on the main thread reaching the oscillators here: a
     new count puts the phase back to nought, and the same count sent again
     - which every frame does - leaves it alone. */
  const lfoAt = (epoch) => ({ lfos: [{ shape: "sine", rate: 3, depth: 1, epoch }] });
  node.port.onmessage({ data: lfoAt(0) });
  for (let round = 0; round < 50; round++) node.process([], [out], {});
  const before = node.lfos[0].phase;
  node.port.onmessage({ data: lfoAt(1) });
  const reset = node.lfos[0].phase;
  for (let round = 0; round < 50; round++) node.process([], [out], {});
  node.port.onmessage({ data: lfoAt(1) });
  report.epoch = { before, reset, again: node.lfos[0].phase };

  report.posted = node.posted;
  report.ok = true;
} catch (error) {
  report.error = String(error && error.stack ? error.stack.split("\n")[0] : error);
}

process.stdout.write(JSON.stringify(report));
