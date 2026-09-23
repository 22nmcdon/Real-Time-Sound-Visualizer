"""The keyboard on the screen: playing the generator with nothing plugged in.

Driven the way a person drives it - Playwright's mouse on the keys and its
keyboard on the letters - so what is tested is the pointer and key handling,
not a function called from underneath it. The notes are checked against the
stack every other path writes to, and the pitches are worked out here from the
note numbers rather than read back from the page.

The failures this is written against: a key that stays lit after a panic, a
latch that forgets it was holding something, a finger lifted after an octave
shift releasing the wrong note, two ways of holding one key where lifting one
ends it, letters that fire the shortcut as well as the note, and a note played
into a rack that reaches nothing because the code asked what the source was
rather than where the generator is.
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

HZ = lambda note: 440 * 2 ** ((note - 69) / 12)


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

    def held():
        return p.evaluate("() => midi.notes.map((n) => n.note)")

    def lit():
        return p.evaluate("""() => [...document.querySelectorAll('#keysBed .held')]
                                     .map((k) => Number(k.dataset.note))""")

    def key(note):
        return p.locator('#keysBed [data-note="%d"]' % note)

    def press(note):
        key(note).hover(); p.mouse.down(); p.wait_for_timeout(60)

    def lift():
        p.mouse.up(); p.wait_for_timeout(60)

    def tap(note):
        press(note); lift()

    def latch(on):
        p.evaluate("(on) => { el.keysLatch.checked = on; "
                   "el.keysLatch.dispatchEvent(new Event('change')); }", on)

    print("\n--- a keyboard is there to wait for ---")
    # The waveform generator is the default source, so the gate is the thing
    # to watch: it shuts between notes only while something could play one.
    before = p.evaluate("() => ({ present: keyboardPresent(), gated: state.source.gated })")
    # Things that are on the screen. The first draft measured the lag's mix
    # slider, which lives in the closed Settings panel: its box is all noughts
    # open or shut, so the check could not fail.
    BOXES = """() => [el.trace, el.timebase].map((e) => {
      const r = e.getBoundingClientRect();
      return [r.x, r.y, r.width, r.height].map((v) => Math.round(v * 10) / 10); })"""
    where = p.evaluate(BOXES)
    p.evaluate("() => el.keysOpen.click()"); p.wait_for_timeout(150)
    opened = p.evaluate("""() => ({ present: keyboardPresent(), gated: state.source.gated,
      shown: !el.screenKeys.hidden, keys: el.keysBed.children.length,
      playing: !el.midiPlayingRow.hidden, label: el.keysOpen.textContent,
    })""")
    opened["moved"] = p.evaluate(BOXES)
    print("    closed %s; open %s" % (before, opened))
    check("with no port and no keys, nothing is waiting and the generator is not gated",
          before["present"] is False and before["gated"] is False, str(before))
    check("opening the keys makes a keyboard present, and the waveform waits for a note",
          opened["present"] is True and opened["gated"] is True, str(opened))
    check("two octaves and the C that closes them, twenty-five keys",
          opened["shown"] and opened["keys"] == 25, str(opened["keys"]))
    check("and the Playing line shows, as it does for a port",
          opened["playing"] and opened["label"] == "Hide keys", str(opened))
    check("opening it moves no control on the page, and does not resize the trace",
          opened["moved"] == where and all(w > 0 and h > 0 for _, _, w, h in where),
          "%s -> %s" % (where, opened["moved"]))

    print("\n--- a key is a note ---")
    # E3, not A3: the generator starts at 220 Hz, which is A3, so a key that
    # did nothing would pass a check on A3.
    press(52)
    down = p.evaluate("""() => ({ notes: midi.notes.map((n) => [n.note, n.velocity]),
                                  freq: state.source.settings.freq })""")
    lit_down = lit()
    lift()
    print("    E3 down: %s, lit %s; released: %s" % (down, lit_down, held()))
    check("pressing E3 puts E3 on the stack at the slider's velocity",
          down["notes"] == [[52, 100 / 127]], str(down["notes"]))
    check("and the generator plays it",
          abs(down["freq"] - HZ(52)) < 1e-6 and abs(down["freq"] - 220) > 1,
          "%.3f Hz against %.3f" % (down["freq"], HZ(52)))
    check("the key is lit, and only that key", lit_down == [52], str(lit_down))
    check("and lifting the finger releases it", held() == [] and lit() == [], str(held()))

    p.evaluate("() => { el.keysVelocity.value = '40'; "
               "el.keysVelocity.dispatchEvent(new Event('input')); }")
    press(52)
    soft = p.evaluate("() => midi.notes.map((n) => n.velocity)")
    lift()
    p.evaluate("() => { el.keysVelocity.value = '100'; "
               "el.keysVelocity.dispatchEvent(new Event('input')); }")
    check("the velocity slider is the velocity",
          soft == [40 / 127], str(soft))

    print("\n--- dragging is a glissando ---")
    press(48)
    box = key(50).bounding_box()
    p.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] - 12, steps=6)
    p.wait_for_timeout(60)
    slid = held(); slid_lit = lit()
    lift()
    print("    down on C3, dragged to D3: %s, lit %s; released: %s" % (slid, slid_lit, held()))
    check("dragging from C3 to D3 leaves D3 held and C3 released",
          slid == [50] and slid_lit == [50], "%s, lit %s" % (slid, slid_lit))
    check("and letting go ends it", held() == [], str(held()))

    print("\n--- latch, which is how one mouse holds a dyad ---")
    latch(True)
    tap(48); tap(55)
    fifth = p.evaluate("""() => ({ notes: midi.notes.map((n) => n.note).sort((a, b) => a - b),
      interval: state.source.settings.interval, octaves: state.source.settings.octaves })""")
    tap(48)
    after_toggle = held()
    latch(False)
    after_off = held()
    print("    C3 and G3 tapped: %s; C3 tapped again: %s; latch off: %s"
          % (fifth, after_toggle, after_off))
    check("two taps under latch hold both notes after the mouse is up",
          fifth["notes"] == [48, 55], str(fifth["notes"]))
    check("and the dyad is the interval between them - seven semitones, a fifth",
          fifth["interval"] == 55 - 48 and fifth["octaves"] == 0, str(fifth))
    check("tapping a latched key again lets it go", after_toggle == [55], str(after_toggle))
    check("and turning latch off lets go of the rest", after_off == [], str(after_off))

    # Turned on with a finger already down: the note must not vanish when the
    # finger lifts, and must be released when the latch goes off.
    press(52)
    latch(True)
    lift()
    kept = held()
    latch(False)
    check("a note held when latch goes on is kept when the finger lifts, then released",
          kept == [52] and held() == [], "%s then %s" % (kept, held()))

    print("\n--- the letters ---")
    p.keyboard.down("s"); p.wait_for_timeout(40)
    typed = p.evaluate("() => ({ notes: midi.notes.map((n) => n.note), mode: state.mode })")
    p.keyboard.up("s"); p.wait_for_timeout(40)
    typed_up = held()
    print("    S down: %s; up: %s" % (typed, typed_up))
    check("S is D3 while the keys are open", typed["notes"] == [50], str(typed["notes"]))
    check("and it does not also switch the scope to Single",
          typed["mode"] == "auto", typed["mode"])
    check("releasing the letter releases the note", typed_up == [], str(typed_up))

    # Octave shift with a key held: the note that goes up must be the note
    # that went down, not whatever that letter means now.
    p.keyboard.down("a"); p.wait_for_timeout(40)
    p.keyboard.press("x"); p.wait_for_timeout(40)
    shifted = p.evaluate("() => ({ base: screenKeys.base, range: el.keysRange.textContent, "
                         "notes: midi.notes.map((n) => n.note) })")
    p.keyboard.up("a"); p.wait_for_timeout(40)
    after_shift = held()
    p.keyboard.down("a"); p.wait_for_timeout(40)
    new_a = held()
    p.keyboard.up("a"); p.keyboard.press("z"); p.wait_for_timeout(40)
    print("    A held, X pressed: %s; A released: %s; A again: %s"
          % (shifted, after_shift, new_a))
    check("X moves the keys up an octave", shifted["base"] == 60
          and shifted["range"] == "C4–C6", str(shifted))
    check("and a letter held across the shift releases the note it started",
          shifted["notes"] == [48] and after_shift == [], "%s then %s"
          % (shifted["notes"], after_shift))
    check("while the same letter now plays the octave above", new_a == [60], str(new_a))

    # One note held two ways.
    press(48)
    p.keyboard.down("a"); p.wait_for_timeout(40)
    lift()
    both = held()
    p.keyboard.up("a"); p.wait_for_timeout(40)
    check("a note held by a finger and a letter survives the finger lifting",
          both == [48] and held() == [], "%s then %s" % (both, held()))

    # A text field is typed into; a checkbox is not a text field.
    p.evaluate("""() => { const t = document.createElement('input'); t.type = 'text';
                          t.id = '__text'; document.body.appendChild(t); t.focus(); }""")
    p.keyboard.press("a"); p.wait_for_timeout(40)
    into_text = p.evaluate("() => ({ notes: midi.notes.length, value: __text.value })")
    p.evaluate("() => { __text.remove(); el.keysLatch.focus(); }")
    p.keyboard.down("d"); p.wait_for_timeout(40)
    from_checkbox = held()
    p.keyboard.up("d")
    p.evaluate("() => document.activeElement.blur()")
    check("typing into a text field types, and plays nothing",
          into_text == {"notes": 0, "value": "a"}, str(into_text))
    check("but a focused checkbox does not stop the letters playing",
          from_checkbox == [52], str(from_checkbox))

    print("\n--- one stack, whoever is playing it ---")
    p.evaluate("() => midiBytes(Uint8Array.from([0x90, 57, 100]))")
    from_wire = lit()
    p.evaluate("() => midiBytes(Uint8Array.from([0x80, 57, 0]))")
    check("a note from a port lights the screen's key", from_wire == [57], str(from_wire))

    latch(True)
    tap(48)
    p.evaluate("() => window.dispatchEvent(new Event('blur'))")
    panicked = {"notes": held(), "lit": lit(),
                "latched": p.evaluate("() => screenKeys.latched.size")}
    tap(48)
    replayed = held()
    tap(48)
    latch(False)
    print("    latched C3, then the window lost focus: %s; C3 tapped: %s"
          % (panicked, replayed))
    check("losing the window darkens the keys and forgets the latch",
          panicked == {"notes": [], "lit": [], "latched": 0}, str(panicked))
    check("so the next tap on that key plays it rather than releasing nothing",
          replayed == [48], str(replayed))

    # A port releasing a key the screen latched. The note-off does not know
    # which hand held it, and whatever the latch still believes afterwards it
    # must neither swallow the next tap nor cut the port's own next C3.
    port = lambda status, note: p.evaluate(
        "(b) => midiBytes(Uint8Array.from(b))", [status, note, 100 if status == 0x90 else 0])
    latch(True)
    tap(48); port(0x80, 48)
    tap(48)
    tapped_after_port = held()
    # From a clean slate rather than from whatever the check above left, so
    # that this one reaches the stale claim on its own and is not carried by
    # the state its neighbour happened to leave.
    latch(False); p.evaluate("() => midiPanic()"); latch(True)
    tap(48); port(0x80, 48); port(0x90, 48)
    latch(False)
    kept_port = held()
    port(0x80, 48)
    print("    latched C3 released by a port, then tapped: %s; "
          "port's own C3 when latch goes off: %s" % (tapped_after_port, kept_port))
    check("a latched note a port released is played again by the next tap",
          tapped_after_port == [48], str(tapped_after_port))
    check("and turning latch off does not cut a C3 the port started since",
          kept_port == [48], str(kept_port))

    # And a finger, rather than a latch: the panic has to end its claim even
    # when the stack was already empty, or lifting it later releases whatever
    # holds that note by then.
    press(48); port(0x80, 48)
    p.evaluate("() => window.dispatchEvent(new Event('blur'))")
    port(0x90, 48)
    lift()
    after_finger = held()
    port(0x80, 48)
    print("    finger on C3, port releases it, window blurs, port plays C3, "
          "finger lifts: %s" % after_finger)
    check("a finger left down across a panic lets go of nothing when it lifts",
          after_finger == [48], str(after_finger))

    p.evaluate("() => midiBytes(Uint8Array.from([0x90, 60, 100]))")
    latch(True); tap(48)
    p.locator("#keysClose").click(); p.wait_for_timeout(100)
    closed = p.evaluate("""() => ({ notes: midi.notes.map((n) => n.note),
      present: keyboardPresent(), gated: state.source.gated, latched: screenKeys.latched.size })""")
    p.evaluate("() => midiBytes(Uint8Array.from([0x80, 60, 0]))")
    latch(False)
    print("    port holding C4, screen holding C3, keys closed: %s" % closed)
    check("closing the keys releases what they held and not what a port holds",
          closed["notes"] == [60] and closed["latched"] == 0, str(closed))
    check("and the generator stops waiting for a keyboard that has gone",
          closed["present"] is False and closed["gated"] is False, str(closed))

    p.keyboard.press("s"); p.wait_for_timeout(60)
    shortcut = p.evaluate("() => state.mode")
    p.evaluate("() => setMode('auto')")
    check("with the keys closed, S is Single again", shortcut == "single", shortcut)

    print("\n--- a generator lane follows the keys ---")
    # A rack of the generator alone: the case where `state.source` is a rack
    # and the generator is one of its lanes, which is what the note path
    # stopped being able to reach.
    p.evaluate("() => { el.rackSynth.checked = true; return setRackSynth(true); }")
    p.wait_for_timeout(800)
    p.evaluate("() => el.keysOpen.click()"); p.wait_for_timeout(150)
    lane_before = p.evaluate("() => genLane() ? genLane().core.tone.freq : null")
    press(52)
    lane_down = p.evaluate("() => genLane().core.tone.freq")
    lift()
    lane_up = p.evaluate("() => ({ freq: genLane().core.tone.freq, "
                         "kind: state.source.kind, notes: midi.notes.length })")
    print("    lane at %s Hz, E3 down %.3f Hz, released %s" % (lane_before, lane_down, lane_up))
    check("the source is a rack, so this is the lane and not the tone source",
          lane_up["kind"] == "rack" and lane_before is not None, str(lane_up))
    check("a note reaches the generator lane",
          abs(lane_down - HZ(52)) < 1e-6 and abs(lane_before - HZ(52)) > 1,
          "%.3f Hz against %.3f" % (lane_down, HZ(52)))
    check("and the lane is a drone: releasing the key leaves the pitch where it was",
          lane_up["notes"] == 0 and abs(lane_up["freq"] - HZ(52)) < 1e-6, str(lane_up))

    display_before = p.evaluate("() => state.display")
    p.evaluate("() => { el.genMode.value = 'harmonograph'; "
               "el.genMode.dispatchEvent(new Event('change')); }")
    p.wait_for_timeout(100)
    kind = p.evaluate("() => ({ mode: genLane().core.tone.mode, display: state.display })")
    p.evaluate("() => { el.midiDrive.checked = false; "
               "el.midiDrive.dispatchEvent(new Event('change')); }")
    drive = p.evaluate("() => ({ harmonograph: midi.drive.harmonograph, wave: midi.drive.wave })")
    p.evaluate("() => { el.midiDrive.checked = true; "
               "el.midiDrive.dispatchEvent(new Event('change')); }")
    print("    Kind set to harmonograph: %s; Drive unticked: %s" % (kind, drive))
    check("the Kind menu reaches the lane", kind["mode"] == "harmonograph", str(kind))
    check("without switching the whole screen to X-Y, which is for the source",
          kind["display"] == display_before, "%s -> %s" % (display_before, kind["display"]))
    check("and the Drive box records its answer for the lane's kind",
          drive == {"harmonograph": False, "wave": True}, str(drive))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the keys play the same stack a keyboard does, and let go of what they hold")
