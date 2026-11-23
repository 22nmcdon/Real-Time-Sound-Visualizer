"""The UI review's three builds (20 Nov): Scope & measure by subject, the Picture strip
readable, Perform labelled. Specs: web/docs/scope-measure.md, picture-strip.md, perform.md.

What would go wrong, and what is checked for it, each check with its null:

Scope & measure
- an id lost, or its type, range or options changed, so the plugin, a setup or a suite
  reads something else: every one of the panel's controls is read and compared with the
  table below, which is testing's before the review. The null: one range's max moved;
- a range left a slider: the fourteen are knobs. The null: a row put in a view is a slider
  until the dressing reaches it;
- the face moving when a subtab is chosen or a value changes: the head, the bar and the
  views' box are measured on every subtab, and every control of each view across the
  states that change readings and greying. The nulls: the box let grow with its view, and
  a knob cell sized to its reading;
- the panel past the Picture strip, outside the window or anything in a view cut off, at
  the six windows. The null: the panel made too short for its views;
- a label over three words or over one line. The null: the sentence the review took out;
- showControl leaving the wrong subtab chosen. The null: the subtab before the call;
- the drawings not reading the values: the trigger's crossing moves with the edge and
  goes to free run past the peak, the toolbar's Zoom's slice is the window over the zoom, the filter's
  cutoff mark moves with Cutoff. Each null is the other value's.

The Picture strip
- the strip still at the page's measure: it spans the window less the gutters. The null:
  the measure put back;
- the reads not drawing the reads: each row's fill and per cent are the stage's. The null:
  the same rows read against other values;
- the strip moving as the line or the reads change. The null: a reading column of no fixed
  width.

Perform
- an unnamed menu, or its values changed: Pattern, Step and Octaves each name their menu,
  and the values are testing's. The null: a menu named only by aria-label;
- the drawing not the arpeggiator's order: each pattern's steps over a bar of C major, the
  step counts of each rate. The null: Down read as Up;
- the clock's sentence and its button: the parts and the button stay put as the bar grows.
  The null: the button on the line;
- Glide greyed only while Quantise is off, Glide and Tempo knobs, the morph a slider with
  its position read from a value set in code; the panel above the strip at six windows.

Parallel: it measures boxes, not time.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
WINDOWS = ((1660, 1050), (1400, 900), (1100, 860), (1200, 680), (1100, 680), (960, 600))

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + str(detail)[:600]) if detail else ""))
    if not ok: fails.append(name)
def null(name, red, detail=""):
    check("null: " + name, red, detail)

# Testing's panel before the review (1704599): each range's min, max and step as the page
# leaves them once it has run (the timebase's max is TIMEBASE's, set by the script).
RANGES = {"level": ["-1000", "1000", ""], "position": ["0", "100", ""], "holdoff": ["0", "50", "1"],
          "timebase": ["0", "8", "1"], "lag": ["1", "400", ""], "lagMix": ["0", "50", ""],
          "ch1Scale": ["0", None, "1"], "ch2Scale": ["0", None, "1"], "ch1Offset": ["-100", "100", ""], "ch2Offset": ["-100", "100", ""],
          "acCorner": ["5", "200", ""], "filterCutoff": ["0", "1000", ""], "filterRes": ["0", "100", ""]}
CHECKS = ["midiTruth", "midiFollow", "lagOn", "ch1On", "ch2On", "ch1Ac", "ch2Ac", "midSide", "filterOn", "readoutsOn", "cursorsOn"]
RADIOS = ["modeAuto", "modeNormal", "modeSingle", "edgeRising", "edgeFalling", "trigSource0", "trigSource1", "lagAuto", "lagManual",
          "seeDry", "seeWet", "hearDry", "hearWet", "measurePre", "measurePost", "layStack", "layOver"]
BUTTONS = ["run", "autoset", "saveReference", "clearReference", "measureClose"]

IDS = """([ranges, checks, radios, buttons]) => {
  const bad = [];
  for (const [id, [lo, hi, step]] of Object.entries(ranges)) {
    const i = document.getElementById(id);
    if (!i || i.type !== 'range' || !el.measurePanel.contains(i)) { bad.push(id + ' missing'); continue; }
    if (i.min !== lo || (hi !== null && i.max !== hi) || i.getAttribute('step') !== (step || null) && (i.getAttribute('step') || '') !== step) bad.push(id + ' ' + [i.min, i.max, i.getAttribute('step')]);
  }
  for (const id of checks) { const i = document.getElementById(id); if (!i || i.type !== 'checkbox' || !el.measurePanel.contains(i)) bad.push(id); }
  for (const id of radios) { const i = document.getElementById(id); if (!i || i.getAttribute('role') !== 'radio' || !el.measurePanel.contains(i)) bad.push(id); }
  for (const id of buttons) { const i = document.getElementById(id); if (!i || i.tagName !== 'BUTTON' || !el.measurePanel.contains(i)) bad.push(id); }
  const types = [...el.filterType.options].map((o) => o.value).join(',');
  if (types !== 'lowpass,highpass,bandpass,notch') bad.push('filterType ' + types);
  return bad;
}"""

# Every visible box in the head, the bar and the views' box, and in the shown view each control's.
BOXES = """() => {
  const r = (n) => { const b = n.getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map((v) => Math.round(v * 2) / 2).join(','); };
  const out = {};
  for (const n of el.measurePanel.querySelectorAll('.measure-head > *, .measure-head .switch button, .fig-tab')) if (n.getClientRects().length) out[(n.id || n.className) + '#' + n.textContent.trim().slice(0, 10)] = r(n);
  out.views = r(document.getElementById('measureViews'));
  out.panel = r(el.measurePanel);
  return out;
}"""
CONTROLS = """(view) => {
  const v = document.getElementById('mview-' + view), out = {};
  const r = (n) => { const b = n.getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map((x) => Math.round(x * 2) / 2).join(','); };
  v.querySelectorAll('.knob-face, .check-switch, select, .switch, .link-btn, .filt-plot, .measure-sec, .menu-label, .mplot').forEach((n, k) => {
    // By its place and kind, not its class, which greying changes (is-idle).
    if (n.getClientRects().length) out[k + ':' + (n.id || n.tagName)] = r(n);
  });
  return out;
}"""
FITS = """() => {
  const z = pageZoom || 1, p = el.measurePanel.getBoundingClientRect(), strip = el.pictureBar.getBoundingClientRect();
  const out = { above: p.bottom <= strip.top + 0.5, inside: p.top >= 0 && p.left >= 0 && p.right <= innerWidth + 0.5 && p.bottom <= innerHeight + 0.5,
                scrolls: el.measurePanel.scrollHeight > el.measurePanel.clientHeight + 1, height: Math.round(p.height / z), cut: [] };
  for (const view of MEASURE_VIEWS) {
    setMeasureView(view);
    const box = document.getElementById('mview-' + view).getBoundingClientRect();
    for (const n of document.getElementById('mview-' + view).querySelectorAll('input:not(.knob-dial):not([type=checkbox]), select, button, .knob-face, .check-switch, .reading, .menu-label, .eyebrow, .measure-sec, .mcap')) {
      if (!n.getClientRects().length || getComputedStyle(n).visibility === 'hidden') continue;
      const b = n.getBoundingClientRect();
      if (b.left < box.left - 0.5 || b.top < box.top - 0.5 || b.right > box.right + 0.5 || b.bottom > box.bottom + 0.5) out.cut.push(view + ':' + (n.id || n.textContent.trim().slice(0, 14)));
    }
  }
  setMeasureView('trigger');
  return out;
}"""
LABELS = """() => {
  const bad = [];
  // The lines its words take: its text nodes' boxes only, so a switch's lamp is not a line.
  const lines = (n) => { const tops = new Set(), walk = document.createTreeWalker(n, NodeFilter.SHOW_TEXT);
    for (let t = walk.nextNode(); t; t = walk.nextNode()) {
      if (!t.textContent.trim()) continue;
      const range = document.createRange(); range.selectNodeContents(t);
      for (const r of range.getClientRects()) if (r.width > 0) tops.add(Math.round(r.top + r.height / 2));
    }
    return tops.size; };
  for (const view of MEASURE_VIEWS) {
    setMeasureView(view);
    for (const n of el.measurePanel.querySelectorAll('.measure-head .eyebrow, .measure-head button, .fig-tab b, .measure-view:not([hidden]) :is(.menu-label, .check-switch, .eyebrow, .measure-sec, .switch button, .link-btn, .menu-title)')) {
      if (!n.getClientRects().length || getComputedStyle(n).display === 'none') continue;
      const words = n.textContent.replace(/speakers$/, '').trim().split(/\\s+/).filter((w) => w && w !== '/' && w !== '\\u00d7');
      if (words.length > 3 || lines(n) > 1) bad.push(view + ': ' + n.textContent.trim() + ' (' + words.length + ' words, ' + lines(n) + ' lines)');
    }
  }
  setMeasureView('trigger');
  return bad;
}"""

def setv(p, id, v, kind="input"):
    p.evaluate("([id, v, kind]) => { const i = document.getElementById(id); i.value = v; i.dispatchEvent(new Event(kind, { bubbles: true })); }", [id, str(v), kind])

def tick(p, id, on):
    p.evaluate("([id, on]) => { const i = document.getElementById(id); if (i.checked !== on) { i.checked = on; i.dispatchEvent(new Event('change', { bubbles: true })); } }", [id, on])

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_context(viewport={"width": 1400, "height": 900}).new_page()
    bad = []
    p.on("pageerror", lambda e: bad.append(str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(2000)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(300)

    print("\n--- Scope & measure: every id, its type, range and options ---")
    p.evaluate("() => setMeasureOpen(true)"); p.wait_for_timeout(200)
    args = [RANGES, CHECKS, RADIOS, BUTTONS]
    lost = p.evaluate(IDS, args)
    check("every control the panel had is in it, with its type, range, step and options", lost == [], lost)
    planted = p.evaluate("(args) => { const keep = el.level.max; el.level.max = '999'; const r = (" + IDS + ")(args); el.level.max = keep; return r; }", args)
    null("the level's max moved by one is found", any(x.startswith("level") for x in planted), planted)

    print("\n--- Scope & measure: the fourteen ranges are knobs ---")
    knobs = p.evaluate("""(ids) => ids.filter((id) => { const i = document.getElementById(id);
      return !(i.closest('.knob-row') && i.parentElement.querySelector('.knob-face')); })""", list(RANGES))
    check("all fourteen of the panel's ranges are knobs over their inputs", knobs == [], knobs)
    probe = p.evaluate("""() => { const host = document.querySelector('#mview-time .measure-knobs'), row = document.createElement('div'); row.className = 'menu-row';
      row.innerHTML = '<label class="menu-label" for="mProbe">Probe</label><div class="grow"><input type="range" id="mProbe" min="0" max="9" value="3"><span class="reading">3</span></div>';
      host.appendChild(row); const before = !!row.querySelector('.knob-face'); dressKnobs(host); const after = !!row.querySelector('.knob-face'); row.remove(); return [before, after]; }""")
    null("a row put in a view is a slider until the dressing reaches it, and a knob after", probe == [False, True], probe)

    print("\n--- Scope & measure: one box, nothing moves ---")
    per = {}
    for view in ("trigger", "time", "vertical", "measure"):
        p.evaluate("(v) => setMeasureView(v)", view); p.wait_for_timeout(120)
        per[view] = p.evaluate(BOXES)
    moved = [v for v in per if per[v] != per["trigger"]]
    check("the head, the bar and the views' box are where they were on every subtab", moved == [] and len(per["trigger"]) > 12,
          {v: {k: per[v].get(k) for k in per[v] if per[v].get(k) != per["trigger"].get(k)} for v in moved})
    grown = p.evaluate("""() => { const box = document.getElementById('measureViews'), out = [];
      for (const v of MEASURE_VIEWS) { box.style.flex = '0 0 auto'; document.getElementById('mview-' + v).style.position = 'static';
        setMeasureView(v); out.push(Math.round(box.getBoundingClientRect().height)); document.getElementById('mview-' + v).style.position = ''; }
      box.style.flex = ''; setMeasureView('trigger'); return out; }""")
    null("a box let grow with its view is a different height on some subtab", len(set(grown)) > 1, grown)

    states = {
        "trigger": [("level", "-1000"), ("level", "1000"), ("holdoff", "50"), ("position", "100"), ("click", "edgeFalling"), ("click", "trigSource1")],
        "time": [("timebase", "0"), ("timebase", "8"), ("tick", "lagOn"), ("click", "lagManual"), ("lag", "400"), ("tick-off", "midiTruth")],
        "vertical": [("tick", "filterOn"), ("filterCutoff", "0"), ("filterRes", "100"), ("ch1Scale", "8"), ("ch1Offset", "-100"), ("tick", "midSide"), ("tick-off", "ch2On")],
        "measure": [("tick", "readoutsOn"), ("tick", "cursorsOn"), ("click", "measurePost"), ("click", "saveReference")],
    }
    shifted = {}
    for view, steps in states.items():
        p.evaluate("(v) => setMeasureView(v)", view); p.wait_for_timeout(100)
        before = p.evaluate(CONTROLS, view)
        for kind, v in steps:
            if kind == "click": p.evaluate("(id) => document.getElementById(id).click()", v)
            elif kind == "tick": tick(p, v, True)
            elif kind == "tick-off": tick(p, v, False)
            else: setv(p, kind, v)
            p.wait_for_timeout(80)
            after = p.evaluate(CONTROLS, view)
            diff = [k for k in before if after.get(k) != before[k]]
            if diff: shifted.setdefault(view, []).append((kind, v, diff[:4]))
    check("nothing in a view moves as its values change: readings grow, the filter and the lag grey, the lanes turn mid / side",
          not shifted, shifted)
    # The trace filter's two knobs since 22 Nov, when the zoom beside the timebase went to the screen's toolbar.
    sized = p.evaluate("""() => { setMeasureView('vertical'); const row = el.filterCutoff.closest('.knob-row'), face = row.querySelector('.knob-face');
      row.style.cssText = 'width: max-content; min-width: 0; max-width: none';
      const a = el.filterRes.closest('.knob-row').getBoundingClientRect().left; el.filterCutoffValue.textContent = '1.00 kHz and then some';
      const b2 = el.filterRes.closest('.knob-row').getBoundingClientRect().left; row.style.cssText = ''; el.filterCutoffValue.textContent = '1.00 kHz';
      void face; setMeasureView('time'); return [a, b2]; }""")
    null("a knob cell sized to its reading moves the knob beside it", abs(sized[0] - sized[1]) > 0.5, sized)
    p.evaluate("() => { el.presetNew.click(); }"); p.wait_for_timeout(400)
    p.evaluate("() => { for (const id of ['filterOn', 'lagOn', 'midSide', 'readoutsOn', 'cursorsOn']) { const i = el[id]; if (i.checked) { i.checked = false; i.dispatchEvent(new Event('change', { bubbles: true })); } } el.ch2On.checked = true; el.ch2On.dispatchEvent(new Event('change', { bubbles: true })); el.midiTruth.checked = true; el.midiTruth.dispatchEvent(new Event('change', { bubbles: true })); el.measurePre.click(); el.clearReference.click(); el.edgeRising.click(); }")

    print("\n--- Scope & measure: at six windows ---")
    fits = {}
    for w, h in WINDOWS:
        p.set_viewport_size({"width": w, "height": h}); p.wait_for_timeout(400)
        p.evaluate("() => { setMeasureOpen(false); setMeasureOpen(true); }"); p.wait_for_timeout(150)
        fits[(w, h)] = p.evaluate(FITS)
    print("    " + "; ".join("%dx%d %s" % (k[0], k[1], {x: v[x] for x in ("height", "above", "cut")}) for k, v in fits.items()))
    check("at every window the panel is one height, inside the window and above the Picture strip, with nothing scrolled or cut on any subtab",
          all(v["above"] and v["inside"] and not v["scrolls"] and not v["cut"] and 440 <= v["height"] <= 520 for v in fits.values()), fits)
    short = p.evaluate("(fits) => { el.measurePanel.style.height = '300px'; const r = (" + FITS + ")(); placeMeasure(); return r.cut.length; }", None)
    null("a panel too short for its views finds controls cut", short > 0, short)

    print("\n--- Scope & measure: short labels ---")
    p.set_viewport_size({"width": 1400, "height": 900}); p.wait_for_timeout(300)
    p.evaluate("() => { setMeasureOpen(false); setMeasureOpen(true); }")
    long = {}
    for w, h in ((1400, 900), (960, 600)):
        p.set_viewport_size({"width": w, "height": h}); p.wait_for_timeout(300); p.evaluate("() => placeMeasure()")
        long[(w, h)] = p.evaluate(LABELS)
    check("every label in the head, the bar and each view is three words or fewer, on one line", all(v == [] for v in long.values()), long)
    planted = p.evaluate("""() => { const s = el.midiTruth.closest('.check-switch'), keep = s.lastChild.textContent;
      s.lastChild.textContent = 'Take the lag and the tuner from the note played'; const r = (""" + LABELS + """)(); s.lastChild.textContent = keep; return r; }""")
    null("the sentence the review took out is found", any("Take the lag" in x for x in planted), planted)
    p.set_viewport_size({"width": 1400, "height": 900}); p.wait_for_timeout(300)

    print("\n--- Scope & measure: showControl chooses the subtab ---")
    chosen = p.evaluate("""() => { setMeasureOpen(false); setMeasureView('trigger'); const out = {};
      out.before = measureView.at;
      for (const id of ['lag', 'filterCutoff', 'cursorsOn', 'holdoff', 'midiFollow', 'ch2Offset']) { showControl(id); out[id] = measureView.at; }
      return out; }""")
    check("showControl opens the panel on the subtab that holds the control",
          chosen == {"before": "trigger", "lag": "time", "filterCutoff": "vertical", "cursorsOn": "measure", "holdoff": "trigger",
                     "midiFollow": "time", "ch2Offset": "vertical"}, chosen)
    null("before the call the subtab was Trigger, so Time for the lag was chosen by it", chosen["before"] != chosen["lag"], chosen)

    print("\n--- Scope & measure: the drawings read the values ---")
    drawn = p.evaluate("""() => { const out = {}; setMeasureView('trigger');
      const at = () => { paintMeasure(true); const d = document.getElementById('trigPlot').dataset; return { free: d.free, crossing: d.crossing, cap: el.measurePanel.querySelector('#trigCap').textContent }; };
      el.level.value = '0'; el.level.dispatchEvent(new Event('input')); el.edgeRising.click(); out.rising = at();
      el.edgeFalling.click(); out.falling = at(); el.edgeRising.click();
      el.level.value = '950'; el.level.dispatchEvent(new Event('input')); out.past = at();
      el.level.value = '0'; el.level.dispatchEvent(new Event('input'));
      setMeasureView('time'); const plot = document.getElementById('timePlot');
      el.zoom.value = '24'; el.zoom.dispatchEvent(new Event('input')); paintMeasure(true); out.slice = Number(plot.dataset.slice); out.zoom = state.zoom; out.w = plot.clientWidth - 8;
      el.zoom.value = '0'; el.zoom.dispatchEvent(new Event('input')); paintMeasure(true); out.whole = Number(plot.dataset.slice);
      setMeasureView('vertical');
      el.filterCutoff.value = '200'; el.filterCutoff.dispatchEvent(new Event('input')); paintMeasure(true); out.cutLow = Number(el.filterSvg.dataset.cutoff);
      el.filterCutoff.value = '900'; el.filterCutoff.dispatchEvent(new Event('input')); paintMeasure(true); out.cutHigh = Number(el.filterSvg.dataset.cutoff);
      el.filterCutoff.value = '566'; el.filterCutoff.dispatchEvent(new Event('input'));
      setMeasureView('trigger'); return out; }""")
    print("    %s" % drawn)
    check("the trigger's crossing is drawn where the edge asked: rising and falling cross at different places",
          drawn["rising"]["free"] == "false" and drawn["falling"]["free"] == "false" and drawn["rising"]["crossing"] != drawn["falling"]["crossing"], drawn)
    check("past the stand-in's peak it runs free, and the caption says so", drawn["past"]["free"] == "true" and drawn["past"]["cap"].startswith("Free run"), drawn["past"])
    null("at nought it is not free run", drawn["rising"]["free"] == "false", drawn["rising"])
    check("the toolbar's Zoom's slice is the window over the zoom", drawn["zoom"] > 1 and abs(drawn["slice"] - drawn["w"] / drawn["zoom"]) < 1, drawn)
    null("at no zoom the slice is the whole window", abs(drawn["whole"] - drawn["w"]) < 1 and abs(drawn["whole"] - drawn["slice"]) > 5, drawn)
    check("the filter's cutoff mark moves with Cutoff, up the log axis", drawn["cutHigh"] - drawn["cutLow"] > 100, drawn)
    p.evaluate("() => setMeasureOpen(false)")

    print("\n--- the Picture strip ---")
    span = {}
    for w, h in ((1660, 1050), (960, 600)):
        p.set_viewport_size({"width": w, "height": h}); p.wait_for_timeout(400)
        span[(w, h)] = p.evaluate("""() => { const z = pageZoom || 1, wrap = el.pictureBar.querySelector('.picture-wrap').getBoundingClientRect();
          const inner = wrap.width / z - 48; const s = el.pictureBar.querySelector('.picture-wrap');
          s.style.maxWidth = 'var(--max)'; const narrow = s.getBoundingClientRect().width / z; s.style.maxWidth = '';
          return { width: Math.round(wrap.width / z), page: Math.round(innerWidth / z), narrow: Math.round(narrow), inner: Math.round(inner) }; }""")
    print("    %s" % span)
    check("the strip runs the window's width", all(abs(v["width"] - v["page"]) <= 1 for v in span.values()), span)
    null("with the page's measure put back it does not, at 1660x1050", span[(1660, 1050)]["narrow"] < span[(1660, 1050)]["page"] - 100, span)
    p.set_viewport_size({"width": 1400, "height": 900}); p.wait_for_timeout(300)
    reads = p.evaluate("""() => { const keep = { ...pictureStage };
      const read = () => [...el.pictureReads.children].map((row) => { const bar = row.querySelector('.read-bar');
        return [row.dataset.read, getComputedStyle(bar).backgroundSize.split(' ')[0], row.querySelector('.read-value').textContent]; });
      Object.assign(pictureStage, { glow: 0.62, motion: 0.18, memory: 0.41 }); paintStage(); const a = read();
      Object.assign(pictureStage, { glow: 1, motion: 0, memory: 0.05 }); paintStage(); const b2 = read();
      Object.assign(pictureStage, keep); return [a, b2]; }""")
    print("    %s" % reads)
    def pct(x): return float(x[1].rstrip("%px")) if x[1].endswith("%") else None
    want = [[0.62, 0.18, 0.41], [1, 0, 0.05]]
    check("each read is a row: its name, a bar filled as far as the read and its reading in per cent",
          all([r[0] for r in reads[k]] == ["glow", "motion", "memory"] and all(r[2] == "%d%%" % round(v * 100) for r, v in zip(reads[k], want[k])) for k in (0, 1)), reads)
    null("the first frame's readings are not the second's", [r[2] for r in reads[0]] != [r[2] for r in reads[1]], reads)
    still = p.evaluate("""() => { const r = (n) => { const b = n.getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map((x) => Math.round(x * 2) / 2).join(','); };
      const boxes = () => [...el.pictureBar.querySelectorAll('.knob-face, .menu-label, #infoMore, #infoName, .read-name, .read-bar, .read-value, .check-switch, #pictureMore, .level-meter')].filter((n) => n.getClientRects().length).map(r);
      const keep = { ...pictureStage }, out = {};
      el.infoMore.classList.remove('is-unseen');
      Object.assign(pictureStage, { glow: 0, motion: 0, memory: 0 }); paintStage(); el.infoName.textContent = 'Amount'; el.infoText.textContent = 'Short.'; const a = boxes();
      Object.assign(pictureStage, { glow: 1, motion: 1, memory: 1 }); paintStage(); el.infoName.textContent = 'Amount'; el.infoText.textContent = CONTROL_WORDS.morphPos[1] + ' ' + CONTROL_WORDS.morphPos[1]; const b2 = boxes();
      out.same = JSON.stringify(a) === JSON.stringify(b2);
      el.pictureReads.style.gridTemplateColumns = 'auto 64px auto';
      Object.assign(pictureStage, { glow: 0, motion: 0, memory: 0 }); paintStage(); const c = boxes();
      Object.assign(pictureStage, { glow: 1, motion: 1, memory: 1 }); paintStage(); const d = boxes();
      el.pictureReads.style.gridTemplateColumns = ''; Object.assign(pictureStage, keep);
      out.nullMoved = JSON.stringify(c) !== JSON.stringify(d); return out; }""")
    check("nothing in the strip moves as the reads go from nought to full and the line from short to long", still["same"], still)
    null("a reading column of no fixed width moves the strip", still["nullMoved"], still)

    print("\n--- Perform ---")
    p.evaluate("() => setPerformOpen(true)"); p.wait_for_timeout(200)
    named = p.evaluate("""() => ['arpMode', 'arpRate', 'arpOctaves', 'keyRoot', 'keyScale', 'quantiseGlide', 'tempo', 'quantise'].map((id) => {
      const i = document.getElementById(id), l = i.labels && i.labels[0];
      return [id, l && l.getClientRects().length ? l.textContent.trim() : null]; })""")
    check("every menu, switch and knob in Perform names itself on the face, three words or fewer",
          dict(named) == {"arpMode": "Pattern", "arpRate": "Step", "arpOctaves": "Octaves", "keyRoot": "Key", "keyScale": "Scale",
                          "quantiseGlide": "Glide", "tempo": "Tempo", "quantise": "Quantise pitch"}, named)
    bare = p.evaluate("""() => { const s = document.createElement('select'); s.setAttribute('aria-label', 'Arpeggio step'); el.performPanel.appendChild(s);
      const l = s.labels && s.labels[0]; s.remove(); return l ? l.textContent : null; }""")
    null("a menu named only by aria-label, as testing's Step was, has no name on the face", bare is None, bare)
    values = p.evaluate("""() => ['arpMode', 'arpRate', 'arpOctaves'].map((id) => [...document.getElementById(id).options].map((o) => o.value).join(','))""")
    check("the menus' values are testing's, so a setup, the plugin and the core hear what they heard",
          values == ["off,up,down,updown,played,random", "1/4,1/8,1/16,1/8t,1/16t", "1,2,3"], values)
    seqs = p.evaluate("""() => { const out = {};
      const run = (mode, rate, oct) => { el.arpMode.value = mode; el.arpRate.value = rate; el.arpOctaves.value = String(oct); el.arpDraw.dataset.key = ''; drawArp(); return el.arpDraw.dataset.seq; };
      out.up = run('up', '1/8', 1); out.down = run('down', '1/8', 1); out.updown = run('updown', '1/8', 1); out.played = run('played', '1/8', 1);
      out.up2 = run('updown', '1/8', 2); out.s16 = run('up', '1/16', 1).split(',').length; out.s8t = run('up', '1/8t', 1).split(',').length;
      out.s16t = run('up', '1/16t', 1).split(',').length; out.s4 = run('up', '1/4', 1).split(',').length; out.off = run('off', '1/8', 1);
      out.cap = el.arpCap.textContent; el.arpMode.value = 'off'; el.arpRate.value = '1/8'; el.arpOctaves.value = '1'; drawArp(); return out; }""")
    print("    %s" % seqs)
    check("over a bar of C major, struck E, C, G: Up, Down, Up and down turning at the ends, and As played",
          seqs["up"] == "60,64,67,60,64,67,60,64" and seqs["down"] == "67,64,60,67,64,60,67,64"
          and seqs["updown"] == "60,64,67,64,60,64,67,64" and seqs["played"] == "64,60,67,64,60,67,64,60"
          and seqs["up2"] == "60,64,67,72,76,79,76,72", seqs)
    check("a step per note value over the bar: 4, 8, 16, 12 and 24, and off draws the chord held",
          (seqs["s4"], seqs["s16"], seqs["s8t"], seqs["s16t"]) == (4, 16, 12, 24) and seqs["off"] == "" and seqs["cap"].startswith("Off"), seqs)
    null("Down is not Up's order", seqs["down"] != seqs["up"], seqs)
    clock = p.evaluate("""() => { syncClockPanel(); const line = document.getElementById('clockLine').textContent.replace(/\\s+/g, ' ').trim();
      const r = (n) => { const b = n.getBoundingClientRect(); return [b.left, b.top].map((x) => Math.round(x * 2) / 2).join(','); };
      const a = [r(el.transportPlay), r(el.transportState)]; const keep = el.transportAt.textContent;
      el.transportAt.textContent = 'bar 128, beat 4'; const b2 = [r(el.transportPlay), r(el.transportState)];
      el.transportAt.style.minWidth = '0'; document.getElementById('clockLine').appendChild(el.transportPlay); el.transportAt.textContent = 'bar 1, beat 1'; const c = r(el.transportPlay);
      el.transportAt.textContent = 'bar 128, beat 4'; const d = r(el.transportPlay);
      el.transportAt.style.minWidth = ''; document.querySelector('.clock-row').appendChild(el.transportPlay); el.transportAt.textContent = keep; syncClockPanel();
      return { line, same: JSON.stringify(a) === JSON.stringify(b2), nullMoved: c !== d, button: el.transportPlay.textContent, state: el.transportState.textContent }; }""")
    print("    %s" % clock)
    check("the clock is one sentence - where from, bar and beat, running or stopped - and the button says what it will do",
          __import__("re").fullmatch(r"(Internal|Host|MIDI clock) · bar \d+, beat [1-4] · (Running|Stopped)", clock["line"]) is not None
          and clock["button"] == ("Stop" if clock["state"] == "Running" else "Start"), clock)
    check("the state and the button stay where they are as the bar count grows to three figures", clock["same"], clock)
    null("the button put on the clock's line, its bar's box let shrink to its words, moves as it grows", clock["nullMoved"], clock)
    idle = p.evaluate("""() => { const row = el.quantiseGlide.closest('.menu-row'), out = {};
      el.quantise.checked = false; el.quantise.dispatchEvent(new Event('change')); out.off = row.classList.contains('is-idle');
      el.quantise.checked = true; el.quantise.dispatchEvent(new Event('change')); out.on = row.classList.contains('is-idle');
      el.quantise.checked = false; el.quantise.dispatchEvent(new Event('change'));
      out.knobs = ['quantiseGlide', 'tempo'].map((id) => !!document.getElementById(id).parentElement.querySelector('.knob-face'));
      out.morphKnob = !!el.morphPos.parentElement.querySelector('.knob-face');
      out.tapBeside = el.tempoTap.closest('.menu-row') === el.tempo.closest('.menu-row') && el.tempoTap.getBoundingClientRect().left > el.tempo.closest('.menu-row').querySelector('.knob-face').getBoundingClientRect().right;
      out.before = el.morphPosValue.textContent; el.morphPos.value = '37'; out.after = el.morphPosValue.textContent; el.morphPos.value = '0';
      return out; }""")
    check("Glide is greyed while Quantise is off and not while it is on", idle["off"] is True and idle["on"] is False, idle)
    check("Glide and Tempo are knobs, Tap beside Tempo, and the morph stays a slider", idle["knobs"] == [True, True] and not idle["morphKnob"] and idle["tapBeside"], idle)
    check("the morph's position is read over it, from a value set in code with no event", idle["after"] == "37%", idle)
    null("before it was set the reading was not 37%", idle["before"] != "37%", idle)
    perf = {}
    for w, h in WINDOWS:
        p.set_viewport_size({"width": w, "height": h}); p.wait_for_timeout(300)
        perf[(w, h)] = p.evaluate("""() => { const b = el.performPanel.getBoundingClientRect(), s = el.pictureBar.getBoundingClientRect();
          return { above: b.bottom <= s.top, inside: b.left >= 0 && b.right <= innerWidth + 0.5 && b.top >= 0, scrolls: el.performPanel.scrollHeight > el.performPanel.clientHeight + 1,
                   h: Math.round(b.height / (pageZoom || 1)) }; }""")
    check("at every window Perform is inside the window, above the Picture strip, and nothing in it scrolls",
          all(v["above"] and v["inside"] and not v["scrolls"] for v in perf.values()), perf)
    p.evaluate("() => setPerformOpen(false)")

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails))
sys.exit(1 if fails else 0)
