"""What reaches the speakers from the screen's side, shown only with a live input (17 Nov, the owner's).

Scope & measure's *Speakers get: Shaped* and Lag X-Y's *Heard* measured
nought on the generator (web/docs/what-reaches-the-sound.md: in the
instrument the speakers get its own sound, whatever the trace's filter, turn
or lag does to the picture). So they are hidden unless a live input is
playing, and kept: their values and ids stay, a setup still carries them.

What would go wrong, and what is checked for it, each with its null:

- the two rows still offered on the generator: on the tone, with Lag X-Y on
  (so the Heard row would otherwise show), both are hidden. The null is
  Lag X-Y's own row and its delay, which stay offered there;
- hidden by taking them away: their ids resolve, their values are where they
  were set, and a setup names them;
- hidden for good: with the instrument drawing its input, both show, and
  going back to the tone hides them again.
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

READ = """() => ({ kind: playingKind(), speakers: el.speakersRow.hidden, heard: el.lagMixRow.hidden,
               lag: el.lagCheck.hidden, lagRow: el.lagRow.hidden,
               // Each on its own subtab since the UI review (20 Nov): the filter's on Vertical, the lag's on Time.
               shown: [[el.speakersRow, 'vertical'], [el.lagMixRow, 'time']].map(([r, v]) => { setMeasureView(v); return r.getClientRects().length > 0; }) })"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required",
                                                         "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
    ctx = b.new_context(permissions=["microphone"], viewport={"width": 1400, "height": 900})
    p = ctx.new_page()
    bad = []
    p.on("pageerror", lambda e: bad.append(str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(2500)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate("() => { setMeasureOpen(true); el.lagOn.checked = true; el.lagOn.dispatchEvent(new Event('change')); }")
    p.wait_for_timeout(200)
    tone = p.evaluate(READ)
    print("    on the tone: %s" % tone)
    check("on the generator, with Lag X-Y on, Speakers get and the lag's Heard are hidden",
          tone["kind"] == "tone" and tone["speakers"] and tone["heard"] and tone["shown"] == [False, False], str(tone))
    check("null: Lag X-Y and its delay are still offered there", not tone["lag"] and not tone["lagRow"], str(tone))
    kept = p.evaluate("""() => { el.lagMix.value = '35'; el.lagMix.dispatchEvent(new Event('input'));
      el.hearWet.click(); const s = snapshot();
      return { ids: !!document.getElementById('hearWet') && !!document.getElementById('lagMix'), mix: el.lagMix.value,
               hear: s.fHear, lagMix: s.lagMix, wet: el.hearWet.getAttribute('aria-checked') }; }""")
    check("hidden, not taken away: the ids resolve, the values stay, and the setup carries them",
          kept["ids"] and kept["mix"] == "35" and kept["hear"] == "post" and kept["lagMix"] == 35, str(kept))
    p.evaluate("() => { el.hearDry.click(); }")
    if p.evaluate("() => !!(state.source && state.source.kind === 'host')"):
        p.evaluate("() => el.srcMic.click()"); p.wait_for_timeout(1500)
        live = p.evaluate(READ)
        print("    drawing the input: %s" % live)
        check("drawing a live input, both are shown", live["kind"] == "mic" and not live["speakers"] and not live["heard"]
              and live["shown"] == [True, True], str(live))
        p.evaluate("() => el.srcTone.click()"); p.wait_for_timeout(800)
        back = p.evaluate(READ)
        check("and back on the tone, hidden again", back["kind"] == "tone" and back["speakers"] and back["heard"], str(back))
    else:
        check("the site's instrument is there to draw an input (the case under test)", False,
              p.evaluate("() => state.source && state.source.kind"))
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\nall passed" if not fails else "\n%d FAILED:\n  %s" % (len(fails), "\n  ".join(fails)))
sys.exit(1 if fails else 0)
