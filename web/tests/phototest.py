"""The photocell, Stage E1: the phosphor grid, the reticle, and the loop.

What would go wrong, and what is checked for it:

- the grid not being where the beam drew. Checked against the canvas's own
  pixels, cell by cell, on figures that are NOT symmetric - a waveform in Y-T
  and a 2:3 figure in X-Y. A circle is the default figure and the wrong
  fixture: it is its own transpose, so a grid with X and Y swapped would agree
  with it perfectly;
- the grid fading at a different rate from the screen. Checked by measuring
  both, the canvas as ink left in a pixel, over the same frames;
- a reading that jumps as the reticle crosses a cell, which would inject the
  instability every loop defence exists to prevent;
- the defences not holding: the slew limit, the reach ceiling (at the point of
  USE, not only where an amount is stored), and the destinations a source
  reading the picture may not reach;
- the reticle's own controls leaking into the page's: its drag setting the
  trigger level, its arrow keys moving the timebase.
"""
# On the default page since stage 5, step 3, batch 6 (14 Nov), where the
# instrument is the brain; until then the first thirty checks were on
# ?brain=js, the figure under each set with genSet and state.persistence by
# hand, which the instrument never hears. They move the controls a player
# moves now (the Level, the Interval and Shape menus, the Persistence menu,
# the display's buttons), so the instrument plays what the face draws.
#
# What the face draws into here is the face's own grid (phosphor.grid, the
# second grid STAGE5-INVENTORY.md section 1 found, the compiled Phosphor on
# the main thread fed the instrument's lanes): the Persistence's reference,
# what the photocell's card shows and what step 5 points at the instrument's.
# So the rows that hold the face to its screen stay - the grid where the
# beam drew, fading at the screen's rate, Clear, the spectrogram, the
# reticle's controls, the routing rules and what a code brings back - and
# the grid's and the photocell's own arithmetic (its fade and its two ends,
# the compositing, the reading, its smoothness and slew, and the loop held
# inside its ranges) is core/tests/pieces/photo.py's, on the core's Phosphor
# and on the instrument rendered offline.
import os, sys
from playwright.sync_api import sync_playwright
import corpus

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

# Which grid cells the canvas has trace ink in, and which the grid has lit, and
# how well each is covered by the other within one cell. The border row and
# column are left out: the X-Y frame is drawn in a dark ink of its own.
AGREE = """async ([blushIsTrace]) => {
  await new Promise((r) => setTimeout(r, 500));
  const N = PHOSPHOR_N, dpr = window.devicePixelRatio || 1;
  const ctx = el.trace.getContext('2d');
  const img = ctx.getImageData(Math.round(plot.x * dpr), Math.round(plot.y * dpr),
                               Math.round(plot.w * dpr), Math.round(plot.h * dpr));
  const W = img.width, H = img.height, d = img.data;
  const ink = new Uint8Array(N * N);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const k = (y * W + x) * 4;
    // Trace inks are well below the graticule's green channel (217) and the
    // paper's (252); the antialiased fringe of a stroke is not counted. In Y-T
    // the dashed trigger-level line is drawn in the blush accent, and it is
    // not the beam, so reddish ink is left out there. In X-Y the figure itself
    // is drawn in blush, so there it counts.
    const reddish = d[k] - d[k + 1] > 40;
    if (d[k + 1] < 185 && (blushIsTrace || !reddish)) {
      const cx = Math.min(N - 1, Math.floor(x / W * N)), cy = Math.min(N - 1, Math.floor(y / H * N));
      ink[cy * N + cx] = 1;
    }
  }
  const lit = (i) => phosphor.grid[i] > 0.05;
  const near = (arr, cx, cy) => {
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      const x = cx + dx, y = cy + dy;
      if (x >= 0 && y >= 0 && x < N && y < N && arr(y * N + x)) return true;
    }
    return false;
  };
  let gridCells = 0, gridHit = 0, inkCells = 0, inkHit = 0;
  for (let cy = 1; cy < N - 1; cy++) for (let cx = 1; cx < N - 1; cx++) {
    const i = cy * N + cx;
    if (lit(i)) { gridCells++; if (near((j) => ink[j], cx, cy)) gridHit++; }
    if (ink[i]) { inkCells++; if (near(lit, cx, cy)) inkHit++; }
  }
  return { gridCells, inkCells, precision: gridHit / Math.max(1, gridCells),
           recall: inkHit / Math.max(1, inkCells) };
}"""


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(1500)
    corpus.old_opening(p)  # the opening it was written against (P8h)
    # Under a note held in Mono: the site waits for one since 10 Nov, and the
    # opening was the tone it drew with none.
    corpus.held_tone(p)
    # The hands the instrument hears, in place of genSet and state.persistence
    # written by hand (batch 6): each moves its control and fires its event.
    p.evaluate("""() => {
      const fire = (e, v, kind) => { e.value = String(v); e.dispatchEvent(new Event(kind, { bubbles: true })); };
      window.__level = (v) => fire(el.amp, Math.round(v * 100), 'input');
      window.__interval = (v) => fire(el.interval, v, 'change');
      window.__shape = (v) => fire(el.shape, v, 'change');
      window.__persist = (v) => fire(el.persistence, v, 'change');
      window.__display = (m) => ({ yt: el.dispYT, xy: el.dispXY, spect: el.dispSpect })[m].click();
    }""")
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    print("\n--- the grid is where the beam drew ---")
    p.evaluate("""() => { state.beam = 'off'; __persist(0); }""")
    yt = p.evaluate(AGREE, [False])
    print("    Y-T waveform: %d grid cells, %d inked; precision %.3f, recall %.3f"
          % (yt["gridCells"], yt["inkCells"], yt["precision"], yt["recall"]))
    check("in Y-T every lit cell is on the trace and every inked cell is lit",
          yt["gridCells"] > 60 and yt["precision"] > 0.97 and yt["recall"] > 0.97, str(yt))
    p.evaluate("""() => { __display('xy'); __persist(0); __interval(7); __shape('sine'); }""")
    xy = p.evaluate(AGREE, [True])
    print("    X-Y 2:3: %d grid cells, %d inked; precision %.3f, recall %.3f"
          % (xy["gridCells"], xy["inkCells"], xy["precision"], xy["recall"]))
    check("and in X-Y, on a figure that is not its own transpose",
          xy["gridCells"] > 60 and xy["precision"] > 0.97 and xy["recall"] > 0.97, str(xy))
    # The fixture's own check (batch 6): the 2:3 is the instrument's, set by
    # the Interval menu it hears - with genSet, as on ?brain=js, it would have
    # gone on drawing the unison's diagonal, which is its own transpose and
    # the wrong fixture. The null is that diagonal, the menu at nought.
    TRANSPOSED = """() => { const N = PHOSPHOR_N, g = phosphor.grid; let lit = 0, both = 0;
      for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) if (g[y * N + x] > 0.05) { lit++; if (g[(N - 1 - x) * N + (N - 1 - y)] > 0.05 || g[x * N + y] > 0.05) both++; }
      return both / Math.max(1, lit); }"""
    own = p.evaluate(TRANSPOSED)
    p.evaluate("() => __interval(0)"); p.wait_for_timeout(500)
    diag = p.evaluate(TRANSPOSED)
    p.evaluate("() => __interval(7)"); p.wait_for_timeout(500)
    check("the X-Y figure is the instrument's 2:3, not its own transpose", own < 0.7, "%.3f of its cells have their mirror lit" % own)
    check("null: the unison's diagonal is", diag > 0.95, "%.3f" % diag)

    print("\n--- it fades with the screen ---")
    fade = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      __interval(0);
      __persist(0.12);
      await wait(600);
      // The brightest cell of the figure, and the pixel at its middle.
      const N = PHOSPHOR_N, g = phosphor.grid;
      let at = 0;
      for (let i = 0; i < g.length; i++) if (g[i] > g[at]) at = i;
      const cx = at % N, cy = Math.floor(at / N);
      const dpr = window.devicePixelRatio || 1;
      const ctx = el.trace.getContext('2d');
      // The darkest pixel in that cell is where the stroke is.
      const x0 = Math.round((plot.x + cx / N * plot.w) * dpr), y0 = Math.round((plot.y + cy / N * plot.h) * dpr);
      const cw = Math.max(1, Math.round(plot.w / N * dpr));
      /* The cell with nothing drawn on it first, so the pixel chosen is one
         whose background is paper. Once F1 moved the screen down by a
         toolbar, the darkest pixel of the brightest cell landed on a
         graticule line in two runs of four: the line is drawn over the
         trace and never fades, so the canvas read 0.934 a frame there, and
         the pixel was not measuring the trace at all. */
      __level(0);
      await wait(1500);
      const bare = ctx.getImageData(x0, y0, cw, cw).data;
      __level(0.55);
      await wait(800);
      const cell = ctx.getImageData(x0, y0, cw, cw).data;
      let px = -1;
      for (let k = 0; k < cell.length; k += 4) {
        if (252 - bare[k + 1] > 8) continue;      // a line, or anything else that does not fade
        if (px < 0 || cell[k + 1] < cell[px + 1]) px = k;
      }
      const pxX = x0 + (px / 4) % cw, pxY = y0 + Math.floor(px / 4 / cw);
      const paperG = 252;
      const inkOf = () => paperG - ctx.getImageData(pxX, pxY, 1, 1).data[1];

      __level(0);                             // nothing new is drawn there
      /* Until the cell is fading: the lanes already on their way from the
         audio thread were drawn at the old amplitude and lay that cell again
         for 25 to 55 ms. This waited a fixed 60 ms, and with the page a
         little heavier (P7a) one or two of those frames fell inside the
         count, read as the grid fading at 0.888 or 0.895 rather than 0.88. */
      let last = g[at];
      for (let k = 0; k < 30; k++) {
        await new Promise((r) => requestAnimationFrame(r));
        if (g[at] < last * 0.95) break;
        last = g[at];
      }
      await new Promise((r) => requestAnimationFrame(r));
      const f0 = phosphor.frames, g0 = g[at], c0 = inkOf();
      await wait(250);
      const f1 = phosphor.frames, g1 = g[at], c1 = inkOf();
      __level(0.55);
      return { frames: f1 - f0, grid: [g0, g1], canvas: [c0, c1] };
    }""")
    import math
    frames = max(1, fade["frames"])
    grid_rate = (fade["grid"][1] / fade["grid"][0]) ** (1 / frames) if fade["grid"][0] > 0 else None
    canvas_rate = (fade["canvas"][1] / fade["canvas"][0]) ** (1 / frames) if fade["canvas"][0] > 0 and fade["canvas"][1] > 0 else None
    print("    over %d frames: grid %s, canvas ink %s; per frame grid %s, canvas %s (want 0.88)"
          % (frames, [round(v, 4) for v in fade["grid"]], fade["canvas"],
             None if grid_rate is None else round(grid_rate, 4),
             None if canvas_rate is None else round(canvas_rate, 4)))
    # "The grid fades by one minus the persistence every frame" is
    # core/tests/pieces/photo.py's since batch 6, on the core's Phosphor; the
    # rate is still measured here, the face's grid's, for the screen's.
    check("the face's grid fades at the rate the screen itself fades at",
          grid_rate is not None and canvas_rate is not None and abs(grid_rate - canvas_rate) < 0.02,
          "grid %s, canvas %s" % (grid_rate, canvas_rate))

    # Gone to core/tests/pieces/photo.py (batch 6): "infinite persistence
    # keeps everything, as the screen does", "and with persistence off nothing
    # is kept but what was just drawn" and "a cell keeps the brighter of two
    # strokes, never their sum" - the page's grid, and its phosphorSegment
    # called by hand; there on the core's Phosphor, a segment laid and faded.

    print("\n--- the photocell reads it ---")
    p.evaluate("""() => { __interval(0); __persist(0.12); el.photoButton.click(); }""")
    p.wait_for_timeout(700)
    # Gone to core/tests/pieces/photo.py (batch 6): "on the figure it reads
    # bright", "and off it, dark", "the reading moves smoothly as the reticle
    # does", "it never moves faster than two full swings a second" and "and
    # still gets there". They read the face's photocell (photo.value) on the
    # face's grid, which on the site is what its card shows and not what
    # the instrument's matrix reads (step 5's); there on the core's
    # PictureSources, and on the instrument's own figure.
    registered = p.evaluate("() => MOD_SOURCES.has('photo.1')")
    check("and it is a source while it is on", registered, "")

    print("\n--- where it may go, and how hard ---")
    rules = p.evaluate("""() => {
      state.modRoutings = state.modRoutings.filter((r) => r.sourceId !== 'photo.1');
      const tried = ['filter.cutoff', 'filter.res', 'gen.freq', 'gen.amp',
                     'view.rotate', 'view.lag', 'view.zoom', 'trig.position'];
      for (const d of tried) addRouting('photo.1', d);
      const got = state.modRoutings.filter((r) => r.sourceId === 'photo.1');
      return { accepted: got.map((r) => r.destId).sort(),
               starts: [...new Set(got.map((r) => r.amount))] };
    }""")
    print("    accepted %s, starting at %s" % (rules["accepted"], rules["starts"]))
    # Stage E1 refused the filter and the generator here, and this check said
    # so. Stage E3 opens them, with the loop total in place of the refusal -
    # looptest.py is where that is held to account.
    check("since E3, a source reading the picture may reach any destination",
          rules["accepted"] == sorted(["filter.cutoff", "filter.res", "gen.freq", "gen.amp",
                                       "view.rotate", "view.lag", "view.zoom", "trig.position"]),
          str(rules["accepted"]))
    check("and starts low", rules["starts"] == [0.2], str(rules["starts"]))

    reach = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      state.modRoutings = state.modRoutings.filter((r) => r.sourceId !== 'photo.1');
      addRouting('photo.1', 'view.rotate');
      const r = state.modRoutings.find((x) => x.sourceId === 'photo.1');
      // Written straight in, round every setter, so only the point of use
      // stands between it and the destination.
      r.amount = 1;
      photo.value = 1; const was = PHOTO_SLEW;
      // The value the matrix used is whatever photoStep left it at, so the
      // offset is compared with half of that, not with a half of one.
      let most = 0, ratio = 0;
      for (let i = 0; i < 20; i++) {
        photo.value = 1;
        applyModMatrix(capture(), 16);
        most = Math.max(most, Math.abs(state.rotateMod));
        ratio = Math.max(ratio, Math.abs(state.rotateMod) / photo.value);
      }
      touchRoutings();
      const stored = r.amount;
      // A setup code carrying a routing past the ceiling, to the resonance.
      state.modRoutings.push({ sourceId: 'photo.1', destId: 'filter.res', amount: 0.9 });
      state.resMod = 0; applyModMatrix(capture(), 16);
      const res = state.resMod;
      state.modRoutings = state.modRoutings.filter((x) => x.sourceId !== 'photo.1');
      applyModMatrix(capture(), 16);
      return { most, ratio, stored, res };
    }""")
    print("    amount written as 1: applied %.3f of rotation's span, stored back as %.2f; "
          "a resonance routing written at 0.9 moved it by %s" % (reach["most"], reach["stored"], reach["res"]))
    # "An amount past the ceiling is held to it where it is used" and "a
    # routing that arrives in a code past the ceiling moves its destination
    # no further than the ceiling" read the page's `applyModMatrix` with
    # `photo.value` forced; they are core/tests/pieces/photo.py's since stage
    # 5, step 3, batch 3 (13 Nov), on the core's matrix. The face's half
    # stays: what the control stores back.
    check("and stored back within it, so the control says what applies",
          reach["stored"] == 0.5, str(reach["stored"]))

    # Gone to core/tests/pieces/photo.py (batch 6): "everything stays inside
    # its range and nothing goes NaN" read the page's visual matrix
    # (state.rotateMod, state.zoomMod) and its photocell for four seconds of
    # real frames; there the instrument rendered four seconds with the
    # photocell on its own figure, routed at the ceiling.

    print("\n--- its controls are its own ---")
    ctrl = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      movePhoto(0.25, 0.25); await wait(100);
      const box = el.photoReticle.getBoundingClientRect();
      return { x: box.left + box.width / 2, y: box.top + box.height / 2,
               level: state.level, timebase: el.timebase.value,
               tx: el.trace.getBoundingClientRect() };
    }""")
    target = (ctrl["tx"]["x"] + 0.5 * ctrl["tx"]["width"], ctrl["tx"]["y"] + 0.6 * ctrl["tx"]["height"])
    p.mouse.move(ctrl["x"], ctrl["y"]); p.mouse.down()
    p.mouse.move(target[0], target[1], steps=8); p.mouse.up()
    p.wait_for_timeout(100)
    after_drag = p.evaluate("() => ({ u: photo.u, v: photo.v, level: state.level })")
    p.keyboard.press("ArrowRight"); p.wait_for_timeout(60)
    after_key = p.evaluate("() => ({ u: photo.u, timebase: el.timebase.value })")
    want_u = (target[0] - ctrl["tx"]["x"] - p.evaluate("() => plot.x")) / p.evaluate("() => plot.w")
    print("    dragged to u %.3f (wanted %.3f), level %s -> %s; arrow: u %.4f, timebase %s -> %s"
          % (after_drag["u"], want_u, ctrl["level"], after_drag["level"], after_key["u"],
             ctrl["timebase"], after_key["timebase"]))
    check("dragging the reticle puts it where it is dropped",
          abs(after_drag["u"] - want_u) < 0.02, "%.3f against %.3f" % (after_drag["u"], want_u))
    check("and does not also drag the trigger level under it",
          after_drag["level"] == ctrl["level"], "%s -> %s" % (ctrl["level"], after_drag["level"]))
    check("its arrow keys move it a cell and leave the timebase alone",
          abs(after_key["u"] - (after_drag["u"] + 1 / 64)) < 1e-9
          and after_key["timebase"] == ctrl["timebase"], str(after_key))

    spect = p.evaluate("""async () => {
      const frame = () => new Promise((r) => requestAnimationFrame(r));
      // On the figure first, so there is something to stop reading: a check
      // made with the reticle over nothing reads nought whatever happens.
      const N = PHOSPHOR_N, g = phosphor.grid;
      let x = -1;
      for (let i = 0; i < N; i++) if (g[32 * N + i] > 0.3) x = i;
      movePhoto((x + 0.5) / N, 32.5 / N);
      /* Until it reads the figure, to two seconds: the value is the
         instrument's (5b), which on a loaded machine had reached only 0.09
         at 700 ms, and a value that low would be slewed to nought within the
         wait below anyway. */
      for (let t = 0; t < 2000 && photo.value <= 0.3; t += 100) await new Promise((r) => setTimeout(r, 100));
      const before = photo.value;
      __display('spect'); await frame(); await frame();
      const hidden = el.photoReticle.hidden, grid = phosphor.grid.reduce((a, v) => a + v, 0);
      /* At once, not slewed down: the slew, two whole swings a second, takes
         a quarter of a second from 0.47. Since stage 5, step 5b the value is
         the instrument's, read as its readings come back from the worklet - a
         block and a picture frame after the click - so it is waited for, to
         100 ms, where a slewed value would still be over a quarter. */
      const t0 = performance.now();
      while (photo.value !== 0 && performance.now() - t0 < 100) await frame();
      const out = { before, hidden, value: photo.value, grid, ms: Math.round(performance.now() - t0) };
      await new Promise((r) => setTimeout(r, 300));
      __display('xy'); await new Promise((r) => setTimeout(r, 100));
      out.back = !el.photoReticle.hidden;
      return out;
    }""")
    check("over a spectrogram, which no beam draws, it is put away and reads nothing at once",
          spect["before"] > 0.3 and spect["hidden"] and spect["value"] == 0 and spect["back"],
          str(spect))
    check("and the phosphor holds nothing there", spect["grid"] == 0, str(spect["grid"]))

    print("\n--- Clear ---")
    cleared = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const frame = () => new Promise((r) => requestAnimationFrame(r));
      __display('xy'); __interval(0); __level(0.55);
      __persist(-1);
      await wait(500);
      // Where the ring is, on the grid and on the canvas.
      const N = PHOSPHOR_N, g = phosphor.grid;
      let x = -1;
      for (let i = 0; i < N; i++) if (g[32 * N + i] > 0.3) x = i;
      const dpr = window.devicePixelRatio || 1, ctx = el.trace.getContext('2d');
      const inkAt = () => {
        const x0 = Math.round((plot.x + x / N * plot.w) * dpr), y0 = Math.round((plot.y + 32 / N * plot.h) * dpr);
        const cw = Math.max(1, Math.round(plot.w / N * dpr));
        const d = ctx.getImageData(x0, y0, cw, cw).data;
        let least = 255;
        for (let k = 1; k < d.length; k += 4) least = Math.min(least, d[k]);
        return 252 - least;
      };
      __level(0);                               // from now on only a dot is drawn
      await wait(300);
      const kept = { grid: g[32 * N + x], ink: inkAt() };
      el.clearButton.click();
      await frame(); await frame();
      const after = { grid: g[32 * N + x], ink: inkAt(), setting: el.persistence.value,
                      persistence: state.persistence };
      __level(0.55);
      __persist(0.12);
      return { kept, after };
    }""")
    print("    ring under infinite persistence: grid %.2f, ink %d; after Clear: grid %.2f, ink %d, setting %s"
          % (cleared["kept"]["grid"], cleared["kept"]["ink"], cleared["after"]["grid"],
             cleared["after"]["ink"], cleared["after"]["setting"]))
    check("with infinite persistence the old figure stays, on the screen and the grid",
          cleared["kept"]["grid"] > 0.5 and cleared["kept"]["ink"] > 60, str(cleared["kept"]))
    # The ring's cell sits on the graticule's centre line, which is 35 below
    # paper in the green channel; the trace is 127. Between them is the test.
    check("Clear wipes both at once",
          cleared["after"]["grid"] == 0 and cleared["after"]["ink"] < 60, str(cleared["after"]))
    check("and leaves persistence as it was set",
          cleared["after"]["setting"] == "-1" and cleared["after"]["persistence"] == -1,
          str(cleared["after"]))

    print("\n--- off, on, and in a setup code ---")
    cycle = p.evaluate("""() => {
      addRouting('photo.1', 'view.rotate');
      el.photoButton.click();
      const off = { registered: MOD_SOURCES.has('photo.1'), value: photo.value,
                    kept: state.modRoutings.some((r) => r.sourceId === 'photo.1'),
                    shown: !el.photoReticle.hidden };
      el.photoButton.click();
      movePhoto(0.3, 0.7);
      const snap = snapshot();
      el.photoButton.click(); movePhoto(0.9, 0.1);
      /* Loaded as a pasted code is, which sends the instrument the setup
         (batch 6): restore() called alone changes the face and nothing it plays. */
      loadCode(encodeSetup(snap));
      const back = { on: photo.on, u: photo.u, v: photo.v, registered: MOD_SOURCES.has('photo.1') };
      loadCode(btoa(JSON.stringify({})).replace(/=+$/, ''));
      const old = { on: photo.on };
      return { off, back, old };
    }""")
    print("    %s" % cycle)
    check("off, it is not a source and reads nothing, and its routings wait for it",
          not cycle["off"]["registered"] and cycle["off"]["value"] == 0 and cycle["off"]["kept"]
          and not cycle["off"]["shown"], str(cycle["off"]))
    check("a setup code brings it back where it was",
          cycle["back"] == {"on": True, "u": 0.3, "v": 0.7, "registered": True}, str(cycle["back"]))
    check("and a code from before it existed has it off", cycle["old"]["on"] is False, str(cycle["old"]))

    print("\n--- switched on by hand, it lands on the figure ---")
    # The fault this is for: switched on, the reticle stayed where it was - three
    # quarters across by default - which on the default figure is dark, so it
    # read about 0.02 and moved nothing. The fixture has to show that dark spot
    # first, or a pass below would prove nothing about the landing.
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(900)
    corpus.old_opening(p)  # the opening it was written against (P8h)
    corpus.install(p)
    corpus.held_tone(p)    # and held, as above
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    land = p.evaluate("""async () => {
      const frames = (n) => new Promise((done) => { let k = 0;
        const f = () => (++k >= n ? done() : requestAnimationFrame(f)); requestAnimationFrame(f); });
      await frames(30);
      const before = { u: photo.u, v: photo.v, read: phosphorRead(photo.u, photo.v),
                       most: Math.max(...pictureEngine.cells) };
      el.photoButton.click();
      await frames(45);
      const after = { u: photo.u, v: photo.v, raw: photo.raw, value: photo.value, on: photo.on };
      // Already on the trace, but a third of a cell off a cell's centre: a
      // landing that ignored being lit would snap it back to a centre.
      movePhoto(photo.u + 0.33 / PHOSPHOR_N, photo.v);
      const nudged = { u: photo.u, v: photo.v, read: phosphorRead(photo.u, photo.v) };
      el.photoButton.click(); el.photoButton.click(); await frames(5);
      const again = { u: photo.u, v: photo.v };
      // A setup that turns it on keeps its own placement, even in the dark:
      // the corner, where a landing would certainly have moved it.
      const snap = snapshot(); snap.photoOn = true; snap.photoU = 0.05; snap.photoV = 0.05;
      restore(snap); await frames(10);
      const dark = { u: photo.u, v: photo.v, on: photo.on, read: phosphorRead(0.05, 0.05) };
      // The old library's, from before P8g, loaded as a preset was: the bank
      // has no setup that turns the photocell on. A waveform's since G2, when
      // the knot it used to be went with the solids.
      loadCorpus('The figure sets its own FM'); await frames(10);
      const preset = { u: photo.u, v: photo.v, on: photo.on };
      return { before, after, nudged, again, dark, preset };
    }""")
    b4, af = land["before"], land["after"]
    check("the fixture: at its default spot on the default figure the photocell is in the dark",
          b4["read"] < 0.1 * b4["most"] and b4["most"] > 0.5, str(b4))
    check("switched on, it moves onto the figure and reads it",
          af["on"] and (af["u"], af["v"]) != (b4["u"], b4["v"]) and af["raw"] > 0.3 and af["value"] > 0.3,
          "from %.3f,%.3f to %.3f,%.3f, reading %.3f" % (b4["u"], b4["v"], af["u"], af["v"], af["raw"]))
    nd = land["nudged"]
    check("on the figure already, off a cell's centre, switching it off and on leaves it exactly there",
          nd["read"] >= 0.25 and land["again"] == {"u": nd["u"], "v": nd["v"]}, "%s -> %s" % (nd, land["again"]))
    check("a setup that turns it on in the dark corner keeps it there",
          land["dark"]["on"] and (land["dark"]["u"], land["dark"]["v"]) == (0.05, 0.05) and land["dark"]["read"] < 0.05,
          str(land["dark"]))
    check("a preset that turns it on keeps its own placement, not a landing",
          land["preset"] == {"u": 0.625, "v": 0.275, "on": True}, str(land["preset"]))

    print("\n--- what it costs ---")
    cost = p.evaluate("""async () => {
      el.photoButton.click();
      setDisplay('xy'); el.timebase.value = String(TIMEBASE.length - 1);
      el.timebase.dispatchEvent(new Event('input'));
      const costs = [];
      for (let i = 0; i < 40; i++) {
        await new Promise((r) => requestAnimationFrame(r));
        costs.push(phosphor.cost);
      }
      costs.sort((a, b) => a - b);
      return { median: costs[20], worst: costs[39] };
    }""")
    print("    depositing a long-timebase X-Y figure: median %.3f ms, worst %.3f ms a frame"
          % (cost["median"], cost["worst"]))
    check("the grid costs well under a millisecond a frame", cost["median"] < 1.0, str(cost))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the photocell reads the beam, and the loop it closes stays inside its bounds")
