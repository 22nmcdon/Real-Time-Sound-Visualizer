"""Rotation, mid/side as a case of it, and the line it is not allowed to cross.

Three things are asserted here and the third is the one that matters most.

That mid/side is what it always was, now that it is written as a rotation at
45 degrees with its gain and its flip kept explicit. That the X-Y figure is
turned before each lane is placed rather than after. And that rotation reaches
the X-Y figure and NOTHING else - not Y-T, not the trigger, not a single
number in the readout.

That last one is a scoping decision rather than an implementation detail. A
rotated lane in Y-T is a blend of two signals with no picture to justify it,
and a frequency or a THD reading taken off it would still be labelled as
though it described the input. Zoom was scoped out of the shared transforms
for the same reason. When rotation does become a signal transform for
everything, these checks are what say which measurements have to be given
their own tap first.
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


# The drawn cloud's shape, as two numbers that survive the canvas mapping: the
# mapping is the same scale on both axes with y flipped, so the ratio of the
# principal axes comes through untouched and the angle comes through negated.
SHAPE = """(xs, ys) => {
  const n = xs.length;
  let mx = 0, my = 0;
  for (let i = 0; i < n; i++) { mx += xs[i]; my += ys[i]; }
  mx /= n; my /= n;
  let sxx = 0, syy = 0, sxy = 0;
  for (let i = 0; i < n; i++) {
    const a = xs[i] - mx, b = ys[i] - my;
    sxx += a * a; syy += b * b; sxy += a * b;
  }
  sxx /= n; syy /= n; sxy /= n;
  const tr = sxx + syy, det = sxx * syy - sxy * sxy;
  const disc = Math.sqrt(Math.max(0, tr * tr / 4 - det));
  const hi = tr / 2 + disc, lo = Math.max(0, tr / 2 - disc);
  return {
    ratio: hi > 0 ? Math.sqrt(lo / hi) : 0,
    angle: 0.5 * Math.atan2(2 * sxy, sxx - syy) * 180 / Math.PI,
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
    p.wait_for_timeout(200)
    p.evaluate("(shape) => { window.__shape = eval(shape); }", SHAPE)

    print("\n--- mid and side are what they were ---")
    # A circle out of the generator, and then the tone stopped so that two
    # captures read the same samples: `tick` only runs while it is running, so
    # a halted generator is a still buffer to compare against itself.
    same = p.evaluate("""() => {
      applyPreset('b:Harmonic tone');
      el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change'));
      el.interval.value = '0'; el.interval.dispatchEvent(new Event('change'));
      el.phase.value = '90'; el.phase.dispatchEvent(new Event('input'));
      return true;
    }""")
    p.wait_for_timeout(500)
    ms = p.evaluate("""() => {
      state.running = false;                      // freeze the ring buffer
      /* And put the trigger out of reach. The trigger searches whichever lane
         it is pointed at, and with mid/side on that lane IS the mid - so the
         two captures would be sliced at different edges and compared sample
         against sample as though they were not. Above full scale nothing is
         found, and both fall back to the same fixed offset. */
      const level = state.level;
      state.level = 2;
      state.midSide = false;
      const plain = capture();
      state.midSide = true;
      const turned = capture();
      const names = [laneName(0), laneName(1)];   // while it is still on
      state.midSide = false;
      state.level = level;
      state.running = true;

      let worstMid = 0, worstSide = 0;
      const l = plain.channels[0], r = plain.channels[1];
      const m = turned.channels[0], s = turned.channels[1];
      for (let i = 0; i < l.length; i++) {
        worstMid = Math.max(worstMid, Math.abs(m[i] - (l[i] + r[i]) / 2));
        worstSide = Math.max(worstSide, Math.abs(s[i] - (l[i] - r[i]) / 2));
      }
      return { worstMid, worstSide, n: l.length, names };
    }""")
    check("mid is still the half sum, to a part in ten million",
          ms["worstMid"] < 1e-7, "worst %.3g over %d samples" % (ms["worstMid"], ms["n"]))
    check("and side is still the half difference, sign and all",
          ms["worstSide"] < 1e-7, "worst %.3g" % ms["worstSide"])
    check("the lanes still say which is which", ms["names"] == ["Mid", "Side"],
          str(ms["names"]))

    # The flip is the part most easily lost: drop it and side comes back
    # negated, which is a mirrored figure rather than a broken one - the kind
    # of change that looks like a different take rather than a bug.
    flip = p.evaluate("""() => {
      const { cos, sin } = turnOf(MID_SIDE_TURNS);
      // What a pure rotation would give for a known pair, against what the
      // page gives. L = 1, R = 0: side should be +0.5, not -0.5.
      const pure = (1 * sin + 0 * cos) * MID_SIDE_GAIN;
      const ours = (1 * sin + 0 * cos) * MID_SIDE_GAIN * MID_SIDE_FLIP;
      return { pure, ours };
    }""")
    check("the M/S matrix is a reflection, and the flip says so",
          abs(flip["ours"] - 0.5) < 1e-12 and abs(flip["pure"] + 0.5) < 1e-12,
          "ours %.3f, a pure rotation would give %.3f" % (flip["ours"], flip["pure"]))

    print("\n--- no preset can see the reorder ---")
    # Turning before placing and placing before turning are the same thing
    # unless the two lanes are placed differently - different full scales, or
    # an offset. Every preset in the page sets them the same and turns by
    # nothing, so this change cannot reach any of them; that is checked here
    # rather than asserted, preset by preset.
    presets = p.evaluate("""() => {
      const odd = [];
      for (const [, entries] of PRESETS) {
        for (const [name] of entries) {
          applyPreset('b:' + name);
          const a = state.channels[0], b = state.channels[1];
          if (state.rotate !== 0 || a.fsDb !== b.fsDb
              || a.offset !== 0 || b.offset !== 0) {
            odd.push({ name, rotate: state.rotate, scales: [a.fsDb, b.fsDb],
                       offsets: [a.offset, b.offset] });
          }
        }
      }
      return { odd, count: PRESETS.reduce((n, [, e]) => n + e.length, 0) };
    }""")
    check("every preset places both lanes alike and turns by nothing",
          presets["odd"] == [], str(presets["odd"][:2]))
    print("    %d presets checked" % presets["count"])

    agree = p.evaluate("""() => {
      // And the algebra behind that claim, at a turn where it would show.
      const { cos, sin } = turnOf(0.125);
      let worst = 0;
      for (const [l, r] of [[1, 0], [0.3, -0.7], [-0.5, 0.5], [0.9, 0.9]]) {
        for (const gain of [1, 0.25, 4]) {
          const turnedFirst = [(l * cos - r * sin) * gain, (l * sin + r * cos) * gain];
          const placedFirst = [(l * gain) * cos - (r * gain) * sin,
                               (l * gain) * sin + (r * gain) * cos];
          worst = Math.max(worst, Math.abs(turnedFirst[0] - placedFirst[0]),
                                  Math.abs(turnedFirst[1] - placedFirst[1]));
        }
      }
      return worst;
    }""")
    check("with both lanes placed alike the two orders are the same figure",
          agree < 1e-15, "worst %.3g" % agree)

    print("\n--- and when they are placed differently, the new order is the one drawn ---")
    # A circle, turned by an eighth, with X at full scale and Y at a quarter.
    # Turn then squash: an ellipse lying along the screen axes. Squash then
    # turn: the same ellipse standing at 45 degrees. The drawn cloud says which
    # one happened, and it is not a subtle difference.
    p.evaluate("""() => {
      applyPreset('b:Harmonic tone');
      el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change'));
      el.phase.value = '90'; el.phase.dispatchEvent(new Event('input'));
      setDisplay('xy');
      el.interval.value = '0'; el.interval.dispatchEvent(new Event('change'));
      /* Full scale is what fills the screen, so a smaller number MAGNIFIES:
         index 3 is -12 dBFS, which is four times the gain of index 0. The
         lanes are placed four to one, which is all this needs. */
      state.channels[0].fsDb = 0;      // 0 dBFS
      state.channels[1].fsDb = -12;    // Y drawn four times as tall
      state.rotate = 0.125;
      state.zoom = 1; state.zoomStep = 0; state.zoomMod = 0;
    }""")
    p.wait_for_timeout(700)
    drawn = p.evaluate("""() => {
      // beamX/beamY hold the polyline the X-Y pass last built, in canvas
      // pixels: the mapping is isotropic with y flipped, so the shape of the
      // cloud survives it and the angle comes through negated.
      const n = Math.min(2000, beamX.length);
      const xs = [], ys = [];
      for (let i = 0; i < n; i++) {
        if (beamX[i] === 0 && beamY[i] === 0) break;
        xs.push(beamX[i]); ys.push(-beamY[i]);
      }
      return __shape(xs, ys);
    }""")
    # A circle turned by an eighth is still a circle, so placing it four to one
    # afterwards puts the long axis straight up the screen. Placing first and
    # turning after would stand the same ellipse at 45 degrees, which is the
    # one number that tells the two orders apart.
    upright = abs(abs(drawn["angle"]) - 90)
    check("the long axis stands up the screen, not at 45 degrees",
          upright < 8, "%.1f degrees off vertical, ratio %.3f"
                       % (upright, drawn["ratio"]))
    check("and the stretch is the one the two full scales ask for",
          abs(drawn["ratio"] - 0.25) < 0.05, "%.3f against 0.250" % drawn["ratio"])

    print("\n--- rotation reaches the figure and nothing else ---")
    # The scoping decision, as a test. Every number in the readout is taken
    # from `capture`, so if rotation ever moves in there this fails and says
    # which measurements have to be given their own tap first.
    scope = p.evaluate("""() => {
      state.channels[1].fsDb = 0;
      state.rotate = 0;
      state.running = false;
      const flat = capture();
      const before = measure(flat.channels[0], flat.rate);
      const corrBefore = correlation(flat.channels[0], flat.channels[1]);

      state.rotate = 0.3;
      const turned = capture();
      const after = measure(turned.channels[0], turned.rate);
      const corrAfter = correlation(turned.channels[0], turned.channels[1]);

      let worst = 0;
      for (let i = 0; i < flat.channels[0].length; i++) {
        worst = Math.max(worst, Math.abs(flat.channels[0][i] - turned.channels[0][i]),
                                Math.abs(flat.channels[1][i] - turned.channels[1][i]));
      }
      state.rotate = 0;
      state.running = true;
      return {
        worst, triggeredSame: flat.triggered === turned.triggered,
        preSame: flat.pre === turned.pre,
        peak: [before.peak, after.peak], rms: [before.rms, after.rms],
        corr: [corrBefore, corrAfter],
      };
    }""")
    check("turning the figure does not touch the captured lanes",
          scope["worst"] == 0, "worst difference %.3g" % scope["worst"])
    check("nor the trigger", scope["triggeredSame"] and scope["preSame"], str(scope))
    check("nor the per-lane peak and RMS",
          scope["peak"][0] == scope["peak"][1] and scope["rms"][0] == scope["rms"][1],
          str(scope["peak"]) + " " + str(scope["rms"]))
    check("nor the correlation the goniometer reports",
          scope["corr"][0] == scope["corr"][1], str(scope["corr"]))

    # Mid/side is the other way about on purpose, and says so: it IS a signal
    # transform, it does reach the measurements, and the lane names change so
    # that a reader knows which signal a number is about.
    asym = p.evaluate("""() => {
      state.running = false;
      state.midSide = false;
      const plain = capture();
      const a = measure(plain.channels[1], plain.rate);
      state.midSide = true;
      const turned = capture();
      const b = measure(turned.channels[1], turned.rate);
      const names = [laneName(0), laneName(1)];
      state.midSide = false;
      state.running = true;
      return { changed: a.rms !== b.rms, names };
    }""")
    check("mid/side does reach them, and renames the lanes so you can tell",
          asym["changed"] and asym["names"] == ["Mid", "Side"], str(asym))

    print("\n--- and the same rotation, in the audio graph ---")
    # The filter's discipline, applied to the second transform that wants to
    # live in two places: one set of numbers, two implementations, and a test
    # that renders the real chain rather than a copy of it.
    #
    # Tapped at the merger rather than at the destination, and that needs
    # saying. What follows the rotation is the limiter and the clamp, and the
    # limiter is Chrome's own: it carries a lookahead delay and an internal
    # makeup gain, so comparing the destination against the arithmetic would be
    # measuring those two rather than the matrix. They are measured below, on
    # their own, and the clamp is checked where it belongs - at the end, with a
    # signal loud enough to need it.
    RENDER = """async ([turns, at, tap]) => {
      const rate = 44100, frames = Math.round(rate * 0.3);
      const ctx = new OfflineAudioContext(2, frames, rate);

      // Two different signals, so a matrix that mixed them the wrong way round
      // could not hide: a sine on the left, a slower cosine on the right.
      const buffer = ctx.createBuffer(2, frames, rate);
      const l = buffer.getChannelData(0), r = buffer.getChannelData(1);
      for (let i = 0; i < frames; i++) {
        l[i] = 0.3 * Math.sin(2 * Math.PI * 220 * i / rate);
        r[i] = 0.3 * Math.cos(2 * Math.PI * 137 * i / rate);
      }

      const src = ctx.createBufferSource();
      src.buffer = buffer;
      const chain = makeMonitorChain(ctx);        // the real thing
      src.connect(chain.input);

      if (tap === 'merger') {
        // Straight out of the rotation, past the limiter and the clamp.
        chain.merger.disconnect();
        chain.merger.connect(ctx.destination);
      }

      const was = { rotate: state.rotate, mod: state.rotateMod,
                    at: state.monitorAt, on: state.filter.on };
      state.rotate = turns; state.rotateMod = 0;
      state.monitorAt = at; state.filter.on = false;
      syncMonitor();                              // the page's own setter
      state.rotate = was.rotate; state.rotateMod = was.mod;
      state.monitorAt = was.at; state.filter.on = was.on;
      /* Out of the live set but still connected: `dropMonitorChain` unhooks
         the clamp from the destination, which would render silence. This only
         stops the page's frame loop re-targeting these gains mid-render. */
      monitorChains.delete(chain);

      src.start();
      const out = await ctx.startRendering();
      return {
        inL: Array.from(l), inR: Array.from(r),
        outL: Array.from(out.getChannelData(0)),
        outR: Array.from(out.getChannelData(1)),
        rate, frames,
      };
    }"""

    def worst_against(run, turns, shift=0, gain=1.0):
        cos, sin = math.cos(turns * 2 * math.pi), math.sin(turns * 2 * math.pi)
        worst = 0.0
        n = run["frames"]
        for i in range(n // 2, n - shift - 1):
            want_l = (run["inL"][i] * cos - run["inR"][i] * sin) * gain
            want_r = (run["inL"][i] * sin + run["inR"][i] * cos) * gain
            worst = max(worst, abs(run["outL"][i + shift] - want_l),
                               abs(run["outR"][i + shift] - want_r))
        return worst

    at_rest = p.evaluate(RENDER, [0, "post", "merger"])
    check("at rest the rotation stage is not there at all",
          worst_against(at_rest, 0) == 0, "worst %.3g" % worst_against(at_rest, 0))

    for turns in (0.125, 0.3, -0.07):
        run = p.evaluate(RENDER, [turns, "post", "merger"])
        worst = worst_against(run, turns)
        check("at %+.3f of a turn the graph is the matrix the picture uses" % turns,
              worst < 1e-7, "worst %.3g" % worst)

    dry = p.evaluate(RENDER, [0.3, "pre", "merger"])
    check("and on the input side it does not turn at all",
          worst_against(dry, 0) == 0, "worst %.3g" % worst_against(dry, 0))

    print("\n--- what the rest of the chain does, since it was measured anyway ---")
    # Facts about monitoring rather than about rotation, and both worth writing
    # down: the latency figure the panel gives is the browser's own for the
    # output side, and this sits on top of it.
    #
    # Measured with an impulse rather than a tone. A 220 Hz sine repeats every
    # 200 samples, so correlating against one finds a maximum every period and
    # answers 264 or 465 or 665 depending on where it started looking - which
    # is exactly the kind of measurement that reads as a result.
    chainFacts = p.evaluate("""async () => {
      const rate = 44100, frames = rate / 4, at = 1000;
      const ctx = new OfflineAudioContext(2, frames, rate);
      const buffer = ctx.createBuffer(2, frames, rate);
      buffer.getChannelData(0)[at] = 0.5;
      buffer.getChannelData(1)[at] = 0.5;

      const src = ctx.createBufferSource();
      src.buffer = buffer;
      const chain = makeMonitorChain(ctx);
      src.connect(chain.input);
      const was = { at: state.monitorAt, on: state.filter.on, rotate: state.rotate };
      state.monitorAt = 'post'; state.filter.on = false;
      state.rotate = 0; state.rotateMod = 0;
      syncMonitor();
      state.monitorAt = was.at; state.filter.on = was.on; state.rotate = was.rotate;
      monitorChains.delete(chain);

      src.start();
      const out = await ctx.startRendering();
      const ch = out.getChannelData(0);
      let first = -1, peak = 0;
      for (let i = 0; i < ch.length; i++) {
        if (Math.abs(ch[i]) > 1e-4) { if (first < 0) first = i; }
        peak = Math.max(peak, Math.abs(ch[i]));
      }
      return { delay: first - at, peak, rate, sent: 0.5 };
    }""")
    ms = chainFacts["delay"] / chainFacts["rate"] * 1000
    print("    an impulse comes out %d samples (%.2f ms) later, at %.2f dB"
          % (chainFacts["delay"], ms,
             20 * math.log10(chainFacts["peak"] / chainFacts["sent"])))
    check("the limiter's lookahead is a few milliseconds, and it is not free",
          1 < ms < 15, "%.2f ms" % ms)

    # And it is not unity either. Chrome's compressor applies a makeup gain of
    # its own whatever the level, so monitoring is slightly louder than the
    # signal being monitored - measured on a steady tone, where an impulse
    # would only measure how much the compressor smears one.
    steady = p.evaluate(RENDER, [0, "post", "destination"])
    rms = lambda xs: math.sqrt(sum(v * v for v in xs) / len(xs))
    gain = rms(steady["outL"][5000:12000]) / rms(steady["inL"][5000:12000])
    print("    and a steady tone comes out %.2f dB louder than it went in"
          % (20 * math.log10(gain)))
    check("its makeup gain is a decibel or so, applied whatever the level",
          1.0 < gain < 1.4, "%.3f, or %.2f dB" % (gain, 20 * math.log10(gain)))

    # The rule that must not bend, with a new node in the way: a turn can put
    # 41% more into one channel than either started with, on top of whatever a
    # resonant filter is doing.
    loud = p.evaluate("""async () => {
      const rate = 44100, frames = rate / 2;
      const ctx = new OfflineAudioContext(2, frames, rate);
      const buffer = ctx.createBuffer(2, frames, rate);
      const l = buffer.getChannelData(0), r = buffer.getChannelData(1);
      for (let i = 0; i < frames; i++) {
        // Both channels alike and already at full scale, which is the worst
        // case for a 45 degree turn: it puts their sum into one of them.
        const v = Math.sin(2 * Math.PI * 400 * i / rate);
        l[i] = v; r[i] = v;
      }
      const src = ctx.createBufferSource();
      src.buffer = buffer;
      const hot = ctx.createGain();
      hot.gain.value = 4;                        // far past full scale
      const chain = makeMonitorChain(ctx);
      src.connect(hot); hot.connect(chain.input);

      const was = { rotate: state.rotate, at: state.monitorAt, on: state.filter.on,
                    res: state.filter.res, type: state.filter.type };
      state.rotate = 0.125; state.rotateMod = 0;
      state.monitorAt = 'post';
      state.filter.on = true; state.filter.type = 'lowpass'; state.filter.res = 100;
      syncMonitor();
      Object.assign(state.filter, { on: was.on, res: was.res, type: was.type });
      state.rotate = was.rotate; state.monitorAt = was.at;
      monitorChains.delete(chain);

      src.start();
      const out = await ctx.startRendering();
      let peak = 0;
      for (const ch of [out.getChannelData(0), out.getChannelData(1)]) {
        for (let i = 0; i < ch.length; i++) peak = Math.max(peak, Math.abs(ch[i]));
      }
      return peak;
    }""")
    check("resonance, a turn and four times full scale still cannot pass the clamp",
          loud <= 1.0, "peak %.4f at the destination" % loud)

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("rotation stays where it was scoped to")
