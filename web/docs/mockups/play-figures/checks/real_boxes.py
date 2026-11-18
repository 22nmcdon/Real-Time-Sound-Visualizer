"""The boxes the mockup lays its window out in, read from scope.html itself:
the header, the tabs' row, the tab's own area, the modulation row, the
Picture section and the Keyboard band (one hand and two), at each window, in
the page's own pixels (divided by its zoom). The numbers in index.html's
SIZES are this script's output at d5c2928.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/play-figures/checks/real_boxes.py
"""
import os
import json
from playwright.sync_api import sync_playwright
SIZES=[(1660,1050),(1400,900),(1100,860),(1200,680),(1100,680),(960,600)]
out={}
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=os.environ.get("CHROME", "/opt/pw-browsers/chromium"),args=["--autoplay-policy=no-user-gesture-required"])
    for W,H in SIZES:
      for hands in (False,True):
        p=b.new_page(viewport={"width":W,"height":H})
        p.goto("file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "scope.html"))); p.wait_for_timeout(1000)
        if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
        p.evaluate("()=>setBenchTab('play')"); p.wait_for_timeout(300)
        if hands:
            p.evaluate("()=>{const c=document.querySelector('#midiLayers'); if(c){c.value=c.options[c.options.length-1].value; c.dispatchEvent(new Event('change',{bubbles:true}));}}"); p.wait_for_timeout(500)
        r=p.evaluate("""()=>{const z=pageZoom;const R=n=>{if(!n)return null;const q=n.getBoundingClientRect();return [q.left/z,q.top/z,q.width/z,q.height/z].map(Math.round)};
          const B=el.benchBody;const band=B.querySelector('.bench-band');
          return {zoom:z,compact:document.body.dataset.compact!==undefined,inner:[innerWidth/z,innerHeight/z].map(Math.round),
           header:R(document.querySelector('header')),screen:R(el.screenFrame||document.getElementById('screenFrame')),
           rail:R(document.getElementById('benchRail')),stage:R(el.benchStage),body:R(B),band:R(band),
           modrow:R(document.getElementById('modRow')),pic:R(document.getElementById('pictureBar')),
           layers:document.querySelector('#midiLayers')&&document.querySelector('#midiLayers').value}}""")
        out[f"{W}x{H}{' two' if hands else ''}"]=r
        p.close()
print(json.dumps(out,indent=0))
