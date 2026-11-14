"""Harmony as geometry (P6): a chord draws one figure, and the readout says
what the figure's outline is and how fast it turns.

What would go wrong, and what is checked for it:

- a chord built a note at a time drawing a different figure from the same
  chord struck at once, because a note joining held notes started at phase
  nought wherever the others were. Checked sample for sample of the drawn
  pair against the struck chord, on both layers. The core's voices are not
  reachable from here (`core.voices` is a copy), so the null is the struck
  chord a hundred samples out of step, and the mutation pass is what puts the
  joiner back at nought and watches this fail;
- a chord struck twice drawing two figures (a guard: every fresh strike is
  born at nought); the null is the second strike out of step;
- the readout naming the wrong interval, or turning at the wrong rate: a just
  fifth still, an equal fifth at |2 f_high - 3 f_low|, a third, an octave and
  a fifth, a tritone with no simple ratio; the null is the rate a wrong ratio
  would give;
- the readout reading the wrong notes: the dyad's pair, poly's outline, each
  layer's outline with a split, and A against B;
- the geometry not reaching the loop: a held just fifth reads still to the
  picture meter, an equal third moving.

Since stage 5, step 3, batch 4 (13 Nov) the figures - the chord built a note
at a time, struck twice, and the third turning on the picture's meter - are
core/tests/pieces/harmony.py's, on the core's own generator and meter; here
they were a makeGeneratorCore built in the page. The readout's words and the
notes it reads are the face's, on the default page. The last two rows, "a
held just fifth reads settled" and its twin, stayed on the page's own brain
until stage 5, step 5a: on the instrument's own meter the still fifth read
"cycling". Since 5a the meter's verdict reads change over the eye's time
(METER_EYE in scope.html says why), and the two rows read the instrument's
meter on the default page.
"""
import math, os, sys
from playwright.sync_api import sync_playwright
import corpus

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, ok, detail=""):
    check("null: " + name, ok, detail)

HZ = lambda note: 440 * 2 ** ((note - 69) / 12)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(700)
    corpus.install(p)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    print("\n--- the readout's words: the interval and how fast it turns ---")
    words = p.evaluate("""() => {
      const et = (n) => 220 * Math.pow(2, n / 12);
      return { justFifth: harmonyText(220, 330), equalFifth: harmonyText(220, et(7)), rate: harmonyOf(220, et(7)).rate,
               third: harmonyText(220, et(4)), octFifth: harmonyText(220, 660), octave: harmonyText(220, 440),
               tritone: harmonyText(220, et(6)), flipped: harmonyText(330, 220) };
    }""")
    print("    %s" % words)
    want_rate = abs(2 * 220 * 2 ** (7 / 12) - 3 * 220)
    wrong_rate = abs(3 * 220 * 2 ** (7 / 12) - 4 * 220)
    check("a just fifth is a fifth, still", words["justFifth"] == "fifth, still", words["justFifth"])
    check("an equal fifth turns at |2 f_high - 3 f_low|, 0.745 a second at A3", abs(words["rate"] - want_rate) < 1e-9
          and words["equalFifth"] == "fifth, turning 0.74 a second", "%s, %.4f" % (words["equalFifth"], words["rate"]))
    check("and not at the rate a wrong ratio would give", abs(words["rate"] - wrong_rate) > 1, "%.3f" % wrong_rate)
    check("an equal third turns nearly nine times a second", words["third"] == "major third, turning 8.73 a second",
          words["third"])
    check("octaves are counted and the interval named within them",
          words["octFifth"] == "octave and a fifth, still" and words["octave"] == "octave, still", str(words))
    check("a tritone has no simple ratio, and says so", words["tritone"].startswith("no simple ratio"), words["tritone"])
    check("the order of the two notes does not matter", words["flipped"] == words["justFifth"], words["flipped"])

    print("\n--- the readout reads the right notes ---")
    # The readout is the face's: its words are harmonySaid's, over the face's
    # mirror of the notes and the tone. Until batch 4 it was driven by
    # setMidiMode and genSet, which the instrument never hears; it is driven
    # here as a player drives it - the mode buttons, the interval menu and the
    # tuning switch - so the face's mirror and the instrument are told the
    # same. That the readout reads the mirror and not the instrument is one
    # of the places step 5 points the face at the instrument's readings.
    said = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const read = async () => { await wait(450); return el.readoutDetail.textContent; };
      const menu = (e, v) => { e.value = v; e.dispatchEvent(new Event('change')); };
      const out = {};
      /* A note held in Mono, which leaves the interval to the menu: the site
         waits for a note since 10 Nov, and this dyad was the tone it drew
         with none. Struck first, since a note sets the pitch it plays. */
      el.midiMono.click(); midiNoteOn(57, 127);
      setDisplay('xy'); menu(el.shape, 'sine'); menu(el.interval, '7'); el.tuneEqual.click();
      out.dyad = await read();
      el.tuneJust.click(); out.dyadJust = await read();
      menu(el.interval, '0'); out.unison = await read();
      midiNoteOff(57);
      setScreenKeys(true); el.midiPoly.click();
      for (const n of [57, 61, 64]) midiNoteOn(n, 100);
      out.poly = await read();
      for (const n of [57, 61, 64]) midiNoteOff(n);
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      for (const n of [48, 55, 64, 72]) midiNoteOn(n, 100);
      out.split = await read();
      el.midiLayerPair.value = 'against'; el.midiLayerPair.dispatchEvent(new Event('change'));
      out.against = await read();
      for (const n of [48, 55, 64, 72]) midiNoteOff(n);
      el.midiLayerPair.value = 'each'; el.midiLayerPair.dispatchEvent(new Event('change'));
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change'));
      el.midiDyad.click(); setScreenKeys(false);
      return out;
    }""")
    for k, v in said.items(): print("    %-8s %s" % (k, v[:160]))
    check("the dyad's pair: an equal fifth, turning", "fifth, turning 0.74 a second" in said["dyad"], said["dyad"])
    check("and just, still - where the readout used to say nothing", "fifth, still" in said["dyadJust"], said["dyadJust"])
    check("and at unison, nothing", "unison" not in said["unison"] and "still" not in said["unison"], said["unison"])
    check("poly's outline: the lowest note against the highest, the inner one left out",
          "fifth, turning 0.74 a second" in said["poly"] and "major third" not in said["poly"], said["poly"])
    check("with a split, each layer's outline: A a fifth, B a minor sixth",
          "A: fifth" in said["split"] and "B: minor sixth" in said["split"], said["split"])
    check("and A against B, A's lowest against B's highest", "A against B: " in said["against"]
          and "A: fifth" not in said["against"], said["against"])

    print("\n--- the geometry reaches the loop ---")
    # On the default page since stage 5, step 5a, read off the instrument's
    # own picture meter (its readings' `meter`, which the face's verdict
    # reads in 5b). Until 5a this stayed on the page's own brain: the
    # instrument's meter called the still fifth "cycling". The cause was not
    # its grid - at the same persistence the two grids change alike, 0.0064
    # and 0.0054 a frame - but the verdict reading change frame against
    # frame, where each frame is one trigger-placed window and a still
    # figure with detail lands a little differently in each (0.027 a frame
    # at no persistence); the verdict reads it over the eye's time now
    # (METER_EYE). Driven as a player drives it: Mono, the note, X-Y, the
    # interval menu and the tuning buttons, which the instrument hears.
    loop = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const menu = (e, v) => { e.value = v; e.dispatchEvent(new Event('change')); };
      const out = {};
      // The old library's Harmonic tone, from before P8g: the plain tone this
      // was measured on, whatever the bank's boot preset comes to set.
      loadCorpus('Harmonic tone'); await wait(300);
      el.midiMono.click(); midiNoteOn(57, 127); el.dispXY.click();
      for (const [name, interval, just] of [['just fifth', '7', true], ['equal third', '4', false]]) {
        menu(el.interval, interval); (just ? el.tuneJust : el.tuneEqual).click();
        // The verdict's window is four seconds: wait it out, then read for six.
        await wait(4800);
        const change = [], seen = [];
        for (let k = 0; k < 40; k++) {
          await wait(150);
          const m = state.source.meter;
          if (m) { change.push(m.change); seen.push(m.seen); }
        }
        change.sort((a, b) => a - b); seen.sort((a, b) => a - b);
        const m = state.source.meter;
        out[name] = { change: change[change.length >> 1], seen: seen[seen.length >> 1], verdict: m && m.verdict,
                      host: state.source.kind === 'host', n: change.length };
      }
      midiNoteOff(57);
      return out;
    }""")
    print("    %s" % loop)
    fifth, third = loop["just fifth"], loop["equal third"]
    check("a held just fifth reads still to the instrument's picture: settled", fifth["host"] and fifth["n"] == 40
          and fifth["verdict"] == "settled", str(fifth))
    check("and an equal third, turning, reads moving, changing more as the eye sees it",
          third["verdict"] not in ("settled", "listening") and third["seen"] > 1.5 * fifth["seen"], "%s against %s" % (third, fifth))
    null("the still fifth's verdict is not the turning third's", fifth["verdict"] != third["verdict"], "%s, %s" % (fifth["verdict"], third["verdict"]))
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("a chord draws one figure, and the readout says how fast it turns")
