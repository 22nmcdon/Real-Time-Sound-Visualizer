"""The preset library and its browser.

What would go wrong, and what is checked for it:

- a preset that quietly does less than it says: every field it names must
  come back out of a snapshot with the value it names. A key spelt wrong is
  not in the snapshot, and a value outside its control's range comes back
  clamped, so either fails here - where otherwise the preset would load,
  look fine and not be what its description says;
- a preset that is silent: every generator preset sounds on the tone,
  unless its description says it waits for a key;
- two presets that are the same preset, a preset or a section with nothing
  to say about itself;
- the bank's shape (P8g and P8h of web/docs/making-it-one-instrument.md):
  two headings, Settled then Breathing, a split under each, Settled with the
  Picture amount at nought and Breathing with the loop at work, no preset
  naming the latch that was cut - and every preset naming the Picture
  amount, since one that did not would inherit whatever the last one set.
  Whether each preset does what its heading says is measured on the sound,
  in honestytest.py;
- the browser: it opens on the heading in use, a menu of one section has no
  rail, New goes back to the base the instrument opens on, a card loads and leaves it open, Enter and a double-click load and
  close, the arrows move between cards by rows and columns, search looks
  across headings, saved setups have a menu, moving a control says Custom,
  the page's own keys stand aside while it is open, and it says when a
  preset cannot be heard.
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


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    print("\n--- every preset is what it says ---")
    report = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      // Read on the way in only: the old two-oscillator enum becomes a
      // routing, and `modtest.py` holds that translation.
      const legacy = new Set(['l0d', 'l1d', 'l0a', 'l1a']);
      const wrong = [], silent = [], snaps = new Map(), noBlurb = [];
      for (const [section, entries, kind] of PRESETS) {
        for (const [name, setup, blurb] of entries) {
          applyPreset('b:' + name);
          const snap = snapshot();
          for (const key of Object.keys(setup)) {
            if (legacy.has(key)) continue;
            // A lane the source has not got: "Bands, low against high" names
            // the band split's third, and the tone has two. It falls back,
            // rightly, and the band split's own test holds the real thing.
            if ((key === 'xy0' || key === 'xy1') && setup[key] >= state.channels.length) continue;
            if (!(key in snap)) { wrong.push([name, key, 'not a setup field']); continue; }
            if (snap[key] !== setup[key]) wrong.push([name, key, setup[key], snap[key]]);
          }
          if (!blurb || blurb.length < 20) noBlurb.push(name);
          const key = JSON.stringify(snap);
          if (snaps.has(key)) wrong.push([name, 'the same as', snaps.get(key)]);
          snaps.set(key, name);
          if (kind === 'generator') {
            await wait(260);
            const w = state.source.getLatestWindow(4410);
            let peak = 0, finite = true;
            for (const ch of w) for (let i = 0; i < ch.length; i++) {
              if (!Number.isFinite(ch[i])) finite = false;
              peak = Math.max(peak, Math.abs(ch[i]));
            }
            if (!finite || peak < 0.01) silent.push([name, peak, /play it/i.test(blurb)]);
          }
        }
      }
      const kinds = PRESETS.map(([s, , kind]) => kind);
      const about = PRESETS.map(([s]) => s).filter((s) => !PRESET_ABOUT[s]);
      restore({}); await wait(30);
      return { wrong, silent, noBlurb, count: snaps.size, kinds, about };
    }""")
    print("    %d presets in %d sections" % (report["count"], len(report["kinds"])))
    check("every field a preset names is in the setup it makes, at the value it names",
          report["wrong"] == [], str(report["wrong"][:4]))
    unexplained = [s for s in report["silent"] if not s[2]]
    check("every generator preset sounds on the tone, or says it waits for a key",
          unexplained == [], "%s; waiting for a key: %s" % (unexplained, [s[0] for s in report["silent"] if s[2]]))
    check("every preset says what it is, every section what it is for, and says what it plays on",
          report["noBlurb"] == [] and report["about"] == []
          and all(k in ("generator", "display") for k in report["kinds"]),
          "%s, %s, %s" % (report["noBlurb"], report["about"], report["kinds"]))
    # The bank's shape. Read from PRESETS as the page ships it, and each rule
    # fed a library that breaks it, so none of them passes whatever the bank is.
    shape_js = """(lib) => {
      const sections = lib.map(([s]) => s);
      const of = (t) => (lib.find(([s]) => s === t) || [, []])[1];
      const split = (st) => st.layers === 'split';
      const scanned = (st) => Number(st.oscScan || 0) > 0 || Number(st.bScan || 0) > 0;
      return {
        order: sections.join(','),
        sizes: lib.map(([, e]) => e.length),
        splits: ['Settled', 'Breathing'].filter((t) => of(t).some(([, st]) => split(st))),
        latched: lib.flatMap(([, e]) => e).filter(([, st]) => 'midiLatch' in st).map(([n]) => n),
        pushed: of('Settled').filter(([, st]) => st.pictureAmount !== 0).map(([n]) => n),
        idle: of('Breathing').filter(([, st]) => !(st.pictureAmount > 0) && !scanned(st)).map(([n]) => n),
        unnamed: lib.flatMap(([, e]) => e).filter(([, st]) => !('pictureAmount' in st)).map(([n]) => n),
      };
    }"""
    def shape_ok(r):
        return (r["order"] == "Settled,Breathing" and all(n >= 2 for n in r["sizes"])
                and 4 <= sum(r["sizes"]) <= 24 and r["splits"] == ["Settled", "Breathing"]
                and not r["latched"] and not r["pushed"] and not r["idle"] and not r["unnamed"])
    shape = p.evaluate("(f) => (eval(f))(PRESETS)", shape_js)
    print("    %s" % shape)
    check("two headings, Settled then Breathing, two or more presets in each and four to twenty-four in all",
          shape["order"] == "Settled,Breathing" and all(n >= 2 for n in shape["sizes"])
          and 4 <= sum(shape["sizes"]) <= 24, "%s %s" % (shape["order"], shape["sizes"]))
    check("a split under each heading, the owner's way of playing",
          shape["splits"] == ["Settled", "Breathing"], str(shape["splits"]))
    check("Settled at nought, Breathing with the loop at work, and no preset naming the latch that was cut",
          not shape["latched"] and not shape["pushed"] and not shape["idle"], str(shape))
    check("every preset names the Picture amount, so none inherits the last one's", not shape["unnamed"], str(shape["unnamed"]))
    # The nulls: the bank with one thing wrong, each rule in turn.
    broken = p.evaluate("""(f) => {
      const shape = eval(f), lib = () => JSON.parse(JSON.stringify(PRESETS));
      const edit = (fn) => { const l = lib(); fn(l); return shape(l); };
      return [
        edit((l) => l.reverse()),
        edit((l) => { l[0][1] = l[0][1].filter(([, st]) => st.layers !== 'split'); }),
        edit((l) => { l[0][1][0][1].midiLatch = true; }),
        edit((l) => { l[0][1][0][1].pictureAmount = 30; }),
        edit((l) => { const st = l[1][1][0][1]; st.pictureAmount = 0; st.oscScan = 0; st.bScan = 0; }),
        edit((l) => { delete l[1][1][0][1].pictureAmount; }),
      ];
    }""", shape_js)
    check("and each of those rules fails a bank that breaks it", not any(shape_ok(r) for r in broken),
          str([shape_ok(r) for r in broken]))

    # The null for the first check: a preset with a key spelt wrong, and one
    # with a value past its control's end, must both be caught by the same
    # comparison.
    null = p.evaluate("""() => {
      const probe = (setup) => { restore(setup); const snap = snapshot();
        return Object.keys(setup).filter((k) => !(k in snap) || snap[k] !== setup[k]); };
      const out = [probe({ vcfEnv: 20 }), probe({ vcfCut: 1400 })];
      restore({});
      return out;
    }""")
    check("and that comparison catches a misspelt field and an out-of-range value",
          null == [["vcfEnv"], ["vcfCut"]], str(null))

    print("\n--- the browser ---")
    p.evaluate("() => applyPreset('b:Slow pad')")
    p.click("#preset"); p.wait_for_timeout(250)
    opened = p.evaluate("""() => ({
      open: el.presetDialog.open,
      menu: el.presetMenus.querySelector('[aria-selected="true"]').dataset.menu,
      menus: Array.from(el.presetMenus.querySelectorAll('.preset-menu')).map((m) => [m.dataset.menu, Number(m.querySelector('.count').textContent)]),
      rail: el.presetRail.hidden,
      railShown: getComputedStyle(el.presetRail).display !== 'none',
      cards: el.presetGrid.querySelectorAll('.preset-card').length,
      pressed: Array.from(el.presetGrid.querySelectorAll('[aria-pressed="true"]')).map((c) => c.dataset.value),
      focused: document.activeElement.dataset.value,
      about: el.presetAbout.textContent,
    })""")
    sizes = p.evaluate("() => PRESET_MENUS.map(([id, , , titles]) => [id, titles.reduce((a, t) => a + PRESETS.find(([n]) => n === t)[1].length, 0)])")
    menus = p.evaluate("""() => {
      const named = PRESET_MENUS.flatMap(([, , , titles]) => titles);
      return { orphans: PRESETS.map(([t]) => t).filter((t) => named.filter((n) => n === t).length !== 1),
               ghosts: named.filter((t) => !PRESETS.some(([n]) => n === t)) };
    }""")
    print("    %s" % opened)
    check("the button opens it on the heading of the preset in use, that card marked and focused, with what the heading means",
          opened["open"] and opened["menu"] == "breathing" and opened["pressed"] == ["b:Slow pad"]
          and opened["focused"] == "b:Slow pad" and opened["about"].startswith("The sound keeps moving"), str(opened))
    check("every section is in exactly one menu, and every menu's sections exist",
          menus["orphans"] == [] and menus["ghosts"] == [], "%s, %s" % (menus["orphans"], menus["ghosts"]))
    check("a menu for each heading in the loop's order, then Saved, each counting its presets",
          [m for m, _ in opened["menus"]] == ["settled", "breathing", "saved"]
          and [c for _, c in opened["menus"]][:2] == [n for _, n in sizes], str((opened["menus"], sizes)))
    # A menu of one section is the section: no rail. The null is a menu of
    # two, made for the purpose and taken away again, which must show it -
    # so a rail hidden whatever the menu fails here.
    rails = p.evaluate("""() => {
      // A section of its own, since a menu is found by its sections and one
      // already in another menu would be taken for that menu.
      PRESETS.push(['Extra', [['Extra one', { freq: 300 }, 'A preset made for this check and taken away again.']], 'generator']);
      PRESET_MENUS.push(['both', 'Both', 'Two sections', ['Extra', 'Settled']]);
      renderPresetBrowser();
      el.presetMenus.querySelector('[data-menu="both"]').click();
      const two = { hidden: el.presetRail.hidden, shown: getComputedStyle(el.presetRail).display !== 'none',
                    sections: Array.from(el.presetRail.querySelectorAll('.preset-section')).map((r) => r.firstChild.textContent) };
      PRESET_MENUS.pop(); PRESETS.pop();
      el.presetMenus.querySelector('[data-menu="breathing"]').click();
      return { two, one: { hidden: el.presetRail.hidden, shown: getComputedStyle(el.presetRail).display !== 'none' } };
    }""")
    check("a menu of one section has no rail, and one of two shows both, so the rail is hidden only when there is nothing to choose",
          opened["rail"] and not opened["railShown"] and rails["one"] == {"hidden": True, "shown": False}
          and rails["two"] == {"hidden": False, "shown": True, "sections": ["Extra", "Settled"]}, str(rails))
    preview = p.evaluate("""() => {
      const card = Array.from(el.presetGrid.querySelectorAll('.preset-card')).find((c) => c.dataset.value === 'b:Turning fifths');
      card.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
      const blurb = card.querySelector('.preset-blurb');
      const full = PRESETS.flatMap(([, e]) => e).find(([n]) => n === 'Turning fifths')[2];
      return { text: el.presetPreview.querySelector('p').textContent === full,
               where: el.presetPreview.querySelector('.where').textContent,
               clamped: blurb.scrollHeight > blurb.clientHeight + 2 };
    }""")
    check("the strip below shows the whole of what the card under the pointer says, and its heading once",
          preview["text"] and preview["where"] == "Breathing", str(preview))
    check("while the card itself shows two lines of it", preview["clamped"], str(preview))

    p.click('.preset-menu[data-menu="settled"]'); p.wait_for_timeout(150)
    p.click('.preset-card:has-text("Drawbar organ")'); p.wait_for_timeout(300)
    loaded = p.evaluate("""() => ({ value: el.preset.value, label: el.presetCurrent.textContent,
      open: el.presetDialog.open, shape: genSettings().shape, bars: el.bars ? el.bars.value : null,
      pressed: Array.from(el.presetGrid.querySelectorAll('[aria-pressed="true"]')).map((c) => c.dataset.value) })""")
    check("a card loads its preset, marks itself, says so on the strip, and leaves the browser open",
          {k: loaded[k] for k in ("value", "label", "open", "shape", "pressed")}
          == {"value": "b:Drawbar organ", "label": "Drawbar organ", "open": True, "shape": "drawbars",
              "pressed": ["b:Drawbar organ"]}, str(loaded))

    # The arrows: by one across, by a row of columns down, held at the last card.
    p.click('.preset-menu[data-menu="breathing"]'); p.wait_for_timeout(150)
    moves = p.evaluate("""() => {
      const cards = Array.from(el.presetGrid.querySelectorAll('.preset-card'));
      const columns = getComputedStyle(el.presetGrid).gridTemplateColumns.split(' ').length;
      cards[0].focus();
      document.activeElement.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
      const right = cards.indexOf(document.activeElement);
      document.activeElement.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
      const down = cards.indexOf(document.activeElement);
      return { right, down, columns, count: cards.length };
    }""")
    check("the arrows move one card across and a row of columns down",
          moves["right"] == 1 and moves["down"] == min(moves["count"] - 1, 1 + moves["columns"]) and moves["columns"] >= 2
          and moves["down"] > moves["right"], str(moves))
    enter = p.evaluate("""() => {
      const card = el.presetGrid.querySelector('.preset-card');
      card.focus();
      card.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      return { value: el.preset.value, open: el.presetDialog.open };
    }""")
    check("Enter loads the focused card and closes", enter == {"value": "b:Harmonic tone", "open": False}, str(enter))

    p.click("#preset"); p.wait_for_timeout(200)
    p.click('.preset-menu[data-menu="breathing"]'); p.wait_for_timeout(150)
    p.dblclick('.preset-card:has-text("Turning fifths")'); p.wait_for_timeout(250)
    dbl = p.evaluate("() => ({ value: el.preset.value, open: el.presetDialog.open })")
    check("a double-click loads and closes", dbl == {"value": "b:Turning fifths", "open": False}, str(dbl))
    # New (P8h): back to the base, from a preset that is not it, which is the
    # null for each field read - Turning fifths has the loop on.
    p.click("#preset"); p.wait_for_timeout(200)
    p.click("#presetNew"); p.wait_for_timeout(300)
    fresh = p.evaluate("""() => ({ value: el.preset.value, label: el.presetCurrent.textContent, open: el.presetDialog.open,
      shape: genSettings().shape, amount: el.pictureAmount.value, round: el.polyRound.checked, mode: midi.mode,
      scan: snapshot().oscScan, same: JSON.stringify(Object.keys(BASE_SETUP).map((k) => snapshot()[k])) === JSON.stringify(Object.values(BASE_SETUP)) })""")
    check("New goes back to the base, a still plain sine, says so on the strip, and closes the browser",
          fresh == {"value": "n:Plain sine", "label": "Plain sine", "open": False, "shape": "sine", "amount": "0",
                    "round": True, "mode": "poly", "scan": 0, "same": True}, str(fresh))

    print("\n--- search, the page's keys, and Custom ---")
    p.click("#preset"); p.wait_for_timeout(200)
    # A word in more than one heading's presets.
    p.fill("#presetFind", "split"); p.wait_for_timeout(150)
    found = p.evaluate("""() => ({
      headings: Array.from(el.presetGrid.querySelectorAll('.preset-heading')).map((h) => h.textContent),
      names: Array.from(el.presetGrid.querySelectorAll('.preset-name')).map((n) => n.textContent) })""")
    print("    'split': %s" % found)
    check("search looks across every heading and heads what it finds by its heading, said once",
          "Bass under the tine piano" in found["names"] and "Bass under the pad" in found["names"]
          and {"Settled", "Breathing"} <= set(found["headings"]), str(found))
    # A word only a description has: "jazz" is in the organ's, nowhere else.
    p.fill("#presetFind", "jazz"); p.wait_for_timeout(150)
    jazz = p.evaluate("() => Array.from(el.presetGrid.querySelectorAll('.preset-name')).map((n) => n.textContent)")
    check("and reads what each preset says about itself, not only its name", jazz == ["Drawbar organ"], str(jazz))
    p.fill("#presetFind", "two words neither"); p.wait_for_timeout(150)
    none = p.evaluate("() => el.presetGrid.textContent")
    p.fill("#presetFind", "bass pad"); p.wait_for_timeout(150)
    both = p.evaluate("() => Array.from(el.presetGrid.querySelectorAll('.preset-name')).map((n) => n.textContent)")
    check("every word has to match, and nothing found says so",
          "No preset matches" in none and "Bass under the pad" in both and "Bass under the tine piano" not in both, str(both))
    p.fill("#presetFind", "")
    # The page's own keys stand aside: 2 would switch to X-Y, B to the Bench.
    keys = p.evaluate("""() => {
      const was = [state.display, document.body.dataset.view];
      for (const key of ['2', 'b', '3']) document.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }));
      return { was, now: [state.display, document.body.dataset.view] };
    }""")
    check("the page's own keys do nothing while it is open", keys["was"] == keys["now"], str(keys))
    p.keyboard.press("Escape"); p.wait_for_timeout(150)
    p.evaluate("() => { el.freq.value = '300'; el.freq.dispatchEvent(new Event('input')); }")
    p.wait_for_timeout(1200)
    custom = p.evaluate("() => [el.preset.value, el.presetCurrent.textContent]")
    check("moving a control off a preset says Custom", custom == ["", "Custom"], str(custom))

    print("\n--- saved setups, and where a preset lands ---")
    saved = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.presetName.value = 'My test setup'; el.presetSave.click(); await wait(50);
      openPresets();
      const menu = el.presetMenus.querySelector('[aria-selected="true"]').dataset.menu;
      const cards = Array.from(el.presetGrid.querySelectorAll('.preset-card')).map((c) => c.dataset.value);
      restore({}); applyPreset('n:Plain sine');
      // Guarded, so that a missing card fails the check below rather than
      // stopping the test with an exception that names nothing.
      const mine = el.presetGrid.querySelector('[data-value="s:My test setup"]');
      if (mine) mine.click();
      const back = [el.preset.value, genSettings().freq];
      el.presetDialog.close();
      el.presetDelete.click(); await wait(30);
      return { menu, cards, back };
    }""")
    check("a saved setup has a card in Saved, where the browser opens while it is in use, and loads from there",
          saved["menu"] == "saved" and saved["cards"] == ["s:My test setup"]
          and saved["back"] == ["s:My test setup", 300], str(saved))
    # A microphone - an oscillator behind getUserMedia - has no generator:
    # a generator section says so, and offers the tone.
    mic = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const ctx = new AudioContext();
      const osc = ctx.createOscillator(), dest = ctx.createMediaStreamDestination();
      osc.connect(dest); osc.start();
      navigator.mediaDevices.getUserMedia = () => Promise.resolve(dest.stream);
      el.srcMic.click(); await wait(900);
      openPresets();
      el.presetMenus.querySelector('[data-menu="settled"]').click();
      const said = el.presetWhere.hidden ? '' : el.presetWhere.textContent;
      // What is playing, not the source's kind: the instrument's is "host" whatever it draws (5m).
      const kind = playingKind();
      const offer = document.getElementById('presetToTone');
      if (offer) offer.click();
      await wait(400);
      const after = { kind: playingKind(), hidden: el.presetWhere.hidden };
      el.presetDialog.close();
      return { said, kind, after };
    }""")
    print("    %s" % mic)
    check("on a microphone a generator section says nothing playing has a generator, and offers the tone",
          "nothing playing now has one" in mic["said"] and mic["kind"] != "tone"
          and mic["after"] == {"kind": "tone", "hidden": True}, str(mic))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("a bank under two headings to browse, and every preset in it is what it says it is")
