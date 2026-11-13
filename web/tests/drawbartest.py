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
# Stage 5, step 3, batch 2 (13 Nov): until then this suite opened ?brain=js
# and read a makeGeneratorCore built in the page, and the page's own
# generator's window after the menu. Those numbers - the saw's and square's
# harmonics, each bar's footage and nothing else, the 16' an octave down, the
# partials past Nyquist silent and fading, the level law, the peaks and
# shares, a key drawing the 4' out, and B's own registration heard - are
# asserted on the core now, each with its null, in core/tests/pieces/
# drawbar.py. What is left here is the face, on the site's default page: the
# menu, a routing's bar left alone, the hands, codes, the panel and search.
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

    print("\n--- the saw is on the menu ---")
    menu = p.evaluate("() => Array.from(el.shape.options).map((o) => [o.value, o.textContent])")
    check("the Shape menu offers the saw and the drawbars",
          ["ramp", "Saw"] in menu and ["drawbars", "Drawbars"] in menu, str(menu))
    # Here stood, on ?brain=js: choosing Saw plays one (its second harmonic
    # -6.0 dB, its third -9.5) and the square none, read off the page's own
    # generator; each bar alone its partial and nothing else 100 dB down; the
    # 16' a sine an octave down; the 1' and 1 1/3' silent at 4 kHz and the 2'
    # all there; nothing between the partials with every bar out; the top bar
    # fading past Nyquist; three decibels a step and silence at nought; one bar
    # full scale, every bar inside it, three bars a third each - all on a
    # makeGeneratorCore built in the page. core/tests/pieces/drawbar.py's now,
    # on the core's generator, with a null beside each.

    print("\n--- a drawbar on the keyboard, on the same bar here ---")
    # On ?brain=js this held a key on the page's brain and read the page's
    # generator's window: the 4' drawn out level with the 8', and gone at
    # depth nought. That sound is core/tests/pieces/drawbar.py's now, through
    # the instrument whole. What stays is the face: the bar's own setting
    # untouched while a key holds a routing on it at full, read off the
    # sliders and the code (on ?brain=js it was the page source's settings,
    # which on the default are only the face's mirror), and the destination.
    patch = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.freq.value = '220'; el.freq.dispatchEvent(new Event('input'));
      el.shape.value = 'drawbars'; el.shape.dispatchEvent(new Event('change'));
      el.bars.value = '008000000'; el.bar0.dispatchEvent(new Event('input'));
      midiRegisterKey(); midiNoteOn(57, 127);
      addRouting('midi.key', 'gen.bar3');
      const routing = state.modRoutings.find((r) => r.sourceId === 'midi.key');
      routing.amount = 1; touchRoutings();
      await wait(1200);
      const held = { panel: el.bars.value, slider: el.bar3.value, code: snapshot().bars, routed: snapshot().mod };
      midiNoteOff(57); state.modRoutings = []; touchRoutings();
      const dest = MOD_DESTS.get('gen.bar3');
      return { held, label: dest.label, reach: [dest.reach(0, 1), dest.reach(8, 1), dest.reach(4, -1)] };
    }""")
    print("    %s" % patch)
    check("the bar's own setting is not written by the controller",
          patch["held"]["panel"] == "008000000" and patch["held"]["slider"] == "0" and patch["held"]["code"] == "008000000",
          str(patch["held"]))
    check("null: the routing was there to write it", "gen.bar3" in str(patch["held"]["routed"]), str(patch["held"]["routed"]))
    check("each bar is a destination named by its footage, and stops at nought and eight",
          patch["label"] == "Drawbar 4\u2032" and patch["reach"] == [8, 8, 0], str(patch["reach"]))
    p.evaluate("() => { state.modRoutings = []; touchRoutings(); }")

    print("\n--- each layer has its own registration ---")
    layers = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.bars.value = '008740000'; el.bar0.dispatchEvent(new Event('input'));
      // Poly by its button: setMidiMode alone the instrument never hears.
      setScreenKeys(true); el.midiPoly.click(); el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(30);
      // The upper hand, and the Generator its own (G6: linked, the drawbars would be both hands').
      document.getElementById('editHandB').click(); document.getElementById('linkGen').click(); await wait(30);
      const title = el.barsTitle.textContent;
      el.shape.value = 'drawbars'; el.shape.dispatchEvent(new Event('change'));
      el.bars.value = '800000000'; el.bar0.dispatchEvent(new Event('input'));
      const whileB = { a: genSettings(0).bars.slice(), b: genSettings(1).bars.slice(), panel: el.bars.value };
      document.getElementById('editHandA').click(); await wait(30);
      const backA = { panel: el.bars.value, title: el.barsTitle.textContent, code: snapshot() };
      return { title, whileB, backA: { panel: backA.panel, title: backA.title,
               bars: backA.code.bars, bBars: backA.code.bBars } };
    }""")
    print("    %s" % layers)
    check("editing B, the section says so and writes B's bars, leaving A's",
          layers["title"] == "Drawbars \u00b7 Upper"
          and layers["whileB"]["b"] == [8, 0, 0, 0, 0, 0, 0, 0, 0]
          and layers["whileB"]["a"] == [0, 0, 8, 7, 4, 0, 0, 0, 0], str(layers["whileB"]))
    check("back on A the sliders are A's again, and the code carries both",
          layers["backA"]["panel"] == "008740000" and layers["backA"]["title"] == "Drawbars \u00b7 Lower"
          and layers["backA"]["bars"] == "008740000" and layers["backA"]["bBars"] == "800000000",
          str(layers["backA"]))
    # Here stood "and B sounds its own: B's picture is its 16' at 110 Hz while
    # A's is its 8' at 220, each alone", on a two-layer makeGeneratorCore
    # built in the page (?brain=js); core/tests/pieces/drawbar.py's now.
    p.evaluate("""() => { el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change'));
                          el.midiDyad.click(); setScreenKeys(false); }""")

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

    # Here stood "a new test tone is built with the sliders' registration, not
    # the core's default, both its layers" (?brain=js): the page's source
    # dropped and toTone() building one from the panel. Only the page's brain
    # builds a generator; gone with stage 5, step 3, batch 2.

    print("\n--- the panel ---")
    panel = p.evaluate("""() => {
      setView('bench'); setBenchTab('play');
      el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change'));
      const sine = { row: el.barsGoRow.hidden, idle: el.barsGroup.hasAttribute('data-idle'),
                     why: el.barsState.textContent, use: !el.barsUse.hidden };
      el.barsUse.click();
      const used = { shape: el.shape.value, heard: genSettings().shape, row: el.barsGoRow.hidden,
                     text: el.barsGo.textContent, idle: el.barsGroup.hasAttribute('data-idle'),
                     state: el.barsStateRow.hidden };
      el.barsGo.click();
      const went = { tab: document.querySelector('[role=tab][aria-selected=true] .tab-name').textContent.trim(),
                     shown: el.bar2.offsetParent !== null };
      // Back to a shape that is not the drawbars, as the search below was
      // written against. (A figure, which had no waveform to colour and said
      // so, was asked here on the way, until G2 took it.)
      el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change'));
      return { sine, used, went };
    }""")
    print("    %s" % panel)
    check("with another shape the registration row is not on Play, and the bars say why they are greyed",
          panel["sine"] == {"row": True, "idle": True, "why": "Not playing.", "use": True},
          str(panel["sine"]))
    check("Use drawbars chooses them, and the row under the menu shows the registration",
          panel["used"] == {"shape": "drawbars", "heard": "drawbars", "row": False,
                            "text": "00 8740 000 ›", "idle": False, "state": True}, str(panel["used"]))
    check("pressing it goes to the bars, on the Ink tab",
          panel["went"] == {"tab": "Ink", "shown": True}, str(panel["went"]))

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
