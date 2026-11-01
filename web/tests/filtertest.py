"""The picture-path filter, against the one the browser already has.

Two implementations of one filter drift apart quietly unless something checks,
so the first and longest section here is agreement with getFrequencyResponse -
including the trap that Q is read in decibels for a lowpass and linearly for a
bandpass, which is the exact mistake that sat in this page's band crossovers.
"""
# On ?brain=js (5m): this suite reads the page's own brain - its oscillators
# set by hand, and its speakers' graph - which core/tests/parity.py holds the
# instrument to, sample for sample. The instrument, the site's default since
# 5m, is braintest.py's and hosttest.py's.
import os, sys
from playwright.sync_api import sync_playwright

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

    # two helpers that only this suite needs
    p.add_init_script("""
      // The magnitude of a biquad at a frequency. This is the MEASUREMENT, not
      // the law: the law is `biquadCoefficients`, which lives in the app and is
      // what these checks are about. It sat in the app for a while purely
      // because this file called it, which made a reader think the page
      // computed frequency responses somewhere. It does not.
      window.biquadMagnitude = (c, hz, rate) => {
        const w = 2 * Math.PI * hz / rate;
        const cw = Math.cos(w), sw = Math.sin(w);
        const c2w = Math.cos(2 * w), s2w = Math.sin(2 * w);
        const nr = c.b0 + c.b1 * cw + c.b2 * c2w;
        const ni = -(c.b1 * sw + c.b2 * s2w);
        const dr = 1 + c.a1 * cw + c.a2 * c2w;
        const di = -(c.a1 * sw + c.a2 * s2w);
        return Math.sqrt((nr * nr + ni * ni) / (dr * dr + di * di));
      };

      // Hertz back to a slider step. Found by bisecting the app's OWN forward
      // mapping rather than by writing the inverse out, so it cannot drift
      // from `cutoffHz` the way a second copy of the formula could. Late
      // binding: `cutoffHz` is declared by the page script, which runs after
      // this, and is in scope by the time anything calls this.
      window.cutoffStep = (hz) => {
        let lo = 0, hi = CUTOFF_STEPS;
        for (let i = 0; i < 40; i++) {
          const mid = (lo + hi) / 2;
          if (cutoffHz(mid) < hz) lo = mid; else hi = mid;
        }
        return (lo + hi) / 2;
      };
    """)

    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0&brain=js"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    print("\n--- the two filters are one filter ---")
    agree = p.evaluate("""() => {
      const rate = 44100;
      const ctx = new OfflineAudioContext(1, 128, rate);
      const probes = new Float32Array([30, 100, 440, 1000, 3000, 9000, 18000]);
      const worst = { db: 0, at: null };
      let checked = 0;

      for (const [type] of FILTER_TYPES) {
        for (const step of [100, 300, 566, 800, 980]) {
          for (const res of [0, 25, 60, 100]) {
            const hz = cutoffHz(step);
            const q = Q_IN_DECIBELS.has(type)
              ? BUTTERWORTH_Q_DB + res / 100 * 27
              : 0.5 + res / 100 * 19.5;

            const node = ctx.createBiquadFilter();
            node.type = type; node.frequency.value = hz; node.Q.value = q;
            const mag = new Float32Array(probes.length), ph = new Float32Array(probes.length);
            node.getFrequencyResponse(probes, mag, ph);

            const mine = biquadCoefficients(type, hz, q, rate);
            for (let i = 0; i < probes.length; i++) {
              const a = 20 * Math.log10(Math.max(1e-9, mag[i]));
              const c = 20 * Math.log10(Math.max(1e-9, biquadMagnitude(mine, probes[i], rate)));
              checked++;
              if (Math.abs(a - c) > Math.abs(worst.db)) {
                worst.db = a - c;
                worst.at = type + ' ' + Math.round(hz) + ' Hz res ' + res
                         + ' probed at ' + probes[i] + ': browser ' + a.toFixed(3)
                         + ', ours ' + c.toFixed(3);
              }
            }
          }
        }
      }
      return { worst, checked };
    }""")
    print("    %d points checked; worst disagreement %.4f dB" % (agree["checked"], agree["worst"]["db"]))
    if agree["worst"]["at"]: print("    at %s" % agree["worst"]["at"])
    check("agreement within a tenth of a decibel", abs(agree["worst"]["db"]) < 0.1,
          "%.4f dB" % agree["worst"]["db"])

    # The trap, stated as its own check: a lowpass at resonance nought must be
    # Butterworth, which is -3.01 dB at the corner and NOT the +0.71 dB that
    # putting a linear 0.707 into a decibel parameter produces.
    corner = p.evaluate("""() => {
      const rate = 44100, hz = 1000;
      const good = biquadCoefficients('lowpass', hz, BUTTERWORTH_Q_DB, rate);
      const wrong = biquadCoefficients('lowpass', hz, 0.707, rate);
      const db = (c) => 20 * Math.log10(biquadMagnitude(c, hz, rate));
      return { good: db(good), wrong: db(wrong) };
    }""")
    check("resonance nought is maximally flat", abs(corner["good"] + 3.0103) < 0.01,
          "%.3f dB at the corner" % corner["good"])
    check("and the linear value in a dB slot would not be",
          abs(corner["wrong"] - 0.71) < 0.05, "%.3f dB" % corner["wrong"])

    print("\n--- it reaches the source that has no audio graph ---")
    # The tone source is a ring buffer filled from the frame loop, so a capture
    # taken in the same tick as a preset is applied reads the PREVIOUS signal.
    # Measuring that mistake once was enough; every setup here now settles.
    p.evaluate("""() => {
      applyPreset('b:Square wave');
      state.timebase = 6;
      state.filter.on = false;
    }""")
    p.wait_for_timeout(700)
    STEEPEST = """() => {
      const x = capture().channels[0];
      let m = 0;
      for (let i = 1; i < x.length; i++) {
        const d = Math.abs(x[i] - x[i - 1]);
        if (d > m) m = d;
      }
      return m;
    }"""
    openEdge = p.evaluate(STEEPEST)
    p.evaluate("""() => {
      state.filter.on = true;
      state.filter.type = 'lowpass';
      state.filter.cutoff = cutoffStep(200);
      state.filter.res = 0;
    }""")
    p.wait_for_timeout(200)
    closedEdge = p.evaluate(STEEPEST)
    kind = p.evaluate("() => state.source.kind")
    p.evaluate("() => { state.filter.on = false; }")

    check("the tone source is the silent one", kind == "tone")
    check("the signal really is a square", openEdge > 0.5,
          "steepest sample step %.3f" % openEdge)
    # NOT total variation, which is the wrong question: smoothing a monotone
    # step spreads it out without changing how far it travels, so the total is
    # preserved and says nothing. How steep the steepest part is falls hard.
    check("a low pass really rounds the corners off it", closedEdge < openEdge * 0.1,
          "steepest edge %.4f -> %.4f, %.0fx gentler"
          % (openEdge, closedEdge, openEdge / max(closedEdge, 1e-9)))

    print("\n--- no ringing at the left edge ---")
    # An IIR started from silence rings while it settles, and this one starts
    # afresh every frame - so an unprimed filter draws a wobble sixty times a
    # second at the one place the eye is most likely to be.
    p.evaluate("() => { applyPreset('b:Pure sine'); state.timebase = 6; }")
    p.wait_for_timeout(700)
    edge = p.evaluate("""() => {
      state.filter.on = true; state.filter.type = 'lowpass';
      state.filter.cutoff = cutoffStep(300); state.filter.res = 80;
      const f = capture();
      const x = f.channels[0];
      const head = x.subarray(0, 64), tail = x.subarray(x.length - 64);
      const peak = (a) => { let m = 0; for (const v of a) if (Math.abs(v) > m) m = Math.abs(v); return m; };
      state.filter.on = false;
      return { head: peak(head), tail: peak(tail), finite: x.every(Number.isFinite) };
    }""")
    check("the first samples are not louder than the rest",
          edge["head"] < edge["tail"] * 1.3,
          "head %.4f against %.4f" % (edge["head"], edge["tail"]))
    check("and nothing is NaN", edge["finite"])

    print("\n--- where it sits in the pipeline ---")
    p.evaluate("() => applyPreset('b:Pure sine')")
    p.wait_for_timeout(700)
    order = p.evaluate("""() => {
      // Lag reads the same buffer the filter wrote, so a phase portrait is a
      // portrait of what is on screen rather than of the unfiltered signal.
      state.lagOn = true; state.lagAuto = false; state.lagMs = 1;
      state.filter.on = true; state.filter.type = 'lowpass';
      state.filter.cutoff = cutoffStep(120); state.filter.res = 0;
      const f = capture();
      const peak = (a) => { let m = 0; for (const v of a) if (Math.abs(v) > m) m = Math.abs(v); return m; };
      const both = { signal: peak(f.channels[0]), delayed: peak(f.channels[1]) };
      state.filter.on = false; state.lagOn = false;
      return both;
    }""")
    check("the lag lane is filtered too",
          abs(order["signal"] - order["delayed"]) < order["signal"] * 0.25 + 1e-6,
          "%.4f against %.4f" % (order["signal"], order["delayed"]))

    print("\n--- what it costs ---")
    p.evaluate("() => { applyPreset('b:Pure sine'); state.timebase = 8; }")
    p.wait_for_timeout(500)
    cost = p.evaluate("""() => {
      state.timebase = 8;                        // the longest window there is
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
      return { off, on, lanes: laneCount() };
    }""")
    print("    capture at 50 ms/div: %.2f ms without, %.2f ms with (%d lanes)"
          % (cost["off"], cost["on"], cost["lanes"]))
    check("it fits in a frame", cost["on"] < 8, "%.2f ms of a 16.7 ms frame" % cost["on"])

    # The band split's four lanes are the most the page draws, and the case
    # where a per-sample filter could stop being affordable. (A rack's six
    # were, until P5 cut the rack.) The microphone is faked.
    p.evaluate("() => { setView('bench'); setBenchTab('play'); }"); p.wait_for_timeout(150)
    p.evaluate("() => toMic()"); p.wait_for_timeout(1500)
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
      for (let i = 2; i < state.channels.length; i++) state.channels[i].on = false;
      run(); const some = run();
      for (const ch of state.channels) ch.on = true;
      state.filter.on = false;
      return { off, all, some, lanes: laneCount() };
    }""")
    print("    %d lanes at 50 ms/div: %.2f ms off, %.2f ms on, %.2f ms with half hidden"
          % (rack["lanes"], rack["off"], rack["all"], rack["some"]))
    check("still fits a frame at full width, on the band split's four lanes", rack["lanes"] == 4 and rack["all"] < 12,
          "%d lanes, %.2f ms" % (rack["lanes"], rack["all"]))
    skipped = p.evaluate("""() => {
      /* A fixed signal, because three captures of a live input are three
         different moments and comparing them says nothing. A square is the
         clearest thing to see a low pass act on. */
      const source = state.source;
      const real = source.getLatestWindow.bind(source);
      source.getLatestWindow = (n) => {
        const lanes = [];
        for (let c = 0; c < source.channels; c++) {
          const x = new Float32Array(n);
          for (let i = 0; i < n; i++) x[i] = Math.sin(i / 50) >= 0 ? 0.8 : -0.8;
          lanes.push(x);
        }
        return lanes;
      };

      state.filter.on = true; state.filter.type = 'lowpass';
      state.filter.cutoff = cutoffStep(200); state.filter.res = 0;
      for (const ch of state.channels) ch.on = true;
      const lit = Array.from(capture().channels.map((c) => c[100]));

      state.channels[1].on = false;
      const dark = Array.from(capture().channels.map((c) => c[100]));

      for (const ch of state.channels) ch.on = true;
      state.filter.on = false;
      const raw = Array.from(capture().channels.map((c) => c[100]));

      source.getLatestWindow = real;
      return { lit, dark, raw };
    }""")
    shownChanged = abs(skipped["lit"][0] - skipped["raw"][0]) > 1e-6
    hiddenSkipped = abs(skipped["dark"][1] - skipped["raw"][1]) < 1e-9
    hiddenFiltered = abs(skipped["lit"][1] - skipped["raw"][1]) > 1e-6
    check("a shown lane is filtered", shownChanged)
    check("a hidden lane is not filtered at all", hiddenSkipped and hiddenFiltered,
          "shown %.6f hidden %.6f raw %.6f"
          % (skipped["lit"][1], skipped["dark"][1], skipped["raw"][1]))
    p.evaluate("() => { el.srcTone.click(); }"); p.wait_for_timeout(500)

    print("\n--- it is patchable, and it round trips ---")
    patched = p.evaluate("""() => {
      state.modRoutings = [{ sourceId: 'lfo1', destId: 'filter.cutoff', amount: 1 }];
      touchRoutings();
      state.filter.cutoff = 500;
      lfos[0].value = 1;
      applyModMatrix(capture(), 16);
      const up = filterNow().hz;
      lfos[0].value = -1;
      applyModMatrix(capture(), 16);
      const down = filterNow().hz;
      state.modRoutings = []; touchRoutings();
      applyModMatrix(capture(), 16);
      return { up, down, rest: filterNow().hz };
    }""")
    print("    cutoff swept %.0f Hz -> %.0f Hz, at rest %.0f Hz"
          % (patched["down"], patched["up"], patched["rest"]))
    check("a source sweeps the cutoff", patched["up"] > patched["rest"] * 3
          and patched["down"] < patched["rest"] / 3, str(patched))

    trip = p.evaluate("""() => {
      state.filter.on = true; state.filter.type = 'notch';
      state.filter.cutoff = 700; state.filter.res = 45;
      const before = snapshot();
      restore(decodeSetup(encodeSetup(before)));
      const after = snapshot();
      return { differ: Object.keys(before).filter((k) => before[k] !== after[k]),
               type: state.filter.type, on: state.filter.on };
    }""")
    check("the filter survives a round trip", trip["differ"] == [], str(trip["differ"]))
    check("with its type and switch", trip["type"] == "notch" and trip["on"] is True, str(trip))

    print("\n--- what reaches the speakers ---")
    p.evaluate("""() => {
      window.__toDest = [];
      const real = AudioNode.prototype.connect;
      AudioNode.prototype.connect = function (dest, ...rest) {
        if (dest && dest.context && dest === dest.context.destination) {
          window.__toDest.push(this.constructor.name);
        }
        return real.call(this, dest, ...rest);
      };
    }""")
    p.evaluate("() => { setView('bench'); setBenchTab('play'); }"); p.wait_for_timeout(150)
    # The generator, built afresh so its chain is made under the hook above,
    # and its sound asked for: the source that goes to the speakers since P5
    # cut file playback, which is what this read until then.
    p.evaluate("""async () => {
      state.source.stop(); state.source = null; el.srcTone.click();
      await applyGeneratorSound();
    }""")
    p.wait_for_timeout(2200)

    wiring = p.evaluate("""() => ({
      toDestination: window.__toDest.slice(),
      chains: monitorChains.size,
      limiter: Array.from(monitorChains).map((c) => ({
        threshold: c.limiter.threshold.value, ratio: c.limiter.ratio.value,
        knee: c.limiter.knee.value, attack: +c.limiter.attack.value.toFixed(4),
        clamped: !!c.clamp && !!c.clamp.curve,
      })),
      wet: Array.from(monitorChains).map((c) => c.wet.gain.value),
    })""")
    check("the only thing touching the speakers is the output clamp",
          wiring["toDestination"] == ["WaveShaperNode"], str(wiring["toDestination"]))
    check("there is exactly one chain for the source", wiring["chains"] == 1, str(wiring["chains"]))
    check("with a limiter set as a brickwall, not a compressor",
          wiring["limiter"][0]["ratio"] >= 20 and wiring["limiter"][0]["knee"] == 0
          and wiring["limiter"][0]["threshold"] <= -1, str(wiring["limiter"]))
    check("and a clamp behind it, because a compressor has no lookahead",
          wiring["limiter"][0]["clamped"] is True)
    check("and the filter starts out of the monitor path", wiring["wet"] == [0], str(wiring["wet"]))

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
    # in the signal. Anything the ears read has to be moved to, not set.
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
      for (let i = 0; i < 10; i++) { lfos[0].value = i / 10; applyModMatrix(frame, 16); }

      Object.defineProperty(AudioParam.prototype, 'value', descriptor);
      AudioParam.prototype.setTargetAtTime = realTarget;
      state.modRoutings = []; touchRoutings();
      state.filter.on = false;
      return { assigned, glided };
    }""")
    check("no AudioParam is assigned during a sweep", zipper["assigned"] == 0,
          "%d direct writes" % zipper["assigned"])
    check("they are all glided", zipper["glided"] >= 30,
          "%d setTargetAtTime calls over 10 frames" % zipper["glided"])

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
    p.evaluate("() => { state.filter.on = true; setAnalyseAt('post'); }")
    p.wait_for_timeout(400)
    said = p.evaluate("() => el.readoutDetail.textContent")
    check("post-filter is stated", "post-filter" in said, said)
    p.evaluate("() => { setAnalyseAt('pre'); }")
    p.wait_for_timeout(400)
    check("and not when the screen reads the input",
          "post-filter" not in p.evaluate("() => el.readoutDetail.textContent"))
    # The source's own chain, by name: since P4 the tone source that replaces
    # it is heard and has a chain of its own, so "no chains left" stopped
    # being the question. The null is the same chain read before the switch.
    # The source is the generator since P5 cut file playback, so it is
    # dropped and Tone pressed: Tone on a tone keeps it, and nothing would go.
    held = p.evaluate("""() => { window.__chain = Array.from(monitorChains)[0] || null;
                                 return !!window.__chain && monitorChains.has(window.__chain); }""")
    p.evaluate("""async () => { state.filter.on = false; state.source.stop(); state.source = null;
                                el.srcTone.click(); await applyGeneratorSound(); }""")
    p.wait_for_timeout(400)
    gone = p.evaluate("() => ({ kept: monitorChains.has(window.__chain), size: monitorChains.size, kind: state.source.kind })")
    check("the chain goes when the source does, and only the new source's own is left",
          held and not gone["kept"] and gone["size"] <= 1 and gone["kind"] == "tone", str(gone))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all filter checks pass")
