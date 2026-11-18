"""Why Play has a gap between the Keyboard band and its columns on testing
(d5c2928), measured in scope.html itself.

The bench body is a wrapping flex row (since the band, 17 Nov): the band is
the first line, the three columns the second. Its height is the tab's, so
there is spare height under the columns, and with `align-content` left at
`normal` a wrapping flex container *stretches its lines*: the spare height is
shared between the two lines, and the band, aligned to the top of its
stretched line, has half the spare height under it. The gap therefore grows
with the window's height and with how short the columns are.

Checked here, at 1660x1050 and 1400x900, the popover shut and open:
- the body's computed align-content is `normal` and it wraps;
- the gap under the band, less the row gap, is half of the spare height
  (body height - band - tallest column - row gap), to a pixel;
- with `align-content: flex-start` the gap is the row gap and nothing more.
  Null: it was not that before;
- neither the hidden knob store nor the popover is the cause: both are out of
  the flow (the store hidden, the popover absolutely placed in the stage), so
  removing them leaves the gap where it was.
And the popover at 1660x1050, as the owner saw it: its drawing's size (the
tower) and how many rows its knobs take.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/play-figures/checks/gap_cause.py
"""
import os, sys, json
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import webfonts

SCOPE = "file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "scope.html"))
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
fails, n = [], [0]
def check(ok, what):
    n[0] += 1
    print(("ok   " if ok else "FAIL ") + what)
    if not ok: fails.append(what)

MEASURE = """() => { const B = el.benchBody, cs = getComputedStyle(B), band = B.querySelector('.bench-band');
  const cols = [...B.querySelectorAll('.bench-col')].filter((c) => c.childElementCount);
  const r = (n) => n.getBoundingClientRect();
  const colTop = Math.min(...cols.map((c) => r(c).top)), colH = Math.max(...cols.map((c) => r(c).height));
  return { ac: cs.alignContent, wrap: cs.flexWrap, rowGap: parseFloat(cs.rowGap), bodyH: r(B).height, bandH: r(band).height, colH,
           gap: colTop - r(band).bottom }; }"""
out = {}
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    for W, H in ((1660, 1050), (1400, 900)):
        p = b.new_page(viewport={"width": W, "height": H})
        webfonts.route(p)
        p.goto(SCOPE); p.wait_for_timeout(1200); out["webfonts"] = webfonts.settle(p)
        if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
        p.evaluate("() => setBenchTab('play')"); p.wait_for_timeout(400)
        for pop in (False, True):
            if pop: p.evaluate("() => openMsegPop('amp')"); p.wait_for_timeout(300)
            m = p.evaluate(MEASURE)
            tag = "%dx%d, the popover %s" % (W, H, "open" if pop else "shut")
            spare = m["bodyH"] - m["bandH"] - m["colH"] - m["rowGap"]
            check(m["ac"] == "normal" and m["wrap"] == "wrap", tag + ": the body wraps, align-content %s" % m["ac"])
            check(abs((m["gap"] - m["rowGap"]) - spare / 2) <= 1, tag + ": the gap under the band, %.0f px, is the row gap %.0f and half the spare height %.0f" % (m["gap"], m["rowGap"], spare))
            p.evaluate("() => { el.benchBody.style.alignContent = 'flex-start'; }"); p.wait_for_timeout(100)
            fixed = p.evaluate(MEASURE)
            p.evaluate("() => { el.benchBody.style.alignContent = ''; }"); p.wait_for_timeout(100)
            check(abs(fixed["gap"] - m["rowGap"]) <= 0.5, tag + ": with align-content flex-start the gap is the row gap, %.0f px" % fixed["gap"])
            check(not abs(m["gap"] - m["rowGap"]) <= 0.5, "null: " + tag + ": before it, it was not (%.0f px)" % m["gap"])
            out[tag] = {"gap": round(m["gap"]), "rowGap": m["rowGap"], "spare": round(spare), "fixed": round(fixed["gap"])}
        # Not the store and not the popover: take both out of the page and the gap stays.
        g2 = p.evaluate("() => { const before = (" + MEASURE + ")().gap; el.ampEnvStore.remove(); el.vcfStore.remove(); el.msegPop.remove(); return [before, (" + MEASURE + ")().gap]; }")
        check(abs(g2[0] - g2[1]) <= 0.5, "%dx%d: with the knob stores and the popover taken out the gap stays %.0f px" % (W, H, g2[1]))
        p.close()
    # The popover as the owner saw it at 1660x1050.
    p = b.new_page(viewport={"width": 1660, "height": 1050})
    webfonts.route(p)
    p.goto(SCOPE); p.wait_for_timeout(1200); webfonts.settle(p)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate("() => setBenchTab('play')"); p.wait_for_timeout(300)
    p.evaluate("() => openMsegPop('amp')"); p.wait_for_timeout(400)
    t = p.evaluate("""() => { const pl = el.msegPlot.getBoundingClientRect(), pop = el.msegPop.getBoundingClientRect();
      const rows = new Set([...el.msegKnobs.querySelectorAll('.menu-row')].map((r) => Math.round(r.getBoundingClientRect().top))).size;
      return { w: Math.round(pl.width), h: Math.round(pl.height), popBottom: Math.round(pop.bottom), modTop: Math.round(document.getElementById('modRow').getBoundingClientRect().top), rows }; }""")
    check(t["h"] > t["w"], "the amp's drawing in the popover at 1660x1050 is a tower, %d x %d" % (t["w"], t["h"]))
    out["popover at 1660x1050"] = t
    print(json.dumps(out))
print("%d checks, %d failed" % (n[0], len(fails)))
sys.exit(1 if fails else 0)
