"""Rotation, mid/side as a case of it, and the line it is still not allowed
to cross.

That mid/side is what it always was, now that it is written as a rotation at
45 degrees with its gain and its flip kept explicit. That the X-Y figure is
turned before each lane is placed rather than after. That the same matrix
reaches the speakers, from the same numbers. And - the part that matters most
- where rotation is allowed to reach and where it is not.

That last one used to be simple: rotation touched the figure and nothing else.
It is now two rules rather than one, and both are asserted here.

On a stereo pair rotation is a transform on the SIGNAL. `capture` turns the
lanes before the trigger reads them, so Y-T, the figure, the trigger and the
speakers are one rotation rather than several that happen to agree. On
anything that is not a pair - a rack of stems, a band split, the lag lane's
delayed copy of one signal - it stays a display knob and turns the figure at
draw time, because there is no stereo image there to turn.

The per-lane measurements read their own tap, and its default is the signal
as it was before rotation. So a turned figure leaves peak, RMS, frequency,
THD and the correlation bar reading exactly what they read before - the same
arithmetic on the same samples, not a close copy. Two things are pinned there
whatever the tap says: the level meter, because a modulation source that moved
when a display knob moved would feed back into the picture through the matrix,
and the Clipping verdict, because clipping is a claim about the input.

One thing the window IS allowed to do is move. The trigger reads what is
drawn, which is what made its level a fraction of the screen in the first
place, so turning the figure can put the edge somewhere else and the
measurements are then over a different slice of the same signal. That is a
bench scope's behaviour rather than a leak, and it is checked as an algebraic
identity instead: whatever window came back, the measured lanes are that
window before it was turned.
"""
import math, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

# The page's own clipping threshold, and the one number this file needs from
# it: a rotation at 45 degrees is what pushes a pair over it without the input
# having gone anywhere near.
CLIP = 0.999

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

    print("\n--- rotation turns the pair, and the tap keeps the numbers still ---")
    # The scoping decision as it now stands, and it is two decisions rather
    # than one. Rotation IS a signal transform on a stereo pair - it reaches
    # the captured lanes, the trigger and the speakers. The per-lane
    # measurements read their own tap, and at its default that tap is the
    # signal before rotation, so every number is the one it was.
    #
    # These checks used to assert that rotation reached nothing at all. They
    # were rewritten rather than deleted, because what they were protecting is
    # still being protected: a measurement that quietly stops describing what
    # its label says.
    scope = p.evaluate("""() => {
      const was = { level: state.level, rotate: state.rotate, tap: state.measureAt };
      state.channels[0].fsDb = 0; state.channels[1].fsDb = 0;
      state.rotateMod = 0;
      state.measureAt = 'pre';
      state.running = false;
      /* The trigger put out of reach, so both captures fall back to the same
         fixed offset and the two windows are the same samples.

         With it live the rotation genuinely does move the window - the
         trigger reads what is drawn now, and a turned lane crosses the level
         somewhere else. That is a real consequence and it gets its own check
         below; mixing it in here would compare two different slices of the
         signal and call the difference a tap failure. */
      state.level = 2;

      state.rotate = 0;
      const flat = capture();
      const restingSame = flat.channels === flat.signal
                       && flat.measured === flat.signal && flat.turned === false;
      const before = measure(flat.measured[0], flat.rate);
      const corrBefore = correlation(flat.measured[0], flat.measured[1]);

      state.rotate = 0.3;
      const turned = capture();
      const after = measure(turned.measured[0], turned.rate);
      const corrAfter = correlation(turned.measured[0], turned.measured[1]);

      let drawnMoved = 0, measuredMoved = 0, matrix = 0;
      const { cos, sin } = turnOf(0.3);
      for (let i = 0; i < flat.channels[0].length; i++) {
        drawnMoved = Math.max(drawnMoved,
          Math.abs(flat.channels[0][i] - turned.channels[0][i]),
          Math.abs(flat.channels[1][i] - turned.channels[1][i]));
        measuredMoved = Math.max(measuredMoved,
          Math.abs(flat.measured[0][i] - turned.measured[0][i]),
          Math.abs(flat.measured[1][i] - turned.measured[1][i]));
        const l = flat.signal[0][i], r = flat.signal[1][i];
        matrix = Math.max(matrix,
          Math.abs(turned.channels[0][i] - (l * cos - r * sin)),
          Math.abs(turned.channels[1][i] - (l * sin + r * cos)));
      }

      // And with the tap moved, the same numbers follow what is drawn.
      state.measureAt = 'post';
      const post = capture();
      const postFollows = post.measured === post.channels;
      const postCorr = correlation(post.measured[0], post.measured[1]);

      state.measureAt = was.tap; state.rotate = was.rotate; state.level = was.level;
      state.running = true;
      return {
        restingSame, turnedFlag: turned.turned, drawnMoved, measuredMoved, matrix,
        peak: [before.peak, after.peak], rms: [before.rms, after.rms],
        corr: [corrBefore, corrAfter], postFollows, postCorr,
      };
    }""")
    check("at rest the block is one set of arrays and not three copies of it",
          scope["restingSame"], str(scope["restingSame"]))
    check("turning a pair turns what is drawn",
          scope["turnedFlag"] and scope["drawnMoved"] > 0.01,
          "moved by %.3f" % scope["drawnMoved"])
    check("and it is exactly the matrix the figure was drawn with",
          scope["matrix"] < 1e-7, "worst %.3g" % scope["matrix"])
    check("the measured lanes do not move one sample",
          scope["measuredMoved"] == 0, "worst %.3g" % scope["measuredMoved"])
    check("so peak and RMS are the same numbers, not close ones",
          scope["peak"][0] == scope["peak"][1] and scope["rms"][0] == scope["rms"][1],
          str(scope["peak"]) + " " + str(scope["rms"]))
    check("and so is the correlation under the goniometer",
          scope["corr"][0] == scope["corr"][1], str(scope["corr"]))
    # Identity rather than a number, and deliberately: this preset draws a
    # circle, and a circle is the one figure a rotation leaves every statistic
    # of alone. That the tap moves the NUMBERS is checked below, on a pair
    # that is not circular - which is the sort of thing a test can be fooled
    # by once and then believed forever.
    check("point the tap at the turned signal and it reads what is drawn",
          scope["postFollows"], str(scope["postFollows"]))

    # The window the trigger picks IS allowed to move - it reads what is
    # drawn, which is what made the level a fraction of the screen in the
    # first place. What may not happen is the measured lanes being anything
    # other than that window before it was turned, and that is an algebraic
    # statement rather than a comparison against a second capture: turn the
    # measured pair by the angle in force and the drawn pair has to come back.
    live = p.evaluate("""() => {
      const wasLevel = state.level;
      state.running = false;
      state.measureAt = 'pre';
      /* A quarter turn, so the two lanes are as far apart as a rotation can
         put them: lane one of what is drawn is the negated second lane of
         what is measured. At three tenths of a turn they came out 0.31 and
         0.34, which is a real difference and too small to assert against
         without picking a threshold to fit it. */
      state.rotate = 0.25; state.rotateMod = 0;
      /* A level worth finding. At nought the check would be satisfied by any
         sample that happened to sit near the axis, which on a sine is one in
         every few - a test that passes whatever the code does. */
      state.level = 0.3;
      const f = capture();
      const { cos, sin } = turnOf(0.25);
      let worst = 0;
      for (let i = 0; i < f.channels[0].length; i++) {
        const l = f.measured[0][i], r = f.measured[1][i];
        worst = Math.max(worst, Math.abs(f.channels[0][i] - (l * cos - r * sin)),
                                Math.abs(f.channels[1][i] - (l * sin + r * cos)));
      }
      const at = f.triggered ? f.channels[state.trigSource][f.pre] : null;
      const measuredAt = f.triggered ? f.measured[state.trigSource][f.pre] : null;
      state.rotate = 0;
      state.level = wasLevel;
      state.running = true;
      return { worst, triggered: f.triggered, at, measuredAt, want: f.levelAt };
    }""")
    check("whatever window the trigger picks, the measured lanes are it unturned",
          live["worst"] < 1e-6, "worst %.3g" % live["worst"])
    check("and the trigger fires on what is drawn, not on what is measured",
          live["triggered"] and abs(live["at"] - live["want"]) < 0.02
          and abs(live["measuredAt"] - live["want"]) > 0.05,
          "drawn %.4f, measured %.4f, wanted %.4f"
          % (live["at"] or 0, live["measuredAt"] or 0, live["want"]))

    # Two things pinned to the signal whatever the tap says, and both for the
    # same reason: one of them feeds back into the picture and the other is a
    # claim about the input rather than about the display.
    #
    # Both lanes carry the same signal at 0.72 from here on, which no rotation
    # can clip on its own - but at 45 degrees the pair comes out 41 per cent
    # taller, which does. The input is the same input either way.
    pinned = p.evaluate("""() => {
      const was = { rotate: state.rotate, tap: state.measureAt, amp: el.amp.value,
                    phase: el.phase.value };
      state.running = true;
      el.phase.value = '0'; el.phase.dispatchEvent(new Event('input'));
      el.amp.value = '72'; el.amp.dispatchEvent(new Event('input'));
      return was;
    }""")
    p.wait_for_timeout(400)

    # The verdict, with the scope RUNNING. This is worth spelling out because
    # the first version of this check was stopped, and a stopped scope reports
    # "held" before it has looked at a single sample - so every assertion
    # below passed no matter what the code did. The control at the end is what
    # says the clipping branch can be reached at all.
    verdicts = p.evaluate("""() => {
      state.running = true;
      state.measureAt = 'pre';
      state.rotate = 0; state.rotateMod = 0;
      const flat = capture();
      let inPeak = 0;
      for (let i = 0; i < flat.signal[0].length; i++) {
        inPeak = Math.max(inPeak, Math.abs(flat.signal[0][i]), Math.abs(flat.signal[1][i]));
      }
      writeReadout(flat);
      const restVerdict = el.verdict.dataset.state;
      const restLine = el.readoutDetail.textContent;

      state.rotate = -0.125;                       // 45 degrees, the M/S angle
      const turned = capture();
      let outPeak = 0;
      for (let i = 0; i < turned.channels[0].length; i++) {
        outPeak = Math.max(outPeak, Math.abs(turned.channels[0][i]),
                                    Math.abs(turned.channels[1][i]));
      }
      writeReadout(turned);
      const turnedVerdict = el.verdict.dataset.state;
      const peakPre = measure(turned.measured[0], turned.rate).peak;

      state.measureAt = 'post';
      const tapped = capture();
      writeReadout(tapped);
      const tappedVerdict = el.verdict.dataset.state;
      const tappedLine = el.readoutDetail.textContent;
      const peakPost = measure(tapped.measured[0], tapped.rate).peak;

      state.measureAt = 'pre';
      state.rotate = 0;
      return { inPeak, outPeak, restVerdict, turnedVerdict, tappedVerdict,
               restLine, tappedLine, peakPre, peakPost };
    }""")
    check("the rotation really did push the drawn pair past the converter",
          verdicts["inPeak"] < CLIP and verdicts["outPeak"] > CLIP,
          "input %.3f, drawn %.3f" % (verdicts["inPeak"], verdicts["outPeak"]))
    check("and the verdict still says the input is not clipping",
          verdicts["restVerdict"] == verdicts["turnedVerdict"] != "clipping",
          "%s then %s" % (verdicts["restVerdict"], verdicts["turnedVerdict"]))
    check("it says so with the tap moved as well",
          verdicts["tappedVerdict"] != "clipping", verdicts["tappedVerdict"])
    # Here the numbers really can move, because this pair is not a circle: two
    # copies of one signal turned by 45 degrees come out 41 per cent taller.
    check("and with the tap moved, peak is about the turned signal",
          abs(verdicts["peakPre"] - verdicts["inPeak"]) < 1e-6
          and verdicts["peakPost"] > verdicts["peakPre"] * 1.3,
          "%.4f at the default, %.4f tapped, input %.4f"
          % (verdicts["peakPre"], verdicts["peakPost"], verdicts["inPeak"]))
    check("the readout says nothing about rotation at the tap's default",
          "post-rotation" not in verdicts["restLine"], verdicts["restLine"][:70])
    check("and names it when the numbers are about the turned signal",
          "post-rotation" in verdicts["tappedLine"], verdicts["tappedLine"][:70])

    # The control. Without it the three verdict checks above are satisfied by
    # a page that never says "Clipping" about anything.
    control = p.evaluate("""() => {
      const amp = el.amp.value;
      el.amp.value = '130'; el.amp.dispatchEvent(new Event('input'));
      return amp;
    }""")
    p.wait_for_timeout(400)
    loud_verdict = p.evaluate("""() => {
      writeReadout(capture());
      return el.verdict.dataset.state;
    }""")
    check("and an input that really is over the top does say so",
          loud_verdict == "clipping", loud_verdict)
    p.evaluate("""(amp) => {
      el.amp.value = amp; el.amp.dispatchEvent(new Event('input'));
    }""", control)
    p.wait_for_timeout(300)

    # The level meter, from two frames of the same samples - so the scope is
    # stopped for this one and the verdict is not being read.
    env = p.evaluate("""() => {
      state.running = false;
      state.rotate = 0; state.rotateMod = 0;
      const flat = capture();
      state.rotate = -0.125;
      const turned = capture();
      /* Run to convergence rather than reaching inside the follower: a huge
         elapsed makes the one-pole settle on the block's RMS exactly, so the
         two runs are comparable. */
      updateEnvelope(flat, 1e6);
      const envFlat = MOD_SOURCES.get('env.live').value();
      updateEnvelope(turned, 1e6);
      const envTurned = MOD_SOURCES.get('env.live').value();
      state.rotate = 0;
      state.running = true;
      return { envFlat, envTurned, turnedFlag: turned.turned };
    }""")
    check("the level meter does not move when the figure turns",
          env["turnedFlag"] and env["envFlat"] == env["envTurned"],
          "%.9f against %.9f" % (env["envFlat"], env["envTurned"]))

    # And the figure is drawn from the lanes as they came out of `capture`,
    # not turned a second time on the way to the paper. Nothing else catches
    # that: the captured lanes would be right, the speakers would be right,
    # every number would be right, and the picture would be at twice the angle
    # the knob says. A line rather than the circle the preset draws, because a
    # circle has no angle to be wrong about.
    twice = p.evaluate("""(shape) => {
      const was = { display: state.display, rotate: state.rotate,
                    persist: state.persistence };
      state.running = false;
      state.display = 'xy';
      state.persistence = 0;
      state.channels[0].fsDb = 0; state.channels[1].fsDb = 0;
      state.channels[0].offset = 0; state.channels[1].offset = 0;
      state.zoom = 1; state.zoomStep = 0; state.zoomMod = 0;
      state.rotate = 1 / 12;                       // 30 degrees
      state.rotateMod = 0;

      const f = capture();
      drawXY(f, fitCanvas(el.trace), 16);
      const n = Math.min(2000, beamX.length);
      const xs = [], ys = [];
      for (let i = 0; i < n; i++) {
        if (beamX[i] === 0 && beamY[i] === 0) break;
        xs.push(beamX[i]); ys.push(-beamY[i]);
      }
      const shapeOf = eval(shape);
      const onPaper = shapeOf(xs, ys);
      const inBlock = shapeOf(Array.from(f.channels[0]), Array.from(f.channels[1]));
      const unturned = shapeOf(Array.from(f.signal[0]), Array.from(f.signal[1]));

      state.display = was.display; state.rotate = was.rotate;
      state.persistence = was.persist;
      state.running = true;
      return { onPaper: onPaper.angle, inBlock: inBlock.angle,
               unturned: unturned.angle, ratio: onPaper.ratio, turned: f.turned };
    }""", SHAPE)
    # The principal axis is only defined to within 180 degrees, so every
    # comparison here is folded into that.
    fold = lambda d: abs((d + 90) % 180 - 90)
    check("the figure on the paper is the block, not the block turned again",
          twice["turned"] and fold(twice["onPaper"] - twice["inBlock"]) < 2,
          "paper %.1f, block %.1f" % (twice["onPaper"], twice["inBlock"]))
    check("and it did turn, by the thirty degrees the knob was set to",
          abs(fold(twice["onPaper"] - twice["unturned"]) - 30) < 3,
          "%.1f degrees from the signal, ratio %.3f"
          % (fold(twice["onPaper"] - twice["unturned"]), twice["ratio"]))

    p.evaluate("""(was) => {
      el.phase.value = was.phase; el.phase.dispatchEvent(new Event('input'));
      el.amp.value = was.amp; el.amp.dispatchEvent(new Event('input'));
      state.rotate = was.rotate; state.measureAt = was.tap;
    }""", pinned)
    p.wait_for_timeout(300)

    print("\n--- and on anything that is not a stereo pair, it is a display knob ---")
    # The rule, as a truth table taken from the page's own predicate. A rack
    # is several real signals; the lag lane's second channel is the first one
    # delayed. Neither is a stereo image, and the speakers are still being
    # handed left against right in both cases.
    rule = p.evaluate("""() => {
      const src = state.source, lagOn = state.lagOn;
      const out = { pair: rotatesSignal() };
      state.source = { channels: 2, lanes: [{ name: 'a' }, { name: 'b' }] };
      out.rack = rotatesSignal();
      state.source = { channels: 1 };
      out.mono = rotatesSignal();
      state.source = src;
      state.lagOn = true; state.lagAuto = false;
      out.lag = rotatesSignal();
      state.lagOn = lagOn; state.lagAuto = true;
      return out;
    }""")
    check("a stereo pair turns; a rack, a mono input and the lag lane do not",
          rule["pair"] and not rule["rack"] and not rule["mono"] and not rule["lag"],
          str(rule))

    # And the figure still turns there, at draw time, exactly as it always
    # did. Without this the widening could have quietly removed rotation from
    # every rack in the page and no other check would have noticed.
    rack = p.evaluate("""(shape) => {
      const was = { display: state.display, rotate: state.rotate,
                    lagOn: state.lagOn, auto: state.lagAuto, persist: state.persistence };
      state.running = false;
      state.display = 'xy';
      state.persistence = 0;
      state.lagOn = true; state.lagAuto = false; state.lagMs = 5;
      const active = lagActive();

      const read = () => {
        const n = Math.min(2000, beamX.length);
        const xs = [], ys = [];
        for (let i = 0; i < n; i++) {
          if (beamX[i] === 0 && beamY[i] === 0) break;
          xs.push(beamX[i]); ys.push(-beamY[i]);
        }
        return eval(shape)(xs, ys);
      };

      state.rotate = 0; state.rotateMod = 0;
      const flat = capture();
      const untouched = flat.channels === flat.signal && flat.turned === false;
      drawXY(flat, fitCanvas(el.trace), 16);
      const before = read();

      state.rotate = 0.25;
      const turned = capture();
      const stillUntouched = turned.channels === turned.signal && turned.turned === false;
      drawXY(turned, fitCanvas(el.trace), 16);
      const after = read();

      state.display = was.display; state.rotate = was.rotate;
      state.lagOn = was.lagOn; state.lagAuto = was.auto;
      state.persistence = was.persist;
      state.running = true;
      return { active, untouched, stillUntouched,
               before: before.angle, after: after.angle,
               ratio: [before.ratio, after.ratio] };
    }""", SHAPE)
    check("the lag lane is a lane and the capture is left alone",
          rack["active"] and rack["untouched"] and rack["stillUntouched"], str(rack))
    # A quarter turn is 90 degrees, and the principal axis is only defined to
    # within 180, so the angle comes back folded. What matters is that it moved
    # by a quarter turn and the figure kept its shape.
    moved = abs(((rack["after"] - rack["before"]) + 90) % 180 - 90)
    check("but the figure itself turns, at draw time, as it always did",
          abs(moved - 90) < 8 or moved > 82,
          "%.1f degrees, ratio %.3f then %.3f"
          % (moved, rack["ratio"][0], rack["ratio"][1]))

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
    RENDER = """async ([turns, at, tap, lag]) => {
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
                    at: state.monitorAt, on: state.filter.on,
                    lagOn: state.lagOn, auto: state.lagAuto };
      state.rotate = turns; state.rotateMod = 0;
      state.monitorAt = at; state.filter.on = false;
      // `lag` puts the page into the one state where rotation is a display
      // knob, to check the speakers agree about that too.
      if (lag) { state.lagOn = true; state.lagAuto = false; }
      syncMonitor();                              // the page's own setter
      state.rotate = was.rotate; state.rotateMod = was.mod;
      state.monitorAt = was.at; state.filter.on = was.on;
      state.lagOn = was.lagOn; state.lagAuto = was.auto;
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

    at_rest = p.evaluate(RENDER, [0, "post", "merger", False])
    check("at rest the rotation stage is not there at all",
          worst_against(at_rest, 0) == 0, "worst %.3g" % worst_against(at_rest, 0))

    for turns in (0.125, 0.3, -0.07):
        run = p.evaluate(RENDER, [turns, "post", "merger", False])
        worst = worst_against(run, turns)
        check("at %+.3f of a turn the graph is the matrix the picture uses" % turns,
              worst < 1e-7, "worst %.3g" % worst)

    dry = p.evaluate(RENDER, [0.3, "pre", "merger", False])
    check("and on the input side it does not turn at all",
          worst_against(dry, 0) == 0, "worst %.3g" % worst_against(dry, 0))

    # And the other half of the rule the picture obeys: where rotation is a
    # display knob, the speakers must not turn either. Otherwise a rack would
    # have its stems mixed into each other by a control that, on screen, only
    # tilts a figure.
    lagged = p.evaluate(RENDER, [0.3, "post", "merger", True])
    check("and where the figure is only a figure, the speakers do not turn",
          worst_against(lagged, 0) == 0, "worst %.3g" % worst_against(lagged, 0))

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
    steady = p.evaluate(RENDER, [0, "post", "destination", False])
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
print("rotation turns the pair, and the numbers stay about the signal")
