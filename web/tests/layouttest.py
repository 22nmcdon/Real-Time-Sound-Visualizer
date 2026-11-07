"""The modulation cards and their editor, reaching any control, and search.

What would go wrong, and what is checked for it:

- a fourth card, for a controller learned, the photocell or a hearing
  source patched - each of which grew the strip before F4 - or a parked
  source's ink lost from the knob it is on;
- a card press that does not open its editor, or an editor left over a tab
  that has been chosen;
- the editor describing one source and editing another, or its meter
  reading something other than the source's own value. The meter is read
  against a source whose value is set here, at a positive and a negative
  number, so a meter that ignored the sign or the bipolar centre would show;
- the Add menu offering a destination the source is already on;
- `showControl` opening the wrong view or the wrong tab;
- search indexing the options inside menus (which made "cutoff" land on every
  destination menu), missing rows behind the dots, going stale when a row
  appears later, or jumping somewhere that is not the row;
- the / key opening nothing, or typing a slash into a field being taken as
  the shortcut.
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

RESULTS = """() => Array.from(el.benchResults.querySelectorAll('button'))
  .map((b) => [b.firstChild.textContent, b.querySelector('.crumb').textContent])"""

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

    def search(q):
        p.evaluate("(q) => { el.benchSearch.value = q; el.benchSearch.dispatchEvent(new Event('input')); }", q)
        return p.evaluate(RESULTS)

    print("\n--- the modulation cards (F4) ---")
    # Three cards under the screen, whatever is plugged in or patched: they
    # replaced a tab of six families, which grew a chip for every controller
    # learned (until F4b cut learning) and the photocell. So the check moves a
    # controller, turns the photocell on and routes a hearing source first -
    # each of which the old strip answered with another chip - and still
    # wants exactly three.
    cards = p.evaluate("""async () => {
      setView('bench'); setBenchTab('play');
      state.modRoutings = []; touchRoutings();
      midiControl(21, 64); setPhoto(true);
      addRouting('hear.bright', 'gen.freq');
      buildSourceChips();
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      const ids = Array.from(el.modStrip.querySelectorAll('.mod-card')).map((c) => c.dataset.source);
      // A parked source keeps its ink on its knob, to be seen and taken off there.
      const ring = document.querySelector('.mod-open[data-dest="gen.freq"]');
      const parked = { pips: ring ? ring.querySelectorAll('.pip').length : -1, empty: ring ? ring.classList.contains('empty') : null };
      state.modRoutings = []; touchRoutings();
      return { ids, parked };
    }""")
    print("    %s" % cards)
    check("three cards, LFO 1, LFO 2 and the Envelope, with a controller learned, the photocell on and a hearing source patched",
          cards["ids"] == ["lfo1", "lfo2", "env.note"], str(cards["ids"]))
    check("and a parked source on a knob still shows its ink there", cards["parked"] == {"pips": 1, "empty": False},
          str(cards["parked"]))

    # Pressed - a real press, so the drag's tap is what opens it - a card opens
    # its editor over the tab, on that source; a tab put away by going to one.
    p.locator('.mod-card[data-source="lfo2"]').click(); p.wait_for_timeout(200)
    opened = p.evaluate("""() => ({ shown: !el.modEditor.hidden, title: el.srcDetailTitle.textContent, selected: selectedSource,
      pressed: Array.from(el.modStrip.querySelectorAll('.mod-card[aria-pressed=true]')).map((c) => c.dataset.source),
      overScreen: el.modEditor.getBoundingClientRect().left < el.traceSheet.getBoundingClientRect().right,
      rate: !!document.getElementById('lfoRate1') })""")
    p.locator('#benchTab-ink').click(); p.wait_for_timeout(200)
    shut = p.evaluate("() => ({ shown: !el.modEditor.hidden, tab: benchTab, pressed: el.modStrip.querySelectorAll('.mod-card[aria-pressed=true]').length })")
    print("    %s; then %s" % (opened, shut))
    check("pressing a card opens its editor on that source, with its rate, the card marked, beside the screen rather than over it",
          opened == {"shown": True, "title": "LFO 2", "selected": "lfo2", "pressed": ["lfo2"], "overScreen": False, "rate": True},
          str(opened))
    check("null: and going to a tab puts it away", shut == {"shown": False, "tab": "ink", "pressed": 0}, str(shut))

    print("\n--- the editor ---")
    detail = p.evaluate("""async () => {
      registerSource({ id: 'test.meter', label: 'Test meter', ink: 'ch4', family: 'signal',
                       description: 'Only for the test.', bipolar: true, value: () => window.__v });
      window.__v = 0.3;
      openModCard('lfo1');
      selectSource('test.meter');
      const read = () => { updateSourceMeter();
        const f = document.getElementById('srcMeter');
        return [parseFloat(f.style.left), parseFloat(f.style.width), document.getElementById('srcMeterValue').textContent]; };
      const up = read();
      window.__v = -0.5;
      const down = read();
      const out = { title: el.srcDetailTitle.textContent, desc: el.srcDetail.querySelector('.src-desc').textContent,
                    focus: focusSource, up, down };
      addRouting('test.meter', 'view.rotate');
      // The panel follows on the next frame, the way every routing change
      // repaints, rather than inside the call.
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      out.offered = Array.from(document.getElementById('srcDetail-add').options).map((o) => o.value);
      out.rows = Array.from(el.srcDetail.querySelectorAll('.mod-edit')).map((r) => r.dataset.dest);
      out.columns = Array.from(el.srcDetail.children).map((c) => c.className);
      state.modRoutings = []; touchRoutings();
      MOD_SOURCES.delete('test.meter');
      closeModCard();
      return out;
    }""")
    print("    %s" % detail)
    check("the editor shows the source chosen, and focuses it for every control",
          detail["title"] == "Test meter" and detail["desc"] == "Only for the test."
          and detail["focus"] == "test.meter", str(detail))
    check("in two columns: its own controls, and where it goes", detail["columns"] == ["src-own", "src-goes"],
          str(detail["columns"]))
    check("the meter reads the source: a bipolar +0.3 grows right from the middle",
          abs(detail["up"][0] - 50) < 0.01 and abs(detail["up"][1] - 15) < 0.01 and detail["up"][2] == "+0.30",
          str(detail["up"]))
    check("and -0.5 grows left from it",
          abs(detail["down"][0] - 25) < 0.01 and abs(detail["down"][1] - 25) < 0.01 and detail["down"][2] == "-0.50",
          str(detail["down"]))
    check("a destination it is on is a row, and is not offered again",
          detail["rows"] == ["view.rotate"] and "view.rotate" not in detail["offered"]
          and "gen.freq" in detail["offered"], str(detail))

    # The control's own editor, opened from its ring, offers the three and
    # nothing else: before F4 it listed every source a hand could route.
    offer = p.evaluate("""async () => {
      setBenchTab('play'); state.modRoutings = []; touchRoutings();
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      const ring = document.querySelector('.mod-open[data-dest="gen.freq"]');
      ring.click();
      await new Promise((r) => setTimeout(r, 100));
      const ids = Array.from(document.querySelectorAll('.mod-add-one')).map((b) => b.dataset.add);
      closeOverlay();
      return ids;
    }""")
    check("a control's own editor offers the three cards' sources and no others", offer == ["lfo1", "lfo2", "env.note"], str(offer))
    # A controller could be forgotten from its own panel, until F4b cut
    # learning: the null now is that moving one registered nothing.
    cc = p.evaluate("() => [...MOD_SOURCES.keys()].filter((id) => id.startsWith('cc.'))")
    check("a controller moved is not learned as a source", cc == [], str(cc))

    print("\n--- reaching any control ---")
    reach = p.evaluate("""() => {
      setView('scope'); setMenuOpen(false);
      setBenchTab('play');
      showControl('planeMirror');
      const bench = { view: document.body.dataset.view, tab: benchTab, seen: el.planeMirror.offsetWidth > 0 };
      setView('scope');
      showControl('filterCutoff');
      const measure = { view: document.body.dataset.view, open: !el.measurePanel.hidden,
                        seen: el.filterCutoff.offsetWidth > 0 };
      setMeasureOpen(false);
      setView('scope');
      showControl('midiConnect');
      const settings = { view: document.body.dataset.view, open: !el.menuPanel.hidden,
                         seen: el.midiConnect.offsetWidth > 0 };
      setMenuOpen(false);
      return { bench, measure, settings };
    }""")
    # The plane's mirror, on Space & Memory from Play: a control on another
    # tab. (It was the arpeggiator in the drawer until F3 took Perform to the
    # header, and the trace filter until F1 took the Measure tab away.)
    check("a Bench control opens the Bench on its tab", reach["bench"] == {"view": "bench", "tab": "space", "seen": True},
          str(reach["bench"]))
    check("a scope's tool opens Scope & measure over the view you were in",
          reach["measure"] == {"view": "scope", "open": True, "seen": True}, str(reach["measure"]))
    check("and a setting opens Settings over the view you were in",
          reach["settings"] == {"view": "scope", "open": True, "seen": True}, str(reach["settings"]))

    print("\n--- search ---")
    p.evaluate("() => setView('scope')")
    p.keyboard.press("/"); p.wait_for_timeout(200)
    slash = p.evaluate("() => ({ view: document.body.dataset.view, focus: document.activeElement.id })")
    check("/ from Scope opens the Bench with the search box focused",
          slash == {"view": "bench", "focus": "benchSearch"}, str(slash))
    p.keyboard.type("a/b"); p.wait_for_timeout(100)
    check("and a slash typed into it is a slash, not the shortcut",
          p.evaluate("el.benchSearch.value") == "a/b", p.evaluate("el.benchSearch.value"))

    cutoff = search("cutoff")
    check("the Sources panel's destination menu is not searched as rows: cutoff is the Filter's",
          cutoff == [["Cutoff", "Scope & measure \u203a Filter"]], str(cutoff))
    notch = search("notch")
    # Two since the voice filter (H3): its Type offers a notch too.
    check("but a menu's own choices find it: notch is a type of the trace's filter and of the voice's",
          sorted(notch) == [["Type", "Scope & measure \u203a Filter"], ["Type", "Voice filter"]], str(notch))
    adsr = search("adsr")
    # The Envelope source comes after them, fairly: its description names them.
    # On show in the Generator since F3, no longer behind its dots.
    check("synonyms: adsr is the four envelope times first, on show in the Generator",
          [r[0] for r in adsr[:4]] == ["Attack", "Decay", "Sustain", "Release"]
          and all(r[1] == "Generator" for r in adsr[:4]), str(adsr))
    rate = search("rate")
    check("a word is matched at its start: rate is not the middle of another word",
          all(" rate" in (" " + r[0].lower()) or r[1] == "Modulation" for r in rate) and rate != [],
          str(rate))
    top = search("zoom")
    # The zoom left the strip for Scope & measure in F1, and is found there.
    check("the strip along the top is searched too, and what left it for Scope & measure",
          ["Zoom", "Scope & measure \u203a Time"] in top and ["Persistence", "Picture"] in search("persistence"),
          str(top) + " " + str(search("persistence")[:2]))

    stale = p.evaluate("""() => { setMidiMode('dyad'); return null; }""")
    dyad = search("draw")
    p.evaluate("() => { setScreenKeys(true); setMidiMode('poly'); }")
    poly = search("draw")
    p.evaluate("() => { setMidiMode('dyad'); setScreenKeys(false); }")
    check("the index is read when the search runs: poly's Draw row is found once it exists",
          not any(r[0] == "Draw" for r in dyad) and any(r[0] == "Draw" for r in poly), str((dyad, poly)))
    # The photocell's source, which came and went with its switch and was
    # found while it was there ("a source is found only while it exists").
    # Since F4 only the three cards' sources are searched: the photocell's is
    # parked, so it is found neither way, and the cards' are found always.
    p.evaluate("() => setPhoto(true)")
    back = search("photocell")
    p.evaluate("() => setPhoto(false)")
    lfo = search("lfo")
    check("only the cards' sources are searched: the photocell's is not, with it on, and both oscillators are",
          not any(r[1] == "Modulation" for r in back) and [r for r in lfo if r[1] == "Modulation"] == [["LFO 1", "Modulation"], ["LFO 2", "Modulation"]],
          str((back, lfo)))

    jump = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      // The plane's shear, under its module's arrow in the rack, from Play:
      // the attack was the row until F3 put the envelope on show, and until
      // F5 the shear was behind its section's dots.
      setBenchTab('play');
      el.benchSearch.focus();
      el.benchSearch.value = 'shear'; el.benchSearch.dispatchEvent(new Event('input'));
      el.benchSearch.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      await wait(200);
      const module = el.planeShear.closest('.fx-module');
      const attack = { tab: benchTab, open: module.dataset.open !== undefined && !el.planeShear.closest('.fx-rest').hidden,
                       focus: document.activeElement.id, hit: !!document.querySelector('.search-hit') };
      openFx(null);
      el.benchSearch.focus();
      el.benchSearch.value = 'device'; el.benchSearch.dispatchEvent(new Event('input'));
      el.benchSearch.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      await wait(200);
      const device = { open: !el.menuPanel.hidden, row: !!document.querySelector('#deviceRow.search-hit') };
      setMenuOpen(false);
      el.benchSearch.focus();
      el.benchSearch.value = 'lfo'; el.benchSearch.dispatchEvent(new Event('input'));
      el.benchSearch.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
      el.benchSearch.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      await wait(200);
      const lfo = { editor: !el.modEditor.hidden, selected: selectedSource };
      closeModCard();
      el.benchSearch.focus();
      el.benchSearch.value = 'zoom'; el.benchSearch.dispatchEvent(new Event('input'));
      el.benchSearch.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
      const esc = { value: el.benchSearch.value, hidden: el.benchResults.hidden };
      return { attack, device, lfo, esc };
    }""")
    print("    %s" % jump)
    check("a row under a module's arrow: its tab, its module open, the control focused",
          jump["attack"] == {"tab": "space", "open": True, "focus": "planeShear", "hit": True}, str(jump["attack"]))
    check("a setting: Settings open, the row marked", jump["device"] == {"open": True, "row": True}, str(jump["device"]))
    check("arrow down then Enter chooses the second result: LFO 2, its card's editor open",
          jump["lfo"] == {"editor": True, "selected": "lfo2"}, str(jump["lfo"]))
    check("Escape clears the box and puts the list away",
          jump["esc"] == {"value": "", "hidden": True}, str(jump["esc"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("every source explained, every control reachable, and found by name")
