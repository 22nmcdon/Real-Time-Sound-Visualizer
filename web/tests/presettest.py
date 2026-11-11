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
- the browser (F6): it opens on the heading in use with that card chosen
  and shown on the right; the headings say what they mean; a heading of one
  section has no rail; a card chosen loads nothing and Load loads it and
  leaves the browser open; Enter and a double-click load and close; the
  arrows walk the list; New goes back to the base the instrument opens on;
  moving a control says Custom; the page's own keys stand aside while it is
  open; and it says when a preset cannot be heard;
- the thumbnails: every bank preset's figure drawn by the instrument and
  still for its setup (a preset changed since is caught, write_figures.py
  draws it again), B drawn only on a split, the cards drawing what is
  stored;
- the footer, which F6 took from Settings: saving asks for a name, keeps the
  figure of what is sounding (none in silence), and lands in Saved; Delete
  takes the chosen saved one and its figure; Copy and Paste the code, and a
  code that cannot be read changes nothing.
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
            /* A B field equal to A's loads its section linked (G6, the owner's
               call), and a linked section writes no B fields: what it named is
               then A's value, which the setup carries. */
            const sec = HAND_SECTION_IDS.find((s) => HAND_SECTIONS[s].fields.includes(key));
            if (!(key in snap) && sec && linked(sec)) continue;
            if (!(key in snap)) { wrong.push([name, key, 'not a setup field']); continue; }
            if (snap[key] !== setup[key]) wrong.push([name, key, setup[key], snap[key]]);
          }
          if (!blurb || blurb.length < 20) noBlurb.push(name);
          const key = JSON.stringify(snap);
          if (snaps.has(key)) wrong.push([name, 'the same as', snaps.get(key)]);
          snaps.set(key, name);
          /* Under a note each side of any split, since the site waits for a
             note (10 Nov): until then every preset drew its generator with
             none, and one silent for want of a key said so in its words. */
          if (kind === 'generator') {
            midiNoteOn(48, 100); midiNoteOn(67, 100);
            await wait(260);
            const w = state.source.getLatestWindow(4410);
            let peak = 0, finite = true;
            for (const ch of w) for (let i = 0; i < ch.length; i++) {
              if (!Number.isFinite(ch[i])) finite = false;
              peak = Math.max(peak, Math.abs(ch[i]));
            }
            if (!finite || peak < 0.01) silent.push([name, peak]);
            midiNoteOff(48); midiNoteOff(67);
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
    check("every generator preset sounds under a note each side of a split", report["silent"] == [], str(report["silent"]))
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
      menus: Array.from(el.presetMenus.querySelectorAll('.preset-menu')).map((m) => [m.dataset.menu,
        Number(m.querySelector('.count').textContent), m.querySelector('.menu-line').textContent]),
      about: el.presetMenus.querySelector('[data-menu="breathing"]').title,
      rail: el.presetRail.hidden,
      railShown: getComputedStyle(el.presetRail).display !== 'none',
      cards: el.presetGrid.querySelectorAll('.preset-card').length,
      pressed: Array.from(el.presetGrid.querySelectorAll('[aria-pressed="true"]')).map((c) => c.dataset.value),
      chosen: Array.from(el.presetGrid.querySelectorAll('[data-chosen]')).map((c) => c.dataset.value),
      focused: document.activeElement.dataset.value,
      right: [el.presetChosenWhere.textContent, el.presetChosenName.textContent],
      code: el.presetCode.value === encodeSetup(snapshot()),
      settings: Array.from(document.querySelectorAll('[data-home="settings"] .menu-title')).map((t) => t.textContent.trim()),
    })""")
    sizes = p.evaluate("() => PRESET_MENUS.map(([id, , , titles]) => [id, titles.reduce((a, t) => a + PRESETS.find(([n]) => n === t)[1].length, 0)])")
    menus = p.evaluate("""() => {
      const named = PRESET_MENUS.flatMap(([, , , titles]) => titles);
      return { orphans: PRESETS.map(([t]) => t).filter((t) => named.filter((n) => n === t).length !== 1),
               ghosts: named.filter((t) => !PRESETS.some(([n]) => n === t)) };
    }""")
    print("    %s" % opened)
    check("the button opens it on the heading of the preset in use, that card in use, chosen, focused and shown on the right",
          opened["open"] and opened["menu"] == "breathing" and opened["pressed"] == ["b:Slow pad"]
          and opened["chosen"] == ["b:Slow pad"] and opened["focused"] == "b:Slow pad"
          and opened["right"] == ["Breathing", "Slow pad"] and opened["about"].startswith("The sound keeps moving"), str(opened))
    check("every section is in exactly one heading, and every heading's sections exist",
          menus["orphans"] == [] and menus["ghosts"] == [], "%s, %s" % (menus["orphans"], menus["ghosts"]))
    check("the headings down the left in the loop's order, then Saved, each counting its presets and saying what it means in a line",
          [m for m, _, _ in opened["menus"]] == ["settled", "breathing", "saved"]
          and [c for _, c, _ in opened["menus"]][:2] == [n for _, n in sizes] and all(l for _, _, l in opened["menus"]),
          str((opened["menus"], sizes)))
    # F6 moved saving and the code out of Settings into the browser's foot:
    # one place for them, not two. The null is Settings' sections before F6.
    check("Settings has no Presets section any more: it is the browser's footer",
          "Presets" not in opened["settings"] and len(opened["settings"]) >= 3, str(opened["settings"]))
    check("and the code field opens holding the code of what is playing", opened["code"], "")
    # A menu of one section is the section: no rail. The null is a menu of
    # two, made for the purpose and taken away again, which must show it -
    # so a rail hidden whatever the menu fails here.
    rails = p.evaluate("""() => {
      // A section of its own, since a menu is found by its sections and one
      // already in another menu would be taken for that menu.
      PRESETS.push(['Extra', [['Extra one', { freq: 300 }, 'A preset made for this check and taken away again.']], 'generator']);
      PRESET_MENUS.push(['both', 'Both', 'Two sections', ['Extra', 'Settled'], 'Two sections']);
      renderPresetBrowser();
      el.presetMenus.querySelector('[data-menu="both"]').click();
      const two = { hidden: el.presetRail.hidden, shown: getComputedStyle(el.presetRail).display !== 'none',
                    sections: Array.from(el.presetRail.querySelectorAll('.preset-section')).map((r) => r.firstChild.textContent) };
      PRESET_MENUS.pop(); PRESETS.pop();
      el.presetMenus.querySelector('[data-menu="breathing"]').click();
      return { two, one: { hidden: el.presetRail.hidden, shown: getComputedStyle(el.presetRail).display !== 'none' } };
    }""")
    check("a heading of one section has no rail, and one of two shows both, so the rail is hidden only when there is nothing to choose",
          opened["rail"] and not opened["railShown"] and rails["one"] == {"hidden": True, "shown": False}
          and rails["two"] == {"hidden": False, "shown": True, "sections": ["Extra", "Settled"]}, str(rails))

    # The thumbnails (F6): every bank preset's figure drawn by the instrument
    # (write_figures.py) and still for the setup it was drawn from - the null
    # a preset changed by one hertz, whose figure must then read as stale. A
    # split draws B; one hand does not; and the cards draw what is stored.
    thumbs = p.evaluate("""() => {
      const bank = PRESETS.flatMap(([, entries]) => entries.map(([n, s]) => ['b:' + n, s]));
      const stale = bank.filter(([v, s]) => !PRESET_FIGURES[v] || PRESET_FIGURES[v].hash !== presetHash(s)).map(([v]) => v);
      const [v0, s0] = bank[0];
      const nudged = PRESET_FIGURES[v0].hash !== presetHash(Object.assign({}, s0, { freq: (s0.freq || 220) + 1 }));
      const wrongB = bank.filter(([v, s]) => !!PRESET_FIGURES[v].b !== (s.layers === 'split')).map(([v]) => v);
      const points = bank.map(([v]) => PRESET_FIGURES[v].a.split(' ').length / 2);
      el.presetMenus.querySelector('[data-menu="settled"]').click();
      const drawn = Array.from(el.presetGrid.querySelectorAll('.preset-card')).map((c) =>
        [c.dataset.value, c.querySelector('.fig-a') && c.querySelector('.fig-a').getAttribute('d') === 'M' + PRESET_FIGURES[c.dataset.value].a,
         !!c.querySelector('.fig-b')]);
      const big = el.presetFigure.querySelector('.fig-a');
      return { stale, nudged, wrongB, points: [Math.min(...points), Math.max(...points)], drawn,
               big: !!big && big.getAttribute('d') === 'M' + PRESET_FIGURES[presetChosen].a };
    }""")
    print("    %s" % {k: thumbs[k] for k in ("stale", "wrongB", "points", "big")})
    check("every bank preset has its figure, drawn from the setup it has now (write_figures.py)",
          thumbs["stale"] == [], "draw these again: %s" % thumbs["stale"])
    check("null: a preset changed by one hertz reads as stale", thumbs["nudged"], "")
    check("a split's figure draws layer B, and one hand's does not", thumbs["wrongB"] == [], str(thumbs["wrongB"]))
    check("each figure is at most FIGURE_POINTS, and enough to draw it: a hundred or more", 100 <= thumbs["points"][0] and thumbs["points"][1] <= 240, str(thumbs["points"]))
    check("each card draws its own figure, with B's only on a split, and the chosen one is drawn large on the right",
          all(ok for _, ok, _ in thumbs["drawn"]) and [b for _, _, b in thumbs["drawn"]] == [
              p.evaluate("(v) => findPreset(v).layers === 'split'", v) for v, _, _ in thumbs["drawn"]]
          and thumbs["big"], str(thumbs["drawn"]))

    # Choosing shows and loads nothing; Load loads and leaves it open.
    p.click('.preset-card:has-text("Drawbar organ")'); p.wait_for_timeout(200)
    chosen = p.evaluate("""() => ({ value: el.preset.value, open: el.presetDialog.open, shape: genSettings().shape,
      right: [el.presetChosenWhere.textContent, el.presetChosenName.textContent],
      text: el.presetChosenText.textContent === findPresetEntry('Drawbar organ'),
      chosen: Array.from(el.presetGrid.querySelectorAll('[data-chosen]')).map((c) => c.dataset.value) })""".replace(
        "findPresetEntry('Drawbar organ')", "PRESETS.flatMap(([, e]) => e).find(([n]) => n === 'Drawbar organ')[2]"))
    check("a card chosen is shown on the right, whole, and nothing is loaded: Slow pad still plays",
          chosen == {"value": "b:Slow pad", "open": True, "shape": chosen["shape"], "right": ["Settled", "Drawbar organ"],
                     "text": True, "chosen": ["b:Drawbar organ"]} and chosen["shape"] != "drawbars", str(chosen))
    # The two short lines (8 Nov): on the card, the listen line in place of
    # the description's first sentence; on the right, both, over the whole.
    # Read off the screen, and each held to the bank, so a pane showing the
    # other preset's lines, or the first sentence, fails.
    lines = p.evaluate("""() => {
      const entry = PRESETS.flatMap(([, e]) => e).find(([n]) => n === 'Drawbar organ');
      const card = el.presetGrid.querySelector('.preset-card[data-value="b:Drawbar organ"] .preset-blurb');
      return { shown: !el.presetChosenLines.hidden && el.presetChosenLines.getBoundingClientRect().height > 20,
               listen: el.presetChosenListen.textContent === entry[3][0], watch: el.presetChosenWatch.textContent === entry[3][1],
               card: card.textContent === entry[3][0], first: card.textContent === firstSentence(entry[2]) };
    }""")
    check("chosen, its card says what to listen for, and the right both that and what to watch for",
          lines == {"shown": True, "listen": True, "watch": True, "card": True, "first": False}, str(lines))
    LINES_RULE = """(lib) => lib.flatMap(([, e]) => e).filter(([, , blurb, l]) => !Array.isArray(l) || l.length !== 2
      || l.some((x) => typeof x !== 'string' || x.length < 12 || x.length > 60 || /[.]$/.test(x))
      || l[0] === l[1] || blurb.startsWith(l[0])).map(([n]) => n)"""
    short = p.evaluate("(f) => (eval(f))(PRESETS)", LINES_RULE)
    check("every preset in the bank has both lines, each short - twelve to sixty characters - and its own", short == [], str(short))
    short_null = p.evaluate("""(f) => { const rule = eval(f), lib = () => JSON.parse(JSON.stringify(PRESETS));
      const a = lib(); a[0][1][0].pop();
      const b = lib(); b[1][1][0][3][1] = 'x'.repeat(80);
      const c = lib(); c[1][1][1][3] = [c[1][1][1][3][0], c[1][1][1][3][0]];
      return [rule(a).length, rule(b).length, rule(c).length]; }""", LINES_RULE)
    check("null: a bank with a preset's lines missing, one too long, or the same line twice fails it", short_null == [1, 1, 1], str(short_null))
    p.click("#presetLoad"); p.wait_for_timeout(300)
    loaded = p.evaluate("""() => ({ value: el.preset.value, label: el.presetCurrent.textContent,
      open: el.presetDialog.open, shape: genSettings().shape,
      pressed: Array.from(el.presetGrid.querySelectorAll('[aria-pressed="true"]')).map((c) => c.dataset.value),
      code: el.presetCode.value === encodeSetup(snapshot()) })""")
    check("Load loads the chosen one, marks it in use, says so on the strip, leaves the browser open and the code follows",
          loaded == {"value": "b:Drawbar organ", "label": "Drawbar organ", "open": True, "shape": "drawbars",
                     "pressed": ["b:Drawbar organ"], "code": True}, str(loaded))

    # The arrows: down the list a card at a time, held at the last.
    p.click('.preset-menu[data-menu="breathing"]'); p.wait_for_timeout(150)
    moves = p.evaluate("""() => {
      const cards = Array.from(el.presetGrid.querySelectorAll('.preset-card'));
      cards[0].focus();
      const step = (key) => { document.activeElement.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }));
                              return cards.indexOf(document.activeElement); };
      const down = step('ArrowDown'), again = step('ArrowDown'), up = step('ArrowUp');
      for (let i = 0; i < cards.length + 2; i++) step('ArrowDown');
      return { down, again, up, last: cards.indexOf(document.activeElement), count: cards.length,
               chosen: presetChosen === cards[cards.length - 1].dataset.value };
    }""")
    check("the arrows move down and up the list a card at a time, held at the last, and the focus chooses",
          moves == {"down": 1, "again": 2, "up": 1, "last": moves["count"] - 1, "count": moves["count"], "chosen": True}
          and moves["count"] >= 3, str(moves))
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

    print("\n--- the page's keys, and Custom ---")
    p.click("#preset"); p.wait_for_timeout(200)
    # The page's own keys stand aside: 2 would switch to X-Y, C the cursors on.
    # (B, which went to the Bench, was the second key until G4 took the views.)
    keys = p.evaluate("""() => {
      const was = [state.display, state.cursors];
      for (const key of ['2', 'c', '3']) document.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }));
      return { was, now: [state.display, state.cursors] };
    }""")
    check("the page's own keys do nothing while it is open", keys["was"] == keys["now"], str(keys))
    p.keyboard.press("Escape"); p.wait_for_timeout(150)
    p.evaluate("() => { el.freq.value = '300'; el.freq.dispatchEvent(new Event('input')); }")
    p.wait_for_timeout(1200)
    custom = p.evaluate("() => [el.preset.value, el.presetCurrent.textContent]")
    check("moving a control off a preset says Custom", custom == ["", "Custom"], str(custom))

    print("\n--- the footer: saving, deleting, the setup code ---")
    # Saved with a note held, so it has a figure; then one saved in silence,
    # which must have none rather than a flat line passed off as a figure.
    saved = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      openPresets();
      el.presetSaveOpen.click();
      const asking = !el.presetSaving.hidden && document.activeElement === el.presetName;
      el.presetName.value = '';
      el.presetSave.click();
      const unnamed = [el.presetNote.textContent, Object.keys(readSaved()).length];
      setScreenKeys(true); midiBytes(new Uint8Array([0x90, 60, 100])); await wait(700);
      el.presetName.value = 'My test setup';
      el.presetName.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      midiBytes(new Uint8Array([0x80, 60, 0])); midiPanic(); await wait(600);
      const menu = el.presetMenus.querySelector('[aria-selected="true"]').dataset.menu;
      const cards = Array.from(el.presetGrid.querySelectorAll('.preset-card')).map((c) => c.dataset.value);
      const figure = readSavedFigures()['My test setup'];
      const drawn = !!el.presetGrid.querySelector('[data-value="s:My test setup"] .fig-a');
      el.presetSaveOpen.click(); el.presetName.value = 'Silent one'; el.presetSave.click(); await wait(50);
      const silent = [readSavedFigures()['Silent one'] === undefined,
                      !!el.presetGrid.querySelector('[data-value="s:Silent one"] .fig-none')];
      restore({}); applyPreset('n:Plain sine');
      const mine = el.presetGrid.querySelector('[data-value="s:My test setup"]');
      if (mine) { mine.click(); el.presetLoad.click(); }
      const back = [el.preset.value, genSettings().freq];
      // A saved sound has no short lines: the pane shows none, not the last preset's.
      const noLines = [el.presetChosenLines.hidden, el.presetChosenListen.textContent];
      // Delete the chosen saved one, then the other, and their figures with them.
      el.presetDelete.click(); await wait(30);
      const afterOne = [Object.keys(readSaved()), Object.keys(readSavedFigures())];
      const other = el.presetGrid.querySelector('[data-value="s:Silent one"]');
      if (other) other.click();
      el.presetDelete.click(); await wait(30);
      const afterBoth = [Object.keys(readSaved()), el.presetGrid.querySelectorAll('.preset-card').length];
      el.presetDialog.close();
      return { asking, unnamed, menu, cards, figure: !!figure && figure.a.split(' ').length > 100, drawn, silent, back,
               afterOne, afterBoth, noLines };
    }""")
    print("    %s" % saved)
    check("Save this sound asks for a name, and saves nothing without one",
          saved["asking"] and saved["unnamed"][1] == 0 and "name" in saved["unnamed"][0], str(saved["unnamed"]))
    check("a sound saved while a note sounds has a card in Saved, with its figure, where the browser now is, and Load loads it",
          saved["menu"] == "saved" and saved["cards"] == ["s:My test setup"] and saved["figure"] and saved["drawn"]
          and saved["back"] == ["s:My test setup", 300], str(saved))
    check("null: one saved in silence has no figure, and its card says so with an empty mark",
          saved["silent"] == [True, True], str(saved["silent"]))
    check("a saved sound chosen shows no listen or watch lines", saved["noLines"] == [True, ""], str(saved["noLines"]))
    check("Delete saved takes the chosen saved one and its figure, then the other",
          saved["afterOne"] == [["Silent one"], []] and saved["afterBoth"] == [[], 0], str((saved["afterOne"], saved["afterBoth"])))

    code = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      applyPreset('b:Slow pad'); openPresets();
      el.presetCopy.click(); await wait(100);
      const copied = el.presetCode.value === encodeSetup(snapshot());
      // A code pasted into the field by hand, then Paste: the drawbar organ's.
      const organ = encodeSetup(findPreset('b:Drawbar organ'));
      el.presetCode.value = organ;
      el.presetPaste.click(); await wait(200);
      const pasted = { shape: genSettings().shape, value: el.preset.value, note: el.presetNote.textContent };
      el.presetCode.value = 'not a code';
      el.presetPaste.click(); await wait(100);
      const bad = [el.presetNote.textContent, genSettings().shape];
      el.presetDialog.close();
      return { copied, pasted, bad };
    }""")
    print("    %s" % code)
    check("Copy puts the code of what is playing in the field", code["copied"], "")
    check("Paste loads a code put in the field: the organ's drawbars, and Custom, since a code is not a preset",
          code["pasted"] == {"shape": "drawbars", "value": "", "note": "Loaded."}, str(code["pasted"]))
    check("and a code that cannot be read says so and changes nothing",
          code["bad"] == ["That code could not be read.", "drawbars"], str(code["bad"]))

    print("\n--- where a preset lands ---")
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
