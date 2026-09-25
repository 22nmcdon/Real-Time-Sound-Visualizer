"""Inside the voice (H1): the second oscillator, FM, ring, hard sync, the sub
and unison.

What would go wrong, and what is checked for it:

- the new path changing a voice with nothing on: it is switched on with a
  routing whose value is nought, and must then be the plain wave to the
  last bit - and, as its null test, not with a value of 0.02;
- FM that is not FM: the sidebands of a sine carrier are Bessel's, J_k of
  the index at the carrier plus k times the modulator, and a 3:2 ratio puts
  every one of them on the harmonics of half the note - the figure's own
  closing - with nothing between;
- FM on a sharp shape band-limited at the wrong frequency: the saw is asked
  about its instantaneous frequency, and what folds back is pinned;
- ring that leaks the carrier;
- sync that is not band-limited, or corrected twice: at ratio one the reset
  and the slave's own wrap are one event, so the voice must be the plain
  band-limited saw one sample late, to float precision. At 2.5 and at a
  whole 2 what folds back is pinned against the naive reset's;
- the sub and unison at the levels their mix says, unison never louder than
  one copy, and the destinations reaching both;
- layer B with a voice of its own, poly, the panel editing the layer on it,
  and setup codes.
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
    """Amplitude spectrum, scaled so a sine of amplitude a reads a."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    i = np.arange(n)
    w = (BH[0] - BH[1] * np.cos(2 * np.pi * i / n)
         + BH[2] * np.cos(4 * np.pi * i / n) - BH[3] * np.cos(6 * np.pi * i / n))
    return np.abs(np.fft.rfft(x * w)) / np.sum(w) * 2, np.arange(n // 2 + 1) * RATE / n


def level_at(spec, hz, f):
    return spec[np.abs(hz - f) < 3 * RATE / (2 * (len(spec) - 1))].max()


def off_grid(x, f0, top=10000):
    """The loudest thing below `top` that is not a harmonic of f0, in dB
    under the loudest thing of all: what folded back."""
    spec, hz = spectrum(x)
    grid = np.zeros(len(spec), dtype=bool)
    grid[:6] = True
    k = 1
    while k * f0 < RATE / 2:
        grid |= np.abs(hz - k * f0) < 4 * RATE / len(x)
        k += 1
    return 20 * math.log10(max(spec[~grid & (hz < top)].max(), 1e-15) / spec.max())


def line(x, f):
    """One line's amplitude, the transform taken at exactly its frequency.
    Between two bins an FFT reads a few per cent low - the window's
    scalloping - and the first unison check read a copy at -20 cents as
    0.323 of a third for that reason alone."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    i = np.arange(n)
    w = (BH[0] - BH[1] * np.cos(2 * np.pi * i / n)
         + BH[2] * np.cos(4 * np.pi * i / n) - BH[3] * np.cos(6 * np.pi * i / n))
    return abs(np.sum(x * w * np.exp(-2j * np.pi * f * i / RATE))) / np.sum(w) * 2


def bessel_j(n, x):
    return sum((-1) ** k * (x / 2) ** (2 * k + n) / (math.factorial(k) * math.factorial(k + n)) for k in range(30))


# A core off the page, with a routing when asked: `held` is the routing's
# value, `slot` the destination's accumulator slot by name.
CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('mode', 'wave'); core.set('amp', 0.5); core.set('interval', 0); core.set('phase', 0);
  for (const k in setup.tone) core.set(k, setup.tone[k]);
  for (const k in setup.toneB || {}) core.set(k, setup.toneB[k], 1);
  if (setup.route) core.setRoutes([{ held: setup.route.held, slot: { fm: FM_SLOT, sync: SYNC_SLOT }[setup.route.to],
                                     amount: 1 }]);
  const n = setup.n, L = new Float32Array(n), R = new Float32Array(n);
  const HL = new Float32Array(n), HR = new Float32Array(n), BL = new Float32Array(n), BR = new Float32Array(n);
  core.block(L, R, n, HL, HR, BL, BR);
  const from = setup.skip || 0;
  return { L: Array.from(L.subarray(from)), R: Array.from(R.subarray(from)),
           HL: Array.from(HL.subarray(from)), BL: Array.from(BL.subarray(from)) };
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

    print("\n--- with nothing on, nothing changes ---")
    # A dyad of a 3:2 on the saw and on the harmonic tone, through the new
    # path - switched on by a routing on the index whose value is nought -
    # against the old one.
    same, moved = [], []
    for shape in ("ramp", "harmonic", "square"):
        # A 3:2 modulator on the nudged run: at 1:1 its sine is nought at
        # both of a square's edges, where all a square's change can be, and
        # an index of 0.1 moved the square by 8e-6.
        tone = {"shape": shape, "freq": 330, "interval": 7, "modRatio": 1.5}
        plain = run(tone, n=8820, skip=0)
        through = run(tone, n=8820, skip=0, route={"to": "fm", "held": 0})
        nudged = run(tone, n=8820, skip=0, route={"to": "fm", "held": 0.02})
        same.append(np.array_equal(plain["L"], through["L"]) and np.array_equal(plain["R"], through["R"]))
        moved.append(float(np.abs(plain["L"] - nudged["L"]).max()))
    print("    identical through the path: %s; with an index of 0.1, moved by %s" % (same, [round(m, 4) for m in moved]))
    check("the voice's oscillator with nothing on is the plain wave to the last bit, dyad and all",
          all(same) and min(moved) > 1e-3, "%s, %s" % (same, moved))
    v = [{"note": 57, "freq": 220, "velocity": 1, "role": "x"}, {"note": 64, "freq": 329.63, "velocity": 1, "role": "y"}]
    polyPlain = run({"shape": "ramp", "voices": v}, n=4410, skip=0)
    polyThrough = run({"shape": "ramp", "voices": v}, n=4410, skip=0, route={"to": "fm", "held": 0})
    check("and so is a chord", np.array_equal(polyPlain["HL"], polyThrough["HL"])
          and np.array_equal(polyPlain["L"], polyThrough["L"]), "")

    print("\n--- FM ---")
    I = 1.5
    fm = run({"shape": "sine", "freq": 440, "fmIndex": I, "modRatio": 1.5}, n=92610)
    spec, hz = spectrum(fm["L"])
    lines = {220: 1, 1100: 1, 880: 2, 1760: 2, 440: 0, 1540: 3, 2420: 3}
    worst = max(abs(level_at(spec, hz, f) / 0.5 - abs(bessel_j(k, I))) / abs(bessel_j(k, I)) for f, k in lines.items())
    print("    index 1.5 at 3:2: J1 %.5f read %.5f at 1100; worst line %.3f%% off Bessel's"
          % (bessel_j(1, I), level_at(spec, hz, 1100) / 0.5, 100 * worst))
    check("a sine carrier's sidebands are Bessel's J_k(1.5), each within 0.1 per cent",
          worst < 1e-3, "%.4f%%" % (100 * worst))
    between = off_grid(fm["L"], 220)
    check("and at 3:2 every one of them is a harmonic of 220, half the note: nothing between them",
          between < -100, "%.1f dB" % between)
    # The same index from a routing, with the slider at nought.
    routed = run({"shape": "sine", "freq": 440, "modRatio": 1.5}, n=92610, route={"to": "fm", "held": 0.3})
    spec2, _ = spectrum(routed["L"])
    check("a source on FM gives the same sidebands from a slider at nought: 0.3 of five is 1.5",
          abs(level_at(spec2, hz, 1100) - level_at(spec, hz, 1100)) < 1e-6,
          "%.6f against %.6f" % (level_at(spec2, hz, 1100), level_at(spec, hz, 1100)))
    # A saw under FM, band-limited at the frequency it has this sample. At a
    # 1:1 ratio every sideband is a harmonic, so anything off the grid folded.
    saw_fm = off_grid(run({"shape": "ramp", "freq": 1500, "fmIndex": 1, "modRatio": 1})["L"], 1500)
    print("    a saw at 1.5 kHz under an index of 1, 1:1: folded back at %.1f dB" % saw_fm)
    # Measured when this landed: -44.8, and -25.8 with the saw corrected at
    # the note's frequency instead of the one FM has taken it to.
    check("a saw under FM is band-limited where FM has taken it: under -42 dB, where the note's own step gave -25.8",
          saw_fm < -42, "%.1f dB" % saw_fm)

    print("\n--- ring ---")
    rg = run({"shape": "sine", "freq": 440, "ringMix": 1, "modRatio": 1.5}, n=92610)
    spec, hz = spectrum(rg["L"])
    got = [level_at(spec, hz, f) / 0.5 for f in (220, 1100, 440)]
    print("    220, 1100, 440: %s" % [round(g, 6) for g in got])
    check("ring at one is the sum and the difference, half each, and no carrier at all",
          abs(got[0] - 0.5) < 1e-4 and abs(got[1] - 0.5) < 1e-4 and got[2] < 1e-6, str(got))
    half = run({"shape": "sine", "freq": 440, "ringMix": 0.5, "modRatio": 1.5}, n=92610)
    spec, hz = spectrum(half["L"])
    got = [level_at(spec, hz, f) / 0.5 for f in (440, 220, 1100)]
    check("and at a half, half the carrier and a quarter each", abs(got[0] - 0.5) < 1e-4
          and abs(got[1] - 0.25) < 1e-4 and abs(got[2] - 0.25) < 1e-4, str([round(g, 5) for g in got]))

    print("\n--- sync ---")
    # Ratio one, switched on by a routing of nought: the reset and the
    # slave's own wrap are the same event, so the result must be the plain
    # band-limited wave, one sample late.
    late = {}
    for shape in ("ramp", "square", "morph"):
        tone = {"shape": shape, "freq": 1234.5, "morph": 2.4}
        plain = run(tone, n=4410, skip=0)["L"]
        synced = run(tone, n=4410, skip=0, route={"to": "sync", "held": 0})["L"]
        late[shape] = float(np.abs(synced[1:] - plain[:-1]).max())
    print("    worst difference from the plain wave one sample late: %s" % {k: "%.1e" % v for k, v in late.items()})
    check("sync at ratio one is the plain band-limited wave one sample late - corrected once, not twice",
          all(v < 1e-5 for v in late.values()), str(late))
    floors = {}
    for ratio in (2.5, 2.0, 3.7):
        floors[ratio] = off_grid(run({"shape": "ramp", "freq": 1000, "syncRatio": ratio})["L"], 1000)
    print("    a saw at 1 kHz synced at 2.5, 2 and 3.7 times: folded back at %s dB"
          % {k: round(v, 1) for k, v in floors.items()})
    # Measured when this landed: -45.2, -51.9 and -47.2; the reset left
    # uncorrected gave -32.7, -34.6 and -31.0.
    check("the reset is band-limited: under -43 dB at 2.5, 2 and 3.7, where the naive reset is -31 to -35",
          all(v < -43 for v in floors.values()), str({k: round(v, 1) for k, v in floors.items()}))
    sweep = run({"shape": "ramp", "freq": 220}, route={"to": "sync", "held": 0.5})
    spec, hz = spectrum(sweep["L"])
    fixed = run({"shape": "ramp", "freq": 220, "syncRatio": 2.75})
    check("a source on Sync moves the slave from a slider at one: 0.5 of 3.5 is 2.75, and the pitch stays 220",
          np.abs(sweep["L"] - fixed["L"]).max() < 1e-6 and off_grid(sweep["L"], 220) < -50,
          "%.2e from the fixed 2.75" % np.abs(sweep["L"] - fixed["L"]).max())

    print("\n--- the sub and unison ---")
    sub = run({"shape": "sine", "freq": 440, "subLevel": 1, "subShape": "sine"}, n=92610)
    spec, hz = spectrum(sub["L"])
    got = [level_at(spec, hz, f) / 0.5 for f in (440, 220)]
    sub2 = run({"shape": "sine", "freq": 440, "subLevel": 1, "subShape": "sine", "subOctave": 2}, n=92610)
    spec2, _ = spectrum(sub2["L"])
    got2 = level_at(spec2, hz, 110) / 0.5
    print("    note and sub an octave down: %s; two octaves down %.5f" % ([round(g, 5) for g in got], got2))
    check("a sine sub at full is mixed half and half with the note, an octave down, or two",
          all(abs(g - 0.5) < 1e-4 for g in got) and abs(got2 - 0.5) < 1e-4, str(got))
    uni = run({"shape": "sine", "freq": 440, "unison": 3, "unisonCents": 20}, n=176400)
    got = [line(uni["L"], 440 * 2 ** (c / 1200)) / 0.5 for c in (-20, 0, 20)]
    print("    three copies at -20, 0 and +20 cents: %s" % [round(g, 4) for g in got])
    check("three copies of a third each, at the note and 20 cents either side",
          all(abs(g - 1 / 3) < 1e-3 for g in got), str(got))
    one = run({"shape": "ramp", "freq": 440}, n=8820)["L"]
    seven = run({"shape": "ramp", "freq": 440, "unison": 7, "unisonCents": 30}, n=88200)["L"]
    check("seven copies are never louder than one: the sum is a mix, as the drawbars' is",
          np.abs(seven).max() <= np.abs(one).max() + 1e-6, "%.4f against %.4f" % (np.abs(seven).max(), np.abs(one).max()))
    # Three copies at no spread are three of the same copy: the plain wave,
    # on a dyad with the right channel a quarter-cycle on - which is what
    # shows whether each copy of Y kept the dyad's phase.
    flat = run({"shape": "ramp", "freq": 220, "interval": 7, "phase": math.pi / 2, "unison": 3, "unisonCents": 0},
               n=8820, skip=0)
    ref = run({"shape": "ramp", "freq": 220, "interval": 7, "phase": math.pi / 2}, n=8820, skip=0)
    err = max(np.abs(flat["L"] - ref["L"]).max(), np.abs(flat["R"] - ref["R"]).max())
    check("three copies with no spread are the plain wave, the right channel's phase and all",
          err < 1e-5 and np.abs(ref["R"] - run({"shape": "ramp", "freq": 220, "interval": 7}, n=8820, skip=0)["R"]).max() > 0.3,
          "%.2e" % err)
    # Unison on a 3:2 dyad: each copy of Y is 3:2 against its copy of X, so
    # the figure stays one figure, thickened.
    dy = run({"shape": "sine", "freq": 220, "interval": 7, "unison": 3, "unisonCents": 15}, n=176400)
    lock = [line(dy["R"], 330 * 2 ** (c / 1200)) / line(dy["L"], 220 * 2 ** (c / 1200)) for c in (-15, 0, 15)]
    check("on a dyad each copy keeps the interval: Y's copies sit at 3:2 of X's, as loud",
          all(abs(r - 1) < 1e-3 for r in lock), str([round(r, 5) for r in lock]))

    print("\n--- layers and poly ---")
    vb = {"shape": "sine", "amp": 0.5, "fmIndex": 2, "modRatio": 2,
          "voices": [{"note": 69, "freq": 440, "velocity": 1, "role": "xy"}]}
    lay = run({"shape": "sine", "voices": [{"note": 57, "freq": 220, "velocity": 1, "role": "xy"}]},
              n=48510, toneB=vb)
    sa, hz = spectrum(lay["L"]); sb, _ = spectrum(lay["BL"])
    a3, b3 = level_at(sa, hz, 660), level_at(sb, hz, 1320)
    plainB = run({"shape": "sine", "voices": [{"note": 57, "freq": 220, "velocity": 1, "role": "xy"}]},
                 n=48510, toneB=dict(vb, fmIndex=0))
    spb, _ = spectrum(plainB["BL"])
    b0 = level_at(spb, hz, 1320)
    print("    layer A's third harmonic %.2e; layer B's sideband at 1320 %.4f, and %.2e without FM" % (a3, b3, b0))
    check("layer B has a voice of its own: B's FM puts sidebands on B, and A stays a sine",
          b3 > 0.05 and b0 < 1e-5 and a3 < 1e-5, "B %.4f (%.2e plain), A %.2e" % (b3, b0, a3))

    print("\n--- the panel, layers and setup codes ---")
    page = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const set = (id, v, kind) => { el[id].value = String(v); el[id].dispatchEvent(new Event(kind)); };
      setView('bench'); setBenchTab('shape');
      const shown = el.oscGroup.offsetHeight > 0;
      set('oscRatio', 1.5, 'change'); set('oscFm', 25, 'input'); set('oscRing', 40, 'input');
      set('oscSync', 250, 'input'); set('oscSub', 30, 'input'); set('oscSubOct', 2, 'change');
      set('oscSubShape', 'sine', 'change'); set('oscUnison', 5, 'change'); set('oscSpread', 20, 'input');
      const g = genSettings();
      const a = [g.modRatio, g.fmIndex, g.ringMix, g.syncRatio, g.subLevel, g.subOctave, g.subShape, g.unison, g.unisonCents];
      const words = [el.oscFmValue.textContent, el.oscRingValue.textContent, el.oscSyncValue.textContent,
                     el.oscSubValue.textContent, el.oscSpreadValue.textContent];
      const code = snapshot();
      restore({}); await wait(30);
      const g0 = genSettings();
      const old = [g0.modRatio, g0.fmIndex, g0.ringMix, g0.syncRatio, g0.subLevel, g0.unison,
                   el.oscSyncValue.textContent, el.oscFmValue.textContent];
      restore(code); await wait(30);
      const g1 = genSettings();
      const back = [g1.modRatio, g1.fmIndex, g1.ringMix, g1.syncRatio, g1.subLevel, g1.subOctave, g1.subShape,
                    g1.unison, g1.unisonCents];
      // Layer B's voice, set from a code, and from the panel while B is on it.
      restore({ oscFm: 10, bFm: 70, bRatio: 2, bUnison: 3 }); await wait(30);
      const split = [genSettings().fmIndex, genSettings(1).fmIndex, genSettings(1).modRatio, genSettings(1).unison];
      showLayerOnPanel(1);
      const onPanel = [el.oscFm.value, el.oscRatio.value, el.oscUnison.value];
      set('oscFm', 40, 'input');
      const editedB = [genSettings(1).fmIndex, genSettings().fmIndex];
      showLayerOnPanel(0);
      const backToA = el.oscFm.value;
      const codeB = snapshot();
      // A code with none of B's voice gives B layer A's, as B's shape does.
      restore({ oscFm: 30, oscUnison: 5 }); await wait(30);
      const fallback = [genSettings(1).fmIndex, genSettings(1).unison];
      // And a new generator is built from what the panel says.
      set('oscSync', 330, 'input');
      const built = {};
      generatorFromPanel((f, v) => { built[f] = v; });
      restore({}); await wait(30);
      return { shown, a, words, old, back, split, onPanel, editedB, backToA, fallback,
               built: [built.fmIndex, built.unison, built.syncRatio],
               codeB: [codeB.oscFm, codeB.bFm, codeB.bRatio, codeB.bUnison] };
    }""")
    print("    %s" % page)
    check("the section is on the Shape tab and every control reaches the generator in its own units",
          page["shown"] and page["a"] == [1.5, 2.5, 0.4, 2.5, 0.3, 2, "sine", 5, 20], str(page["a"]))
    check("and says what it is set to", page["words"] == ["2.5", "0.40", "2.50×", "0.30", "20 cents"], str(page["words"]))
    check("a setup code carries it all back", page["back"] == page["a"], str(page["back"]))
    check("a code from before has the voice plain, and the panel says off",
          page["old"] == [1, 0, 0, 1, 0, 1, "off", "0.0"], str(page["old"]))
    check("layer B's voice comes from its own fields in a code",
          page["split"] == [1, 7, 2, 3], str(page["split"]))
    check("with B on the panel the controls show B's and write B's, and A is left alone",
          page["onPanel"] == ["70", "2", "3"] and page["editedB"] == [4, 1] and page["backToA"] == "10",
          "%s, %s, %s" % (page["onPanel"], page["editedB"], page["backToA"]))
    check("and a code written afterwards carries both", page["codeB"] == [10, 40, 2, 3], str(page["codeB"]))
    check("a code with none of B's voice gives B layer A's", page["fallback"] == [3, 5], str(page["fallback"]))
    check("and a generator built from the panel has the panel's voice", page["built"] == [3, 5, 3.3], str(page["built"]))

    def search(q):
        p.evaluate("(q) => { el.benchSearch.value = q; el.benchSearch.dispatchEvent(new Event('input')); }", q)
        return p.evaluate("""() => Array.from(el.benchResults.querySelectorAll('button'))
          .map((b) => [b.firstChild.textContent, b.querySelector('.crumb').textContent])""")
    found = search("supersaw")
    check("supersaw finds unison", ["Unison", "Oscillator"] in found, str(found[:3]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the voice has a second oscillator, and with it off it is the voice it was")
