"""What each base width costs: the core natively (core/tests/tools/paint_cpp.cpp's
`cost`, a chord of sixteen held) and as WebAssembly in Chromium (the page's own
module, a chord of eight held, as web/tests/paintcosttest.py measures it), and
the map's resolution: what a stroke's width reads as in the 128-cell map against
the brush's own (paint_cpp's `width`). Adds a "cost" entry to results.json.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/listening/paint-width/cost.py
"""
import json, os, subprocess

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
BUILD = os.path.join(ROOT, "core", "build", "listening", "paint-width")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
GL = ["--autoplay-policy=no-user-gesture-required", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
WIDTHS = {"today": 1.0, "medium": 2.0, "wide": 3.5}

COST = """(width) => {
  const setup = (paint) => encodeSetup(Object.assign({}, decodeSetup(encodeSetup(snapshot())),
    { midiMode: 'poly', oscScan: 60, pictureAmount: 50, screenDraws: paint ? 'paint' : 'trace' }));
  const run = (paint) => {
    const brain = makeWasmBrain(wasmModule(), 48000, 128, setup(paint));
    brain.paintWidth(width);
    const l = new Float32Array(128), r = new Float32Array(128), pics = [new Float32Array(128), new Float32Array(128)];
    [36, 43, 48, 52, 55, 60, 64, 67].forEach((n) => brain.midi([0x90, n, 100], -1));
    for (let k = 0; k < 100; k++) brain.block(128, l, r, pics, null);
    const t0 = performance.now();
    const blocks = Math.round(2 * 48000 / 128);
    for (let k = 0; k < blocks; k++) { brain.block(128, l, r, pics, null); if (k % 4 === 0) brain.readings(); }
    return (performance.now() - t0) / blocks;
  };
  const best = (paint) => Math.min(run(paint), run(paint), run(paint));
  return { trace: best(false), paint: best(true) };
}"""


def main():
    os.makedirs(BUILD, exist_ok=True)
    tool = os.path.join(BUILD, "paint_cpp")
    subprocess.run(["g++", "-std=c++17", "-O2", "-I", os.path.join(ROOT, "core", "include"),
                    os.path.join(ROOT, "core", "tests", "tools", "paint_cpp.cpp"), "-o", tool], check=True)
    out = {}
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=CHROME, args=GL)
        p = b.new_page(viewport={"width": 1400, "height": 900})
        p.goto("file://" + os.path.join(ROOT, "web", "scope.html")); p.wait_for_timeout(2000)
        p.keyboard.press("Escape")
        for name, w in WIDTHS.items():
            trace, paint = map(float, subprocess.run([tool, "cost", "2", str(w)], capture_output=True, text=True, check=True).stdout.split())
            spread, hw, _ = map(float, subprocess.run([tool, "width", str(w)], capture_output=True, text=True, check=True).stdout.split())
            c = p.evaluate(COST, w)
            out[name] = dict(native_trace=round(trace, 4), native_paint=round(paint, 4),
                             wasm_trace_ms=round(c["trace"], 4), wasm_paint_ms=round(c["paint"], 4),
                             map_spread=round(spread, 3), brush_half=round(hw, 3),
                             brush_spread=round(((0.488 * hw) ** 2 + 1 / 12) ** 0.5, 3))
            print(name, json.dumps(out[name]), flush=True)
        b.close()
    path = os.path.join(HERE, "results.json")
    results = json.load(open(path)) if os.path.exists(path) else {}
    results["cost"] = out
    with open(path, "w") as f: json.dump(results, f, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
