"""The morph between two sets of sliders, and the macros' going.

Not morphtest.py, which is the shape morph - sine through square. This was
macrotest.py, Stage L's macros and the morph, until P8d cut the macros (the
plugin's host knobs are the loop's own controls now); the morph's checks are
kept whole, and the macros' are replaced by checks that they have gone and
that an old code naming them loads as its nearest survivor.

Against the way each would fail:

- a morph that is a straight line where it should not be, or reaches what it
  should not: halfway between 220 and 880 is 440, not 550; the amplitude is
  halfway; the generator hears both; a menu set differently in A and B is
  left alone; the fader, the keys' strike and the Picture amount are never
  stored;
- a morph that fights the hand: at rest it leaves a slider the hand moved,
  and only moving the fader takes it back;
- a fader the matrix cannot drive: a source on it moves every slider;
- a morph that outlives its sound, or is lost with it: a preset clears it; a
  code brings both ends back exactly, and short;
- macros half gone: a knob, a source, a family or a preset section left
  behind, or an old code whose macro routes are kept by name, moving nothing.
"""
import os
from playwright.sync_api import sync_playwright
import corpus

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
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    print("\n--- the macros, gone ---")
    gone = p.evaluate("""() => {
      const ids = Array.from(document.querySelectorAll('[id]')).map((e) => e.id).filter((id) => /^macro/i.test(id));
      const sources = Array.from(MOD_SOURCES.keys()).filter((id) => id.startsWith('macro.'));
      const families = SOURCE_FAMILIES.map(([id]) => id);
      const sections = PRESETS.map(([name]) => name);
      const morphHome = homeOf(el.morphGroup), title = el.morphGroup.querySelector('.menu-title').textContent;
      // A version-5 code with the macros set, named and routed, read the way
      // a pasted code is read, and loaded.
      const old = { v: 5, mac1: 40, mac3: 100, macroNames: 'Brighten|Grit|Space|Swirl', freq: 330,
                    mod: 'macro.1>gen.vcf@0.700;lfo1>gen.amp@0.400;macro.2>gen.drive@0.800' };
      /* Through both codecs: the site's reads codes with the compiled core
         (setupCodec.kind "wasm"), so a check on decodeSetup alone never ran
         the page's own pass - the first null below went green with that pass
         taken out. The page's own is decodeSetupHere. */
      const read = decodeSetup(btoa(JSON.stringify(old)));
      const readHere = decodeSetupHere(btoa(JSON.stringify(old)));
      const codec = setupCodec.kind;
      restore(read);
      const kept = state.modRoutings.map((r) => r.sourceId + '>' + r.destId);
      // The null: the same code stamped version 6 keeps what it says, so a
      // pass that did nothing would read the same as this.
      const stamped = decodeSetup(btoa(JSON.stringify(Object.assign({}, old, { v: 6 }))));
      const stampedHere = decodeSetupHere(btoa(JSON.stringify(Object.assign({}, old, { v: 6 }))));
      restore({});
      return { ids, sources, families, sections, morphHome, title, read, readHere, codec, kept, stamped, stampedHere,
               version: SETUP_VERSION };
    }""")
    print("    %s" % {k: gone[k] for k in ("ids", "sources", "morphHome", "title", "kept", "version")})
    check("no macro knob, name, source, family or preset section is left on the page",
          gone["ids"] == [] and gone["sources"] == [] and "macros" not in gone["families"]
          and "Macros" not in gone["sections"], str(gone["ids"] + gone["sources"]))
    check("the morph keeps a section of its own, in the header's Perform menu since F3", gone["morphHome"] == "perform"
          and gone["title"] == "Morph", "%s %s" % (gone["morphHome"], gone["title"]))
    # Up to the current version, whatever that is now: the version-7 and -8
    # passes (the latch, the kaleidoscope) came after this was written and
    # leave a code with none of their fields as it was.
    migrated = lambda r: (r["v"] == gone["version"] and r["freq"] == 330 and r["mod"] == "lfo1>gen.amp@0.400"
                          and not any(k in r for k in ("mac1", "mac3", "macroNames")))
    check("a version-5 code loses the macros' values, names and routes, and keeps the rest as written - "
          "read by the site's compiled codec and by the page's own",
          gone["version"] >= 7 and gone["codec"] == "wasm" and migrated(gone["read"]) and migrated(gone["readHere"])
          and gone["kept"] == ["lfo1>gen.amp"], "%s / %s / %s" % (gone["read"], gone["readHere"], gone["kept"]))
    check("null: the same code marked version 6 keeps its macro routes in both, so the pass is what took them",
          all("macro.1>gen.vcf@0.700" in r["mod"] and r.get("mac1") == 40 for r in (gone["stamped"], gone["stampedHere"])),
          "%s / %s" % (gone["stamped"], gone["stampedHere"]))

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
      out.kept = MORPH_IDS.filter((id) => ['morphPos', 'keysVelocity', 'pictureAmount'].includes(id));
      out.has = ['freq', 'vcfCut', 'delayMix', 'planeRadius', 'timebase'].every((id) => MORPH_IDS.includes(id));
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
          # In the page's order, which since G7 has Level in the Generator, before Frequency on Ink.
          blend["both"]["moving"] == ["amp", "freq"]
          and blend["both"]["note"] == "2 sliders move between A and B. Menus and switches stay as they are.",
          str(blend["both"]))
    check("halfway, the pitch is an octave from each end, 440 not 550, and the amplitude is halfway",
          blend["half"]["freq"] == 440 and blend["half"]["amp"] == 78, str(blend["half"]))
    check("and the generator hears it, as it hears a hand on the slider",
          blend["half"]["genFreq"] == 440 and abs(blend["half"]["genAmp"] - 0.78) < 1e-9,
          "%s, %s" % (blend["half"]["genFreq"], blend["half"]["genAmp"]))
    check("at nought it is A, but a menu set differently in A and B stays where it is",
          blend["zero"] == {"freq": 220, "amp": 55, "shape": "square"}, str(blend["zero"]))
    check("the fader, the keys' strike and the Picture amount are never stored",
          blend["kept"] == [] and blend["has"], "%s, %s" % (blend["kept"], blend["has"]))
    check("at rest it leaves a slider the hand has moved, and moving the fader takes it back",
          blend["hand"] == 20 and blend["moved"] == round(55 + 45 * 0.6), "%s then %s" % (blend["hand"], blend["moved"]))

    # A note held in Mono, so the pitch is the slider's: the site waits for a
    # note since 10 Nov, and this heard the tone it drew with none.
    corpus.held_tone(p)
    driven = p.evaluate("""async () => {
      /* A source with nothing behind it but a value this suite sets - what a
         macro was to the matrix, until P8d. */
      window.__hand = 0;
      if (!MOD_SOURCES.has('hand.1')) registerSource({ id: 'hand.1', label: 'Hand', ink: 'ch2', bipolar: false,
        family: 'controllers', description: "This suite's own source.", order: 90, value: () => window.__hand });
      __set('morphPos', 0); await __wait(120);
      state.modRoutings = [{ sourceId: 'hand.1', destId: 'morph.pos', amount: 1 }]; touchRoutings();
      window.__hand = 0.5; await __wait(150);
      const half = { freq: Number(el.freq.value), pitch: await __pitch() };
      window.__hand = 1; await __wait(150);
      const full = { freq: Number(el.freq.value), pitch: await __pitch() };
      window.__hand = 0; await __wait(150);
      const back = Number(el.freq.value);
      state.modRoutings = []; touchRoutings();
      return { half, full, back };
    }""")
    print("    %s" % driven)
    # And let go, since a held note sets the pitch a setup loaded after it names.
    p.evaluate("() => midiPanic()")
    check("a source on the fader drives the morph: half is 440, full is B's 880, and the generator plays it",
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
