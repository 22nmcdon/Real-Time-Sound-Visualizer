"""The site's second arrangement (plugin/PLAN.md, stage 5f): ?brain=core.

The page as the face of the instrument compiled whole - the plugin's brain and
engine (scope::Instrument), playing in a worklet - by the same code that
makes it the plugin's face, rather than the page's own brain driving the
compiled engine. core/tests/parity.py holds the compiled instrument to the
native one sample for sample; this holds what the page does with it:

- without the switch the page is the website, and ?core=js turns the switch
  off - each read from the source the page is drawing, not from the address;
- with it the page draws the instrument's own picture, shows its state, and
  keeps the generator's panel (which hosted pages had lost altogether);
- a note played on the page is heard in the instrument at its pitch - against
  a pitch a semitone up, which is not - and silence before and after it;
- a slider, a preset, the kind menu and a port's bytes reach the instrument,
  and a port's bytes are passed on once, not again as the notes the page
  makes of them;
- what the instrument sends to a MIDI port goes out of the page's port on the
  page's channel, and the page's own brain sends nothing beside it;
- the sound switch opens and closes the instrument's way out;
- a module that will not make leaves the page as the website;
- and a browser that has not been pressed yet runs no blocks, says so, and
  starts on the first press.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
PAGE = f"file://{ART}/scope.html"

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

# The pitch of the picture's left lane, from its rising zero crossings: the
# first and the last, interpolated, and how many lie between.
PITCH = """(n) => {
  const [l] = state.source.getLatestWindow(n);
  const rate = state.source.sampleRate, at = [];
  for (let k = 1; k < l.length; k++) if (l[k - 1] < 0 && l[k] >= 0) at.push(k - 1 + l[k - 1] / (l[k - 1] - l[k]));
  return at.length < 3 ? 0 : (at.length - 1) * rate / (at[at.length - 1] - at[0]);
}"""
PEAK = "(n) => Math.max(...state.source.getLatestWindow(n)[0].map(Math.abs))"
# Where the right lane stands against the left, as a fraction of a cycle of
# 220 Hz: the lag at which the right best matches the left. Harmonic tone puts
# the two a quarter-cycle apart, so a picture handed over with its lanes the
# wrong way round reads three quarters.
SKEW = """(n) => {
  const [l, r] = state.source.getLatestWindow(n);
  const period = state.source.sampleRate / 220;
  let best = -Infinity, at = 0;
  for (let k = 0; k < Math.round(period); k++) {
    let sum = 0;
    for (let t = 0; t + k < n; t++) sum += l[t] * r[t + k];
    if (sum > best) { best = sum; at = k; }
  }
  return at / period;
}"""

def opened(b, query, settle=2500, close=True):
    p = b.new_page(viewport={"width": 1400, "height": 900})
    errors = []
    p.on("pageerror", lambda e: errors.append(str(e)))
    p.goto(PAGE + query)
    p.wait_for_timeout(settle)
    # Closing the help sheet is a press, so a check on an unpressed page leaves it open.
    if close and p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    return p, errors

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    for query, want in (("", "tone"), ("?brain=core&core=js", "tone")):
        p, _ = opened(b, query, 1200)
        got = p.evaluate("() => ({ kind: state.source.kind, host: !!scopeHost, brain: BRAIN_IN_CORE, mic: el.srcMic.disabled })")
        if not query:
            # The website's own picture of a note, for the instrument's to be held to below.
            p.evaluate("() => { applyPreset('b:Harmonic tone'); midiNoteOn(57, 100); }")
            p.wait_for_timeout(600)
            site_skew = p.evaluate(SKEW, 4096)
        check("with %s the page is the website, on its own generator, its other sources offered" % (query or "no switch"),
              got["kind"] == want and not got["host"] and not got["brain"] and got["mic"] is False, str(got))
        p.close()

    p, errors = opened(b, "?brain=core")
    first = p.evaluate("""async () => ({ kind: state.source.kind, mark: el.sourceMark.textContent, on: hostSync.on,
      seen: hostSync.seen, chunks: state.source.chunks, rate: state.source.sampleRate, ctxRate: deviceRate(),
      timebase: decodeSetup((await scopeHost.call('scopeState')).code).timebase })""")
    p.wait_for_timeout(500)
    later = p.evaluate("() => state.source.chunks")
    check("with ?brain=core the page draws the instrument in the worklet, and the instrument is playing",
          first["kind"] == "host" and first["mark"] == "Instrument" and first["on"] and later > first["chunks"] > 0,
          "%s, %d chunks half a second later" % (first, later))
    check("and the page shows the instrument's state, put on it as the plugin's is", first["seen"] >= 1, str(first["seen"]))
    # The page opens on Harmonic tone, whose timebase is 3 where the default's is 4.
    check("and the instrument was made on the setup the page opened on, not on the defaults",
          first["timebase"] == 3, str(first["timebase"]))
    p.evaluate("() => setView('bench')")
    p.wait_for_timeout(300)
    panel = p.evaluate("""() => ({ kind: el.genMode.offsetParent !== null, freq: el.freq ? el.freq.offsetParent !== null : null,
      sound: !el.genSoundRow.hidden, mode: genSettings() && genSettings().mode,
      others: [el.srcFile, el.srcRack].every((b) => b.disabled) && ![el.srcTone, el.srcMic].some((b) => b.disabled) })""")
    check("and keeps the generator's panel, kind and frequency, and the switch to hear it",
          panel["kind"] and panel["freq"] and panel["sound"] and panel["mode"] == "wave", str(panel))
    check("and offers no file and no lanes, and Tone and Mic as what the instrument draws", panel["others"], str(panel))
    p.evaluate("() => setView('scope')")

    # A note from the page's keys. Harmonic tone, keyboard present: gated, so silent until a note.
    p.evaluate("() => applyPreset('b:Harmonic tone')")
    p.wait_for_timeout(600)
    before = p.evaluate(PEAK, 4096)
    p.evaluate("() => midiNoteOn(57, 100)")
    p.wait_for_timeout(700)
    pitch, peak = p.evaluate(PITCH, 8192), p.evaluate(PEAK, 4096)
    check("a note played on the page is heard in the instrument at its pitch, after silence",
          before == 0 and abs(pitch - 220) < 0.5 and peak > 0.1, "before %g, %.2f Hz at %.3f" % (before, pitch, peak))
    check("and the pitch check fails against the semitone above", not abs(pitch - 233.08) < 0.5)
    skew = p.evaluate(SKEW, 4096)
    check("and the picture's left is left and right is right: the right a quarter-cycle on, as the website draws it",
          abs(skew - site_skew) < 0.03 and min(abs(skew - 0.25), abs(skew - 0.75)) < 0.03,
          "%.3f against the website's %.3f" % (skew, site_skew))
    check("and the comparison fails against the lanes the wrong way round", not abs((1 - skew) % 1 - site_skew) < 0.03)
    # A slider: the level halved on the page, the instrument's picture follows.
    p.evaluate("() => { el.amp.value = String(Number(el.amp.value) / 2); el.amp.dispatchEvent(new Event('input')); }")
    p.wait_for_timeout(600)
    halved = p.evaluate(PEAK, 4096)
    check("a slider moved on the page moves the instrument: the level halved, the picture half the height",
          abs(halved / peak - 0.5) < 0.03, "%.4f against %.4f, ratio %.3f" % (halved, peak, halved / peak))
    p.evaluate("() => midiNoteOff(57)")
    p.wait_for_timeout(2500)
    after = p.evaluate(PEAK, 2048)
    check("and the note let go is let go there too", after < 1e-4, "%g" % after)

    # A preset: the code the page sends is the setup the instrument loaded.
    sent = p.evaluate("""async () => {
      applyPreset('b:Harmonic tone');
      const other = encodeSetup(snapshot());
      applyPreset('b:Arpeggiated chords');
      const code = encodeSetup(snapshot());
      await new Promise((r) => setTimeout(r, 600));
      const s = await scopeHost.call('scopeState');
      const strip = (x) => { const y = Object.assign({}, x); delete y.cc; delete y.pluginHands; return JSON.stringify(y); };
      return { same: strip(decodeSetup(s.code)) === strip(decodeSetup(code)), arp: decodeSetup(s.code).arpMode,
               // The null: the same comparison against the preset loaded just before it.
               other: strip(decodeSetup(s.code)) === strip(decodeSetup(other)),
               version: s.version, seen: hostSync.seen };
    }""")
    check("a preset loaded on the page is the setup the instrument loaded, and not counted as the host's",
          sent["same"] and sent["arp"] == "up" and sent["version"] == sent["seen"], str(sent))
    check("and the comparison fails against the preset loaded just before it", sent["other"] is False)

    # MIDI out: the instrument's arpeggio, out of the page's port on the page's channel; the page's own brain silent.
    out = p.evaluate("""async () => {
      const log = [];
      midiOut.port = { send: (bytes) => log.push(Array.from(bytes)) };
      midiOut.channel = 3;
      midiNoteOn(60, 100); midiNoteOn(64, 100); midiNoteOn(67, 100);
      await new Promise((r) => setTimeout(r, 1200));
      // A note the arpeggio never plays: two octaves up from these three reaches 91 at most.
      const page = midiOutNote(100, 1, performance.now());
      midiNoteOff(60); midiNoteOff(64); midiNoteOff(67);
      await new Promise((r) => setTimeout(r, 300));
      midiOut.port = null;
      const ons = log.filter((m) => (m[0] & 0xf0) === 0x90 && m[2] > 0);
      return { ons: ons.length, channels: [...new Set(log.filter((m) => m[0] < 0xf0).map((m) => m[0] & 15))],
               notes: [...new Set(ons.map((m) => m[1]))].sort(), page, of100: log.some((m) => m[1] === 100) };
    }""")
    check("what the instrument sends to a MIDI port goes out of the page's port, on the page's channel",
          out["ons"] >= 4 and out["channels"] == [3] and set(out["notes"]) <= {60, 64, 67, 72, 76, 79} and len(out["notes"]) >= 2,
          str(out))
    check("and the page's own brain sends nothing beside it", out["page"] is False and not out["of100"], str(out))

    # The kind menu, through the page's own handler: the mirror, the panel, the view, and a hand sent.
    kind = p.evaluate("""async () => {
      applyPreset('b:Harmonic tone');
      await new Promise((r) => setTimeout(r, 300));
      el.genMode.value = 'figure'; el.genMode.dispatchEvent(new Event('change', { bubbles: true }));
      await new Promise((r) => setTimeout(r, 600));
      const s = await scopeHost.call('scopeState');
      const hands = decodeSetup(s.code).pluginHands || [];
      return { mode: genSettings().mode, rows: !el.figureRows.hidden, display: state.display,
               sent: hands.some((h) => h[0] === 'c' && h[1] === 'genMode' && h[2] === 'figure') };
    }""")
    check("the kind menu moves the page's generator and the instrument's: the figure's rows, X-Y, and the hand kept",
          kind == {"mode": "figure", "rows": True, "display": "xy", "sent": True}, str(kind))

    # A port's bytes, passed on once and not again as the notes the page makes of them.
    port = p.evaluate("""async () => {
      const passed = [], real = scopeHost.midi;
      scopeHost.midi = (bytes) => { passed.push(Array.from(bytes)); real(bytes); };
      applyPreset('b:Harmonic tone');
      midiBytes(new Uint8Array([0x90, 62, 90]));
      await new Promise((r) => setTimeout(r, 700));
      const pitch = (""" + PITCH + """)(8192);
      const held = midi.notes.map((n) => n.note);
      midiBytes(new Uint8Array([0x80, 62, 0]));
      midiNoteOn(50, 100); midiNoteOff(50);
      // The pedal from the screen and a panic, as the controllers they are.
      midiSetPedal(1); midiSetPedal(0); midiPanic();
      // And a port's pedal once, not again as the pedal the page makes of it.
      midiBytes(new Uint8Array([0xb0, 64, 127])); midiBytes(new Uint8Array([0xb0, 64, 0]));
      scopeHost.midi = real;
      return { passed, pitch, held };
    }""")
    check("a port's note reaches the instrument once, as it came, and the page's keys keep it too",
          port["passed"][:2] == [[0x90, 62, 90], [0x80, 62, 0]] and abs(port["pitch"] - 293.66) < 0.5 and port["held"] == [62],
          str(port))
    check("and a key on the screen is passed on as the note it is, once each way",
          port["passed"][2:4] == [[0x90, 50, 100], [0x80, 50, 0]], str(port["passed"]))
    check("and the pedal and a panic as the controllers they are, a port's pedal once",
          port["passed"][4:] == [[0xb0, 64, 127], [0xb0, 64, 0], [0xb0, 123, 0], [0xb0, 64, 127], [0xb0, 64, 0]],
          str(port["passed"][4:]))

    # The sound switch: the instrument plays either way; the switch opens its way out.
    sound = p.evaluate("""async () => {
      el.genSound.checked = true; el.genSound.dispatchEvent(new Event('change'));
      await new Promise((r) => setTimeout(r, 300));
      const on = [state.genSound, state.source.audible(), Math.round(state.source.gain * 100) / 100];
      el.genSound.checked = false; el.genSound.dispatchEvent(new Event('change'));
      await new Promise((r) => setTimeout(r, 300));
      return { on, off: [state.genSound, state.source.audible(), Math.round(state.source.gain * 100) / 100] };
    }""")
    check("the switch to hear it opens and closes the instrument's way out",
          sound == {"on": [True, True, 1], "off": [False, False, 0]}, str(sound))

    # The input (5g). In place of the microphone, a known pair: 441 Hz on the
    # left and 661.5 Hz on the right, from oscillators in a second context,
    # handed over where the page asks for a live stream.
    p.evaluate("""() => {
      const ctx2 = new AudioContext({ sampleRate: deviceRate() });
      const merge = ctx2.createChannelMerger(2), dest = ctx2.createMediaStreamDestination();
      dest.channelCount = 2;
      [[441, 0], [661.5, 1]].forEach(([hz, ch]) => {
        const o = ctx2.createOscillator(), g = ctx2.createGain();
        o.frequency.value = hz; g.gain.value = 0.5; o.connect(g).connect(merge, 0, ch); o.start();
      });
      merge.connect(dest);
      window.__fakeIn = { stream: dest.stream, opened: 0, released: 0 };
      window.openLiveStream = async () => { window.__fakeIn.opened++; return dest.stream; };
      window.releaseLiveStream = () => { window.__fakeIn.released++; };
    }""")
    p.evaluate("() => { applyPreset('b:Harmonic tone'); el.srcMic.click(); }")
    p.wait_for_timeout(1200)
    drawn = p.evaluate("""async () => {
      const pitchOf = (lane) => {
        const at = [];
        for (let k = 1; k < lane.length; k++) if (lane[k - 1] < 0 && lane[k] >= 0) at.push(k - 1 + lane[k - 1] / (lane[k - 1] - lane[k]));
        return at.length < 3 ? 0 : (at.length - 1) * state.source.sampleRate / (at[at.length - 1] - at[0]);
      };
      const [l, r] = state.source.getLatestWindow(8192);
      const s = await scopeHost.call('scopeState');
      return { left: pitchOf(l), right: pitchOf(r), connected: state.source.inputConnected, mic: el.srcMic.getAttribute('aria-checked'),
               state: decodeSetup(s.code).pluginInput === true, gain: Math.round(state.source.gain * 100) / 100,
               soundRow: el.genSoundRow.hidden, device: el.device.disabled, bands: el.micShapeRow.hidden,
               file: el.srcFile.disabled, opened: window.__fakeIn.opened };
    }""")
    check("Mic in ?brain=core: the instrument draws your input, left as left, and keeps that in its state",
          abs(drawn["left"] - 441) < 0.5 and abs(drawn["right"] - 661.5) < 0.5 and drawn["connected"] and drawn["mic"] == "true"
          and drawn["state"] and drawn["opened"] == 1, str(drawn))
    check("and the pitch check fails against the two lanes the other way round", not abs(drawn["right"] - 441) < 0.5)
    check("a microphone drawn is not heard, the generator's switch goes, and the device is the page's to choose; no band split, no file",
          drawn["gain"] == 0 and drawn["soundRow"] and not drawn["device"] and drawn["bands"] and drawn["file"], str(drawn))
    heard = p.evaluate("""async () => {
      const out = {};
      setLiveKind('line'); el.monitorLive.checked = true; el.monitorLive.dispatchEvent(new Event('change'));
      await new Promise((r) => setTimeout(r, 300));
      out.line = [state.monitorLive, Math.round(state.source.gain * 100) / 100];
      setLiveKind('mic');
      await new Promise((r) => setTimeout(r, 300));
      out.mic = [state.monitorLive, Math.round(state.source.gain * 100) / 100];
      // Through the plane: X folded onto its right half, so the left lane never goes below nought.
      el.planeMirror.value = '1'; el.planeMirror.dispatchEvent(new Event('change', { bubbles: true }));
      await new Promise((r) => setTimeout(r, 500));
      const [l] = state.source.getLatestWindow(4096);
      out.lowest = Math.min(...l);
      el.planeMirror.value = '0'; el.planeMirror.dispatchEvent(new Event('change', { bubbles: true }));
      await new Promise((r) => setTimeout(r, 500));
      out.lowestOff = Math.min(...state.source.getLatestWindow(4096)[0]);
      // Another device chosen: the stream let go and opened again from it.
      el.device.add(new Option('Another input', 'another'));
      el.device.value = 'another'; el.device.dispatchEvent(new Event('change'));
      await new Promise((r) => setTimeout(r, 500));
      out.reopened = [window.__fakeIn.opened, window.__fakeIn.released, state.source.kind, state.source.inputConnected];
      return out;
    }""")
    check("a line input asked to be heard is heard, and a microphone never", heard["line"] == [True, 1] and heard["mic"] == [False, 0],
          str(heard))
    check("another device chosen lets the stream go and opens it again from that device, the instrument still the source",
          heard["reopened"] == [2, 1, "host", True], str(heard["reopened"]))
    check("and the input goes through the instrument's plane: folded onto its right half, the left lane never below nought",
          heard["lowest"] > -0.01 and heard["lowestOff"] < -0.4, "%.3f folded, %.3f not" % (heard["lowest"], heard["lowestOff"]))
    back = p.evaluate("""async () => {
      el.srcTone.click();
      await new Promise((r) => setTimeout(r, 600));
      const s = await scopeHost.call('scopeState');
      return { draws: state.source.drawsInput, connected: state.source.inputConnected, released: window.__fakeIn.released,
               state: decodeSetup(s.code).pluginInput === undefined, tone: el.srcTone.getAttribute('aria-checked'),
               soundRow: el.genSoundRow.hidden };
    }""")
    check("Tone draws the generator again: the input let go, the switch to hear it back, and the state says nothing of an input",
          back == {"draws": False, "connected": False, "released": 2, "state": True, "tone": "true", "soundRow": False}, str(back))
    # The generator's live-input modes take the input in the instrument, heard or not.
    fm = p.evaluate("""async () => {
      el.inputMode.value = '1'; el.inputMode.dispatchEvent(new Event('change', { bubbles: true }));
      await new Promise((r) => setTimeout(r, 600));
      const out = { connected: state.source.inputConnected, wanted: genInputWanted(), where: el.inputWhere.textContent };
      el.inputMode.value = '0'; el.inputMode.dispatchEvent(new Event('change', { bubbles: true }));
      await new Promise((r) => setTimeout(r, 600));
      out.after = state.source.inputConnected;
      return out;
    }""")
    check("the generator's FM from the input takes your input in the instrument, unheard, and lets it go when the mode is off",
          fm["connected"] and fm["wanted"] and fm["after"] is False and fm["where"] == "Your input, into the generator.", str(fm))

    # A module that will not make: no instrument, and the page stays what it was.
    refused = p.evaluate("""async () => {
      const keep = window.wasmCore;
      window.wasmCore = () => new Uint8Array([0, 97, 115, 109, 9, 9, 9, 9]);
      try { const h = makeBrainHost(); return await h.call('scopeHost'); }
      finally { window.wasmCore = keep; }
    }""")
    check("a module that will not make is no instrument, and the page is told so", refused is None, str(refused))
    check("no page errors", not errors, "; ".join(errors[:3]))
    p.close()
    b.close()

    # Without autoplay: no blocks until a press, and the page says so.
    b = pw.chromium.launch(executable_path=CHROME)
    p, errors = opened(b, "?brain=core", 2000, close=False)
    waiting = p.evaluate("() => ({ chunks: state.source.chunks, credit: el.credit.textContent, seen: hostSync.seen })")
    p.mouse.click(700, 450)
    p.wait_for_timeout(800)
    pressed = p.evaluate("() => ({ chunks: state.source.chunks, credit: el.credit.textContent })")
    check("unpressed, the instrument has made itself and shown its state but plays no blocks, and says so",
          waiting["chunks"] == 0 and waiting["seen"] >= 1 and "press" in waiting["credit"], str(waiting))
    check("and the first press starts it", pressed["chunks"] > 0 and "press" not in pressed["credit"], str(pressed))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the page is the face of the instrument compiled, as it is the plugin's")
print("everything passes")
