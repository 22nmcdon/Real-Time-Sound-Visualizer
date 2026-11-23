"""The EQ drawn, and its editor (17 Nov, the owner's mockup, web/docs/mockups/eq/).

What would go wrong, and what is checked for it, each check with its null:

- a point off the line it is drawn on. Since 23 Nov (the band strip,
  web/docs/mockups/eq-bands/) each of the editor's points sits on its own
  band's curve, drawn in its ink, and the line's small curve keeps its dots
  on the sum: for ten settings - among them a shelf over the mid and a narrow
  mid on a high shelf - at 1400x900 and 960x600, the point's centre against
  the drawn path's height at its x, read from the path's own coordinates,
  within half a pixel. The nulls: the editor's points read against the sum,
  and the line's at the band's own full gain, which miss;
- the owner's "no longer follows the mouse" (23 Nov): every band's point,
  dragged with a real mouse to 60 px past each edge, stays under the pointer
  held to its own reach, within a pixel and a half (the knobs' steps), and
  can be taken hold of where it was let go. The nulls: its place before the
  drag, and the sum's height, where the old editor drew the high cut;
- a band switched off by its lamp still heard or still drawn: the engine is
  told nought, its curve goes, its point is a dashed grey ring, it keeps its
  gain; and each cell pressed makes its band's curve, and only it, the one
  drawn stronger and washed in its ink, with its knobs in the foot in its ink;
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
# Each band's ink token and knob ids, by band (0 the low shelf, 1 the mid, 2 the high shelf, 3 the low cut, 4 the high cut).
EQ_INK_NAMES = ["--ch6", "--ch2", "--ch4", "--ch3", "--ch5"]
EQ_BAND_IDS_PY = [["eqLow", "eqLowFreq"], ["eqMid", "eqMidFreq", "eqMidWidth"], ["eqHigh", "eqHighFreq"],
                  ["eqCutLowFreq", "eqCutLowQ"], ["eqCutHighFreq", "eqCutHighQ"]]
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
    # Since 23 Nov the cuts too: [low cut Hz, its Q in hundredths, high cut Hz, its Q], at their ends where not named.
    ("both cuts pulled in, a bump on each", [30, -40, 0], [160, 1000, 4000], 10, [80, 300, 6000, 250]),
    ("the cuts crossed over a boost", [0, 80, 0], [160, 700, 4000], 30, [3000, 71, 400, 400]),
]
SET = """([g, hz, w, cut]) => {
  setEqOn(true);
  // The cuts switched on where a setting names them (23 Nov, version 15: they start off), off where it does not.
  setEqBandOn(3, !!cut); setEqBandOn(4, !!cut);
  cut = cut || [20, 71, 20000, 71];
  const ids = [['eqLow', g[0]], ['eqMid', g[1]], ['eqHigh', g[2]], ['eqLowFreq', eqPos(0, hz[0])], ['eqMidFreq', eqPos(1, hz[1])],
               ['eqHighFreq', eqPos(2, hz[2])], ['eqMidWidth', w], ['eqCutLowFreq', eqPos(3, cut[0])], ['eqCutLowQ', cut[1]],
               ['eqCutHighFreq', eqPos(4, cut[2])], ['eqCutHighQ', cut[3]]];
  for (const [id, v] of ids) setControl(id, v);
}"""
# Since 23 Nov (the band strip) the editor's points sit on their own band's
# curve - each band's own path, drawn in its ink - and the line's small
# curve keeps its dots on the sum it draws. The null each way is the other
# curve: the sum for the editor's points, which misses wherever bands
# overlap, and a band's own full gain for the line's, which misses on
# every shelf. A cut switched on at its end is out, its own curve flat, and
# its point at its resonance off it: it is left out of the plot's, and an
# off band has neither a curve nor a dot on the line.
MEASURE = """(which) => {
  const svg = which === 'plot' ? el.eqPlot : el.eqThumbSvg;
  const parse = (path) => path.getAttribute('d').match(/[ML][^ML]+/g).map((t) => t.slice(1).trim().split(/\\s+/).map(Number));
  const yAt = (pts, x) => { for (let i = 1; i < pts.length; i++) if (pts[i][0] >= x) {
      const [x0, y0] = pts[i - 1], [x1, y1] = pts[i]; return x1 === x0 ? y1 : y0 + (y1 - y0) * (x - x0) / (x1 - x0); }
    return pts[pts.length - 1][1]; };
  const sum = parse(which === 'plot' ? document.getElementById('eqSumPath') : svg.querySelector('.eq-thumb-sum'));
  const h = echoTarget('eq'), gains = [h.eqLow, h.eqMid, h.eqHigh];
  const dots = which === 'plot' ? Array.from(svg.querySelectorAll('.eq-pt .eq-ring')) : Array.from(svg.querySelectorAll('.eq-thumb-pt'));
  const ht = svg.clientHeight;
  const edge = which === 'plot' ? [eqEd.geo.y(EQ_DB_TOP), eqEd.geo.y(EQ_DB_FOOT)] : [3, ht - 3];
  const zero = which === 'plot' ? eqEd.geo.y(0) : 3 + EQ_DB_TOP / (EQ_DB_TOP - EQ_DB_FOOT) * (ht - 6);
  const out = [];
  for (const c of dots) {
    const k = Number(c.dataset.band !== undefined ? c.dataset.band : c.parentNode.dataset.band);
    const cx = +c.getAttribute('cx'), cy = +c.getAttribute('cy');
    const onSum = !eqBandIn(h, k) ? zero : Math.max(edge[0], Math.min(edge[1], yAt(sum, cx)));
    if (which === 'plot') {
      if (!eqBandIn(h, k)) continue;
      const own = parse(svg.querySelector('.eq-band-curve[data-band="' + k + '"]'));
      const onOwn = Math.max(edge[0], Math.min(edge[1], yAt(own, cx)));
      out.push({ band: k, gain: gains[k], miss: Math.abs(cy - onOwn), nullMiss: Math.abs(cy - onSum) });
    } else {
      const oldY = 3 + (EQ_DB_TOP - (gains[k] || 0)) / (EQ_DB_TOP - EQ_DB_FOOT) * (ht - 6);
      out.push({ band: k, gain: gains[k], miss: Math.abs(cy - onSum), nullMiss: k < 3 && k !== 1 ? Math.abs(oldY - onSum) : 0 });
    }
  }
  return out;
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
    worst, shelves, sums, n_plot = 0.0, [], [], 0
    for w, h in [(1400, 900), (960, 600)]:
        p = page(w, h)
        p.evaluate("() => openEqEditor()"); p.wait_for_timeout(200)
        for name, g, pos, wd, *cut in SETTINGS:
            p.evaluate(SET, [g, pos, wd, cut[0] if cut else None]); p.wait_for_timeout(30)
            for which in ["plot", "thumb"]:
                for r in p.evaluate(MEASURE, which):
                    worst = max(worst, r["miss"])
                    if which == "plot": n_plot += 1; sums.append(r["nullMiss"])
                    elif r["band"] in (0, 2) and r["gain"] != 0: shelves.append((r["nullMiss"], "%dx%d %s band %d" % (w, h, name, r["band"])))
                    if r["miss"] > 0.5: check("%dx%d %s %s band %d on its curve" % (w, h, name, which, r["band"]), False, "%.3f px" % r["miss"])
        p.close()
    check("every point within half a pixel of its curve at its x - the editor's on its own band's, the line's on the sum - "
          "%d settings, both windows (%d of the editor's)" % (len(SETTINGS), n_plot), worst <= 0.5 and n_plot >= 50, "worst %.3f px" % worst)
    null("the editor's points read against the sum miss by more than five pixels on %d of them" % sum(1 for s in sums if s > 5),
         sum(1 for s in sums if s > 5) >= 10, "largest %.1f px" % max(sums))
    lo = min(shelves)
    null("the line's dots read at the band's own full gain miss on every shelf", lo[0] > 0.5, "smallest miss %.2f px (%s)" % lo)

    print("\n--- the curve against the core's ---")
    exe = os.path.join(tempfile.mkdtemp(), "eqresponse")
    subprocess.run(["g++", "-std=c++17", "-O1", "-I" + os.path.join(ROOT, "core", "include"),
                    os.path.join(ROOT, "core", "tests", "tools", "eq_response_cpp.cpp"), "-o", exe], check=True)
    # Places on today's knob (a thousand over 20 Hz to 20 kHz): the starts, and the ends both ways, the cut at -16 dB.
    # And the cuts (23 Nov): [low cut's place, its Q, high cut's place, its Q], at their ends (out) where not named.
    CASES = [([3, 0, 3], [301, 567, 767], 1.0), ([3, -4, 3], [301, 528, 767], 1.4), ([12, 12, -16], [0, 1000, 1000], 0.2),
             ([-16, -16, 12], [1000, 0, 0], 4.0), ([0, 6.5, 0], [301, 567, 767], 1.0), ([0, 0, 0], [301, 567, 767], 1.0),
             ([3, 0, 3], [301, 567, 767], 1.0, [200, 3.0, 800, 0.5]), ([0, 0, 0], [301, 567, 767], 1.0, [700, 4.0, 300, 4.0]),
             ([-6, 4, 0], [301, 567, 767], 2.0, [1, 0.71, 999, 2.0])]
    p = page(1400, 900)
    freqs = [20 * 1000 ** (i / 240) for i in range(241)]
    lines, settings = [], []
    for g, pos, wd, *cut in CASES:
        cut = cut[0] if cut else [0, 0.71, 1000, 0.71]
        hz = p.evaluate("(pos) => pos.map((v, k) => eqHz(k, v))", pos + [cut[0], cut[2]])
        e = dict(low=g[0], lowHz=hz[0], mid=g[1], midHz=hz[1], width=wd, high=g[2], highHz=hz[2],
                 cutLowHz=hz[3], cutLowQ=cut[1], cutHighHz=hz[4], cutHighQ=cut[3])
        for rate in (48000, 44100):
            settings.append((e, rate))
            lines.append(f"{rate} {g[0]} {hz[0]!r} {g[1]} {hz[1]!r} {wd} {g[2]} {hz[2]!r} {hz[3]!r} {cut[1]!r} {hz[4]!r} {cut[3]!r}")
    out = subprocess.run([exe], input="\n".join(lines) + "\n", capture_output=True, text=True, check=True).stdout.split("\n")
    worst, nulls = 0.0, []
    for (e, rate), line in zip(settings, out):
        core = [float(v) for v in line.split()]
        page_db = p.evaluate("([e, f, r]) => eqResponseDb(e, f, r)", [e, freqs, rate])
        other = p.evaluate("([e, f, r]) => eqResponseDb(e, f, r)", [e, freqs, 44100 if rate == 48000 else 48000])
        worst = max(worst, max(abs(a - c) for a, c in zip(page_db, core)))
        nulls.append(max(abs(a - c) for a, c in zip(other, core)))
    check("the page's curve is the core's to 0.01 dB, %d settings (three with the cuts), 241 frequencies, 48 and 44.1 kHz" % len(CASES),
          worst < 0.01, "worst %.2e dB" % worst)
    null("the page's curve at the other rate misses the core's where a shelf is high", max(nulls) > 0.01, "largest miss %.3f dB" % max(nulls))

    print("\n--- every point in reach at every extreme (22 Nov) ---")
    # The plot is the gains' range exactly, +12 at its top and -16 at its foot, and a point is held to the plot's
    # edge where the bands together take the curve past it, with a margin of the point's whole reach on every side.
    # Each case puts points at an edge or a corner: the mid alone at its full gain at either end of the range (its
    # point is at its own gain there), and a shelf at the end of the range pushed past the edge by a wide mid beside
    # it (a shelf's own point is only at half its gain, at its corner). For each point: its reach wholly inside the
    # plot, the editor and the window, and the point itself under the pointer at its centre and at eight places a
    # pixel and a half inside its reach's rim - document.elementFromPoint, what a hand would press.
    REACH = """([g, pos, w, bands, nullOld, cut]) => {
      setEqOn(true);
      // The cuts (23 Nov): [low cut's place, its Q in hundredths, high cut's place, its Q], switched on where named.
      setEqBandOn(3, !!cut); setEqBandOn(4, !!cut);
      cut = cut || [59, 71, 985, 71];
      const ids = [['eqLow', g[0]], ['eqMid', g[1]], ['eqHigh', g[2]], ['eqLowFreq', pos[0]], ['eqMidFreq', pos[1]],
                   ['eqHighFreq', pos[2]], ['eqMidWidth', w], ['eqCutLowFreq', cut[0]], ['eqCutLowQ', cut[1]],
                   ['eqCutHighFreq', cut[2]], ['eqCutHighQ', cut[3]]];
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
        # Since 23 Nov a shelf's point is at half its gain on its own curve, whatever the mid beside it does to the
        # sum: at an end of the range it is on that side, and a wide mid at the same end is in the corner beside it.
        ("the low shelf cut at 20 Hz, under the mid cut there in the foot's corner", [-160, -160, 0], [0, 0, 767], 40, [0, 1], ("left",)),
        ("the high shelf boosted at 20 kHz, under the mid boosted there in the top's corner", [0, 120, 120], [301, 1000, 1000], 40, [2, 1], ("right",)),
        ("the high shelf cut at 20 kHz, over the mid cut there in the foot's corner", [0, -160, -160], [301, 1000, 1000], 40, [2, 1], ("right",)),
        ("the low shelf boosted at 20 Hz, under the mid boosted there in the top's corner", [120, 120, 0], [0, 0, 767], 40, [0, 1], ("left",)),
        # The cuts (23 Nov): switched on at their ends, at their resonance (-3 dB) at the plot's sides; and pulled a
        # step in with the most resonance, their bump +12 dB, on the top at either side.
        ("both cuts switched on at their ends, at their resonance at either side", [0, 0, 0], [301, 567, 767], 10, [3, 4], ("left",),
         [0, 71, 1000, 71]),
        ("the low cut a step in with its most resonance, on the top at the left", [0, 0, 0], [301, 567, 767], 10, [3], ("top",),
         [1, 400, 1000, 71]),
        ("the high cut a step in with its most resonance, on the top at the right", [0, 0, 0], [301, 567, 767], 10, [4], ("top",),
         [0, 71, 999, 400]),
    ]
    REACH_WINDOWS = [(1660, 1050), (1400, 900), (1100, 860), (1200, 680), (1100, 680), (960, 600)]
    out_of_reach, off_edge, past, olds, n_points, rows = [], [], 0, [], 0, []
    for w, h in REACH_WINDOWS:
        q = page(w, h)
        q.evaluate("() => openEqEditor()"); q.wait_for_timeout(250)
        # Only the chosen band's knobs in the foot (23 Nov, the band strip), for each band in turn: its own ids and
        # no other's, inside the editor, the editor not scrolling, the strip and its five cells whole, and the plot a
        # height worth drawing in. The others wait in the store, where every id still resolves.
        rows.append((w, h, q.evaluate("""() => { const out = [];
          for (const k of EQ_ORDER) { eqChoose(k); paintEq();
            const f = el.eqFoot.getBoundingClientRect(), e = el.eqEditor.getBoundingClientRect(), s = el.eqStrip.getBoundingClientRect();
            out.push({ band: k, ids: Array.from(el.eqEdKnobs.querySelectorAll('input')).map((i) => i.id), want: EQ_BAND_IDS[k],
                       inside: f.left >= e.left - 0.5 && f.right <= e.right + 0.5 && f.bottom <= e.bottom + 0.5 && s.right <= e.right + 0.5,
                       scrolls: el.eqEditor.scrollHeight > el.eqEditor.clientHeight + 0.5,
                       cells: Array.from(el.eqStrip.children).filter((c) => c.scrollWidth <= c.clientWidth + 0.5).length,
                       stored: el.eqStore.querySelectorAll('input').length,
                       plot: Math.round(el.eqPlot.getBoundingClientRect().height) }); }
          eqChoose(1); return out; }""")))
        for name, g, pos, wd, bands, edges, *cut in EDGE_CASES:
            for r in q.evaluate(REACH, [g, pos, wd, bands, name.startswith("the mid's cut at 20 Hz"), cut[0] if cut else None]):
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
                # Its own height is inside the plot whatever the other bands do to the sum (23 Nov): never held to an edge.
                if r["curve"] < -16 - 1e-9 or r["curve"] > 12.05: past += 1
                if "old" in r: olds.append((w, h, r["old"]))
        q.close()
    check("every point at an edge or a corner wholly in reach - under the pointer at its centre and all round its rim, its reach "
          "inside the plot, the editor and the window: %d points, %d cases, six windows" % (n_points, len(EDGE_CASES)),
          not out_of_reach and n_points == len(REACH_WINDOWS) * sum(len(c[4]) for c in EDGE_CASES),
          "; ".join(out_of_reach[:3]))
    check("and each on the plot, the band at the end of its range on that edge or corner, the cut at -16 dB on the foot",
          not off_edge, "; ".join(off_edge[:3]))
    check("no point's own height is past the plot - its band's reach is inside it - so none is held to an edge it was not taken "
          "to (%d past)" % past, past == 0)
    null("the same point where the old plot drew it, 2 dB past its foot, is not in reach at any window: the probes miss it or it "
         "leaves the plot", len(olds) == len(REACH_WINDOWS) and all(o["missed"] or not o["inside"] for _, _, o in olds),
         str([(w, h, o) for w, h, o in olds][:2]))

    badrows = [(w, h, r) for w, h, rr in rows for r in rr if not (r["ids"] == r["want"] and r["inside"] and not r["scrolls"]
               and r["cells"] == 5 and r["stored"] == 11 - len(r["want"]) and r["plot"] >= 150)]
    check("each band chosen in turn has its own knobs in the foot and no other's, the rest in the store; the foot and the "
          "strip's five cells whole inside the editor, which does not scroll, the plot at least 150 px tall, at all six windows",
          not badrows and len(rows) == 6, str(badrows[:2] or [(w, h, rr[0]["plot"]) for w, h, rr in rows]))
    null("for each band, the next band's knobs are not the ones shown", all(r["ids"] != rr[(i + 1) % 5]["want"]
         for _, _, rr in rows for i, r in enumerate(rr)))

    print("\n--- the cuts pulled in by a hand (23 Nov) ---")
    DOC_SHOTS = os.environ.get("EQ_DOC_SHOTS")
    for w, h in [(1400, 900), (960, 600)]:
        q = page(w, h)
        q.evaluate("() => { restore({}); setEqOn(true); setControl('eqMid', 30); setControl('eqLow', -40); eqEd.sel = 4; openEqEditor(); }")
        q.wait_for_timeout(300)
        ring = lambda k: q.evaluate("""(k) => { const r = eqEd.parts.points[k].querySelector('.eq-ring').getBoundingClientRect();
                                               return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }""", k)
        plot = q.evaluate("() => { const r = el.eqPlot.getBoundingClientRect(); return { left: r.left, width: r.width }; }")
        before = q.evaluate("() => [el.eqCutHighFreq.value, el.eqCutHighQ.value, el.eqCutLowFreq.value, el.eqCutLowQ.value, genSettings(0).eqCutHighHz, el.eqCutHighOn.checked, el.eqCutLowOn.checked]")
        hc, lc = ring(4), ring(3)
        # The high cut from 18 kHz, where it starts off (version 15), to about a third of the way back, and up for a bump;
        # the low cut in from 30 Hz, and down. A hand moving a band that is off switches it on.
        q.mouse.move(hc["x"], hc["y"]); q.mouse.down(); q.mouse.move(hc["x"] - plot["width"] * 0.28, hc["y"] - 45, steps=12); q.mouse.up()
        q.mouse.move(lc["x"], lc["y"]); q.mouse.down(); q.mouse.move(lc["x"] + plot["width"] * 0.18, lc["y"] + 25, steps=12); q.mouse.up()
        q.wait_for_timeout(250)
        after = q.evaluate("""() => { const g = genSettings(0), s = document.querySelector('[data-fx-sum="eq"]').textContent;
          return { knobs: [el.eqCutHighFreq.value, el.eqCutHighQ.value, el.eqCutLowFreq.value, el.eqCutLowQ.value],
                   hz: [g.eqCutHighHz, g.eqCutHighQ, g.eqCutLowHz, g.eqCutLowQ], sum: s,
                   undo: undoHistory.undo.length, dashed: eqEd.parts.points[4].querySelector('.eq-ring').getAttribute('stroke-dasharray'),
                   on: [el.eqCutLowOn.checked, el.eqCutHighOn.checked] }; }""")
        if os.environ.get("EQ_SHOTS"): q.screenshot(path=os.path.join(os.environ["EQ_SHOTS"], "eq-%dx%d-cuts-pulled-in.png" % (w, h)))
        if DOC_SHOTS: q.screenshot(path=os.path.join(DOC_SHOTS, "editor-%dx%d.png" % (w, h)))
        print("    %dx%d before %s, after %s" % (w, h, before, after))
        hk = [int(v) for v in after["knobs"]]
        check("%dx%d: the high cut's point, off, dragged in from 18 kHz and up, is switched on below it with more resonance, and "
              "the engine is told" % (w, h), hk[0] < 900 and hk[1] > 71 and abs(after["hz"][0] - 20 * 1000 ** (hk[0] / 1000)) < 1e-6
              and abs(after["hz"][1] - hk[1] / 100) < 1e-9 and after["on"][1], str(after))
        check("%dx%d: the low cut's, off, dragged in from 30 Hz and down, is switched on above it with less, and the engine is told" % (w, h),
              hk[2] > 59 and hk[3] < 71 and abs(after["hz"][2] - 20 * 1000 ** (hk[2] / 1000)) < 1e-6 and after["on"][0], str(after))
        check("%dx%d: and the rack's line says both cuts" % (w, h), "cut below" in after["sum"] and "cut above" in after["sum"], after["sum"])
        null("%dx%d: before the hand, both were off at 18 kHz and 30 Hz, the engine told their ends, out" % (w, h),
             before[:4] == ["985", "71", "59", "71"] and before[4] == 20000 and before[5] is False and before[6] is False, str(before))
        q.close()

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

    print("\n--- the point under the pointer to every edge (23 Nov, the owner's) ---")
    # The owner's: a cut dragged to the right "eventually forces you to follow the line and no longer follows the
    # mouse". Each point is its own values now, and the pointer is them: for every band, from its point to 60 px
    # past each edge of the plot with a real mouse, the point's centre is where the pointer is, held to the band's
    # own reach - the plot across, and up and down its own range (the mid's gain, half a shelf's, a cut's 20 log10 Q)
    # - within a pixel and a half, the knobs' own steps (a tenth of a decibel, a hundredth of Q). Let go at the edge,
    # the point is still what is under its centre. The nulls: the point's place before the drag, and the sum's
    # height at the point's x, which is where today's editor drew it and which the high cut leaves.
    SHAPED = """() => { restore({}); setEqOn(true); setControl('eqLow', 45); setControl('eqMid', -30); setControl('eqHigh', 40);
      setEqBandOn(3, true); setEqBandOn(4, true); setControl('eqCutLowFreq', eqPos(3, 40)); setControl('eqCutHighFreq', eqPos(4, 9000));
      setControl('eqCutHighQ', 140); eqEd.lastDown = null; paintEq(); }"""
    GEO = """(k) => { const g = eqEd.geo, box = el.eqPlot.getBoundingClientRect(), s = box.width / g.w;
      const ring = eqEd.parts.points[k].querySelector('.eq-ring').getBoundingClientRect();
      const hi = eqIsCut(k) ? 20 * Math.log10(4) : k === 1 ? 12 : 6, lo = eqIsCut(k) ? 20 * Math.log10(0.5) : k === 1 ? -16 : -8;
      const cur = echoTarget('eq'), x = g.x(eqBandHz(cur, k));
      const sumY = box.top + g.y(Math.max(EQ_DB_FOOT, Math.min(EQ_DB_TOP, eqResponseDb(eqOf(cur), [eqBandHz(cur, k)])[0]))) * s;
      return { s, pt: [ring.left + ring.width / 2, ring.top + ring.height / 2], sumY,
               x0: box.left + g.L * s, x1: box.left + (g.L + g.W) * s, y0: box.top + g.y(Math.min(12, hi)) * s,
               y1: box.top + g.y(Math.max(-16, lo)) * s, top: box.top + g.T * s, foot: box.top + (g.T + g.H) * s }; }"""
    import math
    for w, h in [(1400, 900), (960, 600)]:
        q = page(w, h)
        q.evaluate("() => { eqEd.sel = 4; openEqEditor(); }"); q.wait_for_timeout(300)
        worst, worst_start, worst_sum, grabs, drags = 0.0, 0.0, 0.0, 0, 0
        for k in [3, 0, 1, 2, 4]:
            for edge in ("right", "left", "top", "foot"):
                q.evaluate(SHAPED); q.wait_for_timeout(30)
                g = q.evaluate(GEO, k)
                sx, sy = g["pt"]
                tx, ty = {"right": (g["x1"] + 60, sy), "left": (g["x0"] - 60, sy), "top": (sx, g["top"] - 60), "foot": (sx, g["foot"] + 60)}[edge]
                q.mouse.move(sx, sy); q.mouse.down()
                for i in range(1, 21):
                    mx, my = sx + (tx - sx) * i / 20, sy + (ty - sy) * i / 20
                    q.mouse.move(mx, my)
                    now = q.evaluate(GEO, k)
                    want = (min(g["x1"], max(g["x0"], mx)), min(g["y1"], max(g["y0"], my)))
                    worst = max(worst, math.hypot(now["pt"][0] - want[0], now["pt"][1] - want[1]))
                    worst_start = max(worst_start, math.hypot(now["pt"][0] - sx, now["pt"][1] - sy))
                    if k == 4 and edge == "right": worst_sum = max(worst_sum, abs(now["sumY"] - now["pt"][1]))
                q.mouse.up(); drags += 1
                end = q.evaluate(GEO, k)["pt"]
                grabs += q.evaluate("""([x, y, k]) => { const e = document.elementFromPoint(x, y); const pt = e && e.closest && e.closest('.eq-pt');
                                       return !!pt && pt.dataset.band === String(k); }""", [end[0], end[1], k])
                q.evaluate("() => { eqEd.lastDown = null; }")
        if os.environ.get("EQ_SHOTS"): q.screenshot(path=os.path.join(os.environ["EQ_SHOTS"], "eq-%dx%d-dragged-to-the-edge.png" % (w, h)))
        q.close()
        check("%dx%d: every band's point under the pointer to all four edges, held to its own reach, within a pixel and a half "
              "(%d drags of 20 steps)" % (w, h, drags), worst <= 1.5 and drags == 20, "worst %.2f px" % worst)
        check("%dx%d: and where each was let go at an edge, it is what is under its centre" % (w, h), grabs == drags, "%d of %d" % (grabs, drags))
        null("%dx%d: against its place before the drag, the same reading misses by far" % (w, h), worst_start > 50, "%.0f px" % worst_start)
        null("%dx%d: and the high cut dragged right is off the sum, where today's editor drew it, by %.0f px" % (w, h, worst_sum), worst_sum > 5)

    print("\n--- a band switched off by its lamp, and the band chosen (23 Nov) ---")
    for w, h in [(1400, 900), (960, 600)]:
        q = page(w, h)
        q.evaluate("() => { eqEd.sel = 0; openEqEditor(); }"); q.wait_for_timeout(300)
        q.evaluate(SHAPED); q.wait_for_timeout(50)
        READ = """(k) => { const curve = el.eqPlot.querySelector('.eq-band-curve[data-band="' + k + '"]'), ring = eqEd.parts.points[k].querySelector('.eq-ring');
          return { on: el[EQ_ON_ID[k]].checked, told: genSettings(0).eqMid, kept: el.eqMid.value, d: curve.getAttribute('d'),
                   dash: ring.getAttribute('stroke-dasharray'), stroke: ring.getAttribute('stroke'), sel: eqEd.sel,
                   sum: document.getElementById('eqSumPath').getAttribute('d'),
                   lamp: el.eqStrip.querySelector('[data-eq-band="' + k + '"] .eq-lamp').getAttribute('aria-pressed') }; }"""
        before = q.evaluate(READ, 1)
        lamp = q.evaluate("() => { const r = el.eqStrip.querySelector('[data-eq-band=\"1\"] .eq-lamp').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
        q.mouse.click(lamp[0], lamp[1]); q.wait_for_timeout(100)
        off = q.evaluate(READ, 1)
        q.mouse.click(lamp[0], lamp[1]); q.wait_for_timeout(100)
        again = q.evaluate(READ, 1)
        check("%dx%d: the mid's lamp pressed by a hand switches it off: out of the chain (the engine told nought), its gain kept, "
              "its curve gone, its point a dashed grey ring, the band chosen left as it was" % (w, h),
              off["on"] is False and off["told"] == 0 and off["kept"] == "-30" and off["d"] == "" and off["dash"]
              and "unresolved" in off["stroke"] and off["sel"] == 0 and off["lamp"] == "false", str(off)[:300])
        check("%dx%d: and pressed again it is in as it was" % (w, h), again["on"] is True and again["told"] == -3 and again["d"] == before["d"]
              and again["sum"] == before["sum"], str(again)[:200])
        null("%dx%d: the sum changed while it was off" % (w, h), off["sum"] != before["sum"] and before["told"] == -3)
        # Each cell pressed in turn with a real mouse: its band's curve, and only it, stronger and washed in its ink; its cell
        # chosen; its knobs in the foot, their rings in its ink.
        chosen, ok_all = [], True
        for k in [3, 0, 1, 2, 4]:
            cell = q.evaluate("(k) => { const r = el.eqStrip.querySelector('[data-eq-band=\"' + k + '\"] .eq-cell-name').getBoundingClientRect(); return [r.left + 5, r.top + r.height / 2]; }", k)
            q.mouse.click(cell[0], cell[1]); q.wait_for_timeout(60)
            r = q.evaluate("""(k) => { const curves = Array.from(el.eqPlot.querySelectorAll('.eq-band-curve'));
              const face = el.eqEdKnobs.querySelector('.knob-face');
              return { k, strong: curves.filter((c) => c.getAttribute('data-chosen') === '1').map((c) => Number(c.dataset.band)),
                       widths: curves.map((c) => Number(c.getAttribute('stroke-width'))),
                       wash: el.eqPlot.querySelector('.eq-chosen-wash').getAttribute('fill'), washD: el.eqPlot.querySelector('.eq-chosen-wash').getAttribute('d').length,
                       cell: Array.from(el.eqStrip.children).filter((c) => c.getAttribute('aria-selected') === 'true').map((c) => Number(c.dataset.eqBand)),
                       foot: el.eqFoot.dataset.eqBand, ids: Array.from(el.eqEdKnobs.querySelectorAll('input')).map((i) => i.id),
                       arc: face ? getComputedStyle(face).getPropertyValue('--knob-arc').trim() : '',
                       ink: getComputedStyle(document.documentElement).getPropertyValue(EQ_INK[k]).trim() }; }""", k)
            chosen.append(r)
            ok_all &= (r["strong"] == [k] and r["widths"][k] == 2 and all(x < 2 for i, x in enumerate(r["widths"]) if i != k)
                       and EQ_INK_NAMES[k] in r["wash"] and r["washD"] > 0 and r["cell"] == [k] and r["foot"] == str(k)
                       and r["ids"] == EQ_BAND_IDS_PY[k] and r["arc"].lower() == r["ink"].lower())
        check("%dx%d: each cell pressed chooses its band: its curve, and only it, drawn stronger and washed in its ink, its cell "
              "chosen, its knobs in the foot with their rings in its ink" % (w, h), ok_all, str([c for c in chosen])[:400])
        null("%dx%d: for each band, the band before it is not the one drawn stronger" % (w, h),
             all(c["strong"] != [chosen[i - 1]["k"]] for i, c in enumerate(chosen)))
        if os.environ.get("EQ_SHOTS"): q.screenshot(path=os.path.join(os.environ["EQ_SHOTS"], "eq-%dx%d-bands.png" % (w, h)))
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
    # The high shelf chosen, so its knobs are the foot's (23 Nov: only the chosen band's are).
    p.evaluate("() => { setEqOn(false); eqChoose(2); paintEq(); }"); p.wait_for_timeout(100)
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
    check("Esc again closes the editor, the focus back on the curve, the knobs back in their store", esc2 == {"editor": False, "focus": True, "knobs": 11}, str(esc2))

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
    check("on, it is the curve with a dot for each band switched on - three, the cuts starting off", thumb["on"]["sum"]
          and thumb["on"]["dots"] == 3 and not thumb["on"]["grey"], str(thumb["on"]))
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
