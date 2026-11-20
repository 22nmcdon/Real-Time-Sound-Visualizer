"""The strike lab's page: index.html beside this file, made from lab.js and
the instrument's own look, the paint view lifted unchanged out of
web/scope.html (from `const PAINT_SIZE` to the end of `paintView`), so the
lab paints with exactly the shader the face does. Re-run after either
changes:

    python3 web/docs/labs/strike-lab/make.py

The page is self-contained (no scripts from anywhere), so it can be published
as it is.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))


def lifted():
    s = open(os.path.join(ROOT, "web", "scope.html"), encoding="utf-8").read()
    a = s.index("const PAINT_SIZE = 768")
    b = s.index("const paintView = (() => {")
    e = s.index("\n})();", b) + len("\n})();")
    assert s.count("const PAINT_SIZE = 768") == 1 and s.count("const paintView = (() => {") == 1
    return s[a:e]


TEMPLATE = """<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Strike lab</title>
<!-- The strike lab and the bend lab (20 Nov): knobs for one hard strike and one bend's smear, painted live by the
     instrument's own look (lifted from web/scope.html by make.py), from stamps of the kinds the core lays. -->
<style>
  :root { --cream: #faf6f0; --paper: #fffcf7; --charcoal: #241f1d; --text: #3a332f; --text-soft: #6b615a;
          --line: #e4d9cc; --gold: #b08d57;
          --ch1: #241f1d; --ch2: #5c6488; --ch3: #4c4921; --ch4: #6f9169; --ch5: #72245e; --ch6: #a6552d; }
  * { box-sizing: border-box; }
  body { background: var(--cream); color: var(--text); font: 14px/1.4 system-ui, sans-serif; margin: 0; padding: 16px; }
  h1 { color: var(--charcoal); font-size: 1.4rem; margin: 0 0 2px; }
  .soft { color: var(--text-soft); }
  .top { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: baseline; margin-bottom: 10px; }
  .tab { font: inherit; border: 1px solid var(--line); background: var(--paper); border-radius: 999px; padding: 4px 14px; cursor: pointer; }
  .tab[aria-pressed="true"] { background: var(--charcoal); color: var(--paper); border-color: var(--charcoal); }
  .wrap { display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 16px; align-items: start; }
  @media (max-width: 900px) { .wrap { grid-template-columns: 1fr; } }
  .pictures { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); gap: 12px; }
  .frame { position: relative; width: 100%; aspect-ratio: 1; background: var(--paper); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
  .sheet { position: absolute; left: 0; top: 0; width: 100%; height: 100%; }
  .sheet canvas.paint-view { position: absolute; background: var(--paper); }
  #map { width: 100%; aspect-ratio: 1; image-rendering: pixelated; background: var(--paper); border: 1px solid var(--line); border-radius: 8px; }
  .cap { font-size: 12px; color: var(--text-soft); margin: 4px 0 0; }
  #knobs { display: grid; gap: 6px; }
  .knob { display: grid; grid-template-columns: 130px minmax(0, 1fr) 54px; gap: 2px 8px; align-items: center; }
  .knob .name { color: var(--charcoal); font-weight: 600; font-size: 13px; }
  .knob .val { text-align: right; font-variant-numeric: tabular-nums; }
  .knob .help { grid-column: 1 / -1; font-size: 11.5px; color: var(--text-soft); margin-top: -2px; }
  .knob input { width: 100%; accent-color: var(--charcoal); }
  .buttons { display: flex; gap: 8px; margin: 10px 0; flex-wrap: wrap; }
  button { font: inherit; border: 1px solid var(--line); background: var(--paper); border-radius: 6px; padding: 5px 12px; cursor: pointer; }
  textarea { width: 100%; height: 110px; font: 12px/1.4 ui-monospace, monospace; border: 1px solid var(--line); border-radius: 6px; background: var(--paper); padding: 6px; }
</style>
</head>
<body>
  <div class="top">
    <h1>Strike lab</h1>
    <button class="tab" data-lab="strike" aria-pressed="true">Strike</button>
    <button class="tab" data-lab="bend" aria-pressed="false">Bend</button>
    <span class="soft" id="what"></span>
  </div>
  <div class="wrap">
    <div>
      <div class="pictures">
        <div><div class="frame"><div class="sheet" id="sheet"><div id="trace" hidden></div></div></div>
          <p class="cap">The look, as the face paints it: the instrument's own shader. <span id="count"></span></p></div>
        <div><canvas id="map" width="128" height="128"></canvas>
          <p class="cap">The map, at its own cells (128 across the canvas, the same view): the look's paint summed to the core's cells - what Scan reads.</p></div>
      </div>
      <p class="cap">Every mark here is made of the stamps the core already lays (brush stamps, drops and the bend's smear), written by
        this page from the knobs. When you have the look, copy the settings and send them back: the instrument is then made to lay
        the same stamps.</p>
    </div>
    <div>
      <div class="buttons"><button id="reseed">Reseed</button><button id="reset">Reset this lab</button><button id="zoom">Whole canvas</button></div>
      <div id="knobs"></div>
      <p class="cap" style="margin-top:12px">Settings - copy these and send them back.</p>
      <textarea id="copy" readonly></textarea>
      <div class="buttons"><button id="copyBtn">Copy settings</button></div>
    </div>
  </div>
<script>
"use strict";
// What the lifted paint view needs from the page it came from.
const el = { trace: document.getElementById("trace"), traceSheet: document.getElementById("sheet") };
const state = { paintPersistence: 16 };
const PAINT_DEFAULT = 16;
{{PAINT}}
{{LAB}}
</script>
</body>
</html>
"""


def main():
    page = TEMPLATE.replace("{{PAINT}}", lifted()).replace("{{LAB}}", open(os.path.join(HERE, "lab.js"), encoding="utf-8").read())
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f: f.write(page)
    print("wrote", os.path.join(HERE, "index.html"), len(page), "bytes")


if __name__ == "__main__":
    main()
