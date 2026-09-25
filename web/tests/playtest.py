"""The drawings as instruments: the pitched harmonograph, and Play the figure.

What would go wrong, and what is checked for it:

- the pitched harmonograph not at the note: its fundamental is measured, and
  its detune heard as what the plan says it is, the beating between strings;
- its ring time not being the time it takes, or the drawing restarting itself
  like the unpitched one and droning;
- a strike clicking: the pendulums let go while they are still sounding,
  and the sample after is compared with the largest step the tone makes by
  itself;
- a key not striking it, or the unpitched harmonograph changing;
- Play the figure not tracing at the note's pitch, or leaking into the kind
  it was not switched on for;
- a setup code losing either.
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


def peak_hz(x):
    spec, hz = spectrum(x)
    k = int(np.argmax(spec[1:])) + 1
    a, b, c = np.log(spec[k - 1] + 1e-30), np.log(spec[k] + 1e-30), np.log(spec[k + 1] + 1e-30)
    return (k + 0.5 * (a - c) / (a - 2 * b + c)) * RATE / len(x)


# A core off the page. `strikeAt` reswings it at that sample.
CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('mode', 'harmonograph'); core.set('amp', 0.8); core.set('interval', 0);
  for (const k in setup.tone) core.set(k, setup.tone[k]);
  core.reswing();
  const n = setup.n, L = new Float32Array(n), R = new Float32Array(n);
  if (setup.strikeAt) {
    core.block(L.subarray(0, setup.strikeAt), R.subarray(0, setup.strikeAt), setup.strikeAt);
    core.reswing();
    core.block(L.subarray(setup.strikeAt), R.subarray(setup.strikeAt), n - setup.strikeAt);
  } else core.block(L, R, n);
  return Array.from(L);
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
    run = lambda tone, n, strikeAt=None: np.asarray(p.evaluate(CORE, {"tone": tone, "n": n, "strikeAt": strikeAt}))

    print("\n--- the pitched harmonograph is a note ---")
    still = run({"pitched": True, "freq": 220, "detune": 0, "ringMs": 4000}, RATE)
    f0 = peak_hz(still)
    cents = 1200 * math.log2(f0 / 220)
    check("its fundamental is the note: 220 Hz, within a cent", abs(cents) < 1, "%.3f Hz, %.2f cents" % (f0, cents))
    # 50 ms windows, 600 ms apart, both after the 10 ms rise: 1/e with a
    # ring of 600 ms and nothing beating. The first draft measured from the
    # very start, where the rise is, and read 0.397.
    rung = run({"pitched": True, "freq": 220, "detune": 0, "ringMs": 600}, int(1.3 * RATE))
    level = lambda a, b2: float(np.sqrt(np.mean(rung[int(a * RATE):int(b2 * RATE)] ** 2)))
    ratio = level(0.65, 0.70) / level(0.05, 0.10)
    check("with a ring of 600 ms it is 1/e of its first level 600 ms on",
          abs(ratio - math.exp(-1)) < 0.02, "%.3f against 0.368" % ratio)
    # The detune as two strings beating: at 220 Hz a detune of 0.004 puts the
    # second pendulum 0.88 Hz up, so the level swells and dies at 0.88 Hz.
    beats = run({"pitched": True, "freq": 220, "detune": 0.004, "ringMs": 100000}, 4 * RATE)
    frames = beats[: (len(beats) // 441) * 441].reshape(-1, 441)
    env = np.sqrt((frames ** 2).mean(axis=1))
    dips = [i for i in range(1, len(env) - 1) if env[i] < env[i - 1] and env[i] <= env[i + 1] and env[i] < 0.2 * env.max()]
    gaps = np.diff(np.asarray(dips) * 0.01)
    print("    beat dips at %s s" % [round(d * 0.01, 2) for d in dips])
    check("its detune is two strings beating: dips every 1/0.88 = 1.136 s",
          len(gaps) >= 2 and np.abs(gaps - 1 / 0.88).max() < 0.03, str(gaps))

    quant = run({"pitched": True, "freq": 225, "detune": 0, "ringMs": 4000, "qMask": 4095}, RATE)
    check("and quantised with the rest of the generator: 225 Hz, chromatic, plucks A3",
          abs(peak_hz(quant) - 220) < 0.05, "%.3f Hz" % peak_hz(quant))

    print("\n--- it rings out and waits ---")
    left = run({"pitched": True, "freq": 220, "detune": 0, "ringMs": 100}, 2 * RATE)
    tail = float(np.abs(left[int(1.0 * RATE):]).max())
    # Decay 2 a second runs down to the restart threshold, 0.015, at
    # ln(1/0.015)/2 = 2.1 s: just before it the drawing is nearly still, just
    # after it has let go again.
    drawing = run({"pitched": False, "decay": 2.0, "swingRate": 2.1}, 3 * RATE)
    dying = float(np.abs(drawing[int(1.75 * RATE):int(2.05 * RATE)]).max())
    restarted = float(np.abs(drawing[int(2.2 * RATE):int(2.7 * RATE)]).max()) / max(dying, 1e-9)
    print("    pitched, after ten rings: %.2e; the drawing, let go again: %.1f times what it had run down to" % (tail, restarted))
    check("pitched, it dies away and stays silent - it does not start itself again and drone",
          tail < 1e-3, "%.2e" % tail)
    check("while the unpitched drawing still lets itself go again once it has run down",
          restarted > 10, "%.1f" % restarted)

    print("\n--- a strike does not click ---")
    # Struck 150 ms in, at full swing, 220 Hz: the tone's own largest step is
    # 2 pi 220 / 44100 x 0.8 = 0.0251 a sample. The relet fade, starting from
    # nothing as the drawing's restart does, would step by up to 0.8.
    # At half a cycle: 33.5 cycles of 220 Hz, 152.27 ms, where the two
    # pendulums sum to -1 of their peak and a strike that put their phases
    # back to nought would land on +1 - a step of twice the level. The first
    # fixture struck at 150 ms, a whole 33 cycles, where a reset changes
    # nothing; the second at 151.1, where by chance it changes 0.02; the
    # mutation pass caught both.
    at = int(round(33.5 / 220 * RATE))
    struck = run({"pitched": True, "freq": 220, "detune": 0, "ringMs": 400}, int(0.4 * RATE), strikeAt=at)
    steps = np.abs(np.diff(struck))
    around = steps[at - 20: at + 20].max()
    # 20 ms windows - 4.4 cycles - since 441 samples is 2.2 cycles and an
    # RMS over a part-cycle is a few per cent off whatever the level.
    before = float(np.sqrt(np.mean(struck[at - 882: at] ** 2)))
    after = float(np.sqrt(np.mean(struck[at + 441: at + 1323] ** 2)))
    print("    largest step near the strike %.4f (the tone's own is 0.0251); level %.3f before, %.3f after"
          % (around, before, after))
    check("a strike while it sounds puts no step in the wave larger than the tone makes by itself",
          around < 0.0255, "%.4f" % around)
    # Full is 0.4 RMS: the two pendulums a quarter turn apart sum to 0.707 of
    # twice one, halved, times the amplitude 0.8 - a peak of 0.566 - and RMS
    # is 0.707 of that. Ten to thirty milliseconds after the strike the ring
    # has taken e^(-20/400).
    full = 0.4 * math.exp(-0.020 / 0.4)
    check("and it is a strike: the level after is back up to full, from what it had decayed to",
          abs(after - full) < 0.03 * full and before < 0.75 * full,
          "%.3f against %.3f, before %.3f" % (after, full, before))

    print("\n--- a key strikes it, from the keyboard ---")
    keyed = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setView('bench'); setBenchTab('play');
      el.genMode.value = 'harmonograph'; el.genMode.dispatchEvent(new Event('change'));
      setScreenKeys(true);
      const off = { row: el.midiPlayRow.hidden, label: el.midiPlayLabel.textContent, pitched: genSettings().pitched };
      el.midiPlay.checked = true; el.midiPlay.dispatchEvent(new Event('change'));
      const on = { pitched: genSettings().pitched, ring: el.ringRow.hidden, swing: el.swingRow.hidden,
                   decay: el.decayRow.hidden };
      el.ringTime.value = '200'; el.ringTime.dispatchEvent(new Event('input'));
      await wait(1500);                                     // let the load's swing die
      const quiet = Math.max(...state.source.getLatestWindow(2205)[0].map(Math.abs));
      midiNoteOn(57, 110); await wait(60);
      const struck = { freq: genSettings().freq, pitch: estimateFrequency(state.source.getLatestWindow(8820)[0], 44100),
                       peak: Math.max(...state.source.getLatestWindow(2205)[0].map(Math.abs)),
                       credit: el.credit.textContent };
      midiNoteOff(57);
      await wait(1500);
      midiNoteOn(64, 110); await wait(60);
      const again = { freq: genSettings().freq, peak: Math.max(...state.source.getLatestWindow(2205)[0].map(Math.abs)) };
      midiNoteOff(64);
      // With notes not playing the harmonograph at all, nothing can strike
      // it, so it is not pitched whatever the play box says.
      el.midiDrive.checked = false; el.midiDrive.dispatchEvent(new Event('change'));
      const undriven = { pitched: genSettings().pitched, box: el.midiPlay.disabled };
      el.midiDrive.checked = true; el.midiDrive.dispatchEvent(new Event('change'));
      el.midiPlay.checked = false; el.midiPlay.dispatchEvent(new Event('change'));
      const undone = { pitched: genSettings().pitched, swing: el.swingRow.hidden };
      setScreenKeys(false);
      return { off, on, quiet, struck, again, undriven, undone };
    }""")
    print("    %s" % keyed)
    check("on the harmonograph the switch says what it does, and starts off",
          keyed["off"] == {"row": False, "label": "Swing at the note's pitch, a plucked voice", "pitched": False},
          str(keyed["off"]))
    check("on, the harmonograph is pitched and shows Ring in place of Swing and Decay",
          keyed["on"] == {"pitched": True, "ring": False, "swing": True, "decay": True}, str(keyed["on"]))
    # The default detune, 0.004, is two strings 0.88 Hz apart at 220, and the
    # window read reaches back into the silence before the key: the pitch is
    # the struck note's, somewhere in that spread, not the 110 or 440 an
    # octave error would give.
    check("A3 strikes it at 220 Hz, from silence, and the credit says so",
          keyed["quiet"] < 0.01 and keyed["struck"]["freq"] == 220 and keyed["struck"]["peak"] > 0.1
          and 219.5 < (keyed["struck"]["pitch"] or 0) < 221.5
          and keyed["struck"]["credit"] == "harmonograph, plucked at 220 Hz", str(keyed["struck"]))
    check("and a second key, after it has rung out, strikes it again at its own pitch",
          abs(keyed["again"]["freq"] - 329.63) < 0.01 and keyed["again"]["peak"] > 0.1, str(keyed["again"]))
    check("with notes not playing the harmonograph it is not pitched, and the box stands aside",
          keyed["undriven"] == {"pitched": False, "box": True}, str(keyed["undriven"]))
    check("off again, it is a drawing again", keyed["undone"] == {"pitched": False, "swing": False},
          str(keyed["undone"]))

    print("\n--- Play the figure ---")
    figure = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.genMode.value = 'figure'; el.genMode.dispatchEvent(new Event('change'));
      el.figure.value = 'Star'; el.figure.dispatchEvent(new Event('change'));
      setScreenKeys(true);
      const label = el.midiPlayLabel.textContent;
      midiNoteOn(57, 110); await wait(100);
      const drawn = genSettings().figureRate;
      midiNoteOff(57);
      el.midiPlay.checked = true; el.midiPlay.dispatchEvent(new Event('change'));
      // Held long enough that the half second read is all at the note: a
      // full second read 600 ms from before it, drawn at 40.
      midiNoteOn(57, 110); await wait(1000);
      const played = { rate: genSettings().figureRate,
                       samples: Array.from(state.source.getLatestWindow(22050)[0]) };
      midiNoteOff(57);
      el.genMode.value = 'wireframe'; el.genMode.dispatchEvent(new Event('change'));
      const wire = { play: el.midiPlay.checked, label: el.midiPlayLabel.textContent };
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      const wave = el.midiPlayRow.hidden;
      setScreenKeys(false);
      return { label, drawn, played, wire, wave };
    }""")
    rate = figure["played"]["rate"]
    heard = peak_hz(figure["played"]["samples"])
    print("    off: traced %.1f times a second; played: %.1f, heard at %.2f Hz; %s"
          % (figure["drawn"], rate, heard, figure["wire"]))
    check("off, a note scales the figure's rate and keeps it a drawing, under 200",
          figure["drawn"] <= 200 and figure["label"] == "Trace the figure at the note's pitch", str(figure["drawn"]))
    # A star's loudest partial is not its trace rate - it puts most of its
    # energy in the fifth - so the check is that every component sits on a
    # multiple of the note, which is what "the shape is the timbre" means.
    spec, hz = spectrum(figure["played"]["samples"])
    strong = hz[spec > spec.max() * 0.05]
    # Within 10 Hz of a multiple counts as on it: the window's own main lobe
    # is 8 Hz either side at these 2 Hz bins, and read to 1 per cent it
    # flagged 436 and 444 - the lobe of 440, not a partial.
    off_grid = [round(f, 1) for f in strong if f > 20 and abs(f - 220 * round(f / 220)) > 10]
    check("on, A3 traces the star 220 times a second, and every partial it makes is on a multiple of 220",
          rate == 220 and not off_grid and len(strong) > 0, "rate %s, off the grid %s" % (rate, off_grid[:5]))
    check("per kind: switched on for the figure, it is still off for the wireframe",
          figure["wire"] == {"play": False, "label": "Trace the solid at the note's pitch"}, str(figure["wire"]))
    check("and the waveform, whose pitch is the note already, has no switch", figure["wave"], "")

    print("\n--- setup codes ---")
    codes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      midi.play.harmonograph = true; midi.play.figure = true;
      el.ringTime.value = '900'; el.ringTime.dispatchEvent(new Event('input'));
      const code = snapshot();
      restore({}); await wait(30);
      const old = { play: { ...midi.play }, ring: genSettings().ringMs };
      restore(Object.assign({}, code, { gen: 'harmonograph' })); await wait(30);
      const back = { play: { ...midi.play }, ring: genSettings().ringMs, pitched: genSettings().pitched,
                     reading: el.ringTimeValue.textContent };
      return { code: [code.midiPlay, code.ring], old, back };
    }""")
    print("    %s" % codes)
    check("a code carries which drawings play at the note's pitch, and the ring",
          codes["code"] == ["harmonograph,figure", 900], str(codes["code"]))
    check("a code from before has none of them, and a ring of 600 ms",
          codes["old"] == {"play": {"harmonograph": False, "figure": False, "wireframe": False}, "ring": 600},
          str(codes["old"]))
    check("restored, the harmonograph is pitched again with its ring",
          codes["back"]["pitched"] is True and codes["back"]["ring"] == 900 and codes["back"]["reading"] == "900 ms",
          str(codes["back"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the drawings play: the harmonograph plucks, and the figure is a timbre")
