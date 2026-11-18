"""The screenshots beside the mockup: each window alone, at its own size,
drawn at twice the pixels (the plugin's 960x600 at its 90 per cent).

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/play-figures/checks/screenshots.py
"""
import os, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import webfonts

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
    ("06-envelope-editor-over-the-tabs-at-1400x900", "size=1400x900&sub=menv", False),
    ("07-amp-at-1200x680", "size=1200x680&sub=amp", False),
    ("08-filter-at-1100x680", "size=1100x680&sub=filter", False),
    ("09-amp-at-960x600", "size=960x600&sub=amp", False),
    ("10-filter-at-960x600", "size=960x600&sub=filter", False),
    ("11-two-hands-amp-unlinked-at-1400x900", "size=1400x900&sub=amp&hands=2", False),
    ("12-two-hands-amp-unlinked-at-960x600", "size=960x600&sub=amp&hands=2", True),
    ("13-one-hand-at-960x600-compare-with-12", "size=960x600&sub=amp", False),
    ("14-envelope-editor-at-960x600", "size=960x600&sub=menv", False),
    ("15-dyad-at-1400x900", "size=1400x900&sub=amp&mode=dyad", False),
    ("16-wave-sine-at-1400x900", "size=1400x900&sub=wave&shape=sine", False),
    ("17-wave-drawbars-at-1400x900", "size=1400x900&sub=wave&shape=drawbars", False),
    ("18-wave-drawbars-at-960x600", "size=960x600&sub=wave&shape=drawbars", False),
    ("19-wave-sine-at-960x600-compare-with-18", "size=960x600&sub=wave&shape=sine", False),
    ("20-wave-wavetable-at-1100x680", "size=1100x680&sub=wave&shape=wavetable", False),
    ("21-wave-drawn-cycle-at-1660x1050", "size=1660x1050&sub=wave&shape=drawn", False),
    ("22-tuning-in-the-generators-menu-at-1400x900", "size=1400x900&sub=wave&shape=pulse&genmenu=1", False),
]
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    for name, q, note in SHOTS:
        ctx = b.new_context(viewport={"width": 1700, "height": 1100}, device_scale_factor=SCALE)
        p = ctx.new_page()
        webfonts.route(p)
        p.goto(PAGE + "?shot=1&" + q)
        p.wait_for_function("window.__ready === true", timeout=20000)
        webfonts.settle(p)
        p.evaluate("() => window.__figs.render()")
        if "genmenu=1" in q:
            p.click("[data-gen-dots]"); p.wait_for_timeout(200)
        if note:
            p.evaluate("() => { window.__figs.noteDown(); }")
            p.wait_for_timeout(700)
        p.locator("#stage").screenshot(path=os.path.join(HERE, name + ".png"))
        ctx.close()
        print("wrote", name + ".png")
