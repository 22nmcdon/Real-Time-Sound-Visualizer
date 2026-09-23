"""Full scale as a continuous gain, and the nine detents it kept.

The trigger level was made a fraction of full scale so that a modulated full
scale would be safe to point something at. A fraction sitting on top of a table
of nine positions delivers a smaller and stranger promise than that - safe
across nine discrete jumps - so this finishes it: the stored value is decibels,
a source adds decibels to it, and the knob keeps its detents because a scope's
volts-per-division switch has always had them.

The first section is the one that has to hold before any of the rest means
anything. The nine table values must produce the nine gains they always
produced, exactly - not nearly - because everything downstream is measured
against that baseline, and a baseline that has moved makes every later
comparison a comparison with a moving target.
"""
import math, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

# The table the page has always had, written out here rather than read from it:
# a test that asks the page for the numbers and then agrees with them would
# pass whatever the page did.
TABLE = [0, -3, -6, -12, -18, -24, -30, -40, -50]

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

    print("\n--- the nine detents are the nine gains they always were ---")
    exact = p.evaluate("""([table]) => {
      const out = [];
      for (const db of table) {
        state.channels[0].fsDb = db;
        state.channels[0].fsMod = 0;
        out.push({ db, gain: gainOf(0), detent: fsDetent(db) });
      }
      state.channels[0].fsDb = 0;
      return { out, table: FULL_SCALE_DB };
    }""", [TABLE])
    check("the table itself is unchanged", exact["table"] == TABLE, str(exact["table"]))
    worst = 0.0
    for row in exact["out"]:
        want = math.pow(10, -row["db"] / 20)
        worst = max(worst, abs(row["gain"] - want))
    for row in exact["out"][:3] + exact["out"][-1:]:
        print("    %4d dBFS is a gain of %.6f, on detent %d"
              % (row["db"], row["gain"], row["detent"]))
    check("every detent gives its old gain to the last bit", worst == 0,
          "worst difference %r" % worst)
    check("and each one lands back on its own detent",
          [row["detent"] for row in exact["out"]] == list(range(len(TABLE))),
          str([row["detent"] for row in exact["out"]]))

    print("\n--- and the knob still has nine of them ---")
    knob = p.evaluate("""([table]) => {
      buildLaneRows();
      const slider = el.ch1Scale;
      const out = { min: Number(slider.min), max: Number(slider.max),
                    step: Number(slider.step), wrote: [] };
      for (let i = 0; i < table.length; i++) {
        slider.value = String(i);
        slider.dispatchEvent(new Event('input'));
        out.wrote.push(state.channels[0].fsDb);
      }
      slider.value = '0';
      slider.dispatchEvent(new Event('input'));
      return out;
    }""", [TABLE])
    check("the control is still nine stepped positions",
          knob["min"] == 0 and knob["max"] == len(TABLE) - 1 and knob["step"] == 1,
          str(knob))
    check("and each one writes its own decibels", knob["wrote"] == TABLE,
          str(knob["wrote"]))

    print("\n--- continuous underneath, and clamped to what the knob can reach ---")
    smooth = p.evaluate("""() => {
      state.channels[0].fsDb = -12;
      const out = [];
      for (const mod of [0, -6, 6, -1.5, 0.75]) {
        state.channels[0].fsMod = mod;
        out.push({ mod, db: fullScaleDb(0), gain: gainOf(0) });
      }
      // Past both ends of the knob's own range.
      state.channels[0].fsMod = -100;
      const bottom = fullScaleDb(0);
      state.channels[0].fsMod = 100;
      const top = fullScaleDb(0);
      state.channels[0].fsMod = 0;
      state.channels[0].fsDb = 0;
      return { out, bottom, top };
    }""")
    for row in smooth["out"]:
        print("    -12 dBFS with %+5.2f dB on it: %+6.2f dBFS, gain %.4f"
              % (row["mod"], row["db"], row["gain"]))
    check("a source moves it by the decibels it asks for",
          all(abs(row["db"] - (-12 + row["mod"])) < 1e-9 for row in smooth["out"]),
          str([round(row["db"], 3) for row in smooth["out"]]))
    check("and between the detents, not only on them",
          any(abs(row["db"] - round(row["db"])) > 1e-9 for row in smooth["out"]),
          str([round(row["db"], 3) for row in smooth["out"]]))
    check("pushed past the ends it stops where the knob stops",
          smooth["bottom"] == TABLE[-1] and smooth["top"] == 0,
          "%s and %s" % (smooth["bottom"], smooth["top"]))

    print("\n--- and it is somewhere a source can point ---")
    dests = p.evaluate("""() => {
      const ids = Array.from(MOD_DESTS.keys()).filter((k) => k.startsWith('view.scale'));
      return { ids, lanes: state.channels.length,
               label: MOD_DESTS.get('view.scale1').label };
    }""")
    check("one destination per lane, and no more",
          dests["ids"] == ["view.scale" + str(i + 1) for i in range(dests["lanes"])],
          str(dests["ids"]))
    check("named so a reader knows which lane", "lane 1" in dests["label"],
          dests["label"])

    routed = p.evaluate("""() => {
      applyPreset('b:Harmonic tone');
      state.channels[0].fsDb = -12;
      state.channels[0].fsMod = 0;
      // A level of nought fires at nought whatever the gain, which would make
      // the check below true without meaning anything.
      state.level = 0.5;
      state.trigSource = 0;
      state.modRoutings = [{ sourceId: 'lfo1', destId: 'view.scale1', amount: 1 }];
      touchRoutings();

      // Drive the matrix by hand at two points in the oscillator's cycle,
      // rather than waiting for frames to happen to land where we want them.
      const frame = capture();
      lfos[0].value = 1;
      applyModMatrix(frame, 16);
      const high = { db: fullScaleDb(0), levelAt: capture().levelAt };
      lfos[0].value = -1;
      applyModMatrix(frame, 16);
      const low = { db: fullScaleDb(0), levelAt: capture().levelAt };

      state.modRoutings = [];
      touchRoutings();
      applyModMatrix(frame, 16);
      const rest = { db: fullScaleDb(0), mod: state.channels[0].fsMod };
      state.channels[0].fsDb = 0;
      state.level = 0;
      return { high, low, rest };
    }""")
    print("    the oscillator at its ends: %+.2f and %+.2f dBFS"
          % (routed["high"]["db"], routed["low"]["db"]))
    check("a source on full scale moves it", abs(routed["high"]["db"] - routed["low"]["db"]) > 1,
          "%.2f against %.2f" % (routed["high"]["db"], routed["low"]["db"]))
    check("and the trigger follows it within the same capture",
          abs(routed["high"]["levelAt"] - routed["low"]["levelAt"]) > 1e-6,
          "fires at %.4f and %.4f"
          % (routed["high"]["levelAt"], routed["low"]["levelAt"]))
    check("with the patch taken off, it goes back to the knob",
          routed["rest"]["mod"] == 0 and routed["rest"]["db"] == -12,
          str(routed["rest"]))

    print("\n--- the trigger holds its height while the trace breathes ---")
    # The end of the argument that started two changes ago: a modulated full
    # scale moves what the trigger fires at, and the fraction is what keeps the
    # line where the player put it.
    held = p.evaluate("""() => {
      state.level = 0.5;
      state.trigSource = 0;
      state.channels[0].fsDb = -6;
      const out = [];
      for (const mod of [0, -6, 6]) {
        state.channels[0].fsMod = mod;
        const frame = capture();
        out.push({ mod, db: fullScaleDb(0), levelAt: frame.levelAt,
                   height: frame.levelAt * gainOf(0) });
      }
      state.channels[0].fsMod = 0;
      state.channels[0].fsDb = 0;
      state.level = 0;
      return out;
    }""")
    for row in held:
        print("    %+5.1f dB of modulation: fires at %.4f, which is %.3f of the screen"
              % (row["mod"], row["levelAt"], row["height"]))
    check("what it fires at changes with the gain",
          len(set(round(row["levelAt"], 6) for row in held)) == 3,
          str([round(row["levelAt"], 4) for row in held]))
    check("and where that sits on the screen does not",
          all(abs(row["height"] - 0.5) < 1e-9 for row in held),
          str([round(row["height"], 6) for row in held]))

    print("\n--- old setups, through both migrations in order ---")
    migrated = p.evaluate("""([table]) => {
      const code = (o) => btoa(JSON.stringify(o)).replace(/=+$/, '');

      // Version 1: full scale is a table position AND the level is an
      // amplitude. The order matters - the level's conversion has to read the
      // position as a position, before the position becomes decibels.
      const v1 = decodeSetup(code({ v: 1, level: 250, c0s: 3, c1s: 6, trig: 0 }));
      // Version 2: the level is already a fraction; only full scale moves.
      const v2 = decodeSetup(code({ v: 2, level: 250, c0s: 3, c1s: 6 }));
      // Version 3: nothing to do.
      const v3 = decodeSetup(code({ v: 3, level: 250, c0s: -12, c1s: -30 }));
      return { v1, v2, v3, table };
    }""", [TABLE])
    check("a version 1 level is converted with the old table's gain",
          migrated["v1"]["level"] == round(250 * 10 ** (12 / 20)),
          "%s, wanted %d" % (migrated["v1"]["level"], round(250 * 10 ** (12 / 20))))
    check("and its full scales become the decibels they stood for",
          migrated["v1"]["c0s"] == -12 and migrated["v1"]["c1s"] == -30,
          "%s and %s" % (migrated["v1"]["c0s"], migrated["v1"]["c1s"]))
    check("a version 2 setup keeps its level and converts its scales",
          migrated["v2"]["level"] == 250 and migrated["v2"]["c0s"] == -12
          and migrated["v2"]["c1s"] == -30, str(migrated["v2"]))
    check("a version 3 setup is left alone entirely",
          migrated["v3"]["level"] == 250 and migrated["v3"]["c0s"] == -12
          and migrated["v3"]["c1s"] == -30, str(migrated["v3"]))
    check("and everything comes out saying version 3",
          all(migrated[k]["v"] == 3 for k in ("v1", "v2", "v3")),
          str([migrated[k]["v"] for k in ("v1", "v2", "v3")]))

    trip = p.evaluate("""() => {
      state.channels[0].fsDb = -18;
      state.channels[1].fsDb = -3;
      const code = encodeSetup(snapshot());
      state.channels[0].fsDb = 0; state.channels[1].fsDb = 0;
      restore(decodeSetup(code));
      const out = [state.channels[0].fsDb, state.channels[1].fsDb];
      state.channels[0].fsDb = 0; state.channels[1].fsDb = 0;
      return out;
    }""")
    check("a setup saved now comes back in decibels", trip == [-18, -3], str(trip))

    print("\n--- and the lanes themselves are still untouched ---")
    lanes = p.evaluate("""() => {
      state.running = false;
      state.trigSource = 0;
      state.level = 0;
      state.channels[1].fsDb = 0;
      const flat = capture();
      const a = measure(flat.channels[1], flat.rate);

      state.channels[1].fsDb = -30;
      state.channels[1].fsMod = -6;
      const scaled = capture();
      const c = measure(scaled.channels[1], scaled.rate);

      let worst = 0;
      for (let i = 0; i < flat.channels[1].length; i++) {
        worst = Math.max(worst, Math.abs(flat.channels[1][i] - scaled.channels[1][i]));
      }
      state.channels[1].fsDb = 0; state.channels[1].fsMod = 0;
      state.running = true;
      return { worst, peak: [a.peak, c.peak], rms: [a.rms, c.rms] };
    }""")
    check("a modulated full scale does not touch the captured samples",
          lanes["worst"] == 0, "worst %.3g" % lanes["worst"])
    check("so dBFS and the clipping verdict are still about the input",
          lanes["peak"][0] == lanes["peak"][1] and lanes["rms"][0] == lanes["rms"][1],
          str(lanes))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("full scale is a number, with nine places to put it")
