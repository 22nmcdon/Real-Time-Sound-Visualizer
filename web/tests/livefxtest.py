"""The effects on a live input (S1): the plane, the delay and the chorus on a
microphone or a line input, drawn and heard.

What would go wrong, and what is checked for it:

- the input changed with nothing on: no effects node exists until an effect
  is wanted, and none after the last is switched off;
- an effect that reaches the picture and not the speakers, or the other way
  round: the monitor chain is tapped, and what the speakers are handed is
  mirrored exactly as what is drawn is;
- the wrong arithmetic: it is the generator's own code, so a kaleidoscope on
  a microphone folds every angle into its wedge as the generator's does, and
  a delay on a live input puts each repeat at the delay time to within a few
  samples - measured from the input's own burst, not from a guess at when it
  started (a file's, until P5 cut file playback);
- a routing that does not reach it: an oscillator on the twist swirls a
  mono input's diagonal off itself, and the mono input shows as two lanes
  while it does, because what the effect made of it is a pair;
- a band split's lanes twisted into each other: the split gets no insert,
  and the sections say what the effects are acting on. (A rack's stems were
  the case until P5 cut the rack.)

The fixture is two oscillators behind getUserMedia - 220 Hz on the left and
330 Hz on the right, never a circle: a 3:2 pair has a length and a direction
that change all the way round, which a rotation-like effect cannot leave
alone.
"""
# On ?brain=js (5m): this suite reads the page's own brain - its live input's
# insert - which core/tests/parity.py holds the instrument to, sample for
# sample. The instrument, the site's default since 5m, is braintest.py's and
# hosttest.py's.
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
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0&brain=js"); p.wait_for_timeout(700)
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
      /* Read until it stops, up to four seconds, not after a fixed 400 ms.
         The page tells the worklet once a frame and the window read holds
         the audio before that, and under the full suite's load 400 ms came
         out still swirling at 1.2. A worklet that never heard would swirl
         past the four seconds, which is the failure this is for. */
      state.modRoutings[0].amount = 0; touchRoutings();
      const began = performance.now();
      let zeroed = apart();
      while (zeroed >= 1e-3 && performance.now() - began < 4000) { await __wait(100); zeroed = apart(); }
      const stillActive = state.source.fx.active;
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

    print("\n--- a burst, and its echoes ---")
    # A 20 ms burst of 1 kHz every half second, behind getUserMedia as the
    # oscillators are. It was a file until P5 cut file playback, and the
    # repeat is measured the same way: from the burst itself.
    echo = p.evaluate("""async () => {
      const ctx = new AudioContext(), rate = ctx.sampleRate;
      const buf = ctx.createBuffer(2, rate / 2, rate);
      for (let ch = 0; ch < 2; ch++) {
        const d = buf.getChannelData(ch);
        for (let i = 0; i < rate * 0.02; i++) d[i] = 0.5 * Math.sin(2 * Math.PI * 1000 * i / rate);
      }
      const src = ctx.createBufferSource(), dest = ctx.createMediaStreamDestination();
      src.buffer = buf; src.loop = true; src.connect(dest); src.start();
      navigator.mediaDevices.getUserMedia = () => Promise.resolve(dest.stream);
      if (state.source && state.source.kind === 'mic') { el.srcTone.click(); await __wait(300); }
      el.srcMic.click(); await __wait(1200);
      __set('delayMix', 100, 'input'); __set('delayFeedback', 0, 'input'); __set('delayMs', 150, 'input');
      await __wait(900);
      const srate = state.source.sampleRate;
      const w = state.source.getLatestWindow(state.source.capacity)[0];
      // Onsets: the first sample over a threshold after at least 10 ms quiet.
      const onsets = [];
      let quiet = srate;
      for (let i = 0; i < w.length; i++) {
        if (Math.abs(w[i]) > 0.1) { if (quiet > srate * 0.01) onsets.push(i); quiet = 0; } else quiet++;
      }
      const where = el.planeWhere.textContent, active = state.source.fx.active;
      __set('delayMix', 0, 'input'); await __wait(200);
      return { rate: srate, onsets, where, active };
    }""")
    print("    %s" % echo)
    # Burst, repeat, burst: the gaps go 150 ms and 350 ms by turns, and where
    # the window starts decides which comes first, so every 150 ms one is held
    # to it and there has to be one.
    gaps = [b2 - a2 for a2, b2 in zip(echo["onsets"], echo["onsets"][1:])]
    want = 0.15 * echo["rate"]
    short = [g for g in gaps if g < 0.25 * echo["rate"]]
    check("a delay on a live input puts the repeat 150 ms after the burst, to within 2 samples",
          echo["active"] and len(short) >= 1 and all(abs(g - want) <= 2 for g in short),
          "gaps %s against %.0f" % (gaps, want))
    check("and its effects are drawn", echo["where"].startswith("On your input, drawn"), echo["where"])

    print("\n--- where it does not go ---")
    split = p.evaluate("""async () => {
      // The microphone's insert, with an effect on, as the page leaves it for
      // the band split: the page has no other handle on it once the source is
      // replaced.
      __set('delayMix', 60, 'input'); await __wait(500);
      const left = state.source.fx, leftActive = left.active;
      el.micBands.click(); await __wait(600);
      __set('delayMix', 0, 'input');
      __set('planeMirror', 1, 'change'); await __wait(400);
      const out = { leftActive, leftAfter: left.active, lanes: state.source.channels, fx: 'fx' in state.source,
                    where: el.planeWhere.textContent };
      __set('planeMirror', 0, 'change');
      el.micWhole.click(); await __wait(300);
      el.srcTone.click(); await __wait(400);
      out.tone = el.planeWhere.textContent;
      return out;
    }""")
    print("    %s" % split)
    check("a band split gets no effects insert, and the sections say why",
          split["lanes"] == 4 and split["fx"] is False and "not one stereo pair" in split["where"], str(split))
    check("and the source it replaced has let its effects node go, rather than leave it running on a closed input",
          split["leftActive"] is True and split["leftAfter"] is False, str(split))
    check("and on the tone the effects are the generator's", split["tone"] == "On the generator.", split["tone"])

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("a microphone, a line input and a file go through the generator's effects, seen and heard")
