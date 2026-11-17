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

    # The split point learned from the next key is held below, on its own
    # page, on the instrument's lanes: until 14 Nov Learn moved the face's
    # point alone (web/docs/after-stage-5.md), and the check read the page's
    # midi.layers.point, which passed whatever the instrument split at.

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
      /* By the controls, which the instrument hears: since stage 5, step 5b's
         second half the grid read here is the instrument's, which a
         persistence and a beam set on the page alone never reached. */
      const set = (e, v, kind) => { if (e.type === 'checkbox') e.checked = v; else e.value = String(v); e.dispatchEvent(new Event(kind, { bubbles: true })); };
      el.dispXY.click(); set(el.persistence, 0, 'change');
      // Full ink for every stroke. The beam's shading keeps a slowly adapting
      // reference per figure, and after a switch it is still tuned to whatever
      // that figure drew before - a dot, here - so a shaded comparison between
      // the two layouts measures the adaptation rather than the drawing.
      const shaded = el.beamXY.checked; set(el.beamXY, false, 'change');
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
      set(el.beamXY, shaded, 'change');
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
                     layout: state.source.layout, edit: el.toneRows.dataset.layerEdit, rowHidden: el.midiKindsRow.hidden && el.midiTwoHands.hidden };
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

    print("\n--- the split point learned, on the instrument ---")
    # On ?brain=js from batch 2 until stage 5, step 5b's second half; then on
    # the default, holding only what the face did, since Learn did not reach
    # the instrument. Since 14 Nov the face sends the learned note before the
    # note itself (hostSendSplit, Keyboard::setSplitPoint), so this reads the
    # instrument's lanes: G3 learned, A3 must land in B's lanes, where at the
    # old C4 it lands in A's. Since 15 Nov Learn itself is told to the
    # instrument too (hostSendLearn, Keyboard::learnSplit), so that in the
    # plugin a host's note can set it: with the face's send of the point cut,
    # the instrument learns G3 from the note on its own - the plugin's path,
    # run on the site. The null cuts both, which is the bug as it was: A3 in
    # A's lanes. (Until 15 Nov the null cut the point's send alone.)
    LEARN = """async (cut) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      if (cut) hostSendSplit = () => {};
      if (cut === 'both') hostSendLearn = () => {};
      setScreenKeys(true); el.midiPoly.click();
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(200);
      el.midiSplitLearn.click();
      const asking = el.midiSplitLearn.textContent;
      midiNoteOn(55, 100);
      const out = { asking, point: midi.layers.point, learning: midi.layers.learning,
                    said: el.midiStripLine.textContent,
                    played: midi.notes.map((n) => n.note), kind: state.source.kind };
      midiNoteOff(55);
      await wait(400);
      midiNoteOn(57, 100);
      return out;
    }"""
    def learned(cut):
        q = b.new_page(viewport={"width": 1400, "height": 900})
        q.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
        q.goto(f"file://{ART}/scope.html?picture=0"); q.wait_for_timeout(1500)
        if q.locator("#helpClose").is_visible(): q.locator("#helpClose").click()
        q.evaluate(BIN, BIN_SRC)
        out = q.evaluate(LEARN, cut)
        e = [round(x[0], 5) for x in q.evaluate(LANES, [57])]
        out["a"], out["b"] = e[0] + e[1], e[2] + e[3]
        state = q.evaluate("() => scopeHost.call('scopeState').then((s) => s && s.code)")
        out["kept"] = q.evaluate("(code) => JSON.stringify((decodeSetup(code) || {}).pluginHands || [])", state)
        q.close()
        return out
    learn, alone, null = learned(False), learned('split'), learned('both')
    print("    learned %s" % {k: learn[k] for k in ("asking", "point", "said", "played", "a", "b")})
    print("    the point's send cut %s; both cut %s" % ({k: alone[k] for k in ("point", "a", "b")}, {k: null[k] for k in ("point", "a", "b")}))
    check("the split point is learned from the next key, which still plays",
          learn["asking"] == "now play a key" and learn["point"] == 55 and not learn["learning"]
          and learn["said"].startswith("G3 and up: the upper hand.") and learn["played"] == [55] and learn["kind"] == "host", str(learn))
    check("the instrument splits at the learned point: A3 over a learned G3 is in B's lanes",
          learn["b"] > 10 * learn["a"] and learn["b"] > 1e-3, "A %.5f B %.5f" % (learn["a"], learn["b"]))
    check("... and the instrument keeps it, a hand its state carries for a project reopened",
          '["c","splitAt","55"]' in learn["kept"], learn["kept"][:300])
    check("with the face's send of the point cut, the instrument learns G3 from the note itself and keeps it: A3 in B's lanes",
          alone["b"] > 10 * alone["a"] and alone["b"] > 1e-3 and '["c","splitAt","55"]' in alone["kept"],
          "A %.5f B %.5f; %s" % (alone["a"], alone["b"], alone["kept"][:200]))
    check("null: with both the point's send and Learn's cut, A3 is in A's lanes, the bug as it was",
          null["point"] == 55 and null["a"] > 10 * null["b"] and '"splitAt"' not in null["kept"], "A %.5f B %.5f" % (null["a"], null["b"]))

    print("\n--- the split by notes: the face and the instrument deal the same hands ---")
    # The rule itself, with its nulls, is core/tests/pieces/splitnotes.py's on
    # the core's keyboard. What is here is the face: its Split row, told to the
    # instrument as a hand's change, and its mirror (layerNotes, which the
    # readout and the strikes read) dealing the hands the instrument's lanes
    # show. Lower: 1 over C3 E3 G3 and then A2 under them: by rank A2 and C3
    # are the lower hand and E3 and G3 the upper; the key split at C4 would
    # put all four in A. The null cuts the face's sends (hostControl), so the
    # instrument never hears "by notes" and splits at its key while the face
    # deals by notes - the two disagree, which this check must see.
    NOTES = """async (args) => {
      const cut = args.cut, notes = args.notes || [48, 52, 55, 45], apart = args.apart == null ? 60 : args.apart;
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setScreenKeys(true); el.midiPoly.click();
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(150);
      // The strip's (17 Nov): Key, Notes and Layer on its edge, Learn on its line by key, the end and the Chord window by notes.
      const row = { split: !el.midiKindsRow.hidden && el.midiKindKey.getAttribute('aria-checked') === 'true',
                    learnByKey: !el.midiSplitLearn.hidden, endByKey: !el.midiEndLowSide.hidden };
      if (cut) hostSync.on = false;
      const pick = (id, v) => { el[id].value = v; el[id].dispatchEvent(new Event('change', { bubbles: true })); };
      if (args.point) { midi.layers.point = args.point; hostSendSplit(); }
      else { pick('midiSplitBy', 'notes'); pick('midiSplitEnd', 'lower'); pick('midiSplitCount', '1'); }
      if (cut) hostSync.on = true;
      row.learnByNotes = !el.midiSplitLearn.hidden; row.endByNotes = !el.midiEndLowSide.hidden && !el.midiWindowNote.hidden;
      // Longer before a reading made soon after the notes, so the split has surely reached the instrument.
      await wait(args.soon ? 400 : 150);
      // 60 ms apart, so each is a note of its own: within 10 ms of the first they are one struck chord (the gather).
      /* args.busy keeps the page busy that long after each note, as a cold
         page's work on a note can; args.turn lets a turn end between them. */
      const busy = (ms) => { const until = performance.now() + ms; while (performance.now() < until); };
      for (const n of notes) {
        midiNoteOn(n, 100);
        if (args.busy) busy(args.busy);
        if (args.turn) await wait(0);
        if (apart) await wait(apart);
      }
      /* Soon after the chord, where a note dealt to one hand and moved to the
         other would ring on in the first (the 25 ms gather's ghost): each
         note's energy in each hand's lanes over the last 4096 samples, read
         args.soon ms after the last note. */
      let soon = null;
      if (args.soon) {
        await wait(args.soon);
        const w = state.source.getLatestWindow(4096), rate = state.source.sampleRate;
        soon = w.map((x) => [45, 48, 52, 55].map((n) => window.__bin(x, 440 * Math.pow(2, (n - 69) / 12), rate)));
      }
      if (!apart) await wait(60);
      const face = [0, 1].map((l) => layerNotes(l).map((h) => h.note).sort((a, b) => a - b));
      const code = snapshot();
      state.lastReadout = 0; await wait(400);
      return { row, face, soon, readout: el.readoutDetail.textContent,
               code: { splitBy: code.splitBy, splitEnd: code.splitEnd, splitCount: code.splitCount } };
    }"""
    def by_notes(cut, notes=None, apart=None, soon=None, point=None, busy=0, turn=False):
        q = b.new_page(viewport={"width": 1400, "height": 900})
        q.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
        q.goto(f"file://{ART}/scope.html?picture=0"); q.wait_for_timeout(1500)
        if q.locator("#helpClose").is_visible(): q.locator("#helpClose").click()
        q.evaluate(BIN, BIN_SRC)
        out = q.evaluate(NOTES, {"cut": cut, "notes": notes, "apart": apart, "soon": soon, "point": point,
                                 "busy": busy, "turn": turn})
        e = q.evaluate(LANES, [45, 48, 52, 55])
        # Each note's energy in A's two lanes and in B's.
        out["a"] = [round(e[0][i] + e[1][i], 5) for i in range(4)]
        out["b"] = [round(e[2][i] + e[3][i], 5) for i in range(4)]
        q.close()
        return out
    told, cut = by_notes(False), by_notes(True)
    print("    told %s" % told)
    print("    the face's sends cut: A %s, B %s" % (cut["a"], cut["b"]))
    in_hands = lambda r, low, high: all(r["a"][i] > 10 * r["b"][i] and r["a"][i] > 1e-3 for i in low) \
        and all(r["b"][i] > 10 * r["a"][i] and r["b"][i] > 1e-3 for i in high)
    check("a split shows Key lit on the strip's edge, Learn on its line by key, and by notes the counted end and the Chord window's note",
          told["row"] == {"split": True, "learnByKey": True, "endByKey": False, "learnByNotes": False, "endByNotes": True},
          str(told["row"]))
    check("the face deals Lower: 1 by rank: A2 and C3 the lower hand, E3 and G3 the upper",
          told["face"] == [[45, 48], [52, 55]], str(told["face"]))
    check("and the instrument plays those hands: A2 and C3 in A's lanes, E3 and G3 in B's",
          in_hands(told, [0, 1], [2, 3]), "A %s B %s" % (told["a"], told["b"]))
    check("null: the instrument never told, it splits at its key and all four are in A's lanes",
          in_hands(cut, [0, 1, 2, 3], []) and not in_hands(cut, [0, 1], [2, 3]) and cut["face"] == [[45, 48], [52, 55]],
          "A %s B %s" % (cut["a"], cut["b"]))
    check("the split by notes is in the setup the face writes, and in the readout",
          told["code"] == {"splitBy": "notes", "splitEnd": "lower", "splitCount": 1}
          and "split by notes: lowest 1 to the lower hand" in told["readout"], str(told["code"]) + " " + told["readout"][:200])

    # A chord struck at once (16 Nov, the gather): G3 E3 C3 top first in one
    # tick reach the instrument in one block, and are one chord, dealt by
    # pitch - C3 the lower hand, E3 and G3 the upper - on the face and in the
    # instrument's lanes. The null is the same notes 60 ms apart, three notes
    # in turn, each the lowest held as it starts: all three the lower hand's,
    # which is what a chord struck at once was dealt before the gather.
    once, apart = by_notes(False, [55, 52, 48], 0), by_notes(False, [55, 52, 48], 60)
    print("    at once: face %s A %s B %s; 60 ms apart: face %s A %s B %s"
          % (once["face"], once["a"], once["b"], apart["face"], apart["a"], apart["b"]))
    check("G3 E3 C3 struck at once, top first: one chord, C3 the lower hand and E3 G3 the upper, on the face and in the lanes",
          once["face"] == [[48], [52, 55]] and in_hands(once, [1], [2, 3]), "A %s B %s" % (once["a"], once["b"]))
    check("null: the same three 60 ms apart are three notes, each the lowest as it starts, and all three the lower hand's",
          apart["face"] == [[48, 52, 55], []] and in_hands(apart, [1, 2, 3], []) and not in_hands(apart, [1], [2, 3]),
          "A %s B %s" % (apart["a"], apart["b"]))

    # A chord the page plays in one turn is struck at once however long the
    # page takes over each note (16 Nov): what a turn sends the worklet goes
    # as the turn ends, in order. The page kept busy 15 ms after each of
    # G3 E3 C3, which put them further apart in the instrument than its 10 ms
    # look-ahead when each was sent as it was played, is still one chord: C3
    # the lower hand, E3 and G3 the upper. The null lets a turn end between
    # the notes, so each goes when it is played, 15 ms apart: three notes,
    # each the lowest as it starts, all the lower hand's.
    slow, turns = by_notes(False, [55, 52, 48], 0, None, None, 15), by_notes(False, [55, 52, 48], 0, None, None, 15, True)
    print("    busy 15 ms a note, one turn: A %s B %s; a turn between: A %s B %s" % (slow["a"], slow["b"], turns["a"], turns["b"]))
    check("G3 E3 C3 played in one turn with the page busy 15 ms after each are one chord in the instrument: C3 low, E3 G3 high",
          in_hands(slow, [1], [2, 3]), "A %s B %s" % (slow["a"], slow["b"]))
    check("null: a turn between them, each sent as played 15 ms apart, and all three are the lower hand's",
          in_hands(turns, [1, 2, 3], []) and not in_hands(turns, [1], [2, 3]), "A %s B %s" % (turns["a"], turns["b"]))

    # No ghost (16 Nov, the look-ahead): split by notes the instrument holds
    # every note back 10 ms and deals the chord before any of it sounds, so
    # E3 and G3, the upper hand's, are not in the lower hand's lanes even in
    # the first moments after the chord, where the 25 ms gather this replaced
    # sounded them low and moved them, leaving each ringing on in the lower
    # hand for its release. Read 80 ms after G3 E3 C3 struck at once, top
    # first, over the last 4096 samples - a window that holds the onset, so
    # every note leaks a little into every bin (A2, never played, reads a
    # third of C3, and the leakage varies twofold from page to page with
    # where the onset falls) - so each is held under a quarter of C3, where
    # the key split at D3, which deals the same hands and has nothing to
    # move, leaves about a tenth (read 70 ms after, the same moment in its
    # notes' lives, and printed beside it). The ghost was some thirty times
    # that: G3 over C3 itself. The null is the same three
    # 60 ms apart, all the lower hand's, read alike: E3 and G3 are in A's
    # lanes then, so the reading can see a note there. (The core's render
    # check, splitnotes.py, holds the same to the bit; this is the site.)
    near, spread = by_notes(False, [55, 52, 48], 0, 80), by_notes(False, [55, 52, 48], 60, 80)
    keyed = by_notes(False, [55, 52, 48], 0, 70, 50)
    in_a = lambda r: [round(r["soon"][0][i] + r["soon"][1][i], 5) for i in range(4)]
    print("    80 ms after, the lower hand's lanes: at once %s, the key split %s, 60 ms apart %s" % (in_a(near), in_a(keyed), in_a(spread)))
    no_ghost = lambda r: in_a(r)[1] > 1e-2 and all(in_a(r)[i] < 0.25 * in_a(r)[1] for i in (2, 3))
    check("80 ms after G3 E3 C3 struck at once, E3 and G3 in the lower hand's lanes are under a quarter of C3 there, as the key split's leakage is",
          no_ghost(near), "by notes %s, by key %s" % (in_a(near), in_a(keyed)))
    check("null: the same three 60 ms apart are all the lower hand's, and E3 and G3 in its lanes are as strong as C3",
          not no_ghost(spread), str(in_a(spread)))

    check("no page errors on the instrument's face", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("two layers from one keyboard, each drawn and heard as its own")
