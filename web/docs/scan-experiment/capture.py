"""Lay the phosphor from presets in the page and record it frame by frame.
The page's grid is what the C++ core's is (parity.py holds them equal), so this
is the grid Scan would read, without building anything."""
import json, os, sys
import numpy as np
from playwright.sync_api import sync_playwright
ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
OUT = sys.argv[1]
PRESETS = ["Perfect fifth, just", "Perfect fifth, equal", "Rose", "Harmonograph", "Morphing rose", "Kaleidoscope"]
FRAMES = 180
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=os.environ.get("CHROME", "/opt/pw-browsers/chromium"),
                           args=["--autoplay-policy=no-user-gesture-required"])
    for name in PRESETS:
        p = b.new_page(viewport={"width": 1400, "height": 900})
        p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1200)
        if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
        p.evaluate("(n) => applyPreset('b:' + n)", name)
        p.wait_for_timeout(1500)
        got = p.evaluate("""(n) => new Promise((done) => {
            const grids = [], frames = [];
            const step = () => {
              grids.push(Array.from(pictureEngine.cells)); frames.push(pictureEngine.frames);
              if (grids.length >= n) done({ grids, frames, display: state.display, kind: pictureEngine.kind });
              else requestAnimationFrame(step);
            };
            requestAnimationFrame(step);
        })""", FRAMES)
        g = np.array(got["grids"], dtype=np.float32).reshape(FRAMES, 64, 64)
        slug = name.lower().replace(",", "").replace(" ", "-")
        np.save(os.path.join(OUT, slug + ".npy"), g)
        fr = got["frames"]
        p.locator("canvas").first.screenshot(path=os.path.join(OUT, slug + ".png"))
        print("%-22s display %s engine %s | engine frames %d..%d (%d distinct of %d) | lit %.3f..%.3f | max %.2f" % (
            name, got["display"], got["kind"], fr[0], fr[-1], len(set(fr)), FRAMES,
            (g > 0.05).mean(axis=(1, 2)).min(), (g > 0.05).mean(axis=(1, 2)).max(), g.max()), flush=True)
        p.close()
    b.close()
