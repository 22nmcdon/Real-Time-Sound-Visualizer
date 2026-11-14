"""S10: what the generator's voices cost, and what is given up when it is too
much.

Every feature of the voice had a cost check of its own and passed it; nothing
had measured them together. Sixteen held notes over two layers with seven
copies, FM, sync, a sub, drive and fold at four times, the crusher and the
filter came to 1.7 seconds of work a second - a glitch on any machine - and
releases in flight could double the voices. So the core costs each voice by
a model and, over VOICE_BUDGET, gives things up in a stated order. Against the
ways that fails:

- the governed worst case still over real time: measured, with every
  feature on both layers and a full set of releases in flight, it has to run
  in under half of real time;
- a model that has the relative costs wrong, so the governor spends the
  budget on the wrong thing: each feature's measured cost over its modelled
  cost, held near the median of all of them - which is the machine's speed,
  and divides out;
- the order broken: the four times given up only before unison, unison only
  before a voice, releases before held notes, undrawn notes before drawn -
  each stage seen to happen somewhere in the sweep, so none of it is vacuous;
- caps that creep back up as releases die away, re-phasing a held chord for
  no reason anyone could hear; and caps that never come back when the chord
  or the settings change;
- a voice let go with a step: at one and two hertz the signal barely moves
  from one sample to the next, so a cut that steps is a hundred times the
  largest slope and a faded one is not;
- the readout silent while the voice is held back, or talking when nothing
  is;
- a budget so tight it bites ordinary playing: no preset gives anything up
  under a full chord of eight on each layer.

All but the readout's are core/tests/pieces/budget.py's since stage 5, step
3, batch 6; this suite keeps the readout, on the default page.
"""
# On ?brain=js until stage 5, step 3, batch 6 (14 Nov): this suite built the
# page's own makeGeneratorCore in the browser and read its budget, its voices
# and its milliseconds. Those numbers are the core's now, in
# core/tests/pieces/budget.py on core/tests/tools/budget_cpp.cpp - the
# governor's order, its caps, the fade, the 4 kHz drive, the old library and
# the bank under a chord, and the model against the core's own native costs -
# after the page's governor and the core's were run side by side on every one
# of those cases and all 277 setups and thinned the same voices, exactly. What
# is left here is the face: the readout's words for a budget, and a dear chord
# played on the default page through the controls and keys the instrument
# hears, with the readout reading the instrument's budget.
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

# One stub port, so a key can be pressed as a keyboard presses it; installed
# before the page's script runs, as envtest.py and miditest.py do.
STUB = """
  window.__midi = { port: null };
  navigator.requestMIDIAccess = function () {
    const port = { id: "stub", name: "Stub Keyboard", onmidimessage: null };
    window.__midi.port = port;
    return Promise.resolve({ inputs: new Map([["stub", port]]), outputs: new Map(), onstatechange: null });
  };
  window.__send = function (bytes) { window.__midi.port.onmidimessage({ data: Uint8Array.from(bytes) }); };
"""

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    p.add_init_script(STUB)
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    print("\n--- the readout ---")
    # budgetSaid is the face's: the words for a budget object, whichever
    # brain made it. Moved from ?brain=js as it was.
    said = p.evaluate("""() => [
      budgetSaid({ asked: [7, 5], unison: [3, 5], askedFactor: 4, factor: 2, silenced: 2 }, true),
      budgetSaid({ asked: [7, 1], unison: [4, 1], askedFactor: 2, factor: 2, silenced: 1 }, false),
      budgetSaid({ asked: [7, 7], unison: [7, 7], askedFactor: 4, factor: 4, silenced: 0 }, true),
      budgetSaid(null, false)]""")
    print("    %s" % said)
    check("it names each thing given up, per layer when there are two",
          said[0] == "voice budget: unison A 3 of 7 · shaping at 2× · 2 held notes let go"
          and said[1] == "voice budget: unison 4 of 7 · 1 held note let go", str(said[:2]))
    check("and says nothing when nothing is", said[2] == "" and said[3] == "", str(said[2:]))
    # Its null: a budget that gave up only its factor is not said as nothing.
    check("null: a budget that gave up only the four times is not said as nothing",
          p.evaluate("() => budgetSaid({ asked: [7, 7], unison: [7, 7], askedFactor: 4, factor: 2, silenced: 0 }, true)") != "")

    # A dear chord and a cheap one, played on the default page. On ?brain=js
    # this was genSet and midiNoteOn on the page's own generator; genSet only
    # writes the face's mirror on the default, and the instrument would have
    # played the plain base. Here the controls moved with their events, Poly
    # pressed, and the keys sent from a port: what the instrument hears. The
    # readout reads genBudget(), which on the default is the instrument's
    # budget as its readings carry it (makeBrainSource's `budget`).
    page = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      await midiConnect();
      el.midiPoly.click();
      setControl('shape', 'ramp'); setControl('oscUnison', 7); setControl('oscFm', 50); setControl('oscSync', 150);
      setControl('shpDrive', 50); setControl('shpOS', 4);
      await wait(200);
      for (let k = 0; k < 8; k++) window.__send([0x90, 48 + k * 3, 100]);
      await wait(700);
      const kind = state.source.kind;
      const theirs = state.source.budget ? JSON.parse(JSON.stringify(state.source.budget)) : null;
      const read = genBudget() === state.source.budget;
      const dear = el.readoutDetail.textContent;
      /* The null: the instrument's reading replaced by one that gave up
         nothing, with the chord still held - the readout follows it, so it
         is the instrument's budget it says, not one of the page's own. */
      const real = Object.getOwnPropertyDescriptor(state.source, 'budget');
      Object.defineProperty(state.source, 'budget', { configurable: true,
        get: () => ({ units: 100, asked: [7, 1], unison: [7, 1], askedFactor: 4, factor: 4, silenced: 0 }) });
      await wait(700);
      const forged = el.readoutDetail.textContent;
      Object.defineProperty(state.source, 'budget', real);
      for (let k = 0; k < 8; k++) window.__send([0x80, 48 + k * 3, 0]);
      setControl('oscUnison', 1); setControl('oscFm', 0); setControl('oscSync', 100); setControl('shpDrive', 0); setControl('shpOS', 2);
      await wait(200);
      for (const n of [60, 64, 67]) window.__send([0x90, n, 100]);
      await wait(700);
      const cheap = el.readoutDetail.textContent;
      const cheapBudget = state.source.budget ? JSON.parse(JSON.stringify(state.source.budget)) : null;
      for (const n of [60, 64, 67]) window.__send([0x80, n, 0]);
      return { kind, theirs, read, dear, forged, cheap, cheapBudget };
    }""")
    print("    %s" % page)
    check("playing a dear chord, the instrument's budget gives something up and the readout says what",
          page["kind"] == "host" and page["read"] and page["theirs"] is not None
          and page["theirs"]["unison"][0] < page["theirs"]["asked"][0]
          and "voice budget: unison" in page["dear"] and "shaping at 2×" in page["dear"], page["dear"])
    check("null: with the instrument's reading made one that gave up nothing, the readout says nothing of it",
          "voice budget" not in page["forged"], page["forged"])
    check("and a cheap one says nothing about it, the instrument giving nothing up",
          "voice budget" not in page["cheap"] and page["cheapBudget"] is not None
          and page["cheapBudget"]["unison"][0] == page["cheapBudget"]["asked"][0], page["cheap"])

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the readout says what the instrument's budget gave up")
