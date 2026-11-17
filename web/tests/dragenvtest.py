"""The envelopes taken hold of (17 Nov): the amp envelope's curve on Play, the
voice filter's opened from its heading, and the Envelope card's in its
editor, each drawn by the fade's drawing (envelopeDrawing) with three
handles that write the knobs under it; and the Envelope following the amp
envelope until it is edited.

What would go wrong, and what is checked for it:

- a handle that writes the wrong knob, or the right one by the wrong amount:
  the peak dragged with the mouse must move the attack, and only it, to what
  the drawing's square-root scale says for where the pointer let go; the
  corner the decay and the sustain, and not the attack or the release. The
  nulls: the knob it was before, and a straight scale's answer for the same
  place, are both not what it reads;
- a drag that is many undo steps, or none: one step for a drag, taken once
  the pointer lifts, and undo putting the value back; the null is the count
  with the pointer still held, which is no step yet;
- a handle off its curve: every handle's centre on the path drawn for its
  stretch, within half a pixel, on all three drawings and after a drag, and
  under the pointer that let it go. The null: the same measure of a point
  four pixels off the curve finds it;
- the keyboard: Tab reaches a handle, the arrows move it, Shift finer but
  still moving; an arrow that means nothing on a handle (up on the peak)
  moves nothing;
- the menu: right-click, and Shift+F10 on a focused handle, open the
  handle's menu with Type a value, Reset naming where the knobs start, and
  What is this?; Copy to the other hand where the section is a hand's own and
  not where it is linked; typing and Reset write the knobs; two presses put
  them back;
- the hands: a drag while the upper hand of an unlinked split is edited
  writes the upper hand's field and not the lower's;
- following: the Envelope's knobs, readings and drawing show the amp's four
  and are live. The null is the knob as it was until 17 Nov, disabled, which
  a drag does not turn;
- an edit while following: the knob dragged, a handle dragged, an arrow and a
  typed value each copy the amp's four into its own, apply the edit on top
  and set menvOwn, in the generator too, as one step of undo, which puts it
  back to following with its old four. The null: setControl, which is no
  hand, writes the value without making it its own;
- following again: Reset on a knob, two presses on a handle, and Follow;
- the voice filter's drawing: opened from its heading, over its section and
  in the window, the knobs under it in sight; Esc shuts a menu over it before
  it; a press elsewhere shuts it; at all five windows Play does not scroll
  with it open, with the filter on and two hands.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    """A check's null: the same comparison fed a value it must reject."""
    check("null: " + name, red, detail)

def open_page(b, w=1400, h=900):
    p = b.new_page(viewport={"width": w, "height": h})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(900)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(200)
    return p, bad

def centre(p, sel):
    box = p.locator(sel).bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

def drag(p, sel, dx, dy, hold=None):
    x, y = centre(p, sel)
    p.mouse.move(x, y); p.mouse.down()
    p.mouse.move(x + dx / 2, y + dy / 2, steps=4); p.mouse.move(x + dx, y + dy, steps=4)
    held = hold() if hold else None
    p.mouse.up()
    return (x + dx, y + dy), held

# How far a handle's centre is from the polyline its stretch is drawn as, in
# the drawing's own units (CSS pixels for the knobs' drawings).
OFF_CURVE = """([svgId, name, shift]) => {
  const svg = document.getElementById(svgId), h = svg.querySelector('[data-handle="' + name + '"]');
  const x = +h.getAttribute('cx'), y = +h.getAttribute('cy') + (shift || 0);
  let best = Infinity;
  for (const part of ['attack', 'decay', 'holdLine', 'release']) {
    const d = svg.querySelectorAll('.env-line')[['waitLine', 'attack', 'decay', 'holdLine', 'release'].indexOf(part)].getAttribute('d');
    if (!d) continue;
    let pts;
    if (d.includes('H')) {
      const m = /M([\\d.\\-]+),([\\d.\\-]+)H([\\d.\\-]+)/.exec(d);
      pts = [[+m[1], +m[2]], [+m[3], +m[2]]];
    } else pts = d.slice(1).split('L').map((q) => q.split(',').map(Number));
    for (let i = 0; i + 1 < pts.length; i++) {
      const [x0, y0] = pts[i], [x1, y1] = pts[i + 1], dx = x1 - x0, dy = y1 - y0;
      const t = dx || dy ? Math.max(0, Math.min(1, ((x - x0) * dx + (y - y0) * dy) / (dx * dx + dy * dy))) : 0;
      best = Math.min(best, Math.hypot(x - (x0 + t * dx), y - (y0 + t * dy)));
    }
  }
  return best;
}"""

AMP = "() => [el.envAttack.value, el.envDecay.value, el.envSustain.value, el.envRelease.value].map(Number)"
UNDO = "() => undoHistory.undo.length"

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p, bad = open_page(b)

    print("\n--- a handle writes its knob, by the drawing's scale ---")
    p.evaluate("() => { restore(BASE_SETUP); for (const [id, v] of [['envAttack', 20], ['envDecay', 200], ['envSustain', 60], ['envRelease', 400]]) setControl(id, v); }")
    p.wait_for_timeout(600)
    before, u0 = p.evaluate(AMP), p.evaluate(UNDO)
    (px, py), held = drag(p, '#ampEnvCurve [data-handle="peak"]', 30, 0, hold=lambda: p.evaluate(UNDO))
    p.wait_for_timeout(900)
    after, u1 = p.evaluate(AMP), p.evaluate(UNDO)
    # Where the pointer let go, in the drawing's units, and what the scale says for it.
    want = p.evaluate("""([cx]) => {
      const d = envDrawings.amp, f = d.frame, g = d.geo;
      const local = new DOMPoint(cx, 0).matrixTransform(el.ampEnvCurve.getScreenCTM().inverse()).x;
      return { sqrt: Math.round(envSeconds(local - g.waitEnd, 200, f.seg)), straight: Math.round(200 * (local - g.waitEnd) / f.seg) };
    }""", [px])
    print("    %s -> %s, want %s" % (before, after, want))
    check("the peak dragged moves the attack to the square-root scale's value for where it let go",
          abs(after[0] - want["sqrt"]) <= 1 and after[1:] == before[1:], "%s, want %d" % (after, want["sqrt"]))
    null("the attack it had is not that value", abs(before[0] - want["sqrt"]) > 5, str(before))
    null("nor is a straight scale's", abs(want["straight"] - want["sqrt"]) > 5, str(want))
    check("one step of undo, once the pointer lifts", u1 == u0 + 1, "%d -> %d" % (u0, u1))
    null("with the pointer still down there was no step yet", held == u0, "%s" % held)
    under = p.evaluate("""([x, y]) => { const r = el.ampEnvCurve.querySelector('[data-handle="peak"]').getBoundingClientRect();
      return Math.hypot(r.x + r.width / 2 - x, r.y + r.height / 2 - y); }""", [px, py])
    check("and the handle is under the pointer that let go of it", under < 1.5, "%.2f px" % under)
    p.evaluate("() => undoStep(true)"); p.wait_for_timeout(300)
    check("undo puts the attack back", p.evaluate(AMP) == before, str(p.evaluate(AMP)))

    before = p.evaluate(AMP)
    drag(p, '#ampEnvCurve [data-handle="corner"]', 14, -8)
    p.wait_for_timeout(200)
    after = p.evaluate(AMP)
    check("the corner moves the decay longer and the sustain up, and not the attack or the release",
          after[1] > before[1] and after[2] > before[2] and after[0] == before[0] and after[3] == before[3], "%s -> %s" % (before, after))
    before = p.evaluate(AMP)
    drag(p, '#ampEnvCurve [data-handle="end"]', -10, 0)
    p.wait_for_timeout(200)
    after = p.evaluate(AMP)
    check("the end moves the release shorter, and only it", after[3] < before[3] and after[:3] == before[:3], "%s -> %s" % (before, after))

    print("\n--- on the curve ---")
    p.evaluate("() => { el.vcfType.value = '1'; el.vcfType.dispatchEvent(new Event('change', { bubbles: true })); }")
    p.locator("#vcfEnvOpen").click(); p.wait_for_timeout(200)
    p.evaluate("() => openModCard('env.note')"); p.wait_for_timeout(400)
    offs = {}
    for svg in ("ampEnvCurve", "menvCurve"):
        for h in ("peak", "corner", "end"):
            offs[svg + "." + h] = p.evaluate(OFF_CURVE, [svg, h, 0])
    p.locator("#modEditorClose").click()
    p.wait_for_timeout(200)
    p.locator("#vcfEnvOpen").click(); p.wait_for_timeout(200)
    for h in ("peak", "corner", "end"):
        offs["vcfEnvCurve." + h] = p.evaluate(OFF_CURVE, [ "vcfEnvCurve", h, 0])
    worst = max(offs.values())
    check("every handle on all three drawings sits on its curve, within half a pixel", worst < 0.5,
          ", ".join("%s %.2f" % kv for kv in offs.items()))
    null("a point four pixels off the corner is found off it", p.evaluate(OFF_CURVE, ["ampEnvCurve", "corner", 4]) > 3)

    print("\n--- the keyboard ---")
    p.locator("body").click(position={"x": 5, "y": 890}); p.wait_for_timeout(100)
    p.locator('#ampEnvCurve [data-handle="peak"]').focus()
    a0 = p.evaluate(AMP)[0]
    p.keyboard.press("ArrowRight"); a1 = p.evaluate(AMP)[0]
    p.keyboard.press("Shift+ArrowRight"); a2 = p.evaluate(AMP)[0]
    p.keyboard.press("ArrowUp"); a3 = p.evaluate(AMP)
    check("an arrow moves the peak's attack longer", a1 > a0, "%d -> %d" % (a0, a1))
    check("Shift moves it less, and still moves it", 0 < a2 - a1 < a1 - a0, "%d, %d" % (a1 - a0, a2 - a1))
    null("up on the peak means nothing there, and moves nothing", a3[0] == a2, str(a3))
    p.locator('#ampEnvCurve [data-handle="corner"]').focus()
    s0 = p.evaluate(AMP)[2]
    p.keyboard.press("ArrowUp"); s1 = p.evaluate(AMP)[2]
    p.keyboard.press("Shift+ArrowDown"); s2 = p.evaluate(AMP)[2]
    check("up on the corner raises the sustain a twentieth, Shift and down lowers it a hundredth", s1 == min(100, s0 + 5) and s2 == s1 - 1,
          "%d, %d, %d" % (s0, s1, s2))
    tab = p.evaluate("""() => { const h = el.ampEnvCurve.querySelector('[data-handle]'); return h.tabIndex === 0 && h.getAttribute('role') === 'slider'; }""")
    check("each handle is a stop for Tab, a slider", tab)

    print("\n--- the menu, two presses ---")
    p.evaluate("() => { for (const [id, v] of [['envAttack', 50], ['envDecay', 300]]) setControl(id, v); }"); p.wait_for_timeout(200)
    p.locator('#ampEnvCurve [data-handle="corner"]').click(button="right"); p.wait_for_timeout(250)
    items = p.evaluate("() => overlay ? [...overlay.node.querySelectorAll('.ctx-item')].map((b) => [b.dataset.item, b.textContent]) : null")
    check("right-click on the corner: Type a value, Reset naming the decay's and the sustain's starts, What is this?",
          items is not None and [k for k, _ in items] == ["type", "reset", "what"] and "120 ms" in items[1][1] and "0.70" in items[1][1],
          str(items))
    p.locator('.ctx-item[data-item="reset"]').click(); p.wait_for_timeout(150)
    check("Reset puts both of the corner's knobs back", p.evaluate(AMP)[1:3] == [120, 70], str(p.evaluate(AMP)))
    p.locator('#ampEnvCurve [data-handle="peak"]').focus(); p.keyboard.press("Shift+F10"); p.wait_for_timeout(250)
    opened = p.evaluate("() => !!overlay && overlay.opener === el.ampEnvCurve.querySelector('[data-handle=\"peak\"]')")
    check("Shift+F10 on a focused handle opens its menu", opened)
    p.locator('.ctx-item[data-item="type"]').click(); p.wait_for_timeout(100)
    p.keyboard.press("Control+a"); p.keyboard.type("75"); p.keyboard.press("Enter"); p.wait_for_timeout(150)
    check("Type a value writes the attack", p.evaluate(AMP)[0] == 75, str(p.evaluate(AMP)))
    x, y = centre(p, '#ampEnvCurve [data-handle="peak"]')
    p.mouse.click(x, y); p.mouse.click(x, y); p.wait_for_timeout(150)
    check("two presses on the peak put the attack back to its start", p.evaluate(AMP)[0] == 8, str(p.evaluate(AMP)))

    print("\n--- the hands ---")
    hands = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      restore(Object.assign({}, BASE_SETUP, { layers: 'split' })); await wait(200);
      const menu = () => { el.ampEnvCurve.querySelector('[data-handle="peak"]').dispatchEvent(new MouseEvent('contextmenu', { bubbles: true }));
        const keys = overlay ? [...overlay.node.querySelectorAll('.ctx-item')].map((b) => b.dataset.item) : []; closeOverlay(); return keys; };
      const linkedItems = menu();
      document.getElementById('linkAmpEnv').click(); await wait(100);
      const ownItems = menu();
      document.getElementById('editHandB').click(); await wait(100);
      return { linkedItems, ownItems, linked: linked('ampEnv') };
    }""")
    check("linked, a handle's menu has no Copy; the hand's own, it does", "copy" not in hands["linkedItems"] and "copy" in hands["ownItems"]
          and hands["linked"] is False, str(hands))
    s0 = p.evaluate("() => { const s = snapshot(); return [s.atk, s.bAtk]; }")
    drag(p, '#ampEnvCurve [data-handle="peak"]', 25, 0); p.wait_for_timeout(200)
    s1 = p.evaluate("() => { const s = snapshot(); return [s.atk, s.bAtk]; }")
    check("editing the upper hand, a drag writes its attack and not the lower's", s1[0] == s0[0] and s1[1] != s0[1], "%s -> %s" % (s0, s1))
    p.evaluate("() => { document.getElementById('editHandA').click(); restore(BASE_SETUP); }"); p.wait_for_timeout(300)

    print("\n--- the Envelope follows until it is edited ---")
    p.evaluate("() => openModCard('env.note')"); p.wait_for_timeout(400)
    MENV = """() => ({ own: el.menvOwn.checked, gen: genSettings().menvOwn, m: [el.menvAtk.value, el.menvDec.value, el.menvSus.value, el.menvRel.value].map(Number),
      amp: [el.envAttack.value, el.envDecay.value, el.envSustain.value, el.envRelease.value].map(Number),
      read: [el.menvAtkValue.textContent, el.menvDecValue.textContent, el.menvSusValue.textContent, el.menvRelValue.textContent],
      ampRead: [el.envAttackValue.textContent, el.envDecayValue.textContent, el.envSustainValue.textContent, el.envReleaseValue.textContent],
      face: knobFraction(el.menvRel), dis: el.menvAtk.disabled, undo: undoHistory.undo.length })"""
    p.evaluate("() => { restore(BASE_SETUP); for (const [id, v] of [['envAttack', 30], ['envDecay', 250], ['envSustain', 40], ['envRelease', 900], ['menvAtk', 1500], ['menvDec', 3000], ['menvSus', 90], ['menvRel', 3500]]) setControl(id, v); menvFollowAmp(); }")
    p.wait_for_timeout(700)
    f0 = p.evaluate(MENV)
    peakX = p.evaluate("() => { paintModLive(); return el.menvCurve._drawn.corners[1][0]; }")
    wantX = p.evaluate("() => { const d = envDrawings.menv; return d.frame.x0 + envWidth(30, 2000, d.frame.seg); }")
    check("following, its readings are the amp's", f0["read"] == f0["ampRead"] and not f0["own"], str(f0))
    check("its knobs show the amp's on their own ranges and are live", abs(f0["face"] - 899 / 3999) < 1e-3 and not f0["dis"], str(f0["face"]))
    check("its drawing's peak is the amp's attack on its own scale", abs(peakX - wantX) < 0.01, "%.2f / %.2f" % (peakX, wantX))
    null("its own attack would put the peak elsewhere", abs(p.evaluate("() => { const d = envDrawings.menv; return d.frame.x0 + envWidth(1500, 2000, d.frame.seg); }") - peakX) > 5)

    # A knob dragged by hand while following.
    face = p.locator('#menvRel').locator('xpath=..').locator('.knob-face')
    fb = face.bounding_box(); fx, fy = fb["x"] + fb["width"] / 2, fb["y"] + fb["height"] / 2
    p.mouse.move(fx, fy); p.mouse.down(); p.mouse.move(fx, fy - 9, steps=3); p.mouse.up(); p.wait_for_timeout(900)
    k = p.evaluate(MENV)
    check("a knob turned while following copies the amp's four, applies the turn and makes it its own",
          k["own"] and k["gen"] and k["m"][:3] == [30, 250, 40] and k["m"][3] > 900 and k["m"][3] == 900 + round(9 / 180 * 3999), str(k))
    check("in one step of undo", k["undo"] == f0["undo"] + 1, "%d -> %d" % (f0["undo"], k["undo"]))
    p.evaluate("() => undoStep(true)"); p.wait_for_timeout(300)
    back = p.evaluate(MENV)
    check("which undo puts back: following, with its old four", not back["own"] and back["m"] == [1500, 3000, 90, 3500], str(back))
    # The null: the knob as it was until 17 Nov, greyed while following, which no hand could turn.
    p.evaluate("() => { el.menvRel.disabled = true; }")
    p.mouse.move(fx, fy); p.mouse.down(); p.mouse.move(fx, fy - 9, steps=3); p.mouse.up(); p.wait_for_timeout(200)
    dis = p.evaluate(MENV)
    null("a disabled knob, as it was, is not turned and does not make it its own", not dis["own"] and dis["m"][3] == 3500, str(dis))
    p.evaluate("() => { el.menvRel.disabled = false; }")
    p.evaluate("() => setControl('menvAtk', 700)")
    sc = p.evaluate(MENV)
    null("setControl, no hand, writes its value and leaves it following", not sc["own"] and sc["m"][0] == 700, str(sc))
    p.evaluate("() => setControl('menvAtk', 1500)")

    # A handle dragged while following.
    p.wait_for_timeout(300)
    (cx, cy), _ = drag(p, '#menvCurve [data-handle="corner"]', 0, -15)
    p.wait_for_timeout(200)
    h = p.evaluate(MENV)
    check("the corner dragged while following: its own, the attack and release the amp's, the decay the amp's place, the sustain raised",
          h["own"] and h["gen"] and h["m"][0] == 30 and h["m"][3] == 900 and abs(h["m"][1] - 250) <= 30 and h["m"][2] > 40, str(h))
    # Reset on a knob follows again.
    p.locator('#menvAtk').locator('xpath=..').locator('.knob-face').click(button="right"); p.wait_for_timeout(250)
    reset_side = p.evaluate("() => { const r = overlay && overlay.node.querySelector('.ctx-item[data-item=\"reset\"]'); return r ? r.textContent : null; }")
    p.locator('.ctx-item[data-item="reset"]').click(); p.wait_for_timeout(150)
    r = p.evaluate(MENV)
    check("Reset on its knob says it follows the amp envelope, and does", reset_side is not None and "follows the amp envelope" in reset_side
          and not r["own"] and not r["gen"], "%s %s" % (reset_side, r))

    # An arrow on a handle while following.
    p.locator('#menvCurve [data-handle="end"]').focus(); p.keyboard.press("ArrowRight"); p.wait_for_timeout(100)
    a = p.evaluate(MENV)
    check("an arrow on a handle while following: its own, from the amp's, the release a step longer",
          a["own"] and a["m"][:3] == [30, 250, 40] and a["m"][3] > 900, str(a))
    x, y = centre(p, '#menvCurve [data-handle="end"]')
    p.mouse.click(x, y); p.mouse.click(x, y); p.wait_for_timeout(150)
    check("two presses on a handle follow again", not p.evaluate(MENV)["own"])

    # A value typed while following.
    p.locator('#menvDec').locator('xpath=..').locator('.knob-face').click(button="right"); p.wait_for_timeout(250)
    p.locator('.ctx-item[data-item="type"]').click(); p.wait_for_timeout(100)
    p.keyboard.press("Control+a"); p.keyboard.type("1200"); p.keyboard.press("Enter"); p.wait_for_timeout(150)
    t = p.evaluate(MENV)
    check("a value typed while following: its own, the others the amp's, the decay as typed",
          t["own"] and t["m"] == [30, 1200, 40, 900], str(t))
    vis = p.evaluate("() => [!el.menvFollow.hidden, !el.menvFollowing.hidden]")
    p.locator("#menvFollow").click(); p.wait_for_timeout(100)
    fo = p.evaluate(MENV)
    check("its own, Follow is offered; pressed, it follows and keeps its own four", vis == [True, False] and not fo["own"]
          and fo["m"] == [30, 1200, 40, 900] and p.evaluate("() => [!el.menvFollow.hidden, !el.menvFollowing.hidden]") == [False, True],
          "%s %s" % (vis, fo))
    p.locator("#modEditorClose").click(); p.wait_for_timeout(200)

    print("\n--- the voice filter's drawing ---")
    p.evaluate("() => { restore(BASE_SETUP); el.vcfType.value = '1'; el.vcfType.dispatchEvent(new Event('change', { bubbles: true })); }")
    p.wait_for_timeout(300)
    p.locator("#vcfEnvOpen").click(); p.wait_for_timeout(200)
    where = p.evaluate("""() => { const pop = el.vcfEnvPop.getBoundingClientRect(), g = document.getElementById('vcfGroup').getBoundingClientRect();
      const knobs = [...document.querySelectorAll('#vcfGroup .vcf-env .knob-face')].map((f) => f.getBoundingClientRect());
      const covered = knobs.some((k) => !(k.top >= pop.bottom || k.bottom <= pop.top));
      return { open: !el.vcfEnvPop.hidden, inGroup: pop.left >= g.left - 9 && pop.right <= g.right + 9, inWindow: pop.top >= 0 && pop.bottom <= innerHeight && pop.right <= innerWidth,
               covered, expanded: el.vcfEnvOpen.getAttribute('aria-expanded') }; }""")
    check("its heading opens it over its section, in the window, its four knobs in sight", where["open"] and where["inGroup"]
          and where["inWindow"] and not where["covered"] and where["expanded"] == "true", str(where))
    v0 = p.evaluate("() => Number(el.vcfAtk.value)")
    drag(p, '#vcfEnvCurve [data-handle="peak"]', 20, 0); p.wait_for_timeout(150)
    check("its peak dragged writes the filter's attack", p.evaluate("() => Number(el.vcfAtk.value)") > v0)
    p.locator('#vcfEnvCurve [data-handle="end"]').click(button="right"); p.wait_for_timeout(200)
    p.keyboard.press("Escape"); p.wait_for_timeout(100)
    esc1 = p.evaluate("() => [!!overlay, !el.vcfEnvPop.hidden]")
    p.keyboard.press("Escape"); p.wait_for_timeout(100)
    esc2 = p.evaluate("() => [!!overlay, !el.vcfEnvPop.hidden]")
    check("Esc shuts a menu over it first, and then it", esc1 == [False, True] and esc2 == [False, False], "%s %s" % (esc1, esc2))
    p.locator("#vcfEnvOpen").click(); p.wait_for_timeout(150)
    p.mouse.click(700, 200); p.wait_for_timeout(150)
    check("a press elsewhere shuts it", p.evaluate("() => el.vcfEnvPop.hidden"))
    thumb = p.evaluate("() => { const a = el.vcfEnvThumb.firstElementChild.getAttribute('d'); setControl('vcfAtk', 900); paintAmpEnv(); return [a, el.vcfEnvThumb.firstElementChild.getAttribute('d')]; }")
    check("the heading's small copy follows the knobs", thumb[0] != thumb[1] and len(thumb[1]) > 10, str(thumb))
    if bad:
        check("no page errors", False, "; ".join(bad[:3]))
    p.close()

    print("\n--- it fits, with the filter's drawing open ---")
    FIT = """async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      restore(Object.assign({}, BASE_SETUP, { layers: 'split', vcfType: 1 })); await wait(300);
      el.vcfEnvOpen.click(); await wait(200);
      const s = document.getElementById('benchStage'), pop = el.vcfEnvPop.getBoundingClientRect(), st = s.getBoundingClientRect();
      const amp = el.ampEnvCurve.getBoundingClientRect();
      return { over: s.scrollHeight - s.clientHeight, open: !el.vcfEnvPop.hidden, inside: pop.top >= st.top - 1 && pop.bottom <= st.bottom + 1,
               ampH: Math.round(amp.height) };
    }"""
    for w, h in ((1400, 900), (1100, 860), (1200, 680), (1100, 680), (960, 600)):
        q, qbad = open_page(b, w, h)
        r = q.evaluate(FIT)
        check("%dx%d: Play does not scroll with two hands, the filter on and its drawing open, which is inside the tabs" % (w, h),
              r["over"] <= 0 and r["open"] and r["inside"] and r["ampH"] >= 30, str(r))
        if qbad: check("no page errors at %dx%d" % (w, h), False, "; ".join(qbad[:3]))
        q.close()
    q, _ = open_page(b, 960, 420)
    q.evaluate("() => setSize(1)"); q.wait_for_timeout(200)
    r = q.evaluate(FIT)
    null("at 960x420 and 100% the same check fails", not (r["over"] <= 0 and r["inside"]), str(r))
    q.close()
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
