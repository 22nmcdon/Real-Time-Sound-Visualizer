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
      others: ![el.srcTone, el.srcMic, el.srcFile, el.srcRack].some((b) => b.disabled) })""")
    check("and keeps the generator's panel, kind and frequency, and the switch to hear it",
          panel["kind"] and panel["freq"] and panel["sound"] and panel["mode"] == "wave", str(panel))
    check("and offers Tone, Mic, File and Lanes as what the instrument draws", panel["others"], str(panel))
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
    # Until 5j this asserted the Whole / Into bands row hidden: the band split was the page's alone.
    check("a microphone drawn is not heard, the generator's switch goes, the device is the page's to choose, and Whole or Into bands is offered",
          drawn["gain"] == 0 and drawn["soundRow"] and not drawn["device"] and not drawn["bands"] and drawn["file"] is False, str(drawn))
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
    # The live band split (5j): Into bands while the input is drawn. The pair
    # is 441 Hz and 661.5 Hz, both in the Low mid band: that lane carries the
    # most, the High mid some of 661.5 Hz through its gentle slope, and the
    # Low and the High next to nothing - which a split that copied the input
    # into four lanes, or put the bands in another order, cannot do.
    split = p.evaluate("""async () => {
      const out = {}, posted = [];
      const realPost = MessagePort.prototype.postMessage;
      MessagePort.prototype.postMessage = function (m, ...rest) {
        if (m && m.op === 'control') posted.push(m.id + '=' + m.value);
        return realPost.call(this, m, ...rest);
      };
      const rms = (lane) => Math.sqrt(lane.reduce((a, v) => a + v * v, 0) / lane.length);
      el.micBands.click();
      await new Promise((r) => setTimeout(r, 900));
      const s = await scopeHost.call('scopeState');
      out.split = [state.source.channels, state.source.lanes.map((l) => l.name).join(','), decodeSetup(s.code).pluginBands === true,
                   el.srcMic.getAttribute('aria-checked'), el.micBands.getAttribute('aria-checked'), Math.round(state.source.gain * 100) / 100];
      out.rms = state.source.getLatestWindow(8192).map(rms);
      state.source.lanes[2].solo = true; state.source.remix();
      await new Promise((r) => setTimeout(r, 0));
      out.posted = posted.slice();
      state.source.lanes[2].solo = false; state.source.remix();
      el.micWhole.click();
      await new Promise((r) => setTimeout(r, 900));
      const s2 = await scopeHost.call('scopeState');
      out.whole = [state.source.channels, state.source.lanes === undefined, decodeSetup(s2.code).pluginBands === undefined,
                   decodeSetup(s2.code).pluginInput === true];
      // Into bands chosen over the generator, then Mic: the input arrives split.
      el.srcTone.click();
      await new Promise((r) => setTimeout(r, 300));
      el.micBands.click();
      out.overTone = [state.source.channels, state.source.bands];
      el.srcMic.click();
      await new Promise((r) => setTimeout(r, 600));
      out.micSplit = [state.source.channels, state.source.bands, el.srcMic.getAttribute('aria-checked')];
      // A state from the instrument saying it splits, applied over the input whole: split here, and not a word back.
      el.micWhole.click();
      await new Promise((r) => setTimeout(r, 400));
      posted.length = 0;
      hostApply({ version: hostSync.seen + 1, code: encodeSetup(Object.assign(snapshot(), { pluginBands: true })) });
      out.quiet = [state.source.channels, state.micBands, posted.filter((m) => /^srcBands/.test(m))];
      el.micWhole.click();
      await new Promise((r) => setTimeout(r, 600));
      out.after = [state.source.channels, state.micBands];
      MessagePort.prototype.postMessage = realPost;
      return out;
    }""")
    r = split["rms"]
    check("Into bands in ?brain=core: the instrument splits your input into the four bands, in order, keeps it in its state, and is not heard",
          split["split"] == [4, "Low,Low mid,High mid,High", True, "true", "true", 0]
          and r[1] > 0.1 and r[1] > 1.3 * r[2] and r[1] > 5 * r[0] and r[1] > 5 * r[3], str(split))
    check("and the reading fails against the input copied into each lane", not (r[1] > 1.3 * r[1]))
    check("a band soloed is sent as the mix the instrument hears, and Whole is the input whole again",
          "srcBands=1" in split["posted"] and "laneMix=0,0,1,0" in split["posted"] and split["whole"] == [2, True, True, True],
          str(split["posted"]) + " " + str(split["whole"]))
    check("Into bands chosen over the generator waits for Mic, which then splits, and a state saying so is not sent back",
          split["overTone"] == [2, False] and split["micSplit"] == [4, True, "true"] and split["quiet"] == [4, True, []]
          and split["after"] == [2, False], str({k: split[k] for k in ("overTone", "micSplit", "quiet", "after")}))
    back = p.evaluate("""async () => {
      // Counted across the press: the checks before it open and let go the stream as they need to.
      const before = window.__fakeIn.released;
      el.srcTone.click();
      await new Promise((r) => setTimeout(r, 600));
      const s = await scopeHost.call('scopeState');
      return { draws: state.source.drawsInput, connected: state.source.inputConnected, released: window.__fakeIn.released - before,
               state: decodeSetup(s.code).pluginInput === undefined, tone: el.srcTone.getAttribute('aria-checked'),
               soundRow: el.genSoundRow.hidden };
    }""")
    check("Tone draws the generator again: the input let go, the switch to hear it back, and the state says nothing of an input",
          back == {"draws": False, "connected": False, "released": 1, "state": True, "tone": "true", "soundRow": False}, str(back))
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

    # A file (5h): the instrument's input, played in its context. A WAV made
    # here, 441 Hz on the left and 661.5 Hz on the right, two seconds long.
    WAV = """(seconds) => {
      const rate = 44100, n = Math.round(rate * seconds), data = new DataView(new ArrayBuffer(44 + n * 4));
      const str = (o, t) => { for (let i = 0; i < t.length; i++) data.setUint8(o + i, t.charCodeAt(i)); };
      str(0, 'RIFF'); data.setUint32(4, 36 + n * 4, true); str(8, 'WAVE'); str(12, 'fmt '); data.setUint32(16, 16, true);
      data.setUint16(20, 1, true); data.setUint16(22, 2, true); data.setUint32(24, rate, true); data.setUint32(28, rate * 4, true);
      data.setUint16(32, 4, true); data.setUint16(34, 16, true); str(36, 'data'); data.setUint32(40, n * 4, true);
      for (let k = 0; k < n; k++) {
        data.setInt16(44 + k * 4, Math.round(16000 * Math.sin(2 * Math.PI * 441 * k / rate)), true);
        data.setInt16(46 + k * 4, Math.round(16000 * Math.sin(2 * Math.PI * 661.5 * k / rate)), true);
      }
      return new File([data.buffer], 'two tones.wav', { type: 'audio/wav' });
    }"""
    played = p.evaluate("""async (src) => {
      const pitchOf = (lane) => {
        const at = [];
        for (let k = 1; k < lane.length; k++) if (lane[k - 1] < 0 && lane[k] >= 0) at.push(k - 1 + lane[k - 1] / (lane[k - 1] - lane[k]));
        return at.length < 3 ? 0 : (at.length - 1) * state.source.sampleRate / (at[at.length - 1] - at[0]);
      };
      // From the generator: the file has to tell the instrument to draw its input.
      el.srcTone.click();
      await new Promise((r) => setTimeout(r, 400));
      el.fileLoop.checked = true;
      await toFile(eval(src)(2));
      await new Promise((r) => setTimeout(r, 900));
      const [l, r] = state.source.getLatestWindow(8192);
      const s = await scopeHost.call('scopeState');
      const out = { left: pitchOf(l), right: pitchOf(r), peak: Math.max(...l.map(Math.abs)), gain: Math.round(state.source.gain * 100) / 100,
                    file: el.srcFile.getAttribute('aria-checked'),
                    rows: el.fileRows.hidden, state: decodeSetup(s.code).pluginInput === true, credit: el.credit.textContent };
      el.filePlay.click();
      await new Promise((r) => setTimeout(r, 400));
      out.paused = [state.source.playing, el.filePlay.textContent, Math.max(...state.source.getLatestWindow(2048)[0].map(Math.abs))];
      state.source.seek(1.5);
      out.seeked = Math.round(state.source.at * 100) / 100;
      el.filePlay.click();
      await new Promise((r) => setTimeout(r, 900));
      // Looping: past the end of two seconds and back round, still playing.
      out.looped = [state.source.playing, state.source.at < 1.5];
      // A state from the instrument saying the input is drawn, which it is: the file plays on.
      const now = await scopeHost.call('scopeState');
      hostApply({ version: hostSync.seen + 1, code: now.code });
      await new Promise((r) => setTimeout(r, 200));
      out.kept = [!!state.source.file, state.source.playing];
      el.srcTone.click();
      await new Promise((r) => setTimeout(r, 400));
      out.tone = [state.source.file, state.source.drawsInput, el.fileRows.hidden];
      // Drawing the microphone's stream: a file chosen lets the stream go.
      el.srcMic.click();
      await new Promise((r) => setTimeout(r, 500));
      out.streamBefore = state.source.inputConnected;
      await toFile(eval(src)(2));
      await new Promise((r) => setTimeout(r, 500));
      out.streamAfter = state.source.inputConnected;
      el.srcTone.click();
      await new Promise((r) => setTimeout(r, 300));
      return out;
    }""", WAV)
    check("a file in ?brain=core is the instrument's input: drawn at its pitches, left as left, heard, and the stream let go",
          abs(played["left"] - 441) < 0.5 and abs(played["right"] - 661.5) < 0.5 and played["gain"] == 1 and played["streamBefore"]
          and played["streamAfter"] is False and played["state"] and played["file"] == "true" and played["rows"] is False
          and "two tones.wav" in played["credit"], str(played))
    check("and the pitch check fails against the two lanes the other way round", not abs(played["left"] - 661.5) < 0.5)
    check("its transport: paused it is silent, it seeks, and looping it goes round past its end",
          played["paused"][0] is False and played["paused"][1] == "Play" and played["paused"][2] == 0
          and played["seeked"] == 1.5 and played["looped"] == [True, True], str(played))
    check("and a state from the instrument saying what is already so leaves it playing", played["kept"] == [True, True], str(played["kept"]))
    check("and Tone lets the file go", played["tone"] == [None, False, True], str(played["tone"]))

    # A rack (5i): the instrument's lanes. Two mono stems made here, 441 Hz and
    # 661.5 Hz, and the generator's lane first, with a note held in it.
    MONO = """(hz, name) => {
      const rate = 44100, n = rate * 2, data = new DataView(new ArrayBuffer(44 + n * 2));
      const str = (o, t) => { for (let i = 0; i < t.length; i++) data.setUint8(o + i, t.charCodeAt(i)); };
      str(0, 'RIFF'); data.setUint32(4, 36 + n * 2, true); str(8, 'WAVE'); str(12, 'fmt '); data.setUint32(16, 16, true);
      data.setUint16(20, 1, true); data.setUint16(22, 1, true); data.setUint32(24, rate, true); data.setUint32(28, rate * 2, true);
      data.setUint16(32, 2, true); data.setUint16(34, 16, true); str(36, 'data'); data.setUint32(40, n * 2, true);
      for (let k = 0; k < n; k++) data.setInt16(44 + k * 2, Math.round(16000 * Math.sin(2 * Math.PI * hz * k / rate)), true);
      return new File([data.buffer], name, { type: 'audio/wav' });
    }"""
    rack = p.evaluate("""async (src) => {
      const make = eval(src);
      const pitchOf = (lane) => {
        const at = [];
        for (let k = 1; k < lane.length; k++) if (lane[k - 1] < 0 && lane[k] >= 0) at.push(k - 1 + lane[k - 1] / (lane[k - 1] - lane[k]));
        return at.length < 3 ? 0 : Math.round((at.length - 1) * state.source.sampleRate / (at[at.length - 1] - at[0]) * 10) / 10;
      };
      const out = {};
      applyPreset('b:Harmonic tone');
      el.srcRack.click();
      state.rackSynth = true; el.rackSynth.checked = true;
      state.rackLive = false; el.rackLive.checked = false;
      midiNoteOn(57, 100);
      // The pair turned round first, so that a rack starting it again at the first two lanes is seen to.
      el.xyX.value = '1'; el.xyX.dispatchEvent(new Event('change', { bubbles: true }));
      out.turned = state.xyPair.join(',');
      await toRack([make(441, 'a.wav'), make(661.5, 'b.wav')]);
      await new Promise((r) => setTimeout(r, 1200));
      out.names = state.source.lanes.map((lane) => lane.name);
      out.drawn = [state.source.kind, state.source.channels, laneCount(), el.srcRack.getAttribute('aria-checked'), state.stack];
      out.pitches = state.source.getLatestWindow(8192).map(pitchOf);
      const hands = decodeSetup((await scopeHost.call('scopeState')).code).pluginHands || [];
      const told = (id) => (hands.filter((h) => h[0] === 'c' && h[1] === id).pop() || [])[2];
      out.fitted = [state.channels.length, el.xyX.options.length, state.xyPair.join(','), told('xyX'), told('xyY')];
      /* A lane the rack has and the worklet has not posted yet reads as
         silence, not as whatever the ring last held there: three lanes of
         0.5 and then two of 0.25, in one go so nothing comes between, read
         over both - a window of the last two alone would find nothing stale
         in a ring that has not yet come round. */
      const level = (v) => new Float32Array(512).fill(v);
      state.source.absorb([level(0.5), level(0.5), level(0.5)]);
      state.source.absorb([level(0.25), level(0.25)]);
      const unposted = state.source.getLatestWindow(1024);
      out.unposted = [unposted.length, unposted[0][0], unposted[0][1023], Math.max(...unposted[2].map(Math.abs))];
      out.stemsHeard = [state.source.lanes[1].gain.gain.value, state.source.lanes[2].gain.gain.value];
      // The generator's lane is heard through the instrument, as its switch and the mixer say.
      el.genSound.checked = true; el.genSound.dispatchEvent(new Event('change'));
      await new Promise((r) => setTimeout(r, 300));
      out.genHeard = Math.round(state.source.gain * 100) / 100;
      state.source.lanes[0].mute = true; state.source.remix();
      await new Promise((r) => setTimeout(r, 300));
      out.genMuted = Math.round(state.source.gain * 100) / 100;
      state.source.lanes[0].mute = false; state.source.remix();
      el.genSound.checked = false; el.genSound.dispatchEvent(new Event('change'));
      // The trigger on the second stem reaches the instrument as a hand.
      document.getElementById('trigSource2').click();
      await new Promise((r) => setTimeout(r, 300));
      const s = await scopeHost.call('scopeState');
      out.trig = (decodeSetup(s.code).pluginHands || []).some((h) => h[0] === 'k' && h[1] === 'trigSource2');
      // Paused, the stems' lanes go quiet and the generator's draws on.
      el.filePlay.click();
      await new Promise((r) => setTimeout(r, 500));
      const w = state.source.getLatestWindow(2048);
      out.paused = [state.source.playing, Math.max(...w[1].map(Math.abs)), Math.max(...w[0].map(Math.abs)) > 0.1];
      out.align = [el.alignRow.hidden];
      // Playing along - a stem and you - keeps no alignment row: the instrument does not read the page's lanes.
      state.rackSynth = false; el.rackSynth.checked = false;
      state.rackLive = true; el.rackLive.checked = true;
      await toRack([make(441, 'a.wav')]);
      await new Promise((r) => setTimeout(r, 500));
      out.along = [state.source.lanes.map((lane) => lane.name).join(','), state.source.hasLive, el.alignRow.hidden];
      state.rackLive = false; el.rackLive.checked = false;
      // Tone leaves the rack, and the instrument plays on: the rack's stop is not its context's.
      const left = state.source.rack;
      el.srcTone.click();
      await new Promise((r) => setTimeout(r, 600));
      out.tone = [state.source.rack, state.source.channels, el.srcTone.getAttribute('aria-checked'), left.playing];
      const before = state.source.chunks;
      await new Promise((r) => setTimeout(r, 400));
      out.alive = state.source.chunks > before;
      midiNoteOff(57);
      return out;
    }""", MONO)
    check("Lanes in ?brain=core: the instrument draws the rack, the generator's lane its own and each stem at its pitch",
          rack["names"] == ["Generator", "a", "b"] and rack["drawn"] == ["host", 3, 3, "true", True]
          and abs(rack["pitches"][0] - 220) < 0.5 and abs(rack["pitches"][1] - 441) < 0.5 and abs(rack["pitches"][2] - 661.5) < 0.5,
          str(rack))
    check("and the pitch check fails against the stems the other way round", not abs(rack["pitches"][1] - 661.5) < 0.5)
    check("the stems are heard through the page's mixer, the generator's lane through the instrument as the mixer and its switch say",
          rack["stemsHeard"] == [1, 1] and rack["genHeard"] == 1 and rack["genMuted"] == 0, str(rack))
    check("the trigger's lane reaches the instrument; paused, the stems go quiet while the generator draws on; no alignment",
          rack["trig"] and rack["paused"] == [False, 0, True] and rack["align"] == [True], str(rack))
    check("Tone leaves the rack for the generator's pair and stops its stems, and the instrument plays on",
          rack["tone"] == [None, 2, "true", False] and rack["alive"], str(rack))
    check("a rack fits the lanes - three rows, three lanes for the pair - and starts the pair again at the first two, the instrument told",
          rack["turned"] == "1,0" and rack["fitted"] == [3, 3, "0,1", "0", "1"], str(rack["turned"]) + " " + str(rack["fitted"]))
    check("a lane the rack has and the worklet has not posted reads as silence, not as what the ring held there",
          rack["unposted"] == [3, 0.5, 0.25, 0], str(rack["unposted"]))
    check("playing along - a stem and you - keeps no alignment row", rack["along"] == ["a,You", True, True], str(rack["along"]))

    # A file split into bands (5j): 60 Hz and 2 kHz together, mono, so the
    # Low lane is the one and the High mid the other, each clean enough to
    # read its pitch through the other's slope. Heard, as the page's file
    # split is; a band soloed sent as the mix; Tone lets it go.
    filesplit = p.evaluate("""async () => {
      const rate = 48000, n = rate * 2, data = new DataView(new ArrayBuffer(44 + n * 2));
      const str = (o, t) => { for (let i = 0; i < t.length; i++) data.setUint8(o + i, t.charCodeAt(i)); };
      str(0, 'RIFF'); data.setUint32(4, 36 + n * 2, true); str(8, 'WAVE'); str(12, 'fmt '); data.setUint32(16, 16, true);
      data.setUint16(20, 1, true); data.setUint16(22, 1, true); data.setUint32(24, rate, true); data.setUint32(28, rate * 2, true);
      data.setUint16(32, 2, true); data.setUint16(34, 16, true); str(36, 'data'); data.setUint32(40, n * 2, true);
      for (let k = 0; k < n; k++) data.setInt16(44 + k * 2, Math.round(9000 * Math.sin(2 * Math.PI * 60 * k / rate) + 9000 * Math.sin(2 * Math.PI * 2000 * k / rate)), true);
      const file = new File([data.buffer], 'duo.wav', { type: 'audio/wav' });
      const pitchOf = (lane) => {
        const at = [];
        for (let k = 1; k < lane.length; k++) if (lane[k - 1] < 0 && lane[k] >= 0) at.push(k - 1 + lane[k - 1] / (lane[k - 1] - lane[k]));
        return at.length < 3 ? 0 : Math.round((at.length - 1) * state.source.sampleRate / (at[at.length - 1] - at[0]));
      };
      const out = {}, posted = [];
      const realPost = MessagePort.prototype.postMessage;
      MessagePort.prototype.postMessage = function (m, ...rest) {
        if (m && m.op === 'control') posted.push(m.id + '=' + m.value);
        return realPost.call(this, m, ...rest);
      };
      await toBands(file);
      await new Promise((r) => setTimeout(r, 1200));
      const s = await scopeHost.call('scopeState');
      out.drawn = [state.source.kind, el.srcRack.getAttribute('aria-checked'), state.source.channels, state.source.lanes.map((l) => l.name).join(','),
                   el.laneGroup.dataset.off === undefined, Math.round(state.source.gain * 100) / 100, state.source.playing,
                   decodeSetup(s.code).pluginBands === true, /^Add files/.test(el.rackNote.textContent)];
      out.pitches = state.source.getLatestWindow(16384).map(pitchOf);
      out.removable = document.querySelectorAll('[data-act="remove"]').length;
      state.source.lanes[0].solo = true; state.source.remix();
      await new Promise((r) => setTimeout(r, 0));
      out.posted = posted.slice();
      state.source.lanes[0].solo = false; state.source.remix();
      el.srcTone.click();
      await new Promise((r) => setTimeout(r, 600));
      const s2 = await scopeHost.call('scopeState');
      out.tone = [state.source.channels, state.source.file, decodeSetup(s2.code).pluginBands === undefined, el.srcTone.getAttribute('aria-checked')];
      /* Tone pressed while a file split, or a file, is still decoding: the
         file is let go when it has decoded, not played over the generator. */
      toBands(file);
      el.srcTone.click();
      await new Promise((r) => setTimeout(r, 1500));
      out.raceSplit = [state.source.channels, state.source.file, state.source.bands, el.srcTone.getAttribute('aria-checked')];
      toFile(file);
      el.srcTone.click();
      await new Promise((r) => setTimeout(r, 1500));
      out.raceFile = [state.source.file, state.source.drawsInput, el.srcTone.getAttribute('aria-checked')];
      toBands(file);
      el.srcMic.click();
      await new Promise((r) => setTimeout(r, 1500));
      out.raceMic = [state.source.file, state.source.bands, state.source.drawsInput, el.srcMic.getAttribute('aria-checked')];
      el.srcTone.click();
      await new Promise((r) => setTimeout(r, 300));
      MessagePort.prototype.postMessage = realPost;
      return out;
    }""")
    check("a file split into bands in ?brain=core: the instrument draws its four bands, each at its pitch, heard, and keeps the split in its state",
          filesplit["drawn"] == ["host", "true", 4, "Low,Low mid,High mid,High", True, 1, True, True, True]
          and abs(filesplit["pitches"][0] - 60) <= 1 and abs(filesplit["pitches"][2] - 2000) <= 2, str(filesplit))
    check("and the pitch check fails against the bands one place along", not abs(filesplit["pitches"][1] - 60) <= 1)
    check("a band of the file soloed is sent as the mix, and Tone lets the file and the split go",
          "srcBands=1" in filesplit["posted"] and "laneMix=1,0,0,0" in filesplit["posted"]
          and filesplit["tone"] == [2, None, True, "true"], str(filesplit["posted"]) + " " + str(filesplit["tone"]))
    check("a band split's lanes cannot be taken out one by one, being one file through a crossover",
          filesplit["removable"] == 0, str(filesplit["removable"]))
    check("Tone pressed while a file split or a file is still decoding lets it go once decoded, rather than playing it over the generator",
          filesplit["raceSplit"] == [2, None, False, "true"] and filesplit["raceFile"] == [None, False, "true"]
          and filesplit["raceMic"][0] is None and filesplit["raceMic"][2] is True and filesplit["raceMic"][3] == "true",
          str(filesplit["raceSplit"]) + " " + str(filesplit["raceFile"]) + " " + str(filesplit["raceMic"]))

    # The instrument's split against the browser's own (5j): the page's BANDS
    # through BiquadFilterNodes set as buildBands sets them, rendered offline,
    # and the compiled instrument fed the same stereo signal a block at a
    # time - noise on the left, a tone and noise on the right, so every band
    # has something in it and the two channels differ. Each lane the band of
    # the two halved together, and what is heard the bands at the mix's gains.
    wa = p.evaluate("""async () => {
      const rate = 48000, n = 128, blocks = 60, frames = n * blocks;
      let seed = 12345;
      const rnd = () => ((seed = (Math.imul(seed, 1103515245) + 12345) >>> 0) / 4294967296) * 2 - 1;
      const L = new Float32Array(frames), R = new Float32Array(frames);
      for (let k = 0; k < frames; k++) { L[k] = 0.4 * rnd(); R[k] = 0.3 * Math.sin(2 * Math.PI * 300 * k / rate) + 0.2 * rnd(); }
      const gains = [0.5, 1, 0.25, 2];
      const brain = makeWasmBrain(new WebAssembly.Module(wasmCore()), rate, n, encodeSetup(snapshot()));
      brain.control('srcBands', '1');
      brain.control('laneMix', gains.join(','));
      const heardL = new Float32Array(n), heardR = new Float32Array(n), pictures = [0, 1, 2, 3, 4, 5].map(() => new Float32Array(n));
      const lanes = [0, 1, 2, 3].map(() => new Float32Array(frames)), hl = new Float32Array(frames), hr = new Float32Array(frames);
      for (let b = 0; b < blocks; b++) {
        brain.block(n, heardL, heardR, pictures, [L.subarray(b * n, (b + 1) * n), R.subarray(b * n, (b + 1) * n)]);
        for (let c = 0; c < 4; c++) lanes[c].set(pictures[c], b * n);
        hl.set(heardL, b * n); hr.set(heardR, b * n);
      }
      const off = new OfflineAudioContext(8, frames, rate);
      const buffer = off.createBuffer(2, frames, rate);
      buffer.copyToChannel(L, 0); buffer.copyToChannel(R, 1);
      const src = off.createBufferSource(); src.buffer = buffer;
      const merge = off.createChannelMerger(8);
      BANDS.forEach((band, i) => {
        const chain = [];
        if (band.from > 0) { const f = off.createBiquadFilter(); f.type = 'highpass'; f.frequency.value = band.from; f.Q.value = BUTTERWORTH_Q_DB; chain.push(f); }
        if (band.to > 0) { const f = off.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = band.to; f.Q.value = BUTTERWORTH_Q_DB; chain.push(f); }
        src.connect(chain[0]);
        for (let j = 0; j < chain.length - 1; j++) chain[j].connect(chain[j + 1]);
        const split = off.createChannelSplitter(2);
        chain[chain.length - 1].connect(split);
        split.connect(merge, 0, 2 * i); split.connect(merge, 1, 2 * i + 1);
      });
      merge.connect(off.destination);
      src.start();
      const rendered = await off.startRendering();
      const band = (i, ch) => rendered.getChannelData(2 * i + ch);
      let lanesOff = 0, heardOff = 0, along = Infinity, energy = 0;
      for (let k = 0; k < frames; k++) {
        let sl = 0, sr = 0;
        for (let i = 0; i < 4; i++) {
          const want = Math.fround((band(i, 0)[k] + band(i, 1)[k]) * 0.5);
          lanesOff = Math.max(lanesOff, Math.abs(lanes[i][k] - want));
          energy = Math.max(energy, Math.abs(want));
          sl += gains[i] * band(i, 0)[k]; sr += gains[i] * band(i, 1)[k];
        }
        heardOff = Math.max(heardOff, Math.abs(hl[k] - Math.fround(sl)), Math.abs(hr[k] - Math.fround(sr)));
      }
      // The null: the instrument's Low lane against the browser's Low mid.
      along = 0;
      for (let k = 0; k < frames; k++) along = Math.max(along, Math.abs(lanes[0][k] - Math.fround((band(1, 0)[k] + band(1, 1)[k]) * 0.5)));
      return { lanesOff, heardOff, along, energy };
    }""")
    check("the instrument's band split is the browser's own crossovers: each lane and what is heard, sample for sample",
          wa["lanesOff"] == 0 and wa["heardOff"] == 0 and wa["energy"] > 0.1, str(wa))
    check("and the comparison fails against the bands one place along", wa["along"] > 0.01, str(wa["along"]))

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
