"""The latch (P8g): a chord let go goes on sounding until the next one replaces it.

The note stack's rules - what is latched, what a new chord lets go, the pedal
beside it, the panic - are the page's and the core's alike, and parity holds
the two together command for command. What is checked here is the latch as a
player meets it on the site, where the sound is the compiled instrument's:

- the switch on the Play tab sets it, and says so on the MIDI line;
- latched, a note let go is still heard after its release has run out, read
  off what the instrument hands back; unlatched, the same note is silent by
  then, which is the null;
- the next note struck with no key down replaces the chord, on the page's
  stack and in what is heard: the latched pair let go and a new note struck
  is as loud as that note alone, where the same note struck with a key still
  down joins the chord and is louder - by 1.12, measured, rather than the
  square root of two, since a chord is levelled on its way out;
- a setup carries it, a preset that does not name it turns it off and lets
  go of what it held, and the screen keys' own toggle is called something
  else, since two switches called Latch that do different things would be
  one too many.
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
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    # The picture stage out, as the suites that measure something else open it.
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(1200)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.locator("#trace").click(position={"x": 5, "y": 5}); p.wait_for_timeout(500)

    print("\n--- the switch, and what is heard after letting go ---")
    run = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const rms = () => { const [l] = state.source.getLatestWindow(4096); let e = 0;
                          for (const x of l) e += x * x; return Math.sqrt(e / l.length); };
      const notes = () => midi.notes.map((n) => n.note);
      setScreenKeys(true);
      restore({ midiMode: 'poly' }); hostSendSetup(); await wait(500);
      const on = (n) => midiBytes(new Uint8Array([0x90, n, 100]));
      const off = (n) => midiBytes(new Uint8Array([0x80, n, 0]));
      const out = {};
      // Unlatched first: the null for what follows.
      on(60); await wait(600); out.heldOff = rms(); off(60); await wait(900); out.afterOff = rms();
      // The switch as a hand moves it.
      showControl('midiLatch');
      el.midiLatch.click(); await wait(200);
      out.latch = midi.latch; out.line = el.midiMonitor ? el.midiMonitor.textContent : '';
      on(60); await wait(600); off(60); await wait(900);
      out.afterOn = rms(); out.stackAfter = notes(); out.lineAfter = el.midiMonitor ? el.midiMonitor.textContent : '';
      // A new note with no key down replaces it; one with a key down joins.
      on(67); await wait(900); out.replaced = rms(); out.stackReplaced = notes(); off(67); await wait(300);
      on(64); await wait(300); on(71); await wait(900); out.joined = rms(); out.stackJoined = notes();
      off(64); off(71); await wait(300);
      midiPanic(); await wait(900);
      on(67); await wait(900); out.alone = rms(); off(67); await wait(300);
      // A setup carries it; a preset that does not name it lets go.
      out.snapped = snapshot().midiLatch;
      out.code = decodeSetup(encodeSetup(snapshot())).midiLatch;
      restore({ midiMode: 'poly' }); hostSendSetup(); await wait(900);
      out.afterRestore = { latch: midi.latch, box: el.midiLatch.checked, stack: notes(), rms: rms() };
      return out;
    }""")
    print("    %s" % run)
    check("unlatched, a note let go is silent once its release has run out", run["heldOff"] > 0.05 and run["afterOff"] < 0.005,
          "%.3f held, %.4f after" % (run["heldOff"], run["afterOff"]))
    check("the switch on the Play tab latches, and the MIDI line says what it holds",
          run["latch"] is True and "latch" in run["line"] and "latch, holding 1" in run["lineAfter"],
          "%r / %r" % (run["line"], run["lineAfter"]))
    check("latched, the same note let go is still heard after its release, on the site's instrument",
          run["afterOn"] > 0.05 and run["stackAfter"] == [60], "%.3f, stack %s" % (run["afterOn"], run["stackAfter"]))
    check("the next note struck with no key down replaces it, on the stack and in the sound",
          run["stackReplaced"] == [67] and abs(run["replaced"] / run["alone"] - 1) < 0.05,
          "stack %s, %.3f against %.3f alone" % (run["stackReplaced"], run["replaced"], run["alone"]))
    check("and one struck with a key down joins the chord, louder than a note alone, which the check above fails on",
          run["stackJoined"] == [64, 71] and run["joined"] / run["alone"] > 1.08
          and not abs(run["joined"] / run["alone"] - 1) < 0.05,
          "stack %s, %.3f against %.3f" % (run["stackJoined"], run["joined"], run["alone"]))
    check("a setup carries it, and one that does not name it lets go of what it held",
          run["snapped"] is True and run["code"] is True
          and run["afterRestore"]["latch"] is False and run["afterRestore"]["box"] is False
          and run["afterRestore"]["stack"] == [] and run["afterRestore"]["rms"] < 0.005, str(run["afterRestore"]))

    names = p.evaluate("""() => ({
      play: el.midiLatch.closest('label').textContent.trim(),
      keys: el.keysLatch.closest('label').textContent.trim(),
    })""")
    check("the screen keys' toggle is called something else", names["play"].startswith("Latch")
          and "Latch" not in names["keys"], str(names))
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("a chord let go sounds on until the next one replaces it")
