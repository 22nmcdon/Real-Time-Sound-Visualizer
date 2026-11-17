"""What playing costs the audio thread and the frame (the outside review, 17 Nov).

What would go wrong, and what is checked for it:

- the instrument's worklet allocating on every block: fresh views into the
  core's memory each 128 frames, a new lane per chunk, a readings object of
  some thirty objects and a fresh grid every 512 frames - about 1.1 MB a
  second, and a collection a second, on the thread where a stop longer than
  a block is a click. Measured by workletalloc.mjs, which runs the page's own
  module in Node with a chord held and counts what the heap grew by between
  collections. The null is the same run with the page never sending the
  lanes back, which must cost more, so the figure is one the harness can see
  move;
- the core compiled twice, once here and again on the audio thread from a
  copy of its bytes: the node is made with the module this page compiled,
  read off the options the page hands to AudioWorkletNode. And the
  instrument then plays, with its chunks coming back and their buffers going
  back to it, so a module the worklet could not use is not taken for one it
  did;
- the speakers' chain retuned every frame: thirteen setTargetAtTime calls a
  frame whether or not anything had moved. Counted over a second of
  nothing changing; the null is a cutoff moved, which must schedule.

Serial: it measures over real seconds and counts calls a second.
"""
import base64, json, os, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
# Measured 17 Nov, ten seconds with a chord held. Before the review's fix:
# 1.22 MB a second on the heap, 1.92 MB a second of typed arrays' own bytes
# (a grid and two lanes a chunk) and 3,563 views a second, 1.2 collections a
# second. After: 0.35 MB a second on the heap (the harness alone is 0.07),
# no typed array's bytes, 188 views a second (the lanes handed back, two a
# chunk), 0.4 collections a second. Each line is between, with room both ways.
CEILING = 600_000
ARRAY_CEILING = 50_000
VIEW_CEILING = 500

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + str(detail)) if detail else ""))
    if not ok: fails.append(name)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    # What the page hands the worklet, read as it is handed.
    p.add_init_script("""(() => {
      const Real = window.AudioWorkletNode;
      window.__workletOptions = [];
      window.AudioWorkletNode = class extends Real {
        constructor(ctx, name, options) {
          const o = options && options.processorOptions;
          window.__workletOptions.push({ name, module: !!(o && o.wasm instanceof WebAssembly.Module),
                                         bytes: !!(o && o.wasm instanceof ArrayBuffer) });
          super(ctx, name, options);
        }
      };
    })();""")
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    ev = p.evaluate
    text, core, code = ev("() => generatorModuleSource()"), ev("() => WASM_CORE"), ev("() => encodeSetup(snapshot())")

    print("\n--- what the worklet allocates, in Node ---")
    tmp = tempfile.mkdtemp()
    open(os.path.join(tmp, "module.js"), "w").write(text)
    open(os.path.join(tmp, "core.wasm"), "wb").write(base64.b64decode(core))
    def measure(env=None):
        r = subprocess.run(["node", os.path.join(HERE, "workletalloc.mjs"), os.path.join(tmp, "module.js"),
                            os.path.join(tmp, "core.wasm"), code, "10"],
                           capture_output=True, text=True, env=dict(os.environ, **(env or {})), timeout=300)
        try: return json.loads(r.stdout.strip().splitlines()[-1])
        except Exception: return {"error": (r.stdout + r.stderr)[-500:]}
    got = measure()
    check("the instrument played: chunks posted, no error", got.get("chunks", 0) > 900 and not got.get("errors"), got)
    check("under %d KB a second allocated on the audio thread with a chord held" % (CEILING // 1000),
          got.get("bytesPerSecond", 1e9) < CEILING,
          "%s bytes a second, %s collections a second" % (got.get("bytesPerSecond"), got.get("collectionsPerSecond")))
    check("no typed array's bytes made while it plays", got.get("arrayBytesPerSecond", 1e9) < ARRAY_CEILING,
          "%s bytes a second" % got.get("arrayBytesPerSecond"))
    check("and under %d views a second onto memory that exists" % VIEW_CEILING, got.get("viewsPerSecond", 1e9) < VIEW_CEILING,
          "%s a second" % got.get("viewsPerSecond"))
    null = measure({"NO_RECYCLE": "1"})
    check("null: with the lanes never sent back, new lanes are made, over the line",
          null.get("arrayBytesPerSecond", 0) > ARRAY_CEILING, "%s bytes a second" % null.get("arrayBytesPerSecond"))

    print("\n--- the module compiled once ---")
    p.keyboard.press("m"); p.keyboard.down("a"); p.wait_for_timeout(1200)
    made = ev("() => window.__workletOptions")
    brain = [m for m in made if m["name"] == "scope-brain"]
    check("the instrument's node is made with the module this page compiled, not a copy of its bytes",
          brain and brain[-1]["module"] and not brain[-1]["bytes"], made)
    c0 = ev("() => state.source.chunks"); p.wait_for_timeout(600); c1 = ev("() => state.source.chunks")
    check("and the instrument plays from it, its chunks coming back", c1 > c0 > 0, "%s then %s" % (c0, c1))
    p.keyboard.up("a"); p.keyboard.press("m")

    print("\n--- the speakers' chain, frame by frame ---")
    count = """async (ms) => {
      const real = AudioParam.prototype.setTargetAtTime;
      let n = 0;
      AudioParam.prototype.setTargetAtTime = function (...a) { n++; return real.apply(this, a); };
      await new Promise((r) => setTimeout(r, ms));
      AudioParam.prototype.setTargetAtTime = real;
      return { calls: n, chains: monitorChains.size };
    }"""
    p.wait_for_timeout(500)
    idle = ev(count, 1000)
    check("a monitor chain is there (the case under test)", idle["chains"] > 0, idle)
    check("a second with nothing moving schedules nothing on it", idle["calls"] <= 2, "%d calls" % idle["calls"])
    moving = ev("""async () => {
      const real = AudioParam.prototype.setTargetAtTime;
      let n = 0;
      AudioParam.prototype.setTargetAtTime = function (...a) { n++; return real.apply(this, a); };
      state.filter.on = true; state.monitorAt = 'post';
      for (let k = 0; k < 10; k++) { state.filter.hz = 400 + 100 * k; await new Promise((r) => requestAnimationFrame(r)); }
      AudioParam.prototype.setTargetAtTime = real;
      return n;
    }""") if ev("() => state.filter && 'hz' in state.filter") else None
    if moving is None:
        moving = ev("""async () => {
          const real = AudioParam.prototype.setTargetAtTime;
          let n = 0;
          AudioParam.prototype.setTargetAtTime = function (...a) { n++; return real.apply(this, a); };
          state.monitorAt = 'post';
          for (let k = 0; k < 10; k++) { el.rotate.value = String(10 * k); el.rotate.dispatchEvent(new Event('input', { bubbles: true }));
                                         await new Promise((r) => requestAnimationFrame(r)); }
          AudioParam.prototype.setTargetAtTime = real;
          return n;
        }""")
    check("null: a control that moves the chain schedules as it moves", moving >= 10, "%d calls over ten frames" % moving)
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\nall passed" if not fails else "\n%d FAILED:\n  %s" % (len(fails), "\n  ".join(fails)))
sys.exit(1 if fails else 0)
