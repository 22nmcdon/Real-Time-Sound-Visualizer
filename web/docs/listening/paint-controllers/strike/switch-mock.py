"""Where the wheel's and pressure's Sound / Brush / Both switch would go on Play: mocked into the page in a
headless browser for a picture only, at 1400x900, 960x600 (compact) and 1660x1050, with the tabs' scroll checked
before and after. Nothing of it is built.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/listening/paint-controllers/strike/switch-mock.py
"""
import os, sys
from playwright.sync_api import sync_playwright
ART = os.path.abspath("web")
OUT = "web/docs/listening/paint-controllers/strike"
INJECT = """() => {
  const css = document.createElement('style');
  css.textContent = `.mock-lab{display:flex !important;align-items:center;justify-content:space-between;gap:3px;min-width:0;max-width:100%;overflow:hidden;white-space:nowrap}
  .mock-job{display:inline-flex;flex:0 0 auto;border:1px solid var(--line,#d9cdbf);border-radius:999px;overflow:hidden;font-size:8.5px;line-height:1.15;letter-spacing:0.02em}
  .mock-job span{padding:0 4px;color:var(--text-soft,#6b615a)} .mock-job span.on{background:var(--charcoal,#241f1d);color:var(--paper,#fffcf7)}
  body[data-compact] .mock-job span{padding:0 2px} .mock-ring{outline:2px dashed #b08d57;outline-offset:3px;border-radius:6px}`;
  document.head.appendChild(css);
  const compact = document.body.hasAttribute('data-compact');
  for (const [id, name] of [['midiWheelTo', 'Wheel'], ['midiPressureTo', 'Pressure']]) {
    const lab = document.querySelector('label[for="' + id + '"]');
    if (!lab) continue;
    lab.textContent = ''; const nm = document.createElement('span'); nm.textContent = name; lab.appendChild(nm);
    lab.classList.add('mock-lab');
    const j = document.createElement('span'); j.className = 'mock-job';
    j.innerHTML = compact ? '<span title="Sound">S</span><span title="Brush">B</span><span class="on">Both</span>' : '<span>Sound</span><span>Brush</span><span class="on">Both</span>';
    lab.appendChild(j);
    lab.closest('.menu-row').classList.add('mock-ring');
  }
  return true;
}"""
FIT = """() => { const out = []; for (const e of document.querySelectorAll('.bench-tab, .bench-body, [data-tab], .bench-col'))
  if (e.offsetParent && e.scrollHeight > e.clientHeight + 1 && getComputedStyle(e).overflowY !== 'visible') out.push((e.id || e.className) + ' ' + e.scrollHeight + '>' + e.clientHeight);
  const r = document.getElementById('midiWheelTo').getBoundingClientRect(), l = document.querySelector('label[for=midiWheelTo]').getBoundingClientRect();
  return { scrolls: out, label: [Math.round(l.width), Math.round(l.height)], menu: [Math.round(r.width), Math.round(r.height)] }; }"""
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=os.environ.get("CHROME", "/opt/pw-browsers/chromium"))
    for w, h in ((1400, 900), (960, 600), (1660, 1050)):
        p = b.new_page(viewport={"width": w, "height": h})
        p.goto("file://%s/scope.html" % ART); p.wait_for_timeout(2500); p.keyboard.press("Escape"); p.wait_for_timeout(300)
        p.evaluate("() => { if (typeof showControl === 'function') showControl('midiWheelTo'); }"); p.wait_for_timeout(400)
        before = p.evaluate(FIT)
        p.evaluate(INJECT); p.wait_for_timeout(300)
        after = p.evaluate(FIT)
        print(w, h, "before", before, "after", after)
        p.screenshot(path="%s/switch-play-%dx%d.png" % (OUT, w, h))
        p.close()
    b.close()
