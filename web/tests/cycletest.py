"""G2's drawn cycle: one period drawn with the pointer, played as a wavetable.

Against the way it would fail:

- tables that are not the drawing: a drawn sine is a sine in every table,
  and a drawn square's harmonics are the square's, with its third a third of
  its fundamental;
- tables that are not band-limited: each holds nothing above its share of
  the harmonics - all of them, then half, a quarter, down to the fundamental
  - measured with numpy's FFT, not the page's;
- a note that changes level or clicks as it climbs: every table is scaled
  alike, so the fundamental is the same in each, and at the pitch where one
  table hands over to the next the sound does not step;
- a pane that does not draw what it is given: a square drawn with the mouse
  is a square in the points, the tables sent are the tables of those points,
  and the generator's own output is that cycle at the pitch it is playing;
- Sine and Smooth that do something else: Sine is a sine again, Smooth
  softens the corners without moving the middle;
- a code that loses it: the points come back within a byte's precision, a
  sine says nothing, and a code without one draws a sine.
"""
import math, os
import numpy as np
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
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    print("\n--- the tables ---")
    t = p.evaluate("""() => {
      const sine = cycleTables(Array.from({ length: CYCLE_POINTS }, (_, i) => Math.sin(2 * Math.PI * i / CYCLE_POINTS)));
      const square = cycleTables(Array.from({ length: CYCLE_POINTS }, (_, i) => i < CYCLE_POINTS / 2 ? 0.9 : -0.9));
      let sineOff = 0;
      for (const table of sine.levels) table.forEach((v, i) => { sineOff = Math.max(sineOff, Math.abs(v - Math.sin(2 * Math.PI * i / table.length))); });
      return { sineOff, most: square.most, square: square.levels, points: CYCLE_POINTS, size: CYCLE_TABLE };
    }""")
    check("a drawn sine is a sine in every table", t["sineOff"] < 1e-9, "%.2e" % t["sineOff"])
    levels = [np.asarray(l) for l in t["square"]]
    limits = [t["most"] >> k for k in range(len(levels))]
    spectra = [np.abs(np.fft.rfft(l)) / (len(l) / 2) for l in levels]
    above = max(20 * math.log10(max(s[lim + 1:].max(), 1e-15) / s[1]) for s, lim in zip(spectra, limits))
    print("    %d tables of %d points, holding %s harmonics; the most above any table's share: %.1f dB"
          % (len(levels), t["size"], limits, above))
    check("each table holds nothing above its share of the harmonics - all, half, a quarter, down to the fundamental",
          len(levels) == 8 and limits == [128, 64, 32, 16, 8, 4, 2, 1] and above < -200,
          "%s, %.1f dB" % (limits, above))
    s0 = spectra[0]
    check("a drawn square's harmonics are the square's: odd only, the third a third of the fundamental",
          abs(s0[3] / s0[1] - 1 / 3) < 0.01 and s0[2] / s0[1] < 1e-9 and abs(s0[5] / s0[1] - 1 / 5) < 0.01,
          "3rd %.4f, 2nd %.1e, 5th %.4f" % (s0[3] / s0[1], s0[2] / s0[1], s0[5] / s0[1]))
    funds = [s[1] for s in spectra]
    check("every table is scaled alike, so the fundamental is the same in each and the richest peaks at one",
          max(funds) - min(funds) < 1e-9 and abs(max(abs(levels[0])) - 1) < 1e-12,
          "fundamentals %.6f to %.6f, peak %.6f" % (min(funds), max(funds), max(abs(levels[0]))))

    hand = p.evaluate("""() => {
      const tables = cycleTables(Array.from({ length: CYCLE_POINTS }, (_, i) => i < CYCLE_POINTS / 2 ? 0.9 : -0.9));
      // At the step where table k's top harmonic would reach Nyquist, on
      // either side of it, at phases round the cycle.
      let worst = 0, far = 0;
      for (let k = 0; k < 7; k++) {
        const step = 0.5 / (tables.most >> k);
        for (let j = 0; j < 64; j++) {
          const ph = j / 64 * TWO_PI + 0.01;
          const below = waveAt('drawn', ph, step * (1 - 1e-7), tables), above = waveAt('drawn', ph, step * (1 + 1e-7), tables);
          worst = Math.max(worst, Math.abs(below - above));
          far = Math.max(far, Math.abs(waveAt('drawn', ph, step * 0.6, tables) - waveAt('drawn', ph, step * 1.6, tables)));
        }
      }
      return { worst, far };
    }""")
    check("where one table hands over to the next the sound does not step, though tables apart it differs",
          hand["worst"] < 1e-5 and hand["far"] > 0.01, "%.2e at the hand-over; %.3f tables apart" % (hand["worst"], hand["far"]))

    # Layer B plays the page's one drawn cycle: its picture with the drawn
    # shape is not a sine's, which is what it drew when it could not see the
    # tables.
    layer = p.evaluate("""() => {
      const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
      const square = cycleTables(Array.from({ length: CYCLE_POINTS }, (_, i) => i < CYCLE_POINTS / 2 ? 0.9 : -0.9));
      const run = (shapeB) => {
        const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
        core.set('cycle', square);
        core.set('voices', [{ note: 57, freq: 220, velocity: 1, role: 'xy' }]);
        core.set('voices', [{ note: 69, freq: 440, velocity: 1, role: 'xy' }], 1);
        core.set('shape', shapeB, 1);
        const n = 8820, L = new Float32Array(n), R = new Float32Array(n), BL = new Float32Array(n), BR = new Float32Array(n);
        core.block(L, R, n, null, null, BL, BR);
        return BL;
      };
      const drawn = run('drawn'), sine = run('sine');
      let most = 0, loud = 0;
      for (let i = 0; i < drawn.length; i++) { most = Math.max(most, Math.abs(drawn[i] - sine[i])); loud = Math.max(loud, Math.abs(drawn[i])); }
      return { most, loud };
    }""")
    check("layer B plays the page's drawn cycle, not a sine", layer["most"] > 0.05 and layer["loud"] > 0.05,
          "differs from a sine by %.3f" % layer["most"])

    print("\n--- the pane, and what the generator plays ---")
    p.evaluate("""() => { el.shape.value = 'drawn'; el.shape.dispatchEvent(new Event('change'));
                          el.freq.value = '55'; el.freq.dispatchEvent(new Event('input')); showControl('cycleCanvas'); }""")
    p.wait_for_timeout(300)
    box = p.evaluate("() => { const r = el.cycleCanvas.getBoundingClientRect(); return [r.left, r.top, r.width, r.height, !el.cycleGroup.hidden, !el.cycleGoRow.hidden]; }")
    x, y, w, h = box[:4]
    p.mouse.move(x + 1, y + 2); p.mouse.down(); p.mouse.move(x + w / 2 - 1, y + 2, steps=12)
    p.mouse.move(x + w / 2 + 1, y + h - 2, steps=2); p.mouse.move(x + w - 1, y + h - 2, steps=12); p.mouse.up()
    p.wait_for_timeout(400)
    drawn = p.evaluate("""() => {
      const pts = drawnCycle.points;
      const sent = JSON.stringify(genSettings().cycle) === JSON.stringify(cycleTables(pts));
      const rate = state.source.sampleRate, hz = genSettings().freq, step = hz / rate;
      const n = Math.round(rate / hz) * 4;
      const got = Array.from(state.source.getLatestWindow(n)[0]);
      const want = [];
      for (let i = 0; i < n; i++) want.push(waveAt('drawn', TWO_PI * i * step, step, drawnCycle.tables));
      return { first: pts.slice(8, 120), second: pts.slice(136, 248), sent, got, want };
    }""")
    check("the pane shows with the drawn cycle chosen, and a square drawn with the mouse is a square in the points",
          box[4] and box[5] and min(drawn["first"]) > 0.9 and max(drawn["second"]) < -0.9,
          "%.2f..%.2f then %.2f..%.2f" % (min(drawn["first"]), max(drawn["first"]), min(drawn["second"]), max(drawn["second"])))
    check("the tables the generator is sent are the tables of those points", drawn["sent"], str(drawn["sent"]))
    got, want = np.asarray(drawn["got"]), np.asarray(drawn["want"])
    got, want = got - got.mean(), want - want.mean()
    xc = np.fft.irfft(np.fft.rfft(got) * np.conj(np.fft.rfft(want)))
    corr = xc.max() / (np.linalg.norm(got) * np.linalg.norm(want))
    check("and what the generator plays is that cycle at its pitch, whatever its phase",
          corr > 0.995, "correlation %.4f" % corr)

    print("\n--- Sine, Smooth, and the code ---")
    tools = p.evaluate("""() => {
      const jump = (p) => Math.max(...p.map((v, i) => Math.abs(p[(i + 1) % p.length] - v)));
      const mean = (p) => p.reduce((s, v) => s + v, 0) / p.length;
      const before = drawnCycle.points.slice();
      el.cycleSmooth.click();
      const n = before.length;
      const rule = Math.max(...drawnCycle.points.map((v, i) => Math.abs(v - (before[(i + n - 1) % n] + 2 * before[i] + before[(i + 1) % n]) / 4)));
      const smooth = { jump: [jump(before), jump(drawnCycle.points)], mean: [mean(before), mean(drawnCycle.points)], rule };
      const code = snapshot().cycle;
      const decoded = decodeCycle(code);
      // A code that decodes to nothing fails here by name, not with a throw.
      const worst = decoded ? Math.max(...decoded.map((v, i) => Math.abs(v - drawnCycle.points[i]))) : 99;
      const kept = drawnCycle.points.slice();
      restore({});
      const bare = Math.max(...drawnCycle.points.map((v, i) => Math.abs(v - Math.sin(2 * Math.PI * i / CYCLE_POINTS))));
      restore({ cycle: code });
      const back = Math.max(...drawnCycle.points.map((v, i) => Math.abs(v - kept[i])));
      // A new generator, built from the panel, is given the drawn cycle too:
      // away to a file and back to the tone.
      const rate = 44100, nn = rate / 4, bytes = 44 + nn * 2, buf = new ArrayBuffer(bytes), dv = new DataView(buf);
      const str = (o, t) => { for (let i = 0; i < t.length; i++) dv.setUint8(o + i, t.charCodeAt(i)); };
      str(0, 'RIFF'); dv.setUint32(4, bytes - 8, true); str(8, 'WAVE'); str(12, 'fmt '); dv.setUint32(16, 16, true);
      dv.setUint16(20, 1, true); dv.setUint16(22, 1, true); dv.setUint32(24, rate, true); dv.setUint32(28, rate * 2, true);
      dv.setUint16(32, 2, true); dv.setUint16(34, 16, true); str(36, 'data'); dv.setUint32(40, nn * 2, true);
      return (async () => {
      await toFile(new File([buf], 'x.wav', { type: 'audio/wav' }));
      el.srcTone.click(); await new Promise((r) => setTimeout(r, 300));
      const fresh = state.source.kind === 'tone' && JSON.stringify(genSettings().cycle) === JSON.stringify(drawnCycle.tables);
      el.cycleSine.click();
      const sine = Math.max(...drawnCycle.points.map((v, i) => Math.abs(v - Math.sin(2 * Math.PI * i / CYCLE_POINTS))));
      return { smooth, codeLength: code.length, worst, bare, back, sine, sineCode: snapshot().cycle, fresh };
      })();
    }""")
    print("    %s" % tools)
    # Held to its rule rather than to a guess at how much it softens: the
    # first version asked for the largest step to fall under six tenths, and a
    # drawn edge the mouse had already put a point in the middle of fell to 0.62.
    check("Smooth is each point to (left + 2 itself + right) / 4 round the cycle: corners softer, the middle unmoved",
          tools["smooth"]["rule"] < 1e-12 and tools["smooth"]["jump"][1] < tools["smooth"]["jump"][0]
          and abs(tools["smooth"]["mean"][1] - tools["smooth"]["mean"][0]) < 1e-12,
          "off the rule by %.1e; largest step %.3f to %.3f" % (tools["smooth"]["rule"], tools["smooth"]["jump"][0], tools["smooth"]["jump"][1]))
    check("a code carries the points to a byte's precision, a code without one draws a sine, and it comes back",
          tools["codeLength"] == 344 and tools["worst"] <= 0.5 / 127 + 1e-12 and tools["bare"] < 1e-12
          and tools["back"] <= 0.5 / 127 + 1e-12, "%d characters, worst %.4f" % (tools["codeLength"], tools["worst"]))
    check("a new generator built from the panel is given the drawn cycle", tools["fresh"], str(tools["fresh"]))
    check("Sine is a sine again, and a sine says nothing in a code", tools["sine"] < 1e-12 and tools["sineCode"] == "",
          "%.2e, %r" % (tools["sine"], tools["sineCode"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
