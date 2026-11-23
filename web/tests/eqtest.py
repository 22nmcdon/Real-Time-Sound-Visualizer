"""The EQ (17 Nov): three bands in the rack, after the Plane and before the
three the order moves.

What would go wrong, and what is checked for it:

- the EQ out of its place: it is second, after the Plane, under every one of
  the six orders, and has no handle to move it by. The null is the order the
  rack had before it (no EQ);
- a switch that changes its pill and not the sound. Since 17 Nov (the
  owner's) the EQ's switch is a field, eqOn, the one rack module's that is:
  on from fresh is flat - no starting smile - and opens the editor, and the
  engine is told it is in; off keeps the curve in the knobs and tells the
  engine it is out; on again is the same curve. The null is the old switch,
  which took the gains to nought: off here must leave them where they were;
- a code from before the field (version 11) losing its EQ, or a code made
  since turning one on: an old code is on where any gain was off nought,
  the upper hand's by its own gains, and a version-12 code with a gain and no
  eqOn is off (an off switch is the default, and left out of a code). The
  null is the rule read without the version, which would turn the new code on;
- the readings and the line lying about the octave law: since 22 Nov every
  band runs 20 Hz to 20 kHz on the cutoff's law, a thousand places, and
  starts at 160 Hz, 1 kHz and 4 kHz, held against the generator's own fields
  (eqLowHz and the rest), not against the page's arithmetic alone;
- a code from before that law (version 13) playing another frequency: every
  old place of each band and hand, through the page's decode (the compiled
  core's migrateSetup) and restore, is sent to the engine as the hertz the
  old law gave it, to a part in ten thousand million; a band left out of an
  old code with the EQ in it is its old middle. The null is the same places
  restored without the pass, as today's places, which play elsewhere;
- the deeper cut not reaching the sound: a gain's knob goes to -16 dB, is
  sent as -16, and past it is held there; and with the low shelf taken to
  20 kHz a held note's peak in the spectrum after the EQ falls by 16 dB to a
  hundredth of one. The null is the old floor, -12, which falls by 12;
- the cuts (23 Nov, the owner's five points) not reaching the sound, or
  reaching it at rest: a held note (220 Hz) under a low cut at 1 kHz falls
  by more than 20 dB and under a high cut at 1 kHz by less than half of
  one, and with both cuts at their ends - where every setup starts and
  every older code loads them - the note's peak is the EQ's without them,
  to the hundredth of a decibel. The nulls: the cuts were in, reading
  below; a code with no cut fields loads them at their ends, and a setup
  naming one does not. Their fields round trip, and the rack's line names
  a cut that is in;
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

    print("\n--- its switch, a field (17 Nov) ---")
    sw = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const pill = document.querySelector('.fx-on[data-fx-on="eq"]');
      const sum = () => document.querySelector('[data-fx-sum="eq"]').textContent;
      const knobs = () => ['eqLow', 'eqMid', 'eqHigh', 'eqLowFreq', 'eqMidFreq', 'eqMidWidth', 'eqHighFreq'].map((id) => el[id].value);
      const sent = () => { const g = genSettings(0); return [g.eqOn, g.eqLow, g.eqMid, g.eqHigh]; };
      restore({}); await wait(30); paintRack();
      const fresh = { on: fxOn('eq'), pill: pill.getAttribute('aria-pressed'), sum: sum(), sent: sent() };
      pill.click(); await wait(30);
      const start = { knobs: knobs(), echo: [echo.eqOn, echo.eqLow, echo.eqMid, echo.eqHigh], sent: sent(), on: fxOn('eq'), sum: sum(),
                      pill: pill.getAttribute('aria-pressed'), editor: eqEd.open };
      closeEqEditor();
      for (const [id, v] of [['eqLow', -45], ['eqMid', 20], ['eqHigh', 70], ['eqMidFreq', 30], ['eqMidWidth', 25]]) setControl(id, v);
      const set = { knobs: knobs(), sent: sent() };
      pill.click(); await wait(30);
      const off = { knobs: knobs(), sent: sent(), on: fxOn('eq'), sum: sum(), pill: pill.getAttribute('aria-pressed'), code: decodeSetup(encodeSetup(snapshot())) };
      // Moved from code while off - a setup, the morph, a host - it stays off: only a hand switches it on.
      setControl('eqLow', -40);
      const byCode = { on: el.eqOn.checked, sent: sent() };
      setControl('eqLow', -45);
      pill.click(); await wait(30);
      const back = { knobs: knobs(), sent: sent(), on: fxOn('eq'), editor: eqEd.open };
      closeEqEditor(); restore({});
      return { fresh, start, set, off, byCode, back };
    }""")
    print("    %s" % {k: v for k, v in sw.items()})
    check("fresh, it is off, says so, and the engine is told it is out", sw["fresh"] == {"on": False, "pill": "false", "sum": "Off", "sent": [False, 0, 0, 0]},
          str(sw["fresh"]))
    check("on from fresh is flat - no starting smile - in the knobs, the page's state and what the engine is sent, and it is in",
          sw["start"]["knobs"][:3] == ["0", "0", "0"] and sw["start"]["echo"] == [True, 0, 0, 0] and sw["start"]["sent"] == [True, 0, 0, 0]
          and sw["start"]["on"] and sw["start"]["pill"] == "true", str(sw["start"]))
    check("and its line says flat, and the editor opens", sw["start"]["sum"] == "flat" and sw["start"]["editor"], str(sw["start"]))
    check("off keeps the curve in the knobs and tells the engine it is out", sw["off"]["knobs"] == sw["set"]["knobs"]
          and sw["off"]["sent"] == [False, -4.5, 2, 7] and not sw["off"]["on"] and sw["off"]["sum"] == "Off", str(sw["off"]))
    null("the old switch took the gains to nought; these are not", sw["off"]["knobs"][:3] != ["0", "0", "0"])
    check("and a code made off says so by leaving eqOn out, with the curve in it", "eqOn" not in sw["off"]["code"] or sw["off"]["code"]["eqOn"] is False,
          str({k: v for k, v in sw["off"]["code"].items() if k.startswith("eq")}))
    check("a gain moved from code while off leaves it off", sw["byCode"] == {"on": False, "sent": [False, -4.0, 2, 7]}, str(sw["byCode"]))
    check("on again is the same curve, in", sw["back"]["knobs"] == sw["set"]["knobs"] and sw["back"]["sent"] == [True, -4.5, 2, 7]
          and sw["back"]["on"], str(sw["back"]))

    print("\n--- a code from before the field ---")
    old = p.evaluate("""() => {
      const code = (o) => btoa(JSON.stringify(o)).replace(/=+$/, '');
      const read = (o) => { const s = decodeSetup(code(o)); return { eqOn: s.eqOn, bEqOn: s.bEqOn, v: s.v }; };
      return {
        v11gain: read({ v: 11, eqLow: 30 }), v11mid: read({ v: 11, eqMid: -5 }), v11none: read({ v: 11, eqLowFreq: 20 }),
        v11b: read({ v: 11, bEqHigh: 20 }), v11bflat: read({ v: 11, eqLow: 30, bEqLow: 0, bEqLowFreq: 10 }),
        v12gain: read({ v: 12, eqLow: 30 }), v12on: read({ v: 12, eqOn: true }),
        version: SETUP_VERSION,
      };
    }""")
    print("    %s" % old)
    # At 12 or later: 13 since 18 Nov, the drawn envelopes' pass, which a version-12 code goes through on its way.
    check("the page and the core are at version 12 or later, and a version-12 code comes up at the current one",
          old["version"] >= 12 and old["v12gain"]["v"] == old["version"], str(old["version"]))
    check("a version-11 code with a gain off nought loads on, and the mid's counts too",
          old["v11gain"]["eqOn"] is True and old["v11mid"]["eqOn"] is True, str(old))
    check("a version-11 code with every gain at nought loads off, a frequency moved or not, and gains no field", old["v11none"]["eqOn"] is None, str(old["v11none"]))
    check("the upper hand's by its own gains, a gain it lacks the lower's",
          old["v11b"]["bEqOn"] is True and old["v11b"]["eqOn"] is None and old["v11bflat"]["bEqOn"] is False and old["v11bflat"]["eqOn"] is True,
          str([old["v11b"], old["v11bflat"]]))
    null("a version-12 code with a gain and no eqOn is off, which the rule read without the version would turn on",
         old["v12gain"]["eqOn"] in (False, None) and old["v12on"]["eqOn"] is True, str([old["v12gain"], old["v12on"]]))

    print("\n--- its readings, against the engine's own fields ---")
    rd = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      restore({}); await wait(30);
      const out = [];
      for (const [id, v] of [['eqLowFreq', 0], ['eqLowFreq', 301], ['eqLowFreq', 1000], ['eqMidFreq', 567], ['eqMidFreq', 0],
                             ['eqHighFreq', 767], ['eqHighFreq', 1000], ['eqMidWidth', 2], ['eqMidWidth', 40]]) {
        setControl(id, v);
        const g = genSettings(0);
        out.push([id, v, el[id + 'Value'].textContent, g.eqLowHz, g.eqMidHz, g.eqHighHz, g.eqMidWidth]);
      }
      restore({});
      return out;
    }""")
    print("    %s" % rd)
    law = lambda p: 20 * 1000 ** (p / 1000)
    want = [("20 Hz", 3, 20), ("160 Hz", 3, law(301)), ("20.0 kHz", 3, 20000), ("1.0 kHz", 4, law(567)), ("20 Hz", 4, 20),
            ("4.0 kHz", 5, law(767)), ("20.0 kHz", 5, 20000), ("0.2 oct", 6, 0.2), ("4.0 oct", 6, 4)]
    misses = [(r, w) for r, w in zip(rd, want) if r[2] != w[0] or abs(r[w[1]] - w[2]) > 1e-9 * w[2]]
    check("each band runs 20 Hz to 20 kHz and starts at 160 Hz, 1 kHz and 4 kHz, read and sent as the law says; the width 0.2 to 4 octaves",
          not misses and len(rd) == 9, str(misses[:2]))
    check("and each start within eight cents of 160 Hz, 1 kHz and 4 kHz, reading as them", all(abs(1200 * __import__("math").log2(rd[i][k] / hz)) < 8.1
          for i, k, hz in ((1, 3, 160), (3, 4, 1000), (5, 5, 4000))), str([rd[1][3], rd[3][4], rd[5][5]]))
    check("and not a linear law, which would put the low knob's start at 6 kHz", abs(rd[1][3] - 6034) > 1000)

    print("\n--- a code from before the whole range (version 13) ---")
    mg = p.evaluate("""async () => {
      const code = (o) => btoa(JSON.stringify(o)).replace(/=+$/, '');
      const AT = ['eqLowFreq', 'eqMidFreq', 'eqHighFreq'], HZ = ['eqLowHz', 'eqMidHz', 'eqHighHz'];
      const out = [];
      for (let k = 0; k < 3; k++) for (const pl of [0, 1, 17, 37.5, 50, 63, 99, 100, -5, 140]) {
        const o = { v: 13, eqOn: true, eqLow: 20, layers: 'layer', midiMode: 'poly', bPlane: true };
        o[AT[k]] = pl; o['b' + AT[k][0].toUpperCase() + AT[k].slice(1)] = 100 - pl;
        restore(decodeSetup(code(o)));
        const migrated = [genSettings(0)[HZ[k]], genSettings(1)[HZ[k]]];
        // The null: the same places taken as today's, with no pass.
        restore(Object.assign({}, o, { v: undefined }));
        out.push({ k, place: pl, migrated, unmigrated: [genSettings(0)[HZ[k]], genSettings(1)[HZ[k]]] });
      }
      restore(decodeSetup(code({ v: 13, eqOn: true, eqHigh: -30 })));
      const middles = HZ.map((h) => genSettings(0)[h]);
      restore({});
      return { out, middles };
    }""")
    OLD = [(40, 4), (125, 6), (1000, 4)]
    old_hz = lambda k, pl: OLD[k][0] * 2 ** (OLD[k][1] * max(0, min(100, pl)) / 100)
    worst = max(max(abs(r["migrated"][0] / old_hz(r["k"], r["place"]) - 1), abs(r["migrated"][1] / old_hz(r["k"], 100 - r["place"]) - 1)) for r in mg["out"])
    check("every old place of each band, the lower hand's and the upper's, between places and past the ends, is sent as the hertz "
          "the old law gave it (%d codes)" % len(mg["out"]), worst < 1e-10 and len(mg["out"]) == 30, "worst %.2e" % worst)
    check("an old code with the EQ in it and its bands left out plays them at their old middles, 160 Hz, 1 kHz and 4 kHz",
          all(abs(a - b) < 1e-9 * b for a, b in zip(mg["middles"], (160, 1000, 4000))), str(mg["middles"]))
    unm = min(abs(r["unmigrated"][0] / old_hz(r["k"], r["place"]) - 1) for r in mg["out"] if 0 < r["place"] < 100)
    null("the same places restored as today's, with no pass, play elsewhere: every one inside the old range misses by at least %.0f%%" % (100 * unm),
         unm > 0.05, "%.3f" % unm)

    print("\n--- the deeper cut, in the sound ---")
    cut = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      restore({}); setRunning(true); openEqEditor();
      setControl('eqLow', -160);
      const knob = { value: el.eqLow.value, reading: el.eqLowValue.textContent, sent: genSettings(0).eqLow };
      setControl('eqLow', -200);
      const past = { value: el.eqLow.value, sent: genSettings(0).eqLow };
      midiNoteOn(57, 100); await wait(800);
      const peak = () => { let m = -200; for (let i = 2; i < eqEd.spec.length; i++) m = Math.max(m, eqEd.spec[i]); return m; };
      const out = {};
      // The low shelf taken to 20 kHz, so a held note is wholly under it.
      for (const [name, on, g] of [['dry', false, 0], ['cut16', true, -160], ['cut12', true, -120]]) {
        setEqOn(on); setControl('eqLowFreq', 1000); setControl('eqLow', g); await wait(1200);
        out[name] = peak();
      }
      midiNoteOff(57); closeEqEditor(); restore({});
      return { knob, past, out };
    }""")
    print("    %s" % cut)
    check("the gains' knob goes to -16 dB, reads it, and the engine is sent -16; past it, it is held there",
          cut["knob"] == {"value": "-160", "reading": "−16.0 dB", "sent": -16} and cut["past"] == {"value": "-160", "sent": -16}, str(cut))
    fall = cut["out"]["cut16"] - cut["out"]["dry"]
    check("with the low shelf at 20 kHz, a held note's peak after the EQ falls by 16 dB (%.3f)" % fall, abs(fall + 16) < 0.01, str(cut["out"]))
    null("the old floor, -12, falls by 12, which that check would not pass", abs((cut["out"]["cut12"] - cut["out"]["dry"]) + 16) > 3.9,
         "%.3f" % (cut["out"]["cut12"] - cut["out"]["dry"]))

    print("\n--- the cuts, in the sound (23 Nov) ---")
    # A page of its own: the section before leaves a note's level a fifth of a decibel off on the one it used.
    q = b.new_page(viewport={"width": 1400, "height": 900})
    q.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    q.add_init_script(path=COMPILED_CORE)
    q.goto(f"file://{ART}/scope.html"); q.wait_for_timeout(700)
    if q.locator("#helpClose").is_visible(): q.locator("#helpClose").click()
    q.evaluate("() => { setView('bench'); setBenchTab('space'); }"); q.wait_for_timeout(300)
    cuts = q.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      // The Picture at nought: at its default the loop reshapes a held note, and its level drifts by a fifth of a decibel.
      restore({ pictureAmount: 0 }); setRunning(true); openEqEditor();
      const fresh = { knobs: ['eqCutLowFreq', 'eqCutLowQ', 'eqCutHighFreq', 'eqCutHighQ'].map((id) => el[id].value),
                      readings: [el.eqCutLowFreqValue.textContent, el.eqCutHighFreqValue.textContent],
                      sent: [genSettings(0).eqCutLowHz, genSettings(0).eqCutHighHz],
                      switches: EQ_ON_KEYS.map((k) => el[k].checked) };
      // A cut switched on acts at once (23 Nov, version 15): from its start, 30 Hz and 18 kHz, not its end.
      setEqBandOn(3, true); setEqBandOn(4, true);
      const atOnce = [genSettings(0).eqCutLowHz, genSettings(0).eqCutHighHz, eqHz(3, 59), eqHz(4, 985)];
      // The null: switched on where the cuts started before 15, at their ends, they are told their ends - out.
      setControl('eqCutLowFreq', 0); setControl('eqCutHighFreq', 1000);
      const atEnds = [genSettings(0).eqCutLowHz, genSettings(0).eqCutHighHz];
      midiNoteOn(57, 100); await wait(800);
      // The note's own bin and its neighbours, not the loudest anywhere: cut away, the note is not the spectrum's top.
      const bin = Math.round(220 / (eqRate() / FFT_SIZE));
      const peak = () => { let m = -200; for (let i = bin - 2; i <= bin + 2; i++) m = Math.max(m, eqEd.spec[i]); return m; };
      const out = { switch: {} };
      // Each with both cuts switched on (23 Nov) but the last: the low cut at 1 kHz switched off, which is out of the chain.
      for (const [name, on, low, high, lowOn] of [['off', false, 0, 1000, true], ['ends', true, 0, 1000, true], ['low1k', true, 566, 1000, true],
                                                  ['high1k', true, 0, 566, true], ['low1kOff', true, 566, 1000, false]]) {
        setEqOn(on); setControl('eqLow', 30); setControl('eqCutLowFreq', low); setControl('eqCutHighFreq', high);
        setEqBandOn(3, lowOn); setEqBandOn(4, true); await wait(1200);
        out[name] = peak(); out.switch[name] = el.eqOn.checked;
      }
      setEqBandOn(3, true);
      // With the EQ's shelf at nought too, so "ends" is the dry note: a check that the cuts at rest do nothing.
      setControl('eqLow', 0); setControl('eqCutLowFreq', 0); setControl('eqCutHighFreq', 1000); await wait(1200);
      out.endsFlat = peak();
      out.switch.endsFlat = el.eqOn.checked;
      setEqOn(false); await wait(1200); out.dry = peak(); out.switch.dry = el.eqOn.checked;
      midiNoteOff(57); closeEqEditor();
      const line = (() => { restore({}); setEqOn(true); setControl('eqCutLowFreq', 400); setControl('eqCutHighFreq', 800);
                            setEqBandOn(3, true); setEqBandOn(4, true); paintRack();
                            return document.querySelector('[data-fx-sum="eq"]').textContent; })();
      // The null: the same places with the cuts' switches off, which the line does not name.
      const lineOff = (() => { setEqBandOn(3, false); setEqBandOn(4, false); paintRack();
                               return document.querySelector('[data-fx-sum="eq"]').textContent; })();
      const code = (o) => btoa(JSON.stringify(o)).replace(/=+$/, '');
      restore(decodeSetup(code({ v: 13, eqOn: true, eqLow: 30 }))); const old = [genSettings(0).eqCutLowHz, genSettings(0).eqCutHighHz];
      restore(decodeSetup(code({ v: 14, eqOn: true, eqCutLowFreq: 400 }))); const named = [genSettings(0).eqCutLowHz, genSettings(0).eqCutHighHz];
      restore({});
      return { fresh, atOnce, atEnds, out, line, lineOff, old, named };
    }""")
    q.close()
    print("    %s" % cuts)
    o = cuts["out"]
    check("the EQ's switch where each reading wants it: off, on, on, on, on, on, off",
          o["switch"] == {"off": False, "ends": True, "low1k": True, "high1k": True, "low1kOff": True, "endsFlat": True, "dry": False},
          str(o["switch"]))
    check("fresh (version 15), both cuts start switched off at 30 Hz and 18 kHz - the knobs 59 and 985, reading so, the engine "
          "sent their ends, out - their Q 0.71, and the three bands' switches on",
          cuts["fresh"] == {"knobs": ["59", "71", "985", "71"], "readings": ["30 Hz", "18.0 kHz"], "sent": [20, 20000],
                            "switches": [False, True, True, True, False]}, str(cuts["fresh"]))
    a = cuts["atOnce"]
    check("a cut switched on acts at once: the engine is sent 30 Hz and 18 kHz, where they start", abs(a[0] - a[2]) < 1e-9
          and abs(a[1] - a[3]) < 1e-6 and 29 < a[0] < 31 and 17900 < a[1] < 18100, str(a))
    null("switched on at their ends, where they started before version 15, they are sent their ends: out, no change",
         cuts["atEnds"] == [20, 20000], str(cuts["atEnds"]))
    check("the low cut at 1 kHz switched off is out of the chain: the note is where both at their ends leave it, to a hundredth "
          "of a decibel (%.4f)" % (o["low1kOff"] - o["ends"]), abs(o["low1kOff"] - o["ends"]) < 0.01)
    check("a low cut at 1 kHz takes a held 220 Hz note down by more than 20 dB (%.1f)" % (o["low1k"] - o["ends"]), o["low1k"] - o["ends"] < -20)
    check("a high cut at 1 kHz leaves it within half a decibel (%.2f)" % (o["high1k"] - o["ends"]), abs(o["high1k"] - o["ends"]) < 0.5)
    check("both cuts at their ends do nothing: the EQ on and flat with them is the dry note, to a hundredth of a decibel (%.4f)"
          % (o["endsFlat"] - o["dry"]), abs(o["endsFlat"] - o["dry"]) < 0.01)
    null("and the shelf alone, which the cuts sat beside, did move it (%.2f), so the comparison could see a change" % (o["ends"] - o["off"]),
         abs(o["ends"] - o["off"]) > 0.5)
    check("an older code, which names no cut, loads both at their ends, out", cuts["old"] == [20, 20000], str(cuts["old"]))
    null("a code naming the low cut loads it in", cuts["named"][0] > 20 and cuts["named"][1] == 20000, str(cuts["named"]))
    check("the rack's line names each cut that is in", "cut below" in cuts["line"] and "cut above" in cuts["line"], cuts["line"])
    null("and neither when they are switched off at the same places", "cut" not in cuts["lineOff"], cuts["lineOff"])

    print("\n--- a setup, there and back ---")
    rt = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      restore({}); await wait(30);
      const plain = encodeSetup(snapshot()), plainFields = Object.keys(decodeSetup(plain)).filter((k) => /^b?[eE]q/.test(k));
      const set = { eqLow: -160, eqLowFreq: 120, eqMid: 45, eqMidFreq: 700, eqMidWidth: 33, eqHigh: 95, eqHighFreq: 1000,
                    eqCutLowFreq: 250, eqCutLowQ: 300, eqCutHighFreq: 850, eqCutHighQ: 60 };
      for (const [id, v] of Object.entries(set)) setControl(id, v);
      setEqOn(true);
      // The bands' switches (23 Nov): both cuts on and the mid off, each away from where it starts.
      setEqBandOn(3, true); setEqBandOn(4, true); setEqBandOn(1, false);
      const switches = () => EQ_ON_KEYS.map((k) => el[k].checked);
      const swSet = switches();
      const code = encodeSetup(snapshot());
      const engine = () => { const g = genSettings(0); return [g.eqLow, g.eqLowHz, g.eqMid, g.eqMidHz, g.eqMidWidth, g.eqHigh, g.eqHighHz, g.eqOn,
                                                                g.eqCutLowHz, g.eqCutLowQ, g.eqCutHighHz, g.eqCutHighQ]; };
      const before = engine();
      restore({}); await wait(30);
      const cleared = engine();
      restore(decodeSetup(code)); await wait(30);
      const back = { knobs: Object.keys(set).map((id) => Number(el[id].value)), engine: engine(), switches: switches() };
      // A code with no EQ over an EQ that is on: nought, as a code from before the EQ.
      restore({ freq: 330 }); await wait(30);
      const old = engine();
      restore({});
      return { plainFields, set: Object.values(set), before, cleared, back, old, coded: decodeSetup(code), swSet };
    }""")
    print("    %s" % {k: v for k, v in rt.items() if k != "coded"})
    check("a default EQ writes no field into a code", rt["plainFields"] == [], str(rt["plainFields"]))
    check("every field set away from its default comes back, in the knobs and in the engine",
          rt["back"]["knobs"] == rt["set"] and rt["back"]["engine"] == rt["before"] and all(rt["coded"][k] == v for k, v in
          zip(["eqLow", "eqLowFreq", "eqMid", "eqMidFreq", "eqMidWidth", "eqHigh", "eqHighFreq", "eqCutLowFreq", "eqCutLowQ",
               "eqCutHighFreq", "eqCutHighQ"], rt["set"]))
          and rt["coded"].get("eqOn") is True and rt["back"]["engine"][7] is True, str(rt["back"]))
    check("and each band's switch comes back (both cuts on, the mid off), the mid told nought while it keeps its gain",
          rt["swSet"] == [True, True, False, True, True] and rt["back"]["switches"] == rt["swSet"]
          and rt["coded"].get("eqMidOn") is False and rt["coded"].get("eqCutLowOn") is True and rt["back"]["engine"][2] == 0
          and rt["back"]["knobs"][2] == 45, str((rt["swSet"], rt["back"]["switches"])))
    null("the restore between really cleared it", rt["cleared"] != rt["before"] and rt["cleared"][0] == 0)
    check("a code with no EQ, loaded over one that is on, is an EQ at nought, and off", rt["old"][0] == 0 and rt["old"][2] == 0
          and rt["old"][5] == 0 and rt["old"][7] is False, str(rt["old"]))

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
      setControl('eqLow', -80); setControl('eqHighFreq', 900);
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
          hd["upper"]["b"] == [-8, 900] and hd["upper"]["a"] == [2, 767] and hd["upper"]["gen"] == [2, -8], str(hd["upper"]))
    check("and the generator is told the EQ is the upper hand's own (timeOwn's bit 16)", (hd["upper"]["own"] & 16) == 16,
          str(hd["upper"]["own"]))
    null("the lower hand's knob shows the lower's, not the upper's", hd["lowerKnob"] == "20")
    check("the upper hand's own goes into the code", hd["fields"] == [-80, 900], str(hd["fields"]))
    check("linked again from the lower, the two are one", hd["relinked"] == [2, 2], str(hd["relinked"]))
    check("and the code loads the upper hand's own again, unlinked", hd["reloaded"] == {"own": True, "b": [-8, 900], "a": 2},
          str(hd["reloaded"]))

    print("\n--- the tab's line ---")
    line = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      restore({}); await wait(30);
      const dry = TAB_LINES.space();
      setEqOn(true); setControl('eqMid', -30); setControl('delayMix', 20);
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
