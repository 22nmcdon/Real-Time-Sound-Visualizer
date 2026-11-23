"""The line under the screen never moves the screen (22 Nov, the owner's: "In
fullscreen mode and not Picture only, the information beneath it - held
notes, gated, etc. - sometimes causes the view to shift, because it gets too
long and pushes everything up when it collides with the 'looking for'
section"). The readout was a wrapping row, and a long detail took a second
line out of the screen's height. It is a grid of one-line boxes now, each cut
with an ellipsis and whole in its title.

What would go wrong, and what is checked for it, each with its null:

- a long line moving the screen: at the six windows fittest.py uses and the
  plugin's 960x600, in Enlarge with Picture only off and on the face, the
  screen's box is the same to the pixel with the line short as with the
  longest it can be - a held chord of eight in each of two hands, split, the
  loop heard, the scope armed, and then a verdict and a detail written three
  hundred characters long. The null: the same longest line under the old
  rule (a wrapping row, the words free to wrap), which moves the screen in
  Enlarge at some window;
- the line itself growing: the readout's height is one line in Enlarge and
  two on the face's column, the same short and long;
- the cut losing the words: the detail's and the verdict's titles are their
  whole text.

Parallel: every reading is a box, and nothing is timed.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
WINDOWS = [(1660, 1050), (1400, 900), (1100, 860), (1200, 680), (1100, 680), (960, 600)]

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    check("null: " + name, red, detail)

# Short, then the longest the page makes, then longer than it makes: the sheet's box and the readout's at each.
READ = """async ([enlarged, oldRule]) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const box = (n) => { const r = n.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; };
  let style = null;
  if (oldRule) {
    style = document.createElement('style');
    style.textContent = '.readout { display: flex !important; flex-wrap: wrap !important; } .readout > .verdict, .readout > .detail { white-space: normal !important; overflow: visible !important; }';
    document.head.appendChild(style);
  }
  setEnlarged(enlarged);
  if (enlarged && enlarge.pictureOnly) el.pictureOnly.click();
  await wait(300);
  const read = () => ({ sheet: box(el.traceSheet), line: box(el.verdict.closest('.readout')) });
  // Short: nothing held, the verdict the opening one.
  el.verdict.textContent = 'Trigger locked.'; el.readoutDetail.textContent = '60 fps'; await wait(30);
  const short = read();
  // The longest the page makes: two hands split, eight notes each, the scope armed.
  el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
  setMidiMode('poly');
  for (const n of [36, 38, 40, 41, 43, 45, 47, 48, 62, 64, 65, 67, 69, 71, 72, 74]) midiNoteOn(n, 100);
  setMode('single'); await wait(700);
  const real = { text: el.readoutDetail.textContent, verdict: el.verdict.textContent, ...read(),
                 titled: el.readoutDetail.title === el.readoutDetail.textContent && el.verdict.title === el.verdict.textContent };
  // Longer than it makes, written straight in after the page's last write.
  const long = 'outline A 2 of 8 notes · 8 of 8 held sound · '.repeat(7);
  el.verdict.textContent = 'Armed — waiting for an edge, and then some more words than any verdict has.'; el.readoutDetail.textContent = long;
  const longest = read();
  // Written straight in, past the page's writers, the titles are not the words: the null for `titled`.
  const titles = { titled: real.titled, straight: el.readoutDetail.title === el.readoutDetail.textContent };
  if (style) style.remove();
  for (const n of [36, 38, 40, 41, 43, 45, 47, 48, 62, 64, 65, 67, 69, 71, 72, 74]) midiNoteOff(n);
  setMode('auto'); setEnlarged(false); await wait(200);
  return { short, real, longest, titles };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    bad = []
    moved_old = []
    for w, h in WINDOWS:
        for enlarged in (True, False):
            where = ("in Enlarge" if enlarged else "on the face") + " at %dx%d" % (w, h)
            p = b.new_page(viewport={"width": w, "height": h})
            p.on("pageerror", lambda e: bad.append(str(e)))
            p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500); p.keyboard.press("Escape"); p.wait_for_timeout(200)
            r = p.evaluate(READ, [enlarged, False])
            check("%s: the screen does not move for the longest line the page makes, or a longer one" % where,
                  r["short"]["sheet"] == r["real"]["sheet"] == r["longest"]["sheet"],
                  "%s, %s, %s; the page's line %d characters" % (r["short"]["sheet"], r["real"]["sheet"], r["longest"]["sheet"], len(r["real"]["text"])))
            check("%s: and the line keeps its height" % where,
                  r["short"]["line"][3] == r["real"]["line"][3] == r["longest"]["line"][3],
                  "%s, %s, %s" % (r["short"]["line"], r["real"]["line"], r["longest"]["line"]))
            if (w, h) == (1400, 900):
                check("%s: the page's own detail and verdict are whole in their titles" % where, r["titles"]["titled"], str(r["titles"]))
                null("%s: words written past the page's writers are not in the title" % where, not r["titles"]["straight"], str(r["titles"]))
            if enlarged:
                p.close()
                p = b.new_page(viewport={"width": w, "height": h})
                p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500); p.keyboard.press("Escape"); p.wait_for_timeout(200)
                o = p.evaluate(READ, [True, True])
                moved_old.append(o["short"]["sheet"] != o["longest"]["sheet"])
            p.close()
    null("under the old wrapping row the longest line moves the enlarged screen at some window", any(moved_old), str(moved_old))
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
print("%d failed" % len(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
