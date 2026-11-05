"""The loop on the screen (P8f): a toggle that shows where Scan reads.

What it must not be is a drawing of what the code means to do. Each check
reads what the overlay drew (`loopOverlay.drawn`) against the reader's own
state, and each has a null that a ring in the wrong place, a head that
does not turn, an old table or another verdict would pass if the check could
not tell:

- off by default; the Loop button shows and hides it; remembered for this
  viewer across a reload; never in a setup code (the null: a real setting
  does change the code, so the comparison can tell);
- the ring is drawn where the reader's path is, and that path is where the
  figure is - an off-centre figure, so the null, P2's centred circle, lands
  somewhere else;
- the read-head is the voice's phase sampled at each tick: still on a tone
  at four times 60 Hz, turning on one at 250 Hz, which is the null - a head
  pinned to nought or to the frame clock fails one or the other;
- the thumbnail is the newest table, not the one before it (the null);
- the badge is the readout's verdict, and another verdict is not;
- drawn over the trace, not into it: the phosphor's cells, which Scan reads,
  are the same to the bit with it drawn a hundred times, and nothing goes to
  the audio thread (the null: a strike laid into the cells changes them);
- in a split, each layer's ring on the picture it reads, and crossed, on the
  other's;
- in Y-T no ring but the table and the badge; on the spectrogram nothing;
- at a phone's width the button is on screen and nothing scrolls sideways;
  and its frame costs under two milliseconds there.

On the site's instrument, which reads its own grid in the core and hands its
paths, heads and tables back with its readings, and on the page's own brain.
Serial: the frame cost is a cost in milliseconds.
"""
import math, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    """A check's null: the same comparison fed a value it must reject."""
    check("null: " + name, red, detail)

# Scan on, X-Y, a sine pushed right and up by the channels' offsets so the
# figure is not at the screen's middle: P2's centred circle is then wrong.
SCANNING = """async (freq) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  // As a preset lands: on the page, then sent whole to the instrument.
  hostQuietly(() => restore({ shape: 'sine', freq, interval: 7, just: false, oscScan: 100, display: 'xy', persistence: '0.12', pictureAmount: 0 }));
  hostSendSetup();
  await wait(200);
  // By the Offset controls, as a hand moves them, so the site's instrument -
  // whose grid is its own - is told too.
  for (const [id, v] of [['ch1Offset', '35'], ['ch2Offset', '25']]) {
    showControl(id); const s = document.getElementById(id); s.value = v; s.dispatchEvent(new Event('input', { bubbles: true }));
  }
  await wait(4000);
}"""

DRAWN = """() => { const d = loopOverlay.drawn, v = loopView();
  return { on: loopOverlay.on, hidden: el.loopOverlay.hidden, pressed: el.loopButton.getAttribute('aria-pressed'),
           rings: d ? d.rings : null, heads: d ? d.heads : null, thumbs: d ? d.thumbs : null, badge: d ? d.badge : null,
           paths: v ? v.paths : null, reads: v ? v.reads : null, vheads: v ? v.heads : null,
           plot: { x: plot.x, y: plot.y, w: plot.w, h: plot.h }, kind: state.source.kind }; }"""

def circle(path, plot, least=2 / 64):
    r = max(path["r"], least)
    return (plot["x"] + (path["cx"] + 0.35 * r) * plot["w"], plot["y"] + (path["cy"] + 0.2 * r) * plot["h"], 0.8 * r * plot["w"])

def open_page(b, query="", viewport=(1400, 900), ctx=None):
    c = ctx or b.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    p = c.new_page()
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html{query}"); p.wait_for_timeout(2500)
    p.evaluate("() => { const d = document.getElementById('helpDialog'); if (d && d.open) d.close(); }")
    return c, p, bad

def heads_over(p, ms=1200, every=40):
    out = []
    for _ in range(ms // every):
        out.append(p.evaluate("() => { const v = loopView(); return v ? v.heads[0] : null; }"))
        p.wait_for_timeout(every)
    return [h for h in out if h is not None and h >= 0]

def spread(hs):
    # How far round the circle the heads wander, on the circle (0.95 and 0.05 are close).
    if not hs: return None
    best = 1
    for ref in hs:
        best = min(best, max(min(abs(h - ref), 1 - abs(h - ref)) for h in hs))
    return best

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    for label, query in [("the site's instrument", ""), ("the page's own brain", "?brain=js")]:
        print("\n=== %s ===" % label)
        ctx = b.new_context(viewport={"width": 1400, "height": 900})
        c, p, bad = open_page(b, query, ctx=ctx)

        print("\n--- the toggle ---")
        first = p.evaluate(DRAWN)
        check("off by default: hidden, the button not pressed, nothing drawn",
              first["on"] is False and first["hidden"] is True and first["pressed"] == "false" and first["rings"] is None, str(first["on"]))
        code_off = p.evaluate("() => encodeSetup(snapshot())")
        p.click("#loopButton"); p.wait_for_timeout(300)
        on = p.evaluate(DRAWN)
        check("the Loop button shows it", on["on"] is True and on["hidden"] is False and on["pressed"] == "true", str(on["pressed"]))
        code_on = p.evaluate("() => encodeSetup(snapshot())")
        check("and it is not in the setup code", code_on == code_off)
        changed = p.evaluate("() => { const c = snapshot(); c.persistence = '0.5'; return encodeSetup(c); }")
        null("a real setting does change the code, so the comparison can tell", changed != code_off)

        p.evaluate(SCANNING, 240)
        print("\n--- the ring, where the reader reads ---")
        d = p.evaluate(DRAWN)
        print("    kind %s, path %s, ring %s" % (d["kind"], d["paths"][0], d["rings"][:1]))
        ring = d["rings"][0] if d["rings"] else None
        want = circle(ring["path"], d["plot"]) if ring and ring.get("path") else None
        check("a ring is drawn for layer A on its own picture", ring is not None and ring["layer"] == 0 and ring["picture"] == 0 and d["reads"][0] == 1,
              str(d["reads"]))
        err = math.hypot(ring["x"] - want[0], ring["y"] - want[1]) + abs(ring["rx"] - want[2]) if ring and want else 1e9
        check("drawn at the reader's own circle, to a hundredth of a pixel", err < 0.01, "%.4f px" % err)
        # The reader's path against the figure the page itself sees: the page's
        # phosphor is drawn from the same lanes, so its centre of light is where
        # the reader has followed to after four seconds held still.
        geo = p.evaluate("() => scanGeometry(pictureEngine.cells)")
        path = ring["path"]
        off = math.hypot(path["cx"] - geo["cx"], path["cy"] - geo["cy"]) * d["plot"]["w"]
        # Within a fifth of the ring's radius: the reader follows over a
        # second and Scan keeps the figure moving, so the centre of light now
        # and the path are never quite together; P2's centre is many times further.
        check("and that circle follows the figure: its centre within a fifth of the ring's radius of the figure's centre of light",
              off < 0.2 * ring["rx"], "%.2f px of %.1f; figure at (%.3f, %.3f)" % (off, ring["rx"], geo["cx"], geo["cy"]))
        centred = circle({"cx": 0.5, "cy": 0.5, "r": path["r"]}, d["plot"])
        cerr = math.hypot(ring["x"] - centred[0], ring["y"] - centred[1]) if ring else 0
        null("P2's centred circle is not where the ring is drawn", cerr > 20, "%.1f px away" % cerr)

        print("\n--- the read-head, the voice's phase at each tick ---")
        head = d["heads"][0] if d["heads"] else None
        if head:
            hx = ring["x"] + ring["rx"] * math.cos(2 * math.pi * head["head"])
            hy = ring["y"] + ring["ry"] * math.sin(2 * math.pi * head["head"])
            herr = math.hypot(head["x"] - hx, head["y"] - hy)
        else: herr = 1e9
        check("the head is drawn on the ring at its phase", herr < 0.01, "%.4f px" % herr)
        still = spread(heads_over(p))
        check("at 240 Hz, four times the tick, the head stands still", still is not None and still < 0.02, "wanders %s of a turn" % still)
        p.evaluate(SCANNING, 250)
        moving = spread(heads_over(p))
        null("at 250 Hz it turns, so a head pinned anywhere would fail one of the two", moving is not None and moving > 0.2,
             "wanders %s of a turn" % moving)

        print("\n--- the table being played ---")
        if d["kind"] == "tone":
            # The page's own: the newest table read, which the voice takes at
            # the next tick. Caught between two, the old one kept for the null.
            t = p.evaluate("""async () => {
              const wait = (ms) => new Promise((r) => setTimeout(r, ms));
              let prev = scan.tables[0], now = prev;
              for (let i = 0; i < 100 && now === prev; i++) { await wait(5); now = scan.tables[0]; }
              // Drawn by the page's own frame, which reads and then draws:
              // straight after it, what it drew against what it read.
              await new Promise((r) => requestAnimationFrame(() => r()));
              return { drawn: loopOverlay.drawn.thumbs[0], now: loopThumb(scan.tables[0]), prev: loopThumb(prev) };
            }""")
        else:
            # The instrument's: the newest table its readings carried, caught
            # as they arrive rather than read back from where the source keeps
            # it (which is what is under test), and the one before for the null.
            t = p.evaluate("""async () => {
              const wait = (ms) => new Promise((r) => setTimeout(r, ms));
              const src = state.source, real = src.absorb;
              let raw = null, rawPrev = null;
              src.absorb = function (lanes, r) {
                if (r && r.scan && r.scan.tables[0] !== undefined) { rawPrev = raw; raw = r.scan.tables[0]; }
                return real.call(this, lanes, r);
              };
              await wait(500);
              const first = raw;
              for (let i = 0; i < 100 && raw === first; i++) await wait(5);
              await new Promise((r) => requestAnimationFrame(() => r()));
              const out = { drawn: loopOverlay.drawn.thumbs[0], now: raw, prev: rawPrev };
              src.absorb = real;
              return out;
            }""")
        same = t["drawn"] is not None and t["now"] is not None and len(t["drawn"]) == 128 and \
            max(abs(a - b2) for a, b2 in zip(t["drawn"], t["now"])) == 0
        check("the thumbnail is the newest table, point for point", same)
        diff = max(abs(a - b2) for a, b2 in zip(t["drawn"], t["prev"])) if t["drawn"] and t["prev"] else 0
        null("the table before it is not what is drawn", diff > 1e-4, "differs by %.4f" % diff)

        print("\n--- the badge ---")
        # The stage is at nought here, so the readout says nothing of the loop
        # and the badge is the meter's own word; with the stage up, the
        # readout says it too and they must agree.
        v = p.evaluate("() => { drawLoopOverlay(); return { badge: loopOverlay.drawn.badge, verdict: pictureMeter.verdict() }; }")
        check("with Scan alone closing the loop, the badge is the meter's verdict", v["badge"] is not None and v["badge"] == v["verdict"], str(v))
        other = [x for x in ["listening", "running away", "settled", "cycling", "wandering"] if x != v["badge"]][0]
        null("another verdict is not the meter's", other != v["verdict"], other)
        v = p.evaluate("""async () => { el.pictureAmount.value = '60'; el.pictureAmount.dispatchEvent(new Event('input'));
          await new Promise((r) => setTimeout(r, 600)); drawLoopOverlay();
          const out = { badge: loopOverlay.drawn.badge, readout: el.readoutDetail.textContent };
          el.pictureAmount.value = '0'; el.pictureAmount.dispatchEvent(new Event('input')); return out; }""")
        check("with the stage up, the badge is the readout's word", v["badge"] is not None and ("loop " + v["badge"]) in v["readout"],
              "%s / %s" % (v["badge"], v["readout"][-60:]))

        print("\n--- over the trace, not into it ---")
        iso = p.evaluate("""() => {
          setRunning(false);
          const cells = Float32Array.from(pictureEngine.cells);
          for (let i = 0; i < 100; i++) drawLoopOverlay();
          let changed = 0;
          for (let i = 0; i < cells.length; i++) if (cells[i] !== pictureEngine.cells[i]) changed++;
          // The null: what a strike does - light laid into the cells Scan reads.
          const before = Float32Array.from(pictureEngine.cells);
          pictureEngine.segment(plot, plot.x + plot.w * 0.3, plot.y + plot.h * 0.3, plot.x + plot.w * 0.7, plot.y + plot.h * 0.6, 1);
          let struck = 0;
          for (let i = 0; i < before.length; i++) if (before[i] !== pictureEngine.cells[i]) struck++;
          pictureEngine.cells.set(before);
          setRunning(true);
          return { changed, struck, n: cells.length };
        }""")
        check("drawn a hundred times, the phosphor Scan reads is the same to the bit", iso["changed"] == 0, "%d of %d cells" % (iso["changed"], iso["n"]))
        null("light laid into it, as a strike lays it, is seen", iso["struck"] > 0, "%d cells" % iso["struck"])
        src = p.evaluate("() => drawLoopOverlay.toString()")
        check("and the overlay calls nothing that reaches the sound (no genSet, scope call or post)",
              all(w not in src for w in ["genSet(", "postMessage", "scopeHost", "hostSlider(", ".segment("]))

        print("\n--- Y-T and the spectrogram ---")
        yt = p.evaluate("""async () => { el.dispYT.click(); await new Promise((r) => setTimeout(r, 300));
          const d = loopOverlay.drawn; return { rings: d.rings.length, thumbs: d.thumbs.filter(Boolean).length, badge: d.badge }; }""")
        check("in Y-T, no ring, but the table and the badge", yt["rings"] == 0 and yt["thumbs"] == 1 and yt["badge"] is not None, str(yt))
        sp = p.evaluate("""async () => { el.dispSpect.click(); await new Promise((r) => setTimeout(r, 300));
          const d = loopOverlay.drawn; const r = { rings: d.rings.length, thumbs: d.thumbs.filter(Boolean).length, badge: d.badge };
          el.dispXY.click(); await new Promise((r) => setTimeout(r, 300)); return r; }""")
        check("on the spectrogram, nothing", sp["rings"] == 0 and sp["thumbs"] == 0 and sp["badge"] is None, str(sp))

        print("\n--- a split, and crossed hands ---")
        split = p.evaluate("""async () => {
          const wait = (ms) => new Promise((r) => setTimeout(r, ms));
          for (const id of ['ch1Offset', 'ch2Offset']) { const s = document.getElementById(id); s.value = '0'; s.dispatchEvent(new Event('input', { bubbles: true })); }
          // The split preset, each hand reading its own picture to begin with,
          // a keyboard present (the layers need one) and a fifth in each half.
          const setup = Object.assign({}, findPreset('b:Crossed hands'), { pictureAmount: 0, scanReadsA: 'A', scanReadsB: 'B' });
          hostQuietly(() => restore(setup)); hostSendSetup();
          await wait(300);
          setScreenKeys(true);
          for (const n of [43, 50, 72, 79]) midiNoteOn(n, 100);
          await wait(2500);
          const own = loopOverlay.drawn.rings.map((r) => [r.layer, r.picture]);
          el.scanReadsA.value = 'B'; el.scanReadsA.dispatchEvent(new Event('change'));
          el.scanReadsB.value = 'A'; el.scanReadsB.dispatchEvent(new Event('change'));
          await wait(1500);
          const crossed = loopOverlay.drawn.rings.map((r) => [r.layer, r.picture]);
          const heads = loopView().heads.slice();
          for (const n of [43, 50, 72, 79]) midiNoteOff(n);
          el.scanReadsA.value = 'A'; el.scanReadsA.dispatchEvent(new Event('change'));
          el.scanReadsB.value = 'B'; el.scanReadsB.dispatchEvent(new Event('change'));
          el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change')); setScreenKeys(false); midiPanic();
          return { own, crossed, heads };
        }""")
        print("    own %s, crossed %s, heads %s" % (split["own"], split["crossed"], split["heads"]))
        check("split, each layer's ring on its own picture", sorted(split["own"]) == [[0, 0], [1, 1]], str(split["own"]))
        check("crossed, each on the other's", sorted(split["crossed"]) == [[0, 1], [1, 0]], str(split["crossed"]))
        null("crossed is not what split was", sorted(split["crossed"]) != sorted(split["own"]))
        check("and both layers have a read-head", all(0 <= h < 1 for h in split["heads"]), str(split["heads"]))

        print("\n--- remembered ---")
        p.reload(); p.wait_for_timeout(2500)
        back = p.evaluate("() => ({ on: loopOverlay.on, hidden: el.loopOverlay.hidden })")
        check("reloaded, still on: a view this viewer chose", back["on"] is True and back["hidden"] is False, str(back))
        p.click("#loopButton"); p.wait_for_timeout(200)
        p.reload(); p.wait_for_timeout(2500)
        gone = p.evaluate("() => loopOverlay.on")
        check("and off once turned off", gone is False)
        check("no page errors", not bad, "; ".join(bad[:3]))
        ctx.close()

    print("\n=== at a phone's width ===")
    c, p, bad = open_page(b, "", viewport=(390, 844))
    p.evaluate(SCANNING, 220)
    fit = p.evaluate("""() => { const r = el.loopButton.getBoundingClientRect();
      return { left: r.left, right: r.right, w: r.width, vw: window.innerWidth, scroll: document.documentElement.scrollWidth,
               shown: !!el.loopButton.offsetParent }; }""")
    check("the Loop button is on screen at 390 px", fit["shown"] and fit["left"] >= 0 and fit["right"] <= fit["vw"] and fit["w"] > 0, str(fit))
    check("and nothing scrolls sideways", fit["scroll"] <= fit["vw"], "%d of %d" % (fit["scroll"], fit["vw"]))
    p.click("#loopButton"); p.wait_for_timeout(500)
    size = p.evaluate("() => ({ o: [el.loopOverlay.width, el.loopOverlay.height], t: [el.trace.width, el.trace.height] })")
    check("the overlay is the trace's size, pixel for pixel", size["o"] == size["t"], str(size))
    cost = p.evaluate("""() => { const t0 = performance.now(); for (let i = 0; i < 200; i++) drawLoopOverlay(); return (performance.now() - t0) / 200; }""")
    check("a frame of it costs under 2 ms at a phone's width", 0 < cost < 2, "%.3f ms" % cost)
    null("the bound can fail: no frame costs nothing", not (cost <= 0), "%.3f ms" % cost)
    check("no page errors", not bad, "; ".join(bad[:3]))
    c.close()
    b.close()

print("\nLOOP OVERLAY " + ("PASS" if not fails else "FAIL: " + ", ".join(fails)))
sys.exit(1 if fails else 0)
