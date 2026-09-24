"""Two layers: a keyboard split, or every note twice, from one core.

What would go wrong, and what is checked for it:

- the oscillators stepped twice a sample, once per layer, so every modulation
  rate runs at double with a split on. Measured by how far an oscillator's
  phase moves in a quarter of a second of core samples, against a nought that
  a doubled step cannot give;
- a note landing in the wrong layer. The fixture straddles the split point
  and includes the point itself, so `>` and `>=` disagree, and it is pressed
  out of pitch order so a layer that took "the first two" would be caught;
- the two layers sharing one draw rule. Each is given a different rule, and
  each has three notes so the two rules pick different ones;
- a layer's notes leaking into the other's picture, or missing from what is
  heard. Checked by energy at each note's own frequency in each picture and in
  the heard pair, at the core and again through the worklet, where layer B's
  picture crosses a thread in two arrays of its own;
- layer B sounding with layer A's shape or envelope;
- "A against B" not being layer A on X and layer B on Y;
- two figures asked for and one drawn, read from the phosphor with only
  layer B holding notes, so the one figure that is there is B's;
- the panel writing into the wrong layer, or a panel left showing B being
  what a setup code or a new generator is built from;
- the layers outliving the thing that made them possible.

Frequencies are read by a Hann-windowed single-bin transform, as polytest
does and for its reason: a sum of notes crosses zero at the rate of none.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

HZ = lambda note: 440 * 2 ** ((note - 69) / 12)
rounded = lambda xs: [round(x, 4) for x in xs]

BIN = """(src) => { window.__bin = eval(src); }"""
BIN_SRC = """(x, f, rate) => {
  let re = 0, im = 0;
  for (let i = 0; i < x.length; i++) {
    const w = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (x.length - 1));
    re += x[i] * w * Math.cos(2 * Math.PI * f * i / rate);
    im -= x[i] * w * Math.sin(2 * Math.PI * f * i / rate);
  }
  return Math.hypot(re, im) / x.length;
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    p.add_init_script("window.__errs = []; window.addEventListener('error', "
                      "(e) => window.__errs.push(e.error && e.error.stack || e.message));")
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e) + " @ " + (e.stack or "")[:300]))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)
    p.evaluate(BIN, BIN_SRC)

    print("\n--- the core: one step of the oscillators a sample, however many layers ---")
    # A 1 Hz oscillator from phase nought, a quarter of a second of samples:
    # a quarter turn with one step a sample, half a turn with two.
    lfo = p.evaluate("""() => {
      const rate = 44100;
      const run = (layered) => {
        const lfos = [0, 1].map(() => ({ shape: 'sine', rate: 1, depth: 0, phase: 0, held: 0, value: 0 }));
        const core = makeGeneratorCore(rate, GEN_DESTS.length, lfos);
        const chord = [{ note: 48, freq: 130.8, velocity: 1, role: 'x' }];
        core.set('voices', chord);
        if (layered) core.set('voices', [{ note: 72, freq: 523.3, velocity: 1, role: 'xy' }], 1);
        const n = rate / 4, a = new Float32Array(n), c = new Float32Array(n);
        core.block(a, c, n, null, null, new Float32Array(n), new Float32Array(n));
        return lfos[0].phase / (2 * Math.PI);
      };
      return { one: run(false), two: run(true) };
    }""")
    print("    turns in 0.25 s at 1 Hz: one layer %.4f, two layers %.4f" % (lfo["one"], lfo["two"]))
    check("two layers step the oscillators once a sample, not twice",
          abs(lfo["two"] - 0.25) < 1e-3 and abs(lfo["one"] - 0.25) < 1e-3, str(lfo))

    print("\n--- the core: each layer's picture, and one sound ---")
    A = [{"note": 48, "freq": HZ(48), "velocity": 1, "role": "x"},
         {"note": 55, "freq": HZ(55), "velocity": 1, "role": "y"}]
    B = [{"note": 76, "freq": HZ(76), "velocity": 1, "role": "xy"}]
    core = p.evaluate("""([A, B]) => {
      const rate = 44100;
      const quiet = [0, 1].map(() => ({ shape: 'sine', rate: 1, depth: 0, phase: 0, held: 0, value: 0 }));
      const core = makeGeneratorCore(rate, GEN_DESTS.length, quiet);
      core.set('shape', 'sine'); core.set('shape', 'square', 1);
      // Layer B slow to speak and A quick, so an envelope shared between them
      // shows as B arriving at A's speed.
      core.set('attackMs', 2); core.set('attackMs', 400, 1);
      core.set('voices', A); core.set('voices', B, 1);
      const n = Math.round(rate * 0.8);
      const al = new Float32Array(n), ar = new Float32Array(n);
      const hl = new Float32Array(n), hr = new Float32Array(n);
      const bl = new Float32Array(n), br = new Float32Array(n);
      core.block(al, ar, n, hl, hr, bl, br);
      const tail = (x) => x.subarray(n - 16384);
      const f = (x, hz) => window.__bin(tail(x), hz, rate);
      const peak = (x, from, to) => { let m = 0; for (let i = from; i < to; i++) m = Math.max(m, Math.abs(x[i])); return m; };
      const hz = { c: A[0].freq, g: A[1].freq, e: B[0].freq };
      return {
        aX: [f(al, hz.c), f(al, hz.g), f(al, hz.e)],
        aY: [f(ar, hz.c), f(ar, hz.g), f(ar, hz.e)],
        bX: [f(bl, hz.c), f(bl, hz.g), f(bl, hz.e)],
        heard: [f(hl, hz.c), f(hl, hz.g), f(hl, hz.e)],
        // A square has its third harmonic at a third of the fundamental; a
        // sine has none.
        bThird: f(bl, 3 * hz.e) / Math.max(1e-9, f(bl, hz.e)),
        aThird: f(al, 3 * hz.c) / Math.max(1e-9, f(al, hz.c)),
        // 40 ms in: A's 2 ms attack is long done, B's 400 ms one is not.
        aEarly: peak(al, Math.round(rate * 0.03), Math.round(rate * 0.05)),
        bEarly: peak(bl, Math.round(rate * 0.03), Math.round(rate * 0.05)),
        bLate: peak(bl, n - 4096, n),
      };
    }""", [A, B])
    print("    C, G, E  - A's X %s, A's Y %s, B's X %s, heard %s"
          % (rounded(core["aX"]), rounded(core["aY"]), rounded(core["bX"]), rounded(core["heard"])))
    top = max(core["aX"][0], 1e-9)
    check("layer A's picture has A's notes and not B's",
          core["aX"][0] > 0.05 and core["aY"][1] > 0.05
          and core["aX"][2] < top * 0.01 and core["aY"][2] < top * 0.01, str(core))
    check("layer B's picture has B's note and not A's",
          core["bX"][2] > 0.05 and core["bX"][0] < top * 0.01 and core["bX"][1] < top * 0.01,
          str(rounded(core["bX"])))
    check("and the heard pair has all three",
          min(core["heard"]) > 0.05, str(rounded(core["heard"])))
    print("    third harmonic over fundamental: B %.3f, A %.3f" % (core["bThird"], core["aThird"]))
    check("layer B plays its own shape - a square under A's sine",
          0.25 < core["bThird"] < 0.4 and core["aThird"] < 0.02, str(core))
    print("    40 ms in: A %.3f, B %.3f; B at the end %.3f" % (core["aEarly"], core["bEarly"], core["bLate"]))
    check("and speaks with its own envelope - slow where A's is quick",
          core["aEarly"] > 0.3 and core["bEarly"] < core["bLate"] * 0.4, str(core))

    life = p.evaluate("""() => {
      const rate = 44100;
      const quiet = [0, 1].map(() => ({ shape: 'sine', rate: 1, depth: 0, phase: 0, held: 0, value: 0 }));
      const core = makeGeneratorCore(rate, GEN_DESTS.length, quiet);
      core.set('releaseMs', 50, 1);
      // A chord on layer A with nothing in it, and one note on layer B: the
      // envelope a player hears is B's.
      core.set('voices', []);
      core.set('voices', [{ note: 76, freq: 659.3, velocity: 1, role: 'xy' }], 1);
      const n = rate / 2, s = () => new Float32Array(n);
      core.block(s(), s(), n, null, null, s(), s());
      const held = { envelope: core.envelope, voices: core.voicesB.length };
      core.set('voices', [], 1);
      core.block(s(), s(), n, null, null, s(), s());
      return { held, released: { envelope: core.envelope, voices: core.voicesB.length } };
    }""")
    print("    %s" % life)
    check("the envelope a source reads includes layer B's notes",
          life["held"]["envelope"] > 0.5 and life["held"]["voices"] == 1, str(life))
    check("and layer B's voices are let go once their release is over",
          life["released"]["voices"] == 0 and life["released"]["envelope"] < 1e-3, str(life))

    print("\n--- the keyboard: which layer a note goes to ---")
    route = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setScreenKeys(true); setMidiMode('poly');
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      midi.layers.point = 60;
      await wait(60);
      // Out of pitch order, and 60 - the point itself - among them.
      for (const n of [72, 59, 60, 48]) midiNoteOn(n, 100);
      await wait(60);
      const notes = (layer) => genSettings(layer).voices.map((v) => v.note).sort((a, b) => a - b);
      const split = { on: layersOn(), a: notes(0), b: notes(1), channels: state.source.channels,
                      lanes: laneCount(), names: [0, 1, 2, 3].map(laneName),
                      figures: state.source.figures() };
      el.midiLayers.value = 'layer'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(60);
      const layered = { a: notes(0), b: notes(1) };
      midiPanic();
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      return { split, layered };
    }""")
    print("    split at C4: A %s, B %s; layered: A %s, B %s"
          % (route["split"]["a"], route["split"]["b"], route["layered"]["a"], route["layered"]["b"]))
    check("a split sends notes below the point to A and the point upwards to B",
          route["split"]["on"] and route["split"]["a"] == [48, 59] and route["split"]["b"] == [60, 72],
          str(route["split"]))
    check("and offers four lanes, named for their layers, as two figures",
          route["split"]["channels"] == 4 and route["split"]["lanes"] == 4
          and route["split"]["names"] == ["A · X", "A · Y", "B · X", "B · Y"]
          and route["split"]["figures"] == [[0, 1], [2, 3]], str(route["split"]))
    check("layered sends every note to both",
          route["layered"]["a"] == [48, 59, 60, 72] and route["layered"]["b"] == [48, 59, 60, 72],
          str(route["layered"]))

    learn = p.evaluate("""async () => {
      el.midiSplitLearn.click();
      const asking = el.midiSplitLearn.textContent;
      midiNoteOn(65, 100);
      const out = { asking, point: midi.layers.point, learning: midi.layers.learning,
                    said: el.midiSplitLearn.textContent,
                    played: midi.notes.map((n) => n.note), b: genSettings(1).voices.map((v) => v.note) };
      midiPanic(); midi.layers.point = 60; syncMidi();
      return out;
    }""")
    print("    %s" % learn)
    check("the split point is learned from the next key, which still plays",
          learn["asking"] == "play a key" and learn["point"] == 65 and not learn["learning"]
          and learn["said"] == "at F4" and learn["played"] == [65] and learn["b"] == [65], str(learn))

    print("\n--- each layer its own draw rule ---")
    rules = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      midi.draws[0] = { count: 2, which: 'lowest' };
      midi.draws[1] = { count: 2, which: 'highest' };
      for (const n of [52, 48, 55, 79, 72, 76]) midiNoteOn(n, 100);
      await wait(60);
      const drawn = (layer) => genSettings(layer).voices.filter((v) => v.role !== 'u')
        .map((v) => v.note).sort((a, b) => a - b);
      const out = { a: drawn(0), b: drawn(1), readout: null };
      state.lastReadout = 0; await wait(400);
      out.readout = el.readoutDetail.textContent;
      midiPanic();
      midi.draws[0] = { count: 2, which: 'outer' }; midi.draws[1] = { count: 2, which: 'outer' };
      return out;
    }""")
    print("    A (lowest two) draws %s, B (highest two) draws %s" % (rules["a"], rules["b"]))
    check("layer A draws by its rule and layer B by its own",
          rules["a"] == [48, 52] and rules["b"] == [76, 79], str(rules))
    check("and the readout says which layer is leaving notes out",
          "drawing A 2 of 3, B 2 of 3" in rules["readout"] and "split at C4" in rules["readout"],
          rules["readout"][:200])

    print("\n--- A against B ---")
    against = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      genSet('shape', 'sine'); genSet('shape', 'sine', 1);
      el.midiLayerPair.value = 'against'; el.midiLayerPair.dispatchEvent(new Event('change'));
      for (const n of [48, 55, 76]) midiNoteOn(n, 100);
      await wait(700);
      const rate = state.source.sampleRate;
      const w = state.source.getLatestWindow(16384);
      const hz = [48, 55, 76].map((n) => 440 * Math.pow(2, (n - 69) / 12));
      const out = { channels: state.source.channels, figures: state.source.figures(),
        names: [laneName(0), laneName(1)], xyOff: el.xyX.disabled,
        x: hz.map((f) => window.__bin(w[0], f, rate)), y: hz.map((f) => window.__bin(w[1], f, rate)) };
      midiPanic();
      el.midiLayerPair.value = 'each'; el.midiLayerPair.dispatchEvent(new Event('change'));
      return out;
    }""")
    print("    C, G, E - X %s, Y %s" % (rounded(against["x"]), rounded(against["y"])))
    xtop = max(against["x"][0], 1e-9)
    check("A against B is one pair: both of A's drawn notes on X, B's on Y",
          against["channels"] == 2 and against["figures"] is None
          and against["x"][0] > 0.03 and against["x"][1] > 0.03 and against["x"][2] < xtop * 0.01
          and against["y"][2] > 0.03 and against["y"][0] < xtop * 0.01 and against["y"][1] < xtop * 0.01,
          str(against))
    check("named for the layers, with the X-Y menus back",
          against["names"] == ["Layer A", "Layer B"] and not against["xyOff"], str(against))

    print("\n--- two figures, both drawn ---")
    # Only layer B holds notes, so layer A's figure is a dot at the centre and
    # anything else lit on the screen is layer B's.
    figs = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setDisplay('xy'); state.persistence = 0; el.persistence.value = '0';
      // Full ink for every stroke. The beam's shading keeps a slowly adapting
      // reference per figure, and after a switch it is still tuned to whatever
      // that figure drew before - a dot, here - so a shaded comparison between
      // the two layouts measures the adaptation rather than the drawing.
      const shaded = state.beamXY; state.beamXY = false;
      genSet('phase', Math.PI / 2);
      for (const n of [72, 79]) midiNoteOn(n, 100);
      await wait(600);
      const lit = (g) => g.reduce((a, v) => a + (v > 0.2 ? 1 : 0), 0) / g.length;
      const out = { each: lit(phosphor.grid), xyOff: el.xyX.disabled };
      // The same notes in one layer and no split, drawn as a single figure:
      // what B's figure should look like on its own.
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(600);
      out.alone = lit(phosphor.grid);
      midiPanic();
      state.beamXY = shaded;
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      return out;
    }""")
    print("    lit with only layer B playing %.3f; the same notes as one layer %.3f"
          % (figs["each"], figs["alone"]))
    check("layer B's figure is drawn beside A's, not just A's",
          figs["each"] > figs["alone"] * 0.5 and figs["alone"] > 0.02, str(figs))
    check("and the X-Y menus step aside while the layers choose the figures", figs["xyOff"], str(figs))

    lag = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.lagOn.checked = true; el.lagOn.dispatchEvent(new Event('change'));
      for (const n of [48, 72]) midiNoteOn(n, 100);
      await wait(300);
      const out = { lag: lagActive(), figures: sourceFigures(), lanes: laneCount(), xyOff: el.xyX.disabled };
      midiPanic();
      el.lagOn.checked = false; el.lagOn.dispatchEvent(new Event('change'));
      await wait(100);
      out.after = sourceFigures();
      // The lag switched on the way a modulation source does it, by its
      // offset, with nothing rebuilding the lanes: four still exist, so only
      // asking whether the lag is on keeps the layers' figures off the screen.
      const auto = state.lagAuto;
      state.lagAuto = false; state.lagMs = 0;
      el.lagOn.checked = true; el.lagOn.dispatchEvent(new Event('change'));
      await wait(100);
      const idle = { lag: lagActive(), figures: sourceFigures() };
      state.lagMod = 5;
      out.modulated = { idle, lag: lagActive(), lanes: state.channels.length, figures: sourceFigures() };
      state.lagMod = 0; state.lagMs = 5; state.lagAuto = auto;
      el.lagOn.checked = false; el.lagOn.dispatchEvent(new Event('change'));
      return out;
    }""")
    print("    %s" % lag)
    check("with the lag on the figure is the lag's, not the layers'",
          lag["lag"] and lag["figures"] is None and lag["lanes"] == 2
          and lag["after"] == [[0, 1], [2, 3]], str(lag))
    m = lag["modulated"]
    check("even when a modulation turns the lag on and nothing rebuilds the lanes",
          not m["idle"]["lag"] and m["idle"]["figures"] == [[0, 1], [2, 3]]
          and m["lag"] and m["lanes"] == 4 and m["figures"] is None, str(m))

    print("\n--- through the worklet ---")
    heard = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      genSet('shape', 'sine'); genSet('shape', 'sine', 1);
      state.genSound = true; await applyGeneratorSound();
      for (const n of [48, 55, 76]) midiNoteOn(n, 100);
      const chain = Array.from(monitorChains)[0];
      const ctx = chain.input.context;
      const tap = ctx.createAnalyser(); tap.fftSize = 16384;
      chain.input.connect(tap);
      await wait(900);
      const x = new Float32Array(tap.fftSize); tap.getFloatTimeDomainData(x);
      const w = state.source.getLatestWindow(16384);
      const rate = ctx.sampleRate;
      const hz = [48, 55, 76].map((n) => 440 * Math.pow(2, (n - 69) / 12));
      const out = { audible: state.source.audible(), chains: monitorChains.size,
        heard: hz.map((f) => window.__bin(x, f, rate)),
        aX: hz.map((f) => window.__bin(w[0], f, rate)),
        bX: hz.map((f) => window.__bin(w[2], f, rate)) };
      midiPanic();
      state.genSound = false; await applyGeneratorSound();
      return out;
    }""")
    print("    C, G, E - heard %s; A's X %s; B's X %s"
          % (rounded(heard["heard"]), rounded(heard["aX"]), rounded(heard["bX"])))
    htop = max(heard["aX"][0], 1e-9)
    check("the worklet sounds both layers", heard["audible"] and min(heard["heard"]) > 0.01, str(heard))
    check("and posts layer B's picture back apart from A's",
          heard["bX"][2] > 0.03 and heard["bX"][0] < htop * 0.01
          and heard["aX"][0] > 0.03 and heard["aX"][2] < htop * 0.01, str(heard))

    print("\n--- the panel edits one layer at a time ---")
    panel = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const input = (id, v) => { el[id].value = String(v); el[id].dispatchEvent(new Event('input')); };
      input('amp', 50); input('envRelease', 300);
      const a0 = { amp: genSettings().amp, rel: genSettings().releaseMs };
      el.midiEditB.click(); await wait(30);
      const showsB = { title: el.genTitle.textContent,
                       freqShown: getComputedStyle(el.freq.closest('.menu-row')).display !== 'none',
                       ampShown: getComputedStyle(el.amp.closest('.menu-row')).display !== 'none' };
      input('amp', 90); input('envRelease', 1200);
      el.shape.value = 'triangle'; el.shape.dispatchEvent(new Event('change'));
      const out = { a0, showsB,
        a: { amp: genSettings().amp, rel: genSettings().releaseMs, shape: genSettings().shape },
        b: { amp: genSettings(1).amp, rel: genSettings(1).releaseMs, shape: genSettings(1).shape } };
      // A code written while B is on screen is layer A's controls and B's
      // sound, each in its own place.
      out.code = snapshot();
      el.midiEditA.click(); await wait(30);
      out.backToA = { amp: el.amp.value, rel: el.envRelease.value, shape: el.shape.value,
                      title: el.genTitle.textContent };
      return out;
    }""")
    print("    %s" % panel)
    check("with B shown, the panel says so and shows only what B has",
          panel["showsB"]["title"].endswith("layer B") and not panel["showsB"]["freqShown"]
          and panel["showsB"]["ampShown"], str(panel["showsB"]))
    check("and its controls write layer B, leaving A alone",
          abs(panel["b"]["amp"] - 0.9) < 1e-9 and panel["b"]["rel"] == 1200 and panel["b"]["shape"] == "triangle"
          and abs(panel["a"]["amp"] - 0.5) < 1e-9 and panel["a"]["rel"] == 300 and panel["a"]["shape"] != "triangle",
          str(panel))
    check("Edit A puts A's values back on the controls",
          panel["backToA"]["amp"] == "50" and panel["backToA"]["rel"] == "300"
          and panel["backToA"]["shape"] != "triangle" and panel["backToA"]["title"] == "Generator",
          str(panel["backToA"]))
    code = panel["code"]
    check("a code taken with B on screen keeps A's controls as A's",
          code["amp"] == 50 and code["rel"] == 300 and code["bAmp"] == 90 and code["bRel"] == 1200
          and code["bShape"] == "triangle" and code["layers"] == "split", str({k: code[k] for k in
          ("amp", "rel", "bAmp", "bRel", "bShape", "layers")}))

    print("\n--- the setup code carries the layers ---")
    trip = p.evaluate("""async ([code]) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      midi.draws[1] = { count: 3, which: 'recent' };
      const snap = Object.assign({}, code, snapshot());
      snap.layerPair = 'against'; snap.splitAt = 67;
      // Not the defaults: restored with the defaults, A's release and the
      // core's own are both 180 ms, and B getting its own defaults instead of
      // A's values passed this check - the mutation pass found it.
      restore({ midiMode: 'dyad', rel: 900, amp: 30 });
      await wait(60);
      const reset = { layers: midi.layers.mode, b: genSettings(1).amp, bRel: genSettings(1).releaseMs,
                      aRel: genSettings().releaseMs, a: genSettings().amp };
      restore(snap);
      await wait(60);
      return { reset, mode: midi.layers.mode, point: midi.layers.point, pair: midi.layers.pair,
               drawB: { ...midi.draws[1] }, bAmp: genSettings(1).amp, bRel: genSettings(1).releaseMs,
               bShape: genSettings(1).shape, aAmp: genSettings().amp };
    }""", [code])
    print("    %s" % trip)
    check("split, point, pairing, B's rule and B's sound survive a setup code",
          trip["mode"] == "split" and trip["point"] == 67 and trip["pair"] == "against"
          and trip["drawB"] == {"count": 3, "which": "recent"} and abs(trip["bAmp"] - 0.9) < 1e-9
          and trip["bRel"] == 1200 and trip["bShape"] == "triangle" and abs(trip["aAmp"] - 0.5) < 1e-9,
          str(trip))
    check("a code's envelope reaches the generator, not only its sliders",
          trip["reset"]["aRel"] == 900, str(trip["reset"]))
    check("and a code from before layers has none, with B sounding like A",
          trip["reset"]["layers"] == "off" and trip["reset"]["bRel"] == 900
          and abs(trip["reset"]["b"] - 0.3) < 1e-9, str(trip["reset"]))

    print("\n--- the layers go when what made them possible does ---")
    gone = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setMidiMode('poly'); el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      midi.layers.pair = 'each';
      el.midiEditB.click();
      for (const n of [48, 72]) midiNoteOn(n, 100);
      await wait(60);
      const before = { on: layersOn(), channels: state.source.channels, edit: el.toneRows.dataset.layerEdit };
      setMidiMode('dyad'); await wait(60);
      const dyad = { on: layersOn(), b: genSettings(1).voices, channels: state.source.channels,
                     layout: state.source.layout, edit: el.toneRows.dataset.layerEdit,
                     rowHidden: el.midiLayerRow.hidden };
      setMidiMode('poly'); await wait(60);
      const back = { on: layersOn(), b: genSettings(1).voices.map((v) => v.note),
                     a: genSettings().voices.map((v) => v.note) };
      midiPanic();
      return { before, dyad, back };
    }""")
    print("    %s" % gone)
    check("leaving poly ends layer B and gives the page two lanes and layer A's panel",
          gone["before"]["on"] and gone["before"]["channels"] == 4 and gone["before"]["edit"] == "b"
          and not gone["dyad"]["on"] and gone["dyad"]["b"] is None and gone["dyad"]["channels"] == 2
          and gone["dyad"]["layout"] == "one" and gone["dyad"]["edit"] == "a" and gone["dyad"]["rowHidden"],
          str(gone))
    check("and coming back to poly splits the held notes again",
          gone["back"]["on"] and gone["back"]["a"] == [48] and gone["back"]["b"] == [72], str(gone["back"]))

    rack = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.rackSynth.checked = true; await setRackSynth(true);
      await wait(600);
      const out = { lane: !!genLane(), on: layersOn(), mode: midi.layers.mode,
                    note: el.midiLayersNote.hidden ? '' : el.midiLayersNote.textContent };
      return out;
    }""")
    print("    %s" % rack)
    check("in a rack a split is kept, not applied, and the panel says why",
          rack["lane"] and not rack["on"] and rack["mode"] == "split" and "one layer" in rack["note"],
          str(rack))

    if bad: print("    first error inside the page: %s" % p.evaluate("() => window.__errs[0]"))
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("two layers from one keyboard, each drawn and heard as its own")
