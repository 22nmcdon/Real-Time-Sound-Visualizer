"""The picture as a score (K3), and its notes going out as MIDI (K4).

Against the way each would fail:

- a score that plays the wrong row, or upside down: a single lit row is one
  repeated note, the one its height names; a diagonal is a rising scale, and
  in D dorian every note of it is in D dorian;
- a chord that is not the brightest, or a floor that lets smudges play;
- an empty grid that plays anything, or sends anything;
- a playhead not at the tempo: 120 BPM in semiquavers is a step every
  125 ms, nine steps in a second counted from nought, and half the tempo is
  half the steps;
- a voice that is drawn: the score's notes are in the heard pair and the
  picture pair is untouched, sample for sample. P4 drew them for a while, and
  the score then read its own diagonal and filled the screen; they are the
  one note heard and not drawn until P7;
- MIDI out that sends on the wrong channel, leaves a note hanging, or keeps
  sending when the scope stops or the page is hidden;
- a rate limit that is not one: a hundred note-ons at once are forty sent.
"""
# Stage 5, step 3, batch 2 (13 Nov). Sixteen of this suite's twenty checks
# called the page's own scoreColumn, scorePitches, keyMask and scoreTick on
# grids written by hand, built its makeGeneratorCore for the struck voice,
# and fed its midiOutNote a stubbed port: reading a column, the playhead at
# the tempo, the voice heard and not drawn, and MIDI out's channel, note-offs
# and rate limit. They are core/tests/pieces/score.py's now, asserted on the
# core's score, MidiOut and generator with a null each, and parity runs
# them; each old site below says what it was.
#
# What was left stayed on ?brain=js until stage 5, step 5b's second half (below): Stop's and a hidden page's all-notes-off,
# and the box ticked with real frames. Each reads the page's own score and
# MIDI out (score.steps, a wrapped state.source.strike, setRunning and the
# page's visibilitychange calling midiOutPanic). On the default the score and
# its MIDI out are the instrument's (Instrument::midiOut), while the page
# still steps its own score every frame beside it, so which of the two sends
# what reaches the port is step 5's to settle (STAGE5-INVENTORY.md, section
# 4: Stop's all-notes-off); moved now, these would pass on the page's score.
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

STUB = """
  window.__sent = [];
  window.__midi = { port: null };
  navigator.requestMIDIAccess = function () {
    const port = { id: "in", name: "Stub Keyboard", onmidimessage: null };
    const out = { id: "out1", name: "Stub Synth", send: (bytes) => window.__sent.push(Array.from(bytes)) };
    window.__midi.port = port;
    return Promise.resolve({ inputs: new Map([["in", port]]), outputs: new Map([["out1", out]]),
                             onstatechange: null });
  };
  window.__wait = (ms) => new Promise((r) => setTimeout(r, ms));
"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.add_init_script(STUB)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500)
    corpus.old_opening(p)  # the opening it was written against (P8h)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.locator("#trace").click(position={"x": 5, "y": 5}); p.wait_for_timeout(400)

    # Were, on ?brain=js: reading a column (a lit row is one note, a diagonal
    # a rising scale, D dorian's notes, the two brightest, the floor), the
    # playhead (nine steps at 120, five at 60, none from an empty grid) and the
    # voice (heard at 0.4 times velocity over two, not drawn, its null, 1/e at
    # 400 ms). core/tests/pieces/score.py's now.
    #
    # Until stage 5, step 5b's second half the rest stayed on ?brain=js, on
    # the page's own score and MIDI out: Stop's and a hidden page's
    # all-notes-off, written into the page's grid by hand and stepped by the
    # page's scoreTick, and the box ticked with real frames. That brain is off
    # the site now, so they are held on the instrument's score, which is the
    # one that plays: its notes reach the port on the chosen channel, a
    # hidden page still sends all-notes-off there, and its playhead moves. A
    # Stop that ends the instrument's MIDI-out note is not checked: the
    # instrument sends none (web/docs/after-stage-5.md).

    print("\n--- MIDI out, from the instrument's score ---")
    p.evaluate("() => midiConnect()"); p.wait_for_timeout(300)
    out = p.evaluate("""async () => {
      el.midiOut.value = 'out1'; el.midiOutCh.value = '2';
      el.midiOut.dispatchEvent(new Event('change'));
      document.getElementById('dispXY').click();
      midiNoteOn(57, 100); midiNoteOn(64, 100);
      el.scoreOn.checked = true; el.scoreOn.dispatchEvent(new Event('change'));
      await __wait(2500);
      const ons = __sent.filter((m) => (m[0] & 0xf0) === 0x90 && m[2] > 0);
      const channels = [...new Set(ons.map((m) => m[0] & 0x0f))];
      // Hidden: all notes off on that channel.
      __sent.length = 0;
      Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
      document.dispatchEvent(new Event('visibilitychange'));
      Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true });
      const hidden = __sent.map((m) => m.slice());
      el.scoreOn.checked = false; el.scoreOn.dispatchEvent(new Event('change'));
      return { ons: ons.length, channels, hidden };
    }""")
    print("    %s" % out)
    check("the instrument's score plays out of the page's port, on the chosen channel",
          out["ons"] >= 3 and out["channels"] == [2], str(out))
    check("null: the channel check is not the first channel's", not (out["channels"] == [0]))
    check("hiding the page sends all-notes-off on that channel", [0xB2, 123, 0] in out["hidden"], str(out["hidden"]))

    # With real frames: the box ticked, a second of playing, the instrument's
    # playhead as it serves it (Instrument::clockServed); the null is the box
    # unticked, where it stands still.
    def steps_over(on):
        return p.evaluate("""async (on) => {
          setTempo(120);
          el.scoreOn.checked = on; el.scoreOn.dispatchEvent(new Event('change'));
          await __wait(300);
          const a = state.source.clock.score.steps;
          await __wait(1200);
          const b = state.source.clock.score.steps;
          el.scoreOn.checked = false; el.scoreOn.dispatchEvent(new Event('change'));
          return b - a;
        }""", on)
    moved, still = steps_over(True), steps_over(False)
    check("ticked on the page, the instrument's playhead moves with the tempo: a semiquaver at 120 is eight steps a second",
          moved >= 8, "%s steps in 1.2 s" % moved)
    check("null: unticked, it stands still", still == 0, "%s steps" % still)

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
