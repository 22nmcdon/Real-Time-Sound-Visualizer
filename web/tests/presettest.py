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
- the browser: it opens on the section in use, a card loads and leaves it
  open, Enter and a double-click load and close, the arrows move between
  cards by rows and columns, search looks across sections, saved setups
  have a section, moving a control says Custom, the page's own keys stand
  aside while it is open, and it says when a preset cannot be heard.
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
    check("a library with breadth: at least ninety presets in at least fifteen sections",
          report["count"] >= 90 and len(report["kinds"]) >= 15, "%d, %d" % (report["count"], len(report["kinds"])))

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
    p.evaluate("() => applyPreset('b:Wah')")
    p.click("#preset"); p.wait_for_timeout(250)
    opened = p.evaluate("""() => ({
      open: el.presetDialog.open,
      sections: el.presetRail.querySelectorAll('.preset-section').length,
      on: el.presetRail.querySelector('[aria-selected="true"]').firstChild.textContent,
      cards: el.presetGrid.querySelectorAll('.preset-card').length,
      pressed: Array.from(el.presetGrid.querySelectorAll('[aria-pressed="true"]')).map((c) => c.dataset.value),
      focused: document.activeElement.dataset.value,
      about: el.presetAbout.textContent.length > 40,
      counts: Array.from(el.presetRail.querySelectorAll('.count')).map((c) => Number(c.textContent)),
    })""")
    sizes = p.evaluate("PRESETS.map(([, e]) => e.length)")
    print("    %s" % {k: v for k, v in opened.items() if k != "counts"})
    check("the button opens it on the section of the preset in use, that card marked and focused",
          opened["open"] and opened["on"] == "Keys and leads" and opened["pressed"] == ["b:Wah"]
          and opened["focused"] == "b:Wah" and opened["about"], str(opened))
    check("one section a group and one for saved setups, each counting its presets",
          opened["sections"] == len(sizes) + 1 and opened["counts"][:-1] == sizes, str(opened["counts"]))

    p.click('.preset-section:has-text("Bells and metal")'); p.wait_for_timeout(150)
    p.click('.preset-card:has-text("Ring modulator")'); p.wait_for_timeout(300)
    loaded = p.evaluate("""() => ({ value: el.preset.value, label: el.presetCurrent.textContent,
      open: el.presetDialog.open, ring: genSettings().ringMix, ratio: genSettings().modRatio,
      pressed: Array.from(el.presetGrid.querySelectorAll('[aria-pressed="true"]')).map((c) => c.dataset.value) })""")
    check("a card loads its preset, marks itself, says so on the strip, and leaves the browser open",
          loaded == {"value": "b:Ring modulator", "label": "Ring modulator", "open": True, "ring": 1,
                     "ratio": 1.25, "pressed": ["b:Ring modulator"]}, str(loaded))

    # The arrows: by one across, by a row of columns down.
    moves = p.evaluate("""() => {
      const cards = Array.from(el.presetGrid.querySelectorAll('.preset-card'));
      const columns = getComputedStyle(el.presetGrid).gridTemplateColumns.split(' ').length;
      cards[0].focus();
      const key = (k) => el.presetDialog.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true }))
        || document.activeElement.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true }));
      document.activeElement.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
      const right = cards.indexOf(document.activeElement);
      document.activeElement.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
      const down = cards.indexOf(document.activeElement);
      return { right, down, columns };
    }""")
    check("the arrows move one card across and a row of columns down",
          moves["right"] == 1 and moves["down"] == 1 + moves["columns"] and moves["columns"] >= 2, str(moves))
    enter = p.evaluate("""() => {
      const card = el.presetGrid.querySelector('.preset-card');
      card.focus();
      card.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      return { value: el.preset.value, open: el.presetDialog.open };
    }""")
    check("Enter loads the focused card and closes", enter == {"value": "b:Bell", "open": False}, str(enter))

    p.click("#preset"); p.wait_for_timeout(200)
    p.dblclick('.preset-card:has-text("Gong")'); p.wait_for_timeout(250)
    dbl = p.evaluate("() => ({ value: el.preset.value, open: el.presetDialog.open })")
    check("a double-click loads and closes", dbl == {"value": "b:Gong", "open": False}, str(dbl))

    print("\n--- search, the page's keys, and Custom ---")
    p.click("#preset"); p.wait_for_timeout(200)
    # A word in more than one section. ("bell" was the first try, and found
    # the whole of Bells and metal by its title and nothing else: right, and
    # no test of looking across sections.)
    p.fill("#presetFind", "fold"); p.wait_for_timeout(150)
    found = p.evaluate("""() => ({
      headings: Array.from(el.presetGrid.querySelectorAll('.preset-heading')).map((h) => h.textContent),
      names: Array.from(el.presetGrid.querySelectorAll('.preset-name')).map((n) => n.textContent) })""")
    print("    'fold': %s" % found)
    check("search looks across every section and heads what it finds by section",
          "Wavefolder" in found["names"] and "Radial fold" in found["names"]
          and {"Grit", "The plane"} <= set(found["headings"]), str(found))
    # A word only a description has: "tine" is in the FM piano's, nowhere else.
    p.fill("#presetFind", "tine"); p.wait_for_timeout(150)
    tine = p.evaluate("() => Array.from(el.presetGrid.querySelectorAll('.preset-name')).map((n) => n.textContent)")
    check("and reads what each preset says about itself, not only its name", tine == ["FM electric piano"], str(tine))
    p.fill("#presetFind", "two words neither"); p.wait_for_timeout(150)
    none = p.evaluate("() => el.presetGrid.textContent")
    p.fill("#presetFind", "fold petals"); p.wait_for_timeout(150)
    both = p.evaluate("() => Array.from(el.presetGrid.querySelectorAll('.preset-name')).map((n) => n.textContent)")
    check("every word has to match, and nothing found says so",
          "No preset matches" in none and "Folded petals" in both and "Radial fold" not in both, str(both))
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
      const section = el.presetRail.querySelector('[aria-selected="true"]').firstChild.textContent;
      const cards = Array.from(el.presetGrid.querySelectorAll('.preset-card')).map((c) => c.dataset.value);
      restore({}); applyPreset('b:Pure sine');
      // Guarded, so that a missing card fails the check below rather than
      // stopping the test with an exception that names nothing.
      const mine = el.presetGrid.querySelector('[data-value="s:My test setup"]');
      if (mine) mine.click();
      const back = [el.preset.value, genSettings().freq];
      el.preset.value; el.presetDialog.close();
      el.presetDelete.click(); await wait(30);
      return { section, cards, back };
    }""")
    check("a saved setup has a card in Saved, where the browser opens while it is in use, and loads from there",
          saved["section"] == "Saved" and saved["cards"] == ["s:My test setup"]
          and saved["back"] == ["s:My test setup", 300], str(saved))
    live = p.evaluate("""() => {
      openPresets();
      el.presetRail.querySelector('.preset-section:nth-child(' + (PRESETS.findIndex(([s]) => s === 'Live') + 1) + ')').click();
      const text = el.presetWhere.hidden ? '' : el.presetWhere.textContent;
      el.presetDialog.close();
      return text;
    }""")
    check("the Live section says it changes the display only", "display only" in live, live)
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
      el.presetRail.querySelector('.preset-section').click();
      const said = el.presetWhere.hidden ? '' : el.presetWhere.textContent;
      const kind = state.source && state.source.kind;
      const offer = document.getElementById('presetToTone');
      if (offer) offer.click();
      await wait(400);
      const after = { kind: state.source.kind, hidden: el.presetWhere.hidden };
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
print("a library to browse, and every preset in it is what it says it is")
