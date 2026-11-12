"""No Bench tab may scroll - in every combination, not only the ones a
feature's own test happens to set up.

The rule is one of the layout decisions in CLAUDE.md, and each tab was
measured when it changed; but a tab's height depends on things set in other
places - the kind of generator, the band split or the tone, a keyboard
showing, the Photocell on, controllers learned - and nobody measured them
together. A rack of six (cut in P5) with the Photocell on put the Sources tab
18 px over, 74 with a keyboard and a solid, and nothing noticed until a
feature added a line to it.

So, against the ways it fails:

- a tab over in some combination: every tab, on the tone and on the band
  split, with and without the keyboard's sources and the Photocell's, on the
  waveform (and until G2 for each of the four kinds of generator). (Until F4 the Sources tab was swept with
  each family on show, and thirty controllers learned; the tab went with F4
  and the modulation cards, whose editor is held below instead.)
- the rack (F5) over with every effect on and its tallest module open, on
  top of the layered case's extra rows: each module is opened in turn;
- the modulation editor over in the worst case it has: an oscillator on a
  dozen controls, each a row of Where it goes;
- the modulation row (G5a) taking more than the tabs can give: since it runs
  across the window under the screen and the tabs, every case above is
  measured with it in place, and the row is read back as there, under the
  tabs, as cards at 1400x900 and chips at every smaller window. Its null:
  at 1100x860 the same Ink tab with the cards' row in place of the chips
  scrolls, so the fold to chips is what fits it;
- a dealer that measures a section at a width it will not have. It stacks
  every section in the first column to measure them, and with the empty
  columns hidden that column was the whole Bench wide, so everything that
  wraps measured short and the dealer paired sections that could not fit
  together. Each section's measured height is held to its height once dealt.
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


SWEEP = """async ([bands]) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  /* The band split: an input of four lanes, with Picture's Lanes section on
     show - the worst case since P5 cut the rack, whose six lanes it was. */
  if (bands) {
    el.srcMic.click(); await wait(1500);
    el.micBands.click(); await wait(900);
  }
  const lanes = laneCount();
  setView('bench');
  const over = [], cases = [], mismeasured = [];
  let planeRows = null;
  const rackOpened = [];
  const measure = (label) => {
    const views = [];
    for (const [tab] of BENCH_TABS) views.push([tab, null]);
    let last = null;
    for (const [tab, family] of views) {
      setBenchTab(tab);
      /* What the dealer measured each section at, against what it is now -
         straight after the deal, which is what this holds. A section can
         change height afterwards without anything being wrong: the source's
         detail does with the source chosen, and always did, and it has a
         column to itself. Whether any of that puts the tab over is the
         overflow check's question, asked below for every family. */
      if (tab !== last) {
        for (const [group, h] of benchMeasured) {
          if (Math.abs(group.offsetHeight - h) > 1) mismeasured.push([label, tab, group.id || '?', h, group.offsetHeight]);
        }
      }
      last = tab;
      const by = el.benchBody.scrollHeight - el.benchBody.clientHeight;
      const name = family ? tab + ':' + family : tab;
      cases.push(label + '/' + name);
      /* F8 let the drawings off at the compact sizes, parked and 135 px past
         the tab at 960x600; G2 took them, and every case is held now. */
      if (by > 0) over.push([label, name, by]);
    }
  };
  for (const keys of [false, true]) {
    if (keys) { setScreenKeys(true); await wait(100); }
    for (const photoOn of [false, true]) {
      if (photoOn !== photo.on) { el.photoButton.click(); await wait(150); }
      // Each generator kind in turn until G2; the waveform is the one now.
      await wait(120);
      measure([bands ? 'bands' : 'tone', keys ? 'keys' : '', photoOn ? 'photo' : '', 'wave'].filter(Boolean).join('+'));
    }
  }
  /* Two hands, the upper edited and every section its own (G6): the
     header's Editing and a link on every section's title, the Plane's Turn
     the upper's own in the screen's rotation's place, and the clip at the
     radius showing the radius's. (Until G6 B's own plane grew a Layers row
     and a row for B's Turn, and the Delay module a Layers row.) A drawn
     input keeps a split without applying it, so only the tone. */
  if (!bands) {
    setMidiMode('poly');
    el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change')); await wait(120);
    document.getElementById('editHandB').click();
    document.querySelectorAll('.hand-link[aria-pressed="true"]').forEach((link) => link.click());
    el.planeLimit.value = '1'; el.planeLimit.dispatchEvent(new Event('change')); await wait(120);
    planeRows = [el.planeTurnRow.hidden, !el.rotateRow.hidden, el.planeRadiusRow.hidden,
                 document.getElementById('handsPick').hidden,
                 [...document.querySelectorAll('.hand-link')].filter((link) => link.hidden || link.getAttribute('aria-pressed') !== 'false').length];
    measure('tone+keys+photo+layers+planeB');
    /* And the rack (F5) at its tallest: every effect on, so no module is
       folded to its line, and each one opened in turn with its rest showing,
       on top of the layered rows above. Which module was open is read back
       from the page, so a sweep that never opened one cannot pass. */
    for (const id of ['delayMix', 'chorusMix', 'phaserMix']) setControl(id, 40);
    for (const fx of ['plane', 'phaser', 'chorus', 'delay']) {
      openFx(fx, true); await wait(80);
      const rest = document.querySelector('.fx-module[data-fx="' + fx + '"] .fx-rest');
      if (!rest.hidden) rackOpened.push(fx);
      measure('tone+keys+photo+layers+planeB+effects+' + fx);
    }
    openFx(null);
    for (const id of ['delayMix', 'chorusMix', 'phaserMix']) setControl(id, 0);
    document.querySelectorAll('.hand-link[aria-pressed="false"]').forEach((link) => link.click());
    document.getElementById('editHandA').click(); setMidiMode('dyad');
    el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change')); await wait(120);
  }
  /* The modulation editor (F4), which must not scroll either: LFO 1 on a
     dozen controls, a row each under Where it goes - the column that grows. */
  const dests = Array.from(MOD_DESTS.values()).filter((d) => routingAllowed(MOD_SOURCES.get('lfo1'), d)).slice(0, 12);
  for (const d of dests) addRouting('lfo1', d.id);
  openModCard('lfo1'); await wait(150);
  // The panel cannot be over since the list scrolls inside itself past a
  // dozen; so the list is held too, which a dozen must fit without scrolling.
  const goes = el.srcDetail.querySelector('.src-goes');
  const editor = { rows: el.srcDetail.querySelectorAll('.mod-edit').length,
                   over: el.modEditor.scrollHeight - el.modEditor.clientHeight,
                   list: goes.scrollHeight - goes.clientHeight };
  closeModCard(); state.modRoutings = []; touchRoutings();
  // The row, read back: where it is and what it is showing.
  const rowBox = el.modRow.getBoundingClientRect(), mainBox = document.querySelector('.bench-main').getBoundingClientRect();
  const row = { under: rowBox.top >= mainBox.bottom - 1 && rowBox.top >= el.benchSide.getBoundingClientRect().bottom - 1,
                height: Math.round(rowBox.height), chips: document.body.dataset.chips !== undefined,
                cards: el.modStrip.querySelectorAll('.mod-card').length };
  /* The null: the cards' row in place of the chips, on Ink, the tab that was
     over at 1100x860 before the fold. Only where the row is chips. */
  if (row.chips) {
    setBenchTab('ink'); await wait(80);
    delete document.body.dataset.chips; await wait(80);
    row.cardsOver = el.benchBody.scrollHeight - el.benchBody.clientHeight;
    document.body.dataset.chips = ''; await wait(80);
  }
  return { over, cases: cases.length, mismeasured, editor, planeRows, lanes, rackOpened, row };
}"""

# The Picture's Advanced (11 Nov): with a split, so what Scan reads and the
# Pictures rows show, and How the picture responds on Custom, so its two
# knobs show - every row it can have at once - inside the window and not
# scrolling. `extra` copies of the response group are put in for the null,
# which must go over.
ADVANCED = r"""async (extra) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  setMidiMode('poly');
  el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change')); await wait(120);
  el.pictureFeel.value = 'custom'; el.pictureFeel.dispatchEvent(new Event('change'));
  el.pictureSwell.checked = true; el.pictureSwell.dispatchEvent(new Event('change'));
  const group = document.getElementById('responseGroup');
  const copies = [];
  for (let k = 0; k < extra; k++) { const c = group.cloneNode(true); c.removeAttribute('id');
    c.querySelectorAll('[id]').forEach((n) => n.removeAttribute('id')); group.after(c); copies.push(c); }
  setPictureOpen(true); await wait(150);
  const box = el.picturePanel.getBoundingClientRect();
  const shown = [el.pictureMovesRow, el.scanReadsRow, el.pictureRiseRow, el.pictureFallRow].map((r) => !r.hidden && !!r.offsetParent);
  const out = { inside: box.top >= 0 && box.bottom <= innerHeight + 1 && box.left >= 0 && box.right <= innerWidth + 1,
                over: el.picturePanel.scrollHeight - el.picturePanel.clientHeight, shown,
                knobs: [el.pictureRise, el.pictureFall].every((i) => i.classList.contains('knob-dial')) };
  setPictureOpen(false);
  copies.forEach((c) => c.remove());
  return out;
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required",
                                 "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
    # F8: at the page's own size, and at the plugin's default (1200x680)
    # and minimum (960x600), where the face is compact.
    # Each with Size on Auto, as a new user has it, and the zoom Auto should
    # choose: 100 at the page's size, the plugin's default and the corner
    # where 100 still applies; 90 at the plugin's minimum (the owner's
    # choice, 8 Nov). Read back from the page, so an Auto that chose wrong
    # fails here even where the face happened to fit.
    # The full face at the page's size and at its smallest (1100x860); the
    # compact one at the plugin's default, at its own corner at 100, and at
    # the plugin's minimum, where Auto makes it 90.
    SIZES = [(1400, 900, "auto", 1), (1100, 860, "auto", 1), (1200, 680, "auto", 1), (1100, 680, "auto", 1),
             (960, 600, "auto", 0.9)]
    # FIT_SIZES="960x600@0.9,1100x700@1" sweeps others at a Size chosen, for measuring a choice.
    if os.environ.get("FIT_SIZES"):
        SIZES = [(int(a.split("x")[0]), int(a.split("x")[1].split("@")[0]), float(a.split("@")[1]), float(a.split("@")[1]))
                 for a in os.environ["FIT_SIZES"].split(",")]
    zooms = {}
    results = {}
    bad = []
    for w, h, zoom, want_zoom in SIZES:
        ctx = b.new_context(permissions=["microphone"], viewport={"width": w, "height": h})
        for bands in (False, True):
            p = ctx.new_page()
            p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
            p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
            if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
            if zoom != "auto": p.evaluate("(z) => setSize(z)", zoom); p.wait_for_timeout(300)
            zooms[(w, h)] = (p.evaluate("() => pageZoom"), want_zoom)
            results[("bands" if bands else "tone", w, h)] = p.evaluate(SWEEP, [bands])
            p.close()
        p = ctx.new_page()
        p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
        p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
        if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
        if zoom != "auto": p.evaluate("(z) => setSize(z)", zoom); p.wait_for_timeout(300)
        adv = p.evaluate(ADVANCED, 0)
        check("the Picture's Advanced at %dx%d, split and on Custom - Reads, Pictures, Responds to, Rise, fall and its two "
              "knobs - is inside the window and does not scroll" % (w, h),
              adv["inside"] and adv["over"] <= 1 and adv["shown"] == [True] * 4 and adv["knobs"], str(adv))
        if (w, h) == (960, 600):
            crowded = p.evaluate(ADVANCED, 3)
            check("null: three more such groups in it at 960x600 go over", not (crowded["inside"] and crowded["over"] <= 1), str(crowded))
        p.close()
        ctx.close()

    for (name, w, h), r in results.items():
        print("\n--- %s at %dx%d: %d tab-and-state cases ---" % (name, w, h, r["cases"]))
        check("on the %s at %dx%d, no tab scrolls in any of them" % ("band split" if name == "bands" else "tone", w, h),
              # Three tabs since F4 took the Sources tab and its seven families,
              # so the sweep was about fifty cases where it was 180; and one
              # kind since G2 where there were four, so twelve on the band
              # split (four states, three tabs) and 27 on the tone with its
              # layered and rack cases.
              r["over"] == [] and r["cases"] >= (24 if name == "tone" else 12) and r["lanes"] == (4 if name == "bands" else 2),
              "%d lanes; %s" % (r["lanes"], r["over"][:6]))
        want_chips = (w, h) != (1400, 900)
        check("the modulation row was across the window under the tabs, four %s (%dx%d)" % ("chips" if want_chips else "cards", w, h),
              r["row"]["under"] and r["row"]["cards"] == 4 and r["row"]["chips"] == want_chips
              and (r["row"]["height"] <= 40 if want_chips else r["row"]["height"] >= 70), str(r["row"]))
        if (w, h) == (1100, 860) and name == "tone":
            check("null: at 1100x860 the cards' row in place of the chips puts Ink over", r["row"].get("cardsOver", 0) > 0,
                  str(r["row"]))
        check("and every section is dealt at the height it was measured at (%dx%d)" % (w, h),
              r["mismeasured"] == [], str(r["mismeasured"][:4]))
        check("an oscillator on a dozen controls is a dozen rows in its editor, and the editor does not scroll (%dx%d)" % (w, h),
              r["editor"]["rows"] == 12 and r["editor"]["over"] <= 0 and r["editor"]["list"] <= 0, str(r["editor"]))
        if name == "tone":
            check("the layered case had the upper's own Turn in the screen's rotation's place, the Radius row, the header's "
                  "Editing and every section's link showing, each the hand's own (%dx%d)" % (w, h),
                  r["planeRows"] == [False, False, False, False, 0], str(r["planeRows"]))
            check("and on top of it each of the rack's modules was measured open, every effect on (%dx%d)" % (w, h),
                  r["rackOpened"] == ["plane", "phaser", "chorus", "delay"], str(r["rackOpened"]))

    check("Size chose the zoom it should at each window", all(got == want for got, want in zooms.values()), str(zooms))
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("every tab fits, whatever else is on")
