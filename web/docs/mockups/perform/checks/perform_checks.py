"""The Perform mockup's checks, in Chromium (web/docs/mockups/perform/index.html).

Each check has a known-wrong case beside it (a null), which must be seen to fail. Where it can be,
the null is testing itself, web/scope.html loaded at the same window.

- in the brand's webfonts, no console errors;
- every id testing's panel has is here once, with its tag, type, range and option values, and the
  clock's spans keep theirs. Null: the mockup with Step taken out;
- every menu, switch and knob has a name you can see, three words or fewer, on one line. Null:
  testing's Step and Octaves menus, which have none;
- the clock reads as a sentence, "Internal · bar 5, beat 4 · Stopped", and the button says what it
  will do. Null: testing's clock, "From internal Bar STOP 1.1";
- knobs where the face has knobs: Glide and Tempo are knobs over their range inputs; the one
  slider is the morph's crossfader, which CLAUDE.md keeps. Null: testing's three sliders;
- the arpeggiator's drawing plays what the pattern says, step by step: up rising, down falling,
  up and down turning at the ends, as played in the order played, the step count the rate's,
  the range the octaves'. Nulls: up's order read as down; 1/8's eight steps at 1/16;
- no scroll, at the six windows: the panel holds its content, is inside the window, opens where
  testing's does and ends above the Picture strip;
- nothing moves: every box in the panel to half a pixel (the clock line's words aside, which are
  read, not pressed) across every pattern, step and octave, the clock stopped and running at bar
  1 and bar 128, Quantise on and off, Glide and Tempo at their ends, the morph at both ends and the
  longest scale, at the six windows. Null: the button on the clock line, after the words, moves
  when the bar count grows;
- a phone's width has no horizontal page scroll.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/perform/checks/perform_checks.py
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
CLOCK = re.compile(r"^(Internal|Host) · bar \d+, beat [1-4] · (Running|Stopped)$")
STATES = [{}]
for m in ["up", "down", "updown", "played", "random"]:
    STATES.append({"arpMode": m})
for r in ["1/4", "1/16", "1/8t", "1/16t"]:
    STATES.append({"arpMode": "up", "arpRate": r, "arpOctaves": "3"})
STATES += [{"running": True, "bar": 1, "beat": 1}, {"running": True, "bar": 128, "beat": 4}, {"from": "Host", "bar": 64},
           {"quantise": True, "quantiseGlide": 300}, {"tempo": 30}, {"tempo": 300}, {"morphPos": 100}, {"keyRoot": "10", "keyScale": "harmonic"}]

ID_CHECK = r"""() => {
  const bad = [];
  for (const a of UI_DATA.attrs.perform) {
    const all = document.querySelectorAll('#' + CSS.escape(a.id));
    if (all.length !== 1) { bad.push(a.id + ' x' + all.length); continue; }
    const e = all[0];
    if (e.tagName.toLowerCase() !== a.tag || (e.type || '') !== a.type) { bad.push(a.id + ' type'); continue; }
    if (a.type === 'range' && (e.min !== a.min || e.max !== a.max)) bad.push(a.id + ' range');
    if (a.options && JSON.stringify([...e.options].map(o => o.value)) !== JSON.stringify(a.options.map(o => o[0]))) bad.push(a.id + ' options');
  }
  for (const id of ['clockFrom', 'transportAt']) if (document.querySelectorAll('#' + id).length !== 1) bad.push(id);
  return bad; }"""

LABELS = r"""() => {
  const p = document.getElementById('performPanel'), out = [];
  for (const c of p.querySelectorAll('select, input, .switch')) {
    if (c.closest('.sr') && !c.closest('.kcell')) continue;
    let name = null;
    const f = c.closest('.fld'), k = c.closest('.kcell'), t = c.closest('.tog');
    if (f) name = f.querySelector('.fl'); else if (k) name = k.querySelector('.nm'); else if (t) name = t;
    else if (c.id === 'morphPos') name = p.querySelector('#morphGroup .sec');
    out.push({ id: c.id, name: name && name.offsetParent ? name.textContent.trim() : null, lines: name ? name.getClientRects().length : 0 });
  }
  return { out, over: UI.overflows(p) }; }"""

FIT = r"""() => {
  const p = document.getElementById('performPanel'), z = UI.SIZES[__m.S.size], b = UI.boxes(document.getElementById('win')).performPanel;
  return { scroll: p.scrollHeight - p.clientHeight, inWin: b[0] >= 0 && b[1] >= 0 && b[0] + b[2] <= z.w && b[1] + b[3] <= z.h, bottom: b[1] + b[3], picT: z.picT, box: b }; }"""

BOXES = r"""() => { const b = UI.boxes(document.getElementById('performPanel'));
  for (const k of ['clockFrom', 'transportAt', 'transportState', 'clockLine', 'arpCap', 'morphPosValue', 'arpSvg']) delete b[k];
  for (const k of Object.keys(b)) if (/Value$/.test(k)) delete b[k];
  return b; }"""

def diff(a, b):
    return sorted(k for k in set(a) | set(b) if k not in a or k not in b or any(abs(x - y) > 0.5 for x, y in zip(a[k], b[k])))

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

        # testing, for the nulls
        rctx = br.new_context(viewport={"width": 1400, "height": 900}); webfonts.route(rctx)
        rp = rctx.new_page(); rp.goto(REAL); rp.wait_for_timeout(900); webfonts.settle(rp)
        if rp.locator("#helpClose").is_visible(): rp.locator("#helpClose").click()
        rp.evaluate("() => showControl('arpMode')"); rp.wait_for_timeout(300)
        real = rp.evaluate("""() => {
          const named = (id) => { const e = document.getElementById(id); return [...document.querySelectorAll('label')].some(l => l.htmlFor === id && l.offsetParent) || !!(e.closest('label') && e.closest('label').offsetParent); };
          return { rate: named('arpRate'), octaves: named('arpOctaves'), clock: document.getElementById('clockGroup').innerText.replace(/\\s+/g, ' ').trim(),
                   sliders: [...document.querySelectorAll('#performPanel input[type=range]')].filter(r => r.offsetWidth > 2).length }; }""")
        rctx.close()
        results["testing"] = real

        bad = p.evaluate(ID_CHECK)
        check(not bad, "every id on testing's panel is here once, with its tag, type, range and option values (%d ids, and the clock's two spans)" % len(p.evaluate("UI_DATA.attrs.perform")) + (": " + str(bad) if bad else ""))
        p.evaluate("() => document.getElementById('arpRate').remove()")
        null(not p.evaluate(ID_CHECK), "the mockup with Step taken out")
        p.evaluate("() => __m.render()")

        lb = p.evaluate(LABELS)
        unnamed = [x["id"] for x in lb["out"] if not x["name"]]
        long = [x["name"] for x in lb["out"] if x["name"] and len(x["name"].split()) > 3]
        check(not unnamed and not long and not lb["over"], "every menu, switch and knob named where it can be seen, three words or fewer, one line (%s)" % ", ".join(sorted({x["name"] for x in lb["out"] if x["name"]})) + (": " + str(unnamed + long + lb["over"]) if unnamed or long or lb["over"] else ""))
        null(real["rate"] and real["octaves"], "testing's Step and Octaves menus have a name you can see")

        for st in [{}, {"running": True, "bar": 128, "beat": 1}, {"from": "Host", "bar": 1, "beat": 1}]:
            p.evaluate("(o) => __m.set(o)", st)
            line = p.evaluate("() => document.getElementById('clockLine').textContent.replace(/\\s+/g, ' ').trim()")
            btn = p.evaluate("() => document.getElementById('transportPlay').textContent")
            check(bool(CLOCK.match(line)) and btn == ("Stop" if st.get("running") else "Start"), "the clock reads '%s', the button '%s'" % (line, btn))
        null(bool(CLOCK.match(real["clock"])), "testing's clock, '%s'" % real["clock"])

        k = p.evaluate("""() => { const p = document.getElementById('performPanel');
          const sl = [...p.querySelectorAll('input[type=range]')].filter(r => r.offsetWidth > 2).map(r => r.id);
          const kn = [...p.querySelectorAll('.kcell .knob-face')].map(f => f.closest('.kcell').dataset.knob); return { sl, kn }; }""")
        check(k["sl"] == ["morphPos"] and sorted(k["kn"]) == ["quantiseGlide", "tempo"], "Glide and Tempo are knobs; the one slider is the morph's crossfader (%s)" % k)
        null(real["sliders"] <= 1, "testing's panel has %d sliders" % real["sliders"])

        # the arpeggiator's drawing
        def seq(o):
            p.evaluate("(o) => __m.set(o)", o)
            return p.evaluate("() => JSON.parse(document.getElementById('arpSvg').dataset.seq)")
        up = seq({"arpMode": "up", "arpOctaves": "2", "arpRate": "1/8"})
        down = seq({"arpMode": "down", "arpOctaves": "2", "arpRate": "1/8"})
        ud = seq({"arpMode": "updown", "arpOctaves": "1", "arpRate": "1/16"})
        pl = seq({"arpMode": "played", "arpOctaves": "1", "arpRate": "1/4"})
        r16 = seq({"arpMode": "up", "arpOctaves": "3", "arpRate": "1/16"})
        r8t = seq({"arpMode": "up", "arpOctaves": "1", "arpRate": "1/8t"})
        rising = lambda s: all(b > a for a, b in zip(s, s[1:]) if b != s[0]) and s[:6] == sorted(s[:6])
        check(up[:6] == [60, 64, 67, 72, 76, 79] and len(up) == 8, "up over 2 octaves at 1/8: %s" % up)
        check(down[:6] == [79, 76, 72, 67, 64, 60], "down: %s" % down)
        null(down[:6] == sorted(down[:6]), "down's order read as up's")
        check(ud[:8] == [60, 64, 67, 64, 60, 64, 67, 64] and len(ud) == 16, "up and down turns at the ends without repeating them, 16 steps at 1/16: %s" % ud[:8])
        check(pl == [64, 60, 67, 64], "as played, in the order played (E, C, G), 4 steps at 1/4: %s" % pl)
        check(len(r16) == 16 and max(r16) == 79 + 12 and min(r16) == 60 and len(r8t) == 12, "the steps are the rate's (16 at 1/16, 12 at 1/8t) and the range the octaves' (C4 to G6 at 3)")
        null(len(seq({"arpMode": "up", "arpOctaves": "1", "arpRate": "1/16"})) == 8, "1/8's eight steps at 1/16")
        results["arp"] = {"up": up, "down": down, "updown": ud, "played": pl}

        results["sizes"] = {}
        for size in SIZES:
            p.evaluate("(s) => { __m.S.size = s; __m.render(); }", size)
            base, moved, fitbad = None, set(), []
            for st in STATES:
                p.evaluate("(o) => __m.set(o)", st)
                f = p.evaluate(FIT)
                want = {"1660x1050": [646, 58], "1400x900": [516, 58], "1100x860": [326, 58], "1200x680": [420, 45], "1100x680": [330, 45], "960x600": [297, 44]}[size]
                if f["scroll"] > 0 or not f["inWin"] or f["bottom"] > f["picT"] or abs(f["box"][0] - want[0]) > 1 or abs(f["box"][1] - want[1]) > 1:
                    fitbad.append((st, f))
                bx = p.evaluate(BOXES)
                base = base or bx
                moved |= set(diff(base, bx))
            f = p.evaluate(FIT)
            results["sizes"][size] = {"box": f["box"], "bottom": f["bottom"], "picT": f["picT"], "moved": sorted(moved)}
            check(not fitbad, "%s: no scroll in %d states; where testing's opens, %d x %d, ending at %d above the strip at %d" % (size, len(STATES), f["box"][2], f["box"][3], f["bottom"], f["picT"]) + (": " + str(fitbad[:2]) if fitbad else ""))
            check(not moved, "%s: nothing in the panel moves across %d states" % (size, len(STATES)) + (": " + str(sorted(moved)[:8]) if moved else ""))

        # the shift null: the button on the clock line, after the words
        p.evaluate("() => { __m.S.size = '1400x900'; __m.render(); document.getElementById('clockLine').appendChild(document.getElementById('transportPlay')); __m.set({ bar: 1 }); }")
        a = p.evaluate(BOXES)
        p.evaluate("() => __m.set({ bar: 128 })")
        b = p.evaluate(BOXES)
        null(not diff(a, b), "the button on the clock line, after the words, bar 1 then bar 128 (moved: %s)" % diff(a, b)[:3])

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
