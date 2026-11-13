"""The lane: does it tell the truth about where the modulation goes?

The slider is the browser's and it draws itself. The lane under it is a claim -
that this source, at this depth, takes this control HERE - and a claim is the
kind of thing that can be quietly wrong: a bar that looks plausible while the
law it is drawing is not the law the signal path applies. So the numbers are
checked against the destinations' own arithmetic first and the pixels against
the numbers second.

The one to watch is frequency, the only destination whose law is exponential.
Full depth is an octave, so 220 Hz has to put its cap at 440 and not at the end
of a 4 kHz track.

The other half of this is the thing the split thumb it replaces got wrong: the
lane draws ONE source, whichever is armed, so what it shows never depends on how
many are attached.
"""
# On the default page since stage 5's step 3 (13 Nov), but for two sections;
# wholly on ?brain=js from 5m to then. The laws, the ring, the cap and the
# editor's rows are the face's and read the same here. The live tick read the
# page's own oscillator, its rate set by hand; on the default page the
# instrument posts its oscillators into the same `lfos` (makeBrainSource's
# absorb), so the dot is driven by the instrument's LFO 1 and the rate written
# by hand would be dead - it is gone, and a null with a source that does not
# move shows the dot is reading a source.
#
# The zoom's and the trigger position's offsets, eight checks of numbers
# that were left here on a ?brain=js page of their own by batch 1 (LFO 1's
# value set by hand and the page's matrix stepped), are
# core/tests/pieces/lane.py's since batch 3 (13 Nov): a source held at a
# value in the core's matrix, on the destinations the instrument's own
# screen registers, and the capture reading the offset. Which matrix the
# face's screen follows on the site is step 5's to decide.
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
SHOTS = os.path.join(HERE, "shots"); os.makedirs(SHOTS, exist_ok=True)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def close(a, b, tol=1e-6):
    return a is not None and b is not None and abs(a - b) <= tol


def null(name, red, detail=""):
    check("null: " + name, red, detail)

def section(page, name):
    # The section's tab brought forward: the rail names tasks, not sections,
    # since the Bench became tabs.
    page.evaluate("""(want) => {
      const group = settingsGroups().find((g) => groupTitle(g) === want);
      if (group) showBenchFor(group);
    }""", name)
    page.wait_for_timeout(180)


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate("() => { setView('bench'); state.modRoutings = []; touchRoutings(); }")
    p.wait_for_timeout(300)

    # ------------------------------------------------------------------ laws
    print("\n--- the reach is the destination's own law ---")
    reach = p.evaluate("""() => {
      const at = (id, el, s) => destReach(MOD_DESTS.get(id), document.getElementById(el), s);
      el.freq.value = '220'; el.amp.value = '55';
      el.phase.value = '90'; el.rotate.value = '0'; el.filterCutoff.value = '566';
      return {
        octaveUp:   at('gen.freq', 'freq', 1),
        octaveDown: at('gen.freq', 'freq', -1),
        fifth:      at('gen.freq', 'freq', Math.log2(1.5)),
        duckHalf:   at('gen.amp', 'amp', 0.5),
        duckNone:   at('gen.amp', 'amp', 0),
        phaseHalf:  at('gen.phase', 'phase', 0.5),
        rotateHalf: at('view.rotate', 'rotate', 0.5),
        cutoffFull: at('filter.cutoff', 'filterCutoff', 1),
      };
    }""")
    check("full depth on frequency is exactly an octave up",
          close(reach["octaveUp"], 440), "%.4f Hz" % reach["octaveUp"])
    check("and full depth the other way is an octave down",
          close(reach["octaveDown"], 110), "%.4f Hz" % reach["octaveDown"])
    check("a depth of log2(1.5) is a fifth",
          close(reach["fifth"], 330, 1e-9), "%.6f Hz" % reach["fifth"])
    check("amplitude only ducks, and halves at half depth",
          close(reach["duckHalf"], 27.5) and close(reach["duckNone"], 55),
          "%.2f at half, %.2f at none" % (reach["duckHalf"], reach["duckNone"]))
    check("half depth on phase is a quarter turn",
          close(reach["phaseHalf"], 180), "%.1f deg" % reach["phaseHalf"])
    # The rotation's span is 1 turn out of a -2..2 range, on a -50..50 slider:
    # a quarter of the slider's travel at full depth, so half depth is 12.5.
    check("half depth on rotation is an eighth of the slider",
          close(reach["rotateHalf"], 12.5), "%.3f" % reach["rotateHalf"])
    check("full depth on cutoff is 400 steps, as declared",
          close(reach["cutoffFull"], 966), "%.1f" % reach["cutoffFull"])

    # The round-trip check that used to live here went with `amountForReach`.
    # Nothing inverts the reach laws now that the lane only reads, and a
    # function kept alive so that a test can call it is not a tested function -
    # it is a tested test.

    # -------------------------------------------------------------- geometry
    print("\n--- the lane is drawn where those numbers say ---")
    section(p, "Generator")
    p.evaluate("""() => {
      state.modRoutings = [{ sourceId: 'lfo1', destId: 'gen.freq', amount: 1 }];
      el.freq.value = '220'; el.freq.dispatchEvent(new Event('input'));
      focusSource = null; paintRoutings();
    }"""); p.wait_for_timeout(350)
    # A knob since P8c: the lane is a ring round the face, so where it is
    # drawn is an angle - 270 degrees for the whole range, from the bottom
    # left - read off the face's own properties. It was pixels along the
    # slider, with half a thumb's inset at each end.
    geo = p.evaluate("""() => {
      const input = el.freq, face = input.parentElement.querySelector('.knob-face');
      const at = (name) => parseFloat(face.style.getPropertyValue(name));
      return { span: at('--lane-a'), spanW: at('--lane-b') - at('--lane-a'), cap: at('--cap'),
               min: Number(input.min), max: Number(input.max) };
    }""")
    def x_for(value):
        return (value - geo["min"]) / (geo["max"] - geo["min"]) * 270
    check("the cap sits on the octave, not at the end of the range",
          abs(geo["cap"] - x_for(440)) < 1e-6,
          "%.4f deg wanted %.4f (the range ends at %.1f)"
          % (geo["cap"], x_for(440), x_for(geo["max"])))
    check("and the ring runs from the value to it",
          abs(geo["span"] - x_for(220)) < 1e-6
          and abs(geo["spanW"] - (x_for(440) - x_for(220))) < 1e-6,
          "from %.4f for %.4f, wanted %.4f for %.4f"
          % (geo["span"], geo["spanW"], x_for(220), x_for(440) - x_for(220)))

    print("\n--- the lane draws one source, whoever else is on the control ---")
    # The property the split thumb could not hold. Two sources at very
    # different depths: whichever is armed is what the lane shows, and the
    # other one changes nothing about it.
    both = p.evaluate("""async () => {
      const settle = () => new Promise((d) => requestAnimationFrame(
        () => requestAnimationFrame(d)));
      const capAt = () => parseFloat(el.freq.parentElement
        .querySelector('.knob-face').style.getPropertyValue('--cap'));

      state.modRoutings = [{ sourceId: 'lfo1', destId: 'gen.freq', amount: 0.25 }];
      focusSource = null; paintRoutings(); await settle();
      const alone = capAt();

      state.modRoutings.push({ sourceId: 'lfo2', destId: 'gen.freq', amount: 0.95 });
      touchRoutings(); await settle();
      const withCompany = capAt();

      selectSource('lfo2'); await settle();
      const other = capAt();
      return { alone, withCompany, other,
               min: Number(el.freq.min), max: Number(el.freq.max),
               // Since G5b the other source is a tick on the ring, where it was a second dot at the shoulder.
               ticks: [...document.querySelectorAll('[data-mod-dest="gen.freq"] .lane-tick')].map((t) => t.dataset.source) };
    }"""); p.wait_for_timeout(200)

    def freq_x(hz):
        return (hz - both["min"]) / (both["max"] - both["min"]) * 270
    # 220 Hz driven a quarter of an octave up, and nineteen twentieths of one.
    want_one, want_two = freq_x(220 * 2 ** 0.25), freq_x(220 * 2 ** 0.95)
    check("a second source does not move the first one's cap",
          abs(both["alone"] - both["withCompany"]) < 1e-6,
          "%.2f -> %.2f" % (both["alone"], both["withCompany"]))
    check("and the cap is where the first one's own depth puts it",
          abs(both["withCompany"] - want_one) < 1e-6,
          "%.2f wanted %.2f" % (both["withCompany"], want_one))
    check("focusing the second shows the second, at its own depth",
          abs(both["other"] - want_two) < 1e-6,
          "%.2f wanted %.2f" % (both["other"], want_two))
    check("and the one not drawn is a tick", both["ticks"] == ["lfo1"], str(both["ticks"]))

    print("\n--- a bipolar source sweeps both ways, an envelope one ---")
    def bar_for(routing_js, elid, want_section):
        section(p, want_section)
        p.evaluate(routing_js); p.wait_for_timeout(320)
        return p.evaluate("""(elid) => {
          const input = document.getElementById(elid), face = input.parentElement.querySelector('.knob-face');
          const at = (name) => parseFloat(face.style.getPropertyValue(name));
          return { left: at('--lane-a'), width: at('--lane-b') - at('--lane-a'),
                   base: knobFraction(input) * KNOB_SWEEP };
        }""", elid)

    osc = bar_for("""() => {
      el.rotate.value = '0'; el.rotate.dispatchEvent(new Event('input'));
      state.modRoutings = [{ sourceId: 'lfo1', destId: 'view.rotate', amount: 0.6 }];
      focusSource = null; paintRoutings(); }""", "rotate", "Display")
    check("an oscillator's bar reaches one way from the value",
          (abs(osc["left"] - osc["base"]) < 1e-6 or
           abs(osc["left"] + osc["width"] - osc["base"]) < 1e-6) and osc["width"] > 1,
          "from %.2f for %.2f, value at %.2f" % (osc["left"], osc["width"], osc["base"]))

    env = bar_for("""() => {
      state.modRoutings = [{ sourceId: 'env.note', destId: 'view.rotate', amount: 0.6 }];
      focusSource = null; paintRoutings(); }""", "rotate", "Display")
    check("and an envelope's the same, since the bar is the depth you set",
          abs(env["width"] - osc["width"]) < 1e-6 and env["width"] > 1,
          "%.4f deg vs %.4f" % (env["width"], osc["width"]))

    print("\n--- asking for more than the control has ---")
    section(p, "Display")
    p.evaluate("""() => {
      el.rotate.value = '50'; el.rotate.dispatchEvent(new Event('input'));
      state.modRoutings = [{ sourceId: 'env.note', destId: 'view.rotate', amount: 1 }];
      focusSource = null; paintRoutings();
    }"""); p.wait_for_timeout(350)
    marked = p.evaluate("""() => el.rotate.parentElement
      .querySelector('.lane-cap').classList.contains('clipped')""")
    check("the cap says it cannot get there", marked is True)
    kept = p.evaluate("() => state.modRoutings[0].amount")
    check("but the depth is kept, not trimmed", close(kept, 1), str(kept))
    p.evaluate("() => { el.rotate.value = '0'; el.rotate.dispatchEvent(new Event('input')); }")

    print("\n--- the live tick ---")
    section(p, "Display")
    moved = p.evaluate("""async () => {
      state.modRoutings = [{ sourceId: 'lfo1', destId: 'view.rotate', amount: 0.9 }];
      focusSource = null;
      paintRoutings();
      await new Promise((d) => requestAnimationFrame(d));
      const host = el.rotate.parentElement;
      const face = host.querySelector('.knob-face');
      const now = () => parseFloat(face.style.getPropertyValue('--now'));
      const seen = new Set();
      for (let i = 0; i < 40; i++) {
        await new Promise((r) => requestAnimationFrame(r));
        seen.add(Math.round(now()));
      }
      return { places: seen.size,
               tick: !host.querySelector('.lane-now').hidden,
               grabs: document.querySelectorAll('.lane-grab').length };
    }""")
    check("a patched control shows itself working", moved["places"] > 4, str(moved))
    check("the tick is on whether or not anything is in focus", moved["tick"] is True)
    # The lane reads and nothing else now: what used to be a drag target on it
    # is gone, and the editor does the editing.
    check("and the lane has no handle at all", moved["grabs"] == 0, str(moved["grabs"]))
    still = p.evaluate("""async () => {
      // The note's envelope, with no note held: a source at rest.
      state.modRoutings = [{ sourceId: 'env.note', destId: 'view.rotate', amount: 0.9 }];
      focusSource = null; paintRoutings();
      await new Promise((d) => requestAnimationFrame(d));
      const face = el.rotate.parentElement.querySelector('.knob-face');
      const seen = new Set();
      for (let i = 0; i < 40; i++) {
        await new Promise((r) => requestAnimationFrame(r));
        seen.add(Math.round(parseFloat(face.style.getPropertyValue('--now'))));
      }
      return seen.size;
    }""")
    null("from a source at rest the same dot stays in one place, so the places above are the oscillator's",
         still <= 4, "%d places" % still)

    print("\n--- an unpatched control draws no lane ---")
    bare = p.evaluate("""() => {
      state.modRoutings = []; paintRoutings();
      const host = el.rotate.parentElement;
      return { parts: Array.from(host.querySelectorAll('.mod-lane')).filter((n) => !n.hidden).length,
               // The way in since G5b: the control's right-click menu, where it was a hollow ring.
               ring: menuControl(el.rotate) === el.rotate };
    }"""); p.wait_for_timeout(200)
    check("nothing on it, nothing drawn", bare["parts"] == 0, str(bare))
    check("but the way in is still there", bare["ring"] is True, str(bare))

    print("\n--- zoom is a destination now ---")
    p.evaluate("""() => {
      state.modRoutings = [{ sourceId: 'lfo1', destId: 'view.zoom', amount: 1 }];
      touchRoutings();
    }"""); p.wait_for_timeout(300)
    framed = p.evaluate("""() => document.querySelector('[data-mod-dest="view.zoom"]').classList.contains('modulated')""")
    p.evaluate("() => { state.modRoutings = []; touchRoutings(); }")
    check("the transport's zoom takes a patch", framed is True)

    # Its numbers - full depth the eight steps, and the trigger position's
    # offset sliding the window and not the trigger - are
    # core/tests/pieces/lane.py's (see the top).
    section(p, "Display")

    # The oscillator's card's editor (the Sources tab until F4), where its
    # one-destination menu was. That menu had to stand down, disabled, once a
    # source went to two places; a list of destinations has no such case -
    # two are two rows.
    print("\n--- and the card's editor agrees with the controls ---")
    p.evaluate("""() => {
      openModCard('lfo1');
      state.modRoutings = [{ sourceId: 'lfo1', destId: 'view.rotate', amount: 0.42 }];
      touchRoutings();
    }"""); p.wait_for_timeout(350)
    rows = lambda: p.evaluate("""() => Array.from(el.srcDetail.querySelectorAll('.mod-edit'))
      .map((r) => [r.dataset.dest, r.querySelector('input').value])""")
    one = rows()
    check("a routing made anywhere is a row on the source's tab, with its depth",
          one == [["view.rotate", "42"]], str(one))
    p.evaluate("""() => {
      state.modRoutings = [
        { sourceId: 'lfo1', destId: 'view.rotate', amount: 0.4 },
        { sourceId: 'lfo1', destId: 'gen.freq', amount: -0.25 },
      ];
      touchRoutings();
    }"""); p.wait_for_timeout(300)
    two = rows()
    check("and two destinations are two rows, each at its own depth",
          sorted(two) == [["gen.freq", "-25"], ["view.rotate", "40"]], str(two))

    p.screenshot(path=f"{SHOTS}/dual.png")
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all lane checks pass")
