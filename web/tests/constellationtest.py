"""The constellation (step 2 of web/docs/ways-to-draw.md): a prototype way to
draw beside today's one figure, each held note drawing the figure it would
draw alone, at a place the note decides, as large as it is loud. Page-only:
drawn on the main thread from the voice lists, on the page's own brain,
whose Scan reads the screen the page draws. What this holds, each against
the way it would fail, and each check with its null:

- off, nothing changes. The same frame drawn the same number of times with
  the switch at One figure and with the constellation's two entry points
  taken out of the page (as if it had never been written): the phosphor grid
  bit for bit, and so Scan's table, and so what a generator fed that table
  makes - its picture pair and its heard pair, sample for sample. The null:
  the switch on reads a different grid, table and sound. On the instrument's
  brain, choosing it changes nothing either (nothing drawn, the grid the
  same), and says where it is heard. Not in a setup, a code, undo or the
  browser's storage;
- on, each note's figure is where its place puts it, worked out here from
  the rule rather than read from the page: by pitch, four notes over three
  octaves found within a cell of where the clock face and the octave's ring
  say, against the one figure, which finds them nowhere;
- sized by its level: two notes on the clock, one struck at full and one at
  half, measured off the grid, in the ratio of their velocities and at the
  size the level gives; a ring for a sine and a diamond for a triangle, each
  the other's null; and, in time, a slow attack growing a figure and a
  release shrinking it until it goes;
- Scan reads it: with a triad held long enough for Scan's path to follow it,
  on the clock every note's figure is crossed by the circle Scan reads and
  taking any one of them out changes the table; by pitch a middle-register
  triad sits clear of the circle and taking a figure out changes the table
  far less - the difference measured;
- a fast run leaves a trail: thirteen notes at seventy milliseconds each,
  and half a second later the grid holds a figure at the place of most of
  them, where the one figure leaves one smear;
- it fits: Play does not scroll with the constellation's place, hands and
  seed showing, on two hands with the keys and the Photocell, at every
  window fittest.py measures; the null a section made taller by hand;
- the cost of a frame of many small figures, against the one figure's,
  printed for docs/ways-to-draw.md's step 3 (a voice budget), with a ceiling
  far above it so a regression of an order of magnitude is red.

Serial: it measures milliseconds a frame, and runs real seconds of notes.
"""
import os, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
N = 64

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)
def null(name, red, detail=""):
    """A check's null: the same comparison fed a value it must reject."""
    check("null: " + name, red, detail)


def opened(b, query="?brain=js", w=1400, h=900):
    p = b.new_page(viewport={"width": w, "height": h})
    errors = []
    p.on("pageerror", lambda e: errors.append(str(e)))
    p.goto(f"file://{ART}/scope.html" + query); p.wait_for_timeout(1200)
    p.evaluate("() => { if (el.helpDialog.open) el.helpDialog.close(); }")
    return p, errors


# The rule, written again here from the doc rather than read from the page:
# pitch class round a clock face, C at the top and clockwise; by pitch the
# octave a ring from 0.14 (octave two) out by 0.17 an octave to 0.82; on the
# clock a ring of 0.4. In half-widths of the screen, Y up.
def place(note, how):
    pc, octave = note % 12, note // 12 - 1
    th = 2 * np.pi * pc / 12
    r = 0.4 if how == "clock" else 0.14 + 0.17 * (min(6, max(2, octave)) - 2)
    return r * np.sin(th), r * np.cos(th)

def cell_of(x, y):
    # The grid spans the plot, which is the screen at zoom one: X right, Y down.
    return (x + 1) / 2 * N, (1 - y) / 2 * N

def lit_near(grid, u, v, reach, floor=0.05):
    g = np.asarray(grid).reshape(N, N)
    ys, xs = np.mgrid[0:N, 0:N]
    cx, cy = xs + 0.5, ys + 0.5
    mask = (np.hypot(cx - u, cy - v) <= reach) & (g > floor)
    return cx[mask], cy[mask], g[mask]

def components(grid, floor):
    g = np.asarray(grid).reshape(N, N) > floor
    seen = np.zeros_like(g); out = []
    for y in range(N):
        for x in range(N):
            if g[y, x] and not seen[y, x]:
                stack, cells = [(y, x)], []
                seen[y, x] = True
                while stack:
                    a, c = stack.pop(); cells.append((a, c))
                    for da, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        aa, cc = a + da, c + dc
                        if 0 <= aa < N and 0 <= cc < N and g[aa, cc] and not seen[aa, cc]:
                            seen[aa, cc] = True; stack.append((aa, cc))
                cells = np.asarray(cells)
                out.append((cells[:, 1].mean() + 0.5, cells[:, 0].mean() + 0.5, len(cells)))
    return out


SETUP = """async ([way, how, persistence]) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  midiPanic(); await wait(50);
  el.drawWay.value = way; el.drawWay.dispatchEvent(new Event('change'));
  if (how) { el.drawPlace.value = how; el.drawPlace.dispatchEvent(new Event('change')); }
  setPersistence(persistence);
  await wait(300);
  return { live: constellationLive(), way: constellation.way, place: constellation.place };
}"""

# A frame drawn again and again with nothing else moving: the scope stopped,
# nothing held for the frame loop to draw, so these calls are the only
# drawing, from the same start each time - the beam's smoothed anchor
# forgotten and the grid wiped.
REPLAY = """async ([conditions, scanned]) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const frame = state.held;
  setRunning(false); state.held = null; await wait(120);
  const path = { cx: 0.47, cy: 0.52, r: 0.21 };
  const lfosOf = () => [{ shape: 'sine', rate: 0.2, depth: 0.5, phase: 0, held: 0, value: 0 },
                        { shape: 'sine', rate: 0.5, depth: 0.3, phase: 0, held: 0, value: 0 }];
  const voices = genSettings(0).voices.map((v) => Object.assign({}, v));
  const kept = { draw: drawConstellation, live: constellationLive };
  const out = {};
  for (const [name, way, absent] of conditions) {
    constellation.way = way;
    if (absent) { window.drawConstellation = () => {}; window.constellationLive = () => false; }
    beamRefs.clear(); constellation.figures.clear();
    pictureEngine.fade(state.persistence, true);
    for (let i = 0; i < 30; i++) { drawMain(frame, 16); drawConstellation(16); }
    window.drawConstellation = kept.draw; window.constellationLive = kept.live;
    const grid = Array.from(pictureEngine.cells);
    const tables = scanTables(scanRead(pictureEngine.cells, path, scan.soft));
    // What a generator makes of that table: the page's own core, deterministically.
    const core = makeGeneratorCore(48000, GEN_SLOTS, lfosOf());
    core.set('voices', voices); core.set('scan', 0.6);
    if (tables) core.set('scanTable', tables);
    const lanes = [0, 1, 2, 3, 4, 5].map(() => new Float32Array(128)), heard = [], picture = [];
    for (let k = 0; k < 40; k++) {
      core.block(lanes[0], lanes[1], 128, lanes[2], lanes[3], lanes[4], lanes[5]);
      picture.push(...lanes[0], ...lanes[1]); heard.push(...lanes[2], ...lanes[3]);
    }
    out[name] = { grid, table: tables ? Array.from(tables.levels[0]) : null, picture, heard,
                  drawn: constellation.drawn.length };
  }
  constellation.way = 'one';
  state.held = frame; setRunning(true);
  return out;
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    # ------------------------------------------------------------------
    print("\n--- off, nothing changes ---")
    p, errors = opened(b)
    p.evaluate(SETUP, ["one", "clock", 0.3])
    p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.oscScan.value = '60'; el.oscScan.dispatchEvent(new Event('input'));
      for (const n of [48, 60, 64, 67, 71]) midiNoteOn(n, 100);
      await wait(900);
    }""")
    r = p.evaluate(REPLAY, [[["off", "one", False], ["absent", "one", True], ["on", "constellation", False]], True])
    same = lambda a, c, k: r[a][k] == r[c][k]
    check("with the switch at One figure the grid is the one a page without the constellation draws, to the bit",
          same("off", "absent", "grid") and sum(r["off"]["grid"]) > 1, "%.1f of light" % sum(r["off"]["grid"]))
    check("and so is Scan's table read from it, and what a generator makes of that table: its picture pair and its "
          "heard pair, sample for sample", same("off", "absent", "table") and same("off", "absent", "picture")
          and same("off", "absent", "heard") and r["off"]["table"] is not None)
    diff_grid = sum(abs(a - c) for a, c in zip(r["on"]["grid"], r["off"]["grid"]))
    diff_heard = max(abs(a - c) for a, c in zip(r["on"]["heard"], r["off"]["heard"]))
    null("the switch on draws a different grid", diff_grid > 5 and r["on"]["drawn"] == 5,
         "%.1f of light moved, %d figures" % (diff_grid, r["on"]["drawn"]))
    null("and so a different table and a different sound", not same("on", "off", "table") and diff_heard > 1e-3,
         "heard differs by up to %.4f" % diff_heard)
    check("no page errors on the page's brain", not errors, "; ".join(errors[:3]))
    p.close()

    p, errors = opened(b, "")
    p.evaluate(SETUP, ["one", None, 0.3])
    p.evaluate("""async () => { for (const n of [48, 60, 64, 67]) midiNoteOn(n, 100);
                                await new Promise((r) => setTimeout(r, 900)); }""")
    away = p.evaluate("""async () => {
      el.drawWay.value = 'constellation'; el.drawWay.dispatchEvent(new Event('change'));
      await new Promise((r) => setTimeout(r, 200));
      return { kind: state.source.kind, live: constellationLive(), away: !el.drawAway.hidden,
               outline: !el.drawOutline.hidden, place: !el.drawConst.hidden, link: el.drawAwayLink.getAttribute('href') };
    }""")
    check("on the instrument's brain, choosing it draws nothing and says it is heard on the page's own, with the way there",
          away["kind"] == "host" and not away["live"] and away["away"] and not away["place"]
          and away["link"] == "?brain=js&draw=constellation", str(away))
    r = p.evaluate(REPLAY, [[["off", "one", False], ["chosen", "constellation", False]], False])
    check("and the grid it draws is the same to the bit as at One figure", r["off"]["grid"] == r["chosen"]["grid"]
          and r["chosen"]["drawn"] == 0 and sum(r["off"]["grid"]) > 1)
    check("no page errors on the instrument's brain", not errors, "; ".join(errors[:3]))
    p.close()

    print("\n--- never stored ---")
    p, errors = opened(b, "?brain=js")
    stored = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const before = encodeSetup(snapshot()), keys = [];
      try { for (let i = 0; i < localStorage.length; i++) keys.push(localStorage.key(i)); } catch (e) {}
      return { before, keys, steps: undoHistory.undo.length };
    }""")
    p.locator('[data-draw="way"]').select_option("constellation"); p.wait_for_timeout(700)
    p.locator('[data-draw="place"]').select_option("seeded"); p.wait_for_timeout(700)
    after = p.evaluate("""() => {
      const keys = [];
      try { for (let i = 0; i < localStorage.length; i++) keys.push(localStorage.key(i)); } catch (e) {}
      return { code: encodeSetup(snapshot()), keys, steps: undoHistory.undo.length,
               way: constellation.way };
    }""")
    check("choosing it with the mouse is no change to the setup's code, no step in undo and nothing in storage",
          after["way"] == "constellation" and after["code"] == stored["before"] and after["steps"] == stored["steps"]
          and sorted(after["keys"]) == sorted(stored["keys"]), "%d steps, keys %s" % (after["steps"], after["keys"]))
    p.locator("#envAttack").focus(); p.keyboard.press("ArrowRight"); p.wait_for_timeout(700)
    moved = p.evaluate("() => ({ code: encodeSetup(snapshot()), steps: undoHistory.undo.length })")
    null("a control that is in the setup, moved by a key the same way, changes the code and makes a step",
         moved["code"] != after["code"] and moved["steps"] > after["steps"], str(moved["steps"]))
    said = p.evaluate("""() => ({ ids: [el.drawWay, el.drawPlace, el.drawHands].map((s) => s.id),
      keys: [el.drawWay, el.drawPlace, el.drawHands].map(wordsKey), plain: wordsKey(document.createElement('select')) })""")
    check("its menus have no ids, which parity would hold to the core's panel, and the info line still has their words",
          said["ids"] == ["", "", ""] and said["keys"] == ["drawWay", "drawPlace", "drawHands"], str(said))
    null("a menu with no id and no data-draw has no words", said["plain"] is None, str(said["plain"]))
    p.close()
    p, _ = opened(b, "?brain=js&draw=constellation")
    asked = p.evaluate("() => ({ way: constellation.way, shown: el.drawWay.value, place: !el.drawConst.hidden })")
    p.close()
    p, _ = opened(b, "?brain=js")
    plain = p.evaluate("() => constellation.way")
    p.close()
    check("the address can ask for it, and the page opens on One figure otherwise",
          asked == {"way": "constellation", "shown": "constellation", "place": True} and plain == "one", "%s, %s" % (asked, plain))

    # ------------------------------------------------------------------
    print("\n--- each note where its place puts it ---")
    p, errors = opened(b)
    notes = [48, 64, 67, 74]
    grids = {}
    for way in ("constellation", "one"):
        p.evaluate(SETUP, [way, "pitch", 0])
        grids[way] = p.evaluate("""async (notes) => {
          for (const n of notes) midiNoteOn(n, 127);
          await new Promise((r) => setTimeout(r, 700));
          const g = Array.from(pictureEngine.cells);
          midiPanic();
          return g;
        }""", notes)
    found = {}
    for way, g in grids.items():
        found[way] = []
        for n in notes:
            u, v = cell_of(*place(n, "pitch"))
            xs, ys, w = lit_near(g, u, v, 5)
            ok = len(w) >= 4 and np.hypot((xs * w).sum() / w.sum() - u, (ys * w).sum() / w.sum() - v) < 1.0
            found[way].append(bool(ok))
    check("by pitch, each of C3, E4, G4 and D5 is drawn within a cell of its place on the clock face and its octave's ring",
          all(found["constellation"]), str(found["constellation"]))
    null("the one figure, the same notes, is found at none of those places in that way",
         sum(found["one"]) <= 1, str(found["one"]))

    print("\n--- as large as it is loud ---")
    p.evaluate(SETUP, ["constellation", "clock", 0])
    sizes = p.evaluate("""async () => {
      midiNoteOn(60, 127); midiNoteOn(66, 64);
      await new Promise((r) => setTimeout(r, 800));
      const g = Array.from(pictureEngine.cells);
      const drawn = constellation.drawn.map((d) => [d.note, d.size]);
      // The hand's Level is part of how loud: doubled, every figure doubles.
      setControl('amp', 110); await new Promise((r) => setTimeout(r, 300));
      const louder = constellation.drawn.map((d) => [d.note, d.size]);
      setControl('amp', 55);
      midiPanic();
      return { g, drawn, louder };
    }""")
    radii = {}
    for n, vel in ((60, 127), (66, 64)):
        want = 0.58 * 0.7 * vel / 127
        u, v = cell_of(*place(n, "clock"))
        xs, ys, w = lit_near(sizes["g"], u, v, want * 32 * 1.4)
        radii[n] = (float(np.mean(np.hypot(xs - u, ys - v))) / 32, want)
    print("    measured radius %.3f against %.3f at full velocity, %.3f against %.3f at half" %
          (radii[60][0], radii[60][1], radii[66][0], radii[66][1]))
    check("on the clock each figure's radius on the grid is its level's: within 15% of 0.58 x sustain x velocity",
          all(abs(m - w) < 0.15 * w for m, w in radii.values()), str(radii))
    ratio = radii[60][0] / radii[66][0]
    check("and the note struck twice as hard draws twice as large", abs(ratio - 127 / 64) < 0.2, "%.2f" % ratio)
    null("not the same size whatever the velocity", abs(ratio - 1) > 0.5, "%.2f" % ratio)
    by_level = [l[1] / d[1] for d, l in zip(sorted(sizes["drawn"]), sorted(sizes["louder"]))]
    check("and the hand's Level twice as high draws both twice as large", len(by_level) == 2
          and all(abs(x - 2) < 1e-9 for x in by_level), str(by_level))
    null("a Level ignored would leave them as they were", all(abs(x - 1) > 0.5 for x in by_level), str(by_level))

    shapes = {}
    for shape in ("sine", "triangle"):
        shapes[shape] = p.evaluate("""async (shape) => {
          el.shape.value = shape; el.shape.dispatchEvent(new Event('change'));
          midiNoteOn(60, 127);
          await new Promise((r) => setTimeout(r, 700));
          const g = Array.from(pictureEngine.cells);
          midiPanic(); await new Promise((r) => setTimeout(r, 400));
          return g;
        }""", shape)
    p.evaluate("() => { el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change')); }")
    def spread(g):
        u, v = cell_of(*place(60, "clock"))
        xs, ys, w = lit_near(g, u, v, 0.5 * 32)
        e = np.hypot(xs - u, ys - v); l1 = np.abs(xs - u) + np.abs(ys - v)
        return float(np.std(e) / np.mean(e)), float(np.std(l1) / np.mean(l1))
    ring, diamond = spread(shapes["sine"]), spread(shapes["triangle"])
    print("    spread of distance from the centre, round and by the diamond's measure: sine %.3f, %.3f; triangle %.3f, %.3f"
          % (ring[0], ring[1], diamond[0], diamond[1]))
    check("a sine's figure is a ring: every lit cell nearly one distance from its centre", ring[0] < 0.1 and ring[0] < ring[1], str(ring))
    check("a triangle's is a diamond: one distance by |x| + |y|", diamond[1] < 0.1 and diamond[1] < diamond[0], str(diamond))
    null("the ring is not a diamond, nor the diamond a ring", ring[1] > 0.1 and diamond[0] > 0.1)

    print("\n--- in time: it grows on the attack and fades with the release ---")
    grown = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const set = (id, v) => { el[id].value = String(v); el[id].dispatchEvent(new Event('input')); };
      set('envAttack', 200); set('envRelease', 600);
      const size = () => (constellation.drawn[0] ? constellation.drawn[0].size : 0);
      const out = { up: [], down: [] };
      const t0 = performance.now();
      midiNoteOn(60, 127);
      // Inside the 200 ms attack, and then held, past the decay, at the sustain.
      for (const at of [30, 100, 180, 600]) { await wait(at - (performance.now() - t0)); out.up.push(size()); }
      const t1 = performance.now();
      midiNoteOff(60);
      for (const at of [100, 350]) { await wait(at - (performance.now() - t1)); out.down.push(size()); }
      await wait(900);
      out.gone = constellation.drawn.length;
      set('envAttack', 8); set('envRelease', 180);
      return out;
    }""")
    print("    size on the attack %s, on the release %s" % (["%.3f" % x for x in grown["up"]], ["%.3f" % x for x in grown["down"]]))
    check("a slow attack grows the figure, a release shrinks it, and it goes when the release is over",
          grown["up"][0] < grown["up"][1] < grown["up"][2] and abs(grown["up"][3] - 0.58 * 0.7) < 1e-6
          and grown["up"][3] > grown["down"][0] > grown["down"][1] > 0
          and grown["gone"] == 0, str(grown))
    null("not one size from the start: 30 ms into the attack it is under two thirds of the attack's top",
         grown["up"][0] < 0.67 * grown["up"][2], "%.3f of %.3f" % (grown["up"][0], grown["up"][2]))
    check("no page errors placing and sizing", not errors, "; ".join(errors[:3]))
    p.close()

    # ------------------------------------------------------------------
    print("\n--- Scan reads it ---")
    readings = {}
    for how in ("clock", "pitch"):
        p, errors = opened(b)
        p.evaluate(SETUP, ["constellation", how, 0.3])
        readings[how] = p.evaluate("""async () => {
          const wait = (ms) => new Promise((r) => setTimeout(r, ms));
          el.oscScan.value = '60'; el.oscScan.dispatchEvent(new Event('input'));
          // The strike lays light on Scan's circle itself; here only the figures may.
          el.scanStrike.value = '0'; el.scanStrike.dispatchEvent(new Event('input'));
          for (const n of [60, 64, 67]) midiNoteOn(n, 100);
          await wait(4500);
          const path = Object.assign({}, scan.paths[0]);
          const drawn = constellation.drawn.map((d) => Object.assign({}, d));
          // Each figure laid into a grid of its own with the others, and without it.
          const xs = new Float64Array(200), ys = new Float64Array(200);
          const grid = (leave) => {
            const e = makePictureEngine();
            drawn.forEach((d, k) => { if (k !== leave) { const n = constellationTrace(d, xs, ys); e.deposit(plot, xs, ys, n, null); } });
            return e.cells;
          };
          const read = (g) => Array.from(scanRead(g, path, scan.soft));
          const table = (g) => Array.from(scanTables(scanRead(g, path, scan.soft)).levels[0]);
          const all = grid(-1);
          const full = table(all), light = read(all);
          const without = drawn.map((d, k) => table(grid(k))), unlit = drawn.map((d, k) => read(grid(k)));
          const live = scanGeometry(pictureEngine.cells), mine = scanGeometry(all);
          const sent = scan.tables[0] ? Array.from(scan.tables[0].levels[0]) : null;
          midiPanic();
          return { path, drawn, full, without, light, unlit, live, mine, sent };
        }""")
        check("no page errors on %s" % how, not errors, "; ".join(errors[:3]))
        p.close()
    out = {}
    for how, s in readings.items():
        path = s["path"]
        r = max(path["r"], 2 / N)
        rc = (path["cx"] + 0.35 * r, path["cy"] + 0.2 * r); rr = 0.8 * r
        cross, delta, lit = [], [], []
        for k, d in enumerate(s["drawn"]):
            u, v = (d["x"] + 1) / 2, (1 - d["y"]) / 2
            gap = abs(np.hypot(u - rc[0], v - rc[1]) - rr) - d["size"] / 2
            cross.append(gap <= 0)
            delta.append(float(np.mean(np.abs(np.asarray(s["full"]) - np.asarray(s["without"][k])))))
            lit.append(float(np.mean(np.asarray(s["light"]) - np.asarray(s["unlit"][k]))))
        out[how] = (cross, delta, s, lit)
        print("    %s: Scan's path at (%.3f, %.3f) r %.3f (the figures alone put it at (%.3f, %.3f) r %.3f); crossed %s; "
              "with each figure taken out the light read falls by %s (of %.4f) and the table moves by %s"
              % (how, path["cx"], path["cy"], path["r"], s["mine"]["cx"], s["mine"]["cy"], s["mine"]["r"], cross,
                 ["%.4f" % x for x in lit], float(np.mean(s["light"])), ["%.4f" % x for x in delta]))
    cc, cd, cs, cl = out["clock"]
    pc_, pd, ps, pl = out["pitch"]
    check("the circle Scan reads is the one the constellation puts it at: its path within 0.02 of the figures' own geometry",
          all(abs(s["path"][k] - s["mine"][k]) < 0.02 for s in (cs, ps) for k in ("cx", "cy", "r")))
    check("on the clock, Scan's circle crosses every note's figure", len(cc) == 3 and all(cc), str(cc))
    check("and taking any one of them out changes the table: by over 0.02 on average across it", min(cd) > 0.02,
          str(["%.4f" % x for x in cd]))
    check("by pitch, C, E and G in the middle register sit clear of it", len(pc_) == 3 and not any(pc_), str(pc_))
    check("and Scan reads far less of them: under a fifth of the clock's light in all, and from any one figure under half "
          "the least a figure on the clock gives", float(np.mean(ps["light"])) < 0.2 * float(np.mean(cs["light"]))
          and max(pl) < 0.5 * min(cl), "%.4f against %.4f in all; %.4f against %.4f"
          % (float(np.mean(ps["light"])), float(np.mean(cs["light"])), max(pl), min(cl)))
    # What it does not hold, and the report says: Scan evens every table to a
    # peak of one, so the faint light at the blur's edge is played as loud as
    # a figure across the circle, and a figure taking its faint part away
    # still moves the table. Printed, not asserted, until the owner has heard it.
    print("    by pitch the table still moves by up to %.4f for a figure taken out, against %.4f at least on the clock: "
          "the table is evened to a peak of one, so faint light is heard as a shape" % (max(pd), min(cd)))
    null("the clock's crossing judged by the pitch layout's rule fails: not every place crosses", not all(pc_))
    check("and the table Scan sent the generator is its reading of the constellation, place by place different",
          cs["sent"] is not None and ps["sent"] is not None
          and float(np.mean(np.abs(np.asarray(cs["sent"]) - np.asarray(ps["sent"])))) > 0.02)

    # ------------------------------------------------------------------
    print("\n--- a fast run leaves a trail ---")
    trails = {}
    run = list(range(60, 73))
    for way in ("constellation", "one"):
        p, errors = opened(b)
        p.evaluate(SETUP, [way, "pitch", 0.02])
        trails[way] = p.evaluate("""async (run) => {
          const wait = (ms) => new Promise((r) => setTimeout(r, ms));
          for (const n of run) { midiNoteOn(n, 110); await wait(70); midiNoteOff(n); }
          await wait(500);
          return Array.from(pictureEngine.cells);
        }""", run)
        p.close()
    counted = {}
    for way, g in trails.items():
        top = max(g)
        comps = [c for c in components(g, 0.15 * top) if c[2] >= 2]
        matched = 0
        for n in run:
            u, v = cell_of(*place(n, "pitch"))
            if any(np.hypot(cu - u, cv - v) < 2.0 for cu, cv, _ in comps): matched += 1
        counted[way] = (len(comps), matched)
    print("    half a second after the run: %d patches of light at %d of the run's places with the constellation; "
          "%d at %d with the one figure" % (counted["constellation"] + counted["one"]))
    check("the grid holds a figure at the place of at least ten of the run's thirteen notes", counted["constellation"][1] >= 10,
          str(counted["constellation"]))
    null("the one figure, the same run, leaves light at hardly any of those places", counted["one"][1] <= 2, str(counted["one"]))

    # ------------------------------------------------------------------
    print("\n--- it fits ---")
    for w, h in ((1400, 900), (1100, 860), (1200, 680), (1100, 680), (960, 600)):
        p, errors = opened(b, "?brain=js&draw=constellation", w, h)
        fit = p.evaluate("""async () => {
          const wait = (ms) => new Promise((r) => setTimeout(r, ms));
          setMidiMode('poly');
          el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change')); await wait(150);
          el.drawPlace.value = 'seeded'; el.drawPlace.dispatchEvent(new Event('change'));
          setScreenKeys(true); if (!photo.on) el.photoButton.click();
          setBenchTab('play'); await wait(300);
          const shown = [el.drawConst, el.drawPlace, el.drawHands, el.drawSeed].every((e) => !e.hidden && e.offsetHeight > 0);
          const over = el.benchBody.scrollHeight - el.benchBody.clientHeight;
          const pad = document.createElement('div'); pad.style.height = '400px';
          el.midiGroup.append(pad); await wait(100);
          const padded = el.benchBody.scrollHeight - el.benchBody.clientHeight;
          pad.remove();
          return { shown, over, padded, live: constellationLive() };
        }""")
        check("at %dx%d Play does not scroll with the place, both hands and the seed showing on two hands, keys and Photocell"
              % (w, h), fit["shown"] and fit["over"] <= 0 and fit["live"], str(fit))
        null("a section 400 px taller scrolls it (%dx%d)" % (w, h), fit["padded"] > 0, str(fit["padded"]))
        check("no page errors (%dx%d)" % (w, h), not errors, "; ".join(errors[:3]))
        p.close()

    # ------------------------------------------------------------------
    print("\n--- the cost of a frame ---")
    p, errors = opened(b)
    cost = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const out = {};
      const time = async (way, notes, layered) => {
        midiPanic();
        el.midiLayers.value = layered ? 'layer' : 'off'; el.midiLayers.dispatchEvent(new Event('change'));
        el.drawWay.value = way; el.drawWay.dispatchEvent(new Event('change'));
        for (const n of notes) midiNoteOn(n, 100);
        await wait(700);
        const frame = state.held;
        setRunning(false); state.held = null; await wait(80);
        const each = [], figures = [];
        for (let i = 0; i < 300; i++) {
          const t0 = performance.now();
          drawMain(frame, 16); drawConstellation(16);
          each.push(performance.now() - t0); figures.push(constellation.drawn.length);
        }
        each.sort((a, b) => a - b);
        state.held = frame; setRunning(true);
        // The clock is coarsened to a tenth of a millisecond here, so the mean says more than the median.
        return { mean: each.reduce((a, b) => a + b, 0) / each.length, p90: each[270], figures: Math.max(...figures) };
      };
      const six = [48, 55, 60, 64, 67, 71], eight = [48, 52, 55, 59, 62, 65, 69, 72];
      out.one6 = await time('one', six, false);
      out.con6 = await time('constellation', six, false);
      out.one16 = await time('one', eight, true);
      out.con16 = await time('constellation', eight, true);
      midiPanic();
      return out;
    }""")
    for k, label in (("one6", "one figure, six notes"), ("con6", "constellation, six figures"),
                     ("one16", "one figure, two layers of eight"), ("con16", "constellation, sixteen figures")):
        print("    %-34s mean %.3f ms, 90th centile %.3f ms a frame (%d figures)" % (label, cost[k]["mean"], cost[k]["p90"], cost[k]["figures"]))
    check("the frame drew the figures it was timed on: six, and sixteen on two layers",
          cost["con6"]["figures"] == 6 and cost["con16"]["figures"] == 16 and cost["one6"]["figures"] == 0, str(cost))
    check("and sixteen figures cost a frame under 8 ms, far above what they cost here", cost["con16"]["mean"] < 8,
          "%.3f ms" % cost["con16"]["mean"])
    check("no page errors timing", not errors, "; ".join(errors[:3]))
    p.close()
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the constellation draws each note where it lands, Scan hears it, and off it is not there")
