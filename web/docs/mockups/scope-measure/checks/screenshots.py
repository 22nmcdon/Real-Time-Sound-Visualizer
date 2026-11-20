"""The Scope & measure mockup's screenshots, at the window's own size, in the brand's webfonts.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/scope-measure/checks/screenshots.py
"""
import os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "tests"))
import webfonts
MOCK = os.path.dirname(HERE)
SHOTS = [
    ("01-trigger-at-1400x900", "1400x900", {"tab": "trigger", "level": 250, "position": 30, "holdoff": 20}),
    ("02-time-zoom-and-lag-at-1200x680", "1200x680", {"tab": "time", "zoom": 12, "lagOn": True}),
    ("03-vertical-filter-on-at-960x600", "960x600", {"tab": "vertical", "filterOn": True, "ch2Offset": -40, "ch1Offset": 30, "ch1Scale": 1}),
    ("04-measure-readouts-and-cursors-at-1660x1050", "1660x1050", {"tab": "measure", "readoutsOn": True, "cursorsOn": True}),
]
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=os.environ.get("CHROME", "/opt/pw-browsers/chromium"))
    ctx = b.new_context(viewport={"width": 1700, "height": 1100}, device_scale_factor=2)
    webfonts.route(ctx)
    p = ctx.new_page()
    for name, size, state in SHOTS:
        p.goto("file://" + os.path.join(MOCK, "index.html") + "?scale=1&size=" + size)
        webfonts.settle(p)
        p.evaluate("(o) => __m.set(o)", state)
        p.evaluate("(id) => UI.say(id)", {"trigger": "level", "time": "zoom", "vertical": "filterCutoff", "measure": "cursorsOn"}[state["tab"]])
        p.wait_for_timeout(150)
        p.locator("#win").screenshot(path=os.path.join(MOCK, name + ".png"))
        print("wrote", name)
    b.close()
