"""The morph: one position through sine, triangle, saw and square.

What would go wrong, and what is checked for it:

- a detent that is a mix rather than the shape, so "saw" on the morph is not
  a saw. Each whole number is compared with the shape itself, sample for
  sample, band-limiting included;
- a morph that steps between shapes rather than crossfading, which on a
  modulated position is a click at every station. The position is swept in
  thousandths and the largest change a thousandth makes is measured;
- the saw upside down against the other three. Its fundamental is the
  sine's inverted, so a crossfade from the triangle cancels the note half-way
  - 0.09 of the sine's, measured, against 0.72 with the saw turned round. The
  check is on the fundamental across the whole range;
- aliasing: a crossfade of band-limited shapes is band-limited, and a
  position modulated by an oscillator must not undo that;
- a source that cannot reach it, a layer B that plays A's position, a setup
  code that loses it.

The spectra are numpy's, on windows a whole number of hertz wide, for the
reasons drawbartest.py gives.
"""
import math, os, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

RATE = 44100
N = 44100
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


CORE = """([morph, freq, n, extra]) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const lfos = [still(), still()];
  if (extra && extra.lfo) Object.assign(lfos[0], extra.lfo);
  const core = makeGeneratorCore(44100, GEN_DESTS.length, lfos);
  core.set('mode', 'wave'); core.set('shape', 'morph'); core.set('morph', morph);
  core.set('freq', freq); core.set('amp', 0.9); core.set('interval', 0);
  if (extra && extra.routes) core.setRoutes(extra.routes.map((r) => Object.assign({}, r, { slot: MORPH_SLOT })));
  const L = new Float32Array(n), R = new Float32Array(n);
  core.block(L, R, n);
  return Array.from(L);
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
    core = lambda morph, freq, n=N, extra=None: p.evaluate(CORE, [morph, freq, n, extra])

    print("\n--- the stations are the shapes ---")
    stations = p.evaluate("""() => {
      // At 2 kHz, so the band-limiting is doing something at every edge and
      // a detent that skipped it would differ where it matters.
      const step = 2000 / 44100, worst = [0, 0, 0, 0];
      for (let i = 0; i < 4410; i++) {
        const ph = (2 * Math.PI * i * step) % (2 * Math.PI);
        const want = [Math.sin(ph), waveAt('triangle', ph, step),
                      waveAt('ramp', ph + Math.PI, step), waveAt('square', ph, step)];
        for (let k = 0; k < 4; k++) {
          worst[k] = Math.max(worst[k], Math.abs(waveAt('morph', ph, step, null, k) - want[k]));
        }
      }
      return worst;
    }""")
    print("    worst difference at 0, 1, 2, 3: %s" % stations)
    check("at 0, 1, 2 and 3 the morph is the sine, the triangle, the saw and the square, exactly",
          stations == [0, 0, 0, 0], str(stations))

    print("\n--- between them it is continuous ---")
    sweep = p.evaluate("""() => {
      // Every phase a cycle's worth of samples visits, and the position walked
      // in thousandths from 0 to 3: the largest change one thousandth makes.
      let worst = 0;
      for (let i = 0; i < 64; i++) {
        const ph = 2 * Math.PI * i / 64 + 0.013;
        let last = waveAt('morph', ph, 0, null, 0);
        for (let m = 1; m <= 3000; m++) {
          const now = waveAt('morph', ph, 0, null, m / 1000);
          worst = Math.max(worst, Math.abs(now - last));
          last = now;
        }
      }
      return worst;
    }""")
    check("a thousandth of a station moves no sample by more than two thousandths",
          sweep < 0.002, "%.5f" % sweep)

    print("\n--- the fundamental survives the whole way ---")
    fund = {}
    for m in [i / 4 for i in range(13)]:
        spec, hz = spectrum(core(m, 220))
        fund[m] = level_at(spec, hz, 220)
    sine = fund[0]
    rel = {m: round(v / sine, 3) for m, v in fund.items()}
    print("    fundamental against the sine's: %s" % rel)
    check("it never falls below the saw's own, 0.64 of the sine's - the lowest station",
          min(rel.values()) >= 0.63, str(min(rel.values())))
    check("and between the triangle and the saw it goes smoothly from one to the other",
          rel[1.25] > rel[1.5] > rel[1.75] and abs(rel[1.5] - (rel[1.0] + rel[2.0]) / 2) < 0.01,
          "%s, %s, %s" % (rel[1.25], rel[1.5], rel[1.75]))

    print("\n--- band-limited, moved or still ---")
    def floor(x, f0, near=None):
        spec, hz = spectrum(x)
        near = near or 4 * RATE / len(x)
        grid = np.zeros(len(spec), dtype=bool)
        grid[:6] = True
        k = 1
        while k * f0 < RATE / 2:
            grid |= np.abs(hz - k * f0) < near
            k += 1
        return db(spec[~grid & (hz < 10000)].max(), level_at(spec, hz, f0))
    still = {m: round(floor(core(m, 4000), 4000), 1) for m in (0.5, 1.5, 2.5)}
    print("    at 4 kHz, below 10 kHz: %s dB" % still)
    check("half-way between each pair, at 4 kHz, nothing folds back above -45 dB",
          all(v <= -45 for v in still.values()), str(still))
    # An oscillator on the position at 3 Hz, the whole range: what it adds is
    # sidebands at multiples of three hertz either side of each harmonic, so
    # the grid is 40 Hz wide here. What aliasing there would be from 4 kHz
    # lands 100 Hz off a harmonic - the ninth folds to 8.1 kHz, the tenth to
    # 4.1 - which a 40 Hz grid still counts against it.
    moved = floor(core(1.5, 4000, N, {"lfo": {"rate": 3, "depth": 1},
                                      "routes": [{"index": 0, "amount": 1}]}), 4000, near=40)
    check("and with an oscillator sweeping it end to end, still nothing above -45 dB",
          moved <= -45, "%.1f dB" % moved)

    print("\n--- on the panel, and patched ---")
    panel = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setView('bench'); setBenchTab('play');
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change'));
      const sine = el.morphRow.hidden;
      el.shape.value = 'morph'; el.shape.dispatchEvent(new Event('change'));
      const shown = { row: el.morphRow.hidden, reading: el.morphValue.textContent,
                      at: genSettings().morph };
      el.morph.value = '200'; el.morph.dispatchEvent(new Event('input'));
      const saw = { reading: el.morphValue.textContent, at: genSettings().morph };
      el.morph.value = '275'; el.morph.dispatchEvent(new Event('input'));
      const late = el.morphValue.textContent;
      // Every reading inside its row: the first one ran off the end of it.
      const clipped = [];
      for (const v of [0, 50, 100, 150, 200, 250, 275, 300]) {
        el.morph.value = String(v); el.morph.dispatchEvent(new Event('input'));
        const r = el.morphValue.getBoundingClientRect(), row = el.morphRow.getBoundingClientRect();
        if (r.right > row.right + 0.5 || el.morphValue.scrollWidth > el.morphValue.clientWidth + 0.5) {
          clipped.push(el.morphValue.textContent);
        }
      }
      el.genMode.value = 'figure'; el.genMode.dispatchEvent(new Event('change'));
      const figure = el.morphRow.hidden;
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      return { sine, shown, saw, late, figure, clipped };
    }""")
    print("    %s" % panel)
    check("the Morph row is on Play only with Morph chosen, and not for a figure",
          panel["sine"] and not panel["shown"]["row"] and panel["figure"], str(panel))
    check("it starts half-way from the triangle to the saw, and says where it is",
          panel["shown"]["reading"] == "tri→saw" and panel["shown"]["at"] == 1.5
          and panel["saw"] == {"reading": "saw", "at": 2} and panel["late"] == "saw→sqr",
          str(panel))
    check("and every reading fits beside the slider, in a Bench column",
          panel["clipped"] == [], str(panel["clipped"]))

    patched = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.freq.value = '220'; el.freq.dispatchEvent(new Event('input'));
      el.morph.value = '0'; el.morph.dispatchEvent(new Event('input'));
      midiControl(22, 0);
      addRouting('cc.22', 'gen.morph');
      const routing = state.modRoutings.find((r) => r.sourceId === 'cc.22');
      routing.amount = 1; touchRoutings();
      await wait(1200);
      const down = Array.from(state.source.getLatestWindow(44100)[0]);
      midiControl(22, 127); await wait(1200);
      const up = Array.from(state.source.getLatestWindow(44100)[0]);
      const dest = MOD_DESTS.get('gen.morph');
      const out = { down, up, at: genSettings().morph,
                    reach: [dest.reach(0, 1), dest.reach(150, 1), dest.reach(100, -1)] };
      midiControl(22, 0);
      state.modRoutings = []; touchRoutings();
      return out;
    }""")
    spec, hz = spectrum(patched["down"])
    second_down = db(level_at(spec, hz, 440), level_at(spec, hz, 220))
    spec, hz = spectrum(patched["up"])
    second_up = db(level_at(spec, hz, 440), level_at(spec, hz, 220))
    print("    2nd harmonic: controller down %.1f dB, up %.1f dB; reach %s"
          % (second_down, second_up, patched["reach"]))
    # From the sine, full depth is a station and a half: half-way from the
    # triangle to the saw. Only the saw has even harmonics, half of its 1/2
    # against a fundamental of (0.81 + 0.64) / 2.
    want = 20 * math.log10(0.5 * (2 / math.pi) * 0.5 / (0.5 * (8 / math.pi ** 2 + 2 / math.pi)))
    check("a controller on Morph moves the sound: a sine with none of the saw's second harmonic",
          second_down < -100, "%.1f dB" % second_down)
    check("and at full, a station and a half on, exactly the half-saw's %.1f dB" % want,
          abs(second_up - want) < 0.3, "%.2f dB" % second_up)
    check("without writing the slider's own position",
          patched["at"] == 0, str(patched["at"]))
    check("full depth is a station and a half, stopped at both ends",
          patched["reach"] == [150, 300, 0], str(patched["reach"]))

    print("\n--- each layer its own position ---")
    layers = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.morph.value = '300'; el.morph.dispatchEvent(new Event('input'));
      setScreenKeys(true); setMidiMode('poly');
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(30);
      el.midiEditB.click(); await wait(30);
      el.shape.value = 'morph'; el.shape.dispatchEvent(new Event('change'));
      el.morph.value = '0'; el.morph.dispatchEvent(new Event('input'));
      const whileB = { a: genSettings(0).morph, b: genSettings(1).morph, reading: el.morphValue.textContent,
                       row: el.morphRow.hidden };
      el.midiEditA.click(); await wait(30);
      const code = snapshot();
      const backA = { slider: el.morph.value, reading: el.morphValue.textContent,
                      morph: code.morph, bMorph: code.bMorph };
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change'));
      setMidiMode('dyad'); setScreenKeys(false);
      return { whileB, backA };
    }""")
    print("    %s" % layers)
    check("editing B writes B's position and leaves A's",
          layers["whileB"] == {"a": 3, "b": 0, "reading": "sine", "row": False}, str(layers["whileB"]))
    check("and back on A the slider is A's, with the code carrying both",
          layers["backA"] == {"slider": "300", "reading": "square", "morph": 300, "bMorph": 0},
          str(layers["backA"]))
    heard = p.evaluate("""() => {
      // A at the square, B at the sine: a third harmonic in A's picture and
      // none in B's is B's own position, not A's.
      const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
      const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
      core.set('mode', 'wave');
      core.set('shape', 'morph'); core.set('morph', 3);
      core.set('shape', 'morph', 1); core.set('morph', 0, 1); core.set('amp', 0.9, 1);
      // Velocity is a fraction here, as the keyboard hands it over; 127 drove
      // both layers into the clamp and a sine came out square.
      const v = [{ note: 57, freq: 220, velocity: 1, role: 'xy' }];
      core.set('voices', v); core.set('voices', v, 1);
      const n = 52292, L = new Float32Array(n), R = new Float32Array(n);
      const BL = new Float32Array(n), BR = new Float32Array(n);
      core.block(L, R, n, null, null, BL, BR);
      return { a: Array.from(L.subarray(8192)), b: Array.from(BL.subarray(8192)) };
    }""")
    spec, hz = spectrum(heard["a"])
    third_a = db(level_at(spec, hz, 660), level_at(spec, hz, 220))
    spec, hz = spectrum(heard["b"])
    third_b = db(level_at(spec, hz, 660), level_at(spec, hz, 220))
    check("and B sounds its own: A's square has its third harmonic at -9.5 dB, B's sine none",
          abs(third_a - 20 * math.log10(1 / 3)) < 0.3 and third_b < -100,
          "A %.1f dB, B %.1f dB" % (third_a, third_b))

    print("\n--- setup codes ---")
    codes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const read = () => ({ a: genSettings(0).morph, b: genSettings(1).morph, slider: el.morph.value });
      restore({ shape: 'morph', morph: 250 }); await wait(30);
      const one = read();
      restore({ shape: 'morph', morph: 250, bMorph: 75 }); await wait(30);
      const both = read();
      // After a code that set one, so a restore that ignored the field would
      // not pass by standing still on the default.
      restore({ shape: 'morph', morph: 250 }); await wait(30);
      restore({ shape: 'sine' }); await wait(30);
      const old = read();
      return { one, both, old };
    }""")
    print("    %s" % codes)
    check("a code's position reaches the slider and the generator, and B takes A's when it has none",
          codes["one"] == {"a": 2.5, "b": 2.5, "slider": "250"}, str(codes["one"]))
    check("and B its own when it has one", codes["both"]["a"] == 2.5 and codes["both"]["b"] == 0.75,
          str(codes["both"]))
    check("a code from before the morph loads with the default",
          codes["old"] == {"a": 1.5, "b": 1.5, "slider": "150"}, str(codes["old"]))

    built = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.morph.value = '250'; el.morph.dispatchEvent(new Event('input'));
      el.rackSynth.checked = true; await setRackSynth(true); await wait(100);
      const lane = genSettings().morph;
      el.rackSynth.checked = false; await setRackSynth(false);
      toTone(); await wait(100);
      return { lane, tone: genSettings().morph, b: genSettings(1).morph };
    }""")
    check("a generator built later - a rack's lane, a new tone - takes the slider's position",
          built == {"lane": 2.5, "tone": 2.5, "b": 2.5}, str(built))

    def search(q):
        p.evaluate("(q) => { el.benchSearch.value = q; el.benchSearch.dispatchEvent(new Event('input')); }", q)
        return p.evaluate("""() => Array.from(el.benchResults.querySelectorAll('button'))
          .map((b) => [b.firstChild.textContent, b.querySelector('.crumb').textContent])""")
    p.evaluate("() => { el.shape.value = 'morph'; el.shape.dispatchEvent(new Event('change')); }")
    timbre = search("timbre")
    check("timbre finds it", ["Morph", "Generator"] in timbre, str(timbre[:4]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the morph goes from sine to square without a step or a hole")
