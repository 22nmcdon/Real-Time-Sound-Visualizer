"""The Ink-figures mockup's checks, in Chromium (web/docs/mockups/ink/index.html),
against the core itself.

Each check is fed a known-wrong case beside it (a null), and the null must be
seen to fail, as CLAUDE.md asks of every new assertion.

- the drawings are the core's sound: checks/core_ref.cpp is built against
  core/include and runs the real oscStep (osc.h) and shapeSample, setShaping
  and the crush's quantiser (voice.h). The mockup's drawing of each case is
  compared with it, point for point:
  * Unison's still, the copies' average 4.33 of the note's cycles in, at
    3, 5 and 7 copies, within 1e-6 of oscStep run that long (null: the still
    drawn at nought seconds); and the fan grows with Spread;
  * the smooth cases (FM, Ring, Warp on the sine, Unison, the harmonic at
    7:2) within 1e-6; a sine sub within 1e-3, since the core's sub steps
    before it reads and so runs one sample ahead of the note;
  * the cases with edges (Sync, the square) within 0.01 away from the edges.
    The core band-limits the edges and plays sync a sample late; the
    drawing is the shape both approach;
  * Warp on a shape other than the sine within 0.03: there the core takes the
    bend's offset out with a 5 Hz blocker, which ripples at the note, where
    the drawing takes out its settled mean;
  * the shaper's curve to 1e-15 at 2001 inputs, for drive, fold and bits.
  Nulls: the FM drawing against the core with FM off; the sub drawing
  against the core's sub two octaves down; drive's curve with the linear
  law (30 d where the core has 30 d^2);
- which drawing tells more: each control turned from nought, and how far the
  wave drawing's outline and the X-Y figure's outline move, in pixels on a
  300 px drawing. At Phase 0 the figure is the diagonal whatever the
  oscillator does: every control leaves it on the diagonal while the wave
  moves 10 px or more. Null: at Phase 90 FM takes it off the diagonal;
- the fit at the six windows, for each subtab and for the Oscillator drawn as
  the figure: nothing past the view, Ink not scrolled, every drawing that is
  a time 1.5:1 to 7:1 and 120 px tall, the curve and the figure square, the
  controls one row, clear of the modulation row, each summary fitting its
  label. Nulls: a drawing row 100 px taller than the room is seen to run
  over; a control row 300 px wide is seen to wrap;
- nothing moves: every box on Ink the same to half a pixel across nine
  settings, five shapes and both subtabs (outside the view). Null: the key
  over the wave sized to its words changes its box when the shape is renamed;
- Ink draws the settings, still: with Unison on and no control moving,
  neither the wave nor the screen redraws over 1.5 s. Null: the clock-driven
  redraw this replaced, put back, moves the wave. Hold to watch it drift moves
  the copies while held and lets go to the same still;
- Shaping stacks by room (the cycle over the curve) only where that gives the
  curve more than side by side and leaves the cycle 120 px tall, which is
  1660x1050, leaving little paper. Nulls: stacked forced at 960x600 shrinks
  the curve below side by side's; side by side forced at 1660x1050 leaves the paper;
- Wave · Figure moves nothing outside the drawing at the six windows (null:
  the figure's row sized to the figure moves the controls), and the choice is
  remembered by the browser (null: a fresh browser draws the wave);
- no console errors through every window, subtab and setting;
- a phone's width has no horizontal page scroll.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/ink/checks/ink_checks.py
"""
import os, sys, json, subprocess, tempfile
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import webfonts

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
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

# ---- the core, built from core/include ----
exe = os.path.join(tempfile.mkdtemp(), "core_ref")
subprocess.run(["g++", "-std=c++17", "-O2", "-I", os.path.join(ROOT, "core", "include"), os.path.join(HERE, "checks", "core_ref.cpp"), "-o", exe], check=True)
def core_osc(c):
    args = [exe, "osc", c["shape"], str(c.get("fm", 0)), str(c.get("ratio", 1)), str(c.get("warp", 0)), str(c.get("warpAt", 0.25)), str(c.get("ring", 0)),
            str(c.get("sync", 1)), str(c.get("sub", 0)), str(c.get("subOct", 1)), str(c.get("subSine", 0)), str(c.get("unison", 1)), str(c.get("cents", 12)),
            str(c.get("offset", 0)), str(c["cycles"]), str(c["points"])] + ([str(c["settle"])] if "settle" in c else [])
    return [float(x) for x in subprocess.run(args, capture_output=True, text=True, check=True).stdout.split()]
def core_shaper(d, f, bits):
    return [float(x) for x in subprocess.run([exe, "shaper", str(d), str(f), str(bits)], capture_output=True, text=True, check=True).stdout.split()]

SIZES = ["1660x1050", "1400x900", "1100x860", "1200x680", "1100x680", "960x600"]
CASES = [
    ("FM 2.0 at 3:2, left", dict(shape="sine", fm=2, ratio=1.5, cycles=2), 1e-6),
    ("FM 2.0 at 3:2, right at 90°", dict(shape="sine", fm=2, ratio=1.5, offset=90, cycles=2), 1e-6),
    ("Ring 70% at 2:1", dict(shape="sine", ring=0.7, ratio=2, cycles=1), 1e-6),
    ("Warp +0.54 at 25% on the sine", dict(shape="sine", warp=0.54, warpAt=0.25, cycles=1), 1e-6),
    ("Sub 50%, a square an octave down", dict(shape="sine", sub=0.5, cycles=2), 0.01),
    # The core's sub steps before it reads, so it runs one sample ahead of the note: 3.8e-4 rad at
    # this rate two octaves down, 1.3e-4 of level. The drawing is the sub on the beat.
    ("Sub 50%, a sine two octaves down", dict(shape="sine", sub=0.5, subOct=2, subSine=1, cycles=4), 1e-3),
    # Unison's copies drift apart: the core has run two seconds to settle, so the drawing is read at 2 s.
    ("Unison 3 at 12 cents, 2 s in", dict(shape="sine", unison=3, cents=12, cycles=1, t=2.0), 1e-6),
    ("the harmonic, FM 1.0 at 7:2", dict(shape="harmonic", fm=1, ratio=3.5, cycles=2), 1e-6),
    ("the saw, Sync 2.6×", dict(shape="ramp", sync=2.6, cycles=1), 0.01),
    ("the square", dict(shape="square", cycles=1), 0.01),
    ("Warp +0.54 on the triangle (the blocker)", dict(shape="triangle", warp=0.54, warpAt=0.25, cycles=1), 0.03),
]
JS = """([c, points]) => { const I = window.__ink, v = Object.assign({}, I.INK_START, { oscFm: (c.fm || 0) * 10, oscRatio: c.ratio || 1, oscBend: (c.warp || 0) / 0.009,
  oscBendAt: (c.warpAt == null ? 0.25 : c.warpAt) * 100, oscRing: (c.ring || 0) * 100, oscSync: (c.sync || 1) * 100, oscSub: (c.sub || 0) * 100, oscSubOct: c.subOct || 1,
  oscSubShape: c.subSine ? "sine" : "square", oscUnison: c.unison || 1, oscSpread: c.cents == null ? 12 : c.cents });
  I.S.genShape = c.shape; const T = I.toneOf(v); T.hz = 220; const out = I.channel(T, (c.offset || 0) * Math.PI / 180, points + 1, c.t || 0, c.cycles).v; I.S.genShape = "sine"; return out.slice(0, points); }"""

def compare(core, draw, edges):
    worst = 0
    for i in range(len(core)):
        if edges:
            near = any(abs(core[j] - core[j - 1]) > 0.05 for j in range(max(1, i - 2), min(len(core), i + 3)))
            if near: continue
        worst = max(worst, abs(core[i] - draw[i]))
    return worst

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    p = b.new_page(viewport={"width": 1700, "height": 1100})
    webfonts.route(p)
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.on("console", lambda m: m.type == "error" and errs.append(m.text))
    p.goto(PAGE + "?shot=1")
    p.wait_for_function("window.__ready === true", timeout=60000)
    faces = webfonts.settle(p)
    print("measured in " + ("the brand's webfonts" if faces else "FALLBACK faces: the webfonts did not load"))
    results["webfonts"] = faces
    E = lambda js, arg=None: p.evaluate(js, arg)

    # ---- the drawings are the core's sound ----
    rows = []
    for name, c, tol in CASES:
        pts = 512   # divides 4096 times the cycles, so the core prints exactly these phases
        core = core_osc(dict(c, points=pts)); draw = E(JS, [c, pts])
        w = compare(core, draw, tol >= 0.01)
        rows.append({"case": name, "worst": w, "tolerance": tol})
        check(w <= tol, f"{name}: the drawing is oscStep's output within {tol:g} (worst {w:.3g})")
    results["core"] = rows
    # Unison's still: the bold line, the copies' average at the moment drawn (4.33 of the note's cycles
    # in), is oscStep's output at that moment. The core is run that long exactly.
    still = E("() => window.__ink.STILL_CYCLES") / 220
    for n_, cents in ((3, 12), (5, 20), (7, 50)):
        # The core runs whole samples, so both are read at the sample nearest the still.
        at = round(still * 220 * 4096) / (220 * 4096)
        c = dict(shape="sine", unison=n_, cents=cents, cycles=1, t=at, settle=at)
        w = compare(core_osc(dict(c, points=512)), E(JS, [c, 512]), False)
        check(w <= 1e-6, f"Unison {n_} at {cents} cents, the still ({still * 1000:.2f} ms in): the bold line is oscStep's average within 1e-6 (worst {w:.3g})")
    c = dict(shape="sine", unison=5, cents=20, cycles=1, t=0, settle=round(still * 220 * 4096) / (220 * 4096))
    w = compare(core_osc(dict(c, points=512)), E(JS, [c, 512]), False)
    null(w <= 1e-6, f"the still drawn at nought seconds against oscStep at the still's moment ({w:.3f} off)")
    fan = E("""() => { const I = window.__ink, out = []; for (const cents of [5, 20, 50]) { const T = I.toneOf(Object.assign({}, I.INK_START, { oscUnison: 5, oscSpread: cents })); T.hz = 220;
      const t = I.stillT(T), lo = I.channel(Object.assign({}, T, { only: 0 }), 0, 400, t).v, hi = I.channel(Object.assign({}, T, { only: 4 }), 0, 400, t).v;
      out.push(Math.max(...lo.map((x, i) => Math.abs(x - hi[i])))); } return out; }""")
    check(fan[0] < fan[1] < fan[2] and fan[0] > 0.05, f"the still's fan grows with Spread: the outer copies apart by {fan[0]:.2f}, {fan[1]:.2f}, {fan[2]:.2f} at 5, 20 and 50 cents")
    c = CASES[0][1]
    w = compare(core_osc(dict(c, fm=0, points=512)), E(JS, [c, 512]), False)
    null(w <= 1e-6, f"the FM drawing against the core with FM off ({w:.2f} off)")
    c = CASES[4][1]
    w = compare(core_osc(dict(c, subOct=2, cycles=2, points=512)), E(JS, [c, 512]), True)
    null(w <= 0.01, f"the sub drawing against the core's sub two octaves down ({w:.2f} off)")
    SH = """([d, f, bits, linear]) => { const I = window.__ink, T = { drive: d, fold: f, bits }; const sh = I.shaperOf(T); const out = [];
      for (let i = 0; i <= 2000; i++) { const x = -1 + 2 * i / 2000; let v;
        if (linear) { const dr = 30 * d, n = dr > 0 ? 1 / Math.tanh(dr) : 1; v = dr > 0 ? Math.tanh(dr * x) * n : x; v = sh.quant(v); } else v = sh.quant(sh.shape(x)); out.push(v); } return out; }"""
    for d, f, bits in ((0.45, 0, 0), (0, 0.35, 0), (0.6, 0.2, 0), (0.45, 0, 4), (0.2, 0.05, 6), (1, 1, 1)):
        core = core_shaper(d, f, bits); draw = E(SH, [d, f, bits, False])
        w = max(abs(a - b2) for a, b2 in zip(core, draw))
        check(w <= 1e-15, f"the curve at drive {d}, fold {f}, {bits or 'no'} bits is shapeSample's to 1e-15 (worst {w:.3g})")
    core = core_shaper(0.45, 0, 0); w = max(abs(a - b2) for a, b2 in zip(core, E(SH, [0.45, 0, 0, True])))
    null(w <= 1e-15, f"drive's curve with the linear law ({w:.2f} off)")

    # ---- which drawing tells more ----
    t90 = E("() => window.__ink.tells(90)"); t0 = E("() => window.__ink.tells(0)")
    results["tells"] = {"phase90": t90, "phase0": t0}
    # At Phase 0 the two channels are one signal, so the figure is the diagonal whatever the oscillator
    # does (only its length changes, as Warp's offset moves it along): nothing off the diagonal.
    DIAG = """(phase) => { const I = window.__ink, out = [];
      for (const ch of [{ oscFm: 30 }, { oscBend: 60 }, { oscRing: 60 }, { oscSync: 250 }, { oscSub: 50 }, { oscRatio: 1.5, oscFm: 10 }, { oscUnison: 3 }]) {
        const T = I.toneOf(Object.assign({}, I.INK_START, { phase }, ch)); T.hz = 220;
        const L = I.channel(T, 0, 600, 0.25).v, R = I.channel(T, phase * Math.PI / 180, 600, 0.25).v;
        out.push(Math.max(...L.map((x, i) => Math.abs(x - R[i])))); } return out; }"""
    d0 = E(DIAG, 0)
    for r, off in zip(t0, d0):
        check(off < 1e-9 and r["waveOutline"] >= 10, f"at Phase 0, {r['name']} leaves the figure on the diagonal (off it by {off:.1g}) and moves the wave {r['waveOutline']} px")
    d90 = E(DIAG, 90)
    null(d90[0] < 1e-9, f"at Phase 90 FM takes the figure {d90[0]:.2f} off the diagonal")

    # ---- the fit ----
    SET = """([size, sub, shows, set, lay]) => { const I = window.__ink, S = I.S; S.size = size; S.inkSub = sub; S.inkShows = shows; S.shpLay = lay || "auto"; Object.assign(S.ink, I.INK_START, set || {}); I.render(); return I.inkMeasure(); }"""
    surv = []
    for size in SIZES:
        for sub, shows in (("osc", "wave"), ("osc", "figure"), ("shp", "wave")):
            m = E(SET, [size, sub, shows, {"oscFm": 20, "oscRatio": 1.5, "shpDrive": 45, "shpBits": 4}])
            surv.append(m)
            timey = [q for q in m["plots"] if q["what"] in ("wave", "cycle")]
            square = [q for q in m["plots"] if q["what"] in ("xy", "transfer")]
            ok = (m["scroll"] <= 1 and m["over"] <= 1 and all(1.5 <= q["aspect"] <= 7 and q["h"] >= 120 for q in timey)
                  and all(0.85 <= q["aspect"] <= 1.25 and q["h"] >= 120 for q in square) and all(r == 1 for r in m["knobRows"]) and not m["covers"]
                  and all(l["fits"] for l in m["labels"]))
            check(ok, f"{size}, {sub}{' as the figure' if shows == 'figure' else ''}{', ' + str(m.get('shpLay')) if sub == 'shp' else ''}: fits, " + ", ".join(f"{q['what']} {q['w']}x{q['h']} ({q['aspect']}:1)" for q in m["plots"]) + f", one row, {m['empty']:.0f} px of paper spare")
    results["survey"] = surv
    # Shaping stacks by room: only where stacking gives the curve more than side by side and leaves the
    # cycle 120 px tall. Where it stacks, the paper left is small. Nulls: stacked forced at 960x600 makes
    # a curve under 120 px; side by side forced at 1660x1050 leaves the paper this replaced.
    stacked = [m["size"] for m in surv if m["sub"] == "shp" and m.get("shpLay") == "stacked"]
    big = next(m for m in surv if m["sub"] == "shp" and m["size"] == "1660x1050")
    check("1660x1050" in stacked and big["empty"] <= 60, f"Shaping stacks by room at {', '.join(stacked) or 'no window'}, leaving {big['empty']:.0f} px of paper at 1660x1050")
    forced = E(SET, ["960x600", "shp", "wave", {"shpDrive": 45}, "stacked"])
    curve = next(q for q in forced["plots"] if q["what"] == "transfer")
    sideCurve = next(q for q in next(m for m in surv if m["sub"] == "shp" and m["size"] == "960x600")["plots"] if q["what"] == "transfer")
    null(curve["h"] >= sideCurve["h"], f"stacked forced at 960x600 shrinks the curve to {curve['w']}x{curve['h']}, from side by side's {sideCurve['w']}x{sideCurve['h']}")
    forced = E(SET, ["1660x1050", "shp", "wave", {"shpDrive": 45}, "side"])
    null(forced["empty"] <= 60, f"side by side forced at 1660x1050 leaves {forced['empty']:.0f} px of paper")
    over = E("""() => { const I = window.__ink, S = I.S; S.size = "1400x900"; S.inkSub = "osc"; S.inkShows = "wave"; I.render();
      const row = document.querySelector('[data-ink-row="osc"]'); row.style.height = (row.parentElement.clientHeight) + "px"; return I.inkMeasure(); }""")
    null(over["over"] <= 1 and over["scroll"] <= 1, f"a drawing row given the whole view runs {over['over']} px over")
    wrap = E("""() => { const I = window.__ink; I.render(); const k = document.querySelector('.fview:not([hidden]) .knobs.fig'); k.style.width = "300px"; k.style.flexWrap = "wrap"; return I.inkMeasure(); }""")
    null(all(r == 1 for r in wrap["knobRows"]), f"a control row 300 px wide wraps into {wrap['knobRows']} rows")

    # ---- nothing moves ----
    SETTINGS = [{}, {"oscUnison": 3}, {"oscFm": 20, "oscRatio": 1.5}, {"oscBend": 60}, {"oscRing": 70, "oscRatio": 2}, {"oscSync": 260}, {"oscSub": 60}, {"oscUnison": 5, "oscSpread": 20},
                {"shpDrive": 45, "shpBits": 4}, {"shpFold": 35, "shpRate": 2000}]
    STATE = """([size, sub, set, shape]) => { const I = window.__ink, S = I.S; S.size = size; S.inkSub = sub; S.inkShows = "wave"; S.genShape = shape; Object.assign(S.ink, I.INK_START, set); I.render(); return I.inkBoxes(); }"""
    def moved(a, bb):
        return [k for k in a if k in bb and any(abs(x - y) > 0.5 for x, y in zip(a[k], bb[k]))] + [k for k in a if k not in bb]
    for size in SIZES:
        bad = []
        for sub in ("osc", "shp"):
            base = E(STATE, [size, sub, {}, "sine"])
            for s in SETTINGS:
                for shape in ("sine", "harmonic", "triangle", "ramp", "square"):
                    mv = moved(base, E(STATE, [size, sub, s, shape]))
                    if mv: bad.append(f"{sub} {json.dumps(s)} {shape}: " + ", ".join(mv[:3]))
        a = E(STATE, [size, "osc", {}, "sine"]); bb = E(STATE, [size, "shp", {}, "sine"])
        outside = moved({k: v for k, v in a.items() if not k.startswith("view ")}, {k: v for k, v in bb.items() if not k.startswith("view ")})
        if outside: bad.append("the subtabs: " + ", ".join(outside[:3]))
        check(not bad, f"{size}: nothing moves across {len(SETTINGS)} settings, 5 shapes and both subtabs" + ("; " + " | ".join(bad[:3]) if bad else ""))
    # Wave · Figure moves nothing outside the drawing.
    WF = """([size, shows]) => { const I = window.__ink, S = I.S; S.size = size; S.inkSub = "osc"; S.inkShows = shows; Object.assign(S.ink, I.INK_START, { oscFm: 20, oscRatio: 1.5 }); I.render();
      const b = I.inkBoxes(); for (const k of Object.keys(b)) if (k.includes("drawing")) delete b[k]; return b; }"""
    bad = []
    for size in SIZES:
        mv = moved(E(WF, [size, "wave"]), E(WF, [size, "figure"]))
        if mv: bad.append(size + ": " + ", ".join(mv[:3]))
    check(not bad, "Wave · Figure moves nothing outside the drawing at the six windows" + ("; " + " | ".join(bad) if bad else ""))
    E("() => { const st = document.createElement('style'); st.id = 'nullFig'; st.textContent = '.ink-row.figure-mode { height: auto !important; flex: 1 1 auto !important; } .ink-row.figure-mode .plot-wrap.figure { height: 200px !important; }'; document.head.appendChild(st); }")
    a = E(WF, ["1400x900", "wave"]); bb = E(WF, ["1400x900", "figure"])
    E("() => document.getElementById('nullFig').remove()")
    null(not moved(a, bb), "the figure's row sized to the figure moves " + ", ".join(moved(a, bb)[:3]))
    E("() => { const st = document.createElement('style'); st.id = 'nullKey'; st.textContent = '.key-ink { width: auto !important; flex: 0 0 auto !important; }'; document.head.appendChild(st); }")
    a = E(STATE, ["1400x900", "osc", {}, "sine"]); bb = E(STATE, ["1400x900", "osc", {}, "triangle"])
    E("() => document.getElementById('nullKey').remove()")
    null(not moved(a, bb), "the key sized to its words changes " + ", ".join(moved(a, bb)[:3]) + " when the shape goes from sine to triangle")

    # ---- nothing redraws by itself ----
    STILLNESS = """(live) => new Promise((done) => { const I = window.__ink, S = I.S; document.body.classList.remove("shot"); S.size = "1400x900"; S.inkSub = "osc";
      Object.assign(S.ink, I.INK_START, { oscUnison: 5, oscSpread: 20 }); S.liveNull = live; S.nullT = 0; I.render();
      const d0 = document.querySelector('[data-ink-plot="wave"] [data-left]').getAttribute("d"), s0 = document.getElementById("screen").toDataURL();
      setTimeout(() => { const d1 = document.querySelector('[data-ink-plot="wave"] [data-left]').getAttribute("d"), s1 = document.getElementById("screen").toDataURL();
        S.liveNull = false; document.body.classList.add("shot"); done({ wave: d0 === d1, screen: s0 === s1 }); }, 1500); })"""
    r = E(STILLNESS, False)
    check(r["wave"] and r["screen"], "with Unison on and no control moving, nothing on Ink redraws over 1.5 s (the wave and the screen)")
    r = E(STILLNESS, True)
    null(r["wave"], "the clock-driven redraw put back moves the wave within 1.5 s")
    drift = E("""() => new Promise((done) => { const I = window.__ink, S = I.S; Object.assign(S.ink, I.INK_START, { oscUnison: 5, oscSpread: 20 }); I.render();
      const b = document.querySelector("[data-drift]"), r = b.getBoundingClientRect(), d0 = document.querySelector('[data-ink-plot="wave"] [data-left]').getAttribute("d");
      b.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, button: 0, pointerId: 1, clientX: r.left + 4, clientY: r.top + 4 }));
      setTimeout(() => { const d1 = document.querySelector('[data-ink-plot="wave"] [data-left]').getAttribute("d");
        document.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, pointerId: 1 }));
        const d2 = document.querySelector('[data-ink-plot="wave"] [data-left]').getAttribute("d"); done({ held: d1 !== d0, after: d2 === d0 }); }, 600); })""")
    check(drift["held"] and drift["after"], "Hold to watch it drift moves the copies while held, and lets go back to the very same still")

    check(not errs, "no console errors through every window, subtab and setting" + (": " + "; ".join(errs[:3]) if errs else ""))
    # Wave · Figure is remembered per browser, never in the setup. Null: a fresh browser draws the wave.
    ctx = b.new_context(viewport={"width": 1700, "height": 1100}); q = ctx.new_page(); webfonts.route(q)
    q.goto(PAGE + "?shot=1"); q.wait_for_function("window.__ready === true", timeout=60000)
    fresh = q.evaluate("() => window.__ink.S.inkShows")
    q.click('[data-draws="figure"]'); q.reload(); q.wait_for_function("window.__ready === true", timeout=60000)
    kept = q.evaluate("() => window.__ink.S.inkShows")
    check(kept == "figure", "Figure chosen is remembered by the browser across a reload")
    null(fresh == "figure", "a fresh browser draws " + fresh)
    ctx.close()
    ph = b.new_page(viewport={"width": 430, "height": 900}); webfonts.route(ph)
    ph.goto(PAGE); ph.wait_for_function("window.__ready === true", timeout=90000)
    sw = ph.evaluate("() => document.documentElement.scrollWidth")
    check(sw <= 430, f"no horizontal page scroll at 430 px ({sw})")
    b.close()

results["checks"] = n[0]; results["failed"] = fails
json.dump(results, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json"), "w"), indent=1)
print(f"\n{n[0] - len(fails)} of {n[0]} checks pass")
sys.exit(1 if fails else 0)
