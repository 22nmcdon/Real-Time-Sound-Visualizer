"""Stage E2: what the picture says - five sources and a verdict.

Every source has to pass the plan's gate before it may be routed: a small change
in the picture makes a small change in the value. Each check here perturbs a
fixture a little and bounds how far the source moves, and each fixture is built
to be the place where a discontinuous form WOULD jump:

- coverage, on a faded figure whose cells all sit just under one half - where a
  count of cells over a threshold would flip every one of them at once;
- roundness, on a figure shrinking to nothing - where a ratio with no floor
  under it would read a perfect tiny circle until the frame it vanished;
- direction, across a line, where the travel reverses.

Then the verdict, on constructed sequences before any real loop: a frozen
picture, one that repeats, one that never does, one that fills the screen.
Each verdict is checked to be the one its fixture should give AND not the one
any other fixture gives, which is the null test for a classifier.

Then the survey that chose the sixth source, re-run: Direction has to add
information the other five do not hold, beside a copy of roundness that has to
add none. Edge contact, the candidate it was chosen over, was cut in P5.
"""
# Stage 5, step 3, batch 2 (13 Nov): the numbers - roundness, coverage,
# change, novelty, direction, the verdicts on constructed sequences and the
# slew - were read here from the page's own makeMoments, makePictureMeter,
# shapeOfPair and picture sources on ?brain=js. They are the core's now,
# asserted on its output alone with a null each: core/tests/pieces/shape.py,
# which parity runs. What is left is the face on the site's default (the
# picture's sources registered with the photocell, the readout), and the
# survey that chose the sixth source, which plays corpus setups with the loop
# closed for four seconds each and reads the page's own sources' entropies:
# that needs a render of the core with the loop closed and its sources read
# out (render_cpp, not built yet), so it stays on a ?brain=js page of its own.
import os, sys
from playwright.sync_api import sync_playwright
import corpus

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
SURVEY = os.path.join(HERE, "survey.js")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def open_page(pw, query):
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0{query}"); p.wait_for_timeout(700)
    return b, p, bad


# What these were, on ?brain=js, until stage 5's step 3 (13 Nov), and where
# each went - every one to core/tests/pieces/shape.py, against the core's
# Moments, PictureMeter, shapeOfPair and PictureSources, on the same fixtures
# (built by picture_cpp's `m` commands, line for line as HELPERS built them
# here in the page's JavaScript):
# - roundness: a circle round and a line not; a 2:1 ellipse the same turned;
#   a circle unevenly cut still a circle; the square's blind spot; a dark
#   screen nought; fading to nothing a slope.
# - coverage moving a little as every cell crosses a half; change nought,
#   one and small; novelty rising a step at a time.
# - direction one way and the other, a line none, smooth across the line,
#   and wherever the figure sits (state.channels[0].offset written here).
# - the verdicts on the frozen, repeating, never-returning and full
#   fixtures; nothing said before there is history; the bursts judged as the
#   even motion; the rate per sixtieth at sixty and a hundred and twenty.
# - roundness following a circle that becomes a line, and no faster than
#   the slew: here genSet('phase') on the page's generator and 2.5 s of real
#   frames read off picture.round; there the core's sources at made-up
#   frames, which makes the slew's bound exact rather than 0.07 loose.

with sync_playwright() as pw:
    # The site's default: the instrument. Every gesture is one the instrument
    # hears - Mono, X-Y and the Persistence by their controls, the note through
    # midiNoteOn, which sends it to the core - where on ?brain=js the fixture
    # was setMidiMode, setDisplay, genSet and state.persistence, which on the
    # default reach only the page's mirror.
    b, p, bad = open_page(pw, "")
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)
    print("\n--- on the page ---")
    live = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.midiMono.click(); el.dispXY.click(); midiNoteOn(57, 127);
      el.persistence.value = '0.12'; el.persistence.dispatchEvent(new Event('input'));
      const ids0 = ['photo.1', 'picture.round', 'picture.cover', 'picture.change', 'picture.novelty', 'picture.' + SIXTH];
      const before = ids0.filter((id) => MOD_SOURCES.has(id));
      await wait(1500);
      const unheard = el.readoutDetail.textContent;
      el.photoButton.click();
      const ids = ['photo.1', 'picture.round', 'picture.cover', 'picture.change', 'picture.novelty', 'picture.' + SIXTH];
      const registered = ids.filter((id) => MOD_SOURCES.has(id));
      const rules = ids.every((id) => { const s = MOD_SOURCES.get(id); return s && s.fromPicture && s.reach === PHOTO_REACH; });
      addRouting('picture.round', 'filter.res');
      const refused = !state.modRoutings.some((r) => r.sourceId === 'picture.round');
      addRouting('picture.nosuch', 'filter.res');
      const strangerRefused = !state.modRoutings.some((r) => r.sourceId === 'picture.nosuch');
      await wait(6500);
      const readout = el.readoutDetail.textContent;
      const stillOn = ids.filter((id) => MOD_SOURCES.has(id));
      el.photoButton.click();
      const gone = ids.filter((id) => MOD_SOURCES.has(id));
      return { registered, rules, refused, readout, gone, before, unheard, strangerRefused, stillOn,
               kind: state.source && state.source.kind };
    }""")
    print("    %s" % live)
    # The fixture is the instrument's: the source is the host's, not the page's own generator.
    check("on the site's instrument", live["kind"] == "host", str(live["kind"]))
    # These read the face's registry of sources and its routing rules, the
    # same on either brain; the photocell button is a click.
    check("the five come with the photocell, under the same rules as it",
          len(live["registered"]) == 6 and live["rules"], str(live["registered"]))
    check("null: before the photocell, five, which the check fails", len(live["before"]) == 5, str(live["before"]))
    check("since E3 a picture source may reach the filter too", not live["refused"], "")
    check("null: a source the page does not have is refused, so the reading can say so", live["strangerRefused"])
    # The readout's verdict is the page's own meter of the face's grid
    # (pictureMeter), which the default site still keeps beside the
    # instrument's: what the face says, not what the instrument judged. Step 5
    # points it at the instrument's verdict. On ?brain=js it read the same meter.
    check("the readout says what the loop is doing", "loop settled" in live["readout"], live["readout"])
    # Its null: before any routing from the picture is heard, the readout says nothing of a loop.
    check("null: with no picture routing heard it says no loop", "loop" not in live["unheard"], live["unheard"])
    # Since the picture stage (P3) the picture's sources are always there and
    # only the photocell comes and goes; this used to require all six gone.
    check("and only the photocell goes when it is switched off: the picture's stay",
          live["gone"] == live["registered"][1:] and len(live["gone"]) == 5, str(live["gone"]))
    check("null: with the photocell still on, all six are there, which the check fails",
          not (live["stillOn"] == live["registered"][1:] and len(live["stillOn"]) == 5), str(live["stillOn"]))
    check("no page errors on the default", not bad, "; ".join(bad[:3]))
    b.close()

    # The survey, on the page's own brain: it reads the page's sources over
    # four seconds of each corpus setup with the loop closed, which the core
    # cannot be asked for yet without render_cpp (a render with the loop
    # closed and the six sources read out as it goes).
    b, p, bad = open_page(pw, "&brain=js")
    # survey.js reads the old library's setups, from before P8g, by corpusSetup.
    corpus.install(p)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)
    print("\n--- the sixth slot, surveyed with the loop closed ---")
    p.evaluate("() => setPhoto(true)")
    survey = p.evaluate(open(SURVEY).read(), [4])
    for name, r in survey["result"].items():
        print("    %-7s entropy %.2f bits; shares %s; adds %.2f bits; not nought %.0f%% of the time"
              % (name, r["entropy"], r["shared"], r["adds"], 100 * r["nonzero"]))
    chosen = p.evaluate("() => SIXTH")
    # Half a bit: when it was chosen Direction added 1.6 and edge contact 0.7.
    check("the source in the sixth slot adds what the other five do not hold, half a bit or more",
          chosen == "signed" and survey["result"][chosen]["adds"] > 0.5, "%.2f bits" % survey["result"][chosen]["adds"])
    check("and a copy of roundness, the null, adds nothing", abs(survey["result"]["copy of round"]["adds"]) < 0.01,
          "%.3f bits" % survey["result"]["copy of round"]["adds"])

    check("no page errors on ?brain=js", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the picture's sources are on the photocell and the readout, and the sixth adds what the five do not")
