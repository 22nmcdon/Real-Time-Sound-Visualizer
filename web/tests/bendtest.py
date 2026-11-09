"""The Bend (P6c step 1): a knob that bends the voice's wave at a chosen point
of its cycle, so the picture pinches or swells there and the sound
brightens.

It is the voice's FM at one-to-one with the modulator locked to the voice
and turned to `Bend at`, which is checked directly: at a centre of nought it
IS FM at ratio one. Everything else follows from that, the band-limiting
included, and each claim is checked against the way it would fail:

- nought changing anything: the bend switched on by a routing whose value
  is nought must be the plain wave to the last bit, dyad and chord - and, as
  its null, not with a value of 0.02;
- a bend that lands somewhere else: on a sine bent at a quarter cycle, the
  peak narrows and the trough widens, and at three quarters the other way
  round; a negative bend is the positive one half a cycle on;
- a bend that does not brighten: a sine's spectral centroid rises with it;
- a bend band-limited at the wrong frequency: on every sharp shape at a high
  note, what folds back is pinned against the same warp corrected at the
  note's own frequency and against no correction at all;
- chords and the dyad bent unlike the single voice, layer B's bend reaching
  A, and a routing that does not move it.

Every assertion has its null beside it: the same comparison fed the value
it must not accept, which has to go red.
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

def null(name, red, detail=""):
    """A check's null: the same test fed a value it must reject. `red` is
    whether it rejected it; a null that passes is a check that cannot fail."""
    check("null: " + name, red, detail)


def spectrum(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    i = np.arange(n)
    w = (BH[0] - BH[1] * np.cos(2 * np.pi * i / n)
         + BH[2] * np.cos(4 * np.pi * i / n) - BH[3] * np.cos(6 * np.pi * i / n))
    return np.abs(np.fft.rfft(x * w)) / np.sum(w) * 2, np.arange(n // 2 + 1) * RATE / n


def off_grid(x, f0, top=10000):
    """The loudest thing below `top` that is not a harmonic of f0, in dB
    under the loudest thing of all. A bend at one-to-one keeps every partial
    on the note's harmonics, so anything off them folded back."""
    spec, hz = spectrum(x)
    grid = np.zeros(len(spec), dtype=bool)
    grid[:6] = True
    k = 1
    while k * f0 < RATE / 2:
        grid |= np.abs(hz - k * f0) < 4 * RATE / len(x)
        k += 1
    return 20 * math.log10(max(spec[~grid & (hz < top)].max(), 1e-15) / spec.max())


def centroid(x):
    spec, hz = spectrum(x)
    keep = hz > 20                             # past DC: a bent sine has some
    return float(np.sum(spec[keep] * hz[keep]) / np.sum(spec[keep]))


def bessel_j1(x):
    return sum((-1) ** k * (x / 2) ** (2 * k + 1) / (math.factorial(k) * math.factorial(k + 1)) for k in range(30))


def widths(x):
    """How much of the time the wave spends near its top and near its
    bottom, each as a fraction: where a bend pinches, it is there less."""
    x = np.asarray(x, dtype=float)
    top, bottom = x.max(), x.min()
    span = top - bottom
    return float(np.mean(x > top - 0.1 * span)), float(np.mean(x < bottom + 0.1 * span))


CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('mode', 'wave'); core.set('amp', 0.5); core.set('interval', 0); core.set('phase', 0);
  for (const k in setup.tone) core.set(k, setup.tone[k]);
  for (const k in setup.toneB || {}) core.set(k, setup.toneB[k], 1);
  const slots = { fm: FM_SLOT, bend: BEND_SLOT, bendAt: BEND_AT_SLOT };
  if (setup.routes) core.setRoutes(setup.routes.map((r) => ({ held: r.held, heldB: r.held, slot: slots[r.to], amount: 1,
                                                               amountB: r.amountB === undefined ? 1 : r.amountB })));
  const n = setup.n, L = new Float32Array(n), R = new Float32Array(n);
  const HL = new Float32Array(n), HR = new Float32Array(n), BL = new Float32Array(n), BR = new Float32Array(n);
  core.block(L, R, n, HL, HR, BL, BR);
  const from = setup.skip || 0;
  return { L: Array.from(L.subarray(from)), R: Array.from(R.subarray(from)),
           HL: Array.from(HL.subarray(from)), BL: Array.from(BL.subarray(from)) };
}"""

# The same warp written out by hand with the page's own `waveAt`, asked
# about a step of the caller's choosing: the note's own (`f`), or none.
HAND = """({ shape, f, a, c, n, skip, step, amount }) => {
  const out = [];
  for (let i = skip; i < skip + n; i++) {
    const p = TWO_PI * f * i / 44100;
    const q = p + a * Math.sin(p - TWO_PI * c);
    out.push(0.5 * waveAt(shape, q % (2 * TWO_PI), step === 'note' ? f / 44100 : 0, undefined, amount));
  }
  return out;
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
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
    def diff(a, b): return float(np.abs(np.asarray(a) - np.asarray(b)).max())

    print("\n--- at nought, nothing changes ---")
    same, moved = [], []
    for shape in ("ramp", "harmonic", "square", "sine"):
        tone = {"shape": shape, "freq": 330, "interval": 7}
        plain = run(tone, n=8820, skip=0)
        through = run(tone, n=8820, skip=0, routes=[{"to": "bend", "held": 0}, {"to": "bendAt", "held": 0.3}])
        nudged = run(tone, n=8820, skip=0, routes=[{"to": "bend", "held": 0.02}])
        same.append(np.array_equal(plain["L"], through["L"]) and np.array_equal(plain["R"], through["R"]))
        moved.append(diff(plain["L"], nudged["L"]))
    print("    identical through the path: %s; bent by 0.02, moved by %s" % (same, [round(m, 5) for m in moved]))
    check("a bend of nought is the plain wave to the last bit, its centre moved and all, dyad and both channels",
          all(same), str(same))
    null("and the same comparison sees a bend of 0.02 of the travel", min(moved) > 1e-3, str(moved))
    v = [{"note": 57, "freq": 220, "velocity": 1, "role": "x"}, {"note": 64, "freq": 329.63, "velocity": 1, "role": "y"},
         {"note": 60, "freq": 261.63, "velocity": 1, "role": "u"}]
    cp = run({"shape": "ramp", "voices": v}, n=4410, skip=0)
    ct = run({"shape": "ramp", "voices": v}, n=4410, skip=0, routes=[{"to": "bend", "held": 0}])
    cn = run({"shape": "ramp", "voices": v}, n=4410, skip=0, routes=[{"to": "bend", "held": 0.02}])
    check("and so is a chord", np.array_equal(cp["L"], ct["L"]) and np.array_equal(cp["HL"], ct["HL"]))
    null("a chord bent by 0.02 is not", diff(cp["L"], cn["L"]) > 1e-3, "%.2e" % diff(cp["L"], cn["L"]))

    print("\n--- it is FM at one-to-one, turned ---")
    # At a centre of nought the bend's term is FM's at ratio one, term for
    # term, and the band-limiting is asked the same frequency: the sound is
    # the same to rounding, on a sine and on a saw.
    # Since 8 Nov the ramp's bend has its offset taken off by a 5 Hz one-pole
    # on the bend's own difference - the bent wave less the plain - which FM
    # has not got, so the blocker is run here by hand on FM's difference from
    # the plain ramp and FM is compared with that taken off. The sine's term
    # is nought at a centre of nought, so it is FM's as it was.
    def blocked(fm, plain):
        k = 1 - math.exp(-1 / ((1000 / (2 * math.pi * 5)) * RATE / 1000))
        out, dc = np.empty(len(fm)), 0.0
        for i in range(len(fm)):
            dc += k * ((fm[i] - plain[i]) - dc)
            out[i] = fm[i] - dc
        return out
    fmlike = {}
    for shape in ("sine", "ramp"):
        bent = run({"shape": shape, "freq": 440, "warp": 0.7, "warpAt": 0}, skip=0)["L"]
        fm = run({"shape": shape, "freq": 440, "fmIndex": 0.7, "modRatio": 1}, skip=0)["L"]
        if shape == "ramp": fm = blocked(fm, run({"shape": shape, "freq": 440}, skip=0)["L"])
        turned = run({"shape": shape, "freq": 440, "warp": 0.7, "warpAt": 0.1}, skip=0)["L"]
        fmlike[shape] = (diff(bent[4410:], fm[4410:]), diff(turned[4410:], fm[4410:]))
    print("    from FM at 1:1 with an index of 0.7: %s" % {k: "%.1e, turned %.2f" % v for k, v in fmlike.items()})
    check("bent 0.7 at nought is FM at ratio one with an index of 0.7, sine and saw, to float precision",
          all(v[0] < 1e-6 for v in fmlike.values()), str(fmlike))
    null("bent at a tenth of a cycle it is not FM's", all(v[1] > 0.05 for v in fmlike.values()), str(fmlike))

    print("\n--- it lands where Bend at says ---")
    plain = run({"shape": "sine", "freq": 441})["L"]
    at_top = run({"shape": "sine", "freq": 441, "warp": 0.6, "warpAt": 0.25})["L"]
    at_bottom = run({"shape": "sine", "freq": 441, "warp": 0.6, "warpAt": 0.75})["L"]
    w0, wt, wb = widths(plain), widths(at_top), widths(at_bottom)
    print("    time near the top and the bottom: plain %.3f %.3f; bent at 90 deg %.3f %.3f; at 270 deg %.3f %.3f"
          % (w0 + wt + wb))
    pinched_top = lambda w: w[0] < 0.8 * w0[0] and w[1] > 1.2 * w0[1]
    check("bent at a quarter cycle, a sine's peak narrows and its trough widens, each by a fifth or more",
          pinched_top(wt), "%s against %s" % (wt, w0))
    check("and bent at three quarters, the other way round", pinched_top((wb[1], wb[0])), "%s" % (wb,))
    null("the peak test does not pass the unbent sine", not pinched_top(w0))
    null("nor the sine bent at the other point", not pinched_top(wb))
    # Until 9 Nov this held what the bend cost: sin(p + a sin(p - c)) has a
    # mean of -J1(a) sin(c), and the bent sine sat that far off the middle.
    # It is taken off now, and "it sits on the middle" below holds that, with
    # the same warp by hand, uncorrected, as its null.
    neg = run({"shape": "sine", "freq": 441, "warp": -0.6, "warpAt": 0.75})["L"]
    check("a negative bend is the positive one half a cycle on", diff(neg, at_top) < 1e-6, "%.1e" % diff(neg, at_top))
    null("and not the positive one where it was", diff(neg, at_bottom) > 0.05, "%.3f" % diff(neg, at_bottom))
    # The figure, not only the wave: on a dyad a quarter-cycle apart (the
    # circle) each channel is bent at that point of its own cycle, so X and
    # Y are bent differently and the circle stops being one. Rotating or
    # speeding a circle leaves it a circle, so this cannot be passed by a
    # bend that only changed how fast the trace goes round.
    circ = {"shape": "sine", "freq": 220, "phase": math.pi / 2}
    def roundness(o):
        r = np.hypot(o["L"], o["R"])
        return float((r.max() - r.min()) / r.mean())
    rc, rb = roundness(run(circ)), roundness(run(dict(circ, warp=0.5)))
    print("    the circle's radius varies by %.4f plain and %.3f bent" % (rc, rb))
    check("bent, the dyad's circle is no longer a circle: its radius varies by a tenth or more",
          rb > 0.1 and rc < 1e-3, "%.4f against %.4f" % (rb, rc))
    null("the plain circle does not pass", not (rc > 0.1), "%.4f" % rc)

    print("\n--- it sits on the middle ---")
    # The offset a bend gives (8 Nov). A sine bent its most at a quarter cycle
    # sat J1(0.9), 0.41 of its amplitude, below the middle; the same warp by
    # hand, with no term, is the null. Read over whole cycles: 441 Hz is a
    # hundred samples a cycle.
    sdc = run({"shape": "sine", "freq": 441, "warp": 0.9, "warpAt": 0.25})["L"]
    hand = np.asarray(p.evaluate(HAND, {"shape": "sine", "f": 441, "a": 0.9, "c": 0.25, "n": 44100, "skip": 4410,
                                        "step": "none", "amount": 0}))
    m_core, m_hand = float(np.mean(sdc[:44100])), float(np.mean(hand))
    print("    a sine bent 0.9 at 90 deg: mean %.2e here, %.4f by hand with nothing taken off (J1 says %.4f)"
          % (m_core, m_hand, -0.5 * bessel_j1(0.9)))
    check("a sine bent its most at a quarter cycle sits on the middle", abs(m_core) < 1e-4, "%.2e" % m_core)
    null("by hand it sits J1(0.9) of its amplitude off, which the check would see",
         abs(m_hand + 0.5 * bessel_j1(0.9)) < 1e-3 and abs(m_hand) > 0.1, "%.4f" % m_hand)
    # A ramp, by the blocker: a second of it, its offset gone by the end, and
    # still there in the first cycle - the blocker's 32 ms, so automating the
    # bend on a saw is softened rather than undone.
    rdc = run({"shape": "ramp", "freq": 441, "warp": 0.9, "warpAt": 0.3}, n=44100, skip=0)["L"]
    first, last = float(np.mean(rdc[:100])), float(np.mean(rdc[-4410:]))
    check("a ramp bent its most has its offset in its first cycle and none a second on",
          abs(first) > 0.03 and abs(last) < 1e-3, "first cycle %.4f, the last tenth of a second %.2e" % (first, last))

    print("\n--- it brightens ---")
    cents = [centroid(run({"shape": "sine", "freq": 441, "warp": a})["L"]) for a in (0, 0.3, 0.6, 0.9)]
    print("    a 441 Hz sine's centroid at 0, 0.3, 0.6, 0.9: %s Hz" % [round(c) for c in cents])
    rising = lambda c: all(c[k + 1] > c[k] * 1.05 for k in range(len(c) - 1))
    check("a sine's centroid rises with the bend, by more than five per cent at each step", rising(cents), str(cents))
    null("the same test fails a bend that does nothing", not rising([cents[0]] * 4))
    neg_cent = centroid(run({"shape": "sine", "freq": 441, "warp": -0.6})["L"])
    check("and a negative bend brightens as much as a positive one", abs(neg_cent - cents[2]) < 1, "%.1f" % neg_cent)

    print("\n--- band-limited where the bend has taken it ---")
    # A sharp shape at a high note, bent the whole way: the wave runs at up
    # to 1.9 times the note, so a corner corrected at the note's own rate is
    # corrected too gently there. Measured against that and against none.
    floors = {}
    for shape, amount in (("ramp", 0), ("square", 0), ("pulse", 0.3), ("morph", 2.4), ("triangle", 0)):
        # Not 2205, a twentieth of the rate: there every alias folds onto a
        # harmonic, and the first run of this read -99 dB for the warp with
        # no correction at all.
        f = 2345.6
        ours = run({"shape": shape, "freq": f, "warp": 0.9, "warpAt": 0.25, "morph": amount, "width": amount or 0.25},
                   n=32768, skip=4410)["L"]
        note = p.evaluate(HAND, {"shape": shape, "f": f, "a": 0.9, "c": 0.25, "n": 32768, "skip": 4410,
                                 "step": "note", "amount": amount or (0.3 if shape == "pulse" else 0)})
        naive = p.evaluate(HAND, {"shape": shape, "f": f, "a": 0.9, "c": 0.25, "n": 32768, "skip": 4410,
                                  "step": "none", "amount": amount or (0.3 if shape == "pulse" else 0)})
        floors[shape] = (off_grid(ours, f), off_grid(note, f), off_grid(naive, f))
    for k, v in floors.items():
        print("    %-8s at 2346 Hz bent 0.9: folded back at %.1f dB; corrected at the note's rate %.1f; uncorrected %.1f"
              % ((k,) + v))
    # Measured when this landed: -44.8, -45.3, -42.1, -45.2 and -71.9 dB;
    # corrected at the note's own rate -29.5, -31.2, -24.1, -31.2, -52.6;
    # uncorrected -21.5, -21.8, -17.4, -21.8, -47.0. Each floor below is the
    # measured one with two decibels of slack, and is what the cheat sheet
    # states.
    FLOOR = {"ramp": -42.5, "square": -43, "pulse": -40, "morph": -43, "triangle": -69}
    under = lambda k, v: v < FLOOR[k]
    check("every sharp shape bent the whole way at 2.3 kHz folds back under its measured floor",
          all(under(k, floors[k][0]) for k in FLOOR), str({k: round(v[0], 1) for k, v in floors.items()}))
    check("and better than the same warp corrected at the note's own rate by ten decibels or more: "
          "the step is the bent one", all(floors[k][0] < floors[k][1] - 10 for k in FLOOR), "")
    null("the floor test fails the warp corrected at the note's rate", not any(under(k, floors[k][1]) for k in FLOOR))
    null("and the warp uncorrected", not any(under(k, floors[k][2]) for k in FLOOR))

    print("\n--- chords, the dyad and layer B ---")
    one = [{"note": 69, "freq": 441, "velocity": 1, "role": "xy"}]
    poly = run({"shape": "sine", "voices": one, "attackMs": 1, "sustain": 1, "warp": 0.6, "warpAt": 0.25})["HL"]
    wp = widths(poly)
    check("a chord's note is bent as the single voice is: the peak narrows and the trough widens",
          pinched_top(wp), "%s" % (wp,))
    polyPlain = widths(run({"shape": "sine", "voices": one, "attackMs": 1, "sustain": 1})["HL"])
    null("and an unbent chord does not pass", not pinched_top(polyPlain), "%s" % (polyPlain,))
    dy = run({"shape": "sine", "freq": 441, "interval": 7, "warp": 0.6, "warpAt": 0.25})
    dyPlain = run({"shape": "sine", "freq": 441, "interval": 7})
    wr, wr0 = widths(dy["R"]), widths(dyPlain["R"])
    check("the dyad's other channel is bent at the same point of its own cycle",
          wr[0] < 0.8 * wr0[0] and wr[1] > 1.2 * wr0[1], "%s against %s" % (wr, wr0))
    null("and its plain other channel does not pass", not (wr0[0] < 0.8 * wr0[0]))
    va = [{"note": 57, "freq": 220, "velocity": 1, "role": "xy"}]
    vb = [{"note": 69, "freq": 440, "velocity": 1, "role": "xy"}]
    base = run({"shape": "sine", "voices": va}, toneB={"shape": "sine", "voices": vb})
    bentB = run({"shape": "sine", "voices": va}, toneB={"shape": "sine", "voices": vb, "warp": 0.6})
    bentA = run({"shape": "sine", "voices": va, "warp": 0.6}, toneB={"shape": "sine", "voices": vb})
    print("    B bent: A moved %.1e, B %.3f; A bent: A %.3f, B %.1e"
          % (diff(base["L"], bentB["L"]), diff(base["BL"], bentB["BL"]), diff(base["L"], bentA["L"]),
             diff(base["BL"], bentA["BL"])))
    check("layer B has a bend of its own: bending B moves B and leaves A to the bit, and the other way round",
          np.array_equal(base["L"], bentB["L"]) and np.array_equal(base["BL"], bentA["BL"])
          and diff(base["BL"], bentB["BL"]) > 0.05 and diff(base["L"], bentA["L"]) > 0.05)
    null("the same comparison sees A moved when A is bent", not np.array_equal(base["L"], bentA["L"]))
    routedB = run({"shape": "sine", "voices": va}, toneB={"shape": "sine", "voices": vb},
                  routes=[{"to": "bend", "held": 0.5, "amountB": 0}])
    check("and a routing that reaches only A bends only A",
          np.array_equal(routedB["BL"], base["BL"]) and diff(routedB["L"], base["L"]) > 0.05)

    print("\n--- a source on it ---")
    fixed = run({"shape": "ramp", "freq": 330, "warp": 0.45})["L"]
    routed = run({"shape": "ramp", "freq": 330}, routes=[{"to": "bend", "held": 0.5}])["L"]
    unrouted = run({"shape": "ramp", "freq": 330})["L"]
    check("a source on Bend from a slider at nought: 0.5 of the travel is the slider at 50", diff(fixed, routed) < 1e-6,
          "%.1e" % diff(fixed, routed))
    null("and the slider at nought without it is not", diff(unrouted, routed) > 0.05, "%.3f" % diff(unrouted, routed))
    wrapped = run({"shape": "ramp", "freq": 330, "warp": 0.45, "warpAt": 0.9}, routes=[{"to": "bendAt", "held": 0.4}])["L"]
    direct = run({"shape": "ramp", "freq": 330, "warp": 0.45, "warpAt": 0.1})["L"]
    unwrapped = run({"shape": "ramp", "freq": 330, "warp": 0.45, "warpAt": 0.9})["L"]
    check("a source on Bend at moves the centre half a cycle at full depth, and wraps: 0.9 and 0.2 is 0.1",
          diff(wrapped, direct) < 1e-6, "%.1e" % diff(wrapped, direct))
    null("and without the source it stays at 0.9", diff(unwrapped, wrapped) > 0.05, "%.3f" % diff(unwrapped, wrapped))
    held = run({"shape": "ramp", "freq": 330, "warp": 0.9}, routes=[{"to": "bend", "held": 1}])["L"]
    full = run({"shape": "ramp", "freq": 330, "warp": 0.9})["L"]
    check("pushed past its end it is held there, where the phase still never runs backwards", diff(held, full) == 0,
          "%.1e" % diff(held, full))

    print("\n--- the panel, layers and setup codes ---")
    page = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const set = (id, v) => { el[id].value = String(v); el[id].dispatchEvent(new Event('input')); };
      setView('bench'); setBenchTab('ink');
      const shown = el.oscBend.offsetHeight > 0 && el.oscBendAt.offsetHeight > 0
        && el.oscBend.closest('.menu-group') === el.oscGroup;
      const off = [el.oscBendValue.textContent, el.oscBendAtValue.textContent, genSettings().warp, genSettings().warpAt];
      set('oscBend', 45); set('oscBendAt', 75);
      const a = [genSettings().warp, genSettings().warpAt, el.oscBendValue.textContent, el.oscBendAtValue.textContent];
      set('oscBend', -30);
      const neg = [genSettings().warp, el.oscBendValue.textContent];
      const code = snapshot();
      restore({}); await wait(30);
      const old = [genSettings().warp, genSettings().warpAt, el.oscBend.value, el.oscBendValue.textContent];
      restore(code); await wait(30);
      const back = [genSettings().warp, genSettings().warpAt, el.oscBend.value, el.oscBendAt.value];
      restore({ oscBend: 20, bBend: -70, bBendAt: 10 }); await wait(30);
      const split = [genSettings().warp, genSettings(1).warp, genSettings(1).warpAt];
      showLayerOnPanel(1);
      const onPanel = [el.oscBend.value, el.oscBendAt.value];
      set('oscBend', 60);
      const editedB = [genSettings(1).warp, genSettings().warp];
      showLayerOnPanel(0);
      const codeB = snapshot();
      restore({ oscBend: 500, oscBendAt: -3 }); await wait(30);
      const held = [el.oscBend.value, el.oscBendAt.value];
      restore({ oscBend: 40 }); await wait(30);
      const fallback = genSettings(1).warp;
      const dests = ['gen.bend', 'gen.bendAt'].map((id) => MOD_DESTS.has(id));
      restore({}); await wait(30);
      return { shown, off, a, neg, old, back, split, onPanel, editedB, held, fallback, dests,
               codeB: [codeB.oscBend, codeB.bBend, codeB.bBendAt] };
    }""")
    print("    %s" % page)
    r = lambda x: [round(v, 6) if isinstance(v, float) else v for v in x]
    check("Bend and Bend at are in the Oscillator section on the Shape tab", page["shown"])
    check("they start off and at 90 degrees, a quarter of the cycle", r(page["off"]) == ["off", "90°", 0, 0.25],
          str(page["off"]))
    check("and reach the generator in its units, saying what they are set to",
          r(page["a"]) == [0.405, 0.75, "+45%", "270°"] and r(page["neg"]) == [-0.27, "−30%"],
          "%s %s" % (page["a"], page["neg"]))
    check("a setup code carries both back", r(page["back"]) == [-0.27, 0.75, "-30", "75"], str(page["back"]))
    check("a code from before has no bend, and the panel says off",
          r(page["old"]) == [0, 0.25, "0", "off"], str(page["old"]))
    check("layer B's bend comes from its own fields", r(page["split"]) == [0.18, -0.63, 0.1], str(page["split"]))
    check("with B on the panel the controls show B's and write B's, and A is left alone",
          page["onPanel"] == ["-70", "10"] and r(page["editedB"]) == [0.54, 0.18], "%s %s" % (page["onPanel"], page["editedB"]))
    check("a code written afterwards carries both layers'", page["codeB"] == [20, 60, 10], str(page["codeB"]))
    check("a code's value out of range is held to the slider's", page["held"] == ["100", "0"], str(page["held"]))
    check("a code with none of B's bend gives B layer A's", round(page["fallback"], 6) == 0.36, str(page["fallback"]))
    check("both are destinations a source can be put on", page["dests"] == [True, True], str(page["dests"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the Bend pinches the wave where it is set, brightens it, and at nought is the wave it was")
