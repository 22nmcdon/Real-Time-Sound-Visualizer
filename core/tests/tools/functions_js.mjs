/* The page's own pure functions through a list of calls, one result line per
   call, as functions_cpp prints them. The calls are written by parity.py;
   the language is one call a line, `name arg ...`, where an argument is a
   number, a word (a shape's name), a list `a,b,c`, or a drawn cycle's tables
   `T:most:t0;t1;...` (each table a list), or a bank of them `B:` with the
   cycles split by `!`. Usage: node functions_js.mjs <calls> */
import fs from "node:fs";
import { pageScope, coreScope, mulberry32 } from "./js_core.mjs";

const f = pageScope(["TWO_PI", "DRAWBAR_HARMONICS", "INTERVALS", "cycleOf", "polyBlep", "polyBlamp",
                     "drawbarGain", "drawbarWeights", "intervalRatio", "svfG", "svfStep", "cycleRead", "waveAt"]);

const tables = (text) => {
  const [, most, body] = text.split(":");
  return { most: Number(most), levels: body.split(";").map((t) => Float32Array.from(t.split(",").map(Number))) };
};
const arg = (w) => {
  if (w.startsWith("T:")) return tables(w);
  if (w.startsWith("B:")) return w.slice(2).split("!").map((c) => tables("T:" + c));
  if (w.includes(",")) return w.split(",").map(Number);
  const n = Number(w);
  return Number.isNaN(n) && w !== "NaN" ? w : n;
};
const show = (v) => (Array.isArray(v) ? v : [v]).map((x) => Number(x).toPrecision(17)).join(" ");

const out = [];
for (const raw of fs.readFileSync(process.argv[2], "utf8").split("\n")) {
  const words = raw.trim().split(/\s+/);
  if (!words[0]) continue;
  const [name, ...rest] = words;
  const a = rest.map(arg);
  if (name === "noiseRun") {
    // shape seed samples hz rate: a note's phase advancing, the noise drawn.
    const [shape, seed, samples, hz, rate] = a;
    // PINK_GAIN brings BROWN_GAIN with it: the page declares the two in one statement.
    const c = coreScope(["PHASE_WRAP", "PINK_GAIN", "makeNoise", "noiseStep"], rate, mulberry32(seed));
    const z = c.makeNoise(), values = [];
    let phase = 0;
    for (let i = 0; i < samples; i++) {
      phase += f.TWO_PI * hz / rate;
      if (phase >= c.PHASE_WRAP) phase -= c.PHASE_WRAP;
      values.push(c.noiseStep(z, shape, phase, hz / rate));
    }
    out.push(show(values));
    continue;
  }
  if (name === "oscRun") {
    const p = Object.fromEntries(rest.map((kv) => kv.split("=")).map(([k, v]) => [k, arg(v)]));
    const c = coreScope(["UNISON_MAX", "PHASE_WRAP", "dtOf", "makeOsc", "wrapJump", "makeVoiceFx", "voiceFxFor",
                         "unisonAsked", "oscStep"], p.rate);
    const t = { shape: p.shape, width: 0.25, table: 1.5, morph: 0, fmIndex: p.fm, modRatio: p.mod, ringMix: p.ring,
                syncRatio: p.sync, subLevel: p.sub, subOctave: p.suboct, subShape: p.subsine ? "sine" : "square",
                unison: p.n, unisonCents: p.cents, vcfType: 0, vcfQ: 0.707, drive: 0, fold: 0, crushBits: 0, crushHz: 0 };
    const o = c.makeOsc(), x = c.makeVoiceFx(), bars = p.bars === "-" ? undefined : p.bars, values = [];
    c.voiceFxFor(t, x, p.fmr === 1, p.syncr === 1, false);
    let base = 0;
    for (let i = 0; i < p.samples; i++) {
      if (i === p.flip) { t.unison = p.n2; c.voiceFxFor(t, x, p.fmr === 1, p.syncr === 1, false); }
      const hz = p.hz + (p.hz2 - p.hz) * i / p.samples;
      x.fmI = p.fm;
      x.syncR = p.sync + p.sweep * i / p.samples;
      base += f.TWO_PI * hz / p.rate;
      if (base >= c.PHASE_WRAP) base -= c.PHASE_WRAP;
      values.push(c.oscStep(o, base, p.offset, hz, t, bars, p.amount, x));
    }
    out.push(show(values));
    continue;
  }
  if (name === "lowpassTaps") {
    out.push(show(Array.from(coreScope(["lowpassTaps"], 48000).lowpassTaps(a[0]))));
    continue;
  }
  if (name === "shapeRun") {
    // factor drive fold drivePush foldPush x,x,...: one voice's shaper.
    const [factor, drive, fold, dp, fp, xs] = a;
    const c = coreScope(["lowpassTaps", "shapeTaps", "shDrive", "shapeFactor", "shapeSample", "setShaping",
                         "makeShaper"], 48000);
    c.__set("shapeFactor", factor);
    c.setShaping({ drive, fold }, dp, fp);
    const sh = c.makeShaper();
    out.push(show(xs.map((x) => sh.step(x))));
    continue;
  }
  if (name === "crushRun") {
    // crushHz crushBits rate x,x,...: the depth's step from voiceFxFor, as the core has it.
    const [hz, bits, rate, xs] = a;
    const c = coreScope(["UNISON_MAX", "makeVoiceFx", "voiceFxFor", "unisonAsked", "makeCrush", "crushStep"], rate);
    const t = { crushHz: hz, crushBits: bits, unison: 1, vcfType: 0, vcfQ: 0.7071, drive: 0, fold: 0,
                fmIndex: 0, ringMix: 0, syncRatio: 1, subLevel: 0, unisonCents: 0 };
    const x = c.makeVoiceFx(); c.voiceFxFor(t, x, false, false, false);
    const z = c.makeCrush();
    out.push(show(xs.map((v) => c.crushStep(z, v, t, x))));
    continue;
  }
  if (name === "vcfRun") {
    // cutoff env track q type noteHz rate push x,x,... env,env,...
    const [cutoff, envAmt, track, q, type, note, rate, push, xs, envs] = a;
    const c = coreScope(["KEY_REF", "makeVcf", "vcfHz", "vcfCoef"], rate);
    const t = { vcfCutoff: cutoff, vcfEnv: envAmt, vcfTrack: track, vcfQ: q, vcfType: type };
    const st = c.makeVcf(), k = 1 / Math.max(0.1, q);
    // At sample 80 one setting moves (`cutoff`, `env` or `track` and its new value).
    const key = { cutoff: "vcfCutoff", env: "vcfEnv", track: "vcfTrack" }[rest[10]];
    out.push(show(xs.map((x, i) => {
      if (i === 80 && key) t[key] = a[11];
      return f.svfStep(st, x, c.vcfCoef(st, t, note, envs[i], push), k, type);
    })));
    continue;
  }
  if (name === "svfRun") {
    // A run of samples through one filter from rest: g k type x,x,x...
    const s = { ic1: 0, ic2: 0 };
    out.push(show(a[3].map((x) => f.svfStep(s, x, a[0], a[1], a[2]))));
  } else if (name === "drawbarWeights") {
    out.push(show(f.drawbarWeights(a[0], new Array(9))));
  } else if (name === "intervalRatio") {
    out.push(show(f.intervalRatio(a[0], a[1] === 1)));
  } else if (name === "waveAt") {
    // waveAt shape phase step bars amount, with "-" for no bars.
    out.push(show(f.waveAt(a[0], a[1], a[2], rest[3] === "-" ? undefined : a[3], a[4])));
  } else {
    out.push(show(f[name](...a)));
  }
}
process.stdout.write(out.join("\n") + "\n");
