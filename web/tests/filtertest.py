"""The picture-path filter, against the one the browser already has.

Two implementations of one filter drift apart quietly unless something checks,
so the first and longest section here is agreement with getFrequencyResponse -
including the trap that Q is read in decibels for a lowpass and linearly for a
bandpass, which is the exact mistake that sat in this page's band crossovers.
"""
# Stage 5, step 3, batch 4 (13 Nov): until then this suite opened ?brain=js.
# Its numbers - the filter's law against the browser's BiquadFilterNode,
# Butterworth at resonance nought, a low pass rounding a square, the window's
# left edge primed, the lag lane filtered, a hidden lane left alone, and a
# source sweeping the cutoff - read the page's own capture() over the page's
# own generator and a stubbed source, with LFO 1 held by hand. They are
# asserted on the core now, each with its null, in core/tests/pieces/
# filter.py: capture.h's law against the Audio EQ Cookbook's response, and
# capture_cpp's capture. (The page's capture() is the face and stays; parity
# holds it to capture.h.) "The tone source is the silent one" and "the chain
# goes when the source does" went: only the page's brain has a tone source to
# drop. What is left is on the site's default page, where the instrument's
# sound goes to the speakers through the page's monitor chain
# (makeBrainHost): the capture's cost, the round trip, that chain's wiring,
# its taps and glides, the limiter, and the readout.
import os, sys
from playwright.sync_api import sync_playwright
import corpus

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")


fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required",
                                                          "--use-fake-device-for-media-stream",
                                                          "--use-fake-ui-for-media-stream"])
    p = b.new_context(permissions=["microphone"], viewport={"width": 1400, "height": 900}).new_page()

    p.add_init_script("""
      // Every node connected to a context's speakers, from the first: on the
      // default page the instrument's chain is made as the page starts
      // (makeBrainHost). On ?brain=js this hook went in later and the page's
      // own generator was dropped and built again under it; on the default
      // there is no generator of the page's to drop.
      window.__toDest = [];
      const real = AudioNode.prototype.connect;
      AudioNode.prototype.connect = function (dest, ...rest) {
        if (dest && dest.context && dest === dest.context.destination) {
          window.__toDest.push(this.constructor.name);
        }
        return real.call(this, dest, ...rest);
      };
    """)

    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(700)
    corpus.install(p)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    # Here stood, on ?brain=js: "agreement within a tenth of a decibel" with
    # the browser's own biquad, "resonance nought is maximally flat" and its
    # trap, "the tone source is the silent one", "the signal really is a
    # square" and "a low pass really rounds the corners off it", "the first
    # samples are not louder than the rest" and "nothing is NaN", and "the lag
    # lane is filtered too". core/tests/pieces/filter.py's now, on the core,
    # but for the tone source, which only the page's brain had.

    print("\n--- what it costs ---")
    # The face's capture() over the instrument's lanes, the longest window
    # there is: on ?brain=js the same over the page's own generator. A face
    # cost, not the engine's, so it stays with the face.
    corpus.held_tone(p)
    p.wait_for_timeout(500)
    cost = p.evaluate("""() => {
      state.timebase = 8;
      const run = () => {
        const t0 = performance.now();
        for (let i = 0; i < 40; i++) capture();
        return (performance.now() - t0) / 40;
      };
      state.filter.on = false; run();
      const off = run();
      state.filter.on = true; state.filter.type = 'lowpass';
      state.filter.cutoff = 566; state.filter.res = 20; run();
      const on = run();
      state.filter.on = false;
      return { off, on, lanes: laneCount(), kind: state.source.kind, length: capture().channels[0].length };
    }""")
    print("    capture at 50 ms/div: %.2f ms without, %.2f ms with (%d lanes of %d, %s)"
          % (cost["off"], cost["on"], cost["lanes"], cost["length"], cost["kind"]))
    check("it fits in a frame, on the instrument's lanes", cost["on"] < 8 and cost["kind"] == "host"
          and cost["length"] > 20000, "%.2f ms of a 16.7 ms frame, %d samples a lane" % (cost["on"], cost["length"]))

    # The band split's four lanes, the most the page draws. On ?brain=js
    # toMic() and the page's own Mic; on the default toMic() would leave the
    # instrument for the page's Mic (stage 5, batch 1), so the Mic and Bands
    # buttons are pressed, which keep it (hostToMic, hostSplit). The
    # microphone is faked.
    p.evaluate("() => { setView('bench'); setBenchTab('play'); }"); p.wait_for_timeout(150)
    p.evaluate("() => el.srcMic.click()"); p.wait_for_timeout(1500)
    p.evaluate("() => el.micBands.click()"); p.wait_for_timeout(1000)
    rack = p.evaluate("""() => {
      state.timebase = 8;
      const run = () => {
        const t0 = performance.now();
        for (let i = 0; i < 30; i++) capture();
        return (performance.now() - t0) / 30;
      };
      state.filter.on = false; run(); const off = run();
      state.filter.on = true; state.filter.cutoff = 566; run(); const all = run();
      state.filter.on = false;
      return { off, all, lanes: laneCount(), kind: state.source.kind };
    }""")
    print("    %d lanes at 50 ms/div on %s: %.2f ms off, %.2f ms on" % (rack["lanes"], rack["kind"], rack["off"], rack["all"]))
    check("still fits a frame at full width, on the band split's four lanes, the instrument's",
          rack["lanes"] == 4 and rack["kind"] == "host" and rack["all"] < 12,
          "%d lanes on %s, %.2f ms" % (rack["lanes"], rack["kind"], rack["all"]))
    # Here stood "a shown lane is filtered" and "a hidden lane is not filtered
    # at all", on the page's capture() over a stubbed source window
    # (?brain=js); core/tests/pieces/filter.py's now, on capture_cpp's lanes.
    p.evaluate("() => { el.srcTone.click(); }"); p.wait_for_timeout(500)

    print("\n--- it round trips ---")
    # Here stood "a source sweeps the cutoff": LFO 1 held by hand and the
    # page's applyModMatrix read through filterNow (?brain=js);
    # core/tests/pieces/filter.py's now, on the screen's own filter.cutoff.
    trip = p.evaluate("""() => {
      state.filter.on = true; state.filter.type = 'notch';
      state.filter.cutoff = 700; state.filter.res = 45;
      const before = snapshot();
      restore(decodeSetup(encodeSetup(before)));
      const after = snapshot();
      return { differ: Object.keys(before).filter((k) => before[k] !== after[k]),
               type: state.filter.type, on: state.filter.on, saved: [before.filterType, before.filterOn] };
    }""")
    check("the filter survives a round trip", trip["differ"] == [], str(trip["differ"]))
    check("with its type and switch", trip["type"] == "notch" and trip["on"] is True, str(trip))
    p.evaluate("() => { state.filter.on = false; }")

    print("\n--- what reaches the speakers ---")
    p.wait_for_timeout(500)
    wiring = p.evaluate("""() => ({
      toDestination: window.__toDest.slice(),
      chains: monitorChains.size,
      kind: state.source.kind,
      // The instrument's chain since 5a: no limiter (the instrument has its own), and the backstop for the clamp.
      own: Array.from(monitorChains).map((c) => {
        const curve = c.clamp && c.clamp.curve;
        let most = 0, apart = 0;
        if (curve) for (let i = 0; i < curve.length; i++) {
          const x = (i / (curve.length - 1)) * 2 - 1;
          most = Math.max(most, Math.abs(curve[i]));
          if (Math.abs(x) <= 0.99) apart = Math.max(apart, Math.abs(curve[i] - Math.fround(x)));
        }
        return { limiter: !!c.limiter, curve: !!curve, most, apart, reads: typeof c.limiting === "function" };
      }),
      // A chain made as every other source's is (the page's own brain's, a monitored input's): the page's limiter.
      limiter: (() => {
        const ctx = new OfflineAudioContext(2, 128, 44100);
        const c = makeMonitorChain(ctx);
        const out = { threshold: c.limiter.threshold.value, ratio: c.limiter.ratio.value, knee: c.limiter.knee.value,
                      attack: +c.limiter.attack.value.toFixed(4), clamped: !!c.clamp && !!c.clamp.curve && c.clamp.curve[2047] === CLAMP_CURVE[2047] && CLAMP_CURVE[2047] < 0.99 };
        dropMonitorChain(c);
        return [out];
      })(),
      wet: Array.from(monitorChains).map((c) => c.wet.gain.value),
    })""")
    print("    %s" % wiring)
    # Every connection since the page began, so a chain made and dropped on
    # the way (the Mic and Bands pressed above) is counted too: each was a
    # clamp. One chain is left, below.
    check("the only thing touching the speakers is the output clamp",
          len(wiring["toDestination"]) >= 1 and set(wiring["toDestination"]) == {"WaveShaperNode"},
          str(wiring["toDestination"]))
    check("there is exactly one chain, the instrument's", wiring["chains"] == 1 and wiring["kind"] == "host",
          "%s on %s" % (wiring["chains"], wiring["kind"]))
    check("with a limiter set as a brickwall, not a compressor",
          wiring["limiter"][0]["ratio"] >= 20 and wiring["limiter"][0]["knee"] == 0
          and wiring["limiter"][0]["threshold"] <= -1, str(wiring["limiter"]))
    check("and a clamp behind it, because a compressor has no lookahead",
          wiring["limiter"][0]["clamped"] is True)
    check("and the filter starts out of the monitor path", wiring["wet"] == [0], str(wiring["wet"]))
    # Since stage 5, step 5a the instrument limits and clamps its own output
    # (core/include/scope/limiter.h, held to these nodes to the bit by
    # parity's limiter section), so its chain has no limiter, and in place of
    # the clamp a backstop that is the identity to 0.995 and under one above.
    own = wiring["own"][0] if wiring["own"] else {}
    check("the instrument's chain has no limiter of its own, and reads the instrument's for the face's meter",
          own.get("limiter") is False and own.get("reads") is True, str(own))
    check("and its backstop is the identity on all the instrument can send, and never reaches one",
          own.get("curve") and own.get("apart", 1) == 0 and own.get("most", 2) < 1, str(own))
    check("null: the page's clamp is not the identity there", True if not own else
          p.evaluate("() => { let a = 0; for (let i = 0; i < 2048; i++) { const x = (i / 2047) * 2 - 1; if (Math.abs(x) <= 0.99) a = Math.max(a, Math.abs(CLAMP_CURVE[i] - Math.fround(x))); } return a; }") > 0.01)

    print("\n--- the two taps are independent ---")
    taps = p.evaluate("""async () => {
      const chain = Array.from(monitorChains)[0];
      const settle = () => new Promise((r) => setTimeout(r, 200));
      const out = {};
      state.filter.on = true;

      setAnalyseAt('post'); setMonitorAt('pre'); syncMonitor(); await settle();
      out.pictureOnly = { screen: state.analyseAt, wet: +chain.wet.gain.value.toFixed(2) };

      setMonitorAt('post'); syncMonitor(); await settle();
      out.both = { screen: state.analyseAt, wet: +chain.wet.gain.value.toFixed(2) };

      setAnalyseAt('pre'); await settle();
      out.earsOnly = { screen: state.analyseAt, wet: +chain.wet.gain.value.toFixed(2) };

      setAnalyseAt('post'); setMonitorAt('pre'); syncMonitor();
      state.filter.on = false;
      return out;
    }""")
    check("picture only leaves the speakers dry",
          taps["pictureOnly"]["screen"] == "post" and taps["pictureOnly"]["wet"] < 0.05,
          str(taps["pictureOnly"]))
    check("both filtered brings the speakers in",
          taps["both"]["wet"] > 0.9, str(taps["both"]))
    check("and the screen can read the input while the ears do not",
          taps["earsOnly"]["screen"] == "pre" and taps["earsOnly"]["wet"] > 0.9,
          str(taps["earsOnly"]))

    print("\n--- glided, not assigned ---")
    # A value written straight into an AudioParam once a frame is a staircase
    # in the signal. Anything the ears read has to be moved to, not set. On
    # the default the instrument's sound goes through this chain, and the
    # page's own matrix moves its cutoff, from LFO values the instrument
    # posts back: that is the visual matrix step 5 has to decide about
    # (STAGE5-INVENTORY.md, section 1), and this check follows it. LFO 1 is
    # still held by hand here, for the frames the check steps itself.
    zipper = p.evaluate("""() => {
      const descriptor = Object.getOwnPropertyDescriptor(AudioParam.prototype, 'value');
      let assigned = 0, glided = 0;
      Object.defineProperty(AudioParam.prototype, 'value', {
        configurable: true, get: descriptor.get,
        set(v) { assigned++; return descriptor.set.call(this, v); },
      });
      const realTarget = AudioParam.prototype.setTargetAtTime;
      AudioParam.prototype.setTargetAtTime = function (...args) {
        glided++; return realTarget.apply(this, args);
      };

      state.filter.on = true;
      state.modRoutings = [{ sourceId: 'lfo1', destId: 'filter.cutoff', amount: 1 }];
      touchRoutings();
      const frame = capture();
      assigned = 0; glided = 0;
      const mods = [];
      for (let i = 0; i < 10; i++) { lfos[0].value = i / 10; applyModMatrix(frame, 16); mods.push(state.cutoffMod); }

      Object.defineProperty(AudioParam.prototype, 'value', descriptor);
      AudioParam.prototype.setTargetAtTime = realTarget;
      state.modRoutings = []; touchRoutings();
      state.filter.on = false;
      return { assigned, glided, moved: mods[9] - mods[0] };
    }""")
    check("no AudioParam is assigned during a sweep", zipper["assigned"] == 0,
          "%d direct writes" % zipper["assigned"])
    check("they are all glided, while the sweep moves the cutoff", zipper["glided"] >= 30 and zipper["moved"] > 100,
          "%d setTargetAtTime calls over 10 frames, the cutoff moved %.0f steps" % (zipper["glided"], zipper["moved"]))

    print("\n--- the limiter, rendered ---")
    limited = p.evaluate("""async () => {
      const render = async (throughTheChain) => {
        const rate = 44100;
        const ctx = new OfflineAudioContext(1, rate, rate);
        const osc = ctx.createOscillator();
        osc.type = 'sawtooth';
        osc.frequency.value = 400;
        const hot = ctx.createGain();
        hot.gain.value = 4;                       // far past full scale

        osc.connect(hot);
        let chain = null;
        if (throughTheChain) {
          // The real thing, not a copy of it.
          chain = makeMonitorChain(ctx);
          chain.filter.type = 'lowpass';
          chain.filter.frequency.value = 400;
          chain.filter.Q.value = MONITOR_MAX_Q;
          chain.wet.gain.value = 1;
          chain.dry.gain.value = 0;
          hot.connect(chain.input);
        } else {
          const filter = ctx.createBiquadFilter();
          filter.type = 'lowpass';
          filter.frequency.value = 400;
          filter.Q.value = MONITOR_MAX_Q;
          hot.connect(filter); filter.connect(ctx.destination);
        }

        osc.start(0);
        const buffer = await ctx.startRendering();
        if (chain) dropMonitorChain(chain);
        const data = buffer.getChannelData(0);
        let peak = 0;
        for (let i = Math.floor(rate * 0.2); i < data.length; i++) {
          const a = Math.abs(data[i]); if (a > peak) peak = a;
        }
        return peak;
      };
      return { raw: await render(false), limited: await render(true) };
    }""")
    print("    a resonant peak at four times full scale: %.2f raw, %.3f through the chain"
          % (limited["raw"], limited["limited"]))
    check("unlimited it would be far past full scale", limited["raw"] > 2, "%.2f" % limited["raw"])
    check("the chain holds it under full scale", limited["limited"] < 1.0,
          "%.4f" % limited["limited"])

    print("\n--- the readout says which signal it measured ---")
    corpus.held_tone(p)
    p.evaluate("() => { state.filter.on = true; setAnalyseAt('post'); }")
    p.wait_for_timeout(400)
    said = p.evaluate("() => el.readoutDetail.textContent")
    check("post-filter is stated", "post-filter" in said, said)
    p.evaluate("() => { setAnalyseAt('pre'); }")
    p.wait_for_timeout(400)
    check("and not when the screen reads the input",
          "post-filter" not in p.evaluate("() => el.readoutDetail.textContent"))
    # Here stood "the chain goes when the source does, and only the new
    # source's own is left" (?brain=js): the page's source dropped and Tone
    # pressed, which builds the page's own generator. The instrument's chain
    # is there as long as the page is (makeBrainHost); only the page's brain
    # has a source to drop, so it went with stage 5, step 3, batch 4.

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all filter checks pass")
