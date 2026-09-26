"""Live audio into the generator (Stage J3).

Against the way each would fail:

- an input that leaks in when the mode is off, or at a depth of nought;
- FM that is not a factor on the rate: a steady input of a quarter at full
  depth must draw exactly what twice the rate draws, and a deep enough
  negative input must stop the trace rather than run it backwards;
- a ride that shifts the figure instead of scaling it: every sample is the
  plain one times (1 + 2 depth x), to float precision;
- a clock that does not lock: fed 100 Hz, a figure at 40 Hz must repeat every
  441 samples exactly, and a waveform at 330 must too; and when the input
  stops, the generator must run free at its own pitch again, not stall;
- a worklet that ignores its input;
- on the page: an input opened when it cannot reach the generator, or left
  open when it is no longer wanted.
"""
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

# A core off the page, one step at a time, each with its own input.
CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('amp', 0.4); core.set('shape', 'sine'); core.set('interval', 0);
  const out = { L: [], R: [], X: [] };
  let t = 0;
  for (const step of setup.steps) {
    for (const k in step.tone || {}) core.set(k, step.tone[k]);
    const n = step.n, L = new Float32Array(n), R = new Float32Array(n);
    let x = null;
    if (step.input) {
      x = new Float32Array(n);
      for (let i = 0; i < n; i++) {
        const s = (t + i) / 44100, v = step.input;
        x[i] = v.hz ? v.amp * Math.sin(2 * Math.PI * v.hz * s) : v.value;
      }
    }
    core.setInput(x);
    core.block(L, R, n);
    for (let i = 0; i < n; i++) { out.L.push(L[i]); out.R.push(R[i]); out.X.push(x ? x[i] : 0); }
    t += n;
  }
  return out;
}"""

STUB = """
  window.__wait = (ms) => new Promise((r) => setTimeout(r, ms));
  // Streams open, not keys: the cache files one stream under the empty key
  // and under the name the browser gives the device, so its size is two for
  // one stream once it has been opened.
  window.__open = () => new Set(liveStreams.values()).size;
  // The live device: a 4 Hz sine at a half, so a ride at full depth swings
  // the generator's size between nought and twice.
  window.__device = () => {
    const ctx = new AudioContext();
    const dest = ctx.createMediaStreamDestination(), a = ctx.createOscillator(), g = ctx.createGain();
    a.frequency.value = 4; g.gain.value = 0.5; a.connect(g); g.connect(dest); a.start();
    navigator.mediaDevices.getUserMedia = () => Promise.resolve(dest.stream);
  };
"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.add_init_script(STUB)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    run = lambda steps: p.evaluate(CORE, {"steps": steps})
    most = lambda a, c: max(abs(x - y) for x, y in zip(a, c))
    N = 8820
    wave = {"mode": "wave", "freq": 220}
    fig = {"mode": "figure", "figure": "Star", "figureRate": 40, "detail": 5}
    sine7 = {"hz": 7, "amp": 0.5}

    print("\n--- off is off ---")
    plain = run([{"tone": wave, "n": N}])
    off = run([{"tone": dict(wave, inputMode=0), "n": N, "input": sine7}])
    nought = run([{"tone": dict(wave, inputMode=2, inputDepth=0), "n": N, "input": sine7}])
    check("with the mode off, or a ride at a depth of nought, the input changes nothing at all",
          most(plain["L"], off["L"]) == 0 and most(plain["L"], nought["L"]) == 0,
          "%.2e, %.2e" % (most(plain["L"], off["L"]), most(plain["L"], nought["L"])))

    print("\n--- ride ---")
    ride = run([{"tone": dict(wave, inputMode=2, inputDepth=0.5), "n": N, "input": sine7}])
    want = [pl * (1 + 2 * 0.5 * x) for pl, x in zip(plain["L"], ride["X"])]
    gap = most(ride["L"], want)
    print("    against the plain wave times (1 + 2 depth x): %.2e; against the plain wave: %.3f"
          % (gap, most(ride["L"], plain["L"])))
    check("a ride scales every sample by (1 + 2 depth x): the sound rides on the outline",
          gap < 1e-6 and most(ride["L"], plain["L"]) > 0.1, "%.2e" % gap)

    print("\n--- FM ---")
    fast = run([{"tone": dict(fig, figureRate=80), "n": N}])
    fm = run([{"tone": dict(fig, inputMode=1, inputDepth=1), "n": N, "input": {"value": 0.25}}])
    fastw = run([{"tone": dict(wave, freq=440), "n": N}])
    fmw = run([{"tone": dict(wave, inputMode=1, inputDepth=1), "n": N, "input": {"value": 0.25}}])
    print("    a steady quarter at full depth against twice the rate: figure %.2e, waveform %.2e"
          % (most(fm["L"], fast["L"]), most(fmw["L"], fastw["L"])))
    check("FM is a factor on the rate: a steady quarter at full depth draws what twice the rate draws, "
          "figure and waveform alike",
          most(fm["L"], fast["L"]) < 1e-9 and most(fmw["L"], fastw["L"]) < 1e-9
          and most(fm["L"], run([{"tone": fig, "n": N}])["L"]) > 0.1,
          "%.2e, %.2e" % (most(fm["L"], fast["L"]), most(fmw["L"], fastw["L"])))
    stop = run([{"tone": dict(fig, inputMode=1, inputDepth=1), "n": N, "input": {"value": -1}}])
    check("and a deep enough negative input stops the trace rather than running it backwards",
          max(stop["L"][100:]) - min(stop["L"][100:]) < 1e-9, "%.2e" % (max(stop["L"][100:]) - min(stop["L"][100:])))

    print("\n--- clock ---")
    hundred = {"hz": 100, "amp": 0.5}
    P = 441
    clocked = run([{"tone": dict(fig, inputMode=3), "n": N * 2, "input": hundred}])
    free = run([{"tone": fig, "n": N * 2}])
    lock = most(clocked["L"][4410:-P], clocked["L"][4410 + P:])
    loose = most(free["L"][4410:-P], free["L"][4410 + P:])
    print("    a 40 Hz star against a 100 Hz input: repeats every 441 samples to %.2e; unclocked, %.3f"
          % (lock, loose))
    check("clocked by 100 Hz, a 40 Hz figure repeats every 441 samples: the input holds it still",
          lock < 1e-6 and loose > 0.1, "%.2e against %.3f" % (lock, loose))
    cw = run([{"tone": dict(wave, freq=330, inputMode=3), "n": N * 2, "input": hundred},
              {"n": N * 2, "input": {"value": 0}}])
    wlock = most(cw["L"][4410:N * 2 - P], cw["L"][4410 + P:N * 2])
    tail = cw["L"][N * 2 + 2000:]
    ups = sum(1 for a, c in zip(tail, tail[1:]) if a <= 0 < c)
    hz = ups * 44100 / len(tail)
    print("    a 330 Hz waveform clocked by 100 Hz repeats every 441 samples to %.2e; input gone, it runs at "
          "%.1f Hz" % (wlock, hz))
    check("a waveform clocked by the input plays at the input's pitch, and runs free at its own when the input stops",
          wlock < 1e-6 and abs(hz - 330) < 5, "%.2e, %.1f Hz" % (wlock, hz))

    # The restart at each crossing, which a steady input cannot show by
    # periodicity alone - the waveform repeats every 441 samples either way.
    # What it buys is alignment: a sine clocked by the input rises through
    # nought where the input does.
    al = run([{"tone": dict(wave, shape="sine", freq=330, inputMode=3), "n": N, "input": hundred}])
    up = lambda xs: [i for i in range(4410, len(xs) - 1) if xs[i] <= 0 < xs[i + 1]]
    ins, outs = up(al["X"]), up(al["L"])
    off_by = max(min(abs(o - i) for o in outs) for i in ins) if ins and outs else 999
    check("and each of the input's upward crossings restarts the cycle: the clocked sine rises where the input does",
          off_by <= 1 and len(outs) >= len(ins), "worst %d samples, %d crossings against %d" % (off_by, len(outs), len(ins)))

    print("\n--- on the page ---")
    page = p.evaluate("""async () => {
      __device();
      const out = {};
      // Not heard: the input has nowhere to go, and is not opened.
      el.inputMode.value = '2'; el.inputMode.dispatchEvent(new Event('change'));
      await __wait(400);
      out.silent = { where: el.inputWhere.textContent, open: __open() };
      // Heard: opened, connected, and the drawn size swings with the input.
      el.inputDepth.value = '100'; el.inputDepth.dispatchEvent(new Event('input'));
      state.genSound = true; await applyGeneratorSound(); await __wait(1200);
      const peaks = [];
      for (let k = 0; k < 16; k++) {
        const w = state.source.getLatestWindow(441)[0];
        peaks.push(Math.max(...w.map(Math.abs))); await __wait(30);
      }
      out.heard = { where: el.inputWhere.textContent, open: __open(),
                    connected: state.source.inputConnected, low: Math.min(...peaks), high: Math.max(...peaks) };
      const code = snapshot();
      out.code = [code.inputMode, code.inputDepth];
      // Off: released, disconnected.
      el.inputMode.value = '0'; el.inputMode.dispatchEvent(new Event('change'));
      await __wait(300);
      out.off = { open: __open(), connected: state.source.inputConnected, where: el.inputWhere.textContent };
      state.genSound = false; await applyGeneratorSound();
      return out;
    }""")
    print("    %s" % page)
    check("not heard, it says so and opens nothing: the input would have nowhere to go",
          page["silent"]["open"] == 0 and page["silent"]["where"].startswith("Heard only"), str(page["silent"]))
    check("heard, the input is opened and connected, and the drawn size swings with it from near nought to twice",
          page["heard"]["open"] == 1 and page["heard"]["connected"] is True
          and page["heard"]["where"] == "Your input, into the generator."
          and page["heard"]["high"] > 3 * page["heard"]["low"], str(page["heard"]))
    check("and a setup code carries the mode and the depth", page["code"] == [2, 100], str(page["code"]))
    check("switched off, the input is let go of and disconnected",
          page["off"]["open"] == 0 and page["off"]["connected"] is False, str(page["off"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
