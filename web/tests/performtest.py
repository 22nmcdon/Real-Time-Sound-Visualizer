"""The presets for playing: are they played?

The failure these guard against is a preset that loads, looks right in the
browser, and does nothing a player could hear change:

- a routing whose source is spelt wrong or does not exist. The matrix keeps
  a routing it cannot resolve rather than dropping it, which is right for a
  preset loaded before the keyboard is plugged in and means a typo is kept
  forever, silently;
- a routing whose source a keyboard never moves: a keyboard preset that is
  really an LFO preset;
- a split or a layer that sends every note to one layer;
- a live-effects preset that never builds the effects insert, and so draws
  and plays the input exactly as it came in;
- a Listening preset whose source does not hear, or is treated as a loop on a
  microphone and so held to the picture's reach for no reason.

`presettest.py` holds the library as a whole: that every field comes back at
the value it names, that each preset is unique and described.

The sections walked here - the keyboard's, Live effects, Listening - are the
old library's, from before P8g, read from corpus.py: the bank that replaced it
has none of them, and these setups are still the widest test there is of a
routing a hand or an ear moves. Loaded as a preset was (loadCorpus restores
the setup and sends it on), so what is measured is the setup, not the bank.
"""
# Since stage 5, step 3, batch 4 (13 Nov): what the sections are is read on
# the default page (the corpus and the face's codec, no brain). The keyboard
# sections played - every routing reaching the generator, still at rest and
# moving when played, the cut ones loading with none, the misspelt null, and
# both layers sounding - are core/tests/pieces/perform.py's, on the
# instrument: here they read the page's own MOD_SOURCES, genRoutes and
# midi.poly.layers, which on the default are the face's. The live effects and
# the Listening presets stayed on ?brain=js, on a page of their own, until
# batch 5 (13 Nov): they put a microphone through the page's own effects
# insert (state.source.fx) and asked the page's compiler. They are
# pieces/perform.py's `microphone` now: render_cpp draws an input through the
# instrument, which puts it through its own effects (the insert went with the
# page's brain), each preset held over it and what is drawn read against the
# input itself; and the Listening routings read off the instrument's matrix,
# live and no loop on the microphone, and the loop's on the generator. The
# section's words for a microphone are livefxtest.py's.
import os
from playwright.sync_api import sync_playwright
import corpus

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

KEYBOARD = ["Poly keys", "Chords drawn", "Arpeggios", "Split", "Layer", "Hands on the sound", "Many sources"]


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
    corpus.install(p)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    print("\n--- what the sections are ---")
    shape = p.evaluate("""(names) => {
      const hands = /^(midi\\.|notes\\.|cc\\.|env\\.note$)/;
      const played = (setup) => decodeRoutings(setup.mod).some((r) => hands.test(r.sourceId));
      const out = { missing: [], unplayed: [], unlayered: [], counts: {} };
      for (const name of names) {
        const section = CORPUS.find(([s]) => s === name);
        if (!section) { out.missing.push(name); continue; }
        out.counts[name] = section[1].length;
        for (const [preset, setup] of section[1]) {
          if (!played(setup)) out.unplayed.push(preset);
          if (name === 'Split' && setup.layers !== 'split') out.unlayered.push(preset);
          if (name === 'Layer' && setup.layers !== 'layer') out.unlayered.push(preset);
        }
      }
      // The null: a preset from the Organ section, which no hand moves.
      const organ = CORPUS.find(([s]) => s === 'Organ')[1][0];
      out.organPlayed = played(organ[1]);
      const live = CORPUS.find(([s]) => s === 'Live effects');
      out.live = live ? [live[1].length, live[2]] : null;
      return out;
    }""", KEYBOARD)
    print("    %s" % shape)
    check("the sections for playing, each with a routing a hand moves in every preset",
          shape["missing"] == [] and shape["unplayed"] == [] and all(n >= 5 for n in shape["counts"].values())
          and shape["organPlayed"] is False, str(shape))
    check("and every preset in Split is a split, and every one in Layer a layer", shape["unlayered"] == [], str(shape["unlayered"]))
    check("and a section of effects for live inputs, landing on whatever is playing",
          shape["live"] is not None and shape["live"][0] >= 5 and shape["live"][1] == "display", str(shape["live"]))

    # The microphone through the effects, and the Listening presets on it
    # (:231 to :265), are core/tests/pieces/perform.py's since batch 5.

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
