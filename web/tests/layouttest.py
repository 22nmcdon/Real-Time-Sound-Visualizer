"""The layout revamp: the Sources tab, reaching any control, and search.

What would go wrong, and what is checked for it:

- a family with nothing in it vanishing instead of saying how to get
  something, or a source appearing under the wrong family;
- the detail panel describing one source and editing another, or its meter
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

    print("\n--- the Sources tab: families ---")
    fam = p.evaluate("""() => {
      setView('bench'); setBenchTab('sources');
      state.modRoutings = []; touchRoutings(); sourceFamily = null; buildSourceGrid();
      const list = () => ({ family: el.srcList.dataset.family, title: el.srcListTitle.textContent,
        rows: Array.from(el.srcList.querySelectorAll('[data-select]')).map((c) => c.dataset.select),
        hint: (el.srcList.querySelector('.src-empty') || { textContent: '' }).textContent });
      const families = () => Array.from(el.srcFamilies.querySelectorAll('[data-family]')).map((f) => ({
        id: f.dataset.family, empty: f.dataset.empty === '1', count: Number(f.querySelector('.count').textContent) }));
      const show = (id) => { chooseSourceFamily(id); return list(); };
      const out = { opened: el.srcList.dataset.family, order: families() };
      out.before = {};
      for (const id of ['oscillators', 'signal', 'controllers', 'picture', 'inuse']) out.before[id] = show(id);
      out.chosen = { family: 'signal', selected: (show('signal'), selectedSource), title: el.srcDetailTitle.textContent };
      midiLearn(21);
      setPhoto(true);
      out.after = { controllers: show('controllers'), picture: show('picture') };
      addRouting('lfo2', 'view.rotate'); touchRoutings();
      out.inuse = show('inuse');
      sourceFamily = null; buildSourceGrid();
      out.reopened = el.srcList.dataset.family;
      selectSource('hear.bright');
      out.brought = { family: sourceFamily, pressed: (el.srcList.querySelector('[aria-pressed=true]') || {}).dataset };
      out.brought.pressed = out.brought.pressed ? out.brought.pressed.select : null;
      state.modRoutings = []; touchRoutings();
      return out;
    }""")
    print("    opened on %s; order %s" % (fam["opened"], [(f["id"], f["count"]) for f in fam["order"]]))
    print("    before: %s" % {k: (v["rows"] or v["hint"][:40]) for k, v in fam["before"].items()})
    check("the families come in their order, In use first and the macros last, one list",
          [f["id"] for f in fam["order"]] == ["inuse", "oscillators", "signal", "hearing", "keyboard",
                                             "controllers", "picture", "macros"],
          str([f["id"] for f in fam["order"]]))
    check("with nothing patched it opens on the chosen source's family, the oscillators",
          fam["opened"] == "oscillators", fam["opened"])
    bf = fam["before"]
    check("each family's sources are its own, one family on show at a time",
          bf["oscillators"]["rows"] == ["lfo1", "lfo2"] and bf["signal"]["rows"] == ["env.live", "env.note", "threshold"]
          and bf["signal"]["title"] == "Signal", str(bf))
    check("an empty family is listed, quieter, and says how to get something when chosen",
          bf["controllers"]["rows"] == [] and "keyboard" in bf["controllers"]["hint"]
          and bf["picture"]["rows"] == [] and "Photocell" in bf["picture"]["hint"]
          and {f["id"]: f["empty"] for f in fam["order"]}["controllers"] is True
          and {f["id"]: f["empty"] for f in fam["order"]}["oscillators"] is False, str(bf))
    check("choosing a family shows its first source beside it, not whatever was chosen before",
          fam["chosen"]["selected"] == "env.live" and fam["chosen"]["title"] == "Level", str(fam["chosen"]))
    a = fam["after"]
    check("and a family fills when there is something: a controller learned, the photocell on",
          a["controllers"]["rows"] == ["cc.21"] and "photo.1" in a["picture"]["rows"]
          and "picture.bored" in a["picture"]["rows"] and a["controllers"]["hint"] == "", str(a))
    check("In use is empty and says so until something is patched, and then lists only that",
          bf["inuse"]["rows"] == [] and "patched" in bf["inuse"]["hint"] and fam["inuse"]["rows"] == ["lfo2"],
          str((bf["inuse"], fam["inuse"])))
    check("with something patched the tab opens on In use", fam["reopened"] == "inuse", fam["reopened"])
    check("a source chosen from elsewhere brings its family with it, and is the one pressed",
          fam["brought"] == {"family": "hearing", "pressed": "hear.bright"}, str(fam["brought"]))

    meters = p.evaluate("""() => {
      registerSource({ id: 'test.row', label: 'Test row', ink: 'ch4', family: 'signal',
                       description: 'Only for the test.', bipolar: false, value: () => window.__r });
      window.__r = 0.8; chooseSourceFamily('signal'); updateSourceMeter();
      const fill = () => parseFloat(el.srcList.querySelector('[data-select="test.row"] .src-meter-fill').style.width);
      const high = fill();
      window.__r = 0.2; updateSourceMeter();
      const low = fill();
      MOD_SOURCES.delete('test.row'); buildSourceGrid();
      return { high, low };
    }""")
    check("each row's meter reads its own source, every frame: 0.8 is 80 per cent, then 0.2 is 20",
          abs(meters["high"] - 80) < 0.01 and abs(meters["low"] - 20) < 0.01, str(meters))

    print("\n--- the Sources tab: the one selected ---")
    detail = p.evaluate("""async () => {
      registerSource({ id: 'test.meter', label: 'Test meter', ink: 'ch4', family: 'signal',
                       description: 'Only for the test.', bipolar: true, value: () => window.__v });
      window.__v = 0.3;
      chooseSourceFamily('signal');
      document.querySelector('#srcList [data-select="test.meter"]').click();
      const read = () => { updateSourceMeter();
        const f = document.getElementById('srcMeter');
        return [parseFloat(f.style.left), parseFloat(f.style.width), document.getElementById('srcMeterValue').textContent]; };
      const up = read();
      window.__v = -0.5;
      const down = read();
      const out = { title: el.srcDetailTitle.textContent, desc: el.srcDetail.querySelector('.src-desc').textContent,
                    focus: focusSource, up, down,
                    pressed: document.querySelector('#srcList [aria-pressed=true]').dataset.select };
      addRouting('test.meter', 'view.rotate');
      // The panel follows on the next frame, the way every routing change
      // repaints, rather than inside the call.
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      out.offered = Array.from(document.getElementById('srcDetail-add').options).map((o) => o.value);
      out.rows = Array.from(el.srcDetail.querySelectorAll('.mod-edit')).map((r) => r.dataset.dest);
      state.modRoutings = []; touchRoutings();
      MOD_SOURCES.delete('test.meter');
      return out;
    }""")
    print("    %s" % detail)
    check("choosing a chip shows that source, and focuses it for every control",
          detail["title"] == "Test meter" and detail["desc"] == "Only for the test."
          and detail["focus"] == "test.meter" and detail["pressed"] == "test.meter", str(detail))
    check("the meter reads the source: a bipolar +0.3 grows right from the middle",
          abs(detail["up"][0] - 50) < 0.01 and abs(detail["up"][1] - 15) < 0.01 and detail["up"][2] == "+0.30",
          str(detail["up"]))
    check("and -0.5 grows left from it",
          abs(detail["down"][0] - 25) < 0.01 and abs(detail["down"][1] - 25) < 0.01 and detail["down"][2] == "-0.50",
          str(detail["down"]))
    check("a destination it is on is a row, and is not offered again",
          detail["rows"] == ["view.rotate"] and "view.rotate" not in detail["offered"]
          and "gen.freq" in detail["offered"], str(detail))
    cc = p.evaluate("""() => {
      selectSource('cc.21');
      const name = document.getElementById('srcDetail-name');
      const had = !!name && !!document.getElementById('srcDetail-forget');
      document.getElementById('srcDetail-forget').click();
      return { had, gone: !MOD_SOURCES.has('cc.21'), selected: selectedSource, focus: focusSource };
    }""")
    check("a controller can be forgotten from its own panel", cc["had"] and cc["gone"], str(cc))
    check("and the panel falls back to an oscillator rather than a source that has gone",
          cc["selected"] == "lfo1" and cc["focus"] is None, str(cc))

    print("\n--- reaching any control ---")
    reach = p.evaluate("""() => {
      setView('scope'); setMenuOpen(false);
      showControl('filterCutoff');
      const bench = { view: document.body.dataset.view, tab: benchTab,
                      seen: el.filterCutoff.offsetWidth > 0 };
      setView('scope');
      showControl('midiConnect');
      const settings = { view: document.body.dataset.view, open: !el.menuPanel.hidden,
                         seen: el.midiConnect.offsetWidth > 0 };
      setMenuOpen(false);
      return { bench, settings };
    }""")
    check("a Bench control opens the Bench on its tab", reach["bench"] == {"view": "bench", "tab": "picture", "seen": True},
          str(reach["bench"]))
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
          cutoff == [["Cutoff", "Filter"]], str(cutoff))
    notch = search("notch")
    # Two since the voice filter (H3): its Type offers a notch too.
    check("but a menu's own choices find it: notch is a type of the trace's filter and of the voice's",
          sorted(notch) == [["Type", "Filter"], ["Type", "Voice filter"]], str(notch))
    adsr = search("adsr")
    # The Envelope source comes after them, fairly: its description names them.
    check("synonyms: adsr is the four envelope times first, behind the Generator's dots",
          [r[0] for r in adsr[:4]] == ["Attack", "Decay", "Sustain", "Release"]
          and all("behind" in r[1] for r in adsr[:4]), str(adsr))
    rate = search("rate")
    check("a word is matched at its start: rate is not the middle of another word",
          all(" rate" in (" " + r[0].lower()) or r[1].startswith("Sources") for r in rate) and rate != [],
          str(rate))
    top = search("zoom")
    check("the strip along the top is searched too", ["Zoom", "Along the top"] in top, str(top))

    stale = p.evaluate("""() => { setMidiMode('dyad'); return null; }""")
    dyad = search("draw")
    p.evaluate("() => { setScreenKeys(true); setMidiMode('poly'); }")
    poly = search("draw")
    p.evaluate("() => { setMidiMode('dyad'); setScreenKeys(false); }")
    check("the index is read when the search runs: poly's Draw row is found once it exists",
          not any(r[0] == "Draw" for r in dyad) and any(r[0] == "Draw" for r in poly), str((dyad, poly)))
    p.evaluate("() => setPhoto(false)")
    gone = search("boredom")
    p.evaluate("() => setPhoto(true)")
    back = search("boredom")
    check("and a source is found only while it exists",
          gone == [] and back == [["Boredom", "Sources › Picture"]], str((gone, back)))

    jump = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setBenchTab('picture');
      el.benchSearch.focus();
      el.benchSearch.value = 'attack'; el.benchSearch.dispatchEvent(new Event('input'));
      el.benchSearch.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      await wait(200);
      const attack = { tab: benchTab, overlay: !!document.querySelector('.over #envAttack'),
                       focus: document.activeElement.id, hit: !!document.querySelector('.search-hit') };
      closeOverlay();
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
      const lfo = { tab: benchTab, selected: selectedSource };
      el.benchSearch.focus();
      el.benchSearch.value = 'zoom'; el.benchSearch.dispatchEvent(new Event('input'));
      el.benchSearch.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
      const esc = { value: el.benchSearch.value, hidden: el.benchResults.hidden };
      return { attack, device, lfo, esc };
    }""")
    print("    %s" % jump)
    check("a row behind the dots: its tab, its section's detail open, the control focused",
          jump["attack"] == {"tab": "play", "overlay": True, "focus": "envAttack", "hit": True}, str(jump["attack"]))
    check("a setting: Settings open, the row marked", jump["device"] == {"open": True, "row": True}, str(jump["device"]))
    check("arrow down then Enter chooses the second result: LFO 2, on the Sources tab",
          jump["lfo"] == {"tab": "sources", "selected": "lfo2"}, str(jump["lfo"]))
    check("Escape clears the box and puts the list away",
          jump["esc"] == {"value": "", "hidden": True}, str(jump["esc"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("every source explained, every control reachable, and found by name")
