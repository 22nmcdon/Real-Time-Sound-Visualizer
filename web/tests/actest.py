"""AC coupling: one algorithm, used twice, with the corner as one number.

What this replaced was not a worse version of the same thing. Taking the
window's mean out is non-causal and whole-block - it needs every sample before
it can say what to subtract, and what it removes depends on how long the block
is. A one-pole high pass is causal and per-sample. No tolerance was ever going
to close that: a longer fetch changes what the mean removes and does nothing
to what the pole removes. So the fix is the same shape as the Q-in-decibels
fix - stop asking two algorithms to agree and make them one algorithm.

Three things are checked here. That the picture and the speakers run the same
difference equation, which is a property of identical COEFFICIENTS rather than
of identical code, so the corner is read from one place by both. That the IIR
is primed and given a runway, because a filter run fresh on every captured
window settles in plain view otherwise - the main filter needed this and a
one-pole is not too simple to need it. And that the corner is where it says
it is, measured rather than taken from the algebra.
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
    p.wait_for_timeout(200)

    print("\n--- the corner is where it says it is ---")
    # Measured off the transfer function rather than taken from the algebra
    # that produced the pole: the two agree here, but only one of them would
    # have noticed if they stopped agreeing.
    corners = p.evaluate("""([rate]) => {
      const out = [];
      for (const want of [0.5, 1, 5, 10, 20]) {
        const c = dcBlockerCoefficients(want, rate);
        // Walk up in fine steps to where the response first reaches -3.01 dB.
        let found = null;
        for (let hz = 0.05; hz < 80 && found === null; hz += 0.01) {
          if (20 * Math.log10(dcBlockerMagnitude(c, hz, rate)) >= -3.0103) found = hz;
        }
        out.push({ want, found, r: c.r });
      }
      return out;
    }""", [44100])
    worst = max(abs(row["found"] - row["want"]) / row["want"] for row in corners)
    for row in corners:
        print("    asked for %5.1f Hz, the -3 dB point is at %5.2f Hz"
              % (row["want"], row["found"]))
    check("every corner lands within 2% of where it was asked for",
          worst < 0.02, "worst %.2f%%" % (worst * 100))

    clamped = p.evaluate("""() => [
      dcBlockerCoefficients(0.001, 44100).corner,
      dcBlockerCoefficients(500, 44100).corner,
    ]""")
    check("and a corner outside the range is brought back into it",
          clamped == [0.5, 20], str(clamped))

    print("\n--- the picture and the speakers run the same equation ---")
    agree = p.evaluate("""async ([corner]) => {
      const rate = 44100, frames = Math.round(rate * 0.25);
      const ctx = new OfflineAudioContext(1, frames, rate);

      /* A tone that starts at nought, with the offset arriving as a step half
         way through. The starting value matters: `filterInPlace` primes its
         history to the steady state for a constant first sample and an
         IIRFilterNode always starts from zero, so a probe that began at -0.2
         would have the two running from different histories. That difference
         decays with the pole's own time constant - 1,400 samples at ten hertz
         and 28,000 at half a hertz - which is why the first attempt at this
         test failed by 0.19 at the low corner and 3e-6 at the high one, and
         looked for all the world like a precision problem. */
      const buffer = ctx.createBuffer(1, frames, rate);
      const x = buffer.getChannelData(0);
      for (let i = 0; i < frames; i++) {
        const t = i / rate;
        x[i] = 0.4 * Math.sin(2 * Math.PI * 220 * t) + (i > frames / 2 ? 0.3 : 0);
      }

      const src = ctx.createBufferSource();
      src.buffer = buffer;
      const c = dcBlockerCoefficients(corner, rate);
      // The node the monitor chain builds, from the same coefficients.
      const node = ctx.createIIRFilter([c.b0, c.b1], [1, c.a1]);
      src.connect(node); node.connect(ctx.destination);
      src.start();
      const rendered = await ctx.startRendering();

      // And the picture's own pass over the same samples.
      const mine = Float32Array.from(x);
      filterInPlace(mine, c);

      const got = rendered.getChannelData(0);
      let worst = 0, at = -1;
      for (let i = 0; i < frames; i++) {
        const d = Math.abs(got[i] - mine[i]);
        if (d > worst) { worst = d; at = i; }
      }
      return { worst, at, frames };
    }""", [10])
    check("the same coefficients give the same samples, to float32",
          agree["worst"] < 2e-7, "worst %.3g" % agree["worst"])

    for corner in (0.5, 5, 20):
        run = p.evaluate("""async ([corner]) => {
          const rate = 44100, frames = Math.round(rate * 0.2);
          const ctx = new OfflineAudioContext(1, frames, rate);
          const buffer = ctx.createBuffer(1, frames, rate);
          const x = buffer.getChannelData(0);
          for (let i = 0; i < frames; i++) {
            // Starting at nought, for the reason above.
            x[i] = 0.5 * Math.sin(2 * Math.PI * 60 * i / rate)
                 + (i > frames / 3 ? 0.25 : 0);
          }
          const src = ctx.createBufferSource();
          src.buffer = buffer;
          const c = dcBlockerCoefficients(corner, rate);
          const node = ctx.createIIRFilter([c.b0, c.b1], [1, c.a1]);
          src.connect(node); node.connect(ctx.destination);
          src.start();
          const rendered = await ctx.startRendering();
          const mine = Float32Array.from(x);
          filterInPlace(mine, c);
          const got = rendered.getChannelData(0);
          let worst = 0;
          for (let i = 0; i < frames; i++) {
            worst = Math.max(worst, Math.abs(got[i] - mine[i]));
          }
          return worst;
        }""", [corner])
        check("and at %.1f Hz as well" % corner, run < 2e-7, "worst %.3g" % run)

    # And the same again through the chain's OWN blocker at a corner nobody
    # could have hardcoded. Everything above builds its own node from the
    # coefficients, which would still pass if `tuneMonitorAC` quietly asked for
    # ten hertz of its own - the case this is here to catch.
    chained = p.evaluate("""async ([corner]) => {
      const rate = 44100, frames = Math.round(rate * 0.2);
      const ctx = new OfflineAudioContext(2, frames, rate);
      const buffer = ctx.createBuffer(1, frames, rate);
      const x = buffer.getChannelData(0);
      for (let i = 0; i < frames; i++) {
        x[i] = 0.4 * Math.sin(2 * Math.PI * 90 * i / rate)
             + (i > frames / 3 ? 0.3 : 0);
      }
      const src = ctx.createBufferSource();
      src.buffer = buffer;

      const chain = makeMonitorChain(ctx);
      src.connect(chain.input);
      // Straight out of the AC stage: what follows it is the filter and the
      // limiter, neither of which this is about.
      chain.acOut.disconnect();
      chain.acOut.connect(ctx.destination);

      const was = { hz: state.acHz, at: state.monitorAt, a: state.channels[0].ac,
                    b: state.channels[1].ac };
      state.acHz = corner;
      state.monitorAt = 'post';
      state.channels[0].ac = true; state.channels[1].ac = true;
      syncMonitor();
      // The crossfade is glided, and an offline context has no clock until it
      // renders, so put the wet side where the glide is going.
      chain.acWet.gain.cancelScheduledValues(0);
      chain.acDry.gain.cancelScheduledValues(0);
      chain.acWet.gain.value = 1;
      chain.acDry.gain.value = 0;

      state.acHz = was.hz; state.monitorAt = was.at;
      state.channels[0].ac = was.a; state.channels[1].ac = was.b;
      monitorChains.delete(chain);

      src.start();
      const out = await ctx.startRendering();
      const mine = Float32Array.from(x);
      filterInPlace(mine, dcBlockerCoefficients(corner, rate));

      const got = out.getChannelData(0);
      let worst = 0;
      for (let i = 0; i < frames; i++) {
        worst = Math.max(worst, Math.abs(got[i] - mine[i]));
      }
      return { worst, corner };
    }""", [3])
    check("and the chain's own blocker follows the corner, not a default of its own",
          chained["worst"] < 2e-7,
          "worst %.3g at %.1f Hz" % (chained["worst"], chained["corner"]))

    print("\n--- primed, and given a runway ---")
    # The transient this filter would otherwise have is the one the main filter
    # was already fixed for. A one-pole is not too simple to need it: run fresh
    # on every captured window with zero history, a DC offset arrives as a step
    # and the left edge of the screen shows the filter settling rather than the
    # signal.
    primed = p.evaluate("""() => {
      const rate = 44100, n = 4096, offset = 0.4;
      const c = dcBlockerCoefficients(10, rate);

      const x = new Float32Array(n);
      for (let i = 0; i < n; i++) {
        x[i] = 0.3 * Math.sin(2 * Math.PI * 220 * i / rate) + offset;
      }

      const ours = Float32Array.from(x);
      filterInPlace(ours, c);

      // The same filter started from nothing, which is what an unprimed pass
      // would do.
      const cold = new Float32Array(n);
      let x1 = 0, y1 = 0;
      for (let i = 0; i < n; i++) {
        const y = c.b0 * x[i] + c.b1 * x1 - c.a1 * y1;
        x1 = x[i]; y1 = y;
        cold[i] = y;
      }

      // How far from settled each is at the very first sample, measured
      // against where the filter ends up.
      const settledMean = (buf) => {
        let sum = 0;
        for (let i = n - 1000; i < n; i++) sum += buf[i];
        return sum / 1000;
      };
      return {
        oursStart: ours[0], coldStart: cold[0],
        oursSettled: settledMean(ours), coldSettled: settledMean(cold),
        offset,
      };
    }""")
    check("primed, the first sample is already where the filter ends up",
          abs(primed["oursStart"] - primed["oursSettled"]) < 0.02,
          "starts at %.4f, settles at %.4f"
          % (primed["oursStart"], primed["oursSettled"]))
    check("unprimed it would start a whole DC offset away",
          abs(primed["coldStart"] - primed["coldSettled"]) > 0.3,
          "starts at %.4f, settles at %.4f"
          % (primed["coldStart"], primed["coldSettled"]))

    runway = p.evaluate("""() => {
      /* And the runway, end to end: the capture filters the whole fetch and
         draws the last part of it, so even what the priming does not catch
         happens off screen. A step in the middle of the fetch is the test -
         the drawn window must show the signal, not the recovery. */
      state.running = false;
      const before = { ac: state.channels[0].ac, level: state.level };
      state.channels[0].ac = true;
      state.level = 2;                      // no trigger, so the slice is fixed
      const frame = capture();
      state.channels[0].ac = before.ac;
      state.level = before.level;
      state.running = true;

      const lane = frame.channels[0];
      let first = 0, rest = 0;
      for (let i = 0; i < 64; i++) first = Math.max(first, Math.abs(lane[i]));
      for (let i = 64; i < lane.length; i++) rest = Math.max(rest, Math.abs(lane[i]));
      return { first, rest, length: lane.length };
    }""")
    check("the drawn window's left edge is no louder than the rest of it",
          runway["first"] <= runway["rest"] * 1.05,
          "%.4f against %.4f" % (runway["first"], runway["rest"]))

    print("\n--- one corner, read from one place ---")
    shared = p.evaluate("""() => {
      const was = state.acHz;
      el.acCorner.value = '30';                   // 3.0 Hz
      el.acCorner.dispatchEvent(new Event('input'));
      const at3 = { state: state.acHz, label: el.acCornerValue.textContent,
                    r: dcBlockerCoefficients(state.acHz, 44100).r };
      el.acCorner.value = '150';                  // 15.0 Hz
      el.acCorner.dispatchEvent(new Event('input'));
      const at15 = { state: state.acHz, label: el.acCornerValue.textContent,
                     r: dcBlockerCoefficients(state.acHz, 44100).r };
      el.acCorner.value = String(Math.round(was * 10));
      el.acCorner.dispatchEvent(new Event('input'));
      return { at3, at15, back: state.acHz };
    }""")
    check("the slider moves the one number both sides read",
          shared["at3"]["state"] == 3 and shared["at15"]["state"] == 15
          and shared["at3"]["r"] != shared["at15"]["r"], str(shared))
    check("and says so in its own units",
          shared["at3"]["label"] == "3.0 Hz" and shared["at15"]["label"] == "15.0 Hz",
          "%s, %s" % (shared["at3"]["label"], shared["at15"]["label"]))

    rebuilt = p.evaluate("""() => {
      const ctx = new OfflineAudioContext(2, 128, 44100);
      const chain = makeMonitorChain(ctx);
      const was = state.acHz;

      state.acHz = 4;
      syncMonitor();
      const first = { hz: chain.acHz, node: !!chain.ac };
      const firstNode = chain.ac;

      syncMonitor();                              // same corner: leave it alone
      const again = chain.ac === firstNode;

      state.acHz = 12;
      syncMonitor();
      const moved = { hz: chain.acHz, fresh: chain.ac !== firstNode };

      state.acHz = was;
      syncMonitor();
      monitorChains.delete(chain);
      return { first, again, moved };
    }""")
    check("the speakers' blocker is built once and kept",
          rebuilt["first"]["node"] and rebuilt["first"]["hz"] == 4
          and rebuilt["again"] is True, str(rebuilt))
    check("and rebuilt only when the corner moves",
          rebuilt["moved"]["hz"] == 12 and rebuilt["moved"]["fresh"] is True,
          str(rebuilt["moved"]))

    print("\n--- and what the speakers may claim ---")
    mixed = p.evaluate("""async () => {
      /* A real context, not an offline one: `setTargetAtTime` moves a gain as
         the audio clock advances, and an offline context that is not rendering
         has no clock - its `value` would read whatever it was built with,
         however many times the crossfade had been asked to move. */
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      if (ctx.state === 'suspended') await ctx.resume();
      const chain = makeMonitorChain(ctx);
      const settle = () => new Promise((r) => setTimeout(r, 120));
      const was = { at: state.monitorAt, a: state.channels[0].ac, b: state.channels[1].ac };

      state.monitorAt = 'post';
      state.channels[0].ac = true; state.channels[1].ac = true;
      syncMonitor(); await settle();
      const both = chain.acWet.gain.value;

      state.channels[1].ac = false;               // one lane coupled, one not
      syncMonitor(); await settle();
      const one = chain.acWet.gain.value;

      state.channels[1].ac = true;
      state.monitorAt = 'pre';
      syncMonitor(); await settle();
      const dry = chain.acWet.gain.value;

      state.monitorAt = was.at;
      state.channels[0].ac = was.a; state.channels[1].ac = was.b;
      syncMonitor();
      monitorChains.delete(chain);
      ctx.close();
      return { both, one, dry };
    }""")
    check("both lanes coupled and the speakers are coupled too",
          mixed["both"] > 0.9, str(mixed))
    check("one lane coupled and the speakers keep the input",
          mixed["one"] < 0.1, str(mixed))
    check("and on the input side, whatever the lanes say",
          mixed["dry"] < 0.1, str(mixed))

    print("\n--- and the numbers say which signal they are about ---")
    said = p.evaluate("""() => {
      const was = state.channels[0].ac;
      state.channels[0].ac = true;
      writeReadout(capture());
      const on = el.readoutDetail.textContent;
      state.channels[0].ac = false;
      writeReadout(capture());
      const off = el.readoutDetail.textContent;
      state.channels[0].ac = was;
      return { on, off };
    }""")
    check("the readout names the corner while AC is on",
          "AC 10.0 Hz" in said["on"] and "AC" not in said["off"],
          " | ".join(said["on"].split(" \u00b7 ")[-2:]))

    trip = p.evaluate("""() => {
      el.acCorner.value = '75';
      el.acCorner.dispatchEvent(new Event('input'));
      const code = encodeSetup(snapshot());
      el.acCorner.value = '100';
      el.acCorner.dispatchEvent(new Event('input'));
      restore(decodeSetup(code));
      const kept = state.acHz;
      restore({});
      return { kept, byDefault: state.acHz };
    }""")
    check("the corner survives a setup code", trip["kept"] == 7.5, str(trip["kept"]))
    check("and a setup written before it existed gets ten hertz",
          trip["byDefault"] == 10, str(trip["byDefault"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("AC coupling is one algorithm, twice")
