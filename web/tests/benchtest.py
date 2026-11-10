"""The Bench and Settings: every section in its home, the Bench as tabs.

Each section lives in one place - Settings for what is set once, the Bench for
everything played - and the Bench shows one task's sections at a time. The
Bench is the one face since G4 (the Scope view went; Enlarge took its frame),
so what this held "in both views" it now holds on the face and after the
screen has been to Enlarge and back, which is the one move left. The thing most likely to go wrong is still duplication - a control copied into
the bench instead of moved gives two elements one id, and getElementById
silently returns the first. That has already cost this page one readout line,
so it is the first thing asserted.
"""
import os, sys
from playwright.sync_api import sync_playwright
import corpus

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
SHOTS = os.path.join(HERE, "shots")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
os.makedirs(SHOTS, exist_ok=True)

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

DUPES = """() => {
  const seen = new Map(), dupes = [];
  for (const node of document.querySelectorAll('[id]')) {
    if (seen.has(node.id)) dupes.push(node.id); else seen.set(node.id, node);
  }
  return dupes;
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    corpus.install(p)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    print("\n--- one node per control, on the face and through Enlarge ---")
    check("no duplicate ids on the face", p.evaluate(DUPES) == [], str(p.evaluate(DUPES)))
    p.locator("#enlargeButton").click(); p.wait_for_timeout(400)
    check("no duplicate ids with the screen enlarged", p.evaluate(DUPES) == [], str(p.evaluate(DUPES)))
    p.keyboard.press("Escape"); p.wait_for_timeout(300)

    # Every section has a home and stays in it: Settings holds what is set
    # once and left, the Bench everything played. Read on the face and again
    # after Enlarge (the old Scope view's round trip, since G4): Scope & measure
    # travels with the screen, so its sections are the ones that could be left
    # behind in the frame.
    homes = p.evaluate("""() => {
      const where = () => settingsGroups().map((g) => ({
        title: groupTitle(g), home: g.dataset.home,
        // In Settings' panel, in one of its two columns since F7b.
        inPanel: !!g.closest('#menuPanel'), inMeasure: !!g.closest('#measurePanel'),
        // Routings (G5a) is over the tabs, inside the Bench, and is a home of its own.
        inRoutings: !!g.closest('#routingsPanel'),
        onBench: !!g.closest('#bench') && !g.closest('#measurePanel') && !g.closest('#routingsPanel') }));
      const bench = where();
      setEnlarged(true); setEnlarged(false);
      const back = where();
      return { bench, back,
               panelTitles: Array.from(el.menuPanel.querySelectorAll('.settings-col > .menu-group')).map(groupTitle) };
    }""")
    misplaced = [g["title"] + " in " + when for when in ("bench", "back") for g in homes[when]
                 if (g["home"] == "settings") != g["inPanel"] or (g["home"] == "bench") != g["onBench"]
                 or (g["home"] == "measure") != g["inMeasure"] or (g["home"] == "routings") != g["inRoutings"]]
    check("every section is in its home, on the face and after Enlarge and back", misplaced == [], str(misplaced))
    # F1 (redesigning-the-face.md): the scope's own tools are Scope & measure's,
    # a panel over the screen in either view - the null is the P8 drawer's tab.
    measured = sorted(g["title"] for g in homes["bench"] if g["inMeasure"])
    check("Scope & measure holds the scope's tools: lanes, vertical, filter, trigger and measure",
          measured == ["Filter", "Lanes", "Measure", "Trigger", "Vertical"], str(measured))
    # F2: what Scan reads and the score behind the Picture's Advanced.
    pictured = p.evaluate("""() => settingsGroups().filter((g) => g.closest('#picturePanel')).map(groupTitle).sort()""")
    # And the beam's ink since F7b, as only the look.
    check("the Picture's Advanced holds what Scan reads, the score and the beam", pictured == ["Beam", "Score", "What Scan reads"], str(pictured))
    performed = p.evaluate("""() => settingsGroups().filter((g) => g.closest('#performPanel')).map(groupTitle).sort()""")
    check("the header's Perform menu holds the arpeggiator, the clock, the key and tempo and the morph",
          performed == ["Arpeggiator", "Clock", "Key and tempo", "Morph"], str(performed))
    check("Settings holds only the settings: MIDI, audio, the inputs (since F3) and this window (F7b)",
          # Presets left in F6, for the preset browser's footer; the beam in
          # F7b, for the Picture's Advanced; the modulation fade, there from
          # F4, in G5a, for Routings.
          sorted(homes["panelTitles"]) == ["Audio", "Input", "Input into the generator", "MIDI", "This window"],
          str(homes["panelTitles"]))
    routed = sorted(g["title"] for g in homes["bench"] if g["inRoutings"])
    check("Routings holds the fade (G5a)", routed == ["Fade"], str(routed))
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(300)
    check("and Settings opens from the face", p.evaluate("getComputedStyle(el.menuButton).display !== 'none'"))
    check("still no duplicates after a round trip", p.evaluate(DUPES) == [])
    dev = p.evaluate("() => ({ shown: !el.deviceRow.hidden, disabled: el.device.disabled, why: el.device.title })")
    check("the device picker is there over the tone, greyed with the reason",
          dev["shown"] and dev["disabled"] and "Mic" in dev["why"], str(dev))

    print("\n--- no drawer (F4) ---")
    # The routing matrix was behind one switch from P3, Advanced, which took
    # the Sources tab, the chips beside the screen and the hollow rings with it
    # while shut. F4 put each of its tabs somewhere of its own and the matrix
    # in the modulation cards, so the switch went. What it guarded still holds:
    # what is patched plays and keeps its inks; and a control with nothing on
    # it keeps its ring in place, unseen until the control is pointed at.
    drawer = p.evaluate("""() => {
      const rail = () => Array.from(el.benchRail.querySelectorAll('[role=tab]')).map((b) => b.querySelector('.tab-name').textContent);
      const shown = (node) => !!(node && node.offsetParent);
      const ring = (dest) => document.querySelector('.mod-open[data-dest="' + dest + '"]');
      // Ink: Frequency's tab since G3.
      setBenchTab('ink');
      state.modRoutings = []; addRouting('lfo1', 'gen.freq'); touchRoutings(); paintRoutings();
      return { rail: rail(), switch: document.getElementById('benchDrawer'), attr: document.body.dataset.drawer || null,
               attached: shown(ring('gen.freq')) && getComputedStyle(ring('gen.freq')).opacity === '1',
               heard: routingsHeard().filter((r) => r.sourceId === 'lfo1').map((r) => r.destId) };
    }""")
    p.wait_for_timeout(200)
    # The empty ring at rest, then with the pointer on its control: a real hover.
    rest = p.evaluate("() => getComputedStyle(document.querySelector('[data-mod-dest=\"gen.amp\"] .mod-open')).opacity")
    p.locator('[data-mod-dest="gen.amp"]').first.hover(); p.wait_for_timeout(300)
    pointed = p.evaluate("() => getComputedStyle(document.querySelector('[data-mod-dest=\"gen.amp\"] .mod-open')).opacity")
    p.mouse.move(5, 5); p.evaluate("() => { state.modRoutings = []; touchRoutings(); }")
    print("    %s; empty ring at rest %s, pointed at %s" % (drawer, rest, pointed))
    loop_tabs = ["Play", "Ink", "Space & Memory"]
    check("no drawer: the loop's three tabs, and no Advanced switch", drawer["rail"] == loop_tabs
          and drawer["switch"] is None and drawer["attr"] is None, str(drawer))
    check("a patched control keeps its inks, and what is patched is heard",
          drawer["attached"] and drawer["heard"] == ["gen.freq"], str(drawer))
    check("an empty control's ring is unseen at rest and seen when the control is pointed at",
          rest == "0" and pointed == "1", "%s / %s" % (rest, pointed))
    # The arpeggiator, moved to the drawer in P5: on Perform and not on Play,
    # reached from anywhere by showControl, which opens the drawer, and still
    # playing a held chord with the drawer shut, as everything patched does.
    # The null is the same chord with the arpeggiator off, which is not one.
    arp = p.evaluate("""() => {
      const shown = (node) => !!(node && node.offsetParent);
      const out = {};
      setBenchTab('play'); out.onPlay = shown(el.arpMode);
      showControl('arpMode'); out.shown = { menu: !el.performPanel.hidden, seen: shown(el.arpMode) };
      el.arpMode.value = 'up'; el.arpMode.dispatchEvent(new Event('change'));
      setPerformOpen(false);
      for (const n of [48, 52, 55]) midiNoteOn(n, 100);
      out.running = arpActive();
      for (const n of [48, 52, 55]) midiNoteOff(n);
      el.arpMode.value = 'off'; el.arpMode.dispatchEvent(new Event('change'));
      for (const n of [48, 52, 55]) midiNoteOn(n, 100);
      out.offRunning = arpActive();
      for (const n of [48, 52, 55]) midiNoteOff(n);
      return out;
    }""")
    print("    arpeggiator: %s" % arp)
    # In the header's Perform menu since F3, the drawer's tab before that.
    check("the arpeggiator is in the header's Perform menu, not on Play, and showing it opens that menu",
          arp["onPlay"] is False and arp["shown"] == {"menu": True, "seen": True}, str(arp))
    check("and with the menu shut it still plays a held chord, where switched off it does not",
          arp["running"] is True and arp["offRunning"] is False, str(arp))

    # The drawings and the second generator: in the drawer from P5, offered
    # by no menu from F2 (a loaded one stayed chosen, offered and drawn), and
    # cut in G2. So there is no Kind menu and no From - the Input menu beside
    # where From was is the null, which shows the lookup can find a menu -
    # and a drawing loaded from the old library loads as the waveform, with
    # none of a drawing's rows. A search for one finds nothing, where a
    # search for the attack finds it. (The tempo was a null here until P8 put
    # Key and tempo in the drawer, where a search for it rightly opens it.)
    drawings = p.evaluate("""() => {
      const out = {};
      const has = (id) => !!document.getElementById(id);
      out.menus = { kind: has('genMode'), from: has('inputFrom'), input: has('inputMode') };
      // The old library's harmonograph, from before P8g: the bank never had
      // a drawing, and this asks what a code that names one becomes.
      // What the code says it is, against what it loaded as: the decode pass's
      // answer, since the snapshot writes the waveform whatever played.
      const loaded = loadCorpus('Harmonograph');
      out.loaded = { was: corpusSetup('Harmonograph').gen, kind: loaded.gen,
                     rows: ['harmoRows', 'figureRows', 'wireRows', 'traceRateRow', 'gen2Rows'].filter(has) };
      const search = (q) => { el.benchSearch.value = q; showSearch(); const first = searchShown[0];
                              chooseSearch(first); const menu = !el.performPanel.hidden;
                              setPerformOpen(false); closeModCard();
                              return { found: first ? first.label : null, menu }; };
      out.searchDrawing = search('harmonograph');
      out.searchAttack = search('attack');
      out.searchTempo = search('tempo');
      return out;
    }""")
    print("    drawings: %s" % drawings)
    # Out of reach from 7 Nov, the owner's call, to see whether they were
    # missed; they were not, and went on 9 Nov.
    check("the generator has no Kind menu and its input no From: the drawings and the second generator are gone",
          drawings["menus"] == {"kind": False, "from": False, "input": True}, str(drawings["menus"]))
    check("a drawing's code from the old library loads as the waveform, with no drawing's rows",
          drawings["loaded"] == {"was": "harmonograph", "kind": "wave", "rows": []}, str(drawings["loaded"]))
    check("and a search for one finds nothing, where a search finds the attack",
          drawings["searchDrawing"]["found"] is None and drawings["searchAttack"]["found"] is not None, str(drawings))
    check("and a search for the tempo, in the header's Perform menu since F3, opens that",
          drawings["searchTempo"]["menu"] is True and drawings["searchTempo"]["found"] == "Tempo", str(drawings))

    # The clock and the bar, on Perform since P5; the tempo and Tap with them
    # since P8 took Key and tempo off the old Measure tab. The null is Tap
    # beside the tempo, which has always been so and would not be if the
    # section had been split on the way.
    clock = p.evaluate("""() => {
      const tab = (id) => { const g = document.getElementById(id).closest('.menu-group'); return g ? homeOf(g) : null; };
      return { clockFrom: tab('clockFrom'), bar: tab('transportPlay'), at: tab('transportAt'), tempo: tab('tempo'),
               tapBesideTempo: el.tempoTap.closest('.menu-row') === el.tempo.closest('.menu-row') };
    }""")
    check("the clock's source, the bar, and the tempo with Tap beside it are all in the Perform menu",
          clock == {"clockFrom": "perform", "bar": "perform", "at": "perform", "tempo": "perform", "tapBesideTempo": True},
          str(clock))
    hidden = p.evaluate("""() => {
      const chips = [...el.modStrip.querySelectorAll('.mod-card')].map((c) => c.dataset.source);
      el.benchSearch.value = 'glow'; el.benchSearch.dispatchEvent(new Event('input'));
      const found = [...el.benchResults.querySelectorAll('button')].map((b) => b.textContent);
      el.benchSearch.value = ''; el.benchSearch.dispatchEvent(new Event('input'));
      return { chips: chips.filter((id) => id.startsWith('stage.')), lfo: chips.includes('lfo1'), found };
    }""")
    # The Photocell's switch is in its card's editor since G5a, as On; it
    # was in the Picture's Advanced from F2, and with the drawer before. It
    # is there whatever the photocell is doing, and the null is the same
    # switch with the editor shut, out of sight - and the Picture's Advanced
    # open, which no longer holds it.
    cell = p.evaluate("""() => {
      const shown = () => !!el.photoButton.offsetParent;
      const out = {};
      openModCard('photo.1');
      setPhoto(false); out.openOff = shown();
      setPhoto(true); out.openOn = shown();
      setPhoto(false);
      closeModCard(); setPictureOpen(true); out.advanced = shown();
      setPictureOpen(false); out.closed = shown();
      return out;
    }""")
    check("the Photocell's switch is in its card's editor whatever the photocell, and out of sight with it shut",
          cell == {"openOff": True, "openOn": True, "advanced": False, "closed": False}, str(cell))
    check("the stage's reads are not offered by hand: no card, and not found by a search",
          hidden["chips"] == [] and hidden["lfo"] and not any("Glow" in f for f in hidden["found"]), str(hidden))

    print("\n--- the tabs ---")
    # Tabs again, on the evidence: the rail was a table of contents with every
    # section on show at once, and a rack could not fit that way. With the
    # drawer open, so its tab is walked too.
    tabs = p.evaluate("""() => {
      const titles = Array.from(el.benchRail.querySelectorAll('[role=tab]')).map((b) => b.querySelector('.tab-name').textContent);
      const seen = {}, wrong = [];
      for (const button of el.benchRail.querySelectorAll('[role=tab]')) {
        button.click();
        const id = button.dataset.tab;
        const shown = Array.from(el.benchBody.querySelectorAll('.menu-group'))
          .filter((g) => g.dataset.off === undefined);
        for (const g of shown) {
          if (g.dataset.tab !== id) wrong.push(groupTitle(g) + ' on ' + id);
          seen[groupTitle(g)] = (seen[groupTitle(g)] || 0) + 1;
        }
        const marked = el.benchRail.querySelector('[aria-selected=true]');
        if (!marked || marked.dataset.tab !== id) wrong.push(id + ' not marked');
        if (el.benchBody.scrollHeight > el.benchBody.clientHeight + 2) wrong.push(id + ' scrolls');
      }
      const benchTitles = benchable().map(groupTitle);
      return { titles, seen, wrong, benchTitles, role: el.benchRail.getAttribute('role') };
    }""")
    print("    tabs:", ", ".join(tabs["titles"]))
    # Six since Stage H put the voice's oscillator on Shape and moved the
    # plane and the delay to Effects; the five of the loop and the drawer's
    # one, last, since P3; seven since P5 put the arpeggiator on Perform; and
    # since P8 the loop's four in its own order, the drawer's four after.
    # And three since F4 took the drawer's Sources.
    check("three tabs along the loop, and a tab list",
          tabs["titles"] == ["Play", "Ink", "Space & Memory"]
          and tabs["role"] == "tablist", str(tabs["titles"]))
    check("each tab shows its own sections and fits", tabs["wrong"] == [], str(tabs["wrong"]))
    missing = [t for t in tabs["benchTitles"] if tabs["seen"].get(t) != 1]
    check("every Bench section is on exactly one tab", missing == [], str(missing) + " " + str(tabs["seen"]))
    check("no tab holds modulation: the oscillators are cards under the screen, and the Sources tab is gone",
          "Modulation" not in tabs["seen"] and "Sources" not in tabs["seen"], str(tabs["seen"]))

    print("\n--- the cards (F3) ---")
    # Each tab a card with one line of what its stage is doing now. The values
    # are written from code with no event, as the host's knobs and a loaded
    # setup write them, so a line that only followed input events stays put
    # and fails here.
    cards = p.evaluate("""async () => {
      const line = (id) => document.getElementById('benchLine-' + id).textContent;
      const wait = () => new Promise((r) => setTimeout(r, 450));
      setBenchTab('play');
      const before = { space: line('space'), ink: line('ink'), play: line('play') };
      el.delayMix.value = '40'; echo.mix = 0.4;
      el.oscFm.value = '30';
      el.freq.value = '330';
      await wait();
      const after = { space: line('space'), ink: line('ink'), play: line('play') };
      el.delayMix.value = '0'; echo.mix = 0;
      el.oscFm.value = '0';
      el.freq.value = '220';
      await wait();
      return { before, after, back: line('space'),
               name: document.querySelector('#benchTab-space .tab-name').textContent,
               cards: [...el.benchRail.querySelectorAll('[role=tab]')].every((b) => b.querySelector('.tab-line')) };
    }""")
    print("    %s" % cards)
    check("every card has its name and a line under it", cards["cards"] and cards["name"] == "Space & Memory", str(cards))
    check("the lines follow values written with no event: the delay, FM and the pitch",
          cards["after"]["space"] == "Delay" and "FM 3.0" in cards["after"]["ink"]
          and "330 Hz" in cards["after"]["play"], str(cards))
    check("null: before they were written the lines said otherwise, and Space & Memory says Dry again after",
         cards["before"]["space"] != "Delay" and "FM off" in cards["before"]["ink"]
         and "330 Hz" not in cards["before"]["play"] and cards["back"] == "Dry", str(cards))

    # Where each section went in P8, by its title, against the owner's layout:
    # what you play, what the beam draws with, what the screen does to it, the
    # picture read back, and the drawer's. Written as the whole map so a
    # section that strays fails here by name; the null is the layout before
    # P8, which this must reject.
    homes = p.evaluate("""() => {
      const out = {};
      for (const g of benchGroupsAll()) out[groupTitle(g).replace('\u22ef', '').trim()] = g.dataset.tab;
      return out;
    }""")
    want = {"Keyboard": "play", "Generator": "play", "Voice filter": "play",
            "Oscillator": "ink", "Drawbars": "ink", "Shaping": "ink", "Drawn cycle": "ink",
            # F5 put Display, Plane and the delay's section into one rack of
            # modules, the effects in the order the sound goes through them.
            "Effects": "space",
            # The Measure tab's sections went to Scope & measure in F1; in F3
            # Inputs to Settings and Perform to the header's menu.
            }
    before_p8 = dict(want, **{"Voice filter": "shape", "Oscillator": "shape", "Drawbars": "shape",
                              "Shaping": "shape", "Drawn cycle": "shape", "Display": "picture",
                              "Plane": "effects", "Delay, chorus and phaser": "effects", "Input": "play",
                              "Input into the generator": "effects", "Lanes": "picture",
                              "Vertical": "picture", "Filter": "picture", "Trigger": "picture",
                              "Key and tempo": "measure"})
    agree = lambda m: all(homes.get(k) == v for k, v in m.items())
    stray = {k: (homes.get(k), v) for k, v in want.items() if homes.get(k) != v}
    check("each section is on the tab the P8 layout and F1 give it", agree(want), str(stray))
    check("null: the layout before P8 is not what is there", not agree(before_p8), str(homes))
    keys = p.evaluate("""() => {
      setBenchTab('play');
      const tb = el.timebase.value;
      const tab = document.getElementById('benchTab-play');
      tab.focus();
      tab.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
      return { tab: benchTab, focused: document.activeElement.id, timebase: el.timebase.value === tb };
    }""")
    check("the arrow keys walk the tabs, and do not also move the timebase",
          keys["tab"] == "ink" and keys["focused"] == "benchTab-ink" and keys["timebase"], str(keys))
    check("no section starts folded: a tab has room for all of it",
          p.evaluate("() => benchable().filter((g) => g.classList.contains('folded')).length") == 0)

    print("\n--- columns hold still ---")
    # CSS multi-column re-balanced the whole flow whenever a section changed
    # height, and the first drag of the first build teleported the control
    # being dragged into the next column. A patch must not re-deal the tab.
    steady = p.evaluate("""() => {
      setBenchTab('play');
      const cols = document.querySelectorAll('.bench-col').length;
      const where = () => Array.from(document.querySelectorAll('.bench-col'))
        .map((c) => Array.from(c.children).map((g) => groupTitle(g)).join(',')).join('|');
      const before = where();
      const x = () => Math.round(document.getElementById('freq').getBoundingClientRect().x);
      const xBefore = x();
      addRouting('lfo1', 'gen.freq');
      return { cols, before, after: where(), xBefore, xAfter: x() };
    }"""); p.wait_for_timeout(300)
    check("the body is in real columns", steady["cols"] >= 2, str(steady["cols"]))
    check("a patch does not re-deal the sections", steady["before"] == steady["after"], steady["after"])
    check("and does not move the control being patched", steady["xBefore"] == steady["xAfter"],
          "%d -> %d" % (steady["xBefore"], steady["xAfter"]))
    p.evaluate("() => { state.modRoutings = []; touchRoutings(); }")

    print("\n--- the controls still work from the bench ---")
    live = p.evaluate("""() => {
      // Scope & measure since F1, and a slider and a checkbox in it.
      setMeasureOpen(true);
      el.holdoff.value = '30';
      el.holdoff.dispatchEvent(new Event('input'));
      const a = state.holdoffMs;
      el.lagOn.checked = true;
      el.lagOn.dispatchEvent(new Event('change'));
      const b = { lag: state.lagOn, lanes: laneCount() };

      el.lagOn.checked = false; el.lagOn.dispatchEvent(new Event('change'));
      el.holdoff.value = '0'; el.holdoff.dispatchEvent(new Event('input'));
      setMeasureOpen(false);
      return { holdoff: a, lag: b };
    }""")
    check("a slider in Scope & measure drives its state", live["holdoff"] == 3.0, str(live["holdoff"]))
    check("and a checkbox does too",
          live["lag"]["lag"] is True and live["lag"]["lanes"] == 2, str(live["lag"]))

    print("\n--- the trace is live in the square ---")
    # Not "do the pixels change": a locked trigger holds the waveform still on
    # purpose, so an unchanged canvas is the instrument working. What is worth
    # asserting is that the screen really moved into the bench, that it is
    # square, that there is a trace drawn on it, and that the loop is running.
    strip = p.evaluate("""() => {
      const c = el.trace, ctx = c.getContext('2d');
      const px = ctx.getImageData(0, 0, c.width, c.height).data;
      const paper = getComputedStyle(document.documentElement)
        .getPropertyValue('--paper').trim();
      const n = parseInt(paper.slice(1), 16);
      const pr = (n >> 16) & 255, pg = (n >> 8) & 255, pb = n & 255;
      let inked = 0;
      for (let i = 0; i < px.length; i += 4) {
        if (Math.abs(px[i] - pr) + Math.abs(px[i+1] - pg) + Math.abs(px[i+2] - pb) > 18) inked++;
      }
      return { inked, pixels: px.length / 4, height: c.getBoundingClientRect().height,
               fps: state.fps };
    }""")
    # Enlarge took the Scope view's frame and its panes (G4): there the sheet is in the panes.
    p.evaluate("() => setEnlarged(true)"); p.wait_for_timeout(400)
    scope_home = p.evaluate("""() => ({
      parent: el.traceSheet.parentElement.id,
      height: el.trace.getBoundingClientRect().height,
      screenShown: getComputedStyle(document.querySelector('.screen')).display,
    })""")
    p.evaluate("() => setEnlarged(false)"); p.wait_for_timeout(400)
    bench_home = p.evaluate("""() => {
      const box = el.traceSheet.getBoundingClientRect();
      return {
        parent: el.traceSheet.parentElement.id,
        w: box.width, h: box.height,
        screenShown: getComputedStyle(document.querySelector('.screen')).display,
      };
    }""")
    check("the screen is one canvas, moved rather than copied",
          p.evaluate("() => document.querySelectorAll('#trace').length") == 1)
    check("enlarged it lives in the panes", scope_home["parent"] == "panes",
          scope_home["parent"])
    check("on the face it lives in the square", bench_home["parent"] == "benchScope",
          bench_home["parent"])
    check("and Enlarge's frame is not drawn on the face, and is while enlarged",
          bench_home["screenShown"] == "none" and scope_home["screenShown"] != "none",
          "%s / %s" % (bench_home["screenShown"], scope_home["screenShown"]))
    check("the bench screen is square",
          abs(bench_home["w"] - bench_home["h"]) <= 1,
          "%.0f x %.0f" % (bench_home["w"], bench_home["h"]))
    # "And smaller than the one it replaced" (under 3/4 of the Scope view's
    # screen) went in F3, which asks the opposite - the screen as large as
    # the window allows; it only still passed because the drawer's chips are
    # under the screen here. The wide check below holds the size now.
    check("still has a trace drawn on it", strip["inked"] > 500,
          "%d inked pixels of %d" % (strip["inked"], strip["pixels"]))
    check("at a real frame rate", strip["fps"] > 20, "%.0f fps" % strip["fps"])

    print("\n--- the oscillators survive a source that has no generator ---")
    # They used to be switched off wholesale on anything but the test tone,
    # which was right while every destination they had was a generator
    # parameter. It is wrong now: an LFO on the filter cutoff or the rotation
    # is the same patch whatever the signal came from. What withdraws on a
    # live source is the generator half of the DESTINATION list, per entry.
    # Read from the card's editor's Add menu now, which is where a
    # destination is chosen since the one-destination dropdown went.
    mod = p.evaluate("""() => {
      openModCard('lfo1');
      const options = () => Array.from(document.getElementById('srcDetail-add').options).slice(1);
      showSource('mic');                       // just the panel, no stream
      const card = el.modStrip.querySelector('[data-source="lfo1"]');
      const live = {
        off: card ? card.dataset.off : 'gone',
        hidden: card ? card.hidden || !card.offsetParent : true,
        rate: !!document.getElementById('lfoRate0'),
        genDead: options().filter((o) => o.value.startsWith('gen.')).every((o) => o.disabled),
        viewAlive: options().filter((o) => o.value.startsWith('view.')).every((o) => !o.disabled),
        some: options().filter((o) => o.value.startsWith('gen.')).length,
      };
      showSource(null);
      const tone = {
        genAlive: options().filter((o) => o.value.startsWith('gen.')).every((o) => !o.disabled),
      };
      closeModCard();
      return { live, tone };
    }""")
    check("the oscillators stay on a live source",
          mod["live"]["off"] is None and mod["live"]["hidden"] is False, str(mod["live"]))
    check("with their rate and depth still reachable", mod["live"]["rate"])
    check("generator destinations grey out instead",
          mod["live"]["genDead"] and mod["live"]["some"] > 0, str(mod["live"]))
    check("while the ones that apply stay live", mod["live"]["viewAlive"], str(mod["live"]))
    check("and the generator's come back with the tone", mod["tone"]["genAlive"],
          str(mod["tone"]))

    print("\n--- the tab is remembered, and Enlarge is not ---")
    # Ink rather than Play, which is where a forgotten tab lands. The view was
    # remembered too until G4 took the views; a page that last opened on
    # Scope has its key removed, and Enlarge is not kept past the page.
    p.evaluate("() => { setBenchTab('ink'); localStorage.setItem('scope.view', 'scope'); setEnlarged(true); }")
    p.reload(); p.wait_for_timeout(900)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    kept = p.evaluate("""() => ({ tab: benchTab, view: localStorage.getItem('scope.view'), attr: document.body.dataset.view || null,
      enlarged: document.body.dataset.enlarged !== undefined, sheet: el.traceSheet.parentElement.id })""")
    check("the tab survives a reload; the old view's key is gone, and the page opens on the face, not enlarged",
          kept == {"tab": "ink", "view": None, "attr": None, "enlarged": False, "sheet": "benchScope"}, str(kept))
    check("no errors after reload", not bad, "; ".join(bad[:3]))
    # A tab remembered from before P8 lands where its sections went, and a
    # name that never was a tab lands on Play - the null, which shows the
    # reading is the page's choice and not whatever was stored.
    landed = {}
    for stored in ("shape", "effects", "picture", "sources", "nonsense"):
        p.evaluate("(t) => window.localStorage.setItem('scope.benchTab', t)", stored)
        p.reload(); p.wait_for_timeout(700)
        if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
        landed[stored] = p.evaluate("() => benchTab")
    check("a tab remembered from before P8 lands where its sections went: Shape on Ink, Effects on Space & Memory",
          landed["shape"] == "ink" and landed["effects"] == "space" and landed["picture"] == "play"
          and landed["sources"] == "play", str(landed))
    check("null: a stored name that was never a tab lands on Play", landed["nonsense"] == "play", str(landed))
    p.evaluate("() => setBenchTab('space')")
    p.screenshot(path=f"{SHOTS}/bench-wide.png")

    print("\n--- wide ---")
    # The Bench stops at what three columns need rather than taking the window:
    # on a wide screen it used to stretch every slider to half a metre with
    # most of the Bench empty. Three columns still, on every tab, and centred.
    p.set_viewport_size({"width": 1920, "height": 1080}); p.wait_for_timeout(500)
    wide = p.evaluate("""() => {
      const box = document.querySelector('.bench-wrap').getBoundingClientRect();
      const cols = {};
      for (const [tab] of BENCH_TABS) {
        setBenchTab(tab);
        cols[tab] = [document.querySelectorAll('.bench-col').length,
                     el.benchBody.scrollHeight - el.benchBody.clientHeight];
      }
      setBenchTab('play');
      const scope = el.benchScope.getBoundingClientRect(), sheet = el.traceSheet.getBoundingClientRect();
      return { width: Math.round(box.width), left: Math.round(box.left),
               right: Math.round(window.innerWidth - box.right), cols,
               box: [Math.round(scope.width), Math.round(scope.height)],
               sheet: [Math.round(sheet.width), Math.round(sheet.height)],
               leftOfTabs: sheet.right <= el.benchBody.getBoundingClientRect().left };
    }""")
    print("    %s" % wide)
    # 1640 since F3 put the screen on the left at the size the window allows;
    # it was 1420 while the screen was a 318 px column on the right.
    check("on a wide screen the Bench stops at 1640 px, centred",
          wide["width"] == 1640 and abs(wide["left"] - wide["right"]) <= 1, str(wide))
    # Space & Memory is one wide column since F5: the rack reads top to bottom
    # in the order the sound goes through it, which three columns would deal
    # out of order. The null is all three tabs at three.
    want_cols = {"play": 3, "ink": 3, "space": 1}
    fits = lambda w: all(wide["cols"][t][0] == n and wide["cols"][t][1] <= 0 for t, n in w.items())
    check("and every tab is the columns it is meant to have, and fits", fits(want_cols), str(wide["cols"]))
    check("null: three columns everywhere is not what is there",
          not fits({"play": 3, "ink": 3, "space": 3}), str(wide["cols"]))
    # The largest square its box holds, with the drawer's chips under it (the
    # drawer is open here), left of the tabs - and large: the 318 px column it
    # replaced would read about 300 here, and fail.
    side = min(wide["box"])
    check("the screen is on the left of the tabs, the largest square its column holds, and large",
          wide["leftOfTabs"] and abs(wide["sheet"][0] - wide["sheet"][1]) <= 1
          and abs(wide["sheet"][0] - side) <= 1 and side > 550, str(wide))
    p.set_viewport_size({"width": 1400, "height": 900}); p.wait_for_timeout(300)

    print("\n--- narrow ---")
    p.set_viewport_size({"width": 430, "height": 900}); p.wait_for_timeout(500)
    narrow = p.evaluate("""() => ({
      overflow: document.documentElement.scrollWidth > window.innerWidth,
      railRow: getComputedStyle(el.benchRail).flexDirection,
    })""")
    check("no sideways overflow on a phone", narrow["overflow"] is False)
    check("the rail becomes a row", narrow["railRow"] == "row", narrow["railRow"])
    p.screenshot(path=f"{SHOTS}/bench-narrow.png", full_page=True)

    p.set_viewport_size({"width": 1400, "height": 900}); p.wait_for_timeout(300)

    print("\n--- Scope & measure (F1) ---")
    # The scope's own tools in a panel over the screen, shut by default; the
    # readouts under the screen off unless asked for; the toolbar above the
    # screen on the face and enlarged (the Scope view's place until G4); and
    # the developer's labels gone from the face.
    FIT = """() => {
      const out = {};
      for (const view of ['bench', 'enlarged']) {
        setView('bench'); if (view === 'enlarged') setEnlarged(true);
        setMeasureOpen(true);
        const box = el.measurePanel.getBoundingClientRect();
        out[view] = { inside: box.top >= 0 && box.left >= 0 && box.bottom <= innerHeight && box.right <= innerWidth,
                      scrolls: el.measurePanel.scrollHeight > el.measurePanel.clientHeight + 1,
                      over: el.screenTools.nextElementSibling === (view === 'bench' ? el.benchScope : el.panes) };
        setMeasureOpen(false); setEnlarged(false);
      }
      return out;
    }"""
    shut = p.evaluate("""() => { setView('bench'); return { shut: el.measurePanel.hidden, readouts: getComputedStyle(el.measures).display,
      box: el.readoutsOn.checked, labels: /trigger\.js|Test tone/.test(document.querySelector('header').innerText + document.querySelector('.dock').innerText),
      mark: document.getElementById('sourceMark') === null && document.getElementById('colophon') === null }; }""")
    check("Scope & measure is shut and the readouts off on a first load, and no developer's label is left on the face",
          shut == {"shut": True, "readouts": "none", "box": False, "labels": False, "mark": True}, str(shut))
    on = p.evaluate("""() => { el.readoutsOn.click(); const shown = getComputedStyle(el.measures).display;
      const kept = localStorage.getItem('scope.readouts'); el.readoutsOn.click();
      return { shown, kept, after: getComputedStyle(el.measures).display }; }""")
    check("and its box shows them, kept for this viewer, and takes them away again",
          on["shown"] != "none" and on["kept"] == "on" and on["after"] == "none", str(on))
    for w, h in ((1400, 900), (960, 600)):
        p.set_viewport_size({"width": w, "height": h}); p.wait_for_timeout(300)
        fit = p.evaluate(FIT)
        check("at %dx%d the panel is inside the window on the face and enlarged, nothing in it scrolls, and its toolbar is on the screen" % (w, h),
              all(v == {"inside": True, "scrolls": False, "over": True} for v in fit.values()), str(fit))
    print("\n--- the Picture along the bottom (F2) ---")
    # On the face: Enlarge covers it, which is its point (G4; the Scope view had it too).
    BAR = """() => {
      const out = {};
      for (const view of ['bench']) {
        setView(view);
        const bar = el.pictureBar.getBoundingClientRect();
        const knobs = Array.from(el.pictureBar.querySelectorAll('.knob-row input[type=range]')).map((i) => i.id);
        setPictureOpen(true);
        const box = el.picturePanel.getBoundingClientRect();
        out[view] = { bottom: Math.abs(bar.bottom - innerHeight) < 2, knobs,
                      persistence: [!!el.persistence.offsetParent, !!el.scanMemory.offsetParent],
                      panel: box.top >= 0 && box.bottom <= innerHeight && box.left >= 0 && box.right <= innerWidth
                             && el.picturePanel.scrollHeight <= el.picturePanel.clientHeight + 1 };
        setPictureOpen(false);
      }
      return out;
    }"""
    want_bar = {"bottom": True, "knobs": ["pictureAmount", "oscScan", "scanStrike", "scanSoft", "scanMemory", "amp"],
                "persistence": [False, True], "panel": True}
    for w, h in ((1400, 900), (960, 600)):
        p.set_viewport_size({"width": w, "height": h}); p.wait_for_timeout(300)
        bar = p.evaluate(BAR)
        check("at %dx%d the Picture is along the bottom, its six knobs (Level last), one Persistence, and its Advanced inside the window, nothing scrolling" % (w, h),
              all(v == want_bar for v in bar.values()), str(bar))
    # Its null: the menu put back on the face is a second Persistence.
    p.set_viewport_size({"width": 1400, "height": 900}); p.wait_for_timeout(300)
    # Its row is hidden too since F7 took the preset into the header and left
    # the transport with nothing on show, so both are put back.
    two = p.evaluate("""() => { const f = el.persistence.closest('.field'), t = f.closest('.transport');
      f.hidden = false; t.hidden = false;
      const seen = [!!el.persistence.offsetParent, !!el.scanMemory.offsetParent]; f.hidden = true; t.hidden = true; return seen; }""")
    check("null: with the menu back on the face there are two", two == [True, True], str(two))

    # The null: a window shorter than the panel, which no placing can fit -
    # at Size 100, since Auto's 90 (F8) fits it even at 960x480.
    p.set_viewport_size({"width": 960, "height": 480}); p.wait_for_timeout(300)
    p.evaluate("() => setSize(1)"); p.wait_for_timeout(200)
    short = p.evaluate(FIT)
    p.evaluate("() => setSize('auto')")
    check("null: at 960x480 the same check says the panel does not fit", not short["bench"]["inside"], str(short))
    p.set_viewport_size({"width": 1400, "height": 900}); p.wait_for_timeout(300)
    check("no page errors across the run", not bad, "; ".join(bad[:4]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all bench checks pass")
