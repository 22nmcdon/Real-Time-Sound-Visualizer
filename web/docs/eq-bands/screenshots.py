"""Screenshots of the EQ's band strip as built (23 Nov), from scope.html itself,
at 1400x900 and at 960x600 (Auto's 90 per cent), for the owner: the editor
with a shaped curve and each band chosen in turn, a band switched off, and
the high cut dragged past the right-hand edge with the pointer marked.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/eq-bands/screenshots.py
"""
import os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.abspath(os.path.join(HERE, "..", "..", "scope.html"))
sys.path.insert(0, os.path.join(HERE, "..", "mockups", "eq-bands", "checks"))
import webfonts
SHAPED = """() => { setBenchTab('space'); restore({}); setEqOn(true); setControl('eqLow', 45); setControl('eqMid', -30);
  setControl('eqHigh', 40); setEqBandOn(3, true); setEqBandOn(4, true); setControl('eqCutLowFreq', eqPos(3, 40));
  setControl('eqCutHighFreq', eqPos(4, 9000)); setControl('eqCutHighQ', 140); openEqEditor(); }"""
CROSS = """([x, y]) => { const c = document.createElement('div');
  c.style.cssText = 'position:fixed;left:' + (x - 9) + 'px;top:' + (y - 9) + 'px;width:18px;height:18px;pointer-events:none;z-index:99;'
   + 'background:linear-gradient(#a4553f,#a4553f) center/2px 18px no-repeat,linear-gradient(#a4553f,#a4553f) center/18px 2px no-repeat';
  document.body.appendChild(c); }"""
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=os.environ.get("CHROME", "/opt/pw-browsers/chromium"))
    for W, H in [(1400, 900), (960, 600)]:
        def page():
            p = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
            webfonts.route(p)
            p.goto("file://" + PAGE); p.wait_for_timeout(1200); webfonts.settle(p)
            if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
            p.evaluate(SHAPED); p.wait_for_timeout(400)
            return p
        p = page()
        for n, (k, name) in enumerate([(4, "high-cut"), (1, "mid"), (0, "low-shelf"), (3, "low-cut")]):
            p.evaluate("(k) => { eqChoose(k); paintEq(); }", k); p.wait_for_timeout(150)
            p.screenshot(path=os.path.join(HERE, "%02d-%s-chosen-at-%dx%d.png" % (n + 1, name, W, H)))
        lamp = p.evaluate("() => { const r = el.eqStrip.querySelector('[data-eq-band=\"2\"] .eq-lamp').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
        p.mouse.click(lamp[0], lamp[1]); p.wait_for_timeout(150)
        p.screenshot(path=os.path.join(HERE, "05-high-shelf-switched-off-at-%dx%d.png" % (W, H)))
        p.close()
        p = page()
        r = p.evaluate("() => { const q = eqEd.parts.points[4].querySelector('.eq-ring').getBoundingClientRect(), b = el.eqPlot.getBoundingClientRect(); return [q.left + q.width / 2, q.top + q.height / 2, b.right]; }")
        p.mouse.move(r[0], r[1]); p.mouse.down()
        for i in range(1, 21): p.mouse.move(r[0] + (r[2] + 24 - r[0]) * i / 20, r[1])
        p.evaluate(CROSS, [r[2] + 24, r[1]]); p.wait_for_timeout(100)
        p.screenshot(path=os.path.join(HERE, "06-high-cut-dragged-past-the-right-edge-at-%dx%d.png" % (W, H)))
        p.mouse.up(); p.close()
    b.close()
