"""The saw, reachable at last, and the drawbars.

What would go wrong, and what is checked for it:

- the saw built and tested and still not on the menu, which is how it spent
  three stages. The check listens for the one thing only a saw has among the
  shapes: a second harmonic, half the fundamental, six decibels down;
- a bar at the wrong footage. Each bar alone must be one partial at its own
  multiple and nothing else;
- the 16' bar as a rectified sine. A phase wrapped once a note's cycle folds
  a half-frequency sine over into |sin|, which is an octave UP and a row of
  harmonics - so the check is that 16' alone is 110 Hz and nothing at 220;
- a partial above Nyquist folded back rather than dropped, and dropped with a
  click rather than faded as a note slides up past it;
- the level law: three decibels a step, silent at nought, and however many
  bars are out the wave inside the amplitude;
- a drawbar on the keyboard not reaching the same bar here;
- layer B playing layer A's registration, and the panel mixing the two up;
- a setup code losing the registration, or a code from before the drawbars
  failing to load.

The spectra are numpy's, not the page's, for the reason aliastest.py gives:
agreeing with the page's own analysis would test nothing.
"""
import math, os, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

RATE = 44100
# A second, so every whole-hertz partial lands on a bin. At 32768 samples a
# 220 Hz partial sits half a bin off and its own main lobe spills past the
# window's edge at -55 dB, which read as a bar sounding something else.
N = 44100
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
    near = 4 * RATE / (2 * (len(spec) - 1))
    return spec[np.abs(hz - f) < near].max()


def db(a, b):
    return 20 * math.log10(max(float(a), 1e-15) / max(float(b), 1e-15))


def partials(x):
    """The loudest component's frequency, and everything else as dB under it."""
    spec, hz = spectrum(x)
    top = int(np.argmax(spec))
    near = 4 * RATE / len(x)
    others = spec.copy()
    others[np.abs(hz - hz[top]) < near] = 0
    others[:6] = 0
    return float(hz[top]), db(others.max(), spec[top])


# The core, rendered off the page: the same function the worklet runs, with
# oscillators that do nothing so only the drawbars move anything.
CORE = """([bars, freq, n, extra]) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('mode', 'wave'); core.set('shape', 'drawbars'); core.set('bars', bars);
  core.set('freq', freq); core.set('amp', 0.9); core.set('interval', 0);
  if (extra && extra.routes) core.setRoutes(extra.routes);
  const L = new Float32Array(n), R = new Float32Array(n);
  core.block(L, R, n);
  return Array.from(L);
}"""

FOOT = ["16'", "5 1/3'", "8'", "4'", "2 2/3'", "2'", "1 3/5'", "1 1/3'", "1'"]
MULT = [0.5, 1.5, 1, 2, 3, 4, 5, 6, 8]

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
    core = lambda bars, freq, n=N, extra=None: p.evaluate(CORE, [bars, freq, n, extra])

    print("\n--- the saw is on the menu ---")
    # On a bin, with its harmonics: half a bin off, the window's scalloping
    # put the second harmonic 0.6 dB low and the check failed a real saw.
    def harmonics_of(shape):
        p.evaluate("""(shape) => {
          el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
          el.shape.value = shape; el.shape.dispatchEvent(new Event('change'));
          el.freq.value = '440'; el.freq.dispatchEvent(new Event('input'));
        }""", shape)
        p.wait_for_timeout(1000)
        got = p.evaluate("(n) => Array.from(state.source.getLatestWindow(n)[0])", N)
        spec, hz = spectrum(got)
        one = level_at(spec, hz, 440)
        return db(level_at(spec, hz, 880), one), db(level_at(spec, hz, 1320), one)
    menu = p.evaluate("() => Array.from(el.shape.options).map((o) => [o.value, o.textContent])")
    saw2, saw3 = harmonics_of("ramp")
    sq2, _ = harmonics_of("square")
    print("    saw: 2nd %.2f dB, 3rd %.2f dB; square's 2nd %.1f dB" % (saw2, saw3, sq2))
    check("the Shape menu offers the saw and the drawbars",
          ["ramp", "Saw"] in menu and ["drawbars", "Drawbars"] in menu, str(menu))
    check("choosing Saw plays one: the second harmonic is half the first, -6.0 dB, and the third -9.5",
          abs(saw2 - 20 * math.log10(1 / 2)) < 0.5 and abs(saw3 - 20 * math.log10(1 / 3)) < 0.5,
          "%.2f, %.2f" % (saw2, saw3))
    check("which the square it replaced on the menu has none of", sq2 < -40, "%.1f dB" % sq2)

    print("\n--- each bar is one partial, at its own footage ---")
    found = []
    for k in range(9):
        bars = [0] * 9; bars[k] = 8
        f, rest = partials(core(bars, 220))
        found.append((FOOT[k], round(f, 1), round(rest, 1)))
    print("    " + ", ".join("%s %s Hz (rest %s dB)" % row for row in found))
    check("each bar alone is its partial: 110, 330, 220, 440, 660, 880, 1100, 1320, 1760 Hz",
          all(abs(f - 220 * m) < 3 for (_, f, _), m in zip(found, MULT)),
          str([f for _, f, _ in found]))
    check("and nothing else, 100 dB under", all(rest < -100 for _, _, rest in found),
          str([rest for _, _, rest in found]))
    sub = core([8, 0, 0, 0, 0, 0, 0, 0, 0], 220)
    spec, hz = spectrum(sub)
    rect = db(level_at(spec, hz, 220), level_at(spec, hz, 110))
    check("16' is a sine an octave down, not a rectified one an octave up: nothing at 220 Hz",
          rect < -100, "%.1f dB" % rect)

    print("\n--- a partial above Nyquist is left out, and fades on the way ---")
    top = {}
    for k in (5, 7, 8):          # 2' at 16 kHz; 1 1/3' at 24 kHz; 1' at 32 kHz
        bars = [0] * 9; bars[k] = 8
        x = np.asarray(core(bars, 4000, 8192))
        top[FOOT[k]] = float(np.sqrt(np.mean(x * x)))
    print("    rms at 4 kHz: %s" % top)
    check("at 4 kHz the 1' (32 kHz) and 1 1/3' (24 kHz) are silent rather than folded",
          top["1'"] < 1e-9 and top["1 1/3'"] < 1e-9, str(top))
    check("while the 2', at 16 kHz, is all there", abs(top["2'"] - 0.9 / math.sqrt(2)) < 0.01,
          str(top["2'"]))
    full = core([8] * 9, 4000)
    spec, hz = spectrum(full)
    grid = np.zeros(len(spec), dtype=bool)
    grid[:6] = True
    for j in range(1, 12):
        grid |= np.abs(hz - 2000 * j) < 4 * RATE / N
    fold = db(spec[~grid].max(), spec.max())
    check("every bar out at 4 kHz puts nothing between the partials, 100 dB down",
          fold < -100, "%.1f dB" % fold)
    sweep = p.evaluate("""() => {
      // 1' alone, sliding from 2.4 to 2.8 kHz: its partial goes from 19.2 to
      // 22.4 kHz and crosses Nyquist at 2756 Hz. A block's loudest sample,
      // block by block, is the level as it went.
      const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
      const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
      core.set('mode', 'wave'); core.set('shape', 'drawbars');
      core.set('bars', [0, 0, 0, 0, 0, 0, 0, 0, 8]); core.set('amp', 0.9);
      const L = new Float32Array(64), R = new Float32Array(64), peaks = [];
      for (let b = 0; b < 690; b++) {
        core.set('freq', 2400 + 400 * b / 690);
        core.block(L, R, 64);
        let m = 0; for (let i = 0; i < 64; i++) m = Math.max(m, Math.abs(L[i]));
        peaks.push(m);
      }
      let jump = 0;
      for (let i = 1; i < peaks.length; i++) jump = Math.max(jump, Math.abs(peaks[i] - peaks[i - 1]));
      return { first: peaks[0], last: peaks[peaks.length - 1], jump };
    }""")
    print("    %s" % sweep)
    check("sliding up past Nyquist, the top bar fades rather than stepping out",
          sweep["first"] > 0.85 and sweep["last"] < 1e-9 and sweep["jump"] < 0.05, str(sweep))

    print("\n--- the level law ---")
    rms = lambda x: float(np.sqrt(np.mean(np.asarray(x) ** 2)))
    at8 = rms(core([0, 0, 8, 0, 0, 0, 0, 0, 0], 220))
    law = {lv: db(rms(core([0, 0, lv, 0, 0, 0, 0, 0, 0], 220)), at8) for lv in (7, 4, 1)}
    at0 = rms(core([0] * 9, 220))
    print("    8' at 7, 4, 1 against 8: %s dB; at 0 rms %g" % ({k: round(v, 2) for k, v in law.items()}, at0))
    check("three decibels a step: 8' at 7 is -3, at 4 is -12, at 1 is -21",
          all(abs(law[lv] + 3 * (8 - lv)) < 0.05 for lv in law), str(law))
    check("and at nought it is silent", at0 == 0, str(at0))
    peaks = {reg: float(np.max(np.abs(core(bars, 220))))
             for reg, bars in (("one at 8", [0, 0, 8, 0, 0, 0, 0, 0, 0]),
                               ("all nine at 8", [8] * 9),
                               ("88 8000 000", [8, 8, 8, 0, 0, 0, 0, 0, 0]))}
    print("    peaks: %s" % peaks)
    check("one bar at eight is a full-scale sine at the amplitude",
          abs(peaks["one at 8"] - 0.9) < 0.001, str(peaks))
    check("and every bar out stays inside it, rather than being drawn as the clamp",
          peaks["all nine at 8"] <= 0.9 + 1e-6 and peaks["88 8000 000"] <= 0.9 + 1e-6, str(peaks))
    spec1, hz1 = spectrum(core([0, 0, 8, 0, 0, 0, 0, 0, 0], 220))
    spec3, hz3 = spectrum(core([8, 8, 8, 0, 0, 0, 0, 0, 0], 220))
    share = db(level_at(spec3, hz3, 220), level_at(spec1, hz1, 220))
    check("three bars at eight are a third each: the 8' is 9.5 dB under what it is alone",
          abs(share - 20 * math.log10(1 / 3)) < 0.1, "%.2f dB" % share)

    print("\n--- a drawbar on the keyboard, on the same bar here ---")
    patch = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.freq.value = '220'; el.freq.dispatchEvent(new Event('input'));
      el.shape.value = 'drawbars'; el.shape.dispatchEvent(new Event('change'));
      el.bars.value = '008000000'; el.bar0.dispatchEvent(new Event('input'));
      midiControl(21, 0);                      // the bar moves, and is learned
      addRouting('cc.21', 'gen.bar3');
      const routing = state.modRoutings.find((r) => r.sourceId === 'cc.21');
      routing.amount = 1; touchRoutings();
      midiControl(21, 127); await wait(1200);
      const out = Array.from(state.source.getLatestWindow(44100)[0]);
      midiControl(21, 0); await wait(1200);
      const back = Array.from(state.source.getLatestWindow(44100)[0]);
      const dest = MOD_DESTS.get('gen.bar3');
      return { out, back, label: dest.label, reach: [dest.reach(0, 1), dest.reach(8, 1), dest.reach(4, -1)],
               bars: state.source.settings.bars.slice() };
    }""")
    spec, hz = spectrum(patch["out"])
    up = db(level_at(spec, hz, 440), level_at(spec, hz, 220))
    spec, hz = spectrum(patch["back"])
    down = db(level_at(spec, hz, 440), level_at(spec, hz, 220))
    print("    4' against 8': drawn out %.2f dB, pushed in %.1f dB; %s, reach %s"
          % (up, down, patch["label"], patch["reach"]))
    check("a controller on the 4' bar at full draws it out to eight: level with the 8'",
          abs(up) < 0.5, "%.2f dB" % up)
    check("and pushed back in, the 4' is gone", down < -60, "%.1f dB" % down)
    check("the bar's own setting is not written by the controller",
          patch["bars"] == [0, 0, 8, 0, 0, 0, 0, 0, 0], str(patch["bars"]))
    check("each bar is a destination named by its footage, and stops at nought and eight",
          patch["label"] == "Drawbar 4′" and patch["reach"] == [8, 8, 0], str(patch["reach"]))
    p.evaluate("() => { state.modRoutings = []; touchRoutings(); }")

    print("\n--- each layer has its own registration ---")
    layers = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.bars.value = '008740000'; el.bar0.dispatchEvent(new Event('input'));
      setScreenKeys(true); setMidiMode('poly'); el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(30);
      el.midiEditB.click(); await wait(30);
      const title = el.barsTitle.textContent;
      el.shape.value = 'drawbars'; el.shape.dispatchEvent(new Event('change'));
      el.bars.value = '800000000'; el.bar0.dispatchEvent(new Event('input'));
      const whileB = { a: genSettings(0).bars.slice(), b: genSettings(1).bars.slice(), panel: el.bars.value };
      el.midiEditA.click(); await wait(30);
      const backA = { panel: el.bars.value, title: el.barsTitle.textContent, code: snapshot() };
      return { title, whileB, backA: { panel: backA.panel, title: backA.title,
               bars: backA.code.bars, bBars: backA.code.bBars } };
    }""")
    print("    %s" % layers)
    check("editing B, the section says so and writes B's bars, leaving A's",
          layers["title"] == "Drawbars · layer B"
          and layers["whileB"]["b"] == [8, 0, 0, 0, 0, 0, 0, 0, 0]
          and layers["whileB"]["a"] == [0, 0, 8, 7, 4, 0, 0, 0, 0], str(layers["whileB"]))
    check("back on A the sliders are A's again, and the code carries both",
          layers["backA"]["panel"] == "008740000" and layers["backA"]["title"] == "Drawbars"
          and layers["backA"]["bars"] == "008740000" and layers["backA"]["bBars"] == "800000000",
          str(layers["backA"]))
    # The sound: layer B's picture made of B's registration, not A's. A has
    # no 16', so a 110 Hz in B's lanes can only have come from B's bars.
    heard = p.evaluate("""() => {
      const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
      const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
      core.set('mode', 'wave');
      core.set('shape', 'drawbars'); core.set('bars', [0, 0, 8, 0, 0, 0, 0, 0, 0]);
      core.set('shape', 'drawbars', 1); core.set('bars', [8, 0, 0, 0, 0, 0, 0, 0, 0], 1);
      core.set('amp', 0.9, 1);
      // Velocity is a fraction here, as the keyboard hands it over; 127 drove
      // both layers into the clamp and a sine came out square.
      const v = [{ note: 57, freq: 220, velocity: 1, role: 'xy' }];
      core.set('voices', v); core.set('voices', v, 1);
      const n = 52292, L = new Float32Array(n), R = new Float32Array(n);
      const BL = new Float32Array(n), BR = new Float32Array(n);
      core.block(L, R, n, null, null, BL, BR);
      return { a: Array.from(L.subarray(8192)), b: Array.from(BL.subarray(8192)) };
    }""")
    fa, ra = partials(heard["a"])
    fb, rb = partials(heard["b"])
    # And nothing else in either: the loudest partial alone passed with both
    # layers clipped into squares, because a square keeps its fundamental.
    check("and B sounds its own: B's picture is its 16' at 110 Hz while A's is its 8' at 220, each alone",
          abs(fb - 110) < 3 and abs(fa - 220) < 3 and ra < -100 and rb < -100,
          "A %.1f Hz (rest %.0f dB), B %.1f Hz (rest %.0f dB)" % (fa, ra, fb, rb))
    p.evaluate("""() => { el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change'));
                          setMidiMode('dyad'); setScreenKeys(false); }""")

    print("\n--- setup codes ---")
    codes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const read = () => ({ a: genSettings(0).bars.slice(), b: genSettings(1).bars.slice(),
                            panel: el.bars.value });
      restore({ shape: 'drawbars', bars: '888000000' }); await wait(30);
      const jimmy = read();
      restore({ shape: 'drawbars', bars: '888000000', bBars: '000000008' }); await wait(30);
      const both = read();
      restore({ bars: '888000000' }); await wait(30);
      restore({ shape: 'sine' }); await wait(30);
      const old = read();
      // After a code that set one, or a parser that let this through would
      // leave the sliders on the default and pass by standing still.
      restore({ bars: '888000000' }); await wait(30);
      restore({ bars: 'not a registration' }); await wait(30);
      const junk = read();
      return { jimmy, both, old, junk };
    }""")
    print("    %s" % codes)
    J = [8, 8, 8, 0, 0, 0, 0, 0, 0]
    D = [0, 0, 8, 7, 4, 0, 0, 0, 0]
    check("a code's registration reaches the sliders and the generator, and B takes A's when it has none",
          codes["jimmy"] == {"a": J, "b": J, "panel": "888000000"}, str(codes["jimmy"]))
    check("and B its own when it has one",
          codes["both"]["a"] == J and codes["both"]["b"] == [0, 0, 0, 0, 0, 0, 0, 0, 8], str(codes["both"]))
    check("a code from before the drawbars loads with the default, not the last one",
          codes["old"] == {"a": D, "b": D, "panel": "008740000"}, str(codes["old"]))
    check("and one that is not nine digits is not read as some other registration",
          codes["junk"] == {"a": D, "b": D, "panel": "008740000"}, str(codes["junk"]))

    print("\n--- a generator built later ---")
    # Not the default registration, or a generator built with the core's own
    # default instead of the sliders' would look exactly right.
    built = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.bars.value = '888000000'; el.bar0.dispatchEvent(new Event('input'));
      el.rackSynth.checked = true; await setRackSynth(true); await wait(100);
      const lane = { rack: !!genLane(), bars: genSettings().bars.slice() };
      el.rackSynth.checked = false; await setRackSynth(false);
      toTone(); await wait(100);
      const tone = { kind: state.source.kind, a: genSettings().bars.slice(), b: genSettings(1).bars.slice() };
      el.bars.value = '008740000'; el.bar0.dispatchEvent(new Event('input'));
      genSet('bars', [0, 0, 8, 7, 4, 0, 0, 0, 0], 1);
      return { lane, tone };
    }""")
    print("    %s" % built)
    check("a rack's generator lane is built with the sliders' registration, not the core's default",
          built["lane"] == {"rack": True, "bars": J}, str(built["lane"]))
    check("and so is a new test tone, both its layers",
          built["tone"] == {"kind": "tone", "a": J, "b": J}, str(built["tone"]))

    print("\n--- the panel ---")
    panel = p.evaluate("""() => {
      setView('bench'); setBenchTab('play');
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change'));
      const sine = { row: el.barsGoRow.hidden, idle: el.barsGroup.hasAttribute('data-idle'),
                     why: el.barsState.textContent, use: !el.barsUse.hidden };
      el.barsUse.click();
      const used = { shape: el.shape.value, heard: genSettings().shape, row: el.barsGoRow.hidden,
                     text: el.barsGo.textContent, idle: el.barsGroup.hasAttribute('data-idle'),
                     state: el.barsStateRow.hidden };
      el.barsGo.click();
      const went = { tab: document.querySelector('[role=tab][aria-selected=true]').textContent.trim(),
                     shown: el.bar2.offsetParent !== null };
      // Not on the drawbars when the kind changes, or the button is hidden
      // for having been used and a figure offering it would never show.
      el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change'));
      el.genMode.value = 'figure'; el.genMode.dispatchEvent(new Event('change'));
      const figure = { idle: el.barsGroup.hasAttribute('data-idle'), why: el.barsState.textContent,
                       use: !el.barsUse.hidden };
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      return { sine, used, went, figure };
    }""")
    print("    %s" % panel)
    check("with another shape the registration row is not on Play, and the bars say why they are greyed",
          panel["sine"] == {"row": True, "idle": True, "why": "Not playing.", "use": True},
          str(panel["sine"]))
    check("Use drawbars chooses them, and the row under the menu shows the registration",
          panel["used"] == {"shape": "drawbars", "heard": "drawbars", "row": False,
                            "text": "00 8740 000 ›", "idle": False, "state": True}, str(panel["used"]))
    check("pressing it goes to the bars, on the Shape tab",
          panel["went"] == {"tab": "Shape", "shown": True}, str(panel["went"]))
    check("a figure has no waveform to colour, and does not offer to use them",
          panel["figure"]["idle"] and panel["figure"]["why"] == "Only a waveform has drawbars."
          and not panel["figure"]["use"], str(panel["figure"]))

    print("\n--- found by name ---")
    def search(q):
        p.evaluate("(q) => { el.benchSearch.value = q; el.benchSearch.dispatchEvent(new Event('input')); }", q)
        return p.evaluate("""() => Array.from(el.benchResults.querySelectorAll('button'))
          .map((b) => [b.firstChild.textContent, b.querySelector('.crumb').textContent])""")
    hammond = search("hammond")
    saw = search("sawtooth")
    print("    hammond %s; sawtooth %s" % (hammond[:3], saw[:3]))
    # The first result, and a control: the sentence saying why the bars are
    # greyed used to come first, because it was built as a row.
    check("hammond finds the drawbars, and a control first rather than a sentence",
          bool(hammond) and (hammond[0][1] == "Drawbars" and "′" in hammond[0][0]
                             or hammond[0] == ["Shape", "Generator"]), str(hammond[:4]))
    check("and sawtooth the shape menu", ["Shape", "Generator"] in saw, str(saw[:4]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the saw is on the menu and the drawbars are drawbars")
