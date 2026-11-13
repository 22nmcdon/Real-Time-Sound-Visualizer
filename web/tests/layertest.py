"""Two layers: a keyboard split, or every note twice, from one core.

What would go wrong, and what is checked for it:

- the oscillators stepped twice a sample, once per layer, so every modulation
  rate runs at double with a split on. Measured by how far an oscillator's
  phase moves in a quarter of a second of core samples, against a nought that
  a doubled step cannot give;
- a note landing in the wrong layer. The fixture straddles the split point
  and includes the point itself, so `>` and `>=` disagree, and it is pressed
  out of pitch order so a layer that took "the first two" would be caught;
- the two layers sharing one draw rule. Each is given a different rule, and
  each has three notes so the two rules pick different ones;
- a layer's notes leaking into the other's picture, or missing from what is
  heard. Checked by energy at each note's own frequency in each picture and in
  the heard pair, at the core and again through the worklet, where layer B's
  picture crosses a thread in two arrays of its own;
- layer B sounding with layer A's shape or envelope;
- "A against B" not being layer A on X and layer B on Y;
- two figures asked for and one drawn, read from the phosphor with only
  layer B holding notes, so the one figure that is there is B's;
- the panel writing into the wrong layer, or a panel left showing B being
  what a setup code or a new generator is built from;
- the layers outliving the thing that made them possible.

Frequencies are read by a Hann-windowed single-bin transform, as polytest
does and for its reason: a sum of notes crosses zero at the rate of none.
"""
# On the site's default page since stage 5, step 3, batch 2 (13 Nov): the
# instrument, the site's compiled core, with its hands pressed on the face.
# Until then the whole suite was on ?brain=js, reading the page's own brain -
# its voices and worklet, setMidiMode called directly. What it held of the
# engine and the keyboard - one step of the oscillators a sample, each layer's
# picture and the heard pair, B's shape and envelope, the envelope a source
# reads and B's voices let go, which layer a note goes to, each layer's draw
# rule, A against B - is core/tests/pieces/layer.py's now, asserted on the
# core's own output (parity runs it). What is left here is the face: the
# lanes it lays out and names, the learn button, the readout, the drawing,
# the panel and setup codes - and where a check asks whether the instrument
# heard, it reads the lanes the instrument drew (state.source.getLatestWindow
# on the default page), never the page's mirror of the setup, which the
# page's own MIDI apply writes whatever the instrument does.
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

HZ = lambda note: 440 * 2 ** ((note - 69) / 12)
rounded = lambda xs: [round(x, 4) for x in xs]

BIN = """(src) => { window.__bin = eval(src); }"""
BIN_SRC = """(x, f, rate) => {
  let re = 0, im = 0;
  for (let i = 0; i < x.length; i++) {
    const w = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (x.length - 1));
    re += x[i] * w * Math.cos(2 * Math.PI * f * i / rate);
    im -= x[i] * w * Math.sin(2 * Math.PI * f * i / rate);
  }
  return Math.hypot(re, im) / x.length;
}"""

# The lanes the instrument drew, by their bins, at each note.
LANES = """async (ns) => {
  await new Promise((r) => setTimeout(r, 600));
  const w = state.source.getLatestWindow(16384), rate = state.source.sampleRate;
  return w.map((x) => ns.map((n) => window.__bin(x, 440 * Math.pow(2, (n - 69) / 12), rate)));
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    p.add_init_script("window.__errs = []; window.addEventListener('error', "
                      "(e) => window.__errs.push(e.error && e.error.stack || e.message));")
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e) + " @ " + (e.stack or "")[:300]))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(1200)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)
    p.evaluate(BIN, BIN_SRC)
    lanes = lambda ns: p.evaluate(LANES, ns)

    # The core's checks - the oscillators stepped once a sample with two
    # layers, each layer's picture and the heard pair (A's lanes and B's
    # summed), B's own shape and envelope, the envelope a source reads and B's
    # voices let go - were run here on the page's makeGeneratorCore on
    # ?brain=js until batch 2; core/tests/pieces/layer.py holds them on the
    # core. One went rather than moved: "a caller that asks for no lanes of
    # B's hears exactly the same" was the page's core, whose B lanes were
    # optional arguments; the core computes B whether or not they are asked
    # for, and the instrument asks for them with the heard pair.

    print("\n--- the keyboard: the lanes a split lays out ---")
    # Which layer each note goes to (`>` against `>=` at the point, out of
    # pitch order) was read off genSettings(layer).voices, put there by the
    # page's own keyboard on ?brain=js; it is pieces/layer.py's on the core's
    # keyboard now. What stays is the lanes the face lays out: Poly pressed and
    # the split chosen, as a hand does, so the instrument is told (setMidiMode
    # called directly, as this was, never reached it).
    route = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setScreenKeys(true); el.midiPoly.click();
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(200);
      for (const n of [72, 59, 60, 48]) midiNoteOn(n, 100);
      await wait(300);
      const out = { kind: state.source.kind, channels: state.source.channels, lanes: laneCount(),
                    names: [0, 1, 2, 3].map(laneName), figures: state.source.figures() };
      midiPanic();
      return out;
    }""")
    print("    %s" % route)
    check("a split offers four lanes, named for their layers, as two figures",
          route["kind"] == "host" and route["channels"] == 4 and route["lanes"] == 4
          and route["names"] == ["A · X", "A · Y", "B · X", "B · Y"]
          and route["figures"] == [[0, 1], [2, 3]], str(route))

    # The split point learned from the next key stays on ?brain=js (its own
    # page, at the end), and is listed in plugin/STAGE5-INVENTORY.md: on the
    # default page the Learn button and the next key move the face's point
    # ("at G3") and not the instrument's - G3 learned, A3 still lands in A's
    # lanes, where the point is C4 - so the check as it stood, reading the
    # page's midi.layers.point and genSettings(1).voices, passed on the default
    # for the page's reason. It cannot move without a change to the page.

    print("\n--- each layer its own draw rule: the readout ---")
    # Which notes each layer draws is pieces/layer.py's on the core's
    # keyboard; it was midi.draws written by hand on the page, which the
    # instrument never hears. The rule is chosen here as a hand chooses it,
    # each hand's Draw menus with that hand on the face. The readout is the
    # face's own reckoning of it, from the page's note list; the lanes cannot
    # say which notes are drawn, since a note not drawn (role u) is still in
    # both of its layer's lanes, so the instrument's half is the pieces'.
    rules = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const pick = (id, v) => { el[id].value = v; el[id].dispatchEvent(new Event('change')); };
      document.getElementById('editHandA').click(); await wait(30);
      pick('midiDrawCount', '2'); pick('midiDrawWhich', 'lowest');
      document.getElementById('editHandB').click(); await wait(30);
      pick('midiDrawCount', '2'); pick('midiDrawWhich', 'highest');
      document.getElementById('editHandA').click(); await wait(30);
      for (const n of [52, 48, 55, 79, 72, 76]) midiNoteOn(n, 100);
      await wait(60);
      state.lastReadout = 0; await wait(400);
      const out = { readout: el.readoutDetail.textContent };
      midiPanic();
      for (const h of ['editHandA', 'editHandB']) {
        document.getElementById(h).click(); await wait(30); pick('midiDrawWhich', 'outer');
      }
      document.getElementById('editHandA').click();
      return out;
    }""")
    print("    %s" % rules["readout"][:200])
    check("the readout says each layer's outline",
          "outline A 2 of 3, B 2 of 3" in rules["readout"] and "split at C4" in rules["readout"],
          rules["readout"][:200])

    print("\n--- A against B ---")
    # That A against B is A's drawn notes on X and B's on Y is
    # pieces/layer.py's, on the instrument's own lanes; here the face names it.
    against = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.midiLayerPair.value = 'against'; el.midiLayerPair.dispatchEvent(new Event('change'));
      await wait(200);
      const out = { channels: state.source.channels, names: [laneName(0), laneName(1)], xyOff: el.xyX.disabled };
      el.midiLayerPair.value = 'each'; el.midiLayerPair.dispatchEvent(new Event('change'));
      await wait(200);
      out.eachNames = [laneName(0), laneName(1)];
      return out;
    }""")
    check("named for the layers, with the X-Y menus back",
          against["channels"] == 2 and against["names"] == ["Layer A", "Layer B"] and not against["xyOff"], str(against))
    check("null: drawn a figure each, the lanes are not named for the layers", against["eachNames"] != ["Layer A", "Layer B"],
          str(against["eachNames"]))

    print("\n--- two figures, both drawn ---")
    # The face's drawing of the instrument's lanes: the page's own grid, which
    # on the default page draws what the instrument sends. Only layer B holds
    # notes, so layer A's figure is a dot at the centre and anything else lit
    # is layer B's. X-Y pressed (setDisplay was called directly until batch 2),
    # and the phase left at the slider's 90, where genSet put it by hand.
    figs = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.dispXY.click(); state.persistence = 0; el.persistence.value = '0';
      // Full ink for every stroke. The beam's shading keeps a slowly adapting
      // reference per figure, and after a switch it is still tuned to whatever
      // that figure drew before - a dot, here - so a shaded comparison between
      // the two layouts measures the adaptation rather than the drawing.
      const shaded = state.beamXY; state.beamXY = false;
      for (const n of [72, 79]) midiNoteOn(n, 100);
      await wait(800);
      const lit = (g) => g.reduce((a, v) => a + (v > 0.2 ? 1 : 0), 0) / g.length;
      const out = { each: lit(phosphor.grid), xyOff: el.xyX.disabled, phase: el.phase.value };
      // The same notes in one layer and no split, drawn as a single figure:
      // what B's figure should look like on its own.
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(800);
      out.alone = lit(phosphor.grid);
      midiPanic(); await wait(300);
      out.dark = lit(phosphor.grid);
      state.beamXY = shaded;
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(200);
      return out;
    }""")
    print("    lit with only layer B playing %.3f; the same notes as one layer %.3f; let go %.3f"
          % (figs["each"], figs["alone"], figs["dark"]))
    check("layer B's figure is drawn beside A's, not just A's",
          figs["each"] > figs["alone"] * 0.5 and figs["alone"] > 0.02, str(figs))
    check("null: with every note let go the screen is not lit like that", figs["dark"] < 0.5 * figs["each"], str(figs))
    check("and the X-Y menus step aside while the layers choose the figures", figs["xyOff"], str(figs))

    # The lag is the face's: it lays out the lanes the page draws, from what
    # the instrument sends, and a modulation of it (state.lagMod) is the
    # page's visual matrix, which moves the screen's own destinations on the
    # default page as on ?brain=js. Moved as it was.
    lag = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.lagOn.checked = true; el.lagOn.dispatchEvent(new Event('change'));
      for (const n of [48, 72]) midiNoteOn(n, 100);
      await wait(300);
      const out = { lag: lagActive(), figures: sourceFigures(), lanes: laneCount(), xyOff: el.xyX.disabled };
      midiPanic();
      el.lagOn.checked = false; el.lagOn.dispatchEvent(new Event('change'));
      await wait(100);
      out.after = sourceFigures();
      // The lag switched on the way a modulation source does it, by its
      // offset, with nothing rebuilding the lanes: four still exist, so only
      // asking whether the lag is on keeps the layers' figures off the screen.
      const auto = state.lagAuto;
      state.lagAuto = false; state.lagMs = 0;
      el.lagOn.checked = true; el.lagOn.dispatchEvent(new Event('change'));
      await wait(100);
      const idle = { lag: lagActive(), figures: sourceFigures() };
      state.lagMod = 5;
      out.modulated = { idle, lag: lagActive(), lanes: state.channels.length, figures: sourceFigures() };
      state.lagMod = 0; state.lagMs = 5; state.lagAuto = auto;
      el.lagOn.checked = false; el.lagOn.dispatchEvent(new Event('change'));
      return out;
    }""")
    print("    %s" % lag)
    check("with the lag on the figure is the lag's, not the layers'",
          lag["lag"] and lag["figures"] is None and lag["lanes"] == 2
          and lag["after"] == [[0, 1], [2, 3]], str(lag))
    m = lag["modulated"]
    check("even when a modulation turns the lag on and nothing rebuilds the lanes",
          not m["idle"]["lag"] and m["idle"]["figures"] == [[0, 1], [2, 3]]
          and m["lag"] and m["lanes"] == 4 and m["figures"] is None, str(m))

    # "The worklet sounds both layers" and "posts layer B's picture back apart
    # from A's" went with batch 2: they tapped the page brain's own worklet
    # and its monitor chain on ?brain=js, plumbing only that brain has. The
    # instrument's worklet is braintest.py's, and its B lanes are read above.

    print("\n--- the panel edits one layer at a time ---")
    panel = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const input = (id, v) => { el[id].value = String(v); el[id].dispatchEvent(new Event('input')); };
      input('amp', 50); input('envRelease', 300);
      /* The upper hand, and the Generator and the Amp envelope its own (G6):
         linked, as every section is until a link is pressed, the controls
         would write both hands - handstest.py holds that. Until G6 every
         section was each hand's own and Edit B chose the hand. */
      document.getElementById('editHandB').click(); await wait(30);
      document.getElementById('linkGen').click(); document.getElementById('linkAmpEnv').click();
      const showsB = { title: el.genTitle.firstChild.textContent + " / " + document.getElementById('linkGen').textContent,
                       freqShown: getComputedStyle(el.freq.closest('.menu-row')).display !== 'none',
                       ampShown: getComputedStyle(el.amp.closest('.menu-row')).display !== 'none' };
      input('amp', 90); input('envRelease', 1200);
      el.shape.value = 'triangle'; el.shape.dispatchEvent(new Event('change'));
      // A code written while B is on screen is layer A's controls and B's
      // sound, each in its own place.
      const out = { showsB, code: snapshot() };
      document.getElementById('editHandA').click(); await wait(30);
      out.backToA = { amp: el.amp.value, rel: el.envRelease.value, shape: el.shape.value,
                      title: el.genTitle.firstChild.textContent + " / " + document.getElementById('linkGen').textContent };
      return out;
    }""")
    print("    %s" % {k: panel[k] for k in ("showsB", "backToA")})
    check("with B shown and the Generator its own, its link says so and the panel shows only what B has",
          panel["showsB"]["title"] == "Generator / Upper’s own" and not panel["showsB"]["freqShown"]
          and panel["showsB"]["ampShown"], str(panel["showsB"]))
    code = panel["code"]
    # Until batch 2 this read genSettings(0) and genSettings(1), the page's
    # generator on ?brain=js. On the default page they are the page's mirror
    # of the setup, so it reads the setup the face sends the instrument.
    check("and its controls write layer B, leaving A alone",
          code["bAmp"] == 90 and code["bRel"] == 1200 and code["bShape"] == "triangle"
          and code["amp"] == 50 and code["rel"] == 300 and code["shape"] != "triangle",
          str({k: code[k] for k in ("amp", "rel", "shape", "bAmp", "bRel", "bShape")}))
    check("the lower hand chosen puts A's values back on the controls, and the link names it",
          panel["backToA"]["amp"] == "50" and panel["backToA"]["rel"] == "300"
          and panel["backToA"]["shape"] != "triangle" and panel["backToA"]["title"] == "Generator / Lower’s own",
          str(panel["backToA"]))
    check("a code taken with B on screen keeps A's controls as A's",
          code["amp"] == 50 and code["rel"] == 300 and code["bAmp"] == 90 and code["bRel"] == 1200
          and code["bShape"] == "triangle" and code["layers"] == "split", str({k: code[k] for k in
          ("amp", "rel", "bAmp", "bRel", "bShape", "layers")}))

    print("\n--- the setup code carries the layers ---")
    # Each code loaded as the setup box loads one (loadCode), which restores
    # the face and sends the code to the instrument; until batch 2 restore()
    # was called directly, which on the default page changes the face alone.
    # midi.layers, midi.draws and genSettings are the face's copy of the setup
    # on the default page, so these hold the face's decode, and "reaches the
    # generator" is that copy; that the core's restore gives the instrument
    # the same fields is parity's "restore" section.
    trip = p.evaluate("""async ([code]) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const snap = Object.assign({}, code, snapshot());
      snap.layerPair = 'against'; snap.splitAt = 67; snap.midiDrawCountB = 3; snap.midiDrawWhichB = 'recent';
      // Not the defaults: restored with the defaults, A's release and the
      // core's own are both 180 ms, and B getting its own defaults instead of
      // A's values passed this check - the mutation pass found it.
      loadCode(encodeSetup({ midiMode: 'dyad', rel: 900, amp: 30 }));
      await wait(60);
      const reset = { layers: midi.layers.mode, b: genSettings(1).amp, bRel: genSettings(1).releaseMs,
                      aRel: genSettings().releaseMs, a: genSettings().amp };
      loadCode(encodeSetup(snap));
      await wait(60);
      return { reset, mode: midi.layers.mode, point: midi.layers.point, pair: midi.layers.pair,
               drawB: { ...midi.draws[1] }, bAmp: genSettings(1).amp, bRel: genSettings(1).releaseMs,
               bShape: genSettings(1).shape, aAmp: genSettings().amp };
    }""", [code])
    print("    %s" % trip)
    check("split, point, pairing, B's rule and B's sound survive a setup code",
          trip["mode"] == "split" and trip["point"] == 67 and trip["pair"] == "against"
          and trip["drawB"] == {"count": 3, "which": "recent"} and abs(trip["bAmp"] - 0.9) < 1e-9
          and trip["bRel"] == 1200 and trip["bShape"] == "triangle" and abs(trip["aAmp"] - 0.5) < 1e-9,
          str(trip))
    check("a code's envelope reaches the generator, not only its sliders",
          trip["reset"]["aRel"] == 900, str(trip["reset"]))
    check("and a code from before layers has none, with B sounding like A",
          trip["reset"]["layers"] == "off" and trip["reset"]["bRel"] == 900
          and abs(trip["reset"]["b"] - 0.3) < 1e-9, str(trip["reset"]))

    print("\n--- the layers go when what made them possible does ---")
    # Dyad and Poly pressed, as a hand does: until batch 2 setMidiMode was
    # called directly, which the instrument never hears. What the dyad leaves
    # is read off the lanes the instrument sends - two, not four - and
    # Poly's splitting the held notes again off B's lanes, where it read the
    # page's genSettings voices.
    gone = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      midiPanic();
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      el.midiLayerPair.value = 'each'; el.midiLayerPair.dispatchEvent(new Event('change'));
      document.getElementById('editHandB').click();
      for (const n of [48, 72]) midiNoteOn(n, 100);
      await wait(400);
      const before = { channels: state.source.channels, lanes: state.source.getLatestWindow(256).length,
                       edit: el.toneRows.dataset.layerEdit };
      el.midiDyad.click(); await wait(400);
      const dyad = { channels: state.source.channels, lanes: state.source.getLatestWindow(256).length,
                     layout: state.source.layout, edit: el.toneRows.dataset.layerEdit, rowHidden: el.midiLayerRow.hidden };
      el.midiPoly.click(); await wait(200);
      return { before, dyad };
    }""")
    back = lanes([48, 72])
    p.evaluate("() => midiPanic()")
    print("    %s; back in poly, C3 and C5 in A's X %s, B's X %s" % (gone, [round(v, 4) for v in back[0]],
                                                                    [round(v, 4) for v in back[2]]))
    check("leaving poly ends layer B and gives the page two lanes and layer A's panel",
          gone["before"]["channels"] == 4 and gone["before"]["lanes"] == 4 and gone["before"]["edit"] == "b"
          and gone["dyad"]["channels"] == 2 and gone["dyad"]["lanes"] == 2
          and gone["dyad"]["layout"] == "one" and gone["dyad"]["edit"] == "a" and gone["dyad"]["rowHidden"],
          str(gone))
    split_again = lambda r: r[0][0] > 0.02 and r[0][1] < 0.1 * r[0][0] and r[2][1] > 0.02 and r[2][0] < 0.1 * r[2][1]
    check("and coming back to poly splits the held notes again: C3 in A's lanes and C5 in B's", split_again(back), str(back))
    check("null: A's lanes and B's swapped are not that split", not split_again([back[2], back[3], back[0], back[1]]))

    # "With the input drawn a split is kept, not applied" went with batch 2:
    # it installed a stand-in state.source on the page (Object.create over
    # the generator's, layoutable false) and asked the page's own syncMidi,
    # a path only the page's brain had. The instrument's input drawn with the
    # layers is parity's "layered input" run.

    if bad: print("    first error inside the page: %s" % p.evaluate("() => window.__errs[0]"))
    check("no page errors", not bad, "; ".join(bad[:3]))
    p.close()

    print("\n--- the split point learned (the page's own brain, ?brain=js) ---")
    # Left on ?brain=js in batch 2: the Learn button does not reach the
    # instrument on the default page (above), so this holds the page's own
    # keyboard until the page sends the learned point.
    p = b.new_page(viewport={"width": 1400, "height": 900})
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html?picture=0&brain=js"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    learn = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setScreenKeys(true); setMidiMode('poly');
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      midi.layers.point = 60;
      await wait(60);
      el.midiSplitLearn.click();
      const asking = el.midiSplitLearn.textContent;
      midiNoteOn(65, 100);
      return { asking, point: midi.layers.point, learning: midi.layers.learning,
               said: el.midiSplitLearn.textContent,
               played: midi.notes.map((n) => n.note), b: genSettings(1).voices.map((v) => v.note) };
    }""")
    print("    %s" % learn)
    check("the split point is learned from the next key, which still plays",
          learn["asking"] == "play a key" and learn["point"] == 65 and not learn["learning"]
          and learn["said"] == "at F4" and learn["played"] == [65] and learn["b"] == [65], str(learn))
    check("no page errors on the page's own brain", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("two layers from one keyboard, each drawn and heard as its own")
