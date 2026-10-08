"""S10: what the generator's voices cost, and what is given up when it is too
much.

Every feature of the voice had a cost check of its own and passed it; nothing
had measured them together. Sixteen held notes over two layers with seven
copies, FM, sync, a sub, drive and fold at four times, the crusher and the
filter came to 1.7 seconds of work a second - a glitch on any machine - and
releases in flight could double the voices. So the core costs each voice by
a model and, over VOICE_BUDGET, gives things up in a stated order. Against the
ways that fails:

- the governed worst case still over real time: measured, with every
  feature on both layers and a full set of releases in flight, it has to run
  in under half of real time;
- a model that has the relative costs wrong, so the governor spends the
  budget on the wrong thing: each feature's measured cost over its modelled
  cost, held near the median of all of them - which is the machine's speed,
  and divides out;
- the order broken: the four times given up only before unison, unison only
  before a voice, releases before held notes, undrawn notes before drawn -
  each stage seen to happen somewhere in the sweep, so none of it is vacuous;
- caps that creep back up as releases die away, re-phasing a held chord for
  no reason anyone could hear; and caps that never come back when the chord
  or the settings change;
- a voice let go with a step: at one and two hertz the signal barely moves
  from one sample to the next, so a cut that steps is a hundred times the
  largest slope and a faded one is not;
- the readout silent while the voice is held back, or talking when nothing
  is;
- a budget so tight it bites ordinary playing: no preset gives anything up
  under a full chord of eight on each layer.
"""
# On ?brain=js (5m): this suite reads the page's own brain - genSet called
# directly - which core/tests/parity.py holds the instrument to, sample for
# sample. The instrument, the site's default since 5m, is braintest.py's and
# hosttest.py's.
import math, os, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

RATE = 44100
BH = (0.35875, 0.48829, 0.14128, 0.01168)


def off_grid(x, f0, top=10000):
    """The loudest thing off the harmonics of f0 below `top`, in dB under the
    loudest thing of all: what drive aliases back to. As `drivetest.py`."""
    x = np.asarray(x, dtype=float)
    i = np.arange(len(x))
    w = (BH[0] - BH[1] * np.cos(2 * np.pi * i / len(x)) + BH[2] * np.cos(4 * np.pi * i / len(x))
         - BH[3] * np.cos(6 * np.pi * i / len(x)))
    spec = np.abs(np.fft.rfft(x * w))
    hz = np.arange(len(spec)) * RATE / len(x)
    grid = np.zeros(len(spec), dtype=bool)
    grid[:6] = True
    k = 1
    while k * f0 < RATE / 2:
        grid |= np.abs(hz - k * f0) < 4 * RATE / len(x)
        k += 1
    return 20 * math.log10(max(spec[~grid & (hz < top)].max(), 1e-15) / spec.max())


fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


# Everything on: the case that measured 1.7 seconds a second.
ALL = {"shape": "drawbars", "unison": 7, "fmIndex": 2, "syncRatio": 1.5, "subLevel": 0.5, "drive": 0.5,
       "fold": 0.3, "vcfType": 1, "vcfEnv": 2, "vcfTrack": 1, "crushBits": 6, "shapeOS": 4}

HELPERS = """
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const make = () => { const c = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]); c.set('mode', 'wave'); return c; };
  // Eight notes a minor third apart; the lowest drawn on X and the highest on Y.
  const chord = (base, hz) => { const v = []; for (let k = 0; k < 8; k++) v.push({ note: base + k * 3,
    freq: hz ? hz * (1 + k / 8) : 440 * Math.pow(2, (base + k * 3 - 69) / 12), velocity: 1,
    role: k === 0 ? 'x' : k === 7 ? 'y' : 'u' }); return v; };
  const bufs = (n) => [0, 1, 2, 3, 4, 5].map(() => new Float32Array(n));
  const run = (core, n) => { const b = bufs(n); core.block(b[0], b[1], n, b[2], b[3], b[4], b[5]); return b; };
  // The best of three seconds: what the code costs, rather than what else
  // the machine was doing during one of them.
  const second = (core) => { const b = bufs(44100); let best = Infinity;
    for (let r = 0; r < 3; r++) { const t0 = performance.now(); core.block(b[0], b[1], 44100, b[2], b[3], b[4], b[5]);
      best = Math.min(best, performance.now() - t0); } return best; };
  const setAll = (core, cfg) => { for (const layer of [0, 1]) for (const [k, v] of Object.entries(cfg)) core.set(k, v, layer); };
"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    p = b.new_page()
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html?brain=js"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    print("\n--- the worst case, governed ---")
    worst = p.evaluate("""(ALL) => {""" + HELPERS + """
      const core = make();
      setAll(core, ALL);
      for (const layer of [0, 1]) core.set('releaseMs', 5000, layer);
      // A chord, let go into long releases, and a second chord over them:
      // thirty-two voices asked for.
      core.set('voices', chord(36)); core.set('voices', chord(36), 1); run(core, 4410);
      core.set('voices', chord(60)); core.set('voices', chord(60), 1); run(core, 4410);
      const ms = second(core);
      return { ms, budget: core.budget, left: core.voices.length + core.voicesB.length };
    }""", ALL)
    print("    one second of it: %.0f ms, the model's %.0f of %d; %s" % (worst["ms"], worst["budget"]["units"], worst["budget"]["most"], worst["budget"]))
    # Ungoverned, the same case measured 1.7 s alone; the limit is the one
    # the other cost checks use, half of real time.
    check("sixteen held notes and sixteen releasing, everything on, run in under half of real time",
          worst["ms"] < 500, "%.0f ms" % worst["ms"])
    check("and the model says the budget holds", worst["budget"]["units"] <= worst["budget"]["most"], str(worst["budget"]))

    print("\n--- the model against the machine ---")
    # Each case with as many voices as keep it under the budget, so what is
    # measured is what was asked, not what the governor left of it.
    CASES = {
        "saw": {"shape": "ramp"}, "sine": {"shape": "sine"}, "pulse": {"shape": "pulse"},
        "morph": {"shape": "morph", "morph": 1.5}, "drawbars": {"shape": "drawbars"},
        "wavetable": {"shape": "wavetable"}, "drawn": {"shape": "drawn"}, "pink": {"shape": "pink"},
        "saw x7": {"shape": "ramp", "unison": 7}, "morph x7": {"shape": "morph", "morph": 1.5, "unison": 7},
        "drawbars x7": {"shape": "drawbars", "unison": 7}, "pulse x7": {"shape": "pulse", "unison": 7},
        "saw x7 fm": {"shape": "ramp", "unison": 7, "fmIndex": 2},
        "saw x7 sync": {"shape": "ramp", "unison": 7, "syncRatio": 1.5},
        "saw x7 ring sub": {"shape": "ramp", "unison": 7, "ringMix": 0.5, "subLevel": 0.5},
        "drive 2x": {"shape": "ramp", "drive": 0.5}, "drive 4x": {"shape": "ramp", "drive": 0.5, "shapeOS": 4},
        "filter": {"shape": "ramp", "vcfType": 1, "vcfEnv": 2}, "plane 4x": {"shape": "ramp", "planeMirror": 3,
        "planeLimit": 1, "planeRadius": 0.3, "planeOS": 4},
        "everything": ALL,
    }
    model = p.evaluate("""(CASES) => {""" + HELPERS + """
      const out = {};
      for (const [name, cfg] of Object.entries(CASES)) {
        // Found by asking the model, one voice a layer at a time.
        let per = 1;
        for (let k = 1; k <= 8; k++) {
          const probe = make(); setAll(probe, cfg);
          probe.set('voices', chord(48).slice(0, k)); probe.set('voices', chord(48).slice(0, k), 1); run(probe, 128);
          const b = probe.budget;
          if (b.unison[0] < b.asked[0] || b.factor < b.askedFactor || b.silenced > 0) break;
          per = k;
        }
        const core = make(); setAll(core, cfg);
        core.set('voices', chord(48).slice(0, per)); core.set('voices', chord(48).slice(0, per), 1); run(core, 4410);
        const b = core.budget;
        out[name] = { per, ms: second(core), units: b.units, whole: b.unison[0] === b.asked[0] && b.factor === b.askedFactor && b.silenced === 0 };
      }
      return out;
    }""", CASES)
    ratios = {k: v["ms"] / v["units"] for k, v in model.items()}
    mid = sorted(ratios.values())[len(ratios) // 2]
    for k, v in model.items():
        print("    %-16s %d a layer  %6.1f ms  model %6.1f   %.2f of the median" % (k, v["per"], v["ms"], v["units"], ratios[k] / mid))
    check("every case was measured as asked, the governor leaving it whole",
          all(v["whole"] for v in model.values()), str([k for k, v in model.items() if not v["whole"]]))
    # From half to 1.6 times the median, and lopsided on purpose: a feature
    # costed dearer than it is only gives up a copy early, while one costed
    # cheaper is a glitch. Measured, the spread is 0.6 to 1.5 from run to run
    # - noise is dearer in the model than on the machine - and the morph
    # costed as a saw is 2.5.
    off = {k: round(r / mid, 2) for k, r in ratios.items() if not 0.5 <= r / mid <= 1.6}
    check("the model has each feature's cost right relative to the others, from half to 1.6 times the median",
          off == {}, str(off))
    print("    a unit is %.2f ms of work a second on this machine" % mid)

    print("\n--- what is given up, and in what order ---")
    order = p.evaluate("""(ALL) => {""" + HELPERS + """
      const out = [];
      for (let k = 1; k <= 8; k++) {
        const core = make(); setAll(core, ALL);
        core.set('voices', chord(48).slice(0, k)); core.set('voices', chord(60).slice(0, k), 1); run(core, 128);
        const b = core.budget;
        const cut = core.voices.concat(core.voicesB).filter((v) => v.cut);
        const undrawnLeft = core.voices.concat(core.voicesB)
          .filter((v) => v.held && !v.cut && v.gains[0] === 0 && v.gains[1] === 0).length;
        out.push({ k, factor: b.factor, unison: b.unison, silenced: b.silenced, cut: cut.length, undrawnLeft,
                   drawnCut: cut.filter((v) => v.gains[0] > 0 || v.gains[1] > 0).length });
      }
      return out;
    }""", ALL)
    for o in order: print("    %d a layer: %dx, unison %s, %d held let go (%d drawn)" % (o["k"], o["factor"], o["unison"], o["silenced"], o["drawnCut"]))
    check("one note a layer, everything on, gives up nothing", order[0]["factor"] == 4 and order[0]["unison"] == [7, 7]
          and order[0]["silenced"] == 0, str(order[0]))
    check("unison is only thinned once the four times has gone",
          all(o["factor"] == 2 for o in order if o["unison"] != [7, 7]), str(order))
    check("a held note is only let go once unison is down to one on both layers",
          all(o["unison"] == [1, 1] for o in order if o["silenced"] > 0), str(order))
    check("and a drawn note only once every undrawn one has gone",
          all(o["undrawnLeft"] == 0 for o in order if o["drawnCut"] > 0), str(order))
    check("each stage is reached somewhere between one note a layer and eight",
          any(o["factor"] == 2 for o in order) and any(o["unison"] != [7, 7] for o in order)
          and any(o["silenced"] > 0 for o in order), str(order))

    # Two chords over releases: one layer without the shaper, where letting
    # some releases go is enough, and both with everything, where every
    # release goes and held notes after them.
    tails = p.evaluate("""(ALL) => {""" + HELPERS + """
      const out = [];
      for (const both of [false, true]) {
        const core = make(); setAll(core, both ? ALL : Object.assign({}, ALL, { drive: 0, fold: 0 }));
        core.set('releaseMs', 5000);
        core.set('voices', chord(36)); run(core, 2205);
        core.set('voices', chord(60)); if (both) core.set('voices', chord(48), 1);
        run(core, 64);
        const v = core.voices.concat(core.voicesB);
        out.push({ released: v.filter((x) => !x.held).length, releasedCut: v.filter((x) => !x.held && x.cut).length,
                   heldCut: v.filter((x) => x.held && x.cut).length });
      }
      return out;
    }""", ALL)
    print("    a chord over the releases of the last, on one layer and on two: %s" % tails)
    check("releases in flight go first: with some let go, no held note is",
          tails[0]["released"] == 8 and 0 < tails[0]["releasedCut"] < 8 and tails[0]["heldCut"] == 0, str(tails[0]))
    check("and a held note goes only once every release has",
          tails[1]["releasedCut"] == tails[1]["released"] == 8 and tails[1]["heldCut"] > 0, str(tails[1]))

    # Given up means given up, not only reported: a hard drive on a 4 kHz
    # note, as a chord of voices all on it and all in step, so the chord is
    # the one voice louder. Two of them keep the four times and alias at the
    # -46 dB drivetest measures there; twelve are over the budget and have to
    # be at twice, -30. A core that reported twice and ran four would read
    # -46 both times.
    drive = p.evaluate("""() => {""" + HELPERS + """
      const out = {};
      for (const count of [2, 12]) {
        const core = make();
        for (const [k, v] of Object.entries({ shape: 'sine', drive: 0.8, shapeOS: 4, amp: 0.05 })) core.set(k, v);
        const v = [];
        for (let k = 0; k < count; k++) v.push({ note: 40 + k, freq: 4000, velocity: 1, role: 'u' });
        core.set('voices', v);
        run(core, 4410);
        const b = run(core, 44100);
        out[count] = { heard: Array.from(b[2]), factor: core.budget.factor, silenced: core.budget.silenced };
      }
      return out;
    }""")
    few, many = off_grid(drive["2"]["heard"], 4000), off_grid(drive["12"]["heard"], 4000)
    print("    two driven voices at 4 kHz: %dx, %.1f dB; twelve: %dx, %.1f dB" % (drive["2"]["factor"], few, drive["12"]["factor"], many))
    check("two voices keep the four times and alias as it does, under -44 dB",
          drive["2"]["factor"] == 4 and few < -44, "%.1f dB" % few)
    check("twelve are held to twice, and alias as twice does - the governor's choice is the one that runs",
          drive["12"]["factor"] == 2 and drive["12"]["silenced"] == 0 and -36 < many < -26, "%.1f dB" % many)

    print("\n--- the caps come down on their own and go up only when asked ---")
    caps = p.evaluate("""(ALL) => {""" + HELPERS + """
      const core = make();
      setAll(core, { shape: 'ramp', unison: 7, fmIndex: 2, syncRatio: 1.5 });
      core.set('releaseMs', 150);
      core.set('voices', chord(36)); run(core, 2205);
      core.set('voices', chord(60)); run(core, 128);
      const crowded = core.budget.unison[0];
      // The releases die away over the next half second; the chord is the
      // same. Then one block more, because the budget is asked once a block:
      // read straight after the half second, it had not been asked since the
      // releases went, and a cap that rose the moment they did passed.
      run(core, 22050); run(core, 128);
      const after = { unison: core.budget.unison[0], voices: core.voices.length };
      // The same chord, struck again: a chord change, so the caps are free.
      core.set('voices', chord(60)); run(core, 128);
      const struck = core.budget.unison[0];
      // And a setting moved: down and back up, with the chord held.
      core.set('voices', chord(36)); run(core, 128); core.set('voices', chord(60)); run(core, 128);
      const crowdedAgain = core.budget.unison[0];
      run(core, 22050);
      core.set('unison', 5); run(core, 128); core.set('unison', 7); run(core, 128);
      const moved = core.budget.unison[0];
      return { crowded, after, struck, crowdedAgain, moved };
    }""", ALL)
    print("    %s" % caps)
    check("with releases in flight, the chord has fewer copies than it asked for",
          caps["crowded"] < 7, str(caps))
    check("and keeps them as the releases die away under the same chord",
          caps["after"]["voices"] == 8 and caps["after"]["unison"] == caps["crowded"], str(caps))
    check("striking the chord again gives them back", caps["struck"] > caps["crowded"], str(caps))
    check("and so does moving the unison asked for", caps["crowdedAgain"] < caps["moved"], str(caps))

    print("\n--- a note let go fades ---")
    fade = p.evaluate("""() => {""" + HELPERS + """
      // Sines at one to two hertz barely move from one sample to the next,
      // so a step is plain. Folded at four times with seven copies and FM,
      // it is dear enough that a chord over releases has some let go.
      const core = make();
      const cfg = { shape: 'sine', unison: 7, fmIndex: 1, fold: 0.3, shapeOS: 4, vcfType: 1, vcfCutoff: 2000,
                    releaseMs: 10000, attackMs: 200 };
      for (const [k, v] of Object.entries(cfg)) core.set(k, v);
      core.set('voices', chord(36, 1)); run(core, 13230);
      core.set('voices', chord(60, 1.3));
      // Counted inside the fade: once it is over, a release let go has been
      // taken out of the pool, and a count after it read nought.
      const first = run(core, 64);
      const cut = core.voices.filter((v) => v.cut).length;
      const rest = run(core, 2141);
      const heard = Array.from(first[2]).concat(Array.from(rest[2]));
      let most = 0, steady = 0;
      for (let i = 1; i < heard.length; i++) most = Math.max(most, Math.abs(heard[i] - heard[i - 1]));
      const c = run(core, 2205);
      for (let i = 1; i < 2205; i++) steady = Math.max(steady, Math.abs(c[2][i] - c[2][i - 1]));
      return { cut, most, steady };
    }""")
    print("    %s" % fade)
    check("a chord over releases has some let go", fade["cut"] > 0, str(fade))
    # Faded over ten milliseconds, two voices move the sum by 0.002 a sample
    # at most; cut in one sample, by what they were worth, 0.3 or more.
    check("and the sum never steps as they go: its largest move a sample stays under 0.01",
          fade["most"] < 0.01, "%.4f, then %.4f" % (fade["most"], fade["steady"]))

    print("\n--- the readout ---")
    said = p.evaluate("""() => [
      budgetSaid({ asked: [7, 5], unison: [3, 5], askedFactor: 4, factor: 2, silenced: 2 }, true),
      budgetSaid({ asked: [7, 1], unison: [4, 1], askedFactor: 2, factor: 2, silenced: 1 }, false),
      budgetSaid({ asked: [7, 7], unison: [7, 7], askedFactor: 4, factor: 4, silenced: 0 }, true),
      budgetSaid(null, false)]""")
    print("    %s" % said)
    check("it names each thing given up, per layer when there are two",
          said[0] == "voice budget: unison A 3 of 7 · shaping at 2× · 2 held notes let go"
          and said[1] == "voice budget: unison 4 of 7 · 1 held note let go", str(said[:2]))
    check("and says nothing when nothing is", said[2] == "" and said[3] == "", str(said[2:]))
    page = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setScreenKeys(true); el.midiPoly.click();
      for (const [k, v] of Object.entries({ shape: 'ramp', unison: 7, fmIndex: 2, syncRatio: 1.5, drive: 0.5, shapeOS: 4 })) genSet(k, v);
      for (let k = 0; k < 8; k++) midiNoteOn(48 + k * 3, 100);
      await wait(500);
      const dear = el.readoutDetail.textContent;
      for (let k = 0; k < 8; k++) midiNoteOff(48 + k * 3);
      genSet('unison', 1); genSet('fmIndex', 0); genSet('syncRatio', 1); genSet('drive', 0); genSet('shapeOS', 2);
      midiNoteOn(60, 100); midiNoteOn(64, 100); midiNoteOn(67, 100);
      await wait(500);
      const cheap = el.readoutDetail.textContent;
      for (const n of [60, 64, 67]) midiNoteOff(n);
      return { dear, cheap };
    }""")
    print("    %s" % page)
    check("playing a dear chord on the page, the readout says what the budget took",
          "voice budget: unison" in page["dear"] and "shaping at 2×" in page["dear"], page["dear"])
    check("and a cheap one says nothing about it", "voice budget" not in page["cheap"], page["cheap"])

    print("\n--- ordinary playing ---")
    presets = p.evaluate("""async () => {""" + HELPERS + """
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const out = { seen: 0, shapes: new Set(), governed: [], dearest: [0, ''] };
      for (const [, list] of PRESETS) for (const [name] of list) {
        applyPreset('b:' + name); await wait(30);
        const layered = midi.layers.mode !== 'off';
        const core = make();
        for (const [k, v] of Object.entries(genSettings())) if (k !== 'voices') core.set(k, v);
        for (const [k, v] of Object.entries(genSettings(1))) if (k !== 'voices') core.set(k, v, 1);
        core.set('mode', 'wave');
        core.set('voices', chord(48)); if (layered) core.set('voices', chord(60), 1);
        run(core, 128);
        const b = core.budget;
        out.seen++; out.shapes.add(genSettings().shape);
        if (b.units > out.dearest[0]) out.dearest = [b.units, name];
        if (b.unison[0] < b.asked[0] || (layered && b.unison[1] < b.asked[1]) || b.factor < b.askedFactor || b.silenced) out.governed.push(name);
      }
      out.shapes = out.shapes.size;
      return out;
    }""")
    print("    %d presets, %d shapes among them; the dearest %s at %.0f" % (presets["seen"], presets["shapes"], presets["dearest"][1], presets["dearest"][0]))
    # The shapes counted because the first version of this scan loaded each
    # preset by its bare name, found none of them, and measured the default
    # tone 169 times - passing, whatever the budget was.
    check("the scan read the presets it names: more than a hundred, in more than six shapes",
          presets["seen"] > 100 and presets["shapes"] > 6, str(presets["shapes"]))
    check("no preset gives anything up under a chord of eight on each layer it plays",
          presets["governed"] == [], str(presets["governed"][:6]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the voices fit the budget, and it gives things up in the order they are missed least")
