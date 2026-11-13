"""Each layer's picture, and whose sound it moves (P6, the owner's).

Split into two sounds, the keyboard draws two figures, and each is also laid
into a screen of its own behind the one shown, with its own meter, stage and
hold; a menu per layer says whose sound its picture moves. What would go
wrong, and what is checked for it:

- the split leaking into the unsplit instrument. With no layer B the layer
  screens are never made, and every loop route's two layers carry the one
  shared push, exactly; the null is the same check with a split on, where they
  differ;
- a layer's screen measuring the other's figure, or both. Layer A plays a
  moving fifth and layer B a silent note - a dot - so A's screen changes and
  B's does not; then the other way round, so a screen that read its neighbour
  is caught both ways. The null is the shared screen, which moves, so a check
  that read it for B would fail;
- a picture moving the wrong sound. With each picture moving its own sound,
  a change to B's stage alone moves B's push and not A's; with A's set to
  both, it moves A's too;
- "both" summing rather than averaging - the null is the sum, which the
  value is not;
- a crossed pair escaping its governor: with B's hold down to a quarter, the
  cross terms both carry the quarter and A's own term does not; and the real
  governor, from a layer's own verdict, holds that layer and not the other;
- the menus showing where they mean nothing, and a setup losing them.

Since stage 5, step 3, batch 2 (13 Nov) the numbers are the core's own:
the unsplit routes, each layer's screen measuring its own figure, whose sound
each picture moves, layerPush's averaging and crossing and holds, and a
layer's own governor are core/tests/pieces/layerpicture.py's, on
scope::LayerPictures through picture_cpp (parity runs it). Until then they
were here on ?brain=js, reading the page's own layer screens over real
seconds, its stages written by hand and its route compiler stepped. What is
left is the face, on the default page, which plays the site's compiled
instrument: the menus where they mean something, a setup carrying them, and
the instrument's own layer screens read back from it, each measuring its own
figure, with the menus reaching it. Its null is the same split with the
layers off.
"""
import os, sys
from playwright.sync_api import sync_playwright
import corpus

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500)
    corpus.old_opening(p)  # the opening it was written against (P8h)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    # The checks that stood here until batch 2 - unsplit, every loop route
    # carrying the one shared push; each layer's screen moving with its own
    # figure and not the other's; B's stage moving B's push and not A's;
    # a sound hearing both pictures taking their average, own, crossed and
    # neither, a crossed pair held by the lower governor; a layer that runs
    # away held by its own governor - read the page's layerPictures and its
    # route compiler on ?brain=js, with stages written by hand. They are
    # core/tests/pieces/layerpicture.py's, on the core's own output.

    # A split in X-Y, pressed as a hand does: until batch 2 setDisplay and
    # setMidiMode were called directly, which the instrument never hears.
    p.evaluate("""async () => {
      el.dispXY.click(); setScreenKeys(true); el.midiPoly.click();
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      await new Promise((r) => setTimeout(r, 300));
    }""")

    print("\n--- the menus, and a setup ---")
    menus = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const shown = () => !el.pictureMovesRow.hidden;
      const out = { split: shown() };
      el.midiLayerPair.value = 'against'; el.midiLayerPair.dispatchEvent(new Event('change')); await wait(100);
      out.against = shown();
      el.midiLayerPair.value = 'each'; el.midiLayerPair.dispatchEvent(new Event('change')); await wait(100);
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change')); await wait(100);
      out.off = shown();
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change')); await wait(100);
      el.pictureMovesA.value = 'both'; el.pictureMovesA.dispatchEvent(new Event('change'));
      el.pictureMovesB.value = 'A'; el.pictureMovesB.dispatchEvent(new Event('change'));
      const code = encodeSetup(snapshot());
      // Until batch 2 each of these read layerPictures.moves, the page's own
      // on ?brain=js and only its mirror on the default page. They read the
      // menus, what the face shows, and the instrument's own reading of
      // whose sound each picture moves, sent back with its samples - after a
      // split put back, since a code from before layers has none. Each code
      // is loaded as the setup box loads one (loadCode), which sends it to
      // the instrument: restore() called directly, as this was, changes the
      // face alone on the default page.
      const split = async () => { el.midiPoly.click(); el.midiLayers.value = 'split';
        el.midiLayers.dispatchEvent(new Event('change')); await wait(800); };
      const menus = () => [el.pictureMovesA.value, el.pictureMovesB.value];
      const heard = () => state.source.layerPictures && state.source.layerPictures.moves;
      loadCode(encodeSetup({})); await split();
      out.reset = menus(); out.resetHeard = heard();
      loadCode(code); await wait(800);
      out.back = menus(); out.backHeard = heard();
      loadCode(encodeSetup({ pictureMovesA: 'B', pictureMovesB: 'nonsense' })); await split();
      out.odd = menus(); out.oddHeard = heard();
      loadCode(encodeSetup({})); await split();
      return out;
    }""")
    print("    %s" % menus)
    check("the menus show while the layers draw a figure each, and not for A against B or with no split",
          menus["split"] and not menus["against"] and not menus["off"], str(menus))
    check("a setup carries both, an old code is each picture moving its own sound, and nonsense falls back - on the face and in the instrument",
          menus["back"] == ["both", "A"] and menus["reset"] == ["A", "B"] and menus["odd"] == ["B", "B"]
          and menus["backHeard"] == ["both", "A"] and menus["resetHeard"] == ["A", "B"] and menus["oddHeard"] == ["B", "B"],
          str(menus))
    check("null: the code's menus are not the old code's", menus["backHeard"] != menus["resetHeard"], str(menus))

    print("\n--- the site's compiled instrument: each layer's screen ---")
    # The hands go to the instrument as a hand's would - clicks on its buttons
    # and changes on its menus - and what it measures comes back with its
    # samples (the bridge's readings). Layer A a fifth turning, B one note.
    COMPILED = """async (layers) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const pick = (id, value) => { el[id].value = value; el[id].dispatchEvent(new Event('change')); };
      el.dispXY.click(); setScreenKeys(true); el.midiPoly.click(); el.tuneEqual.click();
      pick('midiLayers', layers);
      await wait(500);
      midiPanic();
      for (const n of [48, 55, 72]) midiNoteOn(n, 100);
      await wait(3000);
      const read = state.source.layerPictures;
      const out = { kind: state.source.kind, layers: read && JSON.parse(JSON.stringify(read)) };
      pick('pictureMovesA', 'both'); pick('pictureMovesB', 'A');
      await wait(800);
      out.moved = state.source.layerPictures.moves;
      pick('pictureMovesA', 'A'); pick('pictureMovesB', 'B');
      midiPanic();
      return out;
    }"""
    split = p.evaluate(COMPILED, "split")
    off = p.evaluate(COMPILED, "off")
    print("    split: %s" % split)
    print("    off: %s" % off)
    def own_screens(r):
        l = r["layers"]
        return (r["kind"] == "host" and l is not None and l["live"] and l["stages"][0]["raw"]["cover"] > 0
                and l["stages"][1]["raw"]["cover"] > 0 and l["stages"][0]["raw"]["cover"] != l["stages"][1]["raw"]["cover"])
    check("the compiled instrument split in X-Y gives each layer's figure a screen of its own, each measuring its own figure",
          own_screens(split), str(split["layers"]))
    check("and the reading fails with the layers off, where there is one picture", not own_screens(off), str(off["layers"]))
    check("and the menus reach it: A's picture to both and B's to A's sound, from A and B",
          split["layers"] and split["layers"]["moves"] == ["A", "B"] and split["moved"] == ["both", "A"], str(split["moved"]))
    check("no page errors on the default page", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("each layer's picture moves the sounds its menu sends it to, and nothing else changed")
