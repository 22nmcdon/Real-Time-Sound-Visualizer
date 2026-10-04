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
          return { source: state.source.kind, active: state.source.fx.active, kind: state.source.fx.coreKind,
                   why: state.source.fx.coreWhy, fault: state.source.fx.fault,
                   lowX: Math.min(...w[0]), lowY: Math.min(...w[1]) };
        }""")

    print("\n--- the worklets run it, by default ---")
    p, bad = open_page("")
    on = sound(p)
    check("the generator's worklet says it is running the compiled core", on["switch"] and on["kind"] == "wasm" and on["why"] is None, str(on))
    check("and so does the main thread's generator, which draws while the sound is off", on["main"] == "wasm" and on["mainWhy"] is None,
          "%r %r" % (on["main"], on["mainWhy"]))
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

    print("\n--- the effects worklet, by default ---")
    fx = effects(p)
    # The mirror on both axes folds each channel to its positive half, so
    # neither lane goes below nought if the effect is in the path.
    check("the effects worklet on a microphone says it is running the compiled core, and mirrors the input",
          fx["source"] == "mic" and fx["active"] and fx["kind"] == "wasm" and fx["why"] is None and fx["fault"] is None
          and fx["lowX"] > -0.01 and fx["lowY"] > -0.01, str(fx))
    check("with no errors on the page", not bad, "; ".join(bad[:3]))
    p.close()

    print("\n--- ?core=js, the JavaScript core ---")
    p, bad = open_page("?core=js")
    js = sound(p)
    check("with ?core=js the generator's worklet says it is the JavaScript one", not js["switch"] and js["kind"] == "js"
          and js["why"] is None and js["blocks"] > 3, str(js))
    check("and so does the main thread's", js["main"] == "js" and js["mainWhy"] is None, "%r %r" % (js["main"], js["mainWhy"]))
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
                                  return { main: state.source.mainCoreKind, why: state.source.mainCoreWhy, peak }; }""")
    check("the main thread makes the JavaScript core instead, says why, and draws", early["main"] == "js"
          and "refused for the test" in (early["why"] or "") and early["peak"] > 0.05, str(early))
    later = sound(p)
    check("and the worklet, which can, still runs the compiled core", later["kind"] == "wasm" and later["blocks"] > 3, str(later))
    check("with no errors on the page", not bad, "; ".join(bad[:3]))
    p.close()
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all wasm checks pass")
