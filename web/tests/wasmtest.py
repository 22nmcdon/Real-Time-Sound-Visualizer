"""The generator in WebAssembly (stage 5a): the compiled core behind ?core=wasm.

The page carries the C++ core's generator, compiled, as base64 between two
marker comments, and with `?core=wasm` in the address its worklet runs that in
place of `makeGeneratorCore`. `core/tests/parity.py` holds the module to the
JavaScript generator through the parity harness's own runs. This holds it in
the browser, through what the page itself sends:

THE PAGE'S COPY IS THIS CORE. The module is generated, not written, and has to
be built again whenever the core changes; `core/wasm/build.py --check` builds
it and compares. That needs clang's wasm32 target and the WASI libc, which not
everyone running the web suite has, so without them the check says SKIP, by
name, rather than passing.

THE WORKLET RUNS IT. The worklet says which core it made, and the page
records what it said: `wasm` with the switch and `js` without it, which is
the null - the reading comes from the audio thread, not from the address.

EVERY PRESET IS THE SAME SOUND. Each generator preset applied as a player
would, and its settings, routes and oscillators given to both cores the way
the worklet gives them - through JSON at construction, as processorOptions
are, and then again as live objects, as a message brings them - and run for
a quarter of a second each: the samples and everything the worklet reads
back, compared value for value.
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
  const play = (wasm, tone, toneB, routes, seed) => {
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
        c.block(bufs[0], bufs[1], N, bufs[2], bufs[3], bufs[4], bufs[5]);
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
  const rows = [];
  for (const [, entries, kind] of PRESETS) {
    if (kind !== "generator") continue;
    for (const [name] of entries) {
      applyPreset("b:" + name);
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
      rows.push({ name, worst: far(js, wa), peak, routes: routes.length, length: js.length, wrong });
    }
  }
  return rows;
}"""


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    def open_page(query):
        p = b.new_page(viewport={"width": 1400, "height": 900})
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
          return { kind: state.source.coreKind, switch: CORE_IN_WASM, blocks: state.source.blocks,
                   fault: state.source.fault, peak, driver: lfoDriver(), phase: lfos[0].phase };
        }""")

    print("\n--- the worklet runs it ---")
    p, bad = open_page("?core=wasm")
    on = sound(p)
    check("with ?core=wasm the worklet says it is running the compiled core", on["switch"] and on["kind"] == "wasm", str(on))
    check("and it plays, and the picture is drawn from what it sends",
          on["fault"] is None and on["blocks"] > 3 and on["peak"] > 0.05 and on["driver"] == "worklet",
          "%d blocks, peak %.3f, fault %r" % (on["blocks"], on["peak"], on["fault"]))
    p.wait_for_timeout(300)
    later = p.evaluate("() => ({ phase: lfos[0].phase, blocks: state.source.blocks })")
    check("and the oscillators' phases come back from it", later["phase"] != on["phase"] and later["blocks"] > on["blocks"],
          "%r then %r" % (on["phase"], later["phase"]))
    check("with no errors on the page", not bad, "; ".join(bad[:3]))

    print("\n--- every generator preset, both cores ---")
    rows = p.evaluate(PRESET_RUN)
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
    p.close()

    p, bad = open_page("")
    off = sound(p)
    check("and without the switch the worklet says it is the JavaScript one", not off["switch"] and off["kind"] == "js"
          and off["blocks"] > 3, str(off))
    check("with no errors on the page", not bad, "; ".join(bad[:3]))
    p.close()
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all wasm checks pass")
