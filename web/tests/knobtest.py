"""The Bench's knobs: a face over the range input that still holds the value.

P8c turned the Bench's sliders into knobs, ported from the owner's Headroom.
The design's whole bet is that the range input stays the value - so every
listener, preset, test and host knob that writes `input.value` goes on
working - and the face only follows it. So what this holds is the face and
the input staying one control, each direction:

- which rows became knobs, and that the ones kept as sliders are exactly the
  ones meant to be (the drawbars; the setup morph was too, until F3 took it to the Perform menu, and the macros, until P8d cut them);
- the face points where the value says, at both ends, the middle, and from
  nought for a control either side of it - and follows a value written from
  code with no event, which is how a preset or a host move arrives;
- a drag writes the value and fires input, up is more, shift is fine, and the
  end of a drag is one change; two taps put it back; the arrow keys still
  move it;
- a finger on a knob turns it and does not scroll the page;
- the picture stage still lights the name, and a modulation's lane is a ring
  on the face.

Each check is first seen to fail: against the value before the gesture, the
other branch's number, or a row the dressing has not reached.
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
def null(name, ok, detail=""):
    check("null: " + name, ok, detail)

FACE = """(id) => { const i = document.getElementById(id); const f = i.parentElement.querySelector('.knob-face');
  const s = f.style; return { v: i.value, angle: s.getPropertyValue('--angle'), lo: s.getPropertyValue('--lo'),
  hi: s.getPropertyValue('--hi') }; }"""

def deg(text):
    return float(text.replace("deg", "")) if text else float("nan")

def centre(p, id):
    box = p.evaluate("""(id) => { const r = document.getElementById(id).parentElement
      .querySelector('.knob-face').getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; }""", id)
    return box["x"], box["y"]

def setv(p, id, v):
    p.evaluate("([id, v]) => { const i = document.getElementById(id); i.value = v; i.dispatchEvent(new Event('input', { bubbles: true })); }", [id, str(v)])

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_context(viewport={"width": 1400, "height": 900}).new_page()
    bad = []
    p.on("pageerror", lambda e: bad.append(str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(300)

    print("\n--- which rows are knobs ---")
    rows = p.evaluate("""() => {
      const knobs = [], sliders = [];
      for (const row of document.querySelectorAll('[data-home="bench"] .menu-row')) {
        const grow = row.querySelector(':scope > .grow');
        const ranges = grow ? grow.querySelectorAll(':scope > input[type="range"]') : [];
        if (ranges.length !== 1) continue;
        (row.classList.contains('knob-row') && row.querySelector('.knob-face') ? knobs : sliders).push(ranges[0].id);
      }
      return { knobs, sliders };
    }""")
    kept = sorted(rows["sliders"])
    # The setup morph's crossfader is a slider too, but since F3 it lives in
    # the header's Perform menu (home perform), so it is not on this list.
    meant = sorted(["bar%d" % i for i in range(9)])
    print("    %d knobs; kept as sliders: %s" % (len(rows["knobs"]), ", ".join(kept)))
    check("every Bench slider is a knob but the drawbars",
          # The floor only proves the rows were found at all; it came down
          # from 60 when F2 and F3 took the Picture's and Perform's knobs off
          # the Bench.
          kept == meant and len(rows["knobs"]) >= 50, "%d knobs, %s" % (len(rows["knobs"]), kept))
    # A row the dressing has not reached is counted as a slider, and dressing it makes it a knob.
    fresh = p.evaluate("""() => {
      const group = document.getElementById('oscGroup');
      const row = document.createElement('div'); row.className = 'menu-row';
      row.innerHTML = '<label class="menu-label" for="knobProbe">Probe</label><div class="grow">'
        + '<input type="range" id="knobProbe" min="0" max="10" value="3"><span class="reading">3</span></div>';
      group.appendChild(row);
      const before = row.classList.contains('knob-row');
      dressKnobs(group);
      const after = row.classList.contains('knob-row') && !!row.querySelector('.knob-face');
      row.remove();
      return { before, after };
    }""")
    null("an undressed row reads as a slider", fresh["before"] is False, str(fresh))
    check("and dressing it makes it a knob", fresh["after"] is True, str(fresh))
    access = p.evaluate("""() => { const i = el.oscFm; const cs = getComputedStyle(i);
      return { labels: i.labels.length, display: cs.display, tab: i.tabIndex, hidden: i.closest('[hidden]') !== null }; }""")
    check("the input is still there for the keyboard and a screen reader",
          access["labels"] == 1 and access["display"] != "none" and access["tab"] >= 0, str(access))

    # A knob alone among menu rows is one line, as tall as they are; knobs
    # that come together are cells, read down. Glide is alone in the
    # Generator, between Shape and Interval (Frequency was, between Kind and
    # Shape, until G3 took it to Ink; Twist was, in the Plane, until F5 made
    # it one of the rack's module's main knobs); FM is one of the
    # oscillator's run.
    p.evaluate("() => setBenchTab('play')"); p.wait_for_timeout(200)
    lone = p.evaluate("() => { const r = el.glide.closest('.menu-row'); return { h: r.offsetHeight, w: r.offsetWidth }; }")
    p.evaluate("() => setBenchTab('ink')"); p.wait_for_timeout(200)
    cell = p.evaluate("() => { const r = el.oscFm.closest('.menu-row'); return { h: r.offsetHeight, w: r.offsetWidth }; }")
    print("    alone %s, in a run %s" % (lone, cell))
    check("a knob alone is one line, no taller than a menu row", lone["h"] <= 44 and lone["w"] > 200, str(lone))
    null("a knob in a run is a cell, taller and narrow", cell["h"] > 56 and cell["w"] < 90, str(cell))

    print("\n--- the face points where the value says ---")
    p.evaluate("() => showControl('oscFm')"); p.wait_for_timeout(250)
    ends = {}
    for v in (0, 50, 100):
        setv(p, "oscFm", v)
        ends[v] = p.evaluate(FACE, "oscFm")
    print("    FM 0, 50, 100:", [ends[v]["angle"] for v in (0, 50, 100)])
    check("at the bottom of the range, nought degrees", deg(ends[0]["angle"]) == 0 and deg(ends[0]["hi"]) == 0, str(ends[0]))
    check("at the middle, 135", abs(deg(ends[50]["angle"]) - 135) < 1e-9 and abs(deg(ends[50]["hi"]) - 135) < 1e-9, str(ends[50]))
    check("at the top, the whole 270", abs(deg(ends[100]["angle"]) - 270) < 1e-9, str(ends[100]))
    null("the middle is not the bottom's angle", deg(ends[50]["angle"]) != deg(ends[0]["angle"]))
    bend = {}
    for v in (-100, 0, 100):
        setv(p, "oscBend", v)
        bend[v] = p.evaluate(FACE, "oscBend")
    print("    Bend -100, 0, 100 (lo, hi):", [(bend[v]["lo"], bend[v]["hi"]) for v in (-100, 0, 100)])
    check("a control either side of nought rings out from the top, where nought is",
          deg(bend[0]["lo"]) == 135 and deg(bend[0]["hi"]) == 135
          and deg(bend[100]["lo"]) == 135 and deg(bend[100]["hi"]) == 270
          and deg(bend[-100]["lo"]) == 0 and deg(bend[-100]["hi"]) == 135, str(bend))
    null("from the bottom it would have started at nought", deg(bend[100]["lo"]) != 0)
    setv(p, "oscBend", 0)
    coded = p.evaluate("""() => { const before = el.oscFm.parentElement.querySelector('.knob-face').style.getPropertyValue('--angle');
      el.oscFm.value = '75';      // no event: how a preset, a restore or a host knob writes it
      return { before, after: el.oscFm.parentElement.querySelector('.knob-face').style.getPropertyValue('--angle') }; }""")
    check("a value written from code, with no event, turns the face", abs(deg(coded["after"]) - 202.5) < 1e-9, str(coded))
    null("it was pointing elsewhere before", deg(coded["before"]) != deg(coded["after"]), str(coded))

    print("\n--- turning it by hand ---")
    setv(p, "oscFm", 0)
    p.evaluate("""() => { window.__knobEvents = { input: 0, change: 0 };
      el.oscFm.addEventListener('input', () => window.__knobEvents.input++);
      el.oscFm.addEventListener('change', () => window.__knobEvents.change++); }""")
    x, y = centre(p, "oscFm")
    p.mouse.move(x, y); p.mouse.down(); p.mouse.move(x, y - 90, steps=10); p.mouse.up()
    up = p.evaluate("() => ({ v: Number(el.oscFm.value), reading: el.oscFmValue.textContent, ev: window.__knobEvents })")
    print("    up 90 px:", up)
    check("half the travel up is half the range", up["v"] == 50, str(up))
    null("it began at nought", up["v"] != 0)
    check("and every step fired input, the end of the drag one change",
          up["ev"]["input"] >= 5 and up["ev"]["change"] == 1, str(up["ev"]))
    check("and the reading beside it followed", up["reading"].strip() not in ("", "0.0"), up["reading"])
    p.mouse.move(x, y); p.mouse.down(); p.mouse.move(x, y + 45, steps=6); p.mouse.up()
    down = p.evaluate("() => Number(el.oscFm.value)")
    check("down is less", down == 25, str(down))
    setv(p, "oscFm", 0)
    p.keyboard.down("Shift")
    p.mouse.move(x, y); p.mouse.down(); p.mouse.move(x, y - 90, steps=10); p.mouse.up()
    p.keyboard.up("Shift")
    fine = p.evaluate("() => Number(el.oscFm.value)")
    check("with shift held the same drag is fine: a fifth as far", fine == 11, str(fine))
    null("without shift it was half the range", fine != 50)

    # A disabled control - an oscillator's rate while it follows the tempo - does not turn.
    p.evaluate("() => { el.oscFm.disabled = true; }")
    setv(p, "oscFm", 30)
    p.mouse.move(x, y); p.mouse.down(); p.mouse.move(x, y - 90, steps=10); p.mouse.up()
    frozen = p.evaluate("() => Number(el.oscFm.value)")
    p.evaluate("() => { el.oscFm.disabled = false; }")
    p.mouse.move(x, y); p.mouse.down(); p.mouse.move(x, y - 18, steps=4); p.mouse.up()
    live = p.evaluate("() => Number(el.oscFm.value)")
    check("a disabled knob does not turn", frozen == 30, str(frozen))
    null("enabled again, the same knob does", live == 40, str(live))

    print("\n--- two taps put it back, the arrows still move it ---")
    setv(p, "oscFm", 70)
    p.mouse.click(x, y); p.wait_for_timeout(400)
    once = p.evaluate("() => el.oscFm.value")
    null("one tap leaves it", once == "70", once)
    p.mouse.click(x, y); p.wait_for_timeout(120); p.mouse.click(x, y)
    twice = p.evaluate("() => ({ v: el.oscFm.value, rest: el.oscFm.defaultValue })")
    check("two taps put it back where the page opened it", twice["v"] == twice["rest"] and twice["v"] != "70", str(twice))
    setv(p, "oscFm", 40)
    p.mouse.click(x, y); p.wait_for_timeout(400)
    p.keyboard.press("ArrowUp"); p.keyboard.press("ArrowUp")
    keys = p.evaluate(FACE, "oscFm")
    check("a press on the face gives the keyboard to the input, and the arrows move it and the face",
          keys["v"] == "42" and abs(deg(keys["angle"]) - 42 * 2.7) < 1e-9, str(keys))

    # The Radius is marked at 0.2 and two taps land there; it still opens at
    # 0.4. The Radial menu on first, since a radius with nothing at it is
    # hidden. Two taps on the Cutoff, unmarked, beside it as the null.
    p.evaluate("() => { el.planeLimit.value = '1'; el.planeLimit.dispatchEvent(new Event('change')); showControl('planeRadius'); }")
    p.wait_for_timeout(300)
    setv(p, "planeRadius", 70)
    rb = p.locator("#planeRadiusRow .knob-face").bounding_box()
    rx, ry = rb["x"] + rb["width"] / 2, rb["y"] + rb["height"] / 2
    p.mouse.click(rx, ry); p.wait_for_timeout(120); p.mouse.click(rx, ry); p.wait_for_timeout(100)
    marked = p.evaluate("""() => { const m = document.querySelector('#planeRadiusRow .knob-mark');
      return { v: el.planeRadius.value, rest: el.planeRadius.defaultValue, radius: genSettings().planeRadius,
               t: m ? parseFloat(m.style.getPropertyValue('--t')) : null,
               others: document.querySelectorAll('.knob-mark').length }; }""")
    check("the Radius is marked at 0.2, its one mark on the face, and two taps land there, though it opens at 0.4",
          marked["v"] == "20" and marked["rest"] == "40" and abs(marked["radius"] - 0.2) < 1e-9
          and abs(marked["t"] - (20 - 2) / 98 * 270) < 1e-9 and marked["others"] == 1, str(marked))
    null("the mark is not at the default's angle", abs(marked["t"] - (40 - 2) / 98 * 270) > 10, str(marked["t"]))
    p.evaluate("() => { el.planeLimit.value = '0'; el.planeLimit.dispatchEvent(new Event('change')); }")

    print("\n--- the picture lights the name, and a modulation is a ring on the face ---")
    lit = p.evaluate("""() => { const row = el.oscFm.closest('[data-mod-dest]'), label = row.querySelector(':scope > .menu-label');
      row.style.setProperty('--picture', '1'); const on = getComputedStyle(label).color;
      row.style.setProperty('--picture', '0'); const off = getComputedStyle(label).color;
      row.style.removeProperty('--picture'); return { on, off }; }""")
    def rgb(text):
        # color-mix() comes back as color(srgb r g b) in fractions; a plain colour as rgb().
        import re
        nums = [float(n) for n in re.findall(r"[\d.]+", text)][:3]
        return tuple(round(n * 255) for n in nums) if text.startswith("color(") else tuple(round(n) for n in nums)
    check("moved its whole total, the name is the accent", rgb(lit["on"]) == (192, 127, 121), str(lit))
    null("moved by nought, it is the quiet label's colour", rgb(lit["off"]) == (107, 97, 90), str(lit))
    lane = p.evaluate("""async () => {
      const face = el.freq.parentElement.querySelector('.knob-face');
      state.modRoutings = []; paintRoutings();
      const span = () => face.querySelector('.lane-span');
      const off = span() ? span().hidden : 'none';
      addRouting('lfo1', 'gen.freq'); await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      const s = face.style;
      const out = { off, on: span() && !span().hidden, a: s.getPropertyValue('--lane-a'), b: s.getPropertyValue('--lane-b'),
                    inFace: face.querySelectorAll('.mod-lane').length, inStrip: el.freq.parentElement.querySelectorAll(':scope > .mod-lane').length };
      state.modRoutings = []; paintRoutings();
      return out; }""")
    print("    lane:", lane)
    check("a routing draws its reach as a ring on the face",
          lane["on"] is True and lane["inFace"] == 3 and lane["inStrip"] == 0 and deg(lane["b"]) > deg(lane["a"]), str(lane))
    null("with nothing routed there is no ring", lane["off"] is True, str(lane))
    check("no page errors", not bad, "; ".join(bad[:3]))
    p.close()

    print("\n--- a finger turns it and does not scroll the page ---")
    ctx = b.new_context(viewport={"width": 390, "height": 760}, has_touch=True, is_mobile=True)
    m = ctx.new_page()
    m.goto(f"file://{ART}/scope.html"); m.wait_for_timeout(1500)
    m.evaluate("() => { const d = document.getElementById('helpDialog'); if (d && d.open) d.close(); setView('bench'); showControl('oscFm'); }")
    m.wait_for_timeout(300)
    m.evaluate("""() => { const f = el.oscFm.parentElement.querySelector('.knob-face');
      f.scrollIntoView({ block: 'center' }); el.oscFm.value = '0'; el.oscFm.dispatchEvent(new Event('input')); }""")
    m.wait_for_timeout(300)
    cdp = ctx.new_cdp_session(m)
    def swipe(x0, y0, dy):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
        for k in range(1, 9):
            cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0, "y": y0 + dy * k / 8}]})
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        m.wait_for_timeout(400)
    def scrolled():
        return m.evaluate("""() => { let n = 0; for (const e of [document.scrollingElement, ...document.querySelectorAll('*')])
          { if (e && (e.scrollTop || 0) > 0) n += e.scrollTop; } return n; }""")
    fx, fy = centre(m, "oscFm")
    s0 = scrolled()
    swipe(fx, fy, -60)
    s1 = scrolled()
    v1 = m.evaluate("() => Number(el.oscFm.value)")
    print("    on the knob: scrolled %s -> %s, value %s" % (s0, s1, v1))
    check("a finger dragged up a knob turns it", v1 > 10, str(v1))
    check("and the page under it stays where it was", s1 == s0, "%s -> %s" % (s0, s1))
    # The same swipe off any knob, on the section's own title: the page scrolls.
    tx, ty = m.evaluate("""() => { const t = el.oscFm.closest('.menu-group').querySelector('.menu-title').getBoundingClientRect();
      return [t.x + 20, t.y + t.height / 2]; }""")
    swipe(tx, ty, -60)
    s2 = scrolled()
    null("the same swipe off the knob scrolls the page", s2 != s1, "%s -> %s" % (s1, s2))
    ctx.close()
    b.close()

print("\nKNOBS " + ("PASS" if not fails else "FAIL: " + ", ".join(fails)))
sys.exit(1 if fails else 0)
