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
# Stage 5, step 3, batch 2 (13 Nov). The clock's numbers - locked rates,
# taps, a MIDI clock, Start, Stop and Continue, the bar, the score joining it
# and the byte parser - were this suite's on ?brain=js, calling the page's
# clockTap, setTempo, clockStep, midiBytes, midiRealtime, transport* and
# scoreTick at made-up times. They are core/tests/pieces/clock.py's now,
# asserted on the core's clock (clock_cpp, score_cpp, keyboard_cpp) with a
# null each, and parity runs them. Each old site below says what it was.
#
# What is left is the face, on the default page since stage 5, step 5b: the
# LFO card's reading and its Rate slider, the tempo row, the Bar row and the
# score's playhead, drawn from the instrument's posted clock, each with a
# null that tells the page's own clock something alone; and setup codes,
# read off the face's setup (snapshot), with the tempo and the locks set by
# real input events.
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
    # Stage 5, step 5b (14 Nov): the face's clock is the instrument's. The LFO
    # card's reading, the tempo row and the Bar row were drawn from the page's
    # own lfos and transport, beside the instrument's clock, and were checked
    # on ?brain=js for that reason. They read what the instrument posts now
    # (Instrument::clockServed, instrumentClock in scope.html), so they are
    # checked on the default, moved by real input events and the bytes a port
    # would hand over - and every row has a null that tells the page's own
    # clock something the instrument is not told, so a face that still read
    # the page's would follow it and go red.
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.locator("#trace").click(position={"x": 5, "y": 5})   # the press a browser waits for
    p.wait_for_timeout(900)

    print("\n--- an oscillator locked to the tempo ---")
    lock = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const fire = (id, v, kind) => { const e = document.getElementById(id); e.value = v; e.dispatchEvent(new Event(kind)); };
      const reading = () => document.getElementById('lfoRateValue0').textContent;
      showControl('tempo'); fire('tempo', '120', 'input');
      openModCard('lfo1');
      fire('lfoRate0', '37', 'input');       // 0.37 Hz, free
      fire('lfoSync0', '1/4', 'change');
      await wait(400);
      const out = { host: state.source.kind, served: !!instrumentClock(), reading: reading(),
                    disabled: document.getElementById('lfoRate0').disabled };
      /* The null: the page's own clock told a tempo the instrument is not
         (setTempo, no input event, so no message), and the page's oscillator
         the rate its lock would have there, 1.00 Hz at 60. The face says what
         the instrument plays. */
      setTempo(60); const kept = lfos[0].rate; lfos[0].rate = 1; await wait(400);
      out.pageAlone = { reading: reading(), pageBpm: transport.bpm, pageRate: lfos[0].rate };
      lfos[0].rate = kept;
      showControl('tempo'); fire('tempo', '90', 'input'); await wait(400);
      out.at90 = reading();
      openModCard('lfo1'); fire('lfoSync0', '', 'change'); await wait(400);
      out.readingFree = reading();
      out.enabled = !document.getElementById('lfoRate0').disabled;
      showControl('tempo'); fire('tempo', '120', 'input');
      return out;
    }""")
    print("    %s" % lock)
    check("the default page plays the instrument, and the face has its clock", lock["host"] == "host" and lock["served"], str(lock))
    # Was, on ?brain=js, the page's own lfos[0] (lfoRateReading). The rate's
    # number is the instrument's own now (core/tests/pieces/clock.py has it).
    check("the reading says so, and the Rate slider stands aside while it is locked",
          lock["reading"] == "2.00 Hz · 1/4" and lock["disabled"], str(lock))
    check("null: a tempo told to the page's clock alone moves the page's and not the reading",
          lock["pageAlone"]["pageBpm"] == 60 and lock["pageAlone"]["pageRate"] == 1
          and lock["pageAlone"]["reading"] == "2.00 Hz · 1/4", str(lock["pageAlone"]))
    check("and the tempo slider, which the instrument hears, does: 1/4 at 90 is 1.50 Hz",
          lock["at90"] == "1.50 Hz · 1/4", lock["at90"])
    check("and let go, the Rate slider is back and reads the slider's 0.37 Hz",
          lock["enabled"] and lock["readingFree"].startswith("0.37 Hz"), str(lock))

    # Tap tempo was four checks here on ?brain=js, the page's clockTap at
    # made-up times; they are core/tests/pieces/clock.py's. A tap on the
    # site reaches the instrument as the tempo slider moved (5b, the tap's
    # listener), which the next row reads.
    print("\n--- a tap ---")
    tap = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      showControl('tempoTap');
      const at = [], beforeBeat = instrumentClock().beat;
      for (let i = 0; i < 4; i++) { at.push(performance.now()); document.getElementById('tempoTap').click(); if (i < 3) await wait(400); }
      await wait(300);
      // The last tap is the one on the instrument's bar (tempoTap): 300 ms after it, under a beat in.
      const afterBeat = instrumentClock().beat;
      // The tempo the taps' own gaps make, as clockTap works it out: about 150 at 400 ms, more with a click's latency.
      const want = Math.round(60000 / ((at[3] - at[0]) / 3));
      return { row: el.tempoValue.textContent, inst: instrumentClock().set, want, beforeBeat, afterBeat };
    }""")
    print("    %s" % tap)
    check("taps about 400 ms apart reach the instrument, which takes their tempo, and the row says it",
          abs(tap["inst"] - tap["want"]) <= 1 and 100 < tap["inst"] <= 150 and tap["row"] == "%d BPM" % round(tap["inst"]), str(tap))
    check("null: and not the 120 it was at", tap["inst"] != 120 and tap["row"] != "120 BPM", str(tap))
    check("and the tap is the one on the instrument's bar, which was beats on before it",
          tap["beforeBeat"] > 1.5 and 0 <= tap["afterBeat"] < 1.2, "%.2f, then %.2f" % (tap["beforeBeat"], tap["afterBeat"]))

    print("\n--- MIDI clock ---")
    midiclock = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const fire = (id, v, kind) => { const e = document.getElementById(id); e.value = v; e.dispatchEvent(new Event(kind)); };
      showControl('tempo'); fire('tempo', '90', 'input'); await wait(200);
      // 30 ticks at 120 BPM, a crotchet being 24 of them, 20.833 ms apart, as a port hands them over in time.
      const gap = 60000 / 120 / 24, t0 = performance.now();
      for (let i = 0; i < 30; i++) {
        while (performance.now() < t0 + i * gap) await wait(1);
        midiBytes(Uint8Array.from([0xf8]), performance.now());
      }
      await wait(150);
      const row = () => ({ disabled: el.tempo.disabled, reading: el.tempoValue.textContent, clock: el.clockFrom.textContent });
      const running = Object.assign(row(), { inst: instrumentClock().bpm, from: instrumentClock().from });
      await wait(800);
      const stopped = Object.assign(row(), { from: instrumentClock().from });
      // The null: the page's own transport told it is on a MIDI clock at 200, which the instrument is not.
      transport.from = 'midi'; transport.bpm = 200; transport.ticks = [performance.now()];
      await wait(300);
      const pageAlone = row();
      transport.from = 'internal'; transport.bpm = transport.set; transport.ticks = [];
      return { running, stopped, pageAlone };
    }""")
    print("    %s" % midiclock)
    r = midiclock["running"]
    # Were, on ?brain=js: the clock read from its gaps and handed back, Start
    # and Continue, a clock byte inside a note (the page's midiBytes): all
    # core/tests/pieces/clock.py's. What stays is what the tempo row says.
    check("while a MIDI clock runs the tempo slider stands aside and the row says the instrument's clock's tempo",
          # About 120: a page's timers land ticks on a 4 ms grid, so the clock's
          # own reading of 120 is core/tests/pieces/clock.py's, to the tick.
          r["disabled"] and r["from"] == "midi" and abs(r["inst"] - 120) < 12
          and r["reading"] == "%d BPM" % round(r["inst"]) and r["clock"] == "from MIDI clock", str(r))
    s_ = midiclock["stopped"]
    check("half a second after the last tick the slider is back and the row says internal, at the slider's 90",
          s_ == {"disabled": False, "reading": "90 BPM", "clock": "internal", "from": "internal"}, str(s_))
    check("null: the page's own transport put on a clock at 200 leaves the row the instrument's",
          midiclock["pageAlone"] == {"disabled": False, "reading": "90 BPM", "clock": "internal"}, str(midiclock["pageAlone"]))

    print("\n--- the Bar row ---")
    # The bar's Start and Stop reach the instrument since 5b (HOST_CLICKS'
    # transportPlay, Instrument::press); until then they reached the page's
    # transport alone and the two bars were 1.9 beats apart (5a).
    panel = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const fire = (id, v, kind) => { const e = document.getElementById(id); e.value = v; e.dispatchEvent(new Event(kind)); };
      showControl('tempo'); fire('tempo', '120', 'input'); await wait(200);
      showControl('transportPlay');
      const shown = el.transportPlay.offsetHeight > 0;
      // Stopped and started, so the bar runs from the one; a second in, it is
      // somewhere other than the 1.1 a reading that never moved would show.
      if (instrumentClock().running) { el.transportPlay.click(); await wait(200); }
      el.transportPlay.click(); await wait(1100);
      el.transportPlay.click(); await wait(150);
      const stopped = [el.transportPlay.textContent, el.transportAt.textContent, instrumentClock().running, transport.running];
      await wait(600);
      const stillStopped = el.transportAt.textContent;
      restore(snapshot()); hostSendSetup(); await wait(300);
      const afterRestore = instrumentClock().running;
      el.transportPlay.click(); await wait(1150);
      const running = [el.transportPlay.textContent, el.transportAt.textContent, instrumentClock().running];
      return { shown, stopped, stillStopped, afterRestore, running };
    }""")
    print("    %s" % panel)
    check("the Bar row's button stops the instrument's bar, and the reading says where it stood",
          panel["shown"] and panel["stopped"][0] == "Start" and panel["stopped"][1].startswith("stopped at ")
          and panel["stopped"][2] is False and panel["stillStopped"] == panel["stopped"][1]
          and panel["stopped"][1] == "stopped at 1.3", str(panel))
    # The page's own transport was never told, and runs on: a face that read
    # it would say Stop, and a bar moving.
    check("null: the page's own transport is still running under a row that says stopped",
          panel["stopped"][3] is True, str(panel["stopped"]))
    check("loading a setup code leaves the bar stopped: the transport is playing, not the patch",
          panel["afterRestore"] is False, str(panel["afterRestore"]))
    check("and started again, it runs from the one: a little over a second at 120 is bar 1, beat 3",
          panel["running"][0] == "Stop" and panel["running"][1] == "1.3" and panel["running"][2] is True,
          str(panel["running"]))

    print("\n--- the score's playhead ---")
    head = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      showControl('scoreOn'); const box = document.getElementById('scoreOn'); box.checked = true; box.dispatchEvent(new Event('change'));
      await wait(900);
      // Where drawScorePlayhead puts the line, caught as it strokes, for a column of the page's own told by hand.
      const ctx = el.trace.getContext('2d'), moveTo = ctx.moveTo;
      let x = null;
      ctx.moveTo = function (a, b) { x = a; return moveTo.call(this, a, b); };
      score.col = 7;
      const col = instrumentClock().score.col;
      drawScorePlayhead();
      ctx.moveTo = moveTo;
      const at = (c) => plot.x + (c + 0.5) / PHOSPHOR_N * plot.w;
      const out = { col, x, inst: at(col), page: at(7), steps: instrumentClock().score.steps, pageCol: score.col };
      box.checked = false; box.dispatchEvent(new Event('change'));
      return out;
    }""")
    print("    %s" % head)
    check("the playhead is drawn at the instrument's column, which has moved",
          head["col"] >= 0 and head["steps"] > 0 and head["x"] is not None and abs(head["x"] - head["inst"]) < 1e-6, str(head))
    check("null: and not at a column the page's own score was given", head["col"] == 7 or abs(head["x"] - head["page"]) > 1, str(head))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

    print("\n--- setup codes, on the default ---")
    # On the default page, the site's instrument. These were on ?brain=js,
    # setting the tempo with setTempo(96) and the lock by writing lfos[1]
    # directly, and reading the page's transport.set and lfos[1] after
    # restore(). Here the tempo slider, LFO 2's Rate and Sync are moved by
    # real input events, and what is read is the face's setup (snapshot),
    # which is what a code and the instrument are given; the lock's rate at
    # the code's tempo, 0.8 Hz, is core/tests/pieces/clock.py's, and the
    # core's decode of a code is parity's restore section.
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)
    codes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const fire = (id, v, kind) => { const e = document.getElementById(id); e.value = v; e.dispatchEvent(new Event(kind)); };
      showControl('tempo'); fire('tempo', '96', 'input');
      openModCard('lfo2');
      fire('lfoRate1', '90', 'input');
      fire('lfoSync1', '1/2', 'change');
      const code = snapshot();
      const host = state.source && state.source.kind;
      restore({}); await wait(30);
      const oldCode = snapshot();
      restore(code); await wait(30);
      const backCode = snapshot();
      return { host, code: { bpm: code.bpm, l1y: code.l1y, l1r: code.l1r },
               old: { bpm: oldCode.bpm, l1y: oldCode.l1y },
               back: { bpm: backCode.bpm, l1y: backCode.l1y, l1r: backCode.l1r } };
    }""")
    print("    %s" % codes)
    check("the default page plays the instrument", codes["host"] == "host", str(codes["host"]))
    check("a code carries the tempo, each lock, and the slider's rate rather than the locked one",
          codes["code"] == {"bpm": 96, "l1y": "1/2", "l1r": 90}, str(codes["code"]))
    check("a code from before the clock is 120 and free",
          codes["old"] == {"bpm": 120, "l1y": ""}, str(codes["old"]))
    # Was "and restored, the lock runs at the code's tempo: 1/2 at 96 is 0.8
    # Hz, with 0.9 kept for later", read off the page's lfos[1]; the 0.8 is
    # the core's clock now (pieces/clock.py), and what the face keeps is the
    # code coming back whole, the slider's 0.9 with it.
    check("and restored, the code's tempo, lock and slider's rate come back as they went",
          codes["back"] == codes["code"], str(codes["back"]))
    check("null: the code from before the clock is not the code restored", codes["old"] != {"bpm": 96, "l1y": "1/2"})

    # The 5a rows that held the instrument's posted clock to the page's own
    # (rates, tempo, source, running, the bar's speed, the score's playhead)
    # went in 5b: the face reads the posted clock now, and the rows above
    # hold it there, each against the page's clock told something alone.
    check("no page errors on the default", not bad, "; ".join(bad[:3]))
    b.close()


print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the clock keeps time, and the oscillators keep it with it")
