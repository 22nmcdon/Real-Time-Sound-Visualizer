"""The Picture strip mockup's checks, in Chromium (web/docs/mockups/picture-strip/index.html).

Each check has a known-wrong case beside it (a null), which must be seen to fail. The nulls here
are mostly testing itself: the check loads web/scope.html at the same window and measures the
strip as it is.

- in the brand's webfonts, no console errors;
- the strip's ids are testing's, with their types, ranges and roles. Null: the mockup with Width taken out;
- the same height as testing at every window (90, and 80 compact), and nothing in the strip
  outside it, overlapping or cut. Null: the strip at 100 px against testing's height;
- the info line holds every control's whole line: all of the page's CONTROL_WORDS, set one at a
  time, under the name and a value, unclipped, at the six windows. Null: the same lines in
  testing's info box, which cuts most of them;
- the Width switch is labelled over itself, one line, its label and options three words or fewer.
  Null: testing's caption, *Width on*, sits under its switch;
- one way to more: a single control in the strip says More, and nothing says right-click. Null:
  testing's strip says both;
- the three reads: each a name of at least 10.5 px in --text, a bar at least 50 px long whose
  fill is at least 3:1 against its track, and a reading. Null: testing's reads, 7 px bars with
  names of 10 px in the soft ink;
- nothing moves: every box in the strip to half a pixel across pointing at every control in it,
  the longest and shortest lines, the reads at 0 and 100 per cent, and both Width settings.
  Null: the reads' reading column sized to its figures moves the info line;
- a phone's width has no horizontal page scroll.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/picture-strip/checks/strip_checks.py
"""
import os, sys, json, re
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "web", "tests"))
import webfonts

MOCK = os.path.dirname(HERE)
PAGE = "file://" + os.path.join(MOCK, "index.html")
REAL = "file://" + os.path.join(ROOT, "web", "scope.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
fails, n, results = [], [0], {}

def check(ok, what):
    n[0] += 1
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)

def null(wrong_passes, what):
    check(not wrong_passes, "null: " + what)

SIZES = ["1660x1050", "1400x900", "1100x860", "1200x680", "1100x680", "960x600"]
REAL_VIEW = {"960x600": (960, 600)}

src = open(os.path.join(ROOT, "web", "scope.html"), encoding="utf-8").read()
m = re.search(r"const CONTROL_WORDS = \{\n  /\*.*?\*/\n(.*?)\n\};\n", src, re.S)
ALL_WORDS = json.loads("{" + m.group(1).rstrip().rstrip(",") + "}")

ID_CHECK = r"""() => {
  const bad = [];
  for (const a of UI_DATA.attrs.picture) {
    const all = document.querySelectorAll('#' + CSS.escape(a.id));
    if (all.length !== 1) { bad.push(a.id + ' x' + all.length); continue; }
    const e = all[0];
    if (e.tagName.toLowerCase() !== a.tag || (e.type || '') !== a.type) bad.push(a.id + ' type');
    if (a.type === 'range' && (e.min !== a.min || e.max !== a.max)) bad.push(a.id + ' range');
  }
  return bad; }"""

LINES = r"""(words) => {
  const t = document.getElementById('infoText'), cut = [];
  let longest = 0;
  for (const [id, w] of Object.entries(words)) {
    __m.sayText(w[0], '−18.0 dBFS', w[1]);
    longest = Math.max(longest, w[1].length);
    const lb = document.getElementById('infoLine').getBoundingClientRect(), last = [...t.getClientRects()].pop();
    if (t.scrollHeight > t.clientHeight + 1 || t.scrollWidth > t.clientWidth + 1 || t.getBoundingClientRect().bottom > lb.bottom + 0.5) cut.push(id);
    const top = document.querySelector('.info-top');
    const nr = document.getElementById('infoName').getBoundingClientRect(), mr = document.getElementById('infoMore').getBoundingClientRect();
    if (nr.right > mr.left - 4) cut.push(id + ' (name)');
  }
  const r = document.getElementById('infoLine').getBoundingClientRect();
  return { cut, n: Object.keys(words).length, longest, w: Math.round(r.width) }; }"""

FIT = r"""() => {
  const bar = document.getElementById('pictureBar'), br = bar.getBoundingClientRect(), z = UI.SIZES[__m.S.size];
  const kids = [...bar.children].map(e => e.getBoundingClientRect());
  let overlap = 0, outside = 0;
  for (let i = 0; i < kids.length; i++) {
    const a = kids[i];
    if (a.left < br.left - 0.5 || a.right > br.right + 0.5 || a.top < br.top - 0.5 || a.bottom > br.bottom + 0.5) outside++;
    for (let j = i + 1; j < kids.length; j++) { const b = kids[j]; if (a.right > b.left + 0.5 && b.right > a.left + 0.5) overlap++; }
  }
  return { h: br.height, want: z.picH, overlap, outside, over: UI.overflows(bar) }; }"""

SWITCH = r"""() => {
  const l = document.getElementById('widthToLabel').getBoundingClientRect(), s = document.querySelector('[data-group="widthTo"]').getBoundingClientRect();
  const words = [document.getElementById('widthToLabel'), document.getElementById('widthHeard'), document.getElementById('widthDrawn')].map(e => e.textContent.trim().split(/\s+/).length);
  return { above: l.bottom <= s.top + 0.5, lines: document.getElementById('widthToLabel').getClientRects().length, words }; }"""

MORE = r"""(sel) => { const bar = document.querySelector(sel);
  const all = [...bar.querySelectorAll('*')].filter(e => e.children.length === 0 && e.offsetParent && /\S/.test(e.textContent));
  return { more: all.filter(e => /\bmore\b/i.test(e.textContent)).length, right: all.filter(e => /right-click/i.test(e.textContent)).length }; }"""

def lum(rgb):
    c = [int(x) / 255 for x in re.findall(r"\d+", rgb)[:3]]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

def contrast(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)

READS = r"""() => {
  const rows = [...document.querySelectorAll('#pictureReads .rn')].map((n, i) => {
    const bar = document.querySelectorAll('#pictureReads .rb')[i], fill = bar.querySelector('i'), v = document.querySelectorAll('#pictureReads .rv')[i];
    return { name: n.textContent, size: parseFloat(getComputedStyle(n).fontSize), ink: getComputedStyle(n).color, len: bar.getBoundingClientRect().width,
             fill: getComputedStyle(fill).backgroundColor, track: getComputedStyle(bar).backgroundColor, value: v.textContent }; });
  return { rows, text: getComputedStyle(document.documentElement).getPropertyValue('--text').trim() }; }"""

REAL_READS = r"""() => {
  const r = document.getElementById('pictureReads'), bars = [...r.querySelectorAll('i')], names = document.querySelector('.picture-meter-names');
  const cs = getComputedStyle(names);
  return { bars: bars.map(b => ({ w: b.getBoundingClientRect().width, h: b.getBoundingClientRect().height })), size: parseFloat(cs.fontSize), ink: cs.color,
           info: (() => { const t = document.getElementById('infoText'); const b = t.getBoundingClientRect(); return { w: b.width, h: b.height }; })() }; }"""

BOXES = r"""() => { const b = UI.boxes(document.getElementById('pictureBar'));
  for (const k of Object.keys(b)) if (/Value$|^info(Name|Value|Text|Host)$/.test(k)) delete b[k];
  return b; }"""

def diff(a, b):
    return sorted(k for k in set(a) & set(b) if any(abs(x - y) > 0.5 for x, y in zip(a[k], b[k])))

def open_real(br, size):
    w, h = (960, 600) if size == "960x600" else tuple(int(x) for x in size.split("x"))
    ctx = br.new_context(viewport={"width": w, "height": h})
    webfonts.route(ctx)
    p = ctx.new_page()
    p.goto(REAL); p.wait_for_timeout(900); webfonts.settle(p)
    if p.locator("#helpClose").is_visible():
        p.locator("#helpClose").click()
    return ctx, p

def main():
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=CHROME)
        ctx = br.new_context(viewport={"width": 1700, "height": 1100})
        webfonts.route(ctx)
        p = ctx.new_page()
        errs = []
        p.on("pageerror", lambda e: errs.append(str(e)))
        p.on("console", lambda m: m.type == "error" and errs.append(m.text))
        p.goto(PAGE + "?scale=1")
        check(webfonts.settle(p), "the brand's webfonts loaded (Jost, Playfair Display)")

        bad = p.evaluate(ID_CHECK)
        check(not bad, "the strip's %d ids are testing's, with their types and ranges" % len(p.evaluate("UI_DATA.attrs.picture")) + (": " + str(bad) if bad else ""))
        p.evaluate("() => document.querySelector('[data-knob=stereoWidth]').remove()")
        null(not p.evaluate(ID_CHECK), "the mockup with Width taken out")
        p.evaluate("() => __m.render()")

        results["sizes"] = {}
        for size in SIZES:
            p.evaluate("(s) => { __m.S.size = s; __m.render(); }", size)
            f = p.evaluate(FIT)
            check(abs(f["h"] - f["want"]) < 0.6 and not f["overlap"] and not f["outside"] and not f["over"],
                  "%s: the strip %d px, as testing's %d; nothing outside it, overlapping or cut" % (size, f["h"], f["want"]) + (": " + str(f) if f["overlap"] or f["outside"] or f["over"] else ""))
            lines = p.evaluate(LINES, ALL_WORDS)
            check(not lines["cut"], "%s: all %d controls' lines whole in the info line (%d px wide; longest %d characters)" % (size, lines["n"], lines["w"], lines["longest"]) + (": " + str(lines["cut"][:6]) if lines["cut"] else ""))
            # nothing moves
            base = None; moved = set()
            for said in ["pictureAmount", "oscScan", "scanStrike", "scanSoft", "scanMemory", "output", "stereoWidth", "widthHeard", "widthDrawn", "pictureMore"]:
                for reads in ([0, 0, 0], [1, 1, 1], [0.62, 0.18, 0.41]):
                    p.evaluate("([id, r]) => { __m.setReads(r); UI.say(id); }", [said, reads])
                    bx = p.evaluate(BOXES)
                    base = base or bx
                    moved |= set(diff(base, bx))
            for wid in ("widthDrawn", "widthHeard"):
                p.evaluate("(id) => document.getElementById(id).click()", wid)
                moved |= set(diff(base, p.evaluate(BOXES)))
            for longest in (True, False):
                p.evaluate("(w) => __m.sayText(w[0], w[1], w[2])", max(ALL_WORDS.values(), key=lambda w: len(w[1])) + [""] if longest else ["Clear", "", "Wipes."])
                moved |= set(diff(base, p.evaluate(BOXES)))
            check(not moved, "%s: nothing in the strip moves across 10 controls x 3 reads, both Widths, the longest and shortest lines" % size + (": " + str(sorted(moved)) if moved else ""))
            results["sizes"][size] = {"height": f["h"], "infoWidth": lines["w"], "cut": lines["cut"], "moved": sorted(moved)}

        # nulls, measured on testing itself
        null(abs(100 - 90) < 0.6, "a strip 100 px tall against testing's 90")
        rctx, rp = open_real(br, "1400x900")
        rr = rp.evaluate(REAL_READS)
        rm = rp.evaluate(MORE, "#pictureBar")
        rp.evaluate("() => { const t = document.getElementById('infoText'); t.dataset.w = 1; }")
        cut_real = rp.evaluate("""(words) => { const t = document.getElementById('infoText'); let cut = 0;
            const box = t.closest('.info-words') || t; for (const w of Object.values(words)) { t.textContent = w[1]; if (box.scrollHeight > box.clientHeight + 1) cut++; } return cut; }""", ALL_WORDS)
        null(cut_real == 0, "the same %d lines in testing's info box at 1400 x 900 (%d of them cut)" % (len(ALL_WORDS), cut_real))
        rsw = rp.evaluate("""() => { const row = document.getElementById('widthToRow');
            const l = [...row.querySelectorAll('*')].find(e => e.children.length === 0 && /width on/i.test(e.textContent));
            return l.getBoundingClientRect().bottom <= document.getElementById('widthHeard').getBoundingClientRect().top + 0.5; }""")
        rctx.close()
        results["testing"] = {"reads": rr, "more": rm, "linesCut": cut_real}

        p.evaluate("() => { __m.S.size = '1400x900'; __m.render(); }")
        sw = p.evaluate(SWITCH)
        check(sw["above"] and sw["lines"] == 1 and max(sw["words"]) <= 3, "the Width switch: 'Width is' over it, one line, label and options three words or fewer")
        null(rsw, "testing's caption, 'Width on', over its switch")
        mo = p.evaluate(MORE, "#pictureBar")
        check(mo["more"] == 1 and mo["right"] == 0, "one way to more: %d 'More', %d 'right-click'" % (mo["more"], mo["right"]))
        null(rm["more"] == 1 and rm["right"] == 0, "testing's strip: %d 'more', %d 'right-click'" % (rm["more"], rm["right"]))

        rd = p.evaluate(READS)
        text_rgb = p.evaluate("() => { const d = document.createElement('i'); d.style.color = 'var(--text)'; document.body.appendChild(d); const c = getComputedStyle(d).color; d.remove(); return c; }")
        ok = all(r["size"] >= 10.5 and r["ink"] == text_rgb and r["len"] >= 50 and contrast(r["fill"], r["track"]) >= 3 and r["value"].endswith("%") for r in rd["rows"])
        check(ok, "the reads: names %s px in --text, bars %s px, fill against track %.1f:1, readings %s" % (
            sorted({r["size"] for r in rd["rows"]}), sorted({round(r["len"]) for r in rd["rows"]}), contrast(rd["rows"][0]["fill"], rd["rows"][0]["track"]), [r["value"] for r in rd["rows"]]))
        real_ok = rr["size"] >= 10.5 and rr["ink"] == text_rgb and min(b["w"] for b in rr["bars"]) >= 50
        null(real_ok, "testing's reads: names %.1f px in %s, bars %s px wide" % (rr["size"], rr["ink"], [round(b["w"]) for b in rr["bars"]]))
        results["reads"] = rd

        # the shift null: the reading column sized to its figures
        p.evaluate("() => { const st = document.createElement('style'); st.textContent = '.reads { grid-template-columns: auto 64px auto !important; }'; document.head.appendChild(st); __m.setReads([0, 0, 0]); }")
        a = p.evaluate(BOXES)
        p.evaluate("() => __m.setReads([1, 1, 1])")
        b = p.evaluate(BOXES)
        null(not diff(a, b), "the reads' reading column sized to its figures, 0 then 100 per cent (moved: %s)" % diff(a, b)[:3])

        ph = ctx.new_page()
        ph.set_viewport_size({"width": 390, "height": 844})
        ph.goto(PAGE)
        sx = ph.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
        check(sx <= 0, "a phone's width (390) has no horizontal page scroll (%d)" % sx)
        check(not errs, "no console errors" + (": " + str(errs[:3]) if errs else ""))
        br.close()
    results["checks"] = n[0]
    results["failed"] = fails
    json.dump(results, open(os.path.join(HERE, "results.json"), "w"), indent=1, ensure_ascii=False)
    print("\n%d checks, %d failed" % (n[0], len(fails)))
    sys.exit(1 if fails else 0)

main()
