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
  allowed onto the most sensitive destinations, from silence and from a
  full-scale figure, run headless, with every bound checked every tenth of a
  second - and checked to have MOVED, because a loop that did nothing would
  pass any bound there is.

The plan asked for 60 seconds. It is 30 from each seed, 60 in all, because the
suite is run while working and a minute per seed would double this file.
"""
import math, os, sys
from playwright.sync_api import sync_playwright

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
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)
    p.evaluate("() => { setDisplay('xy'); genSet('shape', 'sine'); el.photoButton.click(); }")

    print("\n--- one total per destination ---")
    visual = p.evaluate("""() => {
      state.modRoutings = [];
      const loop = ['photo.1', 'picture.round', 'picture.cover'];
      const saved = loop.map((id) => MOD_SOURCES.get(id).value);
      for (const id of loop) { MOD_SOURCES.get(id).value = () => 1; addRouting(id, 'view.rotate'); }
      for (const r of state.modRoutings) r.amount = 0.5;
      touchRoutings();
      applyModMatrix(capture(), 16);
      const loopOnly = state.rotateMod;
      // A source that is not the loop, on the same control.
      registerSource({ id: 'test.one', label: 'One', ink: 'ch1', value: () => 1 });
      addRouting('test.one', 'view.rotate');
      state.modRoutings.find((r) => r.sourceId === 'test.one').amount = 0.3;
      touchRoutings();
      applyModMatrix(capture(), 16);
      const withOther = state.rotateMod;
      loop.forEach((id, i) => { MOD_SOURCES.get(id).value = saved[i]; });
      MOD_SOURCES.delete('test.one');
      state.modRoutings = []; touchRoutings(); applyModMatrix(capture(), 16);
      return { loopOnly, withOther };
    }""")
    print("    three picture sources at full on rotation: %.3f of its span; with 0.3 from "
          "something else as well: %.3f" % (visual["loopOnly"], visual["withOther"]))
    check("three picture sources at full move a destination by the loop's total, not three times it",
          abs(visual["loopOnly"] - 0.5) < 1e-9, "%.3f" % visual["loopOnly"])
    check("and a source that is not the loop is not caught in the loop's bound",
          abs(visual["withOther"] - 0.8) < 1e-9, "%.3f" % visual["withOther"])

    # The generator: measured by what it produces. Pitch is read by energy at
    # the frequency each outcome predicts, not by the zero-crossing estimator.
    audio = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const rate = state.source.sampleRate;
      const bin = (x, f) => { let re = 0, im = 0;
        for (let i = 0; i < x.length; i++) { const w = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (x.length - 1));
          re += x[i] * w * Math.cos(2 * Math.PI * f * i / rate); im -= x[i] * w * Math.sin(2 * Math.PI * f * i / rate); }
        return Math.hypot(re, im) / x.length; };
      genSet('freq', 220); genSet('interval', 0);
      state.modRoutings = [];
      const loop = ['photo.1', 'picture.round', 'picture.cover'];
      const saved = loop.map((id) => MOD_SOURCES.get(id).value);
      for (const id of loop) { MOD_SOURCES.get(id).value = () => 1; addRouting(id, 'gen.freq'); }
      for (const r of state.modRoutings) r.amount = 0.5;
      touchRoutings();
      await wait(600);
      compileRoutes();
      const routes = genRoutes.filter((r) => r.slot === GEN_DESTS.findIndex((d) => d.id === 'gen.freq'));
      const w = state.source.getLatestWindow(16384)[0];
      const bounded = 220 * Math.pow(2, 0.5), unbounded = 220 * Math.pow(2, 1.5);
      const out = { routes: routes.length, total: routes.map((r) => r.loopTotal === true),
                    held: routes.map((r) => r.source.value()),
                    atBounded: bin(w, bounded), atUnbounded: bin(w, unbounded), atBase: bin(w, 220) };
      loop.forEach((id, i) => { MOD_SOURCES.get(id).value = saved[i]; });
      state.modRoutings = []; touchRoutings();
      return out;
    }""")
    print("    three at full on pitch: %d route(s) into the slot %s, held at %s; energy at "
          "220 x 2^0.5 %.4f, at 220 x 2^1.5 %.4f, at 220 %.4f"
          % (audio["routes"], audio["total"], audio["held"], audio["atBounded"],
             audio["atUnbounded"], audio["atBase"]))
    check("the loop's routes into a generator parameter cross into the audio loop as one",
          audio["routes"] == 1 and audio["total"] == [True], str(audio))
    check("carrying the bounded total", audio["held"] == [0.5], str(audio["held"]))
    check("and the generator plays the bounded pitch, not three sources' worth",
          audio["atBounded"] > 0.05 and audio["atUnbounded"] < audio["atBounded"] * 0.01
          and audio["atBase"] < audio["atBounded"] * 0.01, str(audio))

    # Amplitude only ever ducks (see GEN_DESTS), and the combined route is
    # built unipolar: false because it carries the total with each part's law
    # already applied. So the law has to survive the combining: a source at
    # full on amplitude asks for no duck at all, and one at nought asks for its
    # whole depth. A total that forgot the law would read the other way round -
    # full volume at nought, and at full a push the worklet would turn into
    # silence.
    amp = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      genSet('freq', 220); genSet('interval', 0);
      state.modRoutings = [];
      const loop = ['photo.1', 'picture.round'];
      const saved = loop.map((id) => MOD_SOURCES.get(id).value);
      const slot = GEN_DESTS.findIndex((d) => d.id === 'gen.amp');
      const rms = (x) => Math.sqrt(x.reduce((a, v) => a + v * v, 0) / x.length);
      const out = {};
      for (const level of [1, 0]) {
        for (const id of loop) MOD_SOURCES.get(id).value = () => level;
        if (!state.modRoutings.length) for (const id of loop) addRouting(id, 'gen.amp');
        for (const r of state.modRoutings) r.amount = 0.5;
        touchRoutings();
        await wait(600);
        compileRoutes();
        const routes = genRoutes.filter((r) => r.slot === slot);
        out[level] = { routes: routes.length, held: routes.map((r) => r.source.value()),
                       rms: rms(state.source.getLatestWindow(8192)[0]) };
      }
      loop.forEach((id, i) => { MOD_SOURCES.get(id).value = saved[i]; });
      state.modRoutings = []; touchRoutings();
      return out;
    }""")
    print("    two on amplitude: at full %s, at nought %s" % (amp["1"], amp["0"]))
    check("two on amplitude at full ask for no duck, through the combined route",
          amp["1"]["routes"] == 1 and abs(amp["1"]["held"][0]) < 1e-9, str(amp["1"]))
    check("and at nought they duck, by no more than the loop's total",
          amp["0"]["routes"] == 1 and 0.2 < amp["0"]["held"][0] <= 0.5 + 1e-9, str(amp["0"]))
    check("and the generator is quieter at nought than at full",
          amp["0"]["rms"] < amp["1"]["rms"] * 0.9 and amp["1"]["rms"] > 0.05, str(amp))

    print("\n--- boredom ---")
    bored = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      genSet('just', true); genSet('interval', 0); genSet('phase', Math.PI / 2);
      state.persistence = 0.12; el.persistence.value = '0.12';
      el.clearButton.click();
      const rise = [];
      const start = performance.now();
      while (performance.now() - start < 11000) { await wait(250); rise.push([(performance.now() - start) / 1000, picture.bored, picture.raw.bored]); }
      // Reach: routed at full, it moves rotation by its own reach at most.
      state.modRoutings = []; addRouting('picture.bored', 'view.rotate');
      state.modRoutings[0].amount = 1; touchRoutings();
      await wait(100);
      const applied = state.rotateMod / picture.bored;
      state.modRoutings = []; touchRoutings();
      // Movement returns: an equal fifth drifts.
      genSet('interval', 7); genSet('just', false);
      const fall = [];
      const again = performance.now();
      while (performance.now() - again < 6000) { await wait(250); fall.push([(performance.now() - again) / 1000, picture.bored]); }
      genSet('interval', 0); genSet('just', true);
      return { rise, applied, fall };
    }""")
    at = lambda series, t: min(series, key=lambda row: abs(row[0] - t))[1]
    peak = max(row[1] for row in bored["rise"])
    print("    stuck: %.2f after 2 s, %.2f after 5 s, %.2f after 10 s; routed at full it applies %.2f of itself; "
          "moving again: %.2f after 5 s"
          % (at(bored["rise"], 2), at(bored["rise"], 5), at(bored["rise"], 10), bored["applied"],
             at(bored["fall"], 5)))
    check("boredom rises while the picture is stuck", at(bored["rise"], 10) > 0.7, str(at(bored["rise"], 10)))
    # The steepest the raw level ever climbs, over any quarter second. Read
    # from the slope and not from the value at a moment: boredom waits for the
    # meter to have history before it can call anything stuck, so the value
    # after two seconds is small whatever the rate is.
    steepest = max((row2[2] - row1[2]) / (row2[0] - row1[0])
                   for row1, row2 in zip(bored["rise"], bored["rise"][1:]))
    check("no faster than a quarter a second - it cannot slam", steepest <= 0.25 * 1.15,
          "%.3f a second at the steepest" % steepest)
    check("and never past one", peak <= 1, "%.3f" % peak)
    check("routed at full it moves a destination by its own reach, lower than the photocell's",
          abs(bored["applied"] - 0.3) < 1e-6, "%.4f" % bored["applied"])
    check("and it drains when the picture moves again", at(bored["fall"], 5) < 0.45,
          "%.2f after 5 s" % at(bored["fall"], 5))

    print("\n--- the loop reaches the sound ---")
    heard = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      genSet('freq', 220); genSet('interval', 0); genSet('phase', Math.PI / 2);
      state.genSound = true; await applyGeneratorSound();
      const chain = Array.from(monitorChains)[0];
      const ctx = chain.input.context, rate = ctx.sampleRate;
      const tap = ctx.createAnalyser(); tap.fftSize = 16384; chain.input.connect(tap);
      const bin = (x, f) => { let re = 0, im = 0;
        for (let i = 0; i < x.length; i++) { const w = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (x.length - 1));
          re += x[i] * w * Math.cos(2 * Math.PI * f * i / rate); im -= x[i] * w * Math.sin(2 * Math.PI * f * i / rate); }
        return Math.hypot(re, im) / x.length; };
      // The photocell held at a known value, onto pitch, heard through the worklet.
      const saved = MOD_SOURCES.get('photo.1').value;
      MOD_SOURCES.get('photo.1').value = () => 0.6;
      state.modRoutings = []; addRouting('photo.1', 'gen.freq');
      state.modRoutings[0].amount = 0.5; touchRoutings();
      await wait(900);
      const x = new Float32Array(tap.fftSize); tap.getFloatTimeDomainData(x);
      const want = 220 * Math.pow(2, 0.3);
      const out = { audible: state.source.audible(), atWant: bin(x, want), atBase: bin(x, 220) };
      MOD_SOURCES.get('photo.1').value = saved;
      state.modRoutings = []; touchRoutings();
      state.genSound = false; await applyGeneratorSound();
      return out;
    }""")
    print("    photocell held at 0.6, onto pitch at 0.5, generator heard: energy at 220 x 2^0.3 %.4f, at 220 %.4f"
          % (heard["atWant"], heard["atBase"]))
    check("the photocell moves the pitch you hear, through the worklet",
          heard["audible"] and heard["atWant"] > 0.03 and heard["atBase"] < heard["atWant"] * 0.05,
          str(heard))

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
      state.genSound = true; await applyGeneratorSound();
      await wait(200);
      const chain = [...monitorChains][0];
      if (!chain) { state.genSound = false; await applyGeneratorSound(); return { quiet, hot: null }; }
      const osc = chain.ctx.createOscillator(), gain = chain.ctx.createGain();
      gain.gain.value = 12; osc.connect(gain); gain.connect(chain.input); osc.start();
      await wait(400);
      const hot = monitorLimiting();
      osc.stop(); gain.disconnect();
      state.genSound = false; await applyGeneratorSound();
      await wait(300);
      return { quiet, hot };
    }"""))
    check("a picture held under ten decibels of limiting is running away, and the same picture unlimited is not",
          strained["strained"] == "running away" and strained["calm"] != "running away", str(strained))
    print("    limiter reading, quiet %s, fed twelve times full scale %s" % (strained["quiet"], strained["hot"]))
    check("and the page reads a hot chain's limiter pulling it down",
          strained["hot"] is not None and strained["hot"] < -6, str(strained))

    print("\n--- the stability run ---")
    RUN = """async ([seed, seconds]) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      toTone(); setDisplay('xy');
      genSet('shape', 'harmonic'); genSet('interval', 7); genSet('just', false);
      genSet('freq', 220);
      if (seed === 'silence') { genSet('amp', 0.0); el.clearButton.click(); }
      else { genSet('amp', 1.0); }
      state.persistence = 0.04; el.persistence.value = '0.04';
      // The filter on, resonant, in the speakers' path.
      state.filter.on = true; el.filterOn.checked = true; el.filterOn.dispatchEvent(new Event('change'));
      state.filter.res = 80; state.monitorAt = 'post';
      el.lagOn.checked = true; el.lagOn.dispatchEvent(new Event('change'));
      state.genSound = true; await applyGeneratorSound();
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
      touchRoutings();
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
      const moved = { res: [Infinity, -Infinity], rot: [Infinity, -Infinity], freq: [Infinity, -Infinity] };
      const verdicts = {};
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
        const v = pictureMeter.verdict(); verdicts[v] = (verdicts[v] || 0) + 1;
      }
      state.modRoutings = []; touchRoutings();
      state.genSound = false; await applyGeneratorSound();
      state.filter.on = false; el.filterOn.checked = false; el.filterOn.dispatchEvent(new Event('change'));
      el.lagOn.checked = false; el.lagOn.dispatchEvent(new Event('change'));
      genSet('amp', 0.55);
      return { worst, moved, verdicts };
    }"""
    for seed in ("silence", "full scale"):
        run = p.evaluate(RUN, ["silence" if seed == "silence" else "full", SECONDS])
        w, mv = run["worst"], run["moved"]
        print("    from %s, %.0f s: output peak %.3f (before the limiter %.3f); resonance offset up to %.1f, "
              "rotation %.3f, zoom %.2f, generator total %.3f; grid %.2f; verdicts %s"
              % (seed, SECONDS, w["post"], w["pre"], w["res"], w["rot"], w["zoom"], w["total"],
                 w["grid"], run["verdicts"]))
        print("      it moved: resonance %.1f to %.1f, rotation %.3f to %.3f, pitch total %.3f to %.3f"
              % (mv["res"][0], mv["res"][1], mv["rot"][0], mv["rot"][1], mv["freq"][0], mv["freq"][1]))
        check("from %s, nothing goes NaN or infinite" % seed, not w["nan"] and math.isfinite(w["pre"]), str(w))
        check("from %s, what reaches the speakers never passes full scale" % seed, w["post"] <= 1.0 + 1e-6,
              "%.4f" % w["post"])
        check("from %s, every destination stays inside the loop's total" % seed,
              w["res"] <= 0.5 * 50 + 1e-6 and w["rot"] <= 0.5 + 1e-9 and w["zoom"] <= 0.5 * 8 + 1e-9
              and w["total"] <= 0.5 + 1e-9, str(w))
        check("from %s, and the grid stays inside the phosphor's range" % seed, w["grid"] <= 1, str(w["grid"]))
        check("from %s, and the loop was really running - it moved what it drives" % seed,
              (mv["res"][1] - mv["res"][0]) > 1 and (mv["freq"][1] - mv["freq"][0]) > 0.01,
              "resonance range %.2f, pitch total range %.3f"
              % (mv["res"][1] - mv["res"][0], mv["freq"][1] - mv["freq"][0]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the loop runs through the sound, and every bound held")
