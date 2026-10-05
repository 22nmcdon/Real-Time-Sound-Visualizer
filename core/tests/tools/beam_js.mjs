/* The page's beam walk - what drawMain and drawXY lay into the phosphor grid
   each frame, the beam's shading included - lifted out of web/scope.html by
   name and driven through the runs in a file, one result line per command, as
   beam_cpp prints them.

   The page's own renderer runs, on a canvas that draws nothing: the frame
   comes from the page's own capture of a source the run builds, exactly as
   capture_js.mjs builds it, and what is compared is the grid, the beam's path
   by its roundness, the graticule and the beam's anchors.

   A file is runs of `run`, then one command a line, then `end`. Every command
   capture_js.mjs takes but `cap`, and:
     canvas W H   resize   name WIDTH   display yt|xy   persist P   zoom Z
     stack 0|1   pair X Y   figures X,Y;X,Y|none   beam LEVEL   beamxy 0|1
     beamyt 0|1   offset CH V   forget   draw ELAPSED
   Usage: node beam_js.mjs <runs> */
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
                analyseAt: "post", measureAt: "pre", source: null, lagActual: 0, starved: 0,
                display: "yt", persistence: 0, zoom: 1, stack: true, xyPair: [0, 1], beam: "moderate", beamXY: true,
                beamYT: false, reference: null, cursors: false };
for (let i = 0; i < 2; i++) state.channels.push({ on: true, ac: false, fsDb: 0, fsMod: 0, offset: 0 });
const ink = new Proxy({}, { get: () => "#808080" });
class Path2D { moveTo() {} lineTo() {} }
let nameWidth = 0;
const ctx = new Proxy({}, {
  get: (t, k) => k === "measureText" ? () => ({ width: nameWidth }) : k in t ? t[k] : () => {},
  set: (t, k, v) => { t[k] = v; return true; },
});
let canvasW = 800, canvasH = 500, resized = false;
const fitCanvas = () => { const r = resized; resized = false; return { ctx, w: canvasW, h: canvasH, resized: r }; };
const el = { trace: {} };
const getComputedStyle = () => ({ fontFamily: "serif" });
const document = { body: {} };
const performance = { now: () => 0 };
const laneName = (i) => "lane " + i;
const drawCursors = () => {};
const drawSpectrogram = () => { throw new Error("the spectrogram is not walked"); };
const cross = { on: false };
const crossSeen = {};
`;
const LIFTED = ["RISING", "DIVS_X", "MIN_WINDOW", "HYSTERESIS", "SEARCH_SECONDS", "MAX_SEARCH_SECONDS", "LAG_MAX_MS",
  "LAG_MIN_SPAN_SECONDS", "lagLock", "Q_IN_DECIBELS", "CUTOFF_STEPS", "cutoffHz", "TIMEBASE", "FULL_SCALE_DB", "TWO_PI",
  "MAX_LANES", "BUTTERWORTH_Q_DB", "windowMs", "laneCount", "FS_TOP", "fullScaleDb", "gainOf", "biquadCoefficients",
  "filterInPlace", "filterNow", "AC_CORNER_MIN", "dcBlockerCoefficients", "turnOf", "rotateTurns", "rotatesSignal",
  "MID_SIDE_TURNS", "MID_SIDE_GAIN", "MID_SIDE_FLIP", "lagSeconds", "lagActive", "SHAPE_STRIDE", "strayBetween",
  "capture", "findTriggerIndex",
  "PAD", "plot", "wipeScreen", "clearOrFade", "stacked", "sourceFigures", "drawMain", "drawXY",
  "PHOSPHOR_N", "phosphor", "makeMoments", "phosphorFade", "phosphorFadeInto", "phosphorSegment", "phosphorSegmentInto",
  "phosphorDeposit", "phosphorReadGrid", "METER_COARSE", "METER_EVERY", "METER_DEPTH", "METER_RECENT", "METER_WINDOW",
  "makePictureMeter", "PICTURE_KEYS", "makePictureEngine", "const pictureEngine = makePictureEngine();",
  "BEAM_K", "BEAM_EPS2", "BEAM_TAU", "BEAM_LEVELS", "beamRamps", "hexToRgb", "buildBeamRamps", "beamStep",
  "BEAM_ANCHOR_Q", "BEAM_HIST_LO", "beamHist", "beamRefs", "beamAnchor", "BEAM_MAX", "beamX", "beamY", "beamL2",
  "beamStepOf", "strokeBeam", "beamColours"];
const source = STUBS + LIFTED.map((name) => (name.startsWith("const ") ? name + "\n" : definition(name))).join("\n") + `
buildBeamRamps();
return { state, capture, laneCount, drawMain, phosphor, engine: pictureEngine, beamRefs, setLock: (v) => { lagLock = v; },
         plot: () => plot, canvas: (w, h) => { canvasW = w; canvasH = h; }, resize: () => { resized = true; },
         name: (w) => { nameWidth = w; } };`;

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
  let figures = null;
  const src = () => ({
    sampleRate: rate, capacity, channels: chans, lanes: lanes ? [{}, {}] : undefined,
    figures: () => figures,
    getLatestWindow: (n) => buffers.slice(0, chans).map((b) => {
      const out = new Float32Array(n);
      const take = Math.min(n, b.length);
      out.set(b.subarray(b.length - take), n - take);
      return out;
    }),
  });
  const chan = (c) => {
    while (st.channels.length <= c) st.channels.push({ on: true, ac: false, fsDb: 0, fsMod: 0, offset: 0 });
    return st.channels[c];
  };
  const lines = [];
  for (const words of commands) {
    const [cmd, ...a] = words;
    let extra = "";
    const ch = Number(a[0]);
    if (["ac", "fs", "fsmod", "on", "offset"].includes(cmd)) chan(ch);
    if (cmd === "rate") rate = Number(a[0]);
    else if (cmd === "cap") capacity = a[0] === "inf" ? Infinity : Number(a[0]);
    else if (cmd === "draw") {
      st.source = src();
      // The lanes the page keeps settings for, fitted as fitChannels fits them.
      const n = s.laneCount();
      while (st.channels.length < n) st.channels.push({ on: true, ac: false, fsDb: 0, fsMod: 0, offset: 0 });
      st.channels.length = Math.max(2, n);
      s.drawMain(s.capture(), Number(a[0]));
      const g = s.phosphor.grid, p = s.plot();
      let a1 = 0, a2 = 0;
      for (let i = 0; i < g.length; i++) { a1 += g[i] * (i + 1); a2 += g[i] * g[i]; }
      const refs = [...s.beamRefs.entries()].sort((x, y) => (x[0] < y[0] ? -1 : 1)).map(([k, v]) => k + " " + show(v));
      extra = [" | grid", show(a1), show(a2), "round", show(s.engine.roundness), "frames", s.phosphor.frames,
               "plot", show(p.x), show(p.y), show(p.w), show(p.h), "refs", ...refs].join(" ");
    }
    else if (cmd === "canvas") s.canvas(Number(a[0]), Number(a[1]));
    else if (cmd === "resize") s.resize();
    else if (cmd === "name") s.name(Number(a[0]));
    else if (cmd === "display") st.display = a[0];
    else if (cmd === "persist") st.persistence = Number(a[0]);
    else if (cmd === "zoom") st.zoom = Number(a[0]);
    else if (cmd === "stack") st.stack = a[0] === "1";
    else if (cmd === "pair") st.xyPair = [Number(a[0]), Number(a[1])];
    else if (cmd === "figures") figures = a[0] === "none" ? null : a[0].split(";").map((f) => f.split(",").map(Number));
    else if (cmd === "beam") st.beam = a[0];
    else if (cmd === "beamxy") st.beamXY = a[0] === "1";
    else if (cmd === "beamyt") st.beamYT = a[0] === "1";
    else if (cmd === "offset") st.channels[ch].offset = Number(a[1]);
    else if (cmd === "forget") s.beamRefs.clear();
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
