"""Ink's figures (19 Nov, web/docs/ink-figures.md): the oscillator and the
shaper drawn, the controls in one row under them, Wave - Figure, and Ink
drawing the settings, still.

(The name: inktest.py was already the X-Y figure's inks.)

Each check is fed a known-wrong case beside it (a null), and the null must be
seen to fail, as CLAUDE.md asks of every new assertion.

- the drawings are the core's sound. inkcore.cpp is built against
  core/include and runs the real oscStep (osc.h), shapeSample, setShaping and
  the crush's quantiser (voice.h); the page's own drawing arithmetic, the
  functions the drawing calls, is compared with it point for point:
  * FM (left and right), Ring, Warp on the sine, Unison and the harmonic at
    7:2 within 1e-9;
  * Unison's still, 4.33 of the note's cycles in, at 3, 5 and 7 copies,
    within 1e-9 of oscStep run exactly that long (null: the still drawn at
    nought seconds), and its fan growing with Spread;
  * Sync, the square and a square sub within 0.0013 away from their edges
    (the core band-limits them and plays sync a sample late);
  * a sine sub within 1e-3: the core's sub steps before it reads, so it runs
    one sample ahead of the note (left alone, ink-figures.md);
  * Warp on the triangle within 0.002 (the core's 5 Hz blocker, the drawing's
    settled mean);
  * the shaper's curve to the bit for drive, fold and bits.
  Nulls: FM against the core with FM off; the sub against the core's sub two
  octaves down; drive's curve with a linear law;
- the drawing is that arithmetic over the hand's tone: a knob turned with the
  real mouse redraws the wave, whose points are the channel at the new value
  (null: they are not the old value's);
- the switches by the real mouse: the Shaping subtab, Figure and Wave;
  showControl on FM from Shaping chooses the Oscillator;
- the fit at the six windows, for the wave, the figure and Shaping: Ink not
  scrolled, the view's content inside it, every time drawing 1.5:1 to 7:1
  and 120 px tall, the curve and the figure square, the controls one row,
  each summary fitting, clear of the modulation row; Shaping stacked at
  1660x1050 alone. Nulls: a drawing row given the whole view runs over; a
  control row 300 px wide wraps; stacked forced at 960x600 shrinks the curve;
  side by side forced at 1660x1050 leaves the paper;
- nothing moves: every box on Ink the same to half a pixel across ten
  settings, five shapes and both subtabs (outside the view), at the six
  windows. Null: the header's words in a box sized to them move the key when
  Unison comes on;
- Wave - Figure moves nothing outside the drawing at the six windows (null:
  the figure's row sized to the figure moves the controls); it is no step of
  undo and not in the setup; it is remembered across a reload (null: a fresh
  browser draws the wave);
- Ink draws the settings, still: with Unison on and nothing touched, the wave
  is not redrawn over 1.5 s (null: a clock put back moves it); Hold to watch
  it drift moves the copies while held by the real mouse, moves no box, and
  lets go to the very same still; its place is kept unseen while Unison is off;
- no errors on the page.

    CHROME=/opt/pw-browsers/chromium python3 web/tests/inkfigtest.py
"""
import json, math, os, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright
import webfonts
from playfigs import SIZES

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(ART)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
PAGE = "file://" + os.path.join(ART, "scope.html")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    check("null: " + name, red, detail)

# ---- the core, built from core/include ----
EXE = os.path.join(tempfile.mkdtemp(), "inkcore")
subprocess.run(["g++", "-std=c++17", "-O2", "-I", os.path.join(ROOT, "core", "include"), os.path.join(HERE, "inkcore.cpp"), "-o", EXE], check=True)
def core_osc(c):
    args = [EXE, "osc", c["shape"], str(c.get("fm", 0)), str(c.get("ratio", 1)), str(c.get("warp", 0)), str(c.get("warpAt", 0.25)), str(c.get("ring", 0)),
            str(c.get("sync", 1)), str(c.get("sub", 0)), str(c.get("subOct", 1)), str(c.get("subSine", 0)), str(c.get("unison", 1)), str(c.get("cents", 12)),
            str(c.get("offset", 0)), str(c["cycles"]), str(c["points"])] + ([str(c["settle"])] if "settle" in c else [])
    return [float(x) for x in subprocess.run(args, capture_output=True, text=True, check=True).stdout.split()]
def core_shaper(d, f, bits):
    return [float(x) for x in subprocess.run([EXE, "shaper", str(d), str(f), str(bits)], capture_output=True, text=True, check=True).stdout.split()]

# The page's drawing arithmetic for one case: the hand's tone from inkTone, its fields replaced by the case's,
# the shape's own function from bendWave as the drawing takes it.
CHANNEL = """([c, points]) => { const I = window.__ink, base = I.tone(), t = Object.assign({}, base.t, { shape: c.shape });
  const T = Object.assign({}, base, { t, shape: c.shape, noise: false, fmI: c.fm || 0, modRatio: c.ratio || 1, warpA: c.warp || 0,
    warpC: c.warpAt == null ? 0.25 : c.warpAt, ring: c.ring || 0, syncR: c.sync || 1, sub: c.sub || 0, subDiv: (c.subOct || 1) === 2 ? 4 : 2,
    subSine: !!c.subSine, n: c.unison || 1, cents: c.cents == null ? 12 : c.cents, hz: 220 });
  T.at = bendWave(t);
  return I.channel(T, (c.offset || 0) * Math.PI / 180, points + 1, c.t || 0, c.cycles).v.slice(0, points); }"""

CASES = [
    ("FM 2.0 at 3:2, left", dict(shape="sine", fm=2, ratio=1.5, cycles=2), 1e-9, False),
    ("FM 2.0 at 3:2, right at 90 degrees", dict(shape="sine", fm=2, ratio=1.5, offset=90, cycles=2), 1e-9, False),
    ("Ring 70% at 2:1", dict(shape="sine", ring=0.7, ratio=2, cycles=1), 1e-9, False),
    ("Warp +0.54 at 25% on the sine", dict(shape="sine", warp=0.54, warpAt=0.25, cycles=1), 1e-9, False),
    ("Unison 3 at 12 cents, 2 s in", dict(shape="sine", unison=3, cents=12, cycles=1, t=2.0), 1e-9, False),
    ("the harmonic, FM 1.0 at 7:2", dict(shape="harmonic", fm=1, ratio=3.5, cycles=2), 1e-9, False),
    ("the saw, Sync 2.6x", dict(shape="ramp", sync=2.6, cycles=1), 0.0013, True),
    ("the square", dict(shape="square", cycles=1), 0.0013, True),
    ("Sub 50%, a square an octave down", dict(shape="sine", sub=0.5, cycles=2), 0.0013, True),
    ("Sub 50%, a sine two octaves down (the core's sub a sample ahead)", dict(shape="sine", sub=0.5, subOct=2, subSine=1, cycles=4), 1e-3, False),
    ("Warp +0.54 on the triangle (the blocker)", dict(shape="triangle", warp=0.54, warpAt=0.25, cycles=1), 0.002, False),
]

def compare(core, draw, edges):
    worst = 0
    for i in range(len(core)):
        if edges and any(abs(core[j] - core[j - 1]) > 0.05 for j in range(max(1, i - 2), min(len(core), i + 3))):
            continue
        worst = max(worst, abs(core[i] - draw[i]))
    return worst

# The fit, for the view shown: as playfigs.MEASURE, for Ink.
MEASURE = """() => {
  const z = pageZoom || 1, R = (n) => n.getBoundingClientRect(), shown = (n) => n && n.getClientRects().length;
  const body = el.benchBody, view = document.querySelector('.ink-figs .fig-view:not([hidden])');
  const tops = (nodes) => new Set([...nodes].filter(shown).map((n) => Math.round(R(n).bottom / z))).size;
  const plotOf = (n, what) => { const r = R(n); return { what, w: Math.round(r.width / z), h: Math.round(r.height / z), aspect: r.width / Math.max(1, r.height) }; };
  const plots = view === el.oscGroup ? [window.__ink.draws() === 'figure' ? plotOf(el.oscXY, 'figure') : plotOf(el.oscWave, 'wave')]
    : [plotOf(el.shpCurve, 'curve'), plotOf(el.shpCycle, 'cycle')];
  const viewOver = Math.max(0, ...[...view.querySelectorAll('*')].filter((n) => shown(n) && !n.closest('svg')).map((n) => (R(n).bottom - R(view).bottom) / z));
  const labels = [...window.__ink.figs.bar.children].map((t) => { const s = t.querySelector('.fig-sum'); return { fits: s.scrollWidth <= s.clientWidth + 0.5, text: s.textContent }; });
  const foot = view.querySelector('.fig-foot');
  return { scroll: body.scrollHeight - body.clientHeight, viewOver, plots, labels, stacked: !!window.__ink.figs.stacked,
    knobRows: tops(view.querySelectorAll('.ink-knobs > .menu-row')), covers: R(view).bottom > R(el.modRow).top + 1,
    paper: (R(view).bottom - R(foot).bottom) / z, area: [Math.round(R(view).width / z), Math.round(R(view).height / z)] };
}"""

# Every box on Ink a choice must not move. The view's own are keyed "view:".
BOXES = """() => {
  const z = pageZoom || 1, out = {};
  const put = (k, n) => { if (!n || !n.getClientRects().length) return; const r = n.getBoundingClientRect(); out[k] = [r.left / z, r.top / z, r.width / z, r.height / z]; };
  put('figs', document.querySelector('.ink-figs')); put('bar', window.__ink.figs.bar);
  for (const t of window.__ink.figs.bar.children) put('tab:' + t.dataset.sub, t);
  const view = document.querySelector('.ink-figs .fig-view:not([hidden])');
  put('view', view);
  view.querySelectorAll('.fig-tools > *, .fig-tools .switch > button, :scope > .menu-title > *, .fig-plot, .ink-plot:not([hidden]), .fig-foot, .fig-note')
    .forEach((n, i) => put('view:' + (n.id || n.className.split(' ')[0] + i), n));
  for (const row of view.querySelectorAll('.ink-knobs > .menu-row')) { const c = row.querySelector('select, input'); if (c) put('view:control:' + c.id, row); }
  return out;
}"""

def same(a, b, keys=None):
    ks = [k for k in a if k in b and (keys is None or keys(k))]
    moved = [(k, [round(x, 1) for x in a[k]], [round(x, 1) for x in b[k]]) for k in ks if any(abs(x - y) > 0.5 for x, y in zip(a[k], b[k]))]
    missing = [k for k in a if k not in b and (keys is None or keys(k))]
    return (not moved and not missing), moved[:2] + [("missing", k) for k in missing[:2]]

# A control set as a hand sets it: the value, then its event, then Ink painted as it is after an input.
SET = """async (values) => {
  for (const [id, v] of Object.entries(values)) { const n = document.getElementById(id); n.value = String(v);
    n.dispatchEvent(new Event(n.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })); }
  window.__ink.paint(); await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))); window.__ink.paint(); }"""
PLAIN = {"oscFm": 0, "oscRatio": "1", "oscBend": 0, "oscBendAt": 25, "oscRing": 0, "oscSync": 100, "oscSub": 0, "oscUnison": "1", "oscSpread": 12,
         "shpDrive": 0, "shpFold": 0, "shpBits": "0", "shpRate": "0"}
SETTINGS = [{}, {"oscUnison": "3"}, {"oscFm": 20, "oscRatio": "1.5"}, {"oscBend": 60}, {"oscRing": 70, "oscRatio": "2"}, {"oscSync": 260},
            {"oscSub": 60}, {"oscUnison": "7", "oscSpread": 50}, {"shpDrive": 45, "shpBits": "4"}, {"shpFold": 35, "shpRate": "2000"}]
SHAPES = ["sine", "harmonic", "triangle", "ramp", "square"]

def open_page(b, w, h, ctx=None):
    p = ctx.new_page() if ctx else b.new_page(viewport={"width": w, "height": h})
    webfonts.route(p)
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto(PAGE)
    p.wait_for_function("typeof faceLaidOut !== 'undefined' && faceLaidOut && !!window.__ink", timeout=90000)
    webfonts.settle(p)
    p.evaluate("() => { const d = document.getElementById('helpDialog'); if (d && d.open) d.close(); setView('bench'); setBenchTab('ink'); }")
    p.wait_for_timeout(300)
    return p, errs

def at_size(p, w, h):
    p.set_viewport_size({"width": w, "height": h})
    p.wait_for_timeout(500)
    p.evaluate("() => { setBenchTab('ink'); window.__ink.paint(); }")
    p.wait_for_timeout(200)

def state(p, sub, values, shape="sine", draws="wave"):
    p.evaluate(SET, dict(PLAIN, **values, shape=shape))
    p.evaluate("([sub, draws]) => { window.__ink.setDraws(draws); window.__ink.setSub(sub); window.__ink.fit(); window.__ink.paint(); }", [sub, draws])
    p.wait_for_timeout(60)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    p, errs = open_page(b, 1400, 900)
    print("measured in " + ("the brand's webfonts" if p.evaluate(webfonts.LOADED) else "FALLBACK faces: the webfonts did not load"))

    # ---- the drawings are the core's sound ----
    for name, c, tol, edges in CASES:
        pts = 512
        w = compare(core_osc(dict(c, points=pts)), p.evaluate(CHANNEL, [c, pts]), edges)
        check(f"{name}: Ink's arithmetic is oscStep's within {tol:g}" + (" away from edges" if edges else ""), w <= tol, f"worst {w:.3g}")
    still = p.evaluate("() => window.__ink.STILL_CYCLES") / 220
    at = round(still * 220 * 4096) / (220 * 4096)   # the core runs whole samples: both read at the sample nearest the still
    for n_, cents in ((3, 12), (5, 20), (7, 50)):
        c = dict(shape="sine", unison=n_, cents=cents, cycles=1, t=at, settle=at)
        w = compare(core_osc(dict(c, points=512)), p.evaluate(CHANNEL, [c, 512]), False)
        check(f"Unison {n_} at {cents} cents, the still ({still * 1000:.2f} ms in): the bold line is oscStep's within 1e-9", w <= 1e-9, f"worst {w:.3g}")
    c = dict(shape="sine", unison=5, cents=20, cycles=1, t=0, settle=at)
    w = compare(core_osc(dict(c, points=512)), p.evaluate(CHANNEL, [c, 512]), False)
    null(f"the still drawn at nought seconds is not oscStep at the still's moment", w > 0.1, f"{w:.2f} off")
    page_still = p.evaluate("() => { const T = window.__ink.tone({ n: 5, hz: 220 }); return window.__ink.stillT(T); }")
    check("the drawing's still is 4.33 of the note's cycles in", abs(page_still * 220 - 4.33) < 0.01, f"{page_still * 220:.3f} cycles")
    fan = p.evaluate("""() => { const I = window.__ink, out = []; for (const cents of [5, 20, 50]) { const T = I.tone({ n: 5, cents, hz: 220, fmI: 0, ring: 0, sub: 0, syncR: 1, warpA: 0 });
      const t = I.stillT(T), lo = I.channel(T, 0, 400, t, 1, 0).v, hi = I.channel(T, 0, 400, t, 1, 4).v; out.push(Math.max(...lo.map((x, i) => Math.abs(x - hi[i])))); } return out; }""")
    check("the still's fan grows with Spread", fan[0] < fan[1] < fan[2] and fan[0] > 0.05, "outer copies apart by %.2f, %.2f, %.2f at 5, 20, 50 cents" % tuple(fan))
    c = CASES[0][1]
    w = compare(core_osc(dict(c, fm=0, points=512)), p.evaluate(CHANNEL, [c, 512]), False)
    null("the FM drawing is not the core with FM off", w > 0.5, f"{w:.2f} off")
    c = CASES[8][1]
    w = compare(core_osc(dict(c, subOct=2, cycles=2, points=512)), p.evaluate(CHANNEL, [c, 512]), True)
    null("the sub drawing is not the core's sub two octaves down", w > 0.1, f"{w:.2f} off")
    SH = """([d, f, bits, linear]) => { const sh = window.__ink.shaper({ drive: d, fold: f, bits }), out = [];
      for (let i = 0; i <= 2000; i++) { const x = -1 + 2 * i / 2000; let v;
        if (linear) { const dr = 30 * d, k = dr > 0 ? 1 / Math.tanh(dr) : 1; v = sh.quant(dr > 0 ? Math.tanh(dr * x) * k : x); } else v = sh.quant(sh.shape(x)); out.push(v); } return out; }"""
    for d, f, bits in ((0.45, 0, 0), (0, 0.35, 0), (0.6, 0.2, 0), (0.45, 0, 4), (0.2, 0.05, 6), (1, 1, 1)):
        core, draw = core_shaper(d, f, bits), p.evaluate(SH, [d, f, bits, False])
        # In ulps of the value: the fold's sine is the C library's in the core and V8's here, which differ by
        # one in the last place now and then (1.1e-16 at fold 0.2). Everything else is to the bit.
        ulps = max((abs(a - b2) / math.ulp(max(abs(a), abs(b2)))) if a != b2 else 0 for a, b2 in zip(core, draw))
        check(f"the curve at drive {d}, fold {f}, {bits or 'no'} bits is shapeSample's " + ("to the bit" if f == 0 else "to one ulp (the libraries' sine)"),
              ulps == 0 if f == 0 else ulps <= 1, f"worst {ulps:.2f} ulp")
    w = max(abs(a - b2) for a, b2 in zip(core_shaper(0.45, 0, 0), p.evaluate(SH, [0.45, 0, 0, True])))
    null("drive's curve with a linear law is not the core's", w > 0.1, f"{w:.2f} off")

    # ---- the drawing is that arithmetic over the hand's tone, a knob turned by the real mouse ----
    state(p, "osc", {})
    DRAWN = """() => { const d = el.oscWave._data, I = window.__ink, T = I.tone(); const n = d.L.length;
      const now = I.channel(T, 0, n, I.stillT(T)).v; return { fm: Number(el.oscFm.value), worst: Math.max(...now.map((x, i) => Math.abs(x - d.L[i]))), L: d.L }; }"""
    before = p.evaluate(DRAWN)
    face = p.locator("#oscFm").locator("xpath=..").locator(".knob-face").bounding_box()
    p.mouse.move(face["x"] + face["width"] / 2, face["y"] + face["height"] / 2); p.mouse.down()
    p.mouse.move(face["x"] + face["width"] / 2, face["y"] - 60, steps=8); p.mouse.up()
    p.wait_for_timeout(200)
    after = p.evaluate(DRAWN)
    check("FM turned by the mouse redraws the wave as the channel at the new value", after["fm"] > before["fm"] and after["worst"] < 1e-12,
          f"FM {before['fm']} to {after['fm']}, worst {after['worst']:.3g}")
    moved = max(abs(a - b2) for a, b2 in zip(after["L"], p.evaluate("() => { const I = window.__ink, T = I.tone({ fmI: 0 }); return I.channel(T, 0, el.oscWave._data.L.length, 0).v; }")))
    null("the wave drawn after the turn is not the channel at the old value", moved > 0.05, f"{moved:.2f} apart")
    p.click("#inkTab-shp"); p.wait_for_timeout(150)
    sub = p.evaluate("() => [window.__ink.figs.sub, el.shpGroup.hidden, el.oscGroup.hidden, el.shpCurve.querySelectorAll('[data-curve]').length]")
    check("the Shaping subtab by the mouse shows Shaping and its curve", sub == ["shp", False, True, 1], str(sub))
    p.evaluate("() => showControl('oscFm')"); p.wait_for_timeout(100)
    check("showControl on FM from Shaping chooses the Oscillator", p.evaluate("() => window.__ink.figs.sub") == "osc")
    p.click('#inkDraws [data-draws="figure"]'); p.wait_for_timeout(150)
    fig = p.evaluate("() => [window.__ink.draws(), el.oscXYBox.hidden, el.oscWaveBox.hidden, el.oscXY.querySelectorAll('[data-figure]').length]")
    check("Figure by the mouse draws the figure in the wave's place", fig == ["figure", False, True, 1], str(fig))
    p.click('#inkDraws [data-draws="wave"]'); p.wait_for_timeout(150)
    check("and Wave by the mouse draws the wave again", p.evaluate("() => window.__ink.draws()") == "wave")

    # ---- the fit, at the six windows ----
    for w_, h_ in SIZES:
        at_size(p, w_, h_)
        for sub, draws in (("osc", "wave"), ("osc", "figure"), ("shp", "wave")):
            state(p, sub, {"oscFm": 20, "oscRatio": "1.5", "oscUnison": "5", "shpDrive": 45, "shpBits": "4", "shpRate": "2000"}, draws=draws)
            m = p.evaluate(MEASURE)
            timey = [q for q in m["plots"] if q["what"] in ("wave", "cycle")]
            square = [q for q in m["plots"] if q["what"] in ("figure", "curve")]
            ok = (m["scroll"] <= 1 and m["viewOver"] <= 1 and all(1.5 <= q["aspect"] <= 7 and q["h"] >= 120 for q in timey)
                  and all(0.85 <= q["aspect"] <= 1.25 and q["h"] >= 120 for q in square) and m["knobRows"] == 1 and not m["covers"]
                  and all(l["fits"] for l in m["labels"]))
            check(f"{w_}x{h_}, {sub}{' as the figure' if draws == 'figure' else ''}{', stacked' if sub == 'shp' and m['stacked'] else ''}: fits, one row",
                  ok, ", ".join(f"{q['what']} {q['w']}x{q['h']}" for q in m["plots"]) + f", {m['paper']:.0f} px of paper, scroll {m['scroll']}, over {m['viewOver']:.1f}")
            if sub == "shp":
                check(f"{w_}x{h_}: Shaping stacks only at 1660x1050", m["stacked"] == (w_ == 1660), "stacked" if m["stacked"] else "side by side")
    at_size(p, 1400, 900); state(p, "osc", {})
    over = p.evaluate("""() => { const row = el.oscRow, view = el.oscGroup; row.style.height = view.clientHeight + 'px'; const z = pageZoom || 1;
      const R = (n) => n.getBoundingClientRect(); const o = Math.max(...[...view.querySelectorAll('.fig-foot *')].map((n) => (R(n).bottom - R(view).bottom) / z)); window.__ink.fit(); return o; }""")
    null("a drawing row given the whole view runs over", over > 1, f"{over:.0f} px over")
    wrap = p.evaluate("""() => { const k = el.oscGroup.querySelector('.ink-knobs'); k.style.width = '300px'; k.style.flexWrap = 'wrap';
      const n = new Set([...k.children].filter((c) => c.getClientRects().length).map((c) => Math.round(c.getBoundingClientRect().bottom))).size; k.style.width = ''; k.style.flexWrap = ''; return n; }""")
    null("a control row 300 px wide wraps", wrap > 1, f"{wrap} rows")
    at_size(p, 960, 600); state(p, "shp", {"shpDrive": 45})
    side = p.evaluate(MEASURE)["plots"][0]["h"]
    p.evaluate("() => { window.__ink.figs.lay = 'stacked'; window.__ink.fit(); window.__ink.paint(); }"); p.wait_for_timeout(50)
    forced = p.evaluate(MEASURE)
    p.evaluate("() => { window.__ink.figs.lay = undefined; window.__ink.fit(); }")
    null("stacked forced at 960x600 shrinks the curve below side by side's", forced["plots"][0]["h"] < side, f"{forced['plots'][0]['h']} against {side}")
    at_size(p, 1660, 1050); state(p, "shp", {"shpDrive": 45})
    stacked_paper = p.evaluate(MEASURE)["paper"]
    p.evaluate("() => { window.__ink.figs.lay = 'side'; window.__ink.fit(); window.__ink.paint(); }"); p.wait_for_timeout(50)
    forced = p.evaluate(MEASURE)
    p.evaluate("() => { window.__ink.figs.lay = undefined; window.__ink.fit(); }")
    check("stacked at 1660x1050 leaves little paper", stacked_paper <= 60, f"{stacked_paper:.0f} px")
    null("side by side forced at 1660x1050 leaves the paper", forced["paper"] > 150, f"{forced['paper']:.0f} px")

    # ---- nothing moves ----
    for w_, h_ in SIZES:
        at_size(p, w_, h_)
        bad = []
        for sub in ("osc", "shp"):
            state(p, sub, {})
            base = p.evaluate(BOXES)
            for s in SETTINGS:
                for shape in SHAPES:
                    state(p, sub, s, shape)
                    ok, moved = same(base, p.evaluate(BOXES))
                    if not ok: bad.append(f"{sub} {json.dumps(s)} {shape}: {moved}")
        state(p, "osc", {}); a = p.evaluate(BOXES); state(p, "shp", {}); b2 = p.evaluate(BOXES)
        ok, moved = same(a, b2, lambda k: not k.startswith("view"))
        if not ok: bad.append(f"the subtabs: {moved}")
        check(f"{w_}x{h_}: nothing on Ink moves across {len(SETTINGS)} settings, {len(SHAPES)} shapes and both subtabs", not bad, " | ".join(bad[:2]))
        # Wave - Figure moves nothing outside the drawing.
        state(p, "osc", {"oscFm": 20, "oscRatio": "1.5"}, draws="wave"); a = p.evaluate(BOXES)
        state(p, "osc", {"oscFm": 20, "oscRatio": "1.5"}, draws="figure"); b2 = p.evaluate(BOXES)
        ok, moved = same(a, b2, lambda k: k not in ("view:oscWaveBox", "view:oscXYBox"))
        check(f"{w_}x{h_}: Wave - Figure moves nothing outside the drawing", ok, str(moved))
    at_size(p, 1400, 900)
    p.evaluate("() => { const st = document.createElement('style'); st.id = 'nullFig'; st.textContent = '#oscRow.is-figure { height: auto !important; } #oscRow.is-figure > #oscXYBox { height: 200px !important; }'; document.head.appendChild(st); }")
    state(p, "osc", {}, draws="wave"); a = p.evaluate(BOXES); state(p, "osc", {}, draws="figure"); b2 = p.evaluate(BOXES)
    p.evaluate("() => document.getElementById('nullFig').remove()")
    ok, moved = same(a, b2, lambda k: k not in ("view:oscWaveBox", "view:oscXYBox"))
    null("the figure's row sized to the figure moves the controls", not ok, str(moved))
    p.evaluate("() => { const st = document.createElement('style'); st.id = 'nullSay'; st.textContent = '.ink-say { flex: 0 0 auto !important; }'; document.head.appendChild(st); }")
    state(p, "osc", {}); a = p.evaluate(BOXES); state(p, "osc", {"oscUnison": "3"}); b2 = p.evaluate(BOXES)
    p.evaluate("() => document.getElementById('nullSay').remove()")
    ok, moved = same(a, b2)
    null("the header's words in a box sized to them move the key when Unison comes on", not ok, str(moved))

    # ---- Wave - Figure is a look: no undo step, not in the setup ----
    state(p, "osc", {}, draws="wave"); p.wait_for_timeout(700)
    snap0, undo0 = p.evaluate("() => [JSON.stringify(snapshot()), undoHistory.undo.length]")
    p.click('#inkDraws [data-draws="figure"]'); p.wait_for_timeout(700)
    snap1, undo1 = p.evaluate("() => [JSON.stringify(snapshot()), undoHistory.undo.length]")
    check("Wave - Figure is not in the setup and is no step of undo", snap0 == snap1 and undo0 == undo1, f"undo {undo0} to {undo1}")
    p.click('#inkDraws [data-draws="wave"]')

    # ---- still: nothing redraws by itself ----
    state(p, "osc", {"oscUnison": "5", "oscSpread": 20})
    p.wait_for_timeout(300)
    STILL = """(clock) => new Promise((done) => { const I = window.__ink, d0 = el.oscWave.querySelector('[data-left]').getAttribute('d'), n0 = I.figs.draws;
      const timer = clock ? setInterval(() => { I.figs.nullT += 0.016; I.paint(); }, 16) : null;
      setTimeout(() => { if (timer) clearInterval(timer); const d1 = el.oscWave.querySelector('[data-left]').getAttribute('d'), n1 = I.figs.draws;
        I.figs.nullT = 0; I.paint(); done({ same: d0 === d1, draws: n1 - n0 }); }, 1500); })"""
    r = p.evaluate(STILL, False)
    check("with Unison on and nothing touched, the wave is not redrawn over 1.5 s", r["same"] and r["draws"] == 0, str(r))
    r = p.evaluate(STILL, True)
    null("a clock put back moves the wave within 1.5 s", not r["same"] and r["draws"] > 10, str(r))
    still_d = p.evaluate("() => el.oscWave.querySelector('[data-left]').getAttribute('d')")
    box0 = p.evaluate(BOXES)
    drift = p.locator("#inkDrift").bounding_box()
    p.mouse.move(drift["x"] + drift["width"] / 2, drift["y"] + drift["height"] / 2); p.mouse.down()
    p.wait_for_timeout(600)
    held = p.evaluate("() => [el.oscWave.querySelector('[data-left]').getAttribute('d'), el.inkDrift.getAttribute('aria-pressed')]")
    box1 = p.evaluate(BOXES)
    p.mouse.up(); p.wait_for_timeout(150)
    let_go = p.evaluate("() => [el.oscWave.querySelector('[data-left]').getAttribute('d'), el.inkDrift.getAttribute('aria-pressed')]")
    check("Hold to watch it drift, held by the mouse, moves the copies", held[0] != still_d and held[1] == "true")
    check("and lets go to the very same still", let_go[0] == still_d and let_go[1] == "false")
    ok, moved = same(box0, box1)
    check("the drift moves no box", ok, str(moved))
    state(p, "osc", {"oscUnison": "1"})
    unseen = p.evaluate("() => [getComputedStyle(el.inkDrift).visibility, el.inkDrift.getClientRects().length > 0]")
    check("with Unison off the drift keeps its place unseen", unseen == ["hidden", True], str(unseen))
    p.mouse.move(drift["x"] + drift["width"] / 2, drift["y"] + drift["height"] / 2); p.mouse.down(); p.wait_for_timeout(200)
    off = p.evaluate("() => window.__ink.figs.drift"); p.mouse.up()
    check("and pressing where it is unseen drifts nothing", off is None)
    check("no errors on the page", not errs, "; ".join(errs[:3]))
    p.close()

    # ---- remembered by the browser ----
    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    q, _ = open_page(b, 1400, 900, ctx)
    fresh = q.evaluate("() => window.__ink.draws()")
    q.click('#inkDraws [data-draws="figure"]'); q.wait_for_timeout(100)
    q.reload(); q.wait_for_function("typeof faceLaidOut !== 'undefined' && faceLaidOut && !!window.__ink", timeout=90000)
    q.evaluate("() => { const d = document.getElementById('helpDialog'); if (d && d.open) d.close(); setBenchTab('ink'); }")
    kept = q.evaluate("() => [window.__ink.draws(), el.oscXYBox.hidden]")
    check("Figure chosen is remembered across a reload, and drawn", kept == ["figure", False], str(kept))
    ctx.close()
    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    q, _ = open_page(b, 1400, 900, ctx)
    null("a fresh browser draws the figure", q.evaluate("() => window.__ink.draws()") == "wave" and fresh == "wave", "it draws the " + q.evaluate("() => window.__ink.draws()"))
    ctx.close()
    b.close()

print(("\nFAILED: " + "; ".join(fails)) if fails else "\nall Ink figure checks pass")
sys.exit(1 if fails else 0)
