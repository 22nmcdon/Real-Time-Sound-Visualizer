"""The gate and the envelope: what a key does to the generator now it sounds.

`tone.amp` was a constant, so there was nothing to gate and a note could only
set a pitch. Releasing everything left the last note standing, because closing
a gate with no envelope behind it would have been a picture that vanished when
you lifted your hands.

Four things are checked here.

IT IS NOT THERE UNTIL IT IS ASKED FOR. With no keyboard driving the generator
the envelope is a multiply by one, and that is not a detail - every preset in
this page and every test that predates a keyboard depends on a steady waveform.
`setGated(false)` has to be exactly the old arithmetic and not nearly it.

THE SHAPE, RENDERED. Not the value of a variable read back, which would only
say the code wrote what it wrote: the real worklet in an `OfflineAudioContext`,
with the envelope measured off the samples that came out of it.

NO STEP AT ANY EDGE. A gate edge, and the harmonograph's restart - which B1
turned up and flagged for this stage. The pendulums run down and the loop lets
them go again, and that used to put the envelope back to one in a single
sample: invisible on a screen, a click the moment there is an output.

LEGATO. A second note over a held one changes the pitch and leaves the
envelope alone, which is what makes a run of notes a phrase. After a release
has finished, the same second note has to start it again.
"""
import math, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

# One stub port, so a key can actually be pressed. Installed before the page's
# own script runs, the same as `miditest.py` does it, because `midi.supported`
# is read at load.
STUB = """
  window.__midi = { port: null };
  navigator.requestMIDIAccess = function () {
    const port = { id: "stub", name: "Stub Keyboard", onmidimessage: null };
    window.__midi.port = port;
    const inputs = new Map([["stub", port]]);
    return Promise.resolve({ inputs, outputs: new Map(), onstatechange: null });
  };
  window.__send = function (bytes) {
    window.__midi.port.onmidimessage({ data: Uint8Array.from(bytes) });
  };
"""

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


# The envelope as it can be measured off rendered audio: the peak of each
# window, which for a window holding a couple of periods is the amplitude.
# Coarser than reading a variable and that is the point - it is the only thing
# a listener could hear.
ENVELOPE_OF = """(samples, rate, windowMs) => {
  const per = Math.max(8, Math.round(windowMs * rate / 1000));
  const out = [];
  for (let at = 0; at + per <= samples.length; at += per) {
    let peak = 0;
    for (let i = at; i < at + per; i++) peak = Math.max(peak, Math.abs(samples[i]));
    out.push(peak);
  }
  return out;
}"""

# The largest step between one sample and the next, which is what a click is.
WORST_STEP = """(samples, from, to) => {
  let worst = 0, at = -1;
  for (let i = Math.max(1, from); i < Math.min(samples.length, to); i++) {
    const step = Math.abs(samples[i] - samples[i - 1]);
    if (step > worst) { worst = step; at = i; }
  }
  return { worst, at };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    p.add_init_script(STUB)
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)
    p.evaluate("([a, b]) => { window.__env = eval(a); window.__step = eval(b); }",
               [ENVELOPE_OF, WORST_STEP])

    print("\n--- it is not there until it is asked for ---")
    ungated = p.evaluate("""() => {
      // A core of its own, with oscillators of its own, so nothing here
      // touches the two the page is using.
      const own = () => [
        { shape: 'sine', rate: 0.2, depth: 0.5, phase: 0, held: 0, value: 0 },
        { shape: 'sine', rate: 0.5, depth: 0.3, phase: 0, held: 0, value: 0 },
      ];
      const rate = 44100, n = 4410;
      const core = makeGeneratorCore(rate, GEN_DESTS.length, own());
      core.set('shape', 'sine');
      const l = new Float32Array(n), r = new Float32Array(n);
      core.block(l, r, n);

      let peakEarly = 0, peakLate = 0;
      for (let i = 0; i < 441; i++) peakEarly = Math.max(peakEarly, Math.abs(l[i]));
      for (let i = n - 441; i < n; i++) peakLate = Math.max(peakLate, Math.abs(l[i]));
      return { gated: core.gated, envelope: core.envelope,
               peakEarly, peakLate, amp: core.tone.amp };
    }""")
    check("a core nobody has gated is wide open and says so",
          ungated["gated"] is False and ungated["envelope"] == 1, str(ungated))
    check("and its amplitude is the slider, from the first sample to the last",
          abs(ungated["peakEarly"] - ungated["amp"]) < 1e-3
          and abs(ungated["peakLate"] - ungated["amp"]) < 1e-3,
          "%.4f then %.4f against %.4f"
          % (ungated["peakEarly"], ungated["peakLate"], ungated["amp"]))
    # The page as it opens: no keyboard, so no gate, whatever else is true.
    check("and the page opens with the generator ungated",
          p.evaluate("() => state.source.kind === 'tone' && state.source.gated === false"))

    print("\n--- the shape, off the samples the worklet produced ---")
    # Timing an event inside an offline render is not obvious and the obvious
    # way is wrong. A message posted before `startRendering` is never
    # processed: the render runs to completion and the port is drained
    # afterwards, so the first version of this measured a whole second of
    # silence and four of its checks passed on the zeros. A message posted
    # from inside a `suspend` callback does arrive, exactly at the frame the
    # suspend named, which is the only way to place one.
    STAGED = """async ([seconds, holdSeconds, gated, patch]) => {
      const rate = 44100, frames = Math.round(rate * seconds);
      const ctx = new OfflineAudioContext(2, frames, rate);
      await ctx.audioWorklet.addModule(
        'data:application/javascript,' + encodeURIComponent(generatorModuleSource()));
      const tone = Object.assign(
        JSON.parse(JSON.stringify(state.source.settings)),
        { shape: 'sine', mode: 'wave', freq: 220, amp: 0.55 }, patch || {});
      const node = new AudioWorkletNode(ctx, 'generator', {
        numberOfInputs: 0, numberOfOutputs: 1, outputChannelCount: [2],
        processorOptions: { slots: GEN_DESTS.length, lfos: [
          { shape: 'sine', rate: 0.2, depth: 0.5 },
          { shape: 'sine', rate: 0.5, depth: 0.3 },
        ], tone, routes: [], gated },
      });
      node.connect(ctx.destination);

      // Frame boundaries, because a render quantum is 128 and a suspend
      // between two of them is not a thing that can happen.
      const onAt = 128;
      const offAt = Math.round(holdSeconds * rate / 128) * 128;
      if (gated) {
        ctx.suspend(onAt / rate).then(() => {
          node.port.postMessage({ gate: { open: true, velocity: 1 } });
          ctx.resume();
        });
        ctx.suspend(offAt / rate).then(() => {
          node.port.postMessage({ gate: { open: false, velocity: 0 } });
          ctx.resume();
        });
      }
      const out = await ctx.startRendering();
      return { left: Array.from(out.getChannelData(0)), rate, frames, onAt, offAt };
    }"""

    shaped = p.evaluate(STAGED, [1.0, 0.45, True, {
        "attackMs": 50, "decayMs": 100, "sustain": 0.5, "releaseMs": 200,
    }])
    env = p.evaluate("""([left, rate]) => window.__env(Float32Array.from(left), rate, 10)""",
                     [shaped["left"], shaped["rate"]])
    amp = 0.55
    at = lambda ms: env[int(ms / 10)]
    print("    10 ms windows, as a fraction of the amplitude:")
    print("      " + "  ".join("%.0fms %.2f" % (ms, at(ms) / amp)
                               for ms in (0, 20, 60, 120, 300, 440, 500, 700, 950)))
    check("it starts from nothing", at(0) / amp < 0.35, "%.3f" % (at(0) / amp))
    # The peak and when it happened, rather than the value at one window. The
    # attack ends and the decay starts in the same sample, so a window chosen
    # a little late is already on the way down - which is true of the signal
    # and not a fault in it.
    peak_at = max(range(len(env)), key=lambda i: env[i])
    check("and is open within the attack it was given",
          env[peak_at] / amp > 0.9 and peak_at * 10 <= 70,
          "%.3f, reached at %d ms, attack 50" % (env[peak_at] / amp, peak_at * 10))
    check("then falls to the sustain it was given",
          abs(at(300) / amp - 0.5) < 0.04 and abs(at(440) / amp - 0.5) < 0.04,
          "%.3f at 300 ms, %.3f at 440" % (at(300) / amp, at(440) / amp))
    check("and is gone within the release it was given",
          at(700) / amp < 0.02,
          "%.4f at 700 ms, released at 450 with 200 ms" % (at(700) / amp))

    # The numbers on the sliders, as durations rather than as shapes. A
    # one-pole aimed at its own target never arrives, so "50 ms" used to mean
    # a 50 ms time constant and a 90 ms attack; each stage works out its own
    # span in time constants at the edge, from where the envelope actually is,
    # so the label is now the duration. Measured at 10 ms resolution, which is
    # the window this envelope is read through.
    settled = next((i for i in range(len(env))
                    if abs(env[i] / amp - 0.5) < 0.02), None)
    silent = next((i for i in range(int(shaped["offAt"] / shaped["rate"] * 100),
                                    len(env)) if env[i] / amp < 0.01), None)
    gate_on_ms = shaped["onAt"] / shaped["rate"] * 1000
    gate_off_ms = shaped["offAt"] / shaped["rate"] * 1000
    print("    gate opened at %.0f ms and closed at %.0f; peak at %d, "
          "sustain by %s, silent by %s"
          % (gate_on_ms, gate_off_ms, peak_at * 10,
             settled * 10 if settled is not None else "never",
             silent * 10 if silent is not None else "never"))
    check("the attack takes the time it says, not a time constant",
          abs(peak_at * 10 - (gate_on_ms + 50)) <= 12,
          "peaked %d ms after the gate, asked for 50" % (peak_at * 10 - gate_on_ms))
    check("and the decay arrives at the sustain when it said it would",
          settled is not None and abs(settled * 10 - (gate_on_ms + 150)) <= 25,
          "settled %d ms after the gate, asked for 50 + 100"
          % ((settled or 0) * 10 - gate_on_ms))
    check("and the release is over when it said it would be",
          silent is not None and abs(silent * 10 - (gate_off_ms + 200)) <= 30,
          "silent %d ms after the release, asked for 200"
          % ((silent or 0) * 10 - gate_off_ms))

    # The plan's own wording: within one block. 128 frames at 44.1 kHz is
    # 2.9 ms, so the first block has to be moving rather than silent.
    first = p.evaluate("""([left, onAt]) => {
      const s = Float32Array.from(left);
      let peak = 0;
      for (let i = onAt; i < onAt + 128; i++) peak = Math.max(peak, Math.abs(s[i]));
      return peak;
    }""", [shaped["left"], shaped["onAt"]])
    check("a note-on is doing something inside the block after it",
          first > 1e-4, "peak %.5f in the 128 frames after the gate" % first)

    print("\n--- no step at any edge ---")
    # What a click is measured against: the waveform's own steepest slope. A
    # 220 Hz sine at 0.55 moves 0.0172 between samples at its zero crossing,
    # so anything the envelope adds has to disappear into that.
    slope = 0.55 * 2 * math.pi * 220 / 44100
    edges = p.evaluate("""([left, offAt]) => {
      const s = Float32Array.from(left);
      return {
        onset: window.__step(s, 0, 4410 + 128),
        release: window.__step(s, offAt - 441, offAt + 4410),
        whole: window.__step(s, 0, s.length),
      };
    }""", [shaped["left"], shaped["offAt"]])
    print("    steepest slope of the tone itself: %.4f per sample" % slope)
    check("the gate opening is not a step",
          edges["onset"]["worst"] < slope * 1.2,
          "%.4f at sample %d" % (edges["onset"]["worst"], edges["onset"]["at"]))
    check("nor the gate closing",
          edges["release"]["worst"] < slope * 1.2,
          "%.4f at sample %d" % (edges["release"]["worst"], edges["release"]["at"]))

    # The harmonograph, which is the one B1 flagged. Decay wound right up so
    # the pendulums run down and are let go several times inside one render.
    # Ungated, because the thing being measured is the harmonograph's OWN
    # envelope running down and being let go again. A note envelope on top
    # would be a second amplitude and the step could hide behind it.
    harmo = p.evaluate(STAGED, [1.0, 0.95, False, {
        "mode": "harmonograph", "decay": 20, "swingRate": 2.1, "amp": 0.55,
    }])
    letgo = p.evaluate("""([left]) => {
      const s = Float32Array.from(left);
      const worst = window.__step(s, 0, s.length);
      // How many times it was let go: the envelope's own restarts show as the
      // signal coming back up after falling to nearly nothing.
      const env = window.__env(s, 44100, 20);
      let restarts = 0;
      for (let i = 1; i < env.length; i++) {
        if (env[i - 1] < 0.02 && env[i] > 0.05) restarts++;
      }
      return { worst: worst.worst, at: worst.at, restarts };
    }""", [harmo["left"]])
    print("    let go %d times in a second, steepest step %.4f"
          % (letgo["restarts"], letgo["worst"]))
    check("the pendulums really were let go again inside the render",
          letgo["restarts"] >= 2, str(letgo["restarts"]))
    # A harmonograph at 2.1 Hz is a much slower waveform than the sine above,
    # so its own slope is tiny and a step stands out by a long way. The old
    # behaviour put a quarter of full scale in one sample.
    check("and letting them go is a fade, not a step",
          letgo["worst"] < 0.01,
          "%.4f at sample %d, against the 0.275 a one-sample restart gave"
          % (letgo["worst"], letgo["at"]))

    print("\n--- legato, and what is not legato ---")
    legato = p.evaluate("""() => {
      const own = () => [
        { shape: 'sine', rate: 0.2, depth: 0.5, phase: 0, held: 0, value: 0 },
        { shape: 'sine', rate: 0.5, depth: 0.3, phase: 0, held: 0, value: 0 },
      ];
      const rate = 44100;
      const core = makeGeneratorCore(rate, GEN_DESTS.length, own());
      core.set('shape', 'sine');
      core.set('attackMs', 20); core.set('decayMs', 40);
      core.set('sustain', 0.5); core.set('releaseMs', 60);
      core.setGated(true);
      const l = new Float32Array(4410), r = new Float32Array(4410);
      const run = (ms) => core.block(l, r, Math.round(ms * rate / 1000));

      core.gate(true, 1);
      run(200);                                    // well into sustain
      const held = core.envelope;

      // A second key while the first is down: quieter, and it must change
      // nothing about the envelope.
      core.gate(true, 0.25);
      run(5);
      const overlaid = core.envelope;

      core.gate(false, 0);
      run(300);                                    // all the way out
      const after = core.envelope;

      // And now the same second key, from silence, does start it.
      core.gate(true, 0.25);
      run(60);
      const again = core.envelope;
      return { held, overlaid, after, again };
    }""")
    print("    sustain %.4f, after a second key %.4f, released %.4f, retriggered %.4f"
          % (legato["held"], legato["overlaid"], legato["after"], legato["again"]))
    check("a second key over a held one does not restart the envelope",
          abs(legato["overlaid"] - legato["held"]) < 0.02,
          "%.4f against %.4f" % (legato["overlaid"], legato["held"]))
    check("and does not take its velocity either",
          legato["overlaid"] > 0.4,
          "%.4f, which would be about 0.125 if it had" % legato["overlaid"])
    check("a release runs all the way out",
          legato["after"] == 0, str(legato["after"]))
    # Sustain times velocity, exactly: 0.5 at a quarter is 0.125, against the
    # 0.5 the first key held. Stated as the arithmetic rather than as a band,
    # now that the stages take the time they say and 60 ms is long enough for
    # a 20 ms attack and a 40 ms decay to have finished.
    check("and the next key starts it again, at its own velocity",
          abs(legato["again"] - 0.5 * 0.25) < 0.005,
          "%.4f, which is the 0.5 sustain at a quarter velocity" % legato["again"])

    # The glide's own time, and that it is its own. `poleFor` used to be
    # shared with the envelope and scaled by whichever stage the envelope was
    # in, so a portamento measured on an ungated core was right and the same
    # portamento under a note was not.
    gated_glide = p.evaluate("""() => {
      const own = () => [
        { shape: 'sine', rate: 0.2, depth: 0.5, phase: 0, held: 0, value: 0 },
        { shape: 'sine', rate: 0.5, depth: 0.3, phase: 0, held: 0, value: 0 },
      ];
      const rate = 44100;
      const measure = (gated) => {
        const core = makeGeneratorCore(rate, GEN_DESTS.length, own());
        core.set('shape', 'sine');
        core.set('glideMs', 200);
        core.set('sustain', 1);
        core.set('attackMs', 1); core.set('decayMs', 1);
        core.set('freq', 220);
        if (gated) { core.setGated(true); core.gate(true, 1); }
        const l = new Float32Array(rate), r = new Float32Array(rate);
        core.block(l, r, 4410);                    // settle, and open the gate
        core.set('freq', 440);
        core.block(l, r, 2205);
        return estimateFrequency(l.subarray(441, 2205), rate);
      };
      return { open: measure(false), held: measure(true) };
    }""")
    print("    50 ms into a glide: %.1f Hz ungated, %.1f Hz under a note"
          % (gated_glide["open"] or 0, gated_glide["held"] or 0))
    check("a glide takes the same time whether a note is holding or not",
          gated_glide["open"] is not None and gated_glide["held"] is not None
          and abs(gated_glide["open"] - gated_glide["held"]) < 8,
          "%.1f against %.1f" % (gated_glide["open"], gated_glide["held"]))

    print("\n--- the envelope as something to point at ---")
    source = p.evaluate("""() => {
      const listed = Array.from(MOD_SOURCES.keys());
      const note = MOD_SOURCES.get('env.note');
      return { listed, hasNote: !!note, ungated: note ? note.value() : null,
               label: note ? note.label : null };
    }""")
    check("it is registered beside the level meter",
          source["hasNote"] and "env.live" in source["listed"], str(source["listed"]))
    check("and reads nothing while nothing is gated",
          source["ungated"] == 0, str(source["ungated"]))

    glide = p.evaluate("""() => {
      const own = () => [
        { shape: 'sine', rate: 0.2, depth: 0.5, phase: 0, held: 0, value: 0 },
        { shape: 'sine', rate: 0.5, depth: 0.3, phase: 0, held: 0, value: 0 },
      ];
      const rate = 44100;
      const measure = (glideMs) => {
        const core = makeGeneratorCore(rate, GEN_DESTS.length, own());
        core.set('shape', 'sine');
        core.set('glideMs', glideMs);
        core.set('freq', 220);
        const l = new Float32Array(rate), r = new Float32Array(rate);
        core.block(l, r, 2205);                    // 50 ms at 220
        core.set('freq', 440);
        core.block(l, r, 2205);                    // the next 50 ms
        return estimateFrequency(l.subarray(441, 2205), rate);
      };
      return { off: measure(0), on: measure(200) };
    }""")
    print("    the 50 ms after a jump to 440: %s off, %s with a 200 ms glide"
          % (glide["off"], glide["on"]))
    check("with no glide the pitch is simply the new one",
          glide["off"] is not None and abs(glide["off"] - 440) < 12,
          str(glide["off"]))
    check("and with a glide it is still on its way there",
          glide["on"] is not None and glide["on"] < 400,
          str(glide["on"]))

    print("\n--- and a key on a real keyboard, end to end ---")
    # None of the above presses a key. The envelope could be perfect and the
    # note stack could reach none of it, which is the join this whole stage
    # exists to make.
    played = p.evaluate("""async () => {
      await midiConnect();
      state.genSound = false;
      midi.drive.wave = true;
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change'));
      state.source.set('attackMs', 10);
      state.source.set('decayMs', 20);
      state.source.set('sustain', 0.8);
      state.source.set('releaseMs', 40);
      const read = () => MOD_SOURCES.get('env.note').value();
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));

      await wait(80);
      const idle = { gated: state.source.gated, env: read() };
      window.__send([0x90, 69, 100]);              // A4, hard
      await wait(160);
      const held = { gated: state.source.gated, env: read() };
      window.__send([0x80, 69, 0]);                // and up
      await wait(200);
      const gone = { gated: state.source.gated, env: read() };

      /* A key already down when the gate is HANDED OVER has to sound. Ticking
         Drives while holding a note is the obvious way to do it, and the
         obvious way for it to be wrong is for the gate to open and then wait
         for a key that is already there. */
      midi.drive.wave = false;
      await wait(120);
      window.__send([0x90, 69, 100]);
      await wait(80);
      const beforeHandover = { gated: state.source.gated, env: read() };
      midi.drive.wave = true;
      await wait(160);
      const afterHandover = { gated: state.source.gated, env: read() };

      // Unticking Drives has to hand the generator back, not leave it shut.
      midi.drive.wave = false;
      await wait(120);
      const handedBack = { gated: state.source.gated, env: read() };
      /* Left with the keyboard not driving it, because that is what the next
         check is about: the trace has to come back, and a generator that is
         gated with nothing held is correctly silent. */
      midiPanic();
      const line = el.readoutDetail.textContent;
      return { idle, held, gone, handedBack, line,
               beforeHandover, afterHandover };
    }""")
    print("    idle %s, held %s, released %s, drives off %s"
          % (played["idle"], played["held"], played["gone"], played["handedBack"]))
    check("connecting a keyboard that drives the generator gates it",
          played["idle"]["gated"] is True and played["idle"]["env"] == 0,
          str(played["idle"]))
    check("a key opens the envelope, at the velocity it was played",
          played["held"]["env"] > 0.5 and played["held"]["env"] < 0.85,
          "%.4f, against a 0.8 sustain at velocity %.2f"
          % (played["held"]["env"], 100 / 127))
    check("and letting go closes it",
          played["gone"]["env"] == 0, str(played["gone"]))
    check("a key held while the gate is handed over sounds straight away",
          played["beforeHandover"]["gated"] is False
          and played["afterHandover"]["gated"] is True
          and played["afterHandover"]["env"] > 0.5,
          "%s then %s" % (played["beforeHandover"], played["afterHandover"]))
    check("unticking Drives hands the generator back wide open",
          played["handedBack"]["gated"] is False
          and played["handedBack"]["env"] == 0
          and p.evaluate("() => state.source.settings.amp > 0"),
          str(played["handedBack"]))

    # And the picture is really there again rather than merely ungated.
    p.wait_for_timeout(300)
    back = p.evaluate("""() => {
      const w = state.source.getLatestWindow(4096)[0];
      let peak = 0;
      for (let i = 0; i < w.length; i++) peak = Math.max(peak, Math.abs(w[i]));
      return peak;
    }""")
    check("and the trace comes back with it",
          back > 0.3, "peak %.3f" % back)

    # The one state in this page where a blank screen is correct, and it has
    # to say so. A generator gated with no key down is silent by design; a
    # scope that just went dark would send somebody to the amplitude slider.
    # Polled rather than slept on. The readout line is rewritten at
    # READOUT_MS - a quarter of a second, not every frame - so a fixed wait is
    # a race, and this check failed about one run in three before it waited
    # for the thing it was asserting about instead of for a number of
    # milliseconds.
    said = p.evaluate("""async () => {
      const until = async (wanted, ms) => {
        const stop = performance.now() + ms;
        while (performance.now() < stop) {
          if (wanted()) return true;
          await new Promise((r) => setTimeout(r, 30));
        }
        return false;
      };
      const says = () => el.readoutDetail.textContent.indexOf("no note held") >= 0;

      midi.drive.wave = true;
      const appeared = await until(says, 1500);
      const gated = state.source.gated;
      const line = el.readoutDetail.textContent;

      midi.drive.wave = false;
      const cleared = await until(() => !says(), 1500);
      return { gated, line, appeared, cleared,
               after: el.readoutDetail.textContent };
    }""")
    check("a gate held open with nothing played says why the screen is empty",
          said["gated"] and said["appeared"], said["line"][:80])
    check("and stops saying it when the generator is handed back",
          said["cleared"], said["after"][:80])

    # And the drawn modes are not gated at all, which is the decision that
    # keeps a keyboard from blanking a harmonograph nobody is playing.
    drawn = p.evaluate("""async () => {
      midi.drive.harmonograph = true;
      el.genMode.value = 'harmonograph';
      el.genMode.dispatchEvent(new Event('change'));
      await new Promise((r) => setTimeout(r, 300));
      const gated = state.source.gated;
      const w = state.source.getLatestWindow(4096)[0];
      let peak = 0;
      for (let i = 0; i < w.length; i++) peak = Math.max(peak, Math.abs(w[i]));
      el.genMode.value = 'wave';
      el.genMode.dispatchEvent(new Event('change'));
      return { gated, peak };
    }""")
    check("a harmonograph with a keyboard attached is not gated, and draws",
          drawn["gated"] is False and drawn["peak"] > 0.05, str(drawn))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the gate opens and closes without a step in it")
