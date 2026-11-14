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
- on the address the prototype handed out, on both brains, the page opens
  with no error and, a chord held, draws the one figure: the tone source asks
  for its figures as it always did (never the empty list the constellation
  answered to hide them), and on the page's own brain the page's grid holds
  light. The null: the source made to answer the empty list again, the grid
  wiped, and the light it reads goes;
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


def moved_code():
    # The prototype's code with one field moved (the quarter turn off), for the null.
    import base64, json
    setup = json.loads(base64.urlsafe_b64decode(PROTOTYPE_CODE + "=" * (-len(PROTOTYPE_CODE) % 4)))
    setup["polyRound"] = False
    return base64.urlsafe_b64encode(json.dumps(setup, separators=(",", ":")).encode()).decode().rstrip("=")


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
           light: Array.from(pictureEngine.cells).reduce((a, v) => a + v, 0) };
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

    for query, brain in (("?brain=js&draw=constellation", "the page's own brain"),
                         ("?draw=constellation", "the instrument's brain")):
        print("\n--- %s, %s ---" % (query, brain))
        p, errors = opened(b, query)
        r = p.evaluate(LOAD, PROTOTYPE_CODE)
        check("a code from the prototype loads and comes back out of its setup unchanged, on " + brain,
              r["back"] == PROTOTYPE_CODE and r["mode"] == "poly", "%s, %s" % (r["mode"], r["back"][:24]))
        if query.startswith("?brain=js"):
            other = p.evaluate(LOAD, moved_code())
            null("a code with one field moved does not come back as the prototype's", other["back"] != PROTOTYPE_CODE,
                 other["back"][-24:])
            r = p.evaluate(LOAD, PROTOTYPE_CODE)
        check("on the address it handed out, a held chord draws the one figure: the source asks for its figures, on " + brain,
              plain_figures(r["figures"]) and r["kind"] in ("tone", "host"), "%s, figures %s" % (r["kind"], r["figures"]))
        null("the empty list the constellation answered is not the one figure", not plain_figures([]))
        if query.startswith("?brain=js"):
            check("and the page's grid holds its light", r["light"] > 1, "%.1f of light" % r["light"])
            hidden = p.evaluate("""async () => {
              const wait = (ms) => new Promise((r) => setTimeout(r, ms));
              const kept = state.source.figures;
              state.source.figures = () => [];
              pictureEngine.fade(1, true); await wait(600);
              const light = Array.from(pictureEngine.cells).reduce((a, v) => a + v, 0);
              state.source.figures = kept;
              return light;
            }""")
            null("the source answering no figures again, the grid wiped, its light goes", hidden < 0.1 * r["light"],
                 "%.2f of light against %.1f" % (hidden, r["light"]))
        found = p.evaluate(FIND)
        check("no Draw way remains: no data-draw menu, no constellation option, no Reseed, none of its names",
              leftovers(found) == 0, str(found))
        check("no page errors on " + brain, not errors, "; ".join(errors[:3]))
        p.close()

    print("\n--- the menu check can see a menu ---")
    p, _ = opened(b, "?brain=js")
    p.evaluate("""() => { const s = document.createElement('select'); s.dataset.draw = 'way';
      s.innerHTML = '<option value="constellation">constellation</option>'; el.midiDrawRow.appendChild(s); }""")
    found = p.evaluate(FIND)
    null("a constellation menu put into the page by hand is found", leftovers(found) >= 2, str(found))
    p.close()
    b.close()

print("\n%d failure(s)" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
