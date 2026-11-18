"""Painting on the page (step 2 of web/docs/painting-design.md): Trace and
Paint on the screen's toolbar, the painting's own Persistence on the one
knob, and the look painted from the core's strokes.

What would go wrong, and what is checked for it, each with its null:

- the switch showing Paint while the core goes on reading the trace: Paint is
  pressed with the mouse and the instrument's own readings asked whether it
  paints and whether it serves strokes. The null is the page before the
  press, where it does not;
- one Persistence meaning two things: the knob moved in Paint moves the
  painting's half-life and leaves the trace's, moved in Trace the other way
  round, and both come back out of a setup code into a fresh page. The null
  is the knob in Trace, which does move the trace's - so a check that the
  trace's stayed put could fail;
- the page and the core reading the knob two ways: the half-life the page
  shows is the one the instrument keeps as its hand, at three places;
- the look not being the core's painting: the graphics card's paint, summed
  to the core's 128 cells, against the map the core serves - their
  correlation, and the null the same map turned half a turn, which shares the
  rings but not where on them;
- a face without the graphics card: ?paint=plain draws the core's map plain
  and the instrument plays on (its chunks go on arriving); the null is the
  graphics card's page, which says it paints on the card;
- Clear leaving paint: the core's map and the look both empty after it; the
  null is before it;
- Mono not painting (step 1 painted Poly's voices only): a note in Mono, and
  paint where its ring is;
- Which hands offered in Paint: hidden there while the hands draw a figure
  each, and shown in Trace (the null);
- switching moving the face (the owner's rule, 18 Nov: selecting something
  must not shift the view): every element with an id measured in Trace, in
  Paint and in Trace again, at 1400x900 and the plugin's 960x600, and none
  may have moved or changed size but the painting itself and a box whose own
  words changed with the press (the Persistence's reading): a reading that
  grew and pushed its neighbours would still show in the neighbours. The
  info line is left out whole: it names whatever was last pressed, so its
  words and the menu and More after them move with every press of anything,
  Y-T against X-Y as much as Paint - the line's own behaviour, not the
  switch's. Elements whose box moves on
  its own between two readings a moment apart in Trace are left out first. The null: the Clear button taken out of
  the toolbar, which moves its neighbours, read the same way;
- the toolbar one row at 1400x900 with Paint in the display switch, as it
  was with three; the null is the plugin's 960x600, where it is two.

Parallel: no clock is judged; the frames are waited for, and every reading is
a value.
"""
import math, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
# WebGL 2 in a headless browser is SwiftShader's, asked for by name.
GL = ["--autoplay-policy=no-user-gesture-required", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    check("null: " + name, red, detail)

bad = []
def open_page(b, query="", w=1400, h=900):
    p = b.new_page(viewport={"width": w, "height": h})
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html{query}"); p.wait_for_timeout(2000)
    p.keyboard.press("Escape"); p.wait_for_timeout(200)
    return p

READ = """() => { const r = state.source.read || null; return null; }"""
# Whether the instrument paints and serves strokes, as its readings say: the worklet's, through the source.
PAINTS = """async () => {
  const before = paintView.since;
  await new Promise((r) => setTimeout(r, 400));
  return { since: paintView.since, more: paintView.since > before, draws: state.draws, mode: paintView.mode };
}"""
HANDS = """async () => decodeSetup((await scopeHost.call('scopeState')).code).pluginHands || []"""

def knob_to(p, value):
    p.evaluate("(v) => { el.scanMemory.value = String(v); el.scanMemory.dispatchEvent(new Event('input', { bubbles: true })); }", value)
    p.wait_for_timeout(250)

def corr(a, b):
    n = len(a); ma = sum(a) / n; mb = sum(b) / n
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    sa = math.sqrt(sum((x - ma) ** 2 for x in a)); sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return sab / (sa * sb) if sa > 0 and sb > 0 else 0.0

def turned(g, n=128):
    # Half a turn about the centre: the chord's arcs, laid over 3.5 s of an 8 s turn, land on bare canvas.
    return [g[(n - 1 - y) * n + (n - 1 - x)] for y in range(n) for x in range(n)]

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=GL)

    # --- the switch reaches the core ---
    p = open_page(b)
    p.evaluate("() => { el.oscScan.value = '60'; el.oscScan.dispatchEvent(new Event('input')); midiNoteOn(57, 100); }")
    p.wait_for_timeout(600)
    before = p.evaluate(PAINTS)
    null("before Paint is pressed the instrument serves no strokes", not before["more"] and before["draws"] == "trace", str(before))
    p.click("#drawPaint"); p.wait_for_timeout(400)
    after = p.evaluate(PAINTS)
    check("Paint pressed by hand: the instrument paints, and its strokes reach the face", after["more"] and after["draws"] == "paint",
          str(after))
    hands = p.evaluate(HANDS)
    check("the instrument keeps the press as a hand on its state", ["k", "drawPaint"] in [h[:2] for h in hands] or any("drawPaint" in str(h) for h in hands),
          str(hands[-3:]))
    reading = p.evaluate("() => el.scanMemoryValue.textContent")
    check("the Persistence knob reads the painting's, and says it is a half-life", reading == "16 s to half", reading)

    # --- Persistence: two values, one knob ---
    trace_before = p.evaluate("() => state.persistence")
    knob_to(p, 40)
    got = p.evaluate("() => ({ paint: state.paintPersistence, trace: state.persistence })")
    check("the knob moved in Paint moves the painting's half-life and leaves the trace's",
          got["paint"] == 6.8 and got["trace"] == trace_before, str(got))
    kept = [h for h in p.evaluate(HANDS) if "paintPersistence" in str(h)]
    check("the instrument keeps the same half-life as its own hand", kept and float(kept[-1][2]) == 6.8, str(kept[-1:]))
    for at in (0, 73, 100):
        knob_to(p, at)
        page = p.evaluate("() => state.paintPersistence")
        kept = [h for h in p.evaluate(HANDS) if "paintPersistence" in str(h)]
        check("at %d the page and the instrument read the knob alike" % at, kept and float(kept[-1][2]) == page,
              "%s against %s" % (page, kept[-1][2] if kept else None))
    knob_to(p, 40)
    p.click("#dispXY"); p.wait_for_timeout(300)
    knob_to(p, 80)
    got2 = p.evaluate("() => ({ paint: state.paintPersistence, trace: state.persistence, reading: el.scanMemoryValue.textContent })")
    null("in Trace the same knob does move the trace's", got2["trace"] != trace_before, str(got2))
    check("and leaves the painting's where Paint put it", got2["paint"] == 6.8, str(got2))
    p.click("#drawPaint"); p.wait_for_timeout(300)
    code = p.evaluate("() => encodeSetup(snapshot())")
    p.close()
    q = open_page(b)
    back = q.evaluate("(code) => { loadCode(code); return { draws: state.draws, paint: state.paintPersistence, trace: state.persistence, reading: el.scanMemoryValue.textContent }; }", code)
    check("both come back out of a setup code, with Paint shown", back["draws"] == "paint" and back["paint"] == 6.8
          and back["trace"] == got2["trace"], str(back))
    q.close()

    # --- the look is the core's painting ---
    p = open_page(b)
    p.click("#drawPaint"); p.wait_for_timeout(300)
    mode = p.evaluate("() => paintView.mode")
    p.evaluate("() => { el.oscScan.value = '60'; el.oscScan.dispatchEvent(new Event('input')); [45, 57, 64, 69].forEach((n) => midiNoteOn(n, 110)); }")
    p.wait_for_timeout(3500)
    got = p.evaluate("""() => { const m = paintView.map, s = paintView.sample();
      return { map: m ? Array.from(m.subarray(0, 128 * 128)) : null, look: s ? Array.from(s) : null }; }""")
    if got["map"] and got["look"]:
        c = corr(got["map"], got["look"]); w = corr(turned(got["map"]), got["look"])
        check("the graphics card paints where the core's map has paint (correlation over 128 cells)", c > 0.6, "%.2f" % c)
        null("the same map turned half a turn does not line up", w < 0.3, "%.2f" % w)
    else:
        check("the graphics card paints, and the core serves its map", False, "mode %s, map %s, look %s" % (mode, bool(got["map"]), bool(got["look"])))

    # --- Clear ---
    p.evaluate("() => [45, 57, 64, 69].forEach((n) => midiNoteOff(n))"); p.wait_for_timeout(300)
    full = p.evaluate("() => ({ map: paintView.map ? paintView.map.subarray(0, 16384).reduce((a, b) => a + b, 0) : 0, look: (paintView.sample() || []).reduce((a, b) => a + b, 0) })")
    null("before Clear there is paint in the core and on the screen", full["map"] > 1 and full["look"] > 1, str(full))
    p.click("#clearButton"); p.wait_for_timeout(1200)
    empty = p.evaluate("() => ({ map: paintView.map ? paintView.map.subarray(0, 16384).reduce((a, b) => a + b, 0) : 0, look: (paintView.sample() || []).reduce((a, b) => a + b, 0) })")
    check("Clear wipes the painting in the core and on the screen", empty["map"] < 1e-6 and empty["look"] < 1e-6, str(empty))
    p.close()

    # --- without the graphics card ---
    p = open_page(b, "?paint=plain")
    p.click("#drawPaint"); p.wait_for_timeout(300)
    p.evaluate("() => { el.oscScan.value = '60'; el.oscScan.dispatchEvent(new Event('input')); [57, 64].forEach((n) => midiNoteOn(n, 110)); }")
    c0 = p.evaluate("() => state.source.chunks"); p.wait_for_timeout(2500)
    got = p.evaluate("""() => { const c = paintView.canvas, x = c.getContext('2d').getImageData(0, 0, 128, 128).data, ink = [];
      for (let i = 0; i < 128 * 128; i++) ink.push(255 - x[i * 4]);
      return { mode: paintView.mode, why: paintView.why, ink, map: paintView.map ? Array.from(paintView.map.subarray(0, 16384)) : null, chunks: state.source.chunks }; }""")
    check("asked for plain, the face draws the core's map plain and says why", got["mode"] == "plain" and got["why"] == "asked for plain", got["mode"] + " / " + got["why"])
    if got["map"]:
        c = corr(got["map"], got["ink"])
        check("the plain drawing is the core's map", c > 0.8, "%.2f" % c)
    else:
        check("the plain drawing is the core's map", False, "no map served")
    check("and the instrument plays on", got["chunks"] > c0 + 50, "%d chunks in 2.5 s" % (got["chunks"] - c0))
    p.close()
    null("a page with the graphics card says it paints on it", mode == "gpu", mode)

    # --- Mono paints ---
    p = open_page(b)
    p.click("#drawPaint"); p.wait_for_timeout(300)
    p.evaluate("() => { el.oscScan.value = '60'; el.oscScan.dispatchEvent(new Event('input')); el.midiMono.click(); }"); p.wait_for_timeout(300)
    p.evaluate("() => midiNoteOn(57, 110)"); p.wait_for_timeout(2500)
    ring = p.evaluate("""() => { const m = paintView.map; if (!m) return null;
      const r = 0.47 * (1 / 3 + 2 / 3 * Math.log2(220 / 27.5) / Math.log2(4186.009044809578 / 27.5)) * 128;
      let on = 0, all = 0;
      for (let y = 0; y < 128; y++) for (let x = 0; x < 128; x++) { const a = m[y * 128 + x]; all += a;
        if (Math.abs(Math.hypot(x + 0.5 - 64, y + 0.5 - 64) - r) < 1.5) on += a; }
      return { on, all }; }""")
    check("a note in Mono paints its own ring", ring and ring["all"] > 0.5 and ring["on"] / ring["all"] > 0.8, str(ring))
    p.close()

    # --- switching moves nothing on the face ---
    SNAP = """() => { const out = {};
      for (const e of document.querySelectorAll('body *')) {
        if (!e.id || e.id === 'paintCanvas' || e.closest('#infoLine')) continue;
        const r = e.getBoundingClientRect();
        if (!r.width && !r.height) continue;
        out[e.id] = [r.x, r.y, r.width, r.height].map((v) => Math.round(v * 10) / 10).concat([e.textContent.slice(0, 60)]);
      }
      return out; }"""
    def moved(a, b, skip):
        # A box whose own words changed may change with them (a reading, the info line naming the press); nothing else may.
        return sorted(k for k in set(a) | set(b) if k not in skip and a.get(k) != b.get(k)
                      and not (k in a and k in b and a[k][4] != b[k][4]))
    for w, h in ((1400, 900), (960, 600)):
        p = open_page(b, "", w, h)
        p.evaluate("() => { el.oscScan.value = '60'; el.oscScan.dispatchEvent(new Event('input')); midiNoteOn(57, 100); }")
        p.wait_for_timeout(800)
        one = p.evaluate(SNAP); p.wait_for_timeout(400); two = p.evaluate(SNAP)
        live = set(moved(one, two, set()))
        p.click("#drawPaint"); p.wait_for_timeout(600)
        painted = p.evaluate(SNAP)
        p.click("#dispXY"); p.wait_for_timeout(600)
        back = p.evaluate(SNAP)
        shift = moved(two, painted, live) + moved(two, back, live)
        check("at %dx%d switching to Paint and back moves and resizes nothing on the face" % (w, h), not shift,
              "%d elements read, %d live left out; moved: %s" % (len(two), len(live), ", ".join(shift[:8])))
        rows = p.evaluate("() => Math.round(el.screenTools.getBoundingClientRect().height)")
        if w == 1400:
            check("the screen's toolbar is one row at 1400x900, Paint in the display switch", rows < 40, "%d px" % rows)
            p.evaluate("() => { el.clearButton.style.display = 'none'; }"); p.wait_for_timeout(200)
            gone = p.evaluate(SNAP)
            null("Clear taken out of the toolbar moves its neighbours, and the same reading sees it", moved(two, gone, live) != [],
                 ", ".join(moved(two, gone, live)[:4]))
        else:
            null("at the plugin's minimum the toolbar is two rows, so the row's check can fail", rows > 40, "%d px" % rows)
        p.close()

    # --- Which hands ---
    p = open_page(b)
    p.evaluate("""() => { const s = Object.assign({}, decodeSetup(encodeSetup(snapshot())), { midiMode: 'poly', layers: 'split', splitAt: 60, layerPair: 'each', display: 'xy' });
      loadCode(encodeSetup(s)); midiNoteOn(48, 100); midiNoteOn(67, 100); setEnlarged(true); }""")
    p.wait_for_timeout(800)
    shown = p.evaluate("() => { paintHands(); return !el.handsField.hidden; }")
    null("in Trace, with the hands each drawing a figure, Which hands is offered", shown)
    p.click("#drawPaint"); p.wait_for_timeout(400)
    hidden = p.evaluate("() => { paintHands(); return el.handsField.hidden; }")
    check("in Paint it is hidden: one canvas, each hand's ink the look", hidden)
    p.evaluate("() => setEnlarged(false)")
    p.close()

    b.close()

check("no page errors", not bad, "; ".join(bad[:3]))
print()
if fails: print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("painting on the page holds")
