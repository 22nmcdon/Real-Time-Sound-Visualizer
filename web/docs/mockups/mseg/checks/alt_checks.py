"""The MSEG alternatives page's checks, in Chromium (web/docs/mockups/mseg/alternatives.html).

- no console errors, through every alternative, window, editing state and
  preview style, with a note held;
- every row of the page's own survey fits: Play does not scroll, B's popover
  covers neither its block nor the keyboard band and stays inside the tab,
  D's strip covers no section, and no editable drawing is under 44 px;
- the nulls: B's popover moved over its own block must be seen to cover it,
  and D's strip reaching 138 px further up must be seen to cover a section, so
  neither check is one that cannot fail;
- a phone's width has no horizontal page scroll.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/mseg/checks/alt_checks.py
"""
import os, sys
from playwright.sync_api import sync_playwright

PAGE = "file://" + os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "alternatives.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
fails = []

def check(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME if os.path.exists(CHROME) else None)
    page = b.new_page(viewport={"width": 1500, "height": 1100})
    errs = []
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(PAGE)
    page.wait_for_timeout(800)
    for style in ["i", "ii", "iii"]:
        page.click('#pgStyle [data-v="%s"]' % style)
        rows = page.evaluate("__mseg.survey(), window.__survey")
        for m in rows:
            name = "style %s, %s %s %s" % (style, m["alt"], m["size"], m["label"])
            check(m["over"] <= 1, name + ": Play fits (%s px over)" % m["over"])
            small = [x for x in m["plots"] if x["h"] < 44]
            check(not small, name + ": no drawing under 44 px %s" % small)
            if m.get("pop"):
                q = m["pop"]
                check(not q["coversBlock"] and not q["coversBand"] and q["inside"] and q["over"] <= 1,
                      name + ": popover %sx%s, %s%% of the tab, clear of its block and the band" % (q["w"], q["h"], q["share"]))
            if m.get("strip"):
                check(m["strip"]["covers"] == 0 and m["strip"]["over"] <= 1, name + ": strip %sx%s covers no section" % (m["strip"]["w"], m["strip"]["h"]))
    # Walk the views by hand too, with a note held, for errors.
    for alt in "ABCD":
        page.click('#pgAlt [data-v="%s"]' % alt)
        for size in ["big", "small"]:
            page.click('#pgSize [data-v="%s"]' % size)
            for edit in (["amp"] if alt == "A" else ["", "amp", "filter"]):
                if alt != "A":
                    page.click('#pgEdit [data-v="%s"]' % edit)
                page.evaluate("__mseg.noteDown()"); page.wait_for_timeout(90); page.evaluate("__mseg.noteUp()")
    # The nulls.
    page.click('#pgSize [data-v="big"]'); page.click('#pgAlt [data-v="B"]'); page.click('#pgEdit [data-v="amp"]')
    hit = page.evaluate("""() => { const pop = document.getElementById('pop'), blk = document.querySelector('[data-sect="amp"]');
        const sc = +document.getElementById('stage').dataset.scale, br = document.getElementById('bench').getBoundingClientRect(), r = blk.getBoundingClientRect();
        pop.style.left = ((r.left - br.left) / sc - 20) + 'px'; return __mseg.measureNow().pop.coversBlock; }""")
    check(hit, "null: a popover moved over its block is seen to cover it")
    page.click('#pgAlt [data-v="D"]'); page.click('#pgEdit [data-v="amp"]')
    cov = page.evaluate("""() => { document.getElementById('win').style.setProperty('--strip-up', '200px'); const c = __mseg.measureNow().strip.covers;
        document.getElementById('win').style.removeProperty('--strip-up'); return c; }""")
    check(cov > 0, "null: the strip reaching 138 px further up is seen to cover %s section(s)" % cov)
    page.set_viewport_size({"width": 390, "height": 800}); page.wait_for_timeout(200)
    sw = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
    check(sw[0] <= sw[1], "phone width: no horizontal scroll (%s within %s)" % tuple(sw))
    check(not errs, "no console errors %s" % errs[:3])
    b.close()
print("%d failed" % len(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
