"""No Bench tab may scroll - in every combination, not only the ones a
feature's own test happens to set up.

The rule is one of the layout decisions in CLAUDE.md, and each tab was
measured when it changed; but a tab's height depends on things set in other
places - the kind of generator, a rack or the tone, a keyboard showing, the
Photocell on, controllers learned - and nobody measured them together. A
rack of six with the Photocell on put the Sources tab 18 px over, 74 with a
keyboard and a solid, and nothing noticed until a feature added a line to it.

So, against the ways it fails:

- a tab over in some combination: every tab, on the tone and on a rack of
  six, with and without the keyboard's sources and the Photocell's, for each
  of the four kinds of generator - and the worst of them again with a Nord's
  ten controllers learned;
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


SWEEP = """async ([rack]) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const wav = (name, hz) => {
    const rate = 44100, n = rate / 4, bytes = 44 + n * 2;
    const buf = new ArrayBuffer(bytes), v = new DataView(buf);
    const str = (o, t) => { for (let i = 0; i < t.length; i++) v.setUint8(o + i, t.charCodeAt(i)); };
    str(0, 'RIFF'); v.setUint32(4, bytes - 8, true); str(8, 'WAVE'); str(12, 'fmt ');
    v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
    v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true);
    v.setUint16(34, 16, true); str(36, 'data'); v.setUint32(40, n * 2, true);
    for (let i = 0; i < n; i++) v.setInt16(44 + i * 2, Math.round(12000 * Math.sin(2 * Math.PI * hz * i / rate)), true);
    return new File([buf], name + '.wav', { type: 'audio/wav' });
  };
  if (rack) {
    el.rackSynth.checked = true; state.rackSynth = false; await setRackSynth(true);
    await addRackFiles([1, 2, 3, 4, 5].map((i) => wav('f' + i, 200 + 60 * i)));
    await wait(900);
  }
  setView('bench');
  const over = [], cases = [], mismeasured = [];
  const measure = (label) => {
    for (const [tab] of BENCH_TABS) {
      setBenchTab(tab);
      const by = el.benchBody.scrollHeight - el.benchBody.clientHeight;
      cases.push(label + '/' + tab);
      if (by > 0) over.push([label, tab, by]);
      // What the dealer measured each section at, against what it is now.
      for (const [group, h] of benchMeasured) {
        if (Math.abs(group.offsetHeight - h) > 1) mismeasured.push([label, tab, group.id || '?', h, group.offsetHeight]);
      }
    }
  };
  for (const keys of [false, true]) {
    if (keys) { setScreenKeys(true); await wait(100); }
    for (const photoOn of [false, true]) {
      if (photoOn !== photo.on) { el.photoButton.click(); await wait(150); }
      for (const mode of ['wave', 'harmonograph', 'figure', 'wireframe']) {
        el.genMode.value = mode; el.genMode.dispatchEvent(new Event('change')); await wait(120);
        measure([rack ? 'rack' : 'tone', keys ? 'keys' : '', photoOn ? 'photo' : '', mode].filter(Boolean).join('+'));
      }
    }
  }
  // The worst of them with ten controllers learned - a Nord Electro's nine
  // drawbars and its swell pedal - which grow the Controllers family by a chip
  // each. It holds about twenty in this state before its column is full.
  for (let n = 16; n < 26; n++) midiControl(n, 64);
  buildSourceGrid();
  measure((rack ? 'rack' : 'tone') + '+keys+photo+wireframe+10cc');
  return { over, cases: cases.length, mismeasured };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    results = {}
    bad = []
    for rack in (False, True):
        p = b.new_page(viewport={"width": 1400, "height": 900})
        p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
        p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
        if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
        results["rack" if rack else "tone"] = p.evaluate(SWEEP, [rack])
        p.close()

    for name, r in results.items():
        print("\n--- %s: %d tab-and-state cases ---" % (name, r["cases"]))
        check("on the %s, no tab scrolls in any of them" % ("rack of six" if name == "rack" else "tone"),
              r["over"] == [] and r["cases"] >= 100, str(r["over"][:6]))
        check("and every section is dealt at the height it was measured at",
              r["mismeasured"] == [], str(r["mismeasured"][:4]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("every tab fits, whatever else is on")
