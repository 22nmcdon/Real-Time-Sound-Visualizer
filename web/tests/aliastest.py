"""Band-limiting: what the generator would put in the air, and in the pane.

The generator is silent today, which is exactly why this can be checked now: a
picture of a square wave is perfect however it is made, and the moment it is
audible every harmonic above Nyquist folds back to a frequency that is a
multiple of nothing. This page ships a Harmonics and THD preset, so an aliased
generator is the instrument lying in the place it claims to measure.

The analysis here is numpy's, not the page's. Asking the page for a spectrum
and then agreeing with it would test nothing: these are the samples the page
produced, transformed by something that has never heard of it.

The floors asserted below are measured numbers with a couple of decibels of
slack, not aspirations. They are stated in full so a later reader can see what
changed rather than only that something did.
"""
import math, os, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

RATE = 44100
N = 32768
BH = [0.35875, 0.48829, 0.14128, 0.01168]     # the window the page uses too

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


def window(n):
    i = np.arange(n)
    return (BH[0] - BH[1] * np.cos(2 * np.pi * i / n)
            + BH[2] * np.cos(4 * np.pi * i / n) - BH[3] * np.cos(6 * np.pi * i / n))


def alias_floors(samples, f0, rate=RATE, against="fundamental"):
    """Everything that is not a harmonic of f0, in dB below the fundamental.

    Two numbers, because they answer different questions. The worst peak
    anywhere includes whatever lands just under Nyquist, which two-point
    polyBLEP can do least about and nobody can hear; the worst below 10 kHz is
    the one that would be audible and the one the spectrum pane is read at.
    """
    x = np.asarray(samples, dtype=float)
    n = len(x)
    spec = np.abs(np.fft.rfft(x * window(n)))
    hz = np.arange(len(spec)) * rate / n
    near = 4 * rate / n                       # the window's own main lobe

    harmonic = np.zeros(len(spec), dtype=bool)
    harmonic[:6] = True                       # DC, and the skirt around it
    k = 1
    while k * f0 < rate / 2:
        harmonic |= np.abs(hz - k * f0) < near
        k += 1

    # A drawn figure's loudest partial is not the one at its trace rate - a
    # five-pointed star puts most of its energy in the fifth - so those are
    # measured against the loudest component instead. For a waveform the two
    # are the same thing.
    ref = spec.max() if against == "loudest" else spec[np.abs(hz - f0) < near].max()
    db = lambda v: 20 * math.log10(max(float(v), 1e-12) / ref)
    return db(spec[~harmonic].max()), db(spec[~harmonic & (hz < 10000)].max())


# What was measured when this landed, in dB below the fundamental, for the
# audible half of the spectrum. The assertion allows 3 dB of slack on each.
WANT = {
    ("square", 440): -62.1, ("square", 2000): -58.5, ("square", 4000): -46.2,
    ("ramp", 440): -61.1, ("ramp", 2000): -52.4, ("ramp", 4000): -46.2,
    ("triangle", 440): -99.5, ("triangle", 2000): -84.1, ("triangle", 4000): -65.2,
}

RENDER = """([shape, f0, n, rate]) => {
  const inc = TWO_PI * f0 / rate, dt = f0 / rate;
  const limited = [], naive = [];
  let a = 0, c = 0;
  for (let i = 0; i < n; i++) {
    limited.push(waveAt(shape, a, dt)); a += inc; if (a >= TWO_PI) a -= TWO_PI;
    // The same loop with no step is the code as it was before band-limiting,
    // which makes it the control rather than a second implementation to
    // disagree with.
    naive.push(waveAt(shape, c, 0)); c += inc; if (c >= TWO_PI) c -= TWO_PI;
  }
  return { limited, naive };
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

    print("\n--- what the correction is worth ---")
    for shape in ("square", "ramp", "triangle"):
        for f0 in (440, 2000, 4000):
            pair = p.evaluate(RENDER, [shape, f0, N, RATE])
            naive_peak, naive_audible = alias_floors(pair["naive"], f0)
            peak, audible = alias_floors(pair["limited"], f0)
            want = WANT[(shape, f0)]

            check("%s at %d Hz folds back at %.0f dB or less" % (shape, f0, want),
                  audible <= want + 3,
                  "%.1f dB below 10 kHz, %.1f dB anywhere" % (audible, peak))
            check("%s at %d Hz is at least 20 dB better than uncorrected"
                  % (shape, f0), audible - naive_audible <= -20,
                  "was %.1f dB, now %.1f" % (naive_audible, audible))

    print("\n--- the LFOs are left alone ---")
    # A shape is a shape whether it runs at 220 Hz or at a fifth of one, and an
    # oscillator at 0.2 Hz has no aliasing to correct: a correction applied to
    # it would be a dent in the shape it exists to draw.
    lfo = p.evaluate("""() => {
      const square = new Set(), ramp = [], triangle = [];
      for (let i = 0; i < 1000; i++) {
        const phase = i * TWO_PI / 1000;
        square.add(waveAt('square', phase));
        let t = (phase / TWO_PI) % 1; if (t < 0) t += 1;
        ramp.push(Math.abs(waveAt('ramp', phase) - (t * 2 - 1)));
        triangle.push(Math.abs(waveAt('triangle', phase)
                               - (2 / Math.PI) * Math.asin(Math.sin(phase))));
      }
      return { square: Array.from(square).sort(), ramp: Math.max(...ramp),
               triangle: Math.max(...triangle) };
    }""")
    check("a square with no step given is still two values",
          lfo["square"] == [-0.9, 0.9], str(lfo["square"]))
    check("and the ramp and triangle are bit for bit what they were",
          lfo["ramp"] == 0 and lfo["triangle"] == 0,
          "%r, %r" % (lfo["ramp"], lfo["triangle"]))

    rates = p.evaluate("""async () => {
      // The rate an LFO actually runs at, which is the thing this project has
      // got wrong before. Stepped at 1000 a second for one second - and the
      // values it hands back are collected too, because `lfoStep` is the path
      // that would be broken by passing it a step it does not need.
      const lfo = { shape: 'square', rate: 2, depth: 1, phase: 0, held: 0, value: 0 };
      const seen = new Set();
      let crossings = 0, last = lfoStep(lfo, 1000);
      seen.add(last);
      for (let i = 1; i < 1000; i++) {
        const now = lfoStep(lfo, 1000);
        seen.add(now);
        if (now > 0 && last <= 0) crossings++;
        last = now;
      }
      return { crossings, seen: Array.from(seen).sort() };
    }""")
    check("a 2 Hz square LFO still completes two cycles a second",
          rates["crossings"] == 2, "%d cycles" % rates["crossings"])
    check("and steps between two values, with no correction in it",
          rates["seen"] == [-0.9, 0.9], str(rates["seen"]))

    print("\n--- and the generator passes its own step ---")
    # The one that matters. Everything above tests `waveAt`; this tests that
    # `fill` tells it how fast it is running. With that argument left off, the
    # unit checks all pass and the instrument aliases anyway.
    p.evaluate("""() => {
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      el.shape.value = 'square'; el.shape.dispatchEvent(new Event('change'));
      el.freq.value = '4000'; el.freq.dispatchEvent(new Event('input'));
      el.amp.value = '100'; el.amp.dispatchEvent(new Event('input'));
    }""")
    p.wait_for_timeout(1000)          # the ring buffer has to turn over first
    out = p.evaluate("""(n) => Array.from(state.source.getLatestWindow(n)[0])""", N)
    peak, audible = alias_floors(out, 4000)
    check("the generator's own samples are band-limited, not just waveAt",
          audible <= -40, "%.1f dB below 10 kHz, %.1f dB anywhere" % (audible, peak))

    print("\n--- the drawn generators, which polyBLEP cannot reach ---")
    # A figure, a solid and a harmonograph are parametric paths: their
    # discontinuities, where they have any, are at no phase anything knows in
    # advance, so the correction above does not apply to them. The plan's
    # choice was between rendering them at 4x and decimating, or leaving them
    # and stating the limit. Measured, they do not need it: the worst of them
    # is no worse than the corrected square, which is the floor this page has
    # decided to live with. These checks keep that true - a figure added later
    # with a jump in it will say so here.
    def drawn(name, setup, f0, want, settle=1100):
        p.evaluate(setup)
        p.wait_for_timeout(settle)
        got = p.evaluate("(n) => Array.from(state.source.getLatestWindow(n)[0])", N)
        peak, audible = alias_floors(got, f0, against="loudest")
        check("%s stays under %d dB" % (name, want), audible <= want,
              "%.1f dB below 10 kHz, %.1f dB anywhere" % (audible, peak))

    drawn("a star traced 200 times a second", """() => {
      el.genMode.value = 'figure'; el.genMode.dispatchEvent(new Event('change'));
      el.figure.value = 'Star'; el.figure.dispatchEvent(new Event('change'));
      el.figureRate.value = '200'; el.figureRate.dispatchEvent(new Event('input'));
    }""", 200, -70)

    # The butterfly is the longest path of any figure - fifty-seven times the
    # circle's - so it has the most above its trace rate, and it is measured
    # at the fastest rate there is. It is a smooth curve with no corner, and
    # measured at -96.7 dB; held to the star's -70, the figures' floor.
    drawn("a butterfly traced 200 times a second", """() => {
      el.genMode.value = 'figure'; el.genMode.dispatchEvent(new Event('change'));
      el.figure.value = 'Butterfly'; el.figure.dispatchEvent(new Event('change'));
      el.figureRate.value = '200'; el.figureRate.dispatchEvent(new Event('input'));
    }""", 200, -70)

    # Text and an imported drawing: strokes with fast travel between them,
    # the one kind of figure whose path has anything like a jump in it. The
    # travel is continuous, not a step, and measured it costs little: a word
    # at 40 is -89 dB and a drawing -87, held to the figures' -70. At 200 a
    # word is -62 - worse than the star, since "SCOPE" turns forty corners a
    # lap to the star's five, and held to the -42 the solids are, whose
    # corners it has more in common with.
    drawn("a word written 40 times a second", """() => {
      el.genMode.value = 'figure'; el.genMode.dispatchEvent(new Event('change'));
      el.figure.value = 'Text'; el.figure.dispatchEvent(new Event('change'));
      setFigureText('SCOPE'); syncFigurePath();
      el.figureRate.value = '40'; el.figureRate.dispatchEvent(new Event('input'));
    }""", 40, -70)
    drawn("a word written 200 times a second", """() => {
      el.figureRate.value = '200'; el.figureRate.dispatchEvent(new Event('input'));
    }""", 200, -42)
    drawn("an imported drawing at 40", """() => {
      el.figure.value = 'Path'; el.figure.dispatchEvent(new Event('change'));
      setFigurePathD('M 30 80 a 12 9 -20 1 1 0.1 0 M 42 78 L 42 20 C 50 30 62 34 58 52'); syncFigurePath();
      el.figureRate.value = '40'; el.figureRate.dispatchEvent(new Event('input'));
    }""", 40, -70)

    drawn("a cube tumbling at 40", """() => {
      el.genMode.value = 'wireframe'; el.genMode.dispatchEvent(new Event('change'));
      el.model.value = 'Cube'; el.model.dispatchEvent(new Event('change'));
      el.figureRate.value = '40'; el.figureRate.dispatchEvent(new Event('input'));
    }""", 40, -42)

    # The torus and the knot are the solids with the most segments a lap, 144
    # and 210, and so the most corners a second for the beam to turn. Both
    # measured near -52.5 dB, better than the cube, whose corners are
    # sharper; held to the cube's -42, the solids' floor.
    drawn("a torus tumbling at 40", """() => {
      el.genMode.value = 'wireframe'; el.genMode.dispatchEvent(new Event('change'));
      el.model.value = 'Torus'; el.model.dispatchEvent(new Event('change'));
      el.figureRate.value = '40'; el.figureRate.dispatchEvent(new Event('input'));
    }""", 40, -42)
    drawn("a knot tumbling at 40", """() => {
      el.model.value = 'Knot'; el.model.dispatchEvent(new Event('change'));
    }""", 40, -42)

    # The harmonograph's partials are two hertz apart, which no window can
    # separate, so "is this a harmonic" is not a question that can be put to
    # it. It is also not worth putting: a sum of sines at a few hertz has
    # nothing above Nyquist to fold. What can be asked is whether anything
    # lands up high at all.
    p.evaluate("""() => {
      el.genMode.value = 'harmonograph'; el.genMode.dispatchEvent(new Event('change'));
      el.swingRate.value = '21'; el.swingRate.dispatchEvent(new Event('input'));
      state.source.reswing();
    }""")
    p.wait_for_timeout(1100)
    swung = np.asarray(p.evaluate("(n) => Array.from(state.source.getLatestWindow(n)[0])", N))
    spec = np.abs(np.fft.rfft(swung * window(len(swung))))
    hz = np.arange(len(spec)) * RATE / len(swung)
    high = 20 * math.log10(max(float(spec[hz > 1000].max()), 1e-12) / spec.max())
    check("the harmonograph puts nothing above a kilohertz", high < -100,
          "%.1f dB down" % high)

    print("\n--- what it costs the picture ---")
    # The generator is a picture first and will be a sound second, so it is
    # worth stating exactly where the correction lands: one sample either side
    # of each edge and nowhere else. A square has two edges a cycle, so four
    # samples a cycle move and the rest are bit for bit what they were. At
    # 220 Hz that is four samples in two hundred - an edge the screen draws as
    # a vertical line either way.
    touched = p.evaluate("""([f0, rate, n]) => {
      const inc = TWO_PI * f0 / rate, dt = f0 / rate;
      let a = 0, c = 0, moved = 0, worst = 0;
      for (let i = 0; i < n; i++) {
        const x = waveAt('square', a, dt), y = waveAt('square', c, 0);
        if (Math.abs(x - y) > 1e-12) moved++;
        else worst = Math.max(worst, Math.abs(x - y));
        a += inc; c += inc;
        if (a >= TWO_PI) a -= TWO_PI;
        if (c >= TWO_PI) c -= TWO_PI;
      }
      return { moved, worst, cycles: n * f0 / rate };
    }""", [220, RATE, 8192])
    check("the correction touches four samples a cycle and no others",
          abs(touched["moved"] - 4 * touched["cycles"]) <= 4 and touched["worst"] == 0,
          "%d samples over %.1f cycles" % (touched["moved"], touched["cycles"]))

    print("\n--- the pane still reads a square as a square ---")
    # 431 Hz, not 440, and the reason is worth knowing. The pane walks a grid
    # of bins out from whichever bin the fundamental landed in - 21.5 Hz apart
    # at this transform size - and searches two bins either side of each
    # multiple. At 440 the seventh multiple of the fundamental's BIN sits 66 Hz
    # below the seventh harmonic, outside that window, so the pane reads the
    # skirt and comes back about 3 dB low. 431 Hz is twenty bins exactly, so
    # every harmonic lands on one. That is the pane's own resolution and has
    # nothing to do with band-limiting, but it catches anyone who tries this
    # with a round number.
    p.evaluate("""() => {
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      el.shape.value = 'square'; el.shape.dispatchEvent(new Event('change'));
      el.freq.value = '431'; el.freq.dispatchEvent(new Event('input'));
      state.panesExtra.harmonics = true; syncPanes();
    }""")
    p.wait_for_timeout(900)
    pane = p.evaluate("""() => {
      const h = analyseHarmonics(state.source.sampleRate);
      return h && { thd: h.thd, rel: h.partials.map((q) => Math.round(q.rel * 10) / 10),
                    hz: Math.round(h.hz) };
    }""")
    odd = [pane["rel"][k - 1] for k in (3, 5, 7)] if pane else []
    even = [pane["rel"][k - 1] for k in (2, 4, 6, 8)] if pane else []
    want_odd = [20 * math.log10(1 / k) for k in (3, 5, 7)]
    check("it finds the fundamental where it was put",
          pane and abs(pane["hz"] - 431) <= 22, str(pane and pane["hz"]))
    check("the odd harmonics are the textbook 1/k, to a decibel",
          all(abs(a - b) < 1.0 for a, b in zip(odd, want_odd)),
          "%s against %s" % (odd, [round(v, 1) for v in want_odd]))
    check("and the even ones are not there",
          all(v < -40 for v in even), str(even))
    # Eight partials of a square: sqrt(1/9 + 1/25 + 1/49) = 41.4%. The whole
    # series is 48.3%, and the pane stops at eight - so a reading near 48 would
    # mean it had found energy that is not a harmonic.
    check("so the distortion figure is the eight-partial one, 41.4%",
          pane and abs(pane["thd"] - 0.414) < 0.02,
          "%.1f%%" % (pane["thd"] * 100 if pane else -1))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the generator is band-limited")
