"""The voice filter (H3): a state-variable filter in every note, with key
tracking and an envelope of its own.

What would go wrong, and what is checked for it:

- the wrong response: at a fixed cutoff the filter is held to Web Audio's
  own BiquadFilterNode, four types, three cutoffs and three Qs, to 0.01 dB -
  with the spec's one trap minded, that a low or high pass takes its Q in
  decibels and the other two as a ratio;
- a filter that blows up when its cutoff moves: swept at audio rate across
  the whole range at a Q of 20, it stays finite and bounded;
- key tracking that tracks the wrong thing: a saw's harmonics, each divided
  by the same saw unfiltered, are the cookbook response at the cutoff the
  note should have moved it to;
- the envelope: a note is bright as it opens and settles to the plain
  cutoff; each note of a chord has its own, from its own start; the dyad's is
  gated with the amplifier's;
- a source on the cutoff, layer B's own filter, the rows shown only while it
  is on, the panel and setup codes.
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


def line(x, f):
    x = np.asarray(x, dtype=float)
    n = len(x)
    i = np.arange(n)
    w = (BH[0] - BH[1] * np.cos(2 * np.pi * i / n)
         + BH[2] * np.cos(4 * np.pi * i / n) - BH[3] * np.cos(6 * np.pi * i / n))
    return abs(np.sum(x * w * np.exp(-2j * np.pi * f * i / RATE))) / np.sum(w) * 2


def cookbook_lp(f, fc, q):
    """The cookbook low pass's magnitude at f - the bilinear transform of the
    same prototype the filter is."""
    w0 = 2 * np.pi * fc / RATE
    alpha = np.sin(w0) / (2 * q)
    b = np.array([(1 - np.cos(w0)) / 2, 1 - np.cos(w0), (1 - np.cos(w0)) / 2])
    a = np.array([1 + alpha, -2 * np.cos(w0), 1 - alpha])
    z = np.exp(-1j * 2 * np.pi * f / RATE)
    return abs((b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z))


CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('mode', 'wave'); core.set('amp', 0.5); core.set('interval', 0); core.set('phase', 0);
  core.set('shape', 'ramp');
  for (const k in setup.tone) core.set(k, setup.tone[k]);
  for (const k in setup.toneB || {}) core.set(k, setup.toneB[k], 1);
  if (setup.route) core.setRoutes([{ held: setup.route.held, slot: VCF_SLOT, amount: 1 }]);
  if (setup.gated) { core.setGated(true); core.gate(true, 1); }
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

    print("\n--- against Web Audio's biquad ---")
    cmp = p.evaluate("""() => {
      const ctx = new OfflineAudioContext(1, 1, 44100);
      const types = [[1, 'lowpass'], [2, 'bandpass'], [3, 'highpass'], [4, 'notch']];
      const freqs = new Float32Array(40);
      for (let i = 0; i < 40; i++) freqs[i] = 20 * Math.pow(1000, i / 39) * 0.999;
      const rows = [];
      for (const [type, name] of types) for (const fc of [200, 1000, 5000]) for (const q of [Math.SQRT1_2, 2, 10]) {
        const bq = ctx.createBiquadFilter();
        bq.type = name; bq.frequency.value = fc;
        // The spec's trap: a low or high pass reads Q in decibels.
        bq.Q.value = name === 'lowpass' || name === 'highpass' ? 20 * Math.log10(q) : q;
        const mag = new Float32Array(40), ph = new Float32Array(40);
        bq.getFrequencyResponse(freqs, mag, ph);
        // The filter's own response: its impulse response, transformed at
        // exactly those frequencies.
        const s = { ic1: 0, ic2: 0 }, g = svfG(fc, 44100), k = 1 / q, n = 16384, h = new Float64Array(n);
        for (let i = 0; i < n; i++) h[i] = svfStep(s, i === 0 ? 1 : 0, g, k, type);
        let worst = 0, worstAt = 0;
        for (let j = 0; j < 40; j++) {
          let re = 0, im = 0;
          const w = 2 * Math.PI * freqs[j] / 44100;
          for (let i = 0; i < n; i++) { re += h[i] * Math.cos(w * i); im -= h[i] * Math.sin(w * i); }
          const ours = Math.hypot(re, im);
          const err = mag[j] > 1e-3 ? Math.abs(20 * Math.log10(ours / mag[j])) : Math.abs(ours - mag[j]) * 1000;
          if (err > worst) { worst = err; worstAt = freqs[j]; }
        }
        rows.push([name, fc, Math.round(q * 100) / 100, worst, worstAt]);
      }
      return rows;
    }""")
    worst = max(cmp, key=lambda r: r[3])
    print("    36 settings, 40 frequencies each; worst %.5f dB (%s, %d Hz, Q %.2f, at %.0f Hz)"
          % (worst[3], worst[0], worst[1], worst[2], worst[4]))
    check("at a fixed cutoff the voice filter is Web Audio's biquad to 0.01 dB, all four types, three cutoffs, three Qs",
          worst[3] < 0.01, str(worst))
    # The null: read with the Q the spec does NOT use for a low pass, the
    # same comparison has to fail - or it was never looking at the Q.
    trap = p.evaluate("""() => {
      const ctx = new OfflineAudioContext(1, 1, 44100);
      const bq = ctx.createBiquadFilter();
      bq.type = 'lowpass'; bq.frequency.value = 1000; bq.Q.value = 10;
      const f = new Float32Array([1000]), mag = new Float32Array(1), ph = new Float32Array(1);
      bq.getFrequencyResponse(f, mag, ph);
      const s = { ic1: 0, ic2: 0 }, g = svfG(1000, 44100), n = 16384;
      let re = 0, im = 0;
      for (let i = 0; i < n; i++) { const y = svfStep(s, i === 0 ? 1 : 0, g, 1 / 10, 1); re += y * Math.cos(2 * Math.PI * 1000 * i / 44100); im -= y * Math.sin(2 * Math.PI * 1000 * i / 44100); }
      return 20 * Math.log10(Math.hypot(re, im) / mag[0]);
    }""")
    check("and a Q handed to a low pass as a ratio, not in decibels, misses by 10 dB at the cutoff: the comparison sees Q",
          abs(trap) > 5, "%.2f dB" % trap)

    print("\n--- a moving cutoff ---")
    swept = p.evaluate("""() => {
      const s = { ic1: 0, ic2: 0 };
      let worst = 0, finite = true, seed = 7;
      for (let i = 0; i < 44100; i++) {
        seed = (seed * 16807) % 2147483647;
        const x = seed / 2147483647 * 2 - 1;
        const fc = 50 * Math.pow(360, 0.5 + 0.5 * Math.sin(2 * Math.PI * 3000 * i / 44100));
        const y = svfStep(s, x, svfG(fc, 44100), 1 / 20, 1);
        if (!Number.isFinite(y)) finite = false;
        worst = Math.max(worst, Math.abs(y));
      }
      return { worst, finite };
    }""")
    check("swept from 50 Hz to 18 kHz three thousand times a second at a Q of 20, it stays finite and bounded",
          swept["finite"] and swept["worst"] < 50, str(swept))

    print("\n--- key tracking ---")
    rows = []
    # Half-way too: at nought and at one, "all the way whenever it is on"
    # gives the same answers as the real law, and a mutation of it passed.
    for f0 in (220, 880):
        for track in (0, 0.5, 1):
            fc = 1000 * (f0 / 261.63) ** track
            filt = run({"freq": f0, "vcfType": 1, "vcfCutoff": 1000, "vcfTrack": track}, n=88200)["L"]
            dry = run({"freq": f0}, n=88200)["L"]
            err = max(abs(20 * math.log10(line(filt, k * f0) / line(dry, k * f0) / cookbook_lp(k * f0, fc, math.sqrt(0.5))))
                      for k in (1, 2, 3, 5, 8))
            rows.append((f0, track, round(fc), err))
    print("    note, track, cutoff it should be at, worst harmonic off the cookbook: %s"
          % [(a, b2, c, round(d, 4)) for a, b2, c, d in rows])
    check("each harmonic is cut by the cookbook's response at the tracked cutoff, to 0.02 dB: fixed at 0, half-way at 0.5, following the note at 1",
          all(r[3] < 0.02 for r in rows), str(rows))

    print("\n--- the envelope ---")
    one = [{"note": 57, "freq": 220, "velocity": 1, "role": "xy"}]
    env = run({"voices": one, "vcfType": 1, "vcfCutoff": 300, "vcfEnv": 4, "fAttackMs": 1, "fDecayMs": 150,
               "fSustain": 0, "attackMs": 1, "sustain": 1}, n=44100, skip=0)["HL"]
    still = run({"voices": one, "vcfType": 1, "vcfCutoff": 300, "attackMs": 1, "sustain": 1}, n=44100, skip=0)["HL"]
    early, late = env[220:1102], env[30870:39690]
    b_early = line(early, 1100) / line(early, 220)
    b_late = line(late, 1100) / line(late, 220)
    b_still = line(still[30870:39690], 1100) / line(still[30870:39690], 220)
    print("    fifth harmonic against the note: %.4f as it opens, %.5f settled, %.5f with no envelope"
          % (b_early, b_late, b_still))
    check("a note opens bright and settles to the plain cutoff: its envelope, four octaves, then sustain nought",
          b_early > 10 * b_late and abs(b_late - b_still) < 0.01 * b_still, "%.4f, %.5f, %.5f" % (b_early, b_late, b_still))
    # Two notes, the second 400 ms after the first: each has its own.
    two = run({"voices": one, "vcfType": 1, "vcfCutoff": 300, "vcfEnv": 4, "fAttackMs": 1, "fDecayMs": 150,
               "fSustain": 0, "attackMs": 1, "sustain": 1}, n=0, skip=0,
              steps=[{"n": 17640}, {"n": 4410, "tone": {"voices": one + [{"note": 64, "freq": 330, "velocity": 1, "role": "xy"}]}}])["HL"]
    win = two[17640 + 220:17640 + 1543]
    first = line(win, 1100) / line(win, 220)
    second = line(win, 1650) / line(win, 330)
    print("    30 ms after the second note: fifth harmonic of the first %.5f, of the second %.4f" % (first, second))
    check("each note of a chord has its own filter envelope, from its own start",
          second > 10 * first, "%.5f, %.4f" % (first, second))
    # A key let go: the filter's release is its own, so a note with a long
    # amplifier release and a short filter release goes dark while it is
    # still sounding.
    held = {"voices": one, "vcfType": 1, "vcfCutoff": 300, "vcfEnv": 4, "fAttackMs": 1, "fSustain": 1,
            "fReleaseMs": 30, "attackMs": 1, "sustain": 1, "releaseMs": 2000}
    rel = run(held, n=0, skip=0, steps=[{"n": 13230}, {"n": 13230, "tone": {"voices": []}}])["HL"]
    before, after = rel[4410:13230], rel[13230 + 4410:26460]
    r_before = line(before, 1100) / line(before, 220)
    r_after = line(after, 1100) / line(after, 220)
    print("    fifth harmonic held open %.4f, and 100 ms after the key %.5f, the note still at %.2f of its level"
          % (r_before, r_after, line(after, 220) / line(before, 220)))
    check("letting go closes the filter on its own release while the note sounds on",
          r_after < 0.2 * r_before and line(after, 220) > 0.5 * line(before, 220), "%.4f, %.5f" % (r_before, r_after))
    # A cutoff moved in the middle of a sustained note, nothing else moving:
    # the coefficient is cached, and this is what would go stale.
    # The filter's own envelope settled - attack 1 ms, sustain 1 - so that
    # nothing but the cutoff moves: the first version left it decaying, its
    # level changed every sample, the cache was refreshed anyway and a stale
    # cache passed.
    still_env = {"voices": one, "vcfType": 1, "attackMs": 1, "sustain": 1, "fAttackMs": 1, "fSustain": 1}
    moved = run(dict(still_env, vcfCutoff=300), n=0, skip=0,
                steps=[{"n": 8820}, {"n": 17640, "tone": {"vcfCutoff": 3000}}])["HL"][8820 + 4410:]
    ref3k = run(dict(still_env, vcfCutoff=3000), n=26460, skip=13230)["HL"]
    m5, r5 = line(moved, 1100) / line(moved, 220), line(ref3k, 1100) / line(ref3k, 220)
    check("a cutoff moved in the middle of a held note takes effect there and then",
          abs(m5 - r5) < 1e-3 * r5, "%.5f against %.5f" % (m5, r5))
    # Layer B's filter envelope runs on B's times: B's decay long, A's short.
    vbe = {"shape": "ramp", "amp": 0.5, "vcfType": 1, "vcfCutoff": 300, "vcfEnv": 4, "fAttackMs": 1,
           "fDecayMs": 2000, "fSustain": 0, "attackMs": 1, "sustain": 1,
           "voices": [{"note": 69, "freq": 440, "velocity": 1, "role": "xy"}]}
    both = run({"voices": one, "vcfType": 1, "vcfCutoff": 300, "vcfEnv": 4, "fAttackMs": 1, "fDecayMs": 20,
                "fSustain": 0, "attackMs": 1, "sustain": 1}, n=17640, skip=8820, toneB=vbe)
    a_dark = line(both["L"], 1100) / line(both["L"], 220)
    b_bright = line(both["BL"], 2200) / line(both["BL"], 440)
    check("layer B's filter envelope runs on B's own times: B still open at 200 ms, A long shut",
          b_bright > 5 * a_dark, "B %.4f, A %.5f" % (b_bright, a_dark))
    gatedRun = run({"freq": 220, "vcfType": 1, "vcfCutoff": 300, "vcfEnv": 4, "fAttackMs": 1, "fDecayMs": 150,
                    "fSustain": 0}, n=44100, skip=0, gated=True)["L"]
    ungated = run({"freq": 220, "vcfType": 1, "vcfCutoff": 300, "vcfEnv": 4, "fAttackMs": 1, "fDecayMs": 150,
                   "fSustain": 0}, n=44100, skip=0)["L"]
    g_early = line(gatedRun[220:1102], 1100) / line(gatedRun[220:1102], 220)
    u_early = line(ungated[220:1102], 1100) / line(ungated[220:1102], 220)
    check("the dyad's filter envelope opens with a key, and stays shut with nothing gating it",
          g_early > 10 * u_early, "%.4f gated, %.5f not" % (g_early, u_early))

    print("\n--- a source on it, and layer B ---")
    pushed = run({"freq": 220, "vcfType": 1, "vcfCutoff": 500}, n=8820, route={"held": 0.5})["L"]
    fixed = run({"freq": 220, "vcfType": 1, "vcfCutoff": 500 * 2 ** 1.5}, n=8820)["L"]
    check("a source on the cutoff at half depth moves it an octave and a half",
          np.abs(pushed - fixed).max() < 1e-6, "%.2e" % np.abs(pushed - fixed).max())
    vb = {"shape": "ramp", "amp": 0.5, "vcfType": 1, "vcfCutoff": 300,
          "voices": [{"note": 69, "freq": 440, "velocity": 1, "role": "xy"}]}
    lay = run({"voices": [{"note": 57, "freq": 220, "velocity": 1, "role": "xy"}], "attackMs": 1, "sustain": 1},
              n=48510, toneB=dict(vb, attackMs=1, sustain=1))
    plainB = run({"voices": [{"note": 57, "freq": 220, "velocity": 1, "role": "xy"}], "attackMs": 1, "sustain": 1},
                 n=48510, toneB=dict(vb, vcfType=0, attackMs=1, sustain=1))
    a5 = line(lay["L"], 1100) / line(lay["L"], 220)
    b5 = line(lay["BL"], 2200) / line(lay["BL"], 440)
    b5plain = line(plainB["BL"], 2200) / line(plainB["BL"], 440)
    check("layer B filters its own voice: B's top cut, A's saw untouched",
          b5 < 0.2 * b5plain and abs(a5 - 0.2) < 0.01, "B %.4f of %.4f, A %.4f" % (b5, b5plain, a5))

    print("\n--- the panel and setup codes ---")
    page = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const set = (id, v, kind) => { el[id].value = String(v); el[id].dispatchEvent(new Event(kind)); };
      setView('bench'); setBenchTab('shape');
      const hidden = el.vcfCut.closest('.menu-row').hidden;
      set('vcfType', 3, 'change');
      const shownOn = el.vcfCut.closest('.menu-row').hidden === false && el.vcfGroup.offsetHeight > 0;
      set('vcfCut', 500, 'input'); set('vcfRes', 100, 'input'); set('vcfTrack', 50, 'input');
      set('vcfEnvAmt', -25, 'input'); set('vcfAtk', 20, 'input'); set('vcfDec', 400, 'input');
      set('vcfSus', 60, 'input'); set('vcfRel', 900, 'input');
      const g = genSettings();
      const a = [g.vcfType, Math.round(g.vcfCutoff * 100) / 100, Math.round(g.vcfQ * 1000) / 1000, g.vcfTrack, g.vcfEnv,
                 g.fAttackMs, g.fDecayMs, g.fSustain, g.fReleaseMs];
      const words = [el.vcfCutValue.textContent, el.vcfResValue.textContent, el.vcfTrackValue.textContent,
                     el.vcfEnvAmtValue.textContent];
      const code = snapshot();
      restore({}); await wait(30);
      const g0 = genSettings();
      const old = [g0.vcfType, el.vcfCut.closest('.menu-row').hidden];
      restore(code); await wait(30);
      const g1 = genSettings();
      const back = [g1.vcfType, Math.round(g1.vcfCutoff * 100) / 100, Math.round(g1.vcfQ * 1000) / 1000, g1.vcfTrack,
                    g1.vcfEnv, g1.fAttackMs, g1.fDecayMs, g1.fSustain, g1.fReleaseMs, el.vcfCut.closest('.menu-row').hidden];
      restore({ vcfType: 1, bVcf: 2, bVcfCut: 800 }); await wait(30);
      const split = [genSettings().vcfType, genSettings(1).vcfType, Math.round(genSettings(1).vcfCutoff)];
      // A's filter off and B's on, so the rows are right only if the switch
      // looks again: with both on they would show whether it did or not.
      restore({ vcfType: 0, bVcf: 2 }); await wait(30);
      showLayerOnPanel(1);
      const bRows = el.vcfCut.closest('.menu-row').hidden;
      showLayerOnPanel(0);
      const aRows = el.vcfCut.closest('.menu-row').hidden;
      restore({ vcfType: 4 }); await wait(30);
      const fallback = genSettings(1).vcfType;
      restore({}); await wait(30);
      return { hidden, shownOn, a, words, old, back, split, bRows, aRows, fallback };
    }""")
    print("    %s" % page)
    check("the filter's rows are hidden while it is off and shown when it is on",
          page["hidden"] and page["shownOn"], "%s, %s" % (page["hidden"], page["shownOn"]))
    check("its controls reach the generator in its own units: hertz on the trace filter's law, Q 0.71 to 20",
          page["a"] == [3, 632.46, 20.0, 0.5, -2.5, 20, 400, 0.6, 900], str(page["a"]))
    check("and say so", page["words"] == ["632 Hz", "Q 20.00", "50%", "-2.5 oct"], str(page["words"]))
    check("a setup code carries it back, rows and all", page["back"] == page["a"] + [False], str(page["back"]))
    check("a code from before has it off, rows hidden", page["old"] == [0, True], str(page["old"]))
    check("layer B filters from its own fields, and from A's where a code has none of B's",
          page["split"] == [1, 2, round(20 * 1000 ** 0.8)] and page["fallback"] == 4, "%s, %s" % (page["split"], page["fallback"]))
    # A was set off-and-on above; B is on. Switching the panel to B has to
    # show B's rows, or B's cutoff cannot be reached from the panel.
    check("switching the panel to B, filter on, shows its rows, and back to A, filter off, hides them",
          page["bRows"] is False and page["aRows"] is True, "%s, %s" % (page["bRows"], page["aRows"]))

    def search(q):
        p.evaluate("(q) => { el.benchSearch.value = q; el.benchSearch.dispatchEvent(new Event('input')); }", q)
        return p.evaluate("""() => Array.from(el.benchResults.querySelectorAll('button'))
          .map((b) => [b.firstChild.textContent, b.querySelector('.crumb').textContent])""")
    # With the filter on: while it is off its rows are hidden, and a search
    # that offered a hidden row would land on nothing.
    off = search("keytrack")
    p.evaluate("() => { el.vcfType.value = '1'; el.vcfType.dispatchEvent(new Event('change')); }")
    found = search("keytrack")
    p.evaluate("() => { el.vcfType.value = '0'; el.vcfType.dispatchEvent(new Event('change')); }")
    check("keytrack finds the voice filter while it is on, and offers nothing hidden while it is off",
          ["Key track", "Voice filter"] in found and not any(c == "Voice filter" for _, c in off), "%s / %s" % (found[:2], off[:2]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("every note has a filter of its own, and it is the cookbook's")
