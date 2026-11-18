"""The MSEG mockup's own checks, in Chromium (web/docs/mockups/mseg).

- no console errors, opening every view at both windows and playing a note;
- Play fits with no scroll at 1400x900 and at 960x600 (Auto's 90 per cent),
  and so does each editor; the null is Play with the old sections' height
  put back (
  150 and 160 px, about what the amp envelope's drawing and knobs and
  the filter's four knob rows and envelope heading took), which must
  overflow at 960x600, or the measure could not see an overflow;
- the decibel axis: every row of the page's own table within half a pixel
  (or 0.05 dB read back), and its null, a straight amplitude axis, missing
  by more than that on every row but 0 dB and silence, which the two axes share;
- a point added on the line changes nothing heard (levelAt at 2000 times),
  and its null - the new halves given the whole stretch's bend as a
  midpoint, the obvious way to write it - must change it;
- a phone's width has no horizontal page scroll.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/mseg/checks/page_checks.py
"""
import os, sys
from playwright.sync_api import sync_playwright

PAGE = "file://" + os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "index.html")
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
    page.wait_for_timeout(300)
    for size in ["big", "small"]:
        page.click('#pgSize [data-v="%s"]' % size)
        for v in ["play", "amp", "filter", "menv"]:
            page.click('#pgView [data-v="%s"]' % v)
            page.evaluate("__mseg.noteDown()"); page.wait_for_timeout(120); page.evaluate("__mseg.noteUp()")
            fit = page.evaluate("window.__fit")
            check(fit["over"] <= 1, "%s %s: Play fits (%s px over), free %s" % (size, v, fit["over"], fit["frees"]))
            if v != "play":
                check(fit.get("editorOver", 0) <= 1, "%s %s: the editor fits (%s px over)" % (size, v, fit.get("editorOver")))
        # The null for the fit: the old sections' height back on Play must overflow at the small window.
        if size == "small":
            over = page.evaluate("""() => { __mseg.S.view = 'play'; __mseg.render();
              const add = (id, h) => { const d = document.createElement('div'); d.style.height = h + 'px'; d.className = 'nullpad'; document.getElementById(id).insertBefore(d, document.querySelector('#' + id + ' .free')); };
              add('col2', 150); add('col3', 160);
              const cols = document.getElementById('cols'); const o = cols.scrollHeight - cols.clientHeight;
              document.querySelectorAll('.nullpad').forEach((n) => n.remove()); return o; }""")
            check(over > 1, "null: Play with 150 and 160 px more in its two columns overflows at 960x600 (%s px over)" % over)
    # The decibel axis.
    page.click('#pgSize [data-v="big"]'); page.click('#pgView [data-v="amp"]'); page.wait_for_timeout(100)
    rows = page.evaluate("dbAxisCheck()")
    for r in rows:
        tol = 0.05 if r.get("unit") == "dB" else 0.5
        check(abs(r["drawn"] - r["req"]) < tol, "dB axis: %s drawn %.3f, required %.3f" % (r["what"], r["drawn"], r["req"]))
        # 0 dB, the floor (0.001 of full scale, 0.4 px off the foot either way) and silence are where the two
        # axes meet, so the null cannot tell them apart there, and is not asked to.
        shared = r["what"].startswith("Gridline 0 ") or r["what"].startswith("Gridline −60") or r["what"] == "Silence"
        if not shared:
            check(abs(r["nul"] - r["req"]) >= tol, "dB axis null misses: %s (straight %.2f)" % (r["what"], r["nul"]))
    # A point added on the line.
    res = page.evaluate("""() => {
      const times = Array.from({ length: 2000 }, (_, i) => i * 0.4);
      const base = makeEnv({ attack: 30, decay: 300, sus: 0.3, release: 400 }, { decay: { m: 0.8 } });
      const before = times.map((t) => levelAt(base, t, 500));
      const S = __mseg.S, keep = S.amp; S.amp = [JSON.parse(JSON.stringify(base)), JSON.parse(JSON.stringify(base))];
      __mseg.addPoint('amp', 'pre', 150);
      const added = S.amp[0], after = times.map((t) => levelAt(added, t, 500));
      // The null: both halves given the whole stretch's bend as a midpoint.
      const nul = JSON.parse(JSON.stringify(added)); nul.inner.decay[0].b = { m: 0.8 }; nul.b.decay = { m: 0.8 };
      const after0 = times.map((t) => levelAt(nul, t, 500));
      S.amp = keep; __mseg.render();
      const d = (a) => Math.max(...a.map((v, i) => Math.abs(v - before[i])));
      return { n: added.inner.decay.length, diff: d(after), nul: d(after0) };
    }""")
    check(res["n"] == 1 and res["diff"] < 1e-12, "a point added on the line changes nothing (%.1e)" % res["diff"])
    check(res["nul"] > 1e-3, "null: halves given the whole's midpoint change it (%.4f)" % res["nul"])
    page.set_viewport_size({"width": 390, "height": 800}); page.wait_for_timeout(200)
    sw = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
    check(sw[0] <= sw[1], "phone width: no horizontal scroll (%s within %s)" % tuple(sw))
    check(not errs, "no console errors %s" % errs)
    b.close()
print("%d failed" % len(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
