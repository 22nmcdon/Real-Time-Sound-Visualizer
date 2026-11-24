"""Write index.html: analysis.json, audio/index.json and the words in summary.html, in one file.

Everything the page shows is inlined - the data as JSON, the script, the styles -
so it opens from the disk as well as from the site, and asks nothing of the
network. The MP3s are beside it in audio/, by relative path.

    python3 web/docs/listening/sound-audit/page.py
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
A = json.load(open(os.path.join(HERE, "analysis.json")))
R = json.load(open(os.path.join(HERE, "results.json")))
AUDIO = json.load(open(os.path.join(HERE, "audio", "index.json"))) if os.path.exists(os.path.join(HERE, "audio", "index.json")) else []
SUMMARY = open(os.path.join(HERE, "summary.html")).read()

data = {
    "A": {k: A[k] for k in ("space", "names", "scale", "renders", "pca", "effects", "effectPca", "dead", "groups", "pairs",
                            "hypothesis", "darken", "gaps", "smooth", "null", "floor")},
    "features": R["features"], "validation": R["validation"], "leftOut": R["left_out"], "bases": R["bases"],
    "controls": [[c[0], c[1], c[2], c[3], c[4]] for c in R["controls"]], "audio": AUDIO,
}

PAGE = r"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Where the controls go</title>
<!-- The sound audit (24 Nov): every control that changes the sound swept across its
     range from four bases, rendered offline by the core and measured on the same
     features, to find which controls are the same move and which moves no control
     makes. render.py renders and measures, analyse.py finds the effects and groups,
     audio.py writes the MP3s, page.py writes this file with the data inlined.
     Nothing here changes the instrument. -->
<style>
  :root { --cream: #faf6f0; --paper: #fffcf7; --charcoal: #241f1d; --text: #3a332f; --text-soft: #6b615a;
          --line: #e4d9cc; --gold: #b08d57; --sage: #6f7f63; --rust: #a4553f; --slate: #4f6274;
          --hot: #c0573f; --cold: #4f7a94; --grid: #ece3d7;
          --g1: #a4553f; --g2: #b08d57; --g3: #6f7f63; --g4: #4f6274; --g5: #8a5a83; --g6: #3f7f7a;
          --g7: #c07f79; --g8: #7a6a3a; --g9: #5a5a5a; --g10: #9a6b3f; --g11: #3f5a9a; --g12: #7f3f5a; }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
          --cream: #1d1a18; --paper: #262220; --charcoal: #f3ece4; --text: #ddd4ca; --text-soft: #a99e93;
          --line: #3d3631; --grid: #332d29; --hot: #e07a5f; --cold: #7fb0cc;
          --g1: #e08a70; --g2: #d6b47a; --g3: #9fb38f; --g4: #8fa6bd; --g5: #c08ab8; --g6: #6fbdb5;
          --g7: #e0a39d; --g8: #c0ad70; --g9: #a8a8a8; --g10: #d39a66; --g11: #8fa6e0; --g12: #c07f9f; } }
  :root[data-theme="dark"] { --cream: #1d1a18; --paper: #262220; --charcoal: #f3ece4; --text: #ddd4ca; --text-soft: #a99e93;
          --line: #3d3631; --grid: #332d29; --hot: #e07a5f; --cold: #7fb0cc;
          --g1: #e08a70; --g2: #d6b47a; --g3: #9fb38f; --g4: #8fa6bd; --g5: #c08ab8; --g6: #6fbdb5;
          --g7: #e0a39d; --g8: #c0ad70; --g9: #a8a8a8; --g10: #d39a66; --g11: #8fa6e0; --g12: #c07f9f; }
  * { box-sizing: border-box; }
  body { background: var(--cream); color: var(--text); font: 16px/1.55 system-ui, sans-serif; margin: 0; padding: 24px 16px 64px; }
  main { max-width: 1060px; margin: 0 auto; }
  h1 { color: var(--charcoal); font-size: 1.7rem; margin: 0 0 4px; }
  h2 { color: var(--charcoal); font-size: 1.2rem; margin: 36px 0 8px; border-top: 1px solid var(--line); padding-top: 20px; }
  h3 { color: var(--charcoal); font-size: 1rem; margin: 18px 0 6px; }
  p { margin: 8px 0; max-width: 78ch; }
  .soft { color: var(--text-soft); }
  .tag { font-size: 0.72rem; letter-spacing: 0.07em; text-transform: uppercase; font-weight: 600; }
  .numbers { color: var(--slate); } .judgement { color: var(--rust); }
  .box { background: var(--paper); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; margin: 12px 0; }
  .box.numbers-box { border-left: 4px solid var(--slate); } .box.judgement-box { border-left: 4px solid var(--rust); }
  .box ul { margin: 6px 0; padding-left: 20px; } .box li { margin: 5px 0; }
  table { border-collapse: collapse; width: 100%; background: var(--paper); font-size: 0.88rem; }
  th, td { padding: 5px 8px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
  th { color: var(--charcoal); font-weight: 600; }
  td.n { font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }
  .scroll { overflow-x: auto; border: 1px solid var(--line); border-radius: 10px; }
  .controls { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; margin: 8px 0; font-size: 0.9rem; }
  .controls label { display: inline-flex; gap: 4px; align-items: center; }
  select, button { font: inherit; color: var(--text); background: var(--paper); border: 1px solid var(--line); border-radius: 6px; padding: 3px 8px; }
  button[aria-pressed="true"] { background: var(--charcoal); color: var(--cream); }
  .map { position: relative; background: var(--paper); border: 1px solid var(--line); border-radius: 10px; }
  .map svg { display: block; width: 100%; height: auto; }
  .tip { position: absolute; pointer-events: none; background: var(--charcoal); color: var(--cream); font-size: 0.8rem;
         padding: 4px 8px; border-radius: 6px; white-space: nowrap; display: none; z-index: 2; }
  .legend { display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 0.82rem; margin: 6px 0; }
  .legend span { display: inline-flex; align-items: center; gap: 5px; cursor: pointer; user-select: none; }
  .legend span.off { opacity: 0.35; }
  .legend i { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
  .cell { text-align: center; font-variant-numeric: tabular-nums; }
  .groups { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 10px; }
  .groups .box { margin: 0; }
  .chip { display: inline-block; border: 1px solid var(--line); border-radius: 999px; padding: 0 8px; margin: 2px 3px 2px 0; font-size: 0.82rem; }
  .sets { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }
  .sets .box { margin: 0; }
  audio { width: 100%; height: 32px; }
  .clip { margin: 6px 0; } .clip div { font-size: 0.85rem; font-weight: 600; color: var(--charcoal); }
  code { font-size: 0.88em; }
  details summary { cursor: pointer; color: var(--charcoal); font-weight: 600; }
</style>
</head>
<body>
<main>
<h1>Where the controls go</h1>
<p class="soft">24 Nov. A measurement study for the question "do many of these controls do the same thing?" Every
  control that changes the sound, swept across its range one at a time from four starting sounds, rendered through
  the instrument's core offline and measured on the same features. Nothing in the instrument was changed to make it.
  <span class="tag numbers">Numbers</span> marks what was measured, <span class="tag judgement">Judgement</span>
  what is my reading of it.</p>

__SUMMARY__

<h2 id="map">The map</h2>
<p>Two pictures of the same data. <b>The sound space</b> puts every render at a point, the features squashed to two
  dimensions (a principal-component projection: it keeps <span id="pcaKept"></span> of the spread, so two points close
  here can still differ on what it drops - the tables below are in the full space). Each control is a line from where
  the starting sound has it to the far end of its range. <b>The effect map</b> puts each control at a point by the
  direction it moves the sound, whatever its size: controls that are the same move land on top of each other.</p>
<div class="controls">
  <span role="group" aria-label="Which map"><button type="button" id="viewSpace" aria-pressed="true">The sound space</button>
  <button type="button" id="viewEffect" aria-pressed="false">The effect map</button></span>
  <label>From <select id="base"></select></label>
  <label><input type="checkbox" id="showPresets" checked> presets</label>
  <label>Highlight <select id="hl"><option value="">nothing</option></select></label>
</div>
<div class="legend" id="legend"></div>
<div class="map" id="mapBox"><svg id="map" viewBox="0 0 1000 640" role="img" aria-label="The map"></svg><div class="tip" id="tip"></div></div>
<p class="soft" id="axes"></p>

<h2 id="hyp">The hypothesis, tested</h2>
<p>The brief's suspects: Drive, Fold, Bits, Rate, the Plane's Snap, Scan, the Picture amount and Swell. Each cell is
  the similarity of two controls' directions (the cosine, 1 the same move, 0 unrelated, -1 opposite), averaged over the
  starting sounds where both do something measurable; blank where they never act from the same one.</p>
<div class="scroll"><table id="hypTable"></table></div>
<p id="hypWhere"></p>

<h2 id="groups">Overlap groups</h2>
<p>Controls clustered by direction (average linkage, every pair in a group at least 0.8 alike on average, and acting
  from a common starting sound). The number is the mean similarity within. A group says the controls move the
  features the same way; it does not say they sound the same - the pairs below have where they part.</p>
<div class="groups" id="groupList"></div>
<h3>Near-duplicates across sections</h3>
<p>Pairs of different controls at 0.85 or more, with how far each reaches (in the space's units; a unit is about
  one standard deviation of what the whole instrument does on that feature). Sorted by similarity.</p>
<div class="controls"><label>Show <select id="pairFilter"><option value="all">every pair</option>
  <option value="cross">only pairs from different sections</option></select></label></div>
<div class="scroll" style="max-height: 460px; overflow-y: auto"><table id="pairTable"></table></div>

<h2 id="gaps">Directions, and which controls reach them</h2>
<p>For each direction a sound could go, the controls whose move points most nearly that way (cosine of the move
  against the direction) and how far along it they get. A direction whose best cosine is low is a gap: nothing on
  the instrument goes there on its own.</p>
<div class="scroll"><table id="gapTable"></table></div>
<h3>What takes brightness away</h3>
<p>Every control that lowers the spectral centroid by at least a fifth of an octave at the far end of its range from
  some starting sound.</p>
<div id="darkList"></div>

<h2 id="smooth">A smooth Scan</h2>
<p>Scan reads the picture's 64 by 64 grid of cells round a circle, bilinear between cell centres, and turns it into a
  table of 64 harmonics sixty times a second. Four prototypes, in the render harness only: <b>interp</b> reads the
  grid bicubic, so the read has no corners where it crosses a cell's edge; <b>taper</b> rolls the 64 harmonics off
  (a tenth by the 32nd); <b>time</b> averages each read with the last, so the table does not jump a frame's change
  at once; <b>smooth</b> is all three. Scan swept 0 to 100 from each starting sound under each.</p>
<div class="scroll"><table id="smoothTable"></table></div>

<h2 id="listen">Listen</h2>
<p>Each set is the six-note phrase the measures use, matched in loudness within the set so the louder is not heard
  as the better. 64 kbps MP3.</p>
<div class="sets" id="sets"></div>

<h2 id="method">How it was measured</h2>
<h3>The starting sounds</h3>
<div id="bases"></div>
<h3>The features</h3>
<div class="scroll"><table id="featTable"></table></div>
<h3>The aliasing measure, against sounds whose answer is known</h3>
<p>A bitcrusher's steps make partials that are not the note's harmonics, but so does an FM bell, on purpose. Told
  apart by holding the note twice, on A3 and a fourth up: a partial the sound is made of follows the note (an FM
  bell's 1.4 is 1.4 times either), one folded back by a sample rate - the host's, or a hold's own - does not. These
  were made in numpy and measured as every render is.</p>
<div class="scroll"><table id="valTable"></table></div>
<p class="soft">Known limits. Where a sound has many partials that do not follow the note, a few land near each other
  in the second note by chance and are counted as following: the bitcrushers' Inharmonicity of -24 to -33 dB above is
  that, not a bell. And a sound that moves while held (the Slow pad) smears its harmonics into the floor between them,
  so it reads as noisier than a still one.</p>
<h3>The null</h3>
<p>The loop is chaotic: where in its state a note lands changes how it goes on. So the same sound with the key a
  millisecond or twenty later is rendered from each base as if it were a control, and an effect counts only where it
  reaches more than twice that, and at least one unit. The null's reach from each base:
  <span id="nullText"></span>.</p>
<h3>Included and left out</h3>
<details><summary>Every control swept (<span id="nCtl"></span>)</summary><div class="scroll"><table id="ctlTable"></table></div></details>
<details><summary>Left out, and why</summary><div class="scroll"><table id="outTable"></table></div></details>
<details><summary>Controls that did nothing measurable from any starting sound</summary><p id="deadText"></p></details>
<p class="soft">Made by <code>render.py</code>, <code>analyse.py</code>, <code>audio.py</code> and <code>page.py</code> beside
  this file; <code>results.json</code> holds every render's features and <code>analysis.json</code> what this page shows.</p>
</main>
<script>
const D = __DATA__;
const A = D.A;
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;"}[c]));
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const GROUPS = [...new Set(D.controls.map((c) => c[1]))];
const gcol = (g) => "var(--g" + (GROUPS.indexOf(g) % 12 + 1) + ")";
const name = (k) => A.names[k] || k;
const effect = Object.fromEntries(A.effects.map((e) => [e.key, e]));
const label = (k) => effect[k] ? effect[k].label : k;
const fmt = (v, d = 2) => v == null ? "" : Number(v).toFixed(d);

// ---------------------------------------------------------------- the map
let view = "space", hidden = new Set();
const baseSel = $("base");
baseSel.innerHTML = Object.entries(D.bases).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("") + '<option value="all">all four</option>';
$("hl").innerHTML += A.effects.map((e) => `<option value="${e.key}">${esc(e.label)} (${esc(e.group)})</option>`).join("");
$("pcaKept").textContent = Math.round(100 * (A.pca.explained[0] + A.pca.explained[1])) + " per cent";
$("legend").innerHTML = GROUPS.map((g) => `<span data-g="${esc(g)}"><i style="background:${gcol(g)}"></i>${esc(g)}</span>`).join("");
$("legend").addEventListener("click", (ev) => {
  const s = ev.target.closest("span[data-g]"); if (!s) return;
  const g = s.dataset.g; hidden.has(g) ? hidden.delete(g) : hidden.add(g); s.classList.toggle("off"); draw();
});
for (const [id, v] of [["viewSpace", "space"], ["viewEffect", "effect"]]) $(id).addEventListener("click", () => {
  view = v; $("viewSpace").setAttribute("aria-pressed", v === "space"); $("viewEffect").setAttribute("aria-pressed", v === "effect"); draw();
});
for (const id of ["base", "showPresets", "hl"]) $(id).addEventListener("change", draw);

const W = 1000, H = 640, PAD = 40;
function scaler(pts) {
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const k = Math.min((W - 2 * PAD) / (x1 - x0 || 1), (H - 2 * PAD) / (y1 - y0 || 1));
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  return ([x, y]) => [W / 2 + (x - cx) * k, H / 2 - (y - cy) * k];
}
function loadWords(l) { return Object.entries(l).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, 4)
  .map(([k, v]) => (v > 0 ? "+" : "-") + name(k).toLowerCase()).join(", "); }

function draw() {
  const svg = $("map"), base = baseSel.value, hl = $("hl").value;
  let out = "";
  const grid = css("--grid"), soft = css("--text-soft");
  if (view === "space") {
    const rs = A.renders;
    const S = scaler(rs.map((r) => [r.x, r.y]));
    const [ox, oy] = S([0, 0]);
    out += `<line x1="0" x2="${W}" y1="${oy}" y2="${oy}" stroke="${grid}"/><line y1="0" y2="${H}" x1="${ox}" x2="${ox}" stroke="${grid}"/>`;
    const bases = base === "all" ? Object.keys(D.bases) : [base];
    const lines = [];
    for (const c of D.controls) {
      if (hidden.has(c[1]) || c[0] === "_land") continue;
      for (const b of bases) {
        const rr = rs.filter((r) => r.kind === "sweep" && r.base === b && r.control === c[0]);
        if (!rr.length) continue;
        const rest = rr.find((r) => JSON.stringify(r.value) === JSON.stringify(r.rest));
        const order = c[3].map((v) => JSON.stringify(v));
        const pts = rr.slice().sort((a, b) => order.indexOf(JSON.stringify(a.value)) - order.indexOf(JSON.stringify(b.value)));
        const on = hl && effect[hl] && effect[hl].id === c[0];
        lines.push({ c, b, pts, rest, on });
      }
    }
    lines.sort((a, b) => a.on - b.on);
    for (const { c, b, pts, rest, on } of lines) {
      const d = pts.map((r, i) => (i ? "L" : "M") + S([r.x, r.y]).map((v) => v.toFixed(1)).join(" ")).join("");
      const op = hl ? (on ? 1 : 0.12) : 0.75;
      out += `<path d="${d}" fill="none" stroke="${gcol(c[1])}" stroke-width="${on ? 3 : 1.4}" opacity="${op}" data-tip="${esc(c[2] + " - " + D.bases[b])}"/>`;
      const end = S([pts[pts.length - 1].x, pts[pts.length - 1].y]);
      out += `<circle cx="${end[0]}" cy="${end[1]}" r="${on ? 4 : 2.5}" fill="${gcol(c[1])}" opacity="${op}" data-tip="${esc(c[2] + " at " + pts[pts.length - 1].value + " - " + D.bases[b])}"/>`;
    }
    for (const b of bases) {
      const r = rs.find((r) => r.kind === "base" && r.base === b);
      const [x, y] = S([r.x, r.y]);
      out += `<rect x="${x - 6}" y="${y - 6}" width="12" height="12" fill="${css("--charcoal")}" data-tip="${esc("Start: " + D.bases[b])}"/>`;
      out += `<text x="${x + 9}" y="${y - 8}" font-size="13" fill="${css("--charcoal")}">${esc(D.bases[b])}</text>`;
    }
    if ($("showPresets").checked) for (const r of rs.filter((r) => r.kind === "preset")) {
      const [x, y] = S([r.x, r.y]);
      out += `<path d="M${x} ${y - 7}L${x + 7} ${y}L${x} ${y + 7}L${x - 7} ${y}Z" fill="none" stroke="${css("--gold")}" stroke-width="2" data-tip="${esc("Preset: " + r.name + " (" + r.section + ")")}"/>`;
    }
    $("axes").textContent = "Across: " + loadWords(A.pca.loadings[0]) + ". Up: " + loadWords(A.pca.loadings[1]) + ".";
  } else {
    const es = A.effects.filter((e) => !hidden.has(e.group) && (base === "all" || (e.bases[base] && e.bases[base].active)));
    const S = scaler(A.effects.map((e) => [e.x, e.y]));
    const [ox, oy] = S([0, 0]);
    out += `<line x1="0" x2="${W}" y1="${oy}" y2="${oy}" stroke="${grid}"/><line y1="0" y2="${H}" x1="${ox}" x2="${ox}" stroke="${grid}"/>`;
    for (const e of es) {
      const [x, y] = S([e.x, e.y]), on = hl === e.key;
      const grp = e.cluster == null ? "" : " - group " + (e.cluster + 1);
      out += `<circle cx="${x}" cy="${y}" r="${on ? 8 : 5}" fill="${gcol(e.group)}" opacity="${hl && !on ? 0.25 : 0.9}" data-tip="${esc(e.label + " (" + e.group + ")" + grp)}"/>`;
      if (on || (!hl && e.cluster != null && e.cluster < 6)) out += `<text x="${x + 7}" y="${y + 4}" font-size="11" fill="${soft}">${esc(e.label)}</text>`;
    }
    $("axes").textContent = "Across: " + loadWords(A.effectPca.loadings[0]) + ". Up: " + loadWords(A.effectPca.loadings[1]) +
      ". Each dot is a direction; its size on the map is not its size in sound.";
  }
  svg.innerHTML = out;
}
const tip = $("tip");
$("map").addEventListener("pointermove", (ev) => {
  const t = ev.target.getAttribute && ev.target.getAttribute("data-tip");
  if (!t) { tip.style.display = "none"; return; }
  const box = $("mapBox").getBoundingClientRect();
  tip.textContent = t; tip.style.display = "block";
  tip.style.left = Math.min(ev.clientX - box.left + 12, box.width - tip.offsetWidth - 4) + "px";
  tip.style.top = (ev.clientY - box.top + 12) + "px";
});
$("map").addEventListener("pointerleave", () => { tip.style.display = "none"; });
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", draw);
draw();

// ---------------------------------------------------------------- tables
function heat(v) {
  if (v == null) return "";
  const c = v >= 0 ? "--hot" : "--cold";
  return `background: color-mix(in srgb, var(${c}) ${Math.round(Math.abs(v) * 70)}%, transparent)`;
}
const hyp = A.hypothesis;
$("hypTable").innerHTML = "<tr><th></th>" + hyp.labels.map((l) => `<th class="cell">${esc(l)}</th>`).join("") + "</tr>" +
  hyp.matrix.map((row, i) => `<tr><th>${esc(hyp.labels[i])}</th>` + row.map((v, j) =>
    `<td class="cell" style="${i === j ? "" : heat(v)}">${i === j ? "" : fmt(v)}</td>`).join("") + "</tr>").join("");
$("hypWhere").innerHTML = "Where each goes, averaged over the starting sounds it acts from, its three largest moves in the space's units: " +
  hyp.keys.map((k) => `<b>${esc(label(k))}</b> ${effect[k].where.map(([f, v]) => (v > 0 ? "+" : "") + v + " " + name(f).toLowerCase()).join(", ")}`).join("; ") + ".";

$("groupList").innerHTML = A.groups.map((g, i) => `<div class="box"><div class="tag">Group ${i + 1} &middot; ${fmt(g.within)} alike</div>
  <div>${g.members.map((k) => `<span class="chip" style="border-color:${gcol(effect[k].group)}">${esc(effect[k].group)}: ${esc(effect[k].label)}</span>`).join("")}</div>
  <div class="soft" style="font-size:0.85rem">Moves: ${g.where.map(([f, v]) => (v > 0 ? "more " : "less ") + name(f).toLowerCase()).join(", ")}</div></div>`).join("");
function pairs() {
  const cross = $("pairFilter").value === "cross";
  const ps = A.pairs.filter((p) => !cross || p.ga !== p.gb);
  $("pairTable").innerHTML = "<tr><th>Similarity</th><th>One</th><th>The other</th><th>From</th><th class='n'>Reach</th></tr>" +
    ps.map((p) => `<tr><td class="n">${fmt(p.sim)}</td><td>${esc(p.ga)}: ${esc(p.la)}</td><td>${esc(p.gb)}: ${esc(p.lb)}</td>
      <td>${p.bases.map((b) => esc(b)).join(", ")}</td><td class="n">${fmt(p.reachA, 1)} / ${fmt(p.reachB, 1)}</td></tr>`).join("");
}
$("pairFilter").addEventListener("change", pairs); pairs();

$("gapTable").innerHTML = "<tr><th>Direction</th><th>Best cosine</th><th>The controls that point most nearly there (cosine, how far along, from)</th></tr>" +
  A.gaps.map((g) => `<tr><td><b>${esc(g.name)}</b></td><td class="n" style="${heat(g.best[0] ? g.best[0].cos : 0)}">${fmt(g.best[0] && g.best[0].cos)}</td>
    <td>${g.best.slice(0, 4).map((t) => `${esc(effect[t.key] ? effect[t.key].group + ": " : "")}${esc(t.label)} <span class="soft">(${fmt(t.cos)}, ${fmt(t.along, 1)}, ${esc(t.base)})</span>`).join("; ")}</td></tr>`).join("");
$("darkList").innerHTML = "<p>" + A.darken.map((d) => `<span class="chip">${esc(d.group)}: ${esc(d.label)} <b>${fmt(d.octaves)}</b> oct (${esc(d.base)})</span>`).join("") + "</p>";

const SV = Object.keys(A.smooth);
const sb = Object.keys(D.bases);
$("smoothTable").innerHTML = "<tr><th>Scan read</th>" + sb.map((b) => `<th colspan="4">${esc(D.bases[b])}</th>`).join("") + "</tr><tr><th></th>" +
  sb.map(() => "<th class='n'>like the crusher</th><th class='n'>aliasing at 100</th><th class='n'>brightness at 100</th><th class='n'>movement at 100</th>").join("") + "</tr>" +
  SV.map((v) => `<tr><th>${v === "core" ? "as it is" : esc(v)}</th>` + sb.map((b) => { const s = A.smooth[v][b];
    return `<td class="n">${fmt(s.cosToCrusher)}</td><td class="n">${fmt(s.at100.alias, 1)} dB</td><td class="n">${fmt(s.at100.bright)} oct</td><td class="n">${fmt(s.at100.move, 3)}</td>`; }).join("") + "</tr>").join("") +
  "<tr><th class='soft'>Scan at 0</th>" + sb.map((b) => { const s = A.smooth.core[b];
    return `<td></td><td class="n soft">${fmt(s.at0.alias, 1)} dB</td><td class="n soft">${fmt(s.at0.bright)} oct</td><td class="n soft">${fmt(s.at0.move, 3)}</td>`; }).join("") + "</tr>";

$("sets").innerHTML = D.audio.map((s) => `<div class="box"><h3 style="margin-top:0">${esc(s.title)}</h3><p class="soft" style="font-size:0.88rem">${esc(s.listen)}</p>` +
  s.clips.map((c) => `<div class="clip"><div>${esc(c.label)}</div><audio controls preload="none" src="${esc(c.file)}"></audio></div>`).join("") + "</div>").join("")
  || "<p class='soft'>No examples rendered.</p>";

$("bases").innerHTML = "<ul>" + Object.entries(D.bases).map(([k, v]) => `<li><b>${esc(v)}</b></li>`).join("") +
  "</ul><p>Each held A3 for three seconds and let go (and a fourth up, for the aliasing measure), and the phrase A3 C4 E4 D4 A4 E4 at varied velocities, a third of a second each, the last held. Splits in the bank play A2 under A4.</p>";
$("featTable").innerHTML = "<tr><th>Feature</th><th>How it is read</th><th class='n'>One unit</th></tr>" +
  D.features.map(([k, n, w]) => `<tr><td><b>${esc(n)}</b></td><td>${esc(w)}${A.space.includes(k) ? "" : " <span class='soft'>(reported, not in the space)</span>"}</td><td class="n">${A.scale[k] != null ? fmt(A.scale[k], A.scale[k] < 1 ? 3 : 1) : ""}</td></tr>`).join("");
$("valTable").innerHTML = "<tr><th>Known sound</th><th class='n'>Aliasing</th><th class='n'>Inharmonicity</th><th class='n'>Noisiness</th><th class='n'>Flatness</th><th class='n'>Brightness</th></tr>" +
  D.validation.map((v) => `<tr><td>${esc(v.name)}</td><td class="n">${fmt(v.alias, 1)}</td><td class="n">${fmt(v.inharm, 1)}</td><td class="n">${fmt(v.noise, 1)}</td><td class="n">${fmt(v.flat, 1)}</td><td class="n">${fmt(v.bright)}</td></tr>`).join("");
$("nullText").textContent = Object.entries(A.null).map(([b, v]) => D.bases[b] + " " + fmt(v) + " (floor " + fmt(A.floor[b]) + ")").join("; ");
$("nCtl").textContent = D.controls.length - 1;
$("ctlTable").innerHTML = "<tr><th>Section</th><th>Control</th><th>Places</th></tr>" +
  D.controls.filter((c) => c[0] !== "_land").map((c) => `<tr><td>${esc(c[1])}</td><td>${esc(c[2])} <code>${esc(c[0])}</code></td><td>${esc(c[3].join(", "))}</td></tr>`).join("");
$("outTable").innerHTML = "<tr><th>Fields</th><th>Why</th></tr>" + D.leftOut.map(([f, w]) => `<tr><td><code>${esc(f)}</code></td><td>${esc(w)}</td></tr>`).join("");
$("deadText").textContent = A.dead.map((e) => e.group + ": " + e.label).join("; ") + ".";
</script>
</body>
</html>
"""

html = PAGE.replace("__SUMMARY__", SUMMARY).replace("__DATA__", json.dumps(data, separators=(",", ":")).replace("</", "<\\/"))
open(os.path.join(HERE, "index.html"), "w").write(html)
print("index.html", len(html) // 1024, "KB")
