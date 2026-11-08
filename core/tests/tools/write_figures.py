"""Write each preset's figure into web/scope.html, for the browser's thumbnails (F6).

A thumbnail is the preset's figure as the instrument draws it, not a picture
of what the page thinks it sounds like: the page is opened, each bank preset
loaded as a player loads one, the note honestytest.py probes it with held
(an interval where the preset's line asks for one, a note in each hand of a
split), and after the sound has had time to strike and settle the pair it
drew is kept, through the page's own figureFromLanes - the function Save uses
for a saved sound, so the two are drawn alike. Each figure carries the hash
of the setup it was drawn from (presetHash), and presettest.py fails one whose
preset has changed since: a preset tuned by ear has to be drawn again.

Run it after changing the bank, beside write_presets.py:

    CHROME=/opt/pw-browsers/chromium python3 core/tests/tools/write_figures.py

It plays in real time, a couple of seconds a preset.
"""
import json, os, re, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.normpath(os.path.join(HERE, "..", "..", "..", "web", "scope.html"))
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")

# As honestytest.py's probes, but every hand at once: a split's thumbnail is both figures.
def probe(name, setup):
    if name == "Crossed hands": return [48, 67]
    if name == "Turning fifths": return [48, 55]
    if setup.get("layers") == "split": return [36, 67]
    return [60]

DRAW = r"""async ([value, notes]) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  setScreenKeys(true);
  applyPreset(value);
  await wait(900);
  for (const n of notes) midiBytes(new Uint8Array([0x90, n, 100]));
  await wait(1600);
  // Two periods of the lowest note held, so the figure closes on itself.
  const low = 440 * Math.pow(2, (Math.min(...notes) - 69) / 12);
  const n = Math.min(FIGURE_N, Math.ceil(2 * (state.source.sampleRate || 44100) / low));
  const figure = figureFromLanes(state.source.getLatestWindow(n));
  for (const n of notes) midiBytes(new Uint8Array([0x80, n, 0]));
  midiPanic();
  await wait(300);
  return { figure, hash: presetHash(findPreset(value)) };
}"""


def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
        p = b.new_page(viewport={"width": 1400, "height": 900})
        bad = []
        p.on("pageerror", lambda e: bad.append(str(e)))
        p.goto("file://" + PAGE); p.wait_for_timeout(1200)
        if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
        p.locator("#trace").click(position={"x": 5, "y": 5})
        p.wait_for_timeout(600)
        bank = p.evaluate("() => PRESETS.flatMap(([, entries]) => entries.map(([n, s]) => [n, s]))")
        figures = {}
        for name, setup in bank:
            got = p.evaluate(DRAW, ["b:" + name, probe(name, setup)])
            if not got["figure"] or not got["figure"].get("a"):
                sys.exit("%s drew nothing with %s held: a thumbnail of nothing would say it is silent" % (name, probe(name, setup)))
            figures["b:" + name] = dict(got["figure"], hash=got["hash"])
            print("  %-28s %s%s" % (name, "A" if got["figure"].get("a") else "-", "B" if got["figure"].get("b") else ""))
        b.close()
        if bad:
            sys.exit("the page threw: " + "; ".join(bad[:3]))
    with open(PAGE, encoding="utf-8") as f:
        page = f.read()
    line = "const PRESET_FIGURES = " + json.dumps(figures, separators=(",", ":")) + ";\n"
    new, n = re.subn(r"const PRESET_FIGURES = \{.*?\};\n", lambda m: line, page, count=1, flags=re.S)
    if n != 1:
        sys.exit("no `const PRESET_FIGURES = {...};` line in the page to write over")
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(new)
    print("wrote %d figures, %d characters, into %s" % (len(figures), len(line), PAGE))


if __name__ == "__main__":
    main()
