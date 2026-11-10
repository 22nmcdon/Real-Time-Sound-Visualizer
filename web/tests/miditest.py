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
# On ?brain=js (5m): this suite reads the page's own brain - its keyboard's
# flags, set directly - which core/tests/parity.py holds the instrument to,
# sample for sample. The instrument, the site's default since 5m, is
# braintest.py's and hosttest.py's.
import math, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


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
    p.goto(f"file://{ART}/scope.html?picture=0&brain=js"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    def send(*data):
        p.evaluate("(d) => __send(d)", list(data))

    def held():
        return p.evaluate("() => midi.notes.map((n) => n.note)")

    def tone():
        return p.evaluate("""() => ({
          freq: state.source.settings.freq,
          interval: state.source.settings.interval,
          octaves: state.source.settings.octaves,
          menu: Number(el.interval.value),
          credit: el.credit.textContent,
        })""")

    # The routes the generator is handed, as [slot, depth] pairs: what is
    # heard, rather than what the routings list says.
    ROUTES = """() => { stepRoutes(); return genRoutes.map((r) => [r.slot, r.full]); }"""
    vcf = p.evaluate("() => MOD_DESTS.get('gen.vcf').slot")

    print("\n--- the port ---")
    # A routing from the key's strength made before there is a keyboard is
    # skipped, there being no source; the port opening has to bring it in.
    # Asserting the routing was still listed passed while it was never heard.
    p.evaluate("() => { state.modRoutings = [{ sourceId: 'midi.key', destId: 'gen.vcf', amount: 0.5 }]; touchRoutings(); }")
    unplugged = p.evaluate(ROUTES)
    p.evaluate("() => midiConnect()")
    p.wait_for_timeout(100)
    plugged = p.evaluate(ROUTES)
    check("a routing from the keyboard made before it was plugged in is heard once it is, and not before",
          unplugged == [] and plugged == [[vcf, 0.5]], "%s, then %s" % (unplugged, plugged))
    p.evaluate("() => { state.modRoutings = []; touchRoutings(); }")
    wired = p.evaluate("() => ({ status: midi.status, ports: midi.ports, "
                       "bound: typeof __midi.port.onmidimessage })")
    check("a port is opened and its messages are listened to",
          wired["status"] == "on" and wired["bound"] == "function", str(wired))
    check("and it is named in the panel", wired["ports"] == ["Stub Keyboard"],
          str(wired["ports"]))

    print("\n--- parsing ---")
    send(0x90, 60, 100)
    check("a note-on holds the note", held() == [60], str(held()))
    send(0x90, 60, 0)
    check("a note-on at velocity zero is a note-off", held() == [], str(held()))

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
    p.evaluate("() => window.dispatchEvent(new Event('blur'))")
    check("losing the window releases everything", held() == [], str(held()))

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
    p.evaluate("""() => {
      midiPanic();
      midi.mode = 'dyad'; midi.hold = false;
      el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change'));
      el.tuneJust.click();
      syncMidi();
    }""")

    check("nothing held is a closed gate", p.evaluate("() => midi.key") == 0)

    send(0x90, 60, 100)
    one = tone()
    check("one note is a unison at its own pitch",
          close(one["freq"], HZ(60), 0.01) and one["interval"] == 0
          and one["octaves"] == 0, str(one))

    send(0x90, 67, 100)
    up = tone()
    send(0x80, 67, 0); send(0x80, 60, 0)
    send(0x90, 67, 100); send(0x90, 60, 100)
    down = tone()
    check("two notes are the lower pitch and the interval above it",
          close(up["freq"], HZ(60), 0.01) and up["interval"] == 7, str(up))
    check("and the press order does not turn the figure over",
          close(down["freq"], up["freq"], 1e-9) and down["interval"] == up["interval"],
          "%s vs %s" % (down["interval"], up["interval"]))
    check("the interval menu says what is being played", up["menu"] == 7, str(up["menu"]))

    p.evaluate("() => midiPanic()")
    send(0x90, 60, 100); send(0x90, 67, 100); send(0x90, 64, 100)
    three = tone()
    check("a third note displaces the older of the pair",
          close(three["freq"], HZ(64), 0.01) and three["interval"] == 3, str(three))

    send(0x80, 67, 0)
    after = tone()
    check("releasing one of the pair promotes what was under it",
          close(after["freq"], HZ(60), 0.01) and after["interval"] == 4, str(after))

    p.evaluate("() => midiPanic()")
    send(0x90, 60, 100); send(0x90, 67, 100); send(0x80, 67, 0)
    lone = tone()
    check("back to one note is back to a unison", lone["interval"] == 0, str(lone))

    p.evaluate("() => { midiPanic(); midi.hold = true; }")
    send(0x90, 60, 100); send(0x90, 67, 100); send(0x80, 67, 0)
    kept = tone()
    # One finger walking: the old note goes before the new one arrives, or the
    # two of them are a dyad in their own right and Hold has nothing to do.
    send(0x80, 60, 0); send(0x90, 62, 100)
    walked = tone()
    check("with Hold on the interval stays above the one note",
          kept["interval"] == 7 and close(kept["freq"], HZ(60), 0.01), str(kept))
    check("and walks with it", walked["interval"] == 7
          and close(walked["freq"], HZ(62), 0.01), str(walked))
    p.evaluate("() => { midiPanic(); midi.hold = false; }")

    print("\n--- wider than an octave ---")
    send(0x90, 60, 100); send(0x90, 79, 100)      # C4 and G5: an octave and a fifth
    wide = tone()
    check("nineteen semitones is a fifth plus an octave",
          wide["interval"] == 7 and wide["octaves"] == 1, str(wide))
    check("and the credit line says so", "octave" in wide["credit"], wide["credit"])

    ratios = p.evaluate("""() => {
      const t = state.source.settings;
      const one = intervalRatio(t.interval, true) * Math.pow(2, t.octaves);
      const two = intervalRatio(t.interval, false) * Math.pow(2, t.octaves);
      return { just: one, equal: two,
               beatJust: beatRate(t.interval, true, t.freq, t.octaves),
               beatEqual: beatRate(t.interval, false, t.freq, t.octaves),
               freq: t.freq };
    }""")
    want_beat = abs(2 * ratios["freq"] * 2 ** (19 / 12) - 3 * 2 * ratios["freq"])
    check("a wide dyad is 3:1 in just tuning", close(ratios["just"], 3.0, 1e-12),
          str(ratios["just"]))
    check("and 2^(19/12) in equal", close(ratios["equal"], 2 ** (19 / 12), 1e-12),
          str(ratios["equal"]))
    check("the beat is zero in just and the octave-wide rate in equal",
          ratios["beatJust"] == 0 and close(ratios["beatEqual"], want_beat, 1e-9),
          "%.4f vs %.4f" % (ratios["beatEqual"], want_beat))

    print("\n--- tuning (D3) ---")
    p.evaluate("() => midiPanic()")
    send(0x90, 57, 100); send(0x90, 64, 100)      # A3 and E4: a fifth
    fifth = p.evaluate("""() => {
      const t = state.source.settings;
      el.tuneJust.click();
      const just = intervalRatio(t.interval, t.just) * Math.pow(2, t.octaves);
      const beatJust = beatRate(t.interval, t.just, t.freq, t.octaves);
      el.tuneEqual.click();
      const equal = intervalRatio(t.interval, t.just) * Math.pow(2, t.octaves);
      const beatEqual = beatRate(t.interval, t.just, t.freq, t.octaves);
      el.tuneJust.click();
      return { just, equal, beatJust, beatEqual, freq: t.freq };
    }""")
    check("a played fifth is exactly 3:2 in just tuning",
          close(fifth["just"], 1.5, 1e-12), str(fifth["just"]))
    check("and the tempered ratio in equal",
          close(fifth["equal"], 2 ** (7 / 12), 1e-12), str(fifth["equal"]))
    check("so the figure stands still in just and turns in equal",
          fifth["beatJust"] == 0
          and close(fifth["beatEqual"], abs(2 * fifth["freq"] * 2 ** (7 / 12)
                                            - 3 * fifth["freq"]), 1e-9),
          "%.4f Hz" % fifth["beatEqual"])

    # The end of the argument: not what the page computes, but what came out of
    # the generator. The ring buffer has to turn over first.
    p.wait_for_timeout(400)
    measured = p.evaluate("""() => {
      const w = state.source.getLatestWindow(8192);
      return [estimateFrequency(w[0], state.source.sampleRate),
              estimateFrequency(w[1], state.source.sampleRate)];
    }""")
    ok = measured[0] and measured[1]
    check("and the note is in the samples, not only in the state",
          ok and close(measured[0], HZ(57), 2) and close(measured[1] / measured[0], 1.5, 0.01),
          str(measured))

    # The estimator is good to about a part in ten million here, and just and
    # equal differ in the third decimal place, so the difference between a
    # figure that stands still and one that turns is measurable in the samples
    # rather than only assertable about the state. The beat the page claims in
    # its readout is |2*fR - 3*fL| of what actually came out.
    p.evaluate("() => el.tuneEqual.click()")
    p.wait_for_timeout(450)
    tempered = p.evaluate("""() => {
      const w = state.source.getLatestWindow(8192);
      const t = state.source.settings;
      return { l: estimateFrequency(w[0], state.source.sampleRate),
               r: estimateFrequency(w[1], state.source.sampleRate),
               claimed: beatRate(t.interval, t.just, t.freq, t.octaves) };
    }""")
    p.evaluate("() => el.tuneJust.click()")
    p.wait_for_timeout(450)
    pure = p.evaluate("""() => {
      const w = state.source.getLatestWindow(8192);
      return { l: estimateFrequency(w[0], state.source.sampleRate),
               r: estimateFrequency(w[1], state.source.sampleRate) };
    }""")
    beat = abs(2 * tempered["r"] - 3 * tempered["l"]) if tempered["r"] else None
    check("in equal the samples carry the tempered ratio",
          close(tempered["r"] / tempered["l"], 2 ** (7 / 12), 1e-4),
          str(tempered["r"] / tempered["l"]) if tempered["r"] else "no pitch")
    check("and the figure turns at the rate the readout claims",
          close(beat, tempered["claimed"], 0.05),
          "%.3f Hz measured, %.3f claimed" % (beat, tempered["claimed"]))
    check("in just it is 3:2 and stands still",
          close(pure["r"] / pure["l"], 1.5, 1e-4)
          and abs(2 * pure["r"] - 3 * pure["l"]) < 0.05,
          str(pure))

    print("\n--- mono ---")
    p.evaluate("""() => {
      midiPanic();
      el.interval.value = '4'; el.interval.dispatchEvent(new Event('change'));
      el.midiMono.click();
    }""")
    send(0x90, 60, 100); send(0x90, 67, 100)
    mono = tone()
    check("mono takes the newest note as the pitch",
          close(mono["freq"], HZ(67), 0.01), str(mono["freq"]))
    check("and leaves the interval to the menu", mono["interval"] == 4, str(mono))

    # A dyad two octaves wide, then mono: the menu says "major 3rd" and covers
    # one octave, so anything left in `octaves` is a ratio nothing can say.
    wide_then_mono = p.evaluate("""() => {
      midiPanic(); el.midiDyad.click();
      midiBytes(Uint8Array.from([0x90, 48, 100]));
      midiBytes(Uint8Array.from([0x90, 76, 100]));      // two octaves and a third
      const dyad = state.source.settings.octaves;
      el.midiMono.click();
      return { dyad, mono: state.source.settings.octaves,
               interval: state.source.settings.interval };
    }""")
    check("and does not inherit the dyad's octaves",
          wide_then_mono["dyad"] == 2 and wide_then_mono["mono"] == 0
          and wide_then_mono["interval"] == 4, str(wide_then_mono))
    p.evaluate("() => { midiPanic(); el.midiDyad.click(); }")

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
      const vibrato = genSettings().vibrato;
      midiBytes(Uint8Array.from([0xB0, 1, 0]));
      buildSourceChips();
      return { learned: [...MOD_SOURCES.keys()].filter((id) => id.startsWith('cc.')), vibrato,
               cards: Array.from(document.querySelectorAll('.mod-card')).map((c) => c.dataset.source) };
    }""")
    check("controllers moved are learned as nothing, and the cards are still three",
          moved["learned"] == [] and moved["cards"] == ["lfo1", "lfo2", "env.note"], str(moved))
    check("null: the wheel still sets the vibrato", moved["vibrato"] > 0.3, str(moved["vibrato"]))

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
    truth = p.evaluate("""() => {
      midiPanic();
      state.modRoutings = []; touchRoutings();
      state.lagOn = true; state.lagAuto = true;
      midi.truth = true;
      // A dyad, whose pitch is the slider's once the note has set it; a
      // chord's voices keep their notes' pitches whatever the slider says.
      el.midiDyad.click();
      midiBytes(Uint8Array.from([0x90, 69, 100]));   // A4, 440 Hz
      /* A deliberately wrong estimate: the generator moved off the note after
         it was struck, so the note and the signal disagree. Until G2 this
         unticked the waveform's drive first, so the note never moved it;
         notes always play the waveform now, so it is moved back by hand. */
      el.freq.value = '100'; el.freq.dispatchEvent(new Event('input'));
      lagLock = null;
      lagLockUpdate(capture());
      return lagLock;
    }""")
    check("with a note held the lag is a quarter period of the note, exactly",
          truth == 0.25 / 440, "%r vs %r" % (truth, 0.25 / 440))

    p.wait_for_timeout(400)
    estimate = p.evaluate("""() => {
      midi.truth = false;
      lagLock = null;
      lagLockUpdate(capture());
      const fromEstimate = lagLock;
      midi.truth = true;
      return fromEstimate;
    }""")
    check("and without it the estimator is back, on the signal that is there",
          close(estimate, 0.25 / 100, 0.25 / 100 * 0.05), str(estimate))

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
