"""The keyboard on the screen: playing the generator with nothing plugged in.

Driven the way a person drives it - Playwright's mouse on the keys and its
keyboard on the letters - so what is tested is the pointer and key handling,
not a function called from underneath it. The notes are checked against the
stack every other path writes to, and the pitches are worked out here from the
note numbers rather than read back from the page.

The failures this is written against: a key that stays lit after a panic, a
latch that forgets it was holding something, a finger lifted after an octave
shift releasing the wrong note, two ways of holding one key where lifting one
ends it, and letters that fire the shortcut as well as the note. (And a note
played into a rack that reached nothing, until P5 cut the rack.)
"""
# On the default page since stage 5's step 3 (13 Nov); on ?brain=js from 5m
# to then. The keys, the stack and the lit keys are the face's and read the
# same here. Three readings changed with the move:
# - the gate (`state.source.gated`) was the page generator's own flag; here it
#   is the instrument's, from its readings. Either way it says the generator
#   is one that waits for notes, not that it is silent now, so the claim that
#   the waveform waits is also read off the lane the instrument drew: silent
#   with no note, and (the null) sounding with one;
# - "the generator plays it" read `state.source.settings.freq`, and the
#   dyad's interval `settings.interval`. On the default those are the page's
#   mirror of the setup, written by the page's own MIDI apply
#   (midiApplyNotesTo), not by anything the instrument does, so they passed
#   here unchanged and for the old reason. Both are read now off the lanes the
#   instrument drew: the pitch of a held E3, and the ratio of a latched
#   fifth's two channels.
import math, os, sys
from playwright.sync_api import sync_playwright
import corpus

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

HZ = lambda note: 440 * 2 ** ((note - 69) / 12)

def null(name, red, detail=""):
    check("null: " + name, red, detail)

def pitch(xs, rate):
    """A lane's frequency from its rising zero crossings, placed between
    samples: worked out here from the samples the instrument drew, so it needs
    nothing of the page's but the ring."""
    m = sum(xs) / len(xs)
    xs = [x - m for x in xs]
    ups = [i - 1 + (-xs[i - 1]) / (xs[i] - xs[i - 1]) for i in range(1, len(xs)) if xs[i - 1] < 0 <= xs[i]]
    if len(ups) < 3: return 0.0
    return rate * (len(ups) - 1) / (ups[-1] - ups[0])

DRAWN = """(n) => ({ rate: state.source.sampleRate,
  lanes: state.source.getLatestWindow(n).slice(0, 2).map((x) => Array.from(x)) })"""


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    corpus.old_opening(p)  # the opening it was written against (P8h)
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

    print("\n--- the keys, and a generator that waits for a note either way ---")
    # The waveform generator is the default source, so the gate is the thing
    # to watch. It shut between notes only while something could play one
    # until 10 Nov, which on the site was a drone before a port could connect;
    # since then it waits for a note with the keys shut too, as the plugin does.
    QUIET = "() => { let m = 0; for (const v of state.source.getLatestWindow(4096)[0]) m = Math.max(m, Math.abs(v)); return m; }"
    before = p.evaluate("() => ({ present: keyboardPresent(), gated: state.source.gated })")
    before["peak"] = p.evaluate(QUIET)
    # Things that are on the screen. The first draft measured the lag's mix
    # slider, which lives in the closed Settings panel: its box is all noughts
    # open or shut, so the check could not fail.
    # The trace, and two controls on the face: the timebase was the second
    # until F1 put it in Scope & measure, shut, where it measures nothing.
    BOXES = """() => [el.trace, el.measureButton, el.pictureMore].map((e) => {
      const r = e.getBoundingClientRect();
      return [r.x, r.y, r.width, r.height].map((v) => Math.round(v * 10) / 10); })"""
    where = p.evaluate(BOXES)
    p.evaluate("() => el.keysOpen.click()"); p.wait_for_timeout(150)
    opened = p.evaluate("""() => ({ present: keyboardPresent(), gated: state.source.gated,
      shown: !el.screenKeys.hidden, keys: el.keysBed.children.length,
      playing: !el.midiPlayingRow.hidden, label: el.keysOpen.textContent,
    })""")
    opened["moved"] = p.evaluate(BOXES)
    opened["peak"] = p.evaluate(QUIET)
    print("    closed %s; open %s" % (before, opened))
    waits = lambda r, present: r["present"] is present and r["gated"] is True
    check("with no port and no keys there is no keyboard, and the waveform waits for a note all the same",
          waits(before, False) and before["peak"] == 0, str(before))
    # The null: the reading as the page opened until 10 Nov, ungated.
    check("and the reading fails against an ungated generator", not waits(dict(before, gated=False), False))
    check("opening the keys makes a keyboard present, and the waveform still waits for a note",
          waits(opened, True) and opened["peak"] == 0, str(opened))
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
    down = p.evaluate("""() => ({ notes: midi.notes.map((n) => [n.note, n.velocity]) })""")
    lit_down = lit()
    # Held, long enough for the instrument to have drawn it: its pitch read off
    # what it drew, and its gate, which a held note opens.
    p.wait_for_timeout(500)
    drawn = p.evaluate(DRAWN, 8192)
    down["freq"] = pitch(drawn["lanes"][0], drawn["rate"])
    held_peak = p.evaluate(QUIET)
    lift()
    print("    E3 down: %s, lit %s; released: %s" % (down, lit_down, held()))
    check("pressing E3 puts E3 on the stack at the slider's velocity",
          down["notes"] == [[52, 100 / 127]], str(down["notes"]))
    # Within a twentieth of a semitone of E3, read off the instrument's lane
    # (the page's mirror was exact, but it was the page's arithmetic); A3, the
    # old opening's pitch, and D3 and F3 either side are all well outside it.
    check("and the instrument plays it: the lane it drew is E3",
          abs(math.log2(down["freq"] / HZ(52)) * 12) < 0.05, "%.3f Hz against %.3f" % (down["freq"], HZ(52)))
    null("the same reading taken against D#3 fails", abs(math.log2(down["freq"] / HZ(51)) * 12) >= 0.05, "%.3f Hz" % down["freq"])
    null("and a held note sounds, so the silence read with none is the waiting and not a dead lane", held_peak > 0.05, "peak %.3f" % held_peak)
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
    fifth = p.evaluate("""() => ({ notes: midi.notes.map((n) => n.note).sort((a, b) => a - b) })""")
    p.wait_for_timeout(500)
    drawn = p.evaluate(DRAWN, 8192)
    lo_hz, hi_hz = (pitch(x, drawn["rate"]) for x in drawn["lanes"])
    fifth["ratio"] = hi_hz / lo_hz if lo_hz else 0
    fifth["hz"] = [round(lo_hz, 2), round(hi_hz, 2)]
    tap(48)
    after_toggle = held()
    latch(False)
    after_off = held()
    print("    C3 and G3 tapped: %s; C3 tapped again: %s; latch off: %s"
          % (fifth, after_toggle, after_off))
    check("two taps under latch hold both notes after the mouse is up",
          fifth["notes"] == [48, 55], str(fifth["notes"]))
    # The fifth just or tempered, as the setup tunes it (1.5 or 1.4983): within
    # a twentieth of a semitone of seven, which a fourth or a sixth is not.
    semis = lambda r: 12 * math.log2(r) if r > 0 else 0
    check("and the dyad the instrument draws is the interval between them - seven semitones, a fifth, on C3",
          abs(semis(fifth["ratio"]) - (55 - 48)) < 0.05 and abs(math.log2(lo_hz / HZ(48)) * 12) < 0.05, str(fifth))
    null("the same reading against a fourth fails", abs(semis(fifth["ratio"]) - 5) >= 0.05, "%.3f semitones" % semis(fifth["ratio"]))
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
    check("and the generator goes on waiting for a note with the keys gone",
          waits(closed, False), str(closed))

    p.keyboard.press("s"); p.wait_for_timeout(60)
    shortcut = p.evaluate("() => state.mode")
    p.evaluate("() => setMode('auto')")
    check("with the keys closed, S is Single again", shortcut == "single", shortcut)

    # A generator lane following the keys - a note played into a rack reaching
    # the generator as one of its lanes, the Kind menu reaching the lane, and
    # Drive recording its answer for the lane's kind - was checked here until
    # P5 cut the rack.

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the keys play the same stack a keyboard does, and let go of what they hold")
