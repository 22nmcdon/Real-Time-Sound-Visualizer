"""The popover page's checks, in Chromium (web/docs/mockups/mseg/popover.html).

- no console errors, through both takes, both windows, both small-block and
  filter-block variants and both level axes, with a note held;
- the page opens on the owner's choice of 18 Nov (take 2, straight
  amplitude, small block a, the filter's block with its envelope), its
  switches saying so. Null: a choice the owner did not make must not match;
- every row of the page's survey: Play does not scroll; the panel stays
  clear of its own block and the keyboard band, inside the tab, and its
  content inside it; the knobs are always there (one group for the amp
  envelope, two for the filter) and each group is one row. Nulls: the panel
  squeezed to 150 px wide must be seen to wrap its knobs, and a panel with
  its knobs taken out must be seen to have none;
- the small blocks carry the shape and nothing else: no text, no handles, no
  grid at rest, and only the gold dot while a note sounds. Null: a word
  added to one must be seen;
- the level axis: the sustain point is drawn at 1 - 0.70 of the height in
  straight amplitude and at 3.1 / 48 of it in decibels, to half a pixel; the
  null, each drawn by the other's law, must miss by more than 5 px;
- every handle of the panel's drawings lies inside its drawing, in every
  survey row. Null: a drawing whose fitted scale is doubled must be seen to
  put its release's end outside;
- a phone's width has no horizontal page scroll.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/mseg/checks/popover_checks.py
"""
import os, sys, math
from playwright.sync_api import sync_playwright

PAGE = "file://" + os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "popover.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
fails = []

def check(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)

# What a small block holds beyond its curve and fill.
EXTRAS = """() => Array.from(document.querySelectorAll('svg.pv, svg.pvf')).map((s) => ({
    text: s.querySelectorAll('text').length, circles: Array.from(s.querySelectorAll('circle')).filter((c) => !c.hasAttribute('data-now')).length,
    lines: s.querySelectorAll('line').length, now: s.querySelectorAll('[data-now]').length }))"""

# Handles of the panel's envelope drawings outside their own drawing's width.
INSIDE = """() => { let out = 0; document.querySelectorAll('#pop svg.plot[data-kind]').forEach((s) => {
    const w = s.clientWidth; s.querySelectorAll('.pt .ring').forEach((c) => { const x = +c.getAttribute('cx'); if (x < 0 || x > w) out++; }); }); return out; }"""

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME if os.path.exists(CHROME) else None)
    page = b.new_page(viewport={"width": 1500, "height": 1100})
    errs = []
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(PAGE)
    page.wait_for_timeout(900)
    chosen = {"take": "beside", "block": "a", "fblock": "box", "level": "lin"}
    state = page.evaluate("""() => { const S = __mseg.S, pressed = {};
        for (const [id, key] of [['pgTake', 'take'], ['pgBlock', 'block'], ['pgFblock', 'fblock'], ['pgLevel', 'level']])
          pressed[key] = (document.querySelector('#' + id + ' [aria-pressed="true"]') || {}).dataset.v;
        return { take: S.take, block: S.block, fblock: S.fblock, level: S.level, pressed }; }""")
    matches = lambda want: all(state[k] == v and state["pressed"][k] == v for k, v in want.items())
    check(matches(chosen), "the page opens on the chosen design %s" % state)
    check(not matches(dict(chosen, take="wide")) and not matches(dict(chosen, fblock="words")), "null: a choice the owner did not make does not match")
    seen_knobs = page.evaluate("document.querySelectorAll('#pop .knobs .kcell').length")
    check(seen_knobs == 6, "the chosen panel opens with its six knobs showing (%s)" % seen_knobs)
    for blk in ["a", "b"]:
        page.click('#pgBlock [data-v="%s"]' % blk)
        for fb in ["words", "box"]:
            page.click('#pgFblock [data-v="%s"]' % fb)
            for take in ["beside", "wide"]:
                for size in ["big", "small"]:
                    for edit in ["amp", "filter"]:
                        page.click('#pgTake [data-v="%s"]' % take); page.click('#pgSize [data-v="%s"]' % size); page.click('#pgEdit [data-v="%s"]' % edit)
                        out = page.evaluate(INSIDE)
                        check(out == 0, "block %s, filter %s, take %s %s %s: every handle inside its drawing (%s out)" % (blk, fb, take, size, edit, out))
            for m in page.evaluate("__mseg.survey(), window.__survey"):
                name = "block %s, filter %s, take %s %s %s" % (blk, fb, m["take"], m["size"], m["label"])
                q = m["pop"]
                check(m["over"] <= 1 and q["over"] <= 1, name + ": Play and the panel fit (%s, %s px over)" % (m["over"], q["over"]))
                check(not q["coversBlock"] and not q["coversBand"] and q["inside"], name + ": the panel is clear of its block and the band")
                groups = 1 if m["edit"] == "amp" else 2
                check(len(q["knobRows"]) == groups and all(r == 1 for r in q["knobRows"]), name + ": knobs always shown, %d group(s) in one row each %s" % (groups, q["knobRows"]))
            ex = page.evaluate(EXTRAS)
            check(all(x["text"] == 0 and x["circles"] == 0 and x["lines"] <= 1 for x in ex), "block %s, filter %s: the small blocks hold the shape only %s" % (blk, fb, ex))
    page.evaluate("__mseg.noteDown()"); page.wait_for_timeout(150)
    ex = page.evaluate(EXTRAS)
    check(any(x["now"] == 1 for x in ex) and all(x["text"] == 0 for x in ex), "while a note sounds, a gold dot and still no words")
    page.evaluate("__mseg.noteUp()"); page.wait_for_timeout(500)
    # Null for the blocks: a word put on one is seen.
    seen = page.evaluate("""() => { const s = document.querySelector('svg.pv'); const t = document.createElementNS('http://www.w3.org/2000/svg', 'text'); t.textContent = 'A'; s.appendChild(t);
        const n = s.querySelectorAll('text').length; t.remove(); return n; }""")
    check(seen == 1, "null: a word added to a small block is seen")
    # Null for the knob rows: squeezed, they wrap.
    page.click('#pgTake [data-v="wide"]'); page.click('#pgEdit [data-v="amp"]')
    rows = page.evaluate("""() => { const k = document.querySelector('#pop .knobs'); k.style.flexWrap = 'wrap'; k.style.width = '150px';
        const n = new Set(Array.from(k.querySelectorAll('.kcell')).map((c) => Math.round(c.getBoundingClientRect().top))).size; k.style.width = ''; k.style.flexWrap = ''; return n; }""")
    check(rows > 1, "null: knobs squeezed into 150 px are seen in %s rows" % rows)
    gone = page.evaluate("""() => { const ks = Array.from(document.querySelectorAll('#pop .knobs')); const keep = ks.map((k) => [k, k.parentNode, k.nextSibling]);
        ks.forEach((k) => k.remove()); const n = __mseg.measureNow().pop.knobRows.length; keep.forEach(([k, p, nx]) => p.insertBefore(k, nx)); return n; }""")
    check(gone == 0, "null: a panel with its knobs taken out is seen to have %s groups" % gone)
    page.click('#pgTake [data-v="beside"]'); page.click('#pgEdit [data-v="amp"]')
    out = page.evaluate("() => { const s = document.querySelector('#pop svg.plot[data-kind=\"amp\"]'); const g = s._g; g.ui.view.k *= 2; drawSoft('amp', s); return (" + INSIDE + ")(); }")
    check(out > 0, "null: a drawing at twice its fitted scale is seen with %s handle(s) outside" % out)
    # The level axis.
    for level in ["lin", "db"]:
        page.click('#pgLevel [data-v="%s"]' % level); page.click('#pgTake [data-v="beside"]'); page.click('#pgEdit [data-v="amp"]')
        r = page.evaluate("""() => { const svg = document.querySelector('svg.plot[data-kind="amp"]'), g = svg._g, e = __mseg.S.amp[0];
            const i = flatten(e).pre.findIndex((p) => p.role === 'decay'); const c = svg.querySelector('[data-pt="pre' + i + '"] .ring');
            return { y: +c.getAttribute('cy'), T: g.T, B: g.B, sus: e.m.sus }; }""")
        lin = r["T"] + (1 - r["sus"]) * (r["B"] - r["T"])
        db = r["T"] + (20 * math.log10(r["sus"]) / -48) * (r["B"] - r["T"])
        want, other = (lin, db) if level == "lin" else (db, lin)
        check(abs(r["y"] - want) < 0.5, "level %s: the sustain point at %.2f, required %.2f" % (level, r["y"], want))
        check(abs(r["y"] - other) > 5, "null, level %s: the other law would put it at %.2f, %.1f px away" % (level, other, abs(r["y"] - other)))
    page.set_viewport_size({"width": 390, "height": 800}); page.wait_for_timeout(200)
    sw = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
    check(sw[0] <= sw[1], "phone width: no horizontal scroll (%s within %s)" % tuple(sw))
    check(not errs, "no console errors %s" % errs[:3])
    b.close()
print("%d failed" % len(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
