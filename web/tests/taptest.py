"""The two taps, and the block they straddle.

`Screen reads` and `Speakers get` are two switches over one ordered block of
transforms - the filter, the AC coupling and the X-Y rotation - and the four
combinations of them are four different instruments. Both shaped is the
ordinary sense. Screen shaped and speakers on the input is the block as
something to look through. Screen on the input and speakers shaped is watching
what you are feeding it.

They did not straddle the same block until now, and that is what this suite
was written for. The screen's switch took out the filter and nothing else,
while the speakers' took out the filter, the coupling and the rotation: so
"Input" meant one thing to the eyes and another to the ears, on a page whose
whole argument is that they are the same block. Nothing said so, because
nothing tested the combinations.

The lag is deliberately not in it. The speakers have no lag to bypass - that is
C1's last unbuilt row - and a switch that took something out of one side only
is the thing being fixed rather than a thing to add.
"""
import math, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

# The drawn cloud's shape, as `rotatetest.py` measures it: the canvas mapping
# is isotropic with y flipped, so the principal angle comes through negated and
# the caller undoes that by pushing -beamY.
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
  return 0.5 * Math.atan2(2 * sxy / n, (sxx - syy) / n) * 180 / Math.PI;
}"""

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


# A stereo pair with a DC offset on it and a little high-frequency content, so
# all three transforms have something to do: the coupling has an offset to
# remove, the low pass has a harmonic to take off, and the rotation has two
# genuinely different channels to mix.
STANDIN = """(rate, capacity, offset) => {
  const buf = [new Float32Array(capacity), new Float32Array(capacity)];
  for (let i = 0; i < capacity; i++) {
    const t = i / rate;
    buf[0][i] = offset + 0.35 * Math.sin(2 * Math.PI * 220 * t)
                       + 0.12 * Math.sin(2 * Math.PI * 3300 * t);
    buf[1][i] = offset + 0.30 * Math.cos(2 * Math.PI * 220 * t);
  }
  return {
    kind: 'tone', settings: null,
    get sampleRate() { return rate; },
    get capacity() { return capacity; },
    get channels() { return 2; },
    tick() {}, stop() {}, setMonitor() { return false; },
    describe: () => 'stand-in',
    getLatestWindow: (n) => buf.map((b) => b.subarray(Math.max(0, capacity - n))),
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
    p.evaluate("(src) => { window.__standin = eval(src); }", STANDIN)

    print("\n--- what the screen's switch takes out ---")
    # Every transform turned on at once, and then the switch thrown. Each of
    # the three has a fingerprint of its own: the coupling shows in the mean,
    # the filter in the high harmonic, the rotation in how much of lane two is
    # in lane one.
    taps = p.evaluate("""() => {
      const was = { src: state.source, run: state.running, see: state.analyseAt,
                    ac: state.channels.map((c) => c.ac), on: state.filter.on,
                    type: state.filter.type, cutoff: state.filter.cutoff,
                    rotate: state.rotate, level: state.level, tb: state.timebase };
      state.running = false;
      state.timebase = 5;
      state.source = window.__standin(44100, 32768, 0.25);
      state.channels[0].ac = true; state.channels[1].ac = true;
      state.filter.on = true; state.filter.type = 'lowpass';
      state.filter.cutoff = 400;                  // well under the 3.3 kHz partial
      state.rotate = 0.125; state.rotateMod = 0;
      state.level = 2;                            // out of reach, same window both ways

      const look = () => {
        const f = capture();
        const a = f.channels[0], b2 = f.channels[1];
        let mean = 0, energy = 0, cross = 0, self = 0;
        for (let i = 0; i < a.length; i++) {
          mean += a[i];
          energy += a[i] * a[i];
          cross += a[i] * b2[i];
          self += b2[i] * b2[i];
        }
        return { mean: mean / a.length, rms: Math.sqrt(energy / a.length),
                 turned: f.turned,
                 // How much of the two lanes is the same signal: a 45 degree
                 // rotation of a quadrature pair leaves this near nought, and
                 // not rotating a DC-coupled pair leaves it near one.
                 corr: cross / Math.sqrt(Math.max(1e-12, energy * self)) };
      };

      state.analyseAt = 'post';
      const shaped = look();
      state.analyseAt = 'pre';
      const input = look();

      Object.assign(state, { source: was.src, running: was.run, analyseAt: was.see,
                             rotate: was.rotate, level: was.level, timebase: was.tb });
      state.filter.on = was.on; state.filter.type = was.type;
      state.filter.cutoff = was.cutoff;
      state.channels.forEach((c, i) => { c.ac = was.ac[i]; });
      return { shaped, input };
    }""")
    print("    shaped: mean %+.4f, rms %.4f, turned %s"
          % (taps["shaped"]["mean"], taps["shaped"]["rms"], taps["shaped"]["turned"]))
    print("    input:  mean %+.4f, rms %.4f, turned %s"
          % (taps["input"]["mean"], taps["input"]["rms"], taps["input"]["turned"]))
    check("on the input the offset is still there",
          abs(taps["input"]["mean"] - 0.25) < 0.01,
          "%+.4f, and the source was given 0.25" % taps["input"]["mean"])
    check("and the coupling takes it out on the shaped side",
          abs(taps["shaped"]["mean"]) < 0.01,
          "%+.4f" % taps["shaped"]["mean"])
    check("the rotation reaches the shaped side and not the input",
          taps["shaped"]["turned"] is True and taps["input"]["turned"] is False,
          "%s then %s" % (taps["shaped"]["turned"], taps["input"]["turned"]))

    # The filter on its own, with the other two out of the way, so the check
    # is about the filter rather than about three things at once.
    just_filter = p.evaluate("""() => {
      const was = { src: state.source, run: state.running, see: state.analyseAt,
                    ac: state.channels.map((c) => c.ac), on: state.filter.on,
                    type: state.filter.type, cutoff: state.filter.cutoff,
                    rotate: state.rotate, level: state.level, tb: state.timebase };
      state.running = false;
      state.timebase = 5;
      state.source = window.__standin(44100, 32768, 0);
      state.channels[0].ac = false; state.channels[1].ac = false;
      state.rotate = 0;
      state.level = 2;
      state.filter.on = true; state.filter.type = 'lowpass'; state.filter.cutoff = 400;

      /* The 3.3 kHz partial, as the height of its own bin. A low pass an
         octave and a half below it has to take most of it away, and nothing
         else in this signal lives up there. */
      const partial = () => {
        const f = capture();
        computeSpectrum(f.channels[0]);
        const bin = Math.round(3300 / (f.rate / FFT_SIZE));
        let best = -Infinity;
        for (let i = bin - 2; i <= bin + 2; i++) best = Math.max(best, spectrumDb[i]);
        return best;
      };
      state.analyseAt = 'post';
      const shaped = partial();
      state.analyseAt = 'pre';
      const input = partial();

      Object.assign(state, { source: was.src, running: was.run, analyseAt: was.see,
                             rotate: was.rotate, level: was.level, timebase: was.tb });
      state.filter.on = was.on; state.filter.type = was.type;
      state.filter.cutoff = was.cutoff;
      state.channels.forEach((c, i) => { c.ac = was.ac[i]; });
      return { shaped, input };
    }""")
    print("    the 3.3 kHz partial: %.1f dB on the input, %.1f dB shaped"
          % (just_filter["input"], just_filter["shaped"]))
    check("and the filter still does what it always did",
          just_filter["input"] - just_filter["shaped"] > 20,
          "%.1f dB taken off" % (just_filter["input"] - just_filter["shaped"]))

    print("\n--- and it says which one you are looking at ---")
    words = p.evaluate("""async () => {
      const was = { see: state.analyseAt, hear: state.monitorAt, on: state.filter.on,
                    rotate: state.rotate, sound: state.genSound,
                    ac: state.channels.map((c) => c.ac) };
      const read = () => { writeReadout(capture()); return el.readoutDetail.textContent; };

      state.filter.on = false; state.rotate = 0;
      state.channels.forEach((c) => { c.ac = false; });
      state.analyseAt = 'post'; state.monitorAt = 'pre';
      const bare = read();
      // Nothing in the block AND the screen on the input: still nothing to
      // say, which is the case the first version of this got wrong.
      state.analyseAt = 'pre';
      const bareOnInput = read();
      state.analyseAt = 'post';

      state.filter.on = true;
      const filtered = read();

      state.channels.forEach((c) => { c.ac = true; });
      const coupled = read();

      state.analyseAt = 'pre';
      const onInput = read();
      state.analyseAt = 'post';

      /* And the mirror. It needs real speakers, because the speakers' switch
         changes nothing when there is no chain to change - so the generator is
         actually switched on for this one. */
      state.genSound = true;
      await applyGeneratorSound();
      const audible = state.source.audible ? state.source.audible() : false;
      state.monitorAt = 'pre';
      const speakersDry = read();
      state.monitorAt = 'post';
      const bothShaped = read();
      state.genSound = false;
      await applyGeneratorSound();
      // The same switch position, with nothing listening: no note, because
      // there is nothing on the other side of the mismatch.
      state.monitorAt = 'pre';
      const speakersDrySilent = read();

      state.analyseAt = was.see; state.monitorAt = was.hear;
      state.filter.on = was.on; state.rotate = was.rotate;
      state.genSound = was.sound;
      state.channels.forEach((c, i) => { c.ac = was.ac[i]; });
      return { bare, bareOnInput, filtered, coupled, onInput,
               audible, speakersDry, bothShaped, speakersDrySilent };
    }""")
    for name in ("bare", "bareOnInput", "filtered", "coupled", "onInput",
                 "speakersDry", "bothShaped", "speakersDrySilent"):
        print("    %-18s %s" % (name, words[name][:66]))
    # It used to say "post-filter" whenever the switch was on the shaped side
    # and the filter was on, which is a claim about a stage rather than about
    # what is in force. With nothing switched on there is nothing to say.
    check("with nothing shaping it, the line says nothing about shaping",
          "post-" not in words["bare"] and "AC " not in words["bare"],
          words["bare"][:60])
    check("the filter names itself",
          "post-filter" in words["filtered"], words["filtered"][:60])
    check("the coupling names its corner",
          "AC " in words["coupled"], words["coupled"][:60])
    check("and on the input it says so, and stops naming what it is not doing",
          "screen on the input" in words["onInput"]
          and "post-" not in words["onInput"] and "AC " not in words["onInput"],
          words["onInput"][:60])
    check("with nothing in the block, being on the input is not worth saying",
          "screen on the input" not in words["bareOnInput"],
          words["bareOnInput"][:60])

    # The mirror, which the first version of this had no note for at all: a
    # sweep on the graticule over a plain tone is the same confusion the other
    # way round.
    check("the generator really was sounding for the mirror case",
          words["audible"] is True, str(words["audible"]))
    check("speakers on the input is named too, not only the screen",
          "speakers on the input" in words["speakersDry"], words["speakersDry"][:66])
    check("and with both on the shaped side there is no mismatch to name",
          "speakers on the input" not in words["bothShaped"]
          and "screen on the input" not in words["bothShaped"],
          words["bothShaped"][:66])
    check("and with nothing listening, the speakers' switch is not worth a note",
          "speakers on the input" not in words["speakersDrySilent"],
          words["speakersDrySilent"][:66])

    # And the FIGURE, which is drawn rather than captured and so obeys the
    # switch in a different place. With a stereo pair the lanes arrive turned
    # or they do not; `drawXY` turns them itself when they did not, and on the
    # input side there is nothing to orient - so it must not. Nothing above
    # catches that, because nothing above draws anything.
    figure = p.evaluate("""(shape) => {
      const was = { src: state.source, run: state.running, see: state.analyseAt,
                    rotate: state.rotate, display: state.display, level: state.level,
                    persist: state.persistence, tb: state.timebase,
                    fs: state.channels.map((c) => c.fsDb),
                    off: state.channels.map((c) => c.offset) };
      state.running = false;
      state.display = 'xy';
      state.persistence = 0;
      state.timebase = 5;
      state.level = 2;
      state.channels.forEach((c) => { c.fsDb = 0; c.offset = 0; });
      state.zoom = 1; state.zoomStep = 0; state.zoomMod = 0;
      // A LINE rather than the quadrature pair above: a circle is the one
      // figure whose angle a rotation leaves alone, so it could not tell the
      // two cases apart.
      const rate = 44100, capacity = 32768;
      const buf = [new Float32Array(capacity), new Float32Array(capacity)];
      for (let i = 0; i < capacity; i++) {
        const v = 0.4 * Math.sin(2 * Math.PI * 220 * i / rate);
        buf[0][i] = v; buf[1][i] = v;             // a diagonal at 45 degrees
      }
      state.source = {
        kind: 'tone', settings: null,
        get sampleRate() { return rate; },
        get capacity() { return capacity; },
        get channels() { return 2; },
        tick() {}, stop() {}, setMonitor() { return false; },
        describe: () => 'line',
        getLatestWindow: (n) => buf.map((b) => b.subarray(Math.max(0, capacity - n))),
      };
      state.rotate = 1 / 12;                       // 30 degrees
      state.rotateMod = 0;

      const shapeOf = eval(shape);
      const drawnAngle = () => {
        const f = capture();
        drawXY(f, fitCanvas(el.trace), 16);
        const n = Math.min(2000, beamX.length);
        const xs = [], ys = [];
        for (let i = 0; i < n; i++) {
          if (beamX[i] === 0 && beamY[i] === 0) break;
          xs.push(beamX[i]); ys.push(-beamY[i]);
        }
        return { paper: shapeOf(xs, ys),
                 block: shapeOf(Array.from(f.channels[0]),
                                Array.from(f.channels[1])),
                 turned: f.turned };
      };

      state.analyseAt = 'post';
      const shaped = drawnAngle();
      state.analyseAt = 'pre';
      const input = drawnAngle();

      Object.assign(state, { source: was.src, running: was.run, analyseAt: was.see,
                             rotate: was.rotate, display: was.display,
                             level: was.level, persistence: was.persist,
                             timebase: was.tb });
      state.channels.forEach((c, i) => { c.fsDb = was.fs[i]; c.offset = was.off[i]; });
      return { shaped, input };
    }""", SHAPE)
    fold = lambda d: abs((d + 90) % 180 - 90)
    print("    shaped: paper %.1f, block %.1f; input: paper %.1f, block %.1f"
          % (figure["shaped"]["paper"], figure["shaped"]["block"],
             figure["input"]["paper"], figure["input"]["block"]))
    check("shaped, the figure is turned by the thirty degrees asked for",
          figure["shaped"]["turned"] is True
          and abs(fold(figure["shaped"]["paper"] - 45) - 30) < 4,
          "%.1f degrees off the diagonal" % fold(figure["shaped"]["paper"] - 45))
    check("on the input the figure is not turned at all",
          figure["input"]["turned"] is False
          and fold(figure["input"]["paper"] - 45) < 4,
          "%.1f degrees off the diagonal" % fold(figure["input"]["paper"] - 45))
    check("and either way the paper is the block it was drawn from",
          fold(figure["shaped"]["paper"] - figure["shaped"]["block"]) < 3
          and fold(figure["input"]["paper"] - figure["input"]["block"]) < 3,
          "%.1f and %.1f apart"
          % (fold(figure["shaped"]["paper"] - figure["shaped"]["block"]),
             fold(figure["input"]["paper"] - figure["input"]["block"])))

    print("\n--- the four combinations are four instruments ---")
    # The two switches are independent, which is the whole reason there are two
    # of them. Asserted on the graph rather than on the state: the monitor
    # chain is where the speakers' switch actually lands.
    RENDER = """async ([see, hear]) => {
      const rate = 44100, frames = Math.round(rate * 0.25);
      const ctx = new OfflineAudioContext(2, frames, rate);
      const buffer = ctx.createBuffer(2, frames, rate);
      const l = buffer.getChannelData(0), r = buffer.getChannelData(1);
      for (let i = 0; i < frames; i++) {
        l[i] = 0.3 * Math.sin(2 * Math.PI * 220 * i / rate);
        r[i] = 0.3 * Math.cos(2 * Math.PI * 137 * i / rate);
      }
      const src = ctx.createBufferSource();
      src.buffer = buffer;
      const chain = makeMonitorChain(ctx);
      src.connect(chain.input);
      chain.merger.disconnect();
      chain.merger.connect(ctx.destination);      // before the limiter

      const was = { see: state.analyseAt, hear: state.monitorAt,
                    rotate: state.rotate, on: state.filter.on };
      state.analyseAt = see; state.monitorAt = hear;
      state.rotate = 0.125; state.rotateMod = 0; state.filter.on = false;
      syncMonitor();
      state.analyseAt = was.see; state.monitorAt = was.hear;
      state.rotate = was.rotate; state.filter.on = was.on;
      monitorChains.delete(chain);

      src.start();
      const out = await ctx.startRendering();
      const a = out.getChannelData(0);
      /* Floored, because `frames / 2` is not an integer and `a[5512.5]` is
         `undefined`: every comparison came out NaN, `Math.max` carried the NaN
         along, and all four combinations reported "something else" with the
         graph behaving perfectly. */
      const from = Math.floor(frames / 2);
      const cos = Math.cos(0.125 * 2 * Math.PI), sin = Math.sin(0.125 * 2 * Math.PI);
      let worst = 0, flat = 0;
      for (let i = from; i < frames - 1; i++) {
        worst = Math.max(worst, Math.abs(a[i] - (l[i] * cos - r[i] * sin)));
        flat = Math.max(flat, Math.abs(a[i] - l[i]));
      }
      // Both have to be finite, or "not turned" and "arithmetic that went
      // wrong" are the same answer.
      return { turned: worst < 1e-6, untouched: flat === 0,
               worst, flat, sane: isFinite(worst) && isFinite(flat) };
    }"""
    grid = {}
    for see in ("pre", "post"):
        for hear in ("pre", "post"):
            grid[(see, hear)] = p.evaluate(RENDER, [see, hear])
    for (see, hear), got in grid.items():
        print("    screen %-4s speakers %-4s: speakers %s"
              % (see, hear, "turned" if got["turned"] else
                 "untouched" if got["untouched"] else "something else"))
    check("every combination rendered a real number",
          all(g["sane"] for g in grid.values()),
          str({str(k): (v["worst"], v["flat"]) for k, v in grid.items()}))
    check("the speakers follow their own switch, whatever the screen's says",
          grid[("pre", "post")]["turned"] and grid[("post", "post")]["turned"]
          and grid[("pre", "pre")]["untouched"] and grid[("post", "pre")]["untouched"],
          str({str(k): (round(v["worst"], 9), round(v["flat"], 9))
               for k, v in grid.items()}))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("both switches straddle the same block")
