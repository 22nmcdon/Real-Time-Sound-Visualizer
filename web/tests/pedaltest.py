"""The sustain pedal: a pedal that holds notes, and a source.

What would go wrong, and what is checked for it:

- a released note under the pedal being dropped anyway, or a note still held
  by a finger being dropped when the pedal lifts. The fixture strikes a note
  again while the pedal holds it and keeps that key down through the lift -
  the case a pedal that only remembers "released while down" gets wrong;
- the switch point off by one: 63 of 127 must not hold and 64 must;
- CC 64 learned as a controller beside the pedal, so it shows twice;
- the source jumping with the pedal, which on the amplitude is a click;
- the sound not following: the envelope has to stay open while the pedal
  holds a released note, and close once it lifts;
- the screen's pedal and the space bar, and the space bar still being run
  and stop once the keys are closed;
- a panic, or closing the keys, leaving notes hanging.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)
    send = lambda *bytes_: p.evaluate("(b) => midiBytes(Uint8Array.from(b))", list(bytes_))
    held = lambda: p.evaluate("() => midi.notes.map((n) => n.note)")

    print("\n--- it holds what you let go of ---")
    p.evaluate("() => setScreenKeys(true)")
    send(0xB0, 64, 127)
    send(0x90, 60, 100); send(0x90, 64, 100)
    send(0x80, 60, 0); send(0x80, 64, 0)
    under = {"notes": held(), "monitor": p.evaluate("midi.last")}
    send(0xB0, 64, 0)
    lifted = held()
    print("    under the pedal %s; lifted %s" % (under, lifted))
    check("keys let go under the pedal go on sounding",
          under["notes"] == [60, 64] and "holding 2" in under["monitor"], str(under))
    check("and go when the pedal lifts", lifted == [], str(lifted))

    # Struck again while the pedal holds it, and still down when it lifts.
    send(0xB0, 64, 127)
    send(0x90, 67, 100); send(0x80, 67, 0)      # held by the pedal
    send(0x90, 67, 100)                          # struck again, and kept down
    send(0x90, 72, 100); send(0x80, 72, 0)       # held by the pedal only
    send(0xB0, 64, 0)
    kept = held()
    send(0x80, 67, 0)
    check("a key struck again under the pedal and still down stays when the pedal lifts",
          kept == [67], str(kept))

    edge = p.evaluate("""() => {
      midiControl(64, 63); const off = midi.sustain;
      midiControl(64, 64); const on = midi.sustain;
      midiControl(64, 0);
      return { off, on };
    }""")
    check("the switch point is 64 of 127: 63 does not hold and 64 does",
          edge == {"off": False, "on": True}, str(edge))

    print("\n--- a source, not a controller ---")
    src = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      midiControl(64, 0); await wait(600);
      midiControl(64, 127);
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      const soon = MOD_SOURCES.get('midi.pedal').value();
      await wait(700);
      const later = MOD_SOURCES.get('midi.pedal').value();
      midiControl(64, 64); await wait(700);
      const half = MOD_SOURCES.get('midi.pedal').value();
      midiControl(64, 0);
      return { soon, later, half, family: MOD_SOURCES.get('midi.pedal').family,
               learned: midi.cc.has(64), chip: MOD_SOURCES.has('cc.64') };
    }""")
    print("    %s" % src)
    check("Sustain is a source with the keyboard's, and CC 64 is not learned beside it",
          src["family"] == "keyboard" and not src["learned"] and not src["chip"], str(src))
    check("it walks to the pedal rather than stepping, which on the amplitude would click",
          src["soon"] < 0.9 and src["later"] > 0.99, str(src))
    check("and reads a half-pedal as a half", abs(src["half"] - 64 / 127) < 0.01, str(src))

    print("\n--- the sound follows ---")
    sound = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      genSet('releaseMs', 60);
      midiControl(64, 127);
      midiNoteOn(57, 100); await wait(200); midiNoteOff(57);
      await wait(500);
      const holding = state.source.envelope;
      midiControl(64, 0);
      await wait(500);
      const gone = state.source.envelope;
      midiNoteOn(57, 100); await wait(200); midiNoteOff(57);
      await wait(500);
      const without = state.source.envelope;
      return { holding, gone, without, gated: state.source.gated };
    }""")
    print("    %s" % sound)
    check("the envelope stays open while the pedal holds a released note",
          sound["gated"] and sound["holding"] > 0.5, str(sound))
    check("and closes once it lifts, as it does with no pedal at all",
          sound["gone"] < 0.05 and sound["without"] < 0.05, str(sound))

    print("\n--- the screen's pedal ---")
    screen = p.evaluate("""() => {
      el.keysPedal.click();
      const pressed = { sustain: midi.sustain, aria: el.keysPedal.getAttribute('aria-pressed') };
      el.keysPedal.click();
      return { pressed, lifted: midi.sustain };
    }""")
    check("the Pedal button presses and lifts", screen["pressed"] == {"sustain": True, "aria": "true"}
          and screen["lifted"] is False, str(screen))
    running = p.evaluate("() => state.running")
    p.keyboard.down("Space"); p.wait_for_timeout(100)
    down = p.evaluate("() => ({ sustain: midi.sustain, running: state.running })")
    p.keyboard.up("Space"); p.wait_for_timeout(100)
    up = p.evaluate("() => ({ sustain: midi.sustain, running: state.running })")
    check("space held is the pedal while the keys are open, and does not stop the scope",
          down == {"sustain": True, "running": running} and up == {"sustain": False, "running": running},
          str((down, up)))
    p.evaluate("() => { el.keysPedal.click(); midiNoteOn(60, 100); midiNoteOff(60); setScreenKeys(false); }")
    closed = p.evaluate("() => ({ sustain: midi.sustain, notes: midi.notes.length })")
    check("closing the keys lifts their pedal and lets go of what it held",
          closed == {"sustain": False, "notes": 0}, str(closed))
    p.keyboard.press("Space"); p.wait_for_timeout(100)
    check("and space is run and stop again", p.evaluate("() => state.running") != running)
    p.keyboard.press("Space"); p.wait_for_timeout(100)

    panic = p.evaluate("""() => {
      setScreenKeys(true);
      midiControl(64, 127); midiNoteOn(62, 100); midiNoteOff(62);
      const before = midi.notes.length;
      midiPanic();
      const out = { before, after: midi.notes.length, sustained: midi.sustained.size };
      midiControl(64, 0);
      return out;
    }""")
    check("a panic lets go of what the pedal was holding",
          panic == {"before": 1, "after": 0, "sustained": 0}, str(panic))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the pedal holds, lifts, and moves what it is patched to")
