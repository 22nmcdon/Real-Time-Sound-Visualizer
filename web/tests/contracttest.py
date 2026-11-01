"""The lane contract: what a lane is, as against how one happens to be built.

A lane used to be "an object with an `analyser` and a `scratch`", and three
separate sources had each written the same eight lines against that - read the
analyser into the scratch, take the tail. That is a statement about how these
lanes are built rather than about what a lane is, and it is what would have
stopped a lane with nothing audible behind it from existing.

It is now three members: `read(n)`, `frames`, and `setMix(value)`. Feeding a
lane is deliberately outside the contract, because what goes into one is
specific to what is behind it - a media stream, a buffer source, a crossover
tail - in a way that reading it is not.

Two things are checked.

THE CONTRACT HOLDS, for every lane of the band split, the one lane-bearing
source since P5 cut the rack, and nothing outside `makeLane` can go round it:
`scratch` is a local now rather than a property, so bypassing the contract is
a `ReferenceError` rather than a convention politely observed.

AND A LANE NEEDS NO AUDIO BEHIND IT: a lane made of three plain functions goes
through the mixer and through `capture`. It was the piece of Stage D1 the
generator as a rack's lane depended on; the rack is gone, and it is kept
because it is what holds the contract to being a contract rather than a
description of the one source left.

That every reader honoured a lane's `delay`, the rack's alignment, the
generator as a real lane beside files, the lane budget, and the generator and
a live input as lanes of one rack were checked here until P5 cut them.
"""
# On ?brain=js (5m): this suite reads the page's own brain - its lanes'
# contract - which core/tests/parity.py holds the instrument to,
# sample for sample. The instrument, the site's default since 5m, is
# braintest.py's and hosttest.py's.
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")


fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


CONTRACT = """() => {
  const source = state.source;
  if (!source || !source.lanes) return { lanes: 0 };
  return {
    kind: source.kind,
    lanes: source.lanes.length,
    // The three members, and the absence of the fourth.
    keeps: source.lanes.every((lane) =>
      typeof lane.read === 'function'
      && typeof lane.setMix === 'function'
      && typeof lane.frames === 'number' && lane.frames > 0),
    hides: source.lanes.every((lane) => lane.scratch === undefined),
    reads: source.lanes.map((lane) => lane.read(777).length),
    capacity: source.capacity,
    frames: source.lanes[0].frames,
  };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required",
                                 "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
    p = b.new_context(permissions=["microphone"], viewport={"width": 1400, "height": 900}).new_page()
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html?brain=js"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    # The source buttons live inside the menu, and a click on a hidden control
    # waits thirty seconds and then says "not visible" rather than saying that.
    p.evaluate("() => { setView('bench'); setBenchTab('play'); }"); p.wait_for_timeout(200)

    print("\n--- every lane of the band split ---")
    # The faked microphone, split into bands. A rack of stems was checked here
    # too, the other source that built lanes its own way, until P5 cut it.
    p.evaluate("() => toMic()"); p.wait_for_timeout(1500)
    p.evaluate("() => el.micBands.click()"); p.wait_for_timeout(800)
    bands = p.evaluate(CONTRACT)
    print("    %-6s %d lanes, %d frames each, capacity %d, reads %s"
          % (bands["kind"], bands["lanes"], bands["frames"], bands["capacity"],
             bands["reads"]))
    check("a band split's lanes keep it too",
          bands["lanes"] == 4 and bands["keeps"] and bands["hides"], str(bands))
    check("and return what was asked for",
          bands["reads"] == [777] * 4, str(bands["reads"]))

    print("\n--- a lane with nothing audible behind it ---")
    # Stage D1's load-bearing claim: the generator can be a lane while it is
    # still arithmetic into a ring buffer. Three plain functions, no analyser,
    # no gain node, through the mixer and through `capture`.
    synthetic = p.evaluate("""() => {
      const rate = 44100, frames = 8192;
      const made = (name, hz) => {
        const ring = new Float32Array(frames);
        for (let i = 0; i < frames; i++) {
          ring[i] = 0.4 * Math.sin(2 * Math.PI * hz * i / rate);
        }
        let mix = 1;
        return {
          name, level: 0, mute: false, solo: false, delay: 0,
          live: false, monitored: true,
          get frames() { return frames; },
          read(n) {
            const out = new Float32Array(n);
            const take = Math.min(n, frames - this.delay);
            const end = frames - this.delay;
            out.set(ring.subarray(end - take, end), n - take);
            return out;
          },
          setMix(value) { mix = value; },
          get mix() { return mix; },
        };
      };
      const lanes = [made('Left', 220), made('Right', 330)];

      /* The mixer, which is the one place that used to reach for a GainNode.
         Every call wrapped, not only the first: with the mixer put back to
         reaching for `lane.gain.gain`, an unwrapped call throws out of the
         whole `evaluate` and the suite dies with a stack trace instead of a
         named check - which aborts everything after it and reads as a broken
         test rather than a broken page. */
      let mixerThrew = null;
      const mix = () => {
        try { laneMixer(lanes); } catch (error) {
          if (mixerThrew === null) mixerThrew = String(error.message);
        }
      };
      mix();
      const afterPlain = lanes.map((lane) => lane.mix);
      lanes[1].mute = true;
      mix();
      const afterMute = lanes.map((lane) => lane.mix);
      lanes[1].mute = false;
      lanes[0].solo = true;
      mix();
      const afterSolo = lanes.map((lane) => lane.mix);
      lanes[0].solo = false;
      mix();

      /* And a source built out of them, with the same one line every real
         source now uses. If `capture` needs anything an analyser provides,
         this is where it says so. */
      const was = { src: state.source, run: state.running, tb: state.timebase };
      state.running = false;
      state.timebase = 5;
      state.source = {
        kind: 'mic', lanes, settings: null,
        get sampleRate() { return rate; },
        get capacity() { return lanes[0].frames; },
        get channels() { return lanes.length; },
        tick() {}, stop() {}, describe: () => 'made up',
        getLatestWindow: (n) => lanes.map((lane) => lane.read(n)),
      };
      let captureThrew = null, peaks = [];
      try {
        const f = capture();
        peaks = f.channels.map((ch) => {
          let peak = 0;
          for (let i = 0; i < ch.length; i++) peak = Math.max(peak, Math.abs(ch[i]));
          return peak;
        });
      } catch (error) { captureThrew = String(error.message); }

      Object.assign(state, { source: was.src, running: was.run, timebase: was.tb });
      return { mixerThrew, captureThrew, afterPlain, afterMute, afterSolo, peaks };
    }""")
    print("    mixer: plain %s, one muted %s, one soloed %s"
          % (synthetic["afterPlain"], synthetic["afterMute"], synthetic["afterSolo"]))
    print("    capture drew peaks %s"
          % [round(x, 3) for x in synthetic["peaks"]])
    check("the mixer takes a lane with no gain node",
          synthetic["mixerThrew"] is None, str(synthetic["mixerThrew"]))
    check("and mute and solo still mean what they mean",
          synthetic["afterPlain"] == [1, 1] and synthetic["afterMute"] == [1, 0]
          and synthetic["afterSolo"] == [1, 0], str(synthetic))
    check("capture draws from a lane with no analyser behind it",
          synthetic["captureThrew"] is None, str(synthetic["captureThrew"]))
    check("and what it drew is the signal the lane made",
          len(synthetic["peaks"]) == 2
          and all(abs(x - 0.4) < 0.01 for x in synthetic["peaks"]),
          str([round(x, 4) for x in synthetic["peaks"]]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("a lane is three functions, and one of them need not touch audio")
