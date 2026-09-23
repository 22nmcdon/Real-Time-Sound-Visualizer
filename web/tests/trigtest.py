"""The trigger level, as a fraction of full scale rather than an amplitude.

A bench scope taps its trigger after the vertical amplifier, so the front-panel
level is a volts-per-division quantity: set the line halfway up the screen and
it stays halfway up the screen when you change volts per division. This page
compared an absolute amplitude instead, so the line sat wherever full scale
happened to put it.

That was merely mislabelled until full scale became something a source can
modulate. Then it is wrong: the point the trigger fires at would drift against
what is on screen while nobody touched a control. So the level is a fraction
now, and the amplitude it comes to is worked out per capture, on the gain in
force for that block rather than the gain in force when a human last moved
something.

What this deliberately does NOT do is scale the captured lanes. That would put
full scale inside the block, which changes what `dBFS` means, what the clipping
verdict is about, and what `env.live` follows - the same measurement-honesty
question rotation is held on. The trigger needs the fraction, not the scaling,
and the two can be separated.
"""
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
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    print("\n--- the same height on the screen, whatever full scale says ---")
    heights = p.evaluate("""() => {
      applyPreset('b:Harmonic tone');
      state.level = 0.5;                          // half way up the graticule
      const out = [];
      for (const scale of [0, 3, 6]) {            // 0, -12 and -30 dBFS
        state.channels[0].fsDb = FULL_SCALE_DB[scale];
        state.trigSource = 0;
        const frame = capture();
        out.push({ scale, db: FULL_SCALE_DB[scale], levelAt: frame.levelAt });
      }
      state.channels[0].fsDb = 0;
      return out;
    }""")
    for row in heights:
        print("    full scale %4d dBFS: the trigger fires at %.4f"
              % (row["db"], row["levelAt"]))
    wanted = [0.5 * math.pow(10, row["db"] / 20) for row in heights]
    got = [row["levelAt"] for row in heights]
    check("the amplitude follows full scale exactly",
          all(abs(a - b) < 1e-9 for a, b in zip(got, wanted)),
          "%s against %s" % ([round(v, 4) for v in got],
                             [round(v, 4) for v in wanted]))
    check("and it is a different amplitude each time, which is the point",
          len(set(round(v, 6) for v in got)) == 3, str(got))

    print("\n--- worked out per capture, not when a knob last moved ---")
    # The staleness this exists to prevent. Full scale is about to be something
    # a source can modulate, so the conversion has to happen on the gain that
    # is in force for the block being captured - not on whatever it was when
    # the slider was last touched by hand.
    stale = p.evaluate("""() => {
      state.level = 0.25;
      state.trigSource = 0;
      state.channels[0].fsDb = 0;
      const first = capture().levelAt;

      // Moved with no slider event of any kind, which is what a modulated full
      // scale will look like: the state changes and the next capture is the
      // first thing to notice.
      state.channels[0].fsDb = -12;
      const second = capture().levelAt;

      state.channels[0].fsDb = 0;
      const third = capture().levelAt;
      return { first, second, third };
    }""")
    check("a full scale that moves with no event still moves the threshold",
          abs(stale["first"] - 0.25) < 1e-9
          and abs(stale["second"] - 0.25 * math.pow(10, -12 / 20)) < 1e-9,
          str(stale))
    check("and moves it back", abs(stale["third"] - 0.25) < 1e-9, str(stale))

    print("\n--- and it really triggers there ---")
    # Not just that the number is computed: that the edge found is the one at
    # that amplitude. A ramp from -1 to 1 crosses every level exactly once, so
    # where the trigger lands says what it compared against.
    landed = p.evaluate("""() => {
      /* A source of our own, so the crossing is arithmetic rather than
         whatever the generator happens to be doing: a slow ramp, rising once
         across the whole buffer. */
      const rate = 44100;
      const sweep = (want) => {
        const out = new Float32Array(want);
        for (let i = 0; i < want; i++) out[i] = -1 + 2 * i / (want - 1);
        return out;
      };
      const fake = {
        kind: 'tone', sampleRate: rate, channels: 2, capacity: rate,
        settings: state.source.settings,
        describe: () => 'ramp', set() {}, tick() {}, stop() {},
        // Whatever length is asked for, one rise from -1 to +1 across it, so
        // every level is crossed exactly once wherever the window lands.
        getLatestWindow: (want) => [sweep(want), sweep(want)],
      };
      const was = state.source;
      state.source = fake;
      state.trigSource = 0;
      state.mode = 'normal';

      const out = [];
      for (const [level, scale] of [[0.5, 0], [0.5, 3], [-0.25, 0]]) {
        state.level = level;
        state.channels[0].fsDb = FULL_SCALE_DB[scale];
        const frame = capture();
        // The sample the trigger sat on, read out of the returned window.
        out.push({ level, scale, levelAt: frame.levelAt,
                   atTrigger: frame.channels[0][frame.pre],
                   triggered: frame.triggered });
      }
      state.source = was;
      state.channels[0].fsDb = 0;
      state.mode = 'auto';
      return out;
    }""")
    for row in landed:
        print("    level %+.2f fs, scale index %d: fires at %+.4f, sample there %+.4f"
              % (row["level"], row["scale"], row["levelAt"], row["atTrigger"]))
    check("every capture triggered", all(row["triggered"] for row in landed),
          str([row["triggered"] for row in landed]))
    check("and the sample under the trigger is the level it was told",
          all(abs(row["atTrigger"] - row["levelAt"]) < 0.01 for row in landed),
          str([round(row["atTrigger"] - row["levelAt"], 5) for row in landed]))

    print("\n--- and the line is drawn where it fires ---")
    # The drawn line is the other half of the change: it used to be placed at
    # the level times the lane's gain, which was right while the level was an
    # amplitude. Found in the canvas by its own colour rather than by asking
    # the code where it put it.
    rows = p.evaluate("""() => {
      const found = [];
      for (const scale of [0, 3, 6]) {
        applyPreset('b:Harmonic tone');
        setDisplay('yt');
        state.level = 0.5;
        state.trigSource = 0;
        state.channels[0].fsDb = FULL_SCALE_DB[scale];
        state.channels[1].fsDb = FULL_SCALE_DB[scale];
        drawMain(capture(), 16);

        const c = el.trace, ctx = c.getContext('2d');
        const { width: w, height: h } = c;
        const data = ctx.getImageData(0, 0, w, h).data;
        const want = getComputedStyle(document.body)
          .getPropertyValue('--blush-deep').trim();
        const m = /#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})/i.exec(want);
        const tr = parseInt(m[1], 16), tg = parseInt(m[2], 16), tb = parseInt(m[3], 16);

        let best = -1, bestCount = 0;
        for (let y = 0; y < h; y++) {
          let n = 0;
          for (let x = 0; x < w; x++) {
            const i = (y * w + x) * 4;
            if (Math.abs(data[i] - tr) < 12 && Math.abs(data[i + 1] - tg) < 12
                && Math.abs(data[i + 2] - tb) < 12) n++;
          }
          if (n > bestCount) { bestCount = n; best = y; }
        }
        found.push({ scale, row: best, count: bestCount });
      }
      state.channels[0].fsDb = 0; state.channels[1].fsDb = 0;
      state.level = 0;
      return found;
    }""")
    for row in rows:
        print("    scale index %d: the line is at row %d, %d pixels of it"
              % (row["scale"], row["row"], row["count"]))
    check("a dashed line was actually found",
          all(row["count"] > 100 for row in rows),
          str([row["count"] for row in rows]))
    check("and it stays at the same height as full scale changes",
          max(row["row"] for row in rows) - min(row["row"] for row in rows) <= 1,
          str([row["row"] for row in rows]))

    print("\n--- autoset sets a fraction of the scale it just chose ---")
    # Autoset picks the trigger level AND the full scales. The level is now
    # expressed in terms of those scales, so it has to be worked out after they
    # are chosen - stating a fraction of a number that is about to change is
    # the same staleness the per-capture conversion exists to prevent, arriving
    # through a different door.
    auto = p.evaluate("""() => {
      const rate = 44100, offset = 0.05, swing = 0.1;
      const wave = (want) => {
        const out = new Float32Array(want);
        for (let i = 0; i < want; i++) {
          out[i] = offset + swing * Math.sin(2 * Math.PI * 200 * i / rate);
        }
        return out;
      };
      const fake = {
        kind: 'tone', sampleRate: rate, channels: 2, capacity: rate,
        settings: state.source.settings,
        describe: () => 'quiet tone on an offset', set() {}, tick() {}, stop() {},
        getLatestWindow: (want) => [wave(want), wave(want)],
      };
      const was = state.source;
      state.source = fake;
      state.trigSource = 0;

      el.autoset.click();

      const out = {
        db: state.channels[0].fsDb,
        level: state.level,
        amplitude: state.level / gainOf(0),
        offset,
      };
      state.source = was;
      state.channels[0].fsDb = 0; state.channels[1].fsDb = 0;
      state.level = 0; el.level.value = '0';
      state.running = true;
      syncLabels();
      return out;
    }""")
    print("    a 0.10 swing on a 0.05 offset: full scale %d dBFS, level %+.3f fs"
          % (auto["db"], auto["level"]))
    check("autoset opened the lane up for a quiet signal",
          auto["db"] <= -12, "%d dBFS" % auto["db"])
    check("and the level it chose is that fraction of the NEW full scale",
          abs(auto["amplitude"] - auto["offset"]) < 0.005,
          "fires at %.4f, the signal's centre is %.4f"
          % (auto["amplitude"], auto["offset"]))

    print("\n--- what the panel says about it ---")
    said = p.evaluate("""() => {
      state.level = 0.5;
      state.channels[0].fsDb = -12;               // so the two differ
      state.trigSource = 0;
      syncLabels();
      const out = { slider: el.levelValue.textContent, looking: el.looking.textContent };
      state.channels[0].fsDb = 0;
      syncLabels();
      return out;
    }""")
    check("the slider's own reading says it is a fraction",
          "fs" in said["slider"], said["slider"])
    check("and the dock gives the amplitude beside it",
          "0.500 fs" in said["looking"] and "0.126" in said["looking"],
          said["looking"])

    print("\n--- setups written before this still mean what they meant ---")
    # The same treatment the modulation enum got: a stored number whose meaning
    # changed is migrated on the way in rather than fixed up at the point of
    # use. A version 1 code stored an amplitude; the fraction it corresponds to
    # is that amplitude times the lane's gain.
    migrated = p.evaluate("""() => {
      const asV1 = (extra) => btoa(JSON.stringify(Object.assign({ v: 1 }, extra)))
        .replace(/=+$/, '');

      const plain = decodeSetup(asV1({ level: 250 }));
      const scaled = decodeSetup(asV1({ level: 250, c0s: 3, trig: 0 }));
      // Lane two's scale, not lane one's: a level of 100 at -12 dBFS becomes
      // 398, where reading the wrong lane would leave it at 100.
      const other = decodeSetup(asV1({ level: 100, c0s: 0, c1s: 3, trig: 1 }));
      const huge = decodeSetup(asV1({ level: 250, c0s: 6, trig: 0 }));
      const rack = decodeSetup(asV1({ level: 250, trig: 4 }));
      const current = decodeSetup(btoa(JSON.stringify({ v: 2, level: 250 })).replace(/=+$/, ''));
      return { plain, scaled, other, huge, rack, current };
    }""")
    # The version the page is on, not a digit written here - the same trap the
    # modulation suite fell into when this format last moved. What matters is
    # that the level is left alone, and that the code comes out saying which
    # format it is in; `scaletest.py` owns the version story itself.
    check("at nought dBFS the number is already a fraction and is left alone",
          migrated["plain"]["level"] == 250
          and migrated["plain"]["v"] == p.evaluate("() => SETUP_VERSION"),
          str(migrated["plain"]))
    check("at -12 dBFS it becomes where it sat on the graticule",
          migrated["scaled"]["level"] == round(250 * 10 ** (12 / 20)),
          "%s, wanted %d" % (migrated["scaled"]["level"], round(250 * 10 ** (12 / 20))))
    check("and it reads the lane the trigger was actually watching",
          migrated["other"]["level"] == round(100 * 10 ** (12 / 20)),
          "%s, wanted %d" % (migrated["other"]["level"], round(100 * 10 ** (12 / 20))))
    check("a conversion that would run off the slider stops at the end of it",
          migrated["huge"]["level"] == 1000, str(migrated["huge"]["level"]))
    check("a trigger on a rack lane, which stores no scale, is left as it was",
          migrated["rack"]["level"] == 250, str(migrated["rack"]["level"]))
    check("and a setup already in the new units is not migrated twice",
          migrated["current"]["level"] == 250, str(migrated["current"]["level"]))

    trip = p.evaluate("""() => {
      state.level = 0.4; el.level.value = '400';
      state.channels[0].fsDb = -6;
      const code = encodeSetup(snapshot());
      state.level = 0; el.level.value = '0';
      restore(decodeSetup(code));
      const after = { level: state.level, scale: state.channels[0].fsDb,
                      v: decodeSetup(code).v };
      state.channels[0].fsDb = 0;
      return after;
    }""")
    check("a setup saved now comes back unchanged",
          abs(trip["level"] - 0.4) < 1e-9 and trip["scale"] == -6 and trip["v"] == 3,
          str(trip))

    print("\n--- and the lanes are still the lanes ---")
    # The part deliberately not done: full scale is not inside the captured
    # block, so dBFS still means dB relative to the converter, the clipping
    # verdict is still about the input, and `env.live` still follows the
    # signal rather than the knob. If someone moves full scale into `capture`
    # without giving the measurements their own tap, this is what says so.
    untouched = p.evaluate("""() => {
      state.running = false;
      /* The trigger watches lane one and lane one's scale does not move, so
         both captures are sliced at the same edge; what moves is lane TWO's
         full scale, and lane two is what is compared. A level of 2 is not the
         escape hatch it used to be, by the way - a fraction of two at -30 dBFS
         is 0.06 of an amplitude, which a signal reaches easily. That is the
         change working, and it cost this test a rewrite. */
      state.trigSource = 0;
      state.level = 0;
      state.channels[0].fsDb = 0;

      state.channels[1].fsDb = 0;
      const flat = capture();
      const a = measure(flat.channels[1], flat.rate);

      state.channels[1].fsDb = -30;               // on the lane being read
      const scaled = capture();
      const c = measure(scaled.channels[1], scaled.rate);

      let worst = 0;
      for (let i = 0; i < flat.channels[1].length; i++) {
        worst = Math.max(worst, Math.abs(flat.channels[1][i] - scaled.channels[1][i]));
      }
      state.channels[1].fsDb = 0;
      state.running = true;
      return { worst, peaks: [a.peak, c.peak], rms: [a.rms, c.rms] };
    }""")
    check("full scale does not touch the captured samples",
          untouched["worst"] == 0, "worst %.3g" % untouched["worst"])
    check("so dBFS is still about the converter, not the graticule",
          untouched["peaks"][0] == untouched["peaks"][1]
          and untouched["rms"][0] == untouched["rms"][1], str(untouched))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the trigger level is a height on the screen")
