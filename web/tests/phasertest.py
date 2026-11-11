"""The phaser (P8e): four all-passes a channel, swept in quadrature, on the pair.

What would go wrong, and what is checked for it:

- the all-passes not being what they say: with the sweep held still (range
  nought) and no resonance, the wet half is read back out of the mix and its
  phase at three frequencies compared with four first-order all-passes'
  formula, -2 atan(tan(pi f / rate) / tan(pi fc / rate)) each. Its nulls are
  the same formula for two stages and for six;
- the effect not acting on the figure: a diagonal line - one signal in both
  channels, the fixture a rotation or a quadrature pair cannot be, since a
  phaser alike on both channels leaves a line a line - must come out with
  its channels apart, and come back together, identical, with the range at
  nought, where both channels have the same all-passes. That null is the
  design's own reason for the quadrature;
- something running at nought: the amount at nought, with the other three at
  their most, is the generator without a phaser to the bit; a hundredth is
  not;
- a resonance that runs away: asked for five, it is 0.75, to the bit, and a
  sine at the notch-free top of the response stays under the loop's own
  bound, (1 + 1 / (1 - 0.75)) / 2 of what goes in;
- what a phaser must not add: a sine in gives that sine and its sweep's
  sidebands, nothing a harmonic away (the drive, at the same depth of
  effect, is the null: it puts harmonics there); and after a note the
  resonance rings and then falls silent. That the silence is reached by the
  flush rather than by decaying through the denormals is parity's to check,
  in doubles: this page's output is float32, which rounds a ring under
  1e-45 to nought flushed or not, and the mutation pass showed this file's
  version of the check passing with the flush taken out;
- a routing on its amount: from nought it runs the phaser as the knob does,
  sample for sample, and without the routing nought is nought;
- layer B's own: with B's own effects B's phaser bends B's pair only and A's
  is untouched; without B's own, B's setting is not read;
- the picture stage steering it: Memory pushes the amount;
- the panel, setup codes in and out with B's own, and the site's compiled
  instrument opening a line on the screen, not only the page's brain.
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


CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_SLOTS, [still(), still()]);
  core.set('shape', 'sine'); core.set('amp', 0.5);
  const out = { L: [], R: [], HL: [], HR: [], BL: [], BR: [] };
  for (const step of setup.steps) {
    for (const k in step.tone || {}) core.set(k, step.tone[k]);
    for (const k in step.toneB || {}) core.set(k, step.toneB[k], 1);
    if (step.routes) core.setRoutes(step.routes);
    const n = step.n, L = new Float32Array(n), R = new Float32Array(n);
    const HL = new Float32Array(n), HR = new Float32Array(n), BL = new Float32Array(n), BR = new Float32Array(n);
    core.block(L, R, n, HL, HR, BL, BR);
    for (const [k, a] of [['L', L], ['R', R], ['HL', HL], ['HR', HR], ['BL', BL], ['BR', BR]])
      for (let i = 0; i < n; i++) out[k].push(a[i]);
  }
  return out;
}"""


def phase_at(x, f):
    i = np.arange(len(x))
    s, c = np.sin(2 * np.pi * f * i / RATE), np.cos(2 * np.pi * f * i / RATE)
    return math.atan2(float(np.dot(x, c)), float(np.dot(x, s)))


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def allpass_phase(f, fc, stages):
    return stages * -2 * math.atan(math.tan(math.pi * f / RATE) / math.tan(math.pi * fc / RATE))


def spectrum(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    i = np.arange(n)
    w = BH[0] - BH[1] * np.cos(2 * np.pi * i / n) + BH[2] * np.cos(4 * np.pi * i / n) - BH[3] * np.cos(6 * np.pi * i / n)
    return np.abs(np.fft.rfft(x * w)), np.fft.rfftfreq(n, 1 / RATE)


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text) if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    def run(*steps):
        out = p.evaluate(CORE, {"steps": list(steps)})
        return {k: np.asarray(v, dtype=float) for k, v in out.items()}

    # A diagonal: the same sine in both channels.
    LINE = {"freq": 220, "interval": 0, "phase": 0}

    print("\n--- the all-passes against their formula ---")
    # Range nought holds both channels' all-passes at 700 Hz. The amount at
    # one is half dry and half wet, so the wet is twice the mix less the dry.
    rows, worst, worst2, worst6 = [], 0, 0, 0
    for f in (150, 700, 3000):
        tone = dict(LINE, freq=f)
        dry = run({"tone": tone, "n": 30000})
        wet = run({"tone": dict(tone, phaserMix=1, phaserDepth=0, phaserFeedback=0, phaserRate=0.3), "n": 30000})
        w = 2 * wet["L"][10000:] - dry["L"][10000:]
        got = wrap(phase_at(w, f) - phase_at(dry["L"][10000:], f))
        gain = float(np.sqrt(np.mean(w ** 2)) / np.sqrt(np.mean(dry["L"][10000:] ** 2)))
        want = wrap(allpass_phase(f, 700, 4))
        worst = max(worst, abs(wrap(got - want)))
        worst2 = max(worst2, abs(wrap(got - wrap(allpass_phase(f, 700, 2)))))
        worst6 = max(worst6, abs(wrap(got - wrap(allpass_phase(f, 700, 6)))))
        rows.append((f, round(math.degrees(got), 2), round(math.degrees(want), 2), round(gain, 5)))
    print("    (Hz, measured, formula, wet gain): %s" % rows)
    check("four all-passes at 700 Hz turn 150, 700 and 3000 Hz by the formula's phase, at unity gain",
          worst < 1e-3 and all(abs(r[3] - 1) < 1e-3 for r in rows), "worst %.2e rad" % worst)
    check("and the formula for two stages, or for six, does not fit them (the null)",
          worst2 > 0.3 and worst6 > 0.3, "%.2f, %.2f rad" % (worst2, worst6))

    print("\n--- a line opens into a loop ---")
    swept = run({"tone": dict(LINE, phaserMix=1, phaserDepth=0.8, phaserRate=2, phaserFeedback=0.3), "n": 44100})
    flat = run({"tone": dict(LINE, phaserMix=1, phaserDepth=0, phaserRate=2, phaserFeedback=0.3), "n": 44100})
    plain = run({"tone": LINE, "n": 44100})
    win = []
    for k in range(4410, 44100 - 2205, 2205):
        l, r = swept["L"][k:k + 2205], swept["R"][k:k + 2205]
        win.append(float(np.dot(l, r) / math.sqrt(np.dot(l, l) * np.dot(r, r))))
    print("    the line's correlation across windows, swept: %.3f to %.3f" % (min(win), max(win)))
    check("the fixture is a line: the generator's two channels identical",
          np.array_equal(plain["L"], plain["R"]) and np.abs(plain["L"]).max() > 0.3, "")
    check("swept in quadrature the line opens: its channels part, by an amount that comes and goes",
          min(win) < 0.6 and max(win) > 0.9, "%.3f to %.3f" % (min(win), max(win)))
    check("and with the range at nought, the same all-passes on both, it stays a line to the bit (the design's null)",
          np.array_equal(flat["L"], flat["R"]) and np.abs(flat["L"] - plain["L"]).max() > 0.05, "")

    print("\n--- nought is nought ---")
    most = dict(LINE, interval=7, phaserMix=0, phaserDepth=1, phaserRate=5, phaserFeedback=0.75)
    off = run({"tone": most, "n": 8820})
    base = run({"tone": dict(LINE, interval=7), "n": 8820})
    tiny = run({"tone": dict(most, phaserMix=0.01), "n": 8820})
    check("the amount at nought, everything else at its most, is the generator without a phaser, to the bit",
          all(np.array_equal(off[k], base[k]) for k in ("L", "R", "HL", "HR")), "")
    check("and a hundredth is not (the null)", np.abs(tiny["L"] - base["L"]).max() > 1e-4,
          "%.2e" % np.abs(tiny["L"] - base["L"]).max())

    print("\n--- the resonance is held ---")
    hot = dict(LINE, freq=700, phaserMix=1, phaserDepth=0.4, phaserRate=0.7)
    five = run({"tone": dict(hot, phaserFeedback=5), "n": 44100})
    top = run({"tone": dict(hot, phaserFeedback=0.75), "n": 44100})
    less = run({"tone": dict(hot, phaserFeedback=0.7), "n": 44100})
    dry = run({"tone": dict(hot, phaserMix=0), "n": 44100})
    bound = (1 + 1 / (1 - 0.75)) / 2 * np.abs(dry["L"]).max()
    peak = float(np.abs(five["L"]).max())
    check("asked for a resonance of 5 it is 0.75, to the bit, and 0.7 is not that",
          np.array_equal(five["L"], top["L"]) and not np.array_equal(less["L"], top["L"]), "")
    check("and at 0.75 the pair stays finite and inside the loop's own bound, (1 + 4) / 2 of what goes in",
          bool(np.all(np.isfinite(five["L"]))) and peak <= bound + 1e-9 and peak > np.abs(dry["L"]).max(),
          "peak %.3f, bound %.3f, dry %.3f" % (peak, bound, np.abs(dry["L"]).max()))

    print("\n--- nothing added, and a silence ends ---")
    sweepy = dict(LINE, freq=1000, phaserMix=1, phaserDepth=1, phaserRate=0.3, phaserFeedback=0.5)
    ph = run({"tone": sweepy, "n": 65536})
    drv = run({"tone": dict(LINE, freq=1000, drive=0.5), "n": 65536})
    def stray(x):
        spec, hz = spectrum(x[-32768:])
        near = np.abs(hz - 1000) < 60
        return 20 * math.log10(spec[~near & (hz > 30)].max() / spec[near].max())
    s_ph, s_drv = stray(ph["L"]), stray(drv["L"])
    print("    loudest anything 60 Hz or more from the sine: phased %.1f dB, driven %.1f dB" % (s_ph, s_drv))
    check("a sine through the phaser at full range comes out with nothing a harmonic away, 80 dB down or more",
          s_ph < -80, "%.1f dB" % s_ph)
    check("and the same check finds the drive's harmonics (the null)", s_drv > -60, "%.1f dB" % s_drv)
    # The note ends in one sample: the amplitude routed to nought, which rides
    # on the Level unsmoothed and only ever ducks. This put the Level to
    # nought until the Level glided (11 Nov, 20 ms a sample at a time); then
    # the first 200 samples after it were the sine itself at about 0.5, read
    # 0.891 for the ring's 0.645, and would have passed with no phaser at all.
    stop = {"held": -1, "heldB": -1, "slot": p.evaluate("() => MOD_DESTS.get('gen.amp').slot"),
            "amount": 1, "amountB": 1, "unipolar": True}
    tail = run({"tone": dict(sweepy, phaserFeedback=0.75), "n": 4410}, {"routes": [stop], "n": 44100 * 3})
    t = tail["L"][4410:]
    rang = float(np.abs(t[:200]).max())
    last = np.nonzero(t)[0]
    ends = int(last[-1]) if len(last) else -1
    check("after the note the resonance rings, then the pair falls silent",
          rang > 1e-3 and 0 < ends < len(t) - 44100 and np.all(t[ends + 1:] == 0),
          "rings %.3f, last non-zero sample %d of %d" % (rang, ends, len(t)))

    print("\n--- a routing on its amount ---")
    slot = p.evaluate("() => PHASER_SLOT")
    held = [{"held": 1, "slot": slot, "amount": 1, "unipolar": False}]
    fig = dict(LINE, interval=7, phaserRate=3, phaserDepth=0.7, phaserFeedback=0.4)
    static = run({"tone": dict(fig, phaserMix=0.5), "n": 8820})
    routed = run({"tone": dict(fig, phaserMix=0), "routes": held, "n": 8820})
    unrouted = run({"tone": dict(fig, phaserMix=0), "n": 8820})
    gap = float(np.abs(routed["L"] - static["L"]).max())
    check("held at full from nought it is the knob at a half, sample for sample, and unrouted nought is not that",
          gap < 1e-6 and np.abs(unrouted["L"] - static["L"]).max() > 0.01,
          "%.2e; unrouted %.3f" % (gap, np.abs(unrouted["L"] - static["L"]).max()))

    print("\n--- layer B's own ---")
    v = [{"note": 57, "freq": 220, "velocity": 0.5, "role": "x"}, {"note": 64, "freq": 329.63, "velocity": 0.5, "role": "y"}]
    vb = {"shape": "sine", "amp": 0.4, "voices": [{"note": 69, "freq": 440, "velocity": 0.5, "role": "xy"}]}
    # B's own phaser is its bit of timeOwn since G6 (1), where planeOwn gave B its plane and every effect at once.
    own = run({"tone": {"voices": v}, "toneB": dict(vb, timeOwn=1, phaserMix=0.9, phaserRate=4, phaserDepth=0.8),
               "n": 8820})
    dryb = run({"tone": {"voices": v}, "toneB": dict(vb, timeOwn=1), "n": 8820})
    shared = run({"tone": {"voices": v}, "toneB": dict(vb, timeOwn=0, phaserMix=0.9, phaserRate=4, phaserDepth=0.8),
                  "n": 8820})
    check("with B's own effects B's phaser bends B's pair, and A's is untouched to the bit",
          np.abs(own["BL"] - dryb["BL"]).max() > 0.05 and np.array_equal(own["L"], dryb["L"]),
          "B moved %.3f" % np.abs(own["BL"] - dryb["BL"]).max())
    check("and without B's own, B's setting is not read: B is as dry as A",
          np.array_equal(shared["BL"], dryb["BL"]), "")

    print("\n--- the picture stage, the panel and setup codes ---")
    stage = p.evaluate("() => STAGE_BUNDLES.filter(([s, d]) => d === 'gen.phaser')")
    check("the picture's Memory pushes the phaser's amount", stage == [["stage.memory", "gen.phaser", 0.5]], str(stage))
    page = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const set = (id, v) => { el[id].value = String(v); el[id].dispatchEvent(new Event('input')); };
      setView('bench'); setBenchTab('space');
      // In the rack's Phaser module since F5, where it shared the delay's section.
      const module = el.phaserMix.closest('.fx-module');
      const shown = !!module && module.dataset.fx === 'phaser' && module.closest('.menu-group') === document.getElementById('rackGroup')
        && module.offsetHeight > 0;
      set('phaserMix', 70); set('phaserRate', 120); set('phaserDepth', 40); set('phaserFeedback', 90);
      const after = { phaser: echo.phaser, rate: echo.phRate, depth: echo.phDepth, fb: echo.phFeedback,
                      reading: el.phaserMixValue.textContent, range: el.phaserDepthValue.textContent };
      const code = encodeSetup(snapshot());
      const decoded = decodeSetup(code);
      set('phaserMix', 0); set('phaserRate', 30);
      restore(decodeSetup(code)); await wait(100);
      const back = { phaser: echo.phaser, rate: echo.phRate, depth: echo.phDepth, fb: echo.phFeedback };
      // A code asking past the knob's top is held at it, as the knob is.
      restore(Object.assign({}, decoded, { phaserFeedback: 90 })); await wait(50);
      const over = echo.phFeedback;
      const old = Object.assign({}, decoded); delete old.phaserMix; delete old.phaserRate; delete old.phaserDepth;
      delete old.phaserFeedback;
      restore(old); await wait(100);
      const older = { phaser: echo.phaser, rate: echo.phRate };
      return { shown, after, fields: [decoded.phaserMix, decoded.phaserRate, decoded.phaserDepth, decoded.phaserFeedback],
               back, older, over };
    }""")
    print("    %s" % page)
    check("the phaser's knobs are on Space & Memory, in the rack's Phaser module, and write the echo's state",
          page["shown"] and page["after"] == {"phaser": 0.7, "rate": 1.2, "depth": 0.4, "fb": 0.75,
                                               "reading": "0.70", "range": "±1.0 oct"}, str(page["after"]))
    check("a setup code carries all four and gives them back; a code from before the phaser plays none",
          page["fields"] == [70, 120, 40, 75] and page["back"] == {"phaser": 0.7, "rate": 1.2, "depth": 0.4, "fb": 0.75}
          and page["older"] == {"phaser": 0, "rate": 0.3}, "%s %s %s" % (page["fields"], page["back"], page["older"]))
    check("and a code asking a resonance of 0.9 gets 0.75, the knob's top", page["over"] == 0.75, str(page["over"]))
    bown = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const code = encodeSetup(Object.assign(snapshot(), { midiMode: 'poly', layers: 'layer', bPlane: true,
        phaserMix: 20, bPhaserMix: 85, bPhaserRate: 250 }));
      restore(decodeSetup(code)); await wait(100);
      const d = decodeSetup(encodeSetup(snapshot()));
      return { a: echo.phaser, b: echoB.phaser, bRate: echoB.phRate, coded: [d.phaserMix, d.bPhaserMix, d.bPhaserRate] };
    }""")
    check("and B's own phaser goes in and out of a code beside A's",
          bown == {"a": 0.2, "b": 0.85, "bRate": 2.5, "coded": [20, 85, 250]}, str(bown))
    check("no page errors", not bad, "; ".join(bad[:3]))
    p.close()

    print("\n--- the site's instrument ---")
    # The compiled core, as the site opens: the line drawn on its screen opens.
    q = b.new_page(viewport={"width": 1400, "height": 900})
    errs = []
    q.on("pageerror", lambda e: errs.append(str(e)))
    q.goto(f"file://{ART}/scope.html"); q.wait_for_timeout(2500)
    if q.locator("#helpClose").is_visible(): q.locator("#helpClose").click()
    corr = """() => { const [l, r] = state.source.getLatestWindow(4096); let sl = 0, sr = 0, slr = 0;
      for (let i = 0; i < l.length; i++) { sl += l[i] * l[i]; sr += r[i] * r[i]; slr += l[i] * r[i]; }
      return { corr: slr / Math.sqrt(sl * sr + 1e-30), kind: state.source.kind }; }"""
    # Under a note held in Mono, where a lone note is the line the menus set
    # (in Poly it is a ring): the site waits for a note since 10 Nov.
    q.evaluate("""() => { const set = (id, v) => { el[id].value = String(v); el[id].dispatchEvent(new Event('input')); };
      el.midiMono.click(); midiNoteOn(57, 127);
      set('interval', 0); set('phase', 0); set('pictureAmount', 0); }""")
    q.wait_for_timeout(800)
    before = q.evaluate(corr)
    q.evaluate("() => { el.phaserMix.value = '100'; el.phaserMix.dispatchEvent(new Event('input')); }")
    q.wait_for_timeout(1500)
    lows = []
    for _ in range(6):
        lows.append(q.evaluate(corr)["corr"]); q.wait_for_timeout(250)
    print("    the site's %s: a line at %.4f, phased %s" % (before["kind"], before["corr"], [round(c, 3) for c in lows]))
    check("on the site's compiled instrument the line opens too",
          before["kind"] == "host" and before["corr"] > 0.99 and min(lows) < 0.8, "")
    check("no errors on the site's page", not errs, "; ".join(errs[:3]))
    b.close()

print("\nPHASER " + ("PASS" if not fails else "FAIL: " + ", ".join(fails)))
sys.exit(1 if fails else 0)
