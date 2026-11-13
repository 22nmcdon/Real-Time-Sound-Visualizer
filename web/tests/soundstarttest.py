"""The first press starts the sound, on a phone as on a computer.

Every other suite launches the browser with `--autoplay-policy=no-user-gesture-
required`, which switches off the one rule this file is about: a page may start
sound only from a press the browser counts. So for as long as the suites have
existed, none of them could see that the site was never heard on a phone. The
owner found it with a keyboard plugged into an iPhone: the figure followed every
key, the readout named every note, and nothing came out.

Two faults, either enough on its own. The ask made as the page opened awaited
`resume()`, which a browser that wants a press holds unanswered rather than
refusing, so it waited for ever; and since every later ask joins the one in
flight, no press could start the sound. And the presses listened for were
`pointerdown` and `keydown`, while the rule browsers follow counts a
pointerdown only from a mouse: a finger counts at its pointerup or touchend.

So this file runs Chromium with the rule ON, which Chromium enforces as WebKit
does for this purpose, and holds both:
- before any press nothing is heard (the null that proves the rule is on here -
  with it off, every check below would pass whatever the page did);
- a finger's tap starts it, on the site's compiled instrument, and samples
  reach the screen through the heard path;
- a mouse click starts it;
- and what a press starts is silence until a note (10 Nov, the owner's call):
  the site is as the plugin is, nothing sounding or drawn
  until a key goes down, and the empty screen says how to play one until the
  first has. A press that is not a note is where the drone used to begin, so
  the silence is read after one, with the sound on - a press on the title,
  since opening the keys would itself have gated the old drone, and a check
  made after it could not fail; then the keys opened, a typed A and K are the
  notes the line says they are, and the line is gone and stays gone;
- and a key that is itself the first press sounds, held: the
  sound it starts arrives after the key, which nothing checked while the
  generator sounded with no note.

Until stage 5, step 3, batch 4 (13 Nov) each of these also ran on the page's
own brain: a finger on ?brain=js&core=js (its JavaScript engine under the
autoplay rule, a fallback step 5 replaces with a line), and the two loops
below once more on ?brain=js, reading that brain's gate. Those legs went with
the brain; the site's legs hold every claim.
"""
import os, sys, threading, functools
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.environ.get("SCOPE_DIR", os.path.dirname(HERE))
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

# Served over http rather than opened as a file, as the site is: a browser may
# treat a file:// page's sound more leniently than a published one's.
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=ART))
threading.Thread(target=server.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:%d/scope.html" % server.server_address[1]

STATE = """() => { const v = genVoice();
  return { audible: !!(v && v.audible && v.audible()), credit: el.credit.textContent,
           fault: el.genFault.textContent, kind: state.source.kind }; }"""

def open_page(b, touch, query=""):
    c = b.new_context(viewport={"width": 390, "height": 844} if touch else {"width": 1400, "height": 900},
                      has_touch=touch, is_mobile=touch)
    p = c.new_page()
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(BASE + query); p.wait_for_timeout(2500)
    # The help dialog opens on a first visit; shut from code, which is not a
    # press, so it cannot start the sound for us.
    p.evaluate("() => { const d = document.getElementById('helpDialog'); if (d && d.open) d.close(); }")
    p.wait_for_timeout(300)
    return c, p, bad

with sync_playwright() as pw:
    # Deliberately without --autoplay-policy=no-user-gesture-required.
    b = pw.chromium.launch(executable_path=CHROME)

    print("\n--- a finger, on the site's instrument ---")
    c, p, bad = open_page(b, True)
    before = p.evaluate(STATE)
    print("    before:", before)
    check("before any press nothing is heard, so the rule is on in this browser",
          before["audible"] is False and before["kind"] == "host", str(before))
    p.touchscreen.tap(195, 300)
    p.wait_for_timeout(1500)
    after = p.evaluate(STATE)
    print("    after a tap:", after)
    check("one tap of a finger starts the sound", after["audible"] is True and not after["fault"], str(after))
    check("and the credit stops asking for a press", "press anything" not in after["credit"], after["credit"])
    check("no page errors", not bad, "; ".join(bad[:3]))
    c.close()

    print("\n--- a mouse ---")
    c, p, bad = open_page(b, False)
    before = p.evaluate(STATE)
    check("before a click nothing is heard", before["audible"] is False, str(before))
    p.mouse.click(700, 120)
    p.wait_for_timeout(1500)
    after = p.evaluate(STATE)
    check("one click starts the sound", after["audible"] is True and not after["fault"], str(after))
    check("no page errors", not bad, "; ".join(bad[:3]))
    c.close()

    # Nothing until a note. The picture is read rather than the speakers: the
    # same gate silences both, and on the instrument the picture is the
    # instrument's own. A second of it, so a drone that started with the
    # press and was not there a moment ago is in the window.
    SILENT = """() => { const n = Math.round(state.source.sampleRate);
      const lanes = state.source.getLatestWindow(n); let peak = 0;
      for (const l of lanes) for (let i = 0; i < l.length; i++) peak = Math.max(peak, Math.abs(l[i]));
      const v = genVoice();
      return { peak, hint: !el.playHint.hidden, text: el.playHint.textContent, gated: !!state.source.gated,
               audible: !!(v && v.audible && v.audible()), held: midi.notes.map((h) => h.note), kind: state.source.kind }; }"""
    quiet = lambda r: r["peak"] < 1e-6 and r["hint"]
    for query, brain in (("", "host"),):
        print("\n--- nothing until a note, on the site's instrument ---")
        c, p, bad = open_page(b, False, query)
        first = p.evaluate(SILENT)
        print("    opened:", first)
        check("opened and unpressed, nothing is drawn and the empty screen says how to play a note, the ways that are true here",
              quiet(first) and first["kind"] == brain and first["gated"]
              and first["text"].startswith("Play a note: show the keys and type A") and "connect MIDI in Settings" in first["text"],
              str(first))
        # A press that plays nothing and opens nothing: the title. Until 10 Nov
        # this was the drone's first moment, with no keyboard there.
        p.locator(".sheet-title").click()
        p.wait_for_timeout(1500)
        pressed = p.evaluate(SILENT)
        print("    pressed:", pressed)
        check("pressed, the sound is on and still nothing sounds, with no keyboard there: no drone before a note",
              quiet(pressed) and pressed["audible"] and pressed["text"] == first["text"], str(pressed))
        # The keys opened, as a visitor would, and the line names them.
        p.locator("#keysOpen").click(); p.wait_for_timeout(300)
        opened = p.evaluate(SILENT)
        check("and with the keys opened the line names them and still nothing sounds",
              quiet(opened) and "press a key below" in opened["text"], str(opened))
        # The letters the line names: A is the keys' first C, K the C above.
        p.keyboard.down("a"); p.wait_for_timeout(700)
        played = p.evaluate(SILENT)
        p.keyboard.up("a"); p.keyboard.down("k"); p.wait_for_timeout(100)
        top = p.evaluate("() => midi.notes.map((h) => h.note)")
        p.keyboard.up("k"); p.wait_for_timeout(1500)
        let_go = p.evaluate("() => ({ hint: !el.playHint.hidden, held: midi.notes.length })")
        print("    A held:", played, "K:", top, "let go:", let_go)
        check("a typed A is C3 and sounds, and the line is gone with it",
              played["held"] == [48] and played["peak"] > 0.1 and not played["hint"], str(played))
        check("and K is the C above, so the line's A to K is an octave of keys", top == [60], str(top))
        check("and the line stays gone once the notes are let go", not let_go["hint"] and let_go["held"] == 0, str(let_go))
        # The nulls: each half of the quiet reading, against the note's own window.
        check("and the silence reading fails on the note's window, and the line's on its hidden line",
              not played["peak"] < 1e-6 and not quiet(dict(pressed, hint=played["hint"])))
        check("no page errors", not bad, "; ".join(bad[:3]))
        c.close()

    # The first press a key on the screen's keys, held. The keys opened from
    # code, which is no press, so the key is the one that starts the sound.
    for query, brain in (("", "host"),):
        print("\n--- a key as the first press, on the site's instrument ---")
        c, p, bad = open_page(b, False, query)
        p.evaluate("() => setScreenKeys(true)"); p.wait_for_timeout(300)
        unpressed = p.evaluate(SILENT)
        key = p.locator('#keysBed [data-note="57"]').bounding_box()
        p.mouse.move(key["x"] + key["width"] / 2, key["y"] + key["height"] * 0.8)
        p.mouse.down(); p.wait_for_timeout(1500)
        first = p.evaluate(SILENT)
        p.mouse.up(); p.wait_for_timeout(200)
        print("    A3 held as the first press:", first)
        sounds = lambda r: r["audible"] and r["held"] == [57] and r["peak"] > 0.1 and r["kind"] == brain
        check("a key as the first press starts the sound, and is heard while it is held", sounds(first), str(first))
        check("and the reading fails on the page before the press", not sounds(unpressed), str(unpressed))
        check("no page errors", not bad, "; ".join(bad[:3]))
        c.close()

    b.close()

server.shutdown()
print("\nSOUND START " + ("PASS" if not fails else "FAIL: " + ", ".join(fails)))
sys.exit(1 if fails else 0)
