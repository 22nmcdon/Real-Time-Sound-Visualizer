"""The delay's Tone, Low cut, Width and Wow (F5c).

What would go wrong, and what is checked for it:

- a tone or a cut that is not the one-pole it says, or is outside the loop:
  a burst goes in and then silence, so the repeats can be read alone, and
  each pass round the loop must lose what the filter's gain at the burst's
  frequency says - the ratio of one repeat to the one before is the feedback
  times that gain. The null is the same formula with the filter open, which
  must not fit; and the tone must leave a low burst nearly alone, the cut a
  high one, or either would be a volume knob;
- width not acting, or acting in the loop: with nought the repeats are on
  the diagonal, left and right equal to the bit, while the live burst before
  them was not; at two their side is twice what it is at one, which is the
  null for nought;
- wow as anything but a slow swing of the time: a steady tone's repeat must
  move in pitch by the law's own amount - half a hertz, two milliseconds
  either side, so 2 pi 0.5 0.002 of the pitch - and not at all at nought;
- the controls at rest changing anything: the four at their defaults are the
  delay without them to the bit, against an old build in parity; here, the
  page's controls moved and put back leave the generator's fields where
  they started;
- the knobs not reaching the generator, or reading wrongly: each is moved as
  a hand moves it and the generator's own field read, with its reading;
- codes: the four go out and come back, B's own with bPlane, an old code
  without them is the old delay, and a width past its range is held to it.
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

# The generator core alone, steps in order on one core: a burst, then the
# amplitude at nought and the repeats coming round.
CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_SLOTS, [still(), still()]);
  core.set('shape', 'sine'); core.set('amp', 0.5);
  const out = { L: [], R: [] };
  for (const step of setup.steps) {
    for (const k in step.tone || {}) core.set(k, step.tone[k]);
    if (step.routes) core.setRoutes(step.routes);
    const n = step.n, L = new Float32Array(n), R = new Float32Array(n);
    const HL = new Float32Array(n), HR = new Float32Array(n), BL = new Float32Array(n), BR = new Float32Array(n);
    core.block(L, R, n, HL, HR, BL, BR);
    for (let i = 0; i < n; i++) { out.L.push(L[i]); out.R.push(R[i]); }
  }
  return out;
}"""

def onepole_low(f, fc):
    a = 1 - math.exp(-2 * math.pi * fc / RATE)
    z = complex(math.cos(2 * math.pi * f / RATE), -math.sin(2 * math.pi * f / RATE))
    return abs(a / (1 - (1 - a) * z))

def onepole_high(f, fc):
    a = 1 - math.exp(-2 * math.pi * fc / RATE)
    z = complex(math.cos(2 * math.pi * f / RATE), -math.sin(2 * math.pi * f / RATE))
    return abs(1 - a / (1 - (1 - a) * z))

def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, dtype=float) ** 2)))

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    def run(*steps):
        out = p.evaluate(CORE, {"steps": list(steps)})
        return {k: np.asarray(v, dtype=float) for k, v in out.items()}

    # A burst of 100 ms, then 600 ms of silence: the repeats at 150 ms come
    # round four times, each read in the middle of its 100 ms, away from the
    # edges where a filter's own rise and fall would be counted.
    MS = 150
    def repeats(freq, fb, extra, routes=None):
        base = dict(freq=freq, interval=0, phase=90, delayMix=1, delayMs=MS, delayFeedback=fb)
        first = {"tone": dict(base, **extra), "n": int(0.1 * RATE)}
        if routes: first["routes"] = routes
        out = run(first, {"tone": {"amp": 0}, "n": int(0.6 * RATE)})
        L = out["L"]
        level = []
        for k in range(1, 4):
            at = int(k * MS / 1000 * RATE)   # the k-th repeat of the burst starts k times 150 ms in
            level.append(rms(L[at + 1000: at + int(0.1 * RATE) - 1000]))
        return out, level

    print("\n--- Tone, in the loop ---")
    FB = 0.6
    tone_v = 0.3
    fc_tone = 500 * 40 ** tone_v
    _, open_ = repeats(5000, FB, {})
    _, dark = repeats(5000, FB, {"delayTone": tone_v})
    ratio = dark[2] / dark[1]
    want = FB * onepole_low(5000, fc_tone)
    check("each pass round the loop at a tone of 0.3 (%.0f Hz) loses a 5 kHz burst by the one-pole's gain" % fc_tone,
          abs(ratio - want) / want < 0.03, "repeat over repeat %.4f, feedback x gain %.4f" % (ratio, want))
    check("null: with the tone open each pass loses only the feedback, which the dark ratio is not",
          abs(open_[2] / open_[1] - FB) / FB < 0.02 and abs(ratio - FB) / FB > 0.3,
          "open %.4f" % (open_[2] / open_[1]))
    _, low_open = repeats(220, FB, {})
    _, low_dark = repeats(220, FB, {"delayTone": tone_v})
    check("and a 220 Hz burst through the same tone keeps almost all of itself, as the gain says",
          abs((low_dark[1] / low_dark[0]) - FB * onepole_low(220, fc_tone)) < 0.01 and low_dark[0] > 0.9 * low_open[0],
          "%.4f against %.4f" % (low_dark[1] / low_dark[0], FB * onepole_low(220, fc_tone)))

    print("\n--- Tone as a destination ---")
    # A source held at -0.8 on the tone, the knob open: half its travel either
    # way, so the tone is 0.6 and each pass loses that one-pole's gain.
    dts = p.evaluate("() => DELAY_TONE_SLOT")
    _, pushed = repeats(5000, FB, {}, [{"held": -0.8, "slot": dts, "amount": 1, "unipolar": False}])
    fc_push = 500 * 40 ** 0.6
    want = FB * onepole_low(5000, fc_push)
    check("pushed down by a routing, the open tone darkens each pass by the gain at 0.6 (%.0f Hz)" % fc_push,
          abs(pushed[2] / pushed[1] - want) / want < 0.03, "%.4f against %.4f" % (pushed[2] / pushed[1], want))
    check("null: the same run unrouted loses only the feedback", abs(open_[2] / open_[1] - FB) / FB < 0.02)
    # The push arriving after the tone has been worked out once: the burst
    # with nothing routed, the routing from the silence on, so every repeat
    # goes round after it. A tone reckoned once and kept (the cache never
    # asked again) still loses only the feedback here.
    late = run({"tone": dict(freq=5000, interval=0, phase=90, delayMix=1, delayMs=MS, delayFeedback=FB), "n": int(0.1 * RATE)},
               {"tone": {"amp": 0}, "n": int(0.6 * RATE),
                "routes": [{"held": -0.8, "slot": dts, "amount": 1, "unipolar": False}]})["L"]
    late_lv = [rms(late[int(k * MS / 1000 * RATE) + 1000: int(k * MS / 1000 * RATE) + int(0.1 * RATE) - 1000]) for k in (1, 2)]
    check("and a push that arrives after the first pass darkens the passes after it alike",
          abs(late_lv[1] / late_lv[0] - want) / want < 0.03, "%.4f against %.4f" % (late_lv[1] / late_lv[0], want))
    offered = p.evaluate("""() => ({ dest: !!MOD_DESTS.get('gen.delayTone'), slot: MOD_DESTS.get('gen.delayTone').slot === DELAY_TONE_SLOT,
      lfo: routingAllowed(MOD_SOURCES.get('lfo1'), MOD_DESTS.get('gen.delayTone')),
      env: routingAllowed(MOD_SOURCES.get('env.note'), MOD_DESTS.get('gen.delayTone')),
      row: !!document.querySelector('[data-mod-dest="gen.delayTone"] #delayTone'),
      reach: [MOD_DESTS.get('gen.delayTone').reach(100, -1), MOD_DESTS.get('gen.delayTone').reach(30, 0.5)] })""")
    check("the Tone knob takes the LFOs and the Envelope, its lane drawn by its law", offered == {
        "dest": True, "slot": True, "lfo": True, "env": True, "row": True, "reach": [50, 55]}, str(offered))
    none = p.evaluate("() => ['delayWidth', 'delayWow', 'delayLowCut', 'menvAtk'].filter((id) => document.querySelector('[data-mod-control=\"' + id + '\"]'))")
    check("and Width, Wow, Low cut and the Envelope's own times are left off the matrix", none == [], str(none))

    print("\n--- Low cut, in the loop ---")
    cut_v = 0.6
    fc_cut = 20 * 50 ** cut_v
    _, thin = repeats(150, FB, {"delayLowCut": cut_v})
    ratio = thin[2] / thin[1]
    want = FB * onepole_high(150, fc_cut)
    check("each pass at a low cut of 0.6 (%.0f Hz) loses a 150 Hz burst by the one-pole's gain" % fc_cut,
          abs(ratio - want) / want < 0.03, "repeat over repeat %.4f, feedback x gain %.4f" % (ratio, want))
    check("null: that is not the feedback alone", abs(ratio - FB) / FB > 0.3)
    _, hi = repeats(4000, FB, {"delayLowCut": cut_v})
    check("and a 4 kHz burst keeps almost all of itself", abs(hi[2] / hi[1] - FB * onepole_high(4000, fc_cut)) < 0.01,
          "%.4f" % (hi[2] / hi[1]))

    print("\n--- Width, on what is heard ---")
    # A fifth between the channels, so left and right differ.
    def wide(w):
        out = run({"tone": dict(freq=330, interval=7, phase=90, delayMix=1, delayMs=MS, delayFeedback=0.5, delayWidth=w),
                   "n": int(0.1 * RATE)}, {"tone": {"amp": 0}, "n": int(0.4 * RATE)})
        a, z = int(0.16 * RATE), int(0.24 * RATE)
        return out, out["L"][a:z] - out["R"][a:z], out["L"][:int(0.1 * RATE)] - out["R"][:int(0.1 * RATE)]
    _, side0, live0 = wide(0)
    _, side1, _ = wide(1)
    _, side2, _ = wide(2)
    check("at nought the repeats are on the diagonal, left and right equal, while the live burst was not",
          float(np.max(np.abs(side0))) < 1e-6 and rms(live0) > 0.05, "%.2g, live %.3f" % (float(np.max(np.abs(side0))), rms(live0)))
    check("at two their side is twice what it is at one", abs(rms(side2) / rms(side1) - 2) < 0.01,
          "%.4f" % (rms(side2) / rms(side1)))
    check("null: at one the repeats are not on the diagonal", rms(side1) > 0.02, "%.3f" % rms(side1))
    # Past its range, as only something writing the generator directly could
    # send (a code is held by the table first): five is two, the engine's own
    # limit, and not five.
    _, side5, _ = wide(5)
    check("a width of five given to the generator is held at two", float(np.max(np.abs(side5 - side2))) == 0,
          "%.2g" % float(np.max(np.abs(side5 - side2))))

    print("\n--- Wow, the time swung slowly ---")
    # Four seconds of 1 kHz and its repeat 1.9 s later with nothing fed back:
    # from 4 s the repeat is alone, for 1.8 s of it. That is less than the
    # wow's two-second period, so the swing is not max less min - the first
    # version read 0.9 s that way and found 5.4 Hz of a 6.3 Hz swing - but a
    # half-hertz sinusoid fitted to the pitch, whose amplitude is the swing.
    def wow(v):
        out = run({"tone": dict(freq=1000, interval=0, phase=90, delayMix=1, delayMs=1900, delayFeedback=0, delayWow=v),
                   "n": 4 * RATE}, {"tone": {"amp": 0}, "n": 2 * RATE})
        x = out["L"][int(4.05 * RATE): int(5.85 * RATE)]
        # The pitch between each pair of rising crossings, interpolated.
        s = np.signbit(x)
        up = np.where(s[:-1] & ~s[1:])[0]
        t = up + x[up] / (x[up] - x[up + 1])
        f = RATE / np.diff(t)
        mid = (t[:-1] + t[1:]) / 2 / RATE
        A = np.column_stack([np.ones_like(mid), np.sin(2 * np.pi * 0.5 * mid), np.cos(2 * np.pi * 0.5 * mid)])
        c, a_, b_ = np.linalg.lstsq(A, f, rcond=None)[0]
        return float(math.hypot(a_, b_)), float(c)
    swing0, mean0 = wow(0)
    swing1, mean1 = wow(1)
    want = 1000 * 2 * math.pi * 0.5 * 0.002
    check("at one a 1 kHz repeat swings in pitch by the law's own amount, 2 pi x 0.5 Hz x 2 ms of it (%.2f Hz)" % want,
          abs(swing1 - want) / want < 0.1, "%.2f Hz either side, about %.1f" % (swing1, mean1))
    check("null: at nought it holds its pitch", swing0 < 0.1 * want, "%.3f Hz" % swing0)

    print("\n--- the knobs reach the generator ---")
    knobs = p.evaluate("""() => {
      setView('bench'); setBenchTab('space'); openFx('delay', true);
      const field = (k) => genSettings()[k];
      const out = {};
      for (const [id, v, k] of [['delayTone', 30, 'delayTone'], ['delayLowCut', 60, 'delayLowCut'],
                                ['delayWidth', 40, 'delayWidth'], ['delayWow', 25, 'delayWow']]) {
        const before = field(k);
        setControl(id, v);
        out[id] = { before, after: field(k), reading: el[id + 'Value'].textContent };
      }
      const code = snapshot();
      for (const [id, v] of [['delayTone', 100], ['delayLowCut', 0], ['delayWidth', 100], ['delayWow', 0]]) setControl(id, v);
      out.rest = { tone: field('delayTone'), cut: field('delayLowCut'), width: field('delayWidth'), wow: field('delayWow'),
                   readings: ['delayTone', 'delayLowCut', 'delayWidth', 'delayWow'].map((id) => el[id + 'Value'].textContent) };
      out.code = [code.delayTone, code.delayLowCut, code.delayWidth, code.delayWow];
      return out;
    }""")
    check("Tone at 30 is 0.3 in the generator and reads its corner, 1.5 kHz",
          knobs["delayTone"]["before"] == 1 and knobs["delayTone"]["after"] == 0.3 and knobs["delayTone"]["reading"] == "1.5 kHz",
          str(knobs["delayTone"]))
    check("Low cut at 60 is 0.6 and reads 209 Hz",
          knobs["delayLowCut"]["before"] == 0 and knobs["delayLowCut"]["after"] == 0.6 and knobs["delayLowCut"]["reading"] == "209 Hz",
          str(knobs["delayLowCut"]))
    check("Width at 40 is 0.4 and reads 40%", knobs["delayWidth"]["after"] == 0.4 and knobs["delayWidth"]["reading"] == "40%",
          str(knobs["delayWidth"]))
    check("Wow at 25 is 0.25 and reads 0.25", knobs["delayWow"]["after"] == 0.25 and knobs["delayWow"]["reading"] == "0.25",
          str(knobs["delayWow"]))
    check("the code carries all four", knobs["code"] == [30, 60, 40, 25], str(knobs["code"]))
    check("and put back, the generator is at rest and the readings say open, off, 100% and off",
          knobs["rest"] == {"tone": 1, "cut": 0, "width": 1, "wow": 0, "readings": ["open", "off", "100%", "off"]}, str(knobs["rest"]))

    print("\n--- codes ---")
    codes = p.evaluate("""() => {
      const read = () => ({ a: [echo.tone, echo.lowCut, echo.width, echo.wow], gen: ['delayTone', 'delayLowCut', 'delayWidth', 'delayWow'].map((k) => genSettings()[k]) });
      restore(Object.assign(snapshot(), { delayTone: 20, delayLowCut: 70, delayWidth: 150, delayWow: 40 }));
      const set = read();
      restore(Object.assign(snapshot(), { delayWidth: 500, delayTone: -4 }));
      const held = read();
      const old = snapshot(); for (const k of ['delayTone', 'delayLowCut', 'delayWidth', 'delayWow']) delete old[k];
      restore(old);
      const was = read();
      // B's own, with its plane.
      restore(Object.assign(snapshot(), { layers: 'split', bPlane: true, delayTone: 80, bDelayTone: 10, bDelayWidth: 0, bDelayWow: 90 }));
      const own = { b: [echoB.tone, echoB.lowCut, echoB.width, echoB.wow], a: echo.tone,
                    genB: ['delayTone', 'delayWidth', 'delayWow'].map((k) => genSettings(1) && genSettings(1)[k]) };
      const code = snapshot();
      restore(Object.assign(snapshot(), { layers: 'off', bPlane: false }));
      return { set, held, was, own, codeB: [code.bDelayTone, code.bDelayLowCut, code.bDelayWidth, code.bDelayWow] };
    }""")
    check("a code's tone, cut, width and wow come back, into the generator", codes["set"]["a"] == [0.2, 0.7, 1.5, 0.4]
          and codes["set"]["gen"] == [0.2, 0.7, 1.5, 0.4], str(codes["set"]))
    check("a width past its range is held to it, and a tone below to nought", codes["held"]["a"][2] == 2 and codes["held"]["a"][0] == 0,
          str(codes["held"]))
    check("an old code without them is the delay it always was", codes["was"]["a"] == [1, 0, 1, 0], str(codes["was"]))
    check("B's own come back as B's, A's tone left as A's, and B's lacking one is A's",
          codes["own"]["b"] == [0.1, 0, 0, 0.9] and codes["own"]["a"] == 0.8, str(codes["own"]))
    check("and go out again as B's", codes["codeB"] == [10, 0, 0, 90], str(codes["codeB"]))
    b.close()

if bad:
    print("  FAIL  the page threw: " + "; ".join(bad[:3])); fails.append("pageerror")
print("\n%d failed" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
