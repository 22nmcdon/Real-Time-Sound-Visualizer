/* The page's hearing - the window analysed once a frame into a pitch, a
   brightness, four bands, a width, a flux and an onset, and the sources that
   carry them - lifted out of web/scope.html by name and driven through the
   runs in a file, one result line per command, as hearing_cpp prints them.

   The sound is the run's: sines and noise summed into each lane, a window of
   `len` samples ending at the run's own sample clock, which `frame` moves on
   by its elapsed time before the window is read. `gap` silences one half of
   the window, as a note starting or stopping inside it does, and `gap early`
   the first three eighths, so the newer half has four times the older's energy. The keyboard is
   the run's (`held`), and so is whether what is heard is the generator.

   A file is runs of `run`, then one command a line, then `end`:
     at MS   rate HZ   len N   lanes 1|2   tone LANE HZ AMP PHASE   noise LANE SEED AMP   clear
     gap none|first|second|early   frame ELAPSED   held NOTE... | held -   running 0|1   gen 0|1
     trig LANE   xy A B
   Usage: node hearing_js.mjs <runs> */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { mulberry32 } from "./js_core.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const page = fs.readFileSync(path.join(here, "..", "..", "..", "web", "scope.html"), "utf8");

function definition(name) {
  let start = page.indexOf("\nfunction " + name + "(");
  if (start >= 0) return page.slice(start + 1, page.indexOf("\n}\n", start) + 2);
  start = page.indexOf("\nconst " + name + " = ");
  if (start < 0) start = page.indexOf("\nlet " + name + " = ");
  if (start < 0) throw new Error("no definition of " + name + " in scope.html");
  const line = page.slice(start + 1, page.indexOf("\n", start + 1));
  if (/;\s*(\/\/.*)?$/.test(line)) return line + "\n";
  const close = line.endsWith("[") ? "\n];\n" : line.endsWith("{") ? "\n};\n" : ";\n";
  return page.slice(start + 1, page.indexOf(close, start) + close.length);
}
// A statement the page runs at load, from its first line to its close.
function block(first, close) {
  const start = page.indexOf("\n" + first);
  if (start < 0) throw new Error("no block " + first);
  return page.slice(start + 1, page.indexOf(close, start) + close.length);
}

const LIFTED = [
  "ENV_ATTACK", "ENV_FULL", "PHOTO_REACH", "PHOTO_START", "BANDS", "midiHz", "midiPitch", "midiPitchHz",
  "HEAR_N", "HEAR_SLEW", "HEAR_FLOOR", "PITCH_REF", "hearing", "hearsGenerator", "hearingFollow", "hearingSlew", "hearingStep",
  "PITCH_MAX_WINDOW", "PITCH_DIP", "PITCH_TRUST", "pitchPass", "estimatePeriod", "fft", "correlation",
  "ONSET_ON", "onset", "onsetStep", "HEARING_SOURCES", "hearingBands",
];

const STUBS = `
let clock = 0;
const performance = { now: () => clock };
const MOD_SOURCES = new Map();
function registerSource(entry) { MOD_SOURCES.set(entry.id, entry); return entry; }
let touched = 0;
const touchRoutings = () => { touched++; };
const midi = { notes: [] };
const state = { source: null, running: true, trigSource: 0, xyPair: [0, 1] };
`;

const source = STUBS + LIFTED.map(definition).join("\n")
  + block("HEARING_SOURCES.forEach((entry, i) => {", "\n});\n")
  + block('registerSource({\n  id: "hear.onset"', "\n});\n") + `
return { MOD_SOURCES, hearing, onset, hearingStep, state, midi, touched: () => touched, setClock: (ms) => { clock = ms; } };`;

const show = (v) => (v === null ? "null" : Number(v).toPrecision(17));
const IDS = ["hear.pitch", "hear.bright", "hear.band1", "hear.band2", "hear.band3", "hear.band4", "hear.width", "hear.flux", "hear.onset"];

function run(commands) {
  const s = new Function(source)();
  let rate = 48000, len = 4096, lanes = 2, t0 = 0, gap = "none", gen = true;
  let parts = [];
  const window = () => {
    const out = [];
    for (let l = 0; l < lanes; l++) {
      const lane = new Float32Array(len);
      for (let i = 0; i < len; i++) {
        const at = t0 - len + i;
        let v = 0;
        for (const p of parts) {
          if (p.lane !== l) continue;
          if (p.kind === "tone") v += p.amp * Math.sin(2 * Math.PI * p.hz * at / rate + p.phase);
          else v += p.amp * (mulberry32(p.seed * 100003 + at)() * 2 - 1);
        }
        if ((gap === "first" && i < len / 2) || (gap === "second" && i >= len / 2) || (gap === "early" && i < 3 * len / 8)) v = 0;
        lane[i] = v;
      }
      out.push(lane);
    }
    return out;
  };
  const place = () => {
    const w = window();
    s.state.source = gen ? { kind: "tone", sampleRate: rate, getLatestWindow: () => w }
                         : { kind: "file", sampleRate: rate, lanes: w.map(() => ({})), getLatestWindow: () => w };
  };
  const lines = [];
  for (const words of commands) {
    const [cmd, ...a] = words;
    if (cmd === "at") s.setClock(Number(a[0]));
    else if (cmd === "rate") rate = Number(a[0]);
    else if (cmd === "len") len = Number(a[0]);
    else if (cmd === "lanes") lanes = Number(a[0]);
    else if (cmd === "tone") parts.push({ kind: "tone", lane: Number(a[0]), hz: Number(a[1]), amp: Number(a[2]), phase: Number(a[3]) });
    else if (cmd === "noise") parts.push({ kind: "noise", lane: Number(a[0]), seed: Number(a[1]), amp: Number(a[2]) });
    else if (cmd === "clear") parts = [];
    else if (cmd === "gap") gap = a[0];
    else if (cmd === "frame") {
      const elapsed = Number(a[0]);
      t0 += Math.round(elapsed * rate / 1000);
      place();
      s.hearingStep(elapsed);
    } else if (cmd === "held") s.midi.notes = a[0] === "-" ? [] : a.map((n) => ({ note: Number(n), velocity: 0.8 }));
    else if (cmd === "running") s.state.running = a[0] === "1";
    else if (cmd === "gen") gen = a[0] === "1";
    else if (cmd === "trig") s.state.trigSource = Number(a[0]);
    else if (cmd === "xy") s.state.xyPair = [Number(a[0]), Number(a[1])];
    else throw new Error("unknown command " + cmd);
    const h = s.hearing, o = s.onset;
    const src = IDS.map((id) => { const e = s.MOD_SOURCES.get(id); return (e.fromPicture ? 1 : 0) + "/" + show(e.reach === undefined ? 0 : e.reach); });
    lines.push([cmd, "| pitch", show(h.pitch), "bright", show(h.bright), "bands", ...h.bands.map(show), "width", show(h.width),
                "flux", show(h.flux), "raw", show(h.fluxRaw), "frame", h.frame, "want", show(h.pitchWant),
                "onset", o.count, show(o.last), o.armed ? 1 : 0, show(s.MOD_SOURCES.get("hear.onset").value()),
                "touched", s.touched(), "sources", ...src].join(" "));
  }
  return lines.join("\n");
}

const text = fs.readFileSync(process.argv[2], "utf8").split("\n");
const out = [];
for (let i = 0; i < text.length; i++) {
  if (text[i].trim().split(/\s+/)[0] !== "run") continue;
  const commands = [];
  for (i++; i < text.length && text[i].trim() !== "end"; i++) {
    const w = text[i].trim().split(/\s+/);
    if (w[0]) commands.push(w);
  }
  out.push(run(commands));
}
process.stdout.write(out.join("\n") + "\n");
