"""The page's clock: a tempo, tapped or from MIDI, and oscillators locked to it.

What would go wrong, and what is checked for it:

- a locked oscillator at the wrong rate: 1/4 at 120 is 2 Hz, a bar 0.5, a
  quaver triplet 6 - checked as numbers, and as cycles counted off the
  running page;
- letting go of the lock losing the rate the slider had;
- tap tempo reading the wrong gaps, or not starting again after a pause;
- MIDI clock read from one gap, and jumping; not handing the tempo back
  when it stops; clock bytes in the middle of a note breaking the note;
- Start not restarting the locked oscillators, or Continue restarting them;
- a setup code losing the tempo or the locks;
- and the bar (S6's start and stop): a tempo change that makes it jump, a
  Stop that lets it run on, a Start that leaves the locked oscillators where
  they were, a score that keeps an origin of its own, a MIDI clock whose
  position is counted in time rather than ticks, a Start that plays before
  the device's first tick, a bar that runs ahead of the clock, a clock that
  stops and leaves the bar behind, a tap that is not the one, and a setup
  code that stops the band.
"""
import os, sys
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

    print("\n--- an oscillator locked to the tempo ---")
    lock = p.evaluate("""() => {
      setView('bench'); setBenchTab('sources'); selectSource('lfo1');
      const sync = document.getElementById('lfoSync0'), rate = document.getElementById('lfoRate0');
      rate.value = '37'; rate.dispatchEvent(new Event('input'));       // 0.37 Hz, free
      setTempo(120);
      const at = (v) => { sync.value = v; sync.dispatchEvent(new Event('change'));
                          return Math.round(lfos[0].rate * 1000) / 1000; };
      const out = { quarter: at('1/4'), bar: at('1'), triplet: at('1/8t'), four: at('4') };
      at('1/4');
      out.reading = document.getElementById('lfoRateValue0').textContent;
      out.disabled = document.getElementById('lfoRate0').disabled;
      setTempo(90);
      clockStep(performance.now());
      out.at90 = Math.round(lfos[0].rate * 1000) / 1000;
      at('');
      out.free = lfos[0].rate;
      out.enabled = !document.getElementById('lfoRate0').disabled;
      setTempo(120);
      return out;
    }""")
    print("    %s" % lock)
    check("at 120, 1/4 is 2 Hz, a bar 0.5, a quaver triplet 6 and four bars 0.125",
          (lock["quarter"], lock["bar"], lock["triplet"], lock["four"]) == (2, 0.5, 6, 0.125), str(lock))
    check("the reading says so, and the Rate slider stands aside while it is locked",
          lock["reading"] == "2.00 Hz · 1/4" and lock["disabled"], str(lock))
    check("it follows the tempo: 1/4 at 90 is 1.5 Hz", lock["at90"] == 1.5, str(lock["at90"]))
    check("and let go, it is back at the slider's 0.37 Hz",
          lock["free"] == 0.37 and lock["enabled"], str(lock["free"]))

    # Counted off the running page, not read from the field: a locked rate
    # that the stepping never used would pass everything above.
    counted = p.evaluate("""async () => {
      const sync = document.getElementById('lfoSync0');
      sync.value = '1/8'; sync.dispatchEvent(new Event('change'));   // 4 Hz at 120
      lfos[0].shape = 'sine';
      await new Promise((r) => setTimeout(r, 200));
      let crossings = 0, last = lfos[0].value;
      const started = performance.now();
      while (performance.now() - started < 2000) {
        await new Promise((r) => setTimeout(r, 4));
        const now = lfos[0].value;
        if (last < 0 && now >= 0) crossings++;
        last = now;
      }
      const hz = crossings / ((performance.now() - started) / 1000);
      sync.value = ''; sync.dispatchEvent(new Event('change'));
      return hz;
    }""")
    check("and the running oscillator goes round at it: 1/8 at 120, four times a second",
          abs(counted - 4) < 0.6, "%.2f Hz" % counted)

    print("\n--- tap tempo ---")
    taps = p.evaluate("""() => {
      transport.taps.length = 0;
      lfos[0].sync = '1/4'; lfos[0].phase = 2; const epoch = lfos[0].epoch;
      clockTap(10000); const one = transport.set;
      clockTap(10500); clockTap(11000); clockTap(11500);
      const tapped = { bpm: transport.set, phase: lfos[0].phase, restarts: lfos[0].epoch - epoch };
      clockTap(11900);                          // a faster tap folds in with the last three
      const blended = transport.set;
      clockTap(20000); const paused = transport.set;     // a pause: one tap is no tempo
      clockTap(20400); clockTap(20800);
      const fresh = transport.set;
      lfos[0].sync = '';
      return { one, tapped, blended, paused, fresh, slider: el.tempo.value };
    }""")
    print("    %s" % taps)
    check("taps half a second apart are 120, and restart the locked oscillator on each",
          taps["tapped"] == {"bpm": 120, "phase": 0, "restarts": 3}, str(taps["tapped"]))
    check("and one tap on its own is no tempo: it leaves the tempo where it was",
          taps["one"] == 120 and taps["paused"] == 129, str((taps["one"], taps["paused"])))
    check("the tempo is the mean of the last four taps' gaps: 500, 500 and 400 is 129",
          taps["blended"] == 129, str(taps["blended"]))
    check("after a pause of two seconds it starts again: 400 apart is 150, not a blend with before",
          taps["fresh"] == 150 and taps["slider"] == "150", str(taps))

    print("\n--- MIDI clock ---")
    midiclock = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setTempo(90);
      lfos[0].sync = '1/4';
      // 25 ticks at 120 BPM - a crotchet is 24 of them, 20.833 ms apart -
      // with the jitter USB gives them, ending now.
      const now = performance.now(), gap = 60000 / 120 / 24;
      for (let i = 24; i >= 0; i--) {
        const jitter = (i % 3 === 0 ? 4 : i % 3 === 1 ? -3 : -1);
        midiBytes(Uint8Array.from([0xf8]), now - i * gap + (i === 0 || i === 24 ? 0 : jitter));
      }
      clockStep(performance.now());
      const running = { bpm: Math.round(transport.bpm * 10) / 10, from: transport.from,
                        rate: lfos[0].rate, disabled: el.tempo.disabled,
                        reading: el.tempoValue.textContent, clock: el.clockFrom.textContent };
      await wait(700);
      clockStep(performance.now());
      const stopped = { bpm: transport.bpm, from: transport.from, disabled: el.tempo.disabled,
                        clock: el.clockFrom.textContent };
      // Start restarts; Continue does not.
      lfos[0].phase = 3; const e0 = lfos[0].epoch;
      midiBytes(Uint8Array.from([0xfa]));
      const start = { phase: lfos[0].phase, restarts: lfos[0].epoch - e0 };
      lfos[0].phase = 3;
      midiBytes(Uint8Array.from([0xfb]));
      const cont = { phase: lfos[0].phase, restarts: lfos[0].epoch - e0 };
      // A tick in the middle of a note-on: the note still lands.
      setScreenKeys(true);
      const before = transport.ticks.length;
      midiBytes(Uint8Array.from([0x90, 64, 0xf8, 100]));
      const note = { held: midi.notes.map((n) => [n.note, Math.round(n.velocity * 127)]),
                     ticked: transport.ticks.length - before };
      midiBytes(Uint8Array.from([0x80, 64, 0]));
      setScreenKeys(false);
      lfos[0].sync = '';
      return { running, stopped, start, cont, note };
    }""")
    print("    %s" % midiclock)
    r = midiclock["running"]
    check("25 ticks at 120, jittered, read as 120 - the mean of the gaps, not the last one",
          abs(r["bpm"] - 120) < 0.2 and r["from"] == "midi", str(r))
    check("while it runs the locked oscillator follows it and the slider stands aside",
          r["rate"] == r["bpm"] / 60 and r["disabled"] and r["reading"] == "120 BPM"
          and r["clock"] == "from MIDI clock", str(r))
    s = midiclock["stopped"]
    check("half a second after the last tick the tempo is the slider's again",
          s == {"bpm": 90, "from": "internal", "disabled": False, "clock": "internal"}, str(s))
    check("Start restarts the locked oscillators, and Continue does not",
          midiclock["start"] == {"phase": 0, "restarts": 1}
          and midiclock["cont"] == {"phase": 3, "restarts": 1}, str((midiclock["start"], midiclock["cont"])))
    # The velocity too: the first parser landed this note at 248.
    check("a clock byte in the middle of a note-on is a tick, and the note lands with its own velocity",
          midiclock["note"] == {"held": [[64, 100]], "ticked": 1}, str(midiclock["note"]))

    print("\n--- the bar: start and stop ---")
    bar = p.evaluate("""() => {
      const out = {};
      const T = 1e7;             // far enough ahead that the page's own frames leave it alone
      transport.ticks.length = 0; transport.from = 'internal';
      setTempo(120, T);
      transportStart(T);
      out.second = transportBeat(T + 1000);
      out.said = transportSaid(T + 1500);
      setTempo(60, T + 1000);
      out.atChange = transportBeat(T + 1000);
      out.after = transportBeat(T + 2000);
      transportStop(T + 2500);
      out.stood = transportBeat(T + 9000);
      out.stoppedSaid = transportSaid(T + 9000);
      lfos[0].sync = '1/4'; lfos[0].phase = 3; const e0 = lfos[0].epoch;
      transportStart(T + 10000);
      out.restart = { beat: transportBeat(T + 10000), phase: lfos[0].phase, restarts: lfos[0].epoch - e0 };

      // The score: a row lit in every column, and what it strikes counted.
      const saved = phosphor.grid.slice(), N = PHOSPHOR_N;
      phosphor.grid.fill(0); for (let c = 0; c < N; c++) phosphor.grid[40 * N + c] = 0.9;
      const src = state.source, strike = src.strike.bind(src); let struck = 0;
      src.strike = (notes) => { struck++; strike(notes); };
      setTempo(120, T + 20000); transportStart(T + 20000);
      score.on = true;
      scoreTick(T + 21300);
      out.joined = score.col;              // 2.6 beats in: the eleventh semiquaver
      transportStart(T + 25000); scoreTick(T + 25000);
      out.downbeat = score.col;
      struck = 0; transportStop(T + 25100);
      for (let t = 25100; t < 27000; t += 50) scoreTick(T + t);
      out.stopped = { struck, col: score.col, notes: score.notes.length };

      // MIDI: a Start waits for the first tick, and the bar counts ticks.
      const M = T + 40000, gap = 60000 / 120 / 24;
      struck = 0;
      midiRealtime(0xfa, M);
      out.beforeTick = transportBeat(M + 10);
      scoreTick(M + 10);
      out.struckBeforeTick = struck;
      midiRealtime(0xf8, M + gap);
      out.firstTick = transportBeat(M + gap);
      scoreTick(M + gap);
      out.firstTickCol = score.col; out.struckOnTick = struck;
      let at = M + gap;
      for (let k = 1; k <= 48; k++) { at = M + gap * (k + 1) + (k % 3 === 0 ? 4 : k % 3 === 1 ? -3 : -1); midiRealtime(0xf8, at); }
      out.ticked = transportBeat(at);
      out.ahead = transportBeat(at + 300);
      // Stop and Continue: on from where it stood, at the next tick, and
      // the locked oscillators not restarted.
      midiRealtime(0xfc, at + 5);
      const stood = transportBeat(at + 5);
      const e1 = lfos[0].epoch;
      midiRealtime(0xfb, at + 2000);
      out.continuedBefore = transportBeat(at + 2010);
      midiRealtime(0xf8, at + 2000 + gap);
      out.continued = { stood, now: transportBeat(at + 2000 + gap), restarts: lfos[0].epoch - e1 };
      // The clock stops: the bar goes on to where the clock would have had it.
      const last = at + 2000 + gap, base = transportBeat(last);
      clockStep(last + 700);
      out.letGo = { at: transportBeat(last + 700), want: base + 700 * 120 / 60000, from: transport.from };
      // A Start that no clock follows.
      midiRealtime(0xfa, last + 10000);
      clockStep(last + 10600);
      out.noClock = transportBeat(last + 10600);

      // A tap is the one, while the bar runs; stopped, it only sets the tempo.
      const P = T + 80000;
      transportStart(P);
      clockTap(P + 100); clockTap(P + 600);
      out.tap = { one: transportBeat(P + 600), next: transportBeat(P + 1100) };
      transportStop(P + 1200);
      transport.taps.length = 0; clockTap(P + 4000); clockTap(P + 4400);
      out.tapStopped = { running: transport.running, bpm: transport.set };

      src.strike = strike; phosphor.grid.set(saved); score.on = false; scoreStop();
      lfos[0].sync = '';
      transport.ticks.length = 0; transport.taps.length = 0; transport.from = 'internal';
      setTempo(120); transport.bpm = transport.set;
      transportStart(performance.now());
      return out;
    }""")
    print("    %s" % bar)
    check("started, the bar moves at the tempo from nought: a second at 120 is two beats, and 1.5 s is bar 1, beat 4",
          bar["second"] == 2 and bar["said"] == "1.4", str((bar["second"], bar["said"])))
    check("a tempo change goes on from where the bar is: two beats at the change, three a second later at 60",
          bar["atChange"] == 2 and bar["after"] == 3, str((bar["atChange"], bar["after"])))
    check("stopped, it stands where it stopped, and says so",
          bar["stood"] == 3.5 and bar["stoppedSaid"] == "1.4", str((bar["stood"], bar["stoppedSaid"])))
    check("Start is the one again, and the locked oscillators start with it",
          bar["restart"] == {"beat": 0, "phase": 0, "restarts": 1}, str(bar["restart"]))
    check("the score switched on mid-bar joins the bar where it is, not at its own column nought",
          bar["joined"] == 10, str(bar["joined"]))
    check("and Start brings it back to column nought on the downbeat", bar["downbeat"] == 0, str(bar["downbeat"]))
    check("stopped, the score strikes nothing and lets go of its notes",
          bar["stopped"] == {"struck": 0, "col": -1, "notes": 0}, str(bar["stopped"]))
    check("a MIDI Start waits for the device's first tick: nothing before it, column nought on it",
          bar["beforeTick"] < 0 and bar["struckBeforeTick"] == 0 and bar["firstTick"] == 0
          and bar["firstTickCol"] == 0 and bar["struckOnTick"] == 1,
          str((bar["beforeTick"], bar["struckBeforeTick"], bar["firstTick"], bar["firstTickCol"], bar["struckOnTick"])))
    # Jittered by up to 4 ms, which in time would be a hundredth of a beat
    # either way: counted in ticks it is exact.
    check("under a clock the bar is counted in ticks: 48 jittered ticks on, exactly two beats",
          abs(bar["ticked"] - 2) < 1e-9, repr(bar["ticked"]))
    check("and between ticks it never guesses past the next one", abs(bar["ahead"] - (2 + 1 / 24)) < 1e-9,
          repr(bar["ahead"]))
    c = bar["continued"]
    check("MIDI Stop stands and Continue goes on from there at the next tick, restarting nothing",
          bar["continuedBefore"] < c["stood"] and abs(c["now"] - c["stood"]) < 1e-9 and c["restarts"] == 0, str(c))
    lg = bar["letGo"]
    check("a clock that stops lets the bar go on to where it would have been, not half a second behind",
          abs(lg["at"] - lg["want"]) < 1e-6 and lg["from"] == "internal", str(lg))
    check("and a Start that no clock follows starts anyway, rather than waiting for ever",
          bar["noClock"] > 1, repr(bar["noClock"]))
    check("a tap is the one while the bar runs", bar["tap"] == {"one": 0, "next": 1}, str(bar["tap"]))
    check("stopped, taps set the tempo and start nothing",
          bar["tapStopped"] == {"running": False, "bpm": 150}, str(bar["tapStopped"]))

    panel = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      showControl('transportPlay');
      const shown = el.transportPlay.offsetHeight > 0;
      // A second in first, so the bar has somewhere to stand other than the
      // 1.1 a reading that never moved would also show.
      transportStart(performance.now()); await wait(1100);
      el.transportPlay.click(); await wait(100);
      const stopped = [el.transportPlay.textContent, el.transportAt.textContent, transport.running];
      await wait(600);
      const stillStopped = el.transportAt.textContent;
      restore(snapshot()); await wait(50);
      const afterRestore = transport.running;
      el.transportPlay.click(); await wait(1150);
      const running = [el.transportPlay.textContent, el.transportAt.textContent, transport.running];
      return { shown, stopped, stillStopped, afterRestore, running };
    }""")
    print("    %s" % panel)
    check("the Bar row's button stops the bar, and the reading says where it stood",
          panel["shown"] and panel["stopped"][0] == "Start" and panel["stopped"][1].startswith("stopped at ")
          and panel["stopped"][2] is False and panel["stillStopped"] == panel["stopped"][1]
          and panel["stopped"][1] == "stopped at 1.3", str(panel))
    check("loading a setup code leaves the bar stopped: the transport is playing, not the patch",
          panel["afterRestore"] is False, str(panel["afterRestore"]))
    check("and started again, it runs from the one: a little over a second at 120 is bar 1, beat 3",
          panel["running"][0] == "Stop" and panel["running"][1] == "1.3" and panel["running"][2] is True,
          str(panel["running"]))

    print("\n--- setup codes ---")
    codes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setTempo(96);
      lfos[1].sync = '1/2'; lfos[1].free = 0.9; clockStep(performance.now());
      const code = snapshot();
      restore({}); await wait(30);
      const old = { bpm: transport.set, sync: lfos[1].sync, rate: lfos[1].rate };
      restore(code); await wait(30);
      const back = { bpm: transport.set, sync: lfos[1].sync, rate: lfos[1].rate, free: lfos[1].free };
      lfos[1].sync = ''; lfos[1].rate = lfos[1].free;
      return { code: { bpm: code.bpm, l1y: code.l1y, l1r: code.l1r }, old, back };
    }""")
    print("    %s" % codes)
    check("a code carries the tempo, each lock, and the slider's rate rather than the locked one",
          codes["code"] == {"bpm": 96, "l1y": "1/2", "l1r": 90}, str(codes["code"]))
    check("a code from before the clock is 120 and free",
          codes["old"]["bpm"] == 120 and codes["old"]["sync"] == "", str(codes["old"]))
    check("and restored, the lock runs at the code's tempo: 1/2 at 96 is 0.8 Hz, with 0.9 kept for later",
          codes["back"] == {"bpm": 96, "sync": "1/2", "rate": 0.8, "free": 0.9}, str(codes["back"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the clock keeps time, and the oscillators keep it with it")
