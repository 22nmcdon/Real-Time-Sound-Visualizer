"""G1's noises: white, pink, brown, and a level sampled and held each cycle.

What would go wrong, and what is checked for it:

- a colour that is not the colour. White is flat, pink falls 3 dB an octave
  and brown 6, measured octave by octave from 100 Hz to 6.4 kHz on averaged
  spectra - the top octave is left out for brown, where any digital sum
  flattens towards Nyquist;
- a noise too loud or too quiet: pink and brown at an RMS of 0.28, white at
  a uniform's 0.577;
- one noise twice. The two channels of a figure, and the layers, are each
  their own: left against right correlates at nought, differenced;
- a stepped shape that is not held, or not clocked by the note: inside each
  cycle it is one level, the levels cover -0.9 to 0.9, and its spectrum has
  a hole at the note and every harmonic - which move when the note does;
- steps that alias: at 4 kHz, where the steps' own spectrum reaches far
  past Nyquist, the holes stay below -50 dB. Uncorrected, what folds back
  fills them to -34;
- the chord's path and layer B, which are other code from the dyad's: a
  poly voice steps at its own note, and layer B plays its own colour.
"""
import math, os, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
RATE = 44100

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


def averaged(x, seg):
    """Power spectrum averaged over half-overlapping Hann windows - a noise's
    spectrum from one window is itself noise, a decibel or two either way."""
    x = np.asarray(x, dtype=float)
    w = np.hanning(seg)
    total, count = None, 0
    for s in range(0, len(x) - seg, seg // 2):
        f = np.abs(np.fft.rfft(x[s:s + seg] * w)) ** 2
        total = f if total is None else total + f
        count += 1
    return total / count, np.fft.rfftfreq(seg, 1 / RATE)


def slopes(x, octaves=7):
    """dB from each octave to the next from 100 Hz, and the straight line's
    slope through all of them.

    The line is what is judged closely. Each octave's own step was first,
    held to 0.4 dB, and it is two band levels' difference with a tenth of a
    decibel of spread in each; pink's lowest step came out at -3.46 on a run
    where its code had not changed. Each step is still held loosely, to
    catch a colour with a bend in it."""
    power, hz = averaged(x, 8192)
    bands = [10 * math.log10(power[(hz >= lo) & (hz < 2 * lo)].mean()) for lo in [100 * 2 ** i for i in range(octaves)]]
    line = float(np.polyfit(np.arange(octaves), bands, 1)[0])
    return [round(b - a, 2) for a, b in zip(bands, bands[1:])], round(line, 2)


def holes(x, f0, count=4):
    """The spectrum at the note and its harmonics, against the middle of the
    first lobe, half-way to the note."""
    power, hz = averaged(x, RATE)
    ref = power[(hz > f0 * 0.3) & (hz < f0 * 0.7)].mean()
    return [round(10 * math.log10(power[np.abs(hz - k * f0) < 2].mean() / ref), 1)
            for k in range(1, count + 1) if k * f0 < RATE / 2]


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('mode', 'wave'); core.set('amp', 1); core.set('interval', 0); core.set('phase', 0);
  for (const k in setup.tone) core.set(k, setup.tone[k]);
  for (const k in setup.toneB || {}) core.set(k, setup.toneB[k], 1);
  if (setup.voices) { core.set('voices', setup.voices); core.set('voices', setup.voices, 1); }
  const n = setup.n, L = new Float32Array(n), R = new Float32Array(n);
  const BL = new Float32Array(n), BR = new Float32Array(n);
  core.block(L, R, n, null, null, BL, BR);
  const from = setup.skip || 0;
  return { L: Array.from(L.subarray(from)), R: Array.from(R.subarray(from)), BL: Array.from(BL.subarray(from)) };
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
    run = lambda setup: p.evaluate(CORE, dict({"n": 441000}, **setup))
    # Twenty seconds for the colours, which halves the spread of each band.
    colour = lambda sh: run({"tone": {"shape": sh, "freq": 220}, "n": 882000})

    print("\n--- the colours ---")
    out = {sh: colour(sh) for sh in ("noise", "pink", "brown")}
    # Brown to 3.2 kHz: above it any digital sum flattens towards Nyquist.
    s = {sh: slopes(o["L"], 6 if sh == "brown" else 7) for sh, o in out.items()}
    for sh in s:
        print("    %-6s RMS %.3f, dB an octave from 100 Hz: %s, the line %.2f" % (sh, rms(out[sh]["L"]), s[sh][0], s[sh][1]))
    def colour_is(sh, want):
        steps, line = s[sh]
        return abs(line - want) < 0.2 and all(abs(v - want) < 0.8 for v in steps)
    check("white is flat: its line within 0.2 dB an octave of level, and no octave a step of 0.8",
          colour_is("noise", 0), str(s["noise"]))
    check("pink falls 3 dB an octave: its line within 0.2 of it, and every octave within 0.8",
          colour_is("pink", -3), str(s["pink"]))
    check("brown falls 6 dB an octave to 3.2 kHz: its line within 0.2 of it, and every octave within 0.8",
          colour_is("brown", -6), str(s["brown"]))
    levels = {sh: round(rms(o["L"]), 3) for sh, o in out.items()}
    check("pink and brown at an RMS of 0.28, white at a uniform's 0.577",
          abs(levels["pink"] - 0.28) < 0.02 and abs(levels["brown"] - 0.28) < 0.03 and abs(levels["noise"] - 0.577) < 0.01,
          str(levels))
    # Of the first differences, not the signals. Brown is nearly all below
    # 30 Hz, so ten seconds of it are a few hundred independent samples and
    # its correlation wandered to -0.07 by chance; differenced it is white
    # again and the ten seconds are 441,000. One state shared by the two
    # channels still shows: each difference then spans the other channel's
    # step, and they correlate at a half.
    corr = {sh: round(float(np.corrcoef(np.diff(o["L"]), np.diff(o["R"]))[0, 1]), 3) for sh, o in out.items()}
    check("and each channel its own noise: left against right correlates at nought",
          all(abs(v) < 0.02 for v in corr.values()), str(corr))

    print("\n--- sample and hold ---")
    held = run({"tone": {"shape": "stepped", "freq": 220}, "n": 44100})
    x = np.asarray(held["L"])
    period = RATE / 220
    # Inside each cycle, away from its edges, one level.
    inside, levels_seen = [], []
    for c in range(2, 200):
        a, e = int(math.ceil((c + 0.1) * period)), int(math.floor((c + 0.9) * period))
        seg = x[a:e]
        inside.append(float(seg.max() - seg.min()))
        levels_seen.append(float(seg.mean()))
    changed = sum(1 for u, v in zip(levels_seen, levels_seen[1:]) if abs(u - v) > 1e-6)
    print("    worst spread inside a cycle %.2e; levels %.3f to %.3f; %d of %d cycles a new level"
          % (max(inside), min(levels_seen), max(levels_seen), changed, len(levels_seen) - 1))
    check("inside each cycle of the note it holds one level, and every cycle draws a new one",
          max(inside) < 1e-6 and changed == len(levels_seen) - 1, "%.2e, %d" % (max(inside), changed))
    check("the levels cover -0.9 to 0.9 and no further",
          -0.9 <= min(levels_seen) < -0.8 and 0.8 < max(levels_seen) <= 0.9, "%.3f, %.3f" % (min(levels_seen), max(levels_seen)))

    at220 = holes(run({"tone": {"shape": "stepped", "freq": 220}})["L"], 220)
    at330 = run({"tone": {"shape": "stepped", "freq": 330}})["L"]
    moved, stale = holes(at330, 330), holes(at330, 220, 1)
    print("    holes at 220 Hz and its harmonics %s dB; at 330 %s, where 220 is now %s" % (at220, moved, stale))
    check("its spectrum has a hole at the note and each harmonic, 38 dB down or more",
          all(v < -38 for v in at220), str(at220))
    check("and the holes follow the note: at 330 Hz they are at 330's harmonics, and 220 is no longer one",
          all(v < -38 for v in moved) and stale[0] > -10, "%s; 220 at %s" % (moved, stale))
    # The right channel at its own note: a just fifth up, 330 Hz. At a unison
    # the two step together whichever phase the right one reads, and a right
    # channel clocked by the left passed.
    fifth = run({"tone": {"shape": "stepped", "freq": 220, "interval": 7, "just": True}})
    right, right_at_left = holes(fifth["R"], 330), holes(fifth["R"], 220, 1)
    check("the right channel steps at its own note: a fifth up, its holes at 330 and not at 220",
          all(v < -38 for v in right) and right_at_left[0] > -10, "%s; 220 at %s" % (right, right_at_left))
    high = holes(run({"tone": {"shape": "stepped", "freq": 4000}})["L"], 4000)
    print("    at 4 kHz: %s dB" % high)
    check("band-limited: at 4 kHz what folds back leaves the holes below -50 dB, where uncorrected it fills them to -34",
          all(v < -50 for v in high), str(high))

    print("\n--- the chord's path and layer B ---")
    poly = run({"tone": {"shape": "stepped"}, "toneB": {"shape": "brown"},
                "voices": [{"note": 57, "freq": 220, "velocity": 1, "role": "xy"}], "n": 441000 + 8192, "skip": 8192})
    ph = holes(poly["L"], 220)
    bs = slopes(poly["BL"], 6)
    print("    a voice's holes %s; layer B's slopes %s" % (ph, bs))
    check("a poly voice steps at its own note", all(v < -38 for v in ph), str(ph))
    # The chord's path has a step of its own to hand the correction, so it is
    # held at 4 kHz as the dyad's is; at 220 Hz one uncorrected passes.
    fast = holes(run({"tone": {"shape": "stepped"}, "voices": [{"note": 107, "freq": 4000, "velocity": 1, "role": "xy"}],
                      "n": 441000 + 8192, "skip": 8192})["L"], 4000)
    check("and is band-limited too: a voice at 4 kHz keeps its holes below -50 dB", all(v < -50 for v in fast), str(fast))
    check("and layer B plays its own colour - brown, 6 dB an octave - not A's",
          abs(bs[1] + 6) < 0.3 and all(abs(v + 6) < 0.8 for v in bs[0]), str(bs))

    print("\n--- on the page ---")
    page = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const offered = [...el.shape.options].map((o) => o.value);
      restore({ shape: 'pink' }); await wait(400);
      const x = state.source.getLatestWindow(8192)[0];
      let power = 0; for (const v of x) power += v * v;
      return { offered, shape: genSettings().shape, code: snapshot().shape, rms: Math.sqrt(power / x.length) };
    }""")
    print("    %s" % {k: v for k, v in page.items() if k != "offered"})
    check("the Shape menu offers the three, and a code's shape is heard and written back",
          {"pink", "brown", "stepped"} <= set(page["offered"]) and page["shape"] == "pink" and page["code"] == "pink"
          and page["rms"] > 0.05, str(page))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("each noise is its colour, and the stepped one is held and pitched")
