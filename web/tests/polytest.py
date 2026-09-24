"""Poly: every held note sounding, and a picture that draws some of them.

What would go wrong, and what is checked for it:

- the draw rule picking the wrong notes. The fixture is five notes pressed in
  an order that is not their pitch order, with the top note pressed FIRST, so
  that "outer", "highest" and "most recent" all give different answers and no
  two rules can pass for each other;
- an undrawn note leaking into the picture, or a drawn one missing from what
  is heard. Checked at the core, by energy at each note's own frequency in the
  picture pair and the heard pair separately, and again through the worklet,
  where the picture crosses a thread and the sound goes to the speakers;
- voices sharing an envelope, so releasing one note ends the chord;
- the tuning: just is the lowest note's small whole-number ratios, exactly;
- the chord being clamped, when louder was asked for and the limiter is what
  catches it - while the picture keeps its full-scale edge;
- the cap, the readout, the sources and the setup code;
- poly lingering after the thing that made it poly has gone.

Frequencies are read by a Hann-windowed single-bin transform at each note's
frequency, never by the page's pitch estimator: that counts zero crossings, and
a sum of notes crosses zero at the rate of none of them.
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

HZ = lambda note: 440 * 2 ** ((note - 69) / 12)

# Energy at one frequency, installed once.
BIN = """(src) => { window.__bin = eval(src); }"""
BIN_SRC = """(x, f, rate) => {
  let re = 0, im = 0;
  for (let i = 0; i < x.length; i++) {
    const w = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (x.length - 1));
    re += x[i] * w * Math.cos(2 * Math.PI * f * i / rate);
    im -= x[i] * w * Math.sin(2 * Math.PI * f * i / rate);
  }
  return Math.hypot(re, im) / x.length;
}"""

# A core of its own, driven directly: the arithmetic under test without a
# frame loop or a keyboard between it and the assertion.
CORE = """([voices, seconds, shape]) => {
  const rate = 44100;
  const quiet = [0, 1].map(() => ({ shape: 'sine', rate: 1, depth: 0, phase: 0, held: 0, value: 0 }));
  const core = makeGeneratorCore(rate, GEN_DESTS.length, quiet);
  core.set('shape', shape || 'sine');
  core.set('voices', voices);
  window.__core = core;
  const n = Math.round(rate * seconds);
  const pl = new Float32Array(n), pr = new Float32Array(n);
  const hl = new Float32Array(n), hr = new Float32Array(n);
  core.block(pl, pr, n, hl, hr);
  window.__run = { pl, pr, hl, hr, rate };
  return n;
}"""

# Energy at each of the given frequencies in the last `tail` seconds of each
# of the four channels, as a fraction of the loudest.
READ = """([freqs, tail]) => {
  const { pl, pr, hl, hr, rate } = window.__run;
  const take = (x) => x.subarray(x.length - Math.round(rate * tail));
  const out = {};
  for (const [k, x] of [['pl', pl], ['pr', pr], ['hl', hl], ['hr', hr]]) {
    out[k] = freqs.map((f) => window.__bin(take(x), f, rate));
  }
  let peak = { pl: 0, pr: 0, hl: 0, hr: 0 };
  for (const [k, x] of [['pl', pl], ['pr', pr], ['hl', hl], ['hr', hr]]) {
    const t = take(x);
    let m = 0, s = 0;
    for (let i = 0; i < t.length; i++) { m = Math.max(m, Math.abs(t[i])); s += t[i] * t[i]; }
    peak[k] = { max: m, rms: Math.sqrt(s / t.length) };
  }
  out.peak = peak;
  return out;
}"""


def rounded(xs):
    return [round(x, 4) for x in xs]


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
    p.evaluate(BIN, BIN_SRC)

    print("\n--- the core: what is drawn, and what is heard ---")
    C, E, G = HZ(48), HZ(48) * 5 / 4, HZ(48) * 3 / 2
    chord = [{"note": 48, "freq": C, "velocity": 1, "role": "x"},
             {"note": 52, "freq": E, "velocity": 1, "role": "u"},
             {"note": 55, "freq": G, "velocity": 1, "role": "y"}]
    p.evaluate(CORE, [chord, 0.6, "sine"])
    r = p.evaluate(READ, [[C, E, G], 0.3])
    print("    energy at C, E, G - picture L %s, picture R %s, heard L %s, heard R %s"
          % (rounded(r["pl"]), rounded(r["pr"]), rounded(r["hl"]), rounded(r["hr"])))
    full = max(r["pl"][0], 1e-9)
    check("the picture's X is the bass alone", r["pl"][1] < full * 0.01 and r["pl"][2] < full * 0.01,
          str(rounded(r["pl"])))
    check("the picture's Y is the drawn upper note alone",
          r["pr"][2] > full * 0.5 and r["pr"][0] < full * 0.01 and r["pr"][1] < full * 0.01,
          str(rounded(r["pr"])))
    check("the undrawn E is heard in both ears",
          r["hl"][1] > full * 0.5 and r["hr"][1] > full * 0.5,
          "left %.4f, right %.4f" % (r["hl"][1], r["hr"][1]))
    check("and each drawn note is heard on its own side only",
          r["hl"][0] > full * 0.5 and r["hl"][2] < full * 0.01
          and r["hr"][2] > full * 0.5 and r["hr"][0] < full * 0.01,
          "heard L %s, heard R %s" % (rounded(r["hl"]), rounded(r["hr"])))

    # Louder, not normalised - and the picture keeps its edge.
    four = [{"note": n, "freq": HZ(n), "velocity": 1, "role": "u"} for n in (48, 52, 55, 59)]
    p.evaluate(CORE, [four[:1], 0.5, "sine"]); one = p.evaluate(READ, [[C], 0.3])["peak"]
    p.evaluate(CORE, [four, 0.5, "sine"]); many = p.evaluate(READ, [[C], 0.3])["peak"]
    print("    one voice heard: rms %.3f, peak %.3f; four: rms %.3f, peak %.3f"
          % (one["hl"]["rms"], one["hl"]["max"], many["hl"]["rms"], many["hl"]["max"]))
    check("four notes are louder than one - about twice, not the same",
          many["hl"]["rms"] > one["hl"]["rms"] * 1.6, "%.3f against %.3f"
          % (many["hl"]["rms"], one["hl"]["rms"]))
    check("and what is heard is not clamped, because the limiter is what catches it",
          many["hl"]["max"] > 1.0, "peak %.3f" % many["hl"]["max"])
    p.evaluate(CORE, [[dict(v, role="xy") for v in four], 0.5, "sine"])
    edge = p.evaluate(READ, [[C], 0.3])["peak"]
    check("while the picture stops at full scale, which is the edge of the screen",
          edge["pl"]["max"] <= 1.0 and edge["pl"]["max"] > 0.99, "peak %.4f" % edge["pl"]["max"])

    # A note changing role - joining the picture as the chord changes - has
    # its gains glide rather than step. A square wave, because its value is
    # always near full either way: with a sine the switch could land near a
    # zero crossing and a step would look like a glide by luck.
    jump = p.evaluate("""([C, G]) => {
      const rate = 44100;
      const quiet = [0, 1].map(() => ({ shape: 'sine', rate: 1, depth: 0, phase: 0, held: 0, value: 0 }));
      const core = makeGeneratorCore(rate, GEN_DESTS.length, quiet);
      core.set('shape', 'square');
      const x = { note: 48, freq: C, velocity: 1, role: 'x' };
      core.set('voices', [x, { note: 55, freq: G, velocity: 1, role: 'u' }]);
      const a = [0, 1, 2, 3].map(() => new Float32Array(8820));
      core.block(a[0], a[1], 8820, a[2], a[3]);
      const before = Math.abs(a[1][8819]);
      core.set('voices', [x, { note: 55, freq: G, velocity: 1, role: 'y' }]);
      const b = [0, 1, 2, 3].map(() => new Float32Array(2205));
      core.block(b[0], b[1], 2205, b[2], b[3]);
      return { before, first: Math.abs(b[1][0]), later: Math.abs(b[1][2204]) };
    }""", [C, G])
    print("    G joining the picture: Y was %.4f, first sample after %.4f, 50 ms later %.4f"
          % (jump["before"], jump["first"], jump["later"]))
    check("a note joining the picture fades in over milliseconds, not in one sample",
          jump["before"] < 1e-6 and jump["first"] < 0.02 and jump["later"] > 0.3, str(jump))

    print("\n--- each voice has its own envelope ---")
    env = p.evaluate("""([chord]) => {
      const core = window.__core;
      const rate = 44100;
      const run = (seconds) => {
        const n = Math.round(rate * seconds);
        const a = [0, 1, 2, 3].map(() => new Float32Array(n));
        core.block(a[0], a[1], n, a[2], a[3]);
        return a;
      };
      core.set('voices', null);
      core.set('releaseMs', 60);
      core.set('voices', chord);
      run(0.3);
      const before = core.voices.map((v) => [v.note, v.stage]);
      core.set('voices', chord.filter((v) => v.note !== 52));   // E released
      const during = core.voices.map((v) => [v.note, v.stage, v.held]);
      const tail = run(0.4);
      const after = core.voices.map((v) => [v.note, v.stage]);
      const x = tail[2].subarray(tail[2].length - 8192);
      const add = chord.concat([{ note: 60, freq: 261.6, velocity: 1, role: 'u' }]);
      core.set('voices', add.filter((v) => v.note !== 52));
      const retrigger = core.voices.map((v) => [v.note, v.stage]);
      return { before, during, after, retrigger,
               e: window.__bin(x, chord[1].freq, rate), c: window.__bin(x, chord[0].freq, rate) };
    }""", [chord])
    print("    held %s; E released %s; after its release %s; C still %.4f, E %.5f"
          % (env["before"], env["during"], env["after"], env["c"], env["e"]))
    print("    a fourth note added: %s" % env["retrigger"])
    check("releasing one note releases that voice and no other",
          [s for n, s, h in env["during"] if n == 52] == ["release"]
          and all(s == "sustain" for n, s, h in env["during"] if n != 52), str(env["during"]))
    check("and once its release is over it is gone, while the rest sound on",
          [n for n, s in env["after"]] == [48, 55] and env["e"] < env["c"] * 0.01,
          "voices %s, E at %.5f of C's %.4f" % (env["after"], env["e"], env["c"]))
    check("a note added to a chord does not restart the others",
          dict((n, s) for n, s in env["retrigger"])[48] == "sustain"
          and dict((n, s) for n, s in env["retrigger"])[60] == "attack", str(env["retrigger"]))

    print("\n--- the draw rules, through the keyboard ---")
    # The top note pressed first, so outer, highest and most recent disagree.
    p.evaluate("() => { setScreenKeys(true); el.midiPoly.click(); }")
    p.wait_for_timeout(150)
    ORDER = [74, 48, 52, 55, 59]
    p.evaluate("(order) => { for (const n of order) midiNoteOn(n, 100); }", ORDER)

    def roles(count, which):
        return p.evaluate("""([count, which]) => {
          el.midiDrawCount.value = String(count); el.midiDrawCount.dispatchEvent(new Event('change'));
          el.midiDrawWhich.value = which; el.midiDrawWhich.dispatchEvent(new Event('change'));
          const out = {};
          for (const v of genSettings().voices) out[v.note] = v.role;
          return out;
        }""", [count, which])

    def xy(r):
        return (sorted(int(n) for n, v in r.items() if v == "x"),
                sorted(int(n) for n, v in r.items() if v == "y"))

    cases = [
        (2, "outer", ([48], [74])),
        (3, "outer", ([48], [59, 74])),
        (3, "lowest", ([48], [52, 55])),
        (2, "highest", ([59], [74])),
        (2, "recent", ([55], [59])),
    ]
    for count, which, want in cases:
        got = xy(roles(count, which))
        check("draw %d, %s: X %s, Y %s" % (count, which, want[0], want[1]),
              got == want, "got X %s, Y %s" % got)

    counts = p.evaluate("""() => { const v = genSettings().voices;
      return { n: v.length, u: v.filter((x) => x.role === 'u').length }; }""")
    check("everything not drawn is still sounding", counts == {"n": 5, "u": 3}, str(counts))

    p.wait_for_timeout(450)
    readout = p.evaluate("() => el.readoutDetail.textContent")
    check("the readout says the picture is leaving notes out",
          "drawing 2 of 5 notes" in readout, readout)

    # Two notes: every rule is the dyad.
    p.evaluate("(order) => { for (const n of order) midiNoteOff(n); }", ORDER)
    p.evaluate("() => { midiNoteOn(55, 100); midiNoteOn(48, 100); }")
    two = [xy(roles(2, w)) for w in ("outer", "lowest", "highest", "recent")]
    check("two notes held are the dyad under every rule - lower on X, upper on Y",
          all(t == ([48], [55]) for t in two), str(two))
    p.wait_for_timeout(450)
    quiet = p.evaluate("() => el.readoutDetail.textContent")
    check("and with nothing left out, the readout says nothing about it",
          "drawing" not in quiet, quiet)
    p.evaluate("() => { midiNoteOff(48); }")
    one_role = p.evaluate("() => genSettings().voices.map((v) => v.role)")
    check("one note is drawn on both axes, the unison it has always been",
          one_role == ["xy"], str(one_role))
    p.evaluate("() => midiNoteOff(55)")

    print("\n--- tuning ---")
    tuned = p.evaluate("""() => {
      for (const n of [48, 52, 55]) midiNoteOn(n, 100);
      const just = genSettings().voices.map((v) => v.freq);
      setTuning(false); midiApplyNotes();
      const equal = genSettings().voices.map((v) => v.freq);
      setTuning(true); midiApplyNotes();
      for (const n of [48, 52, 55]) midiNoteOff(n);
      return { just, equal };
    }""")
    c0 = tuned["just"][0]
    check("just is the lowest note's ratios exactly - 4:5:6",
          abs(tuned["just"][1] / c0 - 5 / 4) < 1e-12 and abs(tuned["just"][2] / c0 - 3 / 2) < 1e-12,
          str(tuned["just"]))
    check("equal is each key as it is",
          all(abs(f - HZ(n)) < 1e-9 for f, n in zip(tuned["equal"], (48, 52, 55))),
          str(tuned["equal"]))

    print("\n--- the cap ---")
    capped = p.evaluate("""() => {
      for (let n = 48; n < 58; n++) midiNoteOn(n, 100);
      const v = genSettings().voices.map((x) => x.note);
      return { v, held: midi.notes.length, poly: midi.poly };
    }""")
    p.wait_for_timeout(450)
    said = p.evaluate("() => el.readoutDetail.textContent")
    p.evaluate("() => { for (let n = 48; n < 58; n++) midiNoteOff(n); }")
    print("    ten held: %s; %s" % (capped, said))
    check("ten held, eight sound - the eight most recent",
          capped["v"] == list(range(50, 58)) and capped["held"] == 10, str(capped["v"]))
    check("and the readout says so", "8 of 10 held sound" in said, said)

    print("\n--- the note sources ---")
    src = p.evaluate("""() => {
      el.midiDrawCount.value = '2'; el.midiDrawCount.dispatchEvent(new Event('change'));
      el.midiDrawWhich.value = 'outer'; el.midiDrawWhich.dispatchEvent(new Event('change'));
      midiNoteOn(48, 127); midiNoteOn(52, 64); midiNoteOn(55, 127);
      const read = (id) => MOD_SOURCES.has(id) ? MOD_SOURCES.get(id).value() : null;
      const out = { count: read('notes.count'), spread: read('notes.spread'),
                    top: read('notes.top'), inner: read('notes.inner') };
      for (const n of [48, 52, 55]) midiNoteOff(n);
      out.after = read('notes.count');
      return out;
    }""")
    print("    C3 E3 G3, E softer: %s" % src)
    check("Notes is how many are held, of eight", abs(src["count"] - 3 / 8) < 1e-9, str(src["count"]))
    check("Spread is bottom to top, of two octaves", abs(src["spread"] - 7 / 24) < 1e-9, str(src["spread"]))
    check("Melody is the top note, C2 to C6", abs(src["top"] - (55 - 36) / 48) < 1e-9, str(src["top"]))
    check("Inner is how hard the undrawn notes were played - E alone, not the chord",
          abs(src["inner"] - 64 / 127) < 1e-9, str(src["inner"]))
    check("and they fall back when the notes go", src["after"] == 0, str(src["after"]))

    rowed = p.evaluate("""() => {
      setMidiMode('poly');
      const out = { wave: !el.midiDrawRow.hidden };
      el.genMode.value = 'wireframe'; el.genMode.dispatchEvent(new Event('change'));
      out.wireframe = !el.midiDrawRow.hidden;
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      setMidiMode('dyad'); out.dyad = !el.midiDrawRow.hidden;
      setMidiMode('poly');
      return out;
    }""")
    check("the Draw row is there only where a chord can play",
          rowed == {"wave": True, "wireframe": False, "dyad": False}, str(rowed))

    print("\n--- it stops being poly when it should ---")
    gone = p.evaluate("""() => {
      midiNoteOn(48, 100); midiNoteOn(55, 100);
      const out = { on: genSettings().voices !== null };
      setMidiMode('dyad'); out.dyad = genSettings().voices;
      setMidiMode('poly'); out.back = genSettings().voices !== null;
      el.genMode.value = 'harmonograph'; el.genMode.dispatchEvent(new Event('change'));
      midiApplyGate(); out.harmonograph = genSettings().voices;
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      midiApplyGate(); out.wave = genSettings().voices !== null;
      setScreenKeys(false); midiApplyGate(); out.closed = genSettings().voices;
      return out;
    }""")
    print("    %s" % gone)
    check("switching to dyad ends the chord", gone["on"] and gone["dyad"] is None, str(gone))
    check("and back to poly resumes it", gone["back"], str(gone))
    check("a generator that is not a waveform plays no chord",
          gone["harmonograph"] is None and gone["wave"], str(gone))
    check("and neither does one with no keyboard to play it", gone["closed"] is None, str(gone))

    print("\n--- through the worklet: the picture crosses a thread, the sound does not ---")
    heard = p.evaluate("""async () => {
      setScreenKeys(true); setMidiMode('poly');
      genSet('shape', 'sine');
      el.midiDrawCount.value = '2'; el.midiDrawCount.dispatchEvent(new Event('change'));
      state.genSound = true; await applyGeneratorSound();
      for (const n of [48, 52, 55]) midiNoteOn(n, 100);
      const chain = Array.from(monitorChains)[0];
      const ctx = chain.input.context;
      const tap = ctx.createAnalyser(); tap.fftSize = 16384;
      chain.input.connect(tap);
      await new Promise((r) => setTimeout(r, 900));
      const x = new Float32Array(tap.fftSize); tap.getFloatTimeDomainData(x);
      const w = state.source.getLatestWindow(16384);
      const rate = ctx.sampleRate;
      const tone = genSettings().voices.map((v) => v.freq);
      const out = { audible: state.source.audible(), chains: monitorChains.size,
        heard: tone.map((f) => window.__bin(x, f, rate)),
        drawnL: tone.map((f) => window.__bin(w[0], f, rate)),
        drawnR: tone.map((f) => window.__bin(w[1], f, rate)) };
      for (const n of [48, 52, 55]) midiNoteOff(n);
      state.genSound = false; await applyGeneratorSound();
      return out;
    }""")
    print("    C, E, G - heard %s; drawn X %s; drawn Y %s"
          % (rounded(heard["heard"]), rounded(heard["drawnL"]), rounded(heard["drawnR"])))
    top = max(heard["drawnL"][0], 1e-9)
    check("the worklet is sounding", heard["audible"] and heard["chains"] == 1, str(heard))
    check("the speakers get the undrawn E",
          heard["heard"][1] > heard["heard"][0] * 0.3, str(rounded(heard["heard"])))
    check("and the picture it posts back does not have it",
          heard["drawnL"][1] < top * 0.01 and heard["drawnR"][1] < top * 0.01,
          "X %s, Y %s" % (rounded(heard["drawnL"]), rounded(heard["drawnR"])))

    print("\n--- the setup code carries it ---")
    trip = p.evaluate("""() => {
      setMidiMode('poly');
      el.midiDrawCount.value = '4'; el.midiDrawCount.dispatchEvent(new Event('change'));
      el.midiDrawWhich.value = 'highest'; el.midiDrawWhich.dispatchEvent(new Event('change'));
      const snap = snapshot();
      setMidiMode('dyad'); midi.draw = { count: 2, which: 'outer' };
      restore(snap);
      // Copied: the second restore below writes into the same object.
      return { mode: midi.mode, draw: { ...midi.draw }, box: el.midiDrawCount.value,
               which: el.midiDrawWhich.value,
               old: (() => { restore({ midiMode: 'dyad' }); return { ...midi.draw }; })() };
    }""")
    print("    %s" % trip)
    check("poly and its draw rule survive a setup code",
          trip["mode"] == "poly" and trip["draw"] == {"count": 4, "which": "highest"}
          and trip["box"] == "4" and trip["which"] == "highest", str(trip))
    check("and a code from before poly existed comes back as the defaults",
          trip["old"] == {"count": 2, "which": "outer"}, str(trip["old"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("every held note sounds, and the picture says which of them it draws")
