from playwright.sync_api import sync_playwright
import os, sys
import corpus
HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)                    # web/, which holds scope.html
SHOTS = os.path.join(HERE, "shots")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
os.makedirs(SHOTS, exist_ok=True)

ok = True
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width":1400,"height":900})
    bad=[]
    p.on("pageerror", lambda e: bad.append("pageerror: "+str(e)))
    p.on("console", lambda m: bad.append("console: "+m.text) if m.type=="error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(800)
    corpus.install(p)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(300)

    # As sources.py: the shared format, and a failure that fails the run. It
    # failed unseen from 5m to 5v on state.source.kind, "host" for the
    # instrument whatever it draws.
    def check(name, cond, detail=""):
        global ok
        print(("  PASS  " if cond else "  FAIL  ") + name + ("   " + str(detail) if detail else ""))
        if not cond: ok = False

    print("-- the tone, untouched --")
    check("source is the tone", p.evaluate("playingKind()") == "tone")
    check("two lanes", p.evaluate("laneCount()") == 2)
    check("not stacked", p.evaluate("stacked()") is False)
    check("mid/side offered", p.evaluate("!el.midSide.parentElement.hidden"))
    check("legend has two", p.evaluate("el.laneLegend.children.length") == 2)
    # Silent until a note since 10 Nov, as the plugin is: nothing to trigger
    # on, and then a note held, which does.
    check("silent, nothing triggers", not p.evaluate("capture().triggered"))
    p.evaluate("() => midiNoteOn(57, 127)"); p.wait_for_timeout(400)
    check("triggers under a note", p.evaluate("capture().triggered"))
    p.evaluate("() => midiNoteOff(57)")

    print("-- every preset applies --")
    # The old library from before P8g, 268 real setups, and then the bank: a
    # setup that throws on loading is as likely among the old as the new, and
    # the bank alone is eleven. The count is held, so a walk that found
    # nothing to load cannot pass as a clean one.
    old = p.evaluate("CORPUS.flatMap(([, entries]) => entries.map(([name]) => name))")
    for v in old:
        p.evaluate(f"loadCorpus({v!r})")
    values = p.evaluate("PRESETS.flatMap(([, entries]) => entries.map(([name]) => 'b:' + name))")
    for v in values:
        p.evaluate(f"applyPreset({v!r})")
    p.wait_for_timeout(400)
    check(f"{len(old)} old presets and {len(values)} of the bank, no errors",
          not bad and len(old) > 250 and len(values) > 0, bad[:2])
    # Back on the base, the plain sound New loads: the bank ends on a split,
    # whose two hands are four lanes with no keyboard too since 10 Nov (it was
    # one layer, two lanes, until a keyboard came), and the checks below are
    # about the tone's two.
    p.evaluate("() => applyPreset('n:' + BASE_NAME)"); p.wait_for_timeout(300)

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

    # A single stereo file, and the tone again with the transport and the
    # rack's rows put away, were checked here until P5 cut both.
    check("two lanes, named L/R, on the tone", p.evaluate("laneCount()") == 2
          and p.evaluate("[laneName(0), laneName(1)]") == ["Left", "Right"])

    print()
    print("problems:", bad if bad else "none")
    check("no console or page errors", not bad)
    b.close()
print()
print("REGRESSION", "PASS" if ok else "FAIL")
raise SystemExit(0 if ok else 1)
