/* The page's picture sources - the phosphor grid, the beam's moments, the
   picture meter, the drawn pair's shape, the photocell and pictureStep -
   lifted out of web/scope.html by name and driven through the runs in a
   file, one result line per command, as picture_cpp prints them.

   What the renderer would deposit is the run's: segments and polylines in
   canvas pixels over a graticule the run places. The drawn pair is lanes the
   run makes, seen through gains, offsets, a turn and a zoom the run sets.

   A file is runs of `run`, then one command a line, then `end`:
     plot X Y W H   persist P   fade [1]   seg X0 Y0 X1 Y1 LEVEL
     poly X,Y;X,Y;... [S,S,...]   read U V   photo 0|1 [U V]   spect 0|1
     pair ellipse A B CYCLES N PHASE | pair noise SEED AMP N | pair none
     view GX GY OX OY SPIN ZOOM   limit DB   step ELAPSED (the photocell, the picture, then its stage)
   and each layer's picture (P6), whose lines add the layers' state:
     lframe L ellipse A B CYCLES N PHASE | lframe L noise SEED AMP N  (layer L's two lanes, 2L and 2L+1)
     lon ON TWO (keyboard layers in X-Y, and two figures drawn)   lfade [1]   lpoly L X,Y;... [S,...]
     lstep ELAPSED   moves A B   lput L GLOW MOTION MEMORY HOLD   sput GLOW MOTION MEMORY HOLD   push
   and how each hand's picture responds (11 Nov): resp HAND MODE RISE FALL SWELL, MODE 0 Change, 1 Level, 2 Both
   Usage: node picture_js.mjs <runs> */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { mulberry32 } from "./js_core.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
// SCOPE_PAGE names another copy of the page, for a check that alters one.
const page = fs.readFileSync(process.env.SCOPE_PAGE || path.join(here, "..", "..", "..", "web", "scope.html"), "utf8");

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
let clock = 0;
const performance = { now: () => clock };
const TWO_PI = Math.PI * 2;
const state = { persistence: 0.12, display: "xy", xyPair: [0, 1],
                channels: [{ offset: 0 }, { offset: 0 }, { offset: 0 }, { offset: 0 }],
                zoom: 1, analyseAt: "post", rotate: 0, rotateMod: 0 };
let plot = { x: 0, y: 0, w: 1, h: 1 };
const gains = [1, 1, 1, 1];
// Each layer's picture: whether the page would have them (layerPicturesOn)
// and whether two figures are drawn (sourceFigures) are the run's to say.
let layersOnNow = false, twoFigures = false;
const wasmModule = () => new WebAssembly.Module(WASM_BYTES);
const gainOf = (ch) => gains[ch];
let limiting = 0;
function monitorLimiting() { return limiting; }
`;
/* The page's picture engine (5d) is made here as the page makes it: the
   JavaScript one, or with CORE=wasm in the environment the compiled core's,
   from the module the page carries - so the same runs hold the compiled
   picture engine to the page's and to the native core. */
const MODE = process.env.CORE || "js";
const ENGINE = MODE === "wasm"
  ? `const pictureEngine = makeWasmPictureEngine(new WebAssembly.Module(WASM_BYTES));`
  : `const pictureEngine = makePictureEngine();`;
const LIFTED = ["PHOSPHOR_N", "phosphor", "phosphorFade", "phosphorFadeInto", "phosphorSegment", "phosphorSegmentInto",
  "phosphorDeposit", "phosphorRead", "phosphorReadGrid",
  "BEAM_K", "PHOTO_REACH", "PHOTO_START", "PHOTO_SLEW", "photo", "photoStep",
  "METER_COARSE", "METER_EVERY", "METER_DEPTH", "METER_RECENT", "METER_WINDOW", "METER_DRIFT", "CHANGE_FLOOR", "NOVELTY_FLOOR",
  "SATURATED", "STRAINED", "makePictureMeter", "makeMoments", "shapeX", "NO_LANE", "pairOfFrame", "shapeOfPair",
  "shapeOfPairValues", "turnOf", "rotateTurns", "SIXTH", "picture", "BORED_REACH", "BORED_RISE", "BORED_LEAK",
  "PICTURE_KEYS", "makePictureEngine", "VERDICTS", "makeWasmPictureEngine", ENGINE, "pictureMeter", "pictureStep",
  "STAGE_LEVEL_EPS", "STAGE_CHANGE_SPAN", "STAGE_SETTLE", "STAGE_CHANGE_DEAD", "STAGE_BOTH_BASE", "STAGE_MOTION_SCALE", "STAGE_SWELL_DEPTH",
  "STAGE_SWELL_LEAST", "STAGE_LIT_FLOOR", "STAGE_DEFAULT", "STAGE_LEVEL_TOP", "stageLevel", "stageSwellPeriod", "stageToward",
  "RESPONDS_TO", "PICTURE_RESPONSE", "PICTURE_FEELS", "pictureFeelMs", "pictureHands", "stageResponse",
  "STAGE_HOLD_FALL", "makeStageState", "pictureStage", "pictureStageStep", "stagePush",
  "pictureCoreKind", "LAYER_MOVES", "makeLayerValues", "makeLayerStage", "layerPictures", "pictureMovesOf", "layerPush",
  "layerEnginesNeeded", "layerPicturesFade", "layerPicturesDeposit", "noPhotocell", "layerPicturesStep"];
const WASM_BYTES = MODE === "wasm" ? (() => {
  const at = page.indexOf("/* WASM_CORE_BEGIN */\"");
  return Uint8Array.from(Buffer.from(page.slice(at + 22, page.indexOf("\"/* WASM_CORE_END */", at)), "base64"));
})() : null;
/* After the lifted definitions, since a declaration later in a scope wins:
   the one-line stagePush is lifted to the next closing brace on its own
   line, which is the end of the page's layerPicturesOn. */
const LAYER_STUBS = `
function layerPicturesOn() { return layersOnNow; }
function sourceFigures() { return twoFigures ? [[0, 1], [2, 3]] : null; }
`;
const source = STUBS + LIFTED.map((name) => (name.startsWith("const ") ? name + "\n" : definition(name))).join("\n") + LAYER_STUBS + `
return { state, gains, phosphor, phosphorFade, phosphorSegment, phosphorDeposit, phosphorRead, photo, photoStep,
         pictureMeter, shapeOfPair, picture, pictureStep, pictureStage, engine: pictureEngine,
         stageSources: { glow: () => stagePush("glow"), motion: () => stagePush("motion"), memory: () => stagePush("memory") },
         setPlot: (p) => { plot = p; }, setLimiting: (v) => { limiting = v; }, getLimiting: () => limiting,
         layerPictures, layerPush, pictureMovesOf, layerPicturesFade, layerPicturesDeposit, layerPicturesStep,
         setLayers: (on, two) => { layersOnNow = on; twoFigures = two; }, setCoreKind: (k) => { pictureCoreKind = k; },
         pictureHands, RESPONDS_TO };`;

const show = (v) => Number(v).toPrecision(17);

function run(commands) {
  const s = new Function("WASM_BYTES", source)(WASM_BYTES);
  // The layers' engines of the same kind as the shown one, as the page makes them.
  s.setCoreKind(MODE);
  let frame = null;
  const layerFrame = { channels: [0, 1, 2, 3].map(() => new Float32Array(0)), turned: false };
  let layerFramed = false;
  // A pair of lanes as the `pair` command makes them.
  const lanesOf = (a) => {
    const n = Number(a[a[0] === "ellipse" ? 4 : 3]);
    const left = new Float32Array(n), right = new Float32Array(n);
    if (a[0] === "ellipse") {
      const A = Number(a[1]), B = Number(a[2]), cycles = Number(a[3]), phase = Number(a[5]);
      for (let i = 0; i < n; i++) {
        left[i] = A * Math.cos(2 * Math.PI * cycles * i / n);
        right[i] = B * Math.sin(2 * Math.PI * cycles * i / n + phase);
      }
    } else {
      const next = mulberry32(Number(a[1])), amp = Number(a[2]);
      for (let i = 0; i < n; i++) { left[i] = (next() * 2 - 1) * amp; right[i] = (next() * 2 - 1) * amp; }
    }
    return [left, right];
  };
  const keys = ["round", "cover", "change", "novelty", "signed", "bored"];
  const layerState = () => {
    const L = s.layerPictures;
    const sums = (engine) => {
      if (!engine) return "- -";
      let a1 = 0, a2 = 0;
      const g = engine.cells;
      for (let i = 0; i < g.length; i++) { a1 += g[i] * (i + 1); a2 += g[i] * g[i]; }
      return show(a1) + " " + show(a2);
    };
    const out = [" layers", L.live ? "1" : "0", "moves", L.moves[0], L.moves[1]];
    for (let l = 0; l < 2; l++) {
      const v = L.values[l], st = L.stages[l], engine = L.engines && L.engines[l];
      out.push("L" + l, "grid", sums(engine), "values", ...keys.map((k) => show(v[k])), "raw", ...keys.map((k) => show(v.raw[k])),
               "verdict", engine ? engine.meter.verdict().replace(/ /g, "_") : "-", "stage", ...["glow", "motion", "memory", "hold"].map((k) => show(st[k])));
    }
    out.push("pushes", ...[0, 1].flatMap((l) => ["glow", "motion", "memory"].map((k) => show(s.layerPush(k, l)))));
    return out.join(" ");
  };
  const lines = [];
  for (const words of commands) {
    const [cmd, ...a] = words;
    let extra = "";
    if (cmd === "plot") s.setPlot({ x: Number(a[0]), y: Number(a[1]), w: Number(a[2]), h: Number(a[3]) });
    else if (cmd === "persist") s.state.persistence = Number(a[0]);
    else if (cmd === "fade") s.phosphorFade(a[0] === "1");
    else if (cmd === "seg") s.phosphorSegment(...a.slice(0, 5).map(Number));
    else if (cmd === "poly") {
      const points = a[0].split(";").map((p) => p.split(",").map(Number));
      const xs = points.map((p) => p[0]), ys = points.map((p) => p[1]);
      s.phosphorDeposit(xs, ys, points.length, a[1] ? a[1].split(",").map(Number) : undefined);
    } else if (cmd === "read") extra = " read " + show(s.phosphorRead(Number(a[0]), Number(a[1])));
    else if (cmd === "photo") {
      // setPhoto's part that is not the panel's. The meter is not started
      // afresh: since the picture stage it never stops.
      s.photo.on = a[0] === "1";
      if (a.length > 2) { s.photo.u = Number(a[1]); s.photo.v = Number(a[2]); }
      if (!s.photo.on) { s.photo.value = 0; s.photo.raw = 0; }
    } else if (cmd === "spect") s.state.display = a[0] === "1" ? "spect" : "xy";
    else if (cmd === "pair") {
      if (a[0] === "none") frame = null;
      else {
        const n = Number(a[a[0] === "ellipse" ? 4 : 3]);
        const left = new Float32Array(n), right = new Float32Array(n);
        if (a[0] === "ellipse") {
          const A = Number(a[1]), B = Number(a[2]), cycles = Number(a[3]), phase = Number(a[5]);
          for (let i = 0; i < n; i++) {
            left[i] = A * Math.cos(2 * Math.PI * cycles * i / n);
            right[i] = B * Math.sin(2 * Math.PI * cycles * i / n + phase);
          }
        } else {
          const next = mulberry32(Number(a[1])), amp = Number(a[2]);
          for (let i = 0; i < n; i++) { left[i] = (next() * 2 - 1) * amp; right[i] = (next() * 2 - 1) * amp; }
        }
        frame = { channels: [left, right], turned: false };
      }
    } else if (cmd === "view") {
      s.gains[0] = Number(a[0]); s.gains[1] = Number(a[1]);
      s.state.channels[0].offset = Number(a[2]); s.state.channels[1].offset = Number(a[3]);
      s.state.rotate = Number(a[4]); s.state.zoom = Number(a[5]);
    } else if (cmd === "limit") s.setLimiting(Number(a[0]));
    else if (cmd === "lframe") {
      const [left, right] = lanesOf(a.slice(1));
      layerFrame.channels[2 * Number(a[0])] = left; layerFrame.channels[2 * Number(a[0]) + 1] = right;
      layerFramed = true;
    } else if (cmd === "lon") s.setLayers(a[0] === "1", a[1] === "1");
    else if (cmd === "lfade") s.layerPicturesFade(a[0] === "1");
    else if (cmd === "lpoly") {
      const points = a[1].split(";").map((p) => p.split(",").map(Number));
      s.layerPicturesDeposit(Number(a[0]), points.map((p) => p[0]), points.map((p) => p[1]), points.length,
                             a[2] ? a[2].split(",").map(Number) : null);
    } else if (cmd === "lstep") s.layerPicturesStep(layerFramed ? layerFrame : null, Number(a[0]), s.state.display === "spect", s.getLimiting());
    else if (cmd === "moves") { s.layerPictures.moves[0] = s.pictureMovesOf(a[0], "A"); s.layerPictures.moves[1] = s.pictureMovesOf(a[1], "B"); }
    else if (cmd === "lput") Object.assign(s.layerPictures.stages[Number(a[0])],
                                           { glow: Number(a[1]), motion: Number(a[2]), memory: Number(a[3]), hold: Number(a[4]) });
    else if (cmd === "sput") Object.assign(s.pictureStage, { glow: Number(a[0]), motion: Number(a[1]), memory: Number(a[2]), hold: Number(a[3]) });
    else if (cmd === "push") { /* the state alone */ }
    else if (cmd === "resp") Object.assign(s.pictureHands[Number(a[0])], { responds: s.RESPONDS_TO[Number(a[1])],
                                           feel: "custom", rise: Number(a[2]), fall: Number(a[3]), swell: a[4] === "1" });
    else if (cmd === "step") {
      s.photoStep(Number(a[0]));
      s.pictureStep(frame, Number(a[0]));
      const p = s.picture, r = p.raw, m = s.pictureMeter;
      const shape = frame ? s.shapeOfPair(frame) : { signed: 0 };
      extra = [" photo", show(s.photo.raw), show(s.photo.value),
               "values", ...["round", "cover", "change", "novelty", "signed", "bored"].map((k) => show(p[k])),
               "raw", ...["round", "cover", "change", "novelty", "signed", "bored"].map((k) => show(r[k])),
               "meter", show(m.coverage), show(m.lit), show(m.change), show(m.novelty), m.depth, m.verdict(),
               "shape", show(shape.signed),
               "stage", ...["glow", "motion", "memory", "hold"].map((k) => show(s.pictureStage[k])),
               // What the stage's sources hand the matrix, read from the sources themselves.
               "pushes", ...["glow", "motion", "memory"].map((k) => show(s.stageSources[k]()))].join(" ");
    } else throw new Error("unknown command " + cmd);
    let a1 = 0, a2 = 0;
    const g = s.phosphor.grid;
    for (let i = 0; i < g.length; i++) { a1 += g[i] * (i + 1); a2 += g[i] * g[i]; }
    if (/^(l|moves|sput|push)/.test(cmd)) extra += layerState();
    lines.push(cmd + " | grid " + show(a1) + " " + show(a2) + " round "
               + show(s.engine.roundness) + extra);
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
