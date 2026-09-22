"""Patching, per input method.

Pointer, keyboard and touch are three different code paths and the obvious test
only covers the first. What they drive is one model: a source is ARMED in the
side column and stays armed, and while it is, every control on the page grows a
lane that is both how that source gets onto the control and how far it goes.

The property worth guarding hardest is at the bottom - that a control looks and
measures the same with nought, one, two and three sources on it. The design
before this one failed exactly there, and failed silently: it looked right until
the second source arrived.
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
    """Every section is on show now, so this is only needed to open a folded
    one and to put it in view."""
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
    page.evaluate("""() => {
      setView('bench'); state.modRoutings = []; armedSource = null; paintRoutings();
    }""")
    page.wait_for_timeout(350)


def lane_drag(page, elid, destId, fraction):
    """Drag a control's lane to a fraction of its track, the way a hand would.
    Returns the depth that landed on the routing."""
    geo = page.evaluate("""(a) => {
      const input = document.getElementById(a.elid);
      const grab = document.querySelector('[data-mod-dest="' + a.dest + '"] .lane-grab');
      const i = input.getBoundingClientRect(), g = grab.getBoundingClientRect();
      return { ix: i.x, iw: i.width, gy: g.y + g.height / 2 };
    }""", {"elid": elid, "dest": destId})
    # The track is inset by half a thumb at each end, and the lane with it.
    x = geo["ix"] + 6.5 + (geo["iw"] - 13) * fraction
    page.mouse.move(geo["ix"] + geo["iw"] / 2, geo["gy"])
    page.mouse.down()
    page.mouse.move(x, geo["gy"], steps=6)
    page.mouse.up(); page.wait_for_timeout(200)
    return page.evaluate("""(d) => {
      const r = state.modRoutings.find((r) => r.destId === d && r.sourceId === armedSource);
      return r ? r.amount : null;
    }""", destId)


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    # ---------------- pointer ----------------------------------------------
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    open_bench(p)

    print("\n--- arming is a mode ---")
    quiet = p.evaluate("""() => ({
      grabs: document.querySelectorAll('.lane-grab:not([hidden])').length,
      offers: document.querySelectorAll('.lane-offer:not([hidden])').length,
    })""")
    check("with nothing armed the lanes are quiet",
          quiet["grabs"] == 0 and quiet["offers"] == 0, str(quiet))

    p.locator('.mod-chip[data-source="lfo1"]').click(); p.wait_for_timeout(300)
    armed = p.evaluate("""() => ({
      armed: armedSource,
      said: document.querySelector('.mod-chip[data-source="lfo1"]')
        .getAttribute('aria-pressed'),
      grabs: document.querySelectorAll('.lane-grab:not([hidden])').length,
      offers: document.querySelectorAll('.lane-offer:not([hidden])').length,
    })""")
    check("clicking a chip arms it", armed["armed"] == "lfo1" and armed["said"] == "true",
          str(armed))
    check("and every control on show offers it a lane",
          armed["grabs"] >= 6 and armed["offers"] == armed["grabs"], str(armed))

    print("\n--- one gesture assigns and sets the depth ---")
    # The rotation, because its law is linear in its own slider: full depth is a
    # quarter of the track, so seven tenths along is +20 of -50..50 and 20/25 of
    # a depth. Frequency could not show an inverted depth at all - it is
    # exponential, and a tenth of the way along its track still asks for more
    # than 220 Hz.
    section(p, "Display")
    depth = lane_drag(p, "rotate", "view.rotate", 0.7)
    check("dragging a lane creates the routing", p.evaluate(ROUTES) != [], str(p.evaluate(ROUTES)))
    check("at the depth the drag implies", depth is not None and abs(depth - 0.8) < 0.05,
          "%.3f wanted 0.800" % (depth if depth is not None else -9))
    check("without touching the value underneath",
          p.evaluate("() => el.rotate.value") == "0", p.evaluate("() => el.rotate.value"))
    back = lane_drag(p, "rotate", "view.rotate", 0.3)
    check("and dragging the other way inverts it", abs(back + 0.8) < 0.05,
          "%.3f wanted -0.800" % back)

    print("\n--- and it stays armed ---")
    still = p.evaluate("() => armedSource")
    check("the source is still in hand after patching", still == "lfo1", str(still))
    section(p, "Filter")
    lane_drag(p, "filterCutoff", "filter.cutoff", 0.9)
    check("so a second control takes it without picking it up again",
          len(p.evaluate(ROUTES)) == 2, str(p.evaluate(ROUTES)))

    print("\n--- a depth of nothing is still a patch ---")
    zeroed = p.evaluate("""() => {
      state.modRoutings.forEach((r) => { if (r.destId === 'view.rotate') r.amount = 0; });
      touchRoutings();
      return state.modRoutings.filter((r) => r.destId === 'view.rotate').length;
    }"""); p.wait_for_timeout(250)
    check("a depth dragged to nothing leaves the routing alone", zeroed == 1, str(zeroed))

    print("\n--- taking it off ---")
    section(p, "Display")
    drop = p.locator('[data-mod-dest="view.rotate"] .mod-drop')
    check("the cross is offered while its own source is armed", drop.count() == 1)
    drop.click(); p.wait_for_timeout(250)
    check("and clicking it removes that one",
          [r for r in p.evaluate(ROUTES) if "view.rotate" in r] == [], str(p.evaluate(ROUTES)))

    print("\n--- keyboard ---")
    p.evaluate("() => { state.modRoutings = []; armedSource = null; paintRoutings(); }")
    p.wait_for_timeout(250)
    p.locator('[data-mod-dest="gen.phase"] .mod-add').click(); p.wait_for_timeout(150)
    picker = p.locator(".mod-picker")
    check("the plus offers a menu", picker.count() == 1)
    picker.select_option("lfo2"); p.wait_for_timeout(250)
    check("choosing from it patches", p.evaluate(ROUTES) == ["lfo2>gen.phase@0.35"],
          str(p.evaluate(ROUTES)))

    # The lane is a control, so it has to be reachable without a pointer. The
    # stack of rows this replaced could not be reached by keyboard at all.
    p.evaluate("() => armSource('lfo2')"); p.wait_for_timeout(250)
    p.locator('[data-mod-dest="gen.phase"] .lane-grab').focus()
    p.keyboard.press("ArrowRight"); p.keyboard.press("ArrowRight")
    p.wait_for_timeout(250)
    stepped = p.evaluate("() => state.modRoutings[0].amount")
    check("arrows on the focused lane set the depth", abs(stepped - 0.45) < 1e-6,
          "%.3f wanted 0.450" % stepped)
    p.locator('[data-mod-dest="gen.phase"] .lane-grab').focus()
    p.keyboard.press("Delete"); p.wait_for_timeout(250)
    check("and Delete on it removes the routing", p.evaluate(ROUTES) == [],
          str(p.evaluate(ROUTES)))

    print("\n--- dragging the chip itself still works ---")
    p.evaluate("() => { armedSource = null; paintRoutings(); }"); p.wait_for_timeout(200)
    chip = p.locator('.mod-chip[data-source="lfo1"]')
    target = p.locator('[data-mod-dest="gen.freq"]')
    cb, tb = chip.bounding_box(), target.bounding_box()
    p.mouse.move(cb["x"] + cb["width"] / 2, cb["y"] + cb["height"] / 2)
    p.mouse.down()
    p.mouse.move(tb["x"] + 40, tb["y"] + tb["height"] / 2, steps=12)
    highlighted = p.evaluate("() => document.querySelectorAll('.mod-target').length")
    p.mouse.up(); p.wait_for_timeout(250)
    check("the control lights up under the chip", highlighted == 1, str(highlighted))
    check("and the drop makes a routing", p.evaluate(ROUTES) == ["lfo1>gen.freq@0.35"],
          str(p.evaluate(ROUTES)))

    print("\n--- several sources on one control change nothing about it ---")
    # The whole point. The design before this one grew the control by a row per
    # attachment, which is what made two of them unusable.
    # Each measurement has to wait for the repaint it is measuring. The repaint
    # is coalesced into a frame on purpose - rebuilding sixty times a second
    # under a finger that is dragging would replace the element being dragged -
    # so reading in the same tick would have measured the page before anything
    # happened and passed for that reason alone.
    shape = p.evaluate("""async () => {
      const row = document.querySelector('[data-mod-dest="gen.freq"]');
      const input = document.getElementById('freq');
      const settle = () => new Promise((done) => requestAnimationFrame(
        () => requestAnimationFrame(done)));
      const snap = () => ({ h: row.offsetHeight,
                            x: Math.round(input.getBoundingClientRect().x),
                            w: Math.round(input.getBoundingClientRect().width) });

      state.modRoutings = []; armedSource = null; paintRoutings();
      await settle();
      const none = snap();
      addRouting('lfo1', 'gen.freq');     await settle();  const one = snap();
      addRouting('lfo2', 'gen.freq');     await settle();  const two = snap();
      addRouting('env.live', 'gen.freq'); await settle();  const three = snap();
      return { none, one, two, three,
               pips: row.querySelectorAll('.mod-pip').length,
               rows: row.nextElementSibling.querySelectorAll('.mod-row').length };
    }"""); p.wait_for_timeout(250)
    same = (shape["none"] == shape["one"] == shape["two"] == shape["three"])
    check("nought, one, two and three sources measure the same", same,
          "%s / %s / %s / %s" % (shape["none"], shape["one"], shape["two"], shape["three"]))
    check("three pips say who is on it", shape["pips"] == 3, str(shape["pips"]))
    check("and no row is added for any of them", shape["rows"] == 0, str(shape["rows"]))

    print("\n--- a pip is how you pick one of them up ---")
    p.locator('[data-mod-dest="gen.freq"] .mod-pip[data-source="lfo2"]').click()
    p.wait_for_timeout(250)
    picked = p.evaluate("""() => ({
      armed: armedSource,
      lane: document.querySelector('[data-mod-dest="gen.freq"] .lane-span').hidden,
      chip: document.querySelector('.mod-chip[data-source="lfo2"]')
        .getAttribute('aria-pressed'),
    })""")
    check("clicking a pip arms that source", picked["armed"] == "lfo2", str(picked))
    check("the chip in the rail agrees", picked["chip"] == "true", str(picked))
    check("and the lane switches to showing it", picked["lane"] is False, str(picked))

    print("\n--- a destination with no slider still gets rows ---")
    p.evaluate("""() => {
      state.modRoutings = [
        { sourceId: 'lfo1', destId: 'gen.ratio', amount: 0.4 },
        { sourceId: 'lfo2', destId: 'gen.ratio', amount: -0.25 },
      ];
      touchRoutings();
    }"""); p.wait_for_timeout(300)
    rows = p.locator('[data-mod-dest="gen.ratio"] + .mod-rows .mod-row')
    check("an interval is a menu, so it keeps the stacked rows", rows.count() == 2,
          str(rows.count()))

    print("\n--- the routings survive a view change ---")
    p.evaluate("""() => {
      state.modRoutings = [{ sourceId: 'lfo2', destId: 'gen.phase', amount: 0.3 }];
      touchRoutings();
    }"""); p.wait_for_timeout(250)
    p.evaluate("() => setView('scope')"); p.wait_for_timeout(300)
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(400)
    check("still patched", p.evaluate(ROUTES) == ["lfo2>gen.phase@0.3"], str(p.evaluate(ROUTES)))
    check("and still framed",
          "modulated" in p.locator('[data-mod-dest="gen.phase"]').get_attribute("class"))
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
    print("\n--- on a touch screen ---")
    ctxb = b.new_context(viewport={"width": 430, "height": 900}, has_touch=True, is_mobile=True)
    t = ctxb.new_page()
    tbad = []
    t.on("pageerror", lambda e: tbad.append("pageerror: " + str(e)))
    open_bench(t)

    t.locator('.mod-chip[data-source="env.live"]').tap(); t.wait_for_timeout(250)
    check("tapping a chip arms it", t.evaluate("() => armedSource") == "env.live",
          str(t.evaluate("() => armedSource")))
    check("and it says so on the chip",
          t.locator('.mod-chip[data-source="env.live"]').get_attribute("aria-pressed") == "true")

    section(t, "Display")
    lane = t.locator('[data-mod-dest="view.rotate"] .lane-grab')
    tall = t.evaluate("""() => {
      const g = document.querySelector('[data-mod-dest="view.rotate"] .lane-grab');
      return g ? g.getBoundingClientRect().height : 0;
    }""")
    check("the lane is a thumb-sized target", tall >= 16, "%.0f px" % tall)
    lane.tap(); t.wait_for_timeout(300)
    check("tapping it patches the armed source",
          [r for r in t.evaluate(ROUTES) if "view.rotate" in r] != [], str(t.evaluate(ROUTES)))
    check("and the source stays in hand", t.evaluate("() => armedSource") == "env.live")

    box = t.evaluate("""() => {
      const b = document.querySelector('[data-mod-dest="view.rotate"] .mod-drop');
      if (!b) return null;
      const r = b.getBoundingClientRect();
      return { w: r.width, h: r.height };
    }""")
    check("the way off it is a real target too", box and box["w"] >= 12 and box["h"] >= 12,
          str(box))
    t.locator('[data-mod-dest="view.rotate"] .mod-drop').tap(); t.wait_for_timeout(250)
    check("tapping that takes the patch off",
          [r for r in t.evaluate(ROUTES) if "view.rotate" in r] == [], str(t.evaluate(ROUTES)))

    t.locator('.mod-chip[data-source="env.live"]').tap(); t.wait_for_timeout(250)
    check("tapping the chip again puts it down", t.evaluate("() => armedSource") is None)
    check("no sideways overflow while patched",
          t.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"))
    t.screenshot(path=f"{SHOTS}/bench-touch.png", full_page=True)
    check("no page errors on touch", not tbad, "; ".join(tbad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all patching checks pass")
