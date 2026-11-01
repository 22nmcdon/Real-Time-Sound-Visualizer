"""Every source button, from every state: Tone, and Mic refused.

The bug this exists for: clicking Stems showed the rack rows before any rack
existed, the picker was cancelled, and Tone returned on its first line because
a tone was already loaded - so nothing put the panel back and the switch was a
one-way door. Stems and File, and their pickers, went in P5; Tone over a tone
still has to put the panel back, and a refused microphone must not strand it.
"""
from playwright.sync_api import sync_playwright
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)                    # web/, which holds scope.html
SHOTS = os.path.join(HERE, "shots")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
os.makedirs(SHOTS, exist_ok=True)

# Reported in the format the other suites use and failing the run, which this
# did not do: it printed " FAIL " and exited 0 whatever happened, so neither
# run.py nor a count of PASS lines saw anything, and from the day the
# instrument became the site's default (5m) to 5v it failed on every run
# unseen. What failed was real twice over - a refused microphone stranded
# the instrument on an input it never got, and a rack let go left its legend
# behind - and a probe the rest of the time: it asked state.source.kind,
# which is "host" whatever the instrument draws, where playingKind() asks
# what is playing on either brain.
ok = True

def check(name, cond, detail=""):
    global ok
    print(("  PASS  " if cond else "  FAIL  ") + name + (("   " + str(detail)) if detail else ""))
    if not cond: ok = False

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width":1400,"height":900})
    bad=[]
    p.on("pageerror", lambda e: bad.append("pageerror: "+str(e)))
    p.on("console", lambda m: bad.append("console: "+m.text) if m.type=="error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate("() => { setView('bench'); setBenchTab('play'); }"); p.wait_for_timeout(150)

    tone_visible = lambda: p.locator("#genMode").is_visible()
    mark = lambda: p.locator("#sourceMark").inner_text()

    # Tone over a tone: it keeps the tone, but puts the panel back, which is
    # what the one-way door above lacked.
    p.locator("#srcTone").click(); p.wait_for_timeout(300)
    check("Tone over a tone keeps the tone and shows its editor",
          p.evaluate("playingKind()") == "tone" and tone_visible() and mark() == "TEST TONE", mark())

    print("-- Mic, denied, must not strand the panel --")
    # No microphone in this container, so the press is refused: the panel
    # goes back to the tone's rows and the credit says the tone still works.
    # (Until P5 it was also refused over a rack, where the credit must not
    # promise a test tone that is not playing; the rack went in P5.)
    p.locator("#srcMic").click(); p.wait_for_timeout(900)
    check("the tone rows came back, and the tone is what plays",
          tone_visible() and p.evaluate("playingKind()") == "tone")
    credit = p.locator("#credit").inner_text().lower()
    check("the credit explains, and says the tone still works", "microphone" in credit and "test tone" in credit,
          credit)
    check("and the head says the tone again", mark() == "TEST TONE", mark())

    print("-- the tone still works after all of that --")
    check("triggers", p.evaluate("capture().triggered"))
    check("generator responds", p.evaluate("""() => {
        el.freq.value = '330'; el.freq.dispatchEvent(new Event('input'));
        return state.source.settings.freq; }""") == 330)
    print()
    print("problems:", bad if bad else "none")
    check("no errors", not bad)
    b.close()
print()
print("SOURCE SWITCHING", "PASS" if ok else "FAIL")
raise SystemExit(0 if ok else 1)
