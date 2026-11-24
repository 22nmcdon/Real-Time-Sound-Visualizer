"""The governor's word on the unison (24 Nov, the owner's report that a
unison of seven "almost cuts out"): when the instrument plays fewer copies
than the Unison menu asks, the face says so, from the budget the instrument
serves, and says nothing otherwise.

What would go wrong, and what is checked for it:

- A word the page works out for itself, which could disagree with what
  plays. The box's numbers are read against the instrument's own budget at
  the same moment (`state.source.budget`, the worklet's readings), and
  under the owner's own setup and a chord of three a hand they are the
  count the core's governor settles on, natively, for that chord: two in
  the lower hand and three in the upper, of seven.
- A word that is always there, or never: a light sound - the plain sine,
  unison seven, one note - shows nothing, the menu's name in its place
  (the null), and the heavy chord let go takes the word away again.
- A word that moves the face: every box in the Ink tab's row of controls,
  the Unison menu and its name, measured to half a pixel with the word and
  without it, at 1400x900 and at the plugin's 960x600.
- An info line that does not say it: resting on the menu while it is cut
  says "7 asked" and how many play, and on a light sound it does not.

The plugin's side, the budget served in lfos.bin and a heavy chord's count,
is the shell test's (plugin/tests/ShellTest.cpp).
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

sys.path.insert(0, HERE)
from unisoncuttest_setup import OWNER, CHORD  # the owner's setup and chord, shared with diagtest

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)
def null(name, ok, detail=""): check("null: " + name, ok, detail)

READ = """() => {
  const box = document.getElementById('oscUnisonCut'), label = box.parentElement.querySelector('.menu-label');
  const b = state.source && state.source.budget;
  return { shown: !box.hidden, text: box.textContent, title: box.title, labelSeen: getComputedStyle(label).visibility !== 'hidden',
           budget: b ? { asked: b.asked.slice(), unison: b.unison.slice() } : null, two: layersOn() };
}"""
# Every box in the row of Ink's Oscillator controls, the menu and its name.
BOXES = """() => {
  const row = document.getElementById('oscUnison').closest('.ink-knobs') || document.getElementById('oscGroup');
  const out = [];
  for (const n of row.querySelectorAll('*')) {
    if (n.id === 'oscUnisonCut' || n.closest('#oscUnisonCut') || n.offsetParent === null) continue;
    const r = n.getBoundingClientRect(); out.push([r.x, r.y, r.width, r.height]);
  }
  return out;
}"""

def same(a, b):
    return len(a) == len(b) and all(abs(x - y) <= 0.5 for p, q in zip(a, b) for x, y in zip(p, q))

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    for w, h in ((1400, 900), (960, 600)):
        print("\n--- at %dx%d ---" % (w, h))
        p = b.new_page(viewport={"width": w, "height": h})
        bad = []
        p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
        p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500)
        if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
        p.wait_for_function("state.source && state.source.kind === 'host'", timeout=30000)

        # The light sound first: the plain sine at unison seven, one note.
        p.evaluate("() => { setBenchTab('ink'); }")
        p.evaluate("() => { el.oscUnison.value = '7'; el.oscUnison.dispatchEvent(new Event('change', { bubbles: true })); }")
        p.wait_for_timeout(300)
        p.evaluate("() => scopeHost.midi([0x90, 60, 100])"); p.wait_for_timeout(1200)
        light = p.evaluate(READ)
        p.evaluate("() => sayInfo(el.oscUnison)")
        light_info = p.evaluate("() => el.infoText.textContent")
        p.evaluate("() => scopeHost.midi([0x80, 60, 0])"); p.wait_for_timeout(600)
        null("a light sound, one sine note at seven copies, shows nothing and keeps the menu's name",
             not light["shown"] and light["labelSeen"] and light["budget"] and light["budget"]["unison"][0] == 7,
             str(light))
        null("and its info line does not say what plays", "asked" not in light_info, light_info[:80])

        # The owner's setup and a chord of three a hand.
        p.evaluate("(c) => loadCode(c)", OWNER); p.wait_for_timeout(1500)
        p.evaluate("() => setBenchTab('ink')"); p.wait_for_timeout(400)
        before = p.evaluate(BOXES)
        for n in CHORD: p.evaluate("(n) => scopeHost.midi([0x90, n, 100])", n)
        p.wait_for_timeout(2000)
        heavy = p.evaluate(READ)
        during = p.evaluate(BOXES)
        bud = heavy["budget"] or {"asked": [0, 0], "unison": [0, 0]}
        want = "%d · %d of %d" % (bud["unison"][0], bud["unison"][1], bud["asked"][0])
        check("under the owner's setup and a chord of three a hand the word is shown, over the menu's name",
              heavy["shown"] and not heavy["labelSeen"], str(heavy))
        check("and it is the instrument's own count, read at the same moment: " + want,
              heavy["two"] and heavy["text"] == want and bud["asked"] == [7, 7] and bud["unison"][0] < 7, heavy["text"])
        check("which is the core's governor's for that chord: two in the lower hand and three in the upper, of seven",
              bud["unison"] == [2, 3], str(bud))
        null("a word that said seven of seven would not be it", heavy["text"] != "7 · 7 of 7")
        check("its title says it in full, asked and playing, each hand by name",
              "Lower 7 asked, 2 playing" in heavy["title"] and "Upper 7 asked, 3 playing" in heavy["title"], heavy["title"])
        p.evaluate("() => sayInfo(el.oscUnison)")
        info = p.evaluate("() => el.infoText.textContent")
        check("resting on the menu, the info line says it first", info.startswith("Now Lower 7 asked, 2 playing"), info[:90])
        check("nothing in the row moves when the word comes: every box the same to half a pixel",
              same(before, during) and len(during) > 10, "%d boxes" % len(during))
        moved = [[x + 1, y, ww, hh] for x, y, ww, hh in during]
        null("the same comparison sees a pixel's move", not same(before, moved))

        for n in CHORD: p.evaluate("(n) => scopeHost.midi([0x80, n, 0])", n)
        p.wait_for_timeout(2500)
        gone = p.evaluate(READ)
        check("let go, the word goes and the name comes back", not gone["shown"] and gone["labelSeen"], str(gone))
        check("no page errors", not bad, str(bad[:3]))
        p.close()
    b.close()

print()
if fails: print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("unisoncuttest: all checks pass")
