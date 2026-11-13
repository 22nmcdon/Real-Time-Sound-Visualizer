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
# What is left stays on ?brain=js: Stop's and a hidden page's all-notes-off,
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
    p.goto(f"file://{ART}/scope.html?brain=js"); p.wait_for_timeout(700)
    corpus.old_opening(p)  # the opening it was written against (P8h)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    # Were, on ?brain=js: reading a column (a lit row is one note, a diagonal
    # a rising scale, D dorian's notes, the two brightest, the floor), the
    # playhead (nine steps at 120, five at 60, none from an empty grid) and the
    # voice (heard at 0.4 times velocity over two, not drawn, its null, 1/e at
    # 400 ms). core/tests/pieces/score.py's now.

    print("\n--- MIDI out ---")
    p.evaluate("() => midiConnect()"); p.wait_for_timeout(300)
    out = p.evaluate("""async () => {
      el.midiOut.value = 'out1'; el.midiOutCh.value = '2';
      el.midiOut.dispatchEvent(new Event('change'));
      const saved = phosphor.grid.slice(), N = PHOSPHOR_N;
      phosphor.grid.fill(0); for (let c = 0; c < N; c++) phosphor.grid[40 * N + c] = 1;
      setTempo(120); score.on = true; transportStart(220000); scoreTick(220000);
      const sounding = __sent.filter((m) => m[0] === 0x92).map((m) => m[1]).pop();
      // Stopping the scope ends what was sent.
      __sent.length = 0; setRunning(false);
      const stopped = __sent.map((m) => m.slice());
      setRunning(true); score.on = false; scoreStop();
      // Hidden: all notes off.
      midiOutNote(64, 1, performance.now());
      __sent.length = 0;
      Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
      document.dispatchEvent(new Event('visibilitychange'));
      Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true });
      const hidden = __sent.map((m) => m.slice());
      phosphor.grid.set(saved);
      transportStart(performance.now());
      return { sounding, stopped, hidden };
    }""")
    print("    stopped %s; hidden %s" % (out["stopped"], out["hidden"]))
    # Were, on ?brain=js: the score's notes on the chosen channel with the
    # last ended before the next begins, the same when the next note is
    # another, a hundred note-ons being forty sent and sixty dropped, and an
    # empty grid sending nothing. core/tests/pieces/score.py's now, on the
    # core's MidiOut.
    n = out["sounding"]
    check("stopping the scope ends the sounding note and sends all-notes-off on that channel",
          n is not None and [0x82, n, 0] in out["stopped"] and [0xB2, 123, 0] in out["stopped"], str(out["stopped"]))
    check("hiding the page does the same", [0x82, 64, 0] in out["hidden"] and [0xB2, 123, 0] in out["hidden"],
          str(out["hidden"]))

    # With real frames: the box ticked, a figure drawn, a second of playing.
    live = p.evaluate("""async () => {
      setTempo(120); state.persistence = -1;
      const src = state.source, strike = src.strike.bind(src); let struck = 0;
      src.strike = (notes) => { struck++; strike(notes); };
      el.scoreOn.checked = true; el.scoreOn.dispatchEvent(new Event('change'));
      await __wait(1200);
      const out = { steps: score.steps, struck, col: score.col };
      el.scoreOn.checked = false; el.scoreOn.dispatchEvent(new Event('change'));
      src.strike = strike;
      return out;
    }""")
    check("ticked on the page, the playhead moves with the frames and the drawn waveform plays",
          live["steps"] >= 8 and live["struck"] >= 4, str(live))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
