"""The page's key, and the quantiser that takes the generator's pitch to it.

What would go wrong, and what is checked for it:

- a note outside the key getting through. A slow oscillator sweeps the pitch
  over two octaves and every pitch played is checked against the key's notes,
  to the last digit;
- the quantiser working out the note and the generator playing something
  else. The sound's own spectrum is read, not the quantiser's answer;
- chatter: a pitch resting on the line between two notes, with a little
  vibrato on it, flicking between them. Counted;
- stepping faster than the rate limit when something fast is on the pitch;
- the glide not being a glide, or being the other glide;
- a chord's notes, or layer B's, left unquantised; the right channel losing
  the interval when the left is moved;
- the key not reaching the generator, a setup code losing it, a generator
  built later not having it.
"""
import math, os, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

RATE = 44100
BH = [0.35875, 0.48829, 0.14128, 0.01168]
DORIAN_D = {2, 4, 5, 7, 9, 11, 0}
C_MAJOR = {0, 2, 4, 5, 7, 9, 11}

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


def peak_hz(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    i = np.arange(n)
    w = (BH[0] - BH[1] * np.cos(2 * np.pi * i / n)
         + BH[2] * np.cos(4 * np.pi * i / n) - BH[3] * np.cos(6 * np.pi * i / n))
    spec = np.abs(np.fft.rfft(x * w))
    k = int(np.argmax(spec))
    # Parabolic interpolation on the log magnitude, for a fraction of a bin.
    a, b, c = np.log(spec[k - 1] + 1e-30), np.log(spec[k] + 1e-30), np.log(spec[k + 1] + 1e-30)
    return (k + 0.5 * (a - c) / (a - 2 * b + c)) * RATE / n


midi = lambda hz: 69 + 12 * math.log2(hz / 440)

# A core off the page, with a still pair of oscillators unless a test gives
# one something to do; `run` returns what the test asks for.
CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const lfos = [still(), still()];
  if (setup.lfo) Object.assign(lfos[0], setup.lfo);
  const core = makeGeneratorCore(44100, GEN_DESTS.length, lfos);
  core.set('mode', 'wave'); core.set('shape', 'sine'); core.set('amp', 0.9);
  for (const k in setup.tone || {}) core.set(k, setup.tone[k]);
  for (const k in setup.toneB || {}) core.set(k, setup.toneB[k], 1);
  if (setup.routes) core.setRoutes(setup.routes);
  const out = { pitches: [], L: null, R: null, BL: null };
  const block = setup.block || 128, n = setup.n || 44100;
  const L = new Float32Array(block), R = new Float32Array(block);
  const BL = new Float32Array(block), BR = new Float32Array(block);
  const keep = setup.keep ? { L: new Float32Array(n), R: new Float32Array(n), BL: new Float32Array(n) } : null;
  for (let done = 0; done < n; done += block) {
    core.block(L, R, block, null, null, BL, BR);
    out.pitches.push(core.pitch);
    if (keep) { keep.L.set(L, done); keep.R.set(R, done); keep.BL.set(BL, done); }
  }
  if (keep) { out.L = Array.from(keep.L); out.R = Array.from(keep.R); out.BL = Array.from(keep.BL); }
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
    run = lambda setup: p.evaluate(CORE, setup)
    mask = lambda root, scale: p.evaluate("([r, s]) => keyMask(r, s)", [root, scale])
    dorian = mask(2, "dorian")
    major = mask(0, "major")
    freq_slot = 0

    print("\n--- only the key's notes come out ---")
    # An oscillator at a fifth of a hertz sweeping the pitch an octave either
    # side of 293.66 Hz (D4), for five seconds: most of a cycle, two octaves.
    swept = run({"tone": {"freq": 293.66, "qMask": dorian}, "n": 5 * 44100,
                 "lfo": {"rate": 0.2, "depth": 1, "shape": "triangle"},
                 "routes": [{"index": 0, "slot": freq_slot, "amount": 1}]})
    notes = [midi(hz) for hz in swept["pitches"]]
    off_key = [round(m, 3) for m in notes if abs(m - round(m)) > 1e-9 or (round(m) % 12) not in DORIAN_D]
    visited = sorted(set(round(m) for m in notes))
    print("    %d blocks, notes visited %s" % (len(notes), visited))
    check("with D dorian, every pitch played over two octaves is a note of D dorian, exactly",
          off_key == [] and dorian == 0b101010110101, "%d off: %s" % (len(off_key), off_key[:5]))
    check("and it went through the key rather than sitting on one note: twelve or more of them",
          len(visited) >= 12, str(visited))
    unq = run({"tone": {"freq": 293.66}, "n": 5 * 44100,
               "lfo": {"rate": 0.2, "depth": 1, "shape": "triangle"},
               "routes": [{"index": 0, "slot": freq_slot, "amount": 1}]})
    between = sum(1 for hz in unq["pitches"] if abs(midi(hz) - round(midi(hz))) > 0.05)
    check("which is the quantiser's doing: unquantised, the same sweep is between notes nearly throughout",
          between > len(unq["pitches"]) * 0.8, "%d of %d" % (between, len(unq["pitches"])))

    print("\n--- and the sound is the note ---")
    # 225 Hz is 0.39 of a semitone above A3. Read from the samples, so a
    # quantiser whose answer the oscillator ignored would read 225.
    heard = {}
    for label, q in (("chromatic", 4095), ("off", 0), ("C major", major)):
        out = run({"tone": {"freq": 225, "qMask": q, "interval": 7}, "keep": True, "block": 441})
        heard[label] = (round(peak_hz(out["L"]), 2), round(peak_hz(out["R"]), 2))
    print("    left, right: %s" % heard)
    check("225 Hz, quantised chromatically, sounds 220 - A3",
          abs(heard["chromatic"][0] - 220) < 0.05, str(heard["chromatic"]))
    check("off, it stays at 225", abs(heard["off"][0] - 225) < 0.05, str(heard["off"]))
    check("and the right channel keeps its fifth over the moved left: 330",
          abs(heard["chromatic"][1] - 330) < 0.05, str(heard["chromatic"]))

    print("\n--- no chatter on the line between two notes ---")
    # 226.54 Hz is half-way from A3 to B-flat, with a 5 Hz vibrato of a
    # twentieth of a semitone on it: across the line and back ten times a
    # second.
    mid = 220 * 2 ** (0.5 / 12)
    wobble = 0.05 / 12
    rest = run({"tone": {"freq": mid, "qMask": 4095}, "n": 2 * 44100,
                "lfo": {"rate": 5, "depth": 1},
                "routes": [{"index": 0, "slot": freq_slot, "amount": wobble}]})
    changes = sum(1 for a, c in zip(rest["pitches"], rest["pitches"][1:]) if a != c)
    check("a pitch resting on the half-way line with a twentieth of a semitone of vibrato does not flick",
          changes == 0, "%d changes in two seconds" % changes)
    # And with more than the hysteresis, it does step: a quantiser that never
    # moved would pass the check above.
    more = run({"tone": {"freq": mid, "qMask": 4095}, "n": 2 * 44100,
                "lfo": {"rate": 5, "depth": 1},
                "routes": [{"index": 0, "slot": freq_slot, "amount": 0.15 / 12}]})
    stepped = sum(1 for a, c in zip(more["pitches"], more["pitches"][1:]) if a != c)
    check("while three twentieths - past the tenth of a semitone it waits for - does step, on each swing",
          stepped >= 15, "%d changes in two seconds" % stepped)

    print("\n--- never faster than forty steps a second ---")
    # A 200 Hz oscillator half an octave either way: the pitch crosses a note
    # boundary thousands of times a second.
    fast = run({"tone": {"freq": 440, "qMask": 4095}, "n": 2 * 44100, "block": 32,
                "lfo": {"rate": 200, "depth": 1},
                "routes": [{"index": 0, "slot": freq_slot, "amount": 0.5}]})
    steps = sum(1 for a, c in zip(fast["pitches"], fast["pitches"][1:]) if a != c) / 2
    check("with something fast on the pitch it steps at most forty times a second - and does step",
          30 <= steps <= 40, "%.1f steps a second" % steps)

    print("\n--- the glide is its own ---")
    glide = p.evaluate("""() => {
      const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
      const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
      core.set('mode', 'wave'); core.set('shape', 'sine');
      core.set('qMask', 4095); core.set('qGlideMs', 100); core.set('freq', 220);
      const L = new Float32Array(1), R = new Float32Array(1);
      for (let i = 0; i < 4410; i++) core.block(L, R, 1);
      core.set('freq', 261.63);                  // A3 to C4: three semitones
      const at = [];
      for (let i = 0; i < 44100; i++) { core.block(L, R, 1); at.push(69 + 12 * Math.log2(core.pitch / 440)); }
      // How long to get 63 per cent of the way, and where it ends.
      const target = 57 + 3 * (1 - Math.exp(-1));
      const reached = at.findIndex((m) => m >= target);
      return { ms: reached / 44.1, end: at[at.length - 1] };
    }""")
    check("with a glide of 100 ms it slides between steps, 63 per cent of the way in 100 ms",
          abs(glide["ms"] - 100) < 3 and abs(glide["end"] - 60) < 1e-3, str(glide))

    print("\n--- chords, and layer B ---")
    # The keys' own hertz, exactly: 277.18 is a hair flat of C sharp, which
    # is nearer C whichever way a tie goes, and the tie was never tested.
    cs, fs = 440 * 2 ** ((61 - 69) / 12), 440 * 2 ** ((66 - 69) / 12)
    chord = run({"tone": {"qMask": major, "voices": [{"note": 61, "freq": cs, "velocity": 1, "role": "xy"}]},
                 "toneB": {"shape": "sine", "amp": 0.9,
                           "voices": [{"note": 66, "freq": fs, "velocity": 1, "role": "xy"}]},
                 "keep": True, "n": 52920, "block": 441})
    a = peak_hz(chord["L"][8820:])
    bb = peak_hz(chord["BL"][8820:])
    print("    C sharp in A's picture reads %.2f Hz; F sharp in B's %.2f Hz" % (a, bb))
    check("in C major a chord's C sharp is played as C (a tie goes down) and layer B's F sharp as F",
          abs(a - 261.63) < 0.1 and abs(bb - 349.23) < 0.1, "%.2f, %.2f" % (a, bb))

    print("\n--- the panel, and setup codes ---")
    panel = p.evaluate("""() => {
      setView('bench'); setBenchTab('sources');
      const shown = el.keyGroup.offsetHeight > 0;
      // Wide enough for "Major pentatonic", the longest: it was cut to "Chroma".
      const probe = document.createElement('canvas').getContext('2d');
      probe.font = getComputedStyle(el.keyScale).font;
      const need = probe.measureText('Major pentatonic').width + 30;
      const roomy = el.keyScale.getBoundingClientRect().width >= need;
      el.keyRoot.value = '2'; el.keyRoot.dispatchEvent(new Event('change'));
      el.keyScale.value = 'dorian'; el.keyScale.dispatchEvent(new Event('change'));
      const before = genSettings().qMask;
      el.quantise.checked = true; el.quantise.dispatchEvent(new Event('change'));
      const on = genSettings().qMask;
      el.quantiseGlide.value = '80'; el.quantiseGlide.dispatchEvent(new Event('input'));
      const glide = { core: genSettings().qGlideMs, reading: el.quantiseGlideValue.textContent };
      el.quantise.checked = false; el.quantise.dispatchEvent(new Event('change'));
      const off = genSettings().qMask;
      el.quantise.checked = true; el.quantise.dispatchEvent(new Event('change'));
      return { shown, roomy, before, on, glide, off, code: snapshot() };
    }""")
    print("    %s" % {k: v for k, v in panel.items() if k != "code"})
    check("the section is on the Sources tab, and the key reaches the generator only while Quantise is on",
          panel["shown"] and panel["before"] == 0 and panel["on"] == 2741 and panel["off"] == 0, str(panel["on"]))
    check("and so does its glide", panel["glide"] == {"core": 80, "reading": "80 ms"}, str(panel["glide"]))
    check("the scale's menu is wide enough to say the longest scale", panel["roomy"], str(panel["roomy"]))
    code = panel["code"]
    check("a setup code carries the key, the quantiser and its glide",
          (code["keyRoot"], code["keyScale"], code["quant"], code["qGlide"]) == (2, "dorian", True, 80),
          str((code["keyRoot"], code["keyScale"], code["quant"], code["qGlide"])))
    codes = p.evaluate("""async ([code]) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      restore({ keyRoot: 7, keyScale: 'blues', quant: true, qGlide: 40 }); await wait(30);
      const one = { root: el.keyRoot.value, scale: el.keyScale.value, q: el.quantise.checked,
                    mask: genSettings().qMask, glide: genSettings().qGlideMs };
      restore({}); await wait(30);
      const old = { root: state.keyRoot, scale: state.keyScale, q: state.quantise, mask: genSettings().qMask };
      restore(code); await wait(30);
      el.rackSynth.checked = true; await setRackSynth(true); await wait(100);
      const lane = genSettings().qMask;
      el.rackSynth.checked = false; await setRackSynth(false);
      toTone(); await wait(100);
      const tone = genSettings().qMask;
      return { one, old, lane, tone, blues: keyMask(7, 'blues') };
    }""", [code])
    print("    %s" % codes)
    check("restored, a code's key reaches the panel and the generator",
          codes["one"] == {"root": "7", "scale": "blues", "q": True, "mask": codes["blues"], "glide": 40}
          # G blues is G, B-flat, C, D-flat, D and F: pitch classes 7, 10, 0, 1,
          # 2 and 5, which is 1191 as twelve bits.
          and codes["blues"] == 1191, str(codes["one"]))
    check("a code from before the key has C chromatic, quantiser off",
          codes["old"] == {"root": 0, "scale": "chromatic", "q": False, "mask": 0}, str(codes["old"]))
    check("a generator built later - a rack's lane, a new tone - has the key",
          codes["lane"] == 2741 and codes["tone"] == 2741, str((codes["lane"], codes["tone"])))

    def search(q):
        p.evaluate("(q) => { el.benchSearch.value = q; el.benchSearch.dispatchEvent(new Event('input')); }", q)
        return p.evaluate("""() => Array.from(el.benchResults.querySelectorAll('button'))
          .map((b) => [b.firstChild.textContent, b.querySelector('.crumb').textContent])""")
    found = search("quantize")
    check("the American spelling finds it", any("Quantise" in name for name, _ in found), str(found[:3]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the quantiser plays the key, and only the key")
