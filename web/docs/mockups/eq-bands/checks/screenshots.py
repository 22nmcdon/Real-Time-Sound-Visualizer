"""The mockup's screenshots, of the editor (and one of the whole window), at
deviceScaleFactor 2, the stage at its own size. A cross marks the pointer
where a drag is shown, so the point can be seen to be under it or not.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/eq-bands/checks/screenshots.py
"""
import os, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import webfonts
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CROSS = """([x, y]) => { const c = document.createElement('div'); c.id = 'cross';
  c.style.cssText = 'position:fixed;left:' + (x - 9) + 'px;top:' + (y - 9) + 'px;width:18px;height:18px;pointer-events:none;z-index:99;'
   + 'background:linear-gradient(#a4553f,#a4553f) center/2px 18px no-repeat,linear-gradient(#a4553f,#a4553f) center/18px 2px no-repeat';
  document.body.appendChild(c); }"""


def page(b, size, place="own", start="shaped"):
    # Wide enough that the stage is at its own size (scale 1, or 0.9 for the compact window).
    p = b.new_page(viewport={"width": 1700, "height": 1150}, device_scale_factor=2)
    webfonts.route(p)
    p.goto("file://" + os.path.join(HERE, "index.html")); p.wait_for_timeout(300); webfonts.settle(p)
    p.add_style_tag(content=".page{max-width:1600px}")
    p.evaluate("() => window.dispatchEvent(new Event('resize'))")
    p.locator('#pgSize button[data-v="%s"]' % size).click()
    p.locator('#pgPlace button[data-v="%s"]' % place).click()
    p.locator('#pgStart button[data-v="%s"]' % start).click()
    p.wait_for_timeout(200)
    return p


def drag_right(p, k, hz=None):
    # From the point, straight across to where hz is on the plot, or (no hz) 24 px past its right edge, as the owner did.
    r = p.evaluate("([k, hz]) => { const q = document.querySelector('.pt[data-band=\"' + k + '\"] .ring').getBoundingClientRect(); const b = document.getElementById('plot').getBoundingClientRect(); return [q.left + q.width / 2, q.top + q.height / 2, hz ? b.left + mock.geo().x(hz) * b.width / mock.geo().w : b.right + 24]; }", [k, hz])
    p.mouse.move(r[0], r[1]); p.mouse.down()
    x = r[2]
    for i in range(1, 21):
        p.mouse.move(r[0] + (x - r[0]) * i / 20, r[1])
    p.evaluate(CROSS, [x, r[1]])


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=os.environ.get("CHROME", "/opt/pw-browsers/chromium"))
    shots = []
    p = page(b, "1400x900"); p.locator("#win").screenshot(path=os.path.join(HERE, "01-the-window-high-cut-chosen-at-1400x900.png")); p.close()
    p = page(b, "1400x900"); p.locator('.cell[data-band="2"]').click(); p.locator("#ed").screenshot(path=os.path.join(HERE, "02-mid-chosen-its-width-bracketed-at-1400x900.png")); p.close()
    p = page(b, "1400x900"); p.locator('.cell[data-band="3"] .lamp').click(); p.locator('.cell[data-band="1"]').click()
    p.locator("#ed").screenshot(path=os.path.join(HERE, "03-high-shelf-off-low-shelf-chosen-at-1400x900.png")); p.close()
    p = page(b, "1400x900"); drag_right(p, 4); p.locator("#ed").screenshot(path=os.path.join(HERE, "04-high-cut-dragged-past-the-right-edge-proposed-at-1400x900.png")); p.close()
    p = page(b, "1400x900", place="sum"); drag_right(p, 4); p.locator("#ed").screenshot(path=os.path.join(HERE, "05-the-same-drag-today-the-point-leaves-the-pointer-at-1400x900.png")); p.close()
    p = page(b, "960x600"); p.locator('.cell[data-band="0"]').click(); p.locator("#ed").screenshot(path=os.path.join(HERE, "06-low-cut-chosen-at-960x600.png")); p.close()
    p = page(b, "960x600", start="flat"); p.locator('.cell[data-band="2"]').click(); p.locator("#ed").screenshot(path=os.path.join(HERE, "07-flat-a-new-setup-at-960x600.png")); p.close()
    p = page(b, "960x600"); p.locator("#edOn").click(); p.locator("#ed").screenshot(path=os.path.join(HERE, "08-the-eq-off-at-960x600.png")); p.close()
    b.close()
