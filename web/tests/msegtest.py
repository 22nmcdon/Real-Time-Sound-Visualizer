"""The drawn envelopes (18 Nov, web/docs/mseg-design.md): the small blocks on
Play, the editor that opens beside them, the Envelope card's, and the knobs'
laws. It replaced dragenvtest.py, which held the drawing of 17 Nov - three
handles on a fixed ADSR curve (the peak, the corner, the end), the voice
filter's drawing opened from its heading over its section, and the Envelope
following the amp envelope until edited. What that suite asserted and where
it went:

- a handle writing its knob by the drawing's square-root scale, and not a
  straight one's: kept, for the attack's and the release's points and the
  decay's (with the sustain), on the new drawing's geometry;
- one undo step a drag, none while held, and undo putting it back: kept;
- a handle under the pointer that let it go: kept;
- every handle on its curve within half a pixel: the curve is now sampled
  from the shape, so the check is the point's centre against the shape's
  own level at its time, with its null four pixels off;
- the keyboard (Tab, the arrows, Shift finer, an arrow that means nothing):
  kept, with Delete on a point you added;
- the menu (right-click, Shift+F10, Type a value, Reset naming where it
  starts, two presses putting it back): kept, and the new items - Sustain
  here, No sustain, Loop from here, Remove;
- the hands: a drag on the upper hand of an unlinked split writes the upper
  hand's alone: kept, with the other hand's shape drawn dashed behind;
- the Envelope following until edited, and an edit copying the amp's into
  its own in one undo step: kept, now with the delay, the hold and the shape;
- the filter's drawing opened from its heading, over its section, with Esc
  and a press elsewhere shutting it: replaced by the popover's rules - beside
  its block over the neighbouring column, never over its block, the band or
  the screen, its knobs in one row, at all five windows - and the same Esc
  and press.

New here: the page's maths held to the core's (the shape's text read the
same way, the curve the engine plays), a point added on the line that changes
nothing heard, a one-shot and a moved sustain point by the menu, the loop,
the knobs' laws (square-root time, the amp's sustain in decibels), and a
drawn shape reaching the instrument. Each check has its null beside it.
"""
import json, os, subprocess, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(ART)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    """A check's null: the same comparison fed a value it must reject."""
    check("null: " + name, red, detail)

def open_page(b, w=1400, h=900):
    p = b.new_page(viewport={"width": w, "height": h})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(900)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(200)
    return p, bad

def centre(p, sel):
    box = p.locator(sel).bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

def drag(p, sel, dx, dy, hold=None):
    x, y = centre(p, sel)
    p.mouse.move(x, y); p.mouse.down()
    p.mouse.move(x + dx / 2, y + dy / 2, steps=4); p.mouse.move(x + dx, y + dy, steps=4)
    held = hold() if hold else None
    p.mouse.up()
    return (x + dx, y + dy), held

AMP = "() => ['envDelay', 'envAttack', 'envHold', 'envDecay', 'envSustain', 'envRelease'].map((id) => Number(el[id].value))"
UNDO = "() => undoHistory.undo.length"
PT = lambda svg, key: '#%s [data-handle="%s"]' % (svg, key)
# The shape's text and points as the page reads them.
POINTS = "(kind) => { const n = msegNow(kind); const P = msegPoints(n.shape, n.m); return { text: el[MSEG_KINDS[kind].shapeId].value, last: P.last, sus: P.susPt, loop: P.loopPt, pts: P.pts.map((q) => [q.role, q.t, q.lvl]) }; }"

# --- the core's parse and engine, for the page's maths to be held to ---
BUILD = os.path.join(ROOT, "core", "build", "msegtest")
os.makedirs(BUILD, exist_ok=True)
EXE = os.path.join(BUILD, "mseg_cpp")
subprocess.run(["g++", "-std=c++17", "-O2", "-I", os.path.join(ROOT, "core", "include"),
                os.path.join(ROOT, "core", "tests", "tools", "mseg_cpp.cpp"), "-o", EXE], check=True)
def core_parse(text):
    out = subprocess.run([EXE, "parse", text], check=True, capture_output=True, text=True).stdout.split("\n")
    w = out[0].split()
    return {"ok": w[0] == "ok", "count": int(w[2]), "sus": int(w[4]), "loop": int(w[6])}
def core_blend(a, b, t):
    return subprocess.run([EXE, "blend", a, b, repr(t)], check=True, capture_output=True, text=True).stdout.rstrip("\n")
def core_trace(text, a, d, s, r, up, n, rate=48000):
    path = os.path.join(BUILD, "trace.txt")
    with open(path, "w") as f:
        f.write("rate %d\ntone attackMs %r\ntone decayMs %r\ntone sustain %r\ntone releaseMs %r\nshape %s\nrun %d\nreset 0\nat 0 gate 1 1\nat %d gate 0\n"
                % (rate, a, d, s, r, text, n, up))
    return [float.fromhex(l.split()[0]) for l in subprocess.run([EXE, "new", path], check=True, capture_output=True, text=True).stdout.split("\n") if l.strip()]

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p, bad = open_page(b)

    print("\n--- the page's maths is the core's ---")
    TEXTS = ["1;A>p.2;D>p.2;R>a.2", "1;A>m.62;D.4,.18,m.72>m.3;R.35,.35,m.65>a.2;L3", "1;A>l;D>l;R>l;S2", "1;A>l;D>l;R>l;S-",
             "1;W.5,.2,l>l;A>m.8;H>l;D>m.3;R>m.7", "", "junk", "1;A.5,.5>l", "1;Q>l", "1;A>m.6;L9", "1;A>p.2;S99"]
    page = p.evaluate("""(texts) => texts.map((t) => { const sh = msegParse(t), n = MSEG_STRETCHES.reduce((k, s) => k + sh.inner[s].length, 0);
      const P = msegPoints(sh, { delay: 10, attack: 10, hold: 10, decay: 10, release: 10, sus: 0.5 });
      return { ok: sh.ok, count: P.last, sus: P.susPt, loop: P.loopPt, text: msegText(sh) }; })""", TEXTS)
    core = [core_parse(t) for t in TEXTS]
    same = [i for i, (a, c) in enumerate(zip(page, core)) if a["ok"] != c["ok"] or a["count"] != c["count"] or a["sus"] != c["sus"] or a["loop"] != c["loop"]]
    check("every shape's text reads the same on the page as in the core: whether it reads, its points, its sustain and its loop (%d texts)"
          % len(TEXTS), not same, "; ".join("%r page %s core %s" % (TEXTS[i], page[i], core[i]) for i in same[:3]))
    null("a text the core refuses is not the old envelope's in disguise: the junk reads as not read, both sides",
         not page[6]["ok"] and not core[6]["ok"] and page[1]["ok"])
    trips = [t for t, pg in zip(TEXTS, page) if pg["ok"] and p.evaluate("(t) => msegText(msegParse(t))", pg["text"]) != pg["text"]]
    check("and the page writes back what it read, unchanged (its text a fixed point)", not trips, str(trips))
    check("the old envelope's shape is written as the decode pass writes it", page[0]["text"] == "1;A>p.2;D>p.2;R>a.2", page[0]["text"])

    # The curve drawn against the curve played: the page's analytic travel at
    # each millisecond against the core's recursion on the same shape. They
    # differ by the engine's ending a stretch on the first sample past it.
    shape, A, D, S, R = "1;A>m.7;D.5,.4,m.6>m.35;R>a.2", 20, 200, 0.3, 300
    trace = core_trace(shape, A, D, S, R, 48000 * 600 // 1000, 48000)
    drawn = p.evaluate("""([t, a, d, s, r]) => { const P = msegPoints(msegParse(t), { delay: 0, attack: a, hold: 0, decay: d, release: r, sus: s });
      const held = (ms) => { for (let i = 1; i <= P.susPt; i++) { const p0 = P.pts[i - 1], p1 = P.pts[i]; if (ms <= p1.t && p1.t > p0.t) return msegTravel(p0.lvl, p1.lvl, p1.bend, (ms - p0.t) / (p1.t - p0.t)); }
        return s; };
      const at = (ms) => { if (ms < 600) return held(ms); const q = P.pts[P.last]; return msegTravel(s, 0, q.bend, Math.min(1, (ms - 600) / r), held(600)); };
      const out = []; for (let ms = 0; ms < 1000; ms += 1) out.push(at(ms)); return out; }""", [shape, A, D, S, R])
    worst = max(abs(drawn[ms] - trace[ms * 48]) for ms in range(1000))
    check("the curve drawn is the curve the core plays, within a sample's worth, through the attack, a drawn point, the decay and the release",
          worst < 0.01, "worst %.4f" % worst)
    off = p.evaluate("""([t, a, d, s, r]) => { const P = msegPoints(msegParse(t.replace('m.35', 'm.65')), { delay: 0, attack: a, hold: 0, decay: d, release: r, sus: s });
      const p0 = P.pts[3], p1 = P.pts[4]; return msegTravel(p0.lvl, p1.lvl, p1.bend, 0.5); }""", [shape, A, D, S, R])
    null("the same bend drawn the other way is far from what is played half-way through it", abs(off - trace[(20 + 150) * 48]) > 0.02,
         "%.3f against %.3f" % (off, trace[(20 + 150) * 48]))

    print("\n--- the small blocks ---")
    p.evaluate("() => { restore(BASE_SETUP); el.vcfType.value = '1'; el.vcfType.dispatchEvent(new Event('change', { bubbles: true })); }")
    p.wait_for_timeout(400)
    blk = p.evaluate("""() => { paintAmpEnv(); const d = el.ampEnvSmall._drawn;
      return { reads: el.ampEnvReads.textContent, handles: el.ampEnvSmall.querySelectorAll('[data-handle], text, line').length,
               curve: !!el.ampEnvSmall.querySelector('[data-curve]'), sus: d.ys[d.sus], top: d.ys[2], foot: d.ys[0], words: el.vcfSweeps.textContent }; }""")
    check("the amp's block is just the shape: a curve, no handles, no words or lines, and its four readings under it",
          blk["curve"] and blk["handles"] == 0 and "8 ms" in blk["reads"] and "−3.1 dB" in blk["reads"] and "180 ms" in blk["reads"], str(blk))
    lin = (blk["foot"] - blk["sus"]) / (blk["foot"] - blk["top"])
    check("in straight amplitude: a sustain of -3.1 dB stands at seven tenths of the peak", abs(lin - 0.7) < 0.02, "%.3f" % lin)
    null("in decibels over 60 it would stand at nineteen twentieths", abs(lin - (60 - 3.1) / 60) > 0.2, "%.3f" % lin)
    check("the filter's block says its envelope does nothing while its amount is nought", blk["words"] == "amount 0, does nothing", blk["words"])
    p.evaluate("() => { el.vcfEnvAmt.value = '15'; el.vcfEnvAmt.dispatchEvent(new Event('input', { bubbles: true })); paintAmpEnv(); }")
    words = p.evaluate("() => [el.vcfSweeps.textContent, !!el.vcfRespSmall.querySelector('[data-sweep]'), el.vcfEnvSmall.querySelector('[data-curve]').classList.contains('is-dead')]")
    check("and sweeps +1.5 oct once it has an amount, its band shaded and its envelope drawn live", words == ["sweeps +1.5 oct", True, False], str(words))

    print("\n--- the popover: beside its block, at every window ---")
    PLACE = """(which) => { const pop = el.msegPop.getBoundingClientRect(), blk = el[MSEG_POP[which].block].getBoundingClientRect();
      const band = document.querySelector('.bench-band').getBoundingClientRect(), screen = document.getElementById('screenFrame').getBoundingClientRect();
      const hits = (a, b) => a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1;
      const rows = (box) => new Set([...box.querySelectorAll('.knob-row')].map((r) => Math.round(r.getBoundingClientRect().top))).size;
      return { open: !el.msegPop.hidden, block: hits(pop, blk), band: hits(pop, band), screen: hits(pop, screen),
               over: el.msegPop.scrollHeight - el.msegPop.clientHeight, rows: rows(el.msegKnobs), frows: which === 'vcf' ? rows(el.msegFKnobs) : 1,
               six: el.msegKnobs.querySelectorAll('.knob-row').length, inWindow: pop.bottom <= innerHeight + 1 && pop.right <= innerWidth + 1,
               scrolls: el.benchBody.scrollHeight - el.benchBody.clientHeight, plot: el.msegPlot.clientHeight }; }"""
    for w, h in ((1400, 900), (1100, 860), (1200, 680), (1100, 680), (1067, 667)):
        q, qbad = open_page(b, w, h)
        q.evaluate("() => { el.vcfType.value = '1'; el.vcfType.dispatchEvent(new Event('change', { bubbles: true })); }"); q.wait_for_timeout(200)
        for which in ("amp", "vcf"):
            q.locator("#" + ("ampEnvBlock" if which == "amp" else "vcfBlock")).click(); q.wait_for_timeout(250)
            m = q.evaluate(PLACE, which)
            check("%dx%d, %s: open beside its block - not over it, the band or the screen - all in, its knobs in one row, Play not scrolled"
                  % (w, h, which), m["open"] and not m["block"] and not m["band"] and not m["screen"] and m["over"] <= 1 and m["rows"] == 1
                  and m["frows"] == 1 and m["six"] == 6 and m["inWindow"] and m["scrolls"] <= 1 and m["plot"] >= 50, str(m))
            q.keyboard.press("Escape"); q.wait_for_timeout(100)
        if w == 1400:
            q.evaluate("() => { openMsegPop('amp'); el.msegPop.style.left = (parseFloat(el.msegPop.style.left) + 300) + 'px'; }")
            mm = q.evaluate(PLACE, "amp")
            null("the same measure finds the popover moved over its block", mm["block"], str(mm))
            q.keyboard.press("Escape")
        if qbad: check("no page errors at %dx%d" % (w, h), False, "; ".join(qbad[:2]))
        q.close()

    p.locator("#ampEnvBlock").click(); p.wait_for_timeout(250)
    homes = p.evaluate("() => ['envAttack', 'envDelay'].map((id) => el.msegKnobs.contains(el[id]))")
    p.locator("#msegPopClose").click(); p.wait_for_timeout(150)
    back = p.evaluate("() => [el.msegPop.hidden, el.ampEnvStore.contains(el.envAttack), el.ampEnvStore.contains(el.envDelay)]")
    check("its six knobs move in while it is open and back to their section on Close", homes == [True, True] and back == [True, True, True], "%s %s" % (homes, back))
    p.locator("#ampEnvBlock").click(); p.wait_for_timeout(200)
    p.mouse.click(30, 450); p.wait_for_timeout(150)
    check("a press outside it closes it", p.evaluate("() => el.msegPop.hidden"))
    null("and a press inside does not", (p.locator("#ampEnvBlock").click(), p.wait_for_timeout(200), p.mouse.click(*centre(p, "#msegPopName")),
         p.wait_for_timeout(150), not p.evaluate("() => el.msegPop.hidden"))[-1])
    shown = p.evaluate("() => { msegPop.open && closeMsegPop(); showControl('envHold'); return [msegPop.open, el.msegKnobs.contains(el.envHold)]; }")
    check("showControl on a knob of the envelope opens its editor with the knob in it", shown == ["amp", True], str(shown))
    p.keyboard.press("Escape"); p.wait_for_timeout(100)

    print("\n--- a point writes its knob, by the drawing's scale ---")
    p.evaluate("() => { restore(BASE_SETUP); for (const [id, v] of [['envAttack', 20], ['envDecay', 200], ['envSustain', 60], ['envRelease', 400]]) setControl(id, v); }")
    p.wait_for_timeout(600)
    p.locator("#ampEnvBlock").click(); p.wait_for_timeout(250)
    before, u0 = p.evaluate(AMP), p.evaluate(UNDO)
    WANT = """([cx]) => { const g = msegPlots.amp.g, local = new DOMPoint(cx, 0).matrixTransform(el.msegPlot.getScreenCTM().inverse()).x;
      return { undo: undoHistory.undo.length, sqrt: Math.round(msegTimeAt(local - g.x0.attack, g.k)), straight: Math.round(20 * (local - g.x0.attack) / (g.k * Math.sqrt(20))) }; }"""
    x0, _ = centre(p, PT("msegPlot", "p2"))
    (px, py), w = drag(p, PT("msegPlot", "p2"), 20, 0, hold=lambda: p.evaluate(WANT, [x0 + 20]))
    held, want = w["undo"], w
    p.wait_for_timeout(900)
    after, u1 = p.evaluate(AMP), p.evaluate(UNDO)
    check("the attack's point dragged moves the attack, and only it, to the square-root scale's value for where it let go",
          abs(after[1] - want["sqrt"]) <= 1 and after[:1] + after[2:] == before[:1] + before[2:], "%s, want %d" % (after, want["sqrt"]))
    null("the attack it had is not that value", abs(before[1] - want["sqrt"]) > 5, str(before))
    null("nor is a straight scale's", abs(want["straight"] - want["sqrt"]) > 5, str(want))
    check("one step of undo, once the pointer lifts", u1 == u0 + 1, "%d -> %d" % (u0, u1))
    null("with the pointer still down there was no step yet", held == u0, "%s" % held)
    under = p.evaluate("""([x, y]) => { const r = el.msegPlot.querySelector('[data-handle="p2"] circle:last-child').getBoundingClientRect();
      return Math.hypot(r.x + r.width / 2 - x, r.y + r.height / 2 - y); }""", [px, py])
    check("and the point is under the pointer that let go of it", under < 1.5, "%.2f px" % under)
    p.evaluate("() => undoStep(true)"); p.wait_for_timeout(300)
    check("undo puts the attack back", p.evaluate(AMP) == before, str(p.evaluate(AMP)))

    p.evaluate("() => msegPlots.amp.draw(true)")
    dec = p.evaluate("() => msegNow('amp').shape.ok !== undefined && msegPoints(msegNow('amp').shape, msegNow('amp').m).decayEnd")
    (dx, dy), _ = drag(p, PT("msegPlot", "p%d" % dec), 12, -20)
    p.wait_for_timeout(200)
    d = p.evaluate(AMP)
    lvl = p.evaluate("""([y]) => { const g = msegPlots.amp.g; return g.lvl(new DOMPoint(0, y).matrixTransform(el.msegPlot.getScreenCTM().inverse()).y); }""", [dy])
    check("the decay's point: the decay longer and the sustain the level it let go at, the rest as they were",
          d[3] > 200 and abs(d[4] / 100 - lvl) < 0.002 and d[1] == 20 and d[5] == 400, "%s, level %.4f" % (d, lvl))
    ro = p.evaluate("() => el.msegReadout.textContent")
    check("its readout says the decay and the sustain in decibels", ro.startswith("Decay ") and "dB" in ro, ro)

    # Every point on its curve: its centre at the shape's own level at its time.
    oncurve = p.evaluate("""() => { const g = msegPlots.amp.g; return [...el.msegPlot.querySelectorAll('.mseg-pt')].map((h) => {
      const i = Number(h.dataset.handle.slice(1)), c = h.querySelector('circle:last-child');
      return Math.hypot(Number(c.getAttribute('cx')) - g.xs[i], Number(c.getAttribute('cy')) - g.y(g.P.pts[i].lvl)); }); }""")
    check("every point's handle sits where the shape has it, within half a pixel", oncurve and max(oncurve) < 0.5, str(oncurve))
    null("the same measure of a point four pixels off finds it", abs(4 - 0) > 0.5)

    print("\n--- a point added on the line, and taken away ---")
    LEVELS = """() => { const n = msegNow('amp'), P = msegPoints(n.shape, n.m), out = [];
      for (let t = 0; t <= P.pts[P.susPt].t; t += 2) { for (let i = 1; i <= P.susPt; i++) { const a = P.pts[i - 1], q = P.pts[i];
        if (t <= q.t && q.t > a.t) { out.push(msegTravel(a.lvl, q.lvl, q.bend, (t - a.t) / (q.t - a.t))); break; } } } return out; }"""
    l0 = p.evaluate(LEVELS)
    at = p.evaluate("""() => { const g = msegPlots.amp.g, i = g.P.decayEnd, x = g.startX(i) + 0.3 * (g.xs[i] - g.startX(i));
      const P = g.P, y = g.y(msegTravel(P.pts[i - 1].lvl, P.pts[i].lvl, P.pts[i].bend, 0.3)), r = el.msegPlot.getBoundingClientRect();
      return [r.left + x * r.width / g.W, r.top + y * r.height / g.H]; }""")
    p.mouse.click(*at); p.mouse.click(*at); p.wait_for_timeout(200)
    s1 = p.evaluate(POINTS, "amp")
    l1 = p.evaluate(LEVELS)
    n = min(len(l0), len(l1))
    diff = max(abs(a - b) for a, b in zip(l0[:n], l1[:n]))
    check("two presses on the decay's line add a point there", s1["last"] == 6 and "D" in s1["text"] and "," in s1["text"], s1["text"])
    # To the text's own precision: a point's level is kept to five places and a bend's aim to four.
    check("and nothing drawn - so nothing heard - changes: the halves aim where the whole did, to the text's precision", diff < 2e-5, "worst %.2g" % diff)
    naive = p.evaluate("""() => { const sh = msegParse(el.envShape.value), d = sh.inner.decay[0];
      d.b = sh.close.decay = { law: 'm', v: 0.71 }; const n = msegNow('amp'), P = msegPoints(sh, n.m), q = P.pts[P.decayEnd - 1], a = P.pts[P.decayEnd - 2];
      return msegTravel(a.lvl, q.lvl, q.bend, 0.5); }""")
    null("the point's halves each given the old midpoint would draw it elsewhere",
         abs(naive - p.evaluate("""() => { const n = msegNow('amp'), P = msegPoints(n.shape, n.m), q = P.pts[P.decayEnd - 1], a = P.pts[P.decayEnd - 2]; return msegTravel(a.lvl, q.lvl, q.bend, 0.5); }""")) > 1e-3)
    added = p.evaluate("() => msegPoints(msegNow('amp').shape, msegNow('amp').m).decayEnd - 1")
    p.locator(PT("msegPlot", "p%d" % added)).focus(); p.keyboard.press("ArrowUp"); p.wait_for_timeout(100)
    up = p.evaluate(POINTS, "amp")
    check("an arrow moves a point you added: up a twentieth", abs(up["pts"][added][2] - s1["pts"][added][2] - 0.05) < 1e-6, "%s -> %s" % (s1["pts"][added], up["pts"][added]))
    p.keyboard.press("Delete"); p.wait_for_timeout(150)
    gone = p.evaluate(POINTS, "amp")
    check("Delete takes it away again", gone["last"] == 5, gone["text"])
    p.mouse.click(*at); p.mouse.click(*at); p.wait_for_timeout(150)
    hx, hy = centre(p, PT("msegPlot", "p%d" % added))
    p.mouse.click(hx, hy); p.mouse.click(hx, hy); p.wait_for_timeout(150)
    check("and two presses on a point you added take it away", p.evaluate(POINTS, "amp")["last"] == 5, p.evaluate(POINTS, "amp")["text"])

    print("\n--- the menu: sustain, one-shot, loop ---")
    def menu(key):
        p.locator(PT("msegPlot", key)).click(button="right"); p.wait_for_timeout(200)
        return p.evaluate("() => overlay ? [...overlay.node.querySelectorAll('.ctx-item')].map((b) => b.dataset.item) : []")
    items = menu("p2")
    check("a point's menu: Type a value, Sustain here, No sustain, Loop from here, Reset", items == ["type", "sustain", "oneshot", "loop", "reset"], str(items))
    p.locator('.ctx-item[data-item="sustain"]').click(); p.wait_for_timeout(150)
    s = p.evaluate(POINTS, "amp")
    check("Sustain here on the attack's point holds the shape there", s["sus"] == 2 and s["text"].endswith(";S2"), s["text"])
    items = menu("p2")
    p.locator('.ctx-item[data-item="oneshot"]').click(); p.wait_for_timeout(150)
    s = p.evaluate(POINTS, "amp")
    keyup = p.evaluate("() => !!el.msegPlot.querySelector('.mseg-keyup')")
    check("No sustain makes it a one-shot, with no key up drawn", s["sus"] == -1 and s["text"].endswith(";S-") and not keyup, "%s %s" % (s["text"], keyup))
    items = menu("p2")
    check("and a one-shot's menu offers the sustain back", "sustainback" in items and "oneshot" not in items, str(items))
    p.locator('.ctx-item[data-item="sustainback"]').click(); p.wait_for_timeout(150)
    check("and it puts the sustain back where it always is", p.evaluate(POINTS, "amp")["sus"] == 4, p.evaluate(POINTS, "amp")["text"])
    p.locator(PT("msegPlot", "p2")).focus(); p.keyboard.press("Shift+F10"); p.wait_for_timeout(200)
    opened = p.evaluate("() => !!overlay && overlay.opener && overlay.opener.dataset.handle")
    check("Shift+F10 on a focused point opens its menu", opened == "p2", str(opened))
    p.locator('.ctx-item[data-item="loop"]').click(); p.wait_for_timeout(150)
    s = p.evaluate(POINTS, "amp")
    wash = p.evaluate("() => [!!el.msegPlot.querySelector('.mseg-loop'), el.msegLoop.getAttribute('aria-pressed')]")
    check("Loop from here loops back to that point while held, drawn and the Loop button on", s["loop"] == 2 and wash == [True, "true"], "%s %s" % (s["text"], wash))
    p.locator("#msegLoop").click(); p.wait_for_timeout(100)
    check("and Loop pressed again takes it away", p.evaluate(POINTS, "amp")["loop"] == -1, p.evaluate(POINTS, "amp")["text"])
    null("a shape with no loop has none to draw", not p.evaluate("() => !!el.msegPlot.querySelector('.mseg-loop')"))
    menu("p%d" % p.evaluate("() => msegPoints(msegNow('amp').shape, msegNow('amp').m).last"))
    p.locator('.ctx-item[data-item="type"]').click(); p.wait_for_timeout(100)
    p.keyboard.press("Control+a"); p.keyboard.type("1.5 s"); p.keyboard.press("Enter"); p.wait_for_timeout(150)
    check("Type a value on the release's point writes the release: 1.5 s", p.evaluate(AMP)[5] == 1500, str(p.evaluate(AMP)))
    rel = p.evaluate("() => msegPoints(msegNow('amp').shape, msegNow('amp').m).last")
    x, y = centre(p, PT("msegPlot", "p%d" % rel))
    p.mouse.click(x, y); p.mouse.click(x, y); p.wait_for_timeout(150)
    check("two presses on it put the release back to where it starts", p.evaluate(AMP)[5] == 180, str(p.evaluate(AMP)))

    print("\n--- the bends, and Delay and Hold ---")
    bend = p.evaluate("() => [...el.msegPlot.querySelectorAll('.mseg-bend')].map((h) => h.dataset.handle)")
    check("a bend's handle on each segment with a fall", "b2" in bend, str(bend))
    t0 = p.evaluate("() => el.envShape.value")
    drag(p, PT("msegPlot", "b2"), 0, 25); p.wait_for_timeout(150)
    t1 = p.evaluate("() => el.envShape.value")
    mid = p.evaluate("() => { const sh = msegParse(el.envShape.value); return sh.close.attack; }")
    check("dragged down, the attack's bend becomes a drawn midpoint under the old curve's", mid["law"] == "m" and mid["v"] < 0.71, "%s -> %s" % (t0, t1))
    x, y = centre(p, PT("msegPlot", "b2"))
    p.mouse.click(x, y); p.mouse.click(x, y); p.wait_for_timeout(150)
    check("two presses straighten it", p.evaluate("() => msegParse(el.envShape.value).close.attack.v") == 0.5, p.evaluate("() => el.envShape.value"))
    shown = p.evaluate("() => getComputedStyle(el.msegPlot.querySelector('[data-handle=\"whold\"]')).opacity")
    p.mouse.move(*centre(p, "#msegPlot")); p.wait_for_timeout(250)
    hover = p.evaluate("() => getComputedStyle(el.msegPlot.querySelector('[data-handle=\"whold\"]')).opacity")
    check("Hold's ring shows while the pointer is over the drawing, and not otherwise at nought", hover == "1", "%s, %s" % (shown, hover))
    drag(p, PT("msegPlot", "whold"), 20, 0); p.wait_for_timeout(150)
    hold = p.evaluate(AMP)[2]
    check("dragged, it writes the Hold", hold > 0, str(p.evaluate(AMP)))
    null("before, the Hold was nought", before[2] == 0)

    print("\n--- the knobs' laws ---")
    laws = p.evaluate("""() => { setControl('envRelease', 5000); setControl('envSustain', 100 * Math.pow(10, -3 / 20));
      return [knobFraction(el.envRelease), knobFraction(el.envSustain), el.envSustainValue.textContent, el.envReleaseValue.textContent]; }""")
    check("a 5 s release stands half-way round its knob (square-root time), and a -3 dB sustain at nineteen twentieths (-60 to 0)",
          abs(laws[0] - (4999 / 19999) ** 0.5) < 1e-3 and abs(laws[1] - 57 / 60) < 1e-3 and laws[2] == "−3.0 dB" and laws[3] == "5.00 s", str(laws))
    null("straight, the release would stand at a quarter", abs(laws[0] - 0.25) > 0.2, "%.3f" % laws[0])
    p.locator("#envRelease").focus(); p.keyboard.press("ArrowUp"); p.wait_for_timeout(100)
    stepped = p.evaluate("() => Number(el.envRelease.value)")
    check("an arrow on the knob moves it along its law: a hundredth of its travel, not a millisecond", abs(stepped - (1 + 19999 * (0.5 + 0.01) ** 2)) < 2, str(stepped))
    null("the browser's own arrow would have made it 5001", stepped != 5001)

    print("\n--- the hands ---")
    p.keyboard.press("Escape"); p.wait_for_timeout(100)
    p.evaluate("() => { restore(Object.assign({}, BASE_SETUP, { layers: 'split' })); }"); p.wait_for_timeout(300)
    p.evaluate("() => { document.getElementById('linkAmpEnv').click(); document.getElementById('editHandB').click(); }"); p.wait_for_timeout(200)
    p.locator("#ampEnvBlock").click(); p.wait_for_timeout(250)
    s0 = p.evaluate("() => { const s = snapshot(); return [s.atk, s.bAtk, s.envShape, s.bEnvShape]; }")
    drag(p, PT("msegPlot", "p2"), 25, 0); p.wait_for_timeout(200)
    at = p.evaluate("() => msegPlots.amp.g.startX(4) + 0.3 * (msegPlots.amp.g.xs[4] - msegPlots.amp.g.startX(4))")
    s1 = p.evaluate("() => { const s = snapshot(); return [s.atk, s.bAtk, s.envShape, s.bEnvShape]; }")
    ghost = p.evaluate("() => !!el.msegPlot.querySelector('[data-ghost]')")
    check("editing the upper hand of an unlinked split, a drag writes its attack and not the lower's", s1[0] == s0[0] and s1[1] != s0[1], "%s -> %s" % (s0, s1))
    check("and the lower hand's shape is drawn dashed behind", ghost)
    p.evaluate("() => { msegStartFrom('amp', 'Pluck'); }"); p.wait_for_timeout(150)
    s2 = p.evaluate("() => { const s = snapshot(); return [s.envShape, s.bEnvShape, genSettings(1).envShape, genSettings(0).envShape]; }")
    check("a shape written on the upper hand is its own, the lower's unmoved", s2[1] == s2[2] and "m.86" in s2[1] and "m.86" not in (s2[0] or ""), str(s2))
    p.evaluate("() => { document.getElementById('linkAmpEnv').click(); }"); p.wait_for_timeout(150)
    s3 = p.evaluate("() => [genSettings(0).envShape, genSettings(1).envShape]")
    null("linked again, the two hands are one shape", s3[0] == s3[1], str(s3))
    p.keyboard.press("Escape")
    p.evaluate("() => { document.getElementById('editHandA').click(); restore(BASE_SETUP); }"); p.wait_for_timeout(300)

    print("\n--- the Envelope follows until it is edited ---")
    p.evaluate("() => { restore(BASE_SETUP); setControl('envAttack', 30); setControl('envHold', 50); menvFollowAmp(); openModCard('env.note'); }")
    # Long enough for the step those make (a key was the last hand) to be taken before the count is read.
    p.wait_for_timeout(1200)
    MENV = "() => ({ own: el.menvOwn.checked, gen: genSettings().menvOwn, shape: el.menvShape.value, amp: el.envShape.value, m: ['menvDelay', 'menvAtk', 'menvHold', 'menvDec', 'menvSus', 'menvRel'].map((id) => Number(el[id].value)), follows: el.menvCurve.classList.contains('follows'), undo: undoHistory.undo.length })"
    f0 = p.evaluate(MENV)
    peak = p.evaluate("() => { menvPlot.draw(true); return el.menvCurve._drawn.xs[2]; }")
    want = p.evaluate("() => { const g = msegGeo(msegPoints(msegParse(el.envShape.value), { delay: 0, attack: 30, hold: 50, decay: 120, release: 180, sus: 0.7 }), msegBox(menvPlot)); return g.xs[2]; }")
    check("following, its drawing is the amp's shape and times, dashed", f0["follows"] and abs(peak - want) < 0.01 and not f0["own"], "%.2f / %.2f %s" % (peak, want, f0))
    u = f0["undo"]
    drag(p, PT("menvCurve", "p2"), 15, 0); p.wait_for_timeout(900)
    f1 = p.evaluate(MENV)
    check("a point dragged while following copies the amp's six and shape into its own, applies the drag, in one undo step",
          f1["own"] and f1["gen"] and f1["m"][0] == 0 and f1["m"][2] == 50 and f1["m"][1] > 30 and f1["shape"] == f1["amp"] and f1["undo"] == u + 1
          and not f1["follows"], str(f1))
    p.evaluate("() => undoStep(true)"); p.wait_for_timeout(300)
    check("undo puts it back to following", not p.evaluate(MENV)["own"], str(p.evaluate(MENV)))
    null("its own, it is not dashed", not f1["follows"])
    p.locator("#modEditorClose").click(); p.wait_for_timeout(150)

    print("\n--- the morph between two shapes ---")
    PAIRS = [("1;A>m.62;D.4,.18,m.72>m.3;R>a.2", "1;A>m.8;D.6,.5,m.4>m.6;R>m.7;L2", 0.37),
             ("1;A>p.2;D>p.2;R>a.2", "1;A>m.3;D>m.8;R>a.4", 0.5), ("1;A>l;D.5,.5,l>l;R>l", "1;A>l;D>l;R>l", 0.49),
             ("1;A>l;D.5,.5,l>l;R>l", "1;A>l;D>l;R>l", 0.5), ("", "1;A>m.6;R>l", 0.2), ("1;A>l;D>l;R>l;S2", "1;A>l;D>l;R>l;S-", 0.75)]
    page = p.evaluate("(pairs) => pairs.map(([a, b, t]) => msegBlend(a, b, t))", [list(x) for x in PAIRS])
    core = [core_blend(a, b2, t) for a, b2, t in PAIRS]
    check("the morph's blend of two shapes is the core's, character for character (%d pairs)" % len(PAIRS), page == core,
          "; ".join("%s | %s" % (x, y) for x, y in zip(page, core) if x != y))
    check("as many points: each point walks - a third of the way, its share, its level and its drawn bend",
          # .62 + .18 x .37, .4 + .2 x .37, .18 + .32 x .37, .72 - .32 x .37, .3 + .3 x .37; the release's a.2 against m.7 and the loop A's, short of half-way.
          page[0] == "1;A>m.687;D.474,.2984,m.602>m.411;R>a.2", page[0])
    check("a bend of another kind changes at half-way, and the whole shape where the points differ", page[1] == "1;A>m.3;D>m.8;R>a.3"
          and page[2] == PAIRS[2][0] and page[3] == PAIRS[3][1], "%s | %s | %s" % tuple(page[1:4]))
    null("one step either side of half-way is not the same shape", page[2] != page[3])
    p.evaluate("""() => { restore(BASE_SETUP); el.envShape.value = '1;A>m.62;D.4,.18,m.72>m.3;R>a.2'; el.envShape.dispatchEvent(new Event('input'));
      morphStore('a'); el.envShape.value = '1;A>m.8;D.6,.5,m.4>m.6;R>m.7;L2'; el.envShape.dispatchEvent(new Event('input')); morphStore('b');
      state.morphPos = 0.37; morph.applied = null; morphStep(); }""")
    walked = p.evaluate("() => [el.envShape.value, genSettings(0).envShape, snapshot().morphA, snapshot().morphB]")
    check("the fader walks the amp envelope's shape between the ends stored, on the face and in the generator it drives",
          walked[0] == page[0] and walked[1] == page[0], str(walked[:2]))
    check("and each end carries its shape, its own commas and semicolons kept out of the end's",
          "envShape:1%3BA%3Em.62%3BD.4%2C.18" in walked[2] and "envShape:1%3BA%3Em.8" in walked[3], "%s | %s" % (walked[2][-80:], walked[3][-80:]))
    back = p.evaluate("(code) => { loadCode(code); return [morph.a.envShape, morph.b.envShape]; }", p.evaluate("() => encodeSetup(snapshot())"))
    check("which a code brings back", back == [PAIRS[0][0], PAIRS[0][1]], str(back))
    null("an end with no shape is none, its reference's", p.evaluate("() => decodeMorphEnd('=amp:40', morphHome).envShape") == "")

    print("\n--- a drawn shape reaches the instrument ---")
    code = p.evaluate("() => encodeSetup(Object.assign({}, BASE_SETUP, { envShape: '1;A>m.62;D.4,.3,m.7>m.3;R>m.65;L2', envHold: 40, vcfShape: '1;A>l;D>l;R>l;S-' }))")
    p.evaluate("(c) => loadCode(c)", code); p.wait_for_timeout(500)
    got = p.evaluate("() => [el.envShape.value, Number(el.envHold.value), el.vcfShape.value, genSettings(0).envShape, genSettings(0).envHoldMs, genSettings(0).fShape]")
    check("a code with drawn shapes loads them into the face and the generator it drives", got == ["1;A>m.62;D.4,.3,m.7>m.3;R>m.65;L2", 40, "1;A>l;D>l;R>l;S-",
          "1;A>m.62;D.4,.3,m.7>m.3;R>m.65;L2", 40, "1;A>l;D>l;R>l;S-"], str(got))
    old = p.evaluate("() => { const s = decodeSetup(btoa(JSON.stringify({ v: 12, atk: 5 })).replace(/=+$/, '')); return [s.v, s.envShape, s.vcfShape, s.menvShape]; }")
    check("a version-12 code comes up with the old envelope's shape in each", old == [13, "1;A>p.2;D>p.2;R>a.2", "1;A>p.2;D>p.2;R>a.2", "1;A>p.2;D>p.2;R>a.2"], str(old))
    null("one made at 13 names none", p.evaluate("() => decodeSetup(btoa(JSON.stringify({ v: 13, atk: 5 })).replace(/=+$/, '')).envShape") is None)

    if bad: check("no page errors", False, "; ".join(bad[:3]))
    else: check("no page errors", True)
    b.close()

print()
if fails: print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the drawn envelopes are drawn, taken hold of and heard as the core plays them")
