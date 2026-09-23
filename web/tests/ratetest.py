"""The sample-rate audit: what this instrument assumes about 44100, and what
it does on a machine that does not run there.

Most converters are at 48 kHz and plenty are at 96. Nothing here used to see
one: the generator was hard-wired to 44100 and the analyser-backed sources
took whatever the context gave them, so the two halves of the page could have
been at different rates and nothing would have said so.

Three kinds of assumption are checked, and they fail in different ways.

A DURATION WRITTEN AS A SAMPLE COUNT silently changes meaning. The trigger's
minimum search room was 512 samples - 11.6 ms at 44.1 kHz and 5.3 at 96, so
the rule that drops the lag lane got twice as permissive on a faster
converter. The automatic lock listened to 8192 samples, which is 186 ms at
44.1 kHz and 85 at 96: under two periods of the lowest pitch it will accept,
and not enough crossings to believe. Both are durations now, and the second
one is checked against `estimatePeriod` at each rate rather than asserted.

A CAPACITY MEASURED IN SAMPLES is a length of time that halves when the
converter doubles. An AnalyserNode holds at most 32768 frames - a Web Audio
ceiling, not a choice - so the longest window this scope can draw is 743 ms at
44.1 kHz and 341 at 96. The slowest timebase asks for 500. That was already
reported, as a short trace with the shortfall underneath it; the point of the
audit is that it is now said on the control before it is chosen.

A TIME CONSTANT IN THE AUDIO GRAPH may be either, and the only way to know is
to render it. The monitor chain quotes six milliseconds of limiter lookahead
in the latency figure on the panel. At 44.1 kHz that is 264 samples, which is
equally consistent with a fixed block of 256 and a rounding error. Rendering
at four rates says which it is.
"""
import math, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

# The rates this page is expected to meet. 22050 is not a converter anyone
# has, but it is the other side of 44100 and an assumption that scales one way
# and not the other shows up there.
RATES = [22050, 44100, 48000, 96000]
ANALYSER_FRAMES = 32768        # the Web Audio ceiling on fftSize

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


# A source with no audio graph behind it, so the capture path can be run at a
# rate no converter in this container offers. It answers the four questions
# `capture` asks - rate, capacity, channels, a window - and nothing else.
STANDIN = """(rate, capacity, hz) => {
  const buf = [new Float32Array(capacity), new Float32Array(capacity)];
  for (let i = 0; i < capacity; i++) {
    buf[0][i] = 0.5 * Math.sin(2 * Math.PI * hz * i / rate);
    buf[1][i] = 0.5 * Math.cos(2 * Math.PI * hz * i / rate);
  }
  return {
    kind: 'tone', settings: null,
    get sampleRate() { return rate; },
    get capacity() { return capacity; },
    get channels() { return 2; },
    tick() {}, stop() {}, setMonitor() { return false; },
    describe: () => 'stand-in at ' + rate + ' Hz',
    getLatestWindow: (n) => buf.map((b) => b.subarray(Math.max(0, capacity - n))),
  };
}"""

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
    p.evaluate("(src) => { window.__standin = eval(src); }", STANDIN)

    print("\n--- the rate this machine runs at, and where it came from ---")
    where = p.evaluate("""async () => {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const real = ctx.sampleRate;
      if (ctx.close) ctx.close();
      return {
        real, asked: deviceRate(), from: deviceRateFrom,
        generator: state.source.sampleRate,
        fallback: FALLBACK_RATE,
      };
    }""")
    check("the page asks the machine rather than assuming",
          where["asked"] == where["real"] and where["from"] == "measured",
          "%d Hz, %s" % (where["asked"], where["from"]))
    check("and the generator runs at that rate, not at the old constant",
          where["generator"] == where["real"],
          "generator %d Hz, machine %d Hz" % (where["generator"], where["real"]))
    # Not a tautology only because this container happens to run at 44100: if
    # it did not, the check above would be the whole story. Said out loud so a
    # reader on a 48 kHz machine knows which line is doing the work.
    print("    (this container reports %d Hz; the fallback is %d)"
          % (where["real"], where["fallback"]))

    moved = p.evaluate("""() => {
      const was = deviceRate();
      noteDeviceRate(96000);
      const after = deviceRate();
      const built = makeToneSource(96000).sampleRate;
      noteDeviceRate(was);
      return { was, after, back: deviceRate(), built };
    }""")
    check("a source that opens a real context corrects the answer",
          moved["after"] == 96000 and moved["back"] == moved["was"], str(moved))
    check("and a generator can be built at a stated rate",
          moved["built"] == 96000, str(moved["built"]))
    # And a generator built with no rate given takes the corrected one. This
    # container happens to run at 44.1 kHz, so every check above is also
    # satisfied by a generator still hard-wired to the old constant - a
    # mutation putting 44100 back survived all of them. Moving the memo first
    # is what tells the two apart without a converter that does.
    follows = p.evaluate("""() => {
      const was = deviceRate();
      noteDeviceRate(48000);
      const built = makeToneSource().sampleRate;
      noteDeviceRate(was);
      return { built, restored: makeToneSource().sampleRate, was };
    }""")
    check("and one built with no rate given follows the machine, not a constant",
          follows["built"] == 48000 and follows["restored"] == follows["was"],
          str(follows))

    print("\n--- what the buffer can serve, at four rates ---")
    # The invariant the give-way order in `capture` exists to keep, held to at
    # every rate and every timebase: never ask the buffer for more than it
    # has. 36 combinations, and the ones that cannot be served have to say so
    # rather than quietly drawing a short window.
    budget = p.evaluate("""([rates, frames]) => {
      const was = state.source, wasTb = state.timebase, wasRun = state.running;
      const out = [];
      state.running = false;
      for (const rate of rates) {
        state.source = window.__standin(rate, frames, 220);
        const rows = [];
        for (let i = 0; i < TIMEBASE.length; i++) {
          state.timebase = i;
          const f = capture();
          rows.push({
            ms: TIMEBASE[i] * DIVS_X,
            asked: f.asked, capacity: f.capacity,
            starved: state.starved,
            fits: f.asked <= f.capacity,
            searchRoom: f.asked - f.length,
          });
        }
        out.push({ rate, ceiling: timebaseCeiling(state.source),
                   budget: windowBudget(state.source), rows });
      }
      state.source = was; state.timebase = wasTb; state.running = wasRun;
      return out;
    }""", [RATES, ANALYSER_FRAMES])

    # The give-way order, stated as the assertion it is. The window is the
    # picture and never shrinks - that is a decision, not an oversight - so
    # the invariant is not "never over-ask". It is: as long as the window
    # itself fits, everything else gives way until the whole fetch fits; and
    # once the window alone is too big, there is nothing left to give and the
    # over-ask is exactly the window's own shortfall, reported as starvation.
    #
    # The first draft of this check asserted the simpler, wronger thing and
    # failed at 96 kHz on the slowest sweep, which is the case the design
    # deliberately handles by drawing short and saying so.
    broke = []
    for row in budget:
        for r in row["rows"]:
            fits = r["asked"] <= r["capacity"]
            if r["starved"] == 0 and not fits:
                broke.append((row["rate"], r["ms"], "over-asked with room to spare"))
            if r["starved"] > 0 and r["asked"] - r["capacity"] != r["starved"]:
                broke.append((row["rate"], r["ms"],
                              "over-ask %d, starvation reported %d"
                              % (r["asked"] - r["capacity"], r["starved"])))
            if r["starved"] > 0 and r["searchRoom"] != 0:
                broke.append((row["rate"], r["ms"],
                              "kept %d samples of search room it could not afford"
                              % r["searchRoom"]))
    check("everything but the window gives way before the buffer is over-asked",
          not broke, str(broke[:3]))

    for row in budget:
        print("    %5d Hz: %6.0f ms of history, ceiling %g ms/div"
              % (row["rate"], row["budget"]["longestMs"],
                 row["rows"][row["ceiling"]]["ms"] / 10))

    # And the ceiling is not decoration: it is exactly the last timebase that
    # comes back whole. Above it the buffer is short; at it and below, not.
    wrong = []
    for row in budget:
        for i, r in enumerate(row["rows"]):
            clean = r["starved"] == 0 and r["searchRoom"] > 0
            if clean != (i <= row["ceiling"]):
                wrong.append((row["rate"], r["ms"], i, row["ceiling"], r["starved"]))
    check("and the ceiling the panel shows is exactly where starvation starts",
          not wrong, str(wrong[:3]))

    # The trigger's share of the buffer, at the boundary where it is the only
    # thing that matters. Everywhere else the timebases are far enough apart
    # that a window either fits with room to spare or does not fit at all, so
    # a ceiling that forgot the trigger needs somewhere to look would give the
    # same answers - that mutation survived the check above. Tuned capacities
    # are where the term earns its place: a buffer exactly as long as the
    # window leaves the trigger nothing, and one window plus the floor is the
    # first that does.
    boundary = p.evaluate("""() => {
      const was = state.source, wasTb = state.timebase, wasRun = state.running;
      state.running = false;
      const rate = 48000, i = 5;                   // 5 ms/div, a 50 ms window
      const length = Math.round(TIMEBASE[i] * DIVS_X * rate / 1000);
      const floor = Math.round(LAG_MIN_SPAN_SECONDS * rate);
      const ceilingAt = (capacity) => {
        state.source = window.__standin(rate, capacity, 220);
        return timebaseCeiling(state.source);
      };
      const exact = ceilingAt(length);
      const justUnder = ceilingAt(length + floor - 1);
      const justOver = ceilingAt(length + floor);
      state.source = was; state.timebase = wasTb; state.running = wasRun;
      return { i, length, floor, exact, justUnder, justOver };
    }""")
    print("    a %d-sample window at 48 kHz: ceiling %d with a buffer that exact, "
          "%d one sample under the floor, %d at it"
          % (boundary["length"], boundary["exact"],
             boundary["justUnder"], boundary["justOver"]))
    check("a buffer exactly as long as the window does not count as serving it",
          boundary["exact"] < boundary["i"] and boundary["justUnder"] < boundary["i"],
          str(boundary))
    check("and one window plus the search floor is the first that does",
          boundary["justOver"] == boundary["i"], str(boundary))

    # The halving, as the number that makes the point: the same buffer is less
    # than half the history at 96 kHz that it is at 44.1.
    at441 = next(r for r in budget if r["rate"] == 44100)["budget"]["longestMs"]
    at96 = next(r for r in budget if r["rate"] == 96000)["budget"]["longestMs"]
    check("the same 32768 frames are less than half the time at 96 kHz",
          abs(at441 / at96 - 96000 / 44100) < 0.01,
          "%.0f ms against %.0f ms" % (at441, at96))
    check("and 96 kHz cannot serve the slowest sweep the panel offers",
          next(r for r in budget if r["rate"] == 96000)["ceiling"] < len(budget[0]["rows"]) - 1
          and next(r for r in budget if r["rate"] == 44100)["ceiling"] == len(budget[0]["rows"]) - 1,
          "ceilings %s" % [r["ceiling"] for r in budget])

    print("\n--- the two durations that used to be sample counts ---")
    durations = p.evaluate("""(rates) => rates.map((rate) => ({
      rate,
      minSpan: Math.round(LAG_MIN_SPAN_SECONDS * rate),
      probe: Math.round(LAG_PROBE_SECONDS * rate),
      minSpanMs: LAG_MIN_SPAN_SECONDS * 1000,
      probeMs: LAG_PROBE_SECONDS * 1000,
    }))""", RATES)
    for d in durations:
        print("    %5d Hz: search floor %5d samples, probe %6d samples"
              % (d["rate"], d["minSpan"], d["probe"]))
    check("the search floor is one duration at every rate",
          len({round(d["minSpanMs"], 6) for d in durations}) == 1
          and durations[1]["minSpan"] == 551,
          "%.1f ms, %d samples at 44.1 kHz" % (durations[0]["minSpanMs"], durations[1]["minSpan"]))
    check("and the probe is four periods of the lowest pitch the lock accepts",
          all(d["probe"] / d["rate"] >= 4 / 20 - 1e-9 for d in durations),
          "%.0f ms, %d samples at 96 kHz" % (durations[0]["probeMs"], durations[3]["probe"]))

    # And the floor behaviourally rather than arithmetically: at what point
    # does the lag lane actually get dropped? `capture` drops it when the room
    # left after reserving the delay falls under the floor, so sweeping the
    # buffer size finds that point exactly. A floor written as a sample count
    # would put it at a different millisecond on every converter, which is the
    # whole complaint; written as a duration it lands on the same one.
    floor = p.evaluate("""(rates) => {
      const was = { src: state.source, tb: state.timebase, run: state.running,
                    on: state.lagOn, auto: state.lagAuto, ms: state.lagMs };
      state.running = false;
      state.timebase = 2;                          // 0.5 ms/div, a short window
      state.lagOn = true; state.lagAuto = false; state.lagMs = 5;
      const out = rates.map((rate) => {
        const length = Math.round(TIMEBASE[state.timebase] * DIVS_X * rate / 1000);
        const lead = Math.ceil(0.005 * rate);
        let smallest = null;
        // Downwards from comfortable to cramped, one per cent at a time.
        for (let extra = Math.round(0.05 * rate); extra >= 0;
             extra -= Math.max(1, Math.round(0.0002 * rate))) {
          state.source = window.__standin(rate, length + lead + extra, 220);
          capture();
          if (state.lagActual > 0) smallest = extra; else break;
        }
        return { rate, roomSamples: smallest,
                 roomMs: smallest === null ? null : smallest / rate * 1000 };
      });
      state.source = was.src; state.timebase = was.tb; state.running = was.run;
      state.lagOn = was.on; state.lagAuto = was.auto; state.lagMs = was.ms;
      return out;
    }""", RATES)
    for f in floor:
        print("    %5d Hz: lag survives down to %s samples of room left (%s ms)"
              % (f["rate"], f["roomSamples"],
                 "none" if f["roomMs"] is None else "%.2f" % f["roomMs"]))
    spread = ([f["roomMs"] for f in floor if f["roomMs"] is not None])
    check("the lag is dropped at the same millisecond of room on every converter",
          len(spread) == len(RATES) and max(spread) - min(spread) < 0.4,
          "%.2f to %.2f ms, against a floor of 12.50"
          % (min(spread or [0]), max(spread or [0])))

    # The one that matters, measured rather than asserted - and the first
    # draft of this got the pitch wrong by reasoning instead of measuring. At
    # 30 Hz the old 8192-sample probe locks perfectly well even at 96 kHz:
    # 85 ms is two and a half periods, which on a clean sine is three
    # crossings, two gaps, and a jitter of exactly nought.
    #
    # Sweeping it downward says where it really breaks. From 21 to 25 Hz at
    # 96 kHz the old probe gets one gap and `estimatePeriod` reports infinite
    # jitter - "no evidence at all", which is the honest answer and which
    # `lagLockUpdate` rejects. At 44.1 kHz the same pitches lock cleanly. So
    # the boundary the change moves sits between 25 and 30 Hz on a fast
    # converter, and 25 is where this stands.
    lock = p.evaluate("""([rates, frames]) => rates.map((rate) => {
      const src = window.__standin(rate, frames, 25);
      const now = Math.round(LAG_PROBE_SECONDS * rate);
      const old = 8192;
      const at = (n) => {
        const got = estimatePeriod(src.getLatestWindow(Math.min(n, frames))[0], rate);
        return got === null ? null : { hz: got.hz, jitter: got.jitter };
      };
      return { rate, now: at(now), old: at(old), max: LAG_JITTER_MAX };
    })""", [RATES, ANALYSER_FRAMES])
    for row in lock:
        print("    %5d Hz: as a duration %s, as 8192 samples %s"
              % (row["rate"],
                 "no lock" if row["now"] is None
                 else "%.2f Hz, jitter %.4f" % (row["now"]["hz"], row["now"]["jitter"]),
                 "no lock" if row["old"] is None
                 else "%.2f Hz, jitter %.4f" % (row["old"]["hz"], row["old"]["jitter"])))
    good = [r for r in lock if r["now"] is not None
            and abs(r["now"]["hz"] - 25) < 1 and r["now"]["jitter"] <= r["max"]]
    check("a 25 Hz tone locks at every rate now",
          len(good) == len(RATES), "%d of %d" % (len(good), len(RATES)))
    fast = next(r for r in lock if r["rate"] == 96000)
    slow = next(r for r in lock if r["rate"] == 44100)
    check("and the old sample-count probe could not, at 96 kHz but not at 44.1",
          (fast["old"] is None or fast["old"]["jitter"] > fast["max"])
          and slow["old"] is not None and slow["old"]["jitter"] <= slow["max"],
          "96 kHz %s, 44.1 kHz %s" % (fast["old"], slow["old"]))

    print("\n--- the audio graph, rendered at four rates ---")
    # Six milliseconds of limiter lookahead is quoted in the latency figure on
    # the panel. If it were a fixed block of frames the figure would be wrong
    # everywhere but 44.1 kHz, and nothing on the page would have said so.
    LOOK = """async (rate) => {
      const frames = Math.round(rate * 0.3);
      const ctx = new OfflineAudioContext(2, frames, rate);
      const buffer = ctx.createBuffer(2, frames, rate);
      const at = Math.round(rate * 0.1);
      buffer.getChannelData(0)[at] = 1; buffer.getChannelData(1)[at] = 1;
      const src = ctx.createBufferSource(); src.buffer = buffer;
      const chain = makeMonitorChain(ctx);
      src.connect(chain.input);
      monitorChains.delete(chain);
      src.start();
      const out = await ctx.startRendering();
      const d = out.getChannelData(0);
      let best = 0, peak = 0;
      for (let i = 0; i < frames; i++) {
        const v = Math.abs(d[i]);
        if (v > peak) { peak = v; best = i; }
      }
      return { rate, samples: best - at, ms: (best - at) / rate * 1000,
               quoted: MONITOR_LOOKAHEAD_MS };
    }"""
    looks = [p.evaluate(LOOK, r) for r in RATES]
    for l in looks:
        print("    %5d Hz: %4d samples, %.3f ms" % (l["rate"], l["samples"], l["ms"]))
    check("the limiter's lookahead is a time, not a block of frames",
          all(abs(l["ms"] - looks[0]["ms"]) < 0.05 for l in looks)
          and len({l["samples"] for l in looks}) == len(RATES),
          "%.3f ms across %s samples" % (looks[0]["ms"], [l["samples"] for l in looks]))
    check("so the six milliseconds the panel quotes is right at every rate",
          all(abs(l["ms"] - l["quoted"]) < 0.05 for l in looks),
          "quoted %g ms, measured %.3f" % (looks[0]["quoted"], looks[0]["ms"]))

    # The AC corner is one number shared by the picture and the speakers, and
    # the coefficients are derived from it and the rate. A corner that drifted
    # with the converter would put the two implementations at different
    # frequencies on the same machine.
    corners = p.evaluate("""(rates) => rates.map((rate) => {
      const c = dcBlockerCoefficients(10, rate);
      return {
        rate,
        atCorner: 20 * Math.log10(dcBlockerMagnitude(c, 10, rate)),
        atDc: dcBlockerMagnitude(c, 0, rate),
        wayUp: 20 * Math.log10(dcBlockerMagnitude(c, 1000, rate)),
      };
    })""", RATES)
    for c in corners:
        print("    %5d Hz: %.3f dB at the corner, %.4f dB at 1 kHz"
              % (c["rate"], c["atCorner"], c["wayUp"]))
    check("the AC corner is at the corner at every rate",
          all(abs(c["atCorner"] + 3.0) < 0.06 for c in corners),
          "worst %.3f dB" % max(abs(c["atCorner"] + 3.0) for c in corners))
    # Flat above the corner, but not equally flat: a ten hertz corner is a
    # larger fraction of 22 kHz than of 96, so the slowest converter has the
    # most of the blocker still showing at a kilohertz. A fiftieth of a
    # decibel at the worst of them, which is two orders below anything a meter
    # on this page resolves.
    check("and it stops nothing at DC and a fiftieth of a decibel at 1 kHz",
          all(c["atDc"] < 1e-12 for c in corners)
          and all(abs(c["wayUp"]) < 0.02 for c in corners),
          "worst %.4f dB at 1 kHz, on the slowest converter"
          % max(abs(c["wayUp"]) for c in corners))

    print("\n--- and the spectrum, which changes resolution with the rate ---")
    # FFT_SIZE is a count of samples, so the bin width is the rate over it:
    # 21.5 Hz at 44.1 kHz and 46.9 at 96. The analysis is coarser on a faster
    # converter, which is worth knowing and is not a bug. What would be a bug
    # is a guard band written in bins that stops meaning the same thing - the
    # local-maximum test looks six bins either side of the line - so the same
    # tone is put through at every rate and the answers have to agree.
    spectra = p.evaluate("""([rates, frames]) => rates.map((rate) => {
      const src = window.__standin(rate, frames, 220);
      computeSpectrum(src.getLatestWindow(FFT_SIZE)[0]);
      const h = analyseHarmonics(rate);
      return { rate, binHz: rate / FFT_SIZE,
               hz: h ? h.hz : null, thd: h ? h.thd : null };
    })""", [RATES, ANALYSER_FRAMES])
    for s in spectra:
        print("    %5d Hz: %.1f Hz bins, fundamental %s"
              % (s["rate"], s["binHz"],
                 "none" if s["hz"] is None else "%.1f Hz, THD %.3f%%"
                 % (s["hz"], (s["thd"] or 0) * 100)))
    check("a 220 Hz sine is found at every rate",
          all(s["hz"] is not None and abs(s["hz"] - 220) <= s["binHz"] for s in spectra),
          str([None if s["hz"] is None else round(s["hz"], 1) for s in spectra]))
    check("and it is called clean at every rate, however wide the bins are",
          all(s["thd"] is not None and s["thd"] < 0.02 for s in spectra),
          str([None if s["thd"] is None else round(s["thd"] * 100, 3) for s in spectra]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the rate is measured, and every assumption about it is an assertion")
