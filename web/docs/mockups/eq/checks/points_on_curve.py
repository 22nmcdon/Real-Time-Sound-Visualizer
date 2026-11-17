"""Every point of the EQ mockup sits on the drawn total curve (the owner, 17 Nov).

For each setting, at both windows, in the large editor and on the line's small
curve: the point's centre against the drawn path's height at the point's x,
read from the path's own coordinates, within half a pixel. The null is the
first version's placement, the band's own full gain, which must miss by more
than that on a shelf - so the check can fail.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/eq/checks/points_on_curve.py
"""
import os, sys
from playwright.sync_api import sync_playwright

PAGE = "file://" + os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "index.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
# gains in tenths of a dB, places 0-100, width in tenths of an octave, as the knobs hold them
SETTINGS = [
    ("the switch's start", [30, 0, 30], [50, 50, 50], 10),
    ("the page's opening", [30, -40, 30], [50, 41, 50], 14),
    # A shelf over the mid. With the mid at +8 dB it filled in the shelf's missing half at its corner,
    # so the old placement happened to sit on the curve there and the null could not see it: +4 here.
    ("a shelf over the mid", [120, 40, 0], [100, 30, 50], 20),
    ("a narrow mid on a high shelf", [-60, 100, 90], [20, 100, 40], 2),
    ("a wide cut between two boosts", [90, -110, 90], [70, 50, 30], 40),
    ("the mid alone", [0, 65, 0], [50, 50, 50], 10),
]
MEASURE = """(which) => {
  const svg = which === 'plot' ? document.getElementById('plot') : document.getElementById('thumbSvg');
  const path = which === 'plot' ? document.getElementById('sumPath') : svg.querySelectorAll('path')[svg.querySelectorAll('path').length - 1];
  const pts = path.getAttribute('d').match(/[ML][^ML]+/g).map((t) => t.slice(1).trim().split(/\\s+/).map(Number));
  const yAt = (x) => { for (let i = 1; i < pts.length; i++) if (pts[i][0] >= x) {
      const [x0, y0] = pts[i - 1], [x1, y1] = pts[i]; return x1 === x0 ? y1 : y0 + (y1 - y0) * (x - x0) / (x1 - x0); }
    return pts[pts.length - 1][1]; };
  const h = cur(), out = [];
  const dots = which === 'plot' ? Array.from(svg.querySelectorAll('.pt .ring')) : Array.from(svg.querySelectorAll('circle'));
  dots.forEach((c, k) => {
    if (which === 'thumb' && h.g[k] === 0 && !h.g.some((v) => v)) return;
    const cx = +c.getAttribute('cx'), cy = +c.getAttribute('cy');
    // The first version's placement, the band's own gain, on the same axis: the null.
    const g = which === 'plot' ? geo : null;
    let oldY;
    if (which === 'plot') oldY = geo.y(h.g[k] / 10);
    else { const ht = svg.clientHeight || 34; oldY = ht / 2 - (h.g[k] / 10) / 13 * (ht / 2 - 3); }
    out.push({ band: k, gain: h.g[k], miss: Math.abs(cy - yAt(cx)), oldMiss: Math.abs(oldY - yAt(cx)) });
  });
  return out;
}"""

fails = []
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    p = b.new_page(viewport={"width": 1500, "height": 1100})
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto(PAGE); p.wait_for_timeout(500)
    worst, nullShelf = 0.0, []
    for size in ["big", "small"]:
        p.click(f'#pgSize button[data-v="{size}"]'); p.wait_for_timeout(100)
        for name, g, pos, w in SETTINGS:
            p.evaluate("([g, pos, w]) => { S.hand.forEach((h) => { h.g = g.slice(); h.pos = pos.slice(); h.w = w; }); paint(); }", [g, pos, w])
            for which in ["plot", "thumb"]:
                for r in p.evaluate(MEASURE, which):
                    worst = max(worst, r["miss"])
                    if r["band"] != 1 and r["gain"] != 0: nullShelf.append((r["oldMiss"], f"{size} {name} {which} band {r['band']}"))
                    if r["miss"] > 0.5:
                        fails.append(f"{size} {name} {which} band {r['band']}: {r['miss']:.3f} px off the curve")
    print(f"worst distance of a point from the drawn curve: {worst:.4f} px (limit 0.5)")
    lo, hi = min(nullShelf), max(nullShelf)
    print(f"null, the band's own gain on a shelf: smallest miss {lo[0]:.2f} px ({lo[1]}), largest {hi[0]:.2f} px")
    if lo[0] <= 0.5: fails.append("null: the old placement does not miss on every shelf: " + lo[1])
    if errs: fails.append("page errors: " + "; ".join(errs))
    b.close()
for f in fails: print("FAIL", f)
print("PASS" if not fails else "FAILED")
sys.exit(1 if fails else 0)
