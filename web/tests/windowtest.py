"""The window (F8): the Size setting, the compact face, the verdict under the
screen and the rack that folds only when it has to.

What would go wrong, and what is checked for it:

- a Size button that paints itself chosen and zooms nothing, or zooms and is
  forgotten: each is pressed with the mouse, in Settings, and the page's zoom,
  the stored key and the buttons' state are read; the page is opened again
  and must come back at the size chosen, and Auto must forget it, so a fresh
  window is Auto again;
- Auto zooming the wrong windows: the plugin's minimum, 960x600, must be at
  90 and its default, 1200x680, at 100, with the edges either side of the
  thresholds (1099 and 1100 wide, 679 and 680 tall) read, so a threshold off
  by one or compared the wrong way round is seen. A window resized in place
  must change its zoom and face with it, not only one opened at that size;
- the compact face chosen from the device rather than the window, or from the
  window without the zoom: at 1400x900 it is the full face at 100 and compact
  at 125, where the page is 1120x720 to itself;
- the verdict left in a band across the window on the Bench, or not put back
  on Scope: its parent and neighbours are read in both views and after going
  round twice;
- the rack folding always, as F5 did, or never: at 1400x900 with every effect
  on and the Plane open the others keep their knobs; at 1200x680 they fold and
  the tab does not scroll, and the null is the same rack with the fold taken
  off, which must scroll - otherwise the fold is not what fits it. A module
  switched on by a value, with no press on the rack, must fold the others too
  (paintRack), and closing the module must unfold them.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, ok):
    # A check fed a known-wrong value must go red; one that never has is not believed.
    print(("  PASS  " if not ok else "  FAIL  ") + "null: " + name)
    if ok: fails.append("null: " + name)

READ = """() => ({ zoom: pageZoom, css: document.documentElement.style.zoom,
  stored: (() => { try { return localStorage.getItem('scope.size'); } catch (e) { return 'n/a'; } })(),
  checked: ['sizeAuto', 'size90', 'size100', 'size125'].filter((id) => el[id].getAttribute('aria-checked') === 'true'),
  compact: document.body.dataset.compact !== undefined })"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    bad = []

    def open_page(ctx, w, h):
        p = ctx.new_page()
        p.set_viewport_size({"width": w, "height": h})
        p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
        p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
        if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
        return p

    print("\n--- Size, pressed and remembered ---")
    ctx = b.new_context()
    p = open_page(ctx, 1400, 900)
    r = p.evaluate(READ)
    check("a fresh window is Auto, at 100, the full face", r["zoom"] == 1 and r["css"] == "" and r["stored"] is None
          and r["checked"] == ["sizeAuto"] and not r["compact"], str(r))
    def press(id):
        if not p.locator("#" + id).is_visible():
            p.locator("#menuButton").click(); p.wait_for_timeout(200)
        p.locator("#" + id).click(); p.wait_for_timeout(250)
        return p.evaluate(READ)
    r = press("size90")
    ok90 = lambda r: r["zoom"] == 0.9 and r["css"] == "0.9" and r["stored"] == "0.9" and r["checked"] == ["size90"]
    check("90% pressed: the page at 0.9, stored, and only 90% marked", ok90(r), str(r))
    null("the same check reads Auto's state as 90%", ok90({"zoom": 1, "css": "", "stored": None, "checked": ["sizeAuto"]}))
    r = press("size125")
    check("125% pressed: the page at 1.25, stored, and only 125% marked",
          r["zoom"] == 1.25 and r["css"] == "1.25" and r["stored"] == "1.25" and r["checked"] == ["size125"], str(r))
    check("and at 125 a 1400x900 window is 1120x720 to the page, so the face is compact", r["compact"], str(r))
    p.close()
    p = open_page(ctx, 1400, 900)
    r = p.evaluate(READ)
    check("opened again, it comes back at 125 with 125% marked", r["zoom"] == 1.25 and r["checked"] == ["size125"], str(r))
    r = press("size100")
    check("100% pressed: no zoom on the page, stored as 1, the full face",
          r["zoom"] == 1 and r["css"] == "" and r["stored"] == "1" and not r["compact"], str(r))
    r = press("sizeAuto")
    check("Auto pressed: the key forgotten and Auto marked", r["stored"] is None and r["checked"] == ["sizeAuto"], str(r))
    p.close()
    p = open_page(ctx, 960, 600)
    r = p.evaluate(READ)
    check("and a window opened after Auto is Auto again: 960x600 at 90", r["zoom"] == 0.9 and r["checked"] == ["sizeAuto"], str(r))
    p.close(); ctx.close()

    print("\n--- Auto, at the plugin's sizes and either side of the thresholds ---")
    # (width, height, zoom Auto must choose, compact). Compact is decided in the
    # page's pixels: 960x600 at 0.9 is 1067x667, under 1100 and 860; 1099x900
    # at 0.9 is 1221x1000, the full face.
    cases = [(960, 600, 0.9, True), (1200, 680, 1, True), (1099, 900, 0.9, False), (1100, 900, 1, False),
             (1400, 679, 0.9, True), (1400, 680, 1, True), (1400, 859, 1, True), (1400, 860, 1, False),
             (1400, 900, 1, False)]
    got = {}
    ctx = b.new_context()
    for w, h, z, c in cases:
        p = open_page(ctx, w, h)
        r = p.evaluate(READ)
        got[(w, h)] = (r["zoom"], r["compact"])
        p.close()
    want = {(w, h): (z, c) for w, h, z, c in cases}
    check("Auto's zoom and the compact face at every size, edges included", got == want,
          str({k: v for k, v in got.items() if want[k] != v}) or "all as expected")
    # The null: thresholds compared the other way at the edge - 1100 zoomed and
    # 1099 not - must be told from the page's answer.
    null("an edge read the wrong way round is not what the page does",
         got == {**want, (1099, 900): (1, True), (1100, 900): (0.9, False)})

    p = open_page(ctx, 1400, 900)
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(200)
    before = p.evaluate(READ)
    p.set_viewport_size({"width": 960, "height": 600}); p.wait_for_timeout(400)
    after = p.evaluate(READ)
    cols = p.evaluate("() => el.benchBody.querySelectorAll(':scope > .bench-col').length")
    check("a window resized in place from 1400x900 to 960x600 goes to 90 and compact",
          before["zoom"] == 1 and not before["compact"] and after["zoom"] == 0.9 and after["compact"], "%s -> %s" % (before, after))
    over = p.evaluate("() => el.benchBody.scrollHeight - el.benchBody.clientHeight")
    check("and its tab is dealt again and does not scroll", over <= 0, "over %d px, %d columns" % (over, cols))
    p.set_viewport_size({"width": 1400, "height": 900}); p.wait_for_timeout(400)
    back = p.evaluate(READ)
    check("and resized back it is the full face at 100 again", back["zoom"] == 1 and not back["compact"], str(back))
    p.close(); ctx.close()

    print("\n--- the compact face as drawn: three columns, and the keys under the cards ---")
    COLS = """() => { setView('bench'); setBenchTab('play');
      const W = el.benchBody.clientWidth;
      return { dealt: Array.from(el.benchBody.querySelectorAll(':scope > .bench-col')).filter((c) => c.children.length).length,
               full: Math.floor((W + BENCH_GAP) / (BENCH_COL + BENCH_GAP)), W } }"""
    ctx = b.new_context()
    for w, h in [(960, 600), (1100, 680)]:
        p = open_page(ctx, w, h)
        r = p.evaluate(COLS)
        # The mockup draws the minimum in three columns. Two also fit, so the fit
        # cannot tell; this is what holds the drawing.
        check("at %dx%d Play is dealt in three columns, as the minimum is drawn" % (w, h), r["dealt"] == 3, str(r))
        check("null: the full face's column at that width would deal two", r["full"] == 2, str(r))
        if (w, h) == (960, 600):
            k = p.evaluate("""async () => { setScreenKeys(true); await new Promise((r) => setTimeout(r, 250));
              const keys = document.querySelector('.screen-keys').getBoundingClientRect();
              const cards = el.modStrip.getBoundingClientRect();
              // The lowest control on the tab: what a hand reaches for.
              const ctl = Array.from(el.benchBody.querySelectorAll('input, select, button, .knob-face'))
                .map((e) => e.getBoundingClientRect()).filter((r) => r.height > 0);
              const low = Math.max(...ctl.map((r) => r.bottom));
              setScreenKeys(false);
              return { top: keys.top, height: keys.height, bottom: keys.bottom, cards: cards.bottom, low }; }""")
            check("at 960x600 the keys stop under the modulation cards and the tab's lowest control",
                  k["top"] >= k["cards"] and k["top"] >= k["low"], str(k))
            # The null: keys at the full face's 175 px from the same foot.
            full_top = k["bottom"] - 175
            check("null: keys at the full face's height from the same foot would cover the cards",
                  full_top < k["cards"], "top would be %.0f, cards end at %.0f" % (full_top, k["cards"]))
        p.close()
    ctx.close()

    print("\n--- the verdict under the screen ---")
    ctx = b.new_context()
    p = open_page(ctx, 1400, 900)
    WHERE = """() => { const d = el.dock; return { parent: d.parentElement.className.split(' ')[0] || d.parentElement.tagName,
      before: d.nextElementSibling && d.nextElementSibling.id, after: d.previousElementSibling && d.previousElementSibling.tagName,
      shown: el.verdict.getBoundingClientRect().height > 0,
      under: el.verdict.getBoundingClientRect().top >= el.benchScope.getBoundingClientRect().bottom - 1 } }"""
    p.evaluate("() => setView('scope')"); p.wait_for_timeout(200)
    scope0 = p.evaluate(WHERE)
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(200)
    bench = p.evaluate(WHERE)
    check("on the Bench the verdict is in the screen's column, under the screen and over the modulation cards",
          bench["parent"] == "bench-side" and bench["before"] == "modStrip" and bench["shown"] and bench["under"], str(bench))
    null("the Scope view's place is not the Bench's", scope0["parent"] == "bench-side" and scope0["before"] == "modStrip")
    p.evaluate("() => { setView('scope'); setView('bench'); setView('scope'); }"); p.wait_for_timeout(200)
    scope1 = p.evaluate(WHERE)
    check("on Scope it is back across the foot where it started, after going round twice",
          scope1["parent"] == scope0["parent"] and scope1["before"] == scope0["before"] and scope1["after"] == scope0["after"]
          and scope1["shown"] and scope0["parent"] != "bench-side", "%s / %s" % (scope0, scope1))
    check("and there is one verdict on the page", p.evaluate("() => document.querySelectorAll('#verdict, #dock').length") == 2)
    p.close(); ctx.close()

    print("\n--- the rack folds only when it has to ---")
    RACK = """async ([layers]) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setView('bench'); setBenchTab('space'); await wait(150);
      // A split needs a keyboard present: the screen's, as fittest has it.
      if (layers) { setScreenKeys(true); await wait(100); setMidiMode('poly'); el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
                    await wait(120); el.planeLayerB.click(); await wait(120); }
      // Read back, so a case that never split (no source yet, say) cannot pass as one.
      const layered = !el.planeLayerRow.hidden && !el.timeLayerRow.hidden;
      for (const id of ['delayMix', 'chorusMix', 'phaserMix']) setControl(id, 40);
      await wait(600);
      openFx('plane', true); await wait(200);
      const rack = document.getElementById('rackGroup');
      const read = () => ({ tight: rack.dataset.tight !== undefined,
        over: el.benchBody.scrollHeight - el.benchBody.clientHeight,
        knobs: ['phaser', 'chorus', 'delay'].map((fx) =>
          getComputedStyle(document.querySelector('.fx-module[data-fx="' + fx + '"] .fx-main')).display !== 'none') });
      const open = read();
      // The null: the same rack with the fold taken off, measured in the same frame.
      delete rack.dataset.tight; const unfolded = el.benchBody.scrollHeight - el.benchBody.clientHeight;
      if (open.tight) rack.dataset.tight = '';
      openFx(null); await wait(150);
      const closed = read();
      /* A module switched on by a value, no press on the rack: the Plane open
         with the others off (folded to their lines by being off), then their
         mixes written as a host knob would. */
      for (const id of ['delayMix', 'chorusMix', 'phaserMix']) setControl(id, 0);
      await wait(600); openFx('plane', true); await wait(200);
      const offOpen = read();
      for (const id of ['delayMix', 'chorusMix', 'phaserMix']) setControl(id, 40);
      await wait(700);
      const valued = read();
      openFx(null);
      return { layered, open, unfolded, closed, offOpen, valued };
    }"""
    ctx = b.new_context()
    for w, h, layers in [(1400, 900, False), (1400, 900, True), (1200, 680, False), (1200, 680, True)]:
        p = open_page(ctx, w, h)
        # The sound started, as a player starts it: a split needs a source to lay out.
        p.locator("#trace").click(position={"x": 5, "y": 5}); p.wait_for_timeout(600)
        r = p.evaluate(RACK, [layers])
        tag = "%dx%d%s" % (w, h, ", two layers" if layers else "")
        check("at %s the Plane's and the Delay's Layers rows are %s" % (tag, "on show" if layers else "hidden"),
              r["layered"] == layers)
        if w == 1400:
            check("at %s, every effect on and the Plane open, the others keep their knobs" % tag,
                  not r["open"]["tight"] and all(r["open"]["knobs"]) and r["open"]["over"] <= 0, str(r["open"]))
        else:
            check("at %s, every effect on and the Plane open, the others fold to their lines and the tab does not scroll" % tag,
                  r["open"]["tight"] and not any(r["open"]["knobs"]) and r["open"]["over"] <= 0, str(r["open"]))
            check("null: unfolded, the same rack at %s scrolls, so the fold is what fits it" % tag, r["unfolded"] > 0,
                  "%d px over" % r["unfolded"])
            check("at %s, switched on by their mixes with the Plane open, the others fold within the rack's repaint" % tag,
                  not r["offOpen"]["tight"] and r["valued"]["tight"] and r["valued"]["over"] <= 0,
                  "%s -> %s" % (r["offOpen"], r["valued"]))
        check("at %s, with nothing open, the rack is not folded and its modules show their knobs" % tag,
              not r["closed"]["tight"] and all(r["closed"]["knobs"]), str(r["closed"]))
        p.close()
    ctx.close()
    b.close()

if bad:
    print("  FAIL  the page threw: " + "; ".join(bad[:3])); fails.append("pageerror")
print("\n%d failed" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
