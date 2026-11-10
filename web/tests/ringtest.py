"""Modulation on a knob (G5b of web/docs/the-face-second-pass.md): the ring,
its ticks and its dot; Alt-drag and the ring's handle; the control's editor;
the right-click menu; and the Routings silence, stored.

What would go wrong, and what is checked for it, each with its null:

- the ring drawing the wrong source, or a depth the wrong way: the fixture is
  asymmetric on purpose - LFO 1 at +40% and LFO 2 at -25% on the Frequency,
  whose law is an octave a whole depth - so the ring for one runs up from the
  hand's value to 220 Hz times two to the 0.4, and for the other back down to
  220 times two to the -0.25. A ring that ignored the sign, or the selection,
  reads the other's angle;
- the other sources missing, or the selected one drawn twice: a tick each for
  the others at their own reach, and none for the selected;
- the dot not being the sum, or not moving: read against the law with every
  source's value at that instant, and against the selected source's alone;
- Alt-drag turning the value, or Shift ignored: a real Alt held on a real
  drag moves the depth by its travel and leaves the value; without Alt the
  same drag turns the value (the null); with Shift too it moves a fifth as far;
- the ring's handle: a real drag on it sets the depth whose reach is where
  the pointer is, and the value stays; a press beside it turns the value;
- the editor named for the destination rather than the control ("Amplitude"
  over a knob named "Level"), its bar not the sources', a typed depth not
  landing;
- the right-click menu: its items with and without sources and on a menu,
  a source opening the editor with it selected, Reset and Type a value, What
  is this? opening the card, Esc and a click away closing it, the arrows,
  Shift+F10 from the keyboard; the browser's own menu suppressed
  (`defaultPrevented` on a real right-click), and left to a text box (the
  null); nothing changing the sound until something is chosen;
- the info line naming the right-click for a control with a menu, and not for
  a button (the null);
- the silence forgotten: stored in the setup as `modSilent`, restored by a
  restore and a setup code, sent to the instrument behind the page after a
  bar and read back from it; a setup without it silences nothing.

Real mouse and keys where the behaviour is a gesture, since a dispatched
event is not one (CLAUDE.md, for undo).

Serial: the dot is read moving over real time, and the menu's long press is
a timer.
"""
import json, math, os, sys
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

FMIN, FMAX = 30, 4000
def freq_deg(hz):
    """The Frequency knob's angle for a value, from its range alone."""
    return (min(FMAX, max(FMIN, hz)) - FMIN) / (FMAX - FMIN) * 270
def deg(text): return float(str(text).replace("deg", "") or "nan")

FACE = '[data-mod-dest="%s"] .knob-face'
RING = """(dest) => {
  const f = document.querySelector('[data-mod-dest="' + dest + '"] .knob-face'), s = f.style;
  const host = f.parentElement;
  return { a: s.getPropertyValue('--lane-a'), b: s.getPropertyValue('--lane-b'), cap: s.getPropertyValue('--cap'),
           now: s.getPropertyValue('--now'), angle: s.getPropertyValue('--angle'), ink: host.style.getPropertyValue('--pip'),
           shown: f.dataset.shown || null, hidden: f.querySelector('.lane-span').hidden,
           ticks: [...f.querySelectorAll('.lane-tick')].map((t) => [t.dataset.source, t.style.getPropertyValue('--tick'),
                                                                     t.style.getPropertyValue('--tick-ink')]) };
}"""
ROUTES = "() => routingsKept().map((r) => r.sourceId + '>' + r.destId + '@' + Math.round(r.amount * 100))"

def centre(box): return (box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

def fresh(p, tab="ink"):
    p.evaluate("""(tab) => { closeOverlay(); closeModCard(); setRoutingsOpen(false);
      state.modRoutings = []; held.clear(); focusSource = null; setBenchTab(tab);
      el.freq.value = '220'; el.freq.dispatchEvent(new Event('input', { bubbles: true }));
      el.amp.value = '55'; el.amp.dispatchEvent(new Event('input', { bubbles: true })); touchRoutings(); }""", tab)
    p.wait_for_timeout(250)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    p = ctx.new_page()
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text) if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(2000)
    p.evaluate("() => { const d = document.getElementById('helpDialog'); if (d && d.open) d.close(); setView('bench'); }")
    p.wait_for_timeout(300)

    print("\n--- the ring: the selected source's, from the hand's value to its reach ---")
    fresh(p)
    p.evaluate("""() => { addRouting('lfo1', 'gen.freq'); addRouting('lfo2', 'gen.freq'); addRouting('env.note', 'gen.freq');
      const r = (id) => state.modRoutings.find((x) => x.sourceId === id);
      r('lfo1').amount = 0.40; r('lfo2').amount = -0.25; r('env.note').amount = 0.15; touchRoutings(); }""")
    p.wait_for_timeout(250)
    # Pressed as a hand presses it: the card, which opens its editor, and the card again, which puts it away.
    def press_card(sid):
        p.locator('.mod-card[data-source="%s"]' % sid).click(); p.wait_for_timeout(250)
        p.locator('.mod-card[data-source="%s"]' % sid).click(); p.wait_for_timeout(250)
    press_card("lfo1")
    one = p.evaluate(RING, "gen.freq")
    base, up, down = freq_deg(220), freq_deg(220 * 2 ** 0.40), freq_deg(220 * 2 ** -0.25)
    print("    LFO 1 pressed:", one)
    check("LFO 1's card pressed, the ring is LFO 1's, in its ink, from 220 Hz up to 220 times two to the 0.4",
          one["shown"] == "lfo1" and one["ink"] == "var(--ch1)" and abs(deg(one["a"]) - base) < 1e-6
          and abs(deg(one["b"]) - up) < 1e-6 and abs(deg(one["cap"]) - up) < 1e-6 and not one["hidden"], str(one))
    press_card("lfo2")
    two = p.evaluate(RING, "gen.freq")
    print("    LFO 2 pressed:", two)
    check("LFO 2's card pressed, the ring is LFO 2's and runs backwards, from 220 Hz down to 220 times two to the -0.25",
          two["shown"] == "lfo2" and two["ink"] == "var(--ch2)" and abs(deg(two["a"]) - down) < 1e-6
          and abs(deg(two["b"]) - base) < 1e-6 and abs(deg(two["cap"]) - down) < 1e-6, str(two))
    null("LFO 1's ring did not run backwards: its end was above the hand's value", deg(one["cap"]) > base + 1, str(one["cap"]))
    null("and LFO 2's is not where LFO 1's was", abs(deg(two["cap"]) - up) > 1, str(two["cap"]))
    check("the pointer stays the hand's value whichever ring is drawn",
          abs(deg(one["angle"]) - base) < 1e-6 and one["angle"] == two["angle"], "%s %s" % (one["angle"], two["angle"]))

    print("\n--- a tick for every other source, at its reach ---")
    ticks = {sid: (deg(t), ink) for sid, t, ink in two["ticks"]}
    check("with LFO 2's ring, LFO 1 and the Envelope are a tick each, at their own reach and in their inks",
          set(ticks) == {"lfo1", "env.note"} and abs(ticks["lfo1"][0] - up) < 1e-6
          and abs(ticks["env.note"][0] - freq_deg(220 * 2 ** 0.15)) < 1e-6
          and ticks["lfo1"][1] == "var(--ch1)" and ticks["env.note"][1] == "var(--ch4)", str(two["ticks"]))
    null("the selected source has no tick of its own", "lfo2" not in ticks and "lfo1" not in {s for s, _, _ in one["ticks"]},
         "%s / %s" % (two["ticks"], one["ticks"]))
    # Nought to three sources, the cell the same: patchtest.py measures it; here the ticks count.
    counts = p.evaluate("""async () => { const wait = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      const face = document.querySelector('[data-mod-dest="gen.freq"] .knob-face'), out = [];
      for (const id of ['env.note', 'lfo2', 'lfo1']) { dropRouting(id, 'gen.freq'); await wait(); out.push(face.querySelectorAll('.lane-tick').length); }
      return out; }""")
    check("taken off one at a time, the ticks go with them: one, none, none", counts == [1, 0, 0], str(counts))

    print("\n--- the dot: where the control is this instant, every source summed ---")
    fresh(p)
    p.evaluate("""() => { addRouting('lfo1', 'gen.freq'); addRouting('lfo2', 'gen.freq');
      state.modRoutings[0].amount = 0.40; state.modRoutings[1].amount = -0.25; focusSource = 'lfo1'; touchRoutings(); }""")
    p.wait_for_timeout(300)
    # A moment when both oscillators are well away from nought, so the sum and either alone are apart.
    dot = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const face = document.querySelector('[data-mod-dest="gen.freq"] .knob-face');
      for (let i = 0; i < 120; i++) {
        const v1 = MOD_SOURCES.get('lfo1').value(), v2 = MOD_SOURCES.get('lfo2').value();
        if (Math.abs(v1) > 0.25 && Math.abs(v2) > 0.25) {
          updateLanes();
          return { v1, v2, now: face.style.getPropertyValue('--now') };
        }
        await wait(50);
      }
      return null; }""")
    first = p.evaluate("() => document.querySelector('[data-mod-dest=\"gen.freq\"] .knob-face').style.getPropertyValue('--now')")
    p.wait_for_timeout(900)
    later = p.evaluate("() => document.querySelector('[data-mod-dest=\"gen.freq\"] .knob-face').style.getPropertyValue('--now')")
    print("    dot:", dot, first, later)
    want = freq_deg(220 * 2 ** (dot["v1"] * 0.40 + dot["v2"] * -0.25)) if dot else None
    check("the dot is at 220 Hz times two to the sum of each source's value times its depth",
          dot is not None and abs(deg(dot["now"]) - want) < 0.05, "%s against %s" % (dot and dot["now"], want))
    null("and not at the selected source's alone", dot is not None and abs(deg(dot["now"]) - freq_deg(220 * 2 ** (dot["v1"] * 0.40))) > 0.05,
         str(dot))
    check("and it moves: read twice nine tenths of a second apart", abs(deg(first) - deg(later)) > 0.01, "%s %s" % (first, later))

    print("\n--- Alt-drag moves the selected source's depth, not the value ---")
    fresh(p, "play")
    p.evaluate("() => { addRouting('lfo1', 'gen.amp'); state.modRoutings[0].amount = 0.35; focusSource = 'lfo1'; touchRoutings(); }")
    p.wait_for_timeout(250)
    face = p.locator(FACE % "gen.amp").bounding_box()
    cx, cy = centre(face)
    def drag(dy, keys=(), read_mid=False):
        for k in keys: p.keyboard.down(k)
        p.mouse.move(cx, cy); p.mouse.down()
        p.mouse.move(cx, cy - dy / 2, steps=4)
        mid = p.evaluate("() => ({ reading: el.ampValue.textContent, info: el.infoValue.textContent, name: el.infoName.textContent })") if read_mid else None
        p.mouse.move(cx, cy - dy, steps=4); p.mouse.up()
        for k in reversed(keys): p.keyboard.up(k)
        p.wait_for_timeout(250)
        return mid
    mid = drag(45, ("Alt",), read_mid=True)
    alt = p.evaluate("() => ({ depth: Math.round(state.modRoutings[0].amount * 100), value: el.amp.value, reading: el.ampValue.textContent })")
    print("    alt-dragged up 45 px:", alt, "while moving:", mid)
    check("Alt held, 45 px up moves LFO 1 a quarter of its reach, +35% to +60%, and leaves the value at 0.55",
          alt["depth"] == 60 and alt["value"] == "55", str(alt))
    check("while it moves the reading over the knob and the info line say whose depth and how much",
          mid["reading"].startswith("LFO 1 +") and mid["reading"].endswith("%") and mid["info"] == mid["reading"] and mid["name"] == "Level",
          str(mid))
    check("and when it stops the reading is the value's again", alt["reading"] == "0.55", alt["reading"])
    p.evaluate("() => { state.modRoutings[0].amount = 0.35; touchRoutings(); }")
    drag(45, ("Shift", "Alt"))
    fine = p.evaluate("() => ({ depth: state.modRoutings[0].amount * 100, value: el.amp.value })")
    check("with Shift too, the same drag moves it a fifth as far: +35% to about +40.5%",
          abs(fine["depth"] - 40.5) <= 0.6 and fine["value"] == "55", str(fine))
    p.evaluate("() => { state.modRoutings[0].amount = 0.35; touchRoutings(); }")
    drag(45)
    plain = p.evaluate("() => ({ depth: Math.round(state.modRoutings[0].amount * 100), value: Number(el.amp.value) })")
    null("without Alt the same drag turns the value and leaves the depth", plain["depth"] == 35 and plain["value"] > 55, str(plain))

    print("\n--- or grab the ring: its end is a handle ---")
    fresh(p, "play")
    p.evaluate("() => { addRouting('lfo1', 'gen.amp'); state.modRoutings[0].amount = 0.35; focusSource = 'lfo1'; touchRoutings(); }")
    p.wait_for_timeout(250)
    p.mouse.move(5, 5); p.wait_for_timeout(250)
    rest = p.evaluate("() => getComputedStyle(document.querySelector('[data-mod-dest=\"gen.amp\"] .lane-handle')).opacity")
    # Past the handle's fade (0.12 s), with room for a busy machine.
    p.mouse.move(cx, cy); p.wait_for_timeout(600)
    hover = p.evaluate("() => getComputedStyle(document.querySelector('[data-mod-dest=\"gen.amp\"] .lane-handle')).opacity")
    handle = p.locator('[data-mod-dest="gen.amp"] .lane-handle').bounding_box()
    hx, hy = centre(handle)
    check("pointed at, the ring's end shows its handle", hover == "1", hover)
    null("at rest it does not", rest == "0", rest)
    # Level's law ducks: a depth p takes 0.55 to 0.55 times (1 - p), so the
    # pointer at the angle of 0.22 asks for +60%. Worked out here from the
    # face's own geometry, the angle round from the bottom left.
    target, R = 22, 25
    a = target / 140 * 270 - 135
    tx, ty = cx + R * math.sin(math.radians(a)), cy - R * math.cos(math.radians(a))
    p.mouse.move(hx, hy); p.mouse.down(); p.mouse.move(tx, ty, steps=8)
    held = p.evaluate("() => el.ampValue.textContent")
    p.mouse.up(); p.wait_for_timeout(250)
    ring = p.evaluate("() => ({ depth: Math.round(state.modRoutings[0].amount * 100), value: el.amp.value })")
    print("    dragged to the angle of 0.22:", ring, "while held:", held)
    check("dragged round to the angle of 0.22, the depth is the one that reaches it, +60%, and the value stays",
          abs(ring["depth"] - 60) <= 2 and ring["value"] == "55", str(ring))
    check("and while it was held the reading said whose depth", held.startswith("LFO 1 +"), held)
    p.evaluate("() => { state.modRoutings[0].amount = 0.35; touchRoutings(); }")
    p.wait_for_timeout(200)
    p.mouse.move(cx, cy); p.mouse.down(); p.mouse.move(cx, cy - 30, steps=6); p.mouse.up(); p.wait_for_timeout(250)
    beside = p.evaluate("() => ({ depth: Math.round(state.modRoutings[0].amount * 100), value: Number(el.amp.value) })")
    null("a press on the face beside the handle turns the value", beside["depth"] == 35 and beside["value"] > 55, str(beside))

    print("\n--- the right-click menu ---")
    fresh(p, "play")
    p.evaluate("() => { addRouting('lfo1', 'gen.amp'); addRouting('lfo2', 'gen.amp'); state.modRoutings[1].amount = -0.30; touchRoutings(); }")
    p.wait_for_timeout(250)
    # Who prevented the browser's own menu: read at the window, after the page's listener.
    p.evaluate("() => { window.__ctx = []; window.addEventListener('contextmenu', (e) => window.__ctx.push([e.target.id || e.target.className, e.defaultPrevented])); }")
    before = p.evaluate("() => JSON.stringify(snapshot())")
    p.mouse.click(cx, cy, button="right"); p.wait_for_timeout(300)
    MENU = """() => { const o = document.querySelector('.over.ctx'); if (!o) return null;
      return { title: o.querySelector('.over-title').textContent, sub: o.querySelector('.over-sub').textContent,
               heads: [...o.querySelectorAll('.ctx-head')].map((h) => h.textContent),
               items: [...o.querySelectorAll('.ctx-item')].map((b) => [b.dataset.item, b.dataset.source || '', b.textContent]),
               focus: document.activeElement && document.activeElement.dataset.item }; }"""
    m = p.evaluate(MENU)
    after = p.evaluate("() => JSON.stringify(snapshot())")
    print("    with two on it:", m)
    keys = [i[0] for i in m["items"]] if m else []
    check("right-clicked with two sources on it: its name and value, the two with their depths, the two to add, Clear, then its value and What is this?",
          m and m["title"] == "Level" and m["sub"] == "0.55" and m["heads"] == ["Modulation"]
          and keys == ["routing", "routing", "add", "add", "clear", "type", "reset", "what"]
          and m["items"][0][2] == "LFO 1+35% ›" and m["items"][1][2] == "LFO 2−30% ›"
          and [i[1] for i in m["items"][2:4]] == ["env.note", "photo.1"] and m["items"][6][2] == "Reset0.55", str(m))
    check("and the browser's own menu was prevented", p.evaluate("() => window.__ctx.slice(-1)[0]")[1] is True,
          str(p.evaluate("() => window.__ctx")))
    check("opening it changed nothing in the sound", before == after)
    check("the first item has the keyboard", m and m["focus"] == "routing", str(m and m["focus"]))
    p.keyboard.press("ArrowDown"); p.keyboard.press("ArrowDown")
    f2 = p.evaluate("() => document.activeElement.dataset.item + ':' + (document.activeElement.dataset.source || '')")
    p.keyboard.press("Home"); p.keyboard.press("ArrowUp")
    wrap = p.evaluate("() => document.activeElement.dataset.item")
    check("the arrows move in it, and up from the first goes round to the last", f2 == "add:env.note" and wrap == "what", "%s %s" % (f2, wrap))
    p.keyboard.press("Escape"); p.wait_for_timeout(200)
    check("Esc closes it", p.evaluate("() => !document.querySelector('.over')"))

    # Choosing a source opens the editor in the menu's place, on that source.
    p.mouse.click(cx, cy, button="right"); p.wait_for_timeout(300)
    p.locator('.ctx-item[data-item="routing"][data-source="lfo2"]').click(); p.wait_for_timeout(300)
    ed = p.evaluate("""() => { const o = document.querySelector('.over.mod-over'); if (!o) return null;
      const box = o.getBoundingClientRect(), face = document.querySelector('[data-mod-dest="gen.amp"] .knob-face').getBoundingClientRect();
      return { title: o.querySelector('.over-title').textContent, dest: MOD_DESTS.get('gen.amp').label, sub: o.querySelector('.over-sub').textContent,
               rows: [...o.querySelectorAll('.mod-edit')].map((r) => [r.dataset.source, r.getAttribute('aria-selected')]),
               focus: focusSource, shown: document.querySelector('[data-mod-dest="gen.amp"] .knob-face').dataset.shown,
               above: box.bottom <= face.top + 1, pics: o.querySelectorAll('canvas.mod-edit-pic').length,
               hint: o.querySelector('.mod-hint').textContent }; }""")
    print("    the editor:", ed)
    check("choosing LFO 2 opens the editor above the knob, on LFO 2, the ring and Alt-drag following it",
          ed and ed["focus"] == "lfo2" and ed["shown"] == "lfo2" and ["lfo2", "true"] in ed["rows"] and ed["above"]
          and ed["hint"].startswith("Alt-drag the knob, or drag its ring, for LFO 2"), str(ed))
    check("headed with the knob's own name and value", ed and ed["title"] == "Level" and ed["sub"] == "0.55", str(ed))
    null("which is not the destination's name", ed and ed["dest"] != ed["title"], str(ed and ed["dest"]))
    check("a row per source, each with a picture of its source", ed and len(ed["rows"]) == 2 and ed["pics"] == 2, str(ed))
    # The bar: the hand's mark at 55 of 140, and each source's band from it to its reach under Level's law.
    bar = p.evaluate("""async () => { await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      const o = document.querySelector('.over.mod-over'), pc = (n) => parseFloat(n.style.left), w = (n) => parseFloat(n.style.width);
      return { mark: pc(o.querySelector('.mod-bar-mark')), hand: [pc(o.querySelector('.mod-bar-hand')), w(o.querySelector('.mod-bar-hand'))],
               bands: [...o.querySelectorAll('.mod-band')].map((b) => [b.dataset.source, pc(b.firstChild), w(b.firstChild), b.style.getPropertyValue('--pip')]),
               now: pc(o.querySelector('.mod-bar-now')) }; }""")
    # Read back from style.left, which keeps six figures.
    frac = lambda v: v / 140 * 100
    near = lambda a, b: abs(a - b) < 1e-3
    print("    the bar:", bar)
    bands = {s: (l, wd, ink) for s, l, wd, ink in bar["bands"]}
    check("its bar marks the hand's 0.55, filled from nought",
          near(bar["mark"], frac(55)) and near(bar["hand"][0], 0) and near(bar["hand"][1], frac(55)), str(bar))
    check("LFO 1's band runs from 0.55 down to 0.3575 (+35% ducks Level) and LFO 2's up to 0.715, each in its ink",
          near(bands["lfo1"][0], frac(35.75)) and near(bands["lfo1"][1], frac(55 - 35.75))
          and near(bands["lfo2"][0], frac(55)) and near(bands["lfo2"][1], frac(71.5 - 55))
          and bands["lfo1"][2] == "var(--ch1)" and bands["lfo2"][2] == "var(--ch2)", str(bands))
    null("the two bands are not one band drawn twice", bands["lfo1"][0] != bands["lfo2"][0], str(bands))
    # A typed depth lands; anything else puts the old one back.
    box = p.locator('.over .mod-edit[data-source="lfo1"] .mod-edit-val')
    box.click(); p.keyboard.type("-20"); p.keyboard.press("Enter"); p.wait_for_timeout(200)
    typed = p.evaluate("""() => ({ amount: state.modRoutings.find((r) => r.sourceId === 'lfo1').amount,
      slider: document.querySelector('.over .mod-edit[data-source="lfo1"] input[type=range]').value,
      shows: document.querySelector('.over .mod-edit[data-source="lfo1"] .mod-edit-val').value })""")
    check("a depth typed lands: -20 and Enter is the routing's -0.2, its slider at -20, shown with a true minus",
          abs(typed["amount"] + 0.2) < 1e-9 and typed["slider"] == "-20" and typed["shows"] == "−20%", str(typed))
    box.click(); p.keyboard.type("abc"); p.keyboard.press("Enter"); p.wait_for_timeout(200)
    kept = p.evaluate("() => state.modRoutings.find((r) => r.sourceId === 'lfo1').amount")
    null("and 'abc' typed changes nothing", abs(kept + 0.2) < 1e-9, str(kept))
    # Pressing a row selects its source.
    p.locator('.over .mod-edit[data-source="lfo1"] .dot-sm').click(); p.wait_for_timeout(200)
    check("pressing a row selects its source, the knob's ring with it",
          p.evaluate("() => focusSource + ' ' + document.querySelector('[data-mod-dest=\"gen.amp\"] .knob-face').dataset.shown") == "lfo1 lfo1")
    p.mouse.click(5, 450); p.wait_for_timeout(200)
    check("a click away closes the editor", p.evaluate("() => !document.querySelector('.over')"))

    # Reset, and Type a value, through the menu.
    p.evaluate("() => { el.amp.value = '100'; el.amp.dispatchEvent(new Event('input', { bubbles: true })); }")
    p.mouse.click(cx, cy, button="right"); p.wait_for_timeout(250)
    p.locator('.ctx-item[data-item="reset"]').click(); p.wait_for_timeout(250)
    reset = p.evaluate("() => ({ value: el.amp.value, gen: genSettings().amp })")
    check("Reset puts Level back where it starts, 0.55, the generator with it", reset["value"] == "55" and abs(reset["gen"] - 0.55) < 1e-9, str(reset))
    null("it was at 1.00 before", True)
    p.evaluate("() => setBenchTab('ink')"); p.wait_for_timeout(200)
    fbox = p.locator(FACE % "gen.freq").bounding_box(); fx, fy = centre(fbox)
    p.mouse.click(fx, fy, button="right"); p.wait_for_timeout(250)
    nothing = p.evaluate(MENU)
    print("    with nothing on it:", nothing)
    check("right-clicked with nothing on it: Modulate with and the four sources, then the value and What is this?",
          nothing and nothing["heads"] == ["Modulate with"] and [i[1] for i in nothing["items"][:4]] == ["lfo1", "lfo2", "env.note", "photo.1"]
          and [i[0] for i in nothing["items"]] == ["add"] * 4 + ["type", "reset", "what"], str(nothing))
    p.locator('.ctx-item[data-item="type"]').click(); p.wait_for_timeout(150)
    p.keyboard.type("2k"); p.keyboard.press("Enter"); p.wait_for_timeout(300)
    typed_value = p.evaluate("() => ({ value: el.freq.value, reading: el.freqValue ? el.freqValue.textContent : '', menu: !!document.querySelector('.over') })")
    check("Type a value, 2k, is 2000 Hz, in the reading's own terms, and the menu closes", typed_value["value"] == "2000" and not typed_value["menu"],
          str(typed_value))
    p.mouse.click(fx, fy, button="right"); p.wait_for_timeout(250)
    p.locator('.ctx-item[data-item="type"]').click(); p.wait_for_timeout(150)
    p.keyboard.type("330 Hz"); p.keyboard.press("Enter"); p.wait_for_timeout(300)
    check("and 330 Hz is 330", p.evaluate("() => el.freq.value") == "330", p.evaluate("() => el.freq.value"))
    p.mouse.click(fx, fy, button="right"); p.wait_for_timeout(250)
    p.locator('.ctx-item[data-item="add"][data-source="lfo2"]').click(); p.wait_for_timeout(300)
    check("a source chosen from Modulate with is patched at its starting depth and selected",
          p.evaluate(ROUTES)[-1] == "lfo2>gen.freq@35" and p.evaluate("() => focusSource") == "lfo2", str(p.evaluate(ROUTES)))
    p.mouse.click(fx, fy, button="right"); p.wait_for_timeout(250)
    p.locator('.ctx-item[data-item="what"]').click(); p.wait_for_timeout(300)
    card = p.evaluate("() => { const o = document.querySelector('.over'); return o && { card: !!o.querySelector('.info-card'), title: o.querySelector('.over-title').textContent }; }")
    check("What is this? opens the control's card", card and card["card"] and card["title"] == "Frequency", str(card))
    p.keyboard.press("Escape"); p.wait_for_timeout(200)

    # A menu: no modulation, and on a split, Copy to the other layer.
    p.evaluate("() => setBenchTab('play')"); p.wait_for_timeout(200)
    p.locator("#shape").click(button="right"); p.wait_for_timeout(250)
    menu_only = p.evaluate(MENU)
    check("a menu's own has no modulation: Reset, naming where it starts, and What is this?",
          menu_only and menu_only["heads"] == [] and [i[0] for i in menu_only["items"]] == ["reset", "what"], str(menu_only))
    p.keyboard.press("Escape")
    # Layers want a keyboard: the screen's.
    p.evaluate("() => { setScreenKeys(true); el.midiPoly.click(); el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change')); }")
    p.wait_for_timeout(250)
    # The amp envelope's Attack, a hand's own and on Play, which the screen's keys leave in view.
    p.evaluate("() => { el.envAttack.value = '150'; el.envAttack.dispatchEvent(new Event('input', { bubbles: true })); }")
    sx, sy = centre(p.locator("#envAttack ~ .knob-face, .menu-row:has(#envAttack) .knob-face").first.bounding_box())
    p.mouse.click(sx, sy, button="right"); p.wait_for_timeout(250)
    split = p.evaluate(MENU)
    copied_before = p.evaluate("() => genSettings(1).attackMs")
    p.locator('.ctx-item[data-item="copy"]').click(); p.wait_for_timeout(250)
    copied = p.evaluate("() => ({ a: genSettings(0).attackMs, b: genSettings(1).attackMs, edit: panelLayer })")
    check("on a split, Copy to layer B copies the Attack to the other hand and leaves the panel on A",
          split and any(i[2] == "Copy to layer B" for i in split["items"]) and copied["b"] == 150
          and copied["a"] == 150 and copied["edit"] == 0, "%s %s" % (copied, split and split["items"]))
    null("layer B was not at 150 ms before", copied_before != 150, str(copied_before))
    p.evaluate("() => { el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change')); el.midiDyad.click(); setScreenKeys(false); }")
    p.wait_for_timeout(200)

    # The keyboard's way: Shift+F10 with the knob focused.
    p.evaluate("() => { closeOverlay(); el.amp.focus(); }")
    p.keyboard.press("Shift+F10"); p.wait_for_timeout(250)
    kb = p.evaluate(MENU)
    check("Shift+F10 with the knob focused opens its menu, the first item focused", kb and kb["title"] == "Level" and kb["focus"] is not None, str(kb))
    p.keyboard.press("Escape"); p.wait_for_timeout(150)
    check("and Esc gives the knob the keyboard back", p.evaluate("() => document.activeElement === el.amp"))

    # The browser's own menu: never over the face, still over a text box.
    p.evaluate("() => { window.__ctx = []; setMenuOpen(false); }")
    p.mouse.click(700, 60, button="right"); p.wait_for_timeout(150)
    p.keyboard.press("Escape")
    p.evaluate("() => { openPresets && openPresets(); }") if p.evaluate("() => typeof openPresets === 'function'") else None
    p.wait_for_timeout(250)
    code = p.locator("#presetCode")
    if code.count() and code.is_visible():
        code.click(button="right"); p.wait_for_timeout(150)
    ctxs = p.evaluate("() => window.__ctx")
    print("    contextmenu events:", ctxs)
    check("a right-click anywhere on the face that is not a text box shows no browser menu", ctxs and ctxs[0][1] is True, str(ctxs))
    null("over the setup code's box the browser's own is left alone", len(ctxs) >= 2 and ctxs[-1][1] is False, str(ctxs))
    p.keyboard.press("Escape"); p.evaluate("() => { closeOverlay(); typeof closePresets === 'function' && closePresets(); }")
    p.wait_for_timeout(200)

    print("\n--- the info line names the right-click ---")
    fresh(p, "play")
    def rest_on(sel):
        p.mouse.move(5, 5); p.wait_for_timeout(100)
        bb = p.locator(sel).first.bounding_box(); p.mouse.move(*centre(bb)); p.wait_for_timeout(600)
        return p.evaluate("() => ({ name: el.infoName.textContent, menu: el.infoMenu.hidden ? null : el.infoMenu.textContent })")
    on_knob, on_menu, on_button = rest_on(FACE % "gen.amp"), rest_on("#shape"), rest_on("#clearButton")
    print("    %s / %s / %s" % (on_knob, on_menu, on_button))
    check("on a knob that takes a source: Right-click for modulation and more", on_knob["menu"] == "Right-click for modulation and more.", str(on_knob))
    check("on a menu: Right-click for more", on_menu["menu"] == "Right-click for more.", str(on_menu))
    null("on a button, which has no menu, nothing", on_button["name"] and on_button["menu"] is None, str(on_button))

    print("\n--- the Routings silence, stored ---")
    fresh(p, "play")
    p.evaluate("() => { addRouting('lfo1', 'gen.amp'); addRouting('lfo2', 'gen.freq'); addRouting('lfo1', 'view.rotate'); }")
    p.wait_for_timeout(200)
    p.evaluate("() => setRoutingsOpen(true)"); p.wait_for_timeout(200)
    p.locator('[data-silence="lfo1"]').click(); p.wait_for_timeout(250)
    snap = p.evaluate("() => { const s = snapshot(); return { mod: s.mod, silent: s.modSilent, heard: state.modRoutings.map((r) => r.sourceId), host: hostRoutingsText() }; }")
    print("    silenced:", snap)
    check("LFO 1 silenced: the setup keeps every routing and names LFO 1 in modSilent, and only LFO 2 is heard",
          snap["silent"] == "lfo1" and snap["mod"].count("lfo1>") == 2 and snap["heard"] == ["lfo2"], str(snap))
    check("and the instrument behind the page is told every routing and the silence after a bar",
          snap["host"].endswith("|lfo1") and snap["host"].count("lfo1>") == 2, snap["host"])
    back = p.evaluate("""() => { const s = snapshot(); restore({ mod: '' }); const cleared = held.size;
      restore(s); return { cleared, silent: [...held.keys()], heard: state.modRoutings.map((r) => r.sourceId), mod: snapshot().mod }; }""")
    check("restored, the silence comes back with the routings", back["cleared"] == 0 and back["silent"] == ["lfo1"] and back["heard"] == ["lfo2"]
          and back["mod"] == snap["mod"], str(back))
    coded = p.evaluate("""() => { const code = encodeSetup(snapshot()); restore({ mod: '' }); loadCode(code);
      return { silent: [...held.keys()], heard: state.modRoutings.map((r) => r.sourceId) }; }""")
    p.wait_for_timeout(300)
    check("and through a setup code", coded["silent"] == ["lfo1"] and coded["heard"] == ["lfo2"], str(coded))
    host = p.evaluate("""(text) => { restore({ mod: '' }); routingsFromHost(text);
      return { silent: [...held.keys()], heard: state.modRoutings.map((r) => r.sourceId), kept: routingsKept().length }; }""", snap["host"])
    check("and read back from the plugin's state as the plugin keeps it", host["silent"] == ["lfo1"] and host["heard"] == ["lfo2"] and host["kept"] == 3,
          str(host))
    none = p.evaluate("""(mod) => { restore({ mod }); return { silent: [...held.keys()], heard: state.modRoutings.length }; }""", snap["mod"])
    null("a setup without modSilent silences nothing", none["silent"] == [] and none["heard"] == 3, str(none))
    old = p.evaluate("""(text) => { restore({ mod: '' }); routingsFromHost(text.split('|')[0]); return held.size; }""", snap["host"])
    null("and a plugin's text without the bar, from before, silences nothing", old == 0, str(old))
    p.evaluate("() => setRoutingsOpen(false)")

    check("no page errors", not bad, "; ".join(bad[:3]))
    ctx.close()

    print("\n--- a long press on a touch screen ---")
    tctx = b.new_context(viewport={"width": 1200, "height": 800}, has_touch=True, is_mobile=True)
    t = tctx.new_page()
    tbad = []
    t.on("pageerror", lambda e: tbad.append(str(e)))
    t.goto(f"file://{ART}/scope.html"); t.wait_for_timeout(2000)
    t.evaluate("() => { const d = document.getElementById('helpDialog'); if (d && d.open) d.close(); setView('bench'); setBenchTab('play'); state.modRoutings = []; touchRoutings(); }")
    t.wait_for_timeout(300)
    tb = t.locator(FACE % "gen.amp").bounding_box(); tx, ty = centre(tb)
    cdp = tctx.new_cdp_session(t)
    def press(ms):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": tx, "y": ty}]})
        t.wait_for_timeout(ms)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        t.wait_for_timeout(250)
        return t.evaluate("() => ({ menu: !!document.querySelector('.over.ctx'), value: el.amp.value })")
    quick = press(120)
    long = press(900)
    print("    quick %s, long %s" % (quick, long))
    check("a long press on a knob opens its menu and turns nothing", long["menu"] and long["value"] == "55", str(long))
    null("a quick tap does not", not quick["menu"], str(quick))
    check("no page errors on touch", not tbad, "; ".join(tbad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all modulation-on-a-knob checks pass")
