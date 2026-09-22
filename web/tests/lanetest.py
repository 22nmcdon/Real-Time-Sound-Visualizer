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


def section(page, name):
    page.evaluate("""(want) => {
      for (const button of document.querySelectorAll('#benchRail button')) {
        if (button.textContent === want) { button.click(); return; }
      }
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

    print("\n--- and dragging it back asks the same law backwards ---")
    # The inverse is bisected rather than written out, so what matters is that
    # it lands on the depth the forward law came from - including on the one
    # destination whose law is not linear and the one that only ducks.
    trip = p.evaluate("""() => {
      const out = [];
      for (const [id, elid] of [['gen.freq','freq'], ['gen.amp','amp'],
                                ['gen.phase','phase'], ['view.rotate','rotate'],
                                ['filter.cutoff','filterCutoff'], ['gen.tumble','spinRate']]) {
        const dest = MOD_DESTS.get(id), input = document.getElementById(elid);
        if (!input) { out.push([id, 'no control']); continue; }
        let worst = 0;
        for (const a of [-0.9, -0.5, -0.1, 0, 0.1, 0.5, 0.9]) {
          const back = amountForReach(dest, input, destReach(dest, input, a));
          worst = Math.max(worst, Math.abs(back - a));
        }
        out.push([id, worst]);
      }
      return out;
    }""")
    for name, worst in trip:
        check("%s round-trips" % name, isinstance(worst, float) and worst < 1e-6,
              "worst %.2e" % worst if isinstance(worst, float) else str(worst))

    # -------------------------------------------------------------- geometry
    print("\n--- the lane is drawn where those numbers say ---")
    section(p, "Generator")
    p.evaluate("""() => {
      state.modRoutings = [{ sourceId: 'lfo1', destId: 'gen.freq', amount: 1 }];
      el.freq.value = '220'; el.freq.dispatchEvent(new Event('input'));
      focusSource = null; paintRoutings();
    }"""); p.wait_for_timeout(350)
    geo = p.evaluate("""() => {
      const input = el.freq, host = input.parentElement;
      const at = (c) => parseFloat(host.querySelector('.' + c).style.left) - input.offsetLeft;
      const w = (c) => parseFloat(host.querySelector('.' + c).style.width);
      return { span: at('lane-span'), spanW: w('lane-span'), cap: at('lane-cap'),
               width: input.offsetWidth,
               min: Number(input.min), max: Number(input.max) };
    }""")
    def x_for(value):
        return 6.5 + (value - geo["min"]) / (geo["max"] - geo["min"]) * (geo["width"] - 13)
    check("the cap sits on the octave, not at the end of the slider",
          abs(geo["cap"] - x_for(440)) < 0.5,
          "%.2f wanted %.2f (the slider ends at %.2f)"
          % (geo["cap"], x_for(440), x_for(geo["max"])))
    check("and the bar runs from the value to it",
          abs(geo["span"] - x_for(220)) < 0.5
          and abs(geo["spanW"] - (x_for(440) - x_for(220))) < 0.7,
          "from %.2f for %.2f, wanted %.2f for %.2f"
          % (geo["span"], geo["spanW"], x_for(220), x_for(440) - x_for(220)))

    print("\n--- the lane draws one source, whoever else is on the control ---")
    # The property the split thumb could not hold. Two sources at very
    # different depths: whichever is armed is what the lane shows, and the
    # other one changes nothing about it.
    both = p.evaluate("""async () => {
      const settle = () => new Promise((d) => requestAnimationFrame(
        () => requestAnimationFrame(d)));
      const capAt = () => parseFloat(el.freq.parentElement
        .querySelector('.lane-cap').style.left) - el.freq.offsetLeft;

      state.modRoutings = [{ sourceId: 'lfo1', destId: 'gen.freq', amount: 0.25 }];
      focusSource = null; paintRoutings(); await settle();
      const alone = capAt();

      state.modRoutings.push({ sourceId: 'lfo2', destId: 'gen.freq', amount: 0.95 });
      touchRoutings(); await settle();
      const withCompany = capAt();

      focusSource = null; armSource('lfo2'); await settle();
      const other = capAt();
      return { alone, withCompany, other,
               width: el.freq.offsetWidth,
               min: Number(el.freq.min), max: Number(el.freq.max),
               pips: document.querySelectorAll('[data-mod-dest="gen.freq"] .mod-open .pip').length };
    }"""); p.wait_for_timeout(200)

    def freq_x(hz):
        return (6.5 + (hz - both["min"]) / (both["max"] - both["min"])
                * (both["width"] - 13))
    # 220 Hz driven a quarter of an octave up, and nineteen twentieths of one.
    want_one, want_two = freq_x(220 * 2 ** 0.25), freq_x(220 * 2 ** 0.95)
    check("a second source does not move the first one's cap",
          abs(both["alone"] - both["withCompany"]) < 0.5,
          "%.2f -> %.2f" % (both["alone"], both["withCompany"]))
    check("and the cap is where the first one's own depth puts it",
          abs(both["withCompany"] - want_one) < 0.5,
          "%.2f wanted %.2f" % (both["withCompany"], want_one))
    check("focusing the second shows the second, at its own depth",
          abs(both["other"] - want_two) < 0.5,
          "%.2f wanted %.2f" % (both["other"], want_two))
    check("and both are counted on the button", both["pips"] == 2, str(both["pips"]))

    print("\n--- a bipolar source sweeps both ways, an envelope one ---")
    def bar_for(routing_js, elid, want_section):
        section(p, want_section)
        p.evaluate(routing_js); p.wait_for_timeout(320)
        return p.evaluate("""(elid) => {
          const input = document.getElementById(elid), host = input.parentElement;
          const num = (c, prop) => parseFloat(host.querySelector('.' + c).style[prop]);
          return { left: num('lane-span', 'left') - input.offsetLeft,
                   width: num('lane-span', 'width'),
                   base: thumbX(input, input.offsetWidth, Number(input.value)) };
        }""", elid)

    osc = bar_for("""() => {
      el.rotate.value = '0'; el.rotate.dispatchEvent(new Event('input'));
      state.modRoutings = [{ sourceId: 'lfo1', destId: 'view.rotate', amount: 0.6 }];
      focusSource = null; paintRoutings(); }""", "rotate", "Display")
    check("an oscillator's bar reaches one way from the value",
          abs(osc["left"] - osc["base"]) < 0.6 or
          abs(osc["left"] + osc["width"] - osc["base"]) < 0.6,
          "from %.2f for %.2f, value at %.2f" % (osc["left"], osc["width"], osc["base"]))

    env = bar_for("""() => {
      state.modRoutings = [{ sourceId: 'env.live', destId: 'view.rotate', amount: 0.6 }];
      focusSource = null; paintRoutings(); }""", "rotate", "Display")
    check("and an envelope's the same, since the bar is the depth you set",
          abs(env["width"] - osc["width"]) < 1.0,
          "%.1f px vs %.1f" % (env["width"], osc["width"]))

    print("\n--- asking for more than the control has ---")
    section(p, "Display")
    p.evaluate("""() => {
      el.rotate.value = '50'; el.rotate.dispatchEvent(new Event('input'));
      state.modRoutings = [{ sourceId: 'env.live', destId: 'view.rotate', amount: 1 }];
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
      lfos[0].rate = 4;
      focusSource = null;
      paintRoutings();
      await new Promise((d) => requestAnimationFrame(d));
      const host = el.rotate.parentElement;
      const now = () => parseFloat(host.querySelector('.lane-now').style.left);
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

    print("\n--- an unpatched control draws no lane ---")
    bare = p.evaluate("""() => {
      state.modRoutings = []; paintRoutings();
      const host = el.rotate.parentElement;
      return { parts: Array.from(host.querySelectorAll('.mod-lane')).filter((n) => !n.hidden).length,
               ring: !!document.querySelector('[data-mod-dest="view.rotate"] .mod-open .ring') };
    }"""); p.wait_for_timeout(200)
    check("nothing on it, nothing drawn", bare["parts"] == 0, str(bare))
    check("but the way in is still there", bare["ring"] is True, str(bare))

    print("\n--- zoom is a destination now ---")
    p.evaluate("""() => {
      state.modRoutings = [{ sourceId: 'lfo1', destId: 'view.zoom', amount: 1 }];
      touchRoutings();
    }"""); p.wait_for_timeout(300)
    zoom = p.evaluate("""() => {
      setZoom(0);
      lfos[0].value = 1;
      const f = capture();
      applyModMatrix(f, 16);
      const up = { mod: state.zoomMod, zoom: state.zoom };
      lfos[0].value = 0;
      applyModMatrix(capture(), 16);
      return { up, rest: { mod: state.zoomMod, zoom: state.zoom },
               framed: document.querySelector('[data-mod-dest="view.zoom"]')
                 .classList.contains('modulated') };
    }""")
    check("the transport's zoom takes a patch", zoom["framed"] is True)
    check("full depth is the eight steps it declares",
          close(zoom["up"]["mod"], 8), str(zoom["up"]["mod"]))
    check("and it magnifies", zoom["up"]["zoom"] > zoom["rest"]["zoom"] * 1.5,
          "%.2f vs %.2f" % (zoom["up"]["zoom"], zoom["rest"]["zoom"]))
    check("with the offset back to nothing at rest", close(zoom["rest"]["mod"], 0),
          str(zoom["rest"]["mod"]))

    print("\n--- the trigger position slides the window, not the trigger ---")
    section(p, "Trigger")
    slid = p.evaluate("""() => {
      state.modRoutings = [{ sourceId: 'lfo1', destId: 'trig.position', amount: 1 }];
      touchRoutings();
      el.position.value = '10'; el.position.dispatchEvent(new Event('input'));
      const level = state.level, pos = state.position;
      lfos[0].value = 1;
      applyModMatrix(capture(), 16);
      const up = state.positionMod;
      lfos[0].value = 0;
      applyModMatrix(capture(), 16);
      return { up, rest: state.positionMod, level, pos,
               levelAfter: state.level, posAfter: state.position };
    }""")
    # Full depth is half the window, but the knob is at a tenth and the
    # destination clamps at the end of its own range: 0.1 + 0.5 cannot pass 1,
    # so what it actually gets is the 0.5 it asked for.
    check("full depth moves it half a window", close(slid["up"], 0.5), str(slid["up"]))
    check("and nothing at rest", close(slid["rest"], 0), str(slid["rest"]))
    check("the trigger level is untouched", close(slid["level"], slid["levelAfter"]),
          "%s -> %s" % (slid["level"], slid["levelAfter"]))
    check("and so is the knob it is offset from",
          close(slid["pos"], slid["posAfter"]), str(slid["posAfter"]))
    p.evaluate("() => { state.modRoutings = []; touchRoutings(); }")
    section(p, "Display")

    print("\n--- and the oscillator panel agrees with the controls ---")
    agree = p.evaluate("""() => {
      state.modRoutings = [{ sourceId: 'lfo1', destId: 'view.rotate', amount: 0.42 }];
      touchRoutings();
      return null;
    }"""); p.wait_for_timeout(350)
    one = p.evaluate("""() => ({
      dest: document.getElementById('lfoDest0').value,
      disabled: document.getElementById('lfoDest0').disabled,
      depth: document.getElementById('lfoDepth0').value,
    })""")
    check("a drag updates the oscillator's own destination menu",
          one["dest"] == "view.rotate", str(one))
    check("and its depth slider", one["depth"] == "42", str(one))

    p.evaluate("""() => {
      state.modRoutings = [
        { sourceId: 'lfo1', destId: 'view.rotate', amount: 0.4 },
        { sourceId: 'lfo1', destId: 'gen.freq', amount: 0.4 },
      ];
      touchRoutings();
    }"""); p.wait_for_timeout(300)
    two = p.evaluate("""() => ({
      disabled: document.getElementById('lfoDest0').disabled,
      text: document.getElementById('lfoDest0').options[0].textContent,
    })""")
    check("past one destination it stops offering to replace them",
          two["disabled"] is True, str(two))
    check("and says how many there are", "2 destinations" in two["text"], str(two))

    p.screenshot(path=f"{SHOTS}/dual.png")
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all lane checks pass")
