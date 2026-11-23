"""The zoom on the screen's toolbar, and only the look (22 Nov, the owner's:
"I don't think zoom should affect the sound anymore ... and it should be a
setting that is always readily available, so maybe move it out of Scope &
measure"). The core's side - the sound and the grid Scan reads the same at
every zoom - is core/tests/pieces/zoom.py; this is the face's.

What would go wrong, and what is checked for it, each with its null:

- the zoom taking room the toolbar has not got: at the six windows fittest.py
  uses and the plugin's 960x600, the knob is on the toolbar, after Clear, and
  the toolbar and the screen's box are the same to the pixel with it as with
  it taken out. The null: the same knob with its name and reading shown, as a
  row would show them, is found taller or the screen moved at some window;
- turning it moving anything: the screen's box and the toolbar's at 1x and
  64x are the same;
- it not being to hand: it is in Enlarge's frame with the screen, it is not
  in Scope & measure, showControl finds it without opening a panel, and the
  search finds it under Screen;
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

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    check("null: " + name, red, detail)

BOXES = """async (how) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const zoom = document.getElementById('screenZoom');
  const box = (n) => { const r = n.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; };
  const read = () => ({ tools: box(el.screenTools), sheet: box(el.traceSheet) });
  const shown = { here: el.screenTools.contains(el.zoom) && !el.measurePanel.contains(el.zoom), visible: !!zoom.offsetParent,
                  afterClear: el.clearButton.compareDocumentPosition(zoom) === Node.DOCUMENT_POSITION_FOLLOWING };
  const withIt = read();
  zoom.style.display = 'none'; await wait(60); const without = read(); zoom.style.display = '';
  // The null: the knob's name and reading shown beside it, as a row would show them.
  const st = document.createElement('style');
  st.textContent = '#screenZoom > .menu-row.knob-row { width: auto !important; } #screenZoom .menu-label, #screenZoom .reading { position: static !important; width: auto !important; height: auto !important; clip-path: none !important; margin: 0 6px; }';
  document.head.appendChild(st); await wait(60); const labelled = read(); st.remove(); await wait(60);
  const at = (v) => { el.zoom.value = String(v); el.zoom.dispatchEvent(new Event('input', { bubbles: true })); };
  at(24); await wait(100); const zoomed = read(); at(0); await wait(60);
  return { shown, withIt, without, labelled, zoomed };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    bad = []
    nulls = []
    for w, h in WINDOWS:
        p = b.new_page(viewport={"width": w, "height": h})
        p.on("pageerror", lambda e: bad.append(str(e)))
        p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500); p.keyboard.press("Escape"); p.wait_for_timeout(200)
        r = p.evaluate(BOXES, None)
        label = "%dx%d" % (w, h)
        check("%s: the zoom is on the toolbar, after Clear, and out of Scope & measure" % label,
              r["shown"]["here"] and r["shown"]["visible"] and r["shown"]["afterClear"], str(r["shown"]))
        check("%s: the toolbar and the screen are the same to the pixel with it as without it" % label,
              r["withIt"] == r["without"], "%s against %s" % (r["withIt"], r["without"]))
        check("%s: and turning it from 1x to 64x moves neither" % label, r["zoomed"] == r["withIt"], "%s against %s" % (r["zoomed"], r["withIt"]))
        nulls.append(r["labelled"] != r["without"])
        p.close()
    null("the knob with its name and reading shown takes room at some window", any(nulls), str(nulls))

    p = b.new_page(viewport={"width": 1400, "height": 900})
    p.on("pageerror", lambda e: bad.append(str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500); p.keyboard.press("Escape"); p.wait_for_timeout(200)
    got = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setEnlarged(true); await wait(200);
      const enlarged = el.screenFrame.contains(el.zoom) && !!document.getElementById('screenZoom').offsetParent;
      setEnlarged(false); await wait(200);
      const shown = showControl('zoom'); await wait(100);
      const opened = { measure: !el.measurePanel.hidden, settings: !document.getElementById('menuPanel').hidden };
      const found = searchFor('zoom').map((r) => [r.label, r.crumb]);
      return { enlarged, shown, opened, found };
    }""")
    check("the zoom goes into Enlarge's frame with the screen", got["enlarged"], str(got))
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
