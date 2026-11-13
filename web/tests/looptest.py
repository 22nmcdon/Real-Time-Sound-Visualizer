"""Stage E3: the loop closed through the sound, and held to its bounds.

E1 refused every destination that could add energy. E3 lets the loop through
them, and what stands in place of the refusal is a set of defences that only
work together: each source's reach, the slew on every picture source, ONE total
per destination for everything the loop pushes into it, and the limiter last in
every chain. So what is checked:

- the total, on a picture destination and on a generator parameter, with three
  picture sources forced to full: a destination moves by the total's bound and
  not by three times a source's reach - measured on the generator by the pitch
  it actually produces, not by the routes it was given;
- that a source which is NOT the loop is not caught in the loop's bound;
- boredom: it rises while the picture is stuck, stays under its own reach,
  drains when the picture moves, and cannot wind up;
- that the photocell reaches the sound itself, through the worklet;
- and the plan's stability run: every picture source routed at the most it is
  allowed onto the most sensitive destinations, and the picture stage (P3) at
  its top as well, from silence and from a full-scale figure, and once more
  with Scan (P7a) at its top beside it all; then Scan at its top with every
  note striking the screen at full (P7b) during fast repeated notes, and a
  split with both layers at Scan's top, each reading the other's picture -
  two feedback paths feeding each other; and the phaser (P8e) at its top
  with its resonance at its most, a feedback inside the loop. Run headless,
  with every bound checked every tenth of a second - and checked to have
  MOVED, because a loop that did nothing would pass any bound there is.

The plan asked for 60 seconds. It is 30 from each seed, 60 in all, because the
suite is run while working and a minute per seed would double this file.
"""
# On ?brain=js (5m): this suite reads the page's own brain - its generator's
# routes and worklet - which core/tests/parity.py holds the instrument to,
# sample for sample. The instrument, the site's default since 5m, is
# braintest.py's and hosttest.py's.
import math, os, sys
from playwright.sync_api import sync_playwright
import corpus

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
SECONDS = float(os.environ.get("LOOP_SECONDS", "30"))

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
    p.goto(f"file://{ART}/scope.html?brain=js"); p.wait_for_timeout(700)
    corpus.old_opening(p)  # the opening it was written against (P8h)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)
    p.evaluate("() => { setDisplay('xy'); genSet('shape', 'sine'); el.photoButton.click(); }")
    # A note held in Mono throughout, and struck again at the top of every
    # stability run, which lets go at its end: the site waits for a note
    # since 10 Nov, and every loop here was the tone it drew with none.
    corpus.held_tone(p)

    # One total per destination, the generator playing the bounded pitch,
    # amplitude's law through the combined route, boredom (its rise, its
    # slope, its ceiling, its reach and its drain) and the photocell moving
    # the pitch you hear were read here off the page's own brain - its
    # picture sources held at a value by hand, its `applyModMatrix` and
    # `compileRoutes`, its generator through its worklet and its picture over
    # eleven real seconds. They are core/tests/pieces/loop.py's since stage
    # 5, step 3, batch 3 (13 Nov): sources held at a value in the core's
    # matrix with the core's own reaches, the route it hands the generator
    # played, and boredom off the core's picture fed a stuck figure and then
    # a moving one. Two that read only the page's compiler - "cross into the
    # audio loop as one" and "carrying the bounded total", off `genRoutes` -
    # are asked of the core's matrix there instead.

    print("\n--- running away, as the limiter sees it ---")
    strained = p.evaluate("""() => {
      const m = makePictureMeter(), g = new Float32Array(PHOSPHOR_N * PHOSPHOR_N);
      for (let i = 0; i < 300; i++) g[i * 7 % g.length] = 1;
      for (let f = 0; f < 600; f++) m.update(g, 1 / 60, -10);
      const calm = makePictureMeter();
      for (let f = 0; f < 600; f++) calm.update(g, 1 / 60, 0);
      return { strained: m.verdict(), calm: calm.verdict() };
    }""")
    # The reading itself. Asserting only that it is nought or negative passed
    # for a monitorLimiting that always answered nought, which is also what a
    # quiet chain answers - so it could never fail. Here a chain is fed a tone
    # at twelve times full scale, which the limiter has to pull down by tens of
    # decibels, and the page must see that.
    strained.update(p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const quiet = monitorLimiting();
      await applyGeneratorSound();
      await wait(200);
      const chain = [...monitorChains][0];
      if (!chain) { { const v = genVoice(); if (v) await v.setSound(false); syncGeneratorSound(); } return { quiet, hot: null }; }
      const osc = chain.ctx.createOscillator(), gain = chain.ctx.createGain();
      gain.gain.value = 12; osc.connect(gain); gain.connect(chain.input); osc.start();
      await wait(400);
      const hot = monitorLimiting();
      osc.stop(); gain.disconnect();
      { const v = genVoice(); if (v) await v.setSound(false); syncGeneratorSound(); }
      await wait(300);
      return { quiet, hot };
    }"""))
    check("a picture held under ten decibels of limiting is running away, and the same picture unlimited is not",
          strained["strained"] == "running away" and strained["calm"] != "running away", str(strained))
    print("    limiter reading, quiet %s, fed twelve times full scale %s" % (strained["quiet"], strained["hot"]))
    check("and the page reads a hot chain's limiter pulling it down",
          strained["hot"] is not None and strained["hot"] < -6, str(strained))

    print("\n--- the stability run ---")
    RUN = """async ([seed, seconds, scanDepth, mode]) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      toTone(); setDisplay('xy');
      midiPanic(); setMidiMode('mono'); midiNoteOn(57, 127);
      genSet('shape', 'harmonic'); genSet('interval', 7); genSet('just', false);
      genSet('freq', 220);
      genSet('amp', seed === 'silence' ? 0.0 : 1.0);
      /* Every seed from a dark screen, not only silence. A seed run on the
         same page as the one before it otherwise opened on that one's
         picture, and the phaser's did once (P8h) with the screen still full
         and the pitch total already at its bound, so it never moved and the
         check below read a running loop as a dead one. From dark the totals
         have to climb, which a dead loop cannot do. */
      el.clearButton.click();
      state.persistence = 0.04; el.persistence.value = '0.04';
      // The filter on, resonant, in the speakers' path.
      state.filter.on = true; el.filterOn.checked = true; el.filterOn.dispatchEvent(new Event('change'));
      state.filter.res = 80; state.monitorAt = 'post';
      /* The lag on, except crossed: a lag draws one figure of a channel
         against itself delayed, so there are no two figures and no layer
         pictures for the layers to cross (the first crossed run was a run
         of one picture and showed nothing). Its route onto view.lag stays. */
      if (mode !== 'cross') { el.lagOn.checked = true; el.lagOn.dispatchEvent(new Event('change')); }
      await applyGeneratorSound();
      if (!photo.on) setPhoto(true);
      // Everything the picture has, at the most it is allowed, onto the
      // destinations that can do the most - two of them onto resonance at once,
      // so the total is what holds it.
      state.modRoutings = [];
      const plan = [['photo.1', 'filter.res'], ['picture.bored', 'filter.res'],
                    ['picture.cover', 'gen.freq'], ['picture.round', 'view.lag'],
                    ['picture.novelty', 'view.rotate'], ['picture.change', 'filter.cutoff'],
                    ['picture.signed', 'view.zoom']];
      for (const [s, d] of plan) addRouting(s, d);
      for (const r of state.modRoutings) r.amount = 1;
      // And the picture stage at its top, on the fold, the echo, the twist
      // and the phase, which nothing above routes: its totals are read with
      // the rest below, so a stage route outside the loop's bound fails here.
      el.pictureAmount.value = '100';
      el.pictureAmount.dispatchEvent(new Event('input'));
      // Scan (P7a) at its top as well, when asked: the voice's wave read
      // from the screen the rest of this loop is moving.
      if (scanDepth) { el.oscScan.value = String(scanDepth); el.oscScan.dispatchEvent(new Event('input')); }
      /* P7b. Struck: Strike at its top and a note every ninety milliseconds
         at full velocity, round the twelve places on the circle, so light is
         laid on the read as fast as a hand could lay it. Crossed: a split
         with Scan at its top on both layers, each reading the other's
         picture, and two notes held in each half so there are two figures. */
      let hammer = null, k = 0;
      if (mode === 'strike') {
        el.scanStrike.value = '100'; el.scanStrike.dispatchEvent(new Event('input'));
        setScreenKeys(true);
        hammer = setInterval(() => { const n = 60 + (k++ * 7) % 12; midiNoteOn(n, 127); setTimeout(() => midiNoteOff(n), 60); }, 90);
      }
      /* P8e. The phaser at its top, its range and resonance at their most,
         sweeping fast, beside the stage's own push on its amount from Memory:
         a resonance fed back inside the loop the picture closes. */
      if (mode === 'phaser') {
        for (const [id, v] of [['phaserMix', 100], ['phaserDepth', 100], ['phaserFeedback', 75], ['phaserRate', 300]]) {
          el[id].value = String(v); el[id].dispatchEvent(new Event('input'));
        }
      }
      /* P9, at the owner's asking: the reverb at full Mix and full Spread,
         and its Size at the top as well, the longest tail the loop can be
         handed - a stage that smears every sound over seconds, so whatever
         the picture does to the sound comes back into it for that long. The
         bounds below are the same ones, unloosened. */
      if (mode === 'reverb') {
        for (const [id, v] of [['reverbMix', 100], ['reverbSpread', 100], ['reverbSize', 100]]) {
          el[id].value = String(v); el[id].dispatchEvent(new Event('input'));
        }
      }
      if (mode === 'cross') {
        setScreenKeys(true); setMidiMode('poly');
        el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
        for (const n of [48, 55, 79, 84]) midiNoteOn(n, 127);
        for (const l of [0, 1]) { midi.layers.edit = l; syncLayerPanel(); el.oscScan.value = '100'; el.oscScan.dispatchEvent(new Event('input')); }
        midi.layers.edit = 0; syncLayerPanel();
        el.scanReadsA.value = 'B'; el.scanReadsA.dispatchEvent(new Event('change'));
        el.scanReadsB.value = 'A'; el.scanReadsB.dispatchEvent(new Event('change'));
      }
      const bright = [], motion = [], motionB = [];
      let leastScanHold = 1, lastTable = null, lastTableB = null, leastLayerHold = 1, liveReads = 0;
      // Silence has to get going somehow: the generator comes up a little way
      // into the run, from nothing, with the loop already closed around it.
      if (seed === 'silence') setTimeout(() => genSet('amp', 0.3), 2000);

      const chain = Array.from(monitorChains)[0];
      const ctx = chain.input.context;
      const pre = ctx.createAnalyser(), post = ctx.createAnalyser();
      pre.fftSize = post.fftSize = 2048;
      chain.limiter.connect(pre); chain.clamp.connect(post);
      const buf = new Float32Array(2048);
      const peakOf = (a) => { a.getFloatTimeDomainData(buf); let m = 0; for (const v of buf) { if (!Number.isFinite(v)) return Infinity; m = Math.max(m, Math.abs(v)); } return m; };
      const worst = { post: 0, pre: 0, res: 0, rot: 0, zoom: 0, total: 0, grid: 0, nan: false };
      const moved = { res: [Infinity, -Infinity], rot: [Infinity, -Infinity], freq: [Infinity, -Infinity],
                      fold: [Infinity, -Infinity] };
      const verdicts = {};
      let leastHold = 1;
      const until = performance.now() + seconds * 1000;
      while (performance.now() < until) {
        await wait(100);
        worst.post = Math.max(worst.post, peakOf(post));
        worst.pre = Math.max(worst.pre, peakOf(pre));
        worst.res = Math.max(worst.res, Math.abs(state.resMod));
        worst.rot = Math.max(worst.rot, Math.abs(state.rotateMod));
        worst.zoom = Math.max(worst.zoom, Math.abs(state.zoomMod));
        const totals = genRoutes.filter((r) => r.loopTotal).map((r) => Math.abs(r.source.value()));
        worst.total = Math.max(worst.total, ...totals, 0);
        let g = 0;
        for (const v of phosphor.grid) { if (!Number.isFinite(v)) worst.nan = true; g = Math.max(g, v); }
        worst.grid = Math.max(worst.grid, g);
        for (const v of [state.resMod, state.rotateMod, state.zoomMod, ...Object.values(picture.raw)]) {
          if (!Number.isFinite(v)) worst.nan = true;
        }
        const fTotal = totals.length ? totals[0] : 0;
        moved.res = [Math.min(moved.res[0], state.resMod), Math.max(moved.res[1], state.resMod)];
        moved.rot = [Math.min(moved.rot[0], state.rotateMod), Math.max(moved.rot[1], state.rotateMod)];
        moved.freq = [Math.min(moved.freq[0], fTotal), Math.max(moved.freq[1], fTotal)];
        const fold = genRoutes.find((r) => r.loopTotal && r.slot === FOLD_SLOT);
        const fv = fold ? fold.source.value() : 0;
        moved.fold = [Math.min(moved.fold[0], fv), Math.max(moved.fold[1], fv)];
        const v = pictureMeter.verdict(); verdicts[v] = (verdicts[v] || 0) + 1;
        leastHold = Math.min(leastHold, pictureStage.hold);
        if (scanDepth) {
          const [l] = state.source.getLatestWindow(4096);
          let e = 0, d = 0;
          for (let k = 1; k < l.length; k++) { e += l[k] * l[k]; d += (l[k] - l[k - 1]) ** 2; }
          bright.push(Math.sqrt(d / Math.max(e, 1e-12)));
          leastScanHold = Math.min(leastScanHold, genSettings().scanHold);
          if (mode === 'cross') {
            leastScanHold = Math.min(leastScanHold, genSettings(1).scanHold);
            if (layerPictures.live) {
              liveReads++;
              leastLayerHold = Math.min(leastLayerHold, layerPictures.stages[0].hold, layerPictures.stages[1].hold);
            }
            const tb = genSettings(1).scanTable;
            if (tb && lastTableB) {
              let m = 0;
              for (let q = 0; q < tb.levels[0].length; q++) m += Math.abs(tb.levels[0][q] - lastTableB.levels[0][q]);
              motionB.push(m / tb.levels[0].length);
            }
            lastTableB = tb;
          }
          // How far the table moved since the last read: the mean change of
          // its richest level, which is evened to a peak of one.
          const table = genSettings().scanTable;
          if (table && lastTable) {
            let m = 0;
            for (let k = 0; k < table.levels[0].length; k++) m += Math.abs(table.levels[0][k] - lastTable.levels[0][k]);
            motion.push(m / table.levels[0].length);
          }
          lastTable = table;
        }
      }
      const reverbHeld = { mix: genSettings().reverbMix, spread: genSettings().reverbSpread, size: genSettings().reverbSize };
      if (hammer) { clearInterval(hammer); el.scanStrike.value = '50'; el.scanStrike.dispatchEvent(new Event('input')); }
      if (mode === 'cross') {
        el.scanReadsA.value = 'A'; el.scanReadsA.dispatchEvent(new Event('change'));
        el.scanReadsB.value = 'B'; el.scanReadsB.dispatchEvent(new Event('change'));
        midi.layers.edit = 1; syncLayerPanel(); el.oscScan.value = '0'; el.oscScan.dispatchEvent(new Event('input'));
        midi.layers.edit = 0; syncLayerPanel();
        el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change'));
      }
      if (mode === 'phaser') { el.phaserMix.value = '0'; el.phaserMix.dispatchEvent(new Event('input')); }
      if (mode === 'reverb') {
        for (const [id, v] of [['reverbMix', 0], ['reverbSpread', 0], ['reverbSize', 40]]) {
          el[id].value = String(v); el[id].dispatchEvent(new Event('input'));
        }
      }
      if (mode) { midiPanic(); setScreenKeys(false); }
      if (scanDepth) { el.oscScan.value = '0'; el.oscScan.dispatchEvent(new Event('input')); }
      state.modRoutings = []; el.pictureAmount.value = String(STAGE_DEFAULT); el.pictureAmount.dispatchEvent(new Event('input'));
      { const v = genVoice(); if (v) await v.setSound(false); syncGeneratorSound(); }
      state.filter.on = false; el.filterOn.checked = false; el.filterOn.dispatchEvent(new Event('change'));
      el.lagOn.checked = false; el.lagOn.dispatchEvent(new Event('change'));
      genSet('amp', 0.55);
      return { worst, moved, verdicts, leastHold, bright, motion, motionB, leastScanHold, leastLayerHold, liveReads, reverbHeld };
    }"""
    # Scan's run is on the page's own brain and JavaScript generator, on a
    # page of its own: the run reads the tables that brain sends, which the
    # site's instrument reads inside its worklet and never hands out. The
    # instrument's reading is held to this one by core/tests/parity.py.
    p2 = b.new_page(viewport={"width": 1400, "height": 900})
    p2.on("pageerror", lambda e: bad.append("pageerror (Scan's page): " + str(e)))
    p2.goto(f"file://{ART}/scope.html?brain=js&core=js"); p2.wait_for_timeout(700)
    corpus.old_opening(p2)  # the opening it was written against (P8h)
    if p2.locator("#helpClose").is_visible(): p2.locator("#helpClose").click()
    p2.wait_for_timeout(200)
    p2.evaluate("() => { setDisplay('xy'); genSet('shape', 'sine'); el.photoButton.click(); }")
    corpus.held_tone(p2)
    SEEDS = [("silence", None), ("full scale", None), ("full scale, with Scan at its top", None),
             ("full scale, Scan at its top, every note striking at full", "strike"),
             ("full scale, a split at Scan's top, each layer reading the other's picture", "cross"),
             ("full scale, the phaser at its top with its resonance at its most", "phaser"),
             ("full scale, the reverb at full Mix, Spread and Size", "reverb")]
    for seed, mode in SEEDS:
        page = p2 if "Scan" in seed else p
        run = page.evaluate(RUN, ["silence" if seed == "silence" else "full", SECONDS, 100 if "Scan" in seed else 0, mode])
        w, mv = run["worst"], run["moved"]
        print("    from %s, %.0f s: output peak %.3f (before the limiter %.3f); resonance offset up to %.1f, "
              "rotation %.3f, zoom %.2f, generator total %.3f; grid %.2f; verdicts %s"
              % (seed, SECONDS, w["post"], w["pre"], w["res"], w["rot"], w["zoom"], w["total"],
                 w["grid"], run["verdicts"]))
        print("      it moved: resonance %.1f to %.1f, rotation %.3f to %.3f, pitch total %.3f to %.3f, fold total %.3f to %.3f"
              % (mv["res"][0], mv["res"][1], mv["rot"][0], mv["rot"][1], mv["freq"][0], mv["freq"][1], mv["fold"][0], mv["fold"][1]))
        check("from %s, nothing goes NaN or infinite" % seed, not w["nan"] and math.isfinite(w["pre"]), str(w))
        check("from %s, what reaches the speakers never passes full scale" % seed, w["post"] <= 1.0 + 1e-6,
              "%.4f" % w["post"])
        # And something reached them: a run the speakers never heard passes
        # the bound above whatever the loop does. Every run here did, on
        # 10 Nov, until it began to wait for a note and its worklet came up
        # shut under the key (0.000 for every seed), which nothing caught.
        check("from %s, and the speakers did hear it" % seed, w["post"] > 0.1, "%.4f" % w["post"])
        check("from %s, every destination stays inside the loop's total" % seed,
              w["res"] <= 0.5 * 50 + 1e-6 and w["rot"] <= 0.5 + 1e-9 and w["zoom"] <= 0.5 * 8 + 1e-9
              and w["total"] <= 0.5 + 1e-9, str(w))
        check("from %s, and the grid stays inside the phosphor's range" % seed, w["grid"] <= 1, str(w["grid"]))
        # The verdict governs as well as reports: running away for more than a
        # couple of seconds holds the stage down to its floor; a moment of it
        # holds it down by no more than half its length in seconds, and a
        # tenth's slack for the sampling; and a run that never runs away is
        # never held - the null of the others. (From silence it ran away for
        # seven tenths once, and the first version, which allowed only the
        # floor or nothing, failed on a hold doing exactly its job.)
        running = run["verdicts"].get("running away", 0)
        least = run["leastHold"]
        held_right = (least == 0.25 if running > 30
                      else least == 1 if running == 0
                      else 1 - 0.5 * running / 10 - 0.1 <= least < 1)
        check("from %s, running away holds the stage's push down, to a quarter at most, and nothing else holds it" % seed,
              held_right, "%d tenths running away, the hold down to %.3f" % (running, least))
        # Struck at full every ninety milliseconds the screen can stay full
        # for the whole run, the coverage with it, and then the pitch total
        # and the stage's fold stop moving: pinned at their bound, which is
        # the bound holding and which the totals check above reads - or, the
        # fold, at nought, since a screen full from first to last gives Glow
        # no range to rescale and the running-away hold reins the stage in.
        # Which of the two depends on timing (the page stage saw the bound;
        # the core stage saw nought in two runs of five). Nought is also what
        # a loop that did nothing reads, so the exemption is not the value but
        # evidence the loop was saturated: the grid full and running away for
        # nine tenths of the run, which a dead loop - settled, never held -
        # cannot show. The resonance still has to move, as everywhere.
        tenths = sum(run["verdicts"].values())
        # The reverb at its fullest too, since 11 Nov: its tail fills the
        # screen from the first frame to the last, and Change, on a fixed
        # scale, has nothing to flare on in a screen that never changes how
        # much is lit - the same evidence is asked of it. And the crossed
        # split since 12 Nov, when Change's dead zone came in: its screens are
        # as full (239 tenths of 240 running away), and a level that cannot
        # rise is no gesture.
        saturated = mode in ("strike", "reverb", "cross") and w["grid"] >= 1 - 1e-9 and tenths > 0 and running >= 0.9 * tenths
        pinned = lambda r: saturated and r[0] >= 0.5 - 1e-9
        check("from %s, and the loop was really running - it moved what it drives, the stage's fold too" % seed,
              (mv["res"][1] - mv["res"][0]) > 1 and ((mv["freq"][1] - mv["freq"][0]) > 0.01 or pinned(mv["freq"]))
              and ((mv["fold"][1] - mv["fold"][0]) > 0.05 or pinned(mv["fold"]) or (saturated and mv["fold"][1] < 0.05)),
              "resonance range %.2f, pitch total %r to %r, fold total %r to %r"
              % (mv["res"][1] - mv["res"][0], mv["freq"][0], mv["freq"][1], mv["fold"][0], mv["fold"][1]))
        if mode == "reverb":
            # The run above is only a run of the reverb if the generator held
            # it there to the end; without this a knob that never reached the
            # sound would pass as the plain full-scale run again.
            rv = run["reverbHeld"]
            check("and the reverb really was in the loop: the generator held Mix, Spread and Size at full to the end",
                  rv["mix"] == 1 and rv["spread"] == 1 and rv["size"] == 1, str(rv))
        if "Scan" in seed:
            mo = sorted(run["motion"])
            median = mo[len(mo) // 2] if mo else 0
            # Too strong a defence and Scan stops moving, which P2 found is a
            # dull tone; so its table has to be seen still moving, read by
            # read, under all of this - not only the sound, which the rest of
            # the loop moves with or without Scan.
            check("with Scan at its top, its wave was still moving: the table changed by a median of over 0.02 a tenth of a second",
                  len(mo) > 0.8 * SECONDS * 10 - 10 and median > 0.02, "median %.3f over %d reads" % (median, len(mo)))
            # Its null is scantest.py's: the same reading with the screen
            # held still, where the brightness stands.
            if mode == "cross":
                # Crossed, Scan's depths are held by the lower of the two
                # layers' pictures' holds, not the shown screen's.
                mb = sorted(run["motionB"])
                medianB = mb[len(mb) // 2] if mb else 0
                check("crossed, the run really had two pictures: the layers drew a figure each throughout",
                      run["liveReads"] > 0.8 * SECONDS * 10 - 10, "%d of the reads" % run["liveReads"])
                check("and B's wave was moving as well as A's", medianB > 0.02, "median %.3f" % medianB)
                check("and both depths were held by the lower of the two pictures' holds, never less",
                      abs(run["leastScanHold"] - run["leastLayerHold"]) < 0.02,
                      "Scan's holds down to %.3f, the pictures' to %.3f" % (run["leastScanHold"], run["leastLayerHold"]))
            else:
                check("and Scan's depth was held by the stage's own hold, never less",
                      abs(run["leastScanHold"] - least) < 0.02, "Scan's hold down to %.3f, the stage's to %.3f"
                      % (run["leastScanHold"], least))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the loop runs through the sound, and every bound held")
