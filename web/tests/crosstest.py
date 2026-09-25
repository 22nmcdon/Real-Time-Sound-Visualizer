"""Crossings: the picture as a rhythm.

What would go wrong, and what is checked for it:

- the rhythm not being the interval. A just 3:2 figure at 2 Hz must fire the
  X line twenty times and the Y line thirty in ten seconds, every gap the same;
  an equal-tempered one must drift against it at exactly the rate its fifth is
  flat, and the just one not at all;
- a beam idling on a line rattling it, or a line that never fires passing
  that check;
- more than twenty-five notes a second under a noise fixture;
- the notes getting into the picture, being the wrong notes, decaying at the
  wrong rate, or starting with a click;
- the lines not drawn where the beam is measured against, the panel not
  reaching the generator, a setup code losing it.
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


# A core off the page. `fires` records when each line fired, to the block,
# and blocks are 16 samples: a third of a millisecond.
CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('mode', 'wave'); core.set('shape', 'sine'); core.set('amp', 0.9);
  core.set('crossOn', true);
  for (const k in setup.tone) core.set(k, setup.tone[k]);
  const block = 16, n = setup.n;
  const L = new Float32Array(block), R = new Float32Array(block);
  const HL = new Float32Array(block), HR = new Float32Array(block);
  const fires = { x: [], y: [] };
  const keep = setup.keep ? { L: new Float32Array(n), HL: new Float32Array(n) } : null;
  let last = core.crossings;
  for (let done = 0; done < n; done += block) {
    core.block(L, R, block, HL, HR);
    const now = core.crossings;
    if (now.x !== last.x) fires.x.push((done + block) / 44100);
    if (now.y !== last.y) fires.y.push((done + block) / 44100);
    last = now;
    if (keep && done + block <= n) { keep.L.set(L, done); keep.HL.set(HL, done); }
  }
  return { fires, counts: core.crossings,
           L: keep ? Array.from(keep.L) : null, HL: keep ? Array.from(keep.HL) : null };
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
    run = lambda tone, n=int(10.4 * RATE), keep=False: p.evaluate(CORE, {"tone": tone, "n": n, "keep": keep})

    print("\n--- the interval is the rhythm ---")
    # 2 Hz on X and a just fifth on Y, 3 Hz. The X line is crossed going up at
    # every half second; the Y line - the right channel starts a quarter cycle
    # on - at 0.25 s and every third of a second after.
    just = run({"freq": 2, "interval": 7, "just": True})
    fx = [t for t in just["fires"]["x"] if 0.3 <= t < 10.3]
    fy = [t for t in just["fires"]["y"] if 0.3 <= t < 10.3]
    gx, gy = np.diff(fx), np.diff(fy)
    print("    ten seconds: X %d, Y %d; X gaps %.4f-%.4f s, Y gaps %.4f-%.4f s"
          % (len(fx), len(fy), gx.min(), gx.max(), gy.min(), gy.max()))
    check("a just 3:2 figure fires the X line twenty times and the Y line thirty in ten seconds",
          (len(fx), len(fy)) == (20, 30), str((len(fx), len(fy))))
    check("every X gap half a second and every Y gap a third, to the block",
          np.abs(gx - 0.5).max() < 0.0004 and np.abs(gy - 1 / 3).max() < 0.0004,
          "%.5f, %.5f" % (np.abs(gx - 0.5).max(), np.abs(gy - 1 / 3).max()))

    # The same figure in equal temperament: Y at 2 x 2^(7/12) = 2.99661 Hz, so
    # each Y crossing lands a little later against the just grid, by the same
    # amount every cycle. After ten seconds the lag is ten times (1/f - 1/3)
    # per cycle times three cycles a second.
    equal = run({"freq": 2, "interval": 7, "just": False})
    ey = [t for t in equal["fires"]["y"] if 0.3 <= t < 10.3]
    grid = [0.25 + k / 3 for k in range(1, 31)]
    drift_equal = [e - g for e, g in zip(ey, grid)]
    drift_just = [e - g for e, g in zip(fy, grid)]
    f_eq = 2 * 2 ** (7 / 12)
    # Where the equal-tempered Y crossings fall: phase 2*pi*f*t + pi/2 crosses
    # upwards at f*t = 3/4 + k, so t = (0.75 + k) / f.
    want = [(0.75 + k) / f_eq - g for k, g in zip(range(1, 31), grid)]
    print("    Y against the just grid: just %.2f ms, equal %.2f ms after ten seconds (predicted %.2f)"
          % (drift_just[-1] * 1000, drift_equal[-1] * 1000, want[-1] * 1000))
    check("in equal temperament the Y crossings drift against the just grid at the rate the fifth is flat",
          len(ey) == 30 and abs(drift_equal[-1] - want[-1]) < 0.0005 and drift_equal[-1] > 0.010,
          "%.2f ms against %.2f" % (drift_equal[-1] * 1000, want[-1] * 1000))
    check("growing steadily, every crossing a little later than the one before",
          all(b2 >= a2 for a2, b2 in zip(drift_equal, drift_equal[1:])), str([round(d * 1000, 2) for d in drift_equal[:6]]))
    check("while the just figure's do not drift at all",
          max(abs(d) for d in drift_just) < 0.0004, "%.3f ms" % (max(abs(d) for d in drift_just) * 1000))

    print("\n--- a beam on the line does not rattle it ---")
    idle = run({"freq": 2, "amp": 0.03}, n=5 * RATE)
    moving = run({"freq": 2, "amp": 0.1}, n=5 * RATE)
    print("    amplitude 0.03: %s; 0.1: %s" % (idle["counts"], moving["counts"]))
    check("a beam swinging three hundredths either side of the line never fires it",
          idle["counts"] == {"x": 0, "y": 0}, str(idle["counts"]))
    check("while one a tenth either side fires both lines on every swing",
          9 <= moving["counts"]["x"] <= 10 and 9 <= moving["counts"]["y"] <= 10, str(moving["counts"]))
    out_of_reach = run({"freq": 2, "crossX": 0.95, "crossY": -0.5}, n=5 * RATE)
    check("a line beyond the figure is never crossed, and one inside it still is, once a cycle",
          out_of_reach["counts"]["x"] == 0 and 9 <= out_of_reach["counts"]["y"] <= 10,
          str(out_of_reach["counts"]))

    print("\n--- never more than twenty-five a second ---")
    noise = run({"shape": "noise"}, n=4 * RATE)
    per = {k: v / 4 for k, v in noise["counts"].items()}
    check("under noise, each line fires at most twenty-five times a second - and does fire",
          all(20 <= v <= 25 for v in per.values()), str(per))

    print("\n--- the notes: heard, not drawn ---")
    heard = run({"freq": 2, "interval": 7}, n=2 * RATE, keep=True)
    quiet = run({"freq": 2, "interval": 7, "crossOn": False}, n=2 * RATE, keep=True)
    pluck = np.asarray(heard["HL"]) - np.asarray(heard["L"])
    none = np.asarray(quiet["HL"]) - np.asarray(quiet["L"])
    same_picture = heard["L"] == quiet["L"]
    spec, hz = spectrum(pluck)
    near = lambda f: spec[np.abs(hz - f) < 3].max()
    c4, g4, between = near(261.63), near(392.0), near(320.0)
    # Where the peaks are, rather than how far above a gap they stand: notes
    # retriggered two and three times a second have sidebands a hertz apart,
    # and the tails of both reach half-way between them.
    lo, hi = (hz >= 200) & (hz < 330), (hz >= 330) & (hz < 500)
    at_lo, at_hi = float(hz[lo][np.argmax(spec[lo])]), float(hz[hi][np.argmax(spec[hi])])
    print("    loudest %.2f Hz and %.2f Hz; C4 %.0f, G4 %.0f against %.1f half-way" % (at_lo, at_hi, c4, g4, between))
    check("what is heard beyond the picture is the two notes, C4 for X and G4 for Y",
          abs(at_lo - 261.63) < 1 and abs(at_hi - 392.0) < 1 and min(c4, g4) > 20 * between,
          "%.2f, %.2f" % (at_lo, at_hi))
    check("the picture is sample for sample the same with the notes on or off",
          same_picture, "")
    check("and with the crossings off nothing is added to what is heard",
          float(np.abs(none).max()) == 0.0, str(float(np.abs(none).max())))

    # One note on its own: X fires at 1 s on a 1 Hz beam, and Y's line is
    # out of reach. Its envelope after 180 ms, the decay's time constant, is
    # 1/e of its peak; and it rises over 2 ms rather than jumping.
    # 1 Hz, so the first crossing is at a second: armed in the half-cycle
    # below the line and fired coming back up through it.
    single = run({"freq": 1, "crossY": 2, "crossDecayMs": 180, "crossLevel": 1}, n=int(1.6 * RATE), keep=True)
    solo = np.abs(np.asarray(single["HL"]) - np.asarray(single["L"]))
    t0 = int(round(single["fires"]["x"][0] * RATE)) if single["fires"]["x"] else 0
    window = lambda a, b2: solo[t0 + int(a * RATE / 1000): t0 + int(b2 * RATE / 1000)].max()
    ratio = window(185, 195) / window(5, 15)
    steps = np.abs(np.diff(np.asarray(single["HL"]) - np.asarray(single["L"])))
    print("    fired at %.3f s; 180 ms on it is %.3f of its peak (1/e = 0.368); worst step %.4f"
          % (t0 / RATE, ratio, steps.max()))
    check("a note decays to 1/e of its peak in the decay's 180 ms",
          abs(ratio - math.exp(-1)) < 0.02, "%.3f" % ratio)
    # A 261 Hz sine at half level moves at most 2 pi 261.63 / 44100 x 0.5 =
    # 0.0186 a sample. A note that jumped in would step by up to 0.5.
    check("and starts without a click: no sample steps further than the sine itself moves",
          steps.max() < 0.02, "%.4f" % steps.max())

    print("\n--- the panel and the screen ---")
    panel = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setView('bench'); setBenchTab('sources');
      const shown = el.crossGroup.offsetHeight > 0;
      el.crossOn.checked = true; el.crossOn.dispatchEvent(new Event('change'));
      el.crossNoteX.value = '57'; el.crossNoteX.dispatchEvent(new Event('change'));
      el.crossX.value = '37'; el.crossX.dispatchEvent(new Event('input'));
      const core = { on: genSettings().crossOn, hz: Math.round(genSettings().crossHzX * 100) / 100,
                     x: genSettings().crossX, reading: el.crossXValue.textContent };
      // A harmonograph, slow: the count beside the switch climbs.
      el.genMode.value = 'harmonograph'; el.genMode.dispatchEvent(new Event('change'));
      el.crossX.value = '0'; el.crossX.dispatchEvent(new Event('input'));
      await wait(2500);
      const count = el.crossCount.textContent;
      // Heard, the picture and the counts come from the worklet's core: the
      // count has to keep climbing from what it posts back.
      el.genSound.checked = true; el.genSound.dispatchEvent(new Event('change'));
      await wait(700);
      const driver = lfoDriver();
      const from = state.source.crossings;
      await wait(2500);
      const to = state.source.crossings;
      el.genSound.checked = false; el.genSound.dispatchEvent(new Event('change'));
      await wait(200);
      return { shown, core, count, heard: { driver, from, to } };
    }""")
    print("    %s" % panel)
    check("the section is on the Sources tab, and its controls reach the generator",
          panel["shown"] and panel["core"] == {"on": True, "hz": 220.0, "x": 0.37, "reading": "0.37"},
          str(panel["core"]))
    import re
    m = re.match(r"X (\d+) · Y (\d+)", panel["count"])
    check("with a slow harmonograph running, the count beside the switch climbs",
          bool(m) and int(m.group(1)) >= 3 and int(m.group(2)) >= 3, panel["count"])
    h = panel["heard"]
    check("and heard, it climbs from what the worklet posts back",
          h["driver"] == "worklet" and h["to"]["x"] - h["from"]["x"] >= 3
          and h["to"]["y"] - h["from"]["y"] >= 3, str(h))

    # The lines drawn where they are measured: the X line at 0.37 of full
    # scale, on a still, tiny figure so nothing else is in that column.
    column = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setView('scope');
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      el.amp.value = '2'; el.amp.dispatchEvent(new Event('input'));
      el.dispXY.click(); el.persistence.value = '0'; el.persistence.dispatchEvent(new Event('change'));
      el.crossX.value = '37'; el.crossX.dispatchEvent(new Event('input'));
      el.crossY.value = '-37'; el.crossY.dispatchEvent(new Event('input'));
      // Zoomed, so a line placed without the zoom would be somewhere else:
      // at 1x the two are the same number and the check could not tell.
      el.zoom.value = '2'; el.zoom.dispatchEvent(new Event('input'));
      const read = async () => {
        await wait(300);
        // Drawing units to canvas pixels by the context's own transform: the
        // canvas's width over its CSS width is 846/844 here, which put the
        // probe a pixel off the line.
        const ctx = el.trace.getContext('2d'), k = ctx.getTransform().a;
        const scale = plot.w / 2 * state.zoom;
        const x = Math.round((plot.x + plot.w / 2 + 0.37 * gainOf(0) * scale) * k);
        const y = Math.round((plot.y + plot.h / 2 + 0.37 * gainOf(1) * scale) * k);
        // Three pixels across and the strongest of each: a 1 px line at 515.7
        // is anti-aliased over two columns, each at half its ink, and read one
        // column wide it looked like no line at all.
        const col = ctx.getImageData(x - 1, Math.round(plot.y * k), 3, Math.round(plot.h * k)).data;
        const row = ctx.getImageData(Math.round(plot.x * k), y - 1, Math.round(plot.w * k), 3).data;
        const inked = (d, across) => {
          const lines = d.length / 4 / 3; let n = 0;
          for (let j = 0; j < lines; j++) {
            let most = 0;
            for (let c = 0; c < 3; c++) {
              const i = across ? (j * 3 + c) * 4 : (c * lines + j) * 4;
              most = Math.max(most, d[i] - d[i + 2]);
            }
            if (most > 25) n++;
          }
          return n / lines;
        };
        return { col: inked(col, true), row: inked(row, false) };
      };
      const on = await read();
      el.crossOn.checked = false; el.crossOn.dispatchEvent(new Event('change'));
      const off = await read();
      el.crossOn.checked = true; el.crossOn.dispatchEvent(new Event('change'));
      el.rotate.value = '25'; el.rotate.dispatchEvent(new Event('input'));
      const turned = await read();
      el.rotate.value = '0'; el.rotate.dispatchEvent(new Event('input'));
      const zoom = state.zoom;
      el.zoom.value = '0'; el.zoom.dispatchEvent(new Event('input'));
      return { on, off, turned, zoom };
    }""")
    print("    blush in the X line's column and the Y line's row: %s" % column)
    check("the lines are drawn where the beam is measured against them: dashed, half their length inked",
          column["on"]["col"] > 0.35 and column["on"]["row"] > 0.35 and column["zoom"] > 1.3,
          str((column["on"], column["zoom"])))
    check("and not there with the crossings off, or under a rotation",
          column["off"]["col"] < 0.05 and column["off"]["row"] < 0.05
          and column["turned"]["col"] < 0.05, str((column["off"], column["turned"])))

    print("\n--- setup codes ---")
    codes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const read = () => ({ on: genSettings().crossOn, x: genSettings().crossX, y: genSettings().crossY,
        hzY: Math.round(genSettings().crossHzY * 100) / 100, decay: genSettings().crossDecayMs,
        level: genSettings().crossLevel, box: el.crossOn.checked });
      restore({ crossOn: true, crossX: -20, crossY: 45, crossNoteY: 69, crossDecay: 400, crossLevel: 70 });
      await wait(30);
      const one = read();
      const code = snapshot();
      restore({}); await wait(30);
      const old = read();
      restore(code); await wait(30);
      el.rackSynth.checked = true; await setRackSynth(true); await wait(100);
      const lane = genSettings().crossOn;
      el.rackSynth.checked = false; await setRackSynth(false);
      toTone(); await wait(100);
      return { one, old, lane, tone: genSettings().crossOn,
               code: [code.crossOn, code.crossX, code.crossY, code.crossNoteY, code.crossDecay, code.crossLevel] };
    }""")
    print("    %s" % codes)
    check("a code's crossings reach the generator and the switch",
          codes["one"] == {"on": True, "x": -0.2, "y": 0.45, "hzY": 440.0, "decay": 400, "level": 0.7, "box": True},
          str(codes["one"]))
    check("and a code carries them", codes["code"] == [True, -20, 45, 69, 400, 70], str(codes["code"]))
    check("a code from before them has them off, at the defaults",
          codes["old"] == {"on": False, "x": 0, "y": 0, "hzY": 392.0, "decay": 180, "level": 0.4, "box": False},
          str(codes["old"]))
    check("a generator built later - a rack's lane, a new tone - has them",
          codes["lane"] is True and codes["tone"] is True, str((codes["lane"], codes["tone"])))

    def search(q):
        p.evaluate("(q) => { el.benchSearch.value = q; el.benchSearch.dispatchEvent(new Event('input')); }", q)
        return p.evaluate("""() => Array.from(el.benchResults.querySelectorAll('button'))
          .map((b) => [b.firstChild.textContent, b.querySelector('.crumb').textContent])""")
    found = search("polyrhythm")
    check("polyrhythm finds them", any(crumb == "Crossings" for _, crumb in found), str(found[:3]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the interval on the screen is the rhythm in the ears")
