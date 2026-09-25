"""Every source button, from every state, including pickers that are cancelled.

The bug this exists for: clicking Stems showed the rack rows before any rack
existed, the picker was cancelled, and Tone returned on its first line because
a tone was already loaded - so nothing put the panel back and the switch was a
one-way door.
"""
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

def check(name, cond, detail=""):
    global ok
    print(("  ok  " if cond else " FAIL ") + name + (("  " + str(detail)) if detail else ""))
    if not cond: ok = False

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width":1400,"height":900})
    bad=[]
    p.on("pageerror", lambda e: bad.append("pageerror: "+str(e)))
    p.on("console", lambda m: bad.append("console: "+m.text) if m.type=="error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.locator("#menuButton").click(); p.wait_for_timeout(150)

    tone_visible = lambda: p.locator("#genMode").is_visible()
    # The rack's own rows, by the box that puts the generator in it. It was the
    # Stacked button, which moved to the Lanes section when the lanes got one
    # - and that section is off until a rack is loaded, which is the point.
    rack_visible = lambda: p.locator("#rackSynth").is_visible()
    mark = lambda: p.locator("#sourceMark").inner_text()

    print("-- Stems, picker cancelled, then back to Tone --")
    p.locator("#srcRack").click(no_wait_after=True); p.wait_for_timeout(250)
    check("rack rows shown", rack_visible())
    check("head still says the tone is playing", mark() == "TEST TONE", mark())
    p.locator("#srcTone").click(); p.wait_for_timeout(250)
    check("tone editor is back", tone_visible())
    check("rack rows put away", not rack_visible())

    print("-- File, picker cancelled, then back to Tone --")
    p.locator("#srcFile").click(no_wait_after=True); p.wait_for_timeout(250)
    check("file rows shown", p.locator("#fileChooseRow").is_visible())
    check("head still says the tone is playing", mark() == "TEST TONE", mark())
    p.locator("#srcTone").click(); p.wait_for_timeout(250)
    check("tone editor is back", tone_visible())

    print("-- Stems cancelled, then straight to File, then back --")
    p.locator("#srcRack").click(no_wait_after=True); p.wait_for_timeout(200)
    p.locator("#srcFile").click(no_wait_after=True); p.wait_for_timeout(250)
    check("file rows shown, rack rows gone", p.locator("#fileChooseRow").is_visible() and not rack_visible())
    p.locator("#srcTone").click(); p.wait_for_timeout(250)
    check("tone editor is back", tone_visible())

    print("-- a real rack, then back to Tone, then back to the rack --")
    p.locator("#srcRack").click(no_wait_after=True); p.wait_for_timeout(200)
    p.locator("#rackInput").set_input_files([f"{STEMS}/{n}.wav" for n in ("drums","bass","other")])
    p.wait_for_timeout(1800)
    check("rack loaded", p.evaluate("state.source.kind") == "rack")
    check("head says Stems", mark() == "STEMS", mark())
    check("three lanes", p.evaluate("laneCount()") == 3)
    p.locator("#srcTone").click(); p.wait_for_timeout(400)
    check("tone loaded", p.evaluate("state.source.kind") == "tone")
    check("tone editor is back", tone_visible())
    check("head says Test tone", mark() == "TEST TONE", mark())
    check("back to two lanes", p.evaluate("laneCount()") == 2)
    check("legend back to two", p.evaluate("el.laneLegend.children.length") == 2)
    # Lanes remembers what was in the rack, so coming back is not starting
    # again - and a file added now goes in beside the three, not instead.
    p.locator("#srcRack").click(no_wait_after=True); p.wait_for_timeout(1800)
    check("Lanes brings the rack back as it was", p.evaluate("laneCount()") == 3
          and p.evaluate("state.source.kind") == "rack")
    p.locator("#rackInput").set_input_files([f"{STEMS}/vocals.wav"])
    p.wait_for_timeout(1800)
    check("and a file added goes in beside them: four lanes", p.evaluate("laneCount()") == 4,
          str(p.evaluate("state.source.lanes.map((l) => l.name)")))

    print("-- a real file over a rack, then Tone --")
    p.locator("#srcFile").click(no_wait_after=True); p.wait_for_timeout(200)
    p.locator("#fileInput").set_input_files(f"{STEMS}/other.wav")
    p.wait_for_timeout(1800)
    check("file loaded", p.evaluate("state.source.kind") == "file")
    check("two lanes, named L/R", p.evaluate("[laneName(0), laneName(1)]") == ["Left","Right"])
    check("rack rows put away", not rack_visible())
    p.locator("#srcTone").click(); p.wait_for_timeout(400)
    check("tone editor is back", tone_visible())

    print("-- Mic, denied, must not strand the panel --")
    # Lanes brings the rack back now, so the mic is refused over a rack: the
    # panel goes back to the rack's rows, and the credit does not promise a
    # test tone that is not playing - which it did, whatever was loaded.
    p.locator("#srcRack").click(no_wait_after=True); p.wait_for_timeout(1800)
    p.locator("#srcMic").click(); p.wait_for_timeout(900)
    check("no mic in this container, so the rack's rows came back",
          p.evaluate("state.source.kind") == "rack" and rack_visible() and not tone_visible())
    credit = p.locator("#credit").inner_text().lower()
    check("credit explains, without promising the test tone", "microphone" in credit
          and "test tone" not in credit, credit)
    p.locator("#srcTone").click(); p.wait_for_timeout(400)
    p.locator("#srcMic").click(); p.wait_for_timeout(900)
    check("and over the tone, the tone rows came back", tone_visible())
    check("saying the tone still works", "test tone" in p.locator("#credit").inner_text().lower(),
          p.locator("#credit").inner_text())

    print("-- the tone still works after all of that --")
    check("triggers", p.evaluate("capture().triggered"))
    check("generator responds", p.evaluate("""() => {
        el.freq.value = '330'; el.freq.dispatchEvent(new Event('input'));
        return state.source.settings.freq; }""") == 330)
    print()
    print("problems:", bad if bad else "none")
    check("no errors", not bad)
    b.close()
print()
print("SOURCE SWITCHING", "PASS" if ok else "FAIL")
