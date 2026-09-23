"""The live band split: the shared stream, and what the graph is wired to.

Chromium's fake media device stands in for an instrument, so the whole path
really runs headless - but the two things most likely to ship broken (a second
getUserMedia call racing the first, and a live mix reaching the speakers) are
tested by watching the calls rather than by listening to the result.
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
    b = pw.chromium.launch(executable_path=CHROME, args=[
        "--autoplay-policy=no-user-gesture-required",
        "--use-fake-device-for-media-stream",
        "--use-fake-ui-for-media-stream",
    ])
    ctxb = b.new_context(permissions=["microphone"])
    p = ctxb.new_page()
    p.set_viewport_size({"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    # ---- the race: two opens in one tick, before either settles -------------
    print("\n--- one stream per device, even when two things ask at once ---")
    race = p.evaluate("""async () => {
      const real = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      let calls = 0, seen = null;
      navigator.mediaDevices.getUserMedia = (c) => {
        calls++; seen = c;
        return new Promise((res, rej) => setTimeout(() => real(c).then(res, rej), 120));
      };
      liveStreams.clear();

      // Both in the same tick, neither awaited: this is the shape that a cache
      // holding the resolved stream cannot catch.
      const a = openLiveStream(undefined);
      const b = openLiveStream(undefined);
      const [sa, sb] = await Promise.all([a, b]);

      const out = { calls, same: sa === sb, constraints: seen && seen.audio };
      releaseLiveStream(undefined); releaseLiveStream(undefined);
      navigator.mediaDevices.getUserMedia = real;
      return out;
    }""")
    check("two simultaneous opens make one call", race["calls"] == 1,
          "getUserMedia called %d times" % race["calls"])
    check("and both get the same stream", race["same"])
    c = race["constraints"] or {}
    check("voice-call processing is refused",
          c.get("echoCancellation") is False and c.get("noiseSuppression") is False
          and c.get("autoGainControl") is False, str(c))

    # ---- a refusal must not be cached forever ------------------------------
    print("\n--- a refusal is not cached ---")
    retry = p.evaluate("""async () => {
      const real = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      let calls = 0, failNext = true;
      navigator.mediaDevices.getUserMedia = (c) => {
        calls++;
        if (failNext) { failNext = false; return Promise.reject(new DOMException('no', 'NotAllowedError')); }
        // The fake device has no such deviceId, so drop the constraint: what is
        // under test is whether a second call happens at all.
        return real({ audio: true });
      };
      liveStreams.clear();
      let first = 'resolved';
      try { await openLiveStream('x'); } catch (e) { first = e.name; }
      const cachedAfterFailure = liveStreams.has('x');
      const stream = await openLiveStream('x');        // must ask again
      const out = { calls, first, cachedAfterFailure, gotStream: !!stream };
      releaseLiveStream('x');
      navigator.mediaDevices.getUserMedia = real;
      return out;
    }""")
    check("the failure is not kept", retry["cachedAfterFailure"] is False)
    check("and the retry really asks again", retry["calls"] == 2,
          "%d calls, first was %s" % (retry["calls"], retry["first"]))

    # ---- the hold count decides when the tracks stop -----------------------
    print("\n--- the tracks stop when the last holder lets go, and not before ---")
    holds = p.evaluate("""async () => {
      liveStreams.clear();
      const s1 = await openLiveStream(undefined);
      const s2 = await openLiveStream(undefined);
      const live = () => s1.getTracks().every((t) => t.readyState === 'live');
      releaseLiveStream(undefined);
      const afterFirst = live();
      releaseLiveStream(undefined);
      const afterSecond = live();
      return { shared: s1 === s2, afterFirst, afterSecond, left: liveStreams.size };
    }""")
    check("still live while one holder remains", holds["afterFirst"] is True)
    check("stopped once the last lets go", holds["afterSecond"] is False)
    check("and the cache is empty again", holds["left"] == 0)

    # ---- the graph: four lanes, and nothing reaching the speakers ----------
    print("\n--- what the live band split is wired to ---")
    p.evaluate("""() => {
      window.__connects = [];
      const realConnect = AudioNode.prototype.connect;
      AudioNode.prototype.connect = function (dest, ...rest) {
        window.__connects.push({
          from: this.constructor.name,
          to: dest && dest.constructor.name,
          isDestination: !!(dest && dest.context && dest === dest.context.destination),
        });
        return realConnect.call(this, dest, ...rest);
      };
    }""")
    p.locator("#menuButton").click(); p.wait_for_timeout(150)
    p.locator("#srcMic").click(no_wait_after=True); p.wait_for_timeout(2000)
    check("the shape switch is reachable once Mic is chosen",
          p.locator("#micBands").is_visible())
    p.locator("#micBands").click(no_wait_after=True); p.wait_for_timeout(2500)

    got = p.evaluate("""() => ({
      kind: state.source.kind,
      live: !!state.source.live,
      bands: !!state.source.bands,
      lanes: state.source.lanes ? state.source.lanes.length : 0,
      names: state.source.lanes ? state.source.lanes.map((l) => l.name) : [],
      laneCount: laneCount(),
      capacity: state.source.capacity,
      mark: el.sourceMark.textContent,
      describe: state.source.describe(),
      playable: playable(),
      toDestination: window.__connects.filter((c) => c.isDestination).length,
      stacked: stacked(),
    })""")
    check("a live input opened", got["kind"] == "mic" and got["live"], str(got["kind"]))
    check("four band lanes", got["lanes"] == 4 and got["laneCount"] == 4,
          "%d lanes, laneCount %d" % (got["lanes"], got["laneCount"]))
    check("named as bands", got["names"] == ["Low", "Low mid", "High mid", "High"],
          str(got["names"]))
    check("NOTHING reaches the speakers", got["toDestination"] == 0,
          "%d connections to destination" % got["toDestination"])
    check("no transport is offered", got["playable"] is False)
    check("the head says so", got["mark"].strip().lower() == "live bands", got["mark"])
    check("and says it is not monitored", "not monitored" in got["describe"], got["describe"])

    ui = p.evaluate("""() => ({
      fileRows: el.fileRows.hidden, rackRows: el.rackRows.hidden,
      deviceRow: el.deviceRow.hidden, shapeRow: el.micShapeRow.hidden,
    })""")
    check("the panel shows live rows and no file rows",
          ui["fileRows"] and ui["rackRows"] and not ui["deviceRow"] and not ui["shapeRow"],
          str(ui))

    solo = p.evaluate("""() => {
      state.source.lanes[0].mute = true;
      state.source.remix();
      return state.source.lanes.map((l) => l.gain.gain.value);
    }""")
    check("mute still moves the lane gains", solo[0] == 0 and solo[1] > 0, str(solo))

    # ---- and that audio really arrives, which wiring alone does not prove --
    print("\n--- signal actually reaches the band analysers ---")
    # This browser's fake device is silent for several seconds and then emits a
    # burst. It is NOT a 440 Hz sine: it has no zero crossings at all and a peak
    # of exactly 1.0, so it is a pulse train and therefore broadband. Peak is
    # useless here - the click lands in every band - so measure RMS.
    stats = None
    for _ in range(40):
        p.wait_for_timeout(500)
        got = p.evaluate("""() => {
          const w = state.source.getLatestWindow(8192);
          return w.map((c) => { let pk = 0, sum = 0;
            for (const v of c) { const a = Math.abs(v); if (a > pk) pk = a; sum += v * v; }
            return { pk, rms: Math.sqrt(sum / c.length) }; });
        }""")
        if max(g["pk"] for g in got) > 0.05:
            stats = got
            break
    names = ["Low", "Low mid", "High mid", "High"]
    if stats:
        for n, g in zip(names, stats):
            print("    %-9s rms %.4f   peak %.3f" % (n, g["rms"], g["pk"]))
    rms = [g["rms"] for g in stats] if stats else []
    check("audio arrives at every band", bool(rms) and all(v > 0 for v in rms), str(rms))
    check("and the bands are not all the same signal",
          bool(rms) and max(rms) > 2 * min(rms),
          "loudest %.4f, quietest %.4f" % (max(rms), min(rms)) if rms else "no signal")

    # ---- switching shape must not re-prompt --------------------------------
    print("\n--- whole and bands share one stream ---")
    swapped = p.evaluate("""async () => {
      const real = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      let calls = 0;
      navigator.mediaDevices.getUserMedia = (c) => { calls++; return real(c); };
      setMicShape(false);
      await new Promise((r) => setTimeout(r, 1200));
      const whole = { kind: state.source.kind, lanes: state.source.lanes ? 1 : 0,
                      channels: state.source.channels };
      setMicShape(true);
      await new Promise((r) => setTimeout(r, 1200));
      navigator.mediaDevices.getUserMedia = real;
      return { calls, whole, backToLanes: state.source.lanes.length };
    }""")
    check("switching to whole gives an ordinary mic",
          swapped["whole"]["kind"] == "mic" and swapped["whole"]["lanes"] == 0,
          str(swapped["whole"]))
    check("and back to four bands", swapped["backToLanes"] == 4)
    check("without asking for the microphone again", swapped["calls"] == 0,
          "%d further getUserMedia calls" % swapped["calls"])

    # ---- microphone or line, and what may reach the speakers ---------------
    print("\n--- a microphone is never monitored, a declared line input may be ---")
    # The rule this bends is the oldest safety rule in the page, so it is
    # tested from both ends: what the state says, and what the graph is
    # actually wired to. The source re-checks the kind itself, so forcing the
    # UI state past it is one of the cases.
    p.evaluate("() => setMicShape(false)")            # monitoring is whole-input only
    p.wait_for_timeout(1400)

    def wiring():
        return p.evaluate("""() => {
          const source = state.source;
          return {
            kind: state.liveKind,
            wanted: state.monitorLive,
            monitored: source.monitored === true,
            chains: monitorChains.size,
            box: el.monitorLive.disabled,
            says: source.describe(),
          };
        }""")

    start = wiring()
    check("a live input opens as a microphone and is not monitored",
          start["kind"] == "mic" and start["monitored"] is False
          and start["chains"] == 0, str(start))
    check("and the toggle is unavailable rather than inert", start["box"] is True)

    forced = p.evaluate("""() => {
      // Past the UI, straight at the state: a preset, a stray click or a bug
      // must not be able to put a microphone through the speakers.
      state.monitorLive = true;
      applyMonitor();
      const direct = state.source.setMonitor(true);
      return { after: state.monitorLive, direct, chains: monitorChains.size };
    }""")
    check("asking for it anyway does nothing at all",
          forced["after"] is False and forced["direct"] is False
          and forced["chains"] == 0, str(forced))

    # Now the declared line input, with the graph watched from the destination
    # backwards rather than from the source forwards.
    lined = p.evaluate("""() => {
      window.__toDest = [];
      const realConnect = AudioNode.prototype.connect;
      AudioNode.prototype.connect = function (dest, ...rest) {
        if (dest && dest.context && dest === dest.context.destination) {
          window.__toDest.push(this.constructor.name);
        }
        return realConnect.call(this, dest, ...rest);
      };
      setLiveKind('line');
      state.monitorLive = true;
      applyMonitor();
      AudioNode.prototype.connect = realConnect;
      return { monitored: state.source.monitored, chains: monitorChains.size,
               lastBeforeSpeakers: window.__toDest,
               says: state.source.describe(), box: el.monitorLive.disabled,
               latency: el.monitorLatency.textContent };
    }""")
    check("a line input can be heard when its toggle is on",
          lined["monitored"] is True and lined["chains"] == 1, str(lined))
    check("and the last thing before the speakers is the clamp",
          lined["lastBeforeSpeakers"] == ["WaveShaperNode"],
          str(lined["lastBeforeSpeakers"]))
    check("the credit line says it is monitored", "monitored" in lined["says"],
          lined["says"])
    check("and the latency is stated rather than left to be discovered",
          "ms" in lined["latency"], lined["latency"])

    back = p.evaluate("""() => {
      window.__cut = 0;
      const realDisconnect = AudioNode.prototype.disconnect;
      AudioNode.prototype.disconnect = function (...args) {
        if (this.constructor.name === 'WaveShaperNode') window.__cut++;
        return realDisconnect.apply(this, args);
      };
      setLiveKind('mic');
      AudioNode.prototype.disconnect = realDisconnect;
      return { monitored: state.source.monitored, wanted: state.monitorLive,
               chains: monitorChains.size, cut: window.__cut };
    }""")
    check("calling it a microphone again takes it off the speakers at once",
          back["monitored"] is False and back["wanted"] is False
          and back["chains"] == 0, str(back))
    check("and the clamp is unhooked rather than left dangling", back["cut"] == 1,
          "%d disconnects" % back["cut"])

    again = p.evaluate("""() => {
      // Switching back must not resume anything. The wish is dropped when the
      // input stops being a line input, so coming back to one starts from
      // silence and waits to be asked - the alternative is a page that begins
      // monitoring because of something you said a minute ago.
      setLiveKind('line');
      return { monitored: state.source.monitored, wanted: state.monitorLive,
               box: el.monitorLive.checked };
    }""")
    check("and calling it a line input again does not resume it",
          again["monitored"] is False and again["wanted"] is False
          and again["box"] is False, str(again))

    split = p.evaluate("""async () => {
      setLiveKind('line');
      state.monitorLive = true;
      applyMonitor();
      const before = state.source.monitored;
      setMicShape(true);                       // a band split cannot be monitored
      await new Promise((r) => setTimeout(r, 1500));
      const out = { before, after: state.monitorLive, chains: monitorChains.size,
                    box: el.monitorLive.disabled };
      setLiveKind('mic');
      return out;
    }""")
    check("splitting into bands takes the monitoring with it",
          split["before"] is True and split["after"] is False
          and split["chains"] == 0 and split["box"] is True, str(split))
    # Left as a band split: this section borrowed the source the ones below
    # were written against rather than bringing its own.

    # ---- the Live presets must not throw away what you are playing ---------
    print("\n--- the Live presets leave the source alone ---")
    presets = p.evaluate("""() => {
      const group = PRESETS.find(([name]) => name === 'Live');
      const before = { kind: state.source.kind, lanes: state.source.lanes.length };
      const rows = [];
      for (const [name] of group[1]) {
        applyPreset('b:' + name);
        rows.push({ name, kind: state.source.kind,
                    lanes: state.source.lanes ? state.source.lanes.length : 0,
                    display: state.display, picked: el.preset.value === 'b:' + name });
      }
      return { before, rows };
    }""")
    kept = [r for r in presets["rows"]
            if r["kind"] != "mic" or r["lanes"] != presets["before"]["lanes"]]
    check("every Live preset keeps the live input", kept == [],
          "lost it on: %s" % [r["name"] for r in kept])
    check("and each one actually loads", all(r["picked"] for r in presets["rows"]),
          str([r["name"] for r in presets["rows"] if not r["picked"]]))
    pair = p.evaluate("""() => {
      applyPreset('b:Bands, low against high');
      return { pair: state.xyPair.slice(),
               names: state.xyPair.map(laneName),
               selects: [el.xyX.value, el.xyY.value] };
    }""")
    check("a preset can choose which bands are the two axes",
          pair["pair"] == [0, 2] and pair["selects"] == ["0", "2"],
          "%s on %s" % (pair["names"], pair["selects"]))

    # ---- each band passes its own range and rejects the others -------------
    # Deterministic, and independent of whatever the browser's fake device
    # happens to emit: the response of each band's real filter chain, read
    # straight off the nodes.
    print("\n--- each band passes its own range ---")
    resp = p.evaluate("""() => {
      const ctx = new OfflineAudioContext(1, 128, 44100);
      const probes = new Float32Array([40, 300, 2000, 9000]);
      return BANDS.map((band) => {
        const mag = new Float32Array(probes.length).fill(1);
        for (const [type, hz] of [["highpass", band.from], ["lowpass", band.to]]) {
          if (!hz) continue;
          const f = ctx.createBiquadFilter();
          f.type = type; f.frequency.value = hz; f.Q.value = BUTTERWORTH_Q_DB;
          const m = new Float32Array(probes.length), ph = new Float32Array(probes.length);
          f.getFrequencyResponse(probes, m, ph);
          for (let i = 0; i < mag.length; i++) mag[i] *= m[i];   // the chain, cascaded
        }
        return { name: band.name,
                 db: Array.from(mag).map((v) => +(20 * Math.log10(v)).toFixed(1)) };
      });
    }""")
    print("                 40 Hz   300 Hz  2 kHz   9 kHz")
    for r in resp:
        print("    %-9s %s" % (r["name"], "  ".join("%6.1f" % d for d in r["db"])))
    owner = ["Low", "Low mid", "High mid", "High"]
    wrong = [(owner[i], resp[j]["name"])
             for i in range(4)
             for j in range(4)
             if j != i and resp[j]["db"][i] > resp[i]["db"][i] - 0.01]
    check("each probe is loudest in the band that owns it", wrong == [], str(wrong[:3]))
    check("and at least 20 dB down two bands away",
          resp[3]["db"][0] < -20 and resp[0]["db"][3] < -20,
          "High at 40 Hz %.1f dB, Low at 9 kHz %.1f dB"
          % (resp[3]["db"][0], resp[0]["db"][3]))

    # ---- the crossovers are Butterworth, not 0.7 dB peaked -----------------
    print("\n--- the crossovers ---")
    q = p.evaluate("""() => {
      const ctx = new OfflineAudioContext(1, 128, 44100);
      const out = [];
      for (const band of BANDS) {
        for (const [type, hz] of [["highpass", band.from], ["lowpass", band.to]]) {
          if (!hz) continue;
          const f = ctx.createBiquadFilter();
          f.type = type; f.frequency.value = hz; f.Q.value = BUTTERWORTH_Q_DB;
          const freqs = new Float32Array([hz]), mag = new Float32Array(1), ph = new Float32Array(1);
          f.getFrequencyResponse(freqs, mag, ph);
          out.push({ band: band.name, type, hz, db: +(20*Math.log10(mag[0])).toFixed(3) });
        }
      }
      return out;
    }""")
    for r in q:
        print("    %-9s %-9s at %5d Hz  %+.3f dB" % (r["band"], r["type"], r["hz"], r["db"]))
    check("every crossover is -3.01 dB at its corner",
          all(abs(r["db"] + 3.0103) < 0.05 for r in q),
          "worst %+.3f dB" % max(q, key=lambda r: abs(r["db"] + 3.0103))["db"])

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all live-input checks pass")
