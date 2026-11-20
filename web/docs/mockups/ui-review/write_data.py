"""Write data.js for the three UI-review mockups from web/scope.html as it is.

What each control says (CONTROL_WORDS), and every control's own attributes and
readings in the three homes the mockups redraw - Scope & measure, Perform and
the Picture strip - read from the page in Chromium, so the mockups keep each
control's id, type, range and options, and say what the page says. Run it
again after the page changes:

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/ui-review/write_data.py
"""
import json, os, re
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
PAGE = os.path.join(ROOT, "web", "scope.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")

src = open(PAGE, encoding="utf-8").read()
m = re.search(r"const CONTROL_WORDS = \{\n  /\*.*?\*/\n(.*?)\n\};\n", src, re.S)
WORDS = json.loads("{" + m.group(1).rstrip().rstrip(",") + "}")

ATTRS = r"""() => {
  const STRIP = ["pictureMore", "pictureAmount", "oscScan", "scanStrike", "scanSoft", "scanMemory", "output", "stereoWidth", "widthHeard", "widthDrawn", "infoMore"];
  const pick = (root) => [...document.querySelectorAll(root + ' [id]')].filter(e => /^(INPUT|SELECT|BUTTON)$/.test(e.tagName)).map(e => ({ id: e.id, tag: e.tagName.toLowerCase(), type: e.type || '', min: e.min || null, max: e.max || null, step: e.step || null, value: e.tagName === 'BUTTON' ? null : (e.type === 'checkbox' ? e.checked : e.value), options: e.tagName === 'SELECT' ? [...e.options].map(o => [o.value, o.text]) : null, role: e.getAttribute('role'), text: e.tagName === 'BUTTON' ? e.textContent.trim() : null }));
  return { measure: pick('#measurePanel'), perform: pick('#performPanel'),
           picture: pick('#pictureBar').filter(e => STRIP.includes(e.id)) };
}"""
READ = r"""(ids) => { const out = {};
  for (const id of ids) { const e = document.getElementById(id), r = document.getElementById(id + 'Value'); if (!e || !r) continue;
    const lo = +e.min, hi = +e.max, st = +e.step || 1, n = Math.round((hi - lo) / st), keep = e.value, t = [];
    for (let i = 0; i <= n; i++) { e.value = lo + i * st; e.dispatchEvent(new Event('input', { bubbles: true })); t.push([+e.value, r.textContent.trim()]); }
    e.value = keep; e.dispatchEvent(new Event('input', { bubbles: true })); out[id] = t; }
  return out; }"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    p = b.new_page(viewport={"width": 1400, "height": 900})
    p.goto("file://" + PAGE); p.wait_for_timeout(900)
    attrs = p.evaluate(ATTRS)
    ranges = [a["id"] for k in attrs for a in attrs[k] if a["type"] == "range"]
    readings = p.evaluate(READ, ranges)
    b.close()

ids = {a["id"] for k in attrs for a in attrs[k]}
extra = ["transportAt", "clockFrom", "pictureReads", "levelMeter"]
words = {k: v for k, v in WORDS.items() if k in ids or k in extra}
out = os.path.join(HERE, "data.js")
with open(out, "w", encoding="utf-8") as f:
    f.write("/* Written by write_data.py from web/scope.html: what each control says, and each\n"
            "   control's attributes and readings on testing. Edit the page and run it, not this. */\n")
    f.write("window.UI_DATA = " + json.dumps({"words": words, "attrs": attrs, "readings": readings}, ensure_ascii=False) + ";\n")
print("wrote", out, {k: len(v) for k, v in attrs.items()}, len(words), "words,", len(readings), "readings")
