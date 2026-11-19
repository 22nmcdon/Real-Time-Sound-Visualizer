"""The screenshots beside the mockup: each window alone, at its own size, drawn
at twice the pixels (the plugin's 960x600 at its 90 per cent).

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/ink/checks/screenshots.py
"""
import os, sys, json
from urllib.parse import quote
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import webfonts

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = "file://" + os.path.join(HERE, "index.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
SCALE = float(os.environ.get("SHOT_SCALE", "2"))
SHOTS = [
    ("01-oscillator-plain-at-1400x900", "size=1400x900", {}),
    ("02-oscillator-fm-at-3-2-at-1400x900", "size=1400x900", {"oscFm": 20, "oscRatio": 1.5}),
    ("03-oscillator-warp-at-1660x1050", "size=1660x1050", {"oscBend": 60, "oscBendAt": 25}),
    ("04-oscillator-ring-at-1100x860", "size=1100x860", {"oscRing": 70, "oscRatio": 2}),
    ("05-oscillator-sync-saw-at-1200x680", "size=1200x680&gen=ramp", {"oscSync": 260}),
    ("06-oscillator-sub-at-960x600", "size=960x600", {"oscSub": 60}),
    ("07-oscillator-unison-at-1100x680", "size=1100x680", {"oscUnison": 5, "oscSpread": 20}),
    ("08-shaping-drive-and-4-bits-at-1400x900", "size=1400x900&sub=shp", {"shpDrive": 45, "shpBits": 4}),
    ("09-shaping-fold-and-2-khz-at-960x600", "size=960x600&sub=shp", {"shpFold": 35, "shpRate": 2000}),
    ("10-shaping-at-1660x1050", "size=1660x1050&sub=shp", {"shpDrive": 30, "shpFold": 15}),
    ("11-not-chosen-wave-and-figure-at-1400x900", "size=1400x900&shows=both", {"oscFm": 20, "oscRatio": 1.5}),
    ("12-not-chosen-wave-and-figure-at-960x600", "size=960x600&shows=both", {"oscRing": 70, "oscRatio": 2}),
]
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    for name, q, st in SHOTS:
        ctx = b.new_context(viewport={"width": 1700, "height": 1100}, device_scale_factor=SCALE)
        p = ctx.new_page()
        webfonts.route(p)
        p.goto(PAGE + "?shot=1&" + q + "&set=" + quote(json.dumps(st)))
        p.wait_for_function("window.__ready === true", timeout=60000)
        webfonts.settle(p)
        p.evaluate("() => window.__ink.render()")
        p.locator("#stage").screenshot(path=os.path.join(HERE, name + ".png"))
        ctx.close()
        print("wrote", name + ".png")
