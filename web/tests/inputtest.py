"""Live audio into the generator (Stage J3).

Against the way each would fail:

- an input that leaks in when the mode is off, or at a depth of nought;
- FM that is not a factor on the rate: a steady input of a quarter at full
  depth must draw exactly what twice the pitch draws, and a deep enough
  negative input must stop the waveform rather than run it backwards;
- a ride that shifts the figure instead of scaling it: every sample is the
  plain one times (1 + 2 depth x), to float precision;
- a clock that does not lock: fed 100 Hz, a waveform at 330 must repeat
  every 441 samples exactly, where unclocked it does not; and when the input
  stops, the generator must run free at its own pitch again, not stall;

Until G2 the FM and the clock were held on a figure as well, a star traced
40 times a second; the figures went with the drawings, and the waveform is
held to the same laws.
- a worklet that ignores its input;
- on the page: an input opened when it cannot reach the generator, or left
  open when it is no longer wanted.
"""
# On the site's default since stage 5, step 3, batch 5 (13 Nov). It opened
# ?brain=js until then. The six numbers rows - off is off, the ride, FM, the
# stop, the clock and its restart - drove the page's own makeGeneratorCore
# with an input; they are core/tests/pieces/input.py's now, the core's
# Generator through generator_cpp with the same inputs. Two page rows read the
# page brain's own rule that an input opens only while it can be heard and is
# let go of when its mode goes off (`liveStreams`, `inputConnected`), which
# the instrument does not have - it hears its input always - and went with
# that brain: "not heard, it says so and opens nothing" and "switched off, the
# input is let go of and disconnected". What is left is the face on the site:
# the input opened and the instrument's figure riding on it, and the code.
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

STUB = """
  window.__wait = (ms) => new Promise((r) => setTimeout(r, ms));
  // How many times the page asked for a microphone.
  window.__opened = 0;
  // The live device: a 4 Hz sine at a half, so a ride at full depth swings
  // the generator's size between nought and twice.
  window.__device = () => {
    const ctx = new AudioContext();
    const dest = ctx.createMediaStreamDestination(), a = ctx.createOscillator(), g = ctx.createGain();
    a.frequency.value = 4; g.gain.value = 0.5; a.connect(g); g.connect(dest); a.start();
    navigator.mediaDevices.getUserMedia = () => { window.__opened++; return Promise.resolve(dest.stream); };
  };
"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.add_init_script(STUB)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    # The ride, the FM, the stop and the clock: core/tests/pieces/input.py (batch 5).

    print("\n--- on the site ---")
    # On ?brain=js this read the page's own generator, its open streams and
    # its `inputConnected`; here the instrument, which the site's input
    # reaches through the face, and the figure it draws (the face's ring,
    # which on the default is the instrument's lanes). Mono by its button and
    # a held note, since the site waits for one (10 Nov). Read at a depth of
    # nought first - the null: the same reading with the input not riding.
    PAGE = """async (depth) => {
      __device();
      el.midiMono.click();
      el.inputMode.value = '2'; el.inputMode.dispatchEvent(new Event('change'));
      el.inputDepth.value = String(depth); el.inputDepth.dispatchEvent(new Event('input'));
      midiNoteOn(57, 127);
      await __wait(1500);
      const peaks = [];
      for (let k = 0; k < 16; k++) {
        const w = state.source.getLatestWindow(441)[0];
        peaks.push(Math.max(...w.map(Math.abs))); await __wait(30);
      }
      const code = snapshot();
      midiNoteOff(57);
      return { where: el.inputWhere.textContent, opened: __opened, kind: state.source.kind,
               low: Math.min(...peaks), high: Math.max(...peaks), code: [code.inputMode, code.inputDepth] };
    }"""
    still = p.evaluate(PAGE, 0)
    heard = p.evaluate(PAGE, 100)
    print("    at nought %s\n    at full %s" % (still, heard))
    check("the input is opened, the face says it goes into the generator, and the instrument's figure swings with it from near nought to twice",
          heard["opened"] >= 1 and heard["kind"] == "host" and heard["where"] == "Your input, into the generator."
          and heard["high"] > 3 * heard["low"] and heard["high"] > 0.3, str(heard))
    check("null: ridden at a depth of nought it does not swing", not (still["high"] > 3 * still["low"]), str(still))
    check("and a setup code carries the mode and the depth", heard["code"] == [2, 100], str(heard["code"]))
    check("null: and the code read at nought says nought", still["code"] == [2, 0], str(still["code"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
