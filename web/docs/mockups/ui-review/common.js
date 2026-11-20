/* The three UI-review mockups' shared frame: the window laid out in the boxes
   scope.html measures at each of the six windows, the knob, the switch, the
   checkbox drawn as a switch, and the info line in the Picture strip. Each
   mockup builds its own panel into it. Controls carry the page's ids, types,
   ranges and options (data.js, read from the page by write_data.py), and the
   info line says what the page says (CONTROL_WORDS). */
(function () {
"use strict";
const D = window.UI_DATA;
const ATTR = {};
for (const k of Object.keys(D.attrs)) for (const a of D.attrs[k]) ATTR[a.id] = a;

/* The windows: header, screen column, tabs, the tab's own area, the modulation row and the
   Picture strip, as scope.html lays them out (the play-band mockup's table, read from the page at
   d5c2928 and unchanged since), and where Scope & measure and Perform open, measured on testing
   (5ba8ae9). 960 x 600 is the plugin's minimum at Auto's 90 per cent: 1067 by 667 of the page's
   own pixels, compact. */
const SIZES = {
  "1660x1050": { label: "1660 × 1050", w: 1660, h: 1050, zoom: 1, compact: false, hdr: 71, benchL: 788, railT: 86, railH: 60, stageT: 159, stageW: 838, stageH: 706, modT: 873, modH: 87, picT: 960, picH: 90, measT: 123, perfL: 646 + 374, perfT: 58 },
  "1400x900": { label: "1400 × 900", w: 1400, h: 900, zoom: 1, compact: false, hdr: 71, benchL: 538, railT: 86, railH: 60, stageT: 159, stageW: 838, stageH: 556, modT: 723, modH: 87, picT: 810, picH: 90, measT: 123, perfL: 646 + 114, perfT: 58 },
  "1100x860": { label: "1100 × 860", w: 1100, h: 860, zoom: 1, compact: false, hdr: 71, benchL: 326, railT: 86, railH: 60, stageT: 159, stageW: 750, stageH: 572, modT: 739, modH: 31, picT: 770, picH: 90, measT: 161, perfL: 1100 - 754, perfT: 58 },
  "1200x680": { label: "1200 × 680", w: 1200, h: 680, zoom: 1, compact: true, hdr: 45, benchL: 338, railT: 56, railH: 35, stageT: 99, stageW: 838, stageH: 467, modT: 569, modH: 31, picT: 600, picH: 80, measT: 121, perfL: 1200 - 754, perfT: 44 },
  "1100x680": { label: "1100 × 680", w: 1100, h: 680, zoom: 1, compact: true, hdr: 45, benchL: 326, railT: 56, railH: 35, stageT: 99, stageW: 750, stageH: 467, modT: 569, modH: 31, picT: 600, picH: 80, measT: 121, perfL: 1100 - 754, perfT: 44 },
  "960x600": { label: "960 × 600 at 90%", w: 1067, h: 667, zoom: 0.9, compact: true, hdr: 44, benchL: 326, railT: 56, railH: 35, stageT: 98, stageW: 717, stageH: 453, modT: 555, modH: 32, picT: 587, picH: 80, measT: 41, perfL: 1067 - 724, perfT: 44 },
};
const ORDER = ["1660x1050", "1400x900", "1100x860", "1200x680", "1100x680", "960x600"];

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");

/* A reading: the page's own, recorded value by value where the page writes one (data.js), else
   the formatter a mockup gives. */
const FMT = {};
function reading(id, v) {
  if (FMT[id]) return FMT[id](+v);
  const t = D.readings[id];
  if (!t) return String(v);
  let best = t[0];
  for (const r of t) if (Math.abs(r[0] - v) < Math.abs(best[0] - v)) best = r;
  return best[1];
}

/* A range input with the page's attributes, under a knob face. */
function rangeInput(id, extra) {
  const a = ATTR[id] || {};
  return '<input type="range" class="sr" id="' + id + '" min="' + a.min + '" max="' + a.max + '"' + (a.step ? ' step="' + a.step + '"' : "") + ' value="' + a.value + '" tabindex="-1"' + (extra || "") + ">";
}
function knob(id, name, o) {
  o = o || {};
  return '<div class="kcell' + (o.host ? " host" : "") + '" data-knob="' + id + '" data-say="' + id + '"' + (o.bip ? ' data-bip="1"' : "") + ">"
    + '<span class="reading" id="' + id + 'Value"></span>'
    + '<span class="knob-face" tabindex="0" role="slider" aria-label="' + esc(name) + '"><span class="knob-cap"></span></span>'
    + '<span class="nm">' + esc(name) + "</span>" + rangeInput(id) + "</div>";
}
/* A switch: buttons with the page's ids, one pressed. */
function sw(group, items, o) {
  o = o || {};
  return '<span class="switch caps' + (o.mini ? " mini" : "") + '" role="radiogroup" data-group="' + group + '"' + (o.label ? ' aria-label="' + esc(o.label) + '"' : "") + ">"
    + items.map((it, i) => '<button type="button" id="' + it[0] + '" role="radio" data-say="' + it[0] + '" aria-checked="' + (o.on === undefined ? i === 0 : o.on === i) + '">' + it[1] + "</button>").join("") + "</span>";
}
/* A checkbox drawn as a switch: the input keeps its id and type. */
function tog(id, label, o) {
  o = o || {};
  const a = ATTR[id] || {};
  return '<label class="tog' + (o.cls ? " " + o.cls : "") + '" data-say="' + id + '"><input type="checkbox" id="' + id + '"' + (a.value ? " checked" : "") + '><span class="lamp"></span>' + label + (o.speakers ? '<span class="speakers">speakers</span>' : "") + "</label>";
}
function select(id, o) {
  o = o || {};
  const a = ATTR[id] || {};
  const opts = (o.options || a.options || []).map((x) => '<option value="' + esc(x[0]) + '"' + (x[2] ? ' title="' + esc(x[2]) + '"' : "") + (String(x[0]) === String(a.value) ? " selected" : "") + ">" + esc(x[1]) + "</option>").join("");
  return '<select id="' + id + '" data-say="' + id + '"' + (o.label ? ' aria-labelledby="' + id + 'Label"' : "") + (o.style ? ' style="' + o.style + '"' : "") + ">" + opts + "</select>";
}
const fld = (id, label, control, o) => '<div class="fld' + ((o && o.cls) ? " " + o.cls : "") + '"' + ((o && o.box) ? ' data-box="' + o.box + '"' : "") + '><span class="fl" id="' + id + 'Label">' + label + "</span>" + control + "</div>";

function setFace(cell) {
  const input = cell.querySelector("input"), face = cell.querySelector(".knob-face");
  const lo = +input.min, hi = +input.max, fr = (input.value - lo) / (hi - lo), a = clamp(fr, 0, 1) * 270;
  const bip = cell.dataset.bip === "1";
  face.style.setProperty("--angle", a + "deg");
  face.style.setProperty("--lo", (bip ? Math.min(135, a) : 0) + "deg");
  face.style.setProperty("--hi", (bip ? Math.max(135, a) : a) + "deg");
  face.setAttribute("aria-valuetext", reading(input.id, input.value));
  cell.querySelector(".reading").textContent = reading(input.id, input.value);
}
function setValue(id, v, quiet) {
  const input = document.getElementById(id);
  input.value = v;
  const cell = input.closest(".kcell");
  if (cell) setFace(cell);
  if (!quiet) input.dispatchEvent(new Event("input", { bubbles: true }));
}

/* Wire a root: knobs turn by a vertical drag, the wheel or the arrow keys (the input is the
   value and hears an input event); switches press one button; double-click resets. */
function bind(root, onChange) {
  for (const cell of root.querySelectorAll(".kcell")) {
    const input = cell.querySelector("input"), face = cell.querySelector(".knob-face");
    const start = input.value, span = +input.max - +input.min, step = +input.step || 1;
    setFace(cell);
    const nudge = (d) => setValue(input.id, clamp(Math.round((+input.value + d) / step) * step, +input.min, +input.max));
    face.addEventListener("pointerdown", (e) => {
      e.preventDefault(); face.setPointerCapture(e.pointerId); face.classList.add("held");
      const y0 = e.clientY, v0 = +input.value;
      const move = (ev) => setValue(input.id, clamp(Math.round((v0 + (y0 - ev.clientY) / 150 * span) / step) * step, +input.min, +input.max));
      const up = () => { face.classList.remove("held"); face.removeEventListener("pointermove", move); face.removeEventListener("pointerup", up); };
      face.addEventListener("pointermove", move); face.addEventListener("pointerup", up);
    });
    face.addEventListener("wheel", (e) => { e.preventDefault(); nudge((e.deltaY < 0 ? 1 : -1) * Math.max(step, span / 100)); }, { passive: false });
    face.addEventListener("keydown", (e) => {
      const big = e.shiftKey ? 10 : 1;
      if (e.key === "ArrowUp" || e.key === "ArrowRight") { e.preventDefault(); nudge(big * Math.max(step, span / 100)); }
      if (e.key === "ArrowDown" || e.key === "ArrowLeft") { e.preventDefault(); nudge(-big * Math.max(step, span / 100)); }
    });
    face.addEventListener("dblclick", () => setValue(input.id, start));
    input.addEventListener("input", () => { setFace(cell); onChange && onChange(input.id); });
  }
  for (const g of root.querySelectorAll(".switch[data-group]")) {
    g.addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b) return;
      for (const x of g.querySelectorAll("button")) x.setAttribute("aria-checked", String(x === b));
      onChange && onChange(b.id);
    });
  }
  for (const i of root.querySelectorAll(".tog input, select")) i.addEventListener("change", () => onChange && onChange(i.id));
}
const pressed = (group) => { const b = document.querySelector('.switch[data-group="' + group + '"] [aria-checked="true"]'); return b ? b.id : null; };
const press = (id) => { const b = document.getElementById(id); for (const x of b.parentNode.querySelectorAll("button")) x.setAttribute("aria-checked", String(x === b)); };

/* ---- the info line: the control under the pointer or the focus, its name, its value and its
   whole line, which the strip has room for at every window (the second mockup's check). ---- */
let saying = null;
function say(id) {
  const w = D.words[id] || (window.EXTRA_WORDS || {})[id];
  if (!w) return;
  saying = id;
  const v = document.getElementById(id + "Value");
  const sel = document.getElementById(id);
  let value = v ? v.textContent : "";
  if (!value && sel && sel.tagName === "SELECT") value = sel.options[sel.selectedIndex].text;
  if (!value && sel && sel.type === "checkbox") value = sel.checked ? "on" : "off";
  document.getElementById("infoName").textContent = (window.SAY_NAMES || {})[id] || w[0];
  document.getElementById("infoValue").textContent = value;
  document.getElementById("infoHost").hidden = !(window.HOST_IDS || []).includes(id);
  document.getElementById("infoText").textContent = w[1];
}
function sayFrom(e) { const t = e.target.closest && e.target.closest("[data-say]"); if (t) say(t.dataset.say); }

/* ---- the window ---- */
function picStrip() {
  const reads = [["Glow", 0.62], ["Motion", 0.18], ["Memory", 0.41]];
  return '<section class="pic" id="pictureBar" aria-label="The Picture">'
    + '<div class="pic-name"><b>Picture</b><button type="button" class="link-btn caps" id="pictureMore" data-say="pictureMore">Advanced</button></div>'
    + '<div class="pic-knobs">' + knob("pictureAmount", "Amount", { host: true }) + knob("oscScan", "Scan", { host: true }) + knob("scanStrike", "Strike", { host: true })
    + knob("scanSoft", "Softness", { host: true }) + knob("scanMemory", "Persistence", { host: true }) + knob("output", "Output", { host: true }) + knob("stereoWidth", "Width", { host: true }) + "</div>"
    + '<div class="pic-width" data-box="widthTo"><span class="fl" id="widthToLabel">Width is</span>' + sw("widthTo", [["widthHeard", "Only heard"], ["widthDrawn", "Drawn too"]], { label: "Width is" }) + "</div>"
    + '<span class="level-meter" id="levelMeter" role="img" aria-label="Output level"><i style="height:58%"></i></span>'
    + '<div class="info" id="infoLine" aria-live="polite"><div class="info-top"><span class="info-name" id="infoName">Picture</span><span class="info-value" id="infoValue"></span><span class="info-host" id="infoHost" hidden></span>'
    + '<button type="button" class="link-btn caps info-more" id="infoMore" title="The card: what it is, what is moving it, the controls either side. Right-click a control for its menu.">More</button></div>'
    + '<div class="info-text" id="infoText">Point at a control and this says what it does.</div></div>'
    + '<div class="reads" id="pictureReads" role="img" aria-label="The picture’s three reads">'
    + reads.map((r) => '<span class="rn">' + r[0] + '</span><span class="rb"><i style="width:' + Math.round(r[1] * 100) + '%"></i></span><span class="rv">' + Math.round(r[1] * 100) + "%</span>").join("") + "</div></section>";
}
function frame(o) {
  const z = SIZES[o.size], scrW = z.benchL - 23, chips = z.modH < 40;
  const side = Math.max(120, Math.min(scrW - 46, z.modT - z.hdr - (z.compact ? 100 : 140)));
  return '<header class="hdr" style="height:' + z.hdr + 'px"><div class="title">OSCILLOSCOPE<small>220 Hz, unison just</small></div>'
    + '<div class="preset"><span class="caps">New</span><b>Plain sine</b></div><span class="link-btn caps">Save</span><span class="spacer"></span>'
    + '<span class="run caps">Running</span><span class="link-btn caps" id="performButton" aria-expanded="' + (o.open === "perform") + '">Perform</span><span class="link-btn caps">Settings</span></header>'
    + '<section class="scr" style="top:' + z.hdr + 'px;width:' + scrW + 'px;height:' + (z.modT - z.hdr) + 'px"><div class="tools">'
    + '<span class="switch caps"><button type="button" aria-pressed="true">Y–T</button><button type="button">X–Y</button><button type="button">Spect</button><button type="button">Paint</button></span>'
    + '<span class="link-btn caps">Clear</span><span class="link-btn caps" id="measureButton" aria-expanded="' + (o.open === "measure") + '">Scope &amp; measure</span></div>'
    + '<div class="sheet" style="width:' + side + 'px;height:' + side + 'px"></div><div class="verdict-line">Trigger locked.<span>Y–T · 220 Hz</span></div></section>'
    + '<section class="bench" style="left:' + z.benchL + 'px;top:' + z.railT + 'px;width:' + z.stageW + 'px;height:' + (z.stageT + z.stageH - z.railT) + 'px">'
    + '<div class="tabs" style="height:' + z.railH + 'px"><div class="tab on"><b>Play</b><span>Poly · sine · 220 Hz</span></div><div class="tab"><b>Ink</b><span>Ratio 1:1</span></div><div class="tab"><b>Space &amp; Memory</b><span>Dry</span></div></div>'
    + '<div class="tab-body" style="top:' + (z.stageT - z.railT) + 'px">the tab, unchanged</div></section>'
    + '<div class="modrow' + (chips ? " chips" : "") + '" style="top:' + z.modT + 'px;height:' + z.modH + 'px"><div class="lead">Modulation<small>Drag onto a knob.</small></div>'
    + ["LFO 1", "LFO 2", "Envelope", "Photocell"].map((n) => '<div class="mcard">' + n + "</div>").join("") + "</div>"
    + picStrip().replace('class="pic"', 'class="pic" style="top:' + z.picT + "px;height:" + z.picH + 'px"')
    + (o.overlay || "");
}

/* The stage: the window at its own size, scaled to the column (or ?scale=1 for the checks). */
function stage(wrap, size, html) {
  const z = SIZES[size];
  wrap.innerHTML = '<div class="stage" id="stage"><div class="win' + (z.compact ? " compact" : "") + '" id="win" style="width:' + z.w + "px;height:" + z.h + 'px">' + html + "</div></div>";
  const fit = () => {
    const q = new URLSearchParams(location.search).get("scale");
    document.body.classList.toggle("full", !!q);
    const s = q ? +q : Math.min(1, wrap.clientWidth / (z.w + 2));
    document.getElementById("stage").style.transform = "scale(" + s + ")";
    wrap.style.height = Math.ceil((z.h + 2) * s) + "px";
  };
  fit(); window.addEventListener("resize", fit);
  const win = document.getElementById("win");
  win.addEventListener("pointerover", sayFrom); win.addEventListener("focusin", sayFrom);
  return win;
}

/* Boxes, for the checks: every element named by an id or a data-box, relative to the window. */
function boxes(root) {
  const win = document.getElementById("win").getBoundingClientRect();
  const s = win.width / document.getElementById("win").offsetWidth;
  const out = {};
  for (const e of root.querySelectorAll("[id],[data-box]")) {
    if (e.closest(".sr") || e.classList.contains("sr")) continue;
    const r = e.getBoundingClientRect();
    if (!r.width && !r.height) continue;
    out[e.id || e.dataset.box] = [(r.left - win.left) / s, (r.top - win.top) / s, r.width / s, r.height / s].map((x) => Math.round(x * 2) / 2);
  }
  return out;
}
/* Every piece of text inside its box: nothing wraps that is meant to be one line, nothing cut. */
function overflows(root) {
  const bad = [];
  for (const e of root.querySelectorAll(".fl, .nm, .reading, .sec, .tog, .ftab b, .ftab span, .switch button, .p-name, .link-btn, .clock-line, .rn, .rv, .info-name, .info-value")) {
    if (!e.offsetParent) continue;
    if (e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflow !== "visible") bad.push((e.id || e.className) + " cut");
    const lh = parseFloat(getComputedStyle(e).lineHeight) || 16;
    if (e.getClientRects().length > 1 || e.getBoundingClientRect().height > lh * 1.6 + 8) bad.push((e.id || e.className || e.tagName) + " wraps: " + e.textContent.trim().slice(0, 40));
  }
  return bad;
}
const inside = (inner, outer, slack) => { slack = slack || 0.5; return inner[0] >= outer[0] - slack && inner[1] >= outer[1] - slack && inner[0] + inner[2] <= outer[0] + outer[2] + slack && inner[1] + inner[3] <= outer[1] + outer[3] + slack; };

window.UI = { D, ATTR, SIZES, ORDER, FMT, reading, knob, sw, tog, select, fld, bind, setValue, setFace, pressed, press, say, frame, stage, boxes, overflows, inside, clamp, esc, get saying() { return saying; } };
})();
