"""G1's pulse: a square whose width is a control, and a destination.

What would go wrong, and what is checked for it:

- a pulse that is some other wave. A pulse of width w has its n-th harmonic
  in proportion to |sin(pi n w)| / n, so a quarter has no fourth, eighth or
  twelfth and a third has no third or sixth; the harmonics are held to that
  formula, computed here, with numpy's FFT. A square passes none of it at a
  quarter - it has no second, where this has one at -3 dB;
- a pulse of a half that is not the square, band-limiting included - the
  menu would then have two squares that sound a hair apart;
- a direct current, or a clip. Its middle is taken out and the larger of its
  two excursions is 0.9, at every width from 5 to 95 per cent;
- aliasing: the square's correction at both edges, measured in aliastest.py
  beside the square's own;
- a width the generator never reads, a layer B that plays A's, a source
  that cannot reach it, hard sync that corrects its reset wrongly, a setup
  code that loses it, a panel that shows the row for the wrong shape.

The spectra are on windows a whole number of hertz wide, as in morphtest.py.
"""
# On ?brain=js (5m): this suite reads the page's own brain - midiControl and
# genSet called directly - which core/tests/parity.py holds the instrument to,
# sample for sample. The instrument, the site's default since 5m, is
# braintest.py's and hosttest.py's.
import math, os, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

RATE = 44100
BH = [0.35875, 0.48829, 0.14128, 0.01168]

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


def spectrum(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    i = np.arange(n)
    w = (BH[0] - BH[1] * np.cos(2 * np.pi * i / n)
         + BH[2] * np.cos(4 * np.pi * i / n) - BH[3] * np.cos(6 * np.pi * i / n))
    spec = np.abs(np.fft.rfft(x * w))
    return spec, np.arange(len(spec)) * RATE / n


def level_at(spec, hz, f):
    return spec[np.abs(hz - f) < 4 * RATE / (2 * (len(spec) - 1))].max()


def db(a, b):
    return 20 * math.log10(max(float(a), 1e-15) / max(float(b), 1e-15))


def harmonics(x, f0, count):
    """Each harmonic against the fundamental, in dB."""
    spec, hz = spectrum(x)
    ref = level_at(spec, hz, f0)
    return [db(level_at(spec, hz, n * f0), ref) for n in range(1, count + 1)]


def formula(w, count):
    ref = abs(math.sin(math.pi * w))
    return [db(abs(math.sin(math.pi * n * w)) / n, ref) for n in range(1, count + 1)]


def duty(x):
    """How much of the time the wave is above nought: its width, for a pulse
    with its middle taken out."""
    x = np.asarray(x)
    return float((x > 0).mean())


# A core off the page, with a routing when asked: `held` is the routing's
# value, `slot` the destination's accumulator slot by name.
CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('mode', 'wave'); core.set('amp', 0.9); core.set('interval', 0); core.set('phase', 0);
  for (const k in setup.tone) core.set(k, setup.tone[k]);
  for (const k in setup.toneB || {}) core.set(k, setup.toneB[k], 1);
  if (setup.voices) { core.set('voices', setup.voices); core.set('voices', setup.voices, 1); }
  if (setup.route) core.setRoutes([{ held: setup.route.held, amount: 1,
                                     slot: { width: WIDTH_SLOT, sync: SYNC_SLOT }[setup.route.to] }]);
  const n = setup.n, L = new Float32Array(n), R = new Float32Array(n);
  const BL = new Float32Array(n), BR = new Float32Array(n);
  core.block(L, R, n, null, null, BL, BR);
  const from = setup.skip || 0;
  return { L: Array.from(L.subarray(from)), BL: Array.from(BL.subarray(from)) };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html?brain=js"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)
    run = lambda setup: p.evaluate(CORE, dict({"n": 44100}, **setup))

    print("\n--- the wave ---")
    wave = p.evaluate("""() => {
      // At 2 kHz, so the correction is doing something at every edge.
      const step = 2000 / 44100;
      let half = 0;
      for (let i = 0; i < 4410; i++) {
        const ph = (2 * Math.PI * i * step) % (2 * Math.PI);
        half = Math.max(half, Math.abs(waveAt('pulse', ph, step, null, 0.5) - waveAt('square', ph, step)));
      }
      // Its middle and its peak, uncorrected, over a whole cycle finely.
      const shape = [0.05, 0.1, 0.25, 0.5, 0.75, 0.95].map((w) => {
        let sum = 0, peak = 0;
        const N = 20000;
        for (let i = 0; i < N; i++) {
          const v = waveAt('pulse', 2 * Math.PI * (i + 0.5) / N, 0, null, w);
          sum += v; peak = Math.max(peak, Math.abs(v));
        }
        return [w, sum / N, peak];
      });
      // Past the ends, the ends.
      const ends = [[0.01, 0.05], [0.99, 0.95]].map(([past, end]) =>
        [0.3, 1.1, 2.9, 4.4, 6.0].every((ph) => waveAt('pulse', ph, 0.01, null, past) === waveAt('pulse', ph, 0.01, null, end)));
      return { half, shape, ends };
    }""")
    check("at a half the pulse is the square, sample for sample, band-limiting included",
          wave["half"] == 0, "worst %.2e" % wave["half"])
    print("    width, mean, peak: %s" % [[w, round(m, 6), round(k, 6)] for w, m, k in wave["shape"]])
    check("at every width from 5 to 95 per cent its middle is nought and its larger excursion 0.9",
          all(abs(m) < 1e-3 and abs(k - 0.9) < 1e-12 for _, m, k in wave["shape"]),
          str(wave["shape"]))
    check("and a width past either end is that end", wave["ends"] == [True, True], str(wave["ends"]))

    # The harmonics, at 220 Hz where the correction leaves the first dozen
    # alone, against |sin(pi n w)| / n computed here.
    print("\n--- the harmonics are a pulse's ---")
    got = {}
    for w in (0.25, 1 / 3, 0.1):
        x = run({"tone": {"shape": "pulse", "width": w, "freq": 220}, "n": 44100 + 4410, "skip": 4410})["L"]
        got[w] = harmonics(x, 220, 12)
    for w, h in got.items():
        print("    width %.3f: %s" % (w, [round(v, 1) for v in h]))
    def matches(w):
        want = formula(w, 12)
        present = [abs(g - f) for g, f in zip(got[w], want) if f > -60]
        absent = [g for g, f in zip(got[w], want) if f <= -60]
        return max(present) < 0.3 and (not absent or max(absent) < -60), max(present), absent
    q, off_q, gone_q = matches(0.25)
    check("a quarter: every harmonic |sin(pi n / 4)| / n to 0.3 dB, and no fourth, eighth or twelfth",
          q and len(gone_q) == 3, "worst %.2f dB off; absent at %s dB" % (off_q, [round(v) for v in gone_q]))
    t, off_t, gone_t = matches(1 / 3)
    check("a third: the same, with no third, sixth, ninth or twelfth",
          t and len(gone_t) == 4, "worst %.2f dB off; absent at %s dB" % (off_t, [round(v) for v in gone_t]))
    n10, off_n, _ = matches(0.1)
    check("a tenth: the first dozen falling as a narrow pulse's do", n10, "worst %.2f dB off" % off_n)

    print("\n--- the generator reads the width, and a source moves it ---")
    widths = {w: round(duty(run({"tone": {"shape": "pulse", "width": w, "freq": 220}})["L"]), 3)
              for w in (0.25, 0.7)}
    # A core built with no width said - as the worklet and these checks build
    # one - starts where the panel does. The page always sends one, so only
    # a core built bare shows its own starting value.
    bare = duty(run({"tone": {"shape": "pulse", "freq": 220}})["L"])
    check("a core built with no width plays a quarter, as the panel starts", abs(bare - 0.25) < 0.01, "%.3f" % bare)
    pushed = run({"tone": {"shape": "pulse", "width": 0.25, "freq": 220}, "route": {"to": "width", "held": 1}})["L"]
    pulled = run({"tone": {"shape": "pulse", "width": 0.5, "freq": 220}, "route": {"to": "width", "held": -1}})["L"]
    past = run({"tone": {"shape": "pulse", "width": 0.8, "freq": 220}, "route": {"to": "width", "held": 1}})["L"]
    print("    duty at 0.25 and 0.7: %s; a quarter pushed full %.3f, a half pulled full %.3f, 0.8 pushed %.3f"
          % (widths, duty(pushed), duty(pulled), duty(past)))
    check("the output is high for the width set: a quarter and seven tenths of the time",
          abs(widths[0.25] - 0.25) < 0.01 and abs(widths[0.7] - 0.7) < 0.01, str(widths))
    check("a source at full pushes a quarter to seven tenths, pulls a half to 5 per cent, and stops at 95",
          abs(duty(pushed) - 0.70) < 0.01 and abs(duty(pulled) - 0.05) < 0.01 and abs(duty(past) - 0.95) < 0.01,
          "%.3f, %.3f, %.3f" % (duty(pushed), duty(pulled), duty(past)))

    # Ratio one, switched on by a routing of nought: the reset and the
    # slave's own wrap are the same event, so the result must be the plain
    # band-limited wave, one sample late - as voicefxtest.py holds the square
    # to. It needs the pulse's jump at the wrap, which is not the square's.
    plain = np.array(run({"tone": {"shape": "pulse", "width": 0.3, "freq": 1234.5}, "n": 4410})["L"])
    synced = np.array(run({"tone": {"shape": "pulse", "width": 0.3, "freq": 1234.5}, "n": 4410,
                           "route": {"to": "sync", "held": 0}})["L"])
    late = float(np.abs(synced[1:] - plain[:-1]).max())
    check("hard sync at ratio one is the plain pulse one sample late - its reset corrected by its own jump",
          late < 1e-5, "%.1e" % late)

    print("\n--- each layer its own width ---")
    heard = run({"tone": {"shape": "pulse", "width": 0.25}, "toneB": {"shape": "pulse", "width": 0.5},
                 "voices": [{"note": 57, "freq": 220, "velocity": 1, "role": "xy"}], "n": 52292, "skip": 8192})
    second_a = harmonics(heard["L"], 220, 2)[1]
    second_b = harmonics(heard["BL"], 220, 2)[1]
    check("A at a quarter has its second harmonic at -3.0 dB, B at a half none: B plays its own",
          abs(second_a - db(0.5, math.sin(math.pi / 4))) < 0.3 and second_b < -60,
          "A %.1f dB, B %.1f dB" % (second_a, second_b))

    print("\n--- on the panel, and patched ---")
    panel = p.evaluate("""async () => {
      setView('bench'); setBenchTab('play');
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      const rows = {};
      for (const shape of ['square', 'morph', 'pulse']) {
        el.shape.value = shape; el.shape.dispatchEvent(new Event('change'));
        rows[shape] = [!el.widthRow.hidden, !el.morphRow.hidden];
      }
      const shown = { reading: el.widthValue.textContent, at: genSettings().width };
      const clipped = [];
      for (const v of [5, 25, 50, 95]) {
        el.width.value = String(v); el.width.dispatchEvent(new Event('input'));
        const r = el.widthValue.getBoundingClientRect(), row = el.widthRow.getBoundingClientRect();
        if (r.right > row.right + 0.5) clipped.push(el.widthValue.textContent);
      }
      const set = { reading: el.widthValue.textContent, at: genSettings().width };
      el.genMode.value = 'figure'; el.genMode.dispatchEvent(new Event('change'));
      const figure = !el.widthRow.hidden;
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      return { rows, shown, set, clipped, figure };
    }""")
    print("    %s" % panel)
    check("the Width row is on Play only with Pulse chosen - not the square, not the morph, not a figure",
          panel["rows"] == {"square": [False, False], "morph": [False, True], "pulse": [True, False]}
          and panel["figure"] is False, str(panel["rows"]))
    check("it starts at a quarter, says so, and the slider writes the generator",
          panel["shown"] == {"reading": "25%", "at": 0.25} and panel["set"] == {"reading": "95%", "at": 0.95}
          and panel["clipped"] == [], str(panel))

    patched = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.freq.value = '220'; el.freq.dispatchEvent(new Event('input'));
      el.width.value = '25'; el.width.dispatchEvent(new Event('input'));
      midiControl(22, 0);
      addRouting('cc.22', 'gen.width');
      const routing = state.modRoutings.find((r) => r.sourceId === 'cc.22');
      routing.amount = 1; touchRoutings();
      await wait(900);
      const down = Array.from(state.source.getLatestWindow(8820)[0]);
      midiControl(22, 127); await wait(900);
      const up = Array.from(state.source.getLatestWindow(8820)[0]);
      const dest = MOD_DESTS.get('gen.width');
      const out = { down, up, at: genSettings().width,
                    reach: [dest.reach(25, 1), dest.reach(50, 1), dest.reach(50, -1), dest.reach(90, 1)] };
      midiControl(22, 0);
      state.modRoutings = []; touchRoutings();
      return out;
    }""")
    print("    duty with the controller down %.3f, up %.3f; reach %s"
          % (duty(patched["down"]), duty(patched["up"]), patched["reach"]))
    check("a controller on Width moves the sound, a quarter to seven tenths, without writing the slider",
          abs(duty(patched["down"]) - 0.25) < 0.02 and abs(duty(patched["up"]) - 0.70) < 0.02
          and patched["at"] == 0.25, "%.3f, %.3f, slider %s" % (duty(patched["down"]), duty(patched["up"]), patched["at"]))
    check("full depth is 45 per cent, stopped at 5 and 95",
          patched["reach"] == [70, 95, 5, 95], str(patched["reach"]))

    layers = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.width.value = '30'; el.width.dispatchEvent(new Event('input'));
      setScreenKeys(true); setMidiMode('poly');
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(30);
      el.midiEditB.click(); await wait(30);
      el.shape.value = 'pulse'; el.shape.dispatchEvent(new Event('change'));
      el.width.value = '60'; el.width.dispatchEvent(new Event('input'));
      const whileB = { a: genSettings(0).width, b: genSettings(1).width, reading: el.widthValue.textContent,
                       row: !el.widthRow.hidden };
      el.midiEditA.click(); await wait(30);
      const code = snapshot();
      const backA = { slider: el.width.value, reading: el.widthValue.textContent,
                      width: code.width, bWidth: code.bWidth };
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change'));
      setMidiMode('dyad'); setScreenKeys(false);
      return { whileB, backA };
    }""")
    print("    %s" % layers)
    check("editing B writes B's width and leaves A's",
          layers["whileB"] == {"a": 0.3, "b": 0.6, "reading": "60%", "row": True}, str(layers["whileB"]))
    check("and back on A the slider is A's, with the code carrying both",
          layers["backA"] == {"slider": "30", "reading": "30%", "width": 30, "bWidth": 60}, str(layers["backA"]))

    print("\n--- setup codes ---")
    codes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const read = () => ({ a: genSettings(0).width, b: genSettings(1).width, slider: el.width.value });
      restore({ shape: 'pulse', width: 40 }); await wait(30);
      const one = read();
      restore({ shape: 'pulse', width: 40, bWidth: 70 }); await wait(30);
      const both = read();
      restore({ shape: 'pulse', width: 400, morph: 400 }); await wait(30);
      const far = Object.assign(read(), { morphB: genSettings(1).morph });
      // After a code that set one, so a restore that ignored the field would
      // not pass by standing still on the default.
      restore({ shape: 'pulse', width: 40 }); await wait(30);
      restore({ shape: 'sine' }); await wait(30);
      const old = read();
      return { one, both, far, old };
    }""")
    print("    %s" % codes)
    check("a code's width reaches the slider and the generator, and B takes A's when it has none",
          codes["one"] == {"a": 0.4, "b": 0.4, "slider": "40"}, str(codes["one"]))
    check("and B its own when it has one", codes["both"]["a"] == 0.4 and codes["both"]["b"] == 0.7, str(codes["both"]))
    # On both layers, and for every slider B takes from the code: B's went
    # straight to the generator, and a width of 400 left B at a width of
    # four while A was held to 95 - the check first looked at A alone.
    check("a width past the end loads as the end on both layers, and so does any of B's sliders",
          codes["far"] == {"a": 0.95, "b": 0.95, "slider": "95", "morphB": 3}, str(codes["far"]))
    check("a code from before the pulse loads with a quarter",
          codes["old"] == {"a": 0.25, "b": 0.25, "slider": "25"}, str(codes["old"]))

    built = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.width.value = '65'; el.width.dispatchEvent(new Event('input'));
      el.rackSynth.checked = true; await setRackSynth(true); await wait(100);
      const lane = genSettings().width;
      el.rackSynth.checked = false; await setRackSynth(false);
      toTone(); await wait(100);
      return { lane, tone: genSettings().width, b: genSettings(1).width };
    }""")
    check("a generator built later - a rack's lane, a new tone - takes the slider's width",
          built == {"lane": 0.65, "tone": 0.65, "b": 0.65}, str(built))

    def search(q):
        p.evaluate("(q) => { el.benchSearch.value = q; el.benchSearch.dispatchEvent(new Event('input')); }", q)
        return p.evaluate("""() => Array.from(el.benchResults.querySelectorAll('button'))
          .map((b) => [b.firstChild.textContent, b.querySelector('.crumb').textContent])""")
    p.evaluate("() => { el.shape.value = 'pulse'; el.shape.dispatchEvent(new Event('change')); }")
    pwm = search("pwm")
    check("pwm finds it", ["Width", "Generator"] in pwm, str(pwm[:4]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the pulse is a pulse at every width, and its width is patchable")
