"""The zoom on the screen's toolbar, and only the look (22 Nov, the owner's:
"I don't think zoom should affect the sound anymore ... and it should be a
setting that is always readily available, so maybe move it out of Scope &
measure"); a slider with its name and reading since 23 Nov (the owner's: "Zoom
has no header, and I think zoom specifically should be a horizontal slider
instead of a knob"). The core's side - the sound and the grid Scan reads the
same at every zoom - is core/tests/pieces/zoom.py; this is the face's.

What would go wrong, and what is checked for it, each with its null:

- the slider taking room the face has not got: at the six windows fittest.py
  uses (the plugin's 960x600 at Auto's 90 per cent among them) it is on the
  toolbar after Clear or under the screen (placeZoom, by room), its name,
  track and reading all on show, inside the side column, clear of the screen
  and the verdict under it; and the toolbar's box and the screen's are those
  testing a79bc17 had with the knob, to the pixel, and the same with it taken
  out. The null: put on the toolbar at 1400x900, where placeZoom does not put
  it, it makes the toolbar a row taller and moves the screen;
- its reading not following it, or moving when it changes: the reading is the
  zoom's at 1x and at 2.8x, and the slider's box and the screen's are the same
  at 1x and 64x;
- not keyboard-operable, or no way back: the arrow key on it steps it, and a
  double-click puts it back to 1x (each null the value before);
- it not being to hand: it is in Enlarge's frame on the toolbar, its name on
  show and the toolbar no taller for it; it is not in Scope & measure,
  showControl finds it without opening a panel, and the search finds it under
  Screen;
- the photocell's reticle left where the unmagnified cell was: in X-Y at 4x
  the reticle sits where its cell is drawn, the middle plus four times its
  distance from it, and a reticle whose cell is magnified off the screen is
  hidden. The null is the unmagnified place, which is elsewhere.

Parallel: every reading is a box or a value, and nothing is timed.
"""
import json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
WINDOWS = [(1660, 1050), (1400, 900), (1100, 860), (1200, 680), (1100, 680), (960, 600)]
# The toolbar's box and the screen's (left, top, right, bottom) at each window on testing
# a79bc17, the knob's last commit, measured by getBoundingClientRect: the slider must leave both.
BEFORE = {(1660, 1050): ([34, 86, 743, 115], [54, 135, 723, 804]), (1400, 900): ([24, 86, 493, 115], [24, 135, 493, 604]),
          (1100, 860): ([24, 86, 281, 153], [24, 173, 281, 430]), (1200, 680): ([24, 56, 293, 123], [24, 143, 293, 412]),
          (1100, 680): ([24, 56, 281, 123], [24, 143, 281, 400]), (960, 600): ([22, 50, 253, 111], [22, 129, 253, 361])}

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    check("null: " + name, red, detail)

BOXES = """async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const zoom = el.screenZoom;
  const box = (n) => { const r = n.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)]; };
  const read = () => ({ tools: box(el.screenTools), sheet: box(el.traceSheet), zoom: box(zoom) });
  const parts = [zoom.querySelector('.menu-label'), el.zoom, el.zoomValue].map((n) => { const r = n.getBoundingClientRect(); return r.width > 8 && r.height > 6 && !!n.offsetParent; });
  const z = box(zoom), side = box(el.benchSide), sheet = box(el.traceSheet), dock = box(el.dock), tools = box(el.screenTools);
  const at = zoom.dataset.at;
  const shown = { at, parts, label: zoom.querySelector('.menu-label').textContent.trim(), knob: !!zoom.querySelector('.knob-face'),
                  inMeasure: el.measurePanel.contains(el.zoom),
                  afterClear: at !== 'toolbar' || zoom.previousElementSibling === el.clearButton,
                  inside: z[0] >= side[0] - 0.5 && z[2] <= side[2] + 0.5,
                  clear: at === 'toolbar' ? (z[1] >= tools[1] && z[3] <= tools[3]) : (z[1] >= sheet[3] && z[3] <= dock[1]) };
  const withIt = read();
  zoom.style.display = 'none'; await wait(60); const without = read(); zoom.style.display = '';
  const set = (v) => { el.zoom.value = String(v); el.zoom.dispatchEvent(new Event('input', { bubbles: true })); };
  const readings = [el.zoomValue.textContent];
  set(6); await wait(60); readings.push(el.zoomValue.textContent, state.zoom.toFixed(1) + '\\u00d7');
  set(24); await wait(100); const zoomed = read(); set(0); await wait(60);
  return { shown, withIt, without, zoomed, readings };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    bad = []
    for w, h in WINDOWS:
        p = b.new_page(viewport={"width": w, "height": h})
        p.on("pageerror", lambda e: bad.append(str(e)))
        p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500); p.keyboard.press("Escape"); p.wait_for_timeout(300)
        r = p.evaluate(BOXES)
        label = "%dx%d" % (w, h)
        sh = r["shown"]
        check("%s: the zoom is a slider named Zoom with its reading, all on show, %s, out of Scope & measure" % (label, sh["at"]),
              sh["at"] in ("toolbar", "under") and sh["parts"] == [True] * 3 and sh["label"] == "Zoom" and not sh["knob"]
              and not sh["inMeasure"] and sh["afterClear"], str(sh))
        check("%s: inside the side column and clear of the screen and the verdict" % label, sh["inside"] and sh["clear"], str(sh))
        tools, sheet = BEFORE[(w, h)]
        check("%s: the toolbar and the screen are where they were with the knob (testing a79bc17), to the pixel" % label,
              r["withIt"]["tools"] == tools and r["withIt"]["sheet"] == sheet, "%s against %s" % (r["withIt"], BEFORE[(w, h)]))
        check("%s: and the same with it taken out" % label,
              [r["withIt"]["tools"], r["withIt"]["sheet"]] == [r["without"]["tools"], r["without"]["sheet"]], "%s against %s" % (r["withIt"], r["without"]))
        check("%s: its reading is 1.0x, then the zoom's at 2.8x" % label,
              r["readings"][0] == "1.0×" and r["readings"][1] == r["readings"][2] == "2.8×", str(r["readings"]))
        check("%s: and turning it from 1x to 64x moves neither it nor the screen" % label, r["zoomed"] == r["withIt"], "%s against %s" % (r["zoomed"], r["withIt"]))
        if (w, h) == (1400, 900):
            forced = p.evaluate("""async () => { const box = (n) => { const r = n.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)]; };
              el.clearButton.after(el.screenZoom); await new Promise((r) => setTimeout(r, 60));
              const out = { tools: box(el.screenTools), sheet: box(el.traceSheet) }; placeZoom(); return out; }""")
            null("put on the toolbar at 1400x900 it makes the toolbar taller and moves the screen",
                 forced["tools"] != tools and forced["sheet"] != sheet, str(forced))
            # The keyboard, and double-click back to 1x, with real input.
            kb = p.evaluate("() => { el.zoom.focus(); return el.zoom.value; }")
            p.keyboard.press("ArrowRight"); p.wait_for_timeout(80)
            stepped = p.evaluate("() => [el.zoom.value, el.zoomValue.textContent, document.activeElement === el.zoom]")
            check("the arrow key on it steps it, and the reading follows", stepped[0] == str(int(kb) + 1) and stepped[1] != "1.0×" and stepped[2], "%s from %s" % (stepped, kb))
            null("the value before the key was another", kb != stepped[0], kb)
            p.evaluate("() => { el.zoom.value = '10'; el.zoom.dispatchEvent(new Event('input', { bubbles: true })); }")
            pre = p.evaluate("() => [el.zoom.value, el.zoomValue.textContent]")
            p.dblclick("#zoom"); p.wait_for_timeout(80)
            post = p.evaluate("() => [el.zoom.value, el.zoomValue.textContent, state.zoom]")
            check("a double-click puts it back to 1x", post[0] == "0" and post[1] == "1.0×" and post[2] == 1, "%s from %s" % (post, pre))
            null("it was not at 1x before the double-click", pre[0] != "0" and pre[1] != "1.0×", str(pre))
        p.close()

    for w, h in ((1400, 900), (960, 600)):
        p = b.new_page(viewport={"width": w, "height": h})
        p.on("pageerror", lambda e: bad.append(str(e)))
        p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500); p.keyboard.press("Escape"); p.wait_for_timeout(200)
        got = p.evaluate("""async () => {
          const wait = (ms) => new Promise((r) => setTimeout(r, ms));
          setEnlarged(true); await wait(250);
          const zoom = el.screenZoom, h = () => Math.round(el.screenTools.getBoundingClientRect().height);
          const label = zoom.querySelector('.menu-label').getBoundingClientRect();
          const out = { inFrame: el.screenFrame.contains(el.zoom) && zoom.parentElement === el.screenTools && !!zoom.offsetParent,
                        named: label.width > 8, height: h() };
          zoom.style.display = 'none'; await wait(60); out.without = h(); zoom.style.display = '';
          setEnlarged(false); await wait(250);
          return out;
        }""")
        check("%dx%d: in Enlarge it is on the toolbar in the frame, named, and the toolbar no taller for it" % (w, h),
              got["inFrame"] and got["named"] and got["height"] == got["without"], str(got))
        p.close()

    p = b.new_page(viewport={"width": 1400, "height": 900})
    p.on("pageerror", lambda e: bad.append(str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500); p.keyboard.press("Escape"); p.wait_for_timeout(200)
    got = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const enlarged = true;
      const shown = showControl('zoom'); await wait(100);
      const opened = { measure: !el.measurePanel.hidden, settings: !document.getElementById('menuPanel').hidden };
      const found = searchFor('zoom').map((r) => [r.label, r.crumb]);
      return { enlarged, shown, opened, found };
    }""")
    check("showControl finds it with no panel opened", got["shown"] is True and not got["opened"]["measure"] and not got["opened"]["settings"], str(got))
    check("the search finds it under Screen", ["Zoom", "Screen"] in got["found"], str(got["found"]))

    # The reticle, in X-Y, a quarter of the way in on both axes so 4x puts it on the screen's edge region and 16x off it.
    ret = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setDisplay('xy'); if (!photo.on) el.photoButton.click(); await wait(200);
      const at = (v) => { el.zoom.value = String(v); el.zoom.dispatchEvent(new Event('input', { bubbles: true })); };
      const where = () => { placeReticle(); const r = el.photoReticle; return { hidden: r.hidden, left: parseFloat(r.style.left), top: parseFloat(r.style.top) }; };
      const ox = el.trace.offsetLeft + plot.x, oy = el.trace.offsetTop + plot.y;
      movePhoto(0.4, 0.45); at(0); await wait(100); const one = where();
      at(8); await wait(100); const four = where();
      at(16); await wait(100); const sixteen = where(); at(0); await wait(60);
      return { one, four, sixteen, ox, oy, w: plot.w, h: plot.h, u: photo.u, v: photo.v };
    }""")
    want = (ret["ox"] + (0.5 + (ret["u"] - 0.5) * 4) * ret["w"], ret["oy"] + (0.5 + (ret["v"] - 0.5) * 4) * ret["h"])
    plain = (ret["ox"] + ret["u"] * ret["w"], ret["oy"] + ret["v"] * ret["h"])
    got4 = (ret["four"]["left"], ret["four"]["top"])
    check("in X-Y at 4x the reticle sits where its cell is drawn, magnified about the middle",
          not ret["four"]["hidden"] and abs(got4[0] - want[0]) < 0.5 and abs(got4[1] - want[1]) < 0.5, "%s against %s" % (got4, want))
    null("the unmagnified place is elsewhere", abs(got4[0] - plain[0]) > 5 or abs(got4[1] - plain[1]) > 5, "%s against %s" % (got4, plain))
    check("and at 16x, its cell magnified off the screen, it is hidden", ret["sixteen"]["hidden"], str(ret["sixteen"]))
    null("at 1x it is shown, where its cell is", not ret["one"]["hidden"] and abs(ret["one"]["left"] - plain[0]) < 0.5, str(ret["one"]))
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
print("%d failed" % len(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
