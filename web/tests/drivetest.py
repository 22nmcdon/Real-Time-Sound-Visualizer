"""Shaping inside the voice (H2): drive, fold and crush.

What would go wrong, and what is checked for it:

- the wrong curve: a sine through the drive has the harmonics of
  tanh(g sin t) / tanh(g), worked out here by a transform of the curve
  itself, and through the fold exactly 2 J(2k+1)(g) - Bessel again;
- a step where the travel starts: a drive of nearly nothing is nearly no
  change, and the shaper with nothing on is the voice filtered and 31
  samples late, no more;
- shaping on the chord rather than in each voice: two driven notes with no
  difference tones between them, where the same two notes driven as one
  sum - worked out here, as the null - have them 30 dB up;
- shaping after the envelope: a note's harmonics keep their proportions as
  it dies away;
- aliasing, at twice the rate against once, pinned;
- the crusher's grid and its held samples, layer B, the cost, the panel and
  setup codes.
"""
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


def window(n):
    i = np.arange(n)
    return (BH[0] - BH[1] * np.cos(2 * np.pi * i / n)
            + BH[2] * np.cos(4 * np.pi * i / n) - BH[3] * np.cos(6 * np.pi * i / n))


def line(x, f):
    """One line's amplitude, the transform taken at exactly its frequency."""
    x = np.asarray(x, dtype=float)
    w = window(len(x))
    i = np.arange(len(x))
    return abs(np.sum(x * w * np.exp(-2j * np.pi * f * i / RATE))) / np.sum(w) * 2


def off_grid(x, f0, top=10000):
    x = np.asarray(x, dtype=float)
    w = window(len(x))
    spec = np.abs(np.fft.rfft(x * w))
    hz = np.arange(len(spec)) * RATE / len(x)
    grid = np.zeros(len(spec), dtype=bool)
    grid[:6] = True
    k = 1
    while k * f0 < RATE / 2:
        grid |= np.abs(hz - k * f0) < 4 * RATE / len(x)
        k += 1
    return 20 * math.log10(max(spec[~grid & (hz < top)].max(), 1e-15) / spec.max())


def curve_harmonics(fn, ks):
    """The odd harmonics a sine gets from a curve, from the curve itself."""
    t = np.arange(8192) * 2 * np.pi / 8192
    c = np.fft.rfft(fn(np.sin(t))) / 8192 * 2
    return [abs(c[k]) for k in ks]


def bessel_j(n, x):
    return sum((-1) ** k * (x / 2) ** (2 * k + n) / (math.factorial(k) * math.factorial(k + n)) for k in range(60))


CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('mode', 'wave'); core.set('amp', 0.5); core.set('interval', 0); core.set('phase', 0);
  core.set('shape', 'sine');
  for (const k in setup.tone) core.set(k, setup.tone[k]);
  for (const k in setup.toneB || {}) core.set(k, setup.toneB[k], 1);
  if (setup.route) core.setRoutes([{ held: setup.route.held, slot: DRIVE_SLOT, amount: 1 }]);
  const out = { L: [], HL: [], BL: [] };
  for (const step of setup.steps || [{ n: setup.n }]) {
    for (const k in step.tone || {}) core.set(k, step.tone[k]);
    const n = step.n, L = new Float32Array(n), R = new Float32Array(n);
    const HL = new Float32Array(n), HR = new Float32Array(n), BL = new Float32Array(n), BR = new Float32Array(n);
    core.block(L, R, n, HL, HR, BL, BR);
    for (let i = 0; i < n; i++) { out.L.push(L[i]); out.HL.push(HL[i]); out.BL.push(BL[i]); }
  }
  const from = setup.skip || 0;
  return { L: out.L.slice(from), HL: out.HL.slice(from), BL: out.BL.slice(from) };
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
    def run(tone, n=48510, skip=4410, **kw):
        out = p.evaluate(CORE, dict({"tone": tone, "n": n, "skip": skip}, **kw))
        return {k: np.asarray(v) for k, v in out.items()}

    print("\n--- with nothing on ---")
    plain = run({"freq": 440}, n=8820, skip=0)["L"]
    through = run({"freq": 440}, n=8820, skip=0, route={"held": 0})["L"]
    pushed = run({"freq": 440}, n=8820, skip=0, route={"held": 0.6})["L"]
    late = np.abs(through[31 + 200:] - plain[200:-31]).max()
    print("    the shaper with nothing on, against the plain wave 31 samples late: %.2e" % late)
    check("the shaper with nothing on is the voice 31 samples late and filtered, no more",
          late < 1e-4 and np.abs(pushed[231:] - plain[200:-31]).max() > 0.05, "%.2e" % late)
    static = run({"freq": 440, "drive": 0.3}, n=8820, skip=0)["L"]
    check("a source on Drive at 0.6 of full depth is a drive of 0.3, from a slider at nought",
          np.abs(pushed - static).max() < 1e-6, "%.2e" % np.abs(pushed - static).max())
    faint = run({"freq": 220, "drive": 0.02})["L"]
    ref = run({"freq": 220}, route={"held": 0})["L"]
    check("and a drive of 0.02 is within 1e-4 of no drive: the travel starts from no change",
          np.abs(faint - ref).max() < 1e-4, "%.2e" % np.abs(faint - ref).max())

    print("\n--- the curves ---")
    d = 0.5
    g = 30 * d * d
    drv = run({"freq": 110, "drive": d}, n=92610)["L"]
    want = curve_harmonics(lambda x: np.tanh(g * x) / np.tanh(g), (1, 3, 5, 7, 9))
    got = [line(drv, 110 * k) / 0.5 for k in (1, 3, 5, 7, 9)]
    worst = max(abs(a - w) / w for a, w in zip(got, want))
    even = max(line(drv, 110 * k) for k in (2, 4, 6)) / 0.5
    print("    drive 0.5 (g 7.5): harmonics 1-9 %s against the curve's %s; evens %.1e"
          % ([round(v, 4) for v in got], [round(v, 4) for v in want], even))
    check("a driven sine has tanh(g x)/tanh(g)'s odd harmonics, each within 0.5 per cent, and no even ones",
          worst < 5e-3 and even < 1e-5, "worst %.3f%%" % (100 * worst))
    for f, name in ((0.5, "folded"), (0.05, "gently curved")):
        gf = 6 * math.pi * f
        norm = 1 / math.sin(gf) if gf < math.pi / 2 else 1
        fd = run({"freq": 110, "fold": f}, n=92610)["L"]
        got = [line(fd, 110 * k) / 0.5 for k in (1, 3, 5, 7, 9, 11)]
        want = [abs(2 * bessel_j(k, gf)) * norm for k in (1, 3, 5, 7, 9, 11)]
        worst = max(abs(a - w) for a, w in zip(got, want))
        print("    fold %.2f (g %.2f): harmonics %s, Bessel's %s" % (f, gf, [round(v, 4) for v in got], [round(v, 4) for v in want]))
        check("a %s sine has the fold's Bessel harmonics, 2 J(2k+1)(g), to 0.002 of full scale" % name,
              worst < 2e-3, "worst %.4f" % worst)

    print("\n--- inside each voice, not on the chord ---")
    v = [{"note": 69, "freq": 440, "velocity": 1, "role": "x"}, {"note": 73, "freq": 554.37, "velocity": 1, "role": "y"}]
    chord = run({"voices": v, "drive": 0.7, "attackMs": 1, "sustain": 1}, n=92610)["HL"]
    top = line(chord, 440)
    im = max(line(chord, f) for f in (554.37 - 440, 2 * 440 - 554.37, 2 * 554.37 - 440)) / top
    # The null: the same two notes driven as one sum, worked out here.
    t = np.arange(92610) / RATE
    g = 30 * 0.7 ** 2
    summed = np.tanh(g * 0.5 * (np.sin(2 * np.pi * 440 * t) + np.sin(2 * np.pi * 554.37 * t))) / np.tanh(g)
    im_sum = max(line(summed, f) for f in (554.37 - 440, 2 * 440 - 554.37, 2 * 554.37 - 440)) / line(summed, 440)
    print("    difference tones against the note: %.1f dB in each voice, %.1f dB were the chord driven as a sum"
          % (20 * math.log10(max(im, 1e-15)), 20 * math.log10(im_sum)))
    check("two driven notes make no difference tones: each voice is driven on its own",
          im < 1e-4 and im_sum > 0.03, "%.2e against %.2e" % (im, im_sum))
    # A note dying away keeps its proportions: the drive is before the envelope.
    note = [{"note": 57, "freq": 220, "velocity": 1, "role": "xy"}]
    dying = run({"freq": 220}, n=0, skip=0, steps=[
        {"n": 22050, "tone": {"voices": note, "drive": 0.6, "attackMs": 1, "decayMs": 5, "sustain": 1,
                              "releaseMs": 400}},
        {"n": 22050, "tone": {"voices": []}}])["HL"]
    early = dying[8000:16820]
    faded = dying[22050 + 4410:22050 + 13230]
    r_early = line(early, 660) / line(early, 220)
    r_late = line(faded, 660) / line(faded, 220)
    print("    third harmonic against the note: %.4f while held, %.4f while it fades (level %.3f of it)"
          % (r_early, r_late, line(faded, 220) / line(early, 220)))
    check("a note keeps its colour as it dies away: shaped before the envelope, not after",
          abs(r_late - r_early) < 0.01 * r_early and line(faded, 220) < 0.6 * line(early, 220),
          "%.4f, %.4f" % (r_early, r_late))

    print("\n--- aliasing ---")
    # A fold of 0.3 at 2 kHz measured -163.5: its Bessel terms die long
    # before any could fold back under 10 kHz, so it could not show what
    # the oversampling is worth. At full fold, g is 6 pi and they reach
    # 40 kHz.
    fold_2k = off_grid(run({"freq": 2000, "fold": 1})["L"], 2000)
    drive_4k = off_grid(run({"freq": 4000, "drive": 0.8})["L"], 4000)
    drive_4k4 = off_grid(run({"freq": 4000, "drive": 0.8, "shapeOS": 4})["L"], 4000)
    print("    full fold at 2 kHz: %.1f dB; drive 0.8 at 4 kHz: %.1f dB, and %.1f at 4x" % (fold_2k, drive_4k, drive_4k4))
    # Measured when this landed: the fold -97.5 at twice and -4.1 with none;
    # the drive -30.4 at twice, -46.3 at four times and -19.8 with none. A
    # hard drive is a square, whose harmonics fall only as 1/k.
    check("twice the rate is worth 90 dB to a full fold: under -95, where none gives -4",
          fold_2k < -95, "%.1f dB" % fold_2k)
    # And a chord's voices, each through a shaper of its own: the dyad's two
    # are not the poly voices', and a mutation that shaped a chord's voices
    # at the base rate passed every check above.
    one_voice = run({"voices": [{"note": 95, "freq": 2000, "velocity": 1, "role": "xy"}], "fold": 1,
                     "attackMs": 1, "sustain": 1})["HL"]
    fold_poly = off_grid(one_voice, 2000)
    check("a chord's voice is folded at twice the rate too: under -95 dB",
          fold_poly < -95, "%.1f dB" % fold_poly)
    check("a hard drive at 4 kHz is under -28 dB at twice the rate, and at four times within a decibel of the square's -46.2",
          drive_4k < -28 and drive_4k4 < -45, "%.1f, %.1f" % (drive_4k, drive_4k4))

    print("\n--- crush ---")
    cr = run({"freq": 220, "crushBits": 3}, n=8820)["L"] / 0.5
    grid = np.abs(cr * 4 - np.round(cr * 4)).max()
    check("three bits put the wave on a grid of quarters, before the level", grid < 1e-6
          and len(np.unique(np.round(cr * 4))) == 9, "%.2e, %d levels" % (grid, len(np.unique(np.round(cr * 4)))))
    first = run({"freq": 220, "crushHz": 1000, "phase": 0}, n=100, skip=0)["L"]
    wave = run({"freq": 220, "phase": 0}, n=100, skip=0)["L"]
    check("the rate holds from the very first sample, not from silence",
          np.array_equal(first[:44], np.full(44, wave[0])) and abs(wave[0]) > 0.01, "%s, %s" % (first[:2], wave[:2]))
    held = run({"freq": 220, "crushHz": 1000}, n=8820)["L"]
    runs = np.diff(np.flatnonzero(np.diff(held) != 0))
    check("a rate of 1 kHz holds each sample for 44 or 45: 44.1 on average",
          set(runs.tolist()) <= {44, 45} and abs(runs.mean() - 44.1) < 0.05, "%s, mean %.3f" % (sorted(set(runs.tolist())), runs.mean()))

    print("\n--- layers, and what it costs ---")
    vb = {"shape": "sine", "amp": 0.5, "fold": 0.4, "voices": [{"note": 69, "freq": 440, "velocity": 1, "role": "xy"}]}
    lay = run({"voices": [{"note": 57, "freq": 220, "velocity": 1, "role": "xy"}]}, n=48510, toneB=vb)
    check("layer B shapes its own voice: B folded, A still a sine",
          line(lay["BL"], 1320) > 0.02 and line(lay["L"], 660) < 1e-5,
          "B %.4f, A %.2e" % (line(lay["BL"], 1320), line(lay["L"], 660)))
    cost = p.evaluate("""() => {
      const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
      const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
      core.set('mode', 'wave'); core.set('shape', 'ramp');
      const v = [];
      for (let k = 0; k < 8; k++) v.push({ note: 48 + k * 3, freq: 130.81 * Math.pow(2, k / 4), velocity: 1, role: k ? 'u' : 'x' });
      core.set('voices', v); core.set('voices', v, 1); core.set('shape', 'ramp', 1);
      for (const layer of [0, 1]) {
        core.set('drive', 0.5, layer); core.set('fold', 0.3, layer); core.set('crushBits', 6, layer);
        core.set('vcfType', 1, layer); core.set('vcfTrack', 1, layer); core.set('vcfEnv', 2, layer);
      }
      const n = 44100, a = new Float32Array(n), b = new Float32Array(n);
      const c = new Float32Array(n), d = new Float32Array(n), e = new Float32Array(n), f = new Float32Array(n);
      core.block(a, b, 4410, c, d, e, f);
      // The best of three: what the code costs, rather than what else the
      // machine was doing during one of them.
      let best = Infinity;
      for (let r = 0; r < 3; r++) {
        const t0 = performance.now(); core.block(a, b, n, c, d, e, f); best = Math.min(best, performance.now() - t0);
      }
      return best;
    }""")
    print("    one second of sixteen voices over two layers, driven, folded, crushed and filtered, best of three: %.0f ms" % cost)
    check("sixteen shaped and filtered voices over two layers run in under half of real time", cost < 500, "%.0f ms" % cost)

    print("\n--- the panel and setup codes ---")
    page = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const set = (id, v, kind) => { el[id].value = String(v); el[id].dispatchEvent(new Event(kind)); };
      setView('bench'); setBenchTab('shape');
      const shown = el.shpGroup.offsetHeight > 0;
      set('shpDrive', 50, 'input'); set('shpFold', 30, 'input'); set('shpBits', 4, 'change'); set('shpRate', 2000, 'change');
      set('shpOS', 4, 'change');
      const g = genSettings();
      const a = [g.drive, g.fold, g.crushBits, g.crushHz, el.shpDriveValue.textContent, el.shpFoldValue.textContent,
                 g.shapeOS];
      const code = snapshot();
      restore({}); await wait(30);
      const g0 = genSettings();
      const old = [g0.drive, g0.fold, g0.crushBits, g0.crushHz, el.shpDriveValue.textContent, g0.shapeOS];
      restore(code); await wait(30);
      const g1 = genSettings();
      const back = [g1.drive, g1.fold, g1.crushBits, g1.crushHz, g1.shapeOS];
      restore({ shpFold: 20, bFold: 60 }); await wait(30);
      const split = [genSettings().fold, genSettings(1).fold];
      restore({ shpDrive: 40 }); await wait(30);
      const fallback = genSettings(1).drive;
      restore({}); await wait(30);
      return { shown, a, old, back, split, fallback };
    }""")
    print("    %s" % page)
    check("the section is on the Shape tab and its controls reach the generator, the drive reading its gain",
          page["shown"] and page["a"] == [0.5, 0.3, 4, 2000, "+17.5 dB", "0.30", 4], str(page["a"]))
    check("a setup code carries it back", page["back"] == [0.5, 0.3, 4, 2000, 4], str(page["back"]))
    check("a code from before has it all off, at twice the rate", page["old"] == [0, 0, 0, 0, "off", 2], str(page["old"]))
    check("layer B shapes from its own fields, and from A's where a code has none of B's",
          page["split"] == [0.2, 0.6] and page["fallback"] == 0.4, "%s, %s" % (page["split"], page["fallback"]))

    def search(q):
        p.evaluate("(q) => { el.benchSearch.value = q; el.benchSearch.dispatchEvent(new Event('input')); }", q)
        return p.evaluate("""() => Array.from(el.benchResults.querySelectorAll('button'))
          .map((b) => [b.firstChild.textContent, b.querySelector('.crumb').textContent])""")
    found = search("lofi")
    check("lofi finds the crusher", ["Crush", "Shaping"] in found, str(found[:3]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the voice can be pushed, folded and crushed, and each voice on its own")
