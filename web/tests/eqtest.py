"""The EQ (17 Nov): three bands in the rack, after the Plane and before the
three the order moves.

What would go wrong, and what is checked for it:

- the EQ out of its place: it is second, after the Plane, under every one of
  the six orders, and has no handle to move it by. The null is the order the
  rack had before it (no EQ);
- a switch that changes its pill and not the sound: with nothing kept it
  gives its start (the low and high shelves up 3 dB, the mid alone) in the
  knobs, in what the page sends the engine and in the module's line; off
  takes the three gains to nought and keeps them, frequencies and width
  left where they were; on puts back what it kept - set first to something
  that is not the start, so a switch that forgot and gave the start again
  would fail - and after a load forgets it and gives the start again;
- the readings and the line lying about the octave laws: each knob's middle
  is 160 Hz, 1 kHz and 4 kHz, the ends 40 Hz and 16 kHz, held against the
  generator's own fields (eqLowHz and the rest), not against the page's
  arithmetic alone;
- a setup that does not come back: every EQ field set off its default,
  written as a code, read back and restored, lands where it was, in the
  knobs and in the engine; a default EQ writes no field at all (additive: an
  old code is an EQ at nought), and a code with no EQ restores one at
  nought over an EQ that was on - the null of the round trip;
- the hands: unlinked, the upper hand's knobs write its own EQ and not the
  lower's, the upper hand's fields go into the code (bEqLow and the rest),
  the generator is told the EQ is the upper hand's own (timeOwn's bit 16),
  and the code loads unlinked again; linked, a knob writes both;
- the Space & Memory tab's line not naming it when it is on.

Everything about what the EQ does to the sound is the core's
(core/tests/pieces/eq.py: the bands against Web Audio's node, its place in
the plane under all six orders, nought the same to the bit as none, a line
kept a line, each hand's own) and the face against the core is
core_tests.py's.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
COMPILED_CORE = os.path.join(HERE, "compiled_core.js")
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, ok, detail=""):
    check("null: " + name, ok, detail)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.add_init_script(path=COMPILED_CORE)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate("() => { setView('bench'); setBenchTab('space'); }"); p.wait_for_timeout(300)

    print("\n--- its place ---")
    places = p.evaluate("""() => FX_ORDERS.map((order) => { setFxOrder(order);
      return Array.from(document.querySelectorAll('#rackGroup > .fx-module')).map((m) => m.dataset.fx); })""")
    p.evaluate("() => setFxOrder('pcd')")
    check("second, after the Plane and before the three, under each of the six orders",
          len(places) == 6 and all(o[:2] == ["plane", "eq"] and o[-1] == "reverb" and sorted(o[2:5]) == ["chorus", "delay", "phaser"]
                                   for o in places), str(places[:2]))
    null("the rack before it had no EQ", ["plane", "phaser", "chorus", "delay", "reverb"] not in places)
    handle = p.evaluate("() => !!document.querySelector('#eqModule [data-fx-move]')")
    check("and it has no handle to move it by, as the Plane has none", handle is False)

    print("\n--- its switch ---")
    sw = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const pill = document.querySelector('.fx-on[data-fx-on="eq"]');
      const sum = () => document.querySelector('[data-fx-sum="eq"]').textContent;
      const knobs = () => ['eqLow', 'eqMid', 'eqHigh', 'eqLowFreq', 'eqMidFreq', 'eqMidWidth', 'eqHighFreq'].map((id) => el[id].value);
      const sent = () => { const g = genSettings(0); return [g.eqLow, g.eqMid, g.eqHigh]; };
      restore({}); await wait(30); paintRack();
      const fresh = { on: fxOn('eq'), pill: pill.getAttribute('aria-pressed'), sum: sum(), sent: sent() };
      pill.click(); await wait(30);
      const start = { knobs: knobs(), echo: [echo.eqLow, echo.eqMid, echo.eqHigh], sent: sent(), on: fxOn('eq'), sum: sum(),
                      pill: pill.getAttribute('aria-pressed') };
      // Away from the start, with a frequency and the width moved too.
      for (const [id, v] of [['eqLow', -45], ['eqMid', 20], ['eqHigh', 70], ['eqMidFreq', 30], ['eqMidWidth', 25]]) setControl(id, v);
      const set = { knobs: knobs(), sent: sent() };
      pill.click(); await wait(30);
      const off = { knobs: knobs(), sent: sent(), on: fxOn('eq'), sum: sum(), pill: pill.getAttribute('aria-pressed') };
      pill.click(); await wait(30);
      const back = { knobs: knobs(), sent: sent(), on: fxOn('eq') };
      // Off, another sound loaded, on: the start again, not what this sound kept.
      pill.click(); await wait(30);
      restore({}); paintRack();
      pill.click(); await wait(30);
      const loaded = { knobs: knobs() };
      pill.click(); await wait(30);
      return { fresh, start, set, off, back, loaded };
    }""")
    print("    %s" % sw)
    check("fresh, it is off, says so, and sends nought", sw["fresh"] == {"on": False, "pill": "false", "sum": "Off", "sent": [0, 0, 0]},
          str(sw["fresh"]))
    check("with nothing kept, on is the start: low and high +3 dB, the mid alone, in the knobs, the page's state and what the engine is sent",
          sw["start"]["knobs"][:3] == ["30", "0", "30"] and sw["start"]["echo"] == [3, 0, 3] and sw["start"]["sent"] == [3, 0, 3]
          and sw["start"]["on"] and sw["start"]["pill"] == "true", str(sw["start"]))
    check("and its line says so, each band where it acts", sw["start"]["sum"] == "low +3.0 dB at 160 Hz · high +3.0 dB at 4.0 kHz",
          sw["start"]["sum"])
    check("off takes the three gains to nought, in the knobs and the engine, and leaves where they act",
          sw["off"]["knobs"] == ["0", "0", "0"] + sw["set"]["knobs"][3:] and sw["off"]["sent"] == [0, 0, 0]
          and not sw["off"]["on"] and sw["off"]["sum"] == "Off", str(sw["off"]))
    check("on puts back what it kept, not the start", sw["back"]["knobs"] == sw["set"]["knobs"]
          and sw["back"]["sent"] == [-4.5, 2, 7] and sw["back"]["on"], str(sw["back"]))
    null("what it kept is not the start", sw["set"]["knobs"][:3] != ["30", "0", "30"])
    check("off, another sound loaded and on again is the start, not what the first sound kept",
          sw["loaded"]["knobs"][:3] == ["30", "0", "30"], str(sw["loaded"]))

    print("\n--- its readings, against the engine's own fields ---")
    rd = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      restore({}); await wait(30);
      const out = [];
      for (const [id, v] of [['eqLowFreq', 0], ['eqLowFreq', 50], ['eqLowFreq', 100], ['eqMidFreq', 50], ['eqMidFreq', 100],
                             ['eqHighFreq', 50], ['eqHighFreq', 100], ['eqMidWidth', 2], ['eqMidWidth', 40]]) {
        setControl(id, v);
        const g = genSettings(0);
        out.push([id, v, el[id + 'Value'].textContent, g.eqLowHz, g.eqMidHz, g.eqHighHz, g.eqMidWidth]);
      }
      restore({});
      return out;
    }""")
    print("    %s" % rd)
    want = [("40 Hz", 3, 40), ("160 Hz", 3, 160), ("640 Hz", 3, 640), ("1.0 kHz", 4, 1000), ("8.0 kHz", 4, 8000),
            ("4.0 kHz", 5, 4000), ("16.0 kHz", 5, 16000), ("0.2 oct", 6, 0.2), ("4.0 oct", 6, 4)]
    misses = [(r, w) for r, w in zip(rd, want) if r[2] != w[0] or abs(r[w[1]] - w[2]) > 1e-9 * w[2]]
    check("each knob's ends and middle read and are sent as their octave laws say: 40, 160, 640 Hz; 1 and 8 kHz; 4 and 16 kHz; 0.2 to 4 octaves",
          not misses and len(rd) == 9, str(misses[:2]))
    check("and not a linear law, which would put the low knob's middle at 340 Hz", abs(rd[1][3] - 340) > 100)

    print("\n--- a setup, there and back ---")
    rt = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      restore({}); await wait(30);
      const plain = encodeSetup(snapshot()), plainFields = Object.keys(decodeSetup(plain)).filter((k) => /^b?[eE]q/.test(k));
      const set = { eqLow: -60, eqLowFreq: 20, eqMid: 45, eqMidFreq: 70, eqMidWidth: 33, eqHigh: 95, eqHighFreq: 85 };
      for (const [id, v] of Object.entries(set)) setControl(id, v);
      const code = encodeSetup(snapshot());
      const engine = () => { const g = genSettings(0); return [g.eqLow, g.eqLowHz, g.eqMid, g.eqMidHz, g.eqMidWidth, g.eqHigh, g.eqHighHz]; };
      const before = engine();
      restore({}); await wait(30);
      const cleared = engine();
      restore(decodeSetup(code)); await wait(30);
      const back = { knobs: Object.keys(set).map((id) => Number(el[id].value)), engine: engine() };
      // A code with no EQ over an EQ that is on: nought, as a code from before the EQ.
      restore({ freq: 330 }); await wait(30);
      const old = engine();
      restore({});
      return { plainFields, set: Object.values(set), before, cleared, back, old, coded: decodeSetup(code) };
    }""")
    print("    %s" % {k: v for k, v in rt.items() if k != "coded"})
    check("a default EQ writes no field into a code", rt["plainFields"] == [], str(rt["plainFields"]))
    check("every field set away from its default comes back, in the knobs and in the engine",
          rt["back"]["knobs"] == rt["set"] and rt["back"]["engine"] == rt["before"] and all(rt["coded"][k] == v for k, v in
          zip(["eqLow", "eqLowFreq", "eqMid", "eqMidFreq", "eqMidWidth", "eqHigh", "eqHighFreq"], rt["set"])), str(rt["back"]))
    null("the restore between really cleared it", rt["cleared"] != rt["before"] and rt["cleared"][0] == 0)
    check("a code with no EQ, loaded over one that is on, is an EQ at nought", rt["old"][0] == 0 and rt["old"][2] == 0
          and rt["old"][5] == 0, str(rt["old"]))

    print("\n--- the hands ---")
    hd = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const click = (id) => document.getElementById(id).click();
      restore(BASE_SETUP); setScreenKeys(true); setMidiMode('poly');
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      click('editHandA'); await wait(30);
      setControl('eqLow', 20);
      const linkedBoth = [echo.eqLow, echoB.eqLow, genSettings(0).eqLow, genSettings(1).eqLow];
      setLink('eq', false);
      click('editHandB'); await wait(30);
      setControl('eqLow', -80); setControl('eqHighFreq', 90);
      const upper = { a: [echo.eqLow, echo.eqHighPos], b: [echoB.eqLow, echoB.eqHighPos], knob: el.eqLow.value,
                      gen: [genSettings(0).eqLow, genSettings(1).eqLow], own: genSettings(1).timeOwn };
      click('editHandA'); await wait(30);
      const lowerKnob = el.eqLow.value;
      const snap = snapshot(), code = encodeSetup(snap);
      setLink('eq', true);
      const relinked = [echo.eqLow, echoB.eqLow];
      restore(decodeSetup(code)); await wait(30);
      const reloaded = { own: !linked('eq'), b: [echoB.eqLow, echoB.eqHighPos], a: echo.eqLow };
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change'));
      setScreenKeys(false); restore({});
      return { linkedBoth, upper, lowerKnob, fields: [snap.bEqLow, snap.bEqHighFreq], relinked, reloaded };
    }""")
    print("    %s" % hd)
    check("linked, a knob writes both hands, in the page and the engine", hd["linkedBoth"] == [2, 2, 2, 2], str(hd["linkedBoth"]))
    check("unlinked, the upper hand's knobs write its own EQ and leave the lower's",
          hd["upper"]["b"] == [-8, 90] and hd["upper"]["a"] == [2, 50] and hd["upper"]["gen"] == [2, -8], str(hd["upper"]))
    check("and the generator is told the EQ is the upper hand's own (timeOwn's bit 16)", (hd["upper"]["own"] & 16) == 16,
          str(hd["upper"]["own"]))
    null("the lower hand's knob shows the lower's, not the upper's", hd["lowerKnob"] == "20")
    check("the upper hand's own goes into the code", hd["fields"] == [-80, 90], str(hd["fields"]))
    check("linked again from the lower, the two are one", hd["relinked"] == [2, 2], str(hd["relinked"]))
    check("and the code loads the upper hand's own again, unlinked", hd["reloaded"] == {"own": True, "b": [-8, 90], "a": 2},
          str(hd["reloaded"]))

    print("\n--- the tab's line ---")
    line = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      restore({}); await wait(30);
      const dry = TAB_LINES.space();
      setControl('eqMid', -30); setControl('delayMix', 20);
      const on = TAB_LINES.space();
      restore({});
      return { dry, on };
    }""")
    check("Space & Memory's line names the EQ when it is on, in the rack's order", line["on"] == "EQ · delay"
          and line["dry"] == "Dry", str(line))
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the EQ holds")
