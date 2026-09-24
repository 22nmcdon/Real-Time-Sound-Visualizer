/* The survey that chose the sixth picture source: the loop closed across five
   kinds of picture, and for each candidate its own entropy less the most it
   shares with any one of the other five. Run by shapetest.py; kept as a file of
   its own so it can be run on its own when the question is asked again. */
async ([seconds]) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const frame = () => new Promise((r) => requestAnimationFrame(r));
  const preset = (name) => PRESETS.flatMap((g) => g[1]).find((p) => p[0] === name)[1];
  const route = (list) => {
    state.modRoutings = [];
    for (const [s, d, a] of list) { addRouting(s, d); const r = state.modRoutings.find((x) => x.sourceId === s && x.destId === d); if (r) r.amount = a; }
    touchRoutings();
  };
  const configs = [
    ["lag X-Y, roundness on the lag", () => { restore({ timebase: 3 }); el.lagOn.checked = true; el.lagOn.dispatchEvent(new Event('change')); setDisplay('xy'); },
      [["picture.round", "view.lag", 0.5], ["photo.1", "view.rotate", 0.5]]],
    ["equal fifth drifting", () => { restore(preset("Tumbling")); genSet('just', false); },
      [["photo.1", "view.zoom", 0.5], ["picture.cover", "view.rotate", 0.5]]],
    ["harmonograph running down", () => { restore(preset("Harmonograph")); },
      [["photo.1", "view.zoom", 0.5], ["picture.novelty", "view.rotate", 0.5]]],
    ["traced rose", () => { restore(preset("Rose")); },
      [["picture.novelty", "view.rotate", 0.5], ["picture.round", "view.zoom", 0.5]]],
    ["tumbling cube", () => { restore(preset("Tumbling cube")); },
      [["photo.1", "view.rotate", 0.5], ["picture.change", "view.zoom", 0.5]]],
  ];
  const rows = [];
  for (const [name, setup, routes] of configs) {
    setup();
    if (!photo.on) setPhoto(true);
    pictureMeter.reset();
    route(routes);
    await wait(800);
    const until = performance.now() + seconds * 1000;
    while (performance.now() < until) {
      await frame();
      rows.push([photo.raw, picture.raw.round, picture.raw.cover, picture.raw.change,
                 picture.raw.novelty, picture.raw.signed, picture.raw.edge, name]);
    }
    el.lagOn.checked = false; el.lagOn.dispatchEvent(new Event('change'));
  }
  state.modRoutings = []; touchRoutings();

  // Mutual information with fixed-width bins over each variable's own range.
  const BINS = 8;
  const binned = (k) => {
    const v = rows.map((r) => r[k]);
    const lo = Math.min(...v), hi = Math.max(...v);
    return v.map((x) => hi - lo < 1e-9 ? 0 : Math.min(BINS - 1, Math.floor((x - lo) / (hi - lo) * BINS)));
  };
  const H = (a) => { const c = new Map(); for (const x of a) c.set(x, (c.get(x) || 0) + 1);
    let h = 0; for (const n of c.values()) { const p = n / a.length; h -= p * Math.log2(p); } return h; };
  const I = (a, b) => H(a) + H(b) - H(a.map((x, i) => x * BINS + b[i]));
  const names = ["photo", "round", "cover", "change", "novelty", "signed", "edge"];
  const cols = names.map((_, k) => binned(k));
  const result = {};
  for (const cand of [5, 6]) {
    const shared = [0, 1, 2, 3, 4].map((j) => I(cols[cand], cols[j]));
    const most = Math.max(...shared);
    result[names[cand]] = { entropy: H(cols[cand]), shared: Object.fromEntries(shared.map((v, j) => [names[j], +v.toFixed(3)])),
                            adds: H(cols[cand]) - most, nonzero: rows.filter((r) => Math.abs(r[cand]) > 0.01).length / rows.length };
  }
  const perConfig = {};
  for (const r of rows) { const k = r[7]; perConfig[k] = perConfig[k] || { n: 0, signedAbs: 0, edge: 0 }; perConfig[k].n++; perConfig[k].signedAbs += Math.abs(r[5]); perConfig[k].edge += r[6]; }
  return { samples: rows.length, result, perConfig };
}
