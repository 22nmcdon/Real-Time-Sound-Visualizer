/* The strike lab and the bend lab (20 Nov). The owner turns knobs and sees
   one hard strike - and the stroke dragged out of it - or one bend's smear,
   painted live by the instrument's own look (paintView, lifted unchanged out
   of web/scope.html by make.py) from stamps of the kinds the core already
   lays: brush stamps (kind 0), drops (1) and the bend's smear (2). So any look
   found here is one the core can be made to lay, stamp for stamp, and the map
   beside it is the look's paint summed to the core's 128 cells, which is what
   the core's map holds when it lays the same stamps (the look equals the map).
   The stamps here are written by this file, not by the core: it is the place
   to find the settings, and the core is then made to match them. */
"use strict";

const N = PAINT_CELLS;  // cells across the canvas
function rng(seed) {
  let a = (seed >>> 0) || 1;
  return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

// One stamp's row, as the instrument serves it (Instrument::kStampFloats, PAINT_STAMP): positions and width in cells here.
function stampRow(o) {
  const r = new Float32Array(PAINT_STAMP);
  r[0] = o.x / N; r[1] = o.y / N; r[2] = o.dx; r[3] = o.dy; r[4] = o.w / N; r[5] = o.p; r[6] = o.t; r[7] = o.per ?? 1;
  for (let k = 0; k < 8; k++) r[8 + k] = o.load[k] ?? o.load[0];
  r[16] = o.serial; r[17] = 0; r[18] = o.ink || 0; r[19] = 60; r[20] = o.kind || 0; r[21] = o.a || 0; r[22] = o.b || 0;
  return r;
}

/* A brush dragged along a path of points (cells), a stamp every 0.35 of a cell
   as the core's stroke stamps, its width, pressure and load a function of how
   far along it is (0 to 1) - each stamp's `per` the core's, so the paint laid
   per length does not depend on the spacing. */
function drag(out, pts, f, serial, t0, t1) {
  let len = 0;
  for (let i = 1; i < pts.length; i++) len += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
  if (len <= 0) return;
  let gone = 0, i = 1, carry = 0;
  let px = pts[0].x, py = pts[0].y;
  while (i < pts.length) {
    const ax = pts[i - 1].x, ay = pts[i - 1].y, bx = pts[i].x, by = pts[i].y;
    const seg = Math.hypot(bx - ax, by - ay);
    if (seg <= 1e-9) { i++; continue; }
    const dx = (bx - ax) / seg, dy = (by - ay) / seg;
    let at = carry;
    while (at <= seg) {
      const x = ax + dx * at, y = ay + dy * at, s = (gone + at) / len;
      const moved = Math.hypot(x - px, y - py) || 0.35;
      const g = f(s);
      if (g.p > 0.02) {
        const w = g.w, hl = Math.max(0.75, 0.15 * w);
        out.push(stampRow({ x, y, dx, dy, w, p: g.p, t: t0 + (t1 - t0) * s, per: clamp(moved / (1.4 * hl), 0.02, 1), load: g.load, serial, ink: g.ink || 0 }));
      }
      px = x; py = y;
      at += 0.35;
    }
    carry = at - seg; gone += seg; i++;
  }
}

/* A wandering path: from a point, heading `th`, `len` cells, the heading
   swinging by a slow sway (amplitude `amp` radians, `freq` swings along it)
   and kinking by a random walk (`kink`), and pulled towards `to` over its
   last part when given - each bristle clump's own path, no two alike. */
function wander(r, x, y, th, len, amp, freq, kink, to) {
  const pts = [{ x, y }];
  const ph = r() * Math.PI * 2, steps = Math.max(2, Math.ceil(len / 0.35));
  let walk = 0;
  for (let k = 1; k <= steps; k++) {
    const s = k / steps;
    walk += (r() - 0.5) * kink * 0.6 + (r() < 0.04 * kink ? (r() - 0.5) * kink * 2 : 0);
    let h = th + amp * Math.sin(ph + 2 * Math.PI * freq * s) + walk;
    if (to) {
      // Drawn back in towards where the brush is going: the pull grows over the path's last two thirds.
      const want = Math.atan2(to.y - y, to.x - x), pull = clamp((s - 0.15) / 0.85, 0, 1);
      let d = want - h; while (d > Math.PI) d -= 2 * Math.PI; while (d < -Math.PI) d += 2 * Math.PI;
      h += d * pull * pull;
    }
    x += Math.cos(h) * len / steps; y += Math.sin(h) * len / steps;
    pts.push({ x, y });
  }
  return pts;
}

const STRIKE = [
  // [key, label, min, max, step, default, what it does]
  ["velocity", "Velocity", 1, 127, 1, 127, "How hard the key is struck, at Strike 100: everything below grows with it."],
  ["seed", "Seed", 1, 9999, 1, 17, "Which strike: the same settings, another note."],
  ["width", "Brush width", 2, 12, 0.1, 6, "The stroke's width after the burst, in the map's cells (128 across)."],
  ["radius", "Burst radius", 2, 30, 0.5, 11, "How far the bristles splay out from where it lands, at a full strike (cells)."],
  ["back", "Burst behind", 0, 1, 0.01, 0.25, "How much of the burst goes behind where it lands: nought, a fan forward; one, all round."],
  ["clumps", "Bristle clumps", 4, 40, 1, 16, "How many clumps of bristles splay out."],
  ["clumpWidth", "Clump width", 0.2, 3, 0.05, 1, "How wide each clump is, against the brush's share."],
  ["amp", "Wander", 0, 1.5, 0.01, 0.35, "How far each clump's path sways off straight (radians)."],
  ["freq", "Wander frequency", 0, 4, 0.05, 1.2, "How many sways along a path."],
  ["kink", "Kinks", 0, 1, 0.01, 0.3, "Sudden turns and wobbles on the paths: crossings come from here."],
  ["irregular", "Irregularity", 0, 1, 0.01, 0.5, "How much the clumps differ in length, width and angle."],
  ["pool", "Pool at the centre", 0, 3, 0.05, 1, "The paint squeezed out where it lands: its size."],
  ["paint", "Paint", 0.2, 3, 0.05, 1.4, "How much paint the burst lays: the harder, the more."],
  ["impasto", "Thickness", 0.3, 3, 0.05, 1.4, "How thick the paint stands: the raised, shaded body."],
  ["skips", "Skips", 0, 1, 0.01, 0.35, "How much the outer bristles run dry and skip on the weave."],
  ["ragged", "Ragged ends", 0, 1, 0.01, 0.5, "How unevenly the clumps end: broken, feathered tips."],
  ["trail", "Trails from the burst", 0, 1, 0.01, 0.6, "How much of each clump drags out of the burst into the stroke."],
  ["close", "Closes over", 0.5, 8, 0.1, 2.5, "How many stroke widths the trails take to join the stroke."],
  ["drag", "Drag shown", 10, 90, 1, 45, "How far the stroke is dragged out of the burst (cells)."],
  ["curve", "Stroke curve", -0.02, 0.02, 0.0005, 0.006, "The stroke bends as the ring does."],
];
const BEND = [
  ["seed", "Seed", 1, 9999, 1, 5, "Which bend: the same settings, another note."],
  ["width", "Brush width", 2, 12, 0.1, 6, "The stroke's width (cells)."],
  ["paint", "Stroke paint", 0.2, 2.5, 0.05, 1, "How much paint the stroke itself holds."],
  ["speed", "Bend speed", 0, 1, 0.01, 1, "Nought a slow bend (broad, soft), one a flick (narrower, longer)."],
  ["reach", "Reach", 3, 80, 1, 30, "How far the smear is dragged (cells)."],
  ["take", "Take", 0.05, 0.95, 0.01, 0.5, "How much of the wet paint under the brush each step drags away."],
  ["body", "Body", 0.05, 2, 0.01, 0.6, "How thick the smear's paint lies."],
  ["sweep", "Sweep", 0, 1.5, 0.01, 0.6, "How much the smear curves back along the stroke as the brush moves on."],
  ["groupWidth", "Smear width", 0.5, 4, 0.05, 1.6, "How wide each bristle group's smear is, against its share of the brush."],
  ["steps", "Bend length", 3, 60, 1, 15, "How many frames the bend moves over: a few a flick, many a slow drag."],
  ["dir", "Up or down", -1, 1, 2, 1, "Up pulls outward, down inward."],
];

function strikeStamps(P) {
  const out = [], r = rng(P.seed * 7919 + 13);
  const impact = clamp(P.velocity / 127, 0, 1), k = Math.pow(impact, 1.5);
  const hw = P.width / 2, L = { x: 30, y: 60 };
  const n = Math.round(P.clumps), R = P.radius * Math.max(0.05, k);
  const along = (s) => ({ x: L.x + s, y: L.y + P.curve * s * s });  // the stroke's own path, gently bending
  let serial = 2;
  // The pool: what the press squeezes out, pooled at the centre and pushed into lumps round it.
  if (P.pool > 0 && k > 0.01) {
    const r0 = P.pool * hw * 0.6 * Math.sqrt(k);
    out.push(stampRow({ x: L.x, y: L.y, dx: 1, dy: 0, w: 2 * r0, p: 1.2, t: 0, load: [0.35 * P.paint * P.impasto * (0.6 + k)], serial: 1, kind: 1, a: 1, b: (P.seed * 31) & 0xffffff }));
    const lumps = 5 + Math.round(4 * r());
    for (let j = 0; j < lumps; j++) {
      const a = r() * Math.PI * 2, d = r0 * (0.7 + 0.6 * r());
      out.push(stampRow({ x: L.x + Math.cos(a) * d, y: L.y + Math.sin(a) * d, dx: Math.cos(a), dy: Math.sin(a), w: 2 * r0 * (0.25 + 0.35 * r()), p: 0.8,
        t: 0, load: [0.3 * P.paint * P.impasto * (0.6 + k)], serial: 1, kind: 1, a: 1 + r(), b: ((P.seed * 131 + j * 977) & 0xffffff) }));
    }
  }
  // The burst: each clump pressed out from where it lands, along its own wandering path; then dragged after the brush.
  for (let i = 0; i < n; i++) {
    const u = ((i + 0.5) / n) * 2 - 1;                    // its place across the brush, -1 to 1
    const irr = P.irregular;
    // Its way out: the middle forward, the sides round to the sides and, as far as `back` says, behind.
    const span = Math.PI * (0.5 + 0.5 * P.back);
    const th = u * span + (r() - 0.5) * irr * 0.9;
    const len = R * (1 - irr * 0.5 + irr * r()) * (1 - 0.25 * Math.abs(u) * P.back);
    const wc = (2 * hw / n) * P.clumpWidth * (1 - irr * 0.45 + irr * 0.9 * r()) * (0.6 + 0.4 * Math.sqrt(k));
    const ink = 0, outer = Math.abs(u);
    const load0 = P.paint * P.impasto * (0.8 + 0.8 * k) * (1 - irr * 0.3 + irr * 0.6 * r());
    const dry = 1 - P.skips * (0.3 + 0.7 * outer);
    const end = 1 - P.ragged * 0.45 * r();
    if (len > 0.3) {
      const pts = wander(r, L.x, L.y, th, len * end, P.amp, P.freq, P.kink, null);
      drag(out, pts, (s) => ({ w: wc * (1 - 0.35 * s), p: clamp(1.05 - 0.6 * s, 0, 1), load: [load0 * (1 - (1 - dry) * s * 1.4)], ink }), serial, 0.0, 0.04);
    }
    // Its trail: from part way out along the burst, dragged into its place in the brush as the stroke leaves.
    if (P.trail > 0 && len > 0.3) {
      const from = len * (1 - P.trail) * 0.9;
      const fx = L.x + Math.cos(th) * from, fy = L.y + Math.sin(th) * from;
      const join = P.close * P.width, to = along(join);
      const target = { x: to.x, y: to.y + u * hw * 0.85 };
      const dist = Math.hypot(target.x - fx, target.y - fy);
      const pts = wander(r, fx, fy, Math.atan2(target.y - fy, target.x - fx) + (r() - 0.5) * 0.8, dist, P.amp * 0.6, P.freq, P.kink * 0.7, target);
      drag(out, pts, (s) => ({ w: wc * (0.8 + 0.2 * s), p: 0.75 + 0.15 * s, load: [load0 * 0.7 * (dry + (1 - dry) * s)], ink }), serial, 0.04, 0.12);
    }
    serial++;
  }
  // The stroke: the brush gathered, dragged on from where the trails join it.
  const start = P.trail > 0 ? P.close * P.width * 0.75 : 0;
  const pts = [];
  for (let s = start; s <= P.drag; s += 0.5) pts.push(along(s));
  drag(out, pts, (s) => ({ w: P.width / (0.4 + 0.6 * 0.85), p: 0.85, load: [0.9, 1.0, 1.05, 1.1, 1.1, 1.05, 1.0, 0.9].map((v) => v * (1.1 - 0.4 * s) * (0.9 + 0.3 * k)) }), 1, 0.12, 0.12 + P.drag / 30);
  return out;
}

/* One bend: a stroke along an arc of the ring, moving out (or in) by the
   bend's few cells over `steps` frames, and each frame of the move the
   brush's eight groups each drag a smear (kind 2) the way the pitch went, as
   the core's pull lays them; the knobs set what the core will compute. */
function bendStamps(P) {
  const out = [], r = rng(P.seed * 104729 + 7);
  const C = { x: 64, y: 64 }, R0 = 38, hw = P.width / 2;
  const turn = 8, fps = 60, speed = 2 * Math.PI * R0 / turn;  // cells a second along the ring
  const total = 2.2 * fps, b0 = Math.round(0.55 * fps), b1 = b0 + Math.round(P.steps);
  const dr = 1.0 * P.dir;
  const sharp = P.speed;
  let prev = null;
  for (let f = 0; f <= total; f++) {
    const t = f / fps, th = -Math.PI * 0.8 + 2 * Math.PI * t / turn;
    const q = f <= b0 ? 0 : f >= b1 ? 1 : (f - b0) / (b1 - b0);
    const rad = R0 + dr * q * q * (3 - 2 * q);
    const x = C.x + Math.cos(th) * rad, y = C.y + Math.sin(th) * rad;
    if (prev) {
      const dx = x - prev.x, dy = y - prev.y, len = Math.hypot(dx, dy);
      const steps = Math.max(1, Math.ceil(len / 0.35));
      for (let s = 1; s <= steps; s++) {
        const sx = prev.x + dx * s / steps, sy = prev.y + dy * s / steps;
        out.push(stampRow({ x: sx, y: sy, dx: dx / len, dy: dy / len, w: P.width / 0.91, p: 0.85, t, per: clamp((len / steps) / (1.4 * Math.max(0.75, 0.15 * P.width)), 0.02, 1),
          load: [P.paint], serial: 1 }));
      }
      if (f > b0 && f <= b1) {
        // The pull: radial, the way the pitch went; the groups across the way the brush travels.
        const ux = Math.cos(th) * Math.sign(dr), uy = Math.sin(th) * Math.sign(dr);
        const fx = -Math.sin(th), fy = Math.cos(th);  // travel
        const vx = -uy, vy = ux;
        const sweep = -(fx * vx + fy * vy) * P.sweep;
        const gw = hw / 8 * P.groupWidth * (1 + 0.9 * (1 - sharp));
        const len = P.reach * (0.45 + 0.55 * sharp) / gw;
        for (let g = 0; g < 8; g++) {
          const across = (2 * g - 7) / 8 * hw;
          out.push(stampRow({ x: x - fy * across, y: y + fx * across, dx: ux, dy: uy, w: 2 * gw, p: P.take, t, per: sweep,
            load: [P.body * (0.8 + 0.4 * r()), sharp, 3.0], serial: 1, kind: 2, a: len, b: (P.seed * 977 + f * 31 + g * 7) & 0xffffff }));
        }
      }
    }
    prev = { x, y };
  }
  return out;
}

// ---- the page -----------------------------------------------------------------
/* Each lab's view: the window onto the 128-cell canvas it shows, its left, top and size in cells - the strike's a
   close-up round where it lands (twice the look's pixels), the bend's the whole ring. Zoom flips to the whole canvas. */
const labs = { strike: { knobs: STRIKE, make: strikeStamps, values: {}, view: [14, 30, 64] },
               bend: { knobs: BEND, make: bendStamps, values: {}, view: [0, 0, 128] } };
let whole = false;
function view() { return whole ? [0, 0, 128] : labs[current].view; }
// The look's canvas is the sheet's; the sheet is made as large as the view needs and slid so the view fills the frame.
function frame() {
  const [x, y, size] = view(), z = N / size, sheet = document.getElementById("sheet");
  sheet.style.width = (z * 100) + "%"; sheet.style.height = (z * 100) + "%";
  sheet.style.left = (-x / N * z * 100) + "%"; sheet.style.top = (-y / N * z * 100) + "%";
}
let current = "strike", pending = 0;

function readStored() {
  for (const [name, lab] of Object.entries(labs)) {
    let kept = {};
    try { kept = JSON.parse(localStorage.getItem("strikeLab." + name) || "{}"); } catch (e) { kept = {}; }
    for (const [key, , , , , def] of lab.knobs) lab.values[key] = Number.isFinite(kept[key]) ? kept[key] : def;
  }
}
function store() { try { localStorage.setItem("strikeLab." + current, JSON.stringify(labs[current].values)); } catch (e) { /* a private window */ } }

function buildKnobs() {
  const box = document.getElementById("knobs");
  box.textContent = "";
  const lab = labs[current];
  for (const [key, label, min, max, step, , what] of lab.knobs) {
    const row = document.createElement("label");
    row.className = "knob"; row.title = what;
    const name = document.createElement("span"); name.className = "name"; name.textContent = label;
    const input = document.createElement("input"); input.type = "range"; input.min = min; input.max = max; input.step = step; input.value = lab.values[key];
    const val = document.createElement("span"); val.className = "val"; val.textContent = String(lab.values[key]);
    const help = document.createElement("span"); help.className = "help"; help.textContent = what;
    input.addEventListener("input", () => { lab.values[key] = Number(input.value); val.textContent = input.value; store(); schedule(); });
    row.append(name, input, val, help);
    box.append(row);
  }
  writeCopy();
}

function writeCopy() {
  document.getElementById("copy").value = JSON.stringify({ lab: current, settings: labs[current].values });
}

function schedule() { writeCopy(); clearTimeout(pending); pending = setTimeout(render, 60); }

let base = 0;
function render() {
  const stamps = labs[current].make(labs[current].values);
  // Stamps' times run on from the last render's, so the look's drying clock sees fresh paint each time.
  base += 100;
  for (const s of stamps) s[6] += base;
  stamps.sort((a, b) => a[6] - b[6]);
  paintView.clear();
  let from = paintView.since + 1, i = 0, ms = base * 1000;
  const step = 1 / 60;
  const t0 = stamps.length ? stamps[0][6] : base;
  for (let edge = t0 + step; i < stamps.length; edge += step) {
    const batch = [];
    while (i < stamps.length && stamps[i][6] < edge) batch.push(stamps[i++]);
    if (batch.length) {
      const f = new Float32Array(batch.length * PAINT_STAMP);
      batch.forEach((s, k) => f.set(s, k * PAINT_STAMP));
      paintView.take({ on: true, from, count: batch.length, stamps: f }); from += batch.length;
    }
    ms += 1000 / 60;
    paintView.draw(ms);
  }
  paintView.draw(ms + 16);
  drawMap();
  document.getElementById("count").textContent = stamps.length + " stamps";
}

// The look's paint summed to the core's cells, as the core's map would hold it: thickness grey, a thick stroke black.
function drawMap() {
  const cv = document.getElementById("map"), g = cv.getContext("2d");
  const cells = paintView.sample(N);
  if (!cells) { g.fillStyle = "#fffcf7"; g.fillRect(0, 0, N, N); return; }
  const per = (PAINT_SIZE / N) * (PAINT_SIZE / N);
  const img = g.createImageData(N, N);
  for (let y = 0; y < N; y++)
    for (let x = 0; x < N; x++) {
      const a = cells[y * N + x] / per;
      const v = Math.pow(clamp(a / 1.2, 0, 1), 0.6), grey = Math.round(255 * (1 - 0.92 * v));
      const o = (y * N + x) * 4;  // the look's row nought is the canvas's top, as its picture shows it
      img.data[o] = grey; img.data[o + 1] = grey; img.data[o + 2] = grey; img.data[o + 3] = 255;
    }
  const full = document.createElement("canvas"); full.width = N; full.height = N;
  full.getContext("2d").putImageData(img, 0, 0);
  const [x, y, size] = view();
  g.imageSmoothingEnabled = false;
  g.fillStyle = "#fffcf7"; g.fillRect(0, 0, N, N);
  g.drawImage(full, x, y, size, size, 0, 0, N, N);
}

function show(name) {
  current = name;
  for (const b of document.querySelectorAll(".tab")) b.setAttribute("aria-pressed", String(b.dataset.lab === name));
  document.getElementById("what").textContent = name === "strike"
    ? "One hard strike at Strike 100, and the stroke dragged out of it. Turn the knobs; the look redraws."
    : "One bend on the ring, and the smear it drags. Turn the knobs; the look redraws.";
  buildKnobs(); frame(); render();
}

window.addEventListener("DOMContentLoaded", () => {
  readStored();
  paintView.setOn(true);
  document.getElementById("reseed").addEventListener("click", () => {
    const lab = labs[current]; lab.values.seed = 1 + Math.floor(Math.random() * 9999); store(); buildKnobs(); render();
  });
  document.getElementById("reset").addEventListener("click", () => {
    const lab = labs[current]; for (const [key, , , , , def] of lab.knobs) lab.values[key] = def; store(); buildKnobs(); render();
  });
  document.getElementById("copyBtn").addEventListener("click", () => {
    const t = document.getElementById("copy"); t.select();
    try { navigator.clipboard.writeText(t.value); } catch (e) { document.execCommand("copy"); }
  });
  for (const b of document.querySelectorAll(".tab")) b.addEventListener("click", () => show(b.dataset.lab));
  document.getElementById("zoom").addEventListener("click", (e) => {
    whole = !whole; e.target.textContent = whole ? "Close up" : "Whole canvas"; frame(); render();
  });
  if (paintView.mode !== "gpu") document.getElementById("count").textContent = "This page needs WebGL 2: " + paintView.why;
  show("strike");
});
