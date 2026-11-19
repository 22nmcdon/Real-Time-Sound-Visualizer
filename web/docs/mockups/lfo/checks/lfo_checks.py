"""The drawn-LFO mockup's checks, in Chromium (web/docs/mockups/lfo/index.html).

Each check is fed a known-wrong case beside it (a null), and the null must be
seen to fail, as CLAUDE.md asks of every new assertion.

- no console errors through every window, both layouts, both LFOs and every
  shape, with a note held and a phrase played;
- the core: today's five shapes run sample by sample through lfo.h's own
  arithmetic (lfoStep, waveAt, the core's Random) beside their drawn twins
  (Random's twin one random point at full reach, the owner's call of 19 Nov)
  through the proposed engine, at three rates and two sample rates. Sine
  within 1e-12 at every sample, and at 200 001 phases read directly; saw up,
  square and Random equal to the bit (Random from one seed each, so the drawn
  engine draws its levels at the same samples as lfoStep); triangle within
  1e-7, the core's own asin(sin) being that far off a straight line at its
  peaks. Nulls: the sine drawn with straight lines (0.21 off), the random
  point rolled a line early, and a phase of a quarter, each seen to differ;
- the card draws the real shape: its two cycles, read back from the SVG, are
  the shape's levels to 0.6 px for all seven shapes. Null: the saw down's card
  read against the saw up's levels;
- the gold dot sits on the line where the LFO is now. Null: the dot's height
  against the level half a cycle on;
- the one-column editor at the six windows, with three routings and with
  eight: everything inside it, the drawing 2:1 to 7:1 and 120 px tall, at
  least three routings in sight, the tools and the knobs one row each, clear
  of the modulation row. Nulls: two columns, as today's editor, make the
  drawing a tower at 1660x1050; and the drawing at its full 2.4:1 at
  1200x680, ignoring Where it goes, leaves fewer than three routings in sight;
- nothing moves: every box in the editor and both cards the same to half a
  pixel across the seven shapes, Hz and tempo, the three starts, Silence, the
  clock stopped, a note held, a point selected, LFO 1 and LFO 2. Null: the
  reading in the head sized to its words moves the description when the rate
  goes to tempo;
- the setup: an LFO untouched writes no new field; one edited writes
  l<i>s drawn and l<i>m, whose text reads back to the points; the sine's twin
  is the text in lfo-drawn.md. Null: the untouched and edited texts differ;
- when it starts again: Each note restarts on every note of a phrase, Each
  phrase on its first only, Free never. Null: a free LFO's phase is seen not
  to move when a note is struck, so the check can see a restart;
- gestures by real mouse: dragging a point of today's sine adopts it (the
  shape becomes drawn and the point moves), pressing the line twice adds a
  point and a point twice takes it away, right-click opens the point's menu.
  Null: before the drag it is today's sine;
- the rate: 1/4 at 120 is 2.00 Hz. Null: the free rate is not;
- a phone's width has no horizontal page scroll.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/lfo/checks/lfo_checks.py
"""
import os, sys, json, re, math
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import webfonts

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = "file://" + os.path.join(HERE, "index.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
fails, n = [], [0]
results = {}

def check(ok, what):
    n[0] += 1
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)

def null(wrong_passes, what):
    check(not wrong_passes, "null: " + what)

SIZES = ["1660x1050", "1400x900", "1100x860", "1200x680", "1100x680", "960x600"]
PRESETS = ["sine", "triangle", "ramp", "rampdown", "square", "random", "smooth"]

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    p = b.new_page(viewport={"width": 1700, "height": 1100})
    webfonts.route(p)
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.on("console", lambda m: m.type == "error" and errs.append(m.text))
    p.goto(PAGE + "?shot=1")
    p.wait_for_function("window.__ready === true", timeout=30000)
    faces = webfonts.settle(p)
    print("measured in " + ("the brand's webfonts" if faces else "FALLBACK faces: the webfonts did not load"))
    results["webfonts"] = faces
    E = lambda js, arg=None: p.evaluate(js, arg)
    SET = """([size, lay, lfo, routes]) => { const S = window.__lfo.S; S.size = size; S.lfoLayout = lay; S.lfoOpen = lfo; S.routes = routes; S.lfoSel = null; S.clock = "stop"; window.__lfo.setRoutes(); window.__lfo.render(); return window.__lfo.lfoMeasure(); }"""

    # ---- every switch, without an error ----
    for size in SIZES:
        for lay in ("one", "two"):
            for lfo in (0, 1):
                E(SET, [size, lay, lfo, "many"])
                for k in PRESETS:
                    E("(k) => { const L = window.__lfo; L.choosePreset(L.S.lfo[L.S.lfoOpen], k); L.render(); }", k)
    E("() => { window.__lfo.S.clock = 'run'; window.__lfo.playPhrase(); }")
    E("() => noteDown()"); p.wait_for_timeout(600); E("() => noteUp()"); p.wait_for_timeout(300)
    check(not errs, "no console errors through every window, layout, LFO and shape" + (": " + "; ".join(errs[:3]) if errs else ""))

    # ---- the core ----
    PAIR = """([shape, twin, opts]) => { const L = window.__lfo; const pts = typeof twin === "string" ? L.PRESETS[twin]() : twin; return L.runPair(shape, pts, opts); }"""
    rows = []
    for rate in (0.01, 0.37, 7.9):
        for sr in (44100, 48000):
            secs = min(40, 3.5 / rate) if rate < 0.1 else 12
            o = {"rate": rate, "sr": sr, "seconds": secs, "seed": 11}
            for shape, tol in (("sine", 1e-12), ("triangle", 1e-7), ("ramp", 0), ("square", 0), ("random", 0)):
                r = E(PAIR, [shape, shape, o])
                rows.append({"shape": shape, "rate": rate, "sr": sr, "worst": r["worst"], "samples": r["samples"]})
                check(r["worst"] <= tol, f"{shape} at {rate} Hz, {sr}: the drawn twin within {tol:g} of lfo.h over {r['samples']} samples (worst {r['worst']:.3g})")
    results["core"] = rows
    worst = E("""() => { const L = window.__lfo, pts = L.PRESETS.sine(), lv = pts.map((q) => q.y); let w = 0;
      for (let k = 0; k <= 200000; k++) { const u = k / 200001, ph = u * 2 * Math.PI; w = Math.max(w, Math.abs(L.levelOf(pts, lv, L.segAt(pts, u) >= 0 ? u : u) - L.coreWave("sine", ph))); } return w; }""")
    check(worst <= 1e-12, f"the drawn sine is the core's sin(phase) at 200 001 phases, worst {worst:.3g}")
    results["sineGrid"] = worst
    o = {"rate": 0.37, "sr": 48000, "seconds": 12, "seed": 11}
    r = E(PAIR, ["sine", "triangle", o]); null(r["worst"] <= 1e-12, f"the sine drawn with straight lines differs from lfo.h ({r['worst']:.3f})")
    # Reach (decided 19 Nov): full reach is today's Random to the bit at every rate above; a reach of
    # 0.3 is today's levels times 0.3 exactly; a reach of nought, the null, is still.
    for reach in (1, 0.3):
        pts_r = [{"x": 0, "y": reach, "law": "h", "m": 0.5, "r": True}]
        r = E("""([pts, o, reach]) => { const L = window.__lfo, a = { shape: "random", rate: o.rate, phase: 0, held: 0 }, ra = L.CoreRandom(o.seed);
          const b = { drawn: pts, rate: o.rate, phase: 0, phase0: 0 }, rb = L.CoreRandom(o.seed); L.drawnInit(b); let w = 0, most = 0;
          for (let s = 0; s < o.sr * o.seconds; s++) { const va = L.coreLfoStep(a, o.sr, ra) * reach, vb = L.drawnStep(b, o.sr, rb); w = Math.max(w, Math.abs(va - vb)); most = Math.max(most, Math.abs(vb)); } return { w, most }; }""", [pts_r, o, reach])
        check(r["w"] == 0 and r["most"] <= reach, f"a random point of reach {reach} is today's Random times {reach}, to the bit (worst {r['w']:.3g}), and never past ±{reach} (most {r['most']:.3f})")
    r = E(PAIR, ["random", [{"x": 0, "y": 0, "law": "h", "m": 0.5, "r": True}], o]); null(r["worst"] == 0, f"a random point of reach nought is still, and differs from today's Random ({r['worst']:.3f})")
    early = [{"x": 0, "y": 1, "law": "l", "m": 0.5, "r": True}]
    r = E(PAIR, ["random", early, o]); null(r["worst"] == 0, f"a random point rolled a line early differs from today's Random ({r['worst']:.3f})")
    r = E(PAIR, ["sine", "sine", dict(o, phase0=0.25)]); null(r["worst"] <= 1e-12, f"a phase of a quarter is read ({r['worst']:.3f} off)")

    # ---- the card draws the real shape; the dot sits on the line ----
    CARD = """([k, against]) => { const L = window.__lfo, S = L.S; S.clock = "stop"; S.size = "1400x900"; L.choosePreset(S.lfo[0], k); L.render();
      const l = S.lfo[0], svg = document.querySelector('[data-lfo-card="0"] svg.card-fig'), path = svg.querySelector('[data-card-curve="0"]').getAttribute("d");
      const pts = L.PRESETS[against](), lv = l.drawn ? l.lv.slice() : (l.legacy === "random" ? [l.held] : pts.map((q) => q.y));
      const lvA = against === k ? lv : pts.map((q) => q.y), h = 36, pad = 3, y = (v) => h / 2 - v * (h / 2 - pad);
      let w = 0; const nums = path.match(/[-0-9.]+/g).map(Number);
      for (let i = 0; i + 1 < nums.length; i += 2) { const x = nums[i], yy = nums[i + 1], u = x / 110; if (u <= 0.002 || u >= 0.998) continue;
        if (pts.some((q) => Math.abs(q.x - u) < 0.012)) continue;   // a jump is upright there
        w = Math.max(w, Math.abs(yy - y(L.levelOf(pts, lvA, u)))); }
      const dot = svg.querySelector("[data-card-now]"); return { w, n: nums.length / 2 }; }"""
    for k in PRESETS:
        r = E(CARD, [k, k]); check(r["w"] <= 0.6, f"the card draws {k} as it plays, to {r['w']:.2f} px over {r['n']:.0f} points")
    r = E(CARD, ["rampdown", "ramp"]); null(r["w"] <= 0.6, f"the saw down's card read against the saw up's levels ({r['w']:.1f} px off)")
    DOT = """(half) => { const L = window.__lfo, S = L.S; S.clock = "stop"; S.lfoOpen = 0; L.choosePreset(S.lfo[0], "sine"); const l = S.lfo[0]; l.phase = 0.3 * 2 * Math.PI; l.value = Math.sin(l.phase); L.render();
      const svg = document.querySelector("#lfoEd svg.plot"), g = svg._g, dot = svg.querySelector("[data-now]"), u = 0.3 + (half ? 0.5 : 0);
      return { dy: Math.abs(+dot.getAttribute("cy") - g.y(Math.sin(u * 2 * Math.PI))), dx: Math.abs(+dot.getAttribute("cx") - g.x(0.3)) }; }"""
    r = E(DOT, False); check(r["dy"] <= 0.5 and r["dx"] <= 0.5, f"the gold dot is on the line where the LFO is now ({r['dx']:.2f}, {r['dy']:.2f} px)")
    r = E(DOT, True); null(r["dy"] <= 0.5, f"the dot against the level half a cycle on ({r['dy']:.0f} px off)")

    # ---- the fit, one column, six windows ----
    surv = []
    for size in SIZES:
        for routes in ("few", "many"):
            m = E(SET, [size, "one", 0, routes])
            surv.append(m)
            ok = m["over"] <= 1 and 2 <= m["drawing"]["aspect"] <= 7 and m["drawing"]["h"] >= 120 and m["rowsShown"] >= min(3, m["routes"]) and m["footRows"] == 1 and m["toolsRows"] == 1 and not m["covers"]
            check(ok, f"{size}, {m['routes']} routings: one column fits, drawing {m['drawing']['w']}x{m['drawing']['h']} ({m['drawing']['aspect']}:1), {m['rowsShown']} routings in sight, one row each, clear")
    results["survey"] = surv
    two = []
    for size in SIZES:
        m = E(SET, [size, "two", 0, "many"]); two.append(m)
    results["two"] = two
    big = two[0]
    null(big["drawing"]["aspect"] >= 2, f"two columns at 1660x1050 make a tower ({big['drawing']['w']}x{big['drawing']['h']}, {big['drawing']['aspect']}:1)")
    r = E("""() => { const L = window.__lfo, S = L.S; S.size = "1200x680"; S.lfoLayout = "one"; S.lfoOpen = 0; S.routes = "many"; L.setRoutes(); L.render();
      const body = document.getElementById("lfoBody"), w = body.querySelector(".plot-wrap").clientWidth; body.style.setProperty("--draw-h", Math.floor(w / 2.4) + "px");
      const m = L.lfoMeasure(); body.style.removeProperty("--draw-h"); return m; }""")
    null(r["rowsShown"] >= 3 and r["over"] <= 1, f"the drawing at its full 2.4:1 at 1200x680, Where it goes ignored, leaves {r['rowsShown']} routings in sight")

    # ---- nothing moves ----
    STATES = [
        ("shape " + k, "(k) => { const L = window.__lfo; L.choosePreset(L.S.lfo[L.S.lfoOpen], k); }", k) for k in PRESETS
    ] + [
        ("tempo", "() => { const L = window.__lfo; L.setSync(L.S.lfo[L.S.lfoOpen], true); }", None),
        ("starts each note", "() => { window.__lfo.S.lfo[window.__lfo.S.lfoOpen].starts = 'note'; }", None),
        ("starts each phrase", "() => { window.__lfo.S.lfo[window.__lfo.S.lfoOpen].starts = 'phrase'; }", None),
        ("silenced", "() => { window.__lfo.S.lfo[window.__lfo.S.lfoOpen].silent = true; }", None),
        ("clock running", "() => { window.__lfo.S.clock = 'run'; }", None),
        ("a point selected", "() => { window.__lfo.S.lfoSel = { pt: 0 }; }", None),
        ("a note held", "() => { window.__figs_note && 0; noteDown(); }", None),
        ("LFO 2", "() => { window.__lfo.S.lfoOpen = 1; }", None),
    ]
    BASE = """(size) => { const L = window.__lfo, S = L.S; S.size = size; S.lfoLayout = "one"; S.lfoOpen = 0; S.routes = "few"; S.clock = "stop"; S.lfoSel = null; S.note = null;
      for (const l of S.lfo) { L.choosePreset(l, "sine"); l.sync = ""; l.starts = "free"; l.silent = false; } L.setRoutes(); L.render(); return L.lfoBoxes(); }"""
    def same(a, bb):
        keys = [k for k in a if k in bb]
        moved = [k for k in keys if any(abs(x - y) > 0.5 for x, y in zip(a[k], bb[k]))]
        # A routing row that is not there in the other state is the list's content (LFO 2 has its own), not a shift.
        missing = [k for k in a if k not in bb and not k.startswith("row ")]
        return moved + missing
    for size in SIZES:
        base = E(BASE, size)
        bad = []
        for name, js, arg in STATES:
            E(BASE, size)
            E(js, arg) if arg is not None else E(js)
            E("() => window.__lfo.render()")
            moved = same(base, E("() => window.__lfo.lfoBoxes()"))
            if moved: bad.append(name + ": " + ", ".join(moved[:4]))
        check(not bad, f"{size}: nothing moves across {len(STATES)} states, {len(base)} boxes" + ("; " + " | ".join(bad) if bad else ""))
    E(BASE, "1400x900")
    E("() => { const r = document.querySelector('[data-lfo-reading]'); }")
    NUDGE = "() => { const st = document.createElement('style'); st.id = 'nullReading'; st.textContent = '.lfo-ed .ed-head .reading { width: auto !important; flex: 0 0 auto !important; }'; document.head.appendChild(st); }"
    E(NUDGE); E("() => window.__lfo.render()"); before = E("() => window.__lfo.lfoBoxes()")
    E("() => { const L = window.__lfo; L.setSync(L.S.lfo[0], true); L.render(); }"); after = E("() => window.__lfo.lfoBoxes()")
    E("() => document.getElementById('nullReading').remove()")
    null(not same(before, after), "the reading sized to its words moves " + ", ".join(same(before, after)[:3]) + " when the rate goes to tempo")

    # ---- the setup ----
    E(BASE, "1400x900")
    untouched = E("() => window.__lfo.setupFields(window.__lfo.S.lfo[0])")
    check(set(untouched) == {"l0s", "l0r", "l0y"} and untouched["l0s"] == "sine", "an LFO untouched writes today's fields only: " + json.dumps(untouched))
    edited = E("() => { const L = window.__lfo, l = L.S.lfo[0]; L.editShape(l, (pts) => { pts[0].y = 0.7; pts.push({ x: 0.5, y: 0.2, law: 'm', m: 0.62, r: false }); }); return L.setupFields(l); }")
    pts = E("() => window.__lfo.S.lfo[0].drawn")
    def parse(t):
        parts = t.split(";"); assert parts[0] == "1"
        out = []
        for q in parts[1:]:
            f = q.split(",")
            law = f[2]; m = 0.5
            if law.startswith("m"): m = float(law[1:]); law = "m"
            out.append({"x": float(f[0]), "y": float(f[1]), "law": law, "m": m, "r": len(f) > 3 and f[3] == "r"})
        return out
    back = parse(edited["l0m"])
    rt = all(abs(a["x"] - b2["x"]) < 1e-5 and abs(a["y"] - b2["y"]) < 1e-5 and a["law"] == b2["law"] and a["r"] == b2["r"] and (a["law"] != "m" or abs(a["m"] - b2["m"]) < 1e-5) for a, b2 in zip(back, pts)) and len(back) == len(pts)
    check(edited["l0s"] == "drawn" and rt, "an edited LFO writes l0s drawn and l0m, which reads back to its points: " + edited["l0m"])
    sine_text = E("() => window.__lfo.shapeText(window.__lfo.PRESETS.sine())")
    check(sine_text == "1;.25,1,s;.75,-1,s", "the sine's twin is the text lfo-drawn.md gives: " + sine_text)
    null(edited.get("l0m") == untouched.get("l0m"), "the edited and untouched setups write different text")

    # ---- when it starts again ----
    E(BASE, "1400x900")
    STARTS = """() => { const L = window.__lfo, S = L.S; S.clock = "stop"; S.lfo[0].starts = "note"; S.lfo[1].starts = "phrase"; S.lfo[0].phase = S.lfo[1].phase = 1; L.playPhrase(); return S.lfo.map((l) => l.phase); }"""
    first = E(STARTS)
    E("() => { const S = window.__lfo.S; S.lfo[0].phase = S.lfo[1].phase = 1; }"); p.wait_for_timeout(520)
    later = E("() => window.__lfo.S.lfo.map((l) => l.phase)")
    check(first == [0, 0], "the first note of a phrase restarts Each note and Each phrase")
    check(later[0] == 0 and later[1] == 1, f"the second note restarts Each note and not Each phrase ({later})")
    E("() => { const S = window.__lfo.S; S.lfo[0].starts = 'free'; S.lfo[0].phase = 1; }")
    E("() => noteDown()"); free = E("() => window.__lfo.S.lfo[0].phase"); E("() => noteUp()")
    check(free == 1, "a note leaves a free LFO where it was")
    null(free == 0, "a free LFO's phase is seen not to be nought, so a restart could be seen")

    # ---- gestures, by real mouse ----
    p.goto(PAGE + "?shot=1&size=1400x900&lfo=0"); p.wait_for_function("window.__ready === true", timeout=30000); webfonts.settle(p)
    E("() => { window.__lfo.S.clock = 'stop'; window.__lfo.render(); }")
    was = E("() => window.__lfo.presetOf(window.__lfo.S.lfo[0])")
    null(was != "sine" or E("() => !!window.__lfo.S.lfo[0].drawn"), "before the drag it is today's sine, not drawn")
    pt = p.locator('#lfoEd [data-lpt="0"] .ring').bounding_box()
    p.mouse.move(pt["x"] + pt["width"] / 2, pt["y"] + pt["height"] / 2); p.mouse.down(); p.mouse.move(pt["x"] + 4, pt["y"] + 60, steps=6); p.mouse.up()
    after = E("() => { const l = window.__lfo.S.lfo[0]; return { drawn: !!l.drawn, y: l.drawn && l.drawn[0].y, s: window.__lfo.setupFields(l).l0s }; }")
    check(after["drawn"] and after["y"] < 0.95 and after["s"] == "drawn", f"dragging a point of today's sine adopts it and moves the point (to {after['y']})")
    n0 = E("() => window.__lfo.S.lfo[0].drawn.length")
    svg = p.locator("#lfoEd svg.plot").bounding_box()
    x = svg["x"] + svg["width"] * 0.62; g = E("() => { const g = document.querySelector('#lfoEd svg.plot')._g; return { y: g.y(window.__lfo.levelOf(window.__lfo.S.lfo[0].drawn, window.__lfo.S.lfo[0].lv, g.u(" + str(svg["width"] * 0.62) + "))), sc: 1 }; }")
    sc = svg["height"] / E("() => document.querySelector('#lfoEd svg.plot').clientHeight")
    p.mouse.dblclick(x, svg["y"] + g["y"] * sc)
    n1 = E("() => window.__lfo.S.lfo[0].drawn.length")
    check(n1 == n0 + 1, f"pressing the line twice adds a point ({n0} to {n1})")
    k = n1 - 1
    q = p.locator('#lfoEd [data-lpt] .ring').nth(1).bounding_box()
    p.mouse.dblclick(q["x"] + q["width"] / 2, q["y"] + q["height"] / 2)
    n2 = E("() => window.__lfo.S.lfo[0].drawn.length")
    check(n2 == n1 - 1, f"pressing a point twice takes it away ({n1} to {n2})")
    q = p.locator('#lfoEd [data-lpt="0"] .ring').bounding_box()
    p.mouse.click(q["x"] + q["width"] / 2, q["y"] + q["height"] / 2, button="right")
    menu = E("() => { const m = document.getElementById('ctx'); return !m.hidden && m.textContent.includes('A new level each pass') && m.textContent.includes('S-curve'); }")
    check(menu, "right-click on a point opens its menu: its line, a new level each pass, remove")

    # ---- the rate ----
    hz = E("() => { const L = window.__lfo, l = L.S.lfo[0]; L.setSync(l, true); l.sync = '1/4'; L.render(); return document.querySelector('[data-lfo-reading]').textContent; }")
    check(hz.startswith("2.00 Hz"), "1/4 at 120 is 2.00 Hz: " + hz)
    hz0 = E("() => { const L = window.__lfo, l = L.S.lfo[0]; L.setSync(l, false); L.render(); return document.querySelector('[data-lfo-reading]').textContent; }")
    null(hz0.startswith("2.00 Hz"), "the free rate reads " + hz0)

    # ---- a phone ----
    ph = b.new_page(viewport={"width": 430, "height": 900}); webfonts.route(ph)
    ph.goto(PAGE); ph.wait_for_function("window.__ready === true", timeout=60000)
    sw = ph.evaluate("() => document.documentElement.scrollWidth")
    check(sw <= 430, f"no horizontal page scroll at 430 px ({sw})")
    b.close()

results["checks"] = n[0]; results["failed"] = fails
json.dump(results, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json"), "w"), indent=1)
print(f"\n{n[0] - len(fails)} of {n[0]} checks pass")
sys.exit(1 if fails else 0)
