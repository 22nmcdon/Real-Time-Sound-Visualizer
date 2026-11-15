"""The face reads the instrument (stage 5, step 5b).

On the site the sound and the picture it reads are the instrument's, compiled
in a worklet; until 5b the page also stepped a picture of its own beside it -
a second grid, a meter, the stage and the photocell - and the face showed
that one. Since 5b the instrument posts what the face shows of its picture
(Instrument::faceServed: the meter, the photocell, the stage's reads and
hold, the picture's sources, the offsets on the screen's own destinations),
the page writes it into its own objects as the readings arrive (takeFace)
and steps none of it.

What would go wrong, and what is checked for it:

- the Picture section's three bars, or its held loop, showing the page's
  stage: the bars are the instrument's reads to the bit; the null is a value
  the page's own stage was left holding, which a face still stepping its own
  would slew from rather than drop;
- the photocell's card, its reticle and its value reading the page's
  photocell: the same, with the reticle on the lit figure;
- the readout's "loop ..." and the overlay's badge reading the page's meter:
  the readout says the instrument's verdict (until stage 5's step 6 the null
  was the page's own meter, never fed, which still said "listening");
- the screen's own destinations (the turn) worked out by the page's matrix:
  the face's offset is the instrument's; the null is a routing told to the
  page alone, which a page summing its own would turn the screen by.

Until step 6 the page's own picture, photocell, visual matrix and arpeggio
walk were counted here at nought (brainCount), and the boot was held to
waiting for the instrument against parity's harness's page brain; step 6
deleted those steps, the counters and the harness's flag together.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, ok, detail=""):
    check("null: " + name, ok, detail)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.locator("#trace").click(position={"x": 5, "y": 5})   # the press a browser waits for
    p.wait_for_timeout(600)

    print("\n--- a held note, with the picture heard ---")
    # X-Y, a held fifth in the dyad, and the Picture amount up, by the face's own controls.
    p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      document.getElementById('dispXY').click();
      document.getElementById('midiDyad').click();
      const amount = document.getElementById('pictureAmount'); amount.value = '60'; amount.dispatchEvent(new Event('input'));
      midiNoteOn(57, 100); midiNoteOn(64, 100);
      await wait(2500);
    }""")
    read = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const face = () => state.source.face;
      const bars = () => Object.fromEntries([...el.pictureReads.children].map((bar) => [bar.dataset.read, bar.style.getPropertyValue('--v')]));
      const out = { host: state.source.kind, hasFace: !!face() };
      // The bars as painted against the instrument's reads at the same frame.
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      out.bars = bars();
      out.inst = { glow: face().stage.glow, motion: face().stage.motion, memory: face().stage.memory, hold: face().stage.hold };
      out.page = { glow: pictureStage.glow, motion: pictureStage.motion, memory: pictureStage.memory, hold: pictureStage.hold };
      // The null: the page's stage left holding values of its own.
      pictureStage.glow = 0.123; pictureStage.motion = 0.456; pictureStage.hold = 0.5;
      await wait(150);
      out.left = { glow: pictureStage.glow, motion: pictureStage.motion, hold: pictureStage.hold };
      out.instAfter = { glow: face().stage.glow, motion: face().stage.motion, hold: face().stage.hold };
      out.bars2 = bars();
      // The verdict: the readout's word, the instrument's meter and the page's own, never fed.
      await wait(300);
      out.readout = el.readoutDetail.textContent;
      out.verdict = state.source.meter.verdict;
      return out;
    }""")
    print("    instrument %s\n    page       %s\n    bars       %s" % (read["inst"], read["page"], read["bars"]))
    check("the default page plays the instrument, and it posts the face's picture", read["host"] == "host" and read["hasFace"], str(read["host"]))
    check("the page's stage is the instrument's, to the bit", read["page"] == read["inst"], "%s against %s" % (read["page"], read["inst"]))
    check("and the Picture section's bars show it", all(read["bars"][k] == ("%.3f" % read["inst"][k]) for k in ("glow", "motion", "memory")),
          "%s against %s" % (read["bars"], read["inst"]))
    check("and the reads are not nothing: a held fifth lights the screen", read["inst"]["glow"] > 0.05, "%.3f" % read["inst"]["glow"])
    null("values the page's own stage was left holding are gone at the next reading",
         read["left"] == read["instAfter"] and read["left"]["glow"] != 0.123 and read["left"]["hold"] != 0.5,
         "%s against %s" % (read["left"], read["instAfter"]))
    check("the readout says the loop's verdict, and it is the instrument's meter's",
          ("loop " + read["verdict"]) in read["readout"] and read["verdict"] != "listening", "%r, %s" % (read["readout"], read["verdict"]))
    # Until stage 5's step 6 the null was the page's own meter, never fed, which
    # said something else; that meter went with the page's picture engine.
    other = "running away" if read["verdict"] != "running away" else "settled"
    null("the same reading of a verdict the instrument did not give fails", ("loop " + other) not in read["readout"],
         "%r against %s" % (read["readout"], other))

    print("\n--- the photocell ---")
    photo = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      if (!photo.on) document.getElementById('photoButton').click();
      // On the figure: the reticle swept until the instrument's photocell reads light.
      let best = null;
      for (const [u, v] of [[0.5, 0.5], [0.3, 0.5], [0.7, 0.5], [0.5, 0.3], [0.5, 0.7], [0.25, 0.25], [0.75, 0.75], [0.25, 0.75], [0.75, 0.25]]) {
        movePhoto(u, v); await wait(700);
        if (state.source.face.photo > 0.05) { best = [u, v]; break; }
      }
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      const f = state.source.face;
      const out = { best, inst: f.photo, page: photo.value, card: cardReading(MOD_SOURCES.get('photo.1') || PHOTO_SOURCE),
                    lit: el.photoReticle.style.getPropertyValue('--lit') };
      photo.value = 0.987;
      await wait(150);
      out.left = photo.value; out.instAfter = state.source.face.photo;
      document.getElementById('photoButton').click();
      return out;
    }""")
    print("    %s" % photo)
    check("the photocell, aimed at the figure, reads light on the instrument", photo["best"] is not None and photo["inst"] > 0.05, str(photo))
    check("and the face's photocell is the instrument's, its card and reticle saying so",
          # As numbers: JavaScript's toFixed and Python's % round a half differently (0.0625 is "0.063" and "0.062").
          photo["page"] == photo["inst"] and abs(float(photo["card"]) - photo["inst"]) <= 0.0051
          and abs(float(photo["lit"]) - photo["inst"]) <= 0.00051, str(photo))
    null("a value the page's photocell was left holding is gone at the next reading",
         photo["left"] == photo["instAfter"] and photo["left"] != 0.987, str(photo))

    print("\n--- the screen's own destinations ---")
    turn = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      // LFO 1 onto the turn, patched as a hand does (addRouting reaches the instrument), at full.
      addRouting('lfo1', 'view.rotate');
      const r = state.modRoutings.find((x) => x.sourceId === 'lfo1' && x.destId === 'view.rotate');
      setDepth(r, 100, true);
      await wait(800);
      const pairs = [];
      for (let i = 0; i < 6; i++) {
        await new Promise((res) => requestAnimationFrame(res));
        pairs.push([state.rotateMod, state.source.face.offsets['view.rotate']]);
      }
      // Off again, and the null: the same routing told to the page alone.
      dropRoutingOn('lfo1', 'view.rotate');
      await wait(500);
      const off = state.rotateMod;
      state.modRoutings.push({ sourceId: 'lfo1', destId: 'view.rotate', amount: 1 });
      await wait(400);
      const alone = [];
      for (let i = 0; i < 4; i++) {
        await new Promise((res) => requestAnimationFrame(res));
        alone.push([state.rotateMod, state.source.face.offsets['view.rotate'], sourceNow(MOD_SOURCES.get('lfo1'))]);
      }
      state.modRoutings.pop();
      return { pairs, off, alone };
    }""")
    print("    %s" % turn)
    moved = max(abs(a) for a, _ in turn["pairs"])
    check("LFO 1 on the turn turns the face's screen by the instrument's offset, frame by frame",
          all(a == b_ for a, b_ in turn["pairs"]) and moved > 0.01, "largest %.3f" % moved)
    null("a routing told to the page alone turns nothing: the instrument has none",
         all(a == 0 and b_ == 0 for a, b_, _ in turn["alone"]) and any(abs(v) > 0.05 for _, _, v in turn["alone"]),
         str(turn["alone"]))

    print("\n--- the rest of the face (5b's second half) ---")
    rest = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const frames = (n) => new Promise((done) => { let k = 0; const f = () => (++k >= n ? done() : requestAnimationFrame(f)); requestAnimationFrame(f); });
      const out = {};
      // The grid: the instrument's, and not the dark stand-in the page reads before it has one (the page has no grid of its own).
      await frames(3);
      let most = 0; for (const v of phosphor.grid) most = Math.max(most, v);
      out.grid = { same: phosphor.grid === state.source.grid, dark: phosphor.grid === PHOSPHOR_DARK, most };
      // The harmony line in poly: the instrument's outline, not the page's own laying out of the notes.
      // By the button, which the instrument hears (setMidiMode alone is the page's).
      midiPanic(); el.midiPoly.click(); midiNoteOn(57, 100); midiNoteOn(64, 100); await wait(600);
      const said = harmonySaid(genSettings()), outline = state.source.face.outlines[0];
      const keep = polyVoices; window.polyVoices = () => [{ role: 'x', freq: 100 }, { role: 'y', freq: 300 }];
      out.harmony = { said, want: outline ? [harmonyText(outline[0], outline[1])] : null, patched: harmonySaid(genSettings()),
                      page: [harmonyText(100, 300)] };
      window.polyVoices = keep;
      // The arpeggio: the instrument walks it, and the face shows its notes; the page's own walk does not move.
      el.arpRate.value = '1/16'; el.arpRate.dispatchEvent(new Event('change'));
      el.arpMode.value = 'up'; el.arpMode.dispatchEvent(new Event('change'));
      midiPanic(); midiNoteOn(57, 100); midiNoteOn(64, 100); midiNoteOn(69, 100);
      const seen = new Set(), shown = new Set(), pairs = [];
      for (let i = 0; i < 60; i++) {
        await new Promise((r) => requestAnimationFrame(r));
        const f = state.source.face.arp.join(','), c = arp.current.map((n) => n.note).join(',');
        seen.add(f); shown.add(c); if (i % 6 === 0) pairs.push([f, c]);
      }
      out.arp = { seen: [...seen], shown: [...shown], pairs };
      el.arpMode.value = 'off'; el.arpMode.dispatchEvent(new Event('change')); midiPanic();
      // The figures: two hands split, the instrument lays out two, and the page's own layout answer is not asked.
      midiNoteOn(48, 100); midiNoteOn(55, 100);
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      midiNoteOn(72, 100); midiNoteOn(79, 100); await wait(800);
      out.figures = { served: state.source.face.figures, shown: sourceFigures() };
      const kept = state.source.layout; state.source.setLayout('one');
      out.figures.pageOne = sourceFigures();
      state.source.setLayout(kept);
      /* Lane three's full scale: the instrument's offset, a routing on it heard there; one told the page alone moves nothing.
         At a depth of minus a hundred: a lane's full scale starts at its top (0 dB), so an offset upwards is
         held at nought by the instrument, and LFO 1, slow, can sit in its upper half for every frame read -
         the first run of this row read nought four times for that reason, a fixture that could not show it. */
      addRouting('lfo1', 'view.scale3');
      const r3 = state.modRoutings.find((x) => x.destId === 'view.scale3'); if (r3) setDepth(r3, -100, true);
      state.modRoutings.push({ sourceId: 'lfo1', destId: 'view.scale4', amount: 1 });
      await wait(700);
      const lanes = [];
      for (let i = 0; i < 4; i++) {
        await new Promise((r) => requestAnimationFrame(r));
        const r = state.modRoutings.find((x) => x.destId === 'view.scale3'), dest = MOD_DESTS.get('view.scale3');
        lanes.push([state.channels[2] ? state.channels[2].fsMod : null, state.source.face.offsets['view.scale3'],
                    state.channels[3] ? state.channels[3].fsMod : null,
                    // What the page's own matrix would have summed there.
                    r ? sourceNow(MOD_SOURCES.get('lfo1')) * routingAmount(MOD_SOURCES.get('lfo1'), r.amount) * dest.span : null]);
      }
      state.modRoutings.pop(); dropRoutingOn('lfo1', 'view.scale3');
      out.lanes = lanes;
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change')); midiPanic(); el.midiDyad.click();
      return out;
    }""")
    print("    %s" % rest)
    g = rest["grid"]
    check("the grid the face reads is the instrument's", g["same"], str(g))
    null("it is not the dark stand-in: a held fifth is lit on it", not g["dark"] and g["most"] > 0.1, str(g))
    h = rest["harmony"]
    check("the harmony line names the instrument's outline of the voices", h["want"] is not None and h["said"] == h["want"], str(h))
    null("the page's own laying out of the notes, made to say a twelfth, is not read", h["patched"] == h["said"] and h["patched"] != h["page"], str(h))
    a = rest["arp"]
    check("the arpeggio is the instrument's: the face shows its notes, more than one in turn, as they change",
          len(a["seen"]) >= 3 and all(f == c for f, c in a["pairs"] if f) and len(a["shown"]) >= 3, str(a))
    null("the face's notes held against the instrument's a reading late do not all agree",
         not all(f == c for (f, _), (_, c) in zip(a["pairs"][1:], a["pairs"][:-1]) if f), str(a["pairs"]))
    fg = rest["figures"]
    check("split, the face draws the two figures the instrument lays out", fg["served"] == 2 and fg["shown"] == [[0, 1], [2, 3]], str(fg))
    null("the page's own layout told one figure is not what is drawn", fg["pageOne"] == [[0, 1], [2, 3]], str(fg))
    # Every lane's full scale is a destination of the instrument's since 15
    # Nov (screen.h); until then only the first two were, so a routing onto
    # lane three was heard by nothing and, since 5b's second half, moved
    # nothing on the face either - which this row required, nought every
    # frame. Now the face's lane three is scaled by the instrument's offset
    # and by nothing of its own: the two the same every frame, and moving.
    # core/tests/pieces/lanescale.py holds what it does to the picture and
    # to Scan.
    ln = rest["lanes"]
    lane_moves = lambda rows: all(x[0] == x[1] for x in rows) and max(abs(x[1] or 0) for x in rows) > 0.05
    check("lane three's full scale is the instrument's offset, frame by frame, and a routing on it moves it",
          lane_moves(ln), str(ln))
    null("the reading until 15 Nov, nought every frame, is not that", not lane_moves([[0, 0, 0, x[3]] for x in ln]))
    null("and a routing on lane four told the page alone moves nothing", all(x[2] == 0 for x in ln), str(ln))

    # Over all of it the page stepped no picture, photocell or screen matrix
    # of its own, and the boot waited for the instrument, stepping nothing of
    # the page's own meanwhile: counted here (brainCount) until stage 5's step
    # 6 deleted those steps, and with them the counters. A browser that cannot
    # start the instrument draws no frame at all (wasmtest.py).
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the face shows the instrument's picture, and steps none of its own")
