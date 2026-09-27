"""The rest of J2: a dyad's ratio closes a rose, the bands can spin a solid
about each axis, and the drawings are sources.

What would go wrong, and what is checked for it:

- a rose that does not close. A dyad of A and E, a just fifth, sets k = 3/2,
  and r = cos(k theta) closes only after two turns - so the trace two turns
  on is the trace now, one turn on it is not, and at no turn does it jump.
  Before this the rose's angle went back to nought every turn, a fractional
  rose jumped at each, and the "precesses" in its comment was not true; that
  jump is what the continuity check is for. A just major third, 5/4, closes
  in four; a tempered fifth never quite does, and turns slowly instead;
- a dyad that sets the wrong thing: one note, a mono mode or a figure other
  than the rose leave the slider's k alone, and handing the generator back
  gives it back;
- spin that goes to the wrong axis: a routing on Spin Y turns the solid
  about Y alone, at the rate its depth says;
- a source reading the wrong thing: the swing is the drawing's gain, the
  pendulum its first pendulum's place, the turns the sine of each angle and
  facing cos x cos y - each against the arithmetic done here - and all of
  them nought while their drawing is not the one playing;
- a source that reads the page's copy while the worklet draws: heard, the
  readings come from the worklet;
- chips offered for a drawing that is not playing, or a Sources tab pushed
  over by them.
"""
import math, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


# A core off the page: a rose at 44.1 laps a second is a thousand samples a
# turn exactly, so "two turns on" is an index, not an interpolation.
ROSE = """([k, turns]) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('mode', 'figure'); core.set('figure', 'Rose'); core.set('detail', k);
  core.set('figureRate', 44.1); core.set('amp', 1);
  const n = 1000 * turns, L = new Float32Array(n), R = new Float32Array(n);
  core.block(L, R, n);
  let step = 0;
  for (let i = 1; i < n; i++) step = Math.max(step, Math.hypot(L[i] - L[i - 1], R[i] - R[i - 1]));
  const apart = (m) => { let d = 0; for (let i = 0; i + m < n; i++) d = Math.max(d, Math.hypot(L[i + m] - L[i], R[i + m] - R[i])); return d; };
  return { step, one: apart(1000), two: apart(2000), four: apart(4000) };
}"""

SOLID = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  for (const k in setup.tone) core.set(k, setup.tone[k]);
  if (setup.route) core.setRoutes([{ held: setup.route[1], amount: 1, slot: SPIN_SLOT + setup.route[0] }]);
  const n = setup.n, L = new Float32Array(n), R = new Float32Array(n);
  core.block(L, R, n);
  return core.drawing;
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

    print("\n--- a dyad closes the rose ---")
    fifth, third = p.evaluate(ROSE, [1.5, 6]), p.evaluate(ROSE, [1.25, 10])
    tempered = p.evaluate(ROSE, [2 ** (7 / 12), 6])
    print("    3/2: %s\n    5/4: %s\n    tempered fifth: %s" % (fifth, third, tempered))
    check("k = 3/2 closes in two turns and not one, and never jumps",
          fifth["two"] < 1e-5 and fifth["one"] > 0.5 and fifth["step"] < 0.02, str(fifth))
    check("k = 5/4 closes in four turns and not two, and never jumps",
          third["four"] < 1e-5 and third["two"] > 0.5 and third["step"] < 0.02, str(third))
    check("a tempered fifth never quite closes, and turns slowly instead - continuous, but a hair off after two",
          1e-3 < tempered["two"] < 0.2 and tempered["step"] < 0.02, str(tempered))

    played = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.genMode.value = 'figure'; el.genMode.dispatchEvent(new Event('change'));
      el.figure.value = 'Rose'; el.figure.dispatchEvent(new Event('change'));
      el.detail.value = '5'; el.detail.dispatchEvent(new Event('input'));
      setScreenKeys(true); setMidiMode('dyad'); await wait(50);
      const out = {};
      midiNoteOn(57, 100); midiNoteOn(64, 100); await wait(60);
      out.fifth = [genSettings().detail, el.detailValue.textContent];
      midiNoteOff(64); midiNoteOn(61, 100); await wait(60);
      out.third = genSettings().detail;
      midiNoteOff(61); await wait(60);
      out.one = genSettings().detail;
      // An octave and a fifth: 3:2 with the octave on top, 3.
      midiNoteOn(76, 100); await wait(60);
      out.wide = genSettings().detail;
      midiNoteOff(76); await wait(60);
      // Tempered: the tuning is the generator's, as the X-Y figure's is.
      el.tuneEqual.click(); await wait(30);
      midiNoteOn(64, 100); await wait(60);
      out.tempered = genSettings().detail;
      el.tuneJust.click(); await wait(30);
      midiNoteOff(64); midiNoteOff(57); await wait(30);
      // Another figure: the dyad sets nothing but the interval.
      el.figure.value = 'Star'; el.figure.dispatchEvent(new Event('change'));
      midiNoteOn(57, 100); midiNoteOn(64, 100); await wait(60);
      out.star = genSettings().detail;
      midiNoteOff(64); midiNoteOff(57);
      el.figure.value = 'Rose'; el.figure.dispatchEvent(new Event('change'));
      // Mono: the slider's - switched to with a fifth still held, so the
      // interval left over from the dyad is a fifth and not a unison, and a
      // rose that forgot to ask the mode would show it.
      midiNoteOn(57, 100); midiNoteOn(64, 100); await wait(60);
      setMidiMode('mono'); midiNoteOn(69, 100); await wait(60);
      out.mono = genSettings().detail;
      midiNoteOff(69); midiNoteOff(64); midiNoteOff(57);
      // Driven, then handed back.
      setMidiMode('dyad'); midiNoteOn(57, 100); midiNoteOn(64, 100); await wait(60);
      const driven = genSettings().detail;
      midiUndrive();
      out.back = [driven, genSettings().detail, el.detailValue.textContent];
      midiNoteOff(64); midiNoteOff(57); setScreenKeys(false);
      return out;
    }""")
    print("    %s" % played)
    check("A and E held on a rose set k to 3/2, and the reading says so",
          played["fifth"] == [1.5, "1.500"], str(played["fifth"]))
    check("A and C sharp, a just major third, set 5/4; one note gives the slider its 5 back",
          played["third"] == 1.25 and played["one"] == 5, "%s, %s" % (played["third"], played["one"]))
    check("an octave and a fifth, A3 and E5, set 3: the octave rides on top of the fifth",
          played["wide"] == 3, str(played["wide"]))
    check("tempered, the fifth is two to the seven twelfths",
          abs(played["tempered"] - 2 ** (7 / 12)) < 1e-12, str(played["tempered"]))
    check("a star, a mono keyboard, and a generator handed back all keep the slider's 5",
          played["star"] == 5 and played["mono"] == 5 and played["back"] == [1.5, 5, "5"], str(played))

    print("\n--- a solid's spin, axis by axis ---")
    base = {"mode": "wireframe", "spin": [0, 0, 0], "spinRate": 1, "figureRate": 40}
    n = 11025                          # a quarter of a second
    want = math.sin(2 * math.pi * 0.6 * n / 44100)
    routed = {axis: p.evaluate(SOLID, {"tone": base, "route": [axis, 1], "n": n})["turn"] for axis in range(3)}
    half = p.evaluate(SOLID, {"tone": base, "route": [1, 0.5], "n": n})["turn"]
    print("    a full routing on each axis, a quarter of a second: %s; half on Y: %s; want %.4f" % (routed, half, want))
    check("full depth on Spin X, Y or Z turns the solid 0.6 Hz about that axis alone",
          all(abs(routed[a][a] - want) < 1e-3 and all(abs(routed[a][o]) < 1e-9 for o in range(3) if o != a) for a in range(3)),
          str(routed))
    check("and half depth half as fast", abs(half[1] - math.sin(2 * math.pi * 0.3 * n / 44100)) < 1e-3, str(half))
    reach = p.evaluate("() => ['gen.spinX', 'gen.spinY', 'gen.spinZ'].map((id) => MOD_DESTS.get(id).reach(11, 1)).concat([MOD_DESTS.get('gen.spinZ').reach(0, -0.5)])")
    check("full depth is 0.6 Hz from the slider, stopped at its end", reach == [60, 60, 60, -30], str(reach))

    print("\n--- the drawings as sources ---")
    solid = p.evaluate(SOLID, {"tone": {"mode": "wireframe", "spin": [0.25, 0.1, 0.05], "spinRate": 1, "figureRate": 40}, "n": n})
    ax, ay, az = [2 * math.pi * f * n / 44100 for f in (0.25, 0.1, 0.05)]
    print("    %s" % solid)
    check("a solid's turns are the sines of its three angles, and its facing cos x cos y",
          max(abs(g - w) for g, w in zip(solid["turn"], [math.sin(ax), math.sin(ay), math.sin(az)])) < 1e-3
          and abs(solid["facing"] - math.cos(ax) * math.cos(ay)) < 1e-3 and solid["swing"] == 0 and solid["pendulum"] == 0,
          str(solid))
    # At a fifth, so the second pendulum is not where the first is and a
    # reading of the wrong one shows.
    # And at 0.5625 s: the first pendulum has done 1.125 swings and reads
    # 0.71, the second, a fifth up, 1.69 and reads -0.92. At half a second
    # both had done whole swings and read nought, whichever it was.
    harmo = p.evaluate(SOLID, {"tone": {"mode": "harmonograph", "swingRate": 2, "decay": 0.5, "interval": 7, "just": True}, "n": 24806})
    t = 24806 / 44100
    print("    %s" % harmo)
    check("the swing is the drawing's gain, e to the minus decay t, and the pendulum its first pendulum's place",
          abs(harmo["swing"] - math.exp(-0.5 * t)) < 1e-3 and abs(harmo["pendulum"] - math.sin(2 * math.pi * 2 * t)) < 1e-2
          and abs(harmo["pendulum"] - math.sin(2 * math.pi * 3 * t)) > 1
          and harmo["turn"] == [0, 0, 0] and harmo["facing"] == 0, str(harmo))
    # Pitched, the swing is the struck note's decay and the envelope the
    # harmonograph keeps for swinging on its own stands still at one: the
    # swing has to be the gain the drawing is drawn at, not that. And a core
    # switched from a harmonograph to a solid reads no swing, though the last
    # gain it drew at is still in it.
    struck = p.evaluate("""() => {
      const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
      const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
      core.set('mode', 'harmonograph'); core.set('pitched', true); core.set('freq', 220); core.set('ringMs', 600);
      const L = new Float32Array(4410), R = new Float32Array(4410);
      core.block(L, R, 4410); core.reswing();
      core.block(L, R, 4410); core.block(L, R, 4410);
      const swing = core.drawing.swing, level = core.swingLevel;
      core.set('mode', 'wireframe'); core.block(L, R, 441);
      return { swing, level, solid: core.drawing.swing };
    }""")
    check("struck and pitched, the swing is the note's decay, e to the minus t over 0.6 s, where the envelope stays at one",
          abs(struck["swing"] - math.exp(-0.2 / 0.6)) < 1e-3 and struck["level"] == 1, str(struck))
    check("and a harmonograph switched to a solid reads no swing", struck["solid"] == 0, str(struck["solid"]))
    wave = p.evaluate(SOLID, {"tone": {"mode": "wave"}, "n": 4410})
    check("and a waveform has none of them", wave == {"swing": 0, "pendulum": 0, "turn": [0, 0, 0], "facing": 0}, str(wave))

    heard = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.genMode.value = 'wireframe'; el.genMode.dispatchEvent(new Event('change'));
      state.genSound = true; await applyGeneratorSound(); await wait(700);
      const read = () => ['draw.turnX', 'draw.turnY', 'draw.facing'].map((id) => MOD_SOURCES.get(id).value());
      const a = read(); await wait(400); const c = read();
      // Heard, the page's own core stands still - `tick` fills from it only
      // while the generator is not heard - so readings that move are the
      // worklet's.
      const out = { audible: state.source.audible(), a, c };
      state.genSound = false; await applyGeneratorSound();
      return out;
    }""")
    print("    %s" % heard)
    check("heard, the readings come from the worklet's core and move", heard["audible"]
          and heard["a"] != heard["c"] and any(abs(v) > 0.01 for v in heard["a"] + heard["c"]), str(heard))

    pitched = p.evaluate("""() => {
      el.genMode.value = 'harmonograph'; el.genMode.dispatchEvent(new Event('change'));
      const loose = !el.freqRow.hidden;
      const was = [midi.play.harmonograph, midi.drive.harmonograph];
      midi.play.harmonograph = true; midi.drive.harmonograph = true; syncMidi();
      const played = !el.freqRow.hidden;
      [midi.play.harmonograph, midi.drive.harmonograph] = was; syncMidi();
      return [loose, played];
    }""")
    check("a harmonograph played at the keyboard's pitch has its Frequency back, since then it has one",
          pitched == [False, True], str(pitched))

    grid = p.evaluate("""async () => {
      const chips = () => [...el.srcGrid.querySelectorAll('[data-family="picture"] [data-select]')].map((c) => c.dataset.select).filter((id) => id.startsWith('draw.'));
      const out = {};
      for (const mode of ['wave', 'harmonograph', 'wireframe']) {
        el.genMode.value = mode; el.genMode.dispatchEvent(new Event('change'));
        out[mode] = chips();
      }
      return out;
    }""")
    print("    %s" % grid)
    check("the Sources tab offers a drawing's sources, under Picture, only while it plays",
          grid == {"wave": [], "harmonograph": ["draw.swing", "draw.pendulum"],
                   "wireframe": ["draw.turnX", "draw.turnY", "draw.turnZ", "draw.facing"]}, str(grid))

    fit = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const wav = (name, hz) => {
        const rate = 44100, n = rate / 4, bytes = 44 + n * 2;
        const buf = new ArrayBuffer(bytes), v = new DataView(buf);
        const str = (o, t) => { for (let i = 0; i < t.length; i++) v.setUint8(o + i, t.charCodeAt(i)); };
        str(0, 'RIFF'); v.setUint32(4, bytes - 8, true); str(8, 'WAVE'); str(12, 'fmt ');
        v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
        v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true);
        v.setUint16(34, 16, true); str(36, 'data'); v.setUint32(40, n * 2, true);
        for (let i = 0; i < n; i++) v.setInt16(44 + i * 2, Math.round(12000 * Math.sin(2 * Math.PI * hz * i / rate)), true);
        return new File([buf], name + '.wav', { type: 'audio/wav' });
      };
      el.rackSynth.checked = true; state.rackSynth = false; await setRackSynth(true);
      await addRackFiles([1, 2, 3, 4, 5].map((i) => wav('f' + i, 200 + 60 * i)));
      await wait(900);
      el.genMode.value = 'wireframe'; el.genMode.dispatchEvent(new Event('change'));
      await wait(300);
      setView('bench'); setBenchTab('sources');
      const over = el.benchBody.scrollHeight - el.benchBody.clientHeight;
      // And Play, in each of the drawn kinds, with the rows each shows.
      const play = {};
      for (const mode of ['wave', 'harmonograph', 'figure', 'wireframe']) {
        el.genMode.value = mode; el.genMode.dispatchEvent(new Event('change')); await wait(150);
        setBenchTab('play');
        play[mode] = [el.benchBody.scrollHeight - el.benchBody.clientHeight, !el.freqRow.hidden, !el.phaseRow.hidden];
      }
      el.genMode.value = 'wireframe'; el.genMode.dispatchEvent(new Event('change')); await wait(150);
      const lane = [MOD_SOURCES.get('draw.turnX').value(), MOD_SOURCES.get('draw.facing').value()];
      setView('scope');
      return { lanes: state.source.lanes.length, over, lane, play };
    }""")
    print("    %s" % fit)
    check("with a rack of six and a solid, the Sources tab does not scroll, and the lane's solid is read",
          fit["lanes"] == 6 and fit["over"] <= 0 and fit["lane"] != [0, 0], str(fit))

    # Frequency and Phase where they move something: a waveform both, a
    # harmonograph swinging on its own its phase, a figure and a solid
    # neither. Their room is what the spin axes' lanes took: before, a rack
    # of six put a solid's Play tab 30 px over, and the harmonograph's 6.
    check("Play shows Frequency and Phase only where they move something, and fits with a rack of six in every kind",
          {m: v[1:] for m, v in fit["play"].items()} == {"wave": [True, True], "harmonograph": [False, True],
                                                         "figure": [False, False], "wireframe": [False, False]}
          and all(v[0] <= 0 for v in fit["play"].values()), str(fit["play"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("a dyad closes the rose, the axes spin apart, and the drawings are sources")
