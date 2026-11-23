"""The boxes the EQ-bands mockup lays its editor out in, read from scope.html
itself at 1400x900 and at 960x600 (Auto's 90 per cent), in the page's own
pixels (divided by its zoom): the window's parts behind the editor, the
editor, its head, the plot and the knobs' foot as the EQ editor opens today.
The numbers in index.html's SIZES are this script's output. It also takes a
screenshot of today's editor at each size, for the note's "today".

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/eq-bands/checks/real_boxes.py
"""
import os, sys, json
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import webfonts
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCOPE = os.path.abspath(os.path.join(HERE, "..", "..", "..", "scope.html"))
SIZES = [(1400, 900), (960, 600)]
out = {}
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=os.environ.get("CHROME", "/opt/pw-browsers/chromium"), args=["--autoplay-policy=no-user-gesture-required"])
    for W, H in SIZES:
        p = b.new_page(viewport={"width": W, "height": H})
        webfonts.route(p)
        p.goto("file://" + SCOPE); p.wait_for_timeout(1200); faces = webfonts.settle(p)
        if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
        p.evaluate("()=>{setBenchTab('space');}"); p.wait_for_timeout(300)
        p.evaluate("()=>{setControl('eqLow','45');setControl('eqMid','-30');setControl('eqCutHighFreq','800');openEqEditor();}"); p.wait_for_timeout(600)
        r = p.evaluate("""()=>{const z=pageZoom;const R=n=>{if(!n||!n.getClientRects().length)return null;const q=n.getBoundingClientRect();return [q.left/z,q.top/z,q.width/z,q.height/z].map(v=>Math.round(v*10)/10)};
          return {zoom:z,compact:document.body.dataset.compact!==undefined,inner:[innerWidth/z,innerHeight/z].map(Math.round),
           header:R(document.querySelector('header')),screen:R(document.getElementById('screenFrame')),
           rail:R(document.getElementById('benchRail')),stage:R(el.benchStage),
           modrow:R(document.getElementById('modRow')),pic:R(document.getElementById('pictureBar')),
           editor:R(el.eqEditor),head:R(el.eqEditorHead),plot:R(el.eqPlotWrap),foot:R(document.querySelector('#eqEditor .eq-foot')),
           knobs:R(el.eqEdKnobs),bands:[...document.querySelectorAll('#eqEdKnobs .eq-band')].map(R),
           knob:R(document.querySelector('#eqEdKnobs .knob'))}}""")
        r["webfonts"] = faces
        out[f"{W}x{H}"] = r
        p.screenshot(path=os.path.join(HERE, f"00-today-at-{W}x{H}.png"))
        p.close()
print(json.dumps(out, indent=1))
