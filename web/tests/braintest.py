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
- and in a browser that has not been pressed yet, the worklet runs no
  blocks and says so, the same instrument draws on the page's thread
  meanwhile and takes the page's hands, and the first press starts the
  worklet, which has had those hands too.
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
    # The picture stage out: this suite holds the instrument's plumbing, and
    # the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(PAGE + query + ("&" if "?" in query else "?") + "picture=0")
    p.wait_for_timeout(settle)
    # Closing the help sheet is a press, so a check on an unpressed page leaves it open.
    if close and p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    return p, errors

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    # The way back (5m made the instrument the default): ?brain=js, or the
    # compiled core turned off, is the page's own brain on its own generator.
    for query, want in (("?brain=js", "tone"), ("?brain=core&core=js", "tone")):
        p, _ = opened(b, query, 1200)
        got = p.evaluate("() => ({ kind: state.source.kind, host: !!scopeHost, brain: BRAIN_IN_CORE, mic: el.srcMic.disabled })")
        if query == "?brain=js":
            # The website's own picture of a note, for the instrument's to be held to below.
            p.evaluate("() => { applyPreset('b:Harmonic tone'); midiNoteOn(57, 100); }")
            p.wait_for_timeout(600)
            site_skew = p.evaluate(SKEW, 4096)
        check("with %s the page is on its own brain and its own generator, its other sources offered" % query,
              got["kind"] == want and not got["host"] and not got["brain"] and got["mic"] is False, str(got))
        p.close()
    # ?brain=core, the switch before the instrument was the default, still asks for it.
    p, _ = opened(b, "?brain=core", 1200)
    check("and ?brain=core, the old switch, is the instrument", p.evaluate("() => BRAIN_IN_CORE && state.source.kind === 'host'"))
    p.close()

    # Heard on a page nobody has pressed (P4): the instrument is asked for its
    # sound as it arrives. A press asks again, which would hide a page that
    # never asked - this suite closes the help sheet, and that is a press.
    # The null is the same page hushed by hand, which reads silent.
    p, _ = opened(b, "", 2500, close=False)
    unpressed = p.evaluate("""async () => {
      const read = () => [state.genSound, state.source.audible(), Math.round(state.source.gain * 100) / 100];
      const on = read();
      { const v = genVoice(); if (v) await v.setSound(false); syncGeneratorSound(); }
      await new Promise((r) => setTimeout(r, 300));
      return { kind: state.source.kind, on, off: read() };
    }""")
    check("the instrument is heard on a page nobody has pressed",
          unpressed["kind"] == "host" and unpressed["on"] == [True, True, 1], str(unpressed))
    check("and the reading there can say otherwise", unpressed["off"] == [False, False, 0], str(unpressed))
    p.close()

    # With no switch at all: the site, which since 5m is the instrument.
    p, errors = opened(b, "")
    first = p.evaluate("""async () => ({ kind: state.source.kind, mark: el.sourceMark.textContent, on: hostSync.on,
      seen: hostSync.seen, chunks: state.source.chunks, rate: state.source.sampleRate, ctxRate: deviceRate(),
      timebase: decodeSetup((await scopeHost.call('scopeState')).code).timebase })""")
    p.wait_for_timeout(500)
    later = p.evaluate("() => state.source.chunks")
    check("with no switch the page draws the instrument in the worklet, and the instrument is playing, its head saying what it plays",
          first["kind"] == "host" and first["mark"] == "Test tone" and first["on"] and later > first["chunks"] > 0,
          "%s, %d chunks half a second later" % (first, later))
    check("and the page shows the instrument's state, put on it as the plugin's is", first["seen"] >= 1, str(first["seen"]))
    # The page opens on Harmonic tone, whose timebase is 3 where the default's is 4.
    check("and the instrument was made on the setup the page opened on, not on the defaults",
          first["timebase"] == 3, str(first["timebase"]))
    p.evaluate("() => setView('bench')")
    p.wait_for_timeout(300)
    panel = p.evaluate("""() => ({ kind: el.genMode.offsetParent !== null, freq: el.freq ? el.freq.offsetParent !== null : null,
      sound: !!genVoice(), mode: genSettings() && genSettings().mode,
      others: ![el.srcTone, el.srcMic].some((b) => b.disabled) })""")
    check("and keeps the generator's panel, kind and frequency, and its voice",
          panel["kind"] and panel["freq"] and panel["sound"] and panel["mode"] == "wave", str(panel))
    check("and offers Tone and Mic as what the instrument draws", panel["others"], str(panel))
    p.evaluate("() => setView('scope')")

    # No keyboard - no port, the screen's keys shut - and nothing played: the
    # instrument draws its generator, as the website opens. It used to open
    # gated, as the plugin does, which was a blank screen until a note.
    unkeyed = p.evaluate("() => ({ present: keyboardPresent() })")
    free = p.evaluate(PEAK, 4096)
    check("with no keyboard and nothing played the instrument draws its generator, as the website opens",
          unkeyed["present"] is False and free > 0.1, "keyboard %s, peak %.3f" % (unkeyed["present"], free))
    # A note from the page's keys. Harmonic tone, the screen's keys open: gated, so
    # silent until a note. They stay open, so the rest is played on a keyboard.
    p.evaluate("() => { setScreenKeys(true); applyPreset('b:Harmonic tone'); }")
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

    # Always heard (P4): nothing here asks for the sound, and the way out is
    # open. Before P4 this ticked a switch, and asserted it opened and shut
    # the way out. Hushed by hand - the state before the browser lets sound
    # start - the reading is seen to be false, and a press asks again.
    sound = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const read = () => [state.genSound, state.source.audible(), Math.round(state.source.gain * 100) / 100];
      await wait(300);
      const on = read();
      { const v = genVoice(); if (v) await v.setSound(false); syncGeneratorSound(); }
      await wait(300);
      const off = read();
      window.dispatchEvent(new PointerEvent('pointerdown'));
      await wait(300);
      return { on, off, back: read(), row: !!document.getElementById('genSound') };
    }""")
    check("the instrument is heard without being asked: its way out is open",
          sound["on"] == [True, True, 1], str(sound))
    check("and the reading can say otherwise: hushed, it is shut", sound["off"] == [False, False, 0], str(sound))
    check("and a press anywhere opens it again, and there is no switch for it", sound["back"] == [True, True, 1]
          and not sound["row"], str(sound))

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
               soundRow: !genVoice(), device: el.device.disabled, bands: el.micShapeRow.hidden,
               opened: window.__fakeIn.opened };
    }""")
    check("Mic in ?brain=core: the instrument draws your input, left as left, and keeps that in its state",
          abs(drawn["left"] - 441) < 0.5 and abs(drawn["right"] - 661.5) < 0.5 and drawn["connected"] and drawn["mic"] == "true"
          and drawn["state"] and drawn["opened"] == 1, str(drawn))
    check("and the pitch check fails against the two lanes the other way round", not abs(drawn["right"] - 441) < 0.5)
    # Until 5j this asserted the Whole / Into bands row hidden: the band split was the page's alone.
    check("a microphone drawn is not heard, the generator's switch goes, the device is the page's to choose, and Whole or Into bands is offered",
          drawn["gain"] == 0 and drawn["soundRow"] and not drawn["device"] and not drawn["bands"], str(drawn))
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
               soundRow: !genVoice() };
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

    # A file (5h), a rack (5i) and a file split into bands (5j) were the
    # instrument's input here, its lanes and its bands, until P5 cut file
    # playback and the rack. The band split of a live input is above.

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

    # What became of the page's own features once the instrument was the
    # default (5m): each was there with the page's brain, and each was found
    # missing by running the whole suite with the instrument the default.
    print("\n--- the default, as it is seen ---")
    p, errors = opened(b, "")
    seen = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const out = { credit: el.credit.textContent };
      // Two layers, played and edited: the A and B buttons, B's drawbars written to B, a figure each.
      setScreenKeys(true); el.midiPoly.click();
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(50);
      el.midiEditB.click(); await wait(50);
      out.titleB = el.barsTitle.textContent;
      el.shape.value = 'drawbars'; el.shape.dispatchEvent(new Event('change'));
      el.bars.value = '800000000'; el.bar0.dispatchEvent(new Event('input'));
      out.bars = [genSettings(0).bars.join(''), genSettings(1).bars.join('')];
      el.midiEditA.click(); await wait(50);
      midiNoteOn(48, 100); midiNoteOn(72, 100); await wait(700);
      const w = state.source.getLatestWindow(8192);
      out.figures = sourceFigures();
      out.hz = w.map((lane) => estimateFrequency(lane, state.source.sampleRate));
      out.names = [0, 1, 2, 3].map(laneName);
      // The generator's readings: its envelope as a source, while a note is held.
      out.envelope = MOD_SOURCES.get('env.note').value();
      midiNoteOff(48); midiNoteOff(72);
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(1500);
      out.envelopeAfter = MOD_SOURCES.get('env.note').value();
      // The fade's dot follows a note's envelope.
      restore({ midiMode: 'poly', mod: 'midi.key>gen.drive@0.500' }); await wait(200);
      setFade('both'); setFadeEnvelope({ delay: 0.4, attack: 0.3, decay: 0.4, sustain: 1, release: 0.5 }); await wait(100);
      fade.editing = 0;
      const stage = () => (fade.last[0] && fade.last[0].gate ? gatePhase(fade.last[0].gate, performance.now()).stage : null);
      midiNoteOn(60, 127); await wait(250); out.inWait = stage();
      await wait(500); out.later = stage(); midiNoteOff(60);
      out.dot = envParts.dot.getAttribute('visibility');
      return out;
    }""")
    print("    %s" % seen)
    check("the line under the title names what the generator plays, as the page's own does", seen["credit"] == "220 Hz, unison just",
          seen["credit"])
    check("with the layers on, the panel edits B and writes B's drawbars, leaving A's",
          seen["titleB"] == "Drawbars \u00b7 layer B" and seen["bars"][1] == "800000000" and seen["bars"][0] != "800000000",
          "%s, %s" % (seen["titleB"], seen["bars"]))
    def layered(hz, a, b):
        return all(h is not None and abs(h - want) < 1 for h, want in zip(hz, (a, a, b, b)))
    check("and the instrument draws a figure each, A's at C3 and B's at C5 on its 16' bar, named so",
          seen["figures"] == [[0, 1], [2, 3]] and layered(seen["hz"], 130.81, 261.63)
          and seen["names"] == ["A \u00b7 X", "A \u00b7 Y", "B \u00b7 X", "B \u00b7 Y"], "%s %s" % (seen["hz"], seen["names"]))
    check("and the reading fails with the figures the other way round", not layered(seen["hz"], 261.63, 130.81))
    check("the generator's envelope is a source the page can read: up while a note is held, back down after",
          seen["envelope"] > 0.3 and seen["envelopeAfter"] < 0.01, "%.3f then %.3f" % (seen["envelope"], seen["envelopeAfter"]))
    check("the fade's dot follows a note: in the wait, then past it", seen["inWait"] == "delay" and seen["later"] in ("decay", "sustain")
          and seen["dot"] == "visible", str(seen))
    # What a suite on ?brain=js checks of the page's own brain, held here for
    # the instrument where it is something seen: a controller on the
    # frequency moves the pitch (miditest), and the readout says why a gated
    # screen is empty (envtest). The crossings' count climbing beside its
    # switch was held here too, until P5 cut the crossings.
    more = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const hz = () => estimateFrequency(state.source.getLatestWindow(8192)[0], state.source.sampleRate);
      const out = {};
      setFade('off'); restore({}); setScreenKeys(false); await wait(200);
      el.freq.value = '220'; el.freq.dispatchEvent(new Event('input'));
      midiBytes(Uint8Array.from([0xB0, 16, 0])); await wait(100);
      state.modRoutings = [{ sourceId: 'cc.16', destId: 'gen.freq', amount: 1 }]; touchRoutings();
      await wait(400); out.low = hz();
      midiBytes(Uint8Array.from([0xB0, 16, 127])); await wait(500); out.high = hz();
      state.modRoutings = []; touchRoutings();
      // The screen's keys open and nothing held: the waveform is gated, and the readout says why it is empty.
      applyPreset('b:Harmonic tone'); setScreenKeys(true); await wait(600);
      out.gated = el.readoutDetail.textContent;
      setScreenKeys(false); await wait(400);
      out.free = el.readoutDetail.textContent;
      return out;
    }""")
    check("a controller routed to the frequency moves the instrument's pitch: an octave at full", abs(more["low"] - 220) < 0.5
          and abs(more["high"] - 440) < 1, "%s then %s" % (more["low"], more["high"]))
    check("and the reading fails against the pitch it started at", not abs(more["low"] - 440) < 1)
    check("and the readout says why a gated screen is empty, and stops once nothing gates it",
          "gated \u00b7 no note held" in more["gated"] and "gated" not in more["free"], str(more))
    # A split kept and not applied while the input is drawn, the panel saying
    # why (layertest's). It was a rack holding the generator until P5. The crossings' lines drawn over the instrument's
    # generator were read here too, until P5 cut them.
    lines = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setScreenKeys(false); applyPreset('b:Harmonic tone'); await wait(300);
      setView('scope');
      // The keyboard split, on the generator and then with the input drawn:
      // a stream of one oscillator handed over where the page asks for a live
      // one, as above, since this page is not the one that had it.
      const ctx2 = new AudioContext({ sampleRate: deviceRate() });
      const osc = ctx2.createOscillator(), dest = ctx2.createMediaStreamDestination();
      osc.connect(dest); osc.start();
      window.openLiveStream = async () => dest.stream;
      window.releaseLiveStream = () => {};
      setScreenKeys(true); el.midiPoly.click();
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change')); await wait(300);
      const own = { on: layersOn(), note: el.midiLayersNote.hidden ? '' : el.midiLayersNote.textContent };
      el.srcMic.click(); await wait(900);
      const drawn = { input: state.source.drawsInput, on: layersOn(), mode: midi.layers.mode,
                      note: el.midiLayersNote.hidden ? '' : el.midiLayersNote.textContent };
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change'));
      el.srcTone.click(); await wait(300); setScreenKeys(false);
      return { own, drawn };
    }""")
    check("and with the input drawn a split is kept, not applied, and the panel says why - and applied on the generator",
          lines["drawn"]["input"] and not lines["drawn"]["on"] and lines["drawn"]["mode"] == "split"
          and "one layer" in lines["drawn"]["note"] and lines["own"]["on"] and lines["own"]["note"] == "", str(lines))
    # One oscillator on the sound and on the picture: LFO 1 at 1 Hz on the
    # instrument's level, read off the picture as each window's peak, and on
    # the page's trigger position. The page used to step copies of its own,
    # started at another moment: r was 0.10, and -0.96 on a run that landed
    # half a cycle out. In a rack holding the instrument's generator lane
    # nobody stepped them at all, and the position stood still - checked here
    # until P5 cut the rack.
    lfo = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const r = (a, b) => { const n = a.length, ma = a.reduce((x, y) => x + y) / n, mb = b.reduce((x, y) => x + y) / n;
        let sab = 0, saa = 0, sbb = 0;
        for (let i = 0; i < n; i++) { sab += (a[i] - ma) * (b[i] - mb); saa += (a[i] - ma) ** 2; sbb += (b[i] - mb) ** 2; }
        return saa > 0 && sbb > 0 ? sab / Math.sqrt(saa * sbb) : 0; };
      const watch = async () => {
        const peaks = [], pos = [];
        for (let i = 0; i < 50; i++) {
          await wait(60);
          peaks.push(Math.max(...state.source.getLatestWindow(1024)[0].map(Math.abs))); pos.push(state.positionMod);
        }
        return { peaks, pos };
      };
      applyPreset('b:Pure sine'); await wait(300);
      const setup = Object.assign(snapshot(), { l0s: 'sine', l0r: 100, l0a: 100, mod: 'lfo1>gen.amp@0.500;lfo1>trig.position@1.000' });
      hostQuietly(() => restore(setup)); hostSendSetup(); await wait(800);
      const alone = await watch();
      // LFO 2 alone, at another rate, so the two cannot stand in for each other.
      const setup2 = Object.assign(snapshot(), { l1s: 'sine', l1r: 150, l1a: 100, mod: 'lfo2>gen.amp@0.500;lfo2>trig.position@1.000' });
      hostQuietly(() => restore(setup2)); hostSendSetup(); await wait(800);
      const second = await watch();
      // The null: the position read a quarter of a cycle - four samples of 60 ms - after the peak.
      return { alone: r(alone.peaks, alone.pos), late: r(alone.peaks.slice(0, -4), alone.pos.slice(4)),
               second: r(second.peaks, second.pos), driver: lfoDriver() };
    }""")
    check("one oscillator on the sound and on the picture moves them in step: the instrument's level and the page's trigger position",
          lfo["alone"] > 0.85 and lfo["driver"] == "instrument", "r %.3f, the oscillators %s's" % (lfo["alone"], lfo["driver"]))
    check("and the reading fails against the position a quarter of a cycle late", not abs(lfo["late"]) > 0.85, "r %.3f" % lfo["late"])
    check("and LFO 2, at its own rate, the same", lfo["second"] > 0.85, "r %.3f" % lfo["second"])
    # The fade is kept in the page's storage, not in a setup: the instrument's
    # first state, taken back at connect as the plugin's is, reset it to off.
    p.evaluate("() => { setFade('both'); setFadeEnvelope({ attack: 1.25 }); saveFade(); }")
    p.reload(); p.wait_for_timeout(1500)
    kept = p.evaluate("() => ({ mode: fade.mode, attack: fade.envs[0].attack, kind: state.source.kind })")
    check("and the fade comes back after a reload", kept == {"mode": "both", "attack": 1.25, "kind": "host"}, str(kept))
    p.evaluate("() => { setFade('off'); saveFade(); }")
    check("no page errors", not errors, "; ".join(errors[:3]))
    p.close()
    b.close()

    # Without autoplay: the worklet plays no blocks until a press, and the page
    # says so. Until 5m this asserted no chunks at all, which was the blank
    # screen a first visit got: now the same instrument draws on this thread
    # meanwhile. The context is held suspended until a press, as a browser's
    # autoplay rule holds it, rather than trusting this one to.
    b = pw.chromium.launch(executable_path=CHROME)
    q = b.new_page(viewport={"width": 1400, "height": 900})
    q.add_init_script("""(() => {
      let pressed = false;
      for (const kind of ['pointerdown', 'keydown']) window.addEventListener(kind, () => { pressed = true; }, true);
      const Real = window.AudioContext;
      window.AudioContext = class extends Real {
        constructor(...a) { super(...a); super.suspend(); }
        resume() { return pressed ? super.resume() : Promise.resolve(); }
      };
    })()""")
    errors = []
    q.on("pageerror", lambda e: errors.append(str(e)))
    q.goto(PAGE + "?picture=0")
    q.wait_for_timeout(2000)
    WAIT = """() => ({ kind: state.source.kind, waiting: state.source.waiting, standing: state.source.standing,
      credit: el.credit.textContent, seen: hostSync.seen, peak: Math.max(...state.source.getLatestWindow(2048)[0].map(Math.abs)) })"""
    waiting = q.evaluate(WAIT)
    check("unpressed, the worklet plays no blocks and the page says so, and the instrument draws on this thread meanwhile",
          waiting["kind"] == "host" and waiting["waiting"] and waiting["standing"] and waiting["seen"] >= 1
          and "press anything to hear it" in waiting["credit"] and waiting["peak"] > 0.1, str(waiting))
    # A hand on a slider before the press: the stand-in takes it, and so does the worklet.
    q.evaluate("() => { el.amp.value = String(Number(el.amp.value) / 2); el.amp.dispatchEvent(new Event('input')); }")
    q.wait_for_timeout(600)
    halved = q.evaluate(WAIT)
    q.keyboard.press("Shift")
    q.wait_for_timeout(1000)
    pressed = q.evaluate(WAIT)
    check("a slider moved before the press reaches the stand-in: the picture half the height",
          abs(halved["peak"] / waiting["peak"] - 0.5) < 0.03, "%.4f then %.4f" % (waiting["peak"], halved["peak"]))
    check("and the first press starts the worklet, which lets the stand-in go and had the slider too",
          not pressed["waiting"] and not pressed["standing"] and "press" not in pressed["credit"]
          and abs(pressed["peak"] / waiting["peak"] - 0.5) < 0.03, str(pressed))
    check("and the comparison fails against the level before the slider", not abs(waiting["peak"] / waiting["peak"] - 0.5) < 0.03)
    check("no page errors while it stood in", not errors, "; ".join(errors[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the page is the face of the instrument compiled, as it is the plugin's")
print("everything passes")
