"""The Picture strip mockup's screenshots: testing's strip and the mockup's at the same window, the
longest line the page has in the info line, in the brand's webfonts.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/picture-strip/checks/screenshots.py
"""
import os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "web", "tests"))
import webfonts
MOCK = os.path.dirname(HERE)
SAY = "scanSoft"   # the line the owner saw cut on testing
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=os.environ.get("CHROME", "/opt/pw-browsers/chromium"))
    for i, (size, vw, vh) in enumerate([("1400x900", 1400, 900), ("960x600", 960, 600)]):
        ctx = b.new_context(viewport={"width": vw, "height": vh}, device_scale_factor=2)
        webfonts.route(ctx)
        p = ctx.new_page()
        p.goto("file://" + os.path.join(ROOT, "web", "scope.html")); p.wait_for_timeout(900); webfonts.settle(p)
        if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
        p.hover("#scanSoft + .knob-face, [data-say='scanSoft'], #scanSoftValue")
        p.wait_for_timeout(300)
        p.locator("#pictureBar").screenshot(path=os.path.join(MOCK, "%02d-testing-at-%s.png" % (2 * i + 1, size)))
        ctx.close()
        ctx = b.new_context(viewport={"width": 1700, "height": 1100}, device_scale_factor=2)
        webfonts.route(ctx)
        p = ctx.new_page()
        p.goto("file://" + os.path.join(MOCK, "index.html") + "?scale=1&size=" + size); webfonts.settle(p)
        p.evaluate("(id) => UI.say(id)", SAY)
        p.wait_for_timeout(150)
        p.locator("#pictureBar").screenshot(path=os.path.join(MOCK, "%02d-mockup-at-%s.png" % (2 * i + 2, size)))
        ctx.close()
    ctx = b.new_context(viewport={"width": 1700, "height": 1100}, device_scale_factor=2)
    webfonts.route(ctx)
    p = ctx.new_page()
    p.goto("file://" + os.path.join(MOCK, "index.html") + "?scale=1&size=1100x860"); webfonts.settle(p)
    p.evaluate("() => { const w = Object.entries(UI.D.words).sort((a, b) => b[1][1].length - a[1][1].length)[0]; UI.say(w[0]); }")
    p.locator("#win").screenshot(path=os.path.join(MOCK, "05-the-longest-line-at-1100x860.png"))
    b.close()
print("done")
