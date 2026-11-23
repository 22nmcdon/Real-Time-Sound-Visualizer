"""The constellation is gone (stage 5, step 4; the owner, 12 Nov): what the
prototype handed out still lands, and lands as the one figure.

The prototype (ways-to-draw step 2, 11-12 Nov) stored nothing - not a setup
field, a preset, undo, the morph or the browser's storage - so a setup code
made while it was drawing is an ordinary code, and no decode pass is needed
for it. What it did hand out was an address, `?draw=constellation` (with
`?brain=js` before it, from the default site's link). So this holds, each
against the way it would fail and each with its null:

- a code taken from the prototype's page while the constellation was drawing
  a held chord, seeded (the code below, captured from it on 14 Nov before it
  was removed), loads through the code field's own path with no page error
  and comes back out of the setup it makes unchanged; the null, a code with
  one field moved, does not;
- on the address the prototype handed out, and on the one without its
  ?brain=js, the page opens with no error and, a chord held, draws the one
  figure: the source asks for its figures as it always did (never the empty
  list the constellation answered to hide them), and the grid the face reads
  holds light. Until stage 5, step 5b's second half ?brain=js was the page's
  own brain, read with its own grid and nulled by making its tone source
  answer the empty list again; since then it is a word on the address and the
  page is the instrument, so the grid is the instrument's and the null is the
  chord let go and Clear pressed, where the light it reads goes;
- no Draw way remains: no `data-draw` menu, no option offering a
  constellation, no Reseed, and nothing of the prototype's in the page's
  script. The null: one such menu put into the page by hand is found.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

# Made on the prototype's page (?brain=js&draw=constellation, Place seeded,
# C3 C4 E4 G4 held at 100 in poly), by encodeSetup(snapshot()) while
# constellationLive() was true and the tone source answered no figures.
PROTOTYPE_CODE = ("eyJ2IjoxMSwic2hhcGUiOiJzaW5lIiwiY3ljbGVzIjoiIiwiZGlzcGxheSI6Inh5IiwicGVyc2lzdGVuY2UiOiIw"
                  "LjMiLCJ0aW1lYmFzZSI6MywibWlkaU1vZGUiOiJwb2x5IiwicG9seVJvdW5kIjp0cnVlLCJwaWN0dXJlQW1vdW50IjowfQ")


def recoded(**moved):
    """The prototype's code with fields moved, or taken out where given None, as the page writes a code."""
    import base64, json
    setup = json.loads(base64.urlsafe_b64decode(PROTOTYPE_CODE + "=" * (-len(PROTOTYPE_CODE) % 4)))
    for k, v in moved.items():
        if v is None: setup.pop(k, None)
        else: setup[k] = v
    return base64.b64encode(json.dumps(setup, separators=(",", ":")).encode()).decode().rstrip("=")


# What the prototype's code comes back out as: the same, less the quarter turn's
# switch, which went on 16 Nov (always on now, so a code's polyRound is read by
# nothing and not written back).
# And stamped with the version it comes up to: 12 since the EQ's switch became a field (17 Nov), and 13
# since the envelopes were drawn (18 Nov), whose pass writes the old envelope's shape into each of the
# three, where the codec writes them, after the cycle.
OLD_ENVELOPE = "1;A>p.2;D>p.2;R>a.2"
def back_code():
    import base64, json
    setup = json.loads(base64.urlsafe_b64decode(PROTOTYPE_CODE + "=" * (-len(PROTOTYPE_CODE) % 4)))
    setup.pop("polyRound")
    import os, re
    # The version the core brings a code up to (14 since 22 Nov, the EQ's whole range; the prototype has no EQ).
    setup["v"] = int(re.search(r"kSetupVersion = (\d+)", open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "core", "include", "scope", "setup.h")).read()).group(1))
    out = {}
    for k, v in setup.items():
        out[k] = v
        if k == "cycles": out.update(envShape=OLD_ENVELOPE, vcfShape=OLD_ENVELOPE, menvShape=OLD_ENVELOPE)
    return base64.b64encode(json.dumps(out, separators=(",", ":")).encode()).decode().rstrip("=")
BACK_CODE = back_code()


def decoded(code):
    """A code as the setup it carries, for a failure to say what came back rather than its first characters."""
    import base64, json
    return json.loads(base64.urlsafe_b64decode(code + "=" * (-len(code) % 4)))


def moved_code():
    # The prototype's code with one field moved (the timebase), for the null.
    # Until 16 Nov the field moved was the quarter turn, which is read by nothing now.
    return recoded(timebase=5)


fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)
def null(name, red, detail=""):
    """A check's null: the same comparison fed a value it must reject."""
    check("null: " + name, red, detail)


def opened(b, query):
    p = b.new_page(viewport={"width": 1400, "height": 900})
    errors = []
    p.on("pageerror", lambda e: errors.append(str(e)))
    p.goto(f"file://{ART}/scope.html" + query); p.wait_for_timeout(1200)
    p.evaluate("() => { if (el.helpDialog.open) el.helpDialog.close(); }")
    return p, errors


# The verdicts, written once so each null is fed to the same function its
# check is.
def plain_figures(answer):
    # The one figure: no list (one pair) or the two hands' pairs; never [].
    return answer is None or (isinstance(answer, list) and len(answer) > 0)

def leftovers(found):
    return found["menus"] + found["options"] + found["reseed"] + found["names"]


LOAD = """async (code) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  midiPanic(); await wait(50);
  loadCode(code);
  await wait(300);
  for (const n of [48, 60, 64, 67]) midiNoteOn(n, 100);
  await wait(700);
  return { back: encodeSetup(snapshot()), kind: state.source.kind, mode: midi.mode,
           figures: state.source.figures ? state.source.figures() : 'none',
           light: Array.from(phosphor.grid).reduce((a, v) => a + v, 0) };
}"""

FIND = """() => ({
  menus: document.querySelectorAll('[data-draw]').length,
  options: Array.from(document.querySelectorAll('option')).filter((o) => /constellation/i.test(o.value + o.textContent)).length,
  reseed: Array.from(document.querySelectorAll('button')).filter((x) => /reseed/i.test(x.textContent)).length,
  names: ['constellation', 'drawConstellation', 'constellationLive', 'paintDraw']
    .filter((n) => { try { return typeof eval(n) !== 'undefined'; } catch (e) { return false; } }).length,
})"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    for query, brain in (("?brain=js&draw=constellation", "the address it handed out"),
                         ("?draw=constellation", "the address without its ?brain=js")):
        print("\n--- %s, %s ---" % (query, brain))
        p, errors = opened(b, query)
        r = p.evaluate(LOAD, PROTOTYPE_CODE)
        check("a code from the prototype loads and comes back out of its setup unchanged but for the quarter turn's switch, on " + brain,
              r["back"] == BACK_CODE and r["mode"] == "poly", "%s, %s" % (r["mode"], decoded(r["back"])))
        if query.startswith("?brain=js"):
            other = p.evaluate(LOAD, moved_code())
            null("a code with one field moved does not come back as the prototype's", other["back"] != BACK_CODE,
                 other["back"][-24:])
            r = p.evaluate(LOAD, PROTOTYPE_CODE)
        check("on the address it handed out, a held chord draws the one figure: the source asks for its figures, on " + brain,
              plain_figures(r["figures"]) and r["kind"] in ("tone", "host"), "%s, figures %s" % (r["kind"], r["figures"]))
        null("the empty list the constellation answered is not the one figure", not plain_figures([]))
        check("and it is the instrument, whose grid holds its light", r["kind"] == "host" and r["light"] > 1,
              "%s, %.1f of light" % (r["kind"], r["light"]))
        if query.startswith("?brain=js"):
            hidden = p.evaluate("""async () => {
              const wait = (ms) => new Promise((r) => setTimeout(r, ms));
              midiPanic(); await wait(300);
              el.clearButton.click(); await wait(400);
              return Array.from(phosphor.grid).reduce((a, v) => a + v, 0);
            }""")
            null("the chord let go and Clear pressed, the light it reads goes", hidden < 0.1 * r["light"],
                 "%.2f of light against %.1f" % (hidden, r["light"]))
        found = p.evaluate(FIND)
        check("no Draw way remains: no data-draw menu, no constellation option, no Reseed, none of its names",
              leftovers(found) == 0, str(found))
        check("no page errors on " + brain, not errors, "; ".join(errors[:3]))
        p.close()

    print("\n--- the menu check can see a menu ---")
    p, _ = opened(b, "")
    p.evaluate("""() => { const s = document.createElement('select'); s.dataset.draw = 'way';
      s.innerHTML = '<option value="constellation">constellation</option>'; el.midiDrawRow.appendChild(s); }""")
    found = p.evaluate(FIND)
    null("a constellation menu put into the page by hand is found", leftovers(found) >= 2, str(found))
    p.close()
    b.close()

print("\n%d failure(s)" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
