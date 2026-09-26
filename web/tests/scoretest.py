"""The picture as a score (K3), and its notes going out as MIDI (K4).

Against the way each would fail:

- a score that plays the wrong row, or upside down: a single lit row is one
  repeated note, the one its height names; a diagonal is a rising scale, and
  in D dorian every note of it is in D dorian;
- a chord that is not the brightest, or a floor that lets smudges play;
- an empty grid that plays anything, or sends anything;
- a playhead not at the tempo: 120 BPM in semiquavers is a step every
  125 ms, nine steps in a second counted from nought, and half the tempo is
  half the steps;
- a voice that is drawn: the score's notes are in the heard pair and the
  picture pair is untouched, sample for sample;
- MIDI out that sends on the wrong channel, leaves a note hanging, or keeps
  sending when the scope stops or the page is hidden;
- a rate limit that is not one: a hundred note-ons at once are forty sent.
"""
import math, os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

STUB = """
  window.__sent = [];
  window.__midi = { port: null };
  navigator.requestMIDIAccess = function () {
    const port = { id: "in", name: "Stub Keyboard", onmidimessage: null };
    const out = { id: "out1", name: "Stub Synth", send: (bytes) => window.__sent.push(Array.from(bytes)) };
    window.__midi.port = port;
    return Promise.resolve({ inputs: new Map([["in", port]]), outputs: new Map([["out1", out]]),
                             onstatechange: null });
  };
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

    print("\n--- reading a column ---")
    cols = p.evaluate("""() => {
      const N = PHOSPHOR_N, grid = () => new Float32Array(N * N);
      const chrom = scorePitches(48, 3, keyMask(0, 'chromatic'));
      const dorian = scorePitches(50, 2, keyMask(2, 'dorian'));
      // One row lit, a quarter of the way up.
      const one = grid(); for (let c = 0; c < N; c++) one[48 * N + c] = 0.8;
      const row = [0, 17, 63].map((c) => scoreColumn(one, N, c, chrom, 2));
      // A diagonal, bottom left to top right.
      const diag = grid(); for (let c = 0; c < N; c++) diag[(N - 1 - c) * N + c] = 1;
      const rising = [], dor = [];
      for (let c = 0; c < N; c++) {
        const a = scoreColumn(diag, N, c, chrom, 1), d = scoreColumn(diag, N, c, dorian, 1);
        rising.push(a.length ? a[0][0] : null); dor.push(d.length ? d[0][0] : null);
      }
      // Four lit at once, two voices; and a smudge below the floor.
      const four = grid(); [[10, 0.9], [20, 0.3], [30, 0.7], [40, 0.5]].forEach(([r, g]) => { four[r * N + 5] = g; });
      const smudge = grid(); smudge[30 * N + 5] = 0.1;
      const empty = scoreColumn(grid(), N, 5, chrom, 4);
      return { row, rising, dor, dorianSet: dorian, two: scoreColumn(four, N, 5, chrom, 2),
               smudge: scoreColumn(smudge, N, 5, chrom, 4), empty, want: chrom[Math.floor(15 * 36 / 64)] };
    }""")
    print("    one row: %s (want %d at 0.8)" % (cols["row"][0], cols["want"]))
    check("a single lit row is one note in every column, the one its height names, at its brightness",
          all(len(c) == 1 and c[0][0] == cols["want"] and abs(c[0][1] - 0.8) < 1e-6 for c in cols["row"]),
          str(cols["row"]))
    rising = cols["rising"]
    steps = [b2 - a2 for a2, b2 in zip(rising, rising[1:])]
    check("a diagonal is a rising scale, every note from C3 to B5 and none twice out of order",
          None not in rising and all(s >= 0 for s in steps) and rising[0] == 48 and rising[-1] == 83
          and sorted(set(rising)) == list(range(48, 84)), "%s ... %s" % (rising[:5], rising[-3:]))
    # Written out here, not asked of the page: checked against the page's own
    # list, a key that was ignored agreed with itself and passed.
    DORIAN = [50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71, 72]
    check("and in D dorian every note of it is in D dorian, the whole scale climbed",
          cols["dorianSet"] == DORIAN and sorted(set(cols["dor"])) == DORIAN, "%s" % sorted(set(cols["dor"])))
    two = cols["two"]
    check("with two voices the chord is the two brightest, loudest first",
          len(two) == 2 and abs(two[0][1] - 0.9) < 1e-6 and abs(two[1][1] - 0.7) < 1e-6, str(two))
    check("and a smudge under the floor plays nothing, as an empty column plays nothing",
          cols["smudge"] == [] and cols["empty"] == [], "%s, %s" % (cols["smudge"], cols["empty"]))

    print("\n--- the playhead ---")
    tick = p.evaluate("""() => {
      const saved = phosphor.grid.slice(), N = PHOSPHOR_N;
      phosphor.grid.fill(0); for (let c = 0; c < N; c++) phosphor.grid[40 * N + c] = 0.9;
      const src = state.source, strike = src.strike.bind(src), got = [];
      src.strike = (notes) => { got.push(notes.map((n) => n[0])); strike(notes); };
      const run = (bpm) => {
        setTempo(bpm); got.length = 0; score.on = true; score.start = null;
        const t0 = 100000, cols = [];
        for (let t = 0; t <= 1000; t += 10) { scoreTick(t0 + t); cols.push(score.col); }
        score.on = false; scoreStop();
        return { strikes: got.length, lastCol: cols[cols.length - 1], hz: got[0] && got[0][0] };
      };
      const fast = run(120), slow = run(60);
      // An empty grid, played for the same second: nothing struck.
      phosphor.grid.fill(0); const none = run(120);
      phosphor.grid.set(saved); src.strike = strike; setTempo(120);
      return { fast, slow, none };
    }""")
    print("    %s" % tick)
    check("at 120 BPM in semiquavers a second from nought is nine steps, each striking the lit row's note",
          tick["fast"]["strikes"] == 9 and tick["fast"]["lastCol"] == 8, str(tick["fast"]))
    check("and at 60 BPM it is five: the playhead keeps the tempo", tick["slow"]["strikes"] == 5, str(tick["slow"]))
    check("and an empty grid strikes nothing", tick["none"]["strikes"] == 0, str(tick["none"]))

    print("\n--- the voice ---")
    voice = p.evaluate("""() => {
      const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
      const make = () => { const c = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
                           c.set('amp', 0.3); c.set('freq', 110); return c; };
      const run = (struck) => {
        const core = make(), n = 44100;
        if (struck) core.strike(1000, 1);
        const L = new Float32Array(n), R = new Float32Array(n), HL = new Float32Array(n), HR = new Float32Array(n);
        core.block(L, R, n, HL, HR);
        return { L, HL };
      };
      const a = run(false), b = run(true);
      let picture = 0, early = 0, late = 0;
      for (let i = 0; i < 44100; i++) picture = Math.max(picture, Math.abs(a.L[i] - b.L[i]));
      // The heard difference is the struck note alone: its peak just after
      // the strike, and after one decay time of 400 ms.
      for (let i = 200; i < 2400; i++) early = Math.max(early, Math.abs(b.HL[i] - a.HL[i]));
      for (let i = 17640; i < 17640 + 441; i++) late = Math.max(late, Math.abs(b.HL[i] - a.HL[i]));
      return { picture, early, late };
    }""")
    print("    picture difference %.2e; heard note %.4f just after the strike (want 0.2), %.4f at 400 ms "
          "(want %.4f)" % (voice["picture"], voice["early"], voice["late"], 0.2 / math.e))
    check("a struck note is heard at its level, 0.4 times its velocity over two, and the picture is untouched",
          voice["picture"] == 0 and abs(voice["early"] - 0.2) < 0.005, str(voice))
    check("and it dies away to 1/e over its 400 ms", abs(voice["late"] - 0.2 / math.e) < 0.006, str(voice))

    print("\n--- MIDI out ---")
    p.evaluate("() => midiConnect()"); p.wait_for_timeout(300)
    out = p.evaluate("""async () => {
      el.midiOut.value = 'out1'; el.midiOutCh.value = '2';
      el.midiOut.dispatchEvent(new Event('change'));
      __sent.length = 0;
      const saved = phosphor.grid.slice(), N = PHOSPHOR_N;
      phosphor.grid.fill(0); for (let c = 0; c < N; c++) phosphor.grid[40 * N + c] = 1;
      setTempo(120); score.on = true; score.start = null;
      scoreTick(200000); scoreTick(200130);
      const played = __sent.map((m) => m.slice());
      /* Two rows in turn, so each step's note differs from the last: the
         last must be ended as the next begins. With one row the new note-on
         of the same note ended it anyway, and nothing checked the rest. */
      score.on = false; scoreStop(); __sent.length = 0;
      phosphor.grid.fill(0);
      for (let c = 0; c < N; c++) phosphor.grid[(c % 2 ? 10 : 50) * N + c] = 1;
      score.on = true; score.start = null;
      scoreTick(210000); scoreTick(210130);
      const turns = __sent.map((m) => m.slice());
      score.on = false; scoreStop();
      phosphor.grid.fill(0); for (let c = 0; c < N; c++) phosphor.grid[40 * N + c] = 1;
      score.on = true; score.start = null; scoreTick(220000);
      // Stopping the scope ends what was sent.
      __sent.length = 0; setRunning(false);
      const stopped = __sent.map((m) => m.slice());
      setRunning(true); score.on = false; scoreStop();
      // Hidden: all notes off.
      midiOutNote(64, 1, performance.now());
      __sent.length = 0;
      Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
      document.dispatchEvent(new Event('visibilitychange'));
      Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true });
      const hidden = __sent.map((m) => m.slice());
      // A hundred note-ons at once.
      __sent.length = 0; midiOut.times = []; midiOut.dropped = 0;
      const t = performance.now();
      for (let i = 0; i < 100; i++) midiOutNote(40 + (i % 40), 0.5, t);
      const burst = { ons: __sent.filter((m) => (m[0] & 0xf0) === 0x90).length, dropped: midiOut.dropped };
      midiOutPanic();
      // An empty grid, played: nothing sent.
      phosphor.grid.fill(0); __sent.length = 0; score.on = true; score.start = null;
      for (let k = 0; k < 20; k++) scoreTick(300000 + k * 60);
      const quiet = __sent.filter((m) => (m[0] & 0xf0) === 0x90).length;
      score.on = false; scoreStop(); phosphor.grid.set(saved);
      const status = el.midiOutStatus.textContent;
      return { played, turns, stopped, hidden, burst, quiet, status };
    }""")
    print("    played %s; stopped %s; hidden %s; burst %s; empty grid sent %d" %
          (out["played"], out["stopped"], out["hidden"], out["burst"], out["quiet"]))
    ons = [m for m in out["played"] if m[0] == 0x92]
    offs = [m for m in out["played"] if m[0] == 0x82]
    check("the score's notes go out on the chosen channel, the last one ended before the next begins",
          len(ons) == 2 and len(offs) == 1
          and out["played"] == [[0x92, ons[0][1], 127], [0x82, ons[0][1], 0], [0x92, ons[0][1], 127]],
          str(out["played"]))
    t = out["turns"]
    check("and when the next step's note is another, the last is ended before it begins",
          len(t) == 3 and t[0][0] == 0x92 and t[1] == [0x82, t[0][1], 0] and t[2][0] == 0x92 and t[2][1] != t[0][1],
          str(t))
    check("stopping the scope ends the sounding note and sends all-notes-off on that channel",
          [0x82, ons[0][1], 0] in out["stopped"] and [0xB2, 123, 0] in out["stopped"], str(out["stopped"]))
    check("hiding the page does the same", [0x82, 64, 0] in out["hidden"] and [0xB2, 123, 0] in out["hidden"],
          str(out["hidden"]))
    check("a hundred note-ons at once are forty sent and sixty dropped, and none of the note-offs",
          out["burst"] == {"ons": 40, "dropped": 60}, str(out["burst"]))
    check("and an empty grid sends nothing at all", out["quiet"] == 0, str(out["quiet"]))

    print("\n--- crossings out ---")
    crossed = p.evaluate("""() => {
      const src = state.source, counts = { x: 5, y: 3 };
      Object.defineProperty(src, 'crossings', { get: () => counts, configurable: true });
      cross.on = true; crossSeen.x = 5; crossSeen.y = 3; __sent.length = 0;
      const t = performance.now() + 5000; midiOut.times = [];
      counts.x = 6; crossStepPanel(t);
      const on = __sent.map((m) => m.slice());
      crossStepPanel(t + 150);
      const off = __sent.map((m) => m.slice());
      // A new generator's count from nought is not a crossing.
      __sent.length = 0; counts.x = 0; crossStepPanel(t + 300);
      const reset = __sent.length;
      cross.on = false; delete src.crossings;
      return { on, off, reset, note: cross.noteX };
    }""")
    print("    %s" % crossed)
    check("a crossing goes out as its line's note and is ended a tenth of a second later",
          [0x92, crossed["note"], 102] in crossed["on"] and [0x82, crossed["note"], 0] in crossed["off"],
          str(crossed))
    check("and a count starting again from nought sends nothing", crossed["reset"] == 0, str(crossed["reset"]))

    # With real frames: the box ticked, a figure drawn, a second of playing.
    live = p.evaluate("""async () => {
      setTempo(120); state.persistence = -1;
      const src = state.source, strike = src.strike.bind(src); let struck = 0;
      src.strike = (notes) => { struck++; strike(notes); };
      el.scoreOn.checked = true; el.scoreOn.dispatchEvent(new Event('change'));
      await __wait(1200);
      const out = { steps: score.steps, struck, col: score.col };
      el.scoreOn.checked = false; el.scoreOn.dispatchEvent(new Event('change'));
      src.strike = strike;
      return out;
    }""")
    check("ticked on the page, the playhead moves with the frames and the drawn waveform plays",
          live["steps"] >= 8 and live["struck"] >= 4, str(live))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
