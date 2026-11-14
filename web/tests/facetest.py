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
  the readout says the instrument's verdict; the null is the page's own
  meter, never fed, which still says "listening" under it;
- the screen's own destinations (the turn) worked out by the page's matrix:
  the face's offset is the instrument's; the null is a routing told to the
  page alone, which a page summing its own would turn the screen by;
- any of it passing because the page's brain is still stepping: over the
  same stretch the page's picture, photocell and visual matrix are counted
  at nought (brainCount), and the null is the boot frames before the
  instrument answered, where they are not.
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
    boot = p.evaluate("() => Object.assign({}, globalThis.__brainCounts)")

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
    before = p.evaluate("() => Object.assign({}, globalThis.__brainCounts)")
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
      out.pageVerdict = pictureMeter.verdict();
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
    null("the page's own meter, which the face no longer feeds, says something else", read["pageVerdict"] != read["verdict"],
         "the page's %s" % read["pageVerdict"])

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
          photo["page"] == photo["inst"] and photo["card"] == "%.2f" % photo["inst"] and photo["lit"] == "%.3f" % photo["inst"], str(photo))
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

    after = p.evaluate("() => Object.assign({}, globalThis.__brainCounts)")
    delta = lambda k: after.get(k, 0) - before.get(k, 0)
    steps = ["pictureStep", "photoStep", "visualMatrix.view.rotate"]
    print("    over the run: %s" % {k: delta(k) for k in steps + ["frames.host"]})
    check("over all of it the page stepped no picture, photocell or screen matrix of its own",
          delta("frames.host") > 100 and all(delta(k) == 0 for k in steps), str({k: delta(k) for k in steps}))
    null("the boot frames before the instrument answered did step the page's picture", boot.get("pictureStep", 0) > 0,
         str({k: boot.get(k, 0) for k in ("pictureStep", "frames.tone")}))
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the face shows the instrument's picture, and steps none of its own")
