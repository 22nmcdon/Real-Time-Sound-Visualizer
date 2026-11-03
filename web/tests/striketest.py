"""P7b: notes strike the screen, each hand can read the other's picture, and
the loop keeps going on its own.

Three things Scan gained after it was built (scantest.py holds Scan itself):

- The strike. Every note lays light on the phosphor as it starts, an arc of
  the circle Scan reads, at the note's place round it, as bright as the
  note's velocity times the Strike amount; it is light like any other and
  fades by the screen's Persistence. Checked against the way it would fail:
  nought (or Scan off) that lays anything at all, a level that is not
  velocity times Strike, light laid somewhere Scan does not read, every note
  struck in one place, a hard note no brighter a tone than a soft one, an
  envelope of its own instead of the phosphor's fade, the meters blind to
  it, and in a split a note struck on the wrong layer's picture.
- Cross-scan. A menu a layer, as P6's pictures have: what that layer's Scan
  reads, its own picture, the other's, or both averaged. Checked: the table
  a layer plays is made from exactly the picture its menu names and not its
  own, both is the average, a crossed pair's depths are held by the lower
  of the two holds and an uncrossed one's each by its own, the menus round a
  setup code and refuse what they do not offer, and the row is shown only
  when there are two pictures.
- The loop that keeps going: presets in which the keys strike the screen
  rather than start the sound, so letting go leaves the loop running. The
  nulls are Stop, which holds the screen and so the tone, and the same
  preset with notes driving the waveform, which falls silent on release.

Run on the page's own brain (`?brain=js&core=js`): the strike and the
cross-reading are the page's until the core learns them, and the site's
instrument reads its own grid. Every assertion has its null beside it.
"""
import math, os, statistics, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    """A check's null: the same comparison fed a value it must reject."""
    check("null: " + name, red, detail)


def centroid(table):
    """The table's harmonic centroid: where its energy sits, in harmonics."""
    h = np.abs(np.fft.rfft(np.asarray(table, dtype=float)))[1:65] ** 2
    return float((np.arange(1, 65) * h).sum() / h.sum())


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html?brain=js&core=js"); p.wait_for_timeout(900)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    # ------------------------------------------------------------------
    print("\n--- the strike ---")
    # Everything here is synchronous with the screen stopped, so no frame
    # draws, fades or reads between a note and what it laid.
    s = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      applyPreset('b:Scanned fifth'); await wait(1500);
      setScreenKeys(true);
      setRunning(false); await wait(100);
      const g = pictureEngine.cells, base = Float32Array.from(g);
      const grew = () => { let m = 0; for (let i = 0; i < g.length; i++) m = Math.max(m, g[i] - base[i]); return m; };
      const strike = (n) => { el.scanStrike.value = String(n); el.scanStrike.dispatchEvent(new Event('input')); };
      const out = {};
      // Nought, and Scan off.
      strike(0); midiNoteOn(60, 127); out.nought = grew(); midiNoteOff(60); g.set(base);
      strike(50); el.oscScan.value = '0'; el.oscScan.dispatchEvent(new Event('input'));
      midiNoteOn(60, 127); out.scanOff = grew(); midiNoteOff(60); g.set(base);
      el.oscScan.value = '100'; el.oscScan.dispatchEvent(new Event('input'));
      midiNoteOn(60, 127); out.on = grew(); midiNoteOff(60); g.set(base);
      out.reading = el.scanStrikeValue.textContent;

      // On a dark screen: the level, the place round the circle, and that
      // it is where Scan reads.
      pictureEngine.blank();
      const dark = Float32Array.from(g);
      const path = { cx: 0.5, cy: 0.5, r: 0.25 };
      scan.paths[0] = path;
      // Read unblurred: the softness spreads a one-cell arc over seven,
      // which would hide where it lies under how wide the blur is.
      const read = () => Array.from(scanRead(g, path, 0));
      const r0 = read();
      midiNoteOn(60, 100); out.level = Math.max(...g); const rC = read(); midiNoteOff(60); g.set(dark);
      midiNoteOn(66, 100); const rF = read(); midiNoteOff(60); midiNoteOff(66); g.set(dark);
      // The same light laid as a stroke through the figure's own centre.
      const cx = plot.x + 0.5 * plot.w, cy = plot.y + 0.5 * plot.h;
      pictureEngine.segment(plot, cx - 0.05 * plot.w, cy, cx + 0.05 * plot.w, cy, out.level);
      const rM = read(); g.set(dark);
      out.rise = { C: rC.map((v, i) => v - r0[i]), F: rF.map((v, i) => v - r0[i]), centre: rM.map((v, i) => v - r0[i]) };

      // A soft and a hard note on the picture as it was: the tables.
      g.set(base); scan.paths[0] = null; scanStep(16);
      const p0 = scan.paths[0];
      const table = () => Array.from(scanTables(scanRead(g, p0, scan.soft)).levels[0]);
      out.t0 = table();
      midiNoteOn(62, 30); out.tSoft = table(); midiNoteOff(62); g.set(base);
      midiNoteOn(62, 30); out.tSoft2 = table(); midiNoteOff(62); g.set(base);
      midiNoteOn(62, 127); out.tHard = table(); midiNoteOff(62); g.set(base);
      midiPanic(); setRunning(true);
      return out;
    }""")
    check("Strike at nought lays nothing at all", s["nought"] == 0, "grew %.3g" % s["nought"])
    check("and neither does a strike with Scan off, since there is no reading for it to be in", s["scanOff"] == 0,
          "grew %.3g" % s["scanOff"])
    null("with Scan on and Strike at half, a note lays light", s["on"] > 0.1, "grew %.3f" % s["on"])
    want = 100 / 127 * 0.5
    check("a note lays light as bright as its velocity times the Strike amount", abs(s["level"] - want) < 1e-6,
          "%.6f against %.6f" % (s["level"], want))
    null("not its velocity alone", abs(s["level"] - 100 / 127) > 0.1, "%.4f" % (100 / 127))
    rise = {k: np.asarray(v) for k, v in s["rise"].items()}
    n = len(rise["C"])
    # Where each strike sits: the circular mean of the reading's rise, since
    # unblurred the arc is a plateau and its highest point could be anywhere
    # along it.
    def place(r):
        w = np.maximum(r, 0); th = 2 * np.pi * np.arange(n) / n
        return int(round((np.arctan2((w * np.sin(th)).sum(), (w * np.cos(th)).sum()) % (2 * np.pi)) / (2 * np.pi) * n)) % n
    peakC, peakF = place(rise["C"]), place(rise["F"])
    print("    the reading rises by up to %.3f for the strike, %.3f for the same light through the figure's centre; "
          "C peaks at point %d of %d, F sharp at %d" % (rise["C"].max(), rise["centre"].max(), peakC, n, peakF))
    check("it is laid where Scan reads: the reading, unblurred, rises by over half the light it laid",
          rise["C"].max() > 0.5 * s["level"], "%.3f of %.3f" % (rise["C"].max(), s["level"]))
    null("the same light laid through the figure's centre barely reaches the reading",
         rise["centre"].max() < 0.1 * s["level"], "%.4f" % rise["centre"].max())
    dist = lambda a, b_: min(abs(a - b_), n - abs(a - b_))
    check("each note strikes its own place round the circle: C at the reading's start, F sharp half a lap on",
          dist(peakC, 0) <= n // 64 and dist(peakF, n // 2) <= n // 64, "C at %d, F sharp at %d" % (peakC, peakF))
    null("not both in one place", dist(peakC, peakF) > n // 4, "%d apart" % dist(peakC, peakF))
    d = lambda a, b_: float(np.mean(np.abs(np.asarray(a) - np.asarray(b_))))
    print("    table moved by %.4f for a soft note and %.4f for a hard one" % (d(s["tSoft"], s["t0"]), d(s["tHard"], s["t0"])))
    check("a harder note changes the next table more: over twice what a soft one does",
          d(s["tHard"], s["t0"]) > 2 * d(s["tSoft"], s["t0"]), "%.4f against %.4f" % (d(s["tHard"], s["t0"]), d(s["tSoft"], s["t0"])))
    null("the same soft note twice makes the same table", d(s["tSoft"], s["tSoft2"]) < 1e-9, "%.2g" % d(s["tSoft"], s["tSoft2"]))
    # Not "brighter": measured on three presets, a hard strike moved the
    # energy above the fundamental up on one, down on another and either way
    # on the third - a plateau on the read adds harmonics where the figure
    # had none and takes them away where it crossed bright lines. What holds
    # on every picture is how far the timbre moves, which is the check above.

    print("\n--- the strike's light fades as the screen's does ---")
    fade = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      applyPreset('b:Scanned fifth'); await wait(800);
      setScreenKeys(true);
      genSet('amp', 0);
      el.persistence.value = '0.04'; el.persistence.dispatchEvent(new Event('change'));
      await wait(300);
      pictureEngine.blank();
      scan.paths[0] = { cx: 0.5, cy: 0.5, r: 0.25 };
      midiNoteOn(60, 127); midiNoteOff(60);
      const g = pictureEngine.cells;
      let at = 0; for (let i = 0; i < g.length; i++) if (g[i] > g[at]) at = i;
      const v0 = g[at], f0 = pictureEngine.frames;
      await wait(300);
      const v1 = g[at], f1 = pictureEngine.frames;
      midiPanic(); genSet('amp', 0.55);
      return { v0, v1, frames: f1 - f0, p: state.persistence };
    }""")
    expect = fade["v0"] * (1 - fade["p"]) ** fade["frames"]
    check("the strike's light fades exactly by the screen's Persistence, frame by frame, as a stroke does",
          fade["frames"] >= 5 and abs(fade["v1"] - expect) < 1e-4 * fade["v0"],
          "%.5f after %d frames, %.5f expected" % (fade["v1"], fade["frames"], expect))
    null("not by an envelope of its own: three frames more or fewer would be another value",
         abs(fade["v1"] - fade["v0"] * (1 - fade["p"]) ** (fade["frames"] + 3)) > 1e-3 * fade["v0"])

    print("\n--- the meters see it ---")
    # On a screen with nothing else on it but the dot of a silent generator,
    # so the figure's own answer to the strike cannot move the reading: what
    # the meter lights is what the strike laid, through the real frame.
    met = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      applyPreset('b:Scanned fifth'); await wait(800);
      setScreenKeys(true);
      genSet('amp', 0);
      el.persistence.value = '0.04'; el.persistence.dispatchEvent(new Event('change'));
      await wait(400);
      const out = {};
      for (const strike of [0, 100]) {
        el.scanStrike.value = String(strike); el.scanStrike.dispatchEvent(new Event('input'));
        pictureEngine.blank(); await wait(200);
        const before = pictureMeter.lit;
        const base = Float32Array.from(pictureEngine.cells);
        for (const n of [60, 63, 66, 69]) { midiNoteOn(n, 127); midiNoteOff(n); }
        let laid = 0; const g = pictureEngine.cells;
        for (let i = 0; i < g.length; i++) laid += Math.min(1, g[i]) - Math.min(1, base[i]);
        const f0 = pictureEngine.frames;
        while (pictureEngine.frames < f0 + 2) await wait(10);
        out[strike] = { before, after: pictureMeter.lit, laid: laid / g.length, frames: pictureEngine.frames - f0 };
      }
      midiPanic(); genSet('amp', 0.55);
      return out;
    }""")
    m0, m1 = met["0"], met["100"]
    print("    lit: struck %.5f -> %.5f (laid %.5f); at nought %.5f -> %.5f" % (m1["before"], m1["after"], m1["laid"], m0["before"], m0["after"]))
    check("the picture meter, which the stage and the running-away hold read, lights with what a strike laid",
          m1["laid"] > 0.002 and m1["after"] - m1["before"] > 0.5 * m1["laid"], str(m1))
    null("the same notes at Strike nought light nothing", abs(m0["after"] - m0["before"]) < 0.1 * m1["laid"], str(m0))

    # ------------------------------------------------------------------
    print("\n--- a split: each layer's strikes, and cross-scan ---")
    SPLIT = """async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      applyPreset('b:Scanned fifth'); await wait(300);
      midiPanic(); setScreenKeys(true); setMidiMode('poly');
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      for (const n of [48, 55]) midiBytes(new Uint8Array([0x90, n, 100]));
      for (const n of [79, 84]) midiBytes(new Uint8Array([0x90, n, 100]));
      for (const l of [0, 1]) { midi.layers.edit = l; syncLayerPanel(); el.oscScan.value = '100'; el.oscScan.dispatchEvent(new Event('input')); }
      midi.layers.edit = 0; syncLayerPanel();
      await wait(1500);
    }"""
    UNSPLIT = """() => {
      for (const n of [48, 55, 79, 84]) midiBytes(new Uint8Array([0x80, n, 0]));
      el.scanReadsA.value = 'A'; el.scanReadsA.dispatchEvent(new Event('change'));
      el.scanReadsB.value = 'B'; el.scanReadsB.dispatchEvent(new Event('change'));
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change')); setScreenKeys(false);
      midiPanic(); setRunning(true);
    }"""
    p.evaluate(SPLIT)
    lay = p.evaluate("""() => {
      if (!layerPictures.live || !layerPictures.engines) return { live: false };
      setRunning(false);
      const e = layerPictures.engines, before = [Float32Array.from(e[0].cells), Float32Array.from(e[1].cells)];
      const grew = (l) => { let m = 0; const g = e[l].cells; for (let i = 0; i < g.length; i++) m = Math.max(m, g[i] - before[l][i]); return m; };
      midiNoteOn(86, 127);
      const high = [grew(0), grew(1)];
      e[0].cells.set(before[0]); e[1].cells.set(before[1]);
      midiNoteOn(50, 127);
      const low = [grew(0), grew(1)];
      e[0].cells.set(before[0]); e[1].cells.set(before[1]);
      midiNoteOff(86); midiNoteOff(50);
      setRunning(true);
      return { live: true, high, low, row: !el.scanReadsRow.hidden };
    }""")
    check("in a split a note above the split strikes B's picture and not A's",
          lay["live"] and lay["high"][1] > 0.1 and lay["high"][0] == 0, str(lay))
    null("and one below strikes A's", lay["live"] and lay["low"][0] > 0.1 and lay["low"][1] == 0, str(lay.get("low")))
    check("the Reads row is shown while the layers draw a figure each", lay.get("row") is True, str(lay.get("row")))

    xs = p.evaluate("""() => {
      if (!layerPictures.live) return { live: false };
      setRunning(false);
      const e = layerPictures.engines;
      const d = (x, y) => { let m = 0; for (let i = 0; i < x.levels[0].length; i++) m = Math.max(m, Math.abs(x.levels[0][i] - y.levels[0][i])); return m; };
      const out = { live: true };
      const set = (a, b) => {
        el.scanReadsA.value = a; el.scanReadsA.dispatchEvent(new Event('change'));
        el.scanReadsB.value = b; el.scanReadsB.dispatchEvent(new Event('change'));
      };
      // Crossed: A's table from B's picture, B's from A's.
      set('B', 'A'); scanStep(16);
      const ownA = scanTables(scanRead(e[0].cells, scan.paths[0], scan.soft));
      const fromB = scanTables(scanRead(e[1].cells, scan.paths[1], scan.soft));
      out.crossA = d(genSettings(0).scanTable, fromB); out.crossAown = d(genSettings(0).scanTable, ownA);
      out.crossB = d(genSettings(1).scanTable, ownA);
      // Both, for A: the two readings averaged.
      set('both', 'B'); scanStep(16);
      const r0 = scanRead(e[0].cells, scan.paths[0], scan.soft), r1 = scanRead(e[1].cells, scan.paths[1], scan.soft);
      const avg = new Float64Array(r0.length); for (let i = 0; i < r0.length; i++) avg[i] = (r0[i] + r1[i]) / 2;
      out.both = d(genSettings(0).scanTable, scanTables(avg));
      out.bothOwn = d(genSettings(0).scanTable, scanTables(r0));
      // The holds: B's picture's governor at 0.3, A's at one.
      const was = [layerPictures.stages[0].hold, layerPictures.stages[1].hold];
      layerPictures.stages[0].hold = 1; layerPictures.stages[1].hold = 0.3;
      set('B', 'A'); scanStep(16);
      out.holdCrossed = [genSettings(0).scanHold, genSettings(1).scanHold];
      set('A', 'B'); scanStep(16);
      out.holdOwn = [genSettings(0).scanHold, genSettings(1).scanHold];
      set('both', 'B'); scanStep(16);
      out.holdBoth = [genSettings(0).scanHold, genSettings(1).scanHold];
      layerPictures.stages[0].hold = was[0]; layerPictures.stages[1].hold = was[1];
      // Menus: a setup code carries them, the defaults are own, and a
      // value a layer's menu does not offer is its own.
      set('B', 'both');
      const code = snapshot();
      restore({}); const cleared = scan.reads.slice();
      restore(code); const back = scan.reads.slice();
      restore(Object.assign({}, code, { scanReadsA: 'A', scanReadsB: 'nobody' }));
      const refused = scan.reads.slice();
      out.code = [code.scanReadsA, code.scanReadsB]; out.cleared = cleared; out.back = back; out.refused = refused;
      out.menus = [el.scanReadsA.value, el.scanReadsB.value];
      setRunning(true);
      return out;
    }""")
    if xs.get("live"):
        print("    crossed: A's table %.2g from B's picture, %.3f from its own; both: %.2g from the average, %.3f from its own"
              % (xs["crossA"], xs["crossAown"], xs["both"], xs["bothOwn"]))
    check("crossed, A plays a table made from B's picture, and B from A's",
          xs.get("live") and xs["crossA"] == 0 and xs["crossB"] == 0, str(xs))
    null("A's table against one made from its own picture", xs.get("live") and xs["crossAown"] > 0.01, str(xs.get("crossAown")))
    check("reading both, A plays the two pictures' readings averaged", xs.get("live") and xs["both"] < 1e-12, str(xs.get("both")))
    null("not its own alone", xs.get("live") and xs["bothOwn"] > 0.01, str(xs.get("bothOwn")))
    check("a crossed pair's depths are both held by the lower of the two holds",
          xs.get("live") and xs["holdCrossed"] == [0.3, 0.3], str(xs.get("holdCrossed")))
    null("each reading its own, each keeps its own hold", xs.get("live") and xs["holdOwn"] == [1, 0.3], str(xs.get("holdOwn")))
    check("and a layer reading both, uncrossed, takes the lower of the two it reads",
          xs.get("live") and xs["holdBoth"] == [0.3, 0.3], str(xs.get("holdBoth")))
    check("a setup code carries what each layer reads and brings it back",
          xs.get("code") == ["B", "both"] and xs.get("back") == ["B", "both"], "%s, %s" % (xs.get("code"), xs.get("back")))
    null("between, the defaults: each its own", xs.get("cleared") == ["A", "B"], str(xs.get("cleared")))
    check("a value a layer's menu does not offer reads its own picture", xs.get("refused") == ["A", "B"], str(xs.get("refused")))
    p.evaluate(UNSPLIT)
    hidden = p.evaluate("() => el.scanReadsRow.hidden")
    check("unsplit, the Reads row is hidden: there is one picture", hidden is True, str(hidden))

    # ------------------------------------------------------------------
    print("\n--- the loop that keeps going ---")
    RUN = """async ([preset, stopAt, drive]) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setRunning(true); applyPreset('b:' + preset); await wait(800);
      setScreenKeys(true);
      if (drive) midi.drive.wave = true;
      const freq0 = genSettings().freq;
      for (const n of [60, 64, 67]) midiNoteOn(n, 120);
      await wait(1000);
      const freqHeld = genSettings().freq;
      for (const n of [60, 64, 67]) midiNoteOff(n);
      if (stopAt !== null) setTimeout(() => setRunning(false), stopAt * 1000);
      const out = []; let last = null; const t0 = performance.now();
      while (performance.now() - t0 < 12000) {
        await wait(250);
        if (!state.running) state.source.tick(performance.now() / 1000);
        const t = genSettings().scanTable, [l] = state.source.getLatestWindow(2048);
        let e = 0; for (const v of l) e += v * v;
        let m = null;
        if (t && last) { m = 0; for (let k = 0; k < t.levels[0].length; k++) m += Math.abs(t.levels[0][k] - last.levels[0][k]); m /= t.levels[0].length; }
        last = t;
        out.push([(performance.now() - t0) / 1000, m, Math.sqrt(e / l.length)]);
      }
      setRunning(true); midiPanic(); setScreenKeys(false); midi.drive.wave = true;
      return { out, freq0, freqHeld };
    }"""
    def summary(run, after=5):
        late = [x for x in run["out"] if x[0] > after]
        ms = [x[1] for x in late if x[1] is not None]
        return (statistics.median(ms) if ms else 0), statistics.mean(x[2] for x in late)
    breathe = p.evaluate(RUN, ["Scan breathes", None, False])
    remember = p.evaluate(RUN, ["Scan remembers", None, False])
    stopped = p.evaluate(RUN, ["Scan breathes", 3, False])
    driven = p.evaluate(RUN, ["Scan breathes", None, True])
    (mb, rb), (mr, rr), (ms_, rs), (md, rd) = summary(breathe), summary(remember), summary(stopped), summary(driven)
    print("    after letting go: breathes moves %.4f a quarter second (level %.3f), remembers %.4f (%.3f), "
          "stopped %.4f, with notes driving the waveform level %.4f" % (mb, rb, mr, rr, ms_, rd))
    check("Scan breathes: five seconds after the keys are let go, the wave is still moving and still sounding",
          mb > 0.02 and rb > 0.05, "%.4f, level %.3f" % (mb, rb))
    check("Scan remembers: so is this one", mr > 0.02 and rr > 0.05, "%.4f, level %.3f" % (mr, rr))
    null("Stop holds the screen, and the wave stands", ms_ < 0.005, "%.4f" % ms_)
    null("the same preset with notes driving the waveform falls silent when they are let go", rd < 0.01, "level %.4f" % rd)
    check("and in it the keys strike rather than play: the note does not move", breathe["freq0"] == breathe["freqHeld"],
          "%s then %s" % (breathe["freq0"], breathe["freqHeld"]))
    null("driving the waveform, the same keys move it", driven["freq0"] != driven["freqHeld"],
         "%s then %s" % (driven["freq0"], driven["freqHeld"]))

    crossed = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      applyPreset('b:Crossed hands'); await wait(500);
      setScreenKeys(true);
      for (const n of [43, 50]) midiNoteOn(n, 100);
      for (const n of [72, 79]) midiNoteOn(n, 100);
      await wait(1500);
      const out = { live: layerPictures.live, reads: scan.reads.slice(), scans: [genSettings(0).scan, genSettings(1).scan] };
      if (layerPictures.live) {
        setRunning(false);
        scanStep(16);
        const e = layerPictures.engines;
        const d = (x, y) => { let m = 0; for (let i = 0; i < x.levels[0].length; i++) m = Math.max(m, Math.abs(x.levels[0][i] - y.levels[0][i])); return m; };
        out.fromB = d(genSettings(0).scanTable, scanTables(scanRead(e[1].cells, scan.paths[1], scan.soft)));
        out.fromOwn = d(genSettings(0).scanTable, scanTables(scanRead(e[0].cells, scan.paths[0], scan.soft)));
        setRunning(true);
      }
      for (const n of [43, 50, 72, 79]) midiNoteOff(n);
      midiPanic(); setScreenKeys(false);
      return out;
    }""")
    check("Crossed hands: two figures, Scan on both, and the left hand's wave read from the right hand's picture",
          crossed["live"] and crossed["reads"] == ["B", "A"] and crossed["scans"] == [1, 1] and crossed.get("fromB") == 0,
          str(crossed))
    null("not from its own", crossed.get("fromOwn", 0) > 0.01, str(crossed.get("fromOwn")))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("STRIKE PASS")
