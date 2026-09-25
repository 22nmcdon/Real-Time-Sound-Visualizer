"""Delay and chorus (I1): the plane's effects that act across time.

What would go wrong, and what is checked for it:

- an echo a sample early or late, or at the wrong level: a burst is played
  and stopped, and every repeat is compared with it, sample for sample -
  the n-th at n delays and mix times feedback^(n-1). The burst is shorter
  than the delay, so the repeats do not overlap and each can be read alone;
- ping-pong crossing the wrong repeat, or none: the fixture is a 3:2 figure,
  so X and Y differ and a crossing shows. The first repeat is not crossed,
  the second is, the third is back;
- a feedback that runs away: asked for five, it is held at 0.9 - measured
  as the ratio of two repeats, and a quiet flanger asked for five stays
  quiet. No feedback is a modulation destination (S4);
- a time change that jumps, which clicks: the read position glides;
- the tempo: a quarter at 120 BPM is 500 ms, and follows the tempo;
- the chorus: its sidebands are at the carrier plus and minus the rate and
  are the size the Bessel function says for the depth, which no chorus that
  merely delays or merely wobbles the level would give; and its two taps
  are in quadrature, so a diagonal - one signal in both channels - comes out
  with the channels apart, and back together with the depth at nought;
- once, and to every pair: in poly the heard pair and both layers' pictures
  each have their own line, outside it the heard pair is the picture;
- the panel, and setup codes.
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


def bessel_j(n, x):
    return sum((-1) ** k * (x / 2) ** (2 * k + n) / (math.factorial(k) * math.factorial(k + n)) for k in range(30))


# A core off the page, run as a list of blocks: each block's settings are
# applied and then that many samples are made, one continuous run.
CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('mode', 'wave'); core.set('shape', 'sine'); core.set('amp', 0.5);
  const out = { L: [], R: [], HL: [], HR: [], BL: [], BR: [] };
  for (const step of setup.steps) {
    for (const k in step.tone || {}) core.set(k, step.tone[k]);
    for (const k in step.toneB || {}) core.set(k, step.toneB[k], 1);
    const n = step.n, L = new Float32Array(n), R = new Float32Array(n);
    const HL = new Float32Array(n), HR = new Float32Array(n), BL = new Float32Array(n), BR = new Float32Array(n);
    core.block(L, R, n, HL, HR, BL, BR);
    for (const [k, a] of [['L', L], ['R', R], ['HL', HL], ['HR', HR], ['BL', BL], ['BR', BR]])
      for (let i = 0; i < n; i++) out[k].push(a[i]);
  }
  return out;
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
    def run(*steps):
        out = p.evaluate(CORE, {"steps": list(steps)})
        return {k: np.asarray(v) for k, v in out.items()}

    print("\n--- the repeats, sample for sample ---")
    # A burst of 2000 samples, then silence: 100 ms is 4410 samples, so each
    # repeat has 2410 samples of silence before the next.
    D, B = 4410, 2000
    fig = {"freq": 220, "interval": 7, "delayMs": 100, "delayMix": 0.7, "delayFeedback": 0.5}
    out = run({"tone": fig, "n": B}, {"tone": {"amp": 0}, "n": 4 * D})
    burstL, burstR = out["L"][:B], out["R"][:B]
    worst, levels = 0, []
    for k in (1, 2, 3):
        want = 0.7 * 0.5 ** (k - 1)
        worst = max(worst, np.abs(out["L"][k * D:k * D + B] - want * burstL).max(),
                    np.abs(out["R"][k * D:k * D + B] - want * burstR).max())
        levels.append(np.abs(out["L"][k * D:k * D + B]).max() / np.abs(burstL).max())
    gaps = max(np.abs(out["L"][k * D + B:(k + 1) * D]).max() for k in (0, 1, 2))
    print("    repeat levels against the burst: %s; worst error %.2e; between them %.2e"
          % ([round(v, 4) for v in levels], worst, gaps))
    check("each repeat is the burst at n x 100 ms exactly, at 0.7 x 0.5^(n-1), to float precision",
          worst < 1e-6 and gaps < 1e-6 and np.abs(burstL).max() > 0.4, "%.2e" % worst)

    # 375 ms, the default, as samples: 16537.5. Between two, so read by
    # interpolation, and the repeat is the mean of each two neighbours of
    # the burst. A first version found the lag by correlation, which
    # favoured whole samples - interpolating an already interpolated repeat
    # smooths it again and loses it energy - and read 16537.0 of a delay
    # that was right; the model is exact, so it is compared exactly.
    out = run({"tone": {"freq": 220, "interval": 0, "delayMs": 375, "delayMix": 1, "delayFeedback": 0}, "n": 300},
              {"tone": {"amp": 0}, "n": 17500})
    burst = np.concatenate([out["L"][:300], np.zeros(17800 - 300)])
    at = np.arange(16537, 16900)
    half = 0.5 * (burst[at - 16538] + burst[at - 16537])
    whole = burst[at - 16537]
    err = np.abs(out["L"][at] - half).max()
    check("375 ms lands at 16537.5 samples, between two, read by interpolation",
          err < 1e-6 and np.abs(out["L"][at] - whole).max() > 1e-3, "worst %.2e" % err)

    print("\n--- ping-pong ---")
    pp = run({"tone": dict(fig, delayPingPong=True), "n": B}, {"tone": {"amp": 0}, "n": 4 * D})
    cross = []
    for k in (1, 2, 3):
        want = 0.7 * 0.5 ** (k - 1)
        straight = max(np.abs(pp["L"][k * D:k * D + B] - want * burstL).max(), np.abs(pp["R"][k * D:k * D + B] - want * burstR).max())
        crossed = max(np.abs(pp["L"][k * D:k * D + B] - want * burstR).max(), np.abs(pp["R"][k * D:k * D + B] - want * burstL).max())
        cross.append((straight < 1e-6, crossed < 1e-6))
    print("    (straight, crossed) for repeats 1, 2, 3: %s" % cross)
    check("the first repeat comes back where it went, the second crossed, the third back again",
          cross == [(True, False), (False, True), (True, False)], str(cross))

    print("\n--- the feedback is held ---")
    held = run({"tone": dict(fig, delayFeedback=5), "n": B}, {"tone": {"amp": 0}, "n": 4 * D})
    ratio = [np.abs(held["L"][(k + 1) * D:(k + 1) * D + B]).max() / np.abs(held["L"][k * D:k * D + B]).max() for k in (1, 2)]
    check("asked for a feedback of 5 the delay gives 0.9: each repeat 0.9 of the last",
          all(abs(r - 0.9) < 1e-4 for r in ratio), str([round(r, 5) for r in ratio]))
    # A quiet flanger with its feedback asked for five: at 0.9 its loop gain
    # is at most 10, and the tone of 0.05 stays under 0.3. At five it would
    # have been at the output's clamp inside a tenth of a second.
    fl = run({"tone": {"freq": 220, "amp": 0.05, "chorusMix": 1, "chorusMs": 2, "chorusDepthMs": 1,
                       "chorusRate": 0.5, "chorusFeedback": 5}, "n": 88200})
    check("a flanger asked for a feedback of 5 is held at 0.9 and stays quiet over two seconds",
          np.abs(fl["L"]).max() < 0.3 and np.isfinite(fl["L"]).all(), "loudest %.3f" % np.abs(fl["L"]).max())
    dests = p.evaluate("() => [...MOD_DESTS.keys()]")
    timeish = [d for d in dests if any(w in d.lower() for w in ("delay", "feedback", "chorus", "echo"))]
    check("no delay, chorus or feedback is a modulation destination (S4)", not timeish and len(dests) > 10, str(timeish))

    print("\n--- a new time glides ---")
    # 100 ms to 133 ms under a steady tone: 1455 samples more, 7.26 cycles
    # of 220 Hz, so a jump would land a quarter-cycle away mid-wave.
    tone = {"freq": 220, "interval": 0, "amp": 0.4, "delayMix": 1, "delayFeedback": 0, "delayMs": 100}
    gl = run({"tone": tone, "n": 13230}, {"tone": {"delayMs": 133}, "n": 8820})
    step = np.abs(np.diff(gl["L"][13230 - 2000:13230 + 4000]))
    steady = np.abs(np.diff(gl["L"][9000:13000])).max()
    print("    largest step between samples: %.4f, where it is steady %.4f" % (step.max(), steady))
    check("the read position glides: no step bigger than one and a half times the steady tone's",
          step.max() < 1.5 * steady, "%.4f against %.4f" % (step.max(), steady))
    settled = run({"tone": tone, "n": 13230}, {"tone": {"delayMs": 133}, "n": 30000},
                  {"tone": {"amp": 0}, "n": 7000})
    tail = settled["L"][43230:]
    # After the tone stops, the echo is the tone 133 ms ago: silent from
    # 5865 samples on, not 4410.
    check("and arrives at the new time", np.abs(tail[4500:5800]).max() > 0.3 and np.abs(tail[5900:]).max() < 1e-6,
          "%.3f, then %.2e" % (np.abs(tail[4500:5800]).max(), np.abs(tail[5900:]).max()))

    print("\n--- the chorus ---")
    # 20 Hz and 0.5 ms: a phase modulation of 220 Hz with index
    # 2 pi 220 0.0005 = 0.691. The wet half's sidebands are J1 of that,
    # halved by the mix; the dry half has none.
    beta = 2 * math.pi * 220 * 0.0005
    ch = run({"tone": {"freq": 220, "interval": 0, "amp": 0.5, "chorusMix": 1, "chorusRate": 20,
                       "chorusDepthMs": 0.5, "chorusMs": 10}, "n": 48510})
    dry = run({"tone": {"freq": 220, "interval": 0, "amp": 0.5}, "n": 48510})
    spec, hz = spectrum(ch["L"][4410:])
    ref, _ = spectrum(dry["L"][4410:])
    carrier = level_at(ref, hz, 220)
    side = [level_at(spec, hz, f) / carrier for f in (200, 240)]
    second = [level_at(spec, hz, f) / carrier for f in (180, 260)]
    stray = [level_at(spec, hz, f) / carrier for f in (190, 250)]
    want1, want2 = bessel_j(1, beta) / 2, bessel_j(2, beta) / 2
    print("    first sidebands %s, want %.4f; second %s, want %.4f; between %s"
          % ([round(v, 4) for v in side], want1, [round(v, 4) for v in second], want2, [round(v, 5) for v in stray]))
    check("sidebands at 220 +- 20 Hz the size J1(0.691)/2 says, and +- 40 as J2 does, within 2 per cent",
          all(abs(v - want1) < 0.02 * want1 for v in side) and all(abs(v - want2) < 0.02 * want2 for v in second),
          "%s, %s" % ([round(v, 4) for v in side], [round(v, 4) for v in second]))
    check("and nothing between them", max(stray) < 1e-3, str([round(v, 5) for v in stray]))

    # One signal in both channels. The taps move in quadrature, so the two
    # channels' delays differ except where sine and cosine cross.
    quad = run({"tone": {"freq": 220, "interval": 0, "phase": 0, "amp": 0.5, "chorusMix": 1, "chorusRate": 2,
                         "chorusDepthMs": 3, "chorusMs": 12}, "n": 44100})
    flat = run({"tone": {"freq": 220, "interval": 0, "phase": 0, "amp": 0.5, "chorusMix": 1, "chorusRate": 2,
                         "chorusDepthMs": 0, "chorusMs": 12}, "n": 44100})
    apart = np.abs(quad["L"] - quad["R"])[2000:]
    # Apart by how much, second by second: the delays differ by
    # depth (sin - cos), which is nought twice a cycle of the rate and
    # depth root 2 in between. Window by window, the loudest difference
    # should swing from near nothing to near the whole wet half.
    # In 5 ms windows: in 50 the delays had moved 1.3 ms apart either side
    # of where they cross, and no window was ever near nought.
    win = [apart[i:i + 221].max() for i in range(0, len(apart) - 221, 110)]
    print("    L - R in 5 ms windows: least %.3f, most %.3f; with the depth at nought %.2e"
          % (min(win), max(win), np.abs(flat["L"] - flat["R"]).max()))
    check("a diagonal comes out of the chorus with its channels apart, and the gap swings with the rate",
          max(win) > 0.3 and min(win) < 0.1, "%.3f to %.3f" % (min(win), max(win)))
    check("and with the depth at nought the two taps are one: the channels are identical",
          np.abs(flat["L"] - flat["R"]).max() < 1e-7, "")

    print("\n--- once, and to every pair ---")
    solo = run({"tone": {"freq": 220, "interval": 7, "delayMix": 0.5, "delayMs": 30, "chorusMix": 0.5}, "n": 8820})
    check("outside poly what is heard is exactly what is drawn - the echo is not added twice",
          np.array_equal(solo["HL"], solo["L"]) and np.array_equal(solo["HR"], solo["R"]), "")
    # In poly, with no feedback, each pair is its own dry signal plus a copy
    # 50 ms late. Every pair's dry is known from the same run with the delay
    # off, so the delayed run can be read exactly.
    v = [{"note": 57, "freq": 220, "velocity": 0.5, "role": "x"}, {"note": 64, "freq": 329.63, "velocity": 0.5, "role": "y"}]
    vb = {"shape": "sine", "amp": 0.4, "voices": [{"note": 69, "freq": 440, "velocity": 0.5, "role": "xy"}]}
    wet = run({"tone": {"voices": v, "delayMix": 1, "delayMs": 50, "delayFeedback": 0}, "toneB": vb, "n": 8820})
    dry = run({"tone": {"voices": v}, "toneB": vb, "n": 8820})
    d = 2205
    errs = {k: float(np.abs(wet[k][d:] - (dry[k][d:] + dry[k][:-d])).max()) for k in ("L", "R", "HL", "HR", "BL", "BR")}
    moved = {k: float(np.abs(dry[k][:-d]).max()) for k in ("L", "HL", "BL")}
    print("    worst error against dry + dry 50 ms late: %s" % {k: "%.1e" % v2 for k, v2 in errs.items()})
    check("in poly layer A's picture, layer B's and the heard pair each carry their own echo",
          max(errs.values()) < 1e-6 and min(moved.values()) > 0.1, str(errs))
    check("and the heard pair is its own there, not the picture's",
          not np.array_equal(wet["HL"], wet["L"]), "")

    print("\n--- the tempo, the panel and setup codes ---")
    page = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const set = (id, v, kind) => { el[id].value = String(v); el[id].dispatchEvent(new Event(kind)); };
      setView('bench'); setBenchTab('effects');
      const shown = el.timeGroup.offsetHeight > 0;
      setTempo(120); await wait(30);
      set('delaySync', '1/4', 'change');
      const quarter = [genSettings().delayMs, el.delayMs.disabled, el.delayMsValue.textContent];
      set('delaySync', '1/8d', 'change');
      const dotted = genSettings().delayMs;
      setTempo(100); await wait(300);
      const followed = [genSettings().delayMs, el.delayMsValue.textContent];
      set('delaySync', '', 'change');
      set('delayMs', 250, 'input');
      const free = [genSettings().delayMs, el.delayMs.disabled];
      set('delayMix', 40, 'input'); set('delayFeedback', 60, 'input');
      el.delayPingPong.checked = true; el.delayPingPong.dispatchEvent(new Event('change'));
      set('chorusMix', 30, 'input'); set('chorusRate', 150, 'input'); set('chorusDepth', 25, 'input');
      set('chorusTime', 80, 'input'); set('chorusFeedback', 45, 'input');
      const g = genSettings();
      const panel = [g.delayMix, g.delayFeedback, g.delayPingPong, g.chorusMix, g.chorusRate, g.chorusDepthMs,
                     g.chorusMs, g.chorusFeedback];
      const code = snapshot();
      restore({}); await wait(30);
      const g0 = genSettings();
      const old = [g0.delayMix, g0.chorusMix, g0.delayMs, g0.delayPingPong, el.delaySync.value];
      restore(code); await wait(30);
      const g1 = genSettings();
      const back = [g1.delayMix, g1.delayMs, g1.delayFeedback, g1.delayPingPong, g1.chorusMix, g1.chorusRate,
                    g1.chorusDepthMs, g1.chorusMs, g1.chorusFeedback];
      // A code carries its tempo, 120 unless it says: a quarter triplet at
      // that is 333 ms. (An eighth was tried first and read 250, the free
      // time left by the code before - right, and unable to tell.)
      restore({ delaySync: '1/4t', delayMix: 20 }); await wait(30);
      const synced = genSettings().delayMs;
      restore({}); setTempo(120); await wait(30);
      return { shown, quarter, dotted, followed, free, panel, old, back, synced };
    }""")
    print("    %s" % page)
    check("a quarter at 120 BPM is 500 ms, the slider standing aside for it",
          page["quarter"] == [500, True, "500 ms"], str(page["quarter"]))
    check("a dotted eighth is 375, and at 100 BPM the delay follows the tempo to 450",
          abs(page["dotted"] - 375) < 1e-9 and abs(page["followed"][0] - 450) < 1e-9 and page["followed"][1] == "450 ms",
          "%s, %s" % (page["dotted"], page["followed"]))
    check("free, the slider's time", page["free"] == [250, False], str(page["free"]))
    check("the section is on the Effects tab and every control reaches the generator in its own units",
          page["shown"] and page["panel"] == [0.4, 0.6, True, 0.3, 1.5, 2.5, 8, 0.45], str(page["panel"]))
    check("a setup code carries it all back", page["back"] == [0.4, 250, 0.6, True, 0.3, 1.5, 2.5, 8, 0.45], str(page["back"]))
    check("a code from before has both off", page["old"] == [0, 0, 375, False, ""], str(page["old"]))
    check("and a code with a note value takes the tempo's time: a quarter triplet at 120 BPM is 333 ms",
          abs(page["synced"] - 1000 / 3) < 1e-9, str(page["synced"]))

    def search(q):
        p.evaluate("(q) => { el.benchSearch.value = q; el.benchSearch.dispatchEvent(new Event('input')); }", q)
        return p.evaluate("""() => Array.from(el.benchResults.querySelectorAll('button'))
          .map((b) => [b.firstChild.textContent, b.querySelector('.crumb').textContent])""")
    found = search("flanger")
    check("flanger finds the chorus", any(c == "Delay and chorus" for _, c in found), str(found[:3]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the echoes land where they should, and stop")
