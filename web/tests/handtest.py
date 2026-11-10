"""Bend the figure by hand (P6c step 2): grab the figure in X-Y and pull, and
it bends where you took hold - the grab sets Bend at to the moment of the
cycle the grabbed point is, and the pull sets Bend to whatever brings the
figure nearest the hand. Nothing is sent but the two sliders' own input
events, so the knob and the hand are one control.

Every press here is a real one, page.mouse or a touch through the browser's
own input, never a handler called. The fixture is a sine against itself a
quarter cycle on - X = sin t, Y = cos t, a circle - because there the moment
of every point is known without the page: it is atan2(X, Y). A circle is
the figure a rotation cannot see, but nothing here is a rotation: the bend
moves each lane in time at its own phase, which a circle shows plainly
everywhere but its four extremes, and the pulls are made on its diagonals
for that reason (a phase change never takes a wave past its own peak, so at
an extreme nothing can move outward - which is checked too, as a pull that
must do nothing).

Against the way it would fail:

- a moment that is not the grabbed point's: on the four diagonals Bend at is
  atan2(X, Y) of the grabbed sample to two hundredths; null, the angle
  counted the other way round fails the same tolerance. On every plain
  shape, the lane read at the phase the page found for it is the shape
  itself (correlation over 0.99); null, half a cycle out is not;
- a pull not followed, or followed where it cannot be: the circle stays on
  its centre since its offset is taken off (9 Nov), so pulled inward on the
  north-east diagonal Bend moves and the figure ends at least twice as near
  the pointer as it began (null, at nought it does not); pulled outward
  there no bend reaches, Bend stays and the hand's mark says it has no
  hold; at the right-hand extreme the centred figure reaches out, so
  outward is followed there, Bend positive;
- a press anywhere being a grab: a press at the circle's middle, and one 24
  pixels off the line, change nothing; one 10 pixels off takes hold; a
  click without a pull changes nothing (null, the same press pulled does);
- double-click not resetting: on the figure it puts Bend to nought; null,
  off the figure it leaves it;
- the reticle and the cursors losing their drags: the photocell's reticle,
  sitting on the figure, drags itself and bends nothing (null: with its
  presses passed through to the screen, the same drag bends); the cursors
  drag in Y-T (null: with them off the same drag moves nothing), and in X-Y,
  where they are not drawn, they no longer catch a press on the figure;
- the wrong layer: split, a grab on B's figure moves B's Bend and Bend at
  and not A's, and puts the panel on B; null, a grab on A's moves A's;
- a touch scrolling the page: a finger dragged on the figure bends it and
  the page stays put; null, the same finger dragged where there is no
  figure scrolls it;
- the drag never reaching the site's instrument: on the default page the
  compiled instrument draws the pulled figure, nearer the pointer; null,
  the figure before the pull fails the same measure.
"""
import math, os, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    check("null: " + name, red, detail)

# A sine against itself a quarter on, by hand: the X-Y button and the menus.
SETUP = """async (shape) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  el.dispXY.click();
  el.shape.value = shape; el.shape.dispatchEvent(new Event('change', { bubbles: true }));
  el.oscBend.value = '0'; el.oscBend.dispatchEvent(new Event('input', { bubbles: true }));
  el.oscBendAt.value = '25'; el.oscBendAt.dispatchEvent(new Event('input', { bubbles: true }));
  await wait(500);
}"""

# Where a figure's samples are on the page, worked out here from the lanes
# and the graticule rather than asked of the code under test: unturned, no
# offsets, the page's own full scale.
FIGURE = """(figure) => {
  const pairs = sourceFigures() || [state.xyPair];
  const [fx, fy] = pairs[figure];
  const ch = xyView.frame.channels, rect = el.trace.getBoundingClientRect();
  const cx = plot.x + plot.w / 2, cy = plot.y + plot.h / 2, s = plot.w / 2 * state.zoom;
  const gx = gainOf(fx), gy = gainOf(fy), out = [];
  for (let i = 0; i < Math.min(ch[fx].length, ch[fy].length); i++) {
    out.push([rect.left + cx + ch[fx][i] * gx * s, rect.top + cy - ch[fy][i] * gy * s, ch[fx][i], ch[fy][i]]);
  }
  return { pts: out, cx: rect.left + cx, cy: rect.top + cy };
}"""

VALUES = """() => ({ bend: +el.oscBend.value, at: +el.oscBendAt.value,
  a: [genSettings(0).warp, genSettings(0).warpAt], b: genSettings(1) ? [genSettings(1).warp, genSettings(1).warpAt] : null,
  edit: editLayer() })"""

def pull(p, x0, y0, dx, dy, steps=12):
    p.mouse.move(x0, y0); p.mouse.down()
    for k in range(1, steps + 1):
        p.mouse.move(x0 + dx * k / steps, y0 + dy * k / steps); p.wait_for_timeout(16)
    p.wait_for_timeout(80)
    p.mouse.up()

def pull_hold(p, x0, y0, dx, dy, steps=12):
    """A pull, and whether the hand's mark had hold at its end, read before
    letting go (the mark hides on release)."""
    p.mouse.move(x0, y0); p.mouse.down()
    for k in range(1, steps + 1):
        p.mouse.move(x0 + dx * k / steps, y0 + dy * k / steps); p.wait_for_timeout(16)
    p.wait_for_timeout(80)
    hold = p.evaluate("() => document.getElementById('bendMark').dataset.hold || null")
    p.mouse.up()
    return hold

def nearest(pts, x, y):
    return min(math.hypot(a[0] - x, a[1] - y) for a in pts)

def diagonal(fig, sx, sy):
    """The figure's sample furthest along (sx, sy) from the middle, screen y down."""
    return max(fig["pts"], key=lambda q: (q[0] - fig["cx"]) * sx + (q[1] - fig["cy"]) * sy)

def moment_of(q):
    return (math.atan2(q[2], q[3]) / (2 * math.pi)) % 1

def cyc(a, b):
    d = abs(a - b) % 1
    return min(d, 1 - d)

def reset(p, bend=0, at=25):
    p.evaluate("""([b, a]) => { handSlider('oscBend', b); handSlider('oscBendAt', a); }""", [bend, at])
    p.wait_for_timeout(450)

def open_page(b, query, **kw):
    p = b.new_page(**({"viewport": {"width": 1400, "height": 900}} | kw))
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html?{query}"); p.wait_for_timeout(1000)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)
    return p, bad

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p, bad = open_page(b, "picture=0&brain=js")
    p.evaluate(SETUP, "sine")

    print("\n--- the grab's moment is the grabbed point's ---")
    corners = [("north-east", 1, -1), ("north-west", -1, -1), ("south-west", -1, 1), ("south-east", 1, 1)]
    for name, sx, sy in corners:
        reset(p)
        fig = p.evaluate(FIGURE, 0)
        q = diagonal(fig, sx, sy)
        want = moment_of(q)
        # A short pull inward, which the bend can always follow, to get past a click.
        pull(p, q[0], q[1], -sx * 12, -sy * 12)
        got = p.evaluate(VALUES)["at"] / 100
        check("grabbed on the %s diagonal, Bend at is that sample's moment" % name, cyc(got, want) <= 0.02,
              "Bend at %.2f, atan2(X, Y) %.3f" % (got, want))
        wrong = (1 - want) % 1
        null("the angle counted the other way round fails the same tolerance on the %s" % name, cyc(got, wrong) > 0.02,
             "-atan2(X, Y) %.3f" % wrong)

    # Every plain shape: the lane read at the phase the page found is the shape.
    for shape in ["triangle", "square", "ramp", "pulse", "harmonic", "morph"]:
        p.evaluate(SETUP, shape)
        r = p.evaluate("""() => {
          const fig = xyView.figures[0], [l, r] = bendLanes(fig), at = Math.floor(l.length / 2);
          const m = bendModel({ figure: 0, at, lanes: [l, r] }, 0), wave = bendWave(genSettings());
          const corr = (lane, shift) => { let sxy = 0, sxx = 0, syy = 0;
            for (let n = 0; n < lane.x.length; n++) { const v = wave(lane.theta + shift + lane.w * (n - at));
              sxy += v * lane.x[n]; sxx += v * v; syy += lane.x[n] * lane.x[n]; }
            return sxy / Math.sqrt(sxx * syy); };
          return { found: m.lanes.map((lane) => corr(lane, 0)), half: m.lanes.map((lane) => corr(lane, Math.PI)) };
        }""")
        check("on the %s, each lane read at the phase found for it is the shape" % shape,
              min(r["found"]) > 0.99, str([round(v, 4) for v in r["found"]]))
        null("half a cycle out, it is not (the %s)" % shape, max(r["half"]) < 0.9,
             str([round(v, 3) for v in r["half"]]))
    p.evaluate(SETUP, "sine")

    print("\n--- the figure follows the hand ---")
    # Since 9 Nov the bend's offset is taken off, so the circle stays on its
    # centre, and bent at a diagonal's own moment it pinches inward there
    # whichever way (to 0.91 of its radius at 0.6, 0.98 at 0.3). Until then
    # this pulled outward and wanted Bend negative: that bulge was the offset
    # sliding the whole figure towards the hand, the same offset that thumped
    # under automation. So the pull that is followed is inward - by either
    # sign nearly as well (-70 and +70 reach within two pixels of each
    # other), so the sign is not held - and the one outward has nothing to
    # follow and must say so.
    reset(p)
    fig = p.evaluate(FIGURE, 0)
    q = diagonal(fig, 1, -1)
    ux, uy = (q[0] - fig["cx"]), (q[1] - fig["cy"])
    L = math.hypot(ux, uy); ux, uy = ux / L, uy / L
    tx, ty = q[0] - ux * 30, q[1] - uy * 30
    before = nearest(fig["pts"], tx, ty)
    hold_in = pull_hold(p, q[0], q[1], -ux * 30, -uy * 30)
    v = p.evaluate(VALUES)
    check("pulled inward on the north-east diagonal, Bend moves a long way and the hand's mark has hold",
          abs(v["bend"]) >= 20 and hold_in == "true", "%s, hold %s" % (v, hold_in))
    p.wait_for_timeout(500)
    after = nearest(p.evaluate(FIGURE, 0)["pts"], tx, ty)
    check("and the figure ends at least twice as near the pointer as it began",
          after <= before / 2, "%.1f px to %.1f px" % (before, after))
    chosen = v["bend"]
    shown = p.evaluate("() => [el.oscBendValue.textContent, el.oscBendAtValue.textContent]")
    check("the sliders' readings say what the hand set",
          shown == [("+" if chosen > 0 else "\u2212") + str(abs(chosen)) + "%", str(round(v["at"] * 3.6)) + "\u00b0"],
          str(shown))
    reset(p, 0, v["at"])
    undone = nearest(p.evaluate(FIGURE, 0)["pts"], tx, ty)
    null("with Bend put back to nought the figure fails the same measure", not (undone <= before / 2), "%.1f px" % undone)

    reset(p)
    fig = p.evaluate(FIGURE, 0)
    q = diagonal(fig, 1, -1)
    hold_out = pull_hold(p, q[0], q[1], ux * 30, uy * 30)
    v = p.evaluate(VALUES)
    check("pulled outward on the same diagonal, where no bend reaches, Bend stays at nought and the mark has no hold",
          abs(v["bend"]) <= 2 and hold_out == "false", "%s, hold %s" % (v, hold_out))
    null("the inward pull's mark, which had hold, fails the same check", not (hold_in == "false"), str(hold_in))

    # At the circle's right-hand extreme the centred figure reaches 1 + J1(a)
    # on one side - the offset taken off moves its peak - so outward there IS
    # followed, Bend positive at that moment. Until 9 Nov the figure could not
    # reach past its edge anywhere and this pull had to do nothing.
    reset(p)
    fig = p.evaluate(FIGURE, 0)
    q = max(fig["pts"], key=lambda k: k[0])
    before = nearest(fig["pts"], q[0] + 40, q[1])
    hold_e = pull_hold(p, q[0], q[1], 40, 0)
    v = p.evaluate(VALUES)
    p.wait_for_timeout(500)
    after = nearest(p.evaluate(FIGURE, 0)["pts"], q[0] + 40, q[1])
    check("pulled outward at the circle's right-hand extreme, Bend goes positive, the figure reaches out and the mark holds",
          v["bend"] >= 20 and after <= before / 2 and hold_e == "true",
          "%s, %.1f px to %.1f px, hold %s" % (v, before, after, hold_e))
    null("the same check against the opposite sign", not (-v["bend"] >= 20), str(-v["bend"]))

    # One signal on both lanes draws a line, and the bend only slides it along
    # itself: every Bend reaches the pointer equally, and the one already set must stay.
    reset(p, 30, 40)
    p.evaluate("""() => { el.phase.value = '0'; el.phase.dispatchEvent(new Event('input', { bubbles: true })); }""")
    p.wait_for_timeout(450)
    fig = p.evaluate(FIGURE, 0)
    q = diagonal(fig, 1, -1)
    spread = max(abs((k[0] - fig["cx"]) + (k[1] - fig["cy"])) for k in fig["pts"])
    pull(p, q[0], q[1], -25, -25)
    v = p.evaluate(VALUES)
    check("the fixture: one signal on both lanes draws a diagonal line", spread < 2, "%.2f px off it" % spread)
    check("pulled across a line, which no bend can move off itself, Bend stays where it was", v["bend"] == 30, str(v))
    p.evaluate("""() => { el.phase.value = '90'; el.phase.dispatchEvent(new Event('input', { bubbles: true })); }""")
    p.wait_for_timeout(300)

    print("\n--- what is not a grab ---")
    reset(p, 30, 40)
    fig = p.evaluate(FIGURE, 0)
    pull(p, fig["cx"], fig["cy"], 60, -60)
    v = p.evaluate(VALUES)
    check("a press at the circle's middle, a radius from the figure, changes nothing", (v["bend"], v["at"]) == (30, 40), str(v))
    q = diagonal(fig, 1, -1)
    for off, takes in [(24, False), (10, True)]:
        reset(p, 30, 40)
        fig = p.evaluate(FIGURE, 0)
        q = diagonal(fig, 1, -1)
        d = math.hypot(q[0] - fig["cx"], q[1] - fig["cy"])
        x0, y0 = q[0] + (q[0] - fig["cx"]) / d * off, q[1] + (q[1] - fig["cy"]) / d * off
        pull(p, x0, y0, -(q[0] - fig["cx"]) / d * 40, -(q[1] - fig["cy"]) / d * 40)
        v = p.evaluate(VALUES)
        moved = (v["bend"], v["at"]) != (30, 40)
        check("a press %d px off the line %s" % (off, "takes hold" if takes else "changes nothing"), moved == takes, str(v))
    reset(p, 30, 40)
    fig = p.evaluate(FIGURE, 0)
    q = diagonal(fig, 1, -1)
    # A hand's click wobbles: two pixels while held, under the three a pull needs.
    p.mouse.move(q[0], q[1]); p.mouse.down(); p.mouse.move(q[0] - 1, q[1] + 1); p.wait_for_timeout(30)
    p.mouse.move(q[0] - 2, q[1]); p.wait_for_timeout(60); p.mouse.up(); p.wait_for_timeout(100)
    v = p.evaluate(VALUES)
    check("a click on the figure that wobbles two pixels changes nothing", (v["bend"], v["at"]) == (30, 40), str(v))
    pull(p, q[0], q[1], -10, 10)
    v2 = p.evaluate(VALUES)
    null("the same press pulled does", (v2["bend"], v2["at"]) != (30, 40), str(v2))

    print("\n--- double-click puts the bend off ---")
    reset(p, 45, 40)
    fig = p.evaluate(FIGURE, 0)
    p.mouse.dblclick(fig["cx"], fig["cy"]); p.wait_for_timeout(100)
    off_fig = p.evaluate(VALUES)["bend"]
    null("a double-click off the figure leaves Bend where it was", off_fig == 45, str(off_fig))
    q = diagonal(fig, -1, 1)
    p.mouse.dblclick(q[0], q[1]); p.wait_for_timeout(100)
    v = p.evaluate(VALUES)
    check("a double-click on the figure puts Bend to nought, and leaves Bend at", v["bend"] == 0 and v["at"] == 40, str(v))

    print("\n--- the hand's cursor and its mark ---")
    reset(p)
    fig = p.evaluate(FIGURE, 0)
    q = diagonal(fig, 1, -1)
    p.mouse.move(fig["cx"], fig["cy"]); p.wait_for_timeout(50)
    far = p.evaluate("() => el.trace.style.cursor")
    p.mouse.move(q[0], q[1]); p.wait_for_timeout(50)
    near = p.evaluate("() => el.trace.style.cursor")
    check("the pointer shows a hand near the figure and the screen's own cursor away from it",
          near == "grab" and far == "", "near %r, far %r" % (near, far))
    p.mouse.down()
    for k in range(1, 6): p.mouse.move(q[0] - 3 * k, q[1] + 3 * k); p.wait_for_timeout(20)
    p.wait_for_timeout(60)
    mark = p.evaluate("""() => { const m = document.getElementById('bendMark'), r = m.getBoundingClientRect();
      return { hidden: m.hidden, x: r.left + r.width / 2, y: r.top + r.height / 2, colour: getComputedStyle(m).borderTopColor,
               gold: getComputedStyle(document.documentElement).getPropertyValue('--gold').trim(), cursor: el.trace.style.cursor }; }""")
    p.mouse.up(); p.wait_for_timeout(50)
    gone = p.evaluate("() => document.getElementById('bendMark').hidden")
    fig2 = p.evaluate(FIGURE, 0)
    check("while held, the mark shows at the grabbed moment, on the figure, and the cursor is a closed hand",
          not mark["hidden"] and nearest(fig2["pts"], mark["x"], mark["y"]) < 6 and mark["cursor"] == "grabbing",
          "mark %.0f,%.0f, %.1f px from the figure" % (mark["x"], mark["y"], nearest(fig2["pts"], mark["x"], mark["y"])))
    check("in the marker's gold", mark["colour"] == "rgb(176, 141, 87)" and mark["gold"].lower() == "#b08d57", str(mark))
    check("and let go, the mark goes", gone)

    print("\n--- the reticle and the cursors keep their drags ---")
    reset(p, 0, 25)
    p.evaluate("() => el.photoButton.click()"); p.wait_for_timeout(800)
    RET = """() => { const r = el.photoReticle.getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2, u: photo.u, v: photo.v, on: photo.on }; }"""
    ret = p.evaluate(RET)
    fig = p.evaluate(FIGURE, 0)
    on_fig = nearest(fig["pts"], ret["x"], ret["y"])
    pull(p, ret["x"], ret["y"], -25, 25)
    ret2 = p.evaluate(RET); v = p.evaluate(VALUES)
    check("the fixture: the reticle sits on the figure, within the grab's reach", ret["on"] and on_fig < 12, "%.1f px" % on_fig)
    check("the reticle on the figure drags itself and bends nothing",
          (ret2["u"], ret2["v"]) != (ret["u"], ret["v"]) and (v["bend"], v["at"]) == (0, 25), "%s -> %s, %s" % (ret, ret2, v))
    reset(p, 0, 25)
    ret = p.evaluate(RET)
    fig = p.evaluate(FIGURE, 0)
    q = min(fig["pts"], key=lambda k: math.hypot(k[0] - ret["x"], k[1] - ret["y"]))
    p.evaluate("() => { el.photoReticle.style.pointerEvents = 'none'; }")
    pull(p, q[0], q[1], -(q[0] - fig["cx"]) * 0.1, -(q[1] - fig["cy"]) * 0.1)
    v = p.evaluate(VALUES)
    p.evaluate("() => { el.photoReticle.style.pointerEvents = ''; el.photoButton.click(); }")
    null("with the reticle's presses passed through to the screen, the same place bends", (v["bend"], v["at"]) != (0, 25), str(v))

    reset(p, 0, 25)
    p.evaluate("() => { el.dispYT.click(); el.cursorsOn.checked = true; el.cursorsOn.dispatchEvent(new Event('change')); }")
    p.wait_for_timeout(300)
    CUR = """() => { const r = el.trace.getBoundingClientRect();
      return { x: r.left + plot.x + state.cursor.t1 * plot.w, y: r.top + plot.y + plot.h * 0.3, t1: state.cursor.t1 }; }"""
    c = p.evaluate(CUR)
    pull(p, c["x"], c["y"], 60, 0)
    c2 = p.evaluate(CUR)
    check("in Y-T the time cursor still drags", c2["t1"] > c["t1"] + 0.03, "%.3f -> %.3f" % (c["t1"], c2["t1"]))
    p.evaluate("() => { el.cursorsOn.checked = false; el.cursorsOn.dispatchEvent(new Event('change')); }")
    c3 = p.evaluate(CUR)
    pull(p, c3["x"], c3["y"], 60, 0)
    c4 = p.evaluate(CUR)
    null("with the cursors off, the same drag moves nothing", c4["t1"] == c3["t1"], "%.3f -> %.3f" % (c3["t1"], c4["t1"]))
    # Back to X-Y with the cursors on, and the time cursor laid across the figure's diagonal.
    p.evaluate("() => { el.cursorsOn.checked = true; el.cursorsOn.dispatchEvent(new Event('change')); el.dispXY.click(); }")
    p.wait_for_timeout(400)
    fig = p.evaluate(FIGURE, 0)
    q = diagonal(fig, -1, 1)
    p.evaluate("""(x) => { const r = el.trace.getBoundingClientRect(); state.cursor.t1 = (x - r.left - plot.x) / plot.w; }""", q[0])
    t_before = p.evaluate("() => state.cursor.t1")
    pull(p, q[0], q[1], 12, -12)
    v = p.evaluate(VALUES); t_after = p.evaluate("() => state.cursor.t1")
    check("in X-Y, where the cursors are not drawn, a press on the figure across a cursor's line bends it and leaves the cursor",
          (v["bend"], v["at"]) != (0, 25) and t_after == t_before, "%s, t1 %.3f -> %.3f" % (v, t_before, t_after))
    p.evaluate("() => { el.cursorsOn.checked = false; el.cursorsOn.dispatchEvent(new Event('change')); }")

    print("\n--- split, the grab bends the figure's own layer ---")
    p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      midiPanic(); setScreenKeys(true); setMidiMode('poly');
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      midi.layers.point = 60;
      el.midiLayerPair.value = 'each'; el.midiLayerPair.dispatchEvent(new Event('change'));
      for (const n of [48, 55, 72, 79]) midiNoteOn(n, 100);
      await wait(1200);
    }""")
    def lone(mine, other):
        """A sample of one figure at least 25 px from every sample of the other."""
        return max(mine["pts"][::3], key=lambda q: nearest(other["pts"][::3], q[0], q[1]))
    def voice_moment(fig, at, hz, rate):
        """Each held note's phase at sample `at` of the X lane, by fitting the
        lane to a sine and cosine at both notes' frequencies at once - known
        exactly, so this needs nothing of the page's but the samples."""
        x = np.array([k[2] for k in fig["pts"]])
        n = np.arange(len(x)) - at
        cols = []
        for f in hz:
            w = 2 * np.pi * f / rate
            cols += [np.sin(w * n), np.cos(w * n)]
        coef = np.linalg.lstsq(np.stack(cols, 1), x, rcond=None)[0]
        return [(math.atan2(coef[2 * k + 1], coef[2 * k]) / (2 * math.pi)) % 1 for k in (0, len(hz) - 1)]
    # The Oscillator, whose Bend this is, each hand's own (G6): linked, as a
    # split starts, a grab on either figure would bend both hands'.
    p.evaluate("() => { setLink('osc', false); for (const layer of [0, 1]) { genSet('warp', 0, layer); genSet('warpAt', 0.25, layer); } }")
    p.wait_for_timeout(500)
    # Held still: an equal fifth turns (B's at 1.8 a second), and the samples
    # fitted here have to be the ones under the press.
    p.evaluate("() => setRunning(false)"); p.wait_for_timeout(100)
    for name, figure in [("B", 1), ("A", 0)]:
        layers0 = p.evaluate(VALUES)
        fa, fb = p.evaluate(FIGURE, 0), p.evaluate(FIGURE, 1)
        mine, other = (fb, fa) if figure == 1 else (fa, fb)
        q = lone(mine, other)
        sep = nearest(other["pts"], q[0], q[1])
        # The notes' frequencies as the keyboard tuned them, and the rate the lanes run at.
        notes, rate = p.evaluate("(layer) => [polyVoices(layer).map((v) => v.freq).sort((a, b) => a - b), xyView.frame.rate]", figure)
        bass, _ = voice_moment(mine, mine["pts"].index(q), notes, rate)
        d = max(1.0, math.hypot(q[0] - mine["cx"], q[1] - mine["cy"]))
        pull(p, q[0], q[1], -(q[0] - mine["cx"]) / d * 15, -(q[1] - mine["cy"]) / d * 15)
        layers1 = p.evaluate(VALUES)
        own, theirs = ("b", "a") if figure == 1 else ("a", "b")
        moved_own = layers1[own] != layers0[own]
        moved_other = layers1[theirs] != layers0[theirs]
        got = layers1[own][1]
        check("on %s's chord, Bend at is the moment of the bass, the voice X leans onto" % name, cyc(got, bass) <= 0.03,
              "Bend at %.2f, the bass at %.3f" % (got, bass))
        null("the bass's moment a quarter cycle out, a shape's offset forgotten, fails the same tolerance (%s)" % name,
             cyc(got, bass + 0.25) > 0.03, "%.3f" % ((bass + 0.25) % 1))
        if figure == 1:
            check("a grab on B's figure (%.0f px from A's) moves B's Bend and Bend at, not A's, and puts the panel on B" % sep,
                  moved_own and not moved_other and layers1["edit"] == 1, "%s -> %s" % (layers0, layers1))
        else:
            null("a grab on A's figure (%.0f px from B's) moves A's, not B's, and puts the panel back on A" % sep,
                 moved_own and not moved_other and layers1["edit"] == 0, "%s -> %s" % (layers0, layers1))
    p.evaluate("""() => { setRunning(true); midiPanic(); el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change')); setMidiMode('mono'); }""")
    check("no page errors on the page's own brain", not bad, "; ".join(bad[:3]))
    p.close()

    print("\n--- a finger on the figure bends it and does not scroll ---")
    ctx = b.new_context(viewport={"width": 420, "height": 800}, has_touch=True, is_mobile=True)
    t = ctx.new_page()
    tbad = []
    t.on("pageerror", lambda e: tbad.append("pageerror: " + str(e)))
    t.goto(f"file://{ART}/scope.html?picture=0&brain=js"); t.wait_for_timeout(1000)
    if t.locator("#helpClose").is_visible(): t.locator("#helpClose").click()
    t.evaluate(SETUP, "sine")
    t.evaluate("() => { el.trace.scrollIntoView({ block: 'center' }); }"); t.wait_for_timeout(300)
    cdp = ctx.new_cdp_session(t)
    def finger(x0, y0, dx, dy, steps=10):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
        for k in range(1, steps + 1):
            cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + dx * k / steps, "y": y0 + dy * k / steps}]})
            t.wait_for_timeout(20)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        t.wait_for_timeout(300)
    fig = t.evaluate(FIGURE, 0)
    q = diagonal(fig, 1, -1)
    s0 = t.evaluate("() => window.scrollY")
    finger(q[0], q[1], -12, 40)
    s1 = t.evaluate("() => window.scrollY"); v = t.evaluate(VALUES)
    check("a finger dragged on the figure bends it and the page does not move", (v["bend"], v["at"]) != (0, 25) and s1 == s0,
          "%s, scroll %d -> %d" % (v, s0, s1))
    fig = t.evaluate(FIGURE, 0)
    rect = t.evaluate("() => el.trace.getBoundingClientRect().toJSON()")
    fx, fy = rect["left"] + 8, rect["top"] + 8
    if nearest(fig["pts"], fx, fy) < 40: fx, fy = fig["cx"], fig["cy"]
    finger(fx, fy, 0, -120)
    s2 = t.evaluate("() => window.scrollY")
    null("the same finger dragged where there is no figure scrolls the page", s2 != s1, "scroll %d -> %d" % (s1, s2))
    check("no page errors on the phone", not tbad, "; ".join(tbad[:3]))
    ctx.close()

    print("\n--- the site's instrument draws what the hand pulled ---")
    p, bad = open_page(b, "picture=0")
    kind = p.evaluate("() => state.source.kind")
    p.evaluate(SETUP, "sine")
    reset(p)
    fig = p.evaluate(FIGURE, 0)
    q = diagonal(fig, 1, -1)
    ux, uy = (q[0] - fig["cx"]), (q[1] - fig["cy"])
    L = math.hypot(ux, uy); ux, uy = ux / L, uy / L
    tx, ty = q[0] - ux * 30, q[1] - uy * 30
    before = nearest(fig["pts"], tx, ty)
    want = moment_of(q)
    pull(p, q[0], q[1], -ux * 30, -uy * 30)
    v = p.evaluate(VALUES)
    p.wait_for_timeout(700)
    after = nearest(p.evaluate(FIGURE, 0)["pts"], tx, ty)
    check("the default page's generator is the compiled instrument", kind == "host", kind)
    check("pulled inward there, Bend at is the grabbed moment and Bend moves a long way",
          cyc(v["at"] / 100, want) <= 0.02 and abs(v["bend"]) >= 20, "%s, moment %.3f" % (v, want))
    check("and the instrument's figure ends at least twice as near the pointer", after <= before / 2,
          "%.1f px to %.1f px" % (before, after))
    reset(p, 0, v["at"])
    undone = nearest(p.evaluate(FIGURE, 0)["pts"], tx, ty)
    null("with Bend put back to nought by its slider, the instrument's figure fails the same measure",
         not (undone <= before / 2), "%.1f px" % undone)
    check("no page errors on the default page", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("the figure bends where the hand takes it, and only there")
