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

Three things are checked.

THE CONTRACT HOLDS, for every lane of every lane-bearing source, and nothing
outside `makeLane` can go round it: `scratch` is a local now rather than a
property, so bypassing the contract is a `ReferenceError` rather than a
convention politely observed.

`delay` IS HONOURED BY EVERY READER. It was honoured by one of the three.
`applyAlignment` writes it on every lane of any source that has lanes, so the
day a band split or a file wanted alignment it would have done nothing and
looked like a broken control. Not reachable before - only a rack reports
`hasLive`, which is what shows the control - which is exactly why it wanted
closing rather than fixing later.

AND A LANE NEEDS NO AUDIO BEHIND IT. This is the piece of Stage D1 the rest
depends on: the generator can be a lane while it is still arithmetic into a
ring buffer, and nothing downstream of `getLatestWindow` need know. Proved by
putting a lane made of three plain functions through the mixer and through
`capture`.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
STEMS = os.path.join(HERE, "fixtures")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

sys.path.insert(0, HERE)
import fixtures
fixtures.ensure()

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
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    # The source buttons live inside the menu, and a click on a hidden control
    # waits thirty seconds and then says "not visible" rather than saying that.
    p.locator("#menuButton").click(); p.wait_for_timeout(200)

    print("\n--- every lane of every source that has lanes ---")
    # A rack of stems, and the same files as one band-split source: the two
    # sources that build lanes in different ways and had written the reader
    # twice between them.
    # `no_wait_after`, because choosing Stems opens a file picker and the click
    # does not settle until something is chosen.
    p.locator("#srcRack").click(no_wait_after=True); p.wait_for_timeout(300)
    p.locator("#rackInput").set_input_files(
        [f"{STEMS}/{n}.wav" for n in ("drums", "bass", "other")])
    p.wait_for_timeout(1500)
    rack = p.evaluate(CONTRACT)
    print("    %-6s %d lanes, %d frames each, capacity %d, reads %s"
          % (rack["kind"], rack["lanes"], rack["frames"], rack["capacity"],
             rack["reads"]))
    check("a rack's lanes keep the contract",
          rack["lanes"] == 3 and rack["keeps"], str(rack))
    check("and hide what is behind them",
          rack["hides"], "scratch is %s" % ("gone" if rack["hides"] else "still there"))
    check("every lane returns exactly what was asked for",
          rack["reads"] == [777, 777, 777], str(rack["reads"]))

    p.locator("#bandInput").set_input_files(f"{STEMS}/other.wav")
    p.wait_for_timeout(1500)
    bands = p.evaluate(CONTRACT)
    print("    %-6s %d lanes, %d frames each, capacity %d, reads %s"
          % (bands["kind"], bands["lanes"], bands["frames"], bands["capacity"],
             bands["reads"]))
    check("a band split's lanes keep it too",
          bands["lanes"] == 4 and bands["keeps"] and bands["hides"], str(bands))
    check("and return what was asked for",
          bands["reads"] == [777] * 4, str(bands["reads"]))

    print("\n--- and every reader honours the delay ---")
    # The latent bug. `applyAlignment` writes `delay` on any source with lanes;
    # two of the three readers ignored it. A band split is the case that would
    # have gone wrong, so it is the case checked.
    # Every lane, not lane one. A band split puts the low frequencies in the
    # first lane, and a thousand samples is a small fraction of a period down
    # there - it shifted by exactly the delay and moved the trace by 0.004,
    # which proves the shift and is a poor witness that anything happened. The
    # property is asserted on all four; the witness comes from whichever lane
    # can actually show it.
    delayed = p.evaluate("""() => state.source.lanes.map((lane, index) => {
      const was = lane.delay;
      const plain = lane.read(4096);
      lane.delay = 1000;
      const held = lane.read(4096);
      lane.delay = was;

      /* The same samples, a thousand later in one than the other: what was at
         index i - 1000 of the un-delayed read has to be at index i of the
         delayed one. Over the middle, away from the zero padding at the
         front. */
      let worst = 0, moved = 0;
      for (let i = 2000; i < 4000; i++) {
        worst = Math.max(worst, Math.abs(held[i] - plain[i - 1000]));
        moved = Math.max(moved, Math.abs(held[i] - plain[i]));
      }
      return { index, name: lane.name, worst, moved };
    })""")
    for row in delayed:
        print("    lane %d (%s): shift exact to %.2e, window moved by %.4f"
              % (row["index"], row["name"], row["worst"], row["moved"]))
    loudest = max(delayed, key=lambda r: r["moved"])
    check("the delay really moved the window on at least one lane",
          loudest["moved"] > 0.05,
          "%.4f on lane %d, which is the one with the high frequencies in it"
          % (loudest["moved"], loudest["index"]))
    check("and on every lane it moved it by exactly the delay",
          all(r["worst"] < 1e-6 for r in delayed),
          "worst %.2e of %d lanes"
          % (max(r["worst"] for r in delayed), len(delayed)))

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
        kind: 'rack', lanes, settings: null,
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
