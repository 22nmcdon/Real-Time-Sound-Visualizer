"""The core in WebAssembly (stage 5): the compiled core in both worklets.

The page carries the C++ core's generator, compiled, as base64 between two
marker comments, and its worklets - the generator's and the effects' on a live
input - run it in place of `makeGeneratorCore` unless the address says
`?core=js`. `core/tests/parity.py` holds the module to the JavaScript core
through the parity harness's own runs. This holds it in the browser, through
what the page itself sends:

THE PAGE'S COPY IS THIS CORE. The module is generated, not written, and has to
be built again whenever the core changes; `core/wasm/build.py --check` builds
it and compares. That needs clang's wasm32 target and the WASI libc, which not
everyone running the web suite has, so without them the check says SKIP, by
name, rather than passing.

THE WORKLETS RUN IT. Each worklet says which core it made, and the page
records what it said: `wasm` by default and `js` with `?core=js`, which is the
null - the reading comes from the audio thread, not from the address. And a
module the browser will not make falls back: the worklet makes the
JavaScript core, says so and why, and the sound goes on.

EVERY PRESET IS THE SAME SOUND. Each generator preset applied as a player
would, and its settings, routes and oscillators given to both cores the way
the worklet gives them - through JSON at construction, as processorOptions
are, and then again as live objects, as a message brings them - and run for
a quarter of a second each: the samples and everything the worklet reads
back, compared value for value. And every preset's effects, as the effects
worklet would be given them, on a stereo input through both cores.
"""
import os, shutil, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(ART)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
TOL = 1e-12

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


print("\n--- the page's copy of the core ---")
def toolchain():
    if not shutil.which("clang++"): return False
    with tempfile.TemporaryDirectory() as tmp:
        probe = os.path.join(tmp, "probe.cpp")
        with open(probe, "w") as f: f.write("#include <vector>\nint main() { return std::vector<int>(1).size(); }\n")
        # Compiled and not linked: whether the target and its headers are
        # here. Whether the core links is the check's business, and fails it.
        return subprocess.run(["clang++", "--target=wasm32-wasi", "--sysroot=/usr", "-c", probe, "-o", os.path.join(tmp, "p.o")],
                              capture_output=True).returncode == 0
if toolchain():
    fresh = subprocess.run([sys.executable, os.path.join(ROOT, "core", "wasm", "build.py"), "--check"],
                           capture_output=True, text=True)
    check("the module in the page is the core as it stands, compiled", fresh.returncode == 0,
          (fresh.stdout + fresh.stderr).strip()[-300:])
else:
    print("  SKIP  the module in the page is the core as it stands: no clang++ with the wasm32-wasi target here")


PRESET_RUN = """async () => {
  const mul = (seed) => {
    let a = seed;
    return () => {
      a |= 0; a = a + 0x6D2B79F5 | 0;
      let t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  };
  const bytes = wasmCore(), N = 128, BLOCKS = 96, AGAIN = 32;
  const far = (a, b) => {
    let most = 0;
    for (let i = 0; i < a.length; i++) {
      const x = a[i], y = b[i];
      if (x === y || (Number.isNaN(x) && Number.isNaN(y))) continue;
      if (Number.isNaN(x) || Number.isNaN(y)) return Infinity;
      most = Math.max(most, Math.abs(x - y) / Math.max(1, Math.abs(x)));
    }
    return a.length === b.length ? most : Infinity;
  };
  // One core of either kind through the worklet's whole life: made, given
  // its settings as processorOptions are (JSON), run, given them again as a
  // message gives them (the objects), run on.
  const play = (wasm, tone, toneB, routes, seed, pictureOnly) => {
    const ls = lfos.map((l) => ({ shape: l.shape, rate: l.rate, depth: l.depth, phase: 0, held: 0, value: 0, epoch: 0 }));
    const real = Math.random;
    Math.random = mul(seed);
    try {
      const c = wasm ? makeWasmCore(bytes, 48000, GEN_DESTS.length, ls, seed) : makeGeneratorCore(48000, GEN_DESTS.length, ls);
      const asSent = JSON.parse(JSON.stringify({ tone, toneB }));
      for (const f in asSent.tone) c.set(f, asSent.tone[f]);
      for (const f in asSent.toneB) c.set(f, asSent.toneB[f], 1);
      c.setRoutes(JSON.parse(JSON.stringify(routes)));
      const bufs = Array.from({ length: 6 }, () => new Float32Array(N));
      const out = [];
      out.peak = 0;
      for (let b = 0; b < BLOCKS; b++) {
        if (b === AGAIN) {
          for (const f in tone) c.set(f, tone[f]);
          for (const f in toneB) c.set(f, toneB[f], 1);
          c.setRoutes(routes);
        }
        if (pictureOnly) c.block(bufs[0], bufs[1], N);
        else c.block(bufs[0], bufs[1], N, bufs[2], bufs[3], bufs[4], bufs[5]);
        for (const buf of bufs) for (let i = 0; i < N; i++) out.push(buf[i]);
        for (let i = 0; i < N; i++) out.peak = Math.max(out.peak, Math.abs(bufs[0][i]), Math.abs(bufs[1][i]));
        const d = c.drawing, g = c.budget;
        out.push(c.envelope, c.crossings.x, c.crossings.y, g.units, g.asked[0], g.asked[1], g.unison[0], g.unison[1],
                 g.askedFactor, g.factor, g.silenced, d.swing, d.pendulum, d.turn[0], d.turn[1], d.turn[2], d.facing);
        for (const l of ls) out.push(l.phase, l.held, l.value);
      }
      return out;
    } finally {
      Math.random = real;
    }
  };
  // The effects worklet's life: made with a live input's fields, given them
  // again as a message would, and handed a stereo input of its own - 220 Hz
  // and 330 Hz, never a circle - block by block.
  const wet = (wasm, tone, routes, seed) => {
    const ls = lfos.map((l) => ({ shape: l.shape, rate: l.rate, depth: l.depth, phase: 0, held: 0, value: 0, epoch: 0 }));
    const real = Math.random;
    Math.random = mul(seed);
    try {
      const c = wasm ? makeWasmCore(bytes, 48000, GEN_DESTS.length, ls, seed) : makeGeneratorCore(48000, GEN_DESTS.length, ls);
      const asSent = JSON.parse(JSON.stringify(tone));
      for (const f in asSent) c.set(f, asSent[f]);
      c.setRoutes(JSON.parse(JSON.stringify(routes)));
      const inL = new Float32Array(N), inR = new Float32Array(N), oL = new Float32Array(N), oR = new Float32Array(N);
      const out = [];
      out.changed = 0;
      for (let b = 0; b < 64; b++) {
        if (b === 16) { for (const f in tone) c.set(f, tone[f]); c.setRoutes(routes); }
        for (let i = 0; i < N; i++) {
          inL[i] = 0.6 * Math.sin(2 * Math.PI * 220 * (b * N + i) / 48000);
          inR[i] = 0.5 * Math.sin(2 * Math.PI * 330 * (b * N + i) / 48000);
        }
        c.effect(inL, inR, oL, oR, N);
        for (let i = 0; i < N; i++) {
          out.push(oL[i], oR[i]);
          out.changed = Math.max(out.changed, Math.abs(oL[i] - inL[i]), Math.abs(oR[i] - inR[i]));
        }
        for (const l of ls) out.push(l.phase, l.held, l.value);
      }
      return out;
    } finally {
      Math.random = real;
    }
  };
  const rows = [], effects = [];
  for (const [, entries, kind] of PRESETS) {
    for (const [name] of entries) {
      applyPreset("b:" + name);
      {
        const tone = liveFxFields(), routes = workletRoutes();
        const js = wet(false, tone, routes, 5);
        effects.push({ name, worst: far(js, wet(true, tone, routes, 5)), changed: js.changed,
                       wrong: effects.length < 4 ? far(js, wet(true, { ...tone, planeTwist: (tone.planeTwist || 0) + 0.01 }, routes, 5)) : null });
      }
      if (kind !== "generator") continue;
      const tone = genSettings(), toneB = genSettings(1) || {};
      if (!tone) { rows.push({ name, missing: true }); continue; }
      const routes = workletRoutes();
      const js = play(false, tone, toneB, routes, 11), wa = play(true, tone, toneB, routes, 11);
      const peak = js.peak;
      // The null: the same preset with its first route a hundredth stronger,
      // or with its tone a cent sharp where it has no route.
      let wrong = null;
      if (rows.length < 6) {
        const bent = routes.length ? routes.map((r, i) => i ? r : { ...r, amount: r.amount * 1.01, amountB: r.amountB * 1.01 }) : routes;
        const sharp = routes.length ? tone : { ...tone, freq: tone.freq * Math.pow(2, 1 / 1200) };
        wrong = far(js, play(true, sharp, toneB, bent, 11));
      }
      // And as the main thread asks: the picture alone.
      const alone = far(play(false, tone, toneB, routes, 11, true), play(true, tone, toneB, routes, 11, true));
      rows.push({ name, worst: Math.max(far(js, wa), alone), peak, routes: routes.length, length: js.length, wrong });
    }
  }
  return { rows, effects };
}"""


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    def open_page(query, init=None):
        p = b.new_page(viewport={"width": 1400, "height": 900})
        if init: p.add_init_script(init)
        bad = []
        p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
        p.on("console", lambda m: bad.append("console: " + m.text)
             if m.type == "error" and "ERR_CERT" not in m.text else None)
        # On ?brain=js (5m): this suite reads which core the page's own two
        # worklets and its main thread run - the page's own brain, which
        # core/tests/parity.py holds the instrument to. The instrument, the
        # site's default since 5m, is braintest.py's and hosttest.py's.
        query = query + "&brain=js" if query else "?brain=js"
        p.goto(f"file://{ART}/scope.html{query}"); p.wait_for_timeout(700)
        if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
        p.wait_for_timeout(200)
        return p, bad

    def sound(p):
        p.evaluate("async () => { state.genSound = true; await applyGeneratorSound(); }")
        p.wait_for_timeout(700)
        return p.evaluate("""() => {
          const f = capture();
          let peak = 0;
          for (const v of f.channels[0]) peak = Math.max(peak, Math.abs(v));
          return { kind: state.source.coreKind, why: state.source.coreWhy, switch: CORE_IN_WASM, blocks: state.source.blocks,
                   main: state.source.mainCoreKind, mainWhy: state.source.mainCoreWhy,
                   picture: pictureCoreKind, pictureWhy: pictureCoreWhy, setup: setupCoreKind, setupWhy: setupCoreWhy,
                   fault: state.source.fault, peak, driver: lfoDriver(), phase: lfos[0].phase };
        }""")

    # The effects worklet, on a stub microphone - two oscillators, 3:2 - with
    # the mirror on, so the insert makes its node.
    def effects(p):
        return p.evaluate("""async () => {
          const wait = (ms) => new Promise((r) => setTimeout(r, ms));
          const ctx = new AudioContext();
          const merge = ctx.createChannelMerger(2), dest = ctx.createMediaStreamDestination();
          const a = ctx.createOscillator(), c = ctx.createOscillator();
          a.frequency.value = 220; c.frequency.value = 330;
          a.connect(merge, 0, 0); c.connect(merge, 0, 1); merge.connect(dest); a.start(); c.start();
          navigator.mediaDevices.getUserMedia = () => Promise.resolve(dest.stream);
          el.srcMic.click(); await wait(1200);
          el.planeMirror.value = "3"; el.planeMirror.dispatchEvent(new Event("change")); await wait(1200);
          const w = state.source.getLatestWindow(4410);
          const fx = state.source.fx || {};
          return { source: state.source.kind, active: fx.active, kind: fx.coreKind,
                   why: fx.coreWhy, fault: fx.fault || state.sourceError || null,
                   lowX: Math.min(...w[0]), lowY: Math.min(...w[1]) };
        }""")

    print("\n--- the worklets run it, by default ---")
    p, bad = open_page("")
    on = sound(p)
    check("the generator's worklet says it is running the compiled core", on["switch"] and on["kind"] == "wasm" and on["why"] is None, str(on))
    check("and so does the main thread's generator, which draws while the sound is off", on["main"] == "wasm" and on["mainWhy"] is None,
          "%r %r" % (on["main"], on["mainWhy"]))
    check("and so do the picture's own sources - the grid, the photocell, the meter", on["picture"] == "wasm" and on["pictureWhy"] is None,
          "%r %r" % (on["picture"], on["pictureWhy"]))
    check("and so do the setup codes", on["setup"] == "wasm" and on["setupWhy"] is None, "%r %r" % (on["setup"], on["setupWhy"]))
    check("and it plays, and the picture is drawn from what it sends",
          on["fault"] is None and on["blocks"] > 3 and on["peak"] > 0.05 and on["driver"] == "worklet",
          "%d blocks, peak %.3f, fault %r" % (on["blocks"], on["peak"], on["fault"]))
    p.wait_for_timeout(300)
    later = p.evaluate("() => ({ phase: lfos[0].phase, blocks: state.source.blocks })")
    check("and the oscillators' phases come back from it", later["phase"] != on["phase"] and later["blocks"] > on["blocks"],
          "%r then %r" % (on["phase"], later["phase"]))

    print("\n--- every preset, both cores ---")
    ran = p.evaluate(PRESET_RUN)
    rows, wets = ran["rows"], ran["effects"]
    missing = [r["name"] for r in rows if r.get("missing")]
    worst = max((r["worst"] for r in rows if not r.get("missing")), default=float("inf"))
    off = [(r["name"], r["worst"]) for r in rows if not r.get("missing") and not r["worst"] <= TOL]
    check("%d generator presets, every one the same to %g in samples and in what comes back" % (len(rows), TOL),
          rows and not missing and not off, "worst %.3g; %s" % (worst, off[:4] or missing[:4]))
    quiet = [r["name"] for r in rows if not r.get("missing") and r["peak"] < 0.05]
    routed = sum(1 for r in rows if not r.get("missing") and r["routes"] > 0)
    check("and they can show it: every one makes a picture, and %d have routes for the oscillators to carry" % routed,
          not quiet and routed >= 10, ", ".join(quiet[:4]))
    nulls = [r for r in rows if r.get("wrong") is not None]
    check("and the comparison fails against a route a hundredth stronger, or a tone a cent sharp",
          len(nulls) == 6 and all(r["wrong"] > TOL for r in nulls), ", ".join("%s %.3g" % (r["name"], r["wrong"]) for r in nulls))
    woff = [(r["name"], r["worst"]) for r in wets if not r["worst"] <= TOL]
    acting = sum(1 for r in wets if r["changed"] > 0.01)
    check("%d presets' effects on a live input, every one the same to %g, %d of them changing it" % (len(wets), TOL, acting),
          wets and not woff and acting >= 20, "worst %.3g; %s" % (max((r["worst"] for r in wets), default=0), woff[:4]))
    wnulls = [r for r in wets if r.get("wrong") is not None]
    check("and the comparison fails against the twist a hundredth of a radian further",
          len(wnulls) == 4 and all(r["wrong"] > TOL for r in wnulls), ", ".join("%s %.3g" % (r["name"], r["wrong"]) for r in wnulls))

    print("\n--- the picture's own sources, recorded and played into both ---")
    # Every call the page makes to its picture engine over a second and a
    # half of real frames, with copies of what it was handed - the walks'
    # polylines, the drawn pair's lanes, the photocell and the picture's
    # values as they stood - played in order into a fresh JavaScript engine and
    # a fresh compiled one, and the cells and every reading compared after
    # each call. The scenarios are every preset that turns the photocell on,
    # then Y-T, the spectrogram, persistence off and infinite, and a Clear.
    PICTURE = """async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const E = pictureEngine;
      const slice = (v, n) => Array.prototype.slice.call(v, 0, n);
      const copies = {
        fade: (p, w) => [p, !!w],
        segment: (plot, x0, y0, x1, y1, level) => [{ ...plot }, x0, y0, x1, y1, level],
        deposit: (plot, xs, ys, count, steps) => [{ ...plot }, slice(xs, count), slice(ys, count), count, steps ? slice(steps, count) : null],
        blank: () => [],
        photoStep: (ph, elapsed, spect) => [{ on: ph.on, u: ph.u, v: ph.v, value: ph.value, raw: ph.raw }, elapsed, spect],
        pictureStep: (ph, pic, pair, elapsed, spect, limiting) => [
          { on: ph.on }, JSON.parse(JSON.stringify(pic)),
          pair ? { ...pair, left: Float32Array.from(pair.left.subarray(0, pair.n)), right: Float32Array.from(pair.right.subarray(0, pair.n)) } : null,
          elapsed, spect, limiting],
      };
      const record = async (setUp, ms) => {
        const log = [], kept = {};
        for (const name in copies) {
          kept[name] = E[name];
          E[name] = function (...args) { log.push([name, copies[name](...args)]); return kept[name].apply(E, args); };
        }
        const keptReset = E.meter.reset;
        E.meter.reset = function () { log.push(["reset", []]); return keptReset.call(E.meter); };
        try { await setUp(); await wait(ms); }
        finally { for (const name in copies) E[name] = kept[name]; E.meter.reset = keptReset; }
        return log;
      };
      const readings = (e) => [e.roundness, e.bored, e.frames, e.meter.coverage, e.meter.lit, e.meter.change, e.meter.novelty,
                               e.meter.depth, e.shape.signed, e.shape.edge];
      // Both engines through one log in step; `bend` changes what one of
      // them is given, for the nulls.
      const replay = (log, bend) => {
        const js = makePictureEngine(), wa = makeWasmPictureEngine(wasmModule());
        let worst = 0, lit = 0, photoMost = 0, worstAt = "";
        const verdicts = new Set(), counts = {};
        const far = (a, b) => (a === b || (Number.isNaN(a) && Number.isNaN(b)) ? 0 : Math.abs(a - b) || Infinity);
        for (let k = 0; k < log.length; k++) {
          const [op, a] = log[k];
          counts[op] = (counts[op] || 0) + 1;
          const forWa = bend ? bend(op, a) : a;
          if (op === "fade") { js.fade(a[0], a[1]); wa.fade(forWa[0], forWa[1]); }
          else if (op === "segment") { js.segment(...a); wa.segment(...forWa); }
          else if (op === "deposit") { js.deposit(...a); wa.deposit(...forWa); }
          else if (op === "blank") { js.blank(); wa.blank(); }
          else if (op === "reset") { js.meter.reset(); wa.meter.reset(); }
          else if (op === "photoStep") {
            const pj = { ...a[0] }, pw = { ...a[0] };
            js.photoStep(pj, a[1], a[2]); wa.photoStep(pw, a[1], a[2]);
            const d = Math.max(far(pj.value, pw.value), far(pj.raw, pw.raw));
            if (d > worst) { worst = d; worstAt = op + " " + k; }
            photoMost = Math.max(photoMost, pj.value);
          } else if (op === "pictureStep") {
            const cj = JSON.parse(JSON.stringify(a[1])), cw = JSON.parse(JSON.stringify(a[1]));
            js.pictureStep(a[0], cj, a[2], a[3], a[4], a[5]); wa.pictureStep(a[0], cw, a[2], a[3], a[4], a[5]);
            for (const key of PICTURE_KEYS) {
              const d = Math.max(far(cj[key], cw[key]), far(cj.raw[key], cw.raw[key]));
              if (d > worst) { worst = d; worstAt = op + " " + key + " " + k; }
            }
            const rj = readings(js), rw = readings(wa);
            for (let i = 0; i < rj.length; i++) { const d = far(rj[i], rw[i]); if (d > worst) { worst = d; worstAt = "reading " + i + " at " + k; } }
            const vj = js.meter.verdict();
            if (vj !== wa.meter.verdict()) { worst = Infinity; worstAt = "verdict at " + k; }
            verdicts.add(vj);
          }
          const gj = js.cells, gw = wa.cells;
          for (let i = 0; i < gj.length; i++) {
            const d = far(gj[i], gw[i]);
            if (d > worst) { worst = d; worstAt = op + " cell " + i + " at " + k; }
            lit = Math.max(lit, gj[i]);
          }
        }
        return { worst, worstAt, lit, photoMost, verdicts: [...verdicts], counts, last: js.meter.verdict(), edge: js.shape.edge };
      };
      const uses = (setup) => setup.photoOn === true;
      const scenarios = [];
      for (const [, entries] of PRESETS) for (const [name, setup] of entries) {
        if (uses(setup)) scenarios.push([name, () => applyPreset("b:" + name)]);
      }
      let turnedOnScreen = 0;
      // And one long enough for the meter to give a verdict - it says nothing
      // until four seconds of history - on a preset that keeps finding new shapes.
      // Five seconds of it, then the photocell off and on, which starts the
      // meter's history again.
      scenarios.push(["Something new each time, then the photocell off and on", async () => {
        applyPreset("b:Something new each time"); await wait(5500); setPhoto(false); setPhoto(true);
      }, 800]);
      // A word turned and zoomed until the screen's edge clips it: the only
      // place the turn shows in what the picture says, since a turn leaves
      // which way round the beam goes alone - and a word, because a figure
      // with a mirror in it (a 3:2 Lissajous, a heart) clips the same turned
      // either way, which hid a turn applied backwards.
      scenarios.push(["a word turned and clipped", () => {
        applyPreset("b:Written on the screen"); el.dispXY.click(); setPhoto(true); state.rotate = 0.1; setZoom(6);
      }]);
      // And the turn the picture applies itself, rather than the signal: with
      // the lag on, the pair is a signal against its own past, which no turn
      // of the signal could mean, so the drawn pair is turned on the screen
      // and the shape is taken from it turned - the only case in which the
      // pair's own turn is not nought.
      scenarios.push(["the lag's figure turned on the screen and clipped", () => {
        applyPreset("b:Harmonic tone"); el.dispXY.click(); setPhoto(true);
        el.lagOn.checked = true; el.lagOn.dispatchEvent(new Event("change")); state.rotate = 0.1; setZoom(6);
      }]);
      scenarios.push(["Y-T with the photocell", () => { applyPreset("b:Harmonic tone"); setPhoto(true); el.dispYT.click(); }]);
      // Ink on the grid first, so the spectrogram's blank has something to clear.
      scenarios.push(["the spectrogram with the photocell", async () => { el.dispXY.click(); setPhoto(true); await wait(600); el.dispSpect.click(); }]);
      scenarios.push(["X-Y, persistence off", () => { el.dispXY.click(); setPhoto(true); state.persistence = 0; }]);
      scenarios.push(["X-Y, persistence infinite", () => { state.persistence = -1; }]);
      scenarios.push(["a Clear", async () => { state.persistence = 0.12; await wait(300); el.clearButton.click(); }]);
      const rows = [];
      let first = null, longest = null;
      for (const [name, setUp, ms] of scenarios) {
        const log = await record(setUp, ms || 1500);
        if (name.startsWith("the lag's")) turnedOnScreen = Math.max(0, ...log.filter(([op, a]) => op === "pictureStep" && a[2]).map(([, a]) => Math.abs(a[2].spin)));
        if (!first && log.some(([op]) => op === "deposit")) first = log;
        if (name.includes("off and on")) longest = log;
        rows.push(Object.assign({ name }, replay(log)));
      }
      setZoom(0); state.rotate = 0; el.lagOn.checked = false; el.lagOn.dispatchEvent(new Event("change"));
      // The long one again with the monitor's limiters held hard down, which
      // the sound being off never does: the verdict has to run away, in both.
      const strained = longest.map(([op, a]) => [op, op === "pictureStep" ? [a[0], a[1], a[2], a[3], a[4], -8] : a]);
      rows.push(Object.assign({ name: "the long one with the limiters at -8 dB" }, replay(strained)));
      // A still picture, which the meter has to call settled: the long one's
      // frames up to its fortieth step, then that step again and again, a
      // quarter of a second apart and nothing new laid, for eight seconds.
      const steps = longest.filter(([op]) => op === "pictureStep");
      const at = longest.indexOf(steps[Math.min(39, steps.length - 1)]);
      const [, held] = longest[at];
      const still = longest.slice(0, at + 1);
      for (let k = 0; k < 32; k++) still.push(["pictureStep", [{ on: true }, held[1], held[2], 250, false, 0]]);
      rows.push(Object.assign({ name: "a still picture, eight seconds" }, replay(still)));
      // The nulls: the compiled engine given persistence a thousandth more,
      // and given every deposit a step brighter.
      const nulls = first ? [
        replay(first, (op, a) => (op === "fade" && a[0] > 0 ? [a[0] + 0.001, a[1]] : a)).worst,
        replay(first, (op, a) => (op === "deposit" ? [a[0], a[1], a[2], a[3], a[4] ? a[4].map((v) => Math.min(v + 1, BEAM_K - 1)) : a[4]] : a)).worst,
      ] : [];
      return { rows, nulls, turnedOnScreen };
    }"""
    ran = p.evaluate(PICTURE)
    prow = ran["rows"]
    off = [(r["name"], r["worst"], r["worstAt"]) for r in prow if not r["worst"] <= TOL]
    check("%d scenarios of the picture's sources, the compiled engine the same as the JavaScript to %g after every call"
          % (len(prow), TOL), prow and not off, "; ".join("%s %.3g at %s" % o for o in off[:3]))
    deposits = sum(r["counts"].get("deposit", 0) + r["counts"].get("segment", 0) for r in prow)
    steps = sum(r["counts"].get("pictureStep", 0) for r in prow)
    verdicts = set(v for r in prow for v in r["verdicts"])
    clipped = [r["name"] for r in prow if r["edge"] > 0.01]
    check("and the lag's figure is turned by the screen, not the signal, a tenth of a turn", abs(ran["turnedOnScreen"] - 0.1) < 1e-9,
          str(ran["turnedOnScreen"]))
    strained = prow[-2]
    still = prow[-1]
    lit = [r["name"] for r in prow if r["lit"] > 0.5]
    lightly = [r["name"] for r in prow if r["photoMost"] > 0.01]
    check("and they can show it: %d walks laid, %d steps, %d scenarios lighting the grid, %d moving the photocell, verdicts %s"
          % (deposits, steps, len(lit), len(lightly), sorted(verdicts)),
          deposits > 1000 and steps > 500 and len(lit) >= len(prow) - 3 and len(lightly) >= 5 and len(verdicts) >= 2)
    reset = next((r for r in prow if "off and on" in r["name"]), {"verdicts": [], "last": None})
    check("and the edge, a reset mid-run, the limiters and a still picture: %s clipped, %s then %s across the reset, %s with the limiters down, %s when still"
          % (clipped, sorted(reset["verdicts"]), reset["last"], sorted(strained["verdicts"]), still["last"]),
          clipped and set(reset["verdicts"]) - {"listening"} and reset["last"] == "listening"
          and "running away" in strained["verdicts"] and still["last"] == "settled")
    check("and the comparison fails against persistence a thousandth more, or every walk a step brighter",
          len(ran["nulls"]) == 2 and all(n > TOL for n in ran["nulls"]), str(ran["nulls"]))

    print("\n--- the effects worklet, by default ---")
    fx = effects(p)
    # The mirror on both axes folds each channel to its positive half, so
    # neither lane goes below nought if the effect is in the path.
    check("the effects worklet on a microphone says it is running the compiled core, and mirrors the input",
          fx["source"] == "mic" and fx["active"] and fx["kind"] == "wasm" and fx["why"] is None and fx["fault"] is None
          and fx["lowX"] > -0.01 and fx["lowY"] > -0.01, str(fx))
    check("with no errors on the page", not bad, "; ".join(bad[:3]))

    print("\n--- the setup codes, both codecs ---")
    # Every preset's snapshot made into a code by each codec, and each code
    # read back by each - the page's copy and load - and then codes nobody
    # made with a snapshot: empty, not base64, base64 of things that are not
    # setups, an old version's level and clip, and names past Latin-1, which
    # cannot be made into a code at all. Each outcome compared, a throw as a
    # throw.
    SETUPS = """() => {
      const wasm = setupCodec, js = { encode: encodeSetupHere, decode: decodeSetupHere };
      const tried = (f) => { try { const v = f(); return v === null ? "null" : JSON.stringify(v); } catch (error) { return "throws"; } };
      const rows = [];
      for (const [, entries] of PRESETS) for (const [name] of entries) {
        applyPreset("b:" + name);
        const snap = snapshot();
        const cw = tried(() => wasm.encode(snap)), cj = tried(() => js.encode(snap));
        const code = cj === "throws" ? "" : JSON.parse(cj);
        rows.push([name, cw === cj && tried(() => wasm.decode(code)) === tried(() => js.decode(code)), cj.length,
                   tried(() => wasm.encode({ ...snap, freq: snap.freq + 1 })) !== cj]);
      }
      const b = (text) => btoa(text).replace(/=+$/, "");
      const odd = ["", "   ", "!!!", "not base64 at all", b("null"), b("5"), b('"x"'), b("[1,2]"), b("{}"), b("true"),
                   b('{"v":1,"trig":1,"c1s":3,"level":100}'), b('{"v":2,"c0s":4}'), b('{"v":3,"planeClip":true}'),
                   b('{"v":9,"freq":1}'), b('{"1":5,"9":1,"b":3,"a":4}'), "  " + b('{"v":4,"freq":330}') + "\\n"];
      const oddRows = odd.map((code) => [code, tried(() => wasm.decode(code)), tried(() => js.decode(code))]);
      const names = [{ macroNames: "caf\\u00e9" }, { macroNames: "\\u4e2d\\u6587" }, { figText: "lone \\ud800" }, { freq: NaN }, { freq: -0 },
                     null, [1, 2], 5, "a string"];
      const nameRows = names.map((snap) => [JSON.stringify(snap), tried(() => wasm.encode(snap)), tried(() => js.encode(snap))]);
      // A setup longer than one of the reader's chunks - twenty thousand
      // characters of text - made and read back by each.
      const long = { figText: "x".repeat(20000) + "y" };
      const longCode = js.encode(long);
      nameRows.push(["a long setup", tried(() => wasm.decode(longCode)), tried(() => js.decode(longCode))]);
      // And a code that is not a string, which the page's own throws on.
      nameRows.push(["a code that is a number", tried(() => wasm.decode(5)), tried(() => js.decode(5))]);
      return { rows, oddRows, nameRows };
    }"""
    st = p.evaluate(SETUPS)
    srows = st["rows"]
    sbad = [r[0] for r in srows if not r[1]]
    check("%d presets: each codec makes the same code from the snapshot, and reads each code back the same" % len(srows),
          srows and not sbad and all(r[2] > 10 for r in srows), ", ".join(sbad[:4]))
    check("and the comparison sees a frequency a hertz higher", all(r[3] for r in srows))
    oddbad = [r for r in st["oddRows"] + st["nameRows"] if r[1] != r[2]]
    outcomes = set(r[2] if r[2] in ("throws", "null") else "read" for r in st["oddRows"] + st["nameRows"])
    check("%d awkward codes and snapshots, the same outcome from each, a throw as a throw: %s"
          % (len(st["oddRows"]) + len(st["nameRows"]), sorted(outcomes)), not oddbad and outcomes == {"throws", "null", "read"},
          "; ".join("%r: %s | %s" % (r[0][:30], r[1][:60], r[2][:60]) for r in oddbad[:3]))

    p.close()

    print("\n--- ?core=js, the JavaScript core ---")
    p, bad = open_page("?core=js")
    js = sound(p)
    check("with ?core=js the generator's worklet says it is the JavaScript one", not js["switch"] and js["kind"] == "js"
          and js["why"] is None and js["blocks"] > 3, str(js))
    check("and so does the main thread's", js["main"] == "js" and js["mainWhy"] is None, "%r %r" % (js["main"], js["mainWhy"]))
    check("and the picture's sources", js["picture"] == "js" and js["pictureWhy"] is None, "%r %r" % (js["picture"], js["pictureWhy"]))
    check("and the setup codes", js["setup"] == "js" and js["setupWhy"] is None, "%r %r" % (js["setup"], js["setupWhy"]))
    fx = effects(p)
    check("and so does the effects worklet", fx["active"] and fx["kind"] == "js" and fx["why"] is None, str(fx))
    check("with no errors on the page", not bad, "; ".join(bad[:3]))
    p.close()

    print("\n--- a module the browser will not make ---")
    p, bad = open_page("")
    # Eight bytes with the module's magic and a version nobody has written.
    p.evaluate("() => { wasmCore = () => new Uint8Array([0, 97, 115, 109, 9, 0, 0, 0]); }")
    fell = sound(p)
    check("the generator's worklet makes the JavaScript core instead, says why, and plays",
          fell["switch"] and fell["kind"] == "js" and bool(fell["why"]) and fell["fault"] is None and fell["blocks"] > 3
          and fell["peak"] > 0.05, str(fell))
    fx = effects(p)
    check("and so does the effects worklet", fx["active"] and fx["kind"] == "js" and bool(fx["why"]) and fx["fault"] is None
          and fx["lowX"] > -0.01, str(fx))
    check("with no errors on the page", not bad, "; ".join(bad[:3]))
    p.close()

    print("\n--- the main thread's settings, read back ---")
    # Every preset applied on a page whose main thread runs the compiled core
    # and on one whose main thread runs the JavaScript core, and the settings
    # each reads back - the mirror on one, the core's own objects on the
    # other - compared as written.
    # Hashed in the page, with the length beside: written out, a preset's
    # settings carry its wavetable bank, a megabyte and more, and the first
    # version of this sent all 281 back - a third of a gigabyte - and stalled.
    SETTINGS = """() => {
      const hash = (text) => {
        let h1 = 0xdeadbeef, h2 = 0x41c6ce57;
        for (let i = 0; i < text.length; i++) {
          const c = text.charCodeAt(i);
          h1 = Math.imul(h1 ^ c, 2654435761); h2 = Math.imul(h2 ^ c, 1597334677);
        }
        h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
        h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
        return (h2 >>> 0).toString(16) + (h1 >>> 0).toString(16);
      };
      const out = [];
      for (const [, entries] of PRESETS) for (const [name] of entries) {
        applyPreset("b:" + name);
        const text = JSON.stringify([genSettings(), genSettings(1)]);
        out.push([name, hash(text) + ":" + text.length]);
      }
      return { kind: state.source.mainCoreKind, out };
    }"""
    pa, bad_a = open_page("")
    pb, bad_b = open_page("?core=js")
    wa_set, js_set = pa.evaluate(SETTINGS), pb.evaluate(SETTINGS)
    differ = [n for (n, x), (_, y) in zip(wa_set["out"], js_set["out"]) if x != y]
    moved = sum(1 for (_, x), (_, y) in zip(js_set["out"], js_set["out"][1:]) if x != y)
    check("%d presets, the settings the page reads back the same from the compiled core's mirror as from the JavaScript core"
          % len(js_set["out"]), wa_set["kind"] == "wasm" and js_set["kind"] == "js" and len(wa_set["out"]) == len(js_set["out"])
          and not differ, ", ".join(differ[:4]))
    check("and they can show it: %d presets leave the settings other than the one before" % moved, moved >= 200)
    # And the rack's generator lane, which makes its core the same way.
    LANE = """async () => {
      el.rackSynth.checked = true; await setRackSynth(true);
      await new Promise((r) => setTimeout(r, 600));
      const lane = genLane();
      genSet("freq", 331);
      return { source: state.source.kind, kind: lane && lane.mainCoreKind, freq: lane && lane.core.tone.freq };
    }"""
    la, lb = pa.evaluate(LANE), pb.evaluate(LANE)
    check("the rack's generator lane runs the compiled core, and keeps its settings where the page reads them",
          la["source"] == "rack" and la["kind"] == "wasm" and la["freq"] == 331, str(la))
    check("and the JavaScript one with ?core=js", lb["source"] == "rack" and lb["kind"] == "js" and lb["freq"] == 331, str(lb))
    check("with no errors on either page", not bad_a and not bad_b, "; ".join((bad_a + bad_b)[:3]))
    pa.close(); pb.close()

    print("\n--- a main thread that will not compile the module ---")
    # The page's own WebAssembly refused before it loads; the worklets have a
    # global scope of their own, and theirs is untouched.
    p, bad = open_page("", "WebAssembly.Module = function () { throw new Error('refused for the test'); };")
    early = p.evaluate("""() => { const f = capture(); let peak = 0; for (const v of f.channels[0]) peak = Math.max(peak, Math.abs(v));
                                  return { main: state.source.mainCoreKind, why: state.source.mainCoreWhy, peak,
                                           picture: pictureCoreKind, pictureWhy: pictureCoreWhy,
                                           setup: setupCoreKind, setupWhy: setupCoreWhy }; }""")
    check("the main thread makes the JavaScript core instead, says why, and draws", early["main"] == "js"
          and "refused for the test" in (early["why"] or "") and early["peak"] > 0.05, str(early))
    check("and the picture's sources are the JavaScript ones, saying why", early["picture"] == "js"
          and "refused for the test" in (early["pictureWhy"] or ""), "%r %r" % (early["picture"], early["pictureWhy"]))
    check("and so are the setup codes", early["setup"] == "js" and "refused for the test" in (early["setupWhy"] or ""),
          "%r %r" % (early["setup"], early["setupWhy"]))
    later = sound(p)
    check("and the worklet, which can, still runs the compiled core", later["kind"] == "wasm" and later["blocks"] > 3, str(later))
    check("with no errors on the page", not bad, "; ".join(bad[:3]))
    p.close()
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all wasm checks pass")
