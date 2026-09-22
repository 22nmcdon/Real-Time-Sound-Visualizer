"""Patching, per input method.

Pointer drag, tap-to-arm and keyboard are three different code paths and the
obvious test only covers the first. Tap-to-arm in particular is a whole target
interaction that nothing else here would exercise - the same gap as the
stereo-hardware check, except this one can be automated, so it is.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
SHOTS = os.path.join(HERE, "shots"); os.makedirs(SHOTS, exist_ok=True)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

ROUTES = "() => state.modRoutings.map((r) => r.sourceId + '>' + r.destId + '@' + r.amount)"

def section(page, name):
    """The bench shows one section at a time, so a control in another one is
    genuinely not on screen. Reach it the way a person would."""
    page.evaluate("""(want) => {
      for (const button of document.querySelectorAll('#benchRail button')) {
        if (button.textContent === want) { button.click(); return; }
      }
    }""", name)
    page.wait_for_timeout(200)


def open_bench(page):
    page.goto(f"file://{ART}/scope.html"); page.wait_for_timeout(700)
    if page.locator("#helpClose").is_visible(): page.locator("#helpClose").click()
    page.wait_for_timeout(150)
    page.evaluate("() => { setView('bench'); state.modRoutings = []; touchRoutings(); }")
    page.wait_for_timeout(300)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    # ---------------- pointer ----------------------------------------------
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    open_bench(p)

    print("\n--- pointer: drag a chip onto a control ---")
    chip = p.locator('.mod-chip[data-source="lfo1"]')
    target = p.locator('[data-mod-dest="gen.freq"]')
    check("the sources rail is there", chip.is_visible())
    cb, tb = chip.bounding_box(), target.bounding_box()
    p.mouse.move(cb["x"] + cb["width"] / 2, cb["y"] + cb["height"] / 2)
    p.mouse.down()
    p.mouse.move(tb["x"] + 40, tb["y"] + tb["height"] / 2, steps=12)
    highlighted = p.evaluate("() => document.querySelectorAll('.mod-target').length")
    p.mouse.up(); p.wait_for_timeout(200)
    check("the control lights up under the chip", highlighted == 1, str(highlighted))
    check("the drop makes a routing", p.evaluate(ROUTES) == ["lfo1>gen.freq@0.35"],
          str(p.evaluate(ROUTES)))
    check("and a depth row appears under it",
          p.locator('[data-mod-dest="gen.freq"] + .mod-rows .mod-row').count() == 1)

    print("\n--- pointer: the depth row is the depth ---")
    trackbox = p.locator('[data-mod-dest="gen.freq"] + .mod-rows .mod-track').bounding_box()
    p.mouse.move(trackbox["x"] + trackbox["width"] * 0.9, trackbox["y"] + trackbox["height"] / 2)
    p.mouse.down()
    p.mouse.move(trackbox["x"] + trackbox["width"] * 0.9, trackbox["y"] + trackbox["height"] / 2, steps=3)
    p.mouse.up(); p.wait_for_timeout(200)
    after = p.evaluate("() => state.modRoutings[0].amount")
    check("dragging it right raises the depth", after > 0.7, "%.2f" % after)

    p.mouse.move(trackbox["x"] + trackbox["width"] * 0.1, trackbox["y"] + trackbox["height"] / 2)
    p.mouse.down(); p.mouse.move(trackbox["x"] + trackbox["width"] * 0.1,
                                 trackbox["y"] + trackbox["height"] / 2, steps=3)
    p.mouse.up(); p.wait_for_timeout(200)
    negative = p.evaluate("() => state.modRoutings[0].amount")
    check("and left inverts it", negative < -0.7, "%.2f" % negative)

    zeroed = p.evaluate("""() => {
      state.modRoutings[0].amount = 0; touchRoutings();
      return state.modRoutings.length;
    }""")
    p.wait_for_timeout(200)
    check("a depth of zero does NOT remove the routing", zeroed == 1, str(zeroed))

    print("\n--- pointer: removing ---")
    p.locator('[data-mod-dest="gen.freq"] + .mod-rows .mod-x').first.click()
    p.wait_for_timeout(200)
    check("the cross removes it", p.evaluate(ROUTES) == [], str(p.evaluate(ROUTES)))

    print("\n--- keyboard ---")
    p.locator('[data-mod-dest="gen.phase"] .mod-add').click()
    p.wait_for_timeout(150)
    picker = p.locator(".mod-picker")
    check("the plus offers a menu", picker.count() == 1)
    picker.select_option("lfo2"); p.wait_for_timeout(200)
    check("choosing from it patches", p.evaluate(ROUTES) == ["lfo2>gen.phase@0.35"],
          str(p.evaluate(ROUTES)))

    p.locator('[data-mod-dest="gen.phase"] + .mod-rows .mod-row').first.focus()
    p.keyboard.press("Delete"); p.wait_for_timeout(200)
    check("and Delete on a focused row removes it", p.evaluate(ROUTES) == [],
          str(p.evaluate(ROUTES)))

    print("\n--- several sources on one destination ---")
    many = p.evaluate("""() => {
      state.modRoutings = [
        { sourceId: 'lfo1', destId: 'view.rotate', amount: 0.4 },
        { sourceId: 'lfo2', destId: 'view.rotate', amount: -0.25 },
        { sourceId: 'env.live', destId: 'view.rotate', amount: 0.6 },
      ];
      touchRoutings();
      return true;
    }""")
    p.wait_for_timeout(250)
    rows = p.locator('[data-mod-dest="view.rotate"] + .mod-rows .mod-row')
    check("one labelled row per routing", rows.count() == 3, str(rows.count()))
    labels = p.evaluate("""() => Array.from(
      document.querySelectorAll('[data-mod-dest="view.rotate"] + .mod-rows .mod-name'))
      .map((n) => n.textContent)""")
    check("each row says which source it is", labels == ["LFO 1", "LFO 2", "Level"], str(labels))
    inks = p.evaluate("""() => Array.from(
      document.querySelectorAll('[data-mod-dest="view.rotate"] + .mod-rows .mod-row'))
      .map((r) => getComputedStyle(r).getPropertyValue('--chip').trim())""")
    check("in three different inks", len(set(inks)) == 3, str(inks))

    summed = p.evaluate("""() => {
      lfos[0].value = 1; lfos[1].value = 1;
      const f = capture();
      applyModMatrix(f, 16);
      return { mod: state.rotateMod, env: MOD_SOURCES.get('env.live').value() };
    }""")
    check("and the offset is their sum",
          abs(summed["mod"] - (0.4 - 0.25 + 0.6 * summed["env"])) < 1e-6,
          "%.4f" % summed["mod"])

    print("\n--- clearing in bulk ---")
    section(p, "Display")
    p.locator('[data-mod-dest="view.rotate"] + .mod-rows [data-clear]').click()
    p.wait_for_timeout(200)
    check("clear empties that control", p.evaluate(ROUTES) == [], str(p.evaluate(ROUTES)))

    p.evaluate("""() => {
      state.modRoutings = [
        { sourceId: 'lfo1', destId: 'view.rotate', amount: 0.4 },
        { sourceId: 'lfo1', destId: 'gen.freq', amount: 0.2 },
        { sourceId: 'lfo2', destId: 'gen.phase', amount: 0.3 },
      ];
      touchRoutings();
    }"""); p.wait_for_timeout(250)
    count = p.evaluate("""() => document.querySelector('.mod-chip[data-source="lfo1"] .count').textContent""")
    check("a chip counts what it drives", count == "2", count)
    p.locator('.mod-chip[data-source="lfo1"] .clear').click(); p.wait_for_timeout(250)
    check("and clearing the chip drops only its own",
          p.evaluate(ROUTES) == ["lfo2>gen.phase@0.3"], str(p.evaluate(ROUTES)))

    print("\n--- the routings survive a view change ---")
    p.evaluate("() => setView('scope')"); p.wait_for_timeout(250)
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(300)
    check("still patched", p.evaluate(ROUTES) == ["lfo2>gen.phase@0.3"], str(p.evaluate(ROUTES)))
    check("and still exactly one row",
          p.locator('.mod-rows .mod-row').count() == 1,
          str(p.locator('.mod-rows .mod-row').count()))
    check("with no duplicate ids", p.evaluate("""() => {
      const seen = new Set(), dupes = [];
      for (const n of document.querySelectorAll('[id]')) {
        if (seen.has(n.id)) dupes.push(n.id); else seen.add(n.id);
      }
      return dupes; }""") == [])
    p.screenshot(path=f"{SHOTS}/bench-patched.png")
    check("no page errors", not bad, "; ".join(bad[:3]))
    p.close()

    # ---------------- touch -------------------------------------------------
    print("\n--- tap to arm, on a touch screen ---")
    ctxb = b.new_context(viewport={"width": 430, "height": 900}, has_touch=True, is_mobile=True)
    t = ctxb.new_page()
    tbad = []
    t.on("pageerror", lambda e: tbad.append("pageerror: " + str(e)))
    open_bench(t)

    t.locator('.mod-chip[data-source="env.live"]').tap(); t.wait_for_timeout(200)
    check("tapping a chip arms it",
          t.evaluate("() => armedSource") == "env.live",
          str(t.evaluate("() => armedSource")))
    check("and it says so on the chip",
          t.locator('.mod-chip[data-source="env.live"]').get_attribute("aria-pressed") == "true")

    t.locator('.mod-chip[data-source="env.live"]').tap(); t.wait_for_timeout(200)
    check("tapping it again cancels", t.evaluate("() => armedSource") is None)

    section(t, "Display")
    t.locator('.mod-chip[data-source="env.live"]').tap(); t.wait_for_timeout(150)
    t.locator('[data-mod-dest="view.rotate"]').tap(); t.wait_for_timeout(250)
    check("tap a chip then a control patches it",
          t.evaluate(ROUTES) == ["env.live>view.rotate@0.35"], str(t.evaluate(ROUTES)))
    check("and the chip disarms itself", t.evaluate("() => armedSource") is None)

    t.locator('.mod-chip[data-source="lfo1"]').tap(); t.wait_for_timeout(150)
    t.locator("#benchRail button").first.tap(); t.wait_for_timeout(250)
    check("tapping something unpatchable cancels rather than doing nothing",
          t.evaluate("() => armedSource") is None
          and len(t.evaluate(ROUTES)) == 1, str(t.evaluate(ROUTES)))

    check("the remove button is always visible on touch",
          t.evaluate("""() => {
            const x = document.querySelector('.mod-rows .mod-x');
            return x ? Number(getComputedStyle(x).opacity) : 0;
          }""") == 1)
    check("no sideways overflow while patched",
          t.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"))
    t.screenshot(path=f"{SHOTS}/bench-touch.png", full_page=True)
    check("no page errors on touch", not tbad, "; ".join(tbad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all patching checks pass")
