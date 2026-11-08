"""The inks: the X-Y figure's, and layer B's, chosen in the Picture's Advanced.

What would go wrong, and what is checked for it:

- an ink chosen and not drawn: the screen's own pixels are read, each sorted
  to the nearest of the seven inks, and the chosen ink has to be what the
  figure is drawn in and the default not - with the beam off, so every
  stroke is the ink itself. The null is the same count read for an ink not
  chosen, which has to come out near nothing;
- B's ink applied to A, or the other way round: with two layers each gets
  its own, and B's default is still its X lane's, as before;
- the loop overlay's rings left in the old inks, so a ring no longer reads
  over its own figure: each ring records the ink it was stroked in, which
  has to be its figure's;
- an ink that reaches the sound: Scan and the photocell read the phosphor
  grid, so one frame is drawn in two inks and the grids must be equal to the
  last cell, while the canvas is not. The null is the same frame a tenth
  smaller, which the comparison has to see;
- a code that loses the inks, or one with an ink the page has not got: codes
  round-trip both, a nonsense ink comes back as the default, and an old code
  without either draws in the inks it always did;
- the swatches as a picture of a choice rather than a control: they are
  pressed with the mouse and stepped with the arrow keys, and exactly one is
  marked chosen.
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

# Each pixel the figure darkened, sorted to the nearest ink, counted. Paper
# and the ruling are left out by distance: they are lighter than every ink.
COUNT = """() => {
  const names = ['blush-deep', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5'];
  const rgb = names.map((n) => hexToRgb(ink[n]));
  const paper = hexToRgb(ink.paper);
  const c = el.trace, g = c.getContext('2d');
  const data = g.getImageData(0, 0, c.width, c.height).data;
  const out = Object.fromEntries(names.map((n) => [n, 0]));
  for (let i = 0; i < data.length; i += 4) {
    const p = [data[i], data[i + 1], data[i + 2]];
    const d2 = (q) => (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2;
    if (d2(paper) < 60 * 60) continue;
    let best = 0;
    for (let k = 1; k < rgb.length; k++) if (d2(rgb[k]) < d2(rgb[best])) best = k;
    if (d2(rgb[best]) < 30 * 30) out[names[best]]++;
  }
  return out;
}"""

def counted(p, frames=4):
    # The most of each ink over a few frames: a moving figure lays more or
    # fewer pixels at full ink from one frame to the next (143 to 274 for the
    # same fifth), and one frame was a coin toss against a fixed bar.
    best = {}
    for _ in range(frames):
        for k, v in p.evaluate(COUNT).items(): best[k] = max(best.get(k, 0), v)
        p.wait_for_timeout(120)
    return best

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(800)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.locator("#trace").click(position={"x": 5, "y": 5}); p.wait_for_timeout(500)
    # The beam off, so a stroke is the ink itself, and no persistence, so the
    # screen is only the frame just drawn.
    p.evaluate("() => { el.dispXY.click(); el.beamLevel.value = 'off'; el.beamLevel.dispatchEvent(new Event('change')); state.persistence = 0; }")
    p.wait_for_timeout(400)

    print("\n--- A's ink, on the screen ---")
    rose = counted(p)
    check("by default the figure is drawn in the accent, as it always was", rose["blush-deep"] > 300 and rose["ch5"] < 20, str(rose))
    p.locator("#pictureMore").click(); p.wait_for_timeout(300)
    p.locator('.ink-swatch[data-ink="ch5"]').click(); p.wait_for_timeout(400)
    plum = counted(p)
    check("Plum pressed: the figure is drawn in plum, and no longer in the accent",
          plum["ch5"] > 300 and plum["blush-deep"] < 20, str(plum))
    check("null: the default frame has next to no plum in it, so the count can tell", rose["ch5"] < 20 and plum["ch5"] > 15 * max(1, rose["ch5"]))
    marks = p.evaluate("() => Array.from(document.querySelectorAll('.ink-swatch[aria-checked=\"true\"]')).map((e) => e.dataset.ink)")
    check("exactly one swatch is marked, the one pressed", marks == ["ch5"], str(marks))
    p.locator('.ink-swatch[data-ink="ch5"]').focus()
    p.keyboard.press("ArrowRight"); p.wait_for_timeout(100)
    wrapped = p.evaluate("() => [state.beamInk, document.activeElement.dataset.ink]")
    p.keyboard.press("ArrowLeft"); p.keyboard.press("ArrowLeft"); p.wait_for_timeout(100)
    back = p.evaluate("() => [state.beamInk, document.activeElement.dataset.ink]")
    check("the arrow keys step through the inks, wrap at the end, and take the focus with them",
          wrapped == ["accent", "accent"] and back == ["ch4", "ch4"], "%s %s" % (wrapped, back))

    print("\n--- the light is not the colour ---")
    grids = p.evaluate("""() => {
      // One frame, drawn synchronously, so the page's own loop cannot draw between.
      const n = 2048, l = new Float32Array(n), r = new Float32Array(n), small = new Float32Array(n);
      for (let i = 0; i < n; i++) { l[i] = 0.6 * Math.sin(i * 0.031); r[i] = 0.5 * Math.sin(i * 0.047 + 1); small[i] = 0.9 * r[i]; }
      const draw = (inkName, right) => {
        state.beamInk = inkName;
        pictureEngine.fade(0, true);
        drawXY({ channels: [l, right], turned: false }, fitCanvas(el.trace), 0);
        const c = el.trace;
        return { grid: Array.from(phosphor.grid), pixels: Array.from(c.getContext('2d').getImageData(0, 0, c.width, c.height).data.filter((_, i) => i % 97 === 0)) };
      };
      /* Through both of drawXY's branches: the beam shading, where the deposit
         follows strokeBeam, and the beam off, a plain stroke. The pixel counts
         above turned the beam off, and the first version of this drew only
         that branch, so an ink kept out of the shaded branch's deposit passed. */
      const same = (x, y) => x.length === y.length && x.every((v, i) => v === y[i]);
      const out = {};
      for (const level of ['moderate', 'off']) {
        state.beam = level; beamRefs.clear();
        const a = draw('accent', r); beamRefs.clear();
        const b = draw('ch2', r); beamRefs.clear();
        const c = draw('accent', small);
        out[level] = { lit: a.grid.filter((v) => v > 0).length, gridSame: same(a.grid, b.grid),
                       pixelsSame: same(a.pixels, b.pixels), nullSame: same(a.grid, c.grid) };
      }
      state.beamInk = 'ch4';
      const all = (k) => out.moderate[k] && out.off[k], none = (k) => !out.moderate[k] && !out.off[k];
      return { lit: Math.min(out.moderate.lit, out.off.lit), gridSame: all('gridSame'), pixelsSame: !none('pixelsSame'),
               nullSame: !none('nullSame'), out };
    }""")
    check("one frame in two inks lays the same light in every cell of the grid Scan and the photocell read",
          grids["gridSame"] and grids["lit"] > 50, str(grids))
    check("while the screen's pixels differ, shaded and plain, so the ink did change what is drawn", not grids["pixelsSame"], str(grids["out"]))
    check("null: the same frame a tenth smaller lays a different grid, so the comparison can see one", not grids["nullSame"])

    print("\n--- B's ink, with two layers ---")
    two = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setScreenKeys(true); setMidiMode('poly');
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change')); await wait(150);
      /* A fifth below the split and one note above it, so the two figures
         differ: a lone note in each hand is the same circle twice, B's over
         A's, and A's ink could not be seen under it. */
      for (const n of [43, 50, 72]) midiNoteOn(n, 100);
      await wait(900);
      const figures = sourceFigures();
      return { figures, laneInk: figures && figures[1] ? 'ch' + (figures[1][0] + 1) : null };
    }""")
    check("the split draws two figures, B's on a lane of its own", two["figures"] and len(two["figures"]) == 2 and two["laneInk"], str(two))
    p.evaluate("() => { el.beamInk.querySelector('[data-ink=\"ch1\"]').click(); }"); p.wait_for_timeout(400)
    lane = counted(p)
    check("B in its lane's ink by default, A in charcoal", lane.get(two["laneInk"], 0) > 150 and lane["ch1"] > 150, str(lane))
    p.select_option("#bInk", "ch5"); p.wait_for_timeout(400)
    plumB = counted(p)
    check("B's ink set to plum: B in plum, A still charcoal, and B's lane ink gone",
          plumB["ch5"] > 150 and plumB["ch1"] > 150 and plumB.get(two["laneInk"], 0) < 30, str(plumB))
    check("null: before, there was next to no plum", lane["ch5"] < 30)

    print("\n--- the loop overlay's rings ---")
    rings = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      // Scan depth is a layer's own, so each is set with its layer on the panel.
      setLoopOverlay(true); setControl('oscScan', 60);
      el.midiEditB.click(); setControl('oscScan', 60); el.midiEditA.click(); await wait(900);
      const r = (loopOverlay.drawn && loopOverlay.drawn.rings || []).map((x) => [x.layer, x.ink]);
      setLoopOverlay(false); setControl('oscScan', 0); el.midiEditB.click(); setControl('oscScan', 0); el.midiEditA.click();
      return r;
    }""")
    check("each ring is stroked in its own figure's ink: A charcoal, B plum",
          rings and all(i == ("ch1" if l == 0 else "ch5") for l, i in rings) and {l for l, _ in rings} == {0, 1}, str(rings))
    p.evaluate("""() => { for (const n of [43, 50, 72]) midiNoteOff(n); midiPanic();
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change')); }""")

    print("\n--- codes ---")
    codes = p.evaluate("""() => {
      const read = () => ({ a: state.beamInk, b: state.bInk, marked: el.beamInk.querySelector('[aria-checked="true"]').dataset.ink,
                            menu: el.bInk.value });
      restore(Object.assign(snapshot(), { beamInk: 'ch3', bInk: 'accent' }));
      const set = read(), code = snapshot();
      restore(Object.assign(snapshot(), { beamInk: 'magenta', bInk: 7 }));
      const odd = read();
      const old = snapshot(); delete old.beamInk; delete old.bInk;
      restore(Object.assign(snapshot(), { beamInk: 'ch2', bInk: 'ch2' })); restore(old);
      const was = read();
      return { set, code: [code.beamInk, code.bInk], odd, was };
    }""")
    check("a code's inks come back, on the swatches and the menu, and go out again",
          codes["set"] == {"a": "ch3", "b": "accent", "marked": "ch3", "menu": "accent"} and codes["code"] == ["ch3", "accent"], str(codes))
    check("an ink the page has not got comes back as the default", codes["odd"] == {"a": "accent", "b": "lane", "marked": "accent", "menu": "lane"}, str(codes["odd"]))
    check("and a code from before the inks draws in the ones it always did", codes["was"]["a"] == "accent" and codes["was"]["b"] == "lane", str(codes["was"]))
    b.close()

if bad:
    print("  FAIL  the page threw: " + "; ".join(bad[:3])); fails.append("pageerror")
print("\n%d failed" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
