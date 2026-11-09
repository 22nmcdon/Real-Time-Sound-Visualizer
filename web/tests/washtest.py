"""The screen fades to the paper, and keeps no ghost of what it said before.

The screen forgets by laying the paper over itself each frame at the
persistence's strength. On an 8-bit canvas that stops short: once a pixel is
close enough to the paper, the frame's step is under half a level and rounds
to nothing, so the pixel never arrives. At Crossed hands' persistence
(0.0255) every pixel the beam had touched stopped at grey 220 for good - the
"wash" the owner saw over the whole screen - and the axis labels, written
into the same canvas, stained the same way, one preset's name staying under
the next one's. The sound never saw it (Scan reads the phosphor grid, which
fades in floating point); the screen showed a picture Scan was not reading.

So these read the canvas's own pixels, never the code's intentions:

- a figure drawn at 0.0255 and at Short (0.12), then the beam sent to the
  middle: everywhere it had been comes back to within two levels of the
  paper. The null: the same pixels before the fade are far from it, so the
  comparison can tell a stain from paper;
- the axis label changed from Left to Mid: the label's strip is what a
  cleared screen draws for Mid alone. The null: Left's strip, from a cleared
  screen, is not Mid's, so the comparison can tell one label from another.

Serial: it waits on real seconds of fading.
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

def null(name, red, detail=""):
    """A check's null: the same comparison fed a value it must reject."""
    check("null: " + name, red, detail)

# A fifth drawn as X-Y at a given persistence, so the figure covers the screen.
DRAW = """async (persistence) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  hostQuietly(() => restore({ shape: 'sine', freq: 220, interval: 7, just: false, display: 'xy',
                               persistence, pictureAmount: 0, oscScan: 0 }));
  hostSendSetup();
  const amp = document.getElementById('amp');
  amp.value = '55'; amp.dispatchEvent(new Event('input', { bubbles: true }));
  wipeScreen = true;
  await wait(3000);
}"""

# The plot's pixels as they are now: where the beam has inked (well below the
# paper in some channel), away from the middle, where a silenced beam sits.
INKED = """() => {
  const c = el.trace, ctx = c.getContext('2d'), k = c.width / c.clientWidth;
  const x0 = Math.round(plot.x * k) + 3, y0 = Math.round(plot.y * k) + 3;
  const w = Math.round(plot.w * k) - 6, h = Math.round(plot.h * k) - 6;
  const d = ctx.getImageData(x0, y0, w, h).data, out = [];
  const cx = w / 2, cy = h / 2, keep = Math.min(w, h) * 0.08;
  for (let y = 0; y < h; y += 2) for (let x = 0; x < w; x += 2) {
    if (Math.hypot(x - cx, y - cy) < keep) continue;
    const i = (y * w + x) * 4;
    if (d[i] < 225 || d[i + 1] < 222 || d[i + 2] < 217) out.push([x0 + x, y0 + y]);
  }
  return out;
}"""

# The whole screen kept under a name, to compare later.
SNAP = """(name) => { const c = el.trace; (window.__wash = window.__wash || {})[name] = c.getContext('2d').getImageData(0, 0, c.width, c.height); }"""

# How far one kept screen is from another at the given pixels, at the worst
# of them. Against a screen just cleared with the beam at rest, rather than
# against the bare paper, so the ruling - redrawn every frame - and the
# resting beam's dot are what is expected there, and only a stain is not.
WORST = """([at, a, b]) => {
  const A = window.__wash[a], B = window.__wash[b], W = A.width;
  let worst = 0, where = null;
  for (const [x, y] of at) {
    const i = (y * W + x) * 4;
    const off = Math.max(Math.abs(A.data[i] - B.data[i]), Math.abs(A.data[i + 1] - B.data[i + 1]), Math.abs(A.data[i + 2] - B.data[i + 2]));
    if (off > worst) { worst = off; where = [x, y, A.data[i], A.data[i + 1], A.data[i + 2], 'cleared', B.data[i], B.data[i + 1], B.data[i + 2]]; }
  }
  return { worst, where, n: at.length };
}"""

# The strip under the plot where the X axis's name is written, as numbers.
STRIP = """() => {
  const c = el.trace, ctx = c.getContext('2d'), k = c.width / c.clientWidth;
  const y0 = Math.round((plot.y + plot.h) * k) + 2, h = Math.max(1, Math.round(16 * k));
  const x0 = Math.round(plot.x * k), w = Math.round(plot.w * k);
  return Array.from(ctx.getImageData(x0, y0, w, h).data);
}"""

def differ(a, b):
    return max(abs(x - y) for x, y in zip(a, b)) if a and b and len(a) == len(b) else 999

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    p = ctx.new_page()
    bad = []
    p.on("pageerror", lambda e: bad.append(str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(2500)
    p.evaluate("() => { const d = document.getElementById('helpDialog'); if (d && d.open) d.close(); }")

    # Long enough for the fade to stall and the nudge to finish: at 0.0255 the
    # last twenty levels go at 0.06 of a level a frame, five or six seconds.
    for label, persistence, fade_ms in [("Crossed hands' 0.0255", "0.0255", 15000), ("Short, 0.12", "0.12", 4000)]:
        print("\n--- the fade at %s ---" % label)
        p.evaluate(DRAW, persistence)
        at = p.evaluate(INKED)
        check("the figure inked the screen to begin with", len(at) > 200, "%d pixels" % len(at))
        p.evaluate(SNAP, "drawn")
        # The beam to the middle: the amplitude to nought, as a hand would.
        p.evaluate("() => { const a = document.getElementById('amp'); a.value = '0'; a.dispatchEvent(new Event('input', { bubbles: true })); }")
        p.wait_for_timeout(fade_ms)
        p.evaluate(SNAP, "faded")
        # What the screen is with nothing left to fade: cleared, the beam at rest.
        p.evaluate("() => { wipeScreen = true; }"); p.wait_for_timeout(500)
        p.evaluate(SNAP, "cleared")
        after = p.evaluate(WORST, [at, "faded", "cleared"])
        check("everywhere it had been is back within two levels of a cleared screen",
              after["worst"] <= 2, "worst %d at %s, of %d pixels" % (after["worst"], after["where"], after["n"]))
        before = p.evaluate(WORST, [at, "drawn", "cleared"])
        null("before the fade the same pixels are far from it", before["worst"] > 20, "worst %d" % before["worst"])

    print("\n--- the axis's name ---")
    p.evaluate(DRAW, "0.0255")
    names = []
    def label_now():
        return p.evaluate("() => laneName(state.xyPair[0])")
    def strip_cleared():
        p.evaluate("() => { wipeScreen = true; }"); p.wait_for_timeout(400)
        return p.evaluate(STRIP)
    def mid_side(on):
        p.evaluate("(on) => { showControl('midSide'); const m = document.getElementById('midSide'); m.checked = on; m.dispatchEvent(new Event('change', { bubbles: true })); setMeasureOpen(false); }", on)
        p.wait_for_timeout(300)
    left_name = label_now()
    left_clean = strip_cleared()
    p.wait_for_timeout(2000)
    mid_side(True)
    mid_name = label_now()
    p.wait_for_timeout(1500)
    mid_now = p.evaluate(STRIP)
    mid_clean = strip_cleared()
    check("the name changed", left_name != mid_name, "%s, then %s" % (left_name, mid_name))
    check("the strip is what a cleared screen draws for the new name alone",
          differ(mid_now, mid_clean) <= 2, "largest difference %d" % differ(mid_now, mid_clean))
    null("the old name's strip is not the new one's", differ(left_clean, mid_clean) > 20, "largest difference %d" % differ(left_clean, mid_clean))
    mid_side(False)

    print("\n--- Y-T's time marks ---")
    # The same in Y-T, whose strip under the plot carries the time marks: a
    # new timebase writes new marks where the old ones were.
    def timebase(i):
        p.evaluate("(i) => { const t = el.timebase; t.value = String(i); t.dispatchEvent(new Event('input', { bubbles: true })); }", i)
        p.wait_for_timeout(300)
    p.evaluate("() => { hostQuietly(() => restore({ shape: 'sine', freq: 220, display: 'yt', persistence: '0.0255', pictureAmount: 0, oscScan: 0 })); hostSendSetup(); }")
    timebase(4); p.wait_for_timeout(800)
    marks_a = strip_cleared()
    p.wait_for_timeout(1500)
    timebase(9); p.wait_for_timeout(1500)
    marks_now = p.evaluate(STRIP)
    marks_b = strip_cleared()
    check("the strip is what a cleared screen draws for the new timebase alone",
          differ(marks_now, marks_b) <= 2, "largest difference %d" % differ(marks_now, marks_b))
    null("the old timebase's marks are not the new one's", differ(marks_a, marks_b) > 20, "largest difference %d" % differ(marks_a, marks_b))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails))
sys.exit(1 if fails else 0)
