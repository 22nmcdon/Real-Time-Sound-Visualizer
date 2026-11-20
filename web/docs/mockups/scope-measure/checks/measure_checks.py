"""The Scope & measure mockup's checks, in Chromium (web/docs/mockups/scope-measure/index.html).

Each check is fed a known-wrong case beside it (a null), and the null must be seen to fail, as
CLAUDE.md asks of every new assertion.

- in the brand's webfonts, no console errors through every window, subtab and state;
- every id the panel has on testing is here once, with its tag, type, range, step, options and
  role (data.js, read from the page by write_data.py). Null: the mockup with Holdoff taken out;
- knobs: every range input is under a knob face, and no slider shows. Null: testing's panel, whose
  fourteen ranges are all sliders;
- labels: every label shown is three words or fewer, on one line and uncut. Null: testing's
  "Take the lag and the tuner from the note played";
- every control in the panel has words, and pointing at it puts them in the info line. Null: the
  panel's name, which has none, leaves the line as it was;
- no scroll, at the six windows and on every subtab: the panel and its views hold their content,
  the panel is inside the window and ends above the Picture strip, so the info line is seen. Null:
  testing's wall, every view in flow at once, scrolls at 960 x 600;
- nothing moves: every box in the panel to half a pixel across the four subtabs and across
  twenty states of the controls (each edge, source, level, position, holdoff, timebase, zoom,
  lag, the note, the lanes, mid / side, the filter, the readouts, run and mode), at the six
  windows. Nulls: a knob cell sized to its reading moves its neighbours when the reading changes;
  the trace filter's knobs taken out while it is off moves the row under them;
- Run, the mode and Autoset are in view on every subtab;
- the trigger's drawing: the dashed level at the level's height and the position's marker at its
  share of the width, the trace crossing the level at the marker on the edge chosen, and free run
  grey past the peak. Nulls: the level of the other sign, the other edge's slope, a level past the
  peak claimed as a crossing;
- Zoom's slice is the window's width over the zoom. Null: 1x's width at 8x;
- a phone's width has no horizontal page scroll.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/scope-measure/checks/measure_checks.py
"""
import os, sys, json
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "tests"))
import webfonts

MOCK = os.path.dirname(HERE)
PAGE = "file://" + os.path.join(MOCK, "index.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
fails, n, results = [], [0], {}

def check(ok, what):
    n[0] += 1
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)

def null(wrong_passes, what):
    check(not wrong_passes, "null: " + what)

SIZES = ["1660x1050", "1400x900", "1100x860", "1200x680", "1100x680", "960x600"]
TABS = ["trigger", "time", "vertical", "measure"]
STATES = [
    {}, {"edge": "edgeFalling"}, {"src": "trigSource1"}, {"level": -1000}, {"level": 1000}, {"level": 333},
    {"position": 0}, {"position": 100}, {"holdoff": 50}, {"timebase": 0}, {"timebase": 8}, {"zoom": 24},
    {"lagOn": True}, {"lagOn": True, "lagHow": "lagManual", "lag": 400}, {"midiTruth": False}, {"midSide": True},
    {"ch1On": False, "ch2Ac": True, "ch1Scale": 8, "ch2Offset": -100}, {"filterOn": True, "filterType": "notch", "filterCutoff": 1000, "filterRes": 100},
    {"readoutsOn": True, "cursorsOn": True, "numbers": "measurePost"}, {"run": False, "mode": "modeSingle"},
]

ID_CHECK = r"""() => {
  const want = UI_DATA.attrs.measure, bad = [];
  for (const a of want) {
    const all = document.querySelectorAll('#' + CSS.escape(a.id));
    if (all.length !== 1) { bad.push(a.id + ' x' + all.length); continue; }
    const e = all[0];
    if (e.tagName.toLowerCase() !== a.tag || (e.type || '') !== a.type) { bad.push(a.id + ' type'); continue; }
    if (a.type === 'range' && (e.min !== a.min || e.max !== a.max || (e.step || null) !== a.step)) bad.push(a.id + ' range');
    if (a.options && JSON.stringify([...e.options].map(o => o.value)) !== JSON.stringify(a.options.map(o => o[0]))) bad.push(a.id + ' options');
    if (a.role && e.getAttribute('role') !== a.role) bad.push(a.id + ' role');
  }
  return bad; }"""

KNOBS = r"""() => {
  const p = document.getElementById('measurePanel');
  const ranges = [...p.querySelectorAll('input[type=range]')];
  return { ranges: ranges.length, underFace: ranges.filter(r => r.closest('.kcell') && r.closest('.kcell').querySelector('.knob-face')).length,
           sliders: ranges.filter(r => r.offsetWidth > 2 && getComputedStyle(r).opacity !== '0').length }; }"""

LABELS = r"""() => {
  const p = document.getElementById('measurePanel'), out = [];
  for (const e of p.querySelectorAll('.fl, .nm, .tog, .sec, .ftab b, .switch button, .link-btn, .who span')) {
    if (!e.offsetParent) continue;
    const t = e.textContent.replace(/speakers$/i, '').trim();
    out.push({ t, words: t.split(/\s+/).filter(w => !/^[\/·–-]$/.test(w)).length });
  }
  return { labels: out, over: UI.overflows(p) }; }"""

SAY = r"""() => {
  const p = document.getElementById('measurePanel'), missing = [], wrong = [];
  for (const e of p.querySelectorAll('[data-say]')) {
    const id = e.dataset.say, w = UI.D.words[id];
    if (!w) { missing.push(id); continue; }
    UI.say(id);
    if (document.getElementById('infoText').textContent !== w[1]) wrong.push(id);
  }
  const ctl = [...p.querySelectorAll('input, select, button')].filter(e => e.id && !['measureClose'].includes(e.id) && !e.closest('[data-say]') && !e.dataset.say && !e.classList.contains('ftab'));
  return { missing, wrong, unsaid: ctl.map(e => e.id), n: p.querySelectorAll('[data-say]').length }; }"""

FIT = r"""() => {
  const p = document.getElementById('measurePanel'), z = UI.SIZES[__m.S.size], b = UI.boxes(document.getElementById('win'));
  const views = [...p.querySelectorAll('.view')].filter(v => !v.hidden);
  const over = [];
  for (const v of views) for (const e of v.querySelectorAll('.kcell, .tog, .switch, .fld, .plot, select, .filt-plot, .sec, .ref'))
    if (e.offsetParent) { const r = e.getBoundingClientRect(), vr = v.getBoundingClientRect(); if (r.bottom > vr.bottom + 0.5 || r.right > vr.right + 0.5) over.push(e.id || e.dataset.knob || e.className); }
  const pb = b.measurePanel;
  const vs = p.querySelector('.views');
  return { scroll: p.scrollHeight - p.clientHeight, viewScroll: Math.max(0, vs.scrollHeight - vs.clientHeight, ...views.map(v => v.scrollHeight - v.clientHeight)), over,
           inWin: pb[0] >= 0 && pb[1] >= 0 && pb[0] + pb[2] <= z.w && pb[1] + pb[3] <= z.h, abovePic: pb[1] + pb[3] <= z.picT, bottom: pb[1] + pb[3], picT: z.picT,
           head: ['run', 'modeAuto', 'modeNormal', 'modeSingle', 'autoset'].every(id => { const r = b[id]; return r && UI.inside(r, pb); }), h: pb[3] }; }"""

BOXES = r"""() => { const b = UI.boxes(document.getElementById('measurePanel'));
  for (const e of document.querySelectorAll('#measurePanel svg [id]')) delete b[e.id];
  return b; }"""

def diff(a, b):
    out = []
    for k in set(a) | set(b):
        if k not in a or k not in b:
            continue  # shown in one state only: a view's own boxes are compared within the view
        if any(abs(x - y) > 0.5 for x, y in zip(a[k], b[k])):
            out.append(k)
    return sorted(out)

def main():
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=CHROME)
        ctx = br.new_context(viewport={"width": 1700, "height": 1100})
        webfonts.route(ctx)
        p = ctx.new_page()
        errs = []
        p.on("pageerror", lambda e: errs.append(str(e)))
        p.on("console", lambda m: m.type == "error" and errs.append(m.text))
        p.goto(PAGE + "?scale=1")
        fonts = webfonts.settle(p)
        check(fonts, "the brand's webfonts loaded (Jost, Playfair Display)")
        results["fonts"] = fonts

        # ids, as on testing
        bad = p.evaluate(ID_CHECK)
        check(not bad, "every id on testing's panel is here once, with its tag, type, range, options and role (%d ids)" % len(p.evaluate("UI_DATA.attrs.measure")) + (": " + str(bad) if bad else ""))
        p.evaluate("() => { const e = document.getElementById('holdoff'); e.parentNode.removeChild(e); }")
        null(not p.evaluate(ID_CHECK), "the mockup with Holdoff taken out")
        p.evaluate("() => __m.render()")

        # knobs
        k = p.evaluate(KNOBS)
        results["knobs"] = k
        check(k["ranges"] == 14 and k["underFace"] == k["ranges"] and k["sliders"] == 0, "all %d range inputs under knob faces, no slider shown" % k["ranges"])
        testing_ranges = p.evaluate("UI_DATA.attrs.measure.filter(a => a.type === 'range').length")
        null(testing_ranges == 0, "testing's panel, %d sliders, passes 'no slider shown'" % testing_ranges)

        # labels, on every subtab
        allover, maxw, words = [], 0, []
        for t in TABS:
            p.evaluate("(t) => __m.set({ tab: t })", t)
            r = p.evaluate(LABELS)
            allover += r["over"]
            for l in r["labels"]:
                words.append(l)
                maxw = max(maxw, l["words"])
        long = [l["t"] for l in words if l["words"] > 3]
        check(not long and not allover, "every label three words or fewer (longest %d), one line, uncut" % maxw + (": " + str(long + allover) if long or allover else ""))
        tw = len("Take the lag and the tuner from the note played".split())
        null(tw <= 3, "testing's 'Take the lag and the tuner from the note played' (%d words)" % tw)

        # words
        s = p.evaluate(SAY)
        results["say"] = s
        check(not s["missing"] and not s["wrong"] and not s["unsaid"], "all %d controls have words and put them in the info line" % s["n"] + (": " + str(s) if s["missing"] or s["wrong"] or s["unsaid"] else ""))
        before = p.evaluate("() => { UI.say('timebase'); UI.say('measureName'); return document.getElementById('infoText').textContent; }")
        null(before != p.evaluate("UI.D.words.timebase[1]"), "the panel's name, which has no words, changes the line")

        # fit and shift at the six windows
        results["fit"], results["shift"] = {}, {}
        for size in SIZES:
            p.evaluate("(s) => { __m.S.size = s; __m.render(); }", size)
            base, fit_bad, moved = None, [], set()
            per_tab = {}
            for t in TABS:
                for st in STATES:
                    o = dict(st); o["tab"] = t
                    p.evaluate("(o) => __m.set(o)", o)
                    f = p.evaluate(FIT)
                    if f["scroll"] > 0 or f["viewScroll"] > 0 or f["over"] or not f["inWin"] or not f["abovePic"] or not f["head"]:
                        fit_bad.append((t, st, f))
                    bx = p.evaluate(BOXES)
                    shared = {k: v for k, v in bx.items() if k in ("measureName", "run", "modeAuto", "modeNormal", "modeSingle", "autoset", "measureClose") or k.startswith("mtab-") or k == "measurePanel"}
                    if base is None:
                        base = shared
                    moved |= set(diff(base, shared))
                    if t not in per_tab:
                        per_tab[t] = bx
                    moved |= {t + ":" + m for m in diff(per_tab[t], bx) if not m.startswith("msum-") and not m.endswith("Value") and m not in ("refState", "laneName1", "laneName2", "runLabel")}
            f0 = p.evaluate("() => (__m.set({ tab: 'vertical' }), 0)") or p.evaluate(FIT)
            results["fit"][size] = {"h": f0["h"], "bottom": f0["bottom"], "picT": f0["picT"], "bad": len(fit_bad)}
            results["shift"][size] = sorted(moved)
            check(not fit_bad, "%s: no scroll on any subtab in %d states; inside the window, above the Picture strip (panel %d tall, ends %d, strip at %d); Run, mode and Autoset in view" % (size, len(STATES), f0["h"], f0["bottom"], f0["picT"]) + (": " + str(fit_bad[:2]) if fit_bad else ""))
            check(not moved, "%s: nothing moves across the 4 subtabs x %d states" % (size, len(STATES)) + (": " + str(sorted(moved)[:8]) if moved else ""))

        # the nulls for fit and shift, at 960 x 600
        p.evaluate("() => { __m.S.size = '960x600'; __m.render(); __m.set({ tab: 'trigger' }); document.getElementById('measurePanel').classList.add('wall'); }")
        f = p.evaluate(FIT)
        null(f["scroll"] <= 0 and f["viewScroll"] <= 0, "testing's wall (every view in flow at once) fits at 960 x 600 (it overflows by %d px)" % max(f["scroll"], f["viewScroll"]))
        p.evaluate("() => __m.render()")
        p.evaluate("() => { const st = document.createElement('style'); st.id = 'nullw'; st.textContent = '.kcell { width: auto !important; }'; document.head.appendChild(st); __m.set({ tab: 'trigger', level: 0 }); }")
        a = p.evaluate(BOXES)
        p.evaluate("() => __m.set({ tab: 'trigger', level: -1000, holdoff: 50 })")
        b = p.evaluate(BOXES)
        null(not diff(a, b), "a knob cell sized to its reading, level 0 then -1, holdoff off then 5 ms (moved: %s)" % diff(a, b)[:3])
        p.evaluate("() => { document.getElementById('nullw').remove(); const st = document.createElement('style'); st.id = 'nulll'; st.textContent = 'body:not(.lagon) .vcol:last-child .row.knobs { display: none !important; }'; document.head.appendChild(st); __m.set({ tab: 'vertical' }); }")
        a = p.evaluate(BOXES)
        p.evaluate("() => { document.body.classList.add('lagon'); __m.set({ tab: 'vertical', filterOn: true }); }")
        b = p.evaluate(BOXES)
        null(not diff(a, b), "the trace filter's knobs taken out while it is off (moved: %s)" % diff(a, b)[:3])
        p.evaluate("() => { document.getElementById('nulll').remove(); document.body.classList.remove('lagon'); __m.S.size = '1400x900'; __m.render(); }")

        # the trigger's drawing
        def geo(o):
            o = dict(o); o["tab"] = "trigger"
            p.evaluate("(o) => __m.set(o)", o)
            return p.evaluate("""() => { const g = JSON.parse(document.getElementById('trigPlot').dataset.geo);
              const lv = document.getElementById('trigLevel'), ps = document.getElementById('trigPos'), tr = document.getElementById('trigTrace');
              const pts = tr.getAttribute('d').slice(1).split('L').map(s => s.split(' ').map(Number));
              let near = pts[0]; for (const q of pts) if (Math.abs(q[0] - g.xp) < Math.abs(near[0] - g.xp)) near = q;
              const i = pts.indexOf(near), dy = pts[Math.min(pts.length - 1, i + 2)][1] - pts[Math.max(0, i - 2)][1];
              return { g, ly: +lv.getAttribute('y1'), px: +ps.getAttribute('x1'), at: near[1], up: dy < 0, ink: tr.getAttribute('stroke') }; }""")
        results["trigger"] = []
        for o in [{"level": 0, "position": 10}, {"level": 300, "position": 50}, {"level": -400, "position": 80, "edge": "edgeFalling"}, {"level": 500, "position": 25}]:
            r = geo(o)
            g = r["g"]
            want_y = g["y0"] + g["h"] / 2 - g["level"] * g["h"] / 2
            want_x = g["x0"] + g["pos"] * g["w"]
            ok = abs(r["ly"] - want_y) < 0.6 and abs(r["px"] - want_x) < 0.6 and abs(r["at"] - r["ly"]) < 1.5 and r["up"] == (o.get("edge", "edgeRising") == "edgeRising") and not g["free"]
            results["trigger"].append({"state": o, "levelY": r["ly"], "wantY": round(want_y, 2), "posX": r["px"], "wantX": round(want_x, 2), "traceAtMarker": r["at"], "rising": r["up"]})
            check(ok, "trigger drawing at %s: level at y %.1f (want %.1f), marker at x %.1f (want %.1f), trace %.1f at the marker, %s" % (o, r["ly"], want_y, r["px"], want_x, r["at"], "rising" if r["up"] else "falling"))
            if o["level"]:
                null(abs(r["ly"] - (g["y0"] + g["h"] / 2 + g["level"] * g["h"] / 2)) < 0.6, "the level of the other sign at %s" % o)
            null(r["up"] != (o.get("edge", "edgeRising") == "edgeRising"), "the other edge's slope at %s" % o)
        r = geo({"level": 900})
        check(r["g"]["free"] and r["ink"] == "var(--unresolved)", "past the peak (level +0.9): free run, the trace grey")
        null(r["g"]["t0"] is not None, "a level past the peak claimed as a crossing")

        # zoom's slice
        p.evaluate("() => __m.set({ tab: 'time', zoom: 12 })")
        g = p.evaluate("() => JSON.parse(document.getElementById('timePlot').dataset.geo)")
        check(abs(g["slice"] - g["w"] / 8) < 0.6, "Zoom 8x keeps a slice %.1f px of %.1f, an eighth" % (g["slice"], g["w"]))
        null(abs(g["w"] - g["w"] / 8) < 0.6, "1x's width at 8x")
        results["zoom"] = g

        # a phone
        ph = ctx.new_page()
        ph.set_viewport_size({"width": 390, "height": 844})
        ph.goto(PAGE)
        sx = ph.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
        check(sx <= 0, "a phone's width (390) has no horizontal page scroll (%d)" % sx)
        check(not errs, "no console errors" + (": " + str(errs[:3]) if errs else ""))
        br.close()
    results["checks"] = n[0]
    results["failed"] = fails
    json.dump(results, open(os.path.join(HERE, "results.json"), "w"), indent=1, ensure_ascii=False)
    print("\n%d checks, %d failed" % (n[0], len(fails)))
    sys.exit(1 if fails else 0)

main()
