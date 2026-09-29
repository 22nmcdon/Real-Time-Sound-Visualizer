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
        await wait(150);
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

    print("\n--- kept in this browser ---")
    p.evaluate("() => { setFade('both', 3.5); syncFadePanel(); }")
    p.reload(); p.wait_for_timeout(700)
    kept = p.evaluate("() => ({ mode: fade.mode, seconds: fade.seconds, shown: el.fadeMode.value, time: el.fadeTimeValue.textContent })")
    check("the fade and its time come back after a reload, on the panel too",
          kept == {"mode": "both", "seconds": 3.5, "shown": "both", "time": "3.5 s"}, str(kept))
    p.evaluate("() => { setFade('off', 2); }")

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("routings fade in and out on every path, and presets glide")
