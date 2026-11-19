"""The screenshots beside the mockup: each window alone, at its own size, drawn
at twice the pixels (the plugin's 960x600 at its 90 per cent). The clock is
stopped for each, the LFO stepped to where the shot catches it.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/lfo/checks/screenshots.py
"""
import os, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import webfonts

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = "file://" + os.path.join(HERE, "index.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
SCALE = float(os.environ.get("SHOT_SCALE", "2"))
# A shape drawn by hand: a quick rise, a held top, a slow curved fall, and a random dip at the end.
DRAWN = """() => { const L = window.__lfo, l = L.S.lfo[0]; L.choosePreset(l, "sine");
  L.editShape(l, (pts) => { pts.splice(0, pts.length,
    { x: 0, y: -0.6, law: "m", m: 0.78, r: false }, { x: 0.125, y: 0.85, law: "l", m: 0.5, r: false }, { x: 0.375, y: 0.85, law: "m", m: 0.3, r: false },
    { x: 0.75, y: -0.2, law: "s", m: 0.5, r: false }, { x: 0.875, y: -0.8, law: "h", m: 0.5, r: true }); });
  l.lv[4] = -0.55; L.S.lfoSel = { pt: 2 }; }"""
SHOTS = [
    ("01-lfo1-sine-as-today-at-1400x900", "size=1400x900&lfo=0&at=0.3", None),
    ("02-a-drawn-shape-at-1400x900", "size=1400x900&lfo=0&at=0.55", DRAWN),
    ("03-saw-down-on-the-tempo-at-1660x1050", "size=1660x1050&lfo=1&shape=rampdown&sync=tempo&starts=note&at=0.4", None),
    ("04-random-steps-at-1200x680", "size=1200x680&lfo=0&shape=random&at=3.4", None),
    ("05-smooth-random-at-960x600", "size=960x600&lfo=1&shape=smooth&at=3.3", None),
    ("06-square-at-1100x860", "size=1100x860&lfo=0&shape=square&at=0.7", None),
    ("07-eight-routings-at-1400x900", "size=1400x900&lfo=0&routes=many&at=0.3", None),
    ("08-a-points-menu-at-1400x900", "size=1400x900&lfo=0&at=0.55", "menu"),
    ("09-a-drawn-shape-at-960x600", "size=960x600&lfo=0&at=0.55", DRAWN),
    ("10-cards-on-the-row-at-1400x900", "size=1400x900&lfo=none&at=0.55", DRAWN),
    ("11-chips-at-960x600", "size=960x600&lfo=none&at=0.55", DRAWN),
    ("12-not-chosen-two-columns-at-1660x1050", "size=1660x1050&lfo=0&layout=two&routes=many&at=0.3", None),
    ("13-not-chosen-two-columns-at-960x600", "size=960x600&lfo=0&layout=two&routes=many&at=0.3", None),
]
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    for name, q, then in SHOTS:
        ctx = b.new_context(viewport={"width": 1700, "height": 1100}, device_scale_factor=SCALE)
        p = ctx.new_page()
        webfonts.route(p)
        p.goto(PAGE + "?shot=1&" + q)
        p.wait_for_function("window.__ready === true", timeout=30000)
        webfonts.settle(p)
        p.evaluate("() => { window.__lfo.S.clock = 'stop'; }")
        if then == "menu":
            p.evaluate(DRAWN); p.evaluate("() => window.__lfo.render()")
            r = p.locator('#lfoEd [data-lpt="4"] .ring').bounding_box()
            p.mouse.click(r["x"] + r["width"] / 2, r["y"] + r["height"] / 2, button="right")
            p.wait_for_timeout(150)
        elif then:
            p.evaluate(then)
            p.evaluate("() => window.__lfo.render()")
        p.locator("#stage").screenshot(path=os.path.join(HERE, name + ".png"))
        ctx.close()
        print("wrote", name + ".png")
