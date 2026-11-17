"""The microphone menu, made from what the browser says is plugged in (the
outside review, 17 Nov).

What would go wrong: a device's name, which the operating system and the
device's maker choose, going into the menu as markup. listDevices built its
options as a string of HTML, so a name with a tag in it made an element and
one with a quote broke the option's value. The browser's list is stood in
for here by one with such a name, and the menu is read back: the text as the
name was, no element made from it, nothing run, and the value the device's
id to the character. The null is a plain name, which must come out the same
whichever way the menu is built, so the reading is of the menu at all.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + str(detail)) if detail else ""))
    if not ok: fails.append(name)

NASTY = 'Studio <img src=x onerror="window.__ran = 1"> Mic & "Line"'
NASTY_ID = 'id" data-x="1'

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(800)
    got = p.evaluate("""async ([nasty, nastyId]) => {
      const list = [{ kind: 'audioinput', deviceId: 'plain', label: 'USB Microphone' },
                    { kind: 'audioinput', deviceId: nastyId, label: nasty },
                    { kind: 'audiooutput', deviceId: 'out', label: 'Speakers' }];
      Object.defineProperty(navigator, 'mediaDevices', { configurable: true,
        value: { enumerateDevices: async () => list, getUserMedia: navigator.mediaDevices && navigator.mediaDevices.getUserMedia } });
      await listDevices();
      await new Promise((r) => setTimeout(r, 50));
      return { options: Array.from(el.device.options).map((o) => [o.value, o.text]),
               elements: el.device.querySelectorAll('*:not(option)').length, ran: !!window.__ran };
    }""", [NASTY, NASTY_ID])
    print("\n--- the microphone menu ---")
    check("null: a plain name is an option with its id", got["options"][:1] == [["plain", "USB Microphone"]], got["options"])
    check("only the inputs are offered", len(got["options"]) == 2, got["options"])
    check("a name with markup in it is its text, to the character", len(got["options"]) > 1 and got["options"][1][1] == NASTY, got["options"])
    check("and its id the value, quotes and all", len(got["options"]) > 1 and got["options"][1][0] == NASTY_ID, got["options"])
    check("no element made from a name, and nothing in it run", got["elements"] == 0 and not got["ran"], got)
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\nall passed" if not fails else "\n%d FAILED:\n  %s" % (len(fails), "\n  ".join(fails)))
sys.exit(1 if fails else 0)
