"""The latch, gone (P8h), and what an old code does without it.

P8g built a latch on the Play tab - a chord let go sounding on until the next
replaced it - for the Wandering presets. The owner found it unplayable: holding
a root and changing the chord above it never let the old notes go, and any rule
for when a latched chord gives way has to guess from timing which notes belong
together, which an arpeggiated chord defeats. The sustain pedal is told rather
than guessing, and is already wired: a keyboard's controller 64, the screen
keys' Pedal, the space bar. So the latch went a day after it was built, with
a version-7 decode pass for a code saved while it was on.

What is checked:

- the switch is gone from the Play tab, and the screen keys' own Tap to hold,
  which is for a mouse and was never the latch, is still there;
- a version-6 code with the latch on comes up to 7 without it, read by the
  page's own codec and by the site's compiled one - the first check of the
  macros' removal read only the compiled one and passed with the page's pass
  taken out (P8d) - and the same code marked 7, which skips the pass, keeps
  it, which is the null;
- a key let go with the pedal down goes on sounding on the site's instrument,
  and without it is silent once its release has run out: what the latch was
  for, done the way the owner plays.
"""
import os, sys, base64, json
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def code_of(obj):
    return base64.b64encode(json.dumps(obj).encode()).decode().rstrip("=")

V6 = code_of({"v": 6, "midiLatch": True, "midiMode": "poly", "freq": 330})
V6_AS_7 = code_of({"v": 7, "midiLatch": True, "midiMode": "poly", "freq": 330})

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(1200)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.locator("#trace").click(position={"x": 5, "y": 5}); p.wait_for_timeout(500)

    print("\n--- gone, and an old code without it ---")
    gone = p.evaluate("""([v6, v6as7]) => ({
      box: !!document.getElementById('midiLatch'),
      tap: !!el.keysLatch && el.keysLatch.closest('label').textContent.trim(),
      inSnap: 'midiLatch' in snapshot(), inDefaults: 'midiLatch' in DEFAULTS,
      here: decodeSetupHere(v6), site: decodeSetup(v6), kind: setupCoreKind,
      hereNull: decodeSetupHere(v6as7), siteNull: decodeSetup(v6as7),
    })""", [V6, V6_AS_7])
    print("    %s" % gone)
    check("the latch's switch is gone and is in neither a snapshot nor the defaults; Tap to hold is still on the screen keys",
          not gone["box"] and gone["tap"] == "Tap to hold" and not gone["inSnap"] and not gone["inDefaults"], str(gone))
    for who in ("here", "site"):
        got = gone[who]
        check("a version-6 code with the latch on comes up to 7 without it, the rest as written (%s)"
              % ("the page's own codec" if who == "here" else "the site's, " + gone["kind"]),
              got is not None and got.get("v") == 7 and "midiLatch" not in got and got.get("freq") == 330
              and got.get("midiMode") == "poly", str(got))
        null = gone[who + "Null"]
        check("and the same code marked 7, which skips the pass, keeps it (%s)" % who,
              null is not None and null.get("midiLatch") is True, str(null))
    check("the site's codec is the compiled one, so the line above read the core's pass", gone["kind"] == "wasm", gone["kind"])

    print("\n--- what it was for, with the pedal ---")
    run = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const rms = () => { const [l] = state.source.getLatestWindow(4096); let e = 0;
                          for (const x of l) e += x * x; return Math.sqrt(e / l.length); };
      setScreenKeys(true);
      hostQuietly(() => restore({ midiMode: 'poly' })); hostSendSetup(); await wait(500);
      const on = (n) => midiBytes(new Uint8Array([0x90, n, 100]));
      const off = (n) => midiBytes(new Uint8Array([0x80, n, 0]));
      const pedal = (v) => midiBytes(new Uint8Array([0xB0, 64, v]));
      on(60); await wait(500); off(60); await wait(900); const bare = rms();
      pedal(127); on(60); await wait(500); off(60); await wait(900); const held = rms();
      pedal(0); await wait(900); const lifted = rms();
      return { bare, held, lifted };
    }""")
    check("a key let go under the pedal sounds on, and is silent once the pedal comes up, or without it",
          run["held"] > 0.05 and run["bare"] < 0.005 and run["lifted"] < 0.005, str(run))
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the latch is gone, an old code loses it, and the pedal holds a chord")
