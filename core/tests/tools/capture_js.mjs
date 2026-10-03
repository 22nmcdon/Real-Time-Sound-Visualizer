/* The page's capture - the window and the search span behind it, the AC
   coupling, the filter, the lag lane, mid and side, the turn and the trigger
   - lifted out of web/scope.html by name and driven through the runs in a
   file, one result line per command, as capture_cpp prints them.

   The source is the run's: a buffer of each channel built from sines,
   squares, noise and offsets at the run's rate, served the latest N samples
   at a time and zero-padded at the front when N is more than it holds, as
   the page's sources pad an over-ask. The view's settings are the run's.

   A file is runs of `run`, then one command a line, then `end`:
     rate R   cap N|inf   chans N   lanes 0|1   signal LENGTH
     add CH sine|square AMP HZ PHASE | add CH noise SEED AMP | add CH dc V
     tb I   pos P   posmod P   holdoff MS   level L   edge rising|falling   trig CH
     ac CH 0|1   achz HZ   fs CH DB   fsmod CH DB   on CH 0|1
     filter TYPE CUTOFF RES | filter off   fmod CUT RES
     lag MS   lagoff   lagmod MS   lagauto SECONDS|none   ms 0|1   rot TURNS   rotmod TURNS
     shaping 0|1   measure 0|1   cap
   Usage: node capture_js.mjs <runs> */
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

const STUBS = `
const state = { timebase: 4, position: 0.1, positionMod: 0, holdoffMs: 0, level: 0, edge: "rising", trigSource: 0,
                acHz: 5, channels: [], filter: { on: false, type: "lowpass", cutoff: 1000, res: 0 }, cutoffMod: 0, resMod: 0,
                lagOn: false, lagMs: 0, lagMod: 0, lagAuto: false, midSide: false, rotate: 0, rotateMod: 0,
                analyseAt: "post", measureAt: "pre", source: null, lagActual: 0, starved: 0 };
for (let i = 0; i < 6; i++) state.channels.push({ on: true, ac: false, fsDb: 0, fsMod: 0, offset: 0 });
`;
const LIFTED = ["RISING", "DIVS_X", "MIN_WINDOW", "HYSTERESIS", "SEARCH_SECONDS", "MAX_SEARCH_SECONDS", "LAG_MAX_MS",
  "LAG_MIN_SPAN_SECONDS", "lagLock", "Q_IN_DECIBELS", "CUTOFF_STEPS", "cutoffHz", "TIMEBASE", "FULL_SCALE_DB", "TWO_PI",
  "MAX_LANES", "BUTTERWORTH_Q_DB", "windowMs", "laneCount", "FS_TOP", "fullScaleDb", "gainOf", "biquadCoefficients",
  "filterInPlace", "filterNow", "AC_CORNER_MIN", "dcBlockerCoefficients", "turnOf", "rotateTurns", "rotatesSignal",
  "MID_SIDE_TURNS", "MID_SIDE_GAIN", "MID_SIDE_FLIP", "lagSeconds", "lagActive", "SHAPE_STRIDE", "strayBetween",
  "capture", "findTriggerIndex"];
const source = STUBS + LIFTED.map(definition).join("\n") + `
return { state, capture, setLock: (v) => { lagLock = v; } };`;

const show = (v) => Number(v).toPrecision(17);
function digest(list) {
  return list.map((b) => {
    let a = 0, q = 0;
    for (let i = 0; i < b.length; i++) { a += b[i] * (i + 1); q += b[i] * b[i]; }
    return [b.length, show(a), show(q), b.length ? show(b[0]) : "-", b.length ? show(b[b.length - 1]) : "-"].join(" ");
  }).join(" / ");
}

function run(commands) {
  const s = new Function(source)();
  const st = s.state;
  let rate = 48000, capacity = Infinity, chans = 2, lanes = false, length = 0;
  let buffers = [];
  const src = () => ({
    sampleRate: rate, capacity, channels: chans, lanes: lanes ? [{}, {}] : undefined,
    getLatestWindow: (n) => buffers.slice(0, chans).map((b) => {
      const out = new Float32Array(n);
      const take = Math.min(n, b.length);
      out.set(b.subarray(b.length - take), n - take);
      return out;
    }),
  });
  const lines = [];
  for (const words of commands) {
    const [cmd, ...a] = words;
    let extra = "";
    const ch = Number(a[0]);
    if (cmd === "rate") rate = Number(a[0]);
    else if (cmd === "cap") {
      if (a.length) capacity = a[0] === "inf" ? Infinity : Number(a[0]);
      else {
        st.source = src();
        const f = s.capture();
        extra = [" trig", f.triggered ? 1 : 0, "level", show(f.levelAt), "asked", f.asked, "len", f.length, "pre", f.pre,
                 "turned", f.turned ? 1 : 0, "shaped", show(f.shaped.ac), show(f.shaped.filter), "lag", show(st.lagActual),
                 "starved", st.starved, "measured", f.measured === f.channels ? "drawn" : "signal",
                 "| ch", digest(f.channels), "| sig", digest(f.signal)].join(" ");
      }
    }
    else if (cmd === "chans") chans = Number(a[0]);
    else if (cmd === "lanes") lanes = a[0] === "1";
    else if (cmd === "signal") { length = Number(a[0]); buffers = []; for (let i = 0; i < 6; i++) buffers.push(new Float32Array(length)); }
    else if (cmd === "add") {
      const b = buffers[ch], kind = a[1];
      if (kind === "sine" || kind === "square") {
        const amp = Number(a[2]), hz = Number(a[3]), phase = Number(a[4]);
        for (let i = 0; i < length; i++) {
          const v = Math.sin(2 * Math.PI * hz * i / rate + phase);
          b[i] += amp * (kind === "sine" ? v : v >= 0 ? 1 : -1);
        }
      } else if (kind === "noise") {
        const next = mulberry32(Number(a[2])), amp = Number(a[3]);
        for (let i = 0; i < length; i++) b[i] += (next() * 2 - 1) * amp;
      } else for (let i = 0; i < length; i++) b[i] += Number(a[2]);
    }
    else if (cmd === "tb") st.timebase = Number(a[0]);
    else if (cmd === "pos") st.position = Number(a[0]);
    else if (cmd === "posmod") st.positionMod = Number(a[0]);
    else if (cmd === "holdoff") st.holdoffMs = Number(a[0]);
    else if (cmd === "level") st.level = Number(a[0]);
    else if (cmd === "edge") st.edge = a[0];
    else if (cmd === "trig") st.trigSource = Number(a[0]);
    else if (cmd === "ac") st.channels[ch].ac = a[1] === "1";
    else if (cmd === "achz") st.acHz = Number(a[0]);
    else if (cmd === "fs") st.channels[ch].fsDb = Number(a[1]);
    else if (cmd === "fsmod") st.channels[ch].fsMod = Number(a[1]);
    else if (cmd === "on") st.channels[ch].on = a[1] === "1";
    else if (cmd === "filter") {
      if (a[0] === "off") st.filter.on = false;
      else Object.assign(st.filter, { on: true, type: a[0], cutoff: Number(a[1]), res: Number(a[2]) });
    } else if (cmd === "fmod") { st.cutoffMod = Number(a[0]); st.resMod = Number(a[1]); }
    else if (cmd === "lag") { st.lagOn = true; st.lagMs = Number(a[0]); }
    else if (cmd === "lagoff") st.lagOn = false;
    else if (cmd === "lagmod") st.lagMod = Number(a[0]);
    else if (cmd === "lagauto") { st.lagAuto = a[0] !== "none"; s.setLock(a[0] === "none" ? null : Number(a[0])); }
    else if (cmd === "ms") st.midSide = a[0] === "1";
    else if (cmd === "rot") st.rotate = Number(a[0]);
    else if (cmd === "rotmod") st.rotateMod = Number(a[0]);
    else if (cmd === "shaping") st.analyseAt = a[0] === "1" ? "post" : "pre";
    else if (cmd === "measure") st.measureAt = a[0] === "1" ? "post" : "pre";
    else throw new Error("unknown command " + cmd);
    lines.push(cmd + extra);
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
