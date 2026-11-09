"""The header (F7 of web/docs/redesigning-the-face.md): the preset's arrows, its
heading, Browse and Save, A/B and undo.

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
- A and B that are one version: a change on B heard on A, B not starting as
  A, or one history for both, so that undo after a switch walks back through
  the other version;
- Ctrl+Z in a text field taken from the field.

Every change here is made with the real mouse and keyboard, since undo counts
only what follows a trusted event: a knob turned by dispatchEvent is, rightly,
no step at all, and is the null for that rule.
"""
import os, re, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(800)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(300)
    state = lambda: p.evaluate("""() => ({ value: el.preset.value, heading: document.getElementById('presetLabel').textContent,
      name: el.presetCurrent.textContent, freq: Number(el.freq.value), undo: versions[versions.on].undo.length,
      redo: versions[versions.on].redo.length, undoOff: el.undoButton.disabled, redoOff: el.redoButton.disabled,
      on: versions.on })""")
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
    p.evaluate("() => { versions.a.undo = []; versions.a.redo = []; undoRebase(); paintUndo(); }")
    start = state()
    # Five presses of the arrow key on the frequency, quickly: one step.
    p.evaluate("() => { showControl('freq'); el.freq.focus(); }")
    for _ in range(5): p.keyboard.press("ArrowUp")
    settle(); turned = state()
    check("null: with nothing done there is nothing to undo", start["undo"] == 0 and start["undoOff"], str(start))
    check("a knob turned by five key presses is one step, and says Custom",
          turned["freq"] != start["freq"] and turned["undo"] == 1 and not turned["undoOff"] and turned["value"] == "",
          str((start["freq"], turned)))
    p.click("#undoButton"); settle(); undone = state()
    check("undo puts back the sound and its name, and redo is offered",
          undone["freq"] == start["freq"] and undone["value"] == "b:Slow pad" and undone["name"] == "Slow pad"
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
          stepped["undo"] == fresh["undo"] + 1 and unstepped["value"] == "" and unstepped["freq"] == fresh["freq"],
          str((stepped, unstepped)))
    # Spread out: five presses 250 ms apart, so the history is looked at
    # twice between each - still one step, since it waits 400 ms for them to
    # stop. (At 90 ms apart a history that recorded any change seen twice
    # would also have made one step, and the mutation pass showed it.)
    p.evaluate("() => { versions.a.undo = []; versions.a.redo = []; undoRebase(); paintUndo(); el.freq.focus(); }")
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
    p.evaluate("() => { applyPreset('b:Drawbar organ'); setBenchTab('ink'); }"); p.wait_for_timeout(600)
    p.evaluate("() => { versions.a.undo = []; versions.a.redo = []; undoRebase(); paintUndo(); }")
    bar = p.evaluate("() => { const r = el.bar3.getBoundingClientRect(); return [r.x, r.y + r.height / 2, r.width, el.bar3.value]; }")
    p.mouse.move(bar[0] + 6, bar[1]); p.mouse.down(); p.mouse.move(bar[0] + bar[2] * 0.35, bar[1], steps=6)
    p.wait_for_timeout(700)
    p.mouse.move(bar[0] + bar[2] * 0.75, bar[1], steps=6); p.mouse.up(); settle()
    slid = p.evaluate("() => ({ value: el.bar3.value, undo: versions.a.undo.length })")
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
    field = p.evaluate("() => ({ undo: versions[versions.on].undo.length, value: el.preset.value })")
    p.keyboard.press("Escape"); p.wait_for_timeout(150)
    check("Ctrl+Z while typing a name is the field's, not the sound's",
          field["undo"] == before_typing and before_typing > 0, str((before_typing, field)))

    print("\n--- A and B ---")
    p.evaluate("() => applyPreset('b:Slow pad')"); settle()
    a_freq = state()["freq"]
    p.click("#abB"); settle(); onb = state()
    check("B starts as a copy of A, with a history of its own",
          onb["on"] == "b" and onb["freq"] == a_freq and onb["value"] == "b:Slow pad" and onb["undo"] == 0, str(onb))
    # Its own tab first: since G3 Frequency is on Ink, and the tab here is Play.
    p.evaluate("() => { showControl('freq'); el.freq.focus(); }")
    for _ in range(3): p.keyboard.press("ArrowUp")
    settle(); b_freq = state()["freq"]
    p.click("#abA"); settle(); ona = state()
    p.click("#abB"); settle(); onb2 = state()
    check("a change on B is B's: A is as it was, and B comes back changed",
          ona["on"] == "a" and ona["freq"] == a_freq and ona["value"] == "b:Slow pad"
          and onb2["freq"] == b_freq and b_freq != a_freq, str((a_freq, b_freq, ona["freq"], onb2["freq"])))
    check("null: B changed is not A", b_freq != a_freq)
    undo_b = onb2["undo"]
    p.click("#abA"); settle(); undo_a = state()["undo"]
    p.click("#undoButton"); settle(); after = state()
    check("each has its own history: B's change is one step on B and none on A, and undo on A leaves B's change alone",
          undo_b == 1 and after["on"] == "a" and (undo_a == 0 or after["freq"] != b_freq), str((undo_b, undo_a, after)))
    p.click("#abB"); settle()
    check("and B still holds its own change", state()["freq"] == b_freq, str(state()))

    print("\n--- Settings (F7b) ---")
    SET = """() => { setMenuOpen(true);
      const r = el.menuPanel.getBoundingClientRect();
      const col = (id) => Array.from(document.getElementById(id).children).map((g) => groupTitle(g));
      return { inside: r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight,
               scrolls: el.menuPanel.scrollHeight > el.menuPanel.clientHeight + 1,
               left: col('settingsLeft'), right: col('settingsRight') }; }"""
    fits = {}
    for w, h in ((1400, 900), (960, 600), (960, 480)):
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
    check("null: at 960x480 the same check says it does not fit", not (fits[(960, 480)]["inside"] and not fits[(960, 480)]["scrolls"]),
          str(fits[(960, 480)]))
    check("two columns as drawn: MIDI, the fade and this window; the inputs and the audio",
          fits[(1400, 900)]["left"] == ["MIDI", "Modulation fade", "This window"]
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
    plugin = re.findall(r'\{ "[a-z]+", "[A-Za-z ]+", "([A-Za-z0-9]+)", \d, (?:true|false) \}', src[:src.index("} };")])
    marks = p.evaluate("""() => ({
      list: HOST_PARAMS,
      marked: Array.from(document.querySelectorAll('.host-param')).map((r) => r.querySelector('input[type=range]').id),
      dot: getComputedStyle(el.vcfCut.closest('.menu-row').querySelector('.menu-label'), '::before').backgroundColor,
      none: getComputedStyle(el.freq.closest('.menu-row').querySelector('.menu-label'), '::before').content,
    })""")
    print("    %s" % marks)
    check("the page's host parameters are the plugin's kKnobs, in its order", marks["list"] == plugin and len(plugin) == 13,
          str((marks["list"], plugin)))
    check("every one, and only those, is marked on the face", sorted(marks["marked"]) == sorted(plugin), str(marks["marked"]))
    check("with a gold dot, and a control that is not one has none",
          marks["dot"] == "rgb(176, 141, 87)" and marks["none"] in ("none", "normal"), str((marks["dot"], marks["none"])))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
