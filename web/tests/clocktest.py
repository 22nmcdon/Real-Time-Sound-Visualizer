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
# What is left is the face. Two pages:
# - ?brain=js, for what the face says about the tempo: the LFO card's
#   reading and its Rate slider, the tempo row's readings and the Bar row's
#   button and reading. All of them are drawn from the page's own `lfos` and
#   `transport` (lfoRateReading, syncClockPanel), which on the default site
#   is the page's brain stepping beside the instrument's clock, and nothing
#   the instrument publishes writes them. On the default they would pass for
#   the page's reason, so they stay here until step 5 points the face at the
#   instrument's clock (STAGE5-INVENTORY.md, section 4, the face's leans).
# - the default, for setup codes, read off the face's setup (snapshot), with
#   the tempo and the locks set by real input events.
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
    p.goto(f"file://{ART}/scope.html?brain=js"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    print("\n--- an oscillator locked to the tempo ---")
    lock = p.evaluate("""() => {
      setView('bench'); openModCard('lfo1');
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
      out.readingFree = document.getElementById('lfoRateValue0').textContent;
      out.enabled = !document.getElementById('lfoRate0').disabled;
      setTempo(120);
      return out;
    }""")
    print("    %s" % lock)
    # Were: "at 120, 1/4 is 2 Hz, a bar 0.5, a quaver triplet 6 and four bars
    # 0.125" and "it follows the tempo: 1/4 at 90 is 1.5 Hz", the page's
    # lfos[0].rate on ?brain=js - core/tests/pieces/clock.py's now.
    check("the reading says so, and the Rate slider stands aside while it is locked",
          lock["reading"] == "2.00 Hz · 1/4" and lock["disabled"], str(lock))
    # Was "and let go, it is back at the slider's 0.37 Hz", lfos[0].rate with
    # the slider enabled. The rate's half is the core's menu path (restore.h's
    # lfoSync, which parity's menus section holds to the page's); the face's
    # half stays: the slider given back, and its reading the slider's.
    check("and let go, the Rate slider is back and reads the slider's 0.37 Hz",
          lock["enabled"] and lock["readingFree"].startswith("0.37 Hz"), str(lock))

    # Was "and the running oscillator goes round at it: 1/8 at 120, four times
    # a second", lfos[0].value's crossings counted over two real seconds on
    # ?brain=js. core/tests/pieces/clock.py counts them over two seconds of
    # the core's generator stepping its oscillators, with no timers.

    # Tap tempo was four checks here on ?brain=js, the page's clockTap at
    # made-up times: taps half a second apart are 120 and restart the locked
    # oscillator, one tap is no tempo, the mean of the last four gaps is 129,
    # and after a pause it starts again at 150 (with the tempo slider reading
    # 150). The first four are core/tests/pieces/clock.py's; the slider's
    # reading went with them, since it is syncClockPanel writing the page's
    # own transport.set, which a direct clockTap set and no tap on the site
    # sends to the instrument.

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
      lfos[0].sync = '';
      return { running, stopped };
    }""")
    print("    %s" % midiclock)
    r = midiclock["running"]
    # Were, on ?brain=js: "25 ticks at 120, jittered, read as 120", the
    # locked oscillator's rate following it, the tempo handed back half a
    # second after, "Start restarts the locked oscillators, and Continue does
    # not", and "a clock byte in the middle of a note-on is a tick, and the
    # note lands with its own velocity" (the page's midiBytes). All
    # core/tests/pieces/clock.py's now. What stays is what the tempo row
    # says while a clock runs and once it stops - the page's transport, as
    # the top of this file says.
    check("while a MIDI clock runs the tempo slider stands aside and the row says the clock's tempo",
          r["disabled"] and r["reading"] == "120 BPM" and r["clock"] == "from MIDI clock", str(r))
    s = midiclock["stopped"]
    check("half a second after the last tick the slider is back and the row says internal",
          s == {"bpm": 90, "from": "internal", "disabled": False, "clock": "internal"}, str(s))

    # The bar was seventeen checks here on ?brain=js, the page's transport*,
    # midiRealtime, clockStep, clockTap and scoreTick at times far ahead of
    # its frames, phosphor.grid lit by hand and the source's strike wrapped:
    # the bar moving from nought, a tempo change going on from where it is,
    # Stop standing, Start the one with the locked oscillators restarted, the
    # score joining the bar mid-bar, Start bringing it to column nought, the
    # score stopped striking nothing, a MIDI Start waiting for the first tick,
    # the bar counted in ticks and never guessed past the next, Stop and
    # Continue, a clock that stops, a Start no clock follows, and taps while
    # running and stopped. Every one is core/tests/pieces/clock.py's now, on
    # the core's clock and score at the run's times.

    print("\n--- the Bar row ---")
    panel = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      showControl('transportPlay');
      const shown = el.transportPlay.offsetHeight > 0;
      // A second in first, so the bar has somewhere to stand other than the
      // 1.1 a reading that never moved would also show.
      // At 120: the bar section that ran before this until batch 2 left the
      // tempo there, and the MIDI clock's left it at 90.
      setTempo(120); transport.bpm = transport.set;
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

    print("\n--- the instrument reports its clock (5a), beside the page's own ---")
    # Since stage 5, step 5a the instrument posts its clock with its
    # readings (Instrument::clockServed): each oscillator's rate, the tempo
    # in force and the slider's, where the tempo comes from, whether the bar
    # runs and where it is, and the score's playhead. The face's panels still
    # draw the page's own lfos, transport and score until 5b points them at
    # these; this holds the two together as they stand. Set by real input
    # events, which reach both: the tempo, LFO 1 locked, LFO 2 free at its
    # slider, the score on.
    p.locator("#trace").click(position={"x": 5, "y": 5})   # the press a browser waits for
    p.wait_for_timeout(900)
    clk = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const fire = (id, v, kind) => { const e = document.getElementById(id); e.value = v; e.dispatchEvent(new Event(kind)); };
      const read = () => {
        const c = state.source.clock, now = performance.now();
        return { inst: c && { rates: c.rates, bpm: c.bpm, set: c.set, from: c.from, running: c.running, beat: c.beat,
                              score: c.score },
                 page: { rates: [lfos[0].rate, lfos[1].rate], bpm: transport.bpm, set: transport.set, from: transport.from,
                         running: transport.running, beat: transportBeat(now), score: { on: score.on, col: score.col } },
                 t: now };
      };
      showControl('tempo'); fire('tempo', '84', 'input');
      openModCard('lfo1'); fire('lfoSync0', '1/8', 'change');
      openModCard('lfo2'); fire('lfoSync1', '', 'change'); fire('lfoRate1', '37', 'input');
      showControl('scoreOn'); const box = document.getElementById('scoreOn'); box.checked = true; box.dispatchEvent(new Event('change'));
      await wait(700);
      const a = read(); await wait(1000); const b = read();
      // The null: a tempo the page alone is told (setTempo, no input event, so no message).
      setTempo(100); await wait(400);
      const c = read();
      return { a, b, c, host: state.source.kind };
    }""")
    a, bb, c = clk["a"], clk["b"], clk["c"]
    print("    instrument %s\n    page       %s" % (a["inst"], a["page"]))
    ok = a["inst"] is not None
    same = lambda r: (r["inst"]["rates"] == r["page"]["rates"] and r["inst"]["bpm"] == r["page"]["bpm"]
                      and r["inst"]["set"] == r["page"]["set"] and r["inst"]["from"] == r["page"]["from"]
                      and r["inst"]["running"] == r["page"]["running"])
    check("the instrument posts its clock, and it is the page's: both rates, the tempo in force and the slider's, where it comes from, running",
          clk["host"] == "host" and ok and same(a) and a["inst"]["rates"] == [84 / 60 * 2, 0.37] and a["inst"]["bpm"] == 84,
          "%s against %s" % (a["inst"], a["page"]))
    check("null: a tempo told to the page alone is told apart", ok and not same(c) and c["inst"]["bpm"] == 84 and c["page"]["bpm"] == 100,
          "%s against %s" % (c["inst"] and c["inst"]["bpm"], c["page"]["bpm"]))
    swapped = dict(a, inst=dict(a["inst"], rates=a["inst"]["rates"][::-1])) if ok else a
    check("null: and the comparison fails with the two oscillators' rates the wrong way round", not same(swapped))
    # The bar: the instrument's goes round at the tempo, a beat every 60/84
    # of a second, and so does the page's. Where each is differs - the
    # page's from its own Start, the instrument's from when it was made, the
    # transport's Start and Stop being the page's alone (not a hand the
    # instrument is sent; 5b's) - so the two are held to the same speed, and
    # the gap is printed for 5b.
    secs = (bb["t"] - a["t"]) / 1000
    inst_bpm = (bb["inst"]["beat"] - a["inst"]["beat"]) / secs * 60 if ok else 0
    page_bpm = (bb["page"]["beat"] - a["page"]["beat"]) / secs * 60
    print("    the bar: the instrument's at beat %.2f, the page's at %.2f; over %.2f s each went at %.1f and %.1f BPM"
          % (a["inst"]["beat"], a["page"]["beat"], secs, inst_bpm, page_bpm))
    check("the instrument's bar goes round at the tempo it posts, as the page's does, to a twentieth",
          abs(inst_bpm - 84) < 84 / 20 and abs(page_bpm - 84) < 84 / 20, "%.1f and %.1f" % (inst_bpm, page_bpm))
    check("null: and not at the slider's old 96", abs(inst_bpm - 96) > 84 / 20, "%.1f" % inst_bpm)
    # The score's playhead: on in both, and moving in both.
    si, sp = (bb["inst"]["score"], bb["page"]["score"]) if ok else ({}, {})
    check("the score is on in both, and the instrument's playhead posted and moving",
          ok and si["on"] and sp["on"] and si["col"] >= 0 and (si["col"] != a["inst"]["score"]["col"] or si["steps"] != a["inst"]["score"]["steps"]),
          "instrument %s, page %s" % (si, sp))
    check("no page errors on the default", not bad, "; ".join(bad[:3]))
    b.close()


print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the clock keeps time, and the oscillators keep it with it")
