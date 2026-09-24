"""Stage E2: what the picture says - five sources and a verdict.

Every source has to pass the plan's gate before it may be routed: a small change
in the picture makes a small change in the value. Each check here perturbs a
fixture a little and bounds how far the source moves, and each fixture is built
to be the place where a discontinuous form WOULD jump:

- coverage, on a faded figure whose cells all sit just under one half - where a
  count of cells over a threshold would flip every one of them at once;
- roundness, on a figure shrinking to nothing - where a ratio with no floor
  under it would read a perfect tiny circle until the frame it vanished;
- direction, across a line, where the travel reverses.

Then the verdict, on constructed sequences before any real loop: a frozen
picture, one that repeats, one that never does, one that fills the screen.
Each verdict is checked to be the one its fixture should give AND not the one
any other fixture gives, which is the null test for a classifier.

Then the survey that chose the sixth source, re-run, with the choice checked
against it: if a change ever makes edge contact the better candidate, this is
the test that says so.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
SURVEY = os.path.join(HERE, "survey.js")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

# Grids made here rather than drawn, so the fixture is exactly what the check
# says it is. An ellipse of half-axes a, b, laid at `level`.
HELPERS = """() => {
  const N = PHOSPHOR_N;
  window.__ellipse = (a, b, level, turn) => {
    const g = new Float32Array(N * N);
    const t0 = turn || 0;
    for (let k = 0; k < 4000; k++) {
      const t = k / 4000 * 2 * Math.PI;
      const x = a * Math.cos(t), y = b * Math.sin(t);
      const u = x * Math.cos(t0) - y * Math.sin(t0), v = x * Math.sin(t0) + y * Math.cos(t0);
      const cx = Math.floor((u + 1) / 2 * N), cy = Math.floor((1 - (v + 1) / 2) * N);
      if (cx >= 0 && cy >= 0 && cx < N && cy < N) g[cy * N + cx] = level;
    }
    return g;
  };
  // The same figures as paths, which is what roundness is measured from.
  window.__ring = (a, b, turn) => {
    const m = makeMoments(), t0 = turn || 0, K = 720;
    let px = null, py = null;
    for (let k = 0; k <= K; k++) {
      const t = k / K * 2 * Math.PI, x = a * Math.cos(t), y = b * Math.sin(t);
      const u = x * Math.cos(t0) - y * Math.sin(t0), v = x * Math.sin(t0) + y * Math.cos(t0);
      if (px !== null) m.add(px, py, u, v, 1);
      px = u; py = v;
    }
    return m;
  };
  window.__box = (h) => {
    const m = makeMoments();
    m.add(-h, -h, h, -h, 1); m.add(h, -h, h, h, 1); m.add(h, h, -h, h, 1); m.add(-h, h, -h, -h, 1);
    return m;
  };
  window.__square = (h, level) => {
    const g = new Float32Array(N * N);
    const lo = Math.floor((1 - h) / 2 * N), hi = Math.floor((1 + h) / 2 * N);
    for (let i = lo; i <= hi; i++) {
      g[lo * N + i] = level; g[hi * N + i] = level; g[i * N + lo] = level; g[i * N + hi] = level;
    }
    return g;
  };
  window.__dot = (u, v) => {
    const g = new Float32Array(N * N);
    const cx = Math.max(0, Math.min(N - 1, Math.floor(u * N)));
    const cy = Math.max(0, Math.min(N - 1, Math.floor(v * N)));
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      const x = cx + dx, y = cy + dy;
      if (x >= 0 && y >= 0 && x < N && y < N) g[y * N + x] = 1;
    }
    return g;
  };
  window.__pair = (phase, amp) => {
    const n = 2048, l = new Float32Array(n), r = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const t = i / n * 2 * Math.PI * 4;
      l[i] = amp * Math.sin(t); r[i] = amp * Math.sin(t + phase);
    }
    return { channels: [l, r], turned: true };
  };
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
    p.wait_for_timeout(200)
    p.evaluate(HELPERS)

    print("\n--- roundness ---")
    rnd = p.evaluate("""() => ({
      circle: __ring(0.5, 0.5).roundness(),
      square: __box(0.4).roundness(),
      line: __ring(0.7, 0).roundness(),
      flat: __ring(0.6, 0.3).roundness(),
      turned: __ring(0.6, 0.3, 0.7).roundness(),
      empty: makeMoments().roundness(),
      // One circle, cut into six hundred segments on its left half and twelve
      // on its right - which is what the beam does, short where it is slow
      // and long where it is fast. Weighted by length it is still a circle;
      // weighted by segment it would lean left and read flatter.
      uneven: (() => {
        const m = makeMoments();
        const at = (t) => [0.5 * Math.cos(t), 0.5 * Math.sin(t)];
        const cuts = [];
        for (let k = 0; k <= 600; k++) cuts.push(Math.PI / 2 + k / 600 * Math.PI);
        for (let k = 1; k <= 12; k++) cuts.push(3 * Math.PI / 2 + k / 12 * Math.PI);
        for (let i = 1; i < cuts.length; i++) {
          const [x0, y0] = at(cuts[i - 1]), [x1, y1] = at(cuts[i]);
          m.add(x0, y0, x1, y1, 1);
        }
        return m.roundness();
      })(),
    })""")
    print("    circle %.3f, square %.3f, line %.3f, 2:1 ellipse %.3f and turned %.3f, empty %s"
          % (rnd["circle"], rnd["square"], rnd["line"], rnd["flat"], rnd["turned"], rnd["empty"]))
    check("a circle is round and a line is not", rnd["circle"] > 0.97 and rnd["line"] < 0.05, str(rnd))
    # Measured from the grid's cells this read 0.557 upright and 0.610 turned:
    # a rasterised line lights more cells per unit length along an axis than
    # across one. From the path it reads the same at any angle.
    check("a 2:1 ellipse reads the same whichever way it is turned",
          0.45 < rnd["flat"] < 0.65 and abs(rnd["turned"] - rnd["flat"]) < 1e-6, str(rnd))
    check("a circle is a circle however unevenly the beam divides it into strokes",
          rnd["uneven"] > 0.97, "%.3f" % rnd["uneven"])
    check("its blind spot, asserted so a change to the measure changes the plan's sentence: "
          "a square is as round as a circle", rnd["square"] > 0.97, "%.3f" % rnd["square"])
    check("and a dark screen is nought, not 0/0", rnd["empty"] == 0, str(rnd["empty"]))

    fade = p.evaluate("""() => {
      // A figure shrinking to nothing, a hundredth of the screen at a time.
      const out = [];
      for (let k = 30; k >= 0; k--) out.push(__ring(k / 60, k / 60).roundness());
      let worst = 0;
      for (let i = 1; i < out.length; i++) worst = Math.max(worst, Math.abs(out[i] - out[i - 1]));
      return { worst, last: out.slice(-4) };
    }""")
    print("    shrinking a circle to nothing: largest step %.3f, the last few %s"
          % (fade["worst"], [round(v, 3) for v in fade["last"]]))
    check("fading to nothing is a slope, not a cliff", fade["worst"] < 0.35, "%.3f" % fade["worst"])

    print("\n--- coverage, change and novelty: continuous ---")
    cont = p.evaluate("""() => {
      const N = PHOSPHOR_N;
      // A faded figure: every lit cell at 0.49, just under a half.
      const faded = __ellipse(0.6, 0.4, 0.49);
      const nudged = faded.map((v) => v > 0 ? v + 0.02 : 0);
      const cover = (g) => { const m = makePictureMeter(); m.update(g, 1 / 60); return m.coverage; };
      const change = (a, b) => { const m = makePictureMeter(); m.update(a, 1 / 60); m.update(b, 1 / 60); return m.change; };
      const base = __ellipse(0.6, 0.4, 1);
      const moved = __ellipse(0.6, 0.41, 1);
      return {
        coverA: cover(faded), coverB: cover(nudged),
        changeSame: change(base, base), changeNear: change(base, moved), changeFar: change(base, __dot(0.9, 0.1)),
      };
    }""")
    print("    coverage %.4f -> %.4f when every lit cell moves 0.49 -> 0.51; change: same %.3f, "
          "nudged %.3f, different %.3f"
          % (cont["coverA"], cont["coverB"], cont["changeSame"], cont["changeNear"], cont["changeFar"]))
    check("coverage moves a little when every cell crosses one half - it is not a count over a threshold",
          abs(cont["coverB"] - cont["coverA"]) < 0.02, "%.4f" % abs(cont["coverB"] - cont["coverA"]))
    check("change is nought for the same picture and one for a different one",
          cont["changeSame"] == 0 and cont["changeFar"] > 0.95, str(cont))
    check("and small for a small difference", cont["changeNear"] < 0.5, "%.3f" % cont["changeNear"])

    novel = p.evaluate("""() => {
      // Fifteen seconds of one ellipse, then the same ellipse opening up a
      // little at a time: novelty should rise gradually, not jump from "seen
      // it" to "never seen it" - which is what a yes-or-no would do.
      const m = makePictureMeter(), dt = 1 / 60;
      for (let f = 0; f < 60 * 15; f++) m.update(__ellipse(0.6, 0.3, 1), dt);
      const out = [];
      for (let k = 0; k <= 20; k++) {
        const g = __ellipse(0.6, 0.3 + k * 0.01, 1);
        for (let f = 0; f < 15; f++) m.update(g, dt);
        out.push(m.novelty);
      }
      let worst = 0;
      for (let i = 1; i < out.length; i++) worst = Math.max(worst, Math.abs(out[i] - out[i - 1]));
      return { worst, first: out[0], last: out[out.length - 1] };
    }""")
    print("    an ellipse opening up a hundredth at a time: novelty %.3f -> %.3f, largest step %.3f"
          % (novel["first"], novel["last"], novel["worst"]))
    check("novelty rises with how far the picture has gone from before, a step at a time",
          novel["last"] > novel["first"] + 0.2 and novel["worst"] < 0.25, str(novel))

    print("\n--- direction ---")
    turn = p.evaluate("""() => {
      const was = { pair: state.xyPair, zoom: state.zoom };
      state.xyPair = [0, 1];
      const d = (phase) => shapeOfPair(__pair(phase, 0.5)).signed;
      const across = [];
      for (let k = -10; k <= 10; k++) across.push(d(k / 100));
      let worst = 0;
      for (let i = 1; i < across.length; i++) worst = Math.max(worst, Math.abs(across[i] - across[i - 1]));
      // Off the centre of the screen, which must not change which way it turns.
      const off = state.channels[0].offset;
      state.channels[0].offset = 0.3;
      const offset = d(-Math.PI / 2);
      state.channels[0].offset = off;
      const out = { ccw: d(-Math.PI / 2), cw: d(Math.PI / 2), line: d(0), worst, offset };
      state.xyPair = was.pair;
      return out;
    }""")
    print("    one way %.3f, the other %.3f, a line %.3f; largest step across the line %.3f"
          % (turn["ccw"], turn["cw"], turn["line"], turn["worst"]))
    check("a circle travelled one way reads one, the other way minus one",
          turn["ccw"] > 0.95 and turn["cw"] < -0.95, str(turn))
    check("a line has no direction", abs(turn["line"]) < 1e-6, str(turn["line"]))
    check("and it passes through nought smoothly as the travel reverses",
          turn["worst"] < 0.1, "%.3f" % turn["worst"])
    check("wherever on the screen the figure sits", abs(turn["offset"] - turn["ccw"]) < 1e-6,
          "%.4f against %.4f" % (turn["offset"], turn["ccw"]))

    print("\n--- the verdict, on constructed sequences ---")
    verdicts = p.evaluate("""() => {
      const N = PHOSPHOR_N, dt = 1 / 60, frames = 60 * 10;
      const run = (grid) => {
        const m = makePictureMeter();
        let first = null;
        for (let f = 0; f < frames; f++) {
          m.update(grid(f * dt), dt);
          if (first === null && m.verdict() !== 'listening') first = f * dt;
        }
        return { verdict: m.verdict(), from: first, novelty: m.novelty, change: m.change };
      };
      const still = __ellipse(0.5, 0.3, 1);
      return {
        frozen: run(() => still),
        repeating: run((t) => __dot(0.5 + 0.35 * Math.cos(t * 2 * Math.PI), 0.5 + 0.35 * Math.sin(t * 2 * Math.PI))),
        // A path that never comes back: a spiral out, then across the rest.
        never: run((t) => {
          const s = t / 10;
          return __dot(0.5 + 0.45 * s * Math.cos(s * 9 * Math.PI), 0.5 + 0.45 * s * Math.sin(s * 9 * Math.PI));
        }),
        full: run((t) => { const g = new Float32Array(N * N).fill(0.8); g[Math.floor(t * 60) % g.length] = 0; return g; }),
        early: (() => { const m = makePictureMeter(); for (let f = 0; f < 60; f++) m.update(still, dt); return m.verdict(); })(),
      };
    }""")
    for k in ("frozen", "repeating", "never", "full"):
        print("    %-9s %s" % (k, verdicts[k]))
    print("    after one second: %s" % verdicts["early"])
    want = {"frozen": "settled", "repeating": "cycling", "never": "wandering", "full": "running away"}
    for k, v in want.items():
        others = [o for o in want if o != k]
        check("a %s picture is %s, and no other fixture is" % (k, v),
              verdicts[k]["verdict"] == v and all(verdicts[o]["verdict"] != v for o in others),
              str({o: verdicts[o]["verdict"] for o in want}))
    check("and nothing is said until there is history to say it from",
          verdicts["early"] == "listening", verdicts["early"])

    print("\n--- on the page ---")
    live = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setDisplay('xy'); genSet('shape', 'sine'); genSet('interval', 0); genSet('just', true);
      state.persistence = 0.12; el.persistence.value = '0.12';
      el.photoButton.click();
      const ids = ['photo.1', 'picture.round', 'picture.cover', 'picture.change', 'picture.novelty', 'picture.' + SIXTH];
      const registered = ids.filter((id) => MOD_SOURCES.has(id));
      const rules = ids.every((id) => { const s = MOD_SOURCES.get(id); return s && s.fromPicture && s.reach === PHOTO_REACH; });
      addRouting('picture.round', 'filter.res');
      const refused = !state.modRoutings.some((r) => r.sourceId === 'picture.round');
      await wait(6500);
      const readout = el.readoutDetail.textContent;
      // The circle becomes a line: roundness has to follow, and no faster than
      // the slew allows. With persistence OFF, so the picture - and the raw
      // measure - change in one frame: with any persistence the raw value falls
      // as the old figure fades, slower than the slew, and a missing slew
      // would never show.
      state.persistence = 0; el.persistence.value = '0';
      await new Promise((r) => setTimeout(r, 300));
      const start = performance.now(), trace = [];
      genSet('phase', 0);
      while (performance.now() - start < 2500) {
        await new Promise((r) => requestAnimationFrame(r));
        trace.push([performance.now() - start, picture.round, picture.raw.round]);
      }
      genSet('phase', Math.PI / 2);
      state.persistence = 0.12; el.persistence.value = '0.12';
      let over = 0;
      const top = trace[0][1];
      for (const [t, v] of trace) over = Math.max(over, (top - v) - (2 * t / 1000 + 0.07));
      const settled = trace[trace.length - 1];
      el.photoButton.click();
      const gone = ids.filter((id) => MOD_SOURCES.has(id));
      return { registered, rules, refused, readout, gone, top, over,
               end: settled[1], endRaw: settled[2],
               direction: MOD_SOURCES.has('picture.' + SIXTH) };
    }""")
    print("    %s" % live)
    check("the five come with the photocell, under the same rules as it",
          len(live["registered"]) == 6 and live["rules"], str(live["registered"]))
    check("a picture source may not reach the filter either", live["refused"], "")
    check("the readout says what the loop is doing", "loop settled" in live["readout"], live["readout"])
    check("and they go when the photocell does", live["gone"] == [], str(live["gone"]))
    print("    circle to line: roundness %.3f -> %.3f (raw %.3f); over the slew envelope by %.3f"
          % (live["top"], live["end"], live["endRaw"], live["over"]))
    check("roundness follows the picture as the screen forgets the old one",
          live["top"] > 0.9 and live["endRaw"] < 0.1 and live["end"] < 0.15, str(live))
    check("and no faster than two full swings a second", live["over"] <= 0, "%.3f" % live["over"])

    print("\n--- the sixth slot, surveyed with the loop closed ---")
    p.evaluate("""() => { setPhoto(true);
      for (const [key, label] of [['edge', 'Edge contact']])
        if (!MOD_SOURCES.has('picture.' + key))
          registerSource({ id: 'picture.' + key, label, ink: 'ch3', fromPicture: true,
                           reach: PHOTO_REACH, start: PHOTO_START, value: () => picture[key] }); }""")
    survey = p.evaluate(open(SURVEY).read(), [4])
    for name, r in survey["result"].items():
        print("    %-7s entropy %.2f bits; shares %s; adds %.2f bits; not nought %.0f%% of the time"
              % (name, r["entropy"], r["shared"], r["adds"], 100 * r["nonzero"]))
    chosen = p.evaluate("() => SIXTH")
    other = "edge" if chosen == "signed" else "signed"
    check("the source in the sixth slot is the one that adds more",
          survey["result"][chosen]["adds"] > survey["result"][other]["adds"],
          "%s %.2f against %s %.2f" % (chosen, survey["result"][chosen]["adds"],
                                       other, survey["result"][other]["adds"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the picture's sources are continuous, and the verdict tells its fixtures apart")
