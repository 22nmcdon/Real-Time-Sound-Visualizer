"""G1's pulse: a square whose width is a control, and a destination.

What would go wrong, and what is checked for it:

- a pulse that is some other wave. A pulse of width w has its n-th harmonic
  in proportion to |sin(pi n w)| / n, so a quarter has no fourth, eighth or
  twelfth and a third has no third or sixth; the harmonics are held to that
  formula, computed here, with numpy's FFT. A square passes none of it at a
  quarter - it has no second, where this has one at -3 dB;
- a pulse of a half that is not the square, band-limiting included - the
  menu would then have two squares that sound a hair apart;
- a direct current, or a clip. Its middle is taken out and the larger of its
  two excursions is 0.9, at every width from 5 to 95 per cent;
- aliasing: the square's correction at both edges, measured in aliastest.py
  beside the square's own;
- a width the generator never reads, a layer B that plays A's, a source
  that cannot reach it, hard sync that corrects its reset wrongly, a setup
  code that loses it, a panel that shows the row for the wrong shape.

The spectra are on windows a whole number of hertz wide, as in morphtest.py.
"""
# Stage 5, step 3, batch 2 (13 Nov): until then this suite opened ?brain=js
# and drove the page's own JavaScript - waveAt, and a makeGeneratorCore built
# in the page with routes put on its slots by hand. Those numbers (the wave at
# a half and its middle and peak, the harmonics at a quarter, a third and a
# tenth, the width the generator reads and a source moving it, hard sync at
# ratio one, each layer its own width) are asserted on the core now, each
# with its null, in core/tests/pieces/pulse.py, as is a key on Width heard by
# the whole instrument. What is left here is the face, on the site's default
# page and its instrument: the Width row, the slider, a routing on it read
# off the instrument's lanes, the hands and setup codes.
import os, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


def duty(x):
    """How much of the time the wave is above nought: its width, for a pulse
    with its middle taken out."""
    x = np.asarray(x)
    return float((x > 0).mean())


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

    # Here stood, on ?brain=js and the page's own waveAt and generator core:
    # at a half the pulse is the square; its middle nought and its peak 0.9 at
    # every width; a width past an end is the end; the harmonics at a quarter,
    # a third and a tenth against |sin(pi n w)| / n; a core built bare plays a
    # quarter; the duty is the width; a source at full pushes and pulls it and
    # stops at 95; sync at ratio one is the plain pulse a sample late; and A
    # and B each their own width. All core/tests/pieces/pulse.py's now.

    print("\n--- on the panel, and patched ---")
    panel = p.evaluate("""async () => {
      setView('bench'); setBenchTab('play');
      const rows = {};
      for (const shape of ['square', 'morph', 'pulse']) {
        el.shape.value = shape; el.shape.dispatchEvent(new Event('change'));
        rows[shape] = [!el.widthRow.hidden, !el.morphRow.hidden];
      }
      const shown = { reading: el.widthValue.textContent, at: genSettings().width };
      const clipped = [];
      for (const v of [5, 25, 50, 95]) {
        el.width.value = String(v); el.width.dispatchEvent(new Event('input'));
        const r = el.widthValue.getBoundingClientRect(), row = el.widthRow.getBoundingClientRect();
        if (r.right > row.right + 0.5) clipped.push(el.widthValue.textContent);
      }
      const set = { reading: el.widthValue.textContent, at: genSettings().width };
      // And not for a figure, until G2 took the figures.
      return { rows, shown, set, clipped };
    }""")
    print("    %s" % panel)
    check("the Width row is on Play only with Pulse chosen - not the square, not the morph",
          panel["rows"] == {"square": [False, False], "morph": [False, True], "pulse": [True, False]},
          str(panel["rows"]))
    check("it starts at a quarter, says so, and the slider writes the generator",
          panel["shown"] == {"reading": "25%", "at": 0.25} and panel["set"] == {"reading": "95%", "at": 0.95}
          and panel["clipped"] == [], str(panel))

    patched = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.freq.value = '220'; el.freq.dispatchEvent(new Event('input'));
      el.width.value = '25'; el.width.dispatchEvent(new Event('input'));
      // A held source: a key struck as hard as a key goes holds Key, velocity,
      // at one while it is down (a learned controller was this until F4b cut
      // learning). A3 sounds the 220 Hz already set; the depth taken to nought,
      // the key still down, is the controller let go.
      midiRegisterKey(); midiNoteOn(57, 127);
      addRouting('midi.key', 'gen.width');
      const routing = state.modRoutings.find((r) => r.sourceId === 'midi.key');
      routing.amount = 0; touchRoutings();
      await wait(900);
      const down = Array.from(state.source.getLatestWindow(8820)[0]);
      routing.amount = 1; touchRoutings(); await wait(900);
      const up = Array.from(state.source.getLatestWindow(8820)[0]);
      const dest = MOD_DESTS.get('gen.width');
      const out = { down, up, at: genSettings().width, slider: el.width.value, code: snapshot().width,
                    reach: [dest.reach(25, 1), dest.reach(50, 1), dest.reach(50, -1), dest.reach(90, 1)] };
      midiNoteOff(57);
      state.modRoutings = []; touchRoutings();
      return out;
    }""")
    print("    duty with the controller down %.3f, up %.3f; reach %s"
          % (duty(patched["down"]), duty(patched["up"]), patched["reach"]))
    # On ?brain=js the window was the page's own generator's and the width
    # read back the page's (genSettings); on the default the window is the
    # lanes the instrument drew, and the slider, the face's mirror and the
    # code are what the face would send. The sound's half is also
    # core/tests/pieces/pulse.py's, on the instrument natively.
    check("a controller on Width moves the instrument's sound, a quarter to seven tenths, without writing the slider",
          abs(duty(patched["down"]) - 0.25) < 0.02 and abs(duty(patched["up"]) - 0.70) < 0.02
          and patched["at"] == 0.25 and patched["slider"] == "25" and patched["code"] == 25,
          "%.3f, %.3f, slider %s, mirror %s, code %s" % (duty(patched["down"]), duty(patched["up"]), patched["slider"],
                                                         patched["at"], patched["code"]))
    check("null: the routing at nought is not the seven tenths", abs(duty(patched["down"]) - 0.70) >= 0.02,
          "%.3f" % duty(patched["down"]))
    check("full depth is 45 per cent, stopped at 5 and 95",
          patched["reach"] == [70, 95, 5, 95], str(patched["reach"]))

    layers = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.width.value = '30'; el.width.dispatchEvent(new Event('input'));
      // Poly by its button: setMidiMode alone the instrument never hears.
      setScreenKeys(true); el.midiPoly.click();
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(30);
      // The upper hand, its Generator its own (G6: linked, the width would be both hands').
      document.getElementById('editHandB').click(); document.getElementById('linkGen').click(); await wait(30);
      el.shape.value = 'pulse'; el.shape.dispatchEvent(new Event('change'));
      el.width.value = '60'; el.width.dispatchEvent(new Event('input'));
      const whileB = { a: genSettings(0).width, b: genSettings(1).width, reading: el.widthValue.textContent,
                       row: !el.widthRow.hidden };
      document.getElementById('editHandA').click(); await wait(30);
      const code = snapshot();
      const backA = { slider: el.width.value, reading: el.widthValue.textContent,
                      width: code.width, bWidth: code.bWidth };
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change'));
      el.midiDyad.click(); setScreenKeys(false);
      return { whileB, backA };
    }""")
    print("    %s" % layers)
    check("editing B writes B's width and leaves A's",
          layers["whileB"] == {"a": 0.3, "b": 0.6, "reading": "60%", "row": True}, str(layers["whileB"]))
    check("and back on A the slider is A's, with the code carrying both",
          layers["backA"] == {"slider": "30", "reading": "30%", "width": 30, "bWidth": 60}, str(layers["backA"]))

    print("\n--- setup codes ---")
    codes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const read = () => ({ a: genSettings(0).width, b: genSettings(1).width, slider: el.width.value });
      restore({ shape: 'pulse', width: 40 }); await wait(30);
      const one = read();
      restore({ shape: 'pulse', width: 40, bWidth: 70 }); await wait(30);
      const both = read();
      restore({ shape: 'pulse', width: 400, morph: 400 }); await wait(30);
      const far = Object.assign(read(), { morphB: genSettings(1).morph });
      // After a code that set one, so a restore that ignored the field would
      // not pass by standing still on the default.
      restore({ shape: 'pulse', width: 40 }); await wait(30);
      restore({ shape: 'sine' }); await wait(30);
      const old = read();
      return { one, both, far, old };
    }""")
    print("    %s" % codes)
    check("a code's width reaches the slider and the generator, and B takes A's when it has none",
          codes["one"] == {"a": 0.4, "b": 0.4, "slider": "40"}, str(codes["one"]))
    check("and B its own when it has one", codes["both"]["a"] == 0.4 and codes["both"]["b"] == 0.7, str(codes["both"]))
    # On both layers, and for every slider B takes from the code: B's went
    # straight to the generator, and a width of 400 left B at a width of
    # four while A was held to 95 - the check first looked at A alone.
    check("a width past the end loads as the end on both layers, and so does any of B's sliders",
          codes["far"] == {"a": 0.95, "b": 0.95, "slider": "95", "morphB": 3}, str(codes["far"]))
    check("a code from before the pulse loads with a quarter",
          codes["old"] == {"a": 0.25, "b": 0.25, "slider": "25"}, str(codes["old"]))

    # Here stood "a generator built later, from the panel, takes the slider's
    # width on both layers" (?brain=js): the page's source dropped and toTone()
    # building a new one from the panel (generatorFromPanel). Only the page's
    # brain builds a generator; the instrument is made once and takes the
    # width as any field. Gone with stage 5, step 3, batch 2.

    def search(q):
        p.evaluate("(q) => { el.benchSearch.value = q; el.benchSearch.dispatchEvent(new Event('input')); }", q)
        return p.evaluate("""() => Array.from(el.benchResults.querySelectorAll('button'))
          .map((b) => [b.firstChild.textContent, b.querySelector('.crumb').textContent])""")
    p.evaluate("() => { el.shape.value = 'pulse'; el.shape.dispatchEvent(new Event('change')); }")
    pwm = search("pwm")
    check("pwm finds it", ["Width", "Generator"] in pwm, str(pwm[:4]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the pulse is a pulse at every width, and its width is patchable")
