/* The compiled core's generator, from the module the page carries, through
   the bridge the page's worklets drove it by until stage 5's step 6 -
   `makeWasmCore`, which moved then to web/tests/compiled_core.js, where the
   web suites that render the core in a page use it - driven a block of 128 at
   a time into Float32Arrays, through the runs in a file, one result line per
   run. The samples, then what the worklets read back of a core: the
   envelope, the budget, the pitch, whether gated, the oscillators as it left
   them, Scan's read-heads, the envelope's stage and velocity.

   This was generator_js.mjs's CORE=wasm mode, held to the page's own
   JavaScript generator run the same way; that went with the page's engine,
   and the core's tests hold this to the native core (generator_cpp) on the
   samples and the readings the two both print.

   A file is runs of `run key=value ...`, then `at N command args...` lines,
   then `end`, as generator_cpp reads them.
   Usage: node generator_wasm.mjs <runs>   (WASM_FILE names another module) */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const page = fs.readFileSync(path.join(here, "..", "..", "..", "web", "scope.html"), "utf8");

function definition(name) {
  let start = page.indexOf("\nfunction " + name + "(");
  if (start >= 0) return page.slice(start + 1, page.indexOf("\n}\n", start) + 2);
  start = page.indexOf("\nconst " + name + " = ");
  if (start < 0) throw new Error("no definition of " + name + " in scope.html");
  const line = page.slice(start + 1, page.indexOf("\n", start + 1));
  const close = line.endsWith("[") ? "\n];\n" : line.endsWith("{") ? "\n};\n" : ";\n";
  return page.slice(start + 1, page.indexOf(close, start) + close.length);
}

// The page's settings store, which the bridge keeps its settings by, and the bridge itself.
const bridge = fs.readFileSync(path.join(here, "..", "..", "..", "web", "tests", "compiled_core.js"), "utf8");
const made = new Function(["DRAWBAR_DEFAULT", "generatorSettings"].map(definition).join("\n") + "\n" + definition("storeGeneratorSetting") + "\n" + bridge
                          + "\nreturn makeWasmCore;")();
const wasmBytes = process.env.WASM_FILE ? new Uint8Array(fs.readFileSync(process.env.WASM_FILE)) : (() => {
  const at = page.indexOf("/* WASM_CORE_BEGIN */\"");
  return Uint8Array.from(Buffer.from(page.slice(at + 22, page.indexOf("\"/* WASM_CORE_END */", at)), "base64"));
})();
const module = new WebAssembly.Module(wasmBytes);
const build = (seed) => (rate, slots, lfos) => made(module, rate, slots, lfos, seed);

// The tables are typed arrays, as a page could hand them over: the compiled
// core is given them through JSON, which has to write a typed array as the
// array it holds.
const numbers = (t) => Float64Array.from(t.split(","), Number);
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
  // At the Width the runs were recorded at, one, as generator_cpp sets it (the default is a half since 17 Nov).
  core.set("stereoWidth", 1); core.set("drawnWidth", 1);
  const out = [];
  const bufs = Array.from({ length: 6 }, () => new Float32Array(N));
  let input = null, inHz = 0, inAmp = 0, inDc = 0, fx = false, gated = false;
  for (let at = 0; at < samples; at += N) {
    for (const words of events.get(at) || []) {
      const [cmd, ...a] = words;
      if (cmd === "set") core.set(a[0], value(a[1]), a[2] === undefined ? undefined : Number(a[2]));
      else if (cmd === "bars") core.set("bars", a[1].split(",").map(Number), Number(a[0]));
      else if (cmd === "voices") {
        core.set("voices", a[1] === "null" ? null : a[1] === "none" ? [] : a[1].split("+").map((n) => {
          const [note, freq, velocity, role] = n.split("/");
          return { note: Number(note), freq: Number(freq), velocity: Number(velocity), role };
        }), Number(a[0]));
      } else if (cmd === "routes") {
        core.setRoutes(a[0] === "none" ? [] : a[0].split("+").map((r) => {
          const [index, held, heldB, slot, amount, amountB, unipolar] = r.split("/").map(Number);
          // The last number is the flags, as the wasm route has them: one unipolar, two the loop's.
          return { index: index < 0 ? undefined : index, held, heldB, slot, amount, amountB, unipolar: (unipolar & 1) === 1,
                   loop: (unipolar & 2) === 2 };
        }));
      } else if (cmd === "gate") core.gate(a[0] === "1", Number(a[1]));
      else if (cmd === "noteDown") core.noteDown();
      else if (cmd === "gated") { core.setGated(a[0] === "1"); gated = a[0] === "1"; }
      else if (cmd === "strike") core.strike(Number(a[0]), Number(a[1]));
      else if (cmd === "reswing") core.reswing();
      // Scan's table for a layer (P7a): `scan LAYER T:...` or `scan LAYER none`.
      else if (cmd === "scan") core.set("scanTable", a[1] === "none" ? null : tables(a[1]), Number(a[0]));
      else if (a[0] === "none" && ["cycle", "wavetable"].includes(cmd)) core.set(cmd, null);
      else if (cmd === "cycle") core.set("cycle", tables(a[0]));
      else if (cmd === "wavetable") core.set("wavetable", a[0].slice(2).split("!").map((c) => tables("T:" + c)));
      else if (cmd === "lfo") { lfos[Number(a[0])].shape = a[1]; lfos[Number(a[0])].rate = Number(a[2]); }
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
  const b = core.budget;
  out.push(core.envelope, b.units, b.asked[0], b.asked[1], b.unison[0], b.unison[1],
           b.askedFactor, b.factor, b.silenced, core.pitch, core.gated ? 1 : 0);
  for (const l of lfos) out.push(l.phase, l.held, l.value);
  out.push(core.scanHead[0], core.scanHead[1]);
  // And the envelope's stage and velocity (11 Nov), as the worklet posts them.
  out.push(core.envelopeStage, core.envelopeVelocity);
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
