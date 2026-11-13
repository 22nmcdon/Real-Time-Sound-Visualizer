"""Band-limiting: what the generator would put in the air, and in the pane.

The generator is silent today, which is exactly why this can be checked now: a
picture of a square wave is perfect however it is made, and the moment it is
audible every harmonic above Nyquist folds back to a frequency that is a
multiple of nothing. This page ships a Harmonics and THD preset, so an aliased
generator is the instrument lying in the place it claims to measure.

The floors are numpy's analysis of the core's samples, not the page's, in
core/tests/pieces/alias.py since stage 5 (below): asking the page for a
spectrum and then agreeing with it would test nothing. What is left here is
the page's own analysis, the harmonics pane, read over a square the site's
instrument plays.
"""
# Stage 5, step 3, batch 2 (13 Nov): until then this suite opened ?brain=js
# and called the page's own JavaScript waveAt, cycleTables and lfoStep, and
# read the page's own generator's window. Those numbers - every floor, the
# drawn cycle's tables, the pulse, the LFO shapes and rate, the generator
# passing its step, the four samples a cycle the correction touches - are
# asserted on the core now, each with its null, in core/tests/pieces/alias.py
# (parity runs it; alone, core/tests/pieces/run.py alias). What is left here
# is the harmonics pane, which is the face's, read over the site's instrument
# on the default page.
import math, os, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    # Here stood, on ?brain=js: the nine floors of the square, ramp and
    # triangle and their twenty decibels over the uncorrected waveAt; the
    # drawn square's -90 against its richest table; the pulse's nine; the
    # LFO's square still two values, the ramp and triangle bit for bit, a
    # 2 Hz square LFO two cycles a second; the page's generator's own window
    # at 4 kHz under -40 dB; and the correction touching four samples a cycle.
    # Each is core/tests/pieces/alias.py's now, on the core's waveAt, lfoStep
    # and generator, with a null beside it.

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
    # A note held in Mono, by its button, which the site's instrument hears
    # (the README's rule: setMidiMode alone it does not), so the Frequency
    # slider moves the held note; the square and the level by their controls.
    # On ?brain=js the note was the page's own generator's; here the pane
    # reads the instrument's lanes (null below: the pane with no note is
    # silent, so what it reads is the note the instrument plays).
    # The note first, and the slider only once it sounds: sent together, the
    # slider's move could reach the instrument before the note-on did, which
    # then played its own A4 - 440 Hz, which the pane, reading the bin, still
    # called 431 (13 Nov, one load in three; see the fundamental's check).
    p.evaluate("""() => {
      el.midiMono.click(); midiNoteOn(69, 127);
      el.shape.value = 'square'; el.shape.dispatchEvent(new Event('change'));
      el.amp.value = '100'; el.amp.dispatchEvent(new Event('input'));
    }""")
    p.wait_for_timeout(600)
    p.evaluate("""() => {
      el.freq.value = '431'; el.freq.dispatchEvent(new Event('input'));
      state.panesExtra.harmonics = true; syncPanes();
    }""")
    READ = """() => {
      const h = analyseHarmonics(state.source.sampleRate);
      return h && { thd: h.thd, rel: h.partials.map((q) => Math.round(q.rel * 10) / 10),
                    hz: Math.round(h.hz) };
    }"""
    p.wait_for_timeout(900)
    pane = p.evaluate(READ)
    # What the instrument plays, by numpy off its own lane: the pane names
    # the bin the fundamental fell in (430.66 Hz), which 440 falls in too.
    lane = np.array(p.evaluate("() => Array.from(state.source.getLatestWindow(32768)[0])"))
    state_rate = p.evaluate("() => state.source.sampleRate")
    spec = np.abs(np.fft.rfft(lane * np.blackman(len(lane))))
    played = float(np.argmax(spec[8:]) + 8) * state_rate / len(lane)
    odd = [pane["rel"][k - 1] for k in (3, 5, 7)] if pane else []
    even = [pane["rel"][k - 1] for k in (2, 4, 6, 8)] if pane else []
    want_odd = [20 * math.log10(1 / k) for k in (3, 5, 7)]
    # Until 13 Nov this read the pane's bin alone, to 22 Hz either side, and
    # passed with the instrument at 440: the fixture's race above. Now the
    # instrument has to be playing 431 as well, to a bin of 1.3 Hz.
    check("it finds the fundamental where it was put, and the instrument plays it",
          pane and abs(pane["hz"] - 431) <= 22 and abs(played - 431) < 2,
          "the pane %s, the lane %.1f Hz" % (pane and pane["hz"], played))
    check("null: A4's 440, which the pane's bin would also have called 431, is not what is played",
          abs(played - 440) >= 2, "%.1f Hz" % played)
    # With no pane both lists are empty and all() of nothing is true: these
    # two passed with the pane reading nothing until stage 5 (13 Nov), when
    # the note-off null showed it. Each needs its partials now.
    check("the odd harmonics are the textbook 1/k, to a decibel",
          len(odd) == 3 and all(abs(a - b) < 1.0 for a, b in zip(odd, want_odd)),
          "%s against %s" % (odd, [round(v, 1) for v in want_odd]))
    check("and the even ones are not there",
          len(even) == 4 and all(v < -40 for v in even), str(even))
    # Eight partials of a square: sqrt(1/9 + 1/25 + 1/49) = 41.4%. The whole
    # series is 48.3%, and the pane stops at eight - so a reading near 48 would
    # mean it had found energy that is not a harmonic.
    check("so the distortion figure is the eight-partial one, 41.4%",
          pane and abs(pane["thd"] - 0.414) < 0.02,
          "%.1f%%" % (pane["thd"] * 100 if pane else -1))

    p.evaluate("() => midiNoteOff(69)")
    p.wait_for_timeout(1500)
    quiet = p.evaluate("() => analyseHarmonics(state.source.sampleRate)")
    check("null: with the note let go, the pane finds no fundamental: it was reading the note the instrument played",
          quiet is None, str(quiet and round(quiet["hz"])))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the pane reads the instrument's square as a square")
