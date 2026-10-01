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
  if (name === "voicesRun") {
    /* A layer's chord through `reconcileVoices` and `sound`, the four mixes a
       sample. `ev` is the events, `;` between them, each `sample:what`: a
       note list (`note/hz/velocity/role`, `+` between notes, `none` for
       every key up), `null` (the layer off), `cut:k` (the governor's fade
       on the k-th voice) or `set:field:value` (a slider moved mid-note) or `factor:f` (the
       shaper's oversampling, as the governor sets it). */
    const p = Object.fromEntries(rest.map((kv) => { const i = kv.indexOf("="); return [kv.slice(0, i), kv.slice(i + 1)]; }));
    const n = (k) => Number(p[k]);
    const rate = n("rate");
    const make = () => ({
      shape: p.shape, amp: n("amp"), attackMs: n("a"), decayMs: n("d"), sustain: n("s"), releaseMs: n("r"),
      fAttackMs: n("fa"), fDecayMs: n("fd"), fSustain: n("fs"), fReleaseMs: n("fr"),
      vcfType: n("vtype"), vcfCutoff: n("vcut"), vcfQ: n("vq"), vcfTrack: n("vtrack"), vcfEnv: n("venv"),
      drive: n("drive"), fold: n("fold"), crushBits: n("cbits"), crushHz: n("chz"), unison: n("n"),
      unisonCents: n("cents"), fmIndex: n("fm"), modRatio: n("mod"), ringMix: n("ring"), syncRatio: n("sync"),
      subLevel: n("sub"), subOctave: n("suboct"), subShape: n("subsine") === 1 ? "sine" : "square",
      width: n("width"), table: n("table"), morph: n("morph"),
    });
    /* On layer B the other layer's filter envelope is different, so a voice
       that read layer A's view would be told apart from one reading B's. */
    const onB = p.layer === "b", tone = make(), toneB = make();
    if (onB) Object.assign(tone, { fAttackMs: 1, fDecayMs: 37, fSustain: 0.2, fReleaseMs: 23 });
    const t = onB ? toneB : tone;
    const c = coreScope(["dtOf", "mix", "UNISON_MAX", "PHASE_WRAP", "Q_HYSTERESIS", "qHold", "qGlide",
                         "quantiserFor", "nearestAllowed", "quantise", "NOISES", "PINK_GAIN", "makeNoise", "noiseStep",
                         "makeOsc", "wrapJump", "oscStep", "makeVoiceFx", "voiceFxFor", "unisonAsked", "lowpassTaps",
                         "shapeTaps", "shDrive", "shapeFactor", "shapeSample", "setShaping", "makeShaper", "shaperOf",
                         "makeCrush", "crushStep", "KEY_REF", "makeVcf", "vcfHz", "vcfCoef", "CUT_SAMPLES", "fenvView",
                         "fviewA", "POLY_TAILS", "ROLES", "chordMoved", "reconcileVoices", "sound"],
                        rate, mulberry32(n("seed")), { tone, toneB });
    c.__set("qMaskNow", n("qmask")); c.__set("qGlide", n("qglide")); c.__set("shapeFactor", n("factor"));
    const x = c.makeVoiceFx();
    c.voiceFxFor(t, x, n("fmr") === 1, n("syncr") === 1, n("shr") === 1);
    x.fmI = t.fmIndex; x.syncR = t.syncRatio; x.vcfPush = n("vpush");
    c.setShaping(t, n("dp"), n("fp"));
    const bars = p.bars === "-" ? undefined : arg(p.bars);
    const events = new Map();
    for (const e of p.ev.split(";")) {
      const at = Number(e.slice(0, e.indexOf(":")));
      if (!events.has(at)) events.set(at, []);
      events.get(at).push(e.slice(e.indexOf(":") + 1));
    }
    const voices = [], values = [], samples = n("samples");
    for (let i = 0; i < samples; i++) {
      for (const what of events.get(i) || []) {
        if (what === "null") c.reconcileVoices(voices, null, t);
        else if (what.startsWith("cut:")) { const v = voices[Number(what.slice(4))]; if (v) v.fade = c.CUT_SAMPLES; }
        else if (what.startsWith("factor:")) c.__set("shapeFactor", Number(what.slice(7)));
        else if (what.startsWith("set:")) { const [, field, value] = what.split(":"); t[field] = Number(value); }
        else {
          const list = what === "none" ? [] : what.split("+").map((w) => {
            const [note, freq, velocity, role] = w.split("/");
            return { note: Number(note), freq: Number(freq), velocity: Number(velocity), role };
          });
          c.reconcileVoices(voices, list, t);
        }
      }
      const bend = n("bend") + (n("bend2") - n("bend")) * i / samples;
      c.sound(voices, t, bars, n("amount"), bend, n("duck"), c.dtOf, n("glide"), x);
      values.push(c.mix[0], c.mix[1], c.mix[2], c.mix[3]);
    }
    out.push(show(values));
    continue;
  }
  if (name === "planeRun") {
    /* The plane through `planeSetup`, `planeTick` and `planeStep`, three
       pairs a sample - layer A's picture, layer B's, the heard pair - with
       the setup done again every 128 samples, as a block would. Its routings'
       pushes are sines of their own, rounded as the Float32Array holding them
       rounds them. `ev` moves a tone field at a sample: `500:planeOS:4`. */
    const p = Object.fromEntries(rest.map((kv) => { const i = kv.indexOf("="); return [kv.slice(0, i), kv.slice(i + 1)]; }));
    const n = (k) => Number(p[k]);
    const rate = n("rate");
    const FIELDS = ["planeMirror", "planeRadius", "planeOS", "planeLimit", "planeScaleX", "planeScaleY", "planeShear",
                    "planeTwist", "planeKaleido", "planeSnap", "delayMix", "delayMs", "delayFeedback", "delayPingPong",
                    "chorusMix", "chorusRate", "chorusDepthMs", "chorusMs", "chorusFeedback"];
    const tone = Object.fromEntries(FIELDS.map((f) => [f, n(f)]));
    const c = coreScope(["poleFor", "opX", "pTwist", "planeOp", "DELAY_MAX", "CHORUS_MAX", "delayGlide", "chorusPhase",
                         "makeTimeFx", "readLine", "timeStep", "lowpassTaps", "makeOversampler", "planeFactor", "fxA",
                         "linearOn", "chorusSin", "genMod", "planeSetup", "planeTick", "planeStep"],
                        rate, null, { tone, slots: 40 });
    const events = new Map();
    for (const e of (p.ev || "").split(";").filter(Boolean)) {
      const [at, field, value] = e.split(":");
      if (!events.has(Number(at))) events.set(Number(at), []);
      events.get(Number(at)).push([field, Number(value)]);
    }
    const g = c.genMod, values = [];
    let on = false;
    for (let i = 0; i < n("samples"); i++) {
      for (const [field, value] of events.get(i) || []) tone[field] = value;
      if (i % 128 === 0 || events.has(i)) on = c.planeSetup(n("twr") === 1, n("ecr") === 1);
      g[c.__get("RADIUS_SLOT")] = n("rpush") * Math.sin(i * 0.0031);
      g[c.__get("TWIST_SLOT")] = n("tpush") * Math.sin(i * 0.0047 + 1);
      g[c.__get("ECHO_SLOT")] = n("epush") * Math.sin(i * 0.0023 + 2);
      g[c.__get("ECHO_TIME_SLOT")] = n("etpush") * Math.sin(i * 0.0013 + 3);
      let x = 0.7 * Math.sin(f.TWO_PI * 220 * i / rate) + 0.25 * Math.sin(f.TWO_PI * 661 * i / rate);
      let y = 0.5 * Math.sin(f.TWO_PI * 330 * i / rate + 0.4);
      // A pair held still, on exact halves of the snap's grid: see parity.py.
      if (n("inp") === 1) { x = -0.375; y = 0.625; }
      if (!on) { values.push(x, y, y, x, x, y); continue; }
      c.planeTick(1 / rate);
      c.planeStep(c.__get("osA"), c.fxA, x, y); values.push(c.__get("opX"), c.__get("opY"));
      c.planeStep(c.__get("osB"), c.__get("fxB"), 0.8 * y, 1.1 * x); values.push(c.__get("opX"), c.__get("opY"));
      c.planeStep(c.__get("osHeard"), c.__get("fxHeard"), 0.6 * (x + y), 0.6 * (x - y));
      values.push(c.__get("opX"), c.__get("opY"));
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
