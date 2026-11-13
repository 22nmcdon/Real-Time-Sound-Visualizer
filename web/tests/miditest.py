"""The keyboard: parsing, the held-note stack, the dyad, and the note as truth.

No keyboard is needed and none is simulated at a level above the wire: the stub
below hands `midiBytes` the same bytes a port would, so every assertion here is
about the code the Nord actually reaches. What cannot be checked this way is the
CC numbers themselves - those are a fact about the firmware in the room, which
is why the page ships a monitor line rather than trusting its own map.

The numbers are worked out here rather than read back from the page. A test that
asks the page what it thinks and then agrees with it passes whatever the page
does.
"""
# On the default page since stage 5, step 3, batch 4 (13 Nov). Until then on
# ?brain=js, reading the page's own brain: its keyboard's flags set directly,
# its generator's settings and samples, its lag lock. On the default those are
# the face's mirror, written by the page's own MIDI apply beside the
# instrument, so every row that said what the generator plays - the dyad, Hold,
# mono, the ratios, the samples, the wheel, the note as the lag's truth - went
# to core/tests/pieces/midi.py, read off the instrument itself. What stays is
# the face's: the port, the stack the keys on the screen show, the panics (now
# also heard to reach the instrument), the menu and credit line, the
# controllers' cards, the timebase and the tuner, the codec and Velocity's menu.
import math, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    check("null: " + name, red, detail)


def close(a, b, tol):
    return a is not None and b is not None and abs(a - b) <= tol


# One port, one callback, and a way to push bytes at it. Installed before the
# page's own script runs, so `midi.supported` sees it.
STUB = """
  window.__midi = { port: null, sent: [] };
  navigator.requestMIDIAccess = function () {
    const port = { id: "stub", name: "Stub Keyboard", onmidimessage: null };
    window.__midi.port = port;
    const inputs = new Map([["stub", port]]);
    return Promise.resolve({ inputs, outputs: new Map(), onstatechange: null });
  };
  window.__send = function (bytes) {
    window.__midi.port.onmidimessage({ data: Uint8Array.from(bytes) });
  };
"""

HZ = lambda note: 440 * 2 ** ((note - 69) / 12)

# The timebase steps, in milliseconds per division, from the page.
TIMEBASE = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50]

def best_timebase(hz, periods=4):
    want = periods * 1000.0 / hz
    return min(range(len(TIMEBASE)),
               key=lambda i: abs(math.log2(TIMEBASE[i] * 10 / want)))


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.add_init_script(STUB)
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    def send(*data):
        p.evaluate("(d) => __send(d)", list(data))

    def held():
        return p.evaluate("() => midi.notes.map((n) => n.note)")

    # The menu and the credit line: the face's, as the page's MIDI apply
    # writes them. What the generator plays is pieces/midi.py's.
    def tone():
        return p.evaluate("""() => ({ menu: Number(el.interval.value), credit: el.credit.textContent })""")

    # The loudest of the instrument's latest 4096 samples on the first lane:
    # what the site's instrument drew, so a panic that cleared only the face's
    # stack would leave it sounding.
    LOUD = "() => { let m = 0; for (const v of state.source.getLatestWindow(4096)[0]) m = Math.max(m, Math.abs(v)); return m; }"

    print("\n--- the port ---")
    # Gone (batch 4): "a routing from the keyboard made before it was plugged
    # in is heard once it is, and not before", which read the page's own
    # stepRoutes and genRoutes. The page registers the Key source when a port
    # opens; the instrument's matrix has it from the start (sources.h), so on
    # the site there is no "before" to hear nothing in. A path only the
    # page's brain has.
    p.evaluate("() => midiConnect()")
    p.wait_for_timeout(100)
    check("the page is the site's: the instrument is the source", p.evaluate("() => state.source.kind") == "host",
          p.evaluate("() => state.source.kind"))
    wired = p.evaluate("() => ({ status: midi.status, ports: midi.ports, "
                       "bound: typeof __midi.port.onmidimessage })")
    check("a port is opened and its messages are listened to",
          wired["status"] == "on" and wired["bound"] == "function", str(wired))
    check("and it is named in the panel", wired["ports"] == ["Stub Keyboard"],
          str(wired["ports"]))

    print("\n--- parsing ---")
    # These read `midi.notes`, the face's stack, which the keys on the screen
    # and the readout show: the page parses a port's bytes for itself and
    # hands the instrument the same bytes. The core keyboard's parse of them,
    # what is heard, is pieces/midi.py's.
    send(0x90, 60, 100)
    check("a note-on holds the note", held() == [60], str(held()))
    send(0x90, 60, 0)
    check("a note-on at velocity zero is a note-off", held() == [], str(held()))

    # The face's stack, and only the face's: on the site the page cuts a
    # port's message into pieces of three bytes, and the instrument's keyboard
    # drops the half message the cut leaves, so the third note here is never
    # heard (in Mono the instrument plays E4, the face says G4 - batch 4,
    # web/docs/after-stage-5.md). The core's parse of the message whole is
    # pieces/midi.py's.
    send(0x90, 60, 100, 64, 100, 67, 100)
    check("running status: one status byte, three notes", held() == [60, 64, 67],
          str(held()))

    send(0x80, 60, 0, 64, 0, 67, 0)
    check("and again on the way out", held() == [], str(held()))

    send(0x90, 60, 100)
    send(0x90, 60, 100)
    check("the same note twice does not stack twice", held() == [60], str(held()))
    send(0x80, 60, 0)
    check("so one release ends it", held() == [], str(held()))

    # A clock byte between messages is the commonest thing on a real cable.
    send(0xF8, 0x90, 62, 100, 0xF8)
    check("a clock byte is not mistaken for a note", held() == [62], str(held()))

    print("\n--- the panic ---")
    # And the instrument hears it: a held note sounding, then the window
    # lost, then the release run out. The null is the same note sounding
    # before, so the reading can read a sound.
    p.wait_for_timeout(500)
    sounding = p.evaluate(LOUD)
    p.evaluate("() => window.dispatchEvent(new Event('blur'))")
    check("losing the window releases everything", held() == [], str(held()))
    p.wait_for_timeout(900)
    after_blur = p.evaluate(LOUD)
    check("and the instrument hears it: the held note is silent once its release has run out",
          after_blur < 1e-4, "%.5f, from %.3f" % (after_blur, sounding))
    null("the same note before the window was lost is sounding", sounding > 0.05, "%.3f" % sounding)

    send(0x90, 62, 100)
    p.evaluate("""() => {
      Object.defineProperty(document, 'visibilityState',
        { value: 'hidden', configurable: true });
      document.dispatchEvent(new Event('visibilitychange'));
    }""")
    check("and so does being hidden without losing it", held() == [], str(held()))
    p.evaluate("""() => {
      Object.defineProperty(document, 'visibilityState',
        { value: 'visible', configurable: true });
    }""")

    send(0x90, 62, 100)
    send(0xB0, 123, 0)
    check("all-notes-off releases them and does not learn as a controller",
          held() == [] and not p.evaluate("() => MOD_SOURCES.has('cc.123')"))

    print("\n--- the dyad (D2) ---")
    # Batch 4: the dyad's pitches, Hold, the wide dyad and its ratios, the
    # tuning heard in the samples and mono went to core/tests/pieces/midi.py.
    # They read `state.source.settings` and the page's own generator's
    # samples here, which on the default site are the face's mirror; there
    # they read the instrument's generator and its heard pair. What stays is
    # what the face says of the notes: its gate flag, the interval menu and
    # the credit line, written by the page's own apply of the same bytes.
    p.evaluate("""() => {
      midiPanic(); midi.hold = false;
      el.midiDyad.click();
      el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change'));
      el.tuneJust.click();
    }""")

    check("nothing held is a closed gate, on the face", p.evaluate("() => midi.key") == 0)

    send(0x90, 60, 100)
    one = tone()
    send(0x90, 67, 100)
    up = tone()
    check("the interval menu says what is being played", up["menu"] == 7, str(up["menu"]))
    null("and with one note it said a unison, not the fifth", one["menu"] != 7, str(one["menu"]))

    p.evaluate("() => midiPanic()")
    print("\n--- wider than an octave ---")
    send(0x90, 60, 100); send(0x90, 79, 100)      # C4 and G5: an octave and a fifth
    wide = tone()
    check("and the credit line says a wide dyad is an octave and more", "octave" in wide["credit"], wide["credit"])
    p.evaluate("() => midiPanic()")
    send(0x90, 60, 100); send(0x90, 67, 100)
    null("and a fifth's credit line does not say an octave", "octave" not in tone()["credit"], tone()["credit"])
    p.evaluate("() => midiPanic()")

    # Which generator kinds a note played (D4), a box a kind, went with the
    # drawings in G2: notes always play the waveform. That they do is every
    # check above; that nothing is left to untick is the setup's, below.

    print("\n--- controllers ---")
    # A controller became a source the first time it moved, named from the
    # Nord's panel, walked to where it was moved and could be renamed, saved
    # and forgotten. F4b (7 Nov) cut learning with the matrix's other sources:
    # what is left is the wheel into Expression, the swell onto the Picture
    # amount, the pedal and the panics. So: moving controllers registers
    # nothing, and the wheel still sets the vibrato - the null, a controller
    # that still does what it is for.
    moved = p.evaluate("""async () => {
      midiBytes(Uint8Array.from([0xB0, 16, 64]));
      midiBytes(Uint8Array.from([0xB0, 42, 10]));
      el.midiWheelTo.value = 'vibrato'; el.midiWheelTo.dispatchEvent(new Event('change'));
      midiBytes(Uint8Array.from([0xB0, 1, 127]));
      midiBytes(Uint8Array.from([0xB0, 1, 0]));
      buildSourceChips();
      return { learned: [...MOD_SOURCES.keys()].filter((id) => id.startsWith('cc.')),
               cards: Array.from(document.querySelectorAll('.mod-card')).map((c) => c.dataset.source) };
    }""")
    # Four since G5a made the Photocell a card; a learned controller would have been a fifth.
    learned_nothing = lambda m: m["learned"] == [] and m["cards"] == ["lfo1", "lfo2", "env.note", "photo.1"]
    check("controllers moved are learned as nothing, and the cards are still the four", learned_nothing(moved), str(moved))
    # Its null was "the wheel still sets the vibrato", read off genSettings():
    # on the default that is the face's mirror, so since batch 4 the wheel is
    # held on the instrument in pieces/midi.py, and the null here is a
    # controller the face did learn - a source put in its registry by hand -
    # which the reading has to see.
    taught = p.evaluate("""() => {
      registerSource({ id: 'cc.16', label: 'Taught', family: 'keyboard', value: () => 0 });
      buildSourceChips();
      const out = { learned: [...MOD_SOURCES.keys()].filter((id) => id.startsWith('cc.')),
                    cards: Array.from(document.querySelectorAll('.mod-card')).map((c) => c.dataset.source) };
      MOD_SOURCES.delete('cc.16'); buildSourceChips();
      return out;
    }""")
    null("a controller in the registry is seen as learned", not learned_nothing(taught), str(taught))

    # A code from before: version 8, a controller on the frequency and its
    # name kept, beside an oscillator's routing. Version 9's decode pass drops
    # the controller's routing and its name and keeps the oscillator's.
    old = p.evaluate("""() => {
      const code = encodeSetup(Object.assign({}, BASE_SETUP, { v: 8, cc: '16:Bass drawbar',
        mod: 'cc.16>gen.freq@1.000;lfo1>view.rotate@0.500' }));
      restore(decodeSetup(code));
      const out = { routes: state.modRoutings.map((r) => r.sourceId + '>' + r.destId), cc: 'cc' in snapshot() };
      state.modRoutings = []; touchRoutings();
      return out;
    }""")
    check("an old code's controller routing and names are dropped, and an oscillator's kept",
          old == {"routes": ["lfo1>view.rotate"], "cc": False}, str(old))

    print("\n--- the note as ground truth ---")
    # Batch 4: "with a note held the lag is a quarter period of the note,
    # exactly" and "without it the estimator is back" read the page's own
    # lagLockUpdate on its own capture; the instrument locks its own lag, and
    # both rows are pieces/midi.py's, read off it. The timebase and the tuner
    # below are the face's: the screen and its reference note, which the
    # instrument has no part in.
    times = p.evaluate("""() => {
      midiPanic();
      midi.follow = true;
      midiBytes(Uint8Array.from([0x90, 57, 100]));   // A3
      midiFollowTimebase();
      const low = state.timebase;
      midiPanic();
      midiBytes(Uint8Array.from([0x90, 69, 100]));   // A4
      midiFollowTimebase();
      const high = state.timebase;
      midi.follow = false; midiPanic();
      return { low, high, slider: Number(el.timebase.value) };
    }""")
    check("the timebase follows the note, four periods across",
          times["low"] == best_timebase(HZ(57))
          and times["high"] == best_timebase(HZ(69)),
          "%s then %s" % (times["low"], times["high"]))
    check("and the slider says what the screen is doing",
          times["slider"] == times["high"], str(times))

    tuner = p.evaluate("""() => {
      state.panesExtra.tuner = true; syncPanes();
      midiPanic();
      midi.truth = true;
      midiBytes(Uint8Array.from([0x90, 57, 100]));
      return true;
    }""")
    p.wait_for_timeout(500)
    reading = p.evaluate("""() => {
      const hz = estimateFrequency(
        state.source.getLatestWindow(8192)[0], state.source.sampleRate);
      const played = midiPitch();
      return { hz, played, ref: midiPitchHz() };
    }""")
    check("the tuner has a played note to read against, and it is the note",
          reading["played"] == 57 and close(reading["ref"], HZ(57), 1e-9),
          str(reading))

    print("\n--- the setup, round tripped ---")
    trip = p.evaluate("""() => {
      midi.mode = 'mono'; midi.hold = true; midi.truth = false; midi.follow = true;
      syncMidi();
      const snap = snapshot(), code = encodeSetup(snap);
      midi.mode = 'dyad'; midi.hold = false; midi.truth = true; midi.follow = false;
      restore(decodeSetup(code));
      // The keyboard's drive and play went with the drawings (G2): a code has neither.
      return { mode: midi.mode, hold: midi.hold, truth: midi.truth,
               follow: midi.follow, kept: ['midiDrive', 'midiPlay'].filter((k) => k in snap),
               shown: el.midiMono.getAttribute('aria-checked') };
    }""")
    check("every keyboard setting comes back, and a code carries no drive or play",
          trip["mode"] == "mono" and trip["hold"] and trip["truth"] is False
          and trip["follow"] and trip["kept"] == [], str(trip))
    check("and the panel says so", trip["shown"] == "true", str(trip["shown"]))

    defaults = p.evaluate("""() => {
      restore({});
      return { mode: midi.mode, truth: midi.truth, follow: midi.follow };
    }""")
    check("a setup written before the keyboard existed restores the defaults",
          defaults["mode"] == "dyad" and defaults["truth"] is True
          and defaults["follow"] is False,
          str(defaults))


    print("\n--- velocity (F4) ---")
    # Expression's Velocity menu: a note's level and strike always follow
    # velocity, and FM adds the Key source's routing onto the FM depth. The
    # menu is a view of that routing rather than a field, so it is read off a
    # preset that carries the routing - found by the routing, not by name -
    # and written by choosing, with another routing beside it left alone.
    vel = p.evaluate("""async () => {
      const wait = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      const routes = () => state.modRoutings.map((r) => r.sourceId + '>' + r.destId + '@' + Number(r.amount).toFixed(2)).sort();
      const out = {};
      restore(Object.assign({}, BASE_SETUP)); await wait();
      out.base = el.midiVelocityTo.value;
      const pick = PRESETS.flatMap(([, e]) => e).find(([, st]) => (st.mod || '').includes('midi.key>gen.fm'));
      applyPreset('b:' + pick[0]); await wait();
      out.preset = el.midiVelocityTo.value;
      restore(Object.assign({}, BASE_SETUP)); await wait();
      addRouting('lfo1', 'gen.freq');
      el.midiVelocityTo.value = 'fm'; el.midiVelocityTo.dispatchEvent(new Event('change')); await wait();
      out.fm = routes();
      el.midiVelocityTo.value = 'strike'; el.midiVelocityTo.dispatchEvent(new Event('change')); await wait();
      out.strike = routes();
      state.modRoutings = []; touchRoutings();
      return out;
    }""")
    print("    %s" % vel)
    check("Velocity reads Level and strike on the base, and FM on a preset that routes velocity to FM",
          vel["base"] == "strike" and vel["preset"] == "fm", str(vel))
    check("choosing FM adds velocity's routing onto the FM depth beside what is there, and Level and strike takes it off alone",
          vel["fm"] == ["lfo1>gen.freq@0.35", "midi.key>gen.fm@0.30"] and vel["strike"] == ["lfo1>gen.freq@0.35"], str(vel))

    print("\n--- and nothing else broke ---")
    p.evaluate("""() => {
      midiPanic();
      applyPreset('b:Harmonic tone');
    }""")
    p.wait_for_timeout(300)
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("every keyboard check passes")
