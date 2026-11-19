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

# Every stroke the face is served, kept as served, so a test can paint them again (paint width, 18 Nov).
RECORD = """() => { window.__served = []; const take = window.__take = paintView.take.bind(paintView);
  paintView.take = (paint) => { if (paint && paint.on && paint.stamps && paint.count)
    window.__served.push(paint.stamps.slice(0, paint.count * 20)); take(paint); }; }"""
# The kept strokes painted again on a cleared canvas, a batch per 1/fps of their own time, every `every`th
# stamp, `widen` times their width: the look's paint as 128 cells, and at `cells` if asked, with where the stamps went.
REPLAY = """({ fps, every, widen, cells }) => {
  const all = []; for (const b of window.__served) for (let k = 0; k < b.length / 20; k++) all.push(b.subarray(k * 20, k * 20 + 20));
  const kept = all.filter((_, k) => k % every === 0).map((s) => { const c = Float32Array.from(s); c[4] *= widen; return c; });
  paintView.clear();
  let from = paintView.since + 1, i = 0;
  const t0 = kept.length ? kept[0][6] : 0, step = 1 / fps;
  for (let edge = t0 + step; i < kept.length; edge += step) {
    const batch = []; while (i < kept.length && kept[i][6] < edge) batch.push(kept[i++]);
    if (batch.length) { const f = new Float32Array(batch.length * 20); batch.forEach((s, k) => f.set(s, k * 20));
      window.__take({ on: true, from, count: batch.length, stamps: f }); from += batch.length; }
    paintView.draw(edge * 1000);
  }
  const look = paintView.sample(cells || 128), coarse = cells ? paintView.sample() : null;
  return { look: look ? Array.from(look) : null, coarse: coarse ? Array.from(coarse) : null, stamps: kept.length,
           at: kept.map((s) => [s[0], s[1]]), t: kept.map((s) => s[6] - t0), cells: cells || 128 };
}"""

# A run of eleven notes, a ninth of a second apart and each held 150 ms, struck alone, painted by a core of its own:
# each note still sounds at the next strike, so the core joins them into one stroke (PaintParams::join).
PLAY_RUN = """() => {
  const code = encodeSetup(Object.assign({}, decodeSetup(encodeSetup(snapshot())),
    { midiMode: 'poly', oscScan: 60, screenDraws: 'paint' }));
  const brain = makeWasmBrain(wasmModule(), 48000, 128, code);
  const l = new Float32Array(128), r = new Float32Array(128), pics = [new Float32Array(128), new Float32Array(128)];
  const run = [60, 62, 64, 65, 67, 69, 71, 72, 71, 69, 67], at = (s) => Math.round(s * 48000 / 128);
  for (let k = 0; k < at(1.6); k++) {
    run.forEach((n, i) => { if (k === at(i / 9)) brain.midi([0x90, n, 100], -1); if (k === at(i / 9 + 0.15)) brain.midi([0x80, n, 0], -1); });
    brain.block(128, l, r, pics, null);
    const p = brain.readings().paint;
    if (p && p.on && p.stamps && p.count) window.__served.push(p.stamps.slice(0, p.count * 20));
  }
}"""

# The run's last note lets go 10/9 + 0.15 s after its first strike: past that the stroke is the release.
HELD = 10 / 9 + 0.15

def spread(g, n=128):
    # The paint's RMS radius about its mean, in the map's cells: how wide a ring's stroke is.
    s = sr = srr = 0.0
    for y in range(n):
        for x in range(n):
            a = g[y * n + x]
            if a <= 0: continue
            r = math.hypot(x + 0.5 - n / 2, y + 0.5 - n / 2) * 128 / n
            s += a; sr += a * r; srr += a * r * r
    if s <= 0: return 0.0
    m = sr / s
    return math.sqrt(max(0.0, srr / s - m * m))

def along(run, until=None):
    """Along the run's own arc, from its first stamp's angle to its last's (or its last before `until` seconds of
    the run, so that the last note's release, which tapers to nothing as it should, is not read as a break), in
    half degrees: the share with paint at a fifth of the median's most, the longest stretch without, and the
    thinnest tenth over the median."""
    n = run["cells"]; g = run["look"]
    ang = lambda x, y: math.degrees(math.atan2(x - 0.5, -(y - 0.5))) % 360
    last = max(k for k, t in enumerate(run["t"]) if until is None or t <= until)
    a0, a1 = ang(*run["at"][0]), ang(*run["at"][last])
    bins = max(1, int((a1 - a0) % 360 * 2))
    most = [0.0] * bins
    for y in range(n):
        for x in range(n):
            v = g[y * n + x]
            if v <= 0: continue
            d = (ang((x + 0.5) / n, (y + 0.5) / n) - a0) % 360
            k = int(d * 2)
            if 1 <= k < bins - 1: most[k] = max(most[k], v)
    most = most[1:-1] or [0.0]
    srt = sorted(most); med = srt[len(srt) // 2]
    if med <= 0: return 0.0, len(most), 0.0
    gap = longest = cov = 0
    for v in most:
        if v > 0.2 * med: cov += 1; gap = 0
        else: gap += 1; longest = max(longest, gap)
    return cov / len(most), longest, srt[len(srt) // 10] / med

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
    # The band is three cells either side of the ring: the medium brush (19 Nov) spreads its paint over about
    # twice the 1.5 cells the width-1 brush did, and 1.5 caught 70 per cent of it.
    RING = """(hz) => { const m = paintView.map; if (!m) return null;
      const r = 0.47 * (1 / 3 + 2 / 3 * Math.log2(hz / 27.5) / Math.log2(4186.009044809578 / 27.5)) * 128;
      let on = 0, all = 0;
      for (let y = 0; y < 128; y++) for (let x = 0; x < 128; x++) { const a = m[y * 128 + x]; all += a;
        if (Math.abs(Math.hypot(x + 0.5 - 64, y + 0.5 - 64) - r) < 3) on += a; }
      return { on, all }; }"""
    ring = p.evaluate(RING, 220)
    check("a note in Mono paints its own ring", ring and ring["all"] > 0.5 and ring["on"] / ring["all"] > 0.8, str(ring))
    other = p.evaluate(RING, 440)
    null("the same band an octave up holds none of it", other and other["on"] / max(other["all"], 1e-9) < 0.2, str(other))
    p.close()

    # --- paint width (18 Nov): the look draws the stroke the sound reads, and draws it whole ---
    p = open_page(b)
    p.click("#drawPaint"); p.wait_for_timeout(300)
    p.evaluate(RECORD)
    p.evaluate("() => { el.oscScan.value = '60'; el.oscScan.dispatchEvent(new Event('input')); midiNoteOn(57, 110); }")
    p.wait_for_timeout(2000)
    p.evaluate("() => midiNoteOff(57)"); p.wait_for_timeout(1500)
    got = p.evaluate("""() => { const m = paintView.map, s = paintView.sample();
      return { map: m ? Array.from(m.subarray(0, 128 * 128)) : null, look: s ? Array.from(s) : null }; }""")
    if got["map"] and got["look"]:
        sm, sl = spread(got["map"]), spread(got["look"])
        check("the look's stroke is the map's width: a held note's spread across its ring, look against map", abs(sl / sm - 1) < 0.12,
              "look %.3f cells, map %.3f" % (sl, sm))
        wide = p.evaluate(REPLAY, {"fps": 60, "every": 1, "widen": 2})
        sw = spread(wide["look"])
        null("the same strokes drawn twice as wide in the look are not the map's width", abs(sw / sm - 1) > 0.5,
             "look %.3f cells, map %.3f" % (sw, sm))
    else:
        check("the look's stroke is the map's width", False, "map %s, look %s" % (bool(got["map"]), bool(got["look"])))
    p.close()

    # A run, each note struck alone, played by the core itself (the page's own module, as the worklet runs it, so
    # the timing is the instrument's to the block and not the page's timers'): its strokes, as served, painted
    # again at 60 and at 4 frames a second.
    p = open_page(b)
    p.click("#drawPaint"); p.wait_for_timeout(300)
    p.evaluate(RECORD)
    p.evaluate(PLAY_RUN)
    runs = {}
    # The null thins the stamps to one in 24: a third of a second's stamps at the medium brush's spacing lies
    # under one stamp's length, so one in eight (the null at width 1) still drew a whole stroke at width 2.
    for name, fps, every in (("60", 60, 1), ("4", 4, 1), ("thinned", 60, 24)):
        runs[name] = p.evaluate(REPLAY, {"fps": fps, "every": every, "widen": 1, "cells": 768})
    if runs["60"]["look"]:
        for name in ("60", "4"):
            cov, gap, dip = along(runs[name], HELD)
            check("the run's look is one unbroken stroke painted at %s frames a second" % name, cov > 0.9 and gap <= 2,
                  "%.0f%% of the arc, longest gap %d half-degrees, %d stamps" % (100 * cov, gap, runs[name]["stamps"]))
        c = corr(runs["60"]["coarse"], runs["4"]["coarse"])
        check("and the same picture at either rate (correlation over 128 cells)", c > 0.95, "%.3f" % c)
        cov, gap, _ = along(runs["thinned"], HELD)
        null("the same strokes with 23 stamps in 24 dropped break into beads, and the check sees it", gap > 2 or cov < 0.8,
             "%.0f%% of the arc, longest gap %d half-degrees" % (100 * cov, gap))
    else:
        check("the run's look is painted", False, str(runs["60"].get("stamps")))
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
