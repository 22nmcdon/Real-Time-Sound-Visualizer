/* The page's clock - the tempo, the bar, a tap, a MIDI clock and its Start,
   Stop and Continue, and the oscillators and the delay locked to the tempo -
   lifted out of web/scope.html by name and driven through the runs in a
   file, one result line per command, as clock_cpp prints them.

   The oscillators and the echo are the page's fields and nothing else; the
   score is a stand-in that says when the bar's anchor and Stop reach it. The
   clock is the run's: `performance.now()` reads what `at` last said.

   A file is runs of `run`, then one command a line, then `end`:
     at MS   tick   rt STATUS   start   stop   tap   tempo BPM   step
     sync LFO VALUE   echo SYNC MS   phase LFO P      (a SYNC of - is free)
   Usage: node clock_js.mjs <runs> */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

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

const LIFTED = [
  "LFO_SYNC", "syncBeats", "transport", "CLOCK_TIMEOUT_MS", "clockTick", "transportBeat", "transportRebase",
  "transportAnchor", "transportStart", "transportStop", "transportContinue", "transportSaid", "clockRestart",
  "clockTap", "setTempo", "clockStep", "midiRealtime",
];

const STUBS = `
let clock = 0;
const performance = { now: () => clock };
const log = [];
const el = {};
const lfos = [{ sync: "", rate: 0.2, phase: 0, epoch: 0 }, { sync: "", rate: 0.5, phase: 0, epoch: 0 }];
const echo = { sync: "", ms: 375 };
const DELAY_SYNC = ${definition("DELAY_SYNC").replace(/^const DELAY_SYNC = /, "").replace(/;\n$/, "")};
${definition("delayTimeMs")}
const genSet = (key, value) => { log.push(key + " " + value); };
// The score as the clock touches it: its anchor resets the column, and Stop lets go.
const score = { set last(v) { log.push("anchor"); }, get last() { return -1; }, steps: 0 };
function scoreStop() { log.push("stop"); }
`;

const source = STUBS + LIFTED.map(definition).join("\n") + `
return { transport, lfos, echo, log, clockTick, transportBeat, transportStart, transportStop, transportContinue,
         transportSaid, clockTap, setTempo, clockStep, midiRealtime, setClock: (ms) => { clock = ms; } };`;

const show = (v) => (v === undefined ? "u" : v === true ? "1" : v === false ? "0" : Number(v).toPrecision(17));

function run(commands) {
  const c = new Function(source)();
  let now = 0;
  const lines = [];
  for (const words of commands) {
    const [cmd, ...a] = words;
    c.log.length = 0;
    if (cmd === "at") { now = Number(a[0]); c.setClock(now); }
    else if (cmd === "tick") c.midiRealtime(0xf8, now);
    else if (cmd === "rt") c.midiRealtime(Number(a[0]), now);
    else if (cmd === "start") c.transportStart(now);
    else if (cmd === "stop") c.transportStop(now);
    else if (cmd === "tap") c.clockTap(now);
    else if (cmd === "tempo") c.setTempo(Number(a[0]), now);
    else if (cmd === "step") c.clockStep(now);
    else if (cmd === "sync") c.lfos[Number(a[0])].sync = a[1] === "-" ? "" : a[1];
    else if (cmd === "echo") { c.echo.sync = a[0] === "-" ? "" : a[0]; c.echo.ms = Number(a[1]); }
    else if (cmd === "phase") c.lfos[Number(a[0])].phase = Number(a[1]);
    else throw new Error("unknown command " + cmd);
    const t = c.transport;
    lines.push([cmd, ...c.log.flatMap((l) => ["::", l]), "|", "bpm", show(t.bpm), "set", show(t.set), "from", t.from,
                "running", show(t.running), "base", show(t.base), "at", show(t.baseAt), "ticking", show(t.onTicks),
                "ticks", t.ticks.length, "taps", t.taps.length, "beat", show(c.transportBeat(now)), "said", c.transportSaid(now),
                ...c.lfos.flatMap((l, i) => ["lfo" + i, show(l.rate), show(l.phase), l.epoch]),
                "sent", show(c.echo.sent)].join(" "));
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
