from playwright.sync_api import sync_playwright
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)                    # web/, which holds scope.html
SHOTS = os.path.join(HERE, "shots")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
os.makedirs(SHOTS, exist_ok=True)

import fixtures
STEMS = fixtures.ensure()
ok = True
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width":1400,"height":900})
    bad=[]
    p.on("pageerror", lambda e: bad.append("pageerror: "+str(e)))
    p.on("console", lambda m: bad.append("console: "+m.text) if m.type=="error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(800)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(300)

    def check(name, cond, detail=""):
        global ok
        print(("  ok  " if cond else " FAIL ") + name + ("  " + str(detail) if detail else ""))
        if not cond: ok = False

    print("-- the tone, untouched --")
    check("source is the tone", p.evaluate("state.source.kind") == "tone")
    check("two lanes", p.evaluate("laneCount()") == 2)
    check("not stacked", p.evaluate("stacked()") is False)
    check("mid/side offered", p.evaluate("!el.midSide.parentElement.hidden"))
    check("legend has two", p.evaluate("el.laneLegend.children.length") == 2)
    check("triggers", p.evaluate("capture().triggered"))

    print("-- every preset applies --")
    values = p.evaluate("PRESETS.flatMap(([, entries]) => entries.map(([name]) => 'b:' + name))")
    for v in values:
        p.evaluate(f"applyPreset({v!r})")
    p.wait_for_timeout(400)
    check(f"{len(values)} presets, no errors", not bad, bad[:2])

    print("-- the three displays --")
    for mode in ("xy", "spect", "yt"):
        p.evaluate(f"setDisplay({mode!r})"); p.wait_for_timeout(500)
    check("display cycle clean", not bad, bad[:2])

    print("-- mid/side, cursors, panes --")
    p.evaluate("""() => { el.midSide.checked = true; el.midSide.dispatchEvent(new Event('change'));
      el.cursorsOn.checked = true; el.cursorsOn.dispatchEvent(new Event('change'));
      el.harmonicsOn.checked = true; el.harmonicsOn.dispatchEvent(new Event('change'));
      el.tunerOn.checked = true; el.tunerOn.dispatchEvent(new Event('change')); }""")
    p.wait_for_timeout(700)
    check("mid/side names", p.evaluate("[laneName(0), laneName(1)]") == ["Mid","Side"])
    p.screenshot(path=f"{SHOTS}/10-tone-regression.png")
    p.evaluate("""() => { el.midSide.checked = false; el.midSide.dispatchEvent(new Event('change')); }""")

    print("-- a single stereo file still behaves --")
    p.evaluate("setMenuOpen(true)"); p.wait_for_timeout(150)
    p.locator("#fileInput").set_input_files(f"{STEMS}/other.wav")
    p.wait_for_timeout(1800)
    check("file source", p.evaluate("state.source.kind") == "file")
    check("two lanes", p.evaluate("laneCount()") == 2)
    check("named L/R", p.evaluate("[laneName(0), laneName(1)]") == ["Left","Right"])
    check("choose-a-file row back", p.evaluate("!el.fileChooseRow.hidden"))
    check("plays", p.evaluate("state.source.playing"))

    print("-- and back to the tone --")
    p.evaluate("toTone()"); p.wait_for_timeout(400)
    check("tone again", p.evaluate("state.source.kind") == "tone")
    check("transport put away", p.evaluate("el.fileRows.hidden"))
    check("rack rows put away", p.evaluate("el.rackRows.hidden"))

    print()
    print("problems:", bad if bad else "none")
    check("no console or page errors", not bad)
    b.close()
print()
print("REGRESSION", "PASS" if ok else "FAIL")
