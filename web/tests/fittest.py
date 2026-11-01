"""No Bench tab may scroll - in every combination, not only the ones a
feature's own test happens to set up.

The rule is one of the layout decisions in CLAUDE.md, and each tab was
measured when it changed; but a tab's height depends on things set in other
places - the kind of generator, the band split or the tone, a keyboard
showing, the Photocell on, controllers learned - and nobody measured them
together. A rack of six (cut in P5) with the Photocell on put the Sources tab
18 px over, 74 with a keyboard and a solid, and nothing noticed until a
feature added a line to it.

So, against the ways it fails:

- a tab over in some combination: every tab, on the tone and on the band
  split, with and without the keyboard's sources and the Photocell's, for each
  of the four kinds of generator - the Sources tab with each family on show,
  since the family decides its height - and the worst of them again with
  thirty controllers learned, where the family's list has to scroll inside
  itself rather than put the tab over;
- a dealer that measures a section at a width it will not have. It stacks
  every section in the first column to measure them, and with the empty
  columns hidden that column was the whole Bench wide, so everything that
  wraps measured short and the dealer paired sections that could not fit
  together. Each section's measured height is held to its height once dealt.
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


SWEEP = """async ([bands]) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  /* The band split: an input of four lanes, with Picture's Lanes section on
     show - the worst case since P5 cut the rack, whose six lanes it was. */
  if (bands) {
    el.srcMic.click(); await wait(1500);
    el.micBands.click(); await wait(900);
  }
  const lanes = laneCount();
  setView('bench');
  const over = [], cases = [], mismeasured = [];
  let planeRows = null;
  const measure = (label) => {
    const views = [];
    for (const [tab] of BENCH_TABS) {
      if (tab !== 'sources') { views.push([tab, null]); continue; }
      for (const [family] of sourceFamilies()) views.push([tab, family]);
    }
    let last = null;
    for (const [tab, family] of views) {
      setBenchTab(tab);
      /* What the dealer measured each section at, against what it is now -
         straight after the deal, which is what this holds. A section can
         change height afterwards without anything being wrong: the source's
         detail does with the source chosen, and always did, and it has a
         column to itself. Whether any of that puts the tab over is the
         overflow check's question, asked below for every family. */
      if (tab !== last) {
        for (const [group, h] of benchMeasured) {
          if (Math.abs(group.offsetHeight - h) > 1) mismeasured.push([label, tab, group.id || '?', h, group.offsetHeight]);
        }
      }
      last = tab;
      if (family) chooseSourceFamily(family);
      const by = el.benchBody.scrollHeight - el.benchBody.clientHeight;
      const name = family ? tab + ':' + family : tab;
      cases.push(label + '/' + name);
      if (by > 0) over.push([label, name, by]);
    }
  };
  for (const keys of [false, true]) {
    if (keys) { setScreenKeys(true); await wait(100); }
    for (const photoOn of [false, true]) {
      if (photoOn !== photo.on) { el.photoButton.click(); await wait(150); }
      for (const mode of ['wave', 'harmonograph', 'figure', 'wireframe']) {
        el.genMode.value = mode; el.genMode.dispatchEvent(new Event('change')); await wait(120);
        measure([bands ? 'bands' : 'tone', keys ? 'keys' : '', photoOn ? 'photo' : '', mode].filter(Boolean).join('+'));
      }
    }
  }
  /* Two layers, with layer B's own plane on the panel: the Plane section
     grows its Layers row and B's Turn, the clip at the radius shows the
     radius's, and Delay and chorus grows its own Layers row. A drawn input
     keeps a split without applying it, so only the tone. */
  if (!bands) {
    el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
    setMidiMode('poly');
    el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change')); await wait(120);
    el.planeLayerB.click();
    el.planeLimit.value = '1'; el.planeLimit.dispatchEvent(new Event('change')); await wait(120);
    planeRows = [el.planeLayerRow.hidden, el.planeTurnRow.hidden, el.planeRadiusRow.hidden, el.timeLayerRow.hidden];
    measure('tone+keys+photo+layers+planeB');
    el.planeLayerBoth.click(); setMidiMode('dyad');
    el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change')); await wait(120);
  }
  // The worst of them with thirty controllers learned - three Nord Electros'
  // worth of drawbars and swells - which grow the Controllers family by a row
  // each. Past a dozen rows the list scrolls inside itself; the tab must not.
  for (let n = 16; n < 46; n++) midiControl(n, 64);
  buildSourceGrid();
  measure((bands ? 'bands' : 'tone') + '+keys+photo+wireframe+30cc');
  setBenchTab('sources'); chooseSourceFamily('controllers');
  const list = { rows: el.srcList.querySelectorAll('.src-row').length,
                 scrolls: el.srcList.scrollHeight > el.srcList.clientHeight + 1 };
  return { over, cases: cases.length, mismeasured, list, planeRows, lanes };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required",
                                 "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
    ctx = b.new_context(permissions=["microphone"], viewport={"width": 1400, "height": 900})
    results = {}
    bad = []
    for bands in (False, True):
        p = ctx.new_page()
        p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
        p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
        if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
        results["bands" if bands else "tone"] = p.evaluate(SWEEP, [bands])
        p.close()

    for name, r in results.items():
        print("\n--- %s: %d tab-and-state cases ---" % (name, r["cases"]))
        check("on the %s, no tab scrolls in any of them" % ("band split" if name == "bands" else "tone"),
              r["over"] == [] and r["cases"] >= 200 and r["lanes"] == (4 if name == "bands" else 2),
              "%d lanes; %s" % (r["lanes"], r["over"][:6]))
        check("and every section is dealt at the height it was measured at",
              r["mismeasured"] == [], str(r["mismeasured"][:4]))
        check("thirty controllers are thirty rows, and the list scrolls inside itself rather than the tab",
              r["list"] == {"rows": 30, "scrolls": True}, str(r["list"]))
        if name == "tone":
            check("the layered case had the Plane section's Layers, Turn and Radius rows and Delay and chorus's Layers row all showing",
                  r["planeRows"] == [False, False, False, False], str(r["planeRows"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("every tab fits, whatever else is on")
