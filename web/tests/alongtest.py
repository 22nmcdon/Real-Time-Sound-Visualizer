"""Playing along with a backing track: one file and one live input, as lanes.

The two things most likely to be wrong are not audible in a test, so both are
asserted by watching the graph: that nothing of the live lane can reach the
speakers, and that the alignment really moves a lane in time rather than
appearing to.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
SHOTS = os.path.join(HERE, "shots"); os.makedirs(SHOTS, exist_ok=True)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

import fixtures
STEMS = fixtures.ensure()

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
    c = b.new_context(permissions=["microphone"])
    p = c.new_page(); p.set_viewport_size({"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    # Watch every connection made from here on, so "nothing reaches the
    # speakers" is a fact about the graph rather than about the comment.
    p.evaluate("""() => {
      window.__toDest = [];
      const real = AudioNode.prototype.connect;
      AudioNode.prototype.connect = function (dest, ...rest) {
        if (dest && dest.context && dest === dest.context.destination) {
          window.__toDest.push(this.constructor.name);
        }
        return real.call(this, dest, ...rest);
      };
    }""")

    p.evaluate("() => setMenuOpen(true)"); p.wait_for_timeout(150)
    p.locator("#srcRack").click(no_wait_after=True); p.wait_for_timeout(200)
    p.locator("#alongInput").set_input_files(f"{STEMS}/other.wav")
    p.wait_for_timeout(3000)

    print("\n--- what got built ---")
    built = p.evaluate("""() => ({
      kind: state.source.kind,
      hasLive: !!state.source.hasLive,
      lanes: state.source.lanes.map((l) => ({
        name: l.name, live: l.live, monitored: l.monitored,
        buffered: !!l.buffer, delay: l.delay,
      })),
      mark: el.sourceMark.textContent.trim(),
      describe: state.source.describe(),
      playable: playable(),
      playing: state.source.playing,
      laneCount: laneCount(),
      suggested: state.source.suggestedAlignMs,
      align: state.alignMs,
    })""")
    check("a rack with a live lane opened",
          built["kind"] == "rack" and built["hasLive"], str(built["kind"]))
    check("two lanes: a track and you", len(built["lanes"]) == 2 and built["laneCount"] == 2,
          str([l["name"] for l in built["lanes"]]))
    check("the track has a buffer and the live lane does not",
          built["lanes"][0]["buffered"] and not built["lanes"][1]["buffered"],
          str([l["buffered"] for l in built["lanes"]]))
    check("the live lane is marked unmonitored",
          built["lanes"][1]["live"] and built["lanes"][1]["monitored"] is False,
          str(built["lanes"][1]))
    check("the transport still works, because a file is playing",
          built["playable"] and built["playing"], str(built))
    check("the head says what it is", built["mark"].lower() == "play along", built["mark"])
    check("and the credit says you are not monitored",
          "not monitored" in built["describe"], built["describe"])
    print("    suggested alignment: %d ms" % built["suggested"])
    check("an alignment was suggested from the context",
          built["align"] == built["suggested"] and 0 <= built["suggested"] < 200,
          str(built["suggested"]))

    print("\n--- nothing of you reaches the speakers ---")
    wiring = p.evaluate("""() => ({
      toDestination: window.__toDest.slice(),
      liveConnectedToGain: (() => {
        // The live lane's source node goes to its analyser and nowhere else.
        const lane = state.source.lanes.find((l) => l.live);
        return !!lane.node;
      })(),
    })""")
    check("the only thing on the destination is the output clamp",
          wiring["toDestination"] == ["WaveShaperNode"], str(wiring["toDestination"]))
    check("the live lane has its own source node", wiring["liveConnectedToGain"])

    solo = p.evaluate("""() => {
      const [track, you] = state.source.lanes;
      you.solo = true; state.source.remix();
      const soloingYou = { track: track.gain.gain.value, you: you.gain.gain.value };
      you.solo = false; track.solo = true; state.source.remix();
      const soloingTrack = { track: track.gain.gain.value, you: you.gain.gain.value };
      track.solo = false; state.source.remix();
      return { soloingYou, soloingTrack };
    }""")
    check("soloing the lane you cannot hear does not silence the track",
          solo["soloingYou"]["track"] > 0, str(solo["soloingYou"]))
    check("soloing the track still works", solo["soloingTrack"]["track"] > 0,
          str(solo["soloingTrack"]))

    print("\n--- the alignment really moves a lane in time ---")
    # A known ramp straight into the analyser, so the shift can be counted
    # rather than estimated.
    shifted = p.evaluate("""() => {
      const lanes = state.source.lanes;
      for (const lane of lanes) {
        lane.analyser.getFloatTimeDomainData = (out) => {
          for (let i = 0; i < out.length; i++) out[i] = i;
        };
      }
      const lastOf = (ms) => {
        state.alignMs = ms; applyAlignment();
        const w = state.source.getLatestWindow(256);
        return { track: w[0][255], you: w[1][255], capacity: state.source.capacity };
      };
      const rate = state.source.sampleRate;
      const out = { rate, at0: lastOf(0), at50: lastOf(50), atMinus50: lastOf(-50) };
      state.alignMs = state.source.suggestedAlignMs; applyAlignment();
      return out;
    }""")
    rate = shifted["rate"]
    want = round(50 * rate / 1000)
    trackShift = shifted["at0"]["track"] - shifted["at50"]["track"]
    youShift = shifted["at0"]["you"] - shifted["at50"]["you"]
    print("    +50 ms moved the track back %d samples (%d wanted), you %d"
          % (trackShift, want, youShift))
    check("a positive alignment holds the track back by exactly that much",
          trackShift == want, "%d against %d" % (trackShift, want))
    check("and leaves the input where it is", youShift == 0, str(youShift))

    backShift = shifted["at0"]["you"] - shifted["atMinus50"]["you"]
    check("a negative alignment holds the input back instead",
          backShift == want and shifted["at0"]["track"] == shifted["atMinus50"]["track"],
          "%d against %d" % (backShift, want))
    check("and the delayed room comes out of what the source can offer",
          shifted["at50"]["capacity"] == shifted["at0"]["capacity"] - want,
          "%d against %d" % (shifted["at50"]["capacity"], shifted["at0"]["capacity"]))

    print("\n--- one stream, and it is given back ---")
    shared = p.evaluate("""async () => {
      const real = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      let calls = 0;
      navigator.mediaDevices.getUserMedia = (c) => { calls++; return real(c); };
      // Distinct entries, not keys: one stream is deliberately filed under
      // both the empty "whatever the default is" key and the device id the
      // browser hands out once permission exists.
      const held = new Set(liveStreams.values()).size;
      const keys = liveStreams.size;
      el.srcMic.click();                      // a plain mic, same device
      await new Promise((r) => setTimeout(r, 2000));
      const after = { calls, held, keys, kind: state.source.kind,
                      streams: new Set(liveStreams.values()).size };
      navigator.mediaDevices.getUserMedia = real;
      return after;
    }""")
    check("a play-along holds exactly one live stream", shared["held"] == 1, str(shared["held"]))
    check("filed under both the default and the named device",
          shared["keys"] == 2, "%d keys for %d stream" % (shared["keys"], shared["held"]))
    check("switching to the plain mic does not ask again", shared["calls"] == 0,
          "%d further getUserMedia calls" % shared["calls"])

    p.evaluate("() => el.srcTone.click()"); p.wait_for_timeout(600)
    check("still one stream after the switch, not two", shared["streams"] == 1,
          str(shared["streams"]))
    check("and going back to the tone gives it back, under every name",
          p.evaluate("() => liveStreams.size") == 0,
          str(p.evaluate("() => liveStreams.size")))

    print("\n--- the panel ---")
    p.evaluate("() => setMenuOpen(true)"); p.wait_for_timeout(150)
    p.locator("#alongInput").set_input_files(f"{STEMS}/bass.wav")
    p.wait_for_timeout(2800)
    panel = p.evaluate("""() => ({
      alignShown: !el.alignRow.hidden, noteShown: !el.alignNote.hidden,
      transport: !el.fileRows.hidden,
    })""")
    check("the alignment control appears for a play-along", panel["alignShown"])
    check("with the note that explains it", panel["noteShown"])
    check("and the transport is there", panel["transport"])
    p.evaluate("() => { setMenuOpen(false); setView('scope'); }")
    p.wait_for_timeout(1200)
    p.screenshot(path=f"{SHOTS}/play-along.png")

    p.evaluate("() => el.srcTone.click()"); p.wait_for_timeout(500)
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all play-along checks pass")
