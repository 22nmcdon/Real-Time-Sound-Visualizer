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
     view GX GY OX OY SPIN ZOOM   limit DB   step ELAPSED
   Usage: node picture_js.mjs <runs> */
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
let clock = 0;
const performance = { now: () => clock };
const TWO_PI = Math.PI * 2;
const state = { persistence: 0.12, display: "xy", xyPair: [0, 1], channels: [{ offset: 0 }, { offset: 0 }],
                zoom: 1, analyseAt: "post", rotate: 0, rotateMod: 0 };
let plot = { x: 0, y: 0, w: 1, h: 1 };
const gains = [1, 1];
const gainOf = (ch) => gains[ch];
let limiting = 0;
function monitorLimiting() { return limiting; }
`;
const LIFTED = ["PHOSPHOR_N", "phosphor", "phosphorFade", "phosphorSegment", "phosphorDeposit", "phosphorRead",
  "BEAM_K", "PHOTO_REACH", "PHOTO_START", "PHOTO_SLEW", "photo", "photoStep",
  "METER_COARSE", "METER_EVERY", "METER_DEPTH", "METER_RECENT", "METER_WINDOW", "CHANGE_FLOOR", "NOVELTY_FLOOR",
  "SATURATED", "STRAINED", "makePictureMeter", "pictureMeter", "makeMoments", "shapeX", "shapeOfPair",
  "turnOf", "rotateTurns", "SIXTH", "picture", "BORED_REACH", "BORED_RISE", "BORED_LEAK", "boredLevel", "pictureStep"];
const source = STUBS + LIFTED.map(definition).join("\n") + `
return { state, gains, phosphor, phosphorFade, phosphorSegment, phosphorDeposit, phosphorRead, photo, photoStep,
         pictureMeter, shapeOfPair, picture, pictureStep, boredLevel: () => boredLevel,
         setPlot: (p) => { plot = p; }, setLimiting: (v) => { limiting = v; } };`;

const show = (v) => Number(v).toPrecision(17);

function run(commands) {
  const s = new Function(source)();
  let frame = null;
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
      // setPhoto's part that is not the panel's.
      s.photo.on = a[0] === "1";
      if (a.length > 2) { s.photo.u = Number(a[1]); s.photo.v = Number(a[2]); }
      if (s.photo.on) s.pictureMeter.reset(); else { s.photo.value = 0; s.photo.raw = 0; }
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
    else if (cmd === "step") {
      s.photoStep(Number(a[0]));
      s.pictureStep(frame, Number(a[0]));
      const p = s.picture, r = p.raw, m = s.pictureMeter;
      const shape = frame ? s.shapeOfPair(frame) : { signed: 0, edge: 0 };
      extra = [" photo", show(s.photo.raw), show(s.photo.value),
               "values", ...["round", "cover", "change", "novelty", "signed", "edge", "bored"].map((k) => show(p[k])),
               "raw", ...["round", "cover", "change", "novelty", "signed", "edge", "bored"].map((k) => show(r[k])),
               "meter", show(m.coverage), show(m.lit), show(m.change), show(m.novelty), m.depth, m.verdict(),
               "shape", show(shape.signed), show(shape.edge)].join(" ");
    } else throw new Error("unknown command " + cmd);
    let a1 = 0, a2 = 0;
    const g = s.phosphor.grid;
    for (let i = 0; i < g.length; i++) { a1 += g[i] * (i + 1); a2 += g[i] * g[i]; }
    lines.push(cmd + " | grid " + show(a1) + " " + show(a2) + " round "
               + show(s.phosphor.moments ? s.phosphor.moments.roundness() : 0) + extra);
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
