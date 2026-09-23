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

    print("\n--- and the generator as one of them, for real ---")
    # Everything above proves a made-up lane satisfies the contract. This is
    # the real one: the generator's own core, in a real rack, beside real
    # files, reached through the real checkbox.
    p.evaluate("() => { el.rackSynth.checked = true; return setRackSynth(true); }")
    p.wait_for_timeout(200)
    p.locator("#rackInput").set_input_files(
        [f"{STEMS}/{n}.wav" for n in ("drums", "bass")])
    p.wait_for_timeout(1800)
    withSynth = p.evaluate("""() => {
      const source = state.source;
      const lane = source.lanes.find((l) => l.synth);
      return {
        lanes: source.lanes.map((l) => l.name),
        found: !!lane,
        keeps: lane ? (typeof lane.read === 'function'
                       && typeof lane.setMix === 'function'
                       && typeof lane.frames === 'number') : false,
        monitored: lane ? lane.monitored : null,
        driver: lfoDriver(),
        budget: el.rackBudget.textContent,
        // The generator panel has to be reachable, or the lane is a thing you
        // can put on the screen and not steer.
        panel: el.toneRows.dataset.off === undefined,
        settings: !!genSettings(),
      };
    }""")
    print("    lanes %s, budget %r, driver %s"
          % (withSynth["lanes"], withSynth["budget"], withSynth["driver"]))
    check("the generator is a lane of the rack",
          withSynth["found"] and withSynth["lanes"][0] == "Generator"
          and len(withSynth["lanes"]) == 3, str(withSynth["lanes"]))
    check("and it keeps the contract like any other lane",
          withSynth["keeps"] and withSynth["monitored"] is False, str(withSynth))
    check("the oscillators are driven by the lane's own loop, not the frame",
          withSynth["driver"] == "fill", withSynth["driver"])
    check("and the generator's controls reach it",
          withSynth["panel"] and withSynth["settings"], str(withSynth))

    # It has to be making something, not merely present.
    p.wait_for_timeout(600)
    making = p.evaluate("""() => {
      const lane = state.source.lanes.find((l) => l.synth);
      const w = lane.read(4096);
      let peak = 0;
      for (let i = 0; i < w.length; i++) peak = Math.max(peak, Math.abs(w[i]));
      // And the generator's own controls move it.
      genSet('amp', 0.2);
      return { peak, amp: genSettings().amp };
    }""")
    p.wait_for_timeout(500)
    quieter = p.evaluate("""() => {
      const lane = state.source.lanes.find((l) => l.synth);
      const w = lane.read(4096);
      let peak = 0;
      for (let i = 0; i < w.length; i++) peak = Math.max(peak, Math.abs(w[i]));
      genSet('amp', 0.55);
      return peak;
    }""")
    print("    the lane made %.3f, and %.3f after the amplitude was turned down"
          % (making["peak"], quieter))
    check("the lane is actually generating",
          making["peak"] > 0.3, "%.3f" % making["peak"])
    check("and the amplitude slider reaches it",
          quieter < making["peak"] * 0.6 and quieter > 0.1,
          "%.3f against %.3f" % (quieter, making["peak"]))

    print("\n--- the lane budget, said before anything is decoded ---")
    budget = p.evaluate("""() => {
      const shown = () => ({ text: el.rackBudget.textContent,
                             over: el.rackBudget.dataset.state });
      const out = { withGenerator: shown() };
      // Six files and the generator is seven lanes' worth of intent.
      const sums = [];
      for (const files of [1, 4, 5, 6, 8]) {
        for (const extras of [0, 1, 2]) {
          const b = laneBudget(files, extras);
          sums.push({ files, extras, wanted: b.wanted, room: b.room, over: b.over });
        }
      }
      return { ...out, sums, max: MAX_LANES };
    }""")
    print("    with two stems and the generator: %r" % budget["withGenerator"]["text"])
    for row in budget["sums"]:
        if row["files"] in (5, 6) and row["extras"] == 1:
            print("    %d files + %d extra: wants %d, room for %d, over by %d"
                  % (row["files"], row["extras"], row["wanted"],
                     row["room"], row["over"]))
    check("the count is shown for what is loaded",
          "3 of 6" in budget["withGenerator"]["text"],
          budget["withGenerator"]["text"])
    check("the generator takes one of the six before any file does",
          all(r["room"] == budget["max"] - r["extras"] for r in budget["sums"]),
          str([(r["extras"], r["room"]) for r in budget["sums"][:6]]))
    check("and a choice that will not fit says so rather than dropping quietly",
          all((r["over"] > 0) == (r["wanted"] > budget["max"]) for r in budget["sums"]),
          str([(r["wanted"], r["over"]) for r in budget["sums"]]))

    # Six stems and the generator: the files give way, not the generator, and
    # the rack says what it took.
    p.locator("#rackInput").set_input_files(
        [f"{STEMS}/{n}.wav" for n in ("drums", "bass", "other", "vocals")])
    p.wait_for_timeout(1800)
    over = p.evaluate("""() => {
      const loaded = {
        lanes: state.source.lanes.length,
        names: state.source.lanes.map((l) => l.name),
      };
      /* Two more pretended, so the over-budget line can be read without two
         more fixtures - and PUT BACK, because the next check rebuilds from
         this list and six files is a perfectly good rack. Leaving it padded
         made "unticking it removes the lane" fail with six lanes and no
         generator, which is the right answer to the wrong question. */
      const was = rackFiles;
      rackFiles = rackFiles.concat(rackFiles.slice(0, 2));
      sayBudget();
      const text = el.rackBudget.textContent;
      const overState = el.rackBudget.dataset.state;
      rackFiles = was;
      sayBudget();
      return { ...loaded, text, over: overState };
    }""")
    print("    four stems and the generator: %d lanes %s; six would say %r"
          % (over["lanes"], over["names"], over["text"]))
    check("four stems plus the generator is five lanes, generator first",
          over["lanes"] == 5 and over["names"][0] == "Generator", str(over["names"]))
    check("and seven wanted is marked as over",
          over["over"] == "over" and "most" in over["text"], over["text"])

    # More files than there is room for, which is the only case where
    # reserving a lane for the generator changes anything - and the case a
    # mutation that stopped reserving it survived, because every rack above
    # fits comfortably. Six chosen, five taken, the generator keeping its one.
    p.evaluate("() => { el.rackSynth.checked = true; return setRackSynth(true); }")
    p.wait_for_timeout(200)
    p.locator("#rackInput").set_input_files(
        [f"{STEMS}/{n}.wav" for n in
         ("drums", "bass", "other", "vocals", "drums", "bass")])
    p.wait_for_timeout(2200)
    crowded = p.evaluate("""() => ({
      lanes: state.source.lanes.length,
      names: state.source.lanes.map((l) => l.name),
      synth: state.source.lanes.filter((l) => l.synth).length,
      budget: el.rackBudget.textContent,
      note: el.rackNote.textContent,
    })""")
    print("    six files and the generator: %d lanes, %s"
          % (crowded["lanes"], crowded["names"]))
    print("    budget %r" % crowded["budget"])
    check("six files and the generator comes to six lanes, not seven",
          crowded["lanes"] == 6, str(crowded["lanes"]))
    check("and the one dropped is a file, not the generator",
          crowded["synth"] == 1 and crowded["names"][0] == "Generator"
          and len(crowded["names"]) - 1 == 5, str(crowded["names"]))
    check("and the page says what it took rather than doing it quietly",
          "most" in crowded["note"] and "5" in crowded["note"],
          crowded["note"][:80])

    # Back to something small for the checks below.
    p.locator("#rackInput").set_input_files(
        [f"{STEMS}/{n}.wav" for n in ("drums", "bass", "other", "vocals")])
    p.wait_for_timeout(1800)

    # Two of them, which no control can ask for and which would be a quiet
    # disaster if one ever could: both would step the shared oscillators once a
    # sample and every modulation rate would run at double. Dropped where the
    # rack is built rather than refused, so a caller that asked for two gets a
    # rack rather than an exception.
    doubled = p.evaluate("""async () => {
      /* A real file alongside, because a rack of nothing but arithmetic is
         refused - and rightly: that is the tone source with extra steps. Built
         here rather than fetched, since a page opened from `file://` cannot
         read its own siblings. A tenth of a second of 16-bit mono is enough
         for `decodeAudioData` to say yes. */
      const wav = () => {
        const rate = 44100, n = Math.round(rate * 0.1);
        const buffer = new ArrayBuffer(44 + n * 2);
        const view = new DataView(buffer);
        const tag = (at, text) => {
          for (let i = 0; i < text.length; i++) view.setUint8(at + i, text.charCodeAt(i));
        };
        tag(0, 'RIFF'); view.setUint32(4, 36 + n * 2, true); tag(8, 'WAVE');
        tag(12, 'fmt '); view.setUint32(16, 16, true);
        view.setUint16(20, 1, true); view.setUint16(22, 1, true);
        view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true);
        view.setUint16(32, 2, true); view.setUint16(34, 16, true);
        tag(36, 'data'); view.setUint32(40, n * 2, true);
        for (let i = 0; i < n; i++) {
          view.setInt16(44 + i * 2,
            Math.round(12000 * Math.sin(2 * Math.PI * 220 * i / rate)), true);
        }
        return buffer;
      };

      const made = await makeRackSource([
        { name: 'Generator', synth: true },
        { name: 'Generator too', synth: true },
        { name: 'A file', data: wav() },
        { name: 'Tone', synth: true },
      ], 'two of them');
      const out = { lanes: made.lanes.length,
                    synths: made.lanes.filter((l) => l.synth).length,
                    names: made.lanes.map((l) => l.name) };
      made.stop();
      return out;
    }""")
    print("    three asked for beside a file: %d lanes, %d arithmetic %s"
          % (doubled["lanes"], doubled["synths"], doubled["names"]))
    check("a rack keeps one generator lane however many were asked for",
          doubled["synths"] == 1, str(doubled))
    check("and it is the first one, not the last",
          doubled["names"][0] == "Generator", str(doubled["names"]))

    print("\n--- and taking it out again ---")
    p.evaluate("() => { el.rackSynth.checked = false; return setRackSynth(false); }")
    p.wait_for_timeout(1800)
    without = p.evaluate("""() => ({
      lanes: state.source.lanes.map((l) => l.name),
      synth: state.source.lanes.some((l) => l.synth),
      driver: lfoDriver(),
      panel: el.toneRows.dataset.off === undefined,
    })""")
    print("    lanes %s, driver %s" % (without["lanes"], without["driver"]))
    check("unticking it rebuilds the rack without the lane",
          without["synth"] is False and len(without["lanes"]) == 4,
          str(without["lanes"]))
    check("and the oscillators go back to the frame clock",
          without["driver"] == "main", without["driver"])
    check("and the generator's controls stop claiming to apply",
          without["panel"] is False, str(without["panel"]))

    print("\n--- and what a lane cannot do, said where it is met ---")
    # Two capabilities that disappear when the generator becomes a lane, and
    # the rule this project keeps applying: a thing withheld has to say so
    # where somebody would go looking for it, not go quietly missing.
    # No keyboard needed and none asked for: the note is about where the
    # generator is, not about whether anything is plugged in, and
    # `requestMIDIAccess` in a headless browser with no stub is a wait with no
    # end to it.
    # With a lane actually present: the section above took it out again, and
    # the first version of this read a note that was hidden and still carrying
    # the text from before - right words, wrong moment.
    p.evaluate("() => { el.rackSynth.checked = true; return setRackSynth(true); }")
    p.wait_for_timeout(1800)
    said = p.evaluate("""async () => {
      midi.mode = 'dyad';
      syncMidi();
      const asLane = { hidden: el.midiLaneNote.hidden,
                       text: el.midiLaneNote.textContent };
      const wasKind = state.source.kind;
      await toTone();
      const asSource = { hidden: el.midiLaneNote.hidden,
                         text: el.midiLaneNote.textContent };
      return { asLane, asSource, wasKind };
    }""")
    print("    as a lane: %r" % said["asLane"]["text"][:110])
    check("with the generator as a lane, the keyboard panel says what is gone",
          said["asLane"]["hidden"] is False
          and "interval figure is not available" in said["asLane"]["text"]
          and "without starting or stopping it" in said["asLane"]["text"],
          said["asLane"]["text"][:80])
    check("and says nothing of the kind when the generator is on its own",
          said["asSource"]["hidden"] is True and said["asSource"]["text"] == "",
          "hidden %s, text %r"
          % (said["asSource"]["hidden"], said["asSource"]["text"][:40]))

    print("\n--- one loop, when the generator can be in two places ---")
    # The ownership rule was written for exactly this shape, and it is worth
    # RE-RUNNING against it rather than assuming the refactor inherited the
    # protection along with the name. `lfoDriver` used to ask "is the source a
    # tone"; it now asks "does anything here run a per-sample loop", and the
    # hazard is a generator sounding as the source while a generator lane also
    # exists - two loops, one set of oscillators, every rate at double.
    #
    # The two cannot coexist today, because `state.source` is one thing and
    # adopting a rack stops the source it replaces. That is the claim being
    # checked, not assumed: switching each way and asking who is driving.
    both = p.evaluate("""async () => {
      const out = {};
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));

      // Generator as the source, sounding: its worklet owns them.
      el.rackSynth.checked = false;
      await setRackSynth(false);
      await toTone();
      state.genSound = true;
      await applyGeneratorSound();
      await wait(300);
      out.asSource = { driver: lfoDriver(),
                       audible: state.source.audible(),
                       kind: state.source.kind };

      /* Now a rack with a generator lane, adopted over it. If the old
         worklet outlived the switch, two loops would be stepping the same two
         oscillators and `assertLfoDriver` would throw on the first block of
         whichever one is not the driver. */
      el.rackSynth.checked = true;
      await setRackSynth(true);
      return out;
    }""")
    p.locator("#rackInput").set_input_files(
        [f"{STEMS}/{n}.wav" for n in ("drums", "bass")])
    p.wait_for_timeout(2000)
    swapped = p.evaluate("""() => ({
      driver: lfoDriver(),
      kind: state.source.kind,
      synth: state.source.lanes.some((l) => l.synth),
      // The generator that WAS the source has been stopped, so nothing of it
      // is still producing.
      soundFlag: state.genSound,
    })""")
    print("    as a source: %s; after adopting a rack with a lane: %s"
          % (both["asSource"], swapped))
    check("as the source and sounding, the worklet owns the oscillators",
          both["asSource"]["driver"] == "worklet" and both["asSource"]["audible"],
          str(both["asSource"]))
    check("and adopting a rack hands them to the lane's loop, not to both",
          swapped["driver"] == "fill" and swapped["synth"]
          and swapped["soundFlag"] is False, str(swapped))

    # A second of real running, because the throw happens on a block rather
    # than on a switch: if anything else were still stepping them, this is
    # where it would say so.
    p.wait_for_timeout(1000)
    ran = p.evaluate("""() => ({ driver: lfoDriver(), value: lfos[0].value })""")
    check("and a second of running produces no ownership complaint",
          not [x for x in [] ] and ran["driver"] == "fill", str(ran))

    # And back the other way: a rack with a lane, then the generator alone
    # with its sound on.
    back = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      await toTone();
      state.genSound = true;
      await applyGeneratorSound();
      await wait(400);
      const out = { driver: lfoDriver(), kind: state.source.kind,
                    audible: state.source.audible() };
      state.genSound = false;
      await applyGeneratorSound();
      return out;
    }""")
    print("    back to the generator alone: %s" % back)
    check("and back again the worklet owns them, with no lane left to argue",
          back["driver"] == "worklet" and back["kind"] == "tone", str(back))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("a lane is three functions, and one of them need not touch audio")
