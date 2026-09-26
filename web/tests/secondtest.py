"""Stage L's second generator: a figure beside the first, drawn on lanes three
and four, and the one input that needs no device.

Against the way it would fail:

- a second generator that is not its figure: its pair, sample for sample, is
  the square at its rate and size, computed here on its own;
- one that leaks when it should not: taken live with no device, or with the
  mode off, the first generator draws exactly what it draws alone;
- modulation that is not what J3's modes mean: FM makes the first's trace
  run at its rate times (1 + 4 depth x) sample by sample, a ride scales every
  sample by (1 + 2 depth x), and a clock holds the first still at the second's
  period - each against a reference built here, not against the page;
- modulation the wrong way round: nothing about the first changes the second;
- a page that offers the wrong lanes or asks for a device: choosing it opens
  nothing, offers four lanes named for what they are and draws two figures;
  the layers take lanes three and four when they want them and say so; off
  the test tone its rows are gone; and a code carries it.
"""
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

# A core off the page, run for n samples with the settings given; lane one,
# lane two, and the second generator's pair.
CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('amp', 0.4); core.set('shape', 'sine'); core.set('interval', 0);
  for (const k in setup.tone) core.set(k, setup.tone[k]);
  const n = setup.n, L = new Float32Array(n), R = new Float32Array(n), BL = new Float32Array(n), BR = new Float32Array(n);
  core.block(L, R, n, null, null, BL, BR);
  return { L: Array.from(L), R: Array.from(R), BL: Array.from(BL), BR: Array.from(BR) };
}"""

STUB = """
  window.__asked = 0;
  navigator.mediaDevices.getUserMedia = () => { window.__asked++; return Promise.reject(new Error('none')); };
  window.__wait = (ms) => new Promise((r) => setTimeout(r, ms));
"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.add_init_script(STUB)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    run = lambda tone, n=8820: p.evaluate(CORE, {"tone": tone, "n": n})
    most = lambda a, c: max(abs(x - y) for x, y in zip(a, c))
    FIG = {"mode": "figure", "figure": "Circle", "figureRate": 40}
    SECOND = {"inputFrom": "gen2", "gen2Figure": "Square", "gen2Rate": 90, "gen2Amp": 0.5}

    print("\n--- the second generator itself ---")
    ref = p.evaluate("""() => {
      let ph = 0; const bl = [], br = [];
      for (let i = 0; i < 8820; i++) {
        ph += 90 / 44100; if (ph >= 1) ph -= Math.floor(ph);
        const at = figureAt('Square', ph, 5, null); bl.push(0.5 * at[0]); br.push(0.5 * at[1]);
      }
      return { bl, br };
    }""")
    alone = run(dict(FIG, **SECOND, inputMode=0))
    check("its pair is its figure, at its rate and size, sample for sample",
          most(alone["BL"], ref["bl"]) < 1e-6 and most(alone["BR"], ref["br"]) < 1e-6 and max(map(abs, alone["BL"])) > 0.45,
          "%.2e, %.2e" % (most(alone["BL"], ref["bl"]), most(alone["BR"], ref["br"])))

    plain = run(FIG)
    live = run(dict(FIG, gen2Figure="Square", gen2Rate=90, inputFrom="live", inputMode=1))
    check("taken live with no device, or with the mode off, the first draws exactly what it draws alone, and lanes three and four are silent when live",
          most(plain["L"], live["L"]) == 0 and most(plain["L"], alone["L"]) == 0 and max(map(abs, live["BL"])) == 0,
          "%.2e, %.2e" % (most(plain["L"], live["L"]), most(plain["L"], alone["L"])))

    print("\n--- what it does to the first ---")
    d = 0.5
    fm = run(dict(FIG, **SECOND, inputMode=1, inputDepth=d))
    fmref = p.evaluate("""([bl, d]) => {
      let ph = 0; const out = [];
      for (let i = 0; i < bl.length; i++) {
        ph += 40 * Math.max(0, 1 + d * 4 * bl[i]) / 44100; if (ph >= 1) ph -= 1;
        out.push(0.4 * figureAt('Circle', ph, 5)[0]);
      }
      return out;
    }""", [alone["BL"], d])
    check("FM runs the first's trace at its rate times (1 + 4 depth x), sample by sample",
          most(fm["L"], fmref) < 1e-5 and most(fm["L"], plain["L"]) > 0.1,
          "%.2e from the reference; %.3f from plain" % (most(fm["L"], fmref), most(fm["L"], plain["L"])))
    ride = run(dict(FIG, **SECOND, inputMode=2, inputDepth=d))
    rideref = [pl * (1 + 2 * d * x) for pl, x in zip(plain["L"], alone["BL"])]
    check("a ride scales every sample of the first by (1 + 2 depth x)",
          most(ride["L"], rideref) < 1e-6 and most(ride["L"], plain["L"]) > 0.05, "%.2e" % most(ride["L"], rideref))
    P = 441
    clocked = run(dict(FIG, inputFrom="gen2", gen2Figure="Circle", gen2Rate=100, gen2Amp=0.5, inputMode=3), 17640)
    lock = most(clocked["L"][4410:-P], clocked["L"][4410 + P:])
    loose = most(plain["L"][2000:-P], plain["L"][2000 + P:])
    check("a clock from it holds the first still at its period: 100 Hz, so every 441 samples",
          lock < 1e-6 and loose > 0.1, "%.2e against %.3f" % (lock, loose))
    other = run(dict(FIG, **SECOND, inputMode=1, inputDepth=d, figureRate=150, figure="Star", amp=0.9))
    check("and only that way round: nothing about the first changes the second",
          most(other["BL"], alone["BL"]) == 0 and most(other["BR"], alone["BR"]) == 0,
          "%.2e" % most(other["BL"], alone["BL"]))

    print("\n--- on the page ---")
    page = p.evaluate("""async () => {
      const out = {};
      el.genMode.value = 'figure'; el.genMode.dispatchEvent(new Event('change'));
      el.inputFrom.value = 'gen2'; el.inputFrom.dispatchEvent(new Event('change'));
      el.gen2Figure.value = 'Square'; el.gen2Figure.dispatchEvent(new Event('change'));
      // Its rate slider reaches the core, and goes back where it was.
      el.gen2Rate.value = '250'; el.gen2Rate.dispatchEvent(new Event('input'));
      out.rate = [genSettings().gen2Rate, el.gen2RateValue.textContent];
      el.gen2Rate.value = '110'; el.gen2Rate.dispatchEvent(new Event('input'));
      await __wait(400);
      const w = state.source.getLatestWindow(4410);
      out.on = { rows: !el.gen2Rows.hidden, asked: __asked, lanes: state.source.channels, names: state.source.laneNames(),
                 figures: state.source.figures(), where: el.inputWhere.textContent,
                 onSquare: w[2].every((x, i) => Math.abs(Math.max(Math.abs(x), Math.abs(w[3][i])) - 0.5) < 1e-3) };
      /* The layers want lanes three and four, and have them - which takes
         real layers: a waveform, poly, and a keyboard, here the one on the
         screen. With a figure and no keyboard the layers are off whatever
         their switch says, and the second generator rightly keeps its lanes;
         the first version of this check asked that of them and failed. */
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      if (el.keysOpen.getAttribute('aria-expanded') !== 'true') el.keysOpen.click();
      midi.mode = 'poly'; midi.layers.mode = 'split'; syncMidi(); syncLayers(); await __wait(200);
      out.layers = { on: layersOn(), names: state.source.laneNames(), where: el.inputWhere.textContent };
      midi.layers.mode = 'off'; midi.mode = 'dyad'; syncMidi(); syncLayers(); await __wait(200);
      out.after = state.source.laneNames();
      if (el.keysOpen.getAttribute('aria-expanded') === 'true') el.keysOpen.click();
      el.genMode.value = 'figure'; el.genMode.dispatchEvent(new Event('change'));
      const code = snapshot();
      out.code = [code.inputFrom, code.gen2Figure, code.gen2Rate];
      restore({}); await __wait(150);
      out.bare = { from: genInput.from, lanes: state.source.channels, rows: !el.gen2Rows.hidden };
      restore(code); await __wait(150);
      out.back = { from: genInput.from, lanes: state.source.channels, figure: genSettings().gen2Figure };
      el.inputFrom.value = 'live'; el.inputFrom.dispatchEvent(new Event('change'));
      await __wait(150);
      out.off = { rows: !el.gen2Rows.hidden, lanes: state.source.channels };
      return out;
    }""")
    print("    %s" % page)
    check("choosing it opens no device, shows its rows, and offers four lanes named for what they are, as two figures",
          page["on"]["asked"] == 0 and page["on"]["rows"] and page["on"]["lanes"] == 4
          and page["on"]["names"] == ["X", "Y", "Second · X", "Second · Y"]
          and page["on"]["figures"] == [[0, 1], [2, 3]]
          and page["on"]["where"] == "The second generator, not into the first yet. Drawn on lanes three and four.",
          str(page["on"]))
    check("its rate slider reaches the core", page["rate"] == [250, "250 Hz"], str(page["rate"]))
    check("and lanes three and four are its square, at its size", page["on"]["onSquare"], str(page["on"]["onSquare"]))
    check("the layers take lanes three and four when they want them, and the note says so; off again, they are the second generator's",
          page["layers"]["on"] is True and page["layers"]["names"] == ["A · X", "A · Y", "B · X", "B · Y"]
          and "Not drawn while the keyboard is split or layered" in page["layers"]["where"]
          and page["after"] == ["X", "Y", "Second · X", "Second · Y"], str(page["layers"]))
    check("a code carries it, a code without it takes the input live, and it comes back",
          page["code"] == ["gen2", "Square", 110] and page["bare"] == {"from": "live", "lanes": 2, "rows": False}
          and page["back"] == {"from": "gen2", "lanes": 4, "figure": "Square"}, "%s / %s / %s" % (page["code"], page["bare"], page["back"]))
    check("choosing your input again takes its rows and lanes away", page["off"] == {"rows": False, "lanes": 2}, str(page["off"]))

    rack = p.evaluate("""async () => {
      el.inputFrom.value = 'gen2'; el.inputFrom.dispatchEvent(new Event('change'));
      const rate = 44100, n = rate / 4, bytes = 44 + n * 2, buf = new ArrayBuffer(bytes), v = new DataView(buf);
      const str = (o, t) => { for (let i = 0; i < t.length; i++) v.setUint8(o + i, t.charCodeAt(i)); };
      str(0, 'RIFF'); v.setUint32(4, bytes - 8, true); str(8, 'WAVE'); str(12, 'fmt '); v.setUint32(16, 16, true);
      v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true);
      v.setUint16(32, 2, true); v.setUint16(34, 16, true); str(36, 'data'); v.setUint32(40, n * 2, true);
      await toFile(new File([buf], 'x.wav', { type: 'audio/wav' }));
      await __wait(200);
      const out = { rows: !el.gen2Rows.hidden, where: el.inputWhere.textContent };
      el.srcTone.click(); await __wait(300);
      out.backRows = !el.gen2Rows.hidden;
      // The tone just built is a new generator, made from the panel: it has to
      // be told where its input comes from.
      out.fresh = genSettings().inputFrom;
      /* Heard, a live input would open the device; from the second generator
         nothing is opened, whatever the mode. */
      el.inputMode.value = '1'; el.inputMode.dispatchEvent(new Event('change'));
      state.genSound = true; await applyGeneratorSound(); await __wait(600);
      out.heard = { asked: __asked, where: el.inputWhere.textContent };
      state.genSound = false; await applyGeneratorSound();
      el.inputMode.value = '0'; el.inputMode.dispatchEvent(new Event('change'));
      el.inputFrom.value = 'live'; el.inputFrom.dispatchEvent(new Event('change'));
      return out;
    }""")
    check("a new generator built from the panel takes its input from the second generator too",
          rack["fresh"] == "gen2", str(rack["fresh"]))
    check("and heard, with the input from the second generator, no device is asked for",
          rack["heard"]["asked"] == 0 and rack["heard"]["where"].startswith("The second generator, into the first"),
          str(rack["heard"]))
    check("off the test tone its rows are gone and the note says where it works; back on the tone they return",
          rack["rows"] is False and rack["where"].startswith("On the test tone only") and rack["backRows"] is True, str(rack))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
