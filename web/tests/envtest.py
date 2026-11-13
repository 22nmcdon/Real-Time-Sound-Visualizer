"""The gate and the envelope: what a key does to the generator now it sounds.

`tone.amp` was a constant, so there was nothing to gate and a note could only
set a pitch. Releasing everything left the last note standing, because closing
a gate with no envelope behind it would have been a picture that vanished when
you lifted your hands.

Four things are checked here.

IT IS NOT THERE UNTIL IT IS ASKED FOR. A core nobody has gated is a multiply
by one, and that is not a detail - a test's own core, a thumbnail's, and every
check that predates a keyboard depend on a steady waveform. `setGated(false)`
has to be exactly the old arithmetic and not nearly it. The page asks for it
from its first frame: since 10 Nov the site waits for a note as the plugin
does, keyboard or none, where until then it drew a steady drone until a
keyboard was there to play.

THE SHAPE, RENDERED. Not the value of a variable read back, which would only
say the code wrote what it wrote: the real worklet in an `OfflineAudioContext`,
with the envelope measured off the samples that came out of it.

NO STEP AT ANY EDGE. A gate edge. (And until G2 took the drawings, the
harmonograph's restart, which B1 turned up and flagged for this stage: the
pendulums ran down and the loop let them go again, which used to put the
envelope back to one in a single sample.)

LEGATO. A second note over a held one changes the pitch and leaves the
envelope alone, which is what makes a run of notes a phrase. After a release
has finished, the same second note has to start it again.
"""
# Stage 5, step 3, batch 4 (13 Nov): until then this suite opened the page on
# ?brain=js and read the page's own brain - a makeGeneratorCore built in the
# page and stepped by hand, and the generator's worklet rendered offline from
# generatorModuleSource(), the page's JavaScript engine both ways. Those
# renders - IT IS NOT THERE UNTIL IT IS ASKED FOR, THE SHAPE, NO STEP and
# LEGATO, and the glide's own time - are core/tests/pieces/env.py now, on the
# core's own generator, each with its null. What is left here is the site:
# the default page, a key on a real keyboard reaching the instrument, and the
# Envelope (env.note) the face reads off the instrument's own reading.
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

# One stub port, so a key can actually be pressed. Installed before the page's
# own script runs, the same as `miditest.py` does it, because `midi.supported`
# is read at load.
STUB = """
  window.__midi = { port: null };
  navigator.requestMIDIAccess = function () {
    const port = { id: "stub", name: "Stub Keyboard", onmidimessage: null };
    window.__midi.port = port;
    const inputs = new Map([["stub", port]]);
    return Promise.resolve({ inputs, outputs: new Map(), onstatechange: null });
  };
  window.__send = function (bytes) {
    window.__midi.port.onmidimessage({ data: Uint8Array.from(bytes) });
  };
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

    print("\n--- it is not there until it is asked for ---")
    # The page as it opens: no keyboard, and the instrument gated all the
    # same - it waits for a note. On ?brain=js until batch 4 this read the
    # page's own tone source ("tone"); on the site the gate is the
    # instrument's own reading, which the face takes with its envelope.
    opens = p.evaluate("() => ({ kind: state.source.kind, gated: state.source.gated, present: keyboardPresent() })")
    check("and the page opens with the instrument gated before any keyboard is there",
          opens == {"kind": "host", "gated": True, "present": False}, str(opens))
    check("and the reading fails against the page as it opened until 10 Nov, ungated",
          not dict(opens, gated=False) == {"kind": "host", "gated": True, "present": False})

    print("\n--- the envelope as something to point at ---")
    source = p.evaluate("""() => {
      const listed = Array.from(MOD_SOURCES.keys());
      const note = MOD_SOURCES.get('env.note');
      return { listed, hasNote: !!note, ungated: note ? note.value() : null,
               label: note ? note.label : null };
    }""")
    # Beside the level, which was a source too until F4b and is the output
    # meter now: the null is that it is no longer listed.
    check("it is registered, and the level is not, since F4b made it the output meter",
          source["hasNote"] and "env.live" not in source["listed"], str(source["listed"]))
    # On the default it is the instrument's envelope, read back (playingKind
    # is "tone" for the instrument's generator): nought with no note held.
    check("and reads nothing while no note is held",
          source["ungated"] == 0, str(source["ungated"]))

    print("\n--- and a key on a real keyboard, end to end ---")
    # None of the above presses a key. The envelope could be perfect and the
    # note stack could reach none of it, which is the join this whole stage
    # exists to make.
    played = p.evaluate("""async () => {
      await midiConnect();
      /* Through the controls, which the instrument hears; on ?brain=js until
         batch 4 these were state.source.set on the page's own generator,
         which on the site would set the face's mirror and nothing heard. */
      setControl('shape', 'sine');
      setControl('envAttack', 10); setControl('envDecay', 20);
      setControl('envSustain', 80); setControl('envRelease', 40);
      const read = () => MOD_SOURCES.get('env.note').value();
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));

      await wait(80);
      const idle = { gated: state.source.gated, env: read() };
      window.__send([0x90, 69, 100]);              // A4, hard
      await wait(160);
      const held = { gated: state.source.gated, env: read() };
      window.__send([0x80, 69, 0]);                // and up
      await wait(200);
      const gone = { gated: state.source.gated, env: read() };
      // The null for the velocity: the same key at full, 0.8 and not 0.63.
      window.__send([0x90, 69, 127]);
      await wait(160);
      const hard = { gated: state.source.gated, env: read() };
      window.__send([0x80, 69, 0]);
      await wait(200);

      /* Until batch 4 a key held while the gate was HANDED OVER from an input
         was checked here: toMic(), a key, toTone() - a new page generator,
         not yet gated, under a key already down. Only the page's brain hands
         a gate over like that; the instrument has one generator, gated from
         the first frame, whatever the screen draws. So it went. */

      // The keyboard going leaves the generator waiting for a note, not freed.
      const access = window.__access = midi.access;
      midi.access = null;
      midiPanic();
      await wait(600);
      const handedBack = { gated: state.source.gated, env: read() };
      const line = el.readoutDetail.textContent;
      return { idle, held, gone, hard, handedBack, line };
    }""")
    print("    idle %s, held %s, released %s, keyboard gone %s"
          % (played["idle"], played["held"], played["gone"], played["handedBack"]))
    # Until batch 4: "connecting a keyboard that drives the generator gates
    # it", on the page's own generator, which until 10 Nov went ungated
    # without one. The instrument is gated from its first frame whatever is
    # connected, so what is left to hold is that a connected keyboard finds it
    # gated and at nought before a key (the key's reading below is the null).
    check("with a keyboard connected the instrument is gated, at nought before a key",
          played["idle"]["gated"] is True and played["idle"]["env"] == 0,
          str(played["idle"]))
    # Tightened in batch 4 from "between 0.5 and 0.85", which a key at full
    # velocity (0.8) also passed.
    at_velocity = lambda env, vel: abs(env - 0.8 * vel / 127) < 0.04
    check("a key opens the envelope, at the velocity it was played",
          at_velocity(played["held"]["env"], 100),
          "%.4f, against a 0.8 sustain at velocity %.2f"
          % (played["held"]["env"], 100 / 127))
    check("null: the same key at full velocity is not read as the one at 100",
          not at_velocity(played["hard"]["env"], 100) and at_velocity(played["hard"]["env"], 127), str(played["hard"]))
    check("and letting go closes it",
          played["gone"]["env"] == 0, str(played["gone"]))
    check("and the keyboard going leaves the generator gated and silent, waiting for a note",
          played["handedBack"]["gated"] is True and played["handedBack"]["env"] == 0,
          str(played["handedBack"]))

    # And the picture is really silent, not merely gated: until 10 Nov the
    # keyboard going freed the generator and the trace came back here.
    PEAK = """() => {
      const w = state.source.getLatestWindow(4096)[0];
      let peak = 0;
      for (let i = 0; i < w.length; i++) peak = Math.max(peak, Math.abs(w[i]));
      return peak;
    }"""
    quiet = p.evaluate(PEAK)
    p.evaluate("() => midiNoteOn(69, 100)"); p.wait_for_timeout(300)
    sounding = p.evaluate(PEAK)
    p.evaluate("() => midiNoteOff(69)"); p.wait_for_timeout(300)
    # Under a thousandth rather than nought: the release's last samples can
    # still be in the window (0.001 once in three runs at 300 ms).
    check("and the trace is silent with it, and a note brings it back",
          quiet < 0.001 and sounding > 0.3, "peak %.4f, then %.3f under a note" % (quiet, sounding))
    check("and the silence reading fails on the note's trace", not sounding < 0.001)

    # The one state in this page where a blank screen is correct, and it has
    # to say so. A generator gated with no key down is silent by design; a
    # scope that just went dark would send somebody to the amplitude slider.
    # Polled rather than slept on. The readout line is rewritten at
    # READOUT_MS - a quarter of a second, not every frame - so a fixed wait is
    # a race, and this check failed about one run in three before it waited
    # for the thing it was asserting about instead of for a number of
    # milliseconds.
    said = p.evaluate("""async () => {
      const until = async (wanted, ms) => {
        const stop = performance.now() + ms;
        while (performance.now() < stop) {
          if (wanted()) return true;
          await new Promise((r) => setTimeout(r, 30));
        }
        return false;
      };
      const says = () => el.readoutDetail.textContent.indexOf("no note held") >= 0;

      // With the keyboard away (it was left so above), as with nothing
      // plugged in on the site: gated, and the line says so until a note.
      const appeared = await until(says, 1500);
      const gated = state.source.gated;
      const line = el.readoutDetail.textContent;

      midiNoteOn(69, 100);
      const cleared = await until(() => !says(), 1500);
      const after = el.readoutDetail.textContent;
      midiNoteOff(69);
      midi.access = window.__access;
      return { gated, line, appeared, cleared, after };
    }""")
    check("a gate held open with nothing played says why the screen is empty",
          said["gated"] and said["appeared"], said["line"][:80])
    check("and stops saying it once a note is held",
          said["cleared"], said["after"][:80])

    # That the drawn modes were not gated at all, so a keyboard could not
    # blank a harmonograph nobody was playing, was held here until G2.

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the gate opens and closes without a step in it")
