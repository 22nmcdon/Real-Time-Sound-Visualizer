"""Who has the keyboard: the shortcuts, undo, the on-screen keys and the widgets
that take keys of their own (the outside review, 17 Nov).

What would go wrong, and what is checked for it, each driven with the real
mouse and keyboard, since what is under test is which handler a key reaches:

- a knob turned, and then nothing: dragging focuses the knob's range input,
  and four handlers each had their own "is the user typing" test, three of
  which took any INPUT for a text field, so Ctrl+Z, S, A, the digits and /
  did nothing until something else was clicked. They share one now
  (takesText), and a text field (the search) is the null: there S types and
  Ctrl+Z is the field's;
- a key acted on twice: a widget that had used an arrow or Space (the
  right-click menu's arrows, the rack handle's, the envelope handle) and the
  shortcuts after it, which moved the trigger level or stopped the scope; ?
  opening the info card and the help together. Each is a reading of what the
  shortcut would have moved, taken before and after the key;
- with the on-screen keys open, a focused menu swallowing the note letters,
  so S played nothing and changed Shape from Sine to Square. The note is read
  off the held notes, the menu off its value, and the menu's own arrow is the
  null for taking every key from it.

Each check was seen red against the page before the fix (a575b7d).
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + str(detail)) if detail else ""))
    if not ok: fails.append(name)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1000)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)
    ev = p.evaluate
    focused = []
    face = p.locator(".menu-row:has(#pictureAmount) .knob-face").first

    def turn_knob():
        """A real drag on the Picture amount's face, which leaves its range input focused."""
        bb = face.bounding_box()
        x, y = bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
        p.mouse.move(x, y); p.mouse.down(); p.mouse.move(x, y - 30, steps=6); p.mouse.up()
        p.wait_for_timeout(700)   # undo records a change once it has held still for 400 ms
        focused.append(ev("() => document.activeElement === el.pictureAmount"))

    def reset():
        p.keyboard.press("Escape"); p.keyboard.press("Escape")
        ev("() => { closeOverlay(); setScreenKeys(false); setMode('auto'); setRunning(true); document.activeElement && document.activeElement.blur(); }")
        p.wait_for_timeout(150)

    print("\n--- after a knob is turned, the shortcuts and undo ---")
    before = ev("() => Number(el.pictureAmount.value)")
    turn_knob()
    after = ev("() => Number(el.pictureAmount.value)")
    focus = ev("() => [document.activeElement.tagName, document.activeElement.type, document.activeElement.id]")
    check("the drag moved the knob and left its range input with the focus (the case under test)",
          after != before and focus == ["INPUT", "range", "pictureAmount"], "%s -> %s, focus %s" % (before, after, focus))
    p.keyboard.press("Control+z"); p.wait_for_timeout(300)
    check("Ctrl+Z puts the knob back", ev("() => Number(el.pictureAmount.value)") == before,
          "now %s, was %s" % (ev("() => el.pictureAmount.value"), before))
    p.keyboard.press("Control+Shift+z"); p.wait_for_timeout(300)
    check("and Ctrl+Shift+Z brings the turn back", ev("() => Number(el.pictureAmount.value)") == after)
    turn_knob(); p.keyboard.press("s"); p.wait_for_timeout(150)
    check("S is Single", ev("() => state.mode") == "single", ev("() => state.mode"))
    reset(); p.keyboard.press("1"); p.wait_for_timeout(200)
    check("null: 1 with nothing focused is the Y-T display, so the next reading starts there", ev("() => state.display") == "yt")
    turn_knob(); p.keyboard.press("2"); p.wait_for_timeout(200)
    check("2 is the X-Y display", ev("() => state.display") == "xy", ev("() => state.display"))
    p.keyboard.press("1"); p.wait_for_timeout(200)
    turn_knob(); p.keyboard.press("/"); p.wait_for_timeout(200)
    check("/ goes to the search", ev("() => document.activeElement === el.benchSearch"))
    p.locator("#benchSearch").click()
    # The null: in a field that takes text, the letters and Ctrl+Z are the field's.
    p.keyboard.type("sa"); p.wait_for_timeout(100)
    check("null: in the search S and A are typed, not Single or Autoset",
          ev("() => el.benchSearch.value") == "sa" and ev("() => state.mode") == "auto", ev("() => [el.benchSearch.value, state.mode]"))
    steps = ev("() => undoHistory.undo.length")
    p.keyboard.press("Control+z"); p.wait_for_timeout(200)
    check("null: and Ctrl+Z there is the field's, not a step of the history",
          ev("() => undoHistory.undo.length") == steps, "%s -> %s" % (steps, ev("() => undoHistory.undo.length")))
    ev("() => { el.benchSearch.value = ''; el.benchSearch.dispatchEvent(new Event('input')); }")
    reset()

    check("every drag left the knob's input focused, so each check above was of the case", all(focused), focused)
    print("\n--- a key a widget has used is not a shortcut as well ---")
    level = lambda: ev("() => Number(el.level.value)")
    timebase = lambda: ev("() => Number(el.timebase.value)")
    # The null for the readings: with nothing focused, the arrows are the trigger level and timebase.
    l0 = level(); p.keyboard.press("ArrowUp"); p.wait_for_timeout(100)
    check("null: with nothing focused ArrowUp moves the trigger level", level() != l0, "%s -> %s" % (l0, level()))
    ev("() => { el.level.value = '0'; el.level.dispatchEvent(new Event('input')); }")
    reset()
    # The right-click menu's arrows.
    face.click(button="right"); p.wait_for_timeout(250)
    opened = ev("() => !!(overlay && overlay.node.querySelector('.ctx-item'))")
    l0, t0 = level(), timebase()
    p.keyboard.press("ArrowDown"); p.keyboard.press("ArrowDown"); p.keyboard.press("ArrowUp"); p.wait_for_timeout(100)
    on_item = ev("() => document.activeElement.classList.contains('ctx-item')")
    check("arrowing through the right-click menu moves in the menu, and not the trigger level",
          opened and on_item and level() == l0, "menu %s, on an item %s, level %s -> %s" % (opened, on_item, l0, level()))
    p.keyboard.press("ArrowRight"); p.wait_for_timeout(100)
    check("nor the timebase", timebase() == t0, "%s -> %s" % (t0, timebase()))
    reset()
    # The rack handle's arrows.
    p.locator("#benchTab-space").click()
    p.wait_for_timeout(250)
    handle = p.locator('.fx-handle[data-fx-move="phaser"]')
    handle.focus()
    o0, l0 = ev("() => fxOrder"), level()
    p.keyboard.press("ArrowDown"); p.wait_for_timeout(150)
    check("the rack handle's ArrowDown moves the module, and not the trigger level",
          ev("() => fxOrder") != o0 and level() == l0, "order %s -> %s, level %s -> %s" % (o0, ev("() => fxOrder"), l0, level()))
    ev("(o) => setFxOrder(o)", o0)
    reset()
    # The envelope handle's Space, in Routings.
    p.locator("#routingsButton").click(); p.wait_for_timeout(300)
    ev("() => envParts.wait.focus()")
    t0 = timebase()
    got = ev("() => document.activeElement && document.activeElement.dataset && document.activeElement.dataset.handle")
    p.keyboard.press("Space"); p.wait_for_timeout(150)
    check("Space on the fade envelope's handle leaves the scope running",
          got == "wait" and ev("() => state.running"), "focus %s, running %s" % (got, ev("() => state.running")))
    p.keyboard.press("ArrowRight"); p.wait_for_timeout(100)
    check("and its ArrowRight is the handle's, not the timebase", timebase() == t0, "%s -> %s" % (t0, timebase()))
    p.keyboard.press("Escape"); reset()
    ev("() => { if (!el.routingsPanel.hidden) el.routingsClose.click(); }")
    # A focused range keeps its arrows: the null for handing a range to the shortcuts whole.
    ev("() => el.pictureAmount.focus()")
    a0, l0 = ev("() => Number(el.pictureAmount.value)"), level()
    p.keyboard.press("ArrowUp"); p.wait_for_timeout(100)
    check("null: a focused knob's ArrowUp moves the knob, not the level",
          ev("() => Number(el.pictureAmount.value)") != a0 and level() == l0)
    reset()
    # ? over a described control: the card, and not the help as well.
    p.locator(".menu-row:has(#pictureAmount) .knob-face").first.hover(); p.wait_for_timeout(900)
    described = ev("() => !!infoAt")
    p.keyboard.press("?"); p.wait_for_timeout(250)
    card = ev("() => !!(overlay && overlay.node.classList.contains('info-card'))") or ev("() => !!document.querySelector('.info-card')")
    check("? over a described control opens its card and not the help as well",
          described and card and not ev("() => el.helpDialog.open"),
          "described %s, card %s, help %s" % (described, card, ev("() => el.helpDialog.open")))
    reset()
    ev("() => { if (el.helpDialog.open) el.helpDialog.close(); infoAt = null; }")
    p.mouse.move(5, 5); p.wait_for_timeout(100)

    print("\n--- with the on-screen keys open, a focused menu ---")
    p.locator("#benchTab-play").click(); p.wait_for_timeout(200)
    ev("() => setScreenKeys(true)"); p.wait_for_timeout(200)
    ev("() => { el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change', { bubbles: true })); }")
    p.wait_for_timeout(150)
    ev("() => el.shape.focus()")
    check("the Shape menu has the focus (the case under test)", ev("() => document.activeElement === el.shape"))
    p.keyboard.down("s"); p.wait_for_timeout(150)
    held = ev("() => midi.notes.map((n) => n.note)")
    shape = ev("() => el.shape.value")
    p.keyboard.up("s"); p.wait_for_timeout(150)
    check("S plays its note with the Shape menu focused", len(held) == 1, "held %s" % held)
    check("and leaves the Shape on Sine", shape == "sine", shape)
    check("and lifting it ends the note", ev("() => midi.notes.length") == 0)
    o0 = ev("() => screenKeys.base")
    p.keyboard.press("x"); p.wait_for_timeout(100)
    check("X moves the keys' octave with the menu focused", ev("() => screenKeys.base") == o0 + 12, "%s -> %s" % (o0, ev("() => screenKeys.base")))
    p.keyboard.press("z"); p.wait_for_timeout(100)
    p.keyboard.down("Space"); p.wait_for_timeout(100)
    pedal = ev("() => !!screenKeys.spacePedal")
    p.keyboard.up("Space"); p.wait_for_timeout(100)
    check("Space is the pedal with the menu focused", pedal and ev("() => state.running"))
    p.keyboard.press("ArrowDown"); p.wait_for_timeout(150)
    check("null: the menu keeps its arrows", ev("() => el.shape.value") != "sine", ev("() => el.shape.value"))
    ev("() => { el.shape.value = 'harmonic'; el.shape.dispatchEvent(new Event('change', { bubbles: true })); }")
    # The null for taking every key: a field that takes text keeps its letters.
    ev("() => el.benchSearch.focus()")
    p.keyboard.type("s"); p.wait_for_timeout(100)
    check("null: in the search, S is typed and plays nothing",
          ev("() => el.benchSearch.value") == "s" and ev("() => midi.notes.length") == 0)
    ev("() => { el.benchSearch.value = ''; el.benchSearch.dispatchEvent(new Event('input')); setScreenKeys(false); }")

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\nall passed" if not fails else "\n%d FAILED:\n  %s" % (len(fails), "\n  ".join(fails)))
sys.exit(1 if fails else 0)
