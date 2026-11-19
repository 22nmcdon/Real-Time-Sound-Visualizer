"""The boxes the LFO mockup lays its window out in, read from scope.html itself
at each of the six windows, in the page's own pixels (divided by its zoom):
the header, the tabs' row, the tab's own area, the modulation row and its
cards, the Picture section, and LFO 1's editor as it opens today over the
tabs (its box, its drawing, its Where it goes). The numbers in index.html's
SIZES are this script's output at 20dc8d3. It also takes a screenshot of
today's editor at 1400x900, for the note's "today".

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/lfo/checks/real_boxes.py
"""
import os, sys, json
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import webfonts
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCOPE = os.path.abspath(os.path.join(HERE, "..", "..", "..", "scope.html"))
SIZES = [(1660, 1050), (1400, 900), (1100, 860), (1200, 680), (1100, 680), (960, 600)]
out = {}
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=os.environ.get("CHROME", "/opt/pw-browsers/chromium"), args=["--autoplay-policy=no-user-gesture-required"])
    for W, H in SIZES:
        p = b.new_page(viewport={"width": W, "height": H})
        webfonts.route(p)
        p.goto("file://" + SCOPE); p.wait_for_timeout(1200); faces = webfonts.settle(p)
        if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
        p.evaluate("()=>setBenchTab('play')"); p.wait_for_timeout(300)
        p.locator('.mod-card[data-source="lfo1"]').first.click(); p.wait_for_timeout(500)
        r = p.evaluate("""()=>{const z=pageZoom;const R=n=>{if(!n||!n.getClientRects().length)return null;const q=n.getBoundingClientRect();return [q.left/z,q.top/z,q.width/z,q.height/z].map(v=>Math.round(v*10)/10)};
          const cards=[...document.querySelectorAll('.mod-card')].map(c=>({src:c.dataset.source,box:R(c),canvas:R(c.querySelector('canvas'))}));
          return {zoom:z,compact:document.body.dataset.compact!==undefined,inner:[innerWidth/z,innerHeight/z].map(Math.round),
           header:R(document.querySelector('header')),screen:R(document.getElementById('screenFrame')),
           rail:R(document.getElementById('benchRail')),stage:R(el.benchStage),body:R(el.benchBody),
           modrow:R(document.getElementById('modRow')),pic:R(document.getElementById('pictureBar')),cards,
           editor:R(el.modEditor),own:R(document.querySelector('#srcDetail .src-own')),goes:R(document.querySelector('#srcDetail .src-goes')),
           draw:R(document.getElementById('srcDraw'))}}""")
        r["webfonts"] = faces
        out[f"{W}x{H}"] = r
        if (W, H) in ((1400, 900), (960, 600)):
            p.screenshot(path=os.path.join(HERE, f"00-today-lfo1-editor-at-{W}x{H}.png"))
        p.close()
print(json.dumps(out, indent=1))
