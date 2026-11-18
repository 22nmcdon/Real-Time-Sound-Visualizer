"""Play's boxes and fit, measured the same way by every suite that holds them
(18 Nov, web/docs/play-figures.md): msegtest.py's figures, fittest.py's six
windows, striptest.py's band and patchtest.py's nothing-moves.

Everything is in the page's own pixels (a rectangle over `pageZoom`), so the
plugin's 960x600 at Auto's 90 per cent reads as the 1067x667 the spec
measured. Measure in the brand's webfonts (webfonts.route before the page
loads): a fallback face moved every width by a pixel or two in the mockup.
"""

# The five windows fittest.py uses and the mockup's sixth, the largest.
SIZES = [(1660, 1050), (1400, 900), (1100, 860), (1200, 680), (1100, 680), (960, 600)]

# Every box on Play that a choice must not move: the band and its strip, line, modes and heading; the
# settings row, each field and its control; the figure area, its bar and each subtab; and in the view
# shown, its header's tools and pill, each drawing and pane, and every knob cell. The view's own boxes
# are keyed "view:..." so a switch of subtab can be judged on everything outside the view.
BOXES = """() => {
  const z = pageZoom || 1;
  const out = {};
  const put = (k, n) => { if (!n || !n.getClientRects().length) return; const r = n.getBoundingClientRect(); out[k] = [r.left / z, r.top / z, r.width / z, r.height / z]; };
  put('band', document.querySelector('.bench-band'));
  put('band:title', el.midiGroup.querySelector(':scope > .menu-title'));
  put('band:twoHands', el.midiTwoHands);
  put('band:modes', el.midiDyad.parentElement);
  put('band:strip', el.midiStrip);
  put('band:box', el.midiStrip.closest('.kb-box'));
  put('band:line', el.midiStrip.closest('.kb-right').querySelector('.kb-line'));
  put('set', document.querySelector('.play-set'));
  for (const g of [el.expressionGroup, el.toneRows]) {
    put('set:' + g.id + ':title', g.querySelector(':scope > .menu-title'));
    for (const row of g.querySelectorAll(':scope > .menu-row')) {
      const c = row.querySelector('select, input');
      if (!c) continue;
      put('set:field:' + c.id, row);
      put('set:control:' + c.id, row.querySelector('select, .knob-face'));
    }
  }
  put('figs', document.querySelector('.play-figs'));
  if (figs.bar) { put('figs:bar', figs.bar); for (const t of figs.bar.children) put('figs:tab:' + t.dataset.sub, t); }
  const view = document.querySelector('.fig-views > .fig-view:not([hidden])');
  if (view) {
    put('view', view);
    view.querySelectorAll('.fig-tools > *, .fig-tools .switch > button, :scope > .menu-title > *, .fig-plot, .fig-pane, .fig-sub, .fig-sub > *, .fig-foot, .wave-band')
      .forEach((n, i) => put('view:' + view.id + ':' + (n.id || (n.dataset.type !== undefined ? 'type' + n.dataset.type : n.className.split(' ')[0] + i)), n));
    for (const input of view.querySelectorAll('.mseg-knobs .knob-row input')) put('view:knob:' + input.id, input.closest('.knob-row'));
  }
  return out;
}"""

# What the fit is judged on, for the view shown (and the Envelope's editor while it is open).
MEASURE = """() => {
  const z = pageZoom || 1, R = (n) => n.getBoundingClientRect();
  const body = el.benchBody, band = document.querySelector('.bench-band'), set = document.querySelector('.play-set'), area = document.querySelector('.play-figs');
  const view = document.querySelector('.fig-views > .fig-view:not([hidden])');
  const shown = (n) => n && n.getClientRects().length;
  const tops = (nodes) => new Set([...nodes].filter(shown).map((n) => Math.round(R(n).top / z))).size;
  const knobRows = view ? [...view.querySelectorAll('.mseg-knobs')].filter(shown).map((k) => tops(k.querySelectorAll('.knob-row'))) : [];
  const setRows = [el.expressionGroup, el.toneRows].map((g) => tops(g.querySelectorAll(':scope > .menu-row:not([data-more])')));
  const plotOf = (n, what) => { const r = R(n); return { what, w: Math.round(r.width / z), h: Math.round(r.height / z), aspect: r.width / Math.max(1, r.height) }; };
  const plots = !view ? [] : view === el.ampEnvGroup ? [plotOf(el.ampPlot, 'amp')]
    : view === el.vcfGroup ? [plotOf(el.vcfResp, 'response'), plotOf(el.fenvPlot, 'fenv')] : [plotOf(el.cycleCanvas, 'wave')];
  // How far anything in the view runs past it, its drawing included.
  const viewOver = !view ? 0 : Math.max(0, ...[...view.querySelectorAll('*')].filter((n) => shown(n) && !n.closest('svg')).map((n) => (R(n).bottom - R(view).bottom) / z));
  const mod = el.modRow, pic = el.pictureBar;
  const bottom = Math.max(R(body).bottom, R(area).bottom);
  const labels = {};
  if (figs.bar) for (const t of figs.bar.children) {
    const s = t.querySelector('.fig-sum');
    labels[t.dataset.sub] = { fits: s.scrollWidth <= s.clientWidth + 0.5, form: Number(t.dataset.form || 0), text: s.textContent };
  }
  // Each settings menu's widest value in its own font, against its width less 20 px for the arrow.
  const g = document.createElement('canvas').getContext('2d');
  const menus = SHORT_MENUS.map((id) => document.getElementById(id)).filter((m) => m && m.closest('.play-set')).map((m) => {
    const cs = getComputedStyle(m); g.font = cs.fontWeight + ' ' + cs.fontSize + ' ' + cs.fontFamily;
    const room = R(m).width / z - 20;
    const shortW = [...m.options].map((o) => [g.measureText(o.textContent).width, o.textContent]);
    const fullW = [...m.options].map((o) => g.measureText(o.title || o.textContent).width);
    const widest = shortW.reduce((a, b) => (b[0] > a[0] ? b : a));
    return { menu: m.id, room, widest: widest[0], text: widest[1], fits: widest[0] <= room, fullFits: Math.max(...fullW) <= room };
  });
  const ed = el.modEditor, editor = ed.hidden ? null : {
    w: Math.round(R(ed).width / z), h: Math.round(R(ed).height / z),
    over: Math.max(ed.scrollHeight - ed.clientHeight, ...[...ed.querySelectorAll('.src-env *')].filter((n) => shown(n) && !n.closest('svg')).map((n) => (R(n).bottom - R(ed).bottom) / z)),
    covers: R(ed).bottom > R(mod).top + 1,
    plots: [plotOf(el.menvCurve, 'menv')],
    knobRows: [tops(el.menvControls.querySelectorAll('.src-knobs .knob-row'))],
  };
  return {
    scroll: body.scrollHeight - body.clientHeight, viewOver, knobRows, setRows, plots, labels, menus, editor,
    gapBandToSettings: (R(set).top - R(band).bottom) / z,
    between: [...body.children].indexOf(set) - [...body.children].indexOf(band) - 1,
    coversModrow: bottom > R(mod).top + 1, coversPicture: bottom > R(pic).top + 1,
    bandOver: el.midiGroup.scrollHeight - el.midiGroup.clientHeight,
    bandH: R(band).height / z, flay: el.vcfBody.classList.contains('stacked') ? 'stacked' : 'side',
  };
}"""


def judge(m):
    """Each of the fit's rules, as the spec states them."""
    return dict(
        nothing=m["gapBandToSettings"] <= 8.5 and m["between"] == 0,
        fit=m["scroll"] <= 1 and m["viewOver"] <= 1,
        clear=not m["coversModrow"] and not m["coversPicture"],
        one=all(r == 1 for r in m["knobRows"]) and all(r == 1 for r in m["setRows"]),
        wide=all(1.5 <= q["aspect"] <= 7 and q["h"] >= 120 and (q["what"] in ("response", "fenv") or q["aspect"] >= 2) for q in m["plots"]),
        fits=all(v["fits"] for v in m["labels"].values()),
    )


def same(a, b, keys=None):
    """Whether every box in both is where it was, to half a pixel: (ok, the first few moved, how many compared)."""
    ks = [k for k in a if k in b and (keys is None or keys(k))]
    moved = [(k, [round(x, 1) for x in a[k]], [round(x, 1) for x in b[k]]) for k in ks if any(abs(x - y) > 0.5 for x, y in zip(a[k], b[k]))]
    missing = [k for k in a if k not in b and (keys is None or keys(k))]
    return (not moved and not missing), moved[:2] + [("missing", k) for k in missing[:2]], len(ks)


def plots_said(m):
    return ", ".join("%s %dx%d %.1f:1" % (q["what"], q["w"], q["h"], q["aspect"]) for q in m["plots"])
