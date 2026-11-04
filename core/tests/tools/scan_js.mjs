/* The page's own Scan reading (P7a) - `scanStep` and everything it calls,
   `scanFreeze` and the `scan` object - lifted out of web/scope.html and
   driven frame by frame over grids the runs give, as scan_cpp drives
   scope::ScanReader. The page reads its live phosphor once a screen frame,
   which no two runs could repeat, so both are fed the same grids instead;
   what the page does with a grid is what is held.

   A file is runs: `run soft=S`, then lines, then `end`. Lines:
     grid NAME v,v,...                 a 64 by 64 grid, row by row
     frame elapsed=MS now=MS spect=0|1 count=1|2 live=0|1 d0=D d1=D
           [r0=A|B|both r1=B|A|both]    (P7b: what each layer's Scan reads; its own if left out)
           hs=H gs=NAME                 (live=0: the stage's hold, the one screen)
           h0=H h1=H g0=NAME g1=NAME    (live=1: each picture's)
     strike note=N vel=V amount=A split=0|1 point=N plot=X,Y,W,H, then a
           frame's words but elapsed and now   (P7b: a note's strike)
     freeze now=MS                     a setup landing
   One output line per frame: for each thing the page did, in order, a code
   and its numbers - 1 layer hold (the hold sent), 2 layer most levels...
   (a table sent: its ceiling, then every level's samples) - and then each
   picture's path, 3 picture cx cy r, or 4 picture for none. One line per
   strike: each segment laid, in order, 5 picture x0 y0 x1 y1 level, the
   picture -1 for the shown screen; or 6 for nothing laid.
   Usage: node scan_js.mjs <runs> */
import fs from "node:fs";
import { pageScopeWith } from "./js_core.mjs";

const prelude = `
let __now = 0, __spect = false, __count = 1, __depth = [0, 0], __sent = [], __laid = [];
// The strike's graticule and the keyboard's layers (P7b); a segment laid is written down.
const plot = { x: 0, y: 0, w: 1, h: 1 };
const PHOSPHOR_N = 64;
const midi = { layers: { mode: "layer", point: 60 } };
const __lay = (p) => (pl, x0, y0, x1, y1, level) => { __laid.push([p, x0, y0, x1, y1, level]); };
const performance = { now: () => __now };
const state = { get display() { return __spect ? "spect" : "xy"; }, source: { kind: "tone" } };
const layerPictures = { live: false, engines: [{ cells: null, segment: __lay(0) }, { cells: null, segment: __lay(1) }],
                        stages: [{ hold: 1 }, { hold: 1 }] };
const pictureStage = { hold: 1 };
const pictureEngine = { cells: null, segment: __lay(-1) };
const genSettings = (l) => ({ scan: __depth[l || 0] });
const genSet = (field, value, l) => { __sent.push([field, value, l || 0]); };
const layersOn = () => __count === 2;
const __put = (o) => { __now = o.now; __spect = o.spect; __count = o.count; __depth = o.depth; };
const __take = () => { const s = __sent; __sent = []; return s; };
const __taken = () => { const s = __laid; __laid = []; return s; };
`;
const names = ["SCAN_SOFT_DEFAULT", "SCAN_POINTS", "SCAN_HARMONICS", "SCAN_TABLE", "SCAN_DARK", "SCAN_FOLLOW",
               "SCAN_LEAST", "scanGeometry", "scanFollow", "scanBlur", "scanBilinear", "scanRead", "scanCosines",
               "scanCosine", "scanTables", "SCAN_FREEZE_MS", "STRIKE_DEFAULT", "scan", "SCAN_READS", "scanReadsOf",
               "scanPicturesOf", "scanFreeze", "scanStep", "STRIKE_ARC", "STRIKE_SEGMENTS", "scanStrike"];
const pageWith = () => pageScopeWith(prelude, names, ["layerPictures", "pictureStage", "pictureEngine", "plot", "midi",
                                                      "__put", "__take", "__taken"]);

const show = (v) => v.map((x) => Number(x).toPrecision(17)).join(" ");
const kv = (words) => Object.fromEntries(words.map((w) => { const i = w.indexOf("="); return [w.slice(0, i), w.slice(i + 1)]; }));

const lines = fs.readFileSync(process.argv[2], "utf8").split("\n");
const grids = new Map();
const out = [];
let p = null;
for (const raw of lines) {
  const words = raw.trim().split(/\s+/);
  if (!words[0]) continue;
  if (words[0] === "grid") { grids.set(words[1], Float32Array.from(words[2].split(","), Number)); continue; }
  if (words[0] === "run") { p = pageWith(); p.scan.soft = Number(kv(words.slice(1)).soft); continue; }
  if (words[0] === "end") { p = null; continue; }
  const o = kv(words.slice(1));
  if (words[0] === "freeze") { p.__put({ now: Number(o.now), spect: false, count: 1, depth: [0, 0] }); p.scanFreeze(); continue; }
  if (words[0] !== "frame" && words[0] !== "strike") throw new Error("unknown line " + words[0]);
  const live = o.live === "1";
  p.layerPictures.live = live;
  if (live) {
    p.layerPictures.engines[0].cells = grids.get(o.g0); p.layerPictures.engines[1].cells = grids.get(o.g1);
    p.layerPictures.stages[0].hold = Number(o.h0); p.layerPictures.stages[1].hold = Number(o.h1);
  } else {
    p.pictureStage.hold = Number(o.hs);
    p.pictureEngine.cells = grids.get(o.gs);
  }
  // As restoreInto takes them: a value the menu has not got is the layer's own.
  p.scan.reads[0] = p.scanReadsOf(o.r0, "A");
  p.scan.reads[1] = p.scanReadsOf(o.r1, "B");
  p.__put({ now: Number(o.now || 0), spect: o.spect === "1", count: Number(o.count), depth: [Number(o.d0), Number(o.d1)] });
  if (words[0] === "strike") {
    const [x, y, w, h] = o.plot.split(",").map(Number);
    Object.assign(p.plot, { x, y, w, h });
    p.midi.layers.mode = o.split === "1" ? "split" : "layer";
    p.midi.layers.point = Number(o.point);
    p.scan.strike = Number(o.amount);
    p.scanStrike(Number(o.note), Number(o.vel));
    const laid = p.__taken();
    const row = [];
    for (const seg of laid) row.push(5, ...seg);
    if (!laid.length) row.push(6);
    out.push(show(row));
    continue;
  }
  p.scanStep(Number(o.elapsed));
  const row = [];
  for (const [field, value, l] of p.__take()) {
    if (field === "scanHold") row.push(1, l, value);
    else if (field === "scanTable") { row.push(2, l, value.most, value.levels.length); for (const t of value.levels) row.push(t.length, ...t); }
    else throw new Error("unexpected genSet " + field);
  }
  for (let l = 0; l < 2; l++) {
    const path = p.scan.paths[l];
    if (path) row.push(3, l, path.cx, path.cy, path.r); else row.push(4, l);
  }
  out.push(show(row));
}
fs.writeSync(1, out.join("\n") + "\n");
