"""The screenshots beside the mockup: each window alone, at its own size, drawn at twice the pixels
(the plugin's 960x600 at its 90 per cent).

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/play-band/checks/screenshots.py
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
    ("01-one-hand-at-1660x1050", "size=1660x1050&sub=amp"),
    ("02-notes-lowest-2-wave-sh-at-1660x1050-the-owners-case", "size=1660x1050&hands=2&link=1&kind=notes&count=2&sub=wave&shape=stepped"),
    ("03-notes-highest-3-at-1400x900", "size=1400x900&hands=2&link=1&kind=notes&edge=high&count=3&sub=amp"),
    ("04-notes-nothing-held-at-1400x900", "size=1400x900&hands=2&link=1&kind=notes&chord=none&sub=amp"),
    ("05-key-at-1400x900", "size=1400x900&hands=2&kind=key&sub=amp"),
    ("06-layer-at-1400x900", "size=1400x900&hands=2&link=1&kind=layer&sub=filter"),
    ("07-dyad-at-1400x900", "size=1400x900&mode=dyad&sub=amp"),
    ("08-mono-at-1400x900", "size=1400x900&mode=mono&sub=amp"),
    ("09-notes-at-1100x860", "size=1100x860&hands=2&link=1&kind=notes&count=4&sub=filter"),
    ("10-key-at-1200x680", "size=1200x680&hands=2&kind=key&sub=amp"),
    ("11-notes-at-1100x680-wave-drawbars", "size=1100x680&hands=2&link=1&kind=notes&count=2&sub=wave&shape=drawbars"),
    ("12-notes-highest-6-at-960x600", "size=960x600&hands=2&link=1&kind=notes&edge=high&count=6&sub=amp"),
    ("13-one-hand-at-960x600-compare-with-12", "size=960x600&sub=amp"),
    ("14-wave-pulse-at-960x600", "size=960x600&sub=wave&shape=pulse"),
    ("15-filter-at-960x600", "size=960x600&hands=2&link=1&kind=notes&sub=filter"),
    ("16-tuning-in-waves-dots-at-1400x900", "size=1400x900&sub=wave&shape=sine&genmenu=1"),
]
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    for name, q in SHOTS:
        ctx = b.new_context(viewport={"width": 1700, "height": 1100}, device_scale_factor=SCALE)
        p = ctx.new_page()
        webfonts.route(p)
        p.goto(PAGE + "?shot=1&" + q)
        p.wait_for_function("window.__ready === true", timeout=30000)
        webfonts.settle(p)
        p.evaluate("() => window.__figs.render()")
        if "genmenu=1" in q:
            p.click("[data-gen-dots]"); p.wait_for_timeout(200)
        p.locator("#stage").screenshot(path=os.path.join(HERE, name + ".png"))
        ctx.close()
        print("wrote", name + ".png")
