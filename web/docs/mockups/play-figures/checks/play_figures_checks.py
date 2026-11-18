"""The figure-area mockup's checks, in Chromium (web/docs/mockups/play-figures/index.html).

Each check is fed a known-wrong case first or beside it (a null), and the null
must be seen to fail, as CLAUDE.md asks of every new assertion.

- no console errors through every window, subtab, filter layout and both
  hands settings, with a note held;
- at the five windows fittest.py uses and at 1660x1050, for each subtab as
  shown (the filter's layout by room), two hands with the amp unlinked too:
  * nothing between the band and the settings row (a gap of at most 8 px,
    no element in it). Null: a 250 px block put there is seen;
  * Play does not scroll, and nothing of the view runs past its foot. Null: a
    figure area made 2000 px tall is seen to scroll;
  * the figure area and the tab clear the modulation row and the Picture
    section. Null: the tab moved down 120 px is seen to cover them;
  * every knob row and both settings rows in one row. Null: a knob row
    squeezed to 120 px is seen to wrap;
  * every drawing wide: between 1.5:1 and 7:1, the amp's and the Envelope's
    at least 2:1, and none under 120 px tall. Null: the figure area squeezed
    to the popover's 254 px is seen to make a tower;
  * each subtab's summary fits its label, and which were shortened is
    recorded. Null: a summary three times as long is seen not to fit;
- the drawing: the -3.1 dB sustain run drawn at 0.70 of the height (straight
  amplitude), to half a pixel; null, the decibel law's place, more than 5 px
  away;
- the level the drawing and the screen follow is round 3's, to 1e-12, over a
  grid of times with the key up at 300 ms, for every shape (the sustain point
  moved and the one-shot added to it, nothing else). Null: a shape with its
  sustain moved to the peak must differ;
- Sustain here moves the held run to the point; No sustain takes the run and
  the key-up tick away and plays through with the key let go. Nulls: before
  the move the run starts elsewhere; with a sustain, letting go changes it;
- two hands, the amp unlinked: the other hand's shape is drawn dashed; linked,
  it is not;
- the Envelope follows the amp envelope dashed and grey until a knob is
  turned, then is its own in sage; Follow puts it back;
- Hold a note: the gold dot moves along the shape;
- a phone's width has no horizontal page scroll.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/play-figures/checks/play_figures_checks.py
"""
import os, sys, json, math
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = "file://" + os.path.join(HERE, "index.html")
ROUND3 = "file://" + os.path.join(os.path.dirname(HERE), "mseg", "popover.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
fails, n = [], [0]

def check(ok, what):
    n[0] += 1
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)

def null(wrong_passes, what):
    """A null: the check, fed a known-wrong case, must fail."""
    check(not wrong_passes, "null: " + what)

def judge(m):
    fit = m["scroll"] <= 1 and m["viewOver"] <= 1
    nothing = m["gapBandToSettings"] <= 8 and m["between"] == 0
    clear = not m["coversModrow"] and not m["coversPicture"]
    one = all(r == 1 for r in m["knobRows"])
    wide = all(1.5 <= p["aspect"] <= 7 and p["h"] >= 120 and (p["what"] in ("response", "fenv") or p["aspect"] >= 2) for p in m["plots"])
    fits = all(v["fits"] for v in m["labels"].values())
    return dict(fit=fit, nothing=nothing, clear=clear, one=one, wide=wide, fits=fits)

SIZES = ["1660x1050", "1400x900", "1100x860", "1200x680", "1100x680", "960x600"]
CASES = [("amp", 1, "auto"), ("filter", 1, "auto"), ("menv", 1, "auto"), ("amp", 2, "auto")]
SET = """([size, sub, hands, flay]) => { const F = window.__figs, S = F.S; S.size = size; S.sub = sub; S.hands = hands; S.flay = flay;
  S.linked.amp = hands !== 2; if (hands === 2) upperOwn(); S.note = null; F.render(); return F.measureNow(); }"""
results = {"rows": []}

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    p = b.new_page(viewport={"width": 1300, "height": 900})
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.on("console", lambda m: m.type == "error" and errs.append(m.text))
    p.goto(PAGE)
    p.wait_for_function("window.__ready === true", timeout=20000)

    # Every switch, a note held.
    for size in SIZES:
        for sub in ("amp", "filter", "menv"):
            for flay in ("auto", "side", "stacked"):
                p.evaluate(SET, [size, sub, 2 if sub == "amp" else 1, flay])
    p.evaluate("() => window.__figs.noteDown()"); p.wait_for_timeout(300)
    p.evaluate("() => window.__figs.noteUp()"); p.wait_for_timeout(300)
    check(not errs, "no console errors through every window, subtab, filter layout and both hands settings, with a note held" + (": " + "; ".join(errs[:3]) if errs else ""))

    # ---- the fit ----
    for size in SIZES:
        for sub, hands, flay in CASES:
            m = p.evaluate(SET, [size, sub, hands, flay])
            j = judge(m)
            results["rows"].append(m)
            tag = "%s, %s%s%s" % (size, sub, " (filter %s)" % m["flayUsed"] if sub == "filter" else "", ", two hands, amp unlinked" if hands == 2 else "")
            check(j["nothing"], tag + ": nothing between the band and the settings row (%s px)" % m["gapBandToSettings"])
            check(j["fit"], tag + ": Play does not scroll and the view's content is inside it (scroll %s, view %s)" % (m["scroll"], m["viewOver"]))
            check(j["clear"], tag + ": clear of the modulation row and the Picture section")
            check(j["one"], tag + ": every knob row and settings row in one row %s" % m["knobRows"])
            check(j["wide"], tag + ": drawings wide, %s" % ", ".join("%s %dx%d %.1f:1" % (q["what"], q["w"], q["h"], q["aspect"]) for q in m["plots"]))
            check(j["fits"], tag + ": the subtab summaries fit their labels (shortened: %s)" % ([k for k, v in m["labels"].items() if v["dropped"]] or "none"))

    # Nulls, each at the tightest window, on the measurement the check reads.
    p.evaluate(SET, ["960x600", "amp", 2, "auto"])
    m = p.evaluate("""() => { const d = document.createElement('div'); d.style.height = '250px'; d.style.flex = '0 0 auto';
      document.getElementById('band').after(d); return window.__figs.measureNow(); }""")
    null(judge(m)["nothing"], "a 250 px block between the band and the settings row is seen (%s px)" % m["gapBandToSettings"])
    p.evaluate(SET, ["960x600", "amp", 2, "auto"])
    m = p.evaluate("() => { document.getElementById('figs').style.minHeight = '2000px'; return window.__figs.measureNow(); }")
    null(judge(m)["fit"], "a figure area 2000 px tall is seen to scroll (%s px)" % m["scroll"])
    p.evaluate(SET, ["960x600", "amp", 2, "auto"])
    m = p.evaluate("() => { const b = document.getElementById('playBody'); b.style.top = (parseFloat(b.style.top) + 120) + 'px'; return window.__figs.measureNow(); }")
    null(judge(m)["clear"], "the tab moved down 120 px is seen to cover the modulation row")
    p.evaluate(SET, ["960x600", "amp", 2, "auto"])
    m = p.evaluate("() => { const k = document.querySelector('.fview:not([hidden]) .knobs.fig'); k.style.flexWrap = 'wrap'; k.style.width = '120px'; return window.__figs.measureNow(); }")
    null(judge(m)["one"], "a knob row squeezed to 120 px is seen to wrap %s" % m["knobRows"])
    p.evaluate(SET, ["1660x1050", "amp", 1, "auto"])
    m = p.evaluate("() => { const f = document.getElementById('figs'); f.style.width = '254px'; f.style.flex = '1 1 auto'; window.__figs.paint(); return window.__figs.measureNow(); }")
    null(judge(m)["wide"], "a figure area squeezed to the popover's 254 px is seen to make a tower (%s)" % [(q["w"], q["h"]) for q in m["plots"]])
    p.evaluate(SET, ["960x600", "amp", 1, "auto"])
    over = p.evaluate("""() => { const s = document.querySelector('[data-sum="amp"]'); s.textContent = s.textContent.repeat(3); return s.scrollWidth <= s.clientWidth + 0.5; }""")
    null(over, "a summary three times as long is seen not to fit its label")

    # ---- the drawing ----
    p.evaluate(SET, ["1400x900", "amp", 1, "auto"])
    d = p.evaluate("""() => { const svg = document.querySelector('svg.plot[data-kind="amp"]'), g = svg._g;
      const held = svg.querySelector('[data-held]').getAttribute('d'), y = parseFloat(held.split(' ')[1]);
      const e = window.__figs.S.amp[0];
      return { y, want: g.T + (1 - e.m.sus) * (g.B - g.T), db: g.T + (20 * Math.log10(e.m.sus) / -48) * (g.B - g.T), sus: e.m.sus }; }""")
    check(abs(d["y"] - d["want"]) <= 0.5, "the -3.1 dB sustain is drawn at %.2f of the height in straight amplitude (y %.1f, want %.1f)" % (d["sus"], d["y"], d["want"]))
    null(abs(d["y"] - d["db"]) <= 5, "the decibel law would put it %.1f px away" % abs(d["y"] - d["db"]))

    # The law against round 3's, shape for shape.
    q = b.new_page(); q.goto(ROUND3); q.wait_for_timeout(1500)
    SHAPES = ["ADSR", "AHDSR", "Pluck", "Swell", "Gate", "Pulse"]
    GRID = "Array.from({length: 120}, (_, i) => i * 31)"
    theirs = q.evaluate("(names) => names.map((n) => " + GRID + ".map((t) => levelAt(SHAPES[n](), t, 300)))", SHAPES)
    ours = p.evaluate("(names) => names.map((n) => " + GRID + ".map((t) => window.__figs.levelAt(SHAPES[n](), t, 300)))", SHAPES)
    worst = max(abs(a - c) for A, C in zip(theirs, ours) for a, c in zip(A, C))
    check(worst <= 1e-12, "the level is round 3's for every shape, the key up at 300 ms (worst %.1e)" % worst)
    moved = p.evaluate("() => { const e = SHAPES.ADSR(); e.sus = 2; return " + GRID + ".map((t) => window.__figs.levelAt(e, t, 300)); }")
    null(max(abs(a - c) for a, c in zip(theirs[0], moved)) <= 1e-6, "the sustain moved to the peak differs from it")
    q.close()

    # Sustain here, and No sustain.
    p.evaluate(SET, ["1400x900", "amp", 1, "auto"])
    s = p.evaluate("""() => { const F = window.__figs, svg = () => document.querySelector('svg.plot[data-kind="amp"]');
      const start = () => parseFloat(svg().querySelector('[data-held]').getAttribute('d').slice(1).split(' ')[0]);
      const cx = (id) => parseFloat(svg().querySelector('[data-pt="' + id + '"] .ring').getAttribute('cx'));
      const before = start(), peak = cx('pre2');
      openMenu('amp', 'pre2', 100, 100); document.querySelector('#ctx [data-act="sushere"]').click();
      const after = start(), peakNow = cx('pre2');
      openMenu('amp', 'pre2', 100, 100); document.querySelector('#ctx [data-act="oneshot"]').click();
      const one = { held: !!svg().querySelector('[data-held]'), tick: !!svg().querySelector('[data-keyup]'), said: !!svg().querySelector('[data-oneshot]') };
      const e = F.S.amp[0], let_go = F.levelAt(e, 60, 10), held_on = F.levelAt(e, 60, null);
      openMenu('amp', 'pre2', 100, 100); document.querySelector('#ctx [data-act="susback"]').click();
      const e2 = F.S.amp[0], with_sus = [F.levelAt(e2, 400, 100), F.levelAt(e2, 400, null)];
      return { before, peak, after, peakNow, one, let_go, held_on, with_sus, back: F.S.amp[0].sus }; }""")
    check(abs(s["after"] - s["peakNow"]) <= 0.5, "Sustain here on the peak starts the held run at the peak (%.1f, the peak at %.1f)" % (s["after"], s["peakNow"]))
    null(abs(s["before"] - s["peak"]) <= 0.5, "before it, the run started at the decay's end, not the peak (%.1f against %.1f)" % (s["before"], s["peak"]))
    check(not s["one"]["held"] and not s["one"]["tick"] and s["one"]["said"], "No sustain takes the held run and the key-up tick away and says one shot")
    check(abs(s["let_go"] - s["held_on"]) <= 1e-12, "a one-shot plays through: letting go at 10 ms changes nothing at 60 ms")
    null(abs(s["with_sus"][0] - s["with_sus"][1]) <= 1e-6, "with a sustain, letting go at 100 ms changes the level at 400 ms")
    check(s["back"] is None, "Sustain at the decay's end puts it back")

    # Two hands.
    p.evaluate(SET, ["1400x900", "amp", 2, "auto"])
    ghost = p.evaluate("() => !!document.querySelector('svg.plot[data-kind=\"amp\"] [data-ghost]')")
    check(ghost, "two hands, the amp unlinked: the upper hand's shape drawn dashed behind")
    linked = p.evaluate("() => { window.__figs.S.linked.amp = true; window.__figs.render(); return !!document.querySelector('svg.plot[data-kind=\"amp\"] [data-ghost]'); }")
    null(linked, "linked, no other hand is drawn")
    pill = p.evaluate("() => { window.__figs.S.linked.amp = false; window.__figs.render(); const b = document.querySelector('.fview:not([hidden]) .fhead [data-link=\"amp\"]'); return b ? b.textContent : null; }")
    check(pill == "Lower’s own", "the link pill is in the subtab's header and says Lower’s own (%r)" % pill)

    # The Envelope.
    p.evaluate(SET, ["1400x900", "menv", 1, "auto"])
    f = p.evaluate("""() => { const F = window.__figs, c = () => document.querySelector('svg.plot[data-kind="menv"] [data-curve]');
      F.S.menv.own = false; F.render();
      const a = [c().getAttribute('stroke'), c().getAttribute('stroke-dasharray'), document.querySelector('[data-sum="menv"]').textContent];
      knobDef('menv-attack').set(0.3);
      const b = [c().getAttribute('stroke'), c().getAttribute('stroke-dasharray'), F.S.menv.own];
      document.querySelector('[data-follow]').click();
      return { a, b, back: F.S.menv.own }; }""")
    check(f["a"][0] == "var(--unresolved)" and f["a"][1] != "none" and f["a"][2] == "follows the amp", "the Envelope follows the amp envelope: dashed, grey, and its label says so")
    check(f["b"][0] == "var(--ch4)" and f["b"][1] == "none" and f["b"][2], "a knob turned makes it its own, solid in sage")
    null(f["a"][0] == f["b"][0], "following and its own are not drawn alike")
    check(f["back"] is False, "Follow puts it back")

    # Hold a note.
    p.evaluate(SET, ["1400x900", "amp", 1, "auto"])
    dots = p.evaluate("""async () => { const F = window.__figs, at = () => { const c = document.querySelector('svg.plot[data-kind="amp"] [data-now]'); return c ? +c.getAttribute('cx') : null; };
      F.noteDown(); await new Promise((r) => setTimeout(r, 60)); const a = at(); await new Promise((r) => setTimeout(r, 250)); const b = at(); F.noteUp(); return [a, b]; }""")
    check(dots[0] is not None and dots[1] is not None and dots[1] > dots[0] + 5, "Hold a note: the gold dot moves along the shape (%s)" % dots)

    # A phone.
    ph = b.new_page(viewport={"width": 390, "height": 800}); ph.goto(PAGE); ph.wait_for_function("window.__ready === true", timeout=20000)
    check(ph.evaluate("() => document.documentElement.scrollWidth <= innerWidth"), "a phone's width has no horizontal page scroll")
    ph.close()

    results["checks"] = n[0]; results["fails"] = fails
    with open(os.path.join(HERE, "checks", "results.json"), "w") as fh:
        json.dump(results, fh, indent=1, ensure_ascii=False)

print("%d checks, %d failed" % (n[0], len(fails)))
sys.exit(1 if fails else 0)
