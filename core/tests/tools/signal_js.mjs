/* The page's level - the envelope follower over the screen's signal lane
   that is the source `env.live` - lifted out of web/scope.html by name and
   driven through the runs in a file, one result line per command, as
   signal_cpp prints them. K1's threshold, which watched it, was here too and
   went in P5.

   The lane is the run's (`sine`, `noise`). The clock is the run's:
   `performance.now()` reads what `at` last said.

   A file is runs of `run`, then one command a line, then `end`:
     at MS   sine AMP CYCLES LENGTH   noise SEED AMP LENGTH   frame ELAPSED
   Usage: node signal_js.mjs <runs> */
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
// A registration as the page makes it, from its first line to its close.
function registration(first) {
  const start = page.indexOf("\nregisterSource({\n" + first);
  if (start < 0) throw new Error("no registration " + first);
  return page.slice(start + 1, page.indexOf("\n});\n", start) + 5);
}

const STUBS = `
let clock = 0;
const performance = { now: () => clock };
const MOD_SOURCES = new Map();
function registerSource(entry) { MOD_SOURCES.set(entry.id, entry); return entry; }
const state = { trigSource: 0 };
let testValue = 0;
`;

const source = STUBS + ["ENV_ATTACK", "ENV_FULL", "envLive", "updateEnvelope"].map(definition).join("\n")
  + registration('  id: "env.live"') + `
return { MOD_SOURCES, updateEnvelope, envLive: () => envLive, setClock: (ms) => { clock = ms; } };`;

const show = (v) => Number(v).toPrecision(17);

function run(commands) {
  const s = new Function(source)();
  let now = 0, lane = new Float32Array(0);
  const lines = [];
  for (const words of commands) {
    const [cmd, ...a] = words;
    if (cmd === "at") { now = Number(a[0]); s.setClock(now); }
    else if (cmd === "sine") {
      const amp = Number(a[0]), cycles = Number(a[1]), n = Number(a[2]);
      lane = new Float32Array(n);
      for (let i = 0; i < n; i++) lane[i] = amp * Math.sin(2 * Math.PI * cycles * i / n);
    } else if (cmd === "noise") {
      const next = mulberry32(Number(a[0])), amp = Number(a[1]), n = Number(a[2]);
      lane = new Float32Array(n);
      for (let i = 0; i < n; i++) lane[i] = (next() * 2 - 1) * amp;
    } else if (cmd === "frame") s.updateEnvelope({ signal: [lane] }, Number(a[0]));
    else throw new Error("unknown command " + cmd);
    const live = s.MOD_SOURCES.get("env.live");
    lines.push([cmd, "| env", show(s.envLive()), "level", show(live.value())].join(" "));
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
