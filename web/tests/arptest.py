"""The arpeggiator (K5).

Against the way it would fail:

- the wrong order: C E G held, up is C E G C E G, down G E C, up-down C E G E
  and round without either end twice, as played in the order the keys went
  down, two octaves C E G and the same an octave up, random only ever what is
  held;
- the generator given the whole chord instead of the step, or the step not
  struck: each step closes the gate and opens it again;
- the hands forgotten: what the notes sources read is still the whole chord;
- the tempo: 120 BPM in quavers is a step every 250 ms, five in a second from
  the first key, and the steps do not drift;
- the dyad not drawing the chord's intervals: each step pairs the lowest held
  note with the arpeggio's, so C E G is unison, a major third and a fifth;
- a note left hanging: letting go stops it and ends what went out as MIDI;
- switching it off with keys down leaving the generator on one note;
- switching it off once it has stepped leaving the keys on the last step's
  envelope (11 Nov): what is held is struck, the gate closed and opened, and
  inside the gather, before a step, it is not; and on both brains, a setup
  without it loaded over a key held through one with it sounds the key at
  the new setup's level. Its null is a key struck under a lower sustain and
  held into the same setup, which keeps the lower level.
"""
# The level a held key reaches under setups loaded over it, on a brain: the
# peak of the last quarter second of the picture, a setup at a time, with
# time between for the arpeggiator to step, which on the site's instrument
# it does on the audio's clock.
LEVEL = """async (steps) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const load = (over) => { const s = Object.assign({}, BASE_SETUP, over); hostQuietly(() => restore(s)); hostSendSetup(); };
  const peak = () => { const n = Math.round(state.source.sampleRate / 4); let most = 0;
    for (const lane of state.source.getLatestWindow(n).slice(0, 2)) for (const v of lane) most = Math.max(most, Math.abs(v));
    return most; };
  const out = [];
  for (const [what, arg] of steps) {
    if (what === 'load') load(arg);
    else if (what === 'on') midiNoteOn(arg, 127);
    else if (what === 'off') midiNoteOff(arg);
    else if (what === 'wait') await wait(arg);
    else if (what === 'read') out.push(peak());
  }
  midiPanic();
  return out;
}"""
PLAIN = {"midiMode": "dyad", "atk": 1, "dec": 200, "sus": 70, "rel": 50}
ARP = {"midiMode": "dyad", "arpMode": "up", "arpRate": "1/16", "arpOctaves": 2, "atk": 1, "dec": 200, "sus": 30, "rel": 50}
LOW = dict(PLAIN, sus=30)

# On ?brain=js (5m): this suite reads the page's own brain - its sources'
# functions, bound directly - which core/tests/parity.py holds the instrument
# to, sample for sample. The instrument, the site's default since 5m, is
# braintest.py's and hosttest.py's.
import os
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
    return Promise.resolve({ inputs: new Map([["in", port]]), outputs: new Map([["out1", out]]), onstatechange: null });
  };
  window.__send = (bytes) => window.__midi.port.onmidimessage({ data: Uint8Array.from(bytes) });
  window.__wait = (ms) => new Promise((r) => setTimeout(r, ms));
  // What the generator is playing: the poly voices' notes, or in the dyad the
  // interval menu index it has been given.
  window.__voices = () => (genSettings().voices || []).map((v) => v.note);
  // Held notes into the arpeggiator, then a run of steps on synthetic times
  // from its own start, each step read as what the generator plays.
  window.__walk = (mode, octaves, keys, steps) => {
    el.arpMode.value = mode; el.arpOctaves.value = String(octaves); el.arpMode.dispatchEvent(new Event('change'));
    for (const k of keys) __send([0x90, k, 100]);
    // Nothing yet: the first key waits 25 ms for the rest of the chord.
    window.__early = __voices().length;
    const t0 = arp.start, dt = arpStepMs(), seen = [];
    for (let i = 0; i < steps; i++) { arpTick(t0 + i * dt + 1); seen.push(__voices()); }
    for (const k of keys) __send([0x80, k, 0]);
    return seen;
  };
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
    p.goto(f"file://{ART}/scope.html?brain=js"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate("() => midiConnect()"); p.wait_for_timeout(300)
    p.evaluate("() => { el.midiPoly.click(); setTempo(120); }"); p.wait_for_timeout(200)

    print("\n--- the order ---")
    C, E, G = 60, 64, 67
    walks = p.evaluate("""() => ({
      up: __walk('up', 1, [60, 64, 67], 6), early: __early,
      down: __walk('down', 1, [60, 64, 67], 6),
      updown: __walk('updown', 1, [60, 64, 67], 8),
      played: __walk('played', 1, [67, 60, 64], 6),
      two: __walk('up', 2, [60, 64, 67], 7),
      random: __walk('random', 1, [60, 64, 67], 40),
    })""")
    for k, v in walks.items():
        if k not in ("random", "early"): print("    %-7s %s" % (k, v))
    check("the first key waits for the rest of the chord rather than striking alone", walks["early"] == 0,
          str(walks["early"]))
    flat = lambda w: [x[0] if len(x) == 1 else tuple(x) for x in w]
    check("up is C E G and round again, one note at a time", flat(walks["up"]) == [C, E, G, C, E, G], str(walks["up"]))
    check("down is G E C", flat(walks["down"]) == [G, E, C, G, E, C], str(walks["down"]))
    check("up-down goes up and back without playing either end twice in a row",
          flat(walks["updown"]) == [C, E, G, E, C, E, G, E], str(walks["updown"]))
    check("as played is the order the keys went down", flat(walks["played"]) == [G, C, E, G, C, E],
          str(walks["played"]))
    check("two octaves climb the chord and the same an octave up", flat(walks["two"]) == [C, E, G, C + 12, E + 12, G + 12, C],
          str(walks["two"]))
    rnd = flat(walks["random"])
    check("random plays only what is held, and more than one of it", set(rnd) <= {C, E, G} and len(set(rnd)) > 1,
          str(sorted(set(rnd))))

    print("\n--- struck, and the hands kept ---")
    struck = p.evaluate("""() => {
      el.arpMode.value = 'up'; el.arpOctaves.value = '1'; el.arpMode.dispatchEvent(new Event('change'));
      const src = state.source, gate = src.gate.bind(src), gates = [];
      src.gate = (open, v) => { gates.push(open); gate(open, v); };
      for (const k of [60, 64, 67]) __send([0x90, k, 100]);
      arpTick(arp.start + 1);
      const held = midi.notes.length;
      gates.length = 0;
      arpTick(arp.start + arpStepMs() + 1);
      const oneStep = gates.slice();
      for (const k of [60, 64, 67]) __send([0x80, k, 0]);
      src.gate = gate;
      return { held, oneStep, voices: __voices() };
    }""")
    print("    %s" % struck)
    check("each step closes the gate and opens it again, so every note is struck",
          struck["oneStep"][-2:] == [False, True], str(struck["oneStep"]))
    # And the Notes source read three, until F4b cut it.
    check("and the hands are still the whole chord: three held",
          struck["held"] == 3, str(struck))

    print("\n--- the tempo ---")
    tempo = p.evaluate("""() => {
      el.arpMode.value = 'up'; el.arpMode.dispatchEvent(new Event('change'));
      for (const k of [60, 64, 67]) __send([0x90, k, 100]);
      const t0 = arp.start;
      for (let t = 0; t <= 1000; t += 10) arpTick(t0 + t);
      const steps = arp.steps;
      // A long way on, the step is where the clock says, not where a sum of
      // frame times would have drifted to.
      arpTick(t0 + 60000 + 5);
      const far = arp.steps;
      for (const k of [60, 64, 67]) __send([0x80, k, 0]);
      // And at 90 BPM, since 120 is also the page's default and a step that
      // ignored the tempo would pass at it.
      setTempo(90);
      for (const k of [60, 64, 67]) __send([0x90, k, 100]);
      const s0 = arp.start;
      for (let t = 0; t <= 1000; t += 10) arpTick(s0 + t);
      const slow = { steps: arp.steps, stepMs: arpStepMs() };
      for (const k of [60, 64, 67]) __send([0x80, k, 0]);
      setTempo(120);
      return { steps, far, stepMs: 250 === arpStepMs() ? 250 : arpStepMs(), slow };
    }""")
    print("    %s" % tempo)
    check("120 BPM in quavers is a step every 250 ms: five in the first second, counting the first",
          tempo["stepMs"] == 250 and tempo["steps"] == 5, str(tempo))
    check("and a minute on the step count is the clock's, 241, not a drifted one", tempo["far"] == 241, str(tempo))
    check("and at 90 BPM a quaver is 333 ms, four steps in the first second",
          abs(tempo["slow"]["stepMs"] - 1000 / 3) < 1e-6 and tempo["slow"]["steps"] == 4, str(tempo["slow"]))

    print("\n--- the dyad draws the chord's intervals ---")
    dyad = p.evaluate("""() => {
      el.midiDyad.click();
      el.arpMode.value = 'up'; el.arpMode.dispatchEvent(new Event('change'));
      for (const k of [60, 64, 67]) __send([0x90, k, 100]);
      const seen = [];
      for (let i = 0; i < 3; i++) { arpTick(arp.start + i * arpStepMs() + 1); seen.push(genSettings().interval); }
      for (const k of [60, 64, 67]) __send([0x80, k, 0]);
      el.midiPoly.click();
      return seen.map((i) => INTERVALS[i][0]);
    }""")
    print("    %s" % dyad)
    check("in the dyad each step pairs the lowest held note with the arpeggio's: unison, major third, fifth",
          dyad == ["Unison", "Major 3rd", "Perfect 5th"], str(dyad))

    print("\n--- letting go, and switching off ---")
    ends = p.evaluate("""() => {
      el.midiOut.value = 'out1'; el.midiOutCh.value = '0'; el.midiOut.dispatchEvent(new Event('change'));
      el.arpMode.value = 'up'; el.arpMode.dispatchEvent(new Event('change'));
      __sent.length = 0;
      for (const k of [60, 64, 67]) __send([0x90, k, 100]);
      arpTick(arp.start + 1); arpTick(arp.start + arpStepMs() + 1);
      const out = __sent.map((m) => m.slice());
      __sent.length = 0;
      for (const k of [60, 64, 67]) __send([0x80, k, 0]);
      const released = { sent: __sent.map((m) => m.slice()), running: arp.start !== null, voices: __voices() };
      // Off with keys down: the whole chord.
      for (const k of [60, 64, 67]) __send([0x90, k, 100]);
      el.arpMode.value = 'off'; el.arpMode.dispatchEvent(new Event('change'));
      const off = __voices().slice().sort();
      for (const k of [60, 64, 67]) __send([0x80, k, 0]);
      el.midiOut.value = ''; el.midiOut.dispatchEvent(new Event('change'));
      const code = (() => { el.arpMode.value = 'updown'; el.arpRate.value = '1/16'; el.arpOctaves.value = '2';
        el.arpMode.dispatchEvent(new Event('change')); el.arpRate.dispatchEvent(new Event('change'));
        el.arpOctaves.dispatchEvent(new Event('change'));
        const s = snapshot(); return [s.arpMode, s.arpRate, s.arpOctaves]; })();
      el.arpMode.value = 'off'; el.arpMode.dispatchEvent(new Event('change'));
      return { out, released, off, code };
    }""")
    print("    %s" % ends)
    check("its notes go out as MIDI, each ended as the next begins",
          ends["out"] == [[0x90, 60, 100], [0x80, 60, 0], [0x90, 64, 100]], str(ends["out"]))
    check("letting go stops it, and the note that went out is ended",
          [0x80, 64, 0] in ends["released"]["sent"] and ends["released"]["running"] is False, str(ends["released"]))
    check("switched off with keys down, the generator has the whole chord again", ends["off"] == [60, 64, 67],
          str(ends["off"]))
    check("and a setup code carries the mode, the step and the octaves", ends["code"] == ["updown", "1/16", 2],
          str(ends["code"]))

    # The chord's own bookkeeping reapplies the notes when the layers or the
    # mode change (`syncLayers`, `syncPoly`): with the arpeggiator on, what it
    # reapplies must be the step, not the whole chord.
    book = p.evaluate("""() => {
      el.arpMode.value = 'up'; el.arpOctaves.value = '1'; el.arpMode.dispatchEvent(new Event('change'));
      for (const k of [60, 64, 67]) __send([0x90, k, 100]);
      arpTick(arp.start + 1);
      const before = __voices().slice();
      el.midiLayers.value = 'layer'; el.midiLayers.dispatchEvent(new Event('change'));
      syncLayers();
      const after = __voices().slice();
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change'));
      for (const k of [60, 64, 67]) __send([0x80, k, 0]);
      el.arpMode.value = 'off'; el.arpMode.dispatchEvent(new Event('change'));
      return { before, after };
    }""")
    check("when the layers change mid-arpeggio the generator is still given the step, not the whole chord",
          book["before"] == [60] and book["after"] == [60], str(book))

    print("\n--- switched off once it has stepped, what is held is struck ---")
    off = p.evaluate("""() => {
      const src = state.source, gate = src.gate.bind(src), gates = [];
      el.arpMode.value = 'up'; el.arpOctaves.value = '1'; el.arpMode.dispatchEvent(new Event('change'));
      for (const k of [60, 64, 67]) __send([0x90, k, 100]);
      arpTick(arp.start + 1);
      src.gate = (open, v) => { gates.push(open); gate(open, v); };
      el.arpMode.value = 'off'; el.arpMode.dispatchEvent(new Event('change'));
      const stepped = { gates: gates.slice(), voices: __voices().slice().sort() };
      gates.length = 0;
      // On and off again inside the gather, before its first step.
      el.arpMode.value = 'up'; el.arpMode.dispatchEvent(new Event('change'));
      el.arpMode.value = 'off'; el.arpMode.dispatchEvent(new Event('change'));
      const gathering = { gates: gates.slice(), voices: __voices().slice().sort() };
      src.gate = gate;
      for (const k of [60, 64, 67]) __send([0x80, k, 0]);
      return { stepped, gathering };
    }""")
    print("    %s" % off)
    check("switched off after a step, the held chord is struck: the gate closes and opens, and the generator has all of it",
          off["stepped"]["gates"][-2:] == [False, True] and off["stepped"]["voices"] == [60, 64, 67], str(off["stepped"]))
    check("null: switched off inside the gather, before any step, the chord it never took is not struck again",
          False not in off["gathering"]["gates"] and off["gathering"]["voices"] == [60, 64, 67], str(off["gathering"]))

    # The sound, on both brains: a key held under a plain setup, then through
    # an arpeggiated one long enough for it to step, then the plain one again.
    for query, brain in (("", "the site's instrument"), ("&brain=js", "the page's own brain")):
        q = b.new_page(viewport={"width": 1400, "height": 900})
        q.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
        q.goto(f"file://{ART}/scope.html?picture=0" + query); q.wait_for_timeout(1500)
        if q.locator("#helpClose").is_visible(): q.locator("#helpClose").click()
        through = q.evaluate(LEVEL, [["load", PLAIN], ["on", 57], ["wait", 700], ["read", None],
                                     ["load", ARP], ["wait", 800], ["load", PLAIN], ["wait", 600], ["read", None]])
        low = q.evaluate(LEVEL, [["load", PLAIN], ["on", 57], ["wait", 700], ["read", None], ["off", 57],
                                 ["load", LOW], ["wait", 300], ["on", 57], ["wait", 600], ["load", PLAIN], ["wait", 600],
                                 ["read", None]])
        q.close()
        ref, after = through
        check("on %s, a key held through an arpeggiated setup and into a plain one sounds at the plain one's level" % brain,
              ref > 0.1 and abs(after / ref - 1) < 0.03, "%.4f against %.4f struck under it" % (after, ref))
        check("null: on %s a key struck under a sustain of 0.3 and held into the same setup keeps its lower level" % brain,
              low[1] / low[0] < 0.6, "%.4f against %.4f" % (low[1], low[0]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
