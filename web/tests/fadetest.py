"""Fading a routing in and out, and a preset's sliders gliding.

Asked for so that patching a source, or loading a preset, need not be a jump
in the sound and a snap in the picture. The failures to guard against:

- a fade that is only on one path. A routing reaches a picture destination
  through the matrix and the generator through `genRoutes`, in three places
  that each send the routes on; and a picture source's routes into the sound
  are folded into one bounded route whose parts are inside a closure. Each is
  read here, not the fade's own bookkeeping: `workletRoutes()` is what the
  worklet is sent, and `state.rotateMod` is what the picture draws with;
- a fade in that is not one at its first block. A routing made between two
  frames is compiled before the fade has seen it, and would be heard whole
  for a block unless an unseen pair counts as nought;
- a routing taken off that is dropped at once, or one that fades but is
  still saved - a ghost is heard, never stored;
- a pair in both the old and the new preset that dips to nought and back,
  because loading replaces every routing object;
- turning the fade on fading in what was already playing;
- a preset whose sliders jump, or a glide that fights the hand;
- the setting stored in the setup code, where every preset load would put it
  back to off before its routings could fade.

A constant source throughout - a macro at full - so the depth that reaches
each destination IS the routing's amount times its fade, and nothing else
moves it.
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

HELPERS = """
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const route = (destId) => {
    const slot = MOD_DESTS.get(destId).slot;
    const found = workletRoutes().find((r) => r.slot === slot);
    return found ? +found.amount.toFixed(4) : null;
  };
  // Where the picture's rotation is being pushed, in the matrix's own units.
  const rotation = () => +state.rotateMod.toFixed(4);
"""

# A keyboard, so the sources that step with your playing are there to fade.
STUB = """
  window.__midi = { port: null };
  navigator.requestMIDIAccess = function () {
    const port = { id: "stub", name: "Stub Keyboard", onmidimessage: null };
    window.__midi.port = port;
    return Promise.resolve({ inputs: new Map([["stub", port]]), outputs: new Map(), onstatechange: null });
  };
  window.__send = (bytes) => window.__midi.port.onmidimessage({ data: Uint8Array.from(bytes) });
"""

def run(p, body):
    return p.evaluate("async () => {" + HELPERS + body + "}")

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    p = ctx.new_page()
    p.add_init_script(STUB)
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    print("\n--- off, as it was: all or nothing ---")
    off = run(p, """
      restore({}); await wait(100); setMacro(0, 1);
      addRouting('macro.1', 'gen.fm'); const on = route('gen.fm');
      dropRouting('macro.1', 'gen.fm'); const gone = route('gen.fm');
      return { mode: fade.mode, on, gone };
    """)
    print("    %s" % off)
    # The null for everything below: with the fade off, the first block has it whole.
    check("off by default, and then a routing is whole the moment it is made and gone the moment it is taken off",
          off["mode"] == "off" and off["on"] == 0.35 and off["gone"] is None, str(off))

    print("\n--- in and out, on the sound ---")
    both = run(p, """
      setFade('both', 1); await wait(50);
      addRouting('macro.1', 'gen.fm');
      const rise = [route('gen.fm')];
      for (let i = 0; i < 6; i++) { await wait(250); rise.push(route('gen.fm')); }
      dropRouting('macro.1', 'gen.fm');
      const kept = state.modRoutings.length, saved = snapshot().mod;
      const fall = [route('gen.fm')];
      for (let i = 0; i < 6; i++) { await wait(250); fall.push(route('gen.fm')); }
      return { rise, fall, kept, saved };
    """)
    print("    %s" % both)
    rise, fall = both["rise"], both["fall"]
    check("fading in, the first block has none of it, the middle some, and a second later all of it",
          rise[0] == 0 and any(0.05 < v < 0.3 for v in rise[1:4]) and rise[-1] == 0.35
          and all(a <= b for a, b in zip(rise, rise[1:])), str(rise))
    check("fading out, it is still heard after it is taken off, falls, and is gone a second later",
          fall[0] == 0.35 and any(0.05 < (v or 0) < 0.3 for v in fall[1:4]) and fall[-1] is None, str(fall))
    check("and while it fades out it is not in the setup, nor in the code a save would write",
          both["kept"] == 0 and both["saved"] == "", str(both))

    print("\n--- only in, only out ---")
    one = run(p, """
      setFade('in', 1); await wait(50);
      addRouting('macro.1', 'gen.fm'); const inFirst = route('gen.fm');
      await wait(1200); dropRouting('macro.1', 'gen.fm'); const inGone = route('gen.fm');
      setFade('out', 1); await wait(50);
      /* A frame between making it and taking it off: a routing made and
         taken off inside one frame was never seen by the fade, has no gain
         to fall from, and goes at once - which no hand can do. */
      addRouting('macro.1', 'gen.fm'); const outFirst = route('gen.fm');
      await wait(100); dropRouting('macro.1', 'gen.fm'); const outKept = route('gen.fm');
      await wait(1200); const outGone = route('gen.fm');
      return { inFirst, inGone, outFirst, outKept, outGone };
    """)
    print("    %s" % one)
    check("In fades in and cuts out; Out comes in whole and fades out",
          one["inFirst"] == 0 and one["inGone"] is None and one["outFirst"] == 0.35
          and one["outKept"] == 0.35 and one["outGone"] is None, str(one))

    print("\n--- the picture's path, and the picture's own sources ---")
    pic = run(p, """
      setFade('both', 1); await wait(50);
      addRouting('macro.1', 'view.rotate');
      await wait(40); const early = rotation();
      await wait(1300); const full = rotation();
      dropRouting('macro.1', 'view.rotate'); await wait(400); const leaving = rotation();
      await wait(1000); const after = rotation();
      /* A source of the picture's own, held at one, onto the sound: its route
         is folded into the bounded loop total, whose parts are faded inside
         a closure rather than as a route of their own. */
      registerSource({ id: 'test.loop', label: 'Test', fromPicture: true, reach: 0.5, bipolar: false,
                       family: 'picture', value: () => 1 });
      state.modRoutings.push({ sourceId: 'test.loop', destId: 'gen.fm', amount: 0.5 }); touchRoutings();
      const held = () => { const slot = MOD_DESTS.get('gen.fm').slot;
                           const r = workletRoutes().find((x) => x.slot === slot); return r ? +r.held.toFixed(4) : null; };
      const loop = [held()];
      await wait(500); loop.push(held()); await wait(800); loop.push(held());
      state.modRoutings = []; touchRoutings(); MOD_SOURCES.delete('test.loop');
      await wait(1300);
      /* The live effects run only while something wants them, and a routing
         on the twist is one of those things: one fading out still is, or a
         microphone's picture would stop swirling at once instead of easing. */
      restore({}); await wait(100);
      addRouting('macro.1', 'gen.twist'); await wait(1200);
      dropRouting('macro.1', 'gen.twist');
      const fxLeaving = liveFxWanted();
      await wait(1300); const fxAfter = liveFxWanted();
      return { early, full, leaving, after, loop, fxLeaving, fxAfter };
    """)
    print("    %s" % pic)
    check("a picture destination fades too: barely turned at first, whole after the fade, part-way as it leaves, then nothing",
          abs(pic["early"]) < 0.05 and pic["full"] == 0.35 and 0.05 < pic["leaving"] < 0.34 and pic["after"] == 0,
          str(pic))
    check("and a picture source into the sound, folded into the loop's one route, fades in with it",
          pic["loop"][0] == 0 and 0.05 < pic["loop"][1] < 0.45 and pic["loop"][2] == 0.5, str(pic["loop"]))
    check("the live effects stay on while a routing on the twist fades out, and go off once it has",
          pic["fxLeaving"] is True and pic["fxAfter"] is False, str(pic))

    print("\n--- what does not dip, and what is not faded in ---")
    keep = run(p, """
      setFade('off'); restore({ mod: 'macro.1>gen.fm@0.300' }); await wait(100); setMacro(0, 1); setMacro(1, 1);
      setFade('in', 1); const already = route('gen.fm');
      // A load that keeps one pair and brings another: restore, as a preset does.
      restore({ mod: 'macro.1>gen.fm@0.300;macro.2>gen.vcf@0.300' }); setMacro(0, 1); setMacro(1, 1);
      const kept = route('gen.fm'), arrived = route('gen.vcf');
      await wait(1200);
      // Taken off, half faded, and put back: from where it had got to.
      setFade('both', 1); dropRouting('macro.1', 'gen.fm'); await wait(500);
      const half = route('gen.fm'); addRouting('macro.1', 'gen.fm');
      state.modRoutings.find((r) => r.sourceId === 'macro.1').amount = 0.3; touchRoutings();
      const back = route('gen.fm');
      return { already, kept, arrived, half, back };
    """)
    print("    %s" % keep)
    check("turning the fade on leaves what is playing whole",
          keep["already"] == 0.3, str(keep))
    check("a load keeps a pair both setups have whole, and fades in the one that is new",
          keep["kept"] == 0.3 and keep["arrived"] == 0, str(keep))
    check("put back half-way through fading out, it carries on from where it was rather than starting again",
          keep["half"] is not None and 0.05 < keep["half"] < 0.25 and abs(keep["back"] - keep["half"]) < 0.06, str(keep))

    print("\n--- a note struck, with velocity on the drive ---")
    # What was asked for after the first version: the routing already
    # patched, and each note taking the drive from its rest up to the
    # velocity's worth, rather than jumping there. The first version faded
    # only patching, and velocity still jumped at every strike; the checks
    # above all passed on it.
    note = run(p, """
      const pushed = (destId) => {
        const slot = MOD_DESTS.get(destId).slot;
        const r = workletRoutes().find((x) => x.slot === slot);
        return r ? +(r.held * r.amount).toFixed(4) : 0;
      };
      const walk = async (n, ms) => { const out = [pushed('gen.drive')];
        for (let i = 0; i < n; i++) { await wait(ms); out.push(pushed('gen.drive')); } return out; };
      midiConnect(); await wait(200);
      setFade('off'); restore({ midiMode: 'poly', mod: 'midi.key>gen.drive@0.500;midi.key>view.rotate@0.500' }); await wait(200);
      __send([0x90, 60, 127]); const offOn = pushed('gen.drive');
      __send([0x80, 60, 0]); const offOff = pushed('gen.drive');
      await wait(100);
      setFade('in', 1); await wait(50);
      __send([0x90, 60, 127]); await wait(300);
      // The same note seen on the picture's path, and on the drive's own slider.
      const picture = rotation(), tick = +sweepOf(null, routingsFor('gen.drive')).live.toFixed(4);
      await wait(1000); __send([0x80, 60, 0]); await wait(100);
      __send([0x90, 60, 127]); const inRise = await walk(5, 250);
      __send([0x80, 60, 0]); const inRelease = pushed('gen.drive');
      await wait(100);
      setFade('both', 1); await wait(50);
      __send([0x90, 60, 127]); await wait(1200);
      __send([0x80, 60, 0]); const bothFall = await walk(5, 250);
      // Straight after a release that is fading, a new note climbs from where it was.
      __send([0x90, 60, 127]); await wait(1200); __send([0x80, 60, 0]); await wait(400);
      const before = pushed('gen.drive'); __send([0x90, 62, 127]); const after = pushed('gen.drive');
      await wait(1200); __send([0x80, 62, 0]); await wait(1200);
      // A knob is a hand and is not eased: a macro onto the same control answers at once.
      setMacro(0, 0); state.modRoutings.push({ sourceId: 'macro.1', destId: 'gen.fm', amount: 0.5 }); touchRoutings();
      await wait(1200); setMacro(0, 1);
      const slot = MOD_DESTS.get('gen.fm').slot, r = workletRoutes().find((x) => x.slot === slot);
      const knob = +(r.held * r.amount).toFixed(4);
      setFade('off'); restore({}); await wait(100);
      return { offOn, offOff, inRise, inRelease, bothFall, before, after, knob, picture, tick };
    """)
    print("    %s" % note)
    check("with the fade off, a note puts velocity's whole worth on the drive at once, and a release takes it off (the null)",
          note["offOn"] == 0.5 and note["offOff"] == 0, str(note))
    check("fading in, a struck note starts the drive at its rest and brings it up to the velocity's worth over the fade",
          note["inRise"][0] < 0.02 and any(0.1 < v < 0.4 for v in note["inRise"][1:4]) and note["inRise"][-1] == 0.5
          and all(a <= b for a, b in zip(note["inRise"], note["inRise"][1:])), str(note["inRise"]))
    check("the picture's path eases with it, and so does the tick drawn on the drive's slider",
          0.02 < note["picture"] < 0.4 and 0.02 < note["tick"] < 0.4, str(note))
    check("In alone lets a release go at once", note["inRelease"] == 0, str(note))
    check("In and out walks it back down after the release",
          note["bothFall"][0] > 0.45 and any(0.1 < v < 0.4 for v in note["bothFall"][1:4]) and note["bothFall"][-1] == 0,
          str(note["bothFall"]))
    check("a note struck while the last is still fading climbs from where the drive was, rather than dropping to rest",
          0.05 < note["before"] < 0.45 and abs(note["after"] - note["before"]) < 0.05, str(note))
    check("and a knob is not eased: a macro on a control answers the hand at once", note["knob"] == 0.5, str(note))

    print("\n--- a preset's sliders glide ---")
    first = p.evaluate("() => { setFade('off'); restore({ freq: 880 }); return el.freq.value; }")
    p.wait_for_timeout(100)
    snap_off = p.evaluate("""() => { applyPreset("b:Pianist's piano"); return Number(el.freq.value); }""")
    glide = run(p, """
      restore({ freq: 880 }); await wait(100);
      setFade('both', 1);
      applyPreset("b:Pianist's piano");
      const path = [Number(el.freq.value)], names = [];
      for (let i = 0; i < 6; i++) { await wait(250); path.push(Number(el.freq.value)); names.push(el.presetCurrent.textContent); }
      return { path, names: [...new Set(names)], shown: el.presetCurrent.textContent, mode: fade.mode, inCode: 'fade' in snapshot() || 'fadeMode' in snapshot() };
    """)
    print("    off: 880 -> %s at once; glided: %s" % (snap_off, glide))
    path = glide["path"]
    check("with the fade off a preset's frequency is there at once (the null)", first == "880" and snap_off == 220,
          "%s %s" % (first, snap_off))
    check("with it on, the frequency starts where it was, passes between, and lands on the preset's",
          path[0] == 880 and any(220 < v < 880 for v in path[1:4]) and path[-1] == 220
          and all(a >= b for a, b in zip(path, path[1:])), str(path))
    check("the strip names the preset throughout the glide and once it has landed, and loading it did not put the fade back to off",
          glide["shown"] == "Pianist's piano" and glide["names"] == ["Pianist's piano"] and glide["mode"] == "both",
          str(glide))
    check("and the fade is not in the setup code", glide["inCode"] is False)

    p.evaluate("() => { restore({ freq: 880 }); }"); p.wait_for_timeout(100)
    p.evaluate("""() => { applyPreset("b:Pianist's piano"); showControl('freq'); }""")
    p.wait_for_timeout(200)
    p.locator("#freq").focus(); p.keyboard.press("ArrowRight")
    held = p.evaluate("() => Number(el.freq.value)")
    p.wait_for_timeout(1200)
    after = p.evaluate("() => Number(el.freq.value)")
    check("a slider the hand moves during the glide is left to the hand",
          220 < held < 880 and after == held, "moved to %s, a second later %s" % (held, after))

    print("\n--- every preset in the library lands as itself ---")
    # Chained, so each glides from the one before - a different start each time.
    # Found the echo's time: while locked to the tempo its slider is disabled
    # and shows the locked time, and gliding it wrote that back as the free one.
    landed = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setFade('both', 0.1); const bad = []; let glided = 0;
      for (const [name] of PRESETS.flatMap(([, e]) => e)) {
        applyPreset('b:' + name); if (glide.ids) glided++;
        /* Until the glide says it has landed, and a frame more: a fixed wait
           was a race with the frame rate, hidden while the curve was an S -
           flat at its end - and lost once a straight line was the default. */
        for (let i = 0; i < 40 && glide.ids; i++) await wait(25);
        await wait(50);
        const now = snapshot(), d = {};
        for (const k of Object.keys(now)) if (now[k] !== loadedSetup.snap[k]) d[k] = [loadedSetup.snap[k], now[k]];
        if (Object.keys(d).length) bad.push([name, d]);
      }
      setFade('off');
      return { bad, glided, total: PRESETS.flatMap(([, e]) => e).length };
    }""")
    check("every preset, glided into from the one before, ends as the preset and not something near it",
          landed["bad"] == [] and landed["glided"] > landed["total"] * 0.8,
          "%d of %d glided; %s" % (landed["glided"], landed["total"], landed["bad"][:3]))

    print("\n--- the envelope: two times and two shapes ---")
    env = run(p, """
      restore({}); await wait(100); setMacro(0, 1);
      setFade('both'); setFadeEnvelope({ attack: 0.5, release: 2, attackMid: 0.5, releaseMid: 0.5, sustain: 1, delay: 0 });
      addRouting('macro.1', 'gen.fm'); await wait(650); const inDone = route('gen.fm');
      dropRouting('macro.1', 'gen.fm'); await wait(1000); const outHalf = route('gen.fm');
      await wait(1300); const outDone = route('gen.fm');
      // The same second of fading in, along a curve quick to start and one slow to start.
      setFadeEnvelope({ attack: 1, attackMid: 0.85 }); addRouting('macro.1', 'gen.fm');
      await wait(250); const quick = route('gen.fm'); clearSource('macro.1'); await wait(2200);
      setFadeEnvelope({ attackMid: 0.15 }); addRouting('macro.1', 'gen.fm');
      await wait(250); const slow = route('gen.fm'); clearSource('macro.1'); await wait(2200);
      // A preset glides along the attack, so over its time and not the release's.
      restore({ freq: 880 }); await wait(100);
      setFadeEnvelope({ attack: 0.5, release: 5, attackMid: 0.5 });
      applyPreset("b:Pianist's piano"); await wait(700); const glided = Number(el.freq.value);
      return { inDone, outHalf, outDone, quick, slow, glided };
    """)
    print("    %s" % env)
    check("a fade in and a fade out each take their own time: in by half a second, out still going at one of two",
          env["inDone"] == 0.35 and env["outHalf"] is not None and 0.1 < env["outHalf"] < 0.25 and env["outDone"] is None,
          str(env))
    check("the shape is heard: a quarter of the way into a fade, quick to start is most of the way, slow to start barely begun",
          env["quick"] > 0.15 and env["slow"] < 0.05, str(env))
    check("a preset glides over the attack time", env["glided"] == 220, str(env))

    print("\n--- the envelope's stretches, on a note ---")
    # Velocity at full on the drive at half depth: the drive's push is half
    # the envelope's level, so 0.5 is full and 0.2 a sustain of 0.4.
    stretch = run(p, """
      const pushed = () => { const slot = MOD_DESTS.get('gen.drive').slot;
        const r = workletRoutes().find((x) => x.slot === slot); return r ? +(r.held * r.amount).toFixed(3) : 0; };
      const strike = (n) => __send([0x90, n, 127]), lift = (n) => __send([0x80, n, 0]);
      const plain = { delay: 0, attack: 0.2, decay: 0.4, sustain: 1, release: 0.5, restart: false, loop: false,
                      attackMid: 0.5, decayMid: 0.5, releaseMid: 0.5 };
      setFade('off'); restore({ midiMode: 'poly', mod: 'midi.key>gen.drive@0.500' }); await wait(200);
      setFade('both'); setFadeEnvelope(Object.assign({}, plain, { delay: 0.4, attack: 0.3 })); await wait(100);
      fade.editing = 0;
      const dotNow = () => ({ x: +envParts.dot.getAttribute('cx'), y: +envParts.dot.getAttribute('cy'),
                              stage: fade.last[0] && fade.last[0].gate ? gatePhase(fade.last[0].gate, performance.now()).stage : null });
      strike(60); await wait(250); const waiting = pushed(), inWait = dotNow(), waitG = envGeometry(fade.envs[0]);
      await wait(350); const rising = pushed();
      lift(60); await wait(900);
      setFadeEnvelope(Object.assign({}, plain, { sustain: 0.4 })); await wait(50);
      strike(60); await wait(200); const burst = pushed(); await wait(700); const settled = pushed();
      const onHold = dotNow(), holdG = envGeometry(fade.envs[0]);
      lift(60); await wait(250); const releasing = pushed(); await wait(600); const rested = pushed();
      // Restart: a second key struck at the same strength while the first is held.
      const second = async (restart) => {
        setFadeEnvelope({ restart }); strike(60); await wait(900); const before = pushed();
        strike(64); await wait(220); const after = pushed(); lift(64); lift(60); await wait(900);
        return [before, after];
      };
      const restarted = await second(true), carried = await second(false);
      // Loop: sampled for two seconds while held, counting the times it comes back up to full.
      const peaks = async (loop) => {
        setFadeEnvelope({ loop, attack: 0.15, decay: 0.25, sustain: 0.2 }); strike(60);
        let n = 0, high = false;
        for (let i = 0; i < 40; i++) { await wait(50); const v = pushed(); if (!high && v > 0.4) { n++; high = true; } if (v < 0.25) high = false; }
        lift(60); await wait(900); return n;
      };
      const looped = await peaks(true), once = await peaks(false);
      setFadeEnvelope(plain); setFade('off');
      return { waiting, rising, burst, settled, releasing, rested, restarted, carried, looped, once, inWait, waitG, onHold, holdG };
    """)
    print("    %s" % stretch)
    check("the delay: a quarter of a second into a 0.4 s wait nothing has moved, and after it the attack is under way",
          stretch["waiting"] < 0.01 and stretch["rising"] > 0.1, str(stretch))
    # The dot is in the wait while the envelope waits - the sound alone
    # cannot tell a wait from an attack at a time before it began.
    w, wg, h, hg = stretch["inWait"], stretch["waitG"], stretch["onHold"], stretch["holdG"]
    check("and the dot shows it: in the wait during the delay, on the held stretch at the sustain's height once settled",
          w["stage"] == "delay" and 6 < w["x"] < wg["waitEnd"] and w["y"] == 54
          and h["stage"] == "sustain" and hg["corner"] < h["x"] < hg["held"] and abs(h["y"] - (54 - 46 * 0.4)) < 0.01,
          "%s / %s" % (w, h))
    check("the decay: the strike bursts towards full, then settles to the sustain's 40 per cent",
          stretch["burst"] > 0.35 and abs(stretch["settled"] - 0.2) < 0.01, str(stretch))
    check("the release falls from the sustain, and rests at nought",
          0.02 < stretch["releasing"] < 0.2 and stretch["rested"] == 0, str(stretch))
    check("Restart: a second note struck under the first runs the envelope again; without it the drive carries on",
          abs(stretch["restarted"][0] - 0.2) < 0.01 and stretch["restarted"][1] > 0.3
          and abs(stretch["carried"][1] - 0.2) < 0.01, str(stretch))
    check("Loop: a held note comes back up to full again and again; without it, once",
          stretch["looped"] >= 3 and stretch["once"] == 1, str(stretch))

    print("\n--- two layers, two envelopes ---")
    layers = run(p, """
      const both = () => { const slot = MOD_DESTS.get('gen.drive').slot;
        const r = workletRoutes().find((x) => x.slot === slot);
        return r ? [+(r.held * r.amount).toFixed(3), +(r.heldB * r.amountB).toFixed(3)] : [0, 0]; };
      setFade('off'); restore({ midiMode: 'poly', layers: 'layer', mod: 'midi.key>gen.drive@0.500' }); await wait(200);
      const layered = fadeLayered();
      setFade('both');
      setFadeEnvelope({ delay: 0, attack: 0.2, sustain: 1, release: 0.3, restart: false, loop: false }, 0);
      setFadeEnvelope({ delay: 0, attack: 1.5, sustain: 1, release: 0.3, restart: false, loop: false }, 1);
      await wait(100);
      __send([0x90, 60, 127]); await wait(400); const early = both(); await wait(1400); const late = both();
      __send([0x80, 60, 0]); await wait(800);
      // A routing patched while layered fades in on each layer's own attack too.
      setMacro(0, 1); addRouting('macro.1', 'gen.fm'); await wait(400);
      const fm = (() => { const slot = MOD_DESTS.get('gen.fm').slot; const r = workletRoutes().find((x) => x.slot === slot);
                          return [+(r.held * r.amount).toFixed(3), +(r.heldB * r.amountB).toFixed(3)]; })();
      clearSource('macro.1'); await wait(500);
      // Unlayered, layer B's depth is layer A's, whatever its envelope says.
      restore({ midiMode: 'poly', mod: 'midi.key>gen.drive@0.500' }); await wait(200);
      __send([0x90, 60, 127]); await wait(400); const single = both(); __send([0x80, 60, 0]); await wait(800);
      /* In the core itself: a route up an octave on layer A and not on B.
         The null is the same route without a layer-B depth, which is how
         every route was sent before there were two - it moves both. */
      const rate = 44100;
      const quiet = [0, 1].map(() => ({ shape: 'sine', rate: 1, depth: 0, phase: 0, held: 0, value: 0 }));
      const bin = (x, hz) => { let re = 0, im = 0; for (let i = 0; i < x.length; i++) { const w = 2 * Math.PI * hz * i / rate; re += x[i] * Math.cos(w); im += x[i] * Math.sin(w); } return 2 * Math.hypot(re, im) / x.length; };
      const layerPitch = (route) => {
        const core = makeGeneratorCore(rate, GEN_DESTS.length, quiet);
        core.set('shape', 'sine'); core.set('shape', 'sine', 1); core.set('attackMs', 1); core.set('attackMs', 1, 1);
        core.set('voices', [{ note: 57, freq: 220, velocity: 1, role: 'xy' }]);
        core.set('voices', [{ note: 57, freq: 220, velocity: 1, role: 'xy' }], 1);
        core.setRoutes([route]);
        const n = 8192, al = new Float32Array(n), ar = new Float32Array(n), hl = new Float32Array(n), hr = new Float32Array(n);
        const bl = new Float32Array(n), br = new Float32Array(n);
        core.block(al, ar, n, hl, hr, bl, br);
        const tail = (x) => x.subarray(n - 4096);
        return { a: [bin(tail(al), 220), bin(tail(al), 440)].map((v) => +v.toFixed(3)),
                 b: [bin(tail(bl), 220), bin(tail(bl), 440)].map((v) => +v.toFixed(3)) };
      };
      const own = layerPitch({ index: undefined, held: 1, heldB: 0, slot: 0, amount: 1, amountB: 0, unipolar: false });
      const shared = layerPitch({ index: undefined, held: 1, slot: 0, amount: 1, unipolar: false });
      /* Two more of the voice's pushes, each its own line in the core: the
         drive (a sine driven grows a third harmonic) and the level (the
         tremolo destination ducks to silence at a held value of minus one). */
      const layerOut = (route) => {
        const core = makeGeneratorCore(rate, GEN_DESTS.length, quiet);
        core.set('shape', 'sine'); core.set('shape', 'sine', 1); core.set('attackMs', 1); core.set('attackMs', 1, 1);
        core.set('voices', [{ note: 57, freq: 220, velocity: 1, role: 'xy' }]);
        core.set('voices', [{ note: 57, freq: 220, velocity: 1, role: 'xy' }], 1);
        core.setRoutes([route]);
        const n = 8192, al = new Float32Array(n), ar = new Float32Array(n), hl = new Float32Array(n), hr = new Float32Array(n);
        const bl = new Float32Array(n), br = new Float32Array(n);
        core.block(al, ar, n, hl, hr, bl, br);
        const tail = (x) => x.subarray(n - 4096);
        return { a: [bin(tail(al), 220), bin(tail(al), 660)].map((v) => +v.toFixed(4)),
                 b: [bin(tail(bl), 220), bin(tail(bl), 660)].map((v) => +v.toFixed(4)) };
      };
      const drive = layerOut({ index: undefined, held: 1, heldB: 0, slot: MOD_DESTS.get('gen.drive').slot, amount: 1, amountB: 0, unipolar: false });
      const level = layerOut({ index: undefined, held: -1, heldB: -1, slot: MOD_DESTS.get('gen.amp').slot, amount: 1, amountB: 0, unipolar: true });
      setFade('off'); restore({});
      return { layered, early, late, single, own, shared, drive, level, fm };
    """)
    print("    %s" % layers)
    check("layered, each layer's drive follows its own envelope: A arrived at 0.4 s, B still rising, both there later",
          layers["layered"] and layers["early"][0] == 0.5 and 0.05 < layers["early"][1] < 0.3
          and layers["late"] == [0.5, 0.5], str(layers))
    check("and a routing patched while layered fades in on each layer's own attack: A's there, B's under way",
          layers["fm"][0] == 0.35 and 0.02 < layers["fm"][1] < 0.2, str(layers["fm"]))
    check("unlayered, layer B's depth is layer A's", layers["single"][0] == layers["single"][1] == 0.5, str(layers))
    own, shared = layers["own"], layers["shared"]
    check("and in the core, layer B sounds its own depth: an octave up on A and not on B; sent as one, both move (the null)",
          own["a"][1] > 10 * own["a"][0] and own["b"][0] > 10 * own["b"][1]
          and shared["b"][1] > 10 * shared["b"][0], str(layers))
    dr, lv = layers["drive"], layers["level"]
    check("and the drive and the level too: A driven into a third harmonic and B clean; A ducked to silence and B not",
          # B's third is the transform's leakage on a pure sine, about a thousandth; A's is a sixth.
          dr["a"][1] > 0.05 and dr["b"][1] < 0.01 and lv["a"][0] < 0.01 and lv["b"][0] > 0.2, str(layers))

    split = run(p, """
      /* Split at middle C, each layer set to restart: a new bass note under
         a held chord restarts the bass's envelope and leaves the lead's. */
      const both = () => { const slot = MOD_DESTS.get('gen.drive').slot;
        const r = workletRoutes().find((x) => x.slot === slot);
        return r ? [+(r.held * r.amount).toFixed(3), +(r.heldB * r.amountB).toFixed(3)] : [0, 0]; };
      setFade('off'); restore({ midiMode: 'poly', layers: 'split', splitAt: 60, mod: 'midi.key>gen.drive@0.500' }); await wait(200);
      setFade('both');
      for (const l of [0, 1]) setFadeEnvelope({ delay: 0, attack: 0.15, decay: 0.3, sustain: 0.4, release: 0.3, restart: true, loop: false }, l);
      await wait(100);
      __send([0x90, 48, 127]); __send([0x90, 72, 127]); await wait(900); const settled = both();
      __send([0x90, 50, 127]); await wait(150); const bass = both(); await wait(700);
      __send([0x90, 74, 127]); await wait(150); const lead = both();
      for (const n of [48, 50, 72, 74]) __send([0x80, n, 0]);
      for (const l of [0, 1]) setFadeEnvelope({ sustain: 1, restart: false, decay: 0.5 }, l);
      await wait(600); setFade('off'); restore({});
      return { settled, bass, lead };
    """)
    print("    %s" % split)
    check("split, a bass note restarts only the bass layer's envelope, and a lead note only the lead's",
          split["settled"] == [0.2, 0.2] and split["bass"][0] > 0.3 and split["bass"][1] == 0.2
          and split["lead"][1] > 0.3 and abs(split["lead"][0] - 0.2) < 0.01, str(split))

    print("\n--- the envelope drawn, and taken hold of ---")
    drawn = p.evaluate("""() => {
      fade.editing = 0;
      setFadeEnvelope({ delay: 1.25, attack: 2.5, decay: 0.4, sustain: 0.5, release: 0.9,
                        attackMid: 0.8, decayMid: 0.5, releaseMid: 0.3 }); drawFadeEnvelope();
      const at = (name) => ['cx', 'cy'].map((a) => +(+envParts[name].getAttribute(a)).toFixed(2));
      const points = envParts.attack.getAttribute('d').slice(1).split('L').map((p) => p.split(',').map(Number));
      return { wait: at('wait'), peak: at('peak'), corner: at('corner'), end: at('end'), attackMid: at('attackMid'),
               decayMid: at('decayMid'), releaseMid: at('releaseMid'),
               curveMid: +points[ENV.samples / 2][1].toFixed(2), text: el.fadeEnvValue.textContent };
    }""")
    print("    %s" % drawn)
    # Worked by hand: the wait ends at 6 + 24 x sqrt(1.25 / 5) = 18; the peak
    # 60 x sqrt(2.5 / 10) = 30 on, at 48; the corner 60 x sqrt(0.4 / 10) = 12
    # on, at 60, and at half height, 54 - 46 x 0.5 = 31; the hold is 20, so the
    # release starts at 80 and ends 60 x sqrt(0.9 / 10) = 18 on, at 98. The
    # attack's shape 0.8 sits at 54 - 46 x 0.8 = 17.2; the decay's midpoint at
    # 1 - 0.5 x 0.5 = 0.75 of full, 19.5; the release's at 0.5 x 0.7 = 0.35, 37.9.
    check("the handles sit where the numbers put them, and the attack's curve passes through its shape handle",
          drawn["wait"] == [18, 54] and drawn["peak"] == [48, 8] and drawn["corner"] == [60, 31] and drawn["end"] == [98, 54]
          and drawn["attackMid"] == [33, 17.2] and drawn["decayMid"] == [54, 19.5] and drawn["releaseMid"] == [89, 37.9]
          and drawn["curveMid"] == 17.2 and drawn["text"] == "In 2.5 s \u00b7 Out 0.90 s", str(drawn))

    p.evaluate("""() => { setFadeEnvelope({ delay: 0, attack: 1, decay: 1, sustain: 0.6, release: 1,
                                            attackMid: 0.5, decayMid: 0.5, releaseMid: 0.5 }); drawFadeEnvelope(); showControl('fadeMode'); }""")
    p.wait_for_timeout(200)
    def drag(name, dx, dy):
        box = p.locator('[data-handle="%s"]' % name).bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        p.mouse.move(x, y); p.mouse.down(); p.mouse.move(x + dx / 2, y + dy / 2); p.mouse.move(x + dx, y + dy); p.mouse.up()
    E = "() => { const e = fade.envs[0]; return Object.fromEntries(Object.entries(e).map(([k, v]) => [k, typeof v === 'number' ? +v.toFixed(3) : v])); }"
    unmoved = p.evaluate(E)
    check("before the drag the envelope is where it was set",
          [unmoved[k] for k in ("delay", "attack", "decay", "sustain", "attackMid", "releaseMid")] == [0, 1, 1, 0.6, 0.5, 0.5],
          str(unmoved))
    drag("wait", 20, 0); drag("peak", 25, 0); drag("corner", 15, -15); drag("attackMid", 0, -12); drag("releaseMid", 0, 8)
    p.locator('[data-handle="end"]').focus(); p.keyboard.press("ArrowRight")
    moved = p.evaluate(E)
    print("    after dragging and a key: %s" % moved)
    check("dragging moves each stretch: the wait longer, the attack longer, the corner later and higher, the shapes quicker",
          moved["delay"] > 0.2 and moved["attack"] > 1.5 and moved["decay"] > 1.2 and moved["sustain"] > 0.7
          and moved["attackMid"] > 0.6 and moved["releaseMid"] > 0.6, str(moved))
    check("and the arrow keys move a handle: the end a tenth longer", abs(moved["release"] - 1.1) < 1e-6, str(moved))

    ui = run(p, """
      setFade('off'); restore({ midiMode: 'poly', layers: 'layer' }); await wait(200);
      setFade('both'); await wait(100);
      const shown = !el.fadeLayers.hidden;
      el.fadeEditB.click(); const editing = fade.editing;
      el.fadeRestart.click(); el.fadeLoop.click();
      const b = { restart: fade.envs[1].restart, loop: fade.envs[1].loop }, a = { restart: fade.envs[0].restart, loop: fade.envs[0].loop };
      const ghost = envParts.ghost.getAttribute('d').length > 0, label = el.fadeEnvValue.textContent.slice(0, 2);
      el.fadeRestart.click(); el.fadeLoop.click(); el.fadeEditA.click();
      restore({ midiMode: 'poly' }); await wait(200);
      const hiddenAfter = el.fadeLayers.hidden, back = fade.editing, noGhost = envParts.ghost.getAttribute('d') === '';
      setFade('off');
      return { shown, editing, a, b, ghost, label, hiddenAfter, back, noGhost };
    """)
    print("    %s" % ui)
    check("layered, A and B appear, B draws and takes Restart and Loop for itself, with A faint behind; unlayered they go",
          ui["shown"] and ui["editing"] == 1 and ui["b"] == {"restart": True, "loop": True}
          and ui["a"] == {"restart": False, "loop": False} and ui["ghost"] and ui["label"] == "B:"
          and ui["hiddenAfter"] and ui["back"] == 0 and ui["noGhost"], str(ui))

    dot = run(p, """
      setFade('off'); restore({}); await wait(100); setMacro(0, 1);
      setFade('both'); setFadeEnvelope({ delay: 0, attack: 1, release: 1, sustain: 1, attackMid: 0.5, releaseMid: 0.5 });
      const g = () => envGeometry(fade.envs[0]), where = () => ({ x: +envParts.dot.getAttribute('cx'), y: +envParts.dot.getAttribute('cy'),
                                                    shown: envParts.dot.getAttribute('visibility') === 'visible' });
      const before = where();
      addRouting('macro.1', 'gen.fm'); await wait(400); const rising = where();
      await wait(900); const holding = where();
      dropRouting('macro.1', 'gen.fm'); await wait(400); const falling = where();
      await wait(900); const gone = where();
      return { before, rising, holding, falling, gone, g: g() };
    """)
    print("    %s" % dot)
    gx = dot["g"]
    check("the dot rides the attack while a fade in is under way, waits at the top, rides the release, and goes",
          not dot["before"]["shown"]
          and dot["rising"]["shown"] and gx["waitEnd"] < dot["rising"]["x"] < gx["peak"] and 8 < dot["rising"]["y"] < 54
          and dot["holding"]["shown"] and dot["holding"]["y"] == 8
          and dot["falling"]["shown"] and gx["held"] < dot["falling"]["x"] < gx["end"] and 8 < dot["falling"]["y"] < 54
          and not dot["gone"]["shown"], str(dot))

    print("\n--- kept in this browser ---")
    p.evaluate("""() => { setFade('both');
      setFadeEnvelope({ delay: 0.3, attack: 3.5, decay: 0.8, sustain: 0.4, release: 0.25, attackMid: 0.7, releaseMid: 0.2, loop: true }, 0);
      setFadeEnvelope({ attack: 0.1, restart: true }, 1); saveFade(); }""")
    p.reload(); p.wait_for_timeout(700)
    kept = p.evaluate("""() => ({ mode: fade.mode, a: fade.envs[0], b: { attack: fade.envs[1].attack, restart: fade.envs[1].restart },
                                  shown: el.fadeMode.value, text: el.fadeEnvValue.textContent })""")
    check("the fade and both envelopes come back after a reload, on the panel too",
          kept["mode"] == "both" and kept["shown"] == "both" and kept["text"] == "In 3.5 s \u00b7 Out 0.25 s"
          and {k: kept["a"][k] for k in ("delay", "attack", "decay", "sustain", "release", "attackMid", "releaseMid", "loop")}
              == {"delay": 0.3, "attack": 3.5, "decay": 0.8, "sustain": 0.4, "release": 0.25, "attackMid": 0.7, "releaseMid": 0.2, "loop": True}
          and kept["b"] == {"attack": 0.1, "restart": True}, str(kept))
    # Stored by the versions before: one time for both halves, and then in, out and their shapes.
    for stored, want in [({"mode": "in", "seconds": 3}, (3, 3, 0.5)),
                         ({"mode": "in", "inSeconds": 1.5, "outSeconds": 4, "inMid": 0.7, "outMid": 0.5}, (1.5, 4, 0.7))]:
        p.evaluate("(v) => window.localStorage.setItem('scope.fade', JSON.stringify(v))", stored)
        p.reload(); p.wait_for_timeout(700)
        old = p.evaluate("() => [fade.mode].concat([0, 1].map((l) => [fade.envs[l].attack, fade.envs[l].release, fade.envs[l].attackMid]))")
        check("and one stored as %s comes back on both layers" % sorted(stored), old == ["in", list(want), list(want)], str(old))
    p.evaluate("() => { window.localStorage.removeItem('scope.fade'); }")

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("routings fade in and out on every path, and presets glide")
