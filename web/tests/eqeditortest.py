"""The EQ drawn, and its editor (17 Nov, the owner's mockup, web/docs/mockups/eq/).

What would go wrong, and what is checked for it, each check with its null:

- a point off the line it is drawn on. Each point sits on the drawn total
  curve at its band's frequency (the owner's call): for six settings - among
  them a shelf over the mid and a narrow mid on a high shelf - at 1400x900
  and 960x600, in the editor and on the line's small curve, the point's
  centre against the drawn path's height at its x, read from the path's own
  coordinates, within half a pixel. The null is the mockup's first
  placement, the band's own full gain, which misses on every shelf;
- a curve that is not what is heard. The page's response against the core's
  own (core/tests/tools/eq_response_cpp.cpp, Plane::eqBand, the filter the
  engine runs) over six settings, 241 frequencies each, at 48 and 44.1 kHz,
  to 0.01 dB. The null is the page's answer at the other rate, which misses
  where a shelf is high;
- a point out of reach (22 Nov, the owner lost one under the plot's foot): the
  plot's height is the gains' range exactly, +12 to -16 dB, and a point is
  held to its edge where the bands together take the curve past it. Eight
  cases put points on an edge or a corner - the mid at either gain's end at
  either end of the range, and each shelf at an end pushed past the edge by
  a wide mid beside it - at the six windows fittest.py measures, and each
  point must be under the pointer at its centre and all round its reach's
  rim, its reach inside the plot, the editor and the window, and on the
  edge it was taken to. The null is the same point where the old plot drew
  it, 2 dB past its foot, which the probes miss. Then with a real mouse, at
  1400x900 and 960x600: the mid's point dragged far past the foot and the
  right-hand edge lands at -16 dB and 20 kHz in the corner, and is grabbed
  again there; the high shelf's point goes all the way to the right (20 kHz)
  and the low shelf's to the left (20 Hz). EQ_SHOTS=<dir> keeps a screenshot
  of each;
- a point that moves a picture and not the instrument: dragged with a real
  mouse, the mid's point writes its knobs (Mid and Mid at), the engine is
  sent them, and the drag is one step in undo, made on release. The null is
  a drag on the plot away from any point, which writes nothing and is no step;
- moving the EQ while it is off leaving it off: a point dragged and a gain's
  knob turned, by a real hand, each switch it on. The null, in eqtest.py,
  is the same knob moved from code, which leaves it off;
- the keyboard: Tab reaches a point; an arrow moves its gain half a decibel,
  Shift and an arrow its place four of its thousand steps; ] widens the mid; Shift+F10 opens
  its menu, whose Reset names where it starts and whose Esc closes the menu
  and leaves the editor open, and Esc again closes the editor. Double-click
  resets a point. Each read from the knobs, the values;
- the line's small curve: flat and grey with the EQ off, the curve when on,
  and both hands when they differ - the other dashed in its ink. The null
  is the hands linked, which draws one;
- the live spectrum behind the curve: drawn and updated only while the
  editor is open, from the Spect view's analysis of a note held, and what
  it costs a frame, measured: under 2 ms a frame on average. The null is the
  editor shut, where no frame of it is made and its canvas is empty.
"""
import os, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
COMPILED_CORE = os.path.join(HERE, "compiled_core.js")
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + str(detail)) if detail else ""))
    if not ok: fails.append(name)
def null(name, ok, detail=""):
    check("null: " + name, ok, detail)

# gains in tenths of a dB, each band's frequency in hertz (set on its knob's nearest place, eqPos, since the
# places became a thousand over 20 Hz to 20 kHz on 22 Nov), width in tenths of an octave, as the knobs hold them
SETTINGS = [
    ("the shelves up", [30, 0, 30], [160, 1000, 4000], 10),
    ("the mockup's opening", [30, -40, 30], [160, 762, 4000], 14),
    ("a shelf over the mid", [120, 40, 0], [640, 437, 4000], 20),
    ("a narrow mid on a high shelf", [-60, 100, 90], [70, 8000, 3030], 2),
    ("a wide cut between two boosts", [90, -110, 90], [278, 1000, 2297], 40),
    ("the mid alone", [0, 65, 0], [160, 1000, 4000], 10),
    # Since 22 Nov: the deeper cut and the bands at the range's ends, the high shelf at the top and the low at the foot.
    ("the deepest cuts, the shelves at the ends", [-160, -160, -160], [20, 1000, 20000], 10),
    ("the bands crossed", [100, -50, -120], [5000, 300, 60], 20),
]
SET = """([g, hz, w]) => {
  setEqOn(true);
  const ids = [['eqLow', g[0]], ['eqMid', g[1]], ['eqHigh', g[2]], ['eqLowFreq', eqPos(0, hz[0])], ['eqMidFreq', eqPos(1, hz[1])],
               ['eqHighFreq', eqPos(2, hz[2])], ['eqMidWidth', w]];
  for (const [id, v] of ids) setControl(id, v);
}"""
MEASURE = """(which) => {
  const svg = which === 'plot' ? el.eqPlot : el.eqThumbSvg;
  const path = which === 'plot' ? document.getElementById('eqSumPath') : svg.querySelector('.eq-thumb-sum');
  const pts = path.getAttribute('d').match(/[ML][^ML]+/g).map((t) => t.slice(1).trim().split(/\\s+/).map(Number));
  const yAt = (x) => { for (let i = 1; i < pts.length; i++) if (pts[i][0] >= x) {
      const [x0, y0] = pts[i - 1], [x1, y1] = pts[i]; return x1 === x0 ? y1 : y0 + (y1 - y0) * (x - x0) / (x1 - x0); }
    return pts[pts.length - 1][1]; };
  const h = echoTarget('eq'), gains = [h.eqLow, h.eqMid, h.eqHigh];
  const dots = which === 'plot' ? Array.from(svg.querySelectorAll('.eq-pt .eq-ring')) : Array.from(svg.querySelectorAll('.eq-thumb-pt'));
  return dots.map((c, k) => {
    const cx = +c.getAttribute('cx'), cy = +c.getAttribute('cy');
    // The first placement, the band's own gain, on the same axis: the null.
    const ht = svg.clientHeight;
    const oldY = which === 'plot' ? eqEd.geo.y(gains[k]) : 3 + (EQ_DB_TOP - gains[k]) / (EQ_DB_TOP - EQ_DB_FOOT) * (ht - 6);
    // On the curve, or on the plot's edge where the bands together take the curve past it (22 Nov).
    const edge = which === 'plot' ? [eqEd.geo.y(EQ_DB_TOP), eqEd.geo.y(EQ_DB_FOOT)] : [3, ht - 3];
    const onCurve = Math.max(edge[0], Math.min(edge[1], yAt(cx)));
    return { band: k, gain: gains[k], miss: Math.abs(cy - onCurve), oldMiss: Math.abs(oldY - onCurve) };
  });
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    bad = []

    def page(w, h):
        p = b.new_page(viewport={"width": w, "height": h})
        p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
        p.add_init_script(path=COMPILED_CORE)
        p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(800)
        if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
        p.evaluate("() => { setView('bench'); setBenchTab('space'); }"); p.wait_for_timeout(200)
        return p

    print("\n--- each point on the curve it is drawn on ---")
    worst, shelves = 0.0, []
    for w, h in [(1400, 900), (960, 600)]:
        p = page(w, h)
        p.evaluate("() => openEqEditor()"); p.wait_for_timeout(200)
        for name, g, pos, wd in SETTINGS:
            p.evaluate(SET, [g, pos, wd]); p.wait_for_timeout(30)
            for which in ["plot", "thumb"]:
                for r in p.evaluate(MEASURE, which):
                    worst = max(worst, r["miss"])
                    if r["band"] != 1 and r["gain"] != 0: shelves.append((r["oldMiss"], "%dx%d %s %s band %d" % (w, h, name, which, r["band"])))
                    if r["miss"] > 0.5: check("%dx%d %s %s band %d on the curve" % (w, h, name, which, r["band"]), False, "%.3f px" % r["miss"])
        p.close()
    check("every point within half a pixel of the drawn path at its x, %d settings, both windows, editor and line" % len(SETTINGS), worst <= 0.5,
          "worst %.3f px" % worst)
    lo = min(shelves)
    null("the band's own gain misses on every shelf", lo[0] > 0.5, "smallest miss %.2f px (%s)" % lo)

    print("\n--- the curve against the core's ---")
    exe = os.path.join(tempfile.mkdtemp(), "eqresponse")
    subprocess.run(["g++", "-std=c++17", "-O1", "-I" + os.path.join(ROOT, "core", "include"),
                    os.path.join(ROOT, "core", "tests", "tools", "eq_response_cpp.cpp"), "-o", exe], check=True)
    # Places on today's knob (a thousand over 20 Hz to 20 kHz): the starts, and the ends both ways, the cut at -16 dB.
    CASES = [([3, 0, 3], [301, 567, 767], 1.0), ([3, -4, 3], [301, 528, 767], 1.4), ([12, 12, -16], [0, 1000, 1000], 0.2),
             ([-16, -16, 12], [1000, 0, 0], 4.0), ([0, 6.5, 0], [301, 567, 767], 1.0), ([0, 0, 0], [301, 567, 767], 1.0)]
    p = page(1400, 900)
    freqs = [20 * 1000 ** (i / 240) for i in range(241)]
    lines, settings = [], []
    for g, pos, wd in CASES:
        hz = p.evaluate("(pos) => pos.map((v, k) => eqHz(k, v))", pos)
        e = dict(low=g[0], lowHz=hz[0], mid=g[1], midHz=hz[1], width=wd, high=g[2], highHz=hz[2])
        for rate in (48000, 44100):
            settings.append((e, rate))
            lines.append(f"{rate} {g[0]} {hz[0]!r} {g[1]} {hz[1]!r} {wd} {g[2]} {hz[2]!r}")
    out = subprocess.run([exe], input="\n".join(lines) + "\n", capture_output=True, text=True, check=True).stdout.split("\n")
    worst, nulls = 0.0, []
    for (e, rate), line in zip(settings, out):
        core = [float(v) for v in line.split()]
        page_db = p.evaluate("([e, f, r]) => eqResponseDb(e, f, r)", [e, freqs, rate])
        other = p.evaluate("([e, f, r]) => eqResponseDb(e, f, r)", [e, freqs, 44100 if rate == 48000 else 48000])
        worst = max(worst, max(abs(a - c) for a, c in zip(page_db, core)))
        nulls.append(max(abs(a - c) for a, c in zip(other, core)))
    check("the page's curve is the core's to 0.01 dB, six settings, 241 frequencies, 48 and 44.1 kHz", worst < 0.01, "worst %.2e dB" % worst)
    null("the page's curve at the other rate misses the core's where a shelf is high", max(nulls) > 0.01, "largest miss %.3f dB" % max(nulls))

    print("\n--- every point in reach at every extreme (22 Nov) ---")
    # The plot is the gains' range exactly, +12 at its top and -16 at its foot, and a point is held to the plot's
    # edge where the bands together take the curve past it, with a margin of the point's whole reach on every side.
    # Each case puts points at an edge or a corner: the mid alone at its full gain at either end of the range (its
    # point is at its own gain there), and a shelf at the end of the range pushed past the edge by a wide mid beside
    # it (a shelf's own point is only at half its gain, at its corner). For each point: its reach wholly inside the
    # plot, the editor and the window, and the point itself under the pointer at its centre and at eight places a
    # pixel and a half inside its reach's rim - document.elementFromPoint, what a hand would press.
    REACH = """([g, pos, w, bands, nullOld]) => {
      setEqOn(true);
      const ids = [['eqLow', g[0]], ['eqMid', g[1]], ['eqHigh', g[2]], ['eqLowFreq', pos[0]], ['eqMidFreq', pos[1]],
                   ['eqHighFreq', pos[2]], ['eqMidWidth', w]];
      for (const [id, v] of ids) setControl(id, v);
      paintEq();
      const svg = el.eqPlot.getBoundingClientRect(), ed = el.eqEditor.getBoundingClientRect(), geo = eqEd.geo;
      const probe = (pt, hit) => {
        const b = hit.getBoundingClientRect(), cx = b.left + b.width / 2, cy = b.top + b.height / 2, r = b.width / 2;
        const at = [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1], [0.7, 0.7], [-0.7, 0.7], [0.7, -0.7], [-0.7, -0.7]];
        const missed = at.filter(([a, c]) => { const e = document.elementFromPoint(cx + a * (r - 1.5), cy + c * (r - 1.5));
                                               return !(e && e.closest && e.closest('.eq-pt') === pt); }).length;
        const inside = b.left >= Math.max(svg.left, ed.left, 0) - 0.5 && b.right <= Math.min(svg.right, ed.right, innerWidth) + 0.5
                    && b.top >= Math.max(svg.top, ed.top, 0) - 0.5 && b.bottom <= Math.min(svg.bottom, ed.bottom, innerHeight) + 0.5;
        return { missed, inside };
      };
      const cur = echoTarget('eq');
      return bands.map((k) => {
        const pt = eqEd.parts.points[k], hit = pt.querySelector('.eq-hit'), ring = pt.querySelector('.eq-ring');
        const r = probe(pt, hit);
        const out = { band: k, missed: r.missed, inside: r.inside, curve: eqPointDb(cur, k),
                      x: +ring.getAttribute('cx'), y: +ring.getAttribute('cy'), top: geo.y(EQ_DB_TOP), foot: geo.y(EQ_DB_FOOT),
                      left: geo.x(EQ_F_MIN), right: geo.x(EQ_F_MAX) };
        if (nullOld) {
          // The null: the same point where the old plot drew it - +-12 dB over the plot's height less 8 and 20,
          // held 2 dB past the foot - and probed the same way.
          const keep = hit.getAttribute('cy'), yOld = 8 + (12 + 14) / 24 * (geo.h - 28);
          hit.setAttribute('cy', yOld);
          out.old = probe(pt, hit);
          hit.setAttribute('cy', keep);
        }
        return out;
      });
    }"""
    EDGE_CASES = [
        ("the mid's cut at 20 Hz, the foot's left corner", [0, -160, 0], [301, 0, 767], 10, [1], ("foot", "left")),
        ("the mid's boost at 20 kHz, the top's right corner", [0, 120, 0], [301, 1000, 767], 10, [1], ("top", "right")),
        ("the mid's cut at 20 kHz, the foot's right corner", [0, -160, 0], [301, 1000, 767], 10, [1], ("foot", "right")),
        ("the mid's boost at 20 Hz, the top's left corner", [0, 120, 0], [301, 0, 767], 10, [1], ("top", "left")),
        ("the low shelf cut at 20 Hz under a wide mid cut, past the foot", [-160, -160, 0], [0, 100, 767], 40, [0, 1], ("foot",)),
        ("the high shelf boosted at 20 kHz under a wide mid boost, past the top", [0, 120, 120], [301, 930, 1000], 40, [2, 1], ("top",)),
        ("the high shelf cut at 20 kHz under a wide mid cut, past the foot", [0, -160, -160], [301, 930, 1000], 40, [2, 1], ("foot",)),
        ("the low shelf boosted at 20 Hz under a wide mid boost, past the top", [120, 120, 0], [0, 100, 767], 40, [0, 1], ("top",)),
    ]
    REACH_WINDOWS = [(1660, 1050), (1400, 900), (1100, 860), (1200, 680), (1100, 680), (960, 600)]
    out_of_reach, off_edge, past, olds, n_points = [], [], 0, [], 0
    for w, h in REACH_WINDOWS:
        q = page(w, h)
        q.evaluate("() => openEqEditor()"); q.wait_for_timeout(250)
        for name, g, pos, wd, bands, edges in EDGE_CASES:
            for r in q.evaluate(REACH, [g, pos, wd, bands, name.startswith("the mid's cut at 20 Hz")]):
                n_points += 1
                if r["missed"] or not r["inside"]:
                    out_of_reach.append("%dx%d %s band %d: %d of 9 probes missed, inside %s" % (w, h, name, r["band"], r["missed"], r["inside"]))
                # The point's own band at the end of the range sits on that edge; every point is held inside the plot.
                if not (r["top"] - 0.01 <= r["y"] <= r["foot"] + 0.01 and r["left"] - 0.01 <= r["x"] <= r["right"] + 0.01):
                    off_edge.append("%dx%d %s band %d off the plot" % (w, h, name, r["band"]))
                if r["band"] == bands[0]:
                    for e in edges:
                        want = {"foot": r["foot"], "top": r["top"]}.get(e)
                        got = r["y"] if e in ("foot", "top") else r["x"]
                        want = want if want is not None else r[e]
                        if abs(got - want) > 0.01: off_edge.append("%dx%d %s band %d not on its %s (%.2f, %.2f)" % (w, h, name, r["band"], e, got, want))
                if r["curve"] < -16 - 0.5 or r["curve"] > 12 + 0.5: past += 1
                if "old" in r: olds.append((w, h, r["old"]))
        q.close()
    check("every point at an edge or a corner wholly in reach - under the pointer at its centre and all round its rim, its reach "
          "inside the plot, the editor and the window: %d points, eight cases, six windows" % n_points, not out_of_reach and n_points == 72,
          "; ".join(out_of_reach[:3]))
    check("and each on the plot, the band at the end of its range on that edge or corner, the cut at -16 dB on the foot",
          not off_edge, "; ".join(off_edge[:3]))
    check("the curve was taken past the plot's edge at points that are held to it (%d of them)" % past, past >= 4 * len(REACH_WINDOWS))
    null("the same point where the old plot drew it, 2 dB past its foot, is not in reach at any window: the probes miss it or it "
         "leaves the plot", len(olds) == len(REACH_WINDOWS) and all(o["missed"] or not o["inside"] for _, _, o in olds),
         str([(w, h, o) for w, h, o in olds][:2]))

    print("\n--- a point dragged past the plot's corner, and grabbed again (22 Nov) ---")
    SHOTS = os.environ.get("EQ_SHOTS")
    for w, h in [(1400, 900), (960, 600)]:
        q = page(w, h)
        q.evaluate("() => { restore({}); setEqOn(true); eqEd.sel = 1; openEqEditor(); }"); q.wait_for_timeout(300)
        ring = lambda k: q.evaluate("""(k) => { const r = eqEd.parts.points[k].querySelector('.eq-ring').getBoundingClientRect();
                                               return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }""", k)
        plot = q.evaluate("() => { const r = el.eqPlot.getBoundingClientRect(); return { right: r.right, bottom: r.bottom, top: r.top, left: r.left }; }")
        a = ring(1)
        # Far past the foot and the right-hand edge, held there, and let go out there.
        q.mouse.move(a["x"], a["y"]); q.mouse.down()
        q.mouse.move(min(w - 2, plot["right"] + 200), min(h - 2, plot["bottom"] + 250), steps=14); q.mouse.up(); q.wait_for_timeout(200)
        gone = q.evaluate("() => [el.eqMid.value, el.eqMidFreq.value]")
        reach = q.evaluate(REACH, [[0, -160, 0], [301, 1000, 767], 10, [1], False])[0]
        if SHOTS: q.screenshot(path=os.path.join(SHOTS, "eq-%dx%d-foot-right.png" % (w, h)))
        b2 = ring(1)
        q.mouse.move(b2["x"], b2["y"]); q.mouse.down(); q.mouse.move(b2["x"] - 120, b2["y"] - 80, steps=10); q.mouse.up(); q.wait_for_timeout(200)
        back = q.evaluate("() => [el.eqMid.value, el.eqMidFreq.value]")
        check("%dx%d: the mid's point dragged far past the foot and the right-hand edge is at -16 dB and 20 kHz" % (w, h),
              gone == ["-160", "1000"], str(gone))
        check("%dx%d: and is drawn in the plot's corner, wholly in reach" % (w, h), reach["missed"] == 0 and reach["inside"]
              and abs(reach["y"] - reach["foot"]) < 0.01 and abs(reach["x"] - reach["right"]) < 0.01, str(reach))
        check("%dx%d: and grabbed again there by a hand it comes back up and in" % (w, h),
              int(back[0]) > -160 and int(back[1]) < 1000, str(back))
        # The high shelf, the owner's "lowpass", taken all the way to the right, and the low shelf all the way to the left.
        q.evaluate("() => { restore({}); setEqOn(true); setControl('eqHigh', -90); setControl('eqLow', 60); paintEq(); }"); q.wait_for_timeout(100)
        hi, lo = ring(2), ring(0)
        q.mouse.move(hi["x"], hi["y"]); q.mouse.down(); q.mouse.move(min(w - 2, plot["right"] + 300), hi["y"], steps=12); q.mouse.up()
        q.mouse.move(lo["x"], lo["y"]); q.mouse.down(); q.mouse.move(max(2, plot["left"] - 300), lo["y"], steps=12); q.mouse.up()
        q.wait_for_timeout(200)
        ends = q.evaluate("() => ({ high: el.eqHighFreq.value, low: el.eqLowFreq.value, hz: [genSettings(0).eqHighHz, genSettings(0).eqLowHz] })")
        if SHOTS: q.screenshot(path=os.path.join(SHOTS, "eq-%dx%d-shelves-at-the-ends.png" % (w, h)))
        check("%dx%d: the high shelf's point dragged all the way to the right is at 20 kHz, the low shelf's to the left at 20 Hz, "
              "and the engine is told" % (w, h), ends["high"] == "1000" and ends["low"] == "0"
              and abs(ends["hz"][0] - 20000) < 1e-6 and abs(ends["hz"][1] - 20) < 1e-9, str(ends))
        q.close()

    print("\n--- a point dragged by a hand ---")
    p.evaluate("""() => { restore({}); setEqOn(true); eqEd.sel = 1; openEqEditor(); }"""); p.wait_for_timeout(500)
    # What code did before is the base, not a step of the hand's.
    p.evaluate("() => { undoRebase(); undoHanded = false; }")
    box = p.evaluate("""() => { const r = eqEd.parts.points[1].querySelector('.eq-ring').getBoundingClientRect();
                                const plot = el.eqPlot.getBoundingClientRect();
                                return { x: r.left + r.width / 2, y: r.top + r.height / 2, left: plot.left + 60, top: plot.top + 30 }; }""")
    before = p.evaluate("() => ({ undo: undoHistory.undo.length, knobs: [el.eqMid.value, el.eqMidFreq.value] })")
    # The null first: a drag on the plot away from any point.
    p.mouse.move(box["left"], box["top"]); p.mouse.down(); p.mouse.move(box["left"] + 40, box["top"] + 40, steps=6); p.mouse.up()
    p.wait_for_timeout(900)
    empty = p.evaluate("() => ({ undo: undoHistory.undo.length, knobs: [el.eqMid.value, el.eqMidFreq.value] })")
    p.mouse.move(box["x"], box["y"]); p.mouse.down(); p.mouse.move(box["x"] + 60, box["y"] - 70, steps=10)
    held = p.evaluate("() => ({ undo: undoHistory.undo.length, knobs: [el.eqMid.value, el.eqMidFreq.value], sent: [genSettings(0).eqMid, genSettings(0).eqMidHz] })")
    p.mouse.up(); p.wait_for_timeout(900)
    after = p.evaluate("() => ({ undo: undoHistory.undo.length, knobs: [el.eqMid.value, el.eqMidFreq.value], echo: [echo.eqMid, echo.eqMidPos] })")
    print("    before %s, the empty drag %s, held %s, after %s" % (before, empty, held, after))
    check("dragged up and right, the mid's point writes its knobs: a gain up and a place higher",
          int(after["knobs"][0]) > 0 and int(after["knobs"][1]) > 567, str(after))
    check("and the engine is sent them, in its units", abs(held["sent"][0] - int(held["knobs"][0]) / 10) < 1e-9
          and abs(held["sent"][1] - p.evaluate("(v) => eqHz(1, v)", int(held["knobs"][1]))) < 1e-6, str(held))
    check("the drag is one step in undo, made on release, not while held", held["undo"] == before["undo"] and after["undo"] == before["undo"] + 1,
          "%d before, %d held, %d after" % (before["undo"], held["undo"], after["undo"]))
    null("a drag away from any point writes nothing and is no step", empty == before, str(empty))
    p.evaluate("() => el.undoButton.click()"); p.wait_for_timeout(300)
    undone = p.evaluate("() => [el.eqMid.value, el.eqMidFreq.value]")
    check("and undo puts the knobs back where they were", undone == before["knobs"], str(undone))

    print("\n--- moved while off ---")
    p.evaluate("() => { setEqOn(false); paintEq(); }"); p.wait_for_timeout(200)
    box = p.evaluate("""() => { const r = eqEd.parts.points[0].querySelector('.eq-ring').getBoundingClientRect();
                                return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }""")
    p.mouse.move(box["x"], box["y"]); p.mouse.down(); p.mouse.move(box["x"], box["y"] - 40, steps=6); p.mouse.up(); p.wait_for_timeout(100)
    pointed = p.evaluate("() => ({ on: el.eqOn.checked, sent: genSettings(0).eqOn, low: el.eqLow.value })")
    check("a point dragged while the EQ is off switches it on, and the engine is told", pointed["on"] and pointed["sent"] is True
          and int(pointed["low"]) > 0, str(pointed))
    p.evaluate("() => setEqOn(false)"); p.wait_for_timeout(100)
    face = p.evaluate("""() => { const f = el.eqHigh.closest('.menu-row').querySelector('.knob-face').getBoundingClientRect();
                                 return { x: f.left + f.width / 2, y: f.top + f.height / 2 }; }""")
    p.mouse.move(face["x"], face["y"]); p.mouse.down(); p.mouse.move(face["x"], face["y"] - 30, steps=5); p.mouse.up(); p.wait_for_timeout(100)
    knobbed = p.evaluate("() => ({ on: el.eqOn.checked, high: el.eqHigh.value })")
    check("a gain's knob turned by a hand while off switches it on", knobbed["on"] and int(knobbed["high"]) > 0, str(knobbed))

    print("\n--- the keyboard, and a point's menu ---")
    p.evaluate("() => { restore({}); setEqOn(true); closeEqEditor(); eqEd.sel = 1; openEqEditor(); }"); p.wait_for_timeout(300)
    first = p.evaluate("() => document.activeElement && document.activeElement.classList.contains('eq-pt') ? Number(document.activeElement.dataset.band) : null")
    p.keyboard.press("Shift+Tab"); p.keyboard.press("Tab"); p.wait_for_timeout(50)
    focused = p.evaluate("() => document.activeElement.classList.contains('eq-pt') ? Number(document.activeElement.dataset.band) : null")
    p.keyboard.press("ArrowUp"); p.keyboard.press("Shift+ArrowRight"); p.keyboard.press("]"); p.wait_for_timeout(50)
    keys = p.evaluate("() => [el.eqMid.value, el.eqMidFreq.value, el.eqMidWidth.value]")
    check("opened, the mid's point has the focus, and Tab comes back to it", first == 1 and focused == 1, "%s, %s" % (first, focused))
    check("an arrow moves its gain half a decibel, Shift and an arrow its place four of the thousand steps, ] its width a tenth",
          keys == ["5", "571", "11"], str(keys))
    p.keyboard.press("Shift+F10"); p.wait_for_timeout(200)
    menu = p.evaluate("""() => { const m = document.querySelector('.over.ctx'); if (!m) return null;
      return { role: m.getAttribute('role'), items: Array.from(m.querySelectorAll('.ctx-item')).map((b) => b.dataset.item),
               reset: (m.querySelector('[data-item=reset]') || {}).textContent, focus: document.activeElement.classList.contains('ctx-item') }; }""")
    check("Shift+F10 on a point opens its menu: Type a value, Reset, What is this, with the focus in it, and no Copy with one hand",
          menu and menu["role"] == "menu" and menu["items"] == ["type", "reset", "what"] and menu["focus"], str(menu))
    check("Reset names where it starts", menu and "0.0 dB at 1.0 kHz, 1.0 oct" in menu["reset"], str(menu and menu["reset"]))
    p.keyboard.press("Escape"); p.wait_for_timeout(150)
    esc1 = p.evaluate("() => ({ menu: !!document.querySelector('.over.ctx'), editor: eqEd.open, focus: document.activeElement.classList.contains('eq-pt') })")
    check("Esc in the menu closes the menu only, the focus back on the point", esc1 == {"menu": False, "editor": True, "focus": True}, str(esc1))
    p.keyboard.press("Shift+F10"); p.wait_for_timeout(150)
    p.keyboard.press("ArrowDown"); p.keyboard.press("Enter"); p.wait_for_timeout(150)
    reset = p.evaluate("() => [el.eqMid.value, el.eqMidFreq.value, el.eqMidWidth.value, eqEd.open]")
    check("its Reset puts the band back where it starts", reset == ["0", "567", "10", True], str(reset))
    p.keyboard.press("ArrowUp"); p.keyboard.press("ArrowUp"); p.wait_for_timeout(50)
    box = p.evaluate("""() => { const r = eqEd.parts.points[1].querySelector('.eq-ring').getBoundingClientRect();
                                return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }""")
    moved = p.evaluate("() => el.eqMid.value")
    p.mouse.dblclick(box["x"], box["y"]); p.wait_for_timeout(100)
    check("a double-click on a point resets it", moved == "10" and p.evaluate("() => el.eqMid.value") == "0", moved)
    p.evaluate("() => eqFocusPoint()")
    p.keyboard.press("Escape"); p.wait_for_timeout(150)
    esc2 = p.evaluate("() => ({ editor: eqEd.open, focus: document.activeElement === el.eqThumb, knobs: el.eqStore.querySelectorAll('input').length })")
    check("Esc again closes the editor, the focus back on the curve, the knobs back in their store", esc2 == {"editor": False, "focus": True, "knobs": 7}, str(esc2))

    print("\n--- the line's small curve ---")
    thumb = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const read = () => { const s = el.eqThumbSvg, sum = s.querySelector('.eq-thumb-sum'), flat = s.querySelectorAll('path');
        return { sum: !!sum, other: !!s.querySelector('.eq-thumb-other'), dots: s.querySelectorAll('.eq-thumb-pt').length,
                 grey: Array.from(flat).some((p) => p.getAttribute('stroke') === 'var(--unresolved)') }; };
      restore({}); setControl('eqLow', 60); setEqOn(false); paintEq(); await wait(50);
      const off = read();
      setEqOn(true); await wait(50);
      const on = read();
      setScreenKeys(true); setMidiMode('poly');
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change')); await wait(80);
      document.getElementById('editHandA').click(); await wait(30);
      const linkedTwo = read();
      setLink('eq', false);
      document.getElementById('editHandB').click(); await wait(30);
      setControl('eqHigh', -90); await wait(50);
      const differ = read();
      const otherInk = el.eqThumbSvg.querySelector('.eq-thumb-other') && el.eqThumbSvg.querySelector('.eq-thumb-other').getAttribute('stroke');
      setLink('eq', true);
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change')); setScreenKeys(false); restore({});
      return { off, on, linkedTwo, differ, otherInk, lowerInk: 'var(--' + handInk(0) + ')' };
    }""")
    print("    %s" % thumb)
    check("off, the line's curve is flat and grey, with no points", thumb["off"]["grey"] and not thumb["off"]["sum"] and thumb["off"]["dots"] == 0, str(thumb["off"]))
    check("on, it is the curve with its three points", thumb["on"]["sum"] and thumb["on"]["dots"] == 3 and not thumb["on"]["grey"], str(thumb["on"]))
    check("with the hands' EQs their own and different, it draws both, the other dashed in the lower hand's ink",
          thumb["differ"]["sum"] and thumb["differ"]["other"] and thumb["otherInk"] == thumb["lowerInk"], str(thumb))
    null("two hands linked draw one", thumb["linkedTwo"]["sum"] and not thumb["linkedTwo"]["other"], str(thumb["linkedTwo"]))

    print("\n--- the live spectrum ---")
    spec = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const ink = () => { const c = el.eqSpec, x = c.getContext('2d'); if (!c.width) return 0;
        const d = x.getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i]) n++; return n; };
      restore({}); setEqOn(true); setRunning(true);
      midiNoteOn(57, 100); await wait(500);
      const shut0 = eqEd.specFrames; await wait(400);
      const shut = { frames: eqEd.specFrames - shut0, ink: ink() };
      openEqEditor(); eqEd.cost = 0; eqEd.costN = 0; eqEd.costMax = 0;
      const open0 = eqEd.specFrames; await wait(1500);
      const open = { frames: eqEd.specFrames - open0, ink: ink(), cost: eqEd.cost, max: eqEd.costMax, fps: state.fps,
                     peak: Math.max(...eqEd.spec) };
      closeEqEditor();
      const closed0 = eqEd.specFrames; await wait(400);
      const closed = { frames: eqEd.specFrames - closed0, ink: ink() };
      midiNoteOff(57);
      return { shut, open, closed };
    }""")
    print("    %s" % spec)
    check("open, with a note held, the spectrum is drawn behind the curve every frame, from what is sounding",
          spec["open"]["frames"] > 30 and spec["open"]["ink"] > 1000 and spec["open"]["peak"] > -60, str(spec["open"]))
    check("and what it costs a frame, the transform and the drawing, is under 2 ms on average (%.2f ms, most %.2f)" % (spec["open"]["cost"], spec["open"]["max"]),
          0 < spec["open"]["cost"] < 2, str(spec["open"]))
    null("shut, before it was opened and after, none of it is made and its canvas is empty",
         spec["shut"]["frames"] == 0 and spec["closed"]["frames"] == 0 and spec["closed"]["ink"] == 0, str([spec["shut"], spec["closed"]]))
    p.close()

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the EQ is drawn as it sounds")
