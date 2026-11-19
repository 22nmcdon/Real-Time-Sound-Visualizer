"""The drawn LFOs (19 Nov, web/docs/lfo-drawn.md): the LFO card's editor and
the cards, by real mouse and keys.

What is checked, each with its null beside it:

- the page's maths held to the core's: every shape text the editor writes
  read the same way (core/tests/tools/lfo_cpp.cpp's `text`), and the level
  the drawing draws at each instant the level the core plays then (null: an
  S drawn straight);
- the editor in one column at the six windows: the tools on one row, the
  drawing 2.4:1 of its width (2.6:1 compact) and shortened only by room, at
  least 120 px tall, three routings of eight and Add in sight, all inside the
  editor and clear of the modulation row (nulls: the drawing held at 2.4:1
  regardless leaves Where it goes no routing at 1200x680; two columns make
  the drawing a tower at 1660x1050);
- the gestures, a hand's: a drag adopting today's sine as its twin, which
  the instrument then plays (null: before it, the shape is today's sine and
  the setup names no drawing); snapped to the Grid and free with Shift; the
  line pressed twice adding a point at the line's own level, a point pressed
  twice taking it away; a bend dragged into a curve; the arrows and Delete;
  the point's menu by right-click and Shift+F10 - its line's law, a new level
  each pass, Remove - and Esc; a random point's height its reach;
- the seven starting shapes: today's five by name, the twin drawn (null:
  the sine's drawing is not the triangle's), the two new ones drawn;
- the card's drawing the shape's: Saw down falls across each cycle (null:
  Saw up's levels), and the dot on the line where the instrument's phase and
  value put it (null: half a cycle on);
- Phase, Rate in Tempo and Starts again reaching the instrument, and stored
  only away from their defaults (null: an untouched setup names none);
- nothing moves (lfo-drawn.md, Nothing moves): every box in the editor and
  the cards to half a pixel across the seven shapes, Hz and Tempo, the three
  starts, Silence, a point selected, a note held and LFO 1 against LFO 2, at
  the six windows (null: the head's reading sized to its words moves the
  line beside it).
"""
import json, os, subprocess, sys
from playwright.sync_api import sync_playwright
import webfonts, playfigs as PF

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(ART)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    """A check's null: the same comparison fed a value it must reject."""
    check("null: " + name, red, detail)

# --- the core's parse and engine, for the page's maths to be held to ---
BUILD = os.path.join(ROOT, "core", "build", "lfotest")
os.makedirs(BUILD, exist_ok=True)
EXE = os.path.join(BUILD, "lfo_cpp")
subprocess.run(["g++", "-std=c++17", "-O2", "-I", os.path.join(ROOT, "core", "include"),
                os.path.join(ROOT, "core", "tests", "tools", "lfo_cpp.cpp"), "-o", EXE], check=True)
def core_text(texts):
    path = os.path.join(BUILD, "texts.txt")
    with open(path, "w") as f: f.write("\n".join(texts) + "\n")
    out = subprocess.run([EXE, "text", path], check=True, capture_output=True, text=True).stdout.split("\n")
    return [l.split(" ", 2) for l in out if l]
def core_run(text, hz, n, rate=48000):
    path = os.path.join(BUILD, "run.txt")
    with open(path, "w") as f: f.write("shape drawn\ntext %s\nhz %r\nrate %d\nn %d\nseed 3\n" % (text, hz, rate, n))
    out = subprocess.run([EXE, "run", path], check=True, capture_output=True, text=True).stdout.split("\n")
    return [float.fromhex(v) for v in out[1:] if v]

def open_page(b, w=1400, h=900):
    p = b.new_page(viewport={"width": w, "height": h})
    webfonts.route(p)
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(900)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    webfonts.settle(p)
    p.wait_for_function("state.source && state.source.kind === 'host'", timeout=20000)
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(200)
    return p, bad

def centre(p, sel):
    box = p.locator(sel).bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

# Where a point of the cycle is on the screen: u across, v up, in the drawing's own geometry.
AT = "([u, v]) => { const s = document.getElementById('lfoPlot'), g = s._g, r = s.getBoundingClientRect(), z = pageZoom || 1; return [r.left + g.x(u) * z, r.top + g.y(v) * z]; }"
SHAPE = "(i) => ({ shape: lfos[i].shape, drawn: lfos[i].drawn, menu: document.getElementById('lfoShape' + i) && document.getElementById('lfoShape' + i).value })"
UNDO = "() => undoHistory.undo.length"
# Eight routings on LFO 1, onto controls the face shows, for the fit.
EIGHT = """() => { state.modRoutings = []; touchRoutings();
  const ids = Array.from(MOD_DESTS.values()).filter((d) => routingAllowed(MOD_SOURCES.get('lfo1'), d) && document.querySelector('[data-mod-dest="' + d.id + '"]')).map((d) => d.id).slice(0, 8);
  for (const id of ids) addRouting('lfo1', id); return ids.length; }"""
FIT = """() => {
  const z = pageZoom || 1, R = (n) => n.getBoundingClientRect(), ed = R(el.modEditor), svg = document.getElementById('lfoPlot');
  const list = document.getElementById('lfoGoesList'), L = R(list), rows = Array.from(list.querySelectorAll('.mod-edit'));
  const add = R(el.srcDetail.querySelector('.lfo-goes-add')), mod = R(el.modRow);
  const tools = el.srcDetail.querySelector('.lfo-tools');
  const mids = new Set(Array.from(tools.children).filter((n) => n.getClientRects().length).map((n) => Math.round((R(n).top + R(n).height / 2) / z)));
  const last = Math.max(...Array.from(el.modEditor.querySelectorAll('.lfo-tools, #lfoPlot, .lfo-foot, .lfo-goes-head, .lfo-goes-add')).map((n) => R(n).bottom));
  return { editor: [Math.round(ed.width / z), Math.round(ed.height / z)], w: svg.clientWidth, h: svg.clientHeight, aspect: svg.clientWidth / svg.clientHeight,
           shown: rows.filter((n) => R(n).bottom <= L.bottom + 0.5).length, rows: rows.length, addIn: add.bottom <= ed.bottom - 1,
           toolsRows: mids.size, toolsIn: R(tools).right <= ed.right + 0.5, inside: last <= ed.bottom + 0.5, clear: ed.bottom <= mod.top + 0.5,
           compact: document.body.hasAttribute('data-compact') };
}"""
# Every box in the editor and the cards that a choice must not move, in the page's own pixels.
BOXES = """() => {
  const z = pageZoom || 1, out = {};
  const put = (k, n) => { if (!n || !n.getClientRects().length) return; const r = n.getBoundingClientRect(); out[k] = [r.left / z, r.top / z, r.width / z, r.height / z]; };
  const ed = el.modEditor;
  put('editor', ed); put('head', ed.querySelector('.mod-editor-head')); put('name', el.srcDetailTitle); put('reading', el.srcDetailReading);
  put('desc', el.srcDetailDesc); put('close', el.modEditorClose); put('tools', ed.querySelector('.lfo-tools'));
  ed.querySelectorAll('.lfo-start').forEach((n) => put('start ' + n.dataset.start, n));
  put('shape name', document.getElementById('lfoShapeName')); put('grid', document.getElementById('lfoGrid')); put('hold', document.getElementById('lfoHoldNote'));
  put('drawing', document.getElementById('lfoPlot')); put('foot', ed.querySelector('.lfo-foot'));
  put('knob rate', ed.querySelector('.lfo-knobs > .menu-row:not([hidden])')); put('knob phase', document.getElementById('lfoPhase' + lfoEd.i).closest('.menu-row'));
  ed.querySelectorAll('.lfo-fld').forEach((n, k) => put('field ' + k, n));
  ed.querySelectorAll('.lfo-fld .switch button').forEach((n, k) => put('switch ' + k, n));
  put('goes', ed.querySelector('.src-goes')); put('goes head', ed.querySelector('.lfo-goes-head')); put('silence', document.getElementById('lfoSilence'));
  put('goes list', document.getElementById('lfoGoesList')); put('add', ed.querySelector('.lfo-goes-add'));
  ed.querySelectorAll('.mod-edit').forEach((n, k) => put('row ' + k, n));
  el.modStrip.querySelectorAll('.mod-card').forEach((n) => { put('card ' + n.dataset.source, n); put('card ' + n.dataset.source + ' reading', n.querySelector('.reading')); });
  return out;
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p, bad = open_page(b)

    print("\n--- the page's maths, the core's ---")
    texts = ["1;.25,1,s;.75,-1,s", "1;0,-.6,m.78;.125,.85,l;.375,.85,m.3;.75,-.2,s;.875,-.8,h,r", "1;0,1,h,r", "1;0,1,s,r",
             "1;0,.9,l;.5,.9,l;.5,-.9,l;1,-.9,l", "1;.250,1,s;.75,-1,s", "1;0,1,q", "2;0,1,l", "1;0,1,l,x"]
    page = p.evaluate("(ts) => ts.map((t) => { const pts = lfoParse(t); return pts ? ['ok', String(pts.length), lfoText(pts)] : ['no', '0', '1']; })", texts)
    core = core_text(texts)
    check("every shape text reads the same on the page as in the core, and writes back the same", page == core, "%s against %s" % (page[:2], core[:2]))
    # Levels: a shape with each law and no random point, at 5 Hz (9600 samples a cycle), sample by sample.
    shape = "1;0,-1,l;.2501,1,h;.50006,.5,s;.75005,0,m.8"
    played = core_run(shape, 5, 9600)
    drawn = p.evaluate("""([t, n]) => { const pts = lfoParse(t), lv = pts.map((q) => q.y);
      return Array.from({ length: n }, (_, i) => { const u = ((i + 1) * 5 / 48000) % 1; return lfoLevelAt(pts, lv, u); }); }""", [shape, 9600])
    # The core's phase is summed a sample at a time and the page's u is (i + 1) / 9600: a few ulps apart, and at a point's own
    # sample a step, so the samples within one of a point are left out of the comparison.
    near = {2400, 2401, 4800, 4801, 7200, 7201, 0}
    worst = max(abs(a - c) for i, (a, c) in enumerate(zip(drawn, played)) if i not in near and i + 1 not in near)
    check("the level the drawing draws at each instant is the level the core plays, every law, within 1e-6", worst < 1e-6, "%.3g" % worst)
    straight = p.evaluate("""([t, n]) => { const pts = lfoParse(t).map((q) => Object.assign({}, q, { law: q.law === 's' ? 'l' : q.law })), lv = pts.map((q) => q.y);
      return Array.from({ length: n }, (_, i) => lfoLevelAt(pts, lv, ((i + 1) * 5 / 48000) % 1)); }""", [shape, 9600])
    null("the S drawn straight is not what the core plays", max(abs(a - c) for a, c in zip(straight, played)) > 0.05)

    print("\n--- the gestures, by a hand ---")
    p.evaluate("() => { state.modRoutings = []; touchRoutings(); }")
    p.locator('.mod-card[data-source="lfo1"]').click(); p.wait_for_timeout(500)
    before = p.evaluate(SHAPE, 0)
    snap0 = p.evaluate("() => { const s = snapshot(); return [s.l0s, 'l0m' in s, 'l0p' in s, 'l0t' in s]; }")
    null("before any edit the shape is today's sine, and the setup names no drawing, Phase or start", before["shape"] == "sine"
         and snap0 == ["sine", False, False, False], str((before, snap0)))
    steps0 = p.evaluate(UNDO)
    x, y = centre(p, '#lfoPlot [data-lpt="0"]')
    p.mouse.move(x, y); p.mouse.down(); p.mouse.move(x + 3, y + 20, steps=3); p.mouse.move(x + 6, y + 40, steps=3); p.mouse.up()
    p.wait_for_timeout(900)
    after = p.evaluate(SHAPE, 0)
    pts = p.evaluate("() => lfoParse(lfos[0].drawn)")
    served = p.evaluate("() => state.source.lfoLevels.slice(0, 3)")
    check("the first drag adopts the sine's twin, edited: the shape is drawn, its first point lower, its x still on the Grid",
          after["shape"] == "drawn" and after["menu"] == "drawn" and len(pts) == 2 and pts[0]["x"] == 0.25 and 0.2 < pts[0]["y"] < 0.95
          and pts[1] == {"x": 0.75, "y": -1, "law": "s", "m": 0.5, "r": False}, str((after, pts)))
    check("and the instrument plays the drawing: it serves a drawn shape's line and the point's new level", served[0] >= 0 and abs(served[1] - pts[0]["y"]) < 1e-9, str(served))
    check("as one step of undo", p.evaluate(UNDO) == steps0 + 1, "%d then %d" % (steps0, p.evaluate(UNDO)))
    # Shift frees the Grid.
    x, y = centre(p, '#lfoPlot [data-lpt="0"]')
    p.keyboard.down("Shift"); p.mouse.move(x, y); p.mouse.down(); p.mouse.move(x + 7, y, steps=4); p.mouse.up(); p.keyboard.up("Shift"); p.wait_for_timeout(300)
    free = p.evaluate("() => lfoParse(lfos[0].drawn)[0].x")
    x, y = centre(p, '#lfoPlot [data-lpt="0"]')
    p.mouse.move(x, y); p.mouse.down(); p.mouse.move(x - 2, y, steps=3); p.mouse.up(); p.wait_for_timeout(300)
    snapped = p.evaluate("() => lfoParse(lfos[0].drawn)[0].x")
    check("Shift drags off the Grid; without it the point lands on an eighth", abs(free * 8 - round(free * 8)) > 0.01 and snapped * 8 == round(snapped * 8),
          "%r then %r" % (free, snapped))
    null("an eighth is on the Grid and the free x is not", free * 8 != round(free * 8))
    # Twice on the line: a point at the line's own level, so nothing moves. At 0.375, an eighth, off the
    # middle of the line, where its bend's round is.
    lv = p.evaluate("() => { const pts = lfoParse(lfos[0].drawn); return lfoLevelAt(pts, pts.map((q) => q.y), 0.375); }")
    x, y = p.evaluate(AT, [0.375, lv])
    level_before = p.evaluate("() => { const pts = lfoParse(lfos[0].drawn); return [0.3, 0.375, 0.45].map((u) => lfoLevelAt(pts, pts.map((q) => q.y), u)); }")
    p.mouse.click(x, y); p.wait_for_timeout(60); p.mouse.click(x, y); p.wait_for_timeout(400)
    three = p.evaluate("() => lfoParse(lfos[0].drawn)")
    level_after = p.evaluate("() => { const pts = lfoParse(lfos[0].drawn); return [0.3, 0.375, 0.45].map((u) => lfoLevelAt(pts, pts.map((q) => q.y), u)); }")
    check("the line pressed twice adds a point there, at the line's level", len(three) == 3 and three[1]["x"] == 0.375
          and abs(three[1]["y"] - round(lv, 2)) < 1e-9 and abs(level_after[1] - level_before[1]) < 0.006, str(three))
    x, y = centre(p, '#lfoPlot [data-lpt="1"]')
    p.mouse.click(x, y); p.wait_for_timeout(60); p.mouse.click(x, y); p.wait_for_timeout(400)
    check("and that point pressed twice takes it away", len(p.evaluate("() => lfoParse(lfos[0].drawn)")) == 2)
    # A bend dragged.
    has_bend = p.evaluate("() => !!document.querySelector('#lfoPlot [data-lbend=\"0\"]')")
    x, y = centre(p, '#lfoPlot [data-lbend="0"]')
    p.mouse.move(x, y); p.mouse.down(); p.mouse.move(x, y - 25, steps=4); p.mouse.up(); p.wait_for_timeout(300)
    bent = p.evaluate("() => lfoParse(lfos[0].drawn)[0]")
    check("a bend's round dragged makes its line a curve by its midpoint", has_bend and bent["law"] == "m" and bent["m"] != 0.5, str(bent))
    # The keyboard: arrows on a focused point, Delete.
    p.locator('#lfoPlot [data-lpt="1"]').focus()
    was = p.evaluate("() => lfoParse(lfos[0].drawn)[1]")
    p.keyboard.press("ArrowUp"); p.keyboard.press("ArrowLeft"); p.wait_for_timeout(200)
    now = p.evaluate("() => lfoParse(lfos[0].drawn)[1]")
    check("the arrows move a focused point: up a twentieth, left a step of the Grid", abs(now["y"] - (was["y"] + 0.05)) < 1e-9 and abs(now["x"] - (was["x"] - 0.125)) < 1e-9,
          "%s then %s" % (was, now))

    print("\n--- a point's menu ---")
    p.locator('#lfoPlot [data-lpt="1"]').click(button="right"); p.wait_for_timeout(250)
    items = p.evaluate("() => Array.from(document.querySelectorAll('.over .ctx-item')).map((n) => n.dataset.item + (n.getAttribute('aria-checked') === 'true' ? '*' : ''))")
    check("right-click opens its menu: its line's four laws, the one it has ticked, a new level each pass, Remove",
          items == ["law-l", "law-m", "law-s*", "law-h", "random", "remove"], str(items))
    p.locator('.over [data-item="law-h"]').click(); p.wait_for_timeout(250)
    check("Hold sets its law", p.evaluate("() => lfoParse(lfos[0].drawn)[1].law") == "h")
    p.locator('#lfoPlot [data-lpt="1"]').focus(); p.keyboard.press("Shift+F10"); p.wait_for_timeout(250)
    opened = p.evaluate("() => !!document.querySelector('.over .ctx-item')")
    p.locator('.over [data-item="random"]').click(); p.wait_for_timeout(400)
    rnd = p.evaluate("() => lfoParse(lfos[0].drawn)[1]")
    check("Shift+F10 opens it too, and a new level each pass makes the point random, its reach the size of its height",
          opened and rnd["r"] and rnd["y"] > 0, str(rnd))
    shown = p.evaluate("() => !!document.querySelector('#lfoPlot [data-lpt=\"1\"] rect') && document.querySelectorAll('#lfoPlot [data-reach=\"1\"]').length === 2")
    check("a random point is drawn as a diamond with its reach marked either way of nought", shown)
    x, y = centre(p, '#lfoPlot [data-lpt="1"]')
    reach0 = rnd["y"]
    p.mouse.move(x, y); p.mouse.down(); p.mouse.move(x, y + 400, steps=6); p.mouse.up(); p.wait_for_timeout(300)
    reach = p.evaluate("() => lfoParse(lfos[0].drawn)[1].y")
    check("dragged down past nought, its height is still a reach, positive", 0 <= reach <= 1 and reach != reach0, "%r then %r" % (reach0, reach))
    p.locator('#lfoPlot [data-lpt="1"]').click(button="right"); p.wait_for_timeout(200)
    p.keyboard.press("Escape"); p.wait_for_timeout(200)
    check("Esc puts the menu away and leaves the editor open", not p.evaluate("() => !!document.querySelector('.over')") and p.evaluate("() => !el.modEditor.hidden"))
    p.locator('#lfoPlot [data-lpt="1"]').focus(); p.keyboard.press("Delete"); p.wait_for_timeout(300)
    check("Delete takes a focused point away", len(p.evaluate("() => lfoParse(lfos[0].drawn)")) == 1)

    print("\n--- the starting shapes ---")
    p.locator('.lfo-start[data-start="triangle"]').click(); p.wait_for_timeout(300)
    tri = p.evaluate("() => ({ s: lfos[0].shape, kept: lfos[0].drawn, d: document.getElementById('lfoPlot')._drawn.pts, said: document.getElementById('lfoShapeName').textContent, pressed: document.querySelector('.lfo-start[aria-pressed=\"true\"]').dataset.start })")
    check("Triangle is today's triangle by name, the drawing kept for later, its twin drawn", tri["s"] == "triangle" and tri["kept"] != ""
          and [(q["x"], q["y"], q["law"]) for q in tri["d"]] == [(0.25, 1, "l"), (0.75, -1, "l")] and tri["said"] == "Triangle · as today"
          and tri["pressed"] == "triangle", str(tri))
    null("the sine's twin is not the triangle's", [(q["x"], q["y"], q["law"]) for q in tri["d"]] != [(0.25, 1, "s"), (0.75, -1, "s")])
    p.locator('.lfo-start[data-start="rampdown"]').click(); p.wait_for_timeout(500)
    down = p.evaluate("() => ({ s: lfos[0].shape, d: lfos[0].drawn, said: document.getElementById('lfoShapeName').textContent })")
    check("Saw down is drawn from the start", down == {"s": "drawn", "d": "1;0,1,l;1,-1,l", "said": "Saw down"}, str(down))

    print("\n--- the card and the dot ---")
    p.wait_for_timeout(300)
    card = p.evaluate("""() => { paintModLive(); const c = el.modStrip.querySelector('[data-source="lfo1"] canvas'), d = c._drawn;
      return [0.1, 0.3, 0.6, 0.9].map((u) => d.y(u)).concat([d.h, d.w]); }""")
    h = card[4]
    mid, amp = h / 2, h / 2 - 3
    want = [mid - (1 - 2 * u) * amp for u in (0.1, 0.3, 0.6, 0.9)]
    up = [mid - (2 * u - 1) * amp for u in (0.1, 0.3, 0.6, 0.9)]
    check("the card draws Saw down falling across each cycle", all(abs(a - w) < 0.5 for a, w in zip(card[:4], want)), str((card[:4], want)))
    null("Saw up's levels are not what it draws", any(abs(a - w) > 4 for a, w in zip(card[:4], up)))
    dot = p.evaluate("""() => { drawLfoEditor(false); const s = document.getElementById('lfoPlot'), g = s._g, d = s._drawn, u = lfoReadU(lfos[0]);
      const pts = lfoParse(lfos[0].drawn), on = g.y(lfoLevelAt(pts, pts.map((q) => q.y), u)), off = g.y(lfoLevelAt(pts, pts.map((q) => q.y), (u + 0.5) % 1));
      return { dot: d.dot, x: g.x(u), on, off }; }""")
    check("the editor's gold dot is on the line, at the instrument's phase", abs(dot["dot"][0] - dot["x"]) < 0.5 and abs(dot["dot"][1] - dot["on"]) < 3, str(dot))
    null("half a cycle on it would be somewhere else", abs(dot["dot"][1] - dot["off"]) > 20, str(dot))

    print("\n--- Phase, Tempo and Starts again ---")
    p.locator('.lfo-start[data-start="sine"]').click(); p.wait_for_timeout(200)
    p.evaluate("() => { const r = document.getElementById('lfoPhase0'); r.value = '90'; r.dispatchEvent(new Event('input', { bubbles: true })); r.dispatchEvent(new Event('change', { bubbles: true })); }")
    p.wait_for_timeout(500)
    ph = p.evaluate("() => { const l = lfos[0]; return { value: l.value, quarter: Math.sin(l.phase + Math.PI / 2), none: Math.sin(l.phase), said: document.getElementById('lfoPhaseValue0').textContent }; }")
    check("Phase reaches the instrument: a quarter on, its sine is read a quarter on", abs(ph["value"] - ph["quarter"]) < 1e-6 and ph["said"] == "90°", str(ph))
    null("with no Phase it would read its own phase's sine", abs(ph["value"] - ph["none"]) > 0.05, str(ph))
    p.locator('[data-lfo-tempo="1"]').click(); p.wait_for_timeout(300)
    tempo = p.evaluate("() => ({ sync: lfos[0].sync, menu: document.getElementById('lfoSync0').value, shown: Array.from(document.querySelectorAll('[data-lfo-row]')).filter((r) => !r.hidden).map((r) => r.dataset.lfoRow) })")
    check("Rate in Tempo follows the note value it had, a quarter, and the Rate knob is the note value's", tempo == {"sync": "1/4", "menu": "1/4", "shown": ["tempo"]}, str(tempo))
    note = p.locator('[data-lfo-row="tempo"] .knob-face')
    x, y = centre(p, '[data-lfo-row="tempo"] .knob-face')
    p.mouse.move(x, y); p.mouse.down(); p.mouse.move(x, y - 50, steps=5); p.mouse.up(); p.wait_for_timeout(300)
    faster = p.evaluate("() => lfos[0].sync")
    check("the knob turned up in tempo is a shorter note value", faster in ("1/8t", "1/8", "1/16") , faster)
    p.locator('[data-lfo-tempo="0"]').click(); p.wait_for_timeout(200)
    p.locator('[data-lfo-starts="n"]').click(); p.wait_for_timeout(200)
    snap = p.evaluate("() => { const s = snapshot(); return [s.l0p, s.l0t, s.l0y, document.getElementById('lfoStarts0').value]; }")
    check("Phase and Each note are stored away from their defaults, and Hz is free again", snap == [90, "n", "", "n"], str(snap))
    code = p.evaluate("() => encodeSetup(snapshot())")
    p.evaluate("() => loadCode(encodeSetup(Object.assign({}, BASE_SETUP)))"); p.wait_for_timeout(400)
    plain = p.evaluate("() => { const s = snapshot(); return [s.l0s, 'l0m' in s, 'l0p' in s, 'l0t' in s, lfos[0].phaseDeg, lfos[0].starts]; }")
    check("the base names none of them", plain == ["sine", False, False, False, 0, ""], str(plain))
    p.evaluate("(c) => loadCode(c)", code); p.wait_for_timeout(400)
    back = p.evaluate("() => [lfos[0].phaseDeg, lfos[0].starts, lfos[0].drawn]")
    check("and a code brings them back", back[0] == 90 and back[1] == "n" and back[2] == "1;0,1,l;1,-1,l", str(back))

    print("\n--- the host's knob ---")
    host = p.evaluate("() => ({ list: HOST_PARAMS[HOST_PARAMS.length - 1], marked: !!document.getElementById('lfoRate0').closest('.host-param') })")
    check("LFO 1's Rate is the last host parameter, marked with the gold dot in its editor", host == {"list": "lfoRate0", "marked": True}, str(host))
    p.evaluate("() => openModCard('lfo2')"); p.wait_for_timeout(300)
    check("and LFO 2's is not", not p.evaluate("() => !!document.getElementById('lfoRate1').closest('.host-param')"))
    if bad: check("no page errors", False, "; ".join(bad[:3]))
    else: check("no page errors", True)
    p.close()

    print("\n--- the fit, at the six windows ---")
    for w, hh in PF.SIZES:
        q, qbad = open_page(b, w, hh)
        q.evaluate(EIGHT); q.evaluate("() => openModCard('lfo1')"); q.wait_for_timeout(500)
        m = q.evaluate(FIT)
        tag = "%dx%d" % (w, hh)
        lo, hi = (2.6 if m["compact"] else 2.4) - 0.05, 7
        check("%s: editor %dx%d, drawing %dx%d (%.1f:1), %d of %d routings and Add in sight, tools one row, all inside and clear of the row"
              % (tag, m["editor"][0], m["editor"][1], m["w"], m["h"], m["aspect"], m["shown"], m["rows"]),
              m["h"] >= 120 and lo <= m["aspect"] <= hi and m["shown"] >= 3 and m["addIn"] and m["toolsRows"] == 1 and m["toolsIn"] and m["inside"] and m["clear"], str(m))
        if (w, hh) == (1200, 680):
            q.evaluate("() => { const s = document.getElementById('lfoPlot'); el.srcDetail.style.setProperty('--lfo-draw-h', Math.floor(s.clientWidth / 2.4) + 'px'); }")
            q.wait_for_timeout(100)
            held = q.evaluate(FIT)
            null("at 1200x680 the drawing held at 2.4:1 regardless leaves Where it goes no routing", held["shown"] == 0, str(held["shown"]))
        if (w, hh) == (1660, 1050):
            q.evaluate("() => { el.srcDetail.style.gridTemplateColumns = 'minmax(0, 1.25fr) minmax(0, 1fr)'; el.srcDetail.style.gridTemplateRows = 'minmax(0, 1fr)'; el.srcDetail.style.setProperty('--lfo-draw-h', el.srcDetail.clientHeight - 140 + 'px'); }")
            q.wait_for_timeout(100)
            tower = q.evaluate("() => { const s = document.getElementById('lfoPlot'); return s.clientWidth / s.clientHeight; }")
            null("two columns make the drawing a tower at 1660x1050", tower < 1.6, "%.2f:1" % tower)
        if qbad: check("%s: no page errors" % tag, False, "; ".join(qbad[:3]))
        q.close()

    print("\n--- nothing moves, at the six windows ---")
    for w, hh in PF.SIZES:
        q, qbad = open_page(b, w, hh)
        tag = "%dx%d" % (w, hh)
        q.evaluate("() => { state.modRoutings = []; touchRoutings(); addRouting('lfo1', 'gen.freq'); addRouting('lfo1', 'gen.amp'); addRouting('lfo2', 'gen.freq'); addRouting('lfo2', 'gen.amp'); openModCard('lfo1'); }")
        q.wait_for_timeout(500)
        base = q.evaluate(BOXES)
        out = []
        def state(what, js, wait=250):
            if js: q.evaluate(js)
            q.wait_for_timeout(wait)
            ok, moved, nk = PF.same(base, q.evaluate(BOXES))
            out.append((what, ok, moved, nk))
        for k in ["triangle", "ramp", "rampdown", "square", "random", "smooth", "sine"]:
            state("shape " + k, "() => lfoStartFrom(0, '%s')" % k)
        state("Tempo", "() => document.querySelector('[data-lfo-tempo=\"1\"]').click()")
        state("Hz", "() => document.querySelector('[data-lfo-tempo=\"0\"]').click()")
        for v in ["n", "p", ""]:
            state("starts " + (v or "free"), "() => document.querySelector('[data-lfo-starts=\"%s\"]').click()" % v)
        state("Silence", "() => document.getElementById('lfoSilence').click()")
        state("Silence off", "() => document.getElementById('lfoSilence').click()")
        state("a point selected", "() => { lfoEd.sel = 'p0'; drawLfoEditor(true); }")
        state("a note held", "() => msegHoldOn()", 400)
        q.evaluate("() => { msegHoldOff(); lfoEd.sel = null; }")
        state("LFO 2", "() => openModCard('lfo2')", 400)
        state("LFO 2 in Tempo", "() => document.querySelector('[data-lfo-tempo=\"1\"]').click()")
        state("the rate at 8 Hz", "() => { document.querySelector('[data-lfo-tempo=\"0\"]').click(); const r = document.getElementById('lfoRate1'); r.value = '800'; r.dispatchEvent(new Event('input', { bubbles: true })); }")
        moved = [(what, mv) for what, ok, mv, nk in out if not ok]
        counted = min(nk for _, _, _, nk in out)
        check("%s: every one of %d boxes still across the shapes, Hz and Tempo, the starts, Silence, a point selected, a note held, LFO 1 against LFO 2"
              % (tag, counted), not moved and counted >= 38, str(moved[:2]))
        if (w, hh) == (1400, 900):
            q.evaluate("() => { openModCard('lfo1'); document.querySelector('[data-lfo-tempo=\"0\"]').click(); el.srcDetailReading.style.width = 'auto'; }")
            q.wait_for_timeout(300)
            before_null = q.evaluate(BOXES)
            q.evaluate("() => document.querySelector('[data-lfo-tempo=\"1\"]').click()"); q.wait_for_timeout(300)
            ok, mv, _ = PF.same(before_null, q.evaluate(BOXES))
            null("the head's reading sized to its words moves the line beside it", not ok, str(mv[:1]))
        if qbad: check("%s: no page errors" % tag, False, "; ".join(qbad[:3]))
        q.close()
    b.close()

print()
if fails: print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the LFOs are drawn, taken hold of and heard as the core plays them")
