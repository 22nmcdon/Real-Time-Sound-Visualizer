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
- a finger's tap starts it, on the site's compiled instrument and on the page's
  own brain, and samples reach the screen through the heard path;
- a mouse click starts it.
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

    print("\n--- a finger, on the page's own brain ---")
    c, p, bad = open_page(b, True, "?brain=js&core=js")
    before = p.evaluate(STATE)
    check("before any press the page's own brain is not heard either", before["audible"] is False, str(before))
    p.touchscreen.tap(195, 300)
    p.wait_for_timeout(1500)
    after = p.evaluate(STATE)
    print("    after a tap:", after)
    check("one tap starts the page's own brain too", after["audible"] is True and not after["fault"], str(after))
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

    b.close()

server.shutdown()
print("\nSOUND START " + ("PASS" if not fails else "FAIL: " + ", ".join(fails)))
sys.exit(1 if fails else 0)
