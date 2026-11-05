"""Scan (P7a): the phosphor read back as the voice's wave.

Sixty times a second of audio time, the screen's light is read round an
off-centre circle into one cycle of a wave, the voice plays it at the note's
pitch, and each tick's table is crossfaded into the next across the tick -
round one of the Scan experiment, the take the owner chose. Each claim is
checked against the way it would fail:

- the reading: a table that is not the reading's harmonics, a level that
  keeps what would fold, a quiet picture played quieter, darkness divided by
  nothing, a symmetric figure read from its centre (three times too high, as
  P2 found), softness that does not soften;
- the tick: a table that lands when the page sends it rather than at the
  next sixtieth of a second of samples, a crossfade that is a step or the
  wrong length, at three sample rates;
- the voice: nought that changes anything, a pitch that is not the note's,
  a depth that takes the whole voice, a hold that does not rein it in, a
  bend that does not reach it, layer B's Scan in layer A;
- the page: the controls and a setup code's round trip (the depth per layer,
  the softness, Persistence in seconds between the menu's five), the freeze
  while a setup lands, the running-away hold, each layer reading its own
  figure;
- and the first-minute test: a turning fifth, read back, moves its timbre
  within seconds, where without Scan it stands still - and held still, by
  stopping the screen, Scan is an ordinary tone.

The core runs on the main thread from `makeGeneratorCore`, the generator's
JavaScript implementation; most of the page runs on `?brain=js&core=js`,
whose reading and timing are the ones under test, and the C++ port is held
to them by core/tests/parity.py. The last section opens the site as a
visitor does, on the compiled instrument, which reads its own screen at
sixty frames a second of the sound: Scan has to be heard there too, and the
page's own brain on the compiled generator has to send it its tables.
Every assertion has its null beside it.
"""
import math, os, statistics, sys
import numpy as np
from playwright.sync_api import sync_playwright
import corpus

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    """A check's null: the same comparison fed a value it must reject."""
    check("null: " + name, red, detail)


def harmonics(table, top=80):
    """Each harmonic's amplitude in one cycle of a table."""
    spec = np.abs(np.fft.rfft(np.asarray(table, dtype=float))) / len(table) * 2
    return spec[:top + 1]


def lowest(table, share=0.1):
    """The lowest harmonic carrying a tenth of the energy: P2's 'heard'."""
    h = harmonics(table, 64)[1:] ** 2
    return int(np.argmax(h / h.sum() > share)) + 1


# A grid with a figure on it: a curve given in polar form about a centre,
# laid as thin lit lines, as the beam lays a slow figure.
GRID = """(spec) => {
  const n = 64, g = new Float64Array(n * n);
  for (let s = 0; s < 20000; s++) {
    const t = 2 * Math.PI * s / 20000;
    const r = spec.R * (spec.kind === 'rose' ? Math.cos(spec.k * t) : 1);
    const x = spec.cx + r * Math.cos(t + (spec.turn || 0)), y = spec.cy + r * Math.sin(t + (spec.turn || 0));
    const cx = Math.floor(x * n), cy = Math.floor(y * n);
    if (cx >= 0 && cy >= 0 && cx < n && cy < n) g[cy * n + cx] = spec.level || 1;
  }
  return g;
}"""

CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const rate = setup.rate || 44100;
  const core = makeGeneratorCore(rate, GEN_DESTS.length, [still(), still()]);
  core.set('mode', 'wave'); core.set('amp', 0.5); core.set('interval', 0); core.set('phase', 0);
  const table = (h) => {
    if (h === null) return null;
    const pts = new Float64Array(SCAN_POINTS);
    for (let i = 0; i < SCAN_POINTS; i++) {
      for (const [k, a, ph] of h) pts[i] += a * Math.cos(2 * Math.PI * k * i / SCAN_POINTS + (ph || 0));
    }
    return scanTables(pts);
  };
  for (const k in setup.tone) core.set(k, setup.tone[k]);
  for (const k in setup.toneB || {}) core.set(k, setup.toneB[k], 1);
  const L = [], R = [], BL = [], BR = [];
  // Blocks, with a table sent at the start of each: [samples, harmonics, layer].
  for (const [n, h, layer] of setup.blocks) {
    if (h !== undefined) core.set('scanTable', table(h), layer || 0);
    const l = new Float32Array(n), r = new Float32Array(n), hl = new Float32Array(n), hr = new Float32Array(n);
    const bl = new Float32Array(n), br = new Float32Array(n);
    core.block(l, r, n, hl, hr, bl, br);
    L.push(...l); R.push(...r); BL.push(...bl); BR.push(...br);
  }
  return { L, R, BL, BR };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html?brain=js&core=js"); p.wait_for_timeout(900)
    corpus.install(p)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    def run(**setup):
        out = p.evaluate(CORE, setup)
        return {k: np.asarray(v) for k, v in out.items()}

    # ------------------------------------------------------------------
    print("\n--- the reading ---")
    t = p.evaluate("""() => {
      const pts = (f) => Float64Array.from({ length: SCAN_POINTS }, (_, i) => f(2 * Math.PI * i / SCAN_POINTS));
      const three = scanTables(pts((x) => 0.4 + 0.3 * Math.cos(3 * x + 0.7)));
      const quiet = scanTables(pts((x) => 0.04 + 0.03 * Math.cos(3 * x + 0.7)));
      const rich = scanTables(pts((x) => Math.cos(x) + 0.5 * Math.cos(50 * x)));
      return {
        three: Array.from(three.levels[0]), most: three.most, count: three.levels.length,
        quiet: Array.from(quiet.levels[0]),
        rich0: Array.from(rich.levels[0]), rich1: Array.from(rich.levels[1]),
        flat: scanTables(pts(() => 0.3)), dim: scanTables(pts((x) => 0.3 + 5e-5 * Math.cos(x))),
        faint: scanTables(pts((x) => 0.3 + 5e-3 * Math.cos(x))) !== null,
      };
    }""")
    n = len(t["three"])
    want = np.cos(3 * 2 * np.pi * np.arange(n) / n + 0.7)
    want /= np.abs(want).max()                  # evened to the peak its points reach
    err = float(np.abs(np.asarray(t["three"]) - want).max())
    check("a reading's table is its harmonics, evened to a peak of one, with no DC", err < 1e-9,
          "%d levels of %d, most %d, error %.1e" % (t["count"], n, t["most"], err))
    wrong = float(np.abs(np.asarray(t["three"]) - np.cos(2 * 2 * np.pi * np.arange(n) / n + 0.7)).max())
    null("the same table against the second harmonic", wrong > 0.5, "%.2f" % wrong)
    q = float(np.abs(np.asarray(t["quiet"]) - np.asarray(t["three"])).max())
    check("a picture ten times dimmer reads the same table: the picture cannot make the voice quieter", q < 1e-9,
          "%.1e" % q)
    null("the dim table against the bright one unevened, a tenth of it", float(np.abs(np.asarray(t["quiet"]) * 0.1 - np.asarray(t["three"])).max()) > 0.5)
    h0, h1 = harmonics(t["rich0"]), harmonics(t["rich1"])
    check("the second level leaves out what the first has past its 32nd harmonic", h1[33:].max() < 1e-9 and h0[50] > 0.2,
          "level 1 above 32: %.1e; level 0 at 50: %.3f" % (h1[33:].max(), h0[50]))
    null("the first level past its 32nd, where the 50th is", h0[33:].max() > 0.2, "%.3f" % h0[33:].max())
    check("a flat reading is darkness, and so is one under SCAN_DARK: no table, so the last is held",
          t["flat"] is None and t["dim"] is None)
    null("a faint reading over SCAN_DARK is not darkness", t["faint"])

    # The off-centre path: a three-petalled rose, as P2's rose, read from off
    # its centre and from its centre.
    rose = p.evaluate("""([g, spec]) => {
      const grid = (eval(g))(spec);
      const path = scanGeometry(grid);
      const r = Math.max(path.r, SCAN_LEAST / 64);
      const off = scanTables(scanRead(grid, path, 1.5));
      const centred = scanTables(scanRead(grid, { cx: path.cx - 0.35 * r, cy: path.cy - 0.2 * r, r: path.r }, 1.5));
      return { off: Array.from(off.levels[0]), centred: Array.from(centred.levels[0]), path };
    }""", [GRID, {"kind": "rose", "k": 3, "R": 0.3, "cx": 0.5, "cy": 0.5}])
    lo_off, lo_c = lowest(rose["off"]), lowest(rose["centred"])
    check("an off-centre path reads a three-petalled rose at its fundamental", lo_off == 1,
          "lowest harmonic with a tenth of the energy: %d (centre at %.3f, %.3f, radius %.3f)"
          % (lo_off, rose["path"]["cx"], rose["path"]["cy"], rose["path"]["r"]))
    null("the same rose read from its centre plays three times too high, as P2 found", lo_c == 3, "%d" % lo_c)

    # Softness: thin lines read as spikes; three cells of blur takes the top off.
    soft = p.evaluate("""([g, spec]) => {
      const grid = (eval(g))(spec), path = scanGeometry(grid);
      return [0, 3].map((s) => Array.from(scanTables(scanRead(grid, path, s)).levels[0]));
    }""", [GRID, {"kind": "circle", "R": 0.25, "cx": 0.45, "cy": 0.55}])
    def top_share(table):
        h = harmonics(table, 64)[1:] ** 2
        return float(h[15:].sum() / h.sum())
    raw, softened = top_share(soft[0]), top_share(soft[1])
    check("three cells of softness take the spikes out: the share above the 16th harmonic falls tenfold",
          softened < raw / 10, "raw %.3f, soft %.4f" % (raw, softened))
    null("raw against raw", not (raw < raw / 10))

    follow = p.evaluate("""([g]) => {
      const a = (eval(g))({ kind: 'circle', R: 0.2, cx: 0.3, cy: 0.5 }), bgrid = (eval(g))({ kind: 'circle', R: 0.2, cx: 0.7, cy: 0.5 });
      let path = scanFollow(null, a, 0.016);
      const start = path.cx;
      for (let k = 0; k < 60; k++) path = scanFollow(path, bgrid, 1 / 60);
      const dark = scanFollow(path, new Float64Array(64 * 64), 1);
      return { start, after: path.cx, target: scanGeometry(bgrid).cx, dark: dark.cx };
    }""", [GRID])
    frac = (follow["after"] - follow["start"]) / (follow["target"] - follow["start"])
    check("the path follows the figure over about a second: 63 per cent of the way after one", abs(frac - (1 - math.exp(-1))) < 0.01,
          "%.3f of the way" % frac)
    null("that against all of the way", not (abs(frac - 1) < 0.01), "%.3f" % frac)
    check("and holds where it was over darkness", follow["dark"] == follow["after"])

    # ------------------------------------------------------------------
    print("\n--- the tick ---")
    for rate in (44100, 48000, 22050):
        per = rate / 60
        # Where the core's ticks fall: the accumulator, written out.
        ticks, rest, clock = [], [], 0.0
        for i in range(int(per * 8)):
            clock += 1
            if clock >= per: clock -= per; ticks.append(i); rest.append(clock)
        tone = {"shape": "sine", "freq": 220, "scan": 1}
        A, B = [[3, 1]], [[5, 1]]
        set_at = lambda at: run(rate=rate, tone=tone, blocks=[[at, A], [int(per * 8) - at, B]])
        x = set_at(int(ticks[3] + per * 0.1))
        y = set_at(int(ticks[3] + per * 0.9))
        z = set_at(int(ticks[4] + per * 0.1))
        same = float(np.abs(x["L"] - y["L"]).max())
        first = int(np.argmax(np.abs(x["L"] - z["L"]) > 0))
        check("at %d Hz a table sent anywhere in a tick lands at the next, to the sample" % rate, same == 0,
              "sent a tenth and nine tenths in: largest difference %.1e" % same)
        # Where a sixtieth is not a whole number of samples the tick lands
        # part-way through one, so the crossfade has begun at the tick's own
        # sample: they part there, not one after.
        part = ticks[4] + (0 if rest[4] > 0 else 1)
        check("at %d Hz and one sent a tick later lands a tick later: they part at sample %d" % (rate, part),
              first == part, "first difference at %d" % first)
        null("at %d Hz, a table landing when sent would part where it was sent" % rate, first != int(ticks[3] + per * 0.1))

    # The crossfade: linear across one tick, from the table before to the
    # table after - checked against each table played steady, sample by
    # sample, since the voice is linear in what it reads.
    per, ticks = 735, [734 + 735 * k for k in range(8)]
    tone = {"shape": "sine", "freq": 220, "scan": 1}
    one = run(tone=tone, blocks=[[4410, [[3, 1]]]])
    two = run(tone=tone, blocks=[[4410, [[5, 1, 0.4]]]])
    fade = run(tone=tone, blocks=[[2000, [[3, 1]]], [2410, [[5, 1, 0.4]]]])
    i = np.arange(4410)
    x_of = np.clip((i - ticks[2]) / per, 0, 1)
    pred = one["L"] + (two["L"] - one["L"]) * x_of
    span = (i >= ticks[1] + 1)
    errf = float(np.abs(fade["L"][span] - pred[span]).max())
    check("the crossfade is a straight line across one tick, from the last table to the new one", errf < 1e-6,
          "worst %.1e over samples %d to 4410" % (errf, ticks[1] + 1))
    step = one["L"] + (two["L"] - one["L"]) * (i > ticks[2])
    null("the same against a step at the tick", float(np.abs(fade["L"][span] - step[span]).max()) > 0.01)
    half = one["L"] + (two["L"] - one["L"]) * np.clip((i - ticks[2]) / (per / 2), 0, 1)
    null("and against a crossfade half a tick long", float(np.abs(fade["L"][span] - half[span]).max()) > 0.01)

    # ------------------------------------------------------------------
    print("\n--- the voice ---")
    TAB = [[3, 1], [2, 0.5, 1.1]]
    for label, tone in [("dyad", {"shape": "harmonic", "freq": 330, "interval": 7}),
                        ("chord", {"shape": "ramp", "voices": [{"note": 60, "freq": 261.63, "velocity": 1},
                                                              {"note": 64, "freq": 329.63, "velocity": 1}]}),
                        ("unison", {"shape": "square", "freq": 220, "unison": 3})]:
        plain = run(tone=tone, blocks=[[4410, None]])
        zero = run(tone=tone, blocks=[[4410, TAB]])
        nudged = run(tone=dict(tone, scan=0.01), blocks=[[4410, TAB]])
        d0 = float(np.abs(plain["L"] - zero["L"]).max())
        d1 = float(np.abs(plain["L"] - nudged["L"]).max())
        d0r = float(np.abs(plain["R"] - zero["R"]).max())
        d1r = float(np.abs(plain["R"] - nudged["R"]).max())
        check("%s: a table at a depth of nought changes nothing, to the bit, either side" % label, d0 == 0 and d0r == 0,
              "%.1e, %.1e" % (d0, d0r))
        null("%s: at a depth of 0.01 it does, either side" % label, d1 > 1e-5 and d1r > 1e-5, "%.1e, %.1e" % (d1, d1r))

    f = 441.0                                   # a hundred samples a cycle
    steady = run(tone={"shape": "sine", "freq": f, "scan": 1}, blocks=[[8820, [[1, 1], [4, 0.7, 0.3], [7, 0.4, 2]]]])
    s = steady["L"][2205:8000]
    per_err = float(np.abs(s[100:] - s[:-100]).max())
    off = float(np.abs(s[101:] - s[:-101]).max())
    check("Scan plays at the note's pitch: the wave repeats every cycle of the note", per_err < 1e-5,
          "%.1e a period apart" % per_err)
    null("a period and a sample apart", off > 0.01, "%.3f" % off)

    def fundamental(x):
        x = np.asarray(x[2205:2205 + 4410])
        k = np.arange(len(x))
        return abs(np.sum(x * np.exp(-2j * np.pi * f * k / 44100))) * 2 / len(x)
    sine = fundamental(run(tone={"shape": "sine", "freq": f}, blocks=[[8820, None]])["L"])
    for depth, hold, keep in [(1, 1, 1 - 0.8), (1, 0.25, 1 - 0.2), (0.5, 1, 1 - 0.4)]:
        got = fundamental(run(tone={"shape": "sine", "freq": f, "scan": depth, "scanHold": hold},
                              blocks=[[8820, [[2, 1]]]])["L"]) / sine
        check("depth %.1f under a hold of %.2f keeps %.2f of the shape: the note never loses its fundamental" % (depth, hold, keep),
              abs(got - keep) < 0.005, "%.4f" % got)
        null("depth %.1f, hold %.2f: against the whole voice taken, nothing kept" % (depth, hold), abs(got - 0) > 0.1)

    # The bend reaches what Scan reads: the same table read at the bent phase,
    # by hand, over the shape bent the same way.
    tab = [[1, 1], [3, 0.6, 0.5]]
    a, c, fb = 0.6, 0.3, 220.0
    bent = run(tone={"shape": "sine", "freq": fb, "scan": 1, "warp": a, "warpAt": c}, blocks=[[8820, tab]])
    hand = p.evaluate("""([tab, a, c, f]) => {
      const pts = new Float64Array(SCAN_POINTS);
      for (let i = 0; i < SCAN_POINTS; i++) for (const [k, amp, ph] of tab) pts[i] += amp * Math.cos(2 * Math.PI * k * i / SCAN_POINTS + (ph || 0));
      const T = scanTables(pts), out = [], flat = [];
      for (let i = 2205; i < 8820; i++) {
        const p = TWO_PI * f * (i + 1) / 44100, d = p - TWO_PI * c;
        const q = p + a * Math.sin(d), step = Math.abs(f * (1 + a * Math.cos(d))) / 44100;
        const ink = waveAt('sine', q, step);
        out.push(0.5 * (ink + (cycleRead(T, q, step) - ink) * SCAN_MOST));
        flat.push(0.5 * (ink + (cycleRead(T, p, f / 44100) - ink) * SCAN_MOST));
      }
      return { out, flat };
    }""", [tab, a, c, fb])
    eb = float(np.abs(bent["L"][2205:] - np.asarray(hand["out"])).max())
    ef = float(np.abs(bent["L"][2205:] - np.asarray(hand["flat"])).max())
    check("the bend bends what Scan reads, not only the shape under it", eb < 1e-6, "%.1e" % eb)
    null("the same against Scan read at the unbent phase", ef > 0.01, "%.3f" % ef)

    # Layer B's Scan is B's.
    lay = {"shape": "sine", "voices": [{"note": 48, "freq": 130.81, "velocity": 1}]}
    layB = {"voices": [{"note": 72, "freq": 523.25, "velocity": 1}], "shape": "sine"}
    plainB = run(tone=lay, toneB=layB, blocks=[[4410, None]])
    scanB = run(tone=lay, toneB=dict(layB, scan=1), blocks=[[10, [[3, 1]], 1], [4400, None]])
    dA = float(np.abs(plainB["L"] - scanB["L"]).max())
    dB = float(np.abs(plainB["BL"] - scanB["BL"]).max())
    check("layer B's depth and table play in B's lanes and leave A's to the bit", dA == 0 and dB > 0.01,
          "A moved %.1e, B %.3f" % (dA, dB))
    null("B's lanes against themselves unscanned", not (float(np.abs(plainB["BL"] - plainB["BL"]).max()) > 0.01))

    sync = run(tone={"shape": "ramp", "freq": 220, "syncRatio": 2.3, "scan": 1}, blocks=[[8820, [[1, 1], [2, 0.5]]]])
    flat = run(tone={"shape": "ramp", "freq": 220, "syncRatio": 2.3}, blocks=[[8820, None]])
    # Scan in every sample of the slave's cycle, not only at its restarts,
    # which are one sample in two hundred here.
    moved = float(np.mean(np.abs(sync["L"] - flat["L"]) > 0.01))
    check("under sync it is bounded and finite, and Scan is in nearly every sample, not only the restarts",
          np.isfinite(sync["L"]).all() and np.abs(sync["L"]).max() <= 0.5 + 1e-9 and moved > 0.5,
          "peak %.3f, %.0f%% of samples moved" % (np.abs(sync["L"]).max(), 100 * moved))
    # Its null was a mutant: Scan left out between restarts moved 0.5 per cent.

    # ------------------------------------------------------------------
    print("\n--- the page ---")
    # The fifths here and below are the old library's, from before P8g: an
    # equal fifth with no Scan, and the same with Scan at full, which is what
    # every check of this section was measured on. The bank has neither.
    ctl = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      loadCorpus('Perfect fifth, equal'); await wait(500);
      el.oscScan.value = '60'; el.oscScan.dispatchEvent(new Event('input'));
      el.scanSoft.value = '15'; el.scanSoft.dispatchEvent(new Event('input'));
      el.scanMemory.value = '70'; el.scanMemory.dispatchEvent(new Event('input'));
      const set = { scan: genSettings().scan, reading: el.oscScanValue.textContent, soft: scan.soft,
                    pers: state.persistence, menu: el.persistence.value, menuText: el.persistence.selectedOptions[0].textContent,
                    memory: el.scanMemoryValue.textContent };
      const code = snapshot();
      restore({}); await wait(100);
      const cleared = { scan: genSettings().scan, soft: scan.soft, pers: state.persistence, menu: el.persistence.value };
      restore(code); await wait(100);
      const back = { scan: genSettings().scan, slider: el.oscScan.value, soft: scan.soft, pers: state.persistence,
                     menu: el.persistence.value, menuText: el.persistence.selectedOptions[0].textContent };
      el.persistence.value = '0.12'; el.persistence.dispatchEvent(new Event('change'));
      const menu = { slider: el.scanMemory.value, pers: state.persistence, custom: el.persistence.querySelector('option[data-memory]').hidden };
      return { set, code: { oscScan: code.oscScan, scanSoft: code.scanSoft, persistence: code.persistence }, cleared, back, menu };
    }""")
    s0 = ctl["set"]
    check("Depth writes the layer's scan, and says how much of the voice it is", s0["scan"] == 0.6 and s0["reading"] == "48%",
          str(s0))
    check("Persistence in seconds sets the phosphor's fade, and the menu shows its time when it is not one of the five",
          abs(s0["pers"] - (1 - 2 ** (-1 / (60 * 0.02 * 500 ** (69 / 98))))) < 1e-4 and s0["menu"] == str(s0["pers"])
          and s0["menuText"] == s0["memory"], "%s, menu %r reading %r" % (s0["pers"], s0["menuText"], s0["memory"]))
    bk = ctl["back"]
    check("a setup code carries the depth, the softness and that persistence, and brings them back",
          ctl["code"]["oscScan"] == 60 and ctl["code"]["scanSoft"] == 15 and bk["scan"] == 0.6 and bk["slider"] == "60"
          and bk["soft"] == 1.5 and bk["pers"] == s0["pers"] and bk["menuText"] == s0["memory"], str(ctl["code"]) + " " + str(bk))
    cl = ctl["cleared"]
    null("between them, the defaults: no Scan, three cells, no persistence", cl["scan"] == 0 and cl["soft"] == 3 and cl["pers"] == 0,
         str(cl))
    check("a persistence chosen in the menu moves the slider to its time and hides Memory's own",
          ctl["menu"]["pers"] == 0.12 and ctl["menu"]["slider"] == "25" and ctl["menu"]["custom"], str(ctl["menu"]))

    frz = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      loadCorpus('Scanned fifth'); await wait(1000);
      const posts = [], src = state.source, was = src.set;
      src.set = function (field, value, layer) { if (field === 'scanTable') posts.push(performance.now()); return was.call(this, field, value, layer); };
      await wait(300);
      const before = posts.length;
      posts.length = 0;
      const t0 = performance.now();
      loadCorpus('Scanned fifth');
      await wait(700);
      src.set = was;
      return { before, first: posts.length ? posts[0] - t0 : null, count: posts.length };
    }""")
    check("for a quarter of a second after a setup lands nothing is read", frz["first"] is not None and frz["first"] >= 240,
          "first table %s ms after, %d in 0.7 s" % (frz["first"], frz["count"]))
    null("and running, a table goes every frame", frz["before"] >= 10, "%d in 0.3 s" % frz["before"])

    # A voice rebuilt with Scan on - hushed and heard again - is handed the
    # settings through JSON, and a table's Float64Array levels came out of
    # it as objects with no length: the new voice's first table was all NaN
    # and took the generator with it (found by P7b's looptest on its second
    # run, where the first had hushed the voice).
    rebuilt = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      loadCorpus('Scanned fifth'); await wait(1200);
      const table = genSettings().scanTable;
      const naive = JSON.parse(JSON.stringify(table)).levels[0].length;
      // Depth at nought across the rebuild and back up after it, so the
      // table the new voice was built with is the one it plays first: with
      // Scan on throughout, a fresh table usually lands before the first
      // tick and hides the old one, and this check passed on the broken page.
      const depth = (v) => { el.oscScan.value = String(v); el.oscScan.dispatchEvent(new Event('input')); };
      // And through toTone, as a source changed and changed back goes:
      // without it the old voice's settings were not the ones rebuilt.
      // What the rebuilt voice is handed, caught as it is made: whether the
      // table reaches the worklet as tables at all is the cause, and it does
      // not depend on which of a fresh table and the first tick wins - the
      // sound below does, and in the full suite it passed on the broken page.
      let handed = null;
      const Real = window.AudioWorkletNode;
      window.AudioWorkletNode = class extends Real {
        constructor(context, name, options) {
          super(context, name, options);
          if (name === 'generator' && options && options.processorOptions) handed = options.processorOptions.tone.scanTable;
        }
      };
      depth(0);
      const v = genVoice(); await v.setSound(false); syncGeneratorSound();
      toTone(); genSet('shape', 'sine');
      await applyGeneratorSound();
      window.AudioWorkletNode = Real;
      const handedOk = !!(handed && handed.levels && handed.levels.every((L) => Array.isArray(L) && L.length === SCAN_TABLE && L.every(Number.isFinite)));
      depth(100);
      let finite = true, peak = 0;
      for (let k = 0; k < 20; k++) {
        await wait(75);
        const [l, r] = state.source.getLatestWindow(2048);
        for (const x of [...l, ...r]) { if (!Number.isFinite(x)) finite = false; else peak = Math.max(peak, Math.abs(x)); }
      }
      return { finite, peak, audible: genVoice().audible(), naive: naive === undefined ? null : naive, handedOk,
               handed: handed ? typeof handed.levels[0].length : null };
    }""")
    check("a voice rebuilt with Scan on is handed its table as tables, every level its full length and finite",
          rebuilt["handedOk"], str(rebuilt))
    check("and stays finite and sounding", rebuilt["finite"] and rebuilt["peak"] > 0.05 and rebuilt["audible"], str(rebuilt))
    null("a table taken through plain JSON has levels with no length", rebuilt["naive"] is None, str(rebuilt["naive"]))

    hold = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      loadCorpus('Scanned fifth'); await wait(600);
      const calm = [];
      for (let k = 0; k < 10; k++) { await wait(100); calm.push(genSettings().scanHold); }
      // The screen filled: what the meter calls running away.
      const fill = setInterval(() => phosphor.grid.fill(1), 5);
      const held = [];
      for (let k = 0; k < 60; k++) { await wait(100); held.push([genSettings().scanHold, pictureStage.hold, pictureMeter.verdict()]); }
      clearInterval(fill);
      return { calm, held };
    }""")
    last = hold["held"][-1]
    check("a screen full of light is running away, and the hold reins Scan's depth in to a quarter, as the stage's",
          abs(last[0] - 0.25) < 0.01 and abs(last[1] - 0.25) < 1e-9, str(last))
    null("before it, the hold is one", min(hold["calm"]) == 1, str(min(hold["calm"])))

    lyr = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      loadCorpus('Scanned fifth'); await wait(300);
      el.oscScan.value = '0'; el.oscScan.dispatchEvent(new Event('input'));
      midiPanic(); setScreenKeys(true); setMidiMode('poly');
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      for (const n of [48, 55]) midiBytes(new Uint8Array([0x90, n, 100]));
      for (const n of [79, 84]) midiBytes(new Uint8Array([0x90, n, 100]));
      midi.layers.edit = 1; syncLayerPanel();
      el.oscScan.value = '100'; el.oscScan.dispatchEvent(new Event('input'));
      await wait(1500);
      const a = genSettings(0).scan, bScan = genSettings(1).scan;
      if (!layerPictures.engines) return { live: layerPictures.live, a, b: bScan, own: null, other: null };
      scanStep(16);
      const posted = genSettings(1).scanTable;
      const own = scanTables(scanRead(layerPictures.engines[1].cells, scan.paths[1], scan.soft));
      const other = scanTables(scanRead(layerPictures.engines[0].cells, scan.paths[1], scan.soft));
      const d = (x, y) => { let m = 0; for (let i = 0; i < x.levels[0].length; i++) m = Math.max(m, Math.abs(x.levels[0][i] - y.levels[0][i])); return m; };
      const out = { live: layerPictures.live, a, b: bScan, own: posted && own ? d(posted, own) : null,
                    other: posted && other ? d(posted, other) : null };
      for (const n of [48, 55, 79, 84]) midiBytes(new Uint8Array([0x80, n, 0]));
      midi.layers.edit = 0; syncLayerPanel();
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change')); setScreenKeys(false);
      return out;
    }""")
    check("with a split, Depth edits the layer on the panel and B reads its own figure's picture",
          lyr["live"] and lyr["a"] == 0 and lyr["b"] == 1 and lyr["own"] == 0, str(lyr))
    null("B's table against one read from A's picture", lyr["other"] is not None and lyr["other"] > 0.01, str(lyr["other"]))

    # ------------------------------------------------------------------
    print("\n--- the first minute: a moving picture, read back ---")
    FIRST = """async ([preset, scanOn, stopAt, seconds]) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setRunning(true);
      loadCorpus(preset);   // the old library's, as above
      // The picture stage at nought, so what moves the sound here is Scan.
      el.pictureAmount.value = '0'; el.pictureAmount.dispatchEvent(new Event('input', { bubbles: true }));
      if (!scanOn) { el.oscScan.value = '0'; el.oscScan.dispatchEvent(new Event('input')); }
      if (stopAt !== null) setTimeout(() => setRunning(false), stopAt * 1000);
      const out = [], t0 = performance.now();
      while (performance.now() - t0 < seconds * 1000) {
        await wait(250);
        if (!state.running) state.source.tick(performance.now() / 1000);
        const [l] = state.source.getLatestWindow(4096);
        let e = 0, d = 0;
        for (let k = 1; k < l.length; k++) { e += l[k] * l[k]; d += (l[k] - l[k - 1]) ** 2; }
        out.push([(performance.now() - t0) / 1000, Math.sqrt(d / Math.max(e, 1e-12))]);
      }
      setRunning(true);
      el.pictureAmount.value = String(STAGE_DEFAULT); el.pictureAmount.dispatchEvent(new Event('input', { bubbles: true }));
      return out;
    }"""
    moving = p.evaluate(FIRST, ["Scanned fifth", True, None, 6])
    plain = p.evaluate(FIRST, ["Scanned fifth", False, None, 6])
    held = p.evaluate(FIRST, ["Scanned fifth", True, 2, 6])
    sd = lambda series, frm=0: statistics.pstdev([v for t_, v in series if t_ >= frm])
    mean = lambda series, upto: statistics.mean([v for t_, v in series if t_ <= upto])
    print("    brightness: Scan %.4f +- %.4f; without %.4f +- %.4f; held still from 2 s, after 3 s +- %.4f"
          % (statistics.mean(v for _, v in moving), sd(moving), statistics.mean(v for _, v in plain), sd(plain), sd(held, 3)))
    check("a turning fifth read back moves its timbre: the brightness wanders", sd(moving) > 0.004, "%.4f" % sd(moving))
    null("the same fifth without Scan stands still", sd(plain) < 0.001, "%.4f" % sd(plain))
    check("and within three seconds it is plainly not the fifth without Scan",
          abs(mean(moving, 3) - mean(plain, 3)) > 5 * sd(plain, 0) + 0.005,
          "%.4f against %.4f" % (mean(moving, 3), mean(plain, 3)))
    check("held still - the screen stopped - Scan is an ordinary tone: the brightness stands", sd(held, 3) < sd(moving) / 5,
          "%.4f against %.4f running" % (sd(held, 3), sd(moving)))
    null("the held run, before it stopped, was moving", sd([x for x in held if x[0] < 2]) > 0.001,
         "%.4f" % sd([x for x in held if x[0] < 2]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

    # ------------------------------------------------------------------
    print("\n--- on the site's instrument, and the compiled generator ---")
    # The site as a visitor opens it: the compiled instrument, which reads
    # its own grid at its own picture frame. Its sound read off its picture
    # lanes, which are what is heard, as stagetest.py reads it; the picture
    # stage at nought by the slider, so what moves the sound is Scan; and the
    # depth at nought by the slider as the null, sent the way a hand's is.
    SITE = """async ([scanOn, seconds]) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      // The old library's Scanned fifth, from before P8g, as on the page above.
      loadCorpus('Scanned fifth'); await wait(400);
      el.pictureAmount.value = '0'; el.pictureAmount.dispatchEvent(new Event('input', { bubbles: true }));
      if (!scanOn) { el.oscScan.value = '0'; el.oscScan.dispatchEvent(new Event('input', { bubbles: true })); }
      await wait(600);
      const out = [], t0 = performance.now();
      while (performance.now() - t0 < seconds * 1000) {
        await wait(250);
        const [l] = state.source.getLatestWindow(4096);
        let e = 0, d = 0;
        for (let k = 1; k < l.length; k++) { e += l[k] * l[k]; d += (l[k] - l[k - 1]) ** 2; }
        out.push([(performance.now() - t0) / 1000, e > 1e-9 ? Math.sqrt(d / e) : 0, Math.sqrt(e / l.length)]);
      }
      return { out, host: BRAIN_IN_CORE && state.source.kind === 'host' };
    }"""
    def site(query, scan_on):
        bb = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
        pp = bb.new_page(viewport={"width": 1400, "height": 900})
        errs = []
        pp.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
        pp.goto(f"file://{ART}/scope.html" + query); pp.wait_for_timeout(1200)
        corpus.install(pp)
        if pp.locator("#helpClose").is_visible(): pp.locator("#helpClose").click()
        pp.locator("#trace").click(position={"x": 5, "y": 5})   # the press a browser waits for
        pp.wait_for_timeout(800)
        got = pp.evaluate(SITE, [scan_on, 5])
        got["errors"] = errs
        bb.close()
        return got
    on, off = site("", True), site("", False)
    son, soff = sd([(t_, v) for t_, v, _ in on["out"]]), sd([(t_, v) for t_, v, _ in off["out"]])
    print("    site: brightness with Scan +- %.4f, without +- %.4f; loud %.3f" % (son, soff, max(r for _, _, r in on["out"])))
    check("on the site's instrument, the turning fifth read back moves its timbre",
          on["host"] and son > 0.004 and max(r for _, _, r in on["out"]) > 0.02, "%.4f, on the instrument %s" % (son, on["host"]))
    null("and with Depth at nought there it stands still", off["host"] and soff < 0.001, "%.4f" % soff)
    # The page's brain on the compiled generator: the tables go to the
    # module as numbers (scope_scan), and the module plays them.
    gen_on, gen_off = site("?brain=js", True), site("?brain=js", False)
    gon, goff = sd([(t_, v) for t_, v, _ in gen_on["out"]]), sd([(t_, v) for t_, v, _ in gen_off["out"]])
    print("    page's brain, compiled generator: with Scan +- %.4f, without +- %.4f" % (gon, goff))
    check("the page's brain on the compiled generator sends it the tables, and it plays them", gon > 0.004, "%.4f" % gon)
    null("and with Depth at nought it stands still", goff < 0.001, "%.4f" % goff)
    check("no page errors on the site", not (on["errors"] + off["errors"] + gen_on["errors"] + gen_off["errors"]),
          "; ".join((on["errors"] + off["errors"] + gen_on["errors"] + gen_off["errors"])[:3]))

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("everything passes")
