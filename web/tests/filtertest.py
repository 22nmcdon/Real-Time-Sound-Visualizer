"""The picture-path filter, against the one the browser already has.

Two implementations of one filter drift apart quietly unless something checks,
so the first and longest section here is agreement with getFrequencyResponse -
including the trap that Q is read in decibels for a lowpass and linearly for a
bandpass, which is the exact mistake that sat in this page's band crossovers.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

import fixtures
STEMS = fixtures.ensure()

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
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

    # Six lanes is the worst case the page allows, and the one where a
    # per-sample filter could stop being affordable.
    p.locator("#menuButton").click(); p.wait_for_timeout(150)
    p.locator("#srcRack").click(no_wait_after=True); p.wait_for_timeout(150)
    p.locator("#rackInput").set_input_files(
        [f"{STEMS}/{n}.wav" for n in ("drums", "bass", "other", "vocals")])
    p.wait_for_timeout(2500)
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
    check("still fits a frame at full width", rack["all"] < 12,
          "%.2f ms" % rack["all"])
    check("and hiding lanes really saves the work", rack["some"] < rack["all"] * 0.75,
          "%.2f against %.2f ms" % (rack["some"], rack["all"]))
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

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all filter checks pass")
