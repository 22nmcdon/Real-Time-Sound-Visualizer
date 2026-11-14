"""Scan (P7a): the phosphor read back as the voice's wave.

Sixty times a second of audio time, the screen's light is read round an
off-centre circle into one cycle of a wave, the voice plays it at the note's
pitch, and each tick's table is crossfaded into the next across the tick -
round one of the Scan experiment, the take the owner chose. Each claim is
checked against the way it would fail:

- the reading: a table that is not the reading's harmonics, a level that
  keeps what would fold, a quiet picture played quieter, darkness divided by
  nothing, a symmetric figure read from its centre (three times too high, as
  P2 found), softness that does not soften;
- the tick: a table that lands when the page sends it rather than at the
  next sixtieth of a second of samples, a crossfade that is a step or the
  wrong length, at three sample rates;
- the voice: nought that changes anything, a pitch that is not the note's,
  a depth that takes the whole voice, a hold that does not rein it in, a
  bend that does not reach it, layer B's Scan in layer A;
- the page: the controls and a setup code's round trip (the depth per layer,
  the softness, Persistence in seconds between the menu's five), the freeze
  while a setup lands, the running-away hold, each layer reading its own
  figure;
- and the first-minute test: a turning fifth, read back, moves its timbre
  within seconds, where without Scan it stands still - and held still, by
  stopping the screen, Scan is an ordinary tone.

Since stage 5, step 3, batch 3 (13 Nov), the reading, the tick, the voice,
the freeze and the hold are the core's own numbers, held in
core/tests/pieces/scan.py with their nulls. This suite opens the site as a
visitor does, on the compiled instrument, which reads its own screen at
sixty frames a second of the sound: the controls and a setup code's round
trip, the split's depth, and the first minute, heard there.
Every assertion has its null beside it.
"""
import os, statistics, sys
from playwright.sync_api import sync_playwright
import corpus

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



with sync_playwright() as pw:
    # Until stage 5, step 3, batch 3 (13 Nov) most of this suite ran on the
    # page's own brain (?brain=js&core=js): `scanTables`, `scanRead`,
    # `scanGeometry` and `scanFollow` on readings and grids made in the page,
    # a `makeGeneratorCore` built there with tables put in by hand, the
    # page's posts of a table counted for the freeze, its `pictureStage` and
    # `genSettings().scanHold` read under a grid filled by hand, and a voice
    # rebuilt through its worklet plumbing. The reading, the tick, the voice,
    # the freeze and the hold are core/tests/pieces/scan.py's now, on the
    # core alone, each with its null (and the old null for layer B, which
    # subtracted B's lanes from themselves and so could not fail, is two
    # that can); the rebuilt voice was the page brain's plumbing and went
    # with it. What stays is the face and the sound, on the site as a
    # visitor opens it.
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1200)
    corpus.install(p)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.locator("#trace").click(position={"x": 5, "y": 5})   # the press a browser waits for
    p.wait_for_timeout(800)

    # ------------------------------------------------------------------
    print("\n--- the page ---")
    # The fifths here and below are the old library's, from before P8g: an
    # equal fifth with no Scan, and the same with Scan at full, which is what
    # every check of this section was measured on. The bank has neither.
    # The depth was read off `genSettings().scan` and the softness off
    # `scan.soft`, the page brain's own; on the site those are the page's
    # mirror, which the face writes whatever the instrument does, so they
    # read the setup the face sends instead (`snapshot()`), and the slider.
    # What the instrument does with each hand's depth is parity's ("in a
    # split, the instrument hands each layer its own depth ...").
    ctl = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      loadCorpus('Perfect fifth, equal'); await wait(500);
      el.oscScan.value = '60'; el.oscScan.dispatchEvent(new Event('input', { bubbles: true }));
      el.scanSoft.value = '15'; el.scanSoft.dispatchEvent(new Event('input', { bubbles: true }));
      el.scanMemory.value = '70'; el.scanMemory.dispatchEvent(new Event('input', { bubbles: true }));
      const now = snapshot();
      const set = { scan: now.oscScan, reading: el.oscScanValue.textContent, soft: now.scanSoft,
                    pers: state.persistence, menu: el.persistence.value, menuText: el.persistence.selectedOptions[0].textContent,
                    memory: el.scanMemoryValue.textContent };
      const code = snapshot();
      restore({}); await wait(100);
      const c = snapshot();
      const cleared = { scan: c.oscScan, soft: c.scanSoft, pers: state.persistence, menu: el.persistence.value };
      restore(code); await wait(100);
      const k = snapshot();
      const back = { scan: k.oscScan, slider: el.oscScan.value, soft: k.scanSoft, pers: state.persistence,
                     menu: el.persistence.value, menuText: el.persistence.selectedOptions[0].textContent };
      el.persistence.value = '0.12'; el.persistence.dispatchEvent(new Event('change'));
      const menu = { slider: el.scanMemory.value, pers: state.persistence, custom: el.persistence.querySelector('option[data-memory]').hidden };
      return { set, code: { oscScan: code.oscScan, scanSoft: code.scanSoft, persistence: code.persistence }, cleared, back, menu };
    }""")
    s0 = ctl["set"]
    check("Depth writes the layer's scan, and says how much of the voice it is", s0["scan"] == 60 and s0["reading"] == "48%",
          str(s0))
    check("Persistence in seconds sets the phosphor's fade, and the menu shows its time when it is not one of the five",
          abs(s0["pers"] - (1 - 2 ** (-1 / (60 * 0.02 * 500 ** (69 / 98))))) < 1e-4 and s0["menu"] == str(s0["pers"])
          and s0["menuText"] == s0["memory"], "%s, menu %r reading %r" % (s0["pers"], s0["menuText"], s0["memory"]))
    bk = ctl["back"]
    check("a setup code carries the depth, the softness and that persistence, and brings them back",
          ctl["code"]["oscScan"] == 60 and ctl["code"]["scanSoft"] == 15 and bk["scan"] == 60 and bk["slider"] == "60"
          and bk["soft"] == 15 and bk["pers"] == s0["pers"] and bk["menuText"] == s0["memory"], str(ctl["code"]) + " " + str(bk))
    cl = ctl["cleared"]
    null("between them, the defaults: no Scan, three cells, no persistence", cl["scan"] == 0 and cl["soft"] == 30 and cl["pers"] == 0,
         str(cl))
    check("a persistence chosen in the menu moves the slider to its time and hides Memory's own",
          ctl["menu"]["pers"] == 0.12 and ctl["menu"]["slider"] == "25" and ctl["menu"]["custom"], str(ctl["menu"]))

    # The split: Depth edits the hand being edited. Its second half - B
    # reads its own figure's picture - read `layerPictures.engines` and
    # `scan.paths`, the page brain's, through its `scanRead`; on the core it
    # is parity's ("in a split, the instrument hands each layer ... its own
    # picture's grid") and pieces/strike.py's cross-scan. Poly and the split
    # by their buttons, which the instrument hears (setMidiMode it does not).
    p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      loadCorpus('Scanned fifth'); await wait(300);
      el.oscScan.value = '0'; el.oscScan.dispatchEvent(new Event('input', { bubbles: true }));
      midiPanic(); setScreenKeys(true);
    }""")
    p.evaluate("() => showControl('midiPoly')")
    p.locator("#midiPoly").click()
    lyr = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change', { bubbles: true }));
      for (const n of [48, 55, 79, 84]) midiNoteOn(n, 100);
      midi.layers.edit = 1; syncLayerPanel();
      // The Picture section the upper hand's own (G6): linked, Depth would be both hands'.
      setLink('picture', false);
      el.oscScan.value = '100'; el.oscScan.dispatchEvent(new Event('input', { bubbles: true }));
      await wait(300);
      const s = snapshot();
      const out = { a: s.oscScan, b: s.bScan, layers: midi.layers.mode, mode: midi.mode };
      for (const n of [48, 55, 79, 84]) midiNoteOff(n);
      midi.layers.edit = 0; syncLayerPanel();
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change', { bubbles: true })); setScreenKeys(false);
      return out;
    }""")
    check("with a split, Depth edits the layer on the panel: the upper hand's, and the lower's not",
          lyr["layers"] == "split" and lyr["a"] == 0 and lyr["b"] == 100, str(lyr))
    null("the lower hand's depth is not the upper's", lyr["a"] != lyr["b"], str(lyr))

    print("\n--- the first minute: a moving picture, read back ---")
    # Stopped at 2 s and judged from 6 s: Scan's path follows the figure over
    # a second (SCAN_FOLLOW), so once the screen stops it goes on closing on
    # the still figure, smoothly and one way, for a few seconds. Judged from
    # 3 s, one second on, the spread was that glide's tail, 0.0003 to 0.0032
    # by where the glide stood at the stop, and failed against a fifth of the
    # moving run's one time in three (6 Nov, and before). Four seconds on, it
    # is under 2 per cent of where it started.
    # The held run, on the site's instrument since stage 5, step 5a: Stop
    # tells the instrument (setRunning's scopeRunning), which holds the
    # picture it reads - nothing faded, captured or struck into it - so Scan
    # plays a held picture. Until 5a it ran on the page's own brain
    # (?brain=js&core=js), because on the site Stop held the face's screen
    # and not the instrument's: 0.0084 held against 0.0079 running (step 3,
    # batch 3). The run is below, with the site's other legs.
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

    # ------------------------------------------------------------------
    print("\n--- on the site's instrument ---")
    # The site as a visitor opens it: the compiled instrument, which reads
    # its own grid at its own picture frame. Its sound read off its picture
    # lanes, which are what is heard, as stagetest.py reads it; the picture
    # stage at nought by the slider, so what moves the sound is Scan; and the
    # depth at nought by the slider as the null, sent the way a hand's is.
    sd = lambda series, frm=0: statistics.pstdev([v for t_, v in series if t_ >= frm])
    SITE = """async ([scanOn, seconds]) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      // The old library's Scanned fifth, from before P8g, as on the page above, held.
      midiPanic(); loadCorpus('Scanned fifth'); heldTone(); await wait(400);
      el.pictureAmount.value = '0'; el.pictureAmount.dispatchEvent(new Event('input', { bubbles: true }));
      if (!scanOn) { el.oscScan.value = '0'; el.oscScan.dispatchEvent(new Event('input', { bubbles: true })); }
      await wait(600);
      const out = [], t0 = performance.now();
      while (performance.now() - t0 < seconds * 1000) {
        await wait(250);
        const [l] = state.source.getLatestWindow(4096);
        let e = 0, d = 0;
        for (let k = 1; k < l.length; k++) { e += l[k] * l[k]; d += (l[k] - l[k - 1]) ** 2; }
        out.push([(performance.now() - t0) / 1000, e > 1e-9 ? Math.sqrt(d / e) : 0, Math.sqrt(e / l.length)]);
      }
      return { out, host: BRAIN_IN_CORE && state.source.kind === 'host' };
    }"""
    def site(query, scan_on, script=None, args=None):
        bb = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
        pp = bb.new_page(viewport={"width": 1400, "height": 900})
        errs = []
        pp.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
        pp.goto(f"file://{ART}/scope.html" + query); pp.wait_for_timeout(1200)
        corpus.install(pp)
        if pp.locator("#helpClose").is_visible(): pp.locator("#helpClose").click()
        pp.locator("#trace").click(position={"x": 5, "y": 5})   # the press a browser waits for
        pp.wait_for_timeout(800)
        got = pp.evaluate(script or SITE, args or [scan_on, 5])
        got["errors"] = errs
        bb.close()
        return got
    on, off = site("", True), site("", False)
    son, soff = sd([(t_, v) for t_, v, _ in on["out"]]), sd([(t_, v) for t_, v, _ in off["out"]])
    print("    site: brightness with Scan +- %.4f, without +- %.4f; loud %.3f" % (son, soff, max(r for _, _, r in on["out"])))
    check("on the site's instrument, the turning fifth read back moves its timbre",
          on["host"] and son > 0.004 and max(r for _, _, r in on["out"]) > 0.02, "%.4f, on the instrument %s" % (son, on["host"]))
    null("and with Depth at nought there it stands still", off["host"] and soff < 0.001, "%.4f" % soff)
    # The first minute's second claim, here since stage 5, step 3, batch 3,
    # where it ran on the page's brain: the site's two legs are the same
    # fifth with Scan and without, so what it asks is theirs to answer.
    mon = statistics.mean([v for t_, v, _ in on["out"] if t_ <= 3])
    moff = statistics.mean([v for t_, v, _ in off["out"] if t_ <= 3])
    check("and within three seconds it is plainly not the fifth without Scan",
          abs(mon - moff) > 5 * soff + 0.005, "%.4f against %.4f" % (mon, moff))
    null("the fifth without Scan against itself", not (abs(moff - moff) > 5 * soff + 0.005))
    # Until stage 5, step 3, batch 3 the page's brain on the compiled
    # generator (?brain=js) was played here too, and had to send it its
    # tables: a check that existed to hold the two engines together, which
    # goes with the page's brain (step 5); the two legs above hold Scan on
    # the instrument the site plays.
    # The held run (5a): the Scanned fifth with Scan, stopped at 2 s, judged
    # from 6 s against itself before the stop, as it was on the page's brain;
    # and Run as its null - the same fifth on the same page, never stopped,
    # moving from 6 s as before it.
    HELD = SITE.replace("await wait(600);", "await wait(600); if (stopAt !== null) setTimeout(() => setRunning(false), stopAt * 1000);") \
        .replace("async ([scanOn, seconds]) => {", "async ([scanOn, seconds, stopAt]) => {") \
        .replace("return { out, host:", "setRunning(true);\n      return { out, host:")
    assert HELD.count("setRunning(false)") == 1 and "stopAt" in HELD
    held, free = site("", True, HELD, [True, 8, 2]), site("", True, HELD, [True, 8, None])
    hv, fv = [(t_, v) for t_, v, _ in held["out"]], [(t_, v) for t_, v, _ in free["out"]]
    before = [x for x in hv if x[0] < 2]
    print("    site, held: brightness before the stop +- %.4f; stopped, from 6 s +- %.4f; never stopped, from 6 s +- %.4f"
          % (sd(before), sd(hv, 6), sd(fv, 6)))
    check("held still - the screen stopped, and the instrument told - Scan is an ordinary tone: the brightness stands",
          held["host"] and sd(hv, 6) < sd(before) / 5 and sd(hv, 6) < 0.001, "%.4f against %.4f before the stop" % (sd(hv, 6), sd(before)))
    null("the held run, before it stopped, was moving", sd(before) > 0.001, "%.4f" % sd(before))
    null("and Run, never stopped, goes on moving from 6 s", free["host"] and sd(fv, 6) > 5 * sd(hv, 6) and sd(fv, 6) > 0.001,
         "%.4f against %.4f held" % (sd(fv, 6), sd(hv, 6)))
    on["errors"] += held["errors"] + free["errors"]
    check("no page errors on the site", not (on["errors"] + off["errors"]), "; ".join((on["errors"] + off["errors"])[:3]))

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("everything passes")
