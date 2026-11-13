"""The X-Y plane as an effect: its eight operations, and the oversampling (S2).

What would go wrong, and what is checked for it:

- the arithmetic: at 1x the operation is applied as it is, so a mirrored X
  is |x| to the last bit and Y is left alone; a clipped pair has exactly
  r tanh(|v| / r) for its length and exactly its old direction. The fixture
  is a 3:2 figure - never a circle, whose length and direction statistics a
  broken clip could leave alone. The same figure, point by point, for the
  matrix, the twist (a fixed angle misses by 0.4), the fold and the snap,
  and all four non-linear ones together in their stated order (the
  kaleidoscope was cut on 7 November: the owner found it only ever made a
  terrible sound);
- the sound: a mirrored sine is an octave up with no odd harmonics;
- aliasing: what the operations put above Nyquist folded back. Measured at
  1x, 2x and 4x and pinned, against the floor the page already lives with,
  the band-limited square's;
- applied twice, or not at all where it should be: once to each layer's
  picture, and what is heard their sum - since P4 there is no heard pair of
  its own to forget or to do twice;
- the delay the oversampling costs, stated in the code and measured here;
- the panel, a source on the radius and on the twist - the latter with its
  slider at nought, which once did nothing - and setup codes, with the
  version-4 pass that turns the old clip checkbox into the limit menu.
"""
# Stage 5, step 3, batch 4 (13 Nov): until then this suite opened ?brain=js
# and rendered a makeGeneratorCore built in the page, and held a key on the
# page's brain to read the page's generator's window. Those numbers - each
# operation's arithmetic at 1x, the mirrored sine an octave up, the aliasing
# floors and pins and what oversampling buys, once to each layer's picture
# and the heard pair their sum, the 31 samples' delay, the cost, the panel's
# figure clipped once, and a key on the radius and on the twist - are
# asserted on the core now, each with its null, in core/tests/pieces/
# plane.py (the pins and the cost measured again there, on the core). What is
# left here is the face, on the site's default page: the panel, its units,
# codes and search.
import math, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    # Here stood, on ?brain=js: the arithmetic at 1x (mirror, both, the clip's
    # length and direction, scale and shear, the twist, the fold, the snap,
    # all four in order), the mirrored sine an octave up, the aliasing floors
    # and pins at 1x, 2x and 4x, the heard pair the pictures summed, the delay
    # oversampling costs, and the cost of sixteen voices at 4x - all on a
    # makeGeneratorCore built in the page. core/tests/pieces/plane.py's now.

    print("\n--- the panel ---")
    # On ?brain=js this read genSettings(), the page's generator; on the
    # default that is only the face's mirror, so the controls are read off the
    # setup the face sends (snapshot, in the panel's own units). The figure
    # it then drew under a held key - mirrored and clipped once, and opened
    # to 0.75 by a key on the radius - is core/tests/pieces/plane.py's now,
    # through the instrument whole with these same controls moved by id.
    panel = p.evaluate("""async () => {
      setView('bench'); setBenchTab('space');
      const shown = el.planeGroup.offsetHeight > 0;
      el.planeMirror.value = '1'; el.planeMirror.dispatchEvent(new Event('change'));
      const mirror = snapshot().planeMirror;
      el.planeRadius.value = '25'; el.planeRadius.dispatchEvent(new Event('input'));
      const radiusOff = { code: snapshot().planeLimit, row: el.planeRadiusRow.hidden };
      el.planeLimit.value = '1'; el.planeLimit.dispatchEvent(new Event('change'));
      const radiusOn = { code: snapshot().planeLimit, radius: snapshot().planeRadius, row: el.planeRadiusRow.hidden };
      el.planeOS4.click();
      const os = { code: snapshot().planeOS, aria: el.planeOS4.getAttribute('aria-checked') };
      el.planeMirror.value = '0'; el.planeMirror.dispatchEvent(new Event('change'));
      el.planeLimit.value = '0'; el.planeLimit.dispatchEvent(new Event('change'));
      el.planeOS2.click();
      return { shown, mirror, radiusOff, radiusOn, os };
    }""")
    print("    %s" % panel)
    check("the section is in Space & Memory and its controls reach the setup - the radius shown and used only with the clip on",
          panel["shown"] and panel["mirror"] == 1 and panel["radiusOff"] == {"code": 0, "row": True}
          and panel["radiusOn"] == {"code": 1, "radius": 25, "row": False}
          and panel["os"] == {"code": 4, "aria": "true"}, str(panel))

    print("\n--- the rest of the panel ---")
    rest = p.evaluate("""async () => {
      const set = (id, v, kind) => { el[id].value = String(v); el[id].dispatchEvent(new Event(kind)); };
      setView('bench'); setBenchTab('space');
      set('planeTwist', 25, 'input'); set('planeSnap', 5, 'change');
      set('planeScaleX', 150, 'input'); set('planeScaleY', 50, 'input'); set('planeShear', -40, 'input');
      const c = snapshot();
      const got = [c.planeTwist, c.planeSnap, c.planeScaleX, c.planeScaleY, c.planeShear, el.planeTwistValue.textContent];
      set('planeTwist', 0, 'input'); set('planeSnap', 0, 'change');
      set('planeScaleX', 100, 'input'); set('planeScaleY', 100, 'input'); set('planeShear', 0, 'input');
      return { got };
    }""")
    print("    %s" % rest)
    # On ?brain=js this read the page generator's own units (a quarter turn a
    # unit as 0.25 * 2 pi, the scales as fractions); on the default the face
    # sends hundredths, and the core's restore turns them into the
    # generator's units, which parity's restore section holds. The reading
    # beside the slider is the face's own, and stays.
    check("twist, snap, scale and shear reach the setup in the panel's units - a quarter-turn a unit reads 90 degrees",
          rest["got"] == [25, 5, 150, 50, -40, "90°"], str(rest["got"]))
    # Here stood "a source on Twist swirls a figure whose slider is at
    # nought", a key held on the page's brain; core/tests/pieces/plane.py's now.

    print("\n--- setup codes ---")
    # restore() is the face's half of a code; the instrument hears a code only
    # through loadCode or a preset. On ?brain=js these read genSettings(), the
    # page's generator; on the default that is the mirror, so they read the
    # menus and the setup the face would send. That the core's restore gives
    # the generator the same is parity's restore section's.
    codes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const read = () => { const c = snapshot(); return { mirror: c.planeMirror, limit: c.planeLimit,
                            radius: c.planeRadius, os: c.planeOS, menu: el.planeLimit.value }; };
      restore({ planeMirror: 2, planeLimit: 2, planeRadius: 60, planeOS: 4 }); await wait(30);
      const one = read();
      const code = snapshot();
      restore({}); await wait(30);
      const old = read();
      // A code from before version 4 said the clip was on with a box.
      restore(migrateSetup({ v: 3, planeClip: true, planeRadius: 30 })); await wait(30);
      const boxed = read();
      const unboxed = migrateSetup({ v: 3, planeClip: false });
      restore({ planeTwist: -30, planeSnap: 5, planeScaleX: 150, planeScaleY: 60, planeShear: 25 });
      await wait(30);
      const c2 = snapshot();
      const rest = [c2.planeTwist, c2.planeSnap, c2.planeScaleX, c2.planeScaleY, c2.planeShear,
                    el.planeTwist.value, el.planeSnap.value, el.planeScaleX.value, el.planeScaleY.value, el.planeShear.value];
      restore({}); await wait(30);
      const c0 = snapshot();
      const restOld = [c0.planeTwist, c0.planeSnap, c0.planeScaleX, c0.planeScaleY, c0.planeShear];
      return { rest, restOld, one, old, boxed, unboxed: [unboxed.planeLimit, 'planeClip' in unboxed],
               code: [code.planeMirror, code.planeLimit, code.planeRadius, code.planeOS, 'planeClip' in code] };
    }""")
    print("    %s" % codes)
    check("a code's plane reaches the panel",
          codes["one"] == {"mirror": 2, "limit": 2, "radius": 60, "os": 4, "menu": "2"}, str(codes["one"]))
    check("a code carries it, and no box any more", codes["code"] == [2, 2, 60, 4, False], str(codes["code"]))
    check("and a code from before has the plane off, at 2x",
          codes["old"] == {"mirror": 0, "limit": 0, "radius": 40, "os": 2, "menu": "0"}, str(codes["old"]))
    check("a code carries the twist, snap and matrix both ways",
          codes["rest"] == [-30, 5, 150, 60, 25, "-30", "5", "150", "60", "25"], str(codes["rest"]))
    check("and a code from before has them all at rest", codes["restOld"] == [0, 0, 100, 100, 0], str(codes["restOld"]))
    # Version 3 had a checkbox for the clip and a radius; version 4 has one
    # menu of three. Without the decode pass a ticked box would load as off.
    check("a version-3 code with the clip ticked loads as Clip, at its radius",
          codes["boxed"] == {"mirror": 0, "limit": 1, "radius": 30, "os": 2, "menu": "1"}, str(codes["boxed"]))
    check("and one without it as off, the box's field gone",
          codes["unboxed"][1] is False and codes["unboxed"][0] in (None, 0), str(codes["unboxed"]))

    def search(q):
        p.evaluate("(q) => { el.benchSearch.value = q; el.benchSearch.dispatchEvent(new Event('input')); }", q)
        return p.evaluate("""() => Array.from(el.benchResults.querySelectorAll('button'))
          .map((b) => [b.firstChild.textContent, b.querySelector('.crumb').textContent])""")
    found = search("rectifier")
    # In the rack's Plane module since F5, where it was the Plane section.
    check("rectifier finds the mirror", ["Mirror", "Effects \u203a Plane"] in found, str(found[:3]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the plane is an effect: what folds the picture folds the sound")
