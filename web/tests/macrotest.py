"""Stage L's macros, and the morph between two sets of sliders.

Not morphtest.py, which is the shape morph - sine through square - and
which this file once overwrote for sharing the word.

Against the way each would fail:

- a macro that reaches one control, or none: one knob routed to two, a
  picture's rotation and the generator's pitch, moves both, by the amounts
  routed - an octave at full, a fifth-and-a-bit at half - and at rest moves
  neither, not by a hair;
- a name that does not stick, or breaks a code: renamed, the source is called
  that everywhere; a bar in it or an empty one comes back safe; a code
  carries names and knobs, and a code without them brings the defaults;
- a morph that is a straight line where it should not be, or reaches what it
  should not: halfway between 220 and 880 is 440, not 550; the amplitude is
  halfway; the generator hears both; a menu set differently in A and B is
  left alone; the knobs, the fader and where a file is up to are never
  stored;
- a morph that fights the hand: at rest it leaves a slider the hand moved,
  and only moving the fader takes it back;
- a fader the matrix cannot drive: a macro on it moves every slider;
- a morph that outlives its sound, or is lost with it: a preset clears it; a
  code brings both ends back exactly, and short.
"""
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

STUB = """
  window.__wait = (ms) => new Promise((r) => setTimeout(r, ms));
  window.__set = (id, v, kind) => { el[id].value = String(v); el[id].dispatchEvent(new Event(kind || 'input')); };
  // The generator's pitch as drawn: upward crossings of lane one over a
  // tenth of a second, the generator silent so it runs on this thread.
  window.__pitch = async () => {
    await __wait(250);
    const w = state.source.getLatestWindow(8820)[0], rate = state.source.sampleRate || 44100;
    let ups = 0;
    for (let i = 1; i < w.length; i++) if (w[i - 1] <= 0 && w[i] > 0) ups++;
    return ups * rate / w.length;
  };
"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.add_init_script(STUB)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    print("\n--- a macro ---")
    fan = p.evaluate("""async () => {
      __set('shape', 'sine', 'change'); __set('freq', 220);
      state.modRoutings = [{ sourceId: 'macro.1', destId: 'view.rotate', amount: 0.5 },
                           { sourceId: 'macro.1', destId: 'gen.freq', amount: 1 }];
      touchRoutings();
      const at = async (k) => { __set('macro1', k); const hz = await __pitch();
        return { hz, rotate: state.rotateMod, value: MOD_SOURCES.get('macro.1').value() }; };
      const out = { rest: await at(0), half: await at(50), full: await at(100),
                    reading: el.macro1Value.textContent, picked: selectedSource };
      __set('macro1', 0); state.modRoutings = []; touchRoutings();
      return out;
    }""")
    print("    %s" % fan)
    check("one macro routed to two controls moves both: at full an octave and half a turn",
          abs(fan["full"]["hz"] - 440) < 8 and abs(fan["full"]["rotate"] - 0.5) < 1e-9
          and fan["reading"] == "100%", "%.1f Hz, %.3f" % (fan["full"]["hz"], fan["full"]["rotate"]))
    check("at half, half an octave: the knob is a value, not a switch",
          abs(fan["half"]["hz"] - 220 * 2 ** 0.5) < 8 and abs(fan["half"]["rotate"] - 0.25) < 1e-9,
          "%.1f Hz, %.3f" % (fan["half"]["hz"], fan["half"]["rotate"]))
    check("and at rest it moves nothing, not by a hair: a knob, not an oscillator",
          fan["rest"]["value"] == 0 and fan["rest"]["rotate"] == 0 and abs(fan["rest"]["hz"] - 220) < 6,
          str(fan["rest"]))
    check("moving the knob chooses the macro, so the tab says where it goes", fan["picked"] == "macro.1",
          fan["picked"])

    named = p.evaluate("""() => {
      const name = (k, v) => { el['macroName' + k].value = v; el['macroName' + k].dispatchEvent(new Event('change')); };
      name(1, 'Open | up'); name(2, '   '); name(3, 'Swell');
      selectSource('macro.3');
      const shown = el.srcDetailGroup.textContent.includes('Swell');
      __set('macro3', 40);
      const code = snapshot();
      const out = { labels: [1, 2, 3, 4].map((k) => MOD_SOURCES.get('macro.' + k).label), shown,
                    code: [code.macroNames, code.mac3], field: el.macroName2.value };
      // A code without them: every macro at rest with its own name.
      restore({});
      out.bare = { labels: [1, 2, 3].map((k) => MOD_SOURCES.get('macro.' + k).label), mac3: macros[2].value };
      restore(code);
      out.back = { labels: [1, 2, 3].map((k) => MOD_SOURCES.get('macro.' + k).label), mac3: macros[2].value,
                   knob: el.macro3.value };
      const hit = searchEntries().find((e) => e.kind === 'source' && e.id === 'macro.3');
      out.search = hit ? hit.crumb : null;
      out.grid = !!document.querySelector('#srcGrid [data-family="macros"]');
      restore({});
      return out;
    }""")
    print("    %s" % named)
    check("a renamed macro is called that everywhere; a bar is taken out and an empty name comes back as the default",
          named["labels"] == ["Open  up", "Macro 2", "Swell", "Macro 4"] and named["shown"]
          and named["field"] == "Macro 2", str(named["labels"]))
    check("a code carries the names and the knobs, and a code without them brings the defaults at rest",
          named["code"] == ["Open  up|Macro 2|Swell|Macro 4", 40]
          and named["bare"] == {"labels": ["Macro 1", "Macro 2", "Macro 3"], "mac3": 0}
          and named["back"] == {"labels": ["Open  up", "Macro 2", "Swell"], "mac3": 0.4, "knob": "40"},
          "%s / %s / %s" % (named["code"], named["bare"], named["back"]))
    check("macros are found by search under Sources, and have the Macros section rather than a row in the grid",
          named["search"] == "Sources › Macros" and named["grid"] is False,
          "%s, grid row %s" % (named["search"], named["grid"]))

    print("\n--- the morph ---")
    blend = p.evaluate("""async () => {
      const out = {};
      __set('shape', 'saw', 'change'); __set('freq', 220); __set('amp', 55);
      el.morphStoreA.click();
      out.stored = { pos: el.morphPos.value, a: el.morphStoreA.getAttribute('aria-pressed'),
                     b: el.morphStoreB.getAttribute('aria-pressed'), note: el.morphNote.textContent };
      __set('freq', 880); __set('amp', 100); __set('shape', 'square', 'change');
      el.morphStoreB.click();
      out.both = { pos: el.morphPos.value, b: el.morphStoreB.getAttribute('aria-pressed'),
                   note: el.morphNote.textContent, moving: morphMoving() };
      out.kept = MORPH_IDS.filter((id) => ['macro1', 'macro2', 'macro3', 'macro4', 'morphPos', 'fileSeek',
                                          'keysVelocity', 'align'].includes(id));
      out.has = ['freq', 'vcfCut', 'delayMix', 'crossX', 'timebase'].every((id) => MORPH_IDS.includes(id));
      __set('morphPos', 50); await __wait(120);
      out.half = { freq: Number(el.freq.value), amp: Number(el.amp.value), genFreq: genSettings().freq,
                   genAmp: genSettings().amp, shape: el.shape.value };
      __set('morphPos', 0); await __wait(120);
      out.zero = { freq: Number(el.freq.value), amp: Number(el.amp.value), shape: el.shape.value };
      // The hand, with the fader at rest.
      __set('morphPos', 50); await __wait(120);
      __set('amp', 20); await __wait(200);
      out.hand = Number(el.amp.value);
      __set('morphPos', 60); await __wait(120);
      out.moved = Number(el.amp.value);
      return out;
    }""")
    print("    %s" % blend)
    check("storing an end puts the fader there, marks it stored, and the note says what is left to do",
          blend["stored"] == {"pos": "0", "a": "true", "b": "false",
                              "note": "A is stored. Change the sound and store B."}
          and blend["both"]["pos"] == "100" and blend["both"]["b"] == "true", str(blend["stored"]))
    check("and with both, it counts what moves: two sliders, and the menu is not one of them",
          blend["both"]["moving"] == ["freq", "amp"]
          and blend["both"]["note"] == "2 sliders move between A and B. Menus and switches stay as they are.",
          str(blend["both"]))
    check("halfway, the pitch is an octave from each end, 440 not 550, and the amplitude is halfway",
          blend["half"]["freq"] == 440 and blend["half"]["amp"] == 78, str(blend["half"]))
    check("and the generator hears it, as it hears a hand on the slider",
          blend["half"]["genFreq"] == 440 and abs(blend["half"]["genAmp"] - 0.78) < 1e-9,
          "%s, %s" % (blend["half"]["genFreq"], blend["half"]["genAmp"]))
    check("at nought it is A, but a menu set differently in A and B stays where it is",
          blend["zero"] == {"freq": 220, "amp": 55, "shape": "square"}, str(blend["zero"]))
    check("the knobs, the fader, where a file is up to, the keys' strike and the rack's alignment are never stored",
          blend["kept"] == [] and blend["has"], "%s, %s" % (blend["kept"], blend["has"]))
    check("at rest it leaves a slider the hand has moved, and moving the fader takes it back",
          blend["hand"] == 20 and blend["moved"] == round(55 + 45 * 0.6), "%s then %s" % (blend["hand"], blend["moved"]))

    driven = p.evaluate("""async () => {
      __set('morphPos', 0); await __wait(120);
      state.modRoutings = [{ sourceId: 'macro.1', destId: 'morph.pos', amount: 1 }]; touchRoutings();
      __set('macro1', 50); await __wait(150);
      const half = { freq: Number(el.freq.value), pitch: await __pitch() };
      __set('macro1', 100); await __wait(150);
      const full = { freq: Number(el.freq.value), pitch: await __pitch() };
      __set('macro1', 0); await __wait(150);
      const back = Number(el.freq.value);
      state.modRoutings = []; touchRoutings();
      return { half, full, back };
    }""")
    print("    %s" % driven)
    check("a macro on the fader drives the morph: half is 440, full is B's 880, and the generator plays it",
          driven["half"]["freq"] == 440 and driven["full"]["freq"] == 880 and driven["back"] == 220
          and abs(driven["full"]["pitch"] - 880) < 15, str(driven))

    print("\n--- in a setup code ---")
    code = p.evaluate("""async () => {
      /* A slider A moved off its default and B left on it: the phase, 45 in
         A and 90 - where the page starts it - in B. Without one, B stored
         against the defaults and read back against A came out the same, and
         the mutation pass could not tell the two apart. */
      __set('morphPos', 0); await __wait(120);
      __set('phase', 45); el.morphStoreA.click();
      const phases = [morph.a.phase, morph.b.phase, Number(el.phase.defaultValue)];
      __set('morphPos', 30); await __wait(120);
      const a = JSON.stringify(morph.a), b = JSON.stringify(morph.b);
      const snap = snapshot(), text = encodeSetup(snap);
      // A preset has no morph, and loading one clears it.
      restore({ freq: 330 }); await __wait(120);
      __set('morphPos', 80); await __wait(120);
      const cleared = { a: morph.a, b: morph.b, freq: Number(el.freq.value), note: el.morphNote.textContent };
      restore(decodeSetup(text)); await __wait(150);
      const back = { a: JSON.stringify(morph.a) === a, b: JSON.stringify(morph.b) === b,
                     pos: el.morphPos.value, freq: Number(el.freq.value), amp: Number(el.amp.value) };
      __set('morphPos', 100); await __wait(120);
      back.toB = Number(el.freq.value);
      // Nothing different: nothing to move.
      el.morphStoreA.click(); el.morphStoreB.click();
      const same = el.morphNote.textContent;
      restore({});
      return { length: text.length, cleared, back, same, phases };
    }""")
    print("    %s" % code)
    check("a preset clears the morph: the fader moves nothing and the note starts again",
          code["cleared"]["a"] is None and code["cleared"]["b"] is None and code["cleared"]["freq"] == 330
          and code["cleared"]["note"].startswith("Store A"), str(code["cleared"]))
    check("a code brings both ends back exactly, and the fader where it was, in under a kilobyte",
          code["back"]["a"] and code["back"]["b"] and code["back"]["pos"] == "30"
          and code["back"]["freq"] == round(220 * 4 ** 0.3) and code["back"]["toB"] == 880
          and code["length"] < 1000 and code["phases"] == [45, 90, 90],
          "%s, %d characters, phases %s" % (code["back"], code["length"], code["phases"]))
    check("and two ends that are the same say so", code["same"] == "A and B are the same: nothing to move.",
          code["same"])

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
