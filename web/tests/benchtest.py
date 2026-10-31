"""The Bench and Settings: every section in its home, the Bench as tabs.

Each section lives in one place in both views - Settings for what is set once,
the Bench for everything played - and the Bench shows one task's sections at
a time. The thing most likely to go wrong is still duplication - a control copied into
the bench instead of moved gives two elements one id, and getElementById
silently returns the first. That has already cost this page one readout line,
so it is the first thing asserted.
"""
import os, sys
from playwright.sync_api import sync_playwright

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
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    print("\n--- one node per control, in both views ---")
    check("no duplicate ids in Scope", p.evaluate(DUPES) == [], str(p.evaluate(DUPES)))

    p.locator("#viewBench").click(); p.wait_for_timeout(400)
    check("no duplicate ids in Bench", p.evaluate(DUPES) == [], str(p.evaluate(DUPES)))

    # Every section has a home now and stays in it in both views: Settings
    # holds what is set once and left, the Bench everything played. This
    # used to assert the opposite - every group moved to the Bench and every
    # group came back - which is what made the two views identical.
    homes = p.evaluate("""() => {
      const where = () => settingsGroups().map((g) => ({
        title: groupTitle(g), home: g.dataset.home,
        inPanel: g.parentElement === el.menuPanel, onBench: !!g.closest('#bench') }));
      const bench = where();
      setView('scope');
      const scope = where();
      return { bench, scope,
               menuInScope: getComputedStyle(el.menuButton).display !== 'none',
               panelTitles: Array.from(el.menuPanel.querySelectorAll(':scope > .menu-group')).map(groupTitle) };
    }""")
    misplaced = [g["title"] + " in " + view for view in ("bench", "scope") for g in homes[view]
                 if (g["home"] == "settings") != g["inPanel"] or (g["home"] == "bench") != g["onBench"]]
    check("every section is in its home in both views", misplaced == [], str(misplaced))
    check("Settings holds only the settings: MIDI, audio, presets and the beam",
          sorted(homes["panelTitles"]) == ["Audio", "Beam", "MIDI", "Presets"], str(homes["panelTitles"]))
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(300)
    check("and Settings opens from the Bench as well as from Scope",
          homes["menuInScope"] and p.evaluate("getComputedStyle(el.menuButton).display !== 'none'"))
    check("still no duplicates after a round trip", p.evaluate(DUPES) == [])
    dev = p.evaluate("() => ({ shown: !el.deviceRow.hidden, disabled: el.device.disabled, why: el.device.title })")
    check("the device picker is there over the tone, greyed with the reason",
          dev["shown"] and dev["disabled"] and "Mic" in dev["why"], str(dev))

    print("\n--- the drawer ---")
    # The routing matrix behind one switch (P3 of making-it-one-instrument.md):
    # shut on a first visit, and shut it takes the Sources tab, the chips
    # beside the screen and the hollow rings with it - but nothing patched
    # stops playing, and a control with something on it keeps its dots.
    drawer = p.evaluate("""() => {
      const rail = () => Array.from(el.benchRail.querySelectorAll('[role=tab]')).map((b) => b.textContent);
      const shown = (node) => !!(node && node.offsetParent);
      const empties = () => [...document.querySelectorAll('.mod-open.empty')].filter(shown).length;
      const ring = (dest) => document.querySelector('.mod-open[data-dest="' + dest + '"]');
      setBenchTab('play');
      state.modRoutings = []; addRouting('lfo1', 'gen.freq'); touchRoutings(); paintRoutings();
      const look = () => ({ drawer: document.body.dataset.drawer, rail: rail(), chips: shown(el.benchSources),
                            empty: empties(), attached: shown(ring('gen.freq')),
                            heard: routingsHeard().filter((r) => r.sourceId === 'lfo1').map((r) => r.destId),
                            label: el.benchDrawer.getAttribute('aria-expanded') });
      const out = { first: look() };
      el.benchDrawer.click(); paintRoutings();
      out.open = look();
      setBenchTab('sources');
      el.benchDrawer.click();
      out.back = { tab: benchTab, rail: rail() };
      showControl('fadeMode');
      out.shown = { tab: benchTab, drawer: document.body.dataset.drawer };
      el.benchDrawer.click();
      state.modRoutings = []; touchRoutings();
      return out;
    }""")
    print("    shut %s; open %s" % (drawer["first"], drawer["open"]))
    loop_tabs = ["Play", "Picture", "Shape", "Effects", "Measure"]
    check("a first visit opens with the drawer shut: the loop's five tabs, no chips, no hollow rings",
          drawer["first"]["drawer"] == "shut" and drawer["first"]["rail"] == loop_tabs and not drawer["first"]["chips"]
          and drawer["first"]["empty"] == 0 and drawer["first"]["label"] == "false", str(drawer["first"]))
    check("and what is patched still plays and still shows: the oscillator on the frequency heard, its dots on the slider",
          drawer["first"]["attached"] and drawer["first"]["heard"] == drawer["open"]["heard"] == ["gen.freq"], str(drawer["first"]))
    check("opened, the Sources tab comes after the loop's, with the chips and a ring on every control",
          drawer["open"]["rail"] == loop_tabs + ["Sources"] and drawer["open"]["chips"] and drawer["open"]["empty"] > 0
          and drawer["open"]["label"] == "true", str(drawer["open"]))
    check("shut while on Sources, it goes back to the tab before", drawer["back"] == {"tab": "play", "rail": loop_tabs},
          str(drawer["back"]))
    check("and a control in it, shown from anywhere, opens it", drawer["shown"] == {"tab": "sources", "drawer": "open"},
          str(drawer["shown"]))
    hidden = p.evaluate("""() => {
      el.benchDrawer.click(); setBenchTab('sources');
      const chips = [...el.benchSources.querySelectorAll('.mod-chip')].map((c) => c.dataset.source);
      el.benchSearch.value = 'glow'; el.benchSearch.dispatchEvent(new Event('input'));
      const found = [...el.benchResults.querySelectorAll('button')].map((b) => b.textContent);
      el.benchSearch.value = ''; el.benchSearch.dispatchEvent(new Event('input'));
      return { chips: chips.filter((id) => id.startsWith('stage.')), lfo: chips.includes('lfo1'), found };
    }""")
    # The Photocell's switch goes with the drawer while it is off, and stays
    # while it is on, by the rings' rule; open, it is always there.
    cell = p.evaluate("""() => {
      const shown = () => !!el.photoButton.offsetParent;
      const out = {};
      setDrawer(false); setPhoto(false); out.shutOff = shown();
      setPhoto(true); out.shutOn = shown();
      setPhoto(false); setDrawer(true); out.openOff = shown();
      return out;
    }""")
    check("the Photocell's switch is hidden with the drawer shut and the photocell off, shown on, and shown with the drawer open",
          cell == {"shutOff": False, "shutOn": True, "openOff": True}, str(cell))
    check("the stage's reads are not offered by hand: no chip, and not found by a search",
          hidden["chips"] == [] and hidden["lfo"] and not any("Glow" in f for f in hidden["found"]), str(hidden))

    print("\n--- the tabs ---")
    # Tabs again, on the evidence: the rail was a table of contents with every
    # section on show at once, and a rack could not fit that way. With the
    # drawer open, so its tab is walked too.
    tabs = p.evaluate("""() => {
      const titles = Array.from(el.benchRail.querySelectorAll('[role=tab]')).map((b) => b.textContent);
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
    # one, last, since P3.
    check("six tabs by task with the drawer open, its own last, and a tab list",
          tabs["titles"] == ["Play", "Picture", "Shape", "Effects", "Measure", "Sources"]
          and tabs["role"] == "tablist", str(tabs["titles"]))
    check("each tab shows its own sections and fits", tabs["wrong"] == [], str(tabs["wrong"]))
    missing = [t for t in tabs["benchTitles"] if tabs["seen"].get(t) != 1]
    check("every Bench section is on exactly one tab", missing == [], str(missing) + " " + str(tabs["seen"]))
    check("Modulation is gone: the oscillators are sources, on the Sources tab",
          "Modulation" not in tabs["seen"] and tabs["seen"].get("Sources") == 1, str(tabs["seen"]))
    keys = p.evaluate("""() => {
      setBenchTab('play');
      const tb = el.timebase.value;
      const tab = document.getElementById('benchTab-play');
      tab.focus();
      tab.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
      return { tab: benchTab, focused: document.activeElement.id, timebase: el.timebase.value === tb };
    }""")
    check("the arrow keys walk the tabs, and do not also move the timebase",
          keys["tab"] == "picture" and keys["focused"] == "benchTab-picture" and keys["timebase"], str(keys))
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
      // The Picture tab, and a slider and a checkbox that live on it.
      setBenchTab('picture');
      el.holdoff.value = '30';
      el.holdoff.dispatchEvent(new Event('input'));
      const a = state.holdoffMs;
      el.lagOn.checked = true;
      el.lagOn.dispatchEvent(new Event('change'));
      const b = { lag: state.lagOn, lanes: laneCount() };

      el.lagOn.checked = false; el.lagOn.dispatchEvent(new Event('change'));
      el.holdoff.value = '0'; el.holdoff.dispatchEvent(new Event('input'));
      return { holdoff: a, lag: b };
    }""")
    check("a slider in the bench drives its state", live["holdoff"] == 3.0, str(live["holdoff"]))
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
    p.evaluate("() => setView('scope')"); p.wait_for_timeout(400)
    scope_home = p.evaluate("""() => ({
      parent: el.traceSheet.parentElement.id,
      height: el.trace.getBoundingClientRect().height,
      screenShown: getComputedStyle(document.querySelector('.screen')).display,
    })""")
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(400)
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
    check("in Scope it lives in the panes", scope_home["parent"] == "panes",
          scope_home["parent"])
    check("in Bench it lives in the square", bench_home["parent"] == "benchScope",
          bench_home["parent"])
    check("and the full-height screen is gone rather than squeezed",
          bench_home["screenShown"] == "none" and scope_home["screenShown"] != "none",
          "%s / %s" % (bench_home["screenShown"], scope_home["screenShown"]))
    check("the bench screen is square",
          abs(bench_home["w"] - bench_home["h"]) <= 1,
          "%.0f x %.0f" % (bench_home["w"], bench_home["h"]))
    check("and smaller than the one it replaced",
          bench_home["h"] < scope_home["height"] * 0.75,
          "%.0f px in bench vs %.0f in scope" % (bench_home["h"], scope_home["height"]))
    check("still has a trace drawn on it", strip["inked"] > 500,
          "%d inked pixels of %d" % (strip["inked"], strip["pixels"]))
    check("at a real frame rate", strip["fps"] > 20, "%.0f fps" % strip["fps"])

    print("\n--- the oscillators survive a source that has no generator ---")
    # They used to be switched off wholesale on anything but the test tone,
    # which was right while every destination they had was a generator
    # parameter. It is wrong now: an LFO on the filter cutoff or the rotation
    # is the same patch whatever the signal came from. What withdraws on a
    # live source is the generator half of the DESTINATION list, per entry.
    # Read from the Sources tab's Add menu now, which is where a destination
    # is chosen since the one-destination dropdown went.
    mod = p.evaluate("""() => {
      setBenchTab('sources'); selectSource('lfo1');
      const options = () => Array.from(document.getElementById('srcDetail-add').options).slice(1);
      showSource('mic');                       // just the panel, no stream
      const live = {
        off: el.srcGroup.dataset.off,
        hidden: el.srcGroup.hidden,
        rate: !!document.getElementById('lfoRate0'),
        genDead: options().filter((o) => o.value.startsWith('gen.')).every((o) => o.disabled),
        viewAlive: options().filter((o) => o.value.startsWith('view.')).every((o) => !o.disabled),
        some: options().filter((o) => o.value.startsWith('gen.')).length,
      };
      showSource(null);
      const tone = {
        genAlive: options().filter((o) => o.value.startsWith('gen.')).every((o) => !o.disabled),
      };
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

    print("\n--- the view is remembered ---")
    p.reload(); p.wait_for_timeout(900)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    kept = p.evaluate("() => ({ view: document.body.dataset.view, tab: benchTab, drawer: document.body.dataset.drawer })")
    check("the bench, its tab and the drawer open survive a reload",
          kept == {"view": "bench", "tab": "sources", "drawer": "open"}, str(kept))
    check("no errors after reload", not bad, "; ".join(bad[:3]))
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
      const scope = el.benchScope.getBoundingClientRect(), side = el.benchSide.getBoundingClientRect();
      return { width: Math.round(box.width), left: Math.round(box.left),
               right: Math.round(window.innerWidth - box.right), cols,
               scope: Math.round(scope.width), column: Math.round(side.width) };
    }""")
    print("    %s" % wide)
    check("on a wide screen the Bench stops at 1420 px, centred",
          wide["width"] == 1420 and abs(wide["left"] - wide["right"]) <= 1, str(wide))
    check("and every tab is still three columns that fit",
          all(c == [3, 0] or (c[0] == 3 and c[1] <= 0) for c in wide["cols"].values()), str(wide["cols"]))
    check("the screen beside them fills its column, now the oscillators are not under it",
          wide["scope"] >= wide["column"] - 20 and wide["scope"] > 250, str(wide))
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
    p.evaluate("() => setView('scope')")
    check("no page errors across the run", not bad, "; ".join(bad[:4]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all bench checks pass")
