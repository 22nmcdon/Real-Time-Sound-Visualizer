"""Putting a source on a control.

Third design of this surface. The first was a split thumb, which could state
one attachment and not two; the second was a lane you dragged, which could
state any number and was horrible to aim. Both made a drag the only way in, and
both were hard to use for the same reason: the target was a few pixels tall and
nothing said it was there until you had already picked something up.

So: a button on every control that can take a patch, present whether or not
anything is on it, opening a panel of ordinary sliders. One gesture, the same
on a pointer, a keyboard and a thumb. What is asserted here is mostly that -
that the way in is always visible, that the panel is made of real controls, and
that using it never changes the shape of the page underneath.
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


def open_bench(page):
    page.goto(f"file://{ART}/scope.html"); page.wait_for_timeout(700)
    if page.locator("#helpClose").is_visible(): page.locator("#helpClose").click()
    page.wait_for_timeout(150)
    page.evaluate("""() => {
      setView('bench'); state.modRoutings = []; focusSource = null; paintRoutings();
    }""")
    page.wait_for_timeout(350)


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    p = b.new_page(viewport={"width": 1440, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    open_bench(p)

    print("\n--- the way in is always there ---")
    # The complaint about both earlier designs: nothing on an unpatched control
    # said it could take a patch. Every one of them carries the button now,
    # empty or not, and it is in the same place at the same size either way.
    ways = p.evaluate("""() => {
      const rows = Array.from(document.querySelectorAll('[data-mod-dest]'));
      const missing = rows.filter((r) => !r.querySelector('.mod-open')).length;
      const shown = rows.filter((r) => {
        const b = r.querySelector('.mod-open');
        return b && b.offsetWidth > 0;
      }).length;
      return { rows: rows.length, missing,
               shown,                       // the ones whose section is on screen
               rings: document.querySelectorAll('.mod-open .ring').length };
    }""")
    check("every destination has a way in", ways["missing"] == 0, str(ways))
    check("and an empty one still shows a ring", ways["rings"] >= 6, str(ways))

    print("\n--- the editor is made of ordinary controls ---")
    p.locator('[data-mod-dest="gen.freq"] .mod-open').click(); p.wait_for_timeout(300)
    opened = p.evaluate("""() => {
      const over = document.querySelector('.over');
      if (!over) return null;
      return { title: over.querySelector('.over-title').textContent,
               sub: over.querySelector('.over-sub').textContent,
               rows: over.querySelectorAll('.mod-edit').length,
               add: Array.from(over.querySelectorAll('.mod-add-one'))
                 .map((n) => n.textContent.trim()) };
    }""")
    check("pressing the dots opens it on that parameter",
          opened and opened["title"] == "Frequency", str(opened))
    check("it says what the control is at", opened["sub"] == "220 Hz", str(opened))
    # Counted from the registry rather than pinned at three. It was three, and
    # then the note envelope became a source and three tests in this file said
    # the page was broken. What the panel promises is "every source you have",
    # not "three".
    every = p.evaluate("() => MOD_SOURCES.size")
    check("nothing on it yet, so every source is offered",
          len(opened["add"]) == every, "%d offered of %d registered"
          % (len(opened["add"]), every))

    p.locator('.mod-add-one[data-add="lfo1"]').click(); p.wait_for_timeout(300)
    check("adding one patches it", p.evaluate(ROUTES) == ["lfo1>gen.freq@0.35"],
          str(p.evaluate(ROUTES)))
    row = p.evaluate("""() => {
      const line = document.querySelector('.mod-edit');
      const slider = line.querySelector('input[type=range]');
      return { name: line.querySelector('.mod-edit-name').textContent,
               kind: slider.type, value: slider.value,
               reads: line.querySelector('.mod-edit-val').textContent,
               offered: document.querySelectorAll('.mod-add-one').length };
    }""")
    check("and it becomes a row with a real slider in it",
          row["kind"] == "range" and row["value"] == "35", str(row))
    check("named, read out, and no longer in the offer list",
          row["name"] == "LFO 1" and row["reads"] == "+35%"
          and row["offered"] == every - 1,
          "%s, %d offered of %d" % (row["name"], row["offered"], every))

    print("\n--- the slider is the depth ---")
    p.locator(".mod-edit input[type=range]").fill("-80")
    p.wait_for_timeout(250)
    check("dragging it sets the routing",
          abs(p.evaluate("() => state.modRoutings[0].amount") + 0.8) < 1e-6,
          str(p.evaluate("() => state.modRoutings[0].amount")))
    check("and the readout follows",
          p.evaluate("() => document.querySelector('.mod-edit-val').textContent") == "-80%")
    # A keyboard gets this for nothing, which neither earlier design managed.
    p.locator(".mod-edit input[type=range]").focus()
    p.keyboard.press("ArrowRight"); p.wait_for_timeout(200)
    check("arrows work on it because it is a real input",
          abs(p.evaluate("() => state.modRoutings[0].amount") + 0.79) < 1e-6,
          str(p.evaluate("() => state.modRoutings[0].amount")))

    print("\n--- several sources, same panel ---")
    p.locator('.mod-add-one[data-add="lfo2"]').click(); p.wait_for_timeout(250)
    p.locator('.mod-add-one[data-add="env.live"]').click(); p.wait_for_timeout(250)
    # Whatever else is registered, so "nothing left to offer" stays a
    # statement about the panel rather than about how many sources exist.
    while p.locator(".mod-add-one").count() > 0:
        p.locator(".mod-add-one").first.click(); p.wait_for_timeout(200)
    many = p.evaluate("""() => ({
      rows: document.querySelectorAll('.mod-edit').length,
      add: document.querySelectorAll('.mod-add-one').length,
      routings: state.modRoutings.length,
    })""")
    check("every source is a row of its own",
          many["rows"] == every and many["routings"] == every,
          "%d rows, %d routings, %d sources" % (many["rows"], many["routings"], every))
    check("with nothing left to offer", many["add"] == 0, str(many))

    before = p.evaluate(ROUTES)
    p.locator(".mod-edit .mod-edit-off").first.click(); p.wait_for_timeout(250)
    after = p.evaluate(ROUTES)
    # One fewer, and the one whose cross was pressed - rather than a count,
    # which said two and meant "the three that were here when this was
    # written".
    check("and the cross on a row removes that one",
          len(after) == len(before) - 1 and before[0] not in after
          and all(r in after for r in before[1:]),
          "%s became %s" % (before, after))

    print("\n--- and the page underneath does not move ---")
    # The property both earlier designs lost. Measured across the whole range,
    # waiting for the repaint each time, because reading in the same tick
    # passes whatever the design does.
    p.keyboard.press("Escape"); p.wait_for_timeout(250)
    shape = p.evaluate("""async () => {
      const row = document.querySelector('[data-mod-dest="gen.freq"]');
      const input = document.getElementById('freq');
      const settle = () => new Promise((done) => requestAnimationFrame(
        () => requestAnimationFrame(done)));
      const snap = () => ({ h: row.offsetHeight,
                            x: Math.round(input.getBoundingClientRect().x),
                            w: Math.round(input.getBoundingClientRect().width) });

      state.modRoutings = []; paintRoutings(); await settle();
      const none = snap();
      addRouting('lfo1', 'gen.freq');     await settle();  const one = snap();
      addRouting('lfo2', 'gen.freq');     await settle();  const two = snap();
      addRouting('env.live', 'gen.freq'); await settle();  const three = snap();
      return { none, one, two, three,
               pips: row.querySelectorAll('.mod-open .pip').length };
    }"""); p.wait_for_timeout(200)
    same = (shape["none"] == shape["one"] == shape["two"] == shape["three"])
    check("nought, one, two and three sources measure the same", same,
          "%s / %s / %s / %s" % (shape["none"], shape["one"], shape["two"], shape["three"]))
    check("and the button counts them", shape["pips"] == 3, str(shape["pips"]))

    print("\n--- dragging a chip is the quick way ---")
    p.evaluate("() => { state.modRoutings = []; paintRoutings(); }"); p.wait_for_timeout(250)
    chip = p.locator('.mod-chip[data-source="lfo1"]')
    target = p.locator('[data-mod-dest="view.rotate"]')
    cb, tb = chip.bounding_box(), target.bounding_box()
    p.mouse.move(cb["x"] + cb["width"] / 2, cb["y"] + cb["height"] / 2)
    p.mouse.down()
    p.mouse.move(tb["x"] + 40, tb["y"] + tb["height"] / 2, steps=12)
    highlighted = p.evaluate("() => document.querySelectorAll('.mod-target').length")
    p.mouse.up(); p.wait_for_timeout(300)
    check("the control lights up under the chip", highlighted == 1, str(highlighted))
    check("and the drop makes a routing", p.evaluate(ROUTES) == ["lfo1>view.rotate@0.35"],
          str(p.evaluate(ROUTES)))

    print("\n--- a section's detail is moved, not copied ---")
    # Counted before it opens rather than written down here. What this is about
    # is that ALL of a section's secondary content moves and none of it stays
    # behind - not that the filter has two paragraphs, which is a fact about
    # today's prose and changed the first time a paragraph was added.
    had = p.evaluate("""() => ({
      notes: document.querySelectorAll('.menu-group:has(#filterCutoff) .menu-note').length,
      rows: document.querySelectorAll('.menu-group:has(#filterCutoff) [data-more]').length,
    })""")
    p.locator('.menu-group:has(#filterCutoff) .more-dots').click(); p.wait_for_timeout(300)
    detail = p.evaluate("""() => ({
      title: document.querySelector('.over-title').textContent,
      notes: document.querySelectorAll('.over-body .menu-note').length,
      rows: document.querySelectorAll('.over-body [data-more]').length,
      stayed: document.querySelectorAll(
        '.menu-group:has(#filterCutoff) .menu-note, .menu-group:has(#filterCutoff) [data-more]'
      ).length,
      leftBehind: document.querySelectorAll('#benchBody .menu-note').length,
      dupes: (() => { const seen = new Set(), d = [];
        for (const n of document.querySelectorAll('[id]')) {
          if (seen.has(n.id)) d.push(n.id); else seen.add(n.id); }
        return d; })(),
    })""")
    check("the dots open the section's own detail", detail["title"] == "Filter", str(detail))
    check("with all of its prose and its secondary rows, and none left behind",
          detail["notes"] == had["notes"] and detail["rows"] == had["rows"]
          and detail["stayed"] == 0 and had["notes"] > 0,
          "%d notes and %d rows, %d stayed" % (detail["notes"], detail["rows"],
                                               detail["stayed"]))
    check("moved rather than copied, so no id is answered twice",
          detail["dupes"] == [], str(detail["dupes"]))

    p.keyboard.press("Escape"); p.wait_for_timeout(300)
    home = p.evaluate("""() => ({
      notes: document.querySelectorAll('.menu-group:has(#filterCutoff) .menu-note').length,
      more: document.querySelectorAll('.menu-group:has(#filterCutoff) [data-more]').length,
      over: document.querySelectorAll('.over').length,
      switchWorks: (() => { el.seeDry.click(); const a = state.analyseAt;
                            el.seeWet.click(); return a === 'pre' && state.analyseAt === 'post'; })(),
    })""")
    check("Escape puts it away", home["over"] == 0)
    check("and everything goes home",
          home["notes"] == had["notes"] and home["more"] == had["rows"], str(home))
    check("still wired to what it drives", home["switchWorks"], str(home))

    print("\n--- neither panel scrolls ---")
    # The thing this redesign is for. Checked in the modes that add the most
    # rows, since those are where it would first give way.
    modes = p.evaluate("""async () => {
      const settle = () => new Promise((d) => setTimeout(d, 260));
      const fits = () => {
        const body = el.benchBody, side = el.benchSide;
        return { body: body.scrollHeight - body.clientHeight,
                 side: side.scrollHeight - side.clientHeight };
      };
      const out = {};
      for (const kind of ['wave', 'harmonograph', 'figure', 'wireframe']) {
        el.genMode.value = kind;
        el.genMode.dispatchEvent(new Event('change'));
        await settle();
        out[kind] = fits();
      }
      el.filterOn.checked = true; el.filterOn.dispatchEvent(new Event('change'));
      el.lagOn.checked = true; el.lagOn.dispatchEvent(new Event('change'));
      await settle();
      out['filter+lag'] = fits();
      // Poly adds its Draw row, and the switch that chooses it is three words
      // wide - which is what first made this panel scroll, by twelve pixels.
      // On the waveform, which is the only kind a chord plays on and so the
      // only one that shows the Draw row.
      el.genMode.value = 'wave';
      el.genMode.dispatchEvent(new Event('change'));
      el.midiPoly.click();
      await settle();
      out['poly+filter+lag'] = fits();
      // Two more rows with a split on - the Layers menu and the Edit switch -
      // and a keyboard present, which the layers need and which takes the
      // bottom of the page. Then with layer B on the panel, whose note is the
      // one row B adds to the generator section.
      setScreenKeys(true);
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      await settle();
      out['poly+split+keys'] = fits();
      el.midiEditB.click();
      await settle();
      out['poly+split, editing B'] = fits();
      el.midiEditA.click();
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change'));
      setScreenKeys(false);
      el.midiDyad.click();
      return out;
    }""")
    for mode, over in modes.items():
        check("%s fits without scrolling" % mode,
              over["body"] <= 0 and over["side"] <= 0,
              "body over by %d, side by %d" % (over["body"], over["side"]))

    # Width, which the check above cannot see: a row wider than its column
    # does not scroll anything, it runs over the next column. The Draw row's
    # two menus did, by 89 px over the Trigger heading, from poly onwards.
    # Measured in the keyboard section, whose rows are the ones that grow.
    wide = p.evaluate("""async () => {
      const settle = () => new Promise((d) => setTimeout(d, 260));
      const over = () => {
        const group = el.midiGroup.getBoundingClientRect();
        return Array.from(el.midiGroup.querySelectorAll('input, select, button'))
          .filter((c) => c.getBoundingClientRect().width > 0)
          .map((c) => [c.id || c.className, Math.round(c.getBoundingClientRect().right - group.right)])
          .filter(([, by]) => by > 1);
      };
      const out = {};
      setScreenKeys(true);
      el.midiPoly.click(); await settle();
      out.poly = over();
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change')); await settle();
      out.split = over();
      el.midiSplitLearn.click(); await settle();
      out.learning = over();
      el.midiSplitLearn.click();
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change'));
      setScreenKeys(false);
      el.midiDyad.click();
      return out;
    }""")
    for mode, over in wide.items():
        check("the keyboard section's controls stay inside its column (%s)" % mode, not over, str(over))

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

    size = t.evaluate("""() => {
      const b = document.querySelector('[data-mod-dest="gen.freq"] .mod-open');
      const r = b.getBoundingClientRect();
      return { w: r.width, h: r.height };
    }""")
    check("the way in is a thumb-sized target", size["h"] >= 18, str(size))

    t.locator('[data-mod-dest="gen.freq"] .mod-open').tap(); t.wait_for_timeout(350)
    check("tapping it opens the editor",
          t.evaluate("() => !!document.querySelector('.over')"))
    t.locator('.mod-add-one[data-add="lfo1"]').tap(); t.wait_for_timeout(300)
    check("and a source can be added with one tap",
          t.evaluate(ROUTES) == ["lfo1>gen.freq@0.35"], str(t.evaluate(ROUTES)))
    t.locator(".mod-edit-off").tap(); t.wait_for_timeout(300)
    check("and taken off with another", t.evaluate(ROUTES) == [], str(t.evaluate(ROUTES)))

    t.locator(".over-close").tap(); t.wait_for_timeout(250)
    check("the close button puts it away",
          t.evaluate("() => document.querySelectorAll('.over').length") == 0)
    check("no sideways overflow",
          t.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"))
    t.screenshot(path=f"{SHOTS}/bench-touch.png", full_page=True)
    check("no page errors on touch", not tbad, "; ".join(tbad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all patching checks pass")
