"""The info line (G3b): every control says what it does, and the line says it
when the pointer rests, not when it passes.

What would go wrong, and what is checked for it:

- the words in the page drifting from the doc they are written from
  (web/docs/what-each-control-says.md, by web/tools/write_words.py): the page's
  CONTROL_WORDS is compared with the doc as the script reads it. The null: the
  same doc with one line changed is not what the page has;
- a control on the face with no words - one added later, or renamed: every
  control in a section, the header, the Picture section and the rack's
  handles must find its words, but for those the doc says a later stage
  removes. The null: the same check with one control's words taken out finds
  it;
- the line changing under the pointer on its way to More, the owner's
  objection to the first design: a quick sweep across a row of knobs leaves
  it alone. The null: the same path, resting on each, changes it;
- a turned knob not saying what it is until the pointer rests: touching takes
  the line at once;
- More and ? opening the card with the line in it, Esc closing it, and its
  steps going to the next control in the section;
- the switch in This window hiding the line, and the browser remembering it;
- where it sits: the Picture section's free middle at every size, taking no
  height, two lines at most, the three reads still in the window.

Serial: the rest is a third of a second of real time, and a busy machine
stretches a sweep that has to be quicker than it.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ART, "tools"))
import write_words  # noqa: E402

CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    """A check's null: the same comparison fed a value it must reject."""
    check("null: " + name, red, detail)

# Controls the doc marks as removed by a later stage: no words, on purpose.
# Anything else without words fails. (The drawings' rows and the keyboard's
# drive and play were here until G2 took them off the page.)
REMOVED = {"abA", "abB", "viewScope", "viewBench", "midiEditA", "midiEditB",
           "planeTurn", "planeLayerBoth", "planeLayerA", "planeLayerB", "timeLayerBoth", "timeLayerA", "timeLayerB"}

# Every control the face shows, and those without words.
UNSAID = """(removed) => {
  /* Not asked of: the cheat sheet, and Input into the generator, which the
     doc has no rows for - it was let off with the drawings' rows when it
     still held the second generator, and only that part of it went in G2. */
  const drawings = '#inputGroup, #helpDialog';
  const places = '.menu-group, header, .picture-bar, .screen-tools, #keysPanel, .mod-strip, #benchRail';
  const out = [];
  for (const c of document.querySelectorAll('input, select, button')) {
    if (c.type === 'file' || c.type === 'hidden' || c.closest(drawings) || !c.closest(places)) continue;
    if (c.closest('.over, .info-line, #benchResults')) continue;
    // Made for a moment and unnamed: the cards' editors' rows, a chip's clear.
    if (!c.id && !c.matches('[data-fx-on], [data-fx-open], [data-fx-move], .mod-card, [role=tab][id^="benchTab-"]')) continue;
    if (removed.includes(c.id)) continue;
    if (!wordsKey(c)) out.push(c.id || c.className);
  }
  return out;
}"""

def centre(p, selector):
    r = p.locator(selector).first.bounding_box()
    return (r["x"] + r["width"] / 2, r["y"] + r["height"] / 2)

def face_of(input_id):
    return "#%s ~ .knob-face, .menu-row:has(#%s) .knob-face" % (input_id, input_id)

def said(p):
    return p.evaluate("() => ({ name: el.infoName.textContent, text: el.infoText.textContent, at: infoAt && infoAt.id })")

with sync_playwright() as pw:
    print("\n--- the words are the doc's ---")
    doc = open(write_words.DOC, encoding="utf-8").read()
    page_text = open(write_words.PAGE, encoding="utf-8").read()
    want = write_words.block(write_words.parse(doc))
    check("the page's CONTROL_WORDS is what web/tools/write_words.py makes of the doc", want in page_text,
          "%d controls" % len(write_words.parse(doc)))
    changed = doc.replace("Where the filter starts taking the top off.", "Where the filter starts taking the bottom off.", 1)
    null("the doc with one line changed is not what the page has",
         changed != doc and write_words.block(write_words.parse(changed)) not in page_text)

    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    p = ctx.new_page()
    bad = []
    p.on("pageerror", lambda e: bad.append(str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(2500)
    p.evaluate("() => { const d = document.getElementById('helpDialog'); if (d && d.open) d.close(); setView('bench'); setBenchTab('play'); }")
    p.wait_for_timeout(300)

    print("\n--- every control says something ---")
    # Each tab in turn, since a tab's sections are in the store until it is shown.
    unsaid = []
    for tab in ("play", "ink", "space"):
        p.evaluate("(t) => setBenchTab(t)", tab); p.wait_for_timeout(150)
        unsaid += p.evaluate(UNSAID, sorted(REMOVED))
    unsaid = sorted(set(unsaid))
    check("every control on the face, but those a later stage removes, has its words", not unsaid, str(unsaid[:12]))
    knocked = p.evaluate("""(removed) => { const keep = CONTROL_WORDS.vcfCut; delete CONTROL_WORDS.vcfCut;
      setBenchTab('play'); const u = (%s)(removed); CONTROL_WORDS.vcfCut = keep; return u; }""" % UNSAID, sorted(REMOVED))
    null("with the cutoff's words taken out, the check finds the cutoff", "vcfCut" in knocked, str(knocked))
    keyed = p.evaluate("""() => ['[data-fx-on]', '[data-fx-open]', '[data-fx-move]', '.mod-card', '#benchTab-ink']
      .map((s) => { setBenchTab('space'); const n = document.querySelector(s); return [s, n ? wordsKey(n) : 'missing']; })""")
    check("the controls with no id find theirs: the rack's switch, arrow and handle, a card, a tab",
          all(k not in (None, "missing") for _, k in keyed), str(keyed))
    p.evaluate("() => setBenchTab('play')"); p.wait_for_timeout(200)

    print("\n--- resting, not passing ---")
    knobs = ["envAttack", "envDecay", "envSustain", "envRelease"]
    pts = [centre(p, face_of(k)) for k in knobs]
    empty = (pts[-1][0] + 120, pts[-1][1] + 60)
    # Rest on Attack, then sweep across the other three and off into the space beside them.
    p.mouse.move(*pts[0]); p.wait_for_timeout(500)
    first = said(p)
    check("resting a third of a second on Attack puts it on the line", first["at"] == "envAttack", str(first))
    for x, y in pts[1:] + [empty]:
        p.mouse.move(x, y, steps=2); p.wait_for_timeout(40)
    p.wait_for_timeout(500)
    swept = said(p)
    check("a quick sweep across Decay, Sustain and Release and off leaves Attack on the line", swept["at"] == "envAttack", str(swept))
    for x, y in pts[1:]:
        p.mouse.move(x, y, steps=2); p.wait_for_timeout(450)
    p.mouse.move(*empty); p.wait_for_timeout(450)
    rested = said(p)
    null("the same path resting on each ends on Release, and holds it off the knobs", rested["at"] == "envRelease", str(rested))

    print("\n--- touching ---")
    p.mouse.move(*centre(p, face_of("envSustain"))); p.mouse.down(); p.mouse.move(pts[2][0], pts[2][1] - 30, steps=3)
    touched = said(p)
    p.mouse.up()
    check("a knob turned is on the line at once, before any rest", touched["at"] == "envSustain", str(touched))
    p.mouse.move(*empty); p.wait_for_timeout(100)
    p.focus("#midiBendRange"); p.wait_for_timeout(50)
    focused = said(p)
    check("and so is a control the keyboard moves to", focused["at"] == "midiBendRange", str(focused))
    null("what was on the line before the focus was something else", touched["at"] != "midiBendRange")

    print("\n--- the card ---")
    p.mouse.move(*centre(p, face_of("vcfCut"))); p.wait_for_timeout(500)
    before = p.evaluate("() => !!document.querySelector('.over.info-card, .over .info-card')")
    p.click("#infoMore"); p.wait_for_timeout(300)
    card = p.evaluate("""() => { const o = document.querySelector('.over'); return o && {
      title: o.querySelector('.over-title').textContent, line: (o.querySelector('.info-card-line') || {}).textContent,
      facts: Array.from(o.querySelectorAll('dt')).map((d) => d.textContent),
      steps: Array.from(o.querySelectorAll('.info-card-steps button')).map((b) => b.textContent) }; }""")
    check("More opens the card: the name, the line, what modulates it, and a step to the next control",
          card and card["title"] == "Cutoff" and card["line"] == p.evaluate("() => CONTROL_WORDS.vcfCut[1]")
          and "Modulated by" in card["facts"] and any("Resonance" in s for s in card["steps"]), str(card))
    null("no card was open before More", before is False)
    p.locator(".over .info-card-steps button", has_text="Resonance").click(); p.wait_for_timeout(300)
    stepped = p.evaluate("() => document.querySelector('.over .over-title').textContent")
    check("its step goes to Resonance's card, and the line follows", stepped == "Resonance" and said(p)["at"] == "vcfRes", stepped)
    p.keyboard.press("Escape"); p.wait_for_timeout(200)
    check("Esc closes it", p.evaluate("() => !document.querySelector('.over')"))
    p.mouse.move(*empty); p.wait_for_timeout(100)
    p.keyboard.press("?"); p.wait_for_timeout(300)
    keyed_card = p.evaluate("() => { const o = document.querySelector('.over'); return o && o.querySelector('.over-title').textContent; }")
    check("? opens the card for the control on the line", keyed_card == "Resonance", str(keyed_card))
    p.keyboard.press("Escape"); p.wait_for_timeout(150)

    print("\n--- the switch ---")
    p.evaluate("() => { el.infoLineOn.checked = false; el.infoLineOn.dispatchEvent(new Event('change')); }")
    off = p.evaluate("() => ({ shown: el.infoLine.offsetParent !== null, kept: localStorage.getItem('scope.infoLine') })")
    p.reload(); p.wait_for_timeout(2000)
    after = p.evaluate("() => ({ shown: el.infoLine.offsetParent !== null, box: el.infoLineOn.checked })")
    check("off hides the line, and the browser remembers it across a reload",
          off == {"shown": False, "kept": "0"} and after == {"shown": False, "box": False}, "%s / %s" % (off, after))
    p.evaluate("() => { el.infoLineOn.checked = true; el.infoLineOn.dispatchEvent(new Event('change')); }")
    on = p.evaluate("() => el.infoLine.offsetParent !== null")
    null("on, it is shown", on is True)

    print("\n--- where it sits ---")
    # In the Picture section's free middle at every size, so it takes no
    # height: two lines at most, the three reads still in the window, and the
    # section no taller than without it. Measured at the full face, the
    # plugin's opening size and its minimum (960x600 at Auto's 90 per cent).
    sit = {}
    for w, h in ((1400, 900), (1200, 680), (1067, 667)):
        p.set_viewport_size({"width": w, "height": h}); p.wait_for_timeout(500)
        p.mouse.move(*centre(p, face_of("scanStrike"))); p.wait_for_timeout(500)
        sit[(w, h)] = p.evaluate("""() => {
          const wrap = el.infoLine.querySelector('.info-wrap'), lh = parseFloat(getComputedStyle(wrap).lineHeight);
          const bar = el.pictureBar.getBoundingClientRect(), reads = el.pictureBar.querySelector('.picture-meters').getBoundingClientRect();
          const hid = el.infoLine.hidden; el.infoLine.hidden = true; const without = el.pictureBar.getBoundingClientRect().height;
          el.infoLine.hidden = hid;
          return { inBar: el.infoLine.parentElement === el.pictureBar.querySelector('.picture-wrap'), said: infoAt && infoAt.id,
                   lines: Math.round(wrap.getBoundingClientRect().height / lh), readsIn: reads.right <= window.innerWidth + 1,
                   taller: Math.round(bar.height - without) }; }""")
    print("    " + "; ".join("%dx%d %s" % (w, h, v) for (w, h), v in sit.items()))
    check("in the Picture section at every size, two lines at most, the reads in the window and the section no taller",
          all(v["inBar"] and v["said"] == "scanStrike" and 1 <= v["lines"] <= 2 and v["readsIn"] and v["taller"] <= 0
              for v in sit.values()), str(sit))
    unclamped = p.evaluate("""() => { const wrap = el.infoLine.querySelector('.info-wrap'), t = el.infoText.textContent;
      wrap.style.webkitLineClamp = 'unset'; el.infoText.textContent = t + ' ' + t + ' ' + t;
      const n = Math.round(wrap.getBoundingClientRect().height / parseFloat(getComputedStyle(wrap).lineHeight));
      wrap.style.webkitLineClamp = ''; el.infoText.textContent = t; return n; }""")
    null("three times the words with the limit off run past two lines, so the count can fail", unclamped > 2, str(unclamped))
    p.set_viewport_size({"width": 1400, "height": 900}); p.wait_for_timeout(300)

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails))
sys.exit(1 if fails else 0)
