/* The page's own `makeGeneratorCore`, driven as its worklet drives it - a
   block of 128 at a time into Float32Arrays, with the page's calls between
   blocks - through the runs in a file, one result line per run, as
   generator_cpp prints them.

   The core is assembled from the page the way `generatorModuleSource`
   assembles the worklet: the names that function binds, read out of its own
   text, each definition lifted from the page, and the solids handed over as
   JSON as the worklet gets them. So a helper added to the core and to the
   worklet's list is in this runner too, and one missing from the list fails
   here as it would in a browser.

   A file is runs of `run key=value ...`, then `at N command args...` lines,
   then `end`. N is a sample at the start of a block. Commands:
     set FIELD VALUE [LAYER]      a number, true or false, or a word
     bars LAYER v,v,...           voices LAYER null | note/hz/vel/role+...
     spin a,b,c                   routes none | index/held/heldB/slot/amount/amountB/unipolar+...
     gate 0|1 VEL   gated 0|1     kick AMT   strike HZ VEL   reswing
     cycle T:...   wavetable B:...   figPath P:xy;at   (each, or none)   lfo I SHAPE RATE
     restart I   (an oscillator's phase to nought, as the worklet restarts one)
     input HZ AMP [DC]   (0 for none)  fx 0|1 (the effect instead of the block)

   With CORE=wasm in the environment the core is the page's `makeWasmCore`
   over the module the page carries, and with CORE=js the page's JavaScript
   core printed the same way: the samples, then only what the worklet reads
   of a core - the envelope, the crossings, the budget, the drawing - and the
   oscillators as it left them. The effect is not the compiled core's yet, so
   a run that asks for it prints that and nothing else.
   Usage: node generator_js.mjs <runs> */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { pageSpan, mulberry32 } from "./js_core.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
// SCOPE_PAGE names another copy of the page, for a check that alters one.
const page = fs.readFileSync(process.env.SCOPE_PAGE || path.join(here, "..", "..", "..", "web", "scope.html"), "utf8");

function definition(name) {
  let start = page.indexOf("\nfunction " + name + "(");
  if (start >= 0) return page.slice(start + 1, page.indexOf("\n}\n", start) + 2);
  start = page.indexOf("\nconst " + name + " = ");
  if (start < 0) throw new Error("no definition of " + name + " in scope.html");
  const line = page.slice(start + 1, page.indexOf("\n", start + 1));
  const close = line.endsWith("[") ? "\n];\n" : line.endsWith("{") ? "\n};\n" : ";\n";
  return page.slice(start + 1, page.indexOf(close, start) + close.length);
}

const listing = (() => {
  const start = page.indexOf("\nfunction generatorModuleSource(");
  return page.slice(start, page.indexOf("\n}\n", start));
})();
const bound = [...listing.matchAll(/bind\("(\w+)"/g)].map((m) => m[1]);
const solids = pageSpan("const MODELS = [", "/* --- what rate this machine actually runs at", ["TWO_PI"], ["MODELS"]);
const source = bound.map((name) => name === "MODELS" ? "const MODELS = " + JSON.stringify(solids.MODELS) + ";"
                                                     : definition(name)).join("\n")
  + "\nconst MODEL_BY_NAME = new Map(MODELS.map((m) => [m.name, m]));"
  + "\nreturn { makeGeneratorCore, makeWasmCore };";
// The page's sources that read the generator - the note envelope and the
// drawings' six - registered as the page registers them, over a tone source
// that is this core, gated as the run gates it.
const sourcesText = (() => {
  const env = page.indexOf('\nregisterSource({\n  id: "env.note"');
  const draw = page.indexOf("\nconst drawingNow = () => {");
  if (env < 0 || draw < 0) throw new Error("no envelope or drawing sources in scope.html");
  return page.slice(env + 1, page.indexOf("\n});\n", env) + 5) + page.slice(draw + 1, page.indexOf("\n}));\n", draw) + 5);
})();
const readSources = new Function("state", "genLane", "registerSource", sourcesText);
const SOURCE_IDS = ["env.note", "draw.swing", "draw.pendulum", "draw.turnX", "draw.turnY", "draw.turnZ", "draw.facing"];
// One seeded Math.random for everything the core reaches, as the worklet has one.
const MODE = process.env.CORE || "";
// WASM_FILE names a module to run instead of the page's: a mutant's, or one
// broken on purpose so a check can be seen to fail.
const wasmBytes = (() => {
  if (MODE !== "wasm") return null;
  if (process.env.WASM_FILE) return new Uint8Array(fs.readFileSync(process.env.WASM_FILE));
  const at = page.indexOf("/* WASM_CORE_BEGIN */\"");
  const text = page.slice(at + 22, page.indexOf("\"/* WASM_CORE_END */", at));
  return Uint8Array.from(Buffer.from(text, "base64"));
})();
const build = (seed) => {
  const made = new Function("Math", source)(Object.assign(Object.create(globalThis.Math), { random: mulberry32(seed) }));
  return MODE === "wasm" ? (rate, slots, lfos) => made.makeWasmCore(wasmBytes, rate, slots, lfos, seed) : made.makeGeneratorCore;
};

// In the worklet's two modes the tables and the path are typed arrays, as a
// page could hand them over: the JavaScript core indexes either alike, and
// the compiled one is given them through JSON, which has to write a typed
// array as the array it holds.
const numbers = (t) => (MODE ? Float64Array.from(t.split(","), Number) : t.split(",").map(Number));
const tables = (text) => {
  const [, most, body] = text.split(":");
  return { most: Number(most), levels: body.split(";").map(numbers) };
};
const value = (w) => (w === "true" ? true : w === "false" ? false : Number.isNaN(Number(w)) ? w : Number(w));
const show = (v) => v.map((x) => Number(x).toPrecision(17)).join(" ");

function run(head, events) {
  const p = Object.fromEntries(head.map((kv) => { const i = kv.indexOf("="); return [kv.slice(0, i), kv.slice(i + 1)]; }));
  const rate = Number(p.rate), samples = Number(p.samples), N = 128;
  const lfos = [0, 1].map((i) => {
    const [shape, hz] = (p["lfo" + i] || "sine,0.2").split(",");
    return { shape, rate: Number(hz), depth: 0.5, phase: 0, held: 0, value: 0, epoch: 0 };
  });
  const core = build(Number(p.seed))(rate, Number(p.slots), lfos);
  if (MODE && [...events.values()].some((list) => list.some((w) => w[0] === "fx" && w[1] === "1"))) return "fx";
  const out = [];
  const bufs = Array.from({ length: 6 }, () => new Float32Array(N));
  let input = null, inHz = 0, inAmp = 0, inDc = 0, fx = false, gated = false;
  for (let at = 0; at < samples; at += N) {
    for (const words of events.get(at) || []) {
      const [cmd, ...a] = words;
      if (cmd === "set") core.set(a[0], value(a[1]), a[2] === undefined ? undefined : Number(a[2]));
      else if (cmd === "bars") core.set("bars", a[1].split(",").map(Number), Number(a[0]));
      else if (cmd === "spin") core.set("spin", a[0].split(",").map(Number));
      else if (cmd === "voices") {
        core.set("voices", a[1] === "null" ? null : a[1] === "none" ? [] : a[1].split("+").map((n) => {
          const [note, freq, velocity, role] = n.split("/");
          return { note: Number(note), freq: Number(freq), velocity: Number(velocity), role };
        }), Number(a[0]));
      } else if (cmd === "routes") {
        core.setRoutes(a[0] === "none" ? [] : a[0].split("+").map((r) => {
          const [index, held, heldB, slot, amount, amountB, unipolar] = r.split("/").map(Number);
          return { index: index < 0 ? undefined : index, held, heldB, slot, amount, amountB, unipolar: unipolar === 1 };
        }));
      } else if (cmd === "gate") core.gate(a[0] === "1", Number(a[1]));
      else if (cmd === "gated") { core.setGated(a[0] === "1"); gated = a[0] === "1"; }
      else if (cmd === "kick") core.kick(Number(a[0]));
      else if (cmd === "strike") core.strike(Number(a[0]), Number(a[1]));
      else if (cmd === "reswing") core.reswing();
      else if (a[0] === "none" && ["cycle", "wavetable", "figPath"].includes(cmd)) core.set(cmd, null);
      else if (cmd === "cycle") core.set("cycle", tables(a[0]));
      else if (cmd === "wavetable") core.set("wavetable", a[0].slice(2).split("!").map((c) => tables("T:" + c)));
      else if (cmd === "figPath") {
        const [xy, t] = a[0].slice(2).split(";");
        core.set("figPath", { xy: numbers(xy), at: numbers(t) });
      } else if (cmd === "lfo") { lfos[Number(a[0])].shape = a[1]; lfos[Number(a[0])].rate = Number(a[2]); }
      else if (cmd === "restart") lfos[Number(a[0])].phase = 0;
      else if (cmd === "input") { inHz = Number(a[0]); inAmp = Number(a[1]); inDc = Number(a[2] || 0); }
      else if (cmd === "fx") fx = a[0] === "1";
      else throw new Error("unknown command " + cmd);
    }
    // The input as a worklet would hand it over: a block of float samples.
    if (inHz > 0) {
      input = new Float32Array(N);
      for (let k = 0; k < N; k++) input[k] = inDc + inAmp * Math.sin(2 * Math.PI * inHz * (at + k) / rate);
    } else input = null;
    const [l, r, hl, hr, bl, br] = bufs;
    if (fx) {
      const silent = new Float32Array(N), inL = input || silent;
      const inR = new Float32Array(N).map((_, k) => 0.5 * inL[(k + 7) % N]);
      core.effect(inL, inR, l, r, N);
      for (let k = 0; k < N; k++) out.push(l[k], r[k], 0, 0, 0, 0);
      continue;
    }
    core.setInput(input);
    core.block(l, r, N, hl, hr, bl, br);
    for (let k = 0; k < N; k++) out.push(l[k], r[k], hl[k], hr[k], bl[k], br[k]);
  }
  // And what the core says of itself at the end, as the worklet posts it.
  const b = core.budget, d = core.drawing;
  if (MODE) {
    out.push(core.envelope, core.crossings.x, core.crossings.y, b.units, b.asked[0], b.asked[1], b.unison[0], b.unison[1],
             b.askedFactor, b.factor, b.silenced, d.swing, d.pendulum, d.turn[0], d.turn[1], d.turn[2], d.facing);
    for (const l of lfos) out.push(l.phase, l.held, l.value);
    return show(out);
  }
  out.push(core.envelope, core.pitch, core.crossings.x, core.crossings.y, core.spinKick, core.swingLevel,
           b.units, b.asked[0], b.asked[1], b.unison[0], b.unison[1], b.askedFactor, b.factor, b.silenced,
           d.swing, d.pendulum, d.turn[0], d.turn[1], d.turn[2], d.facing, core.voices.length, core.voicesB.length);
  const sources = new Map();
  readSources({ source: { kind: "tone", gated, envelope: core.envelope, drawing: core.drawing } }, () => null,
              (entry) => sources.set(entry.id, entry));
  for (const id of SOURCE_IDS) out.push(sources.get(id).value());
  return show(out);
}

const lines = fs.readFileSync(process.argv[2], "utf8").split("\n");
const results = [];
for (let i = 0; i < lines.length; i++) {
  const words = lines[i].trim().split(/\s+/);
  if (words[0] !== "run") continue;
  const events = new Map();
  for (i++; i < lines.length && lines[i].trim() !== "end"; i++) {
    const w = lines[i].trim().split(/\s+/);
    if (w[0] !== "at") continue;
    const at = Number(w[1]);
    if (!events.has(at)) events.set(at, []);
    events.get(at).push(w.slice(2));
  }
  results.push(run(words.slice(1), events));
}
process.stdout.write(results.join("\n") + "\n");
