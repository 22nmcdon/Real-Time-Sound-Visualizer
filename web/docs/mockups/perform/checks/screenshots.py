"""The Perform mockup's screenshots, at the window's own size, in the brand's webfonts.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/perform/checks/screenshots.py
"""
import os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "tests"))
import webfonts
MOCK = os.path.dirname(HERE)
SHOTS = [
    ("01-up-and-down-two-octaves-at-1400x900", "1400x900", {"arpMode": "updown", "arpOctaves": "2", "arpRate": "1/16", "quantise": True, "quantiseGlide": 80, "morphPos": 35}, "arpMode"),
    ("02-running-at-bar-12-at-960x600", "960x600", {"arpMode": "random", "arpOctaves": "3", "arpRate": "1/8t", "running": True, "bar": 12, "beat": 2}, "transportAt"),
    ("03-off-at-1660x1050", "1660x1050", {}, "tempo"),
]
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=os.environ.get("CHROME", "/opt/pw-browsers/chromium"))
    ctx = b.new_context(viewport={"width": 1700, "height": 1100}, device_scale_factor=2)
    webfonts.route(ctx)
    p = ctx.new_page()
    for name, size, state, said in SHOTS:
        p.goto("file://" + os.path.join(MOCK, "index.html") + "?scale=1&size=" + size)
        webfonts.settle(p)
        p.evaluate("(o) => __m.set(o)", state)
        p.evaluate("(id) => UI.say(id)", said)
        p.wait_for_timeout(150)
        p.locator("#win").screenshot(path=os.path.join(MOCK, name + ".png"))
        print("wrote", name)
    b.close()
