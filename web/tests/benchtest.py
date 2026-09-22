"""The Bench: one set of controls, two places to put them.

The thing most likely to go wrong here is duplication - a control copied into
the bench instead of moved gives two elements one id, and getElementById
silently returns the first. That has already cost this page one readout line,
so it is the first thing asserted.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
SHOTS = os.path.join(HERE, "shots")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
os.makedirs(SHOTS, exist_ok=True)

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

DUPES = """() => {
  const seen = new Map(), dupes = [];
  for (const node of document.querySelectorAll('[id]')) {
    if (seen.has(node.id)) dupes.push(node.id); else seen.set(node.id, node);
  }
  return dupes;
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    print("\n--- one node per control, in both views ---")
    check("no duplicate ids in Scope", p.evaluate(DUPES) == [], str(p.evaluate(DUPES)))

    p.locator("#viewBench").click(); p.wait_for_timeout(400)
    check("no duplicate ids in Bench", p.evaluate(DUPES) == [], str(p.evaluate(DUPES)))

    moved = p.evaluate("""() => {
      const inBench = document.querySelectorAll('#benchBody > .menu-group').length;
      const inSide = document.querySelectorAll('#benchSide > .menu-group').length;
      const inPanel = document.querySelectorAll('#menuPanel > .menu-group').length;
      return { inBench, inSide, inPanel, total: settingsGroups().length };
    }""")
    check("every group moved, none left behind",
          moved["inBench"] + moved["inSide"] == moved["total"] and moved["inPanel"] == 0,
          str(moved))
    check("and the oscillators went to the side column, not the body",
          moved["inSide"] == 1, str(moved))

    p.locator("#viewScope").click(); p.wait_for_timeout(300)
    back = p.evaluate("""() => ({
      inBench: document.querySelectorAll('#benchBody > .menu-group').length,
      inPanel: document.querySelectorAll('#menuPanel > .menu-group').length,
      allShown: settingsGroups().every((g) => !g.hidden || g.dataset.off !== undefined),
    })""")
    check("and every group comes back", back["inPanel"] > 0 and back["inBench"] == 0, str(back))
    check("with none left hidden by the rail", back["allShown"], str(back))
    check("still no duplicates after a round trip", p.evaluate(DUPES) == [])

    print("\n--- the rail ---")
    p.locator("#viewBench").click(); p.wait_for_timeout(400)
    rail = p.evaluate("""() => ({
      titles: Array.from(document.querySelectorAll('#benchRail button')).map((b) => b.textContent),
      inBody: settingsGroups().filter(
        (g) => !g.hidden && g.parentElement === el.benchBody).length,
      modShown: !el.lfoGroup.hidden && el.lfoGroup.dataset.off === undefined,
    })""")
    print("    sections:", ", ".join(rail["titles"]))
    check("a button per available section", len(rail["titles"]) >= 6, str(len(rail["titles"])))
    check("exactly one body section on show", rail["inBody"] == 1, str(rail["inBody"]))
    check("Modulation is not one of the rail's sections",
          "Modulation" not in rail["titles"], str(rail["titles"]))
    check("it is on show beside them instead", rail["modShown"], str(rail))

    # Every section, in turn: the one named is the one shown.
    wrong = p.evaluate("""() => {
      const bad = [];
      const buttons = Array.from(document.querySelectorAll('#benchRail button'));
      for (const button of buttons) {
        button.click();
        const shown = settingsGroups().filter(
          (g) => !g.hidden && g.parentElement === el.benchBody);
        // Whichever section is picked, the oscillators stay up.
        if (shown.length !== 1 || groupTitle(shown[0]) !== button.textContent
            || el.lfoGroup.hidden) {
          bad.push(button.textContent + ' -> ' + shown.map(groupTitle).join(','));
        }
      }
      return bad;
    }""")
    check("each rail button shows its own section", wrong == [], str(wrong))

    print("\n--- the controls still work from the bench ---")
    live = p.evaluate("""() => {
      // Pick the Trigger section and drive a control that lives in it.
      const buttons = Array.from(document.querySelectorAll('#benchRail button'));
      const trig = buttons.find((b) => b.textContent === 'Trigger');
      if (trig) trig.click();
      el.holdoff.value = '30';
      el.holdoff.dispatchEvent(new Event('input'));
      const a = state.holdoffMs;

      const vert = buttons.find((b) => b.textContent === 'Vertical');
      if (vert) vert.click();
      el.lagOn.checked = true;
      el.lagOn.dispatchEvent(new Event('change'));
      const b = { lag: state.lagOn, lanes: laneCount() };

      el.lagOn.checked = false; el.lagOn.dispatchEvent(new Event('change'));
      el.holdoff.value = '0'; el.holdoff.dispatchEvent(new Event('input'));
      return { holdoff: a, lag: b };
    }""")
    check("a slider in the bench drives its state", live["holdoff"] == 3.0, str(live["holdoff"]))
    check("and a checkbox does too",
          live["lag"]["lag"] is True and live["lag"]["lanes"] == 2, str(live["lag"]))

    print("\n--- the trace is live in the square ---")
    # Not "do the pixels change": a locked trigger holds the waveform still on
    # purpose, so an unchanged canvas is the instrument working. What is worth
    # asserting is that the screen really moved into the bench, that it is
    # square, that there is a trace drawn on it, and that the loop is running.
    strip = p.evaluate("""() => {
      const c = el.trace, ctx = c.getContext('2d');
      const px = ctx.getImageData(0, 0, c.width, c.height).data;
      const paper = getComputedStyle(document.documentElement)
        .getPropertyValue('--paper').trim();
      const n = parseInt(paper.slice(1), 16);
      const pr = (n >> 16) & 255, pg = (n >> 8) & 255, pb = n & 255;
      let inked = 0;
      for (let i = 0; i < px.length; i += 4) {
        if (Math.abs(px[i] - pr) + Math.abs(px[i+1] - pg) + Math.abs(px[i+2] - pb) > 18) inked++;
      }
      return { inked, pixels: px.length / 4, height: c.getBoundingClientRect().height,
               fps: state.fps };
    }""")
    p.evaluate("() => setView('scope')"); p.wait_for_timeout(400)
    scope_home = p.evaluate("""() => ({
      parent: el.traceSheet.parentElement.id,
      height: el.trace.getBoundingClientRect().height,
      screenShown: getComputedStyle(document.querySelector('.screen')).display,
    })""")
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(400)
    bench_home = p.evaluate("""() => {
      const box = el.traceSheet.getBoundingClientRect();
      return {
        parent: el.traceSheet.parentElement.id,
        w: box.width, h: box.height,
        screenShown: getComputedStyle(document.querySelector('.screen')).display,
      };
    }""")
    check("the screen is one canvas, moved rather than copied",
          p.evaluate("() => document.querySelectorAll('#trace').length") == 1)
    check("in Scope it lives in the panes", scope_home["parent"] == "panes",
          scope_home["parent"])
    check("in Bench it lives in the square", bench_home["parent"] == "benchScope",
          bench_home["parent"])
    check("and the full-height screen is gone rather than squeezed",
          bench_home["screenShown"] == "none" and scope_home["screenShown"] != "none",
          "%s / %s" % (bench_home["screenShown"], scope_home["screenShown"]))
    check("the bench screen is square",
          abs(bench_home["w"] - bench_home["h"]) <= 1,
          "%.0f x %.0f" % (bench_home["w"], bench_home["h"]))
    check("and smaller than the one it replaced",
          bench_home["h"] < scope_home["height"] * 0.75,
          "%.0f px in bench vs %.0f in scope" % (bench_home["h"], scope_home["height"]))
    check("still has a trace drawn on it", strip["inked"] > 500,
          "%d inked pixels of %d" % (strip["inked"], strip["pixels"]))
    check("at a real frame rate", strip["fps"] > 20, "%.0f fps" % strip["fps"])

    print("\n--- the oscillators survive a source that has no generator ---")
    # They used to be switched off wholesale on anything but the test tone,
    # which was right while every destination they had was a generator
    # parameter. It is wrong now: an LFO on the filter cutoff or the rotation
    # is the same patch whatever the signal came from. What withdraws on a
    # live source is the generator half of the DESTINATION list, per entry.
    mod = p.evaluate("""() => {
      showSource('mic');                       // just the panel, no stream
      const live = {
        off: el.lfoGroup.dataset.off,
        hidden: el.lfoGroup.hidden,
        rate: !!document.getElementById('lfoRate0'),
        genDead: Array.from(document.getElementById('lfoDest0').options)
          .filter((o) => o.value.startsWith('gen.')).every((o) => o.disabled),
        viewAlive: Array.from(document.getElementById('lfoDest0').options)
          .filter((o) => o.value.startsWith('view.')).every((o) => !o.disabled),
      };
      showSource(null);
      const tone = {
        genAlive: Array.from(document.getElementById('lfoDest0').options)
          .filter((o) => o.value.startsWith('gen.')).every((o) => !o.disabled),
      };
      return { live, tone };
    }""")
    check("the oscillators stay on a live source",
          mod["live"]["off"] is None and mod["live"]["hidden"] is False, str(mod["live"]))
    check("with their rate and depth still reachable", mod["live"]["rate"])
    check("generator destinations grey out instead", mod["live"]["genDead"], str(mod["live"]))
    check("while the ones that apply stay live", mod["live"]["viewAlive"], str(mod["live"]))
    check("and the generator's come back with the tone", mod["tone"]["genAlive"],
          str(mod["tone"]))

    print("\n--- the view is remembered ---")
    p.reload(); p.wait_for_timeout(900)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    kept = p.evaluate("() => document.body.dataset.view")
    check("bench survives a reload", kept == "bench", kept)
    check("no errors after reload", not bad, "; ".join(bad[:3]))
    p.screenshot(path=f"{SHOTS}/bench-wide.png")

    print("\n--- narrow ---")
    p.set_viewport_size({"width": 430, "height": 900}); p.wait_for_timeout(500)
    narrow = p.evaluate("""() => ({
      overflow: document.documentElement.scrollWidth > window.innerWidth,
      railRow: getComputedStyle(el.benchRail).flexDirection,
    })""")
    check("no sideways overflow on a phone", narrow["overflow"] is False)
    check("the rail becomes a row", narrow["railRow"] == "row", narrow["railRow"])
    p.screenshot(path=f"{SHOTS}/bench-narrow.png", full_page=True)

    p.set_viewport_size({"width": 1400, "height": 900}); p.wait_for_timeout(300)
    p.evaluate("() => setView('scope')")
    check("no page errors across the run", not bad, "; ".join(bad[:4]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all bench checks pass")
