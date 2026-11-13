"""The morph: one position through sine, triangle, saw and square.

What would go wrong, and what is checked for it:

- a detent that is a mix rather than the shape, so "saw" on the morph is not
  a saw. Each whole number is compared with the shape itself, sample for
  sample, band-limiting included;
- a morph that steps between shapes rather than crossfading, which on a
  modulated position is a click at every station. The position is swept in
  thousandths and the largest change a thousandth makes is measured;
- the saw upside down against the other three. Its fundamental is the
  sine's inverted, so a crossfade from the triangle cancels the note half-way
  - 0.09 of the sine's, measured, against 0.72 with the saw turned round. The
  check is on the fundamental across the whole range;
- aliasing: a crossfade of band-limited shapes is band-limited, and a
  position modulated by an oscillator must not undo that;
- a source that cannot reach it, a layer B that plays A's position, a setup
  code that loses it.

The spectra are numpy's, on windows a whole number of hertz wide, for the
reasons drawbartest.py gives.
"""
# Stage 5, step 3, batch 4 (13 Nov): until then this suite opened ?brain=js
# and read the page's own JavaScript waveAt, a makeGeneratorCore built in the
# page (an LFO and a route put on its morph slot by hand, two layers set
# directly), and a key held on the page's brain read off the page's
# generator's window. Those numbers - the stations exactly the shapes, a
# thousandth moving no sample by more than two thousandths, the fundamental
# never under the saw's, nothing folding back still or swept, a key on Morph
# moving the sound to the half-saw, and B's own position heard - are asserted
# on the core now, each with its null, in core/tests/pieces/morph.py. What is
# left here is the face, on the site's default page: the row and its reading,
# a routing that leaves the slider alone, the reach, the hands, codes and
# search.
import os, sys
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

    # Here stood, on ?brain=js: the stations exactly the shapes, a thousandth
    # moving no sample by more than two thousandths, the fundamental never
    # under the saw's 0.64 and smooth from triangle to saw, nothing folding
    # back above -45 dB still or swept by an oscillator - all on the page's
    # waveAt and a makeGeneratorCore built in the page. core/tests/pieces/
    # morph.py's now, on the core, with a null beside each.

    print("\n--- on the panel, and patched ---")
    panel = p.evaluate("""async () => {
      setView('bench'); setBenchTab('play');
      el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change'));
      const sine = el.morphRow.hidden;
      el.shape.value = 'morph'; el.shape.dispatchEvent(new Event('change'));
      // The position read off the setup the face sends (snapshot), in
      // hundredths: on ?brain=js this was genSettings(), which on the default
      // is only the face's mirror.
      const shown = { row: el.morphRow.hidden, reading: el.morphValue.textContent, at: snapshot().morph };
      el.morph.value = '200'; el.morph.dispatchEvent(new Event('input'));
      const saw = { reading: el.morphValue.textContent, at: snapshot().morph };
      el.morph.value = '275'; el.morph.dispatchEvent(new Event('input'));
      const late = el.morphValue.textContent;
      // Every reading inside its row: the first one ran off the end of it.
      const clipped = [];
      for (const v of [0, 50, 100, 150, 200, 250, 275, 300]) {
        el.morph.value = String(v); el.morph.dispatchEvent(new Event('input'));
        const r = el.morphValue.getBoundingClientRect(), row = el.morphRow.getBoundingClientRect();
        if (r.right > row.right + 0.5 || el.morphValue.scrollWidth > el.morphValue.clientWidth + 0.5) {
          clipped.push(el.morphValue.textContent);
        }
      }
      return { sine, shown, saw, late, clipped };
    }""")
    print("    %s" % panel)
    check("the Morph row is on Play only with Morph chosen",
          panel["sine"] and not panel["shown"]["row"], str(panel))
    check("it starts half-way from the triangle to the saw, and says where it is",
          panel["shown"]["reading"] == "tri→saw" and panel["shown"]["at"] == 150
          and panel["saw"] == {"reading": "saw", "at": 200} and panel["late"] == "saw→sqr",
          str(panel))
    check("and every reading fits beside the slider, in a Bench column",
          panel["clipped"] == [], str(panel["clipped"]))

    # On ?brain=js this held a key on the page's brain and read the page's
    # generator's window: a sine with no second harmonic at depth nought, the
    # half-saw's -13.2 dB at full. That sound is core/tests/pieces/morph.py's
    # now, through the instrument whole. What stays is the face: the slider's
    # own position untouched while a key holds a routing on it at full, read
    # off the slider and the code (on ?brain=js it was genSettings(), the
    # mirror on the default), and the destination's reach.
    patched = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.freq.value = '220'; el.freq.dispatchEvent(new Event('input'));
      el.morph.value = '0'; el.morph.dispatchEvent(new Event('input'));
      midiRegisterKey(); midiNoteOn(57, 127);
      addRouting('midi.key', 'gen.morph');
      const routing = state.modRoutings.find((r) => r.sourceId === 'midi.key');
      routing.amount = 1; touchRoutings(); await wait(1200);
      const held = { slider: el.morph.value, code: snapshot().morph, routed: snapshot().mod };
      const dest = MOD_DESTS.get('gen.morph');
      const out = { held, reach: [dest.reach(0, 1), dest.reach(150, 1), dest.reach(100, -1)] };
      midiNoteOff(57);
      state.modRoutings = []; touchRoutings();
      return out;
    }""")
    print("    %s" % patched)
    check("a key on Morph at full does not write the slider's own position",
          patched["held"]["slider"] == "0" and patched["held"]["code"] == 0, str(patched["held"]))
    check("null: the routing was there to write it", "gen.morph" in str(patched["held"]["routed"]),
          str(patched["held"]["routed"]))
    check("full depth is a station and a half, stopped at both ends",
          patched["reach"] == [150, 300, 0], str(patched["reach"]))

    print("\n--- each layer its own position ---")
    layers = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.morph.value = '300'; el.morph.dispatchEvent(new Event('input'));
      // Poly by its button: setMidiMode alone the instrument never hears.
      setScreenKeys(true); el.midiPoly.click();
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(30);
      // The upper hand, its Generator its own (G6: linked, the position would be both hands').
      document.getElementById('editHandB').click(); document.getElementById('linkGen').click(); await wait(30);
      el.shape.value = 'morph'; el.shape.dispatchEvent(new Event('change'));
      el.morph.value = '0'; el.morph.dispatchEvent(new Event('input'));
      // Each hand's position off the setup the face sends; on ?brain=js
      // genSettings(0) and genSettings(1), the mirror on the default.
      const c = snapshot();
      const whileB = { a: c.morph, b: c.bMorph, reading: el.morphValue.textContent, row: el.morphRow.hidden };
      document.getElementById('editHandA').click(); await wait(30);
      const code = snapshot();
      const backA = { slider: el.morph.value, reading: el.morphValue.textContent,
                      morph: code.morph, bMorph: code.bMorph };
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change'));
      el.midiDyad.click(); setScreenKeys(false);
      return { whileB, backA };
    }""")
    print("    %s" % layers)
    check("editing B writes B's position and leaves A's",
          layers["whileB"] == {"a": 300, "b": 0, "reading": "sine", "row": False}, str(layers["whileB"]))
    check("and back on A the slider is A's, with the code carrying both",
          layers["backA"] == {"slider": "300", "reading": "square", "morph": 300, "bMorph": 0},
          str(layers["backA"]))
    # Here stood "and B sounds its own: A's square has its third harmonic at
    # -9.5 dB, B's sine none", on a two-layer makeGeneratorCore built in the
    # page (?brain=js); core/tests/pieces/morph.py's now.

    print("\n--- setup codes ---")
    # restore() is the face's half of a code: the instrument hears a code only
    # through loadCode or a preset. On ?brain=js these read genSettings(0)
    # and (1), the page's generator; on the default that is the mirror, so
    # they read the slider and the setup the face would send ('A' where it
    # names no B position, so B takes A's). That the core's restore gives B
    # A's position is parity's restore section's, against the page's.
    codes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const read = () => { const c = snapshot(); return { a: c.morph, b: c.bMorph === undefined ? 'A' : c.bMorph,
                                                          slider: el.morph.value }; };
      restore({ shape: 'morph', morph: 250 }); await wait(30);
      const one = read();
      restore({ shape: 'morph', morph: 250, bMorph: 75 }); await wait(30);
      const both = read();
      // After a code that set one, so a restore that ignored the field would
      // not pass by standing still on the default.
      restore({ shape: 'morph', morph: 250 }); await wait(30);
      restore({ shape: 'sine' }); await wait(30);
      const old = read();
      return { one, both, old };
    }""")
    print("    %s" % codes)
    check("a code's position reaches the slider and the code, and B takes A's when it has none",
          codes["one"] == {"a": 250, "b": "A", "slider": "250"}, str(codes["one"]))
    check("and B its own when it has one", codes["both"]["a"] == 250 and codes["both"]["b"] == 75,
          str(codes["both"]))
    check("a code from before the morph loads with the default",
          codes["old"] == {"a": 150, "b": "A", "slider": "150"}, str(codes["old"]))

    # Here stood "a generator built later, from the panel, takes the slider's
    # position on both layers" (?brain=js): the page's source dropped and
    # toTone() building one from the panel. Only the page's brain builds a
    # generator; gone with stage 5, step 3, batch 4.

    def search(q):
        p.evaluate("(q) => { el.benchSearch.value = q; el.benchSearch.dispatchEvent(new Event('input')); }", q)
        return p.evaluate("""() => Array.from(el.benchResults.querySelectorAll('button'))
          .map((b) => [b.firstChild.textContent, b.querySelector('.crumb').textContent])""")
    p.evaluate("() => { el.shape.value = 'morph'; el.shape.dispatchEvent(new Event('change')); }")
    timbre = search("timbre")
    check("timbre finds it", ["Morph", "Generator"] in timbre, str(timbre[:4]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the morph goes from sine to square without a step or a hole")
