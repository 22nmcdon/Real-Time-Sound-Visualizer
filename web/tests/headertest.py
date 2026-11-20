"""The header (F7 of web/docs/redesigning-the-face.md): the preset's arrows, its
heading, Browse and Save, and undo.

What would go wrong, and what is checked for it:

- the arrows stepping in some order other than the browser's, or not
  wrapping, or doing nothing from a sound that is not the bank's. The order
  is read from the browser's own cards, heading by heading, so the two cannot
  disagree without failing here;
- the heading above the name saying something other than where the preset
  lives;
- undo that records nothing, or a step per key press, or a step for a
  change no hand made (a host's automation would fill the history), or that
  puts back the sound and not its name; redo that is lost, or kept after a
  new change;
- A and B coming back (G4 took them out, the-face-second-pass.md): no button
  for either and no second history behind undo. Until G4 this suite held
  them to being two versions, each with its own history;
- Ctrl+Z in a text field taken from the field.

Every change here is made with the real mouse and keyboard, since undo counts
only what follows a trusted event: a knob turned by dispatchEvent is, rightly,
no step at all, and is the null for that rule.
"""
import time
import os, re, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def moved(w, h, an, a, bn, b):
    """Every header box that differs between two readings, with how long after opening each was read."""
    print("      MOVED at %dx%d: %s read %.2f s after opening, %s %.2f s" % (w, h, an, a["since"], bn, b["since"]))
    for k in sorted(set(a["boxes"]) | set(b["boxes"])):
        if a["boxes"].get(k) != b["boxes"].get(k):
            print("        %s: %s %s, %s %s" % (k, an, a["boxes"].get(k), bn, b["boxes"].get(k)))

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(800)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(300)
    # One history since G4: what was versions[versions.on] is undoHistory.
    state = lambda: p.evaluate("""() => ({ value: el.preset.value, heading: document.getElementById('presetLabel').textContent,
      name: el.presetCurrent.textContent, freq: Number(el.freq.value), undo: undoHistory.undo.length,
      redo: undoHistory.redo.length, undoOff: el.undoButton.disabled, redoOff: el.redoButton.disabled,
      edited: !el.presetEdited.hidden && presetEdited })""")
    CLEAR = "undoHistory.undo = []; undoHistory.redo = []; undoRebase(); paintUndo();"
    settle = lambda: p.wait_for_timeout(700)

    print("\n--- the arrows and the heading ---")
    # The browser's order, read off its cards heading by heading.
    browser = p.evaluate("""() => {
      openPresets();
      const out = [];
      for (const [id] of presetMenuList().filter(([id]) => id !== 'saved')) {
        el.presetMenus.querySelector('[data-menu="' + id + '"]').click();
        for (const c of el.presetGrid.querySelectorAll('.preset-card')) out.push(c.dataset.value);
      }
      el.presetDialog.close();
      return out;
    }""")
    p.evaluate("() => applyPreset('b:Slow pad')"); p.wait_for_timeout(200)
    at = browser.index("b:Slow pad")
    p.click("#presetNext"); p.wait_for_timeout(200); nxt = state()
    p.click("#presetPrev"); p.wait_for_timeout(200); back = state()
    check("the next arrow loads the next card in the browser's order, and the previous comes back",
          nxt["value"] == browser[at + 1] and back["value"] == "b:Slow pad", "%s, %s" % (nxt["value"], back["value"]))
    check("null: the next is not the one it came from", nxt["value"] != "b:Slow pad")
    check("the heading above the name is where it lives", back["heading"] == "Breathing" and back["name"] == "Slow pad"
          and nxt["heading"] == "Breathing", str((back["heading"], nxt["heading"])))
    p.evaluate("(v) => applyPreset(v)", browser[-1]); p.wait_for_timeout(150)
    p.click("#presetNext"); p.wait_for_timeout(200); wrapped = state()
    p.evaluate("() => { loadedSetup = null; setPresetValue(''); }")
    custom = state()
    p.click("#presetNext"); p.wait_for_timeout(200); first = state()
    p.evaluate("() => { loadedSetup = null; setPresetValue(''); }")
    p.click("#presetPrev"); p.wait_for_timeout(200); last = state()
    check("past the last it wraps to the first; from Custom, next is the first and previous the last",
          wrapped["value"] == browser[0] and first["value"] == browser[0] and last["value"] == browser[-1]
          and custom["heading"] == "Preset" and custom["name"] == "Custom" and first["heading"] == "Settled",
          str((wrapped["value"], first["value"], last["value"], custom["heading"])))
    p.click("#presetBrowse"); p.wait_for_timeout(200)
    browse = p.evaluate("() => ({ open: el.presetDialog.open, saving: !el.presetSaving.hidden })")
    p.keyboard.press("Escape"); p.wait_for_timeout(150)
    p.click("#presetSaveHead"); p.wait_for_timeout(200)
    save = p.evaluate("() => ({ open: el.presetDialog.open, saving: !el.presetSaving.hidden, focus: document.activeElement === el.presetName })")
    p.keyboard.press("Escape"); p.wait_for_timeout(150)
    check("Browse opens the browser, and Save opens it at its save field with the name to type",
          browse == {"open": True, "saving": False} and save == {"open": True, "saving": True, "focus": True}, str((browse, save)))

    print("\n--- undo ---")
    p.evaluate("() => applyPreset('b:Slow pad')"); settle()
    p.evaluate("() => { %s }" % CLEAR)
    start = state()
    # Five presses of the arrow key on the frequency, quickly: one step.
    p.evaluate("() => { showControl('freq'); el.freq.focus(); }")
    for _ in range(5): p.keyboard.press("ArrowUp")
    settle(); turned = state()
    check("null: with nothing done there is nothing to undo", start["undo"] == 0 and start["undoOff"], str(start))
    # Until 15 Nov this said Custom; an edit keeps the preset's name and says it is edited.
    check("a knob turned by five key presses is one step, and says it is the preset edited",
          turned["freq"] != start["freq"] and turned["undo"] == 1 and not turned["undoOff"] and turned["value"] == "b:Slow pad"
          and turned["edited"],
          str((start["freq"], turned)))
    p.click("#undoButton"); settle(); undone = state()
    check("undo puts back the sound and its name, and redo is offered",
          undone["freq"] == start["freq"] and undone["value"] == "b:Slow pad" and undone["name"] == "Slow pad" and not undone["edited"]
          and undone["undo"] == 0 and undone["redo"] == 1 and not undone["redoOff"], str(undone))
    p.keyboard.press("Control+Shift+Z"); settle(); redone = state()
    check("Ctrl+Shift+Z redoes it", redone["freq"] == turned["freq"] and redone["undo"] == 1 and redone["redo"] == 0, str(redone))
    p.keyboard.press("Control+z"); settle()
    p.evaluate("() => { el.freq.focus(); }")
    p.keyboard.press("ArrowDown"); settle(); fresh = state()
    check("Ctrl+Z undoes, and a new change after it drops what could have been redone",
          fresh["redo"] == 0 and fresh["undo"] == 1 and fresh["freq"] == start["freq"] - 1, str(fresh))
    # A change no hand made: the base moves, and no step is recorded.
    p.evaluate("() => { el.amp.value = '20'; el.amp.dispatchEvent(new Event('input')); }"); settle()
    quiet = state()
    check("a change made by code alone - as a host's automation is - is not a step", quiet["undo"] == fresh["undo"], str(quiet))
    # A preset loaded by a hand is one step, glide and all.
    p.click("#presetNext"); p.wait_for_timeout(1500); stepped = state()
    p.click("#undoButton"); settle(); unstepped = state()
    check("a preset loaded with the arrow is one step, and undo goes back off it",
          stepped["undo"] == fresh["undo"] + 1 and unstepped["value"] == "b:Slow pad" and unstepped["edited"]
          and unstepped["freq"] == fresh["freq"],
          str((stepped, unstepped)))
    # Spread out: five presses 250 ms apart, so the history is looked at
    # twice between each - still one step, since it waits 400 ms for them to
    # stop. (At 90 ms apart a history that recorded any change seen twice
    # would also have made one step, and the mutation pass showed it.)
    p.evaluate("() => { %s el.freq.focus(); }" % CLEAR)
    for _ in range(5):
        p.keyboard.press("ArrowUp"); p.wait_for_timeout(250)
    settle(); spread = state()
    check("five presses spread over a second and a quarter are still one step", spread["undo"] == 1, str(spread))
    # A knob dragged with the mouse, held still half way for longer than a
    # step waits: one step, since a pointer still down is a change not done.
    face = p.evaluate("""() => { const r = el.freq.parentElement.querySelector('.knob-face').getBoundingClientRect();
      return [r.x + r.width / 2, r.y + r.height / 2]; }""")
    p.mouse.move(*face); p.mouse.down(); p.mouse.move(face[0], face[1] - 30, steps=5)
    p.wait_for_timeout(700)
    p.mouse.move(face[0], face[1] - 60, steps=5); p.mouse.up(); settle()
    dragged = state()
    # And all of it: undo then redo lands where the drag ended, not where it
    # paused - a step taken mid-drag would redo only half of it.
    p.click("#undoButton"); settle(); p.click("#redoButton"); settle()
    redrag = state()
    check("a drag held still half way and let go is one step, and redo gives back the whole of it",
          dragged["undo"] == 2 and dragged["freq"] != spread["freq"] and redrag["freq"] == dragged["freq"],
          str((spread["freq"], dragged["freq"], redrag["freq"])))
    # A native slider, whose input events are the browser's own and trusted:
    # a drawbar dragged and held still half way. Without the pointer counted
    # as a change in progress, the pause is a step and the rest of the drag,
    # trusted too, another. (A knob's face sends its value by code, so on a
    # knob the second half was absorbed and the mutation pass could not tell.)
    # Upright under Play's Wave since 18 Nov (on Ink, lying down, until then): dragged up from its foot.
    p.evaluate("() => { applyPreset('b:Drawbar organ'); showControl('bar3'); }"); p.wait_for_timeout(600)
    p.evaluate("() => { %s }" % CLEAR)
    bar = p.evaluate("() => { const r = el.bar3.getBoundingClientRect(); return [r.x + r.width / 2, r.bottom - 3, r.height, el.bar3.value]; }")
    p.mouse.move(bar[0], bar[1]); p.mouse.down(); p.mouse.move(bar[0], bar[1] - bar[2] * 0.35, steps=6)
    p.wait_for_timeout(700)
    p.mouse.move(bar[0], bar[1] - bar[2] * 0.75, steps=6); p.mouse.up(); settle()
    slid = p.evaluate("() => ({ value: el.bar3.value, undo: undoHistory.undo.length })")
    check("a drawbar dragged, held still half way and let go is one step",
          slid["undo"] == 1 and slid["value"] != bar[3] and int(slid["value"]) >= 5, str((bar[3], slid)))
    p.evaluate("() => setBenchTab('play')")
    # Undo across two presets puts back the first one's name: the name is
    # part of what is put back, not left for the Custom check to find.
    p.evaluate("() => applyPreset('b:Slow pad')"); settle()
    p.click("#presetNext"); p.wait_for_timeout(1500)
    p.click("#undoButton"); settle(); across = state()
    check("undo from a preset loaded with the arrow back to the one before it gives that one's name back",
          across["value"] == "b:Slow pad" and across["name"] == "Slow pad", str(across))
    # Ctrl+Z in a text field is the field's.
    before_typing = state()["undo"]
    p.evaluate("() => { openPresets(); showSaving(true); }")
    p.keyboard.type("abc"); p.keyboard.press("Control+z"); p.wait_for_timeout(200)
    field = p.evaluate("() => ({ undo: undoHistory.undo.length, value: el.preset.value })")
    p.keyboard.press("Escape"); p.wait_for_timeout(150)
    check("Ctrl+Z while typing a name is the field's, not the sound's",
          field["undo"] == before_typing and before_typing > 0, str((before_typing, field)))

    print("\n--- playing is not editing, an edit is the preset edited, and the arrows step from it (15 Nov) ---")
    # The owner's list, items 2 to 4. With Harmonic tone loaded, a dyad, a
    # note wrote the Frequency and the Interval, as Dyad's notes do, and the
    # header compared those with the preset's and said Custom. So: every bank
    # preset (by the bank, not by name - the bank changes by ear), a chord
    # played on the letters with the real keyboard, and the header must still
    # name it, unedited, with no step in undo. The null: the same chord with
    # the comparison as it was (the hands' writes counted, asPlayed bypassed)
    # marks Harmonic tone - and a real edit, a knob turned by the keys, marks
    # any of them.
    p.evaluate("() => setScreenKeys(true)")
    def chord_on(value, nobble=False):
        p.evaluate("(v) => { applyPreset(v); }", value); p.wait_for_timeout(600)
        p.evaluate("() => { document.activeElement && document.activeElement.blur && document.activeElement.blur(); %s %s }"
                   % (CLEAR, "asPlayed = (now) => now;" if nobble else ""))
        for k in ("a", "d", "g"): p.keyboard.down(k); p.wait_for_timeout(40)
        p.wait_for_timeout(900)
        during = state()
        for k in ("a", "d", "g"): p.keyboard.up(k)
        # Then B3 alone, 247 Hz, so a dyad's Frequency is left off its preset's 220.
        p.keyboard.down("j"); p.wait_for_timeout(300); p.keyboard.up("j")
        p.wait_for_timeout(900)
        return during, state()
    played = {}
    for value in browser:
        during, after = chord_on(value)
        played[value] = (during, after)
    still = [v for v, (d, a) in played.items() if not (d["value"] == v and not d["edited"] and a["value"] == v
                                                          and not a["edited"] and a["undo"] == 0)]
    print("    %d bank presets played; %s" % (len(played), "every one still named" if not still else "moved: %s" % still))
    check("a chord played on any bank preset leaves the header naming it, unedited, and no step in undo",
          len(played) >= 9 and not still, str([(v, played[v]) for v in still][:2]))
    harmonic = next(v for v in browser if p.evaluate("(v) => (findPreset(v).midiMode || 'dyad') !== 'poly'", v))
    old = chord_on(harmonic, nobble=True)
    p.reload(); p.wait_for_timeout(1200)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate("() => { setView('bench'); setScreenKeys(true); }")
    check("null: on %s, a dyad, with the hands' writes counted as the page counted them, the chord marks it edited" % harmonic,
          old[0]["edited"] and old[1]["edited"] and old[1]["freq"] != 220, str(old))
    # A real edit marks it; undo back to its own values clears the mark.
    p.evaluate("(v) => { applyPreset(v); }", harmonic); p.wait_for_timeout(600)
    p.evaluate("() => { %s showControl('amp'); el.amp.focus(); }" % CLEAR)
    for _ in range(4): p.keyboard.press("ArrowUp")
    settle(); edited = state()
    shown = p.evaluate("() => [document.getElementById('presetLabel').textContent, el.presetEdited.textContent, getComputedStyle(el.presetEdited).color]")
    check("null: a knob turned by the keys marks it, the name kept and edited after its heading in the softer ink",
          edited["value"] == harmonic and edited["edited"] and edited["name"] == harmonic[2:]
          and shown[1].strip() == "· edited" and shown[2] == "rgb(107, 97, 90)", str((edited, shown)))
    p.click("#undoButton"); settle(); back = state()
    check("and undo back to its own values clears edited", back["value"] == harmonic and not back["edited"], str(back))
    # The arrows from an edited preset: the cards beside it, not the bank's
    # ends, which is where they went from Custom until 15 Nov.
    mid = browser[len(browser) // 2]
    def edited_then(arrow):
        p.evaluate("(v) => { applyPreset(v); }", mid); p.wait_for_timeout(500)
        p.evaluate("() => { showControl('amp'); el.amp.focus(); }")
        p.keyboard.press("ArrowUp"); p.keyboard.press("ArrowUp"); settle()
        was = state()
        p.click(arrow); p.wait_for_timeout(500)
        return was, state()
    (was_n, nxt_e), (was_p, prv_e) = edited_then("#presetNext"), edited_then("#presetPrev")
    at = browser.index(mid)
    check("from %s edited, the arrows load the cards beside it in the browser's order" % mid,
          was_n["edited"] and was_p["edited"] and nxt_e["value"] == browser[at + 1] and prv_e["value"] == browser[at - 1]
          and not nxt_e["edited"], str((nxt_e["value"], prv_e["value"], browser[at - 1:at + 2])))
    check("null: those are not the bank's ends, where the arrows went from Custom",
          nxt_e["value"] != browser[0] and prv_e["value"] != browser[-1])
    p.evaluate("() => setScreenKeys(false)")

    print("\n--- A and B are gone (G4) ---")
    # The versions went with G4: the header has neither button, and the page
    # no second history. The hands' selector is a different thing - the hand
    # being edited, which G6 moved here from the Keyboard's Edit A / B - and
    # names its hands A and B while layered; it must not be caught up here.
    GONE = """() => ({ buttons: ['abA', 'abB', 'viewScope', 'viewBench'].filter((id) => document.getElementById(id)),
      versions: typeof versions !== 'undefined', inHeader: Array.from(document.querySelectorAll('header button'))
        // The header's own row, not the panels it opens: Perform's morph and Settings' fade have A and B ends.
        .filter((b) => !b.closest('.menu-panel') && !b.closest('#handsPick') && /^[AB]$/.test(b.textContent.trim())).map((b) => b.id),
      editAB: !!document.getElementById('midiEditA') || !!document.getElementById('midiEditB'),
      hands: !!document.querySelector('header #handsPick #editHandA') && !!document.querySelector('header #handsPick #editHandB') })"""
    gone = p.evaluate(GONE)
    check("no A or B button in the header, no Scope or Bench switch, and one history behind undo",
          gone["buttons"] == [] and not gone["versions"] and gone["inHeader"] == [], str(gone))
    check("and the Keyboard's Edit A / B went in G6, the header's Editing in its place", not gone["editAB"] and gone["hands"], str(gone))
    # The null: an A put back in the header, as the page had it before G4, is found.
    was = p.evaluate("""(read) => { const b = document.createElement('button'); b.id = 'abA'; b.textContent = 'A';
      document.getElementById('undoButton').before(b); const r = (0, eval)('(' + read + ')')(); b.remove(); return r; }""", GONE)
    check("null: an A button put back in the header fails it",
          not (was["buttons"] == [] and not was["versions"] and was["inHeader"] == []), str(was))

    print("\n--- Settings (F7b) ---")
    SET = """() => { setMenuOpen(true);
      const r = el.menuPanel.getBoundingClientRect();
      const col = (id) => Array.from(document.getElementById(id).children).map((g) => groupTitle(g));
      return { inside: r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight,
               scrolls: el.menuPanel.scrollHeight > el.menuPanel.clientHeight + 1,
               left: col('settingsLeft'), right: col('settingsRight') }; }"""
    fits = {}
    for w, h in ((1400, 900), (960, 600), (960, 420)):
        p.set_viewport_size({"width": w, "height": h}); p.wait_for_timeout(250)
        fits[(w, h)] = p.evaluate(SET)
        p.evaluate("() => setMenuOpen(false)")
    p.set_viewport_size({"width": 1400, "height": 900}); p.wait_for_timeout(250)
    print("    %s" % fits)
    for size in ((1400, 900), (960, 600)):
        check("at %dx%d Settings is inside the window and nothing in it scrolls" % size,
              fits[size]["inside"] and not fits[size]["scrolls"], str(fits[size]))
    # The null: a window too short for it must be seen not to fit. At 960
    # wide the header's two rows were what put the old panel off the window.
    # 960x480 until G5a took the fade to Routings, which left the panel short
    # enough to fit there; at 420 it scrolls (measured at 440 too).
    check("null: at 960x420 the same check says it does not fit", not (fits[(960, 420)]["inside"] and not fits[(960, 420)]["scrolls"]),
          str(fits[(960, 420)]))
    # The fade was the left column's middle from F7b to G5a, which moved it to Routings.
    check("two columns as drawn: MIDI and this window; the inputs and the audio",
          fits[(1400, 900)]["left"] == ["MIDI", "This window"]
          and fits[(1400, 900)]["right"] == ["Input", "Audio", "Input into the generator"], str(fits[(1400, 900)]))

    notes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setMenuOpen(true);
      const g = document.getElementById('midiSetGroup');
      const note = Array.from(g.querySelectorAll('.menu-note')).find((n) => n.textContent.includes('Nord'));
      const hidden = note && getComputedStyle(note).display === 'none';
      const dots = g.querySelector(':scope > .menu-title .more-dots');
      if (dots) dots.click();
      await wait(100);
      const shown = !!note && !!note.closest('.over') && getComputedStyle(note).display !== 'none';
      closeOverlay(); setMenuOpen(false);
      const beam = el.beamLevel.closest('.menu-group');
      return { hidden, dots: !!dots, shown, beam: [homeOf(beam), beam.parentElement.id] };
    }""")
    check("a section's notes are behind its dots: hidden in the panel, and shown when the dots are pressed",
          notes["hidden"] and notes["dots"] and notes["shown"], str(notes))
    check("Beam is in Picture > Advanced as only the look, not in Settings", notes["beam"] == ["picture", "pictureLook"], str(notes["beam"]))
    # The help sheet the first time: on a fresh page, with the sheet unseen,
    # ticked opens it and unticked does not. The null is ticked.
    def first_visit(pref):
        q = b.new_page(viewport={"width": 1400, "height": 900})
        q.goto(f"file://{ART}/scope.html"); q.wait_for_timeout(300)
        q.evaluate("(pref) => { localStorage.removeItem('scope.sheetSeen'); if (pref) localStorage.setItem('scope.sheetFirst', pref); else localStorage.removeItem('scope.sheetFirst'); }", pref)
        q.reload(); q.wait_for_timeout(800)
        got = q.evaluate("() => ({ open: el.helpDialog.open, ticked: el.helpFirst.checked })")
        q.close()
        return got
    fresh, off = first_visit(None), first_visit("no")
    # Unticking writes the preference the next load reads.
    p.evaluate("() => { setMenuOpen(true); }")
    p.locator("#helpFirst").uncheck(); written = p.evaluate("() => localStorage.getItem('scope.sheetFirst')")
    p.locator("#helpFirst").check()
    p.evaluate("() => setMenuOpen(false)")
    check("on a first visit the help sheet opens, ticked; unticked, it does not, and unticking is remembered",
          fresh == {"open": True, "ticked": True} and off == {"open": False, "ticked": False} and written == "no",
          str((fresh, off, written)))

    print("\n--- the host's parameters (F7c) ---")
    # The plugin's own table, read as parity reads it, so a parameter added
    # there and not marked here fails.
    src = open(os.path.join(os.path.dirname(ART), "plugin", "src", "PluginProcessor.h")).read()
    src = src[src.index("kKnobs {"):]
    plugin = re.findall(r'\{ "[a-z0-9]+", "[A-Za-z0-9 ]+", "([A-Za-z0-9]+)", \d, (?:true|false) \}', src[:src.index("} };")])
    marks = p.evaluate("""() => ({
      list: HOST_PARAMS,
      marked: Array.from(document.querySelectorAll('.host-param')).map((r) => r.querySelector('input[type=range]').id),
      dot: getComputedStyle(el.vcfCut.closest('.menu-row').querySelector('.menu-label'), '::before').backgroundColor,
      none: getComputedStyle(el.freq.closest('.menu-row').querySelector('.menu-label'), '::before').content,
    })""")
    print("    %s" % marks)
    # Fourteen since G7 added the master Output, in Level's old corner; fifteen
    # since the Width after it (12 Nov).
    # Seventeen since 18 Nov: the amp envelope's Attack and Release, appended after the morph.
    # Eighteen since 19 Nov: LFO 1's Rate, appended after them (lfo-drawn.md), made with LFO 1's editor.
    check("the page's host parameters are the plugin's kKnobs, in its order", marks["list"] == plugin and len(plugin) == 18
          and plugin[-4:] == ["morphPos", "envAttack", "envRelease", "lfoRate0"]
          and plugin[5:7] == ["output", "stereoWidth"],
          str((marks["list"], plugin)))
    check("every one, and only those, is marked on the face", sorted(marks["marked"]) == sorted(plugin), str(marks["marked"]))
    check("with a gold dot, and a control that is not one has none",
          marks["dot"] == "rgb(176, 141, 87)" and marks["none"] in ("none", "normal"), str((marks["dot"], marks["none"])))

    print("\n--- the testing site's mark ---")
    # Shown only under /testing/ (15 Nov), by the test the storage shim at
    # the top of the script uses; and it must move nothing in the header. So
    # the page is opened twice at each window fittest and windowtest measure,
    # from the root and from a directory named testing, and every box in the
    # header is required to be where it was to the hundredth of a pixel, the
    # mark inside the spacer it is drawn in. The nulls: the root, which shows
    # nothing, and the mark put into the flow, which moves the header.
    import shutil, tempfile
    site = tempfile.mkdtemp(prefix="headertest-")
    os.makedirs(os.path.join(site, "testing"))
    shutil.copy(os.path.join(ART, "scope.html"), os.path.join(site, "scope.html"))
    shutil.copy(os.path.join(ART, "scope.html"), os.path.join(site, "testing", "scope.html"))
    BOXES = """(inflow) => {
      const m = document.getElementById('testingMark');
      if (inflow) { m.style.position = 'static'; m.style.transform = 'none'; m.parentElement.style.flex = '0 0 auto'; }
      const box = (e) => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height].map((v) => Math.round(v * 100) / 100); };
      const boxes = {};
      document.querySelectorAll('.top-bar, .top-bar .head > *, .top-bar .preset-bar > *').forEach((e, i) => { boxes[i + ':' + (e.id || e.className)] = box(e); });
      const r = m.getBoundingClientRect(), g = m.parentElement.getBoundingClientRect();
      return { boxes, shown: !m.hidden && r.width > 0, text: m.textContent,
               inside: r.left >= g.left - 0.01 && r.right <= g.right + 0.01, ink: getComputedStyle(m).color };
    }"""
    def opened(where, w, h, inflow=False):
        q = b.new_page(viewport={"width": w, "height": h})
        q.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
        t0 = time.monotonic()
        q.goto("file://%s/%s" % (site, where)); q.wait_for_timeout(1200)
        got = q.evaluate(BOXES, inflow)
        got["since"] = time.monotonic() - t0
        q.close()
        return got
    marked = []
    for w, h in ((1400, 900), (1100, 860), (1200, 680), (1100, 680), (960, 600)):
        root, testing = opened("scope.html", w, h), opened("testing/scope.html", w, h)
        marked.append((w, h, root, testing))
        print("    %dx%d: root shows %s; testing shows %s, inside the spacer %s, header %s"
              % (w, h, root["shown"], testing["shown"], testing["inside"], "the same" if root["boxes"] == testing["boxes"] else "MOVED"))
        # Unreproduced as of 20 Nov (red at 1100x860 in two sessions' full
        # runs, never since): what the next red run needs to say why.
        if root["boxes"] != testing["boxes"]: moved(w, h, "root", root, "testing", testing)
    check("under /testing/ the header says Testing, in the brand's secondary ink, at every window",
          all(t["shown"] and t["text"] == "Testing" and t["ink"] == "rgb(107, 97, 90)" for *_, t in marked), str([t["ink"] for *_, t in marked]))
    check("null: at the root it says nothing", not any(r["shown"] for _, _, r, _ in marked))
    check("and the header is laid out the same to the hundredth of a pixel with it or without it, the mark inside its spacer",
          all(r["boxes"] == t["boxes"] and t["inside"] for _, _, r, t in marked))
    flowed = opened("testing/scope.html", 1400, 900, inflow=True)
    check("null: the mark put into the flow moves the header", flowed["boxes"] != marked[0][2]["boxes"])
    shutil.rmtree(site, ignore_errors=True)

    print("\n--- the edited mark moves nothing (15 Nov) ---")
    # At the five windows, every box in the header with a preset loaded and
    # with it edited, on a short name under a long heading (Slow pad, under
    # Breathing), where a mark that took width would widen the button. The
    # null: the heading given its own width back, which moves the header.
    EDITED_BOXES = """(inflow) => {
      applyPreset('b:Slow pad');
      const box = (e) => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height].map((v) => Math.round(v * 100) / 100); };
      const all = () => { const o = {}; document.querySelectorAll('.top-bar, .top-bar .head > *, .top-bar .preset-bar > *').forEach((e, i) => { o[i + ':' + (e.id || e.className)] = box(e); }); return o; };
      if (inflow) document.querySelector('.preset-heading').style.width = 'auto';
      const plain = all();
      setPresetValue('b:Slow pad', true);
      const m = el.presetEdited.getBoundingClientRect(), btn = el.preset.getBoundingClientRect();
      return { plain, edited: all(), shown: !el.presetEdited.hidden && m.width > 0, inside: m.right <= btn.right + 0.01 };
    }"""
    def edited_at(w, h, inflow=False):
        q = b.new_page(viewport={"width": w, "height": h})
        q.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
        t0 = time.monotonic()
        q.goto(f"file://{ART}/scope.html"); q.wait_for_timeout(1200)
        got = q.evaluate(EDITED_BOXES, inflow)
        got["since"] = time.monotonic() - t0
        q.close()
        return got
    eds = [(w, h, edited_at(w, h)) for w, h in ((1400, 900), (1100, 860), (1200, 680), (1100, 680), (960, 600))]
    for w, h, e in eds:
        print("    %dx%d: edited shown %s, inside the button %s, header %s" % (w, h, e["shown"], e["inside"], "the same" if e["plain"] == e["edited"] else "MOVED"))
        if e["plain"] != e["edited"]: moved(w, h, "plain", {"boxes": e["plain"], "since": e["since"]}, "edited", {"boxes": e["edited"], "since": e["since"]})
    check("with the edited mark the header is laid out the same to the hundredth of a pixel at every window, the mark inside the preset's button",
          all(e["shown"] and e["inside"] and e["plain"] == e["edited"] for *_, e in eds))
    flowed_e = edited_at(1400, 900, inflow=True)
    check("null: the heading given its own width, the mark moves the header", flowed_e["plain"] != flowed_e["edited"])

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
