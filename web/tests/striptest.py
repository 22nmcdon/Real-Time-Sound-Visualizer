"""The Keyboard's band on Play (17 Nov, web/docs/play-redesign.md): the strip
is how the hands share the notes, so what it sets has to reach the instrument,
and what it shows has to be what the instrument plays.

What would go wrong, and what is checked for it, each with its null - the
same reading fed a value it must reject:

- Two hands, or Key, Notes and Layer, lighting without the menus they stand
  for moving: the switches are a view over midiLayers and midiSplitBy, so the
  menus and the setup the face writes are read back after each real click.
  The nulls: the menus before the click, which must not already say it;
- a press on the strip's key not reaching the instrument: G3 pressed, A3
  played must sound in the upper hand's lanes, as Learn's G3 does (layertest).
  The null: the same press with one sound, which sets nothing, so A3 is in
  the lower hand's lanes - the instrument's own C4 split, as it was;
- a press on a place not being the count, and low and high not the end: read
  from the menus and the setup. The null: the seventh place, which is not a
  count (one to six), leaves it;
- the octave buttons moving the sound rather than the view, or not marking a
  note out of view: the range moves, the split point and the held notes do
  not, and a gold mark says which way a held note is;
- the switches showing where they do nothing: Two hands only in Poly on the
  generator, the end and the Chord window's note only by notes, Learn only by
  key; the figure's settings only for their mode (Hold in Dyad, Outline and
  Tune a chord in Poly). The nulls are the other modes;
- M: the on-screen keys open and shut from the computer keyboard, and not
  while typing into a text box, where M is a letter. The null is the text box.
  (That the plugin hides them and M does nothing there is the plugin's shell
  test's, which runs the real face in the real web view.)

Parallel: values and lanes, read after settling, not times.
"""
import os, sys
from playwright.sync_api import sync_playwright
import webfonts, playfigs as PF

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)
def null(name, red, detail=""):
    check("null: " + name, red, detail)

BIN = """(src) => { window.__bin = eval(src); }"""
BIN_SRC = """(x, f, rate) => {
  let re = 0, im = 0;
  for (let i = 0; i < x.length; i++) {
    const w = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (x.length - 1));
    re += x[i] * w * Math.cos(2 * Math.PI * f * i / rate);
    im -= x[i] * w * Math.sin(2 * Math.PI * f * i / rate);
  }
  return Math.hypot(re, im) / x.length;
}"""
# One note's energy in the lower hand's lanes and in the upper's, as the instrument drew them.
HANDS = """async (n) => {
  await new Promise((r) => setTimeout(r, 600));
  const w = state.source.getLatestWindow(16384), rate = state.source.sampleRate;
  const e = w.map((x) => window.__bin(x, 440 * Math.pow(2, (n - 69) / 12), rate));
  return [e[0] + e[1], (e[2] || 0) + (e[3] || 0)];
}"""
READ = """() => ({ layers: el.midiLayers.value, by: el.midiSplitBy.value, end: el.midiSplitEnd.value,
  count: el.midiSplitCount.value, code: (() => { const s = snapshot();
  return [s.layers, s.splitBy, s.splitEnd, s.splitCount].join(' '); })(),
  pill: !el.midiTwoHands.classList.contains('is-unseen') && el.midiTwoHands.getAttribute('aria-pressed'),
  kinds: el.midiKindsRow.hidden ? '' : ['Key', 'Notes', 'Layer'].filter((k) => el['midiKind' + k].getAttribute('aria-checked') === 'true').join(),
  ends: !el.midiEndLowSide.hidden, window: !el.midiWindowNote.hidden, learn: !el.midiSplitLearn.hidden })"""


def page(b):
    p = b.new_page(viewport={"width": 1400, "height": 900})
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(1200)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate("() => setBenchTab('play')"); p.wait_for_timeout(150)
    return p


def key_on_strip(p, note):
    """The middle of a key on the strip, from the drawing's own rectangles."""
    return p.evaluate("""(n) => { const r = el.midiStrip.querySelector('[data-note="' + n + '"]').getBoundingClientRect();
      return [r.x + r.width / 2, r.y + r.height * 0.8]; }""", note)


bad = []
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    print("\n--- only what the mode uses ---")
    p = page(b)
    shown = {}
    for mode in ("dyad", "mono", "poly"):
        p.click("#midi" + mode.capitalize()); p.wait_for_timeout(150)
        shown[mode] = p.evaluate("""() => ({ hold: !el.midiHoldRow.hidden, mono: !el.midiMonoNote.hidden,
          outline: !el.midiDrawRow.hidden, tune: !el.midiPolyJustRow.hidden, pill: !el.midiTwoHands.classList.contains('is-unseen') })""")
    print("    %s" % shown)
    check("Dyad shows Hold the interval and nothing of Poly's", shown["dyad"] == {"hold": True, "mono": False, "outline": False, "tune": False, "pill": False}, str(shown["dyad"]))
    check("Mono shows its line and nothing else", shown["mono"] == {"hold": False, "mono": True, "outline": False, "tune": False, "pill": False}, str(shown["mono"]))
    check("Poly shows Outline, Tune a chord and Two hands, and not Hold", shown["poly"] == {"hold": False, "mono": False, "outline": True, "tune": True, "pill": True}, str(shown["poly"]))
    null("Dyad's set is not Poly's", shown["dyad"] != shown["poly"])

    print("\n--- the pill in the heading, and the band one height (18 Nov, play-figures.md) ---")
    # Two hands is the pill in the Keyboard's heading, unseen in Dyad and Mono but keeping its place, so
    # the heading never reflows; and the band is one height (122 px, 117 compact) in every mode, with one
    # hand or two and each of Key, Notes and Layer, its content inside it. Measured at the six windows.
    BAND = """async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms)), z = pageZoom || 1;
      const box = (n) => { const r = n.getBoundingClientRect(); return [r.left / z, r.top / z, r.width / z, r.height / z].map((v) => Math.round(v * 10) / 10); };
      const out = [];
      const read = (what) => out.push({ what, band: box(document.querySelector('.bench-band')), pill: box(el.midiTwoHands),
        inTitle: el.midiTwoHands.parentElement === el.midiGroup.querySelector(':scope > .menu-title'),
        seen: getComputedStyle(el.midiTwoHands).visibility === 'visible', over: el.midiGroup.scrollHeight - el.midiGroup.clientHeight,
        under: box(document.querySelector('.play-set')) });
      for (const m of ['Dyad', 'Mono', 'Poly']) { el['midi' + m].click(); await wait(150); read(m); }
      el.midiTwoHands.click(); await wait(200); read('Poly, two hands');
      for (const k of ['Notes', 'Layer', 'Key']) { el['midiKind' + k].click(); await wait(150); read('Poly, ' + k); }
      el.midiDyad.click(); await wait(150); read('Dyad, after two hands');
      el.midiPoly.click(); await wait(150); el.midiTwoHands.click(); await wait(150);
      return out;
    }"""
    for w, h in PF.SIZES:
        q = b.new_page(viewport={"width": w, "height": h})
        webfonts.route(q)
        q.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
        q.goto(f"file://{ART}/scope.html?picture=0"); q.wait_for_timeout(1200)
        if q.locator("#helpClose").is_visible(): q.locator("#helpClose").click()
        webfonts.settle(q)
        q.evaluate("() => { setView('bench'); setBenchTab('play'); }"); q.wait_for_timeout(200)
        states = q.evaluate(BAND)
        first = states[0]
        tall = 117 if w < 1100 or h < 860 else 122
        check("%dx%d: the band %d px in Dyad, Mono, Poly, with two hands and each of Key, Notes and Layer, the settings row under it unmoved"
              % (w, h, tall), all(abs(s_["band"][3] - tall) <= 0.5 and s_["band"] == first["band"] and s_["under"] == first["under"] for s_ in states),
              str([(s_["what"], s_["band"][3], s_["under"][1]) for s_ in states if s_["band"] != first["band"] or s_["under"] != first["under"]] or first["band"]))
        check("%dx%d: and its content inside it in every one of those (the least spare %.1f px)" % (w, h, -max(s_["over"] for s_ in states)),
              max(s_["over"] for s_ in states) <= 0, str([(s_["what"], s_["over"]) for s_ in states if s_["over"] > 0]))
        check("%dx%d: Two hands is the pill in the heading, seen in Poly only and in its one place in every mode" % (w, h),
              all(s_["inTitle"] and s_["pill"] == first["pill"] and s_["seen"] == s_["what"].startswith("Poly") for s_ in states),
              str([(s_["what"], s_["seen"], s_["pill"]) for s_ in states]))
        if (w, h) == (960, 600):
            # Nulls: the band 6 px taller with two hands, as testing had it, moves the row under it; a band
            # 90 px tall cuts its content; and the pill hidden by `hidden` rather than unseen moves nothing
            # here but is not in its place to be seen.
            grown = q.evaluate("""async () => { const z = pageZoom || 1, y = () => document.querySelector('.play-set').getBoundingClientRect().top / z;
              const before = y(); el.midiGroup.style.height = (el.midiGroup.offsetHeight + 6) + 'px'; await new Promise((r) => setTimeout(r, 100));
              const after = y(); el.midiGroup.style.height = ''; return [before, after]; }""")
            null("the band 6 px taller with two hands, as testing had it, moves the settings row (%.1f to %.1f)" % tuple(grown), abs(grown[1] - grown[0]) > 0.5)
            cut = q.evaluate("() => { el.midiGroup.style.height = '90px'; const o = el.midiGroup.scrollHeight - el.midiGroup.clientHeight; el.midiGroup.style.height = ''; return o; }")
            null("a band 90 px tall is seen to cut its content (%.1f px over)" % cut, cut > 0)
        q.close()

    print("\n--- Two hands, and Key, Notes, Layer: the menus they stand for ---")
    seen = {"start": p.evaluate(READ)}
    p.click("#midiTwoHands"); p.wait_for_timeout(200); seen["two"] = p.evaluate(READ)
    p.click("#midiKindNotes"); p.wait_for_timeout(200); seen["notes"] = p.evaluate(READ)
    p.click("#midiKindLayer"); p.wait_for_timeout(200); seen["layer"] = p.evaluate(READ)
    p.click("#midiTwoHands"); p.wait_for_timeout(200); seen["off"] = p.evaluate(READ)
    p.click("#midiTwoHands"); p.wait_for_timeout(200); seen["again"] = p.evaluate(READ)
    p.click("#midiKindKey"); p.wait_for_timeout(200); seen["key"] = p.evaluate(READ)
    for k, v in seen.items(): print("    %-6s %s" % (k, v))
    check("Two hands on is a split at a key: the menu, the setup, Key lit and Learn on the line",
          seen["two"]["layers"] == "split" and seen["two"]["by"] == "key" and seen["two"]["code"].startswith("split key")
          and seen["two"]["pill"] == "true" and seen["two"]["kinds"] == "Key" and seen["two"]["learn"] and not seen["two"]["ends"], str(seen["two"]))
    null("before it, one sound", seen["start"]["layers"] == "off" and seen["start"]["pill"] == "false", str(seen["start"]))
    check("Notes is the split by notes, with the counted end and the Chord window's note, and no Learn",
          seen["notes"]["by"] == "notes" and seen["notes"]["code"].startswith("split notes") and seen["notes"]["kinds"] == "Notes"
          and seen["notes"]["ends"] and seen["notes"]["window"] and not seen["notes"]["learn"], str(seen["notes"]))
    check("Layer is layered, and neither the end nor Learn", seen["layer"]["layers"] == "layer" and seen["layer"]["kinds"] == "Layer"
          and not seen["layer"]["ends"] and not seen["layer"]["learn"], str(seen["layer"]))
    check("Two hands off is one sound, the kinds gone", seen["off"]["layers"] == "off" and seen["off"]["kinds"] == "" and seen["off"]["pill"] == "false", str(seen["off"]))
    check("and on again is the sharing it was, layered", seen["again"]["layers"] == "layer" and seen["again"]["kinds"] == "Layer", str(seen["again"]))
    null("a split at a key is not what it came back as", seen["key"]["layers"] == "split" and seen["again"]["layers"] != "split", str(seen["key"]))

    print("\n--- the places and the ends, by notes ---")
    p.click("#midiKindNotes"); p.wait_for_timeout(250)
    places = p.evaluate("""() => [...el.midiStrip.querySelectorAll('[data-count]')].map((r) => r.dataset.count)""")
    def press_place(count):
        xy = p.evaluate("""(c) => { const r = el.midiStrip.querySelector('[data-count="' + c + '"]').getBoundingClientRect();
          return [r.x + r.width / 2, r.y + r.height / 2]; }""", count)
        p.mouse.click(*xy); p.wait_for_timeout(200)
    press_place("3"); three = p.evaluate(READ)
    seventh = p.evaluate("""() => { const svg = el.midiStrip.querySelector('svg'), r = svg.getBoundingClientRect(), w = r.width / 8;
      return [r.x + w * 6.5, r.y + r.height / 2]; }""")
    p.mouse.click(*seventh); p.wait_for_timeout(200); still = p.evaluate(READ)
    p.click("#midiEndHigh"); p.wait_for_timeout(200); high = p.evaluate(READ)
    p.click("#midiEndLow"); p.wait_for_timeout(200)
    press_place("1")
    print("    places %s; the third %s; the seventh %s; high %s" % (places, three["count"], still["count"], high["end"]))
    check("six places are counts, one to six", places == ["1", "2", "3", "4", "5", "6"], str(places))
    check("a press on the third place is a count of three, in the menu and the setup", three["count"] == "3" and three["code"].endswith("lower 3"), str(three))
    null("the seventh place is not a count, and leaves three", still["count"] == "3", str(still))
    check("high counts from the top, in the menu and the setup", high["end"] == "upper" and high["code"].endswith("upper 3"), str(high))
    p.close()

    print("\n--- a key pressed on the strip is the split point, on the instrument ---")
    def strip_split(one_sound):
        q = page(b)
        q.evaluate(BIN, BIN_SRC)
        q.evaluate("() => { setScreenKeys(true); }")
        q.click("#midiPoly"); q.wait_for_timeout(150)
        if not one_sound:
            q.click("#midiTwoHands"); q.wait_for_timeout(250)
        q.mouse.click(*key_on_strip(q, 55)); q.wait_for_timeout(250)
        out = q.evaluate("() => ({ point: midi.layers.point, line: el.midiStripLine.textContent })")
        if one_sound:
            q.click("#midiTwoHands"); q.wait_for_timeout(250)    # after the press: a split, at whatever the press left
        q.evaluate("() => midiNoteOn(57, 100)")
        out["a"], out["b"] = [round(v, 5) for v in q.evaluate(HANDS, 57)]
        q.close()
        return out
    pressed, unpressed = strip_split(False), strip_split(True)
    print("    pressed %s; with one sound %s" % (pressed, unpressed))
    check("G3 pressed on the strip is the point, named on the line", pressed["point"] == 55 and pressed["line"].startswith("G3 and up"), str(pressed))
    check("and the instrument splits there: A3 is in the upper hand's lanes", pressed["b"] > 10 * pressed["a"] and pressed["b"] > 1e-3, str(pressed))
    null("pressed with one sound it sets nothing, and A3 is the lower hand's at C4", unpressed["point"] == 60
         and unpressed["a"] > 10 * unpressed["b"], str(unpressed))

    print("\n--- the octave buttons move the view, and mark a note out of it ---")
    p = page(b)
    p.click("#midiPoly"); p.wait_for_timeout(150)
    p.evaluate("() => midiNoteOn(86, 100)"); p.wait_for_timeout(200)
    before = p.evaluate("() => ({ base: strip.base, up: el.midiStripUp.hasAttribute('data-beyond'), down: el.midiStripDown.hasAttribute('data-beyond'), keys: el.midiStrip.querySelectorAll('[data-note]').length })")
    p.click("#midiStripUp"); p.wait_for_timeout(200)
    after = p.evaluate("() => ({ base: strip.base, up: el.midiStripUp.hasAttribute('data-beyond'), held: midi.notes.map((n) => n.note), point: midi.layers.point, lit: !!el.midiStrip.querySelector('[data-note=\"86\"]') })")
    print("    before %s, after %s" % (before, after))
    check("D6 held above C3-C6's view is marked on the up button, and the strip draws 37 keys", before["up"] and not before["down"] and before["keys"] == 37, str(before))
    check("up an octave moves the view and not the note or the split point", after["base"] == before["base"] + 12 and after["held"] == [86]
          and after["point"] == 60 and after["lit"] and not after["up"], str(after))
    null("the mark is not on the button whose way the note is not", not before["down"])
    p.close()

    print("\n--- M opens and shuts the keys on the screen ---")
    p = page(b)
    p.locator(".sheet-title").click() if p.locator(".sheet-title").is_visible() else None
    p.mouse.click(5, 5)
    p.keyboard.press("m"); p.wait_for_timeout(200); opened = p.evaluate("() => screenKeys.open && !el.screenKeys.hidden")
    p.keyboard.press("m"); p.wait_for_timeout(200); shut = p.evaluate("() => !screenKeys.open")
    p.click("#benchSearch"); p.keyboard.press("m"); p.wait_for_timeout(200)
    typed = p.evaluate("() => ({ open: screenKeys.open, text: el.benchSearch.value })")
    print("    open %s, shut %s, typing %s" % (opened, shut, typed))
    check("M opens the keys, and M again shuts them", opened and shut, str((opened, shut)))
    null("typed into the search, M is a letter and the keys stay shut", typed == {"open": False, "text": "m"}, str(typed))
    row = p.evaluate("() => ({ home: homeOf(el.keysOpen.closest('.menu-group')), group: el.keysOpen.closest('.menu-group').id, shown: !el.keysOpenRow.hidden })")
    check("its button is in Settings' MIDI, beside the Chord window", row == {"home": "settings", "group": "midiSetGroup", "shown": True}, str(row))
    p.close()

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the strip sets the hands the instrument plays, and shows them")
