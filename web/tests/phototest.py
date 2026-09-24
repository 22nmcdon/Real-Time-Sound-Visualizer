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
import os, sys
from playwright.sync_api import sync_playwright

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
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    print("\n--- the grid is where the beam drew ---")
    p.evaluate("""() => { state.beam = 'off'; state.persistence = 0; el.persistence.value = '0'; }""")
    yt = p.evaluate(AGREE, [False])
    print("    Y-T waveform: %d grid cells, %d inked; precision %.3f, recall %.3f"
          % (yt["gridCells"], yt["inkCells"], yt["precision"], yt["recall"]))
    check("in Y-T every lit cell is on the trace and every inked cell is lit",
          yt["gridCells"] > 60 and yt["precision"] > 0.97 and yt["recall"] > 0.97, str(yt))
    p.evaluate("""() => { setDisplay('xy'); state.persistence = 0; el.persistence.value = '0';
                          genSet('interval', 7); genSet('shape', 'sine'); }""")
    xy = p.evaluate(AGREE, [True])
    print("    X-Y 2:3: %d grid cells, %d inked; precision %.3f, recall %.3f"
          % (xy["gridCells"], xy["inkCells"], xy["precision"], xy["recall"]))
    check("and in X-Y, on a figure that is not its own transpose",
          xy["gridCells"] > 60 and xy["precision"] > 0.97 and xy["recall"] > 0.97, str(xy))

    print("\n--- it fades with the screen ---")
    fade = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      genSet('interval', 0);
      state.persistence = 0.12; el.persistence.value = '0.12';
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
      const cell = ctx.getImageData(x0, y0, cw, cw).data;
      let px = 0;
      for (let k = 0; k < cell.length; k += 4) if (cell[k + 1] < cell[px + 1]) px = k;
      const pxX = x0 + (px / 4) % cw, pxY = y0 + Math.floor(px / 4 / cw);
      const paperG = 252;
      const inkOf = () => paperG - ctx.getImageData(pxX, pxY, 1, 1).data[1];

      genSet('amp', 0);                       // nothing new is drawn there
      await wait(60);
      const f0 = phosphor.frames, g0 = g[at], c0 = inkOf();
      await wait(250);
      const f1 = phosphor.frames, g1 = g[at], c1 = inkOf();
      genSet('amp', 0.55);
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
    check("the grid fades by one minus the persistence every frame",
          grid_rate is not None and abs(grid_rate - 0.88) < 0.005, str(grid_rate))
    check("which is the rate the screen itself fades at",
          grid_rate is not None and canvas_rate is not None and abs(grid_rate - canvas_rate) < 0.02,
          "grid %s, canvas %s" % (grid_rate, canvas_rate))

    ends = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const sum = () => phosphor.grid.reduce((a, v) => a + v, 0);
      state.persistence = -1; el.persistence.value = '-1';
      await wait(300); genSet('amp', 0); await wait(60);
      const a = sum(); await wait(300); const kept = sum() / a;
      state.persistence = 0; el.persistence.value = '0';
      await wait(150);
      let outside = 0;
      const N = PHOSPHOR_N;
      for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
        if (Math.abs(x - N / 2) > 2 || Math.abs(y - N / 2) > 2) outside += phosphor.grid[y * N + x];
      }
      genSet('amp', 0.55);
      return { kept, outside };
    }""")
    check("infinite persistence keeps everything, as the screen does",
          ends["kept"] > 0.999, "%.4f of it left" % ends["kept"])
    check("and with persistence off nothing is kept but what was just drawn",
          ends["outside"] == 0, "%.4f away from the dot" % ends["outside"])

    # The compositing rule, directly: the same dim stroke laid on one cell twice
    # leaves it dim. With the beam off every stroke is full ink, so a sum and a
    # maximum agree everywhere and nothing drawn could tell them apart.
    rule = p.evaluate("""() => {
      const was = phosphor.grid.slice();
      phosphor.grid.fill(0);
      const x = plot.x + plot.w * 0.5, y = plot.y + plot.h * 0.5;
      phosphorSegment(x, y, x + 1, y, 0.375);
      phosphorSegment(x, y, x + 1, y, 0.375);
      phosphorSegment(x, y, x + 1, y, 0.25);
      const N = PHOSPHOR_N, cell = phosphor.grid[Math.floor(N / 2) * N + Math.floor(N / 2)];
      phosphor.grid.set(was);
      return cell;
    }""")
    check("a cell keeps the brighter of two strokes, never their sum",
          rule == 0.375, str(rule))

    print("\n--- the photocell reads it ---")
    p.evaluate("""() => { genSet('interval', 0); state.persistence = 0.12; el.persistence.value = '0.12';
                          el.photoButton.click(); }""")
    p.wait_for_timeout(700)
    reading = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const N = PHOSPHOR_N, g = phosphor.grid;
      let x = -1;
      for (let i = 0; i < N; i++) if (g[32 * N + i] > 0.3) x = i;
      movePhoto((x + 0.5) / N, 32.5 / N); await wait(900);
      const ring = photo.value;
      movePhoto(0.5, 0.5); await wait(900);
      const centre = photo.value;
      // Continuity: walked across the ring in tenth-of-a-cell steps.
      let worst = 0, last = null;
      for (let k = -30; k <= 30; k++) {
        const r = phosphorRead((x + 0.5 + k / 10) / N, 32.5 / N);
        if (last !== null) worst = Math.max(worst, Math.abs(r - last));
        last = r;
      }
      return { ring, centre, worst, registered: MOD_SOURCES.has('photo.1') };
    }""")
    print("    on the ring %.3f, at the centre %.3f; the most a tenth-of-a-cell step moved it %.3f"
          % (reading["ring"], reading["centre"], reading["worst"]))
    check("on the figure it reads bright", reading["ring"] > 0.5, "%.3f" % reading["ring"])
    check("and off it, dark", reading["centre"] < 0.02, "%.3f" % reading["centre"])
    check("the reading moves smoothly as the reticle does - no jump at a cell edge",
          reading["worst"] < 0.1, "%.3f" % reading["worst"])
    check("and it is a source while it is on", reading["registered"], "")

    slew = p.evaluate("""async () => {
      const N = PHOSPHOR_N, g = phosphor.grid;
      let x = -1;
      for (let i = 0; i < N; i++) if (g[32 * N + i] > 0.3) x = i;
      movePhoto(0.5, 0.5);
      await new Promise((r) => setTimeout(r, 900));
      const start = performance.now(), trace = [];
      movePhoto((x + 0.5) / N, 32.5 / N);
      while (performance.now() - start < 500) {
        await new Promise((r) => requestAnimationFrame(r));
        trace.push([performance.now() - start, photo.value, photo.raw]);
      }
      // Held against the envelope rather than frame to frame: the page steps
      // on the frame's own clock and this reads on another, and a rate taken
      // between two nearby reads of two clocks is mostly jitter. By time t it
      // cannot have risen more than twice t, plus one frame's worth.
      let over = 0;
      for (const [t, v] of trace) over = Math.max(over, v - (2 * t / 1000 + 2 * 0.034));
      const half = trace.find(([, v]) => v >= 0.35);
      // The ring's brightness flickers from frame to frame as the strokes land
      // a little differently, so the settled comparison is between averages.
      const last = trace.slice(-8);
      const mean = (k) => last.reduce((a, row) => a + row[k], 0) / last.length;
      return { over, half: half ? half[0] : null, end: mean(1), raw: mean(2) };
    }""")
    print("    stepped from dark to bright: halfway after %s ms, reached %.3f of %.3f"
          % (slew["half"], slew["end"], slew["raw"]))
    check("it never moves faster than two full swings a second",
          slew["over"] <= 0 and slew["half"] is not None and slew["half"] >= 150,
          "over the envelope by %.3f, halfway at %s ms" % (slew["over"], slew["half"]))
    check("and still gets there", abs(slew["end"] - slew["raw"]) < 0.05, str(slew))

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
    check("a source reading the picture reaches nothing that can add energy",
          rules["accepted"] == sorted(["view.rotate", "view.lag", "view.zoom", "trig.position"]),
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
      // A setup code carrying a routing it may not have.
      state.modRoutings.push({ sourceId: 'photo.1', destId: 'filter.res', amount: 0.9 });
      state.resMod = 0; applyModMatrix(capture(), 16);
      const res = state.resMod;
      state.modRoutings = state.modRoutings.filter((x) => x.sourceId !== 'photo.1');
      applyModMatrix(capture(), 16);
      return { most, ratio, stored, res };
    }""")
    print("    amount written as 1: applied %.3f of rotation's span, stored back as %.2f; "
          "a smuggled resonance routing moved it by %s" % (reach["most"], reach["stored"], reach["res"]))
    check("an amount past the ceiling is held to it where it is used",
          abs(reach["ratio"] - 0.5) < 1e-9 and reach["most"] > 0.45,
          "applied %.4f of the value, %.4f of the span" % (reach["ratio"], reach["most"]))
    check("and stored back within it, so the control says what applies",
          reach["stored"] == 0.5, str(reach["stored"]))
    check("a routing to a refused destination does nothing even if it arrives in a code",
          reach["res"] == 0, str(reach["res"]))

    print("\n--- a loop that cannot run away ---")
    loop = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      state.persistence = -1; el.persistence.value = '-1';
      addRouting('photo.1', 'view.rotate');
      addRouting('photo.1', 'view.zoom');
      for (const r of state.modRoutings) if (r.sourceId === 'photo.1') r.amount = 0.5;
      touchRoutings();
      let worst = { rotate: 0, zoom: 0, value: 0, grid: 0, nan: false };
      const until = performance.now() + 4000;
      while (performance.now() < until) {
        await wait(50);
        worst.rotate = Math.max(worst.rotate, Math.abs(state.rotateMod));
        worst.zoom = Math.max(worst.zoom, Math.abs(state.zoomMod));
        worst.value = Math.max(worst.value, photo.value);
        let g = 0;
        for (const v of phosphor.grid) { if (!Number.isFinite(v)) worst.nan = true; g = Math.max(g, v); }
        worst.grid = Math.max(worst.grid, g);
        if (!Number.isFinite(state.rotateMod) || !Number.isFinite(photo.value)) worst.nan = true;
      }
      state.modRoutings = state.modRoutings.filter((x) => x.sourceId !== 'photo.1');
      state.persistence = 0.12; el.persistence.value = '0.12';
      return worst;
    }""")
    print("    four seconds at the ceiling on rotation and zoom, infinite persistence: %s" % loop)
    check("everything stays inside its range and nothing goes NaN",
          not loop["nan"] and loop["rotate"] <= 0.5 + 1e-9 and loop["zoom"] <= 0.5 * 8 + 1e-9
          and loop["value"] <= 1 and loop["grid"] <= 1, str(loop))

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
      await new Promise((r) => setTimeout(r, 700));
      const before = photo.value;
      setDisplay('spect'); await frame(); await frame();
      // At once, not slewed down: the slew would take a third of a second.
      const out = { before, hidden: el.photoReticle.hidden, value: photo.value,
                    grid: phosphor.grid.reduce((a, v) => a + v, 0) };
      await new Promise((r) => setTimeout(r, 300));
      setDisplay('xy'); await new Promise((r) => setTimeout(r, 100));
      out.back = !el.photoReticle.hidden;
      return out;
    }""")
    check("over a spectrogram, which no beam draws, it is put away and reads nothing at once",
          spect["before"] > 0.3 and spect["hidden"] and spect["value"] == 0 and spect["back"],
          str(spect))
    check("and the phosphor holds nothing there", spect["grid"] == 0, str(spect["grid"]))

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
      restore(snap);
      const back = { on: photo.on, u: photo.u, v: photo.v, registered: MOD_SOURCES.has('photo.1') };
      restore({});
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
