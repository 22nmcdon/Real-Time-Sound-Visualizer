"""Stage L's drawing: a figure drawn with the pointer on the X-Y screen.

Against the way it would fail:

- a drawing that does not land where it was drawn: every stored point, sent
  forward through the screen's own mapping - amplitude, rotation, full
  scale, zoom - comes out under the pointer that made it, with the figure
  turned a quarter and zoomed as well as plain;
- a generator that draws something else: every sample it draws lies on the
  drawing;
- a pointer that still does its other jobs while drawing, or has lost them
  after: the measuring cursors stay put while drawing is on and move again
  once it is off;
- noise kept as drawing: moves smaller than the pen's step add nothing, and
  a tap adds no stroke;
- a drawing that grows without end: it stops at its limit and says so;
- controls that lie: turning drawing on goes to X-Y, Clear empties it, and
  choosing another figure turns drawing off;
- a code that loses it: the strokes come back exactly, and a code without
  them has none.
"""
import math, os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)

# The screen's forward mapping, written out as drawXY does it: turned first,
# placed second, then zoomed onto the graticule.
FORWARD = """(pts) => {
  const cx = plot.x + plot.w / 2, cy = plot.y + plot.h / 2, scale = (plot.w / 2) * state.zoom;
  const [fx, fy] = state.xyPair, amp = genSettings().amp, { cos, sin } = turnOf(rotateTurns());
  return pts.map(([x, y]) => {
    const l = x * amp, r = y * amp, rx = l * cos - r * sin, ry = l * sin + r * cos;
    return [cx + (rx * gainOf(fx) + state.channels[fx].offset) * scale,
            cy - (ry * gainOf(fy) + state.channels[fy].offset) * scale];
  });
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    setup = p.evaluate("""() => {
      el.genMode.value = 'figure'; el.genMode.dispatchEvent(new Event('change'));
      setDisplay('yt');
      el.figure.value = 'Drawn'; el.figure.dispatchEvent(new Event('change'));
      const before = state.display;
      el.figDrawOn.click();
      return { before, after: state.display, pressed: el.figDrawOn.getAttribute('aria-pressed'),
               row: !el.figDrawRow.hidden, note: el.figPathNote.textContent };
    }""")
    p.wait_for_timeout(300)
    check("turning drawing on goes to X-Y, and the row and its note say what to do",
          setup["before"] == "yt" and setup["after"] == "xy" and setup["pressed"] == "true" and setup["row"]
          and setup["note"].startswith("Press On the screen"), str(setup))

    def screen():
        return p.evaluate("""() => { const r = el.trace.getBoundingClientRect();
          return { left: r.left, top: r.top, x: plot.x, y: plot.y, w: plot.w, h: plot.h }; }""")

    def stroke(path, steps=12):
        """Draws a polyline given in fractions of the graticule, -1 to 1 either way."""
        s = screen()
        def at(u, v):
            return (s["left"] + s["x"] + s["w"] / 2 + u * s["w"] / 2, s["top"] + s["y"] + s["h"] / 2 - v * s["h"] / 2)
        px = []
        x, y = at(*path[0]); p.mouse.move(x, y); p.mouse.down(); px.append((x - s["left"], y - s["top"]))
        for (u0, v0), (u1, v1) in zip(path, path[1:]):
            for k in range(1, steps + 1):
                x, y = at(u0 + (u1 - u0) * k / steps, v0 + (v1 - v0) * k / steps)
                p.mouse.move(x, y); px.append((x - s["left"], y - s["top"]))
        p.mouse.up()
        return px

    print("\n--- where it lands ---")
    results = {}
    # Amplitudes other than one, and in the second case offsets and full scales
    # other than nought: at the identity, a mapping that forgot one of them
    # lands under the pointer all the same - the mutation pass showed the
    # offset and the gain surviving exactly that way.
    for label, pre in [("plain", "state.rotate = 0; el.zoom.value = '0'; el.zoom.dispatchEvent(new Event('input')); el.amp.value = '80';"),
                       ("turned and zoomed", "state.rotate = 0.25; el.zoom.value = '6'; el.zoom.dispatchEvent(new Event('input')); el.amp.value = '120';"
                        + " state.channels[0].offset = 0.08; state.channels[1].offset = -0.06;"
                        + " state.channels[0].fsDb = -6; state.channels[1].fsDb = -3;")]:
        p.evaluate("() => { el.figDrawClear.click(); %s el.amp.dispatchEvent(new Event('input')); }" % pre)
        p.wait_for_timeout(300)
        a = stroke([(-0.3, -0.2), (0.2, 0.3), (0.3, -0.1)])
        c = stroke([(-0.2, 0.25), (-0.05, 0.3)])
        got = p.evaluate("(forward) => { const f = eval(forward); return { strokes: figDrawing.strokes, px: figDrawing.strokes.map(f), zoom: state.zoom, gain: gainOf(0) }; }", FORWARD)
        worst = 0
        for drawn_px, mouse_px in zip(got["px"], [a, c]):
            for q in drawn_px:
                worst = max(worst, min(math.hypot(q[0] - m[0], q[1] - m[1]) for m in mouse_px))
        results[label] = (len(got["strokes"]), worst, got["zoom"], round(got["gain"], 3))
        print("    %s: %d strokes, farthest point %.2f px from the pointer, zoom %.2f" % (label, len(got["strokes"]), worst, got["zoom"]))
    check("every point, sent forward through the screen's mapping, lands under the pointer that drew it",
          results["plain"][0] == 2 and results["plain"][1] < 1.0, str(results["plain"]))
    check("and so it does turned a quarter, zoomed in, offset and at another full scale",
          results["turned and zoomed"][0] == 2 and results["turned and zoomed"][1] < 1.0
          and results["turned and zoomed"][2] > 1.5 and results["turned and zoomed"][3] > 1.5,
          str(results["turned and zoomed"]))

    p.evaluate("""() => { state.rotate = 0; el.zoom.value = '0'; el.zoom.dispatchEvent(new Event('input'));
      state.channels[0].offset = 0; state.channels[1].offset = 0; state.channels[0].fsDb = 0; state.channels[1].fsDb = 0; }""")

    print("\n--- what the generator draws ---")
    drawn = p.evaluate("""async () => {
      el.figureRate.value = '10'; el.figureRate.dispatchEvent(new Event('input'));
      await new Promise((r) => setTimeout(r, 1200));
      const [l, r] = state.source.getLatestWindow(8820);
      return { l: Array.from(l), r: Array.from(r), amp: genSettings().amp, path: genSettings().figPath,
               drawn: JSON.stringify(genSettings().figPath) === JSON.stringify(compilePath(figDrawing.strokes)) };
    }""")
    xy = drawn["path"]["xy"]
    segs = [(xy[2 * k], xy[2 * k + 1], xy[2 * k + 2], xy[2 * k + 3]) for k in range(len(xy) // 2 - 1)]
    off = max(min(seg_dist(x / drawn["amp"], y / drawn["amp"], *s) for s in segs) for x, y in zip(drawn["l"], drawn["r"]))
    check("the generator is sent the drawing, and every sample it draws lies on it",
          drawn["drawn"] and off < 1e-5, "%.2e off the drawing" % off)

    print("\n--- the pointer's other jobs, the pen, and the limit ---")
    jobs = p.evaluate("""() => { state.cursors = true; state.cursor.t1 = 0.25; return plot; }""")
    s = screen()
    # On the first time cursor, a quarter of the way across.
    cx, cy = s["left"] + s["x"] + 0.25 * s["w"], s["top"] + s["y"] + s["h"] * 0.5
    p.mouse.move(cx, cy); p.mouse.down(); p.mouse.move(cx + 60, cy, steps=6); p.mouse.up()
    held = p.evaluate("() => state.cursor.t1")
    p.evaluate("() => el.figDrawOn.click()")
    p.mouse.move(cx, cy); p.mouse.down(); p.mouse.move(cx + 60, cy, steps=6); p.mouse.up()
    moved = p.evaluate("() => state.cursor.t1")
    p.evaluate("() => { state.cursors = false; el.figDrawOn.click(); }")
    check("while drawing the cursors stay put, and once drawing is off they move again",
          held == 0.25 and moved > 0.25 + 0.05, "%.3f then %.3f" % (held, moved))

    pen = p.evaluate("""() => {
      el.figDrawClear.click();
      const before = figDrawing.strokes.length;
      return before;
    }""")
    s = screen()
    x0, y0 = s["left"] + s["x"] + s["w"] / 2, s["top"] + s["y"] + s["h"] / 2
    # A tap.
    p.mouse.move(x0, y0); p.mouse.down(); p.mouse.up()
    tap = p.evaluate("() => figDrawing.strokes.length")
    # A stroke of tiny moves, each far less than the pen's step, then one big one.
    p.mouse.move(x0, y0); p.mouse.down()
    for k in range(1, 30): p.mouse.move(x0 + k * 0.02, y0)
    p.mouse.move(x0 + 80, y0); p.mouse.up()
    tiny = p.evaluate("() => figDrawing.strokes.map((s) => s.length)")
    check("a tap adds no stroke, and moves smaller than the pen's step add no points",
          pen == 0 and tap == 0 and tiny == [2], "tap %d; stroke lengths %s" % (tap, tiny))

    def fill_to(n):
        p.evaluate("""(n) => { figDrawing.full = false;
          figDrawing.strokes = [Array.from({ length: n }, (_, i) => [i / DRAWN_MOST, 0])]; }""", n)
        p.mouse.move(x0, y0 + 40); p.mouse.down(); p.mouse.move(x0 + 100, y0 + 60, steps=10); p.mouse.up()
        return p.evaluate("""() => ({ total: figDrawing.strokes.reduce((n, s) => n + s.length, 0),
                                      strokes: figDrawing.strokes.length, note: el.figPathNote.textContent })""")
    most = p.evaluate("() => DRAWN_MOST")
    # Two short of the limit: the stroke gets its two points and stops there.
    # One short: no stroke fits in one point, so the drawing ends one short and
    # says it is full. The first version of this check expected it to reach
    # the limit from there, which nothing could.
    two, one = fill_to(most - 2), fill_to(most - 1)
    check("a drawing stops exactly at its limit and says so, and keeps no stroke it has no room for",
          two["total"] == most and two["strokes"] == 2 and one["total"] == most - 1 and one["strokes"] == 1
          and two["note"].startswith("That is as much as a drawing holds")
          and one["note"].startswith("That is as much as a drawing holds"),
          "%s / %s" % ({k: two[k] for k in ("total", "strokes")}, {k: one[k] for k in ("total", "strokes")}))

    print("\n--- the controls and the code ---")
    code = p.evaluate("""() => {
      el.figDrawClear.click();
      figDrawing.strokes = [[[0.1, 0.2], [-0.3, 0.4], [0.5, -0.6]], [[0, 0], [0.25, 0.125]]];
      drawnCompile(); syncFigurePath();
      const cleared = (() => { const keep = figDrawing.strokes; el.figDrawClear.click();
        const out = [figDrawing.strokes.length, genSettings().figPath]; figDrawing.strokes = keep; drawnCompile(); syncFigurePath(); return out; })();
      const snap = snapshot();
      restore({});
      const bare = figDrawing.strokes.length;
      restore(snap);
      const back = JSON.stringify(figDrawing.strokes);
      el.figDrawOn.click();
      const wasOn = figDrawing.on;
      el.figure.value = 'Circle'; el.figure.dispatchEvent(new Event('change'));
      return { code: snap.figDrawn, cleared, bare, back, wasOn, offAfter: figDrawing.on,
               pressed: el.figDrawOn.getAttribute('aria-pressed'), cursor: el.trace.style.cursor };
    }""")
    print("    %s" % {k: code[k] for k in ("code", "cleared", "bare", "wasOn", "offAfter")})
    check("Clear empties the drawing and the generator draws nothing",
          code["cleared"] == [0, None], str(code["cleared"]))
    check("a code carries the strokes exactly, a code without them has none, and they come back",
          code["code"] == "0.1,0.2 -0.3,0.4 0.5,-0.6;0,0 0.25,0.125" and code["bare"] == 0
          and code["back"] == "[[[0.1,0.2],[-0.3,0.4],[0.5,-0.6]],[[0,0],[0.25,0.125]]]",
          "%s / %d" % (code["code"], code["bare"]))
    check("choosing another figure turns drawing off, and the pointer goes back to what it was",
          code["wasOn"] is True and code["offAfter"] is False and code["pressed"] == "false" and code["cursor"] == "",
          str({k: code[k] for k in ("wasOn", "offAfter", "pressed", "cursor")}))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
