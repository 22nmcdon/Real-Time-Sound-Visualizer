/* The page's score and MIDI out - the playhead on the bar, a column of the
   grid read as a chord in the key, struck and sent; the out's rate limit,
   its sounding notes and its panic; the crossings' notes and the pluck's,
   each ended after its time - lifted out of web/scope.html by name and driven
   through the runs in a file, one result line per command, as score_cpp
   prints them.

   The grid is the run's (`grid`, `cell`); the generator's strike and the
   port write down what they are given. The clock is the run's:
   `performance.now()` reads what `at` last said.

   A file is runs of `run`, then one command a line, then `end`:
     at MS   tempo BPM   start   stop   tick   midistart   frame   running 0|1   key ROOT SCALE
     score on|off STEP VOICES LOW OCTAVES   grid SEED FILL   cell ROW COL VALUE
     port 0|1 CHANNEL   panic   pluck VELOCITY   pluckNote NOTE
     cross 0|1 NOTEX NOTEY   counts X Y
   Usage: node score_js.mjs <runs> */
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
// A statement the page runs inside its frame, taken as it stands.
function statement(text) {
  if (page.indexOf(text) < 0) throw new Error("no statement " + text.slice(0, 60));
  return text + "\n";
}

const LIFTED = [
  "SCALES", "keyMask", "midiHz", "transport", "CLOCK_TIMEOUT_MS", "clockTick", "transportBeat", "transportRebase", "transportAnchor",
  "transportStart", "transportStop", "clockRestart", "setTempo", "PHOSPHOR_N", "SCORE_STEPS", "SCORE_FLOOR", "score",
  "scorePitches", "scoreColumn", "scoreTick", "scoreStop", "MIDI_OUT_RATE", "midiOut", "midiOutSend", "midiOutNote",
  "midiOutOff", "midiOutPanic", "crossSeen", "crossOffs", "crossOut", "crossStepPanel", "pluck", "pluckFire",
];

const STUBS = `
let clock = 0;
const performance = { now: () => clock };
const log = [];
const show = (v) => Number(v).toPrecision(17);
const lfos = [];
const noop = () => {};
// Only the readout the crossings write; the clock's panel is not there to refresh.
const el = { crossCount: { textContent: "" } };
const state = { running: true, keyRoot: 0, keyScale: "chromatic", source: { kind: "tone", crossings: { x: 0, y: 0 } } };
const cross = { on: false, noteX: 60, noteY: 67 };
const phosphor = { grid: new Float32Array(64 * 64) };
function genStrike(notes) { for (const [hz, velocity] of notes) log.push("strike " + show(hz) + " " + show(velocity)); }
const port = { send: (bytes) => log.push("send " + bytes.join(",")) };
`;

const source = STUBS + LIFTED.map(definition).join("\n") + `
function pluckOffs() {
` + statement(`  for (let k = pluck.offs.length - 1; k >= 0; k--) {
    if (performance.now() >= pluck.offs[k][1]) { midiOutOff(pluck.offs[k][0]); pluck.offs.splice(k, 1); }
  }`) + `}
return { log, state, cross, phosphor, score, midiOut, crossSeen, crossOffs, pluck, port, transport, clockTick,
         transportBeat, transportStart, transportStop, setTempo, scoreTick, scoreStop, crossStepPanel, pluckFire,
         pluckOffs, midiOutPanic, setClock: (ms) => { clock = ms; } };`;

const show = (v) => Number(v).toPrecision(17);

function run(commands) {
  const s = new Function(source)();
  let now = 0;
  const lines = [];
  for (const words of commands) {
    const [cmd, ...a] = words;
    s.log.length = 0;
    if (cmd === "at") { now = Number(a[0]); s.setClock(now); }
    else if (cmd === "tempo") s.setTempo(Number(a[0]), now);
    else if (cmd === "start") s.transportStart(now);
    else if (cmd === "stop") s.transportStop(now);
    else if (cmd === "tick") s.clockTick(now);
    else if (cmd === "midistart") s.transportStart(now, true);
    else if (cmd === "frame") {
      // In the order the page's frame has them.
      s.crossStepPanel(now);
      s.scoreTick(now);
      s.pluckOffs();
    } else if (cmd === "running") s.state.running = a[0] === "1";
    else if (cmd === "key") { s.state.keyRoot = Number(a[0]); s.state.keyScale = a[1]; }
    else if (cmd === "score") {
      // The panel's handlers, each as the page has it.
      s.score.step = a[1];
      s.score.voices = Number(a[2]) || 1;
      s.score.low = Number(a[3]) || 48;
      s.score.octaves = Number(a[4]) || 3;
      s.score.on = a[0] === "on";
      if (!s.score.on) s.scoreStop();
    } else if (cmd === "grid") {
      const next = mulberry32(Number(a[0])), fill = Number(a[1]);
      for (let i = 0; i < 64 * 64; i++) s.phosphor.grid[i] = next() < fill ? next() : 0;
    } else if (cmd === "cell") s.phosphor.grid[Number(a[0]) * 64 + Number(a[1])] = Number(a[2]);
    else if (cmd === "port") {
      // midiOutChoose: everything off on the old, then the new.
      s.midiOutPanic();
      s.midiOut.port = a[0] === "1" ? s.port : null;
      s.midiOut.channel = Number(a[1]) || 0;
    } else if (cmd === "panic") s.midiOutPanic();
    else if (cmd === "pluck") s.pluckFire(Number(a[0]));
    else if (cmd === "pluckNote") s.pluck.note = Number(a[0]);
    else if (cmd === "cross") { s.cross.on = a[0] === "1"; s.cross.noteX = Number(a[1]); s.cross.noteY = Number(a[2]); }
    else if (cmd === "counts") s.state.source.crossings = { x: Number(a[0]), y: Number(a[1]) };
    else throw new Error("unknown command " + cmd);
    const sc = s.score, m = s.midiOut;
    lines.push([cmd, ...s.log.flatMap((l) => ["::", l]), "|", "col", sc.col, "last", sc.last, "steps", sc.steps,
                "notes", sc.notes.map(([n, v]) => n + "/" + show(v)).join("+") || "-",
                "sounding", [...m.sounding.keys()].join("+") || "-", "recent", m.times.length, "dropped", m.dropped,
                "seen", s.crossSeen.x, s.crossSeen.y, "crossoffs", s.crossOffs.map(([n, t]) => n + "/" + show(t)).join("+") || "-",
                "pluckoffs", s.pluck.offs.map(([n, t]) => n + "/" + show(t)).join("+") || "-",
                "beat", show(s.transportBeat(now))].join(" "));
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
