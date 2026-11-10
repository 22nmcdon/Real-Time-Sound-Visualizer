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

The voices are the page's own core here (makeGeneratorCore); the compiled one
is held to it by core/tests/parity.py, whose voice runs strike notes into
held chords.
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

HZ = lambda note: 440 * 2 ** ((note - 69) / 12)

# Steps of [voices or omitted, samples, keep, layer].
RUN = """([steps, shape]) => {
  const rate = 44100;
  const quiet = [0, 1].map(() => ({ shape: 'sine', rate: 1, depth: 0, phase: 0, held: 0, value: 0 }));
  const core = makeGeneratorCore(rate, GEN_SLOTS, quiet);
  for (const layer of [0, 1]) {
    core.set('shape', shape || 'ramp', layer); core.set('attackMs', 1, layer); core.set('decayMs', 1, layer);
    core.set('sustain', 1, layer); core.set('releaseMs', 5, layer);
  }
  const kept = [];
  for (const step of steps) {
    const [voices, n, keep, layer] = step;
    if (voices !== undefined) core.set('voices', voices, layer || 0);
    const a = [0, 1, 2, 3, 4, 5].map(() => new Float32Array(n));
    core.block(a[0], a[1], n, a[2], a[3], a[4], a[5]);
    if (keep) kept.push((layer || 0) === 1 ? [Array.from(a[4]), Array.from(a[5])] : [Array.from(a[0]), Array.from(a[1])]);
  }
  return kept;
}"""

def voice(note, role):
    return {"note": note, "freq": HZ(note), "velocity": 1, "role": role}

def apart(a, b, start=0):
    return max(max(abs(x - y) for x, y in zip(a[c][start:], b[c][start:])) for c in (0, 1))


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html?brain=js&picture=0"); p.wait_for_timeout(700)
    corpus.install(p)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    run = lambda steps, shape='ramp': p.evaluate(RUN, [steps, shape])

    print("\n--- a chord built a note at a time draws the struck chord's figure ---")
    C, E, G = 48, 52, 55
    chord = [voice(C, "x"), voice(E, "u"), voice(G, "y")]
    # A square as well as the ramp: its edges are smoothed by where the phase
    # is in the sample, so it would show a phase that was right only roughly.
    for layer, shape in ((0, "ramp"), (1, "ramp"), (0, "square")):
        # 1000 and 1337 samples: not whole cycles of anything here, so a
        # joiner at nought is somewhere else in its cycle than in step.
        built = run([[[voice(C, "x")], 1000, False, layer], [[voice(C, "x"), voice(E, "y")], 1337, False, layer],
                     [chord, 3000, True, layer]], shape)[0]
        whole = run([[chord, 5437, True, layer]], shape)[0]
        struck = [ch[-3100:-100] for ch in whole]
        late = [ch[-3000:] for ch in whole]
        same, null = apart(built, struck, 2200), apart(built, late, 2200)
        name = ("A" if layer == 0 else "B") + ", " + shape
        print("    layer %s: built against struck %.2e; against it a hundred samples out of step %.3f" % (name, same, null))
        check("layer %s: the chord built a note at a time draws the struck chord's figure, sample for sample" % name,
              same < 1e-4, "%.2e" % same)
        check("layer %s: and the comparison fails out of step" % name, null > 0.05, "%.3f" % null)

    print("\n--- the same chord struck twice draws the same figure ---")
    twice = run([[chord, 4410, True], [[], 4410, False], [[voice(50, "xy")], 2205, False], [[], 4410, False],
                 [chord, 4410, True]])
    shifted = [ch[100:] + ch[:100] for ch in twice[1]]
    same, null = apart(twice[0], twice[1], 200), apart(twice[0], shifted, 200)
    print("    struck twice %.2e; the second out of step %.3f" % (same, null))
    check("a chord struck twice, with other notes and time between, draws the same figure", same < 1e-6, "%.2e" % same)
    check("and the comparison fails with the second strike out of step", null > 0.05, "%.3f" % null)

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
    said = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const read = async () => { await wait(450); return el.readoutDetail.textContent; };
      const out = {};
      setDisplay('xy'); genSet('shape', 'sine'); genSet('freq', 220); genSet('interval', 7); genSet('just', false);
      out.dyad = await read();
      genSet('just', true); out.dyadJust = await read();
      genSet('interval', 0); out.unison = await read();
      setScreenKeys(true); setMidiMode('poly');
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
      setMidiMode('dyad'); setScreenKeys(false);
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
    loop = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const out = {};
      // The old library's Harmonic tone, from before P8g: the plain tone this
      // was measured on, whatever the bank's boot preset comes to set.
      loadCorpus('Harmonic tone'); setDisplay('xy'); genSet('freq', 220);
      for (const [name, interval, just] of [['just fifth', 7, true], ['equal third', 4, false]]) {
        genSet('interval', interval); genSet('just', just);
        await wait(800); pictureMeter.reset();
        const change = [];
        for (let k = 0; k < 40; k++) { await wait(150); change.push(pictureMeter.change); }
        change.sort((a, b) => a - b);
        out[name] = { change: change[20], verdict: pictureMeter.verdict(), memory: pictureStage.memory };
      }
      return out;
    }""")
    print("    %s" % loop)
    fifth, third = loop["just fifth"], loop["equal third"]
    # The still fifth still changes a little a frame, the beam's own flicker
    # (0.004 to 0.014 measured); the turning third half as much again at
    # least (0.032 against 0.014 at the closest). The verdict is the check that
    # matters; the margin only keeps it from passing on two settled readings.
    check("a held just fifth reads still to the picture: settled", fifth["verdict"] == "settled", str(fifth))
    check("and an equal third, turning, reads moving, changing more a frame",
          third["verdict"] != "settled" and third["change"] > 1.5 * fifth["change"], "%s against %s" % (third, fifth))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("a chord draws one figure, and the readout says how fast it turns")
