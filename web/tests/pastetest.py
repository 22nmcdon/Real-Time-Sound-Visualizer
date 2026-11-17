"""A setup code pasted into the browser's footer that is not one this page
can load (the outside review, 17 Nov).

What would go wrong, and what is checked for it, each through the field and
the Paste button as a person pastes:

- a code that decodes to something other than a setup: "NQ" is the number 5,
  which threw an uncaught TypeError out of the core's codec with nothing on
  screen; "W10" is an empty array, which said Loaded and put every control
  back to its default. Neither may change the sound, and each must say in the
  footer's line that it could not be read;
- a code from a newer page (the testing site's, a version ahead): it loaded
  on the stable page with no word, its new fields dropped and the ones whose
  meaning had changed read the old way. It is refused, and the line says
  where it came from;
- the null for all three: a good code, made here from a changed sound, loads
  and says Loaded, so a check that "nothing changed" is not passing because
  Paste never does anything.

The sound is read as the setup code of what is playing (encodeSetup of the
snapshot), before and after, so any control moved is seen.
"""
import base64, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + str(detail)) if detail else ""))
    if not ok: fails.append(name)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1000)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    ev = p.evaluate
    version = ev("() => SETUP_VERSION")
    # A sound that is not the defaults, so a code that resets everything shows.
    ev("""() => { el.shape.value = 'square'; el.shape.dispatchEvent(new Event('change', { bubbles: true }));
                  el.freq.value = '330'; el.freq.dispatchEvent(new Event('input', { bubbles: true })); }""")
    p.wait_for_timeout(200)
    ev("() => openPresets()"); p.wait_for_timeout(300)
    sound = lambda: ev("() => encodeSetup(snapshot())")
    note = lambda: ev("() => [el.presetNote.textContent, el.presetNote.className]")

    def paste(code):
        bad.clear()
        p.locator("#presetCode").fill(code)
        p.locator("#presetPaste").click()
        p.wait_for_timeout(250)
        return note()

    newer = base64.b64encode(('{"v":%d,"freq":440,"shape":"sine"}' % (version + 1)).encode()).decode()
    cases = [("NQ", "the number 5"), ("W10", "an empty array"), ("dHJ1ZQ==", "true"), ("not a code at all", "not base64")]
    print("\n--- codes that are not setups ---")
    for code, what in cases:
        before = sound()
        said, how = paste(code)
        check("%s (%s): no error thrown" % (code, what), not bad, "; ".join(bad))
        check("%s: the sound is untouched" % code, sound() == before)
        check("%s: the line says it could not be read, as a warning" % code,
              "warn" in how and "could not be read" in said.lower() and "Loaded" not in said, (said, how))

    print("\n--- a code from a newer page ---")
    before = sound()
    said, how = paste(newer)
    check("a version-%d code is not loaded on a version-%d page" % (version + 1, version), sound() == before and not bad, "; ".join(bad))
    check("and the line says it is from a newer page", "warn" in how and "newer" in said.lower(), (said, how))

    print("\n--- the null: a good code loads ---")
    good = sound()
    ev("""() => { el.freq.value = '220'; el.freq.dispatchEvent(new Event('input', { bubbles: true })); }""")
    p.wait_for_timeout(150)
    moved = sound()
    said, how = paste(good)
    check("null: a code made here loads and says so", sound() == good and moved != good and said == "Loaded.", (said, how))
    # And one stamped with this page's own version is not taken for a newer one.
    same = base64.b64encode(('{"v":%d,"freq":440}' % version).encode()).decode()
    said, how = paste(same)
    check("null: a code of this page's version loads", said == "Loaded." and ev("() => Number(el.freq.value)") == 440, (said, how))
    check("no page errors", not bad, "; ".join(bad))
    b.close()

print("\nall passed" if not fails else "\n%d FAILED:\n  %s" % (len(fails), "\n  ".join(fails)))
sys.exit(1 if fails else 0)
