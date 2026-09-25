"""The effects on a live input (S1): the plane, the delay and the chorus on a
microphone, a line input or a file, drawn and heard.

What would go wrong, and what is checked for it:

- the input changed with nothing on: no effects node exists until an effect
  is wanted, and none after the last is switched off;
- an effect that reaches the picture and not the speakers, or the other way
  round: the monitor chain is tapped, and what the speakers are handed is
  mirrored exactly as what is drawn is;
- the wrong arithmetic: it is the generator's own code, so a kaleidoscope on
  a microphone folds every angle into its wedge as the generator's does, and
  a delay on a file puts each repeat at the delay time to within a few
  samples - measured from the file's own burst, not from a guess at when it
  started;
- a routing that does not reach it: an oscillator on the twist swirls a
  mono input's diagonal off itself, and the mono input shows as two lanes
  while it does, because what the effect made of it is a pair;
- a rack's stems twisted into each other: a rack gets no insert, and the
  sections say what the effects are acting on.

The fixture is two oscillators behind getUserMedia - 220 Hz on the left and
330 Hz on the right, never a circle: a 3:2 pair has a length and a direction
that change all the way round, which a rotation-like effect cannot leave
alone.
"""
import math, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


SETUP = """() => {
  window.__wait = (ms) => new Promise((r) => setTimeout(r, ms));
  // A stereo input: two oscillators, 3:2, into a stream the page is handed
  // as its microphone. Mono when asked: one oscillator in both channels.
  window.__mic = async (mono) => {
    const ctx = new AudioContext();
    const merge = ctx.createChannelMerger(2), dest = ctx.createMediaStreamDestination();
    const a = ctx.createOscillator(), c = ctx.createOscillator();
    a.frequency.value = 220; c.frequency.value = 330;
    const g = ctx.createGain(); g.gain.value = 0.8;
    a.connect(merge, 0, 0); (mono ? a : c).connect(merge, 0, 1);
    merge.connect(g); g.connect(dest); a.start(); c.start();
    // A mono microphone says so in its settings, which is what the page reads;
    // the stub's stream is two channels whatever it carries, so it is told.
    if (mono) {
      const track = dest.stream.getAudioTracks()[0], own = track.getSettings.bind(track);
      track.getSettings = () => Object.assign({}, own(), { channelCount: 1 });
    }
    navigator.mediaDevices.getUserMedia = () => Promise.resolve(dest.stream);
    /* The page keeps a device's stream and hands it to the next request for
       the same device - which here would be the previous fixture's. So the
       old microphone is left first, by way of the tone, and its release
       empties the cache for the new one. Clearing the cache by hand instead
       left the old source to release the NEW stream, filed under the same
       key, and stop its tracks: a silent second microphone, and a twist
       check that read nought for a reason of its own. */
    if (state.source && state.source.kind === 'mic') { el.srcTone.click(); await __wait(300); }
    el.srcMic.click(); await __wait(1200);
  };
  window.__win = (n) => state.source.getLatestWindow(n || 4410);
  window.__set = (id, v, kind) => { el[id].value = String(v); el[id].dispatchEvent(new Event(kind)); };
  // A file: a 20 ms burst of 1 kHz at the start of a second of silence.
  window.__burst = (rate) => {
    const n = rate, bytes = 44 + n * 4;
    const b = new ArrayBuffer(bytes), v = new DataView(b);
    const str = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
    str(0, 'RIFF'); v.setUint32(4, bytes - 8, true); str(8, 'WAVE'); str(12, 'fmt ');
    v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 2, true);
    v.setUint32(24, rate, true); v.setUint32(28, rate * 4, true); v.setUint16(32, 4, true);
    v.setUint16(34, 16, true); str(36, 'data'); v.setUint32(40, n * 4, true);
    for (let i = 0; i < n; i++) {
      const s = i < rate * 0.02 ? Math.round(16000 * Math.sin(2 * Math.PI * 1000 * i / rate)) : 0;
      v.setInt16(44 + i * 4, s, true); v.setInt16(46 + i * 4, s, true);
    }
    return new File([b], 'burst.wav', { type: 'audio/wav' });
  };
}"""

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
    p.evaluate(SETUP)

    print("\n--- nothing on, nothing there ---")
    first = p.evaluate("""async () => {
      await __mic(false);
      const w = __win();
      return { kind: state.source.kind, active: state.source.fx.active,
               lowX: Math.min(...w[0]), lowY: Math.min(...w[1]), where: el.planeWhere.textContent };
    }""")
    print("    %s" % first)
    check("a microphone with no effect on has no effects node in its path, and draws its input as it is",
          first["kind"] == "mic" and first["active"] is False and first["lowX"] < -0.7 and first["lowY"] < -0.7,
          str(first))

    print("\n--- drawn, and heard ---")
    mirrored = p.evaluate("""async () => {
      // A declared line input, monitored, so the speakers have a chain to tap.
      state.liveKind = 'line'; state.source.setMonitor(true);
      const tap = state.source.monitorChain.ctx.createAnalyser();
      tap.fftSize = 8192;
      state.source.monitorChain.input.connect(tap);
      // Filled before it is read: read at once, it held nothing, and "before"
      // was a silence that proved nothing either way.
      await __wait(400);
      const t = new Float32Array(8192);
      tap.getFloatTimeDomainData(t);
      const heardBefore = Math.min(...t);
      __set('planeMirror', 3, 'change'); await __wait(1500);
      const w = __win();
      tap.getFloatTimeDomainData(t);
      const out = { active: state.source.fx.active, lowX: Math.min(...w[0]), lowY: Math.min(...w[1]),
                    heardBefore, heardAfter: Math.min(...t), where: el.planeWhere.textContent };
      /* From both axes to X only, with the node kept all the way: whatever
         the worklet does now it was told while running. Turning the mirror
         off instead would drop the node, and the rebuild would carry the new
         settings whether or not a change is ever sent. */
      __set('planeMirror', 1, 'change'); await __wait(600);
      const x = __win();
      Object.assign(out, { xOnlyActive: state.source.fx.active, xOnlyLowX: Math.min(...x[0]),
                           xOnlyLowY: Math.min(...x[1]) });
      return out;
    }""")
    print("    %s" % mirrored)
    check("mirrored, the input is drawn with no negative half on either axis",
          mirrored["active"] and mirrored["lowX"] > -0.02 and mirrored["lowY"] > -0.02, str(mirrored))
    check("and a change made while it runs reaches it: X alone folded, Y given back its negative half",
          mirrored["xOnlyActive"] and mirrored["xOnlyLowX"] > -0.02 and mirrored["xOnlyLowY"] < -0.7, str(mirrored))
    check("and the speakers are handed the same: what reaches the monitor chain is mirrored too",
          mirrored["heardBefore"] < -0.5 and mirrored["heardAfter"] > -0.02,
          "%.3f before, %.3f after" % (mirrored["heardBefore"], mirrored["heardAfter"]))
    check("and the section says it is on your input, drawn and heard",
          mirrored["where"] == "On your input, drawn and heard.", mirrored["where"])

    print("\n--- the generator's arithmetic ---")
    kal = p.evaluate("""async () => {
      __set('planeMirror', 0, 'change'); __set('planeKaleido', 6, 'change'); await __wait(1500);
      const w = __win();
      let lowest = Infinity, highest = -Infinity, points = 0;
      for (let i = 0; i < w[0].length; i++) {
        if (Math.hypot(w[0][i], w[1][i]) < 0.1) continue;
        const a = Math.atan2(w[1][i], w[0][i]);
        lowest = Math.min(lowest, a); highest = Math.max(highest, a); points++;
      }
      __set('planeKaleido', 0, 'change'); await __wait(300);
      return { lowest, highest, points };
    }""")
    print("    kaleidoscope of six on the microphone: angles %.4f to %.4f over %d points" % (kal["lowest"], kal["highest"], kal["points"]))
    # The oversampling's filter lets a corner overshoot a hair past the wedge.
    check("a kaleidoscope of six folds every angle of the input into 0 to pi/6, as the generator's does",
          kal["lowest"] > -0.05 and kal["highest"] < math.pi / 6 + 0.05 and kal["points"] > 2000, str(kal))
    # And over the whole wedge, not one ray of it: a stereo input collapsed to
    # its left channel is a diagonal, which folds to one angle inside the
    # wedge and would pass the bounds above.
    check("and the two channels arrive as two: the folded input fills the wedge rather than one ray of it",
          kal["highest"] - kal["lowest"] > 0.4, str(kal))

    off = p.evaluate("""async () => {
      await __wait(300);
      const w = __win();
      return { active: state.source.fx.active, lowX: Math.min(...w[0]) };
    }""")
    check("with the last effect off, the effects node is gone and the input is drawn as it is again",
          off["active"] is False and off["lowX"] < -0.7, str(off))

    print("\n--- a routing, on a mono input ---")
    mono = p.evaluate("""async () => {
      // Switched by the page, never stopped by hand first: the page stops the
      // old source as it installs the new one, and a context closed twice
      // throws part-way through the install and leaves the old one in place.
      await __mic(true);
      // The lane rows under Lanes: what the refit rebuilds. The page keeps
      // two channel records whatever the source, so those cannot show it.
      const __rows = () => el.laneRows.querySelectorAll('input[id$="On"]').length;
      const apart = () => { const w = __win(); let m = 0;
        for (let i = 0; i < w[0].length; i++) m = Math.max(m, Math.abs(w[0][i] - w[1][i])); return m; };
      // A level first: a silent input is also a diagonal that has not moved.
      const level = Math.max(...__win()[0].map(Math.abs));
      const still = apart(), lanes0 = [state.source.channels, __rows()];
      addRouting('lfo1', 'gen.twist');
      state.modRoutings.find((r) => r.destId === 'gen.twist').amount = 1; touchRoutings();
      lfos[0].depth = 1; lfos[0].rate = 0.5;
      await __wait(2500);
      const swirled = apart(), lanes1 = [state.source.channels, __rows()], active = state.source.fx.active;
      // The amount to nought with the routing kept, so the node stays: what
      // the worklet does now it has only from the per-frame message.
      state.modRoutings[0].amount = 0; touchRoutings(); await __wait(400);
      const zeroed = apart(), stillActive = state.source.fx.active;
      state.modRoutings = []; touchRoutings(); await __wait(600);
      return { level, still, swirled, zeroed, stillActive, lanes0, lanes1, active, lanes2: [state.source.channels, __rows()],
               activeAfter: state.source.fx.active };
    }""")
    print("    %s" % mono)
    check("an oscillator on the twist swirls a mono input's diagonal off itself, from a slider at nought",
          mono["level"] > 0.5 and mono["still"] < 1e-3 and mono["swirled"] > 0.2 and mono["active"], str(mono))
    check("and a routing turned to nought mid-stream stops swirling it: the worklet follows the page every frame",
          mono["stillActive"] and mono["zeroed"] < 1e-3, str(mono))
    # Both counts, [the source's, the page's lane rows]: the source's is a
    # getter over the insert and cannot be wrong for long; the rows are what
    # has to follow it, and reading only the first never saw them.
    check("a mono input is one lane, two while the effect is on, and one again when the routing goes with the node",
          mono["lanes0"] == [1, 1] and mono["lanes1"] == [2, 2] and mono["lanes2"] == [1, 1]
          and mono["activeAfter"] is False,
          str(mono))

    print("\n--- a file, and its echoes ---")
    echo = p.evaluate("""async () => {
      await toFile(__burst(48000)); await __wait(300);
      const rate = state.source.sampleRate;
      __set('delayMix', 100, 'input'); __set('delayFeedback', 0, 'input'); __set('delayMs', 150, 'input');
      await __wait(900);
      state.source.seek(0); state.source.play(); await __wait(400);
      const w = state.source.getLatestWindow(state.source.capacity)[0];
      // Onsets: the first sample over a threshold after at least 10 ms quiet.
      const onsets = [];
      let quiet = rate;
      for (let i = 0; i < w.length; i++) {
        if (Math.abs(w[i]) > 0.1) { if (quiet > rate * 0.01) onsets.push(i); quiet = 0; } else quiet++;
      }
      const where = el.planeWhere.textContent, active = state.source.fx.active;
      __set('delayMix', 0, 'input'); await __wait(200);
      return { rate, onsets, where, active };
    }""")
    print("    %s" % echo)
    # The last two onsets are the burst just played and its one repeat. The
    # first gap can be anything: the window reaches back into the play before.
    gaps = [b2 - a2 for a2, b2 in zip(echo["onsets"], echo["onsets"][1:])]
    want = 0.15 * echo["rate"]
    check("a delay on a file puts the repeat 150 ms after the burst, to within 2 samples",
          echo["active"] and len(gaps) >= 1 and abs(gaps[-1] - want) <= 2,
          "gaps %s against %.0f" % (gaps, want))
    check("and a file's effects are drawn and heard", echo["where"] == "On the file, drawn and heard.", echo["where"])

    print("\n--- where it does not go ---")
    rack = p.evaluate("""async () => {
      window.__wav = (name, hz) => {
        const rate = 44100, n = rate / 4, bytes = 44 + n * 2;
        const b = new ArrayBuffer(bytes), v = new DataView(b);
        const str = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
        str(0, 'RIFF'); v.setUint32(4, bytes - 8, true); str(8, 'WAVE'); str(12, 'fmt ');
        v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
        v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true);
        v.setUint16(34, 16, true); str(36, 'data'); v.setUint32(40, n * 2, true);
        for (let i = 0; i < n; i++) v.setInt16(44 + i * 2, Math.round(12000 * Math.sin(2 * Math.PI * hz * i / rate)), true);
        return new File([b], name + '.wav', { type: 'audio/wav' });
      };
      // The file's insert, with an effect on, as the page leaves the file:
      // the page has no other handle on it once the source is replaced.
      __set('delayMix', 60, 'input'); await __wait(500);
      const left = state.source.fx, leftActive = left.active;
      await toRack([__wav('a', 220), __wav('b', 330)]); await __wait(500);
      __set('delayMix', 0, 'input');
      __set('planeMirror', 1, 'change'); await __wait(400);
      const out = { leftActive, leftAfter: left.active, kind: state.source.kind, fx: 'fx' in state.source, where: el.planeWhere.textContent };
      __set('planeMirror', 0, 'change');
      el.srcTone.click(); await __wait(400);
      out.tone = el.planeWhere.textContent;
      return out;
    }""")
    print("    %s" % rack)
    check("a rack of stems gets no effects insert, and the sections say why",
          rack["kind"] == "rack" and rack["fx"] is False and "not one stereo pair" in rack["where"], str(rack))
    check("and the source it replaced has let its effects node go, rather than leave it running on a closed input",
          rack["leftActive"] is True and rack["leftAfter"] is False, str(rack))
    check("and on the tone the effects are the generator's", rack["tone"] == "On the generator.", rack["tone"])

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("a microphone, a line input and a file go through the generator's effects, seen and heard")
