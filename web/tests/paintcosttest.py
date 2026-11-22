"""What painting costs on the site (step 2 of web/docs/painting-design.md):
the core as the site runs it, compiled to WebAssembly in the browser, and the
page's own frame painting the look.

- The core: the same compiled instrument the worklet plays (makeWasmBrain on
  the page's module), a chord of eight held in Poly and played for two
  seconds of blocks of 128, drawing the trace and painting, each instance in
  quarter-second slices taken in turn, the best slice each (22 Nov: whole
  runs one after another measured the shared machine's moment). Painting adds the brushes, the map's drying and fade and a ring
  read a voice a picture frame, so it must cost more than the trace (the
  null: the same setup twice on the trace costs the same to within the
  noise) and stay inside the budget: under half a millisecond more a block
  of 128, which at 48 kHz is under a fifth of the block's 2.7 ms.
- The page's frame: with Paint shown and a chord laying strokes, the time the
  face spends a frame painting the look, from paintView's own count. That is
  the CPU's side - the graphics card's work is asynchronous - so it is a
  floor, and on a machine with a graphics card the frame's GPU time is the
  study's measure (0.7 to 2.3 ms at 512 to 1000 square on the owner's).
  Here the renderer is SwiftShader, on the CPU.

Serial: it measures milliseconds.
"""
import os, sys, json
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
# The container's Chromium drops --use-gl=angle and --use-angle=swiftshader
# unless CHROMIUM_KEEP_GL_SWITCHES=1 (20 Nov, README): what this suite gets is
# Playwright's own --use-angle=swiftshader-webgl, WebGL 2 on SwiftShader with
# the page composited in software, which is what it needs - the look is
# WebGL's - and it checks the face says it paints on the graphics card. Not
# kept on purpose: with the whole compositor on SwiftShader the face drew at
# 2 fps, not 13, and the frame cost read 0.50 ms rather than 0.11.
GL = ["--autoplay-policy=no-user-gesture-required", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

# Each instance is run in short slices, the instances in turn (22 Nov). Until then each was run whole, two
# seconds three times, one after another, and the null compared the trace's best with the trace's best again
# a few seconds later: on this shared container the machine's own speed swings by a third from one second to
# the next (a fixed loop of plain JavaScript, timed ten times running, read 20 to 39 ms), so two runs seconds
# apart measured the moment as much as the instance, and the null went red alone and on testing alike (0.55
# against 0.43). Slice by slice the moments are shared: two fresh instances of the trace read within 4 per
# cent at their best slice, and the median of their slice-by-slice ratios within 2.5. Nothing differs
# instance to instance - the README's open item was the clock. The doubled trace is the null's own null:
# the same trace doing each block twice, which the null's band must see.
SLICES, SLICE = 24, 94       # 24 slices of 94 blocks, a quarter of a second each, about six seconds an instance
COST = """([slices, slice]) => {
  const setup = (paint) => encodeSetup(Object.assign({}, decodeSetup(encodeSetup(snapshot())),
    { midiMode: 'poly', oscScan: 60, pictureAmount: 50, screenDraws: paint ? 'paint' : 'trace' }));
  // An instance with the chord held and warmed, and a slice of it: ms a block of 128 over `slice` blocks.
  const make = (paint, twice) => {
    const brain = makeWasmBrain(wasmModule(), 48000, 128, setup(paint));
    const l = new Float32Array(128), r = new Float32Array(128), pics = [new Float32Array(128), new Float32Array(128)];
    [36, 43, 48, 52, 55, 60, 64, 67].forEach((n) => brain.midi([0x90, n, 100], -1));
    for (let k = 0; k < 100; k++) brain.block(128, l, r, pics, null);
    let k = 0;
    return () => {
      const t0 = performance.now();
      for (let i = 0; i < slice; i++, k++) {
        brain.block(128, l, r, pics, null);
        if (twice) brain.block(128, l, r, pics, null);
        if (k % 4 === 0) brain.readings();
      }
      return (performance.now() - t0) / slice;
    };
  };
  const runs = { trace: make(false), paint: make(true), again: make(false), doubled: make(false, true) };
  const got = { trace: [], paint: [], again: [], doubled: [] };
  for (let i = 0; i < slices; i++) for (const name of Object.keys(runs)) got[name].push(runs[name]());
  const best = (x) => Math.min(...x);
  return { trace: best(got.trace), paint: best(got.paint), again: best(got.again), doubled: best(got.doubled) };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=GL)
    p = b.new_page(viewport={"width": 1400, "height": 900})
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(2000)
    p.keyboard.press("Escape")
    c = p.evaluate(COST, [SLICES, SLICE])
    block_ms = 128 / 48000 * 1000
    print("  the core in WebAssembly, ms a block of 128, the best of %d slices each in turn: trace %.4f, painting %.4f (again on the trace %.4f, doubled %.4f)"
          % (SLICES, c["trace"], c["paint"], c["again"], c["doubled"]))
    print("  a sample: trace %.3f us, painting %.3f us" % (c["trace"] / 128 * 1000, c["paint"] / 128 * 1000))
    check("painting costs more than the trace", c["paint"] > c["trace"] * 1.01, "%.4f against %.4f ms" % (c["paint"], c["trace"]))
    check("null: the trace twice costs the same, within a fifth", abs(c["again"] - c["trace"]) < 0.2 * c["trace"],
          "%.4f and %.4f" % (c["trace"], c["again"]))
    check("and that band sees a trace doing each block twice", abs(c["doubled"] - c["trace"]) >= 0.2 * c["trace"],
          "%.4f against %.4f" % (c["doubled"], c["trace"]))
    check("and painting adds under half a millisecond a block of 128 (%.2f ms at 48 kHz)" % block_ms,
          c["paint"] - c["trace"] < 0.5, "%.4f ms more, %.0f%% of the block" % (c["paint"] - c["trace"], 100 * (c["paint"] - c["trace"]) / block_ms))

    # The page's own frame, painting the look.
    p.click("#drawPaint"); p.wait_for_timeout(300)
    p.evaluate("() => { el.oscScan.value = '60'; el.oscScan.dispatchEvent(new Event('input')); [45, 52, 57, 64, 69, 72].forEach((n) => midiNoteOn(n, 110)); }")
    p.wait_for_timeout(500)
    p.evaluate("() => { const t = paintView.timing; t.frames = 0; t.ms = 0; t.worst = 0; t.stamps = 0; }")
    p.wait_for_timeout(4000)
    t = p.evaluate("() => Object.assign({ mode: paintView.mode, fps: state.fps }, paintView.timing)")
    mean = t["ms"] / max(1, t["frames"])
    print("  the face, painting the look (%s): %.3f ms a frame on the CPU, worst %.3f, %d frames, %.0f stamps a frame, %.0f fps under SwiftShader"
          % (t["mode"], mean, t["worst"], t["frames"], t["stamps"] / max(1, t["frames"]), t["fps"]))
    check("the face paints the look in under 2 ms a frame of its own time, on the graphics card", t["mode"] == "gpu" and t["frames"] > 10 and mean < 2,
          "%.3f ms, %s" % (mean, t["mode"]))
    b.close()

print()
if fails: print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("painting's cost holds")
