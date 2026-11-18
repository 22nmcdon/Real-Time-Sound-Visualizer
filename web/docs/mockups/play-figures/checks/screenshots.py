"""The screenshots beside the mockup: each window alone, at its own size,
drawn at twice the pixels (the plugin's 960x600 at its 90 per cent).

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/play-figures/checks/screenshots.py
"""
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = "file://" + os.path.join(HERE, "index.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
SCALE = float(os.environ.get("SHOT_SCALE", "2"))
SHOTS = [
    ("01-amp-at-1660x1050", "size=1660x1050&sub=amp", False),
    ("02-amp-at-1400x900", "size=1400x900&sub=amp", False),
    ("03-amp-a-note-held-at-1400x900", "size=1400x900&sub=amp", True),
    ("04-filter-by-room-stacked-at-1660x1050", "size=1660x1050&sub=filter", False),
    ("05-filter-side-by-side-at-1400x900", "size=1400x900&sub=filter", False),
    ("06-envelope-following-at-1100x860", "size=1100x860&sub=menv", False),
    ("07-amp-at-1200x680", "size=1200x680&sub=amp", False),
    ("08-filter-at-1100x680", "size=1100x680&sub=filter", False),
    ("09-amp-at-960x600", "size=960x600&sub=amp", False),
    ("10-filter-at-960x600", "size=960x600&sub=filter", False),
    ("11-two-hands-amp-unlinked-at-1400x900", "size=1400x900&sub=amp&hands=2", False),
    ("12-two-hands-amp-unlinked-at-960x600", "size=960x600&sub=amp&hands=2", True),
]
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    for name, q, note in SHOTS:
        ctx = b.new_context(viewport={"width": 1700, "height": 1100}, device_scale_factor=SCALE)
        p = ctx.new_page()
        p.goto(PAGE + "?shot=1&" + q)
        p.wait_for_function("window.__ready === true", timeout=20000)
        if note:
            p.evaluate("() => { window.__figs.noteDown(); }")
            p.wait_for_timeout(700)
        p.locator("#stage").screenshot(path=os.path.join(HERE, name + ".png"))
        ctx.close()
        print("wrote", name + ".png")
