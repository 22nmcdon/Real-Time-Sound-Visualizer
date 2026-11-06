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

All of that on ?brain=js, whose page computes the routes itself. The default
page plays the site's compiled instrument, which computes its routes in the
core - held to the page by parity - and draws its own grids; the last leg
reads them back from it: each layer's screen of its own there too, measuring
its own figure, and the menus reaching it. Its null is the same split with
the layers off.
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

# The two layers set up: A a fifth turning (equal temperament), B one note;
# `quiet` silences one layer, so its figure is a dot that does not move.
SPLIT = """async (quiet) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  midiPanic(); setDisplay('xy'); setScreenKeys(true); setMidiMode('poly');
  el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
  midi.layers.point = 60;
  genSet('just', false); genSet('just', false, 1);
  genSet('amp', quiet === 0 ? 0 : 0.8, 0); genSet('amp', quiet === 1 ? 0 : 0.8, 1);
  for (const n of [48, 55, 72, 79]) midiNoteOn(n, 100);
  await wait(3000);
  const r = (x) => ({ cover: x.raw.cover, change: x.raw.change });
  return { live: layerPictures.live, a: r(layerPictures.values[0]), b: r(layerPictures.values[1]), shared: r(picture) };
}"""

# The loop's combined routes as stepRoutes leaves them, with the frame loop
# stopped so the stages hold what a check puts in them.
ROUTES = """() => { stepRoutes(); return genRoutes.filter((x) => x.loopTotal).map((x) => [x.slot, x.held, x.heldB]); }"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html?brain=js"); p.wait_for_timeout(1200)
    corpus.old_opening(p)  # the opening it was written against (P8h)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    print("\n--- unsplit, nothing changes ---")
    plain = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setDisplay('xy'); setScreenKeys(true); setMidiMode('poly'); genSet('just', false);
      for (const n of [48, 55]) midiNoteOn(n, 100);
      await wait(2000);
      stepRoutes();
      const loops = genRoutes.filter((x) => x.loopTotal);
      return { live: layerPictures.live, made: layerPictures.engines !== null, routes: loops.length,
               same: loops.every((x) => x.heldB === x.held && x.held === x.source.value()),
               moving: loops.some((x) => x.held !== 0), row: !el.pictureMovesRow.hidden };
    }""")
    print("    %s" % plain)
    check("unsplit, the layer screens are never made and every loop route carries the one shared push to both layers",
          not plain["live"] and not plain["made"] and plain["routes"] >= 2 and plain["same"] and plain["moving"]
          and not plain["row"], str(plain))

    # The second generator, with no split, lays out a figure each too - its
    # figure in layer B's lanes - and it is not a layer: the layer screens stay
    # off. A mutant that dropped the split from the condition lived until this.
    second = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.inputFrom.value = 'gen2'; el.inputFrom.dispatchEvent(new Event('change'));
      await wait(1500);
      stepRoutes();
      const loops = genRoutes.filter((x) => x.loopTotal);
      const out = { figures: (sourceFigures() || []).length, layers: layersOn(), live: layerPictures.live,
                    same: loops.every((x) => x.heldB === x.held) };
      el.inputFrom.value = 'live'; el.inputFrom.dispatchEvent(new Event('change'));
      await wait(300);
      return out;
    }""")
    print("    the second generator, unsplit: %s" % second)
    check("and with the second generator drawn as a figure of its own, still one picture for both sounds",
          second["figures"] == 2 and not second["layers"] and not second["live"] and second["same"], str(second))

    print("\n--- each layer's screen measures its own figure ---")
    a_moves = p.evaluate(SPLIT, 1)
    b_moves = p.evaluate(SPLIT, 0)
    print("    B silent: A %s, B %s, shared %s" % (a_moves["a"], a_moves["b"], a_moves["shared"]))
    print("    A silent: A %s, B %s, shared %s" % (b_moves["a"], b_moves["b"], b_moves["shared"]))
    # Activity, coverage times change: a still dot covering a quarter of a per
    # cent of its screen reads a large relative change from the tail of the
    # notes it has just let go, so change alone is noise there; what moves is
    # how much lit screen changes. Twenty times, and five times the coverage.
    # The floor under the moving screen's change is only that it changes at
    # all: it read 0.016 to 0.13 over five runs, and a still dot's change
    # read up to 0.134, so it is the two ratios that tell them apart. The
    # floor was 0.02, and the moving screen failed it once at 0.016 (6 Nov).
    act = lambda x: x["cover"] * x["change"]
    def follows(r, moving, still):
        return (r["live"] and r[moving]["change"] > 0.01 and act(r[moving]) > 20 * act(r[still])
                and r[moving]["cover"] > 5 * r[still]["cover"])
    check("with B silent, A's screen moves and B's does not", follows(a_moves, "a", "b"), str(a_moves))
    check("and with A silent, B's moves and A's does not", follows(b_moves, "b", "a"), str(b_moves))
    check("and the check fails on the shared screen read for the still layer",
          not follows(dict(a_moves, b=a_moves["shared"]), "a", "b"), str(a_moves["shared"]))

    print("\n--- whose sound each picture moves ---")
    p.evaluate(SPLIT, -1)
    p.evaluate("() => { state.running = false; }")
    p.wait_for_timeout(200)
    moved = p.evaluate("""(ROUTES) => {
      const routes = eval(ROUTES);
      const set = (l, glow, motion, memory, hold) => Object.assign(layerPictures.stages[l], { glow, motion, memory, hold });
      const out = {};
      layerPictures.live = true;
      layerPictures.moves = ['A', 'B'];
      set(0, 0.8, 0.6, 0.4, 1); set(1, 0.2, 0.1, 0.3, 1);
      out.before = routes();
      set(1, 0.9, 0.9, 0.9, 1);
      out.bChanged = routes();
      layerPictures.moves = ['A', 'both'];     // B's picture to both: A's sound hears it too
      out.aHearsBoth = routes();
      return out;
    }""", ROUTES)
    def by_slot(rows): return {r[0]: (r[1], r[2]) for r in rows}
    bef, aft, both = by_slot(moved["before"]), by_slot(moved["bChanged"]), by_slot(moved["aHearsBoth"])
    print("    slot: (A's push, B's push) before %s; B's stage changed %s; A's picture to both %s" % (bef, aft, both))
    a_same = all(abs(bef[k][0] - aft[k][0]) < 1e-12 for k in bef)
    b_moved = any(abs(bef[k][1] - aft[k][1]) > 0.01 for k in bef)
    check("each picture moving its own sound: B's stage changing moves B's push and not A's", a_same and b_moved,
          str((bef, aft)))
    check("and with B's picture heard by A as well, it moves A's push too - the check can see it",
          any(abs(both[k][0] - aft[k][0]) > 0.01 for k in aft), str(both))

    pushes = p.evaluate("""() => {
      const set = (l, glow, hold) => Object.assign(layerPictures.stages[l], { glow, hold });
      layerPictures.live = true;
      const at = (moves) => { layerPictures.moves = moves; return [layerPush('glow', 0), layerPush('glow', 1)]; };
      set(0, 0.8, 1); set(1, 0.2, 1);
      const out = { both: at(['both', 'both']), own: at(['A', 'B']), swapped: at(['B', 'A']), none: at(['B', 'B']) };
      set(0, 0.8, 1); set(1, 0.2, 0.25);
      out.heldBoth = at(['both', 'both']);
      out.heldCross = at(['B', 'A']);
      out.heldOneWay = at(['both', 'B']);
      return out;
    }""")
    print("    glow pushes [A's sound, B's sound]: %s" % pushes)
    near = lambda x, y: abs(x - y) < 1e-12
    check("a sound that hears both pictures takes their average", near(pushes["both"][0], 0.5) and near(pushes["both"][1], 0.5),
          str(pushes["both"]))
    check("and not their sum, which the check would read as wrong", not near(pushes["both"][0], 1.0))
    check("own, crossed and neither: each sound hears exactly the pictures its menu sends it",
          near(pushes["own"][0], 0.8) and near(pushes["own"][1], 0.2) and near(pushes["swapped"][0], 0.2)
          and near(pushes["swapped"][1], 0.8) and near(pushes["none"][0], 0) and near(pushes["none"][1], 0.5),
          str(pushes))
    # B's hold at a quarter: in the crossed pair each cross term carries the
    # lower hold - A's sound hears B's picture at 0.2 x 0.25, B's hears A's at
    # 0.8 x 0.25 - while A's own term keeps A's hold of one. One way only (A's
    # picture to both, B's to B alone) is not a crossed pair: B's term into
    # nothing, A's into B at A's own hold.
    check("a crossed pair is held by the lower governor in its cross terms, and an own term by its own",
          near(pushes["heldBoth"][0], (0.8 + 0.2 * 0.25) / 2) and near(pushes["heldBoth"][1], (0.2 * 0.25 + 0.8 * 0.25) / 2)
          and near(pushes["heldCross"][0], 0.2 * 0.25) and near(pushes["heldCross"][1], 0.8 * 0.25)
          and near(pushes["heldOneWay"][1], (0.8 + 0.2 * 0.25) / 2), str(pushes))
    check("and the check fails on a cross term that ignored the hold",
          not near(pushes["heldCross"][1], 0.8), str(pushes["heldCross"]))

    print("\n--- a layer's own governor ---")
    p.evaluate("() => { state.running = true; layerPictures.moves = ['A', 'B']; }")
    governed = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      // B's screen held full every frame: its meter reads a screen saturated,
      // which is running away, and its governor holds - A's figure is untouched.
      const step = window.layerPicturesStep;
      window.layerPicturesStep = function (...a) { if (layerPictures.live) layerPictures.engines[1].cells.fill(1); return step.apply(this, a); };
      for (const s of layerPictures.stages) s.hold = 1;
      await wait(7000);
      window.layerPicturesStep = step;
      return { a: layerPictures.stages[0].hold, b: layerPictures.stages[1].hold,
               verdicts: layerPictures.engines.map((e) => e.meter.verdict()) };
    }""")
    print("    %s" % governed)
    check("a layer whose screen runs away is held to the floor by its own governor, and the other layer is not",
          governed["verdicts"][1] == "running away" and abs(governed["b"] - 0.25) < 1e-9 and governed["a"] == 1, str(governed))

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
      restore({});
      out.reset = layerPictures.moves.slice();
      restore(decodeSetup(code));
      out.back = layerPictures.moves.slice();
      out.menus = [el.pictureMovesA.value, el.pictureMovesB.value];
      restore({ pictureMovesA: 'B', pictureMovesB: 'nonsense' });
      out.odd = layerPictures.moves.slice();
      restore({});
      return out;
    }""")
    print("    %s" % menus)
    check("the menus show while the layers draw a figure each, and not for A against B or with no split",
          menus["split"] and not menus["against"] and not menus["off"], str(menus))
    check("a setup carries both, an old code is each picture moving its own sound, and nonsense falls back",
          menus["back"] == ["both", "A"] and menus["menus"] == ["both", "A"] and menus["reset"] == ["A", "B"]
          and menus["odd"] == ["B", "B"], str(menus))

    check("no page errors", not bad, "; ".join(bad[:3]))
    p.close()

    print("\n--- the site's compiled instrument (the default page) ---")
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500)
    corpus.old_opening(p)  # the opening it was written against (P8h)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
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
