"""The sound driving the drawings (Stage J2), and the events that do it (S3).

Written against the way each would fail:

- energy in that does not hold the swing, or holds it somewhere other than
  where the law puts it: a steady drive against a decay of 0.5 a second must
  settle at 3 / 3.5, and a routing at full depth must be the slider at one,
  sample for sample;
- a drive that stops with a step: the swing picks up the plain decay from
  where it is, not from where the clock says it would be, which is a jump
  from 0.52 to 0.14;
- a kick that is not a kick: six times the spin at once, 1/e of that after
  the friction's 1.2 s, never past twenty (read one sample of friction
  later, so 19.9996), and gone in ten seconds; and a kick of nought that
  changes anything;
- an event that reaches a value, or a value an event: the matrix refuses
  both, the editor never offers them, a drop does nothing;
- an onset that fires on a held note, on a release, on the click of a note
  cut off, more than once an attack, or faster than the gap allows;
- a routing that fires when it is made, or never fires at all.
"""
import math, os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

# A core off the page, as the time tests use: each step's settings, then that
# many samples. Returns what the getters say after each step, and the output.
CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('amp', 0.5);
  const out = { L: [], after: [] };
  for (const step of setup.steps) {
    for (const k in step.tone || {}) core.set(k, step.tone[k]);
    if (step.routes) core.setRoutes(step.routes);
    if (step.kick !== undefined) core.kick(step.kick);
    const L = new Float32Array(step.n), R = new Float32Array(step.n);
    core.block(L, R, step.n);
    if (setup.keep) for (let i = 0; i < step.n; i++) out.L.push(L[i]);
    out.after.push({ swing: core.swingLevel, kick: core.spinKick });
  }
  return out;
}"""

STUB = """
  window.__wait = (ms) => new Promise((r) => setTimeout(r, ms));
  window.__mic = async () => {
    const ctx = new AudioContext();
    const dest = ctx.createMediaStreamDestination(), a = ctx.createOscillator(), g = ctx.createGain();
    a.frequency.value = 330; g.gain.value = 0; a.connect(g); g.connect(dest); a.start();
    window.__osc = { ctx, g };
    navigator.mediaDevices.getUserMedia = () => Promise.resolve(dest.stream);
    el.srcMic.click(); await __wait(1200);
  };
  // A note: on at once, off at once or released over `release` seconds.
  window.__note = (on, release) => {
    const o = window.__osc, t = o.ctx.currentTime;
    o.g.gain.cancelScheduledValues(t); o.g.gain.setValueAtTime(o.g.gain.value, t);
    if (on) o.g.gain.setValueAtTime(0.8, t);
    else if (release) o.g.gain.linearRampToValueAtTime(0, t + release);
    else o.g.gain.setValueAtTime(0, t);
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
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    run = lambda steps, keep=False: p.evaluate(CORE, {"steps": steps, "keep": keep})
    SR = 44100
    slot = p.evaluate("() => SWING_SLOT")
    harmo = {"mode": "harmonograph", "pitched": False, "decay": 0.5, "swingRate": 2}

    print("\n--- energy in ---")
    plain = run([{"tone": dict(harmo, swingDrive=0), "n": 4 * SR}])["after"][0]["swing"]
    held = run([{"tone": dict(harmo, swingDrive=1), "n": 6 * SR}])["after"][0]["swing"]
    print("    no drive, after 4 s: %.4f (want %.4f); full drive, after 6 s: %.4f (want %.4f)"
          % (plain, math.exp(-2), held, 3 / 3.5))
    check("with no drive the swing runs down as it always did, and a full drive holds it at 3 / (3 + decay)",
          abs(plain - math.exp(-2)) < 1e-3 and abs(held - 3 / 3.5) < 0.005, "%.4f, %.4f" % (plain, held))
    static = run([{"tone": dict(harmo, swingDrive=1), "n": SR}], keep=True)["L"]
    routed = run([{"tone": dict(harmo, swingDrive=0), "n": SR,
                   "routes": [{"held": 1, "slot": slot, "amount": 2, "unipolar": False}]}], keep=True)["L"]
    gap = max(abs(a - c) for a, c in zip(static, routed))
    print("    routed at full depth against the slider at one: largest difference %.2e" % gap)
    check("and a routing that pushes it to one draws exactly what the slider at one draws",
          gap < 1e-6 and max(abs(a) for a in routed) > 0.1, "%.2e" % gap)
    stop = run([{"tone": dict(harmo, swingDrive=1), "n": 3 * SR}, {"tone": {"swingDrive": 0}, "n": SR}])["after"]
    want = stop[0]["swing"] * math.exp(-0.5)
    print("    driven 3 s to %.4f, then a second of plain decay: %.4f (want %.4f; from the clock, %.4f)"
          % (stop[0]["swing"], stop[1]["swing"], want, math.exp(-0.5 * 4)))
    check("and when the drive stops it runs down from where it is, not from where the clock says",
          abs(stop[1]["swing"] - want) < 2e-3, "%.4f against %.4f" % (stop[1]["swing"], want))

    print("\n--- a kick, and friction ---")
    wire = {"mode": "wireframe", "model": "Cube", "spinRate": 1}
    k = run([{"tone": wire, "n": 1, "kick": 1}, {"n": int(1.2 * SR)}, {"n": 1, "kick": 10}, {"n": 10 * SR}])["after"]
    print("    after the kick %.4f; after 1.2 s %.4f (want %.4f); kicked hard %.3f; ten seconds on %.5f"
          % (k[0]["kick"], k[1]["kick"], k[0]["kick"] / math.e, k[2]["kick"], k[3]["kick"]))
    check("a kick is six times the spin at once, 1/e of that after the friction's 1.2 s, never past twenty, "
          "and gone ten seconds on",
          abs(k[0]["kick"] - 6) < 1e-3 and abs(k[1]["kick"] - 6 / math.e) < 0.01 and abs(k[2]["kick"] - 20) < 1e-3
          and k[3]["kick"] < 0.01, str([round(x["kick"], 4) for x in k]))
    base = run([{"tone": wire, "n": SR // 2}], keep=True)["L"]
    kicked = run([{"tone": wire, "n": SR // 2, "kick": 1}], keep=True)["L"]
    nought = run([{"tone": wire, "n": SR // 2, "kick": 0}], keep=True)["L"]
    moved = max(abs(a - c) for a, c in zip(base, kicked))
    same = max(abs(a - c) for a, c in zip(base, nought))
    check("and it turns the solid faster, where a kick of nought changes nothing at all",
          moved > 0.05 and same == 0, "kicked %.3f, nought %.2e" % (moved, same))

    print("\n--- events reach only what is struck (S3) ---")
    p.evaluate("() => __mic()")
    s3 = p.evaluate("""() => {
      const offered = (id) => [...MOD_SOURCES.values()].filter((s) => routingAllowed(s, MOD_DESTS.get(id))).map((s) => s.id);
      const reaches = (id) => [...MOD_DESTS.values()].filter((d) => routingAllowed(MOD_SOURCES.get(id), d)).map((d) => d.id);
      state.modRoutings = []; addRouting('hear.onset', 'view.rotate'); addRouting('hear.flux', 'gen.reswing');
      const dropped = state.modRoutings.length;
      return { reswing: offered('gen.reswing'), kick: offered('gen.kick'), onset: reaches('hear.onset').sort(),
               rotate: offered('view.rotate').includes('hear.onset'), dropped };
    }""")
    print("    %s" % s3)
    check("an onset reaches only Swing again and Kick, and only an onset reaches them",
          s3["reswing"] == ["hear.onset"] and s3["kick"] == ["hear.onset"]
          and s3["onset"] == ["gen.kick", "gen.reswing"] and not s3["rotate"], str(s3))
    check("and dropping an event on a value, or a value on an event, makes no routing", s3["dropped"] == 0,
          str(s3["dropped"]))

    print("\n--- onset ---")
    counts = p.evaluate("""async () => {
      const count = () => MOD_SOURCES.get('hear.onset').count;
      const out = {};
      __note(false); await __wait(500);
      let c = count(); __note(true); await __wait(2000); out.held = count() - c;          // one attack, then held
      c = count(); __note(false, 0.08); await __wait(800); out.released = count() - c;
      // Cut off in one sample each time, so each strike ends in a click.
      c = count();
      for (let i = 0; i < 8; i++) { __note(true); await __wait(120); __note(false); await __wait(130); }
      out.struck = count() - c;
      /* The gap, on its own. Played notes cannot test it: an attack takes a
         window's fill to pass, and hysteresis holds every strike 40 ms apart
         to two. So the detector is fed a flux that rises and falls on every
         call, a millisecond apart, with the microphone silent - rising, loud
         and past the threshold every other call. */
      await __wait(300); c = count();
      const t0 = performance.now();
      while (performance.now() - t0 < 400) {
        hearing.fluxRaw = 0.9; onsetStep(0.5, true);
        const t = performance.now(); while (performance.now() - t < 1) {}
        hearing.fluxRaw = 0; onsetStep(0.5, true);
      }
      out.fast = count() - c; out.fastMs = performance.now() - t0;
      /* Hysteresis, on its own too: a flux held high for 400 ms - a long
         swell - is one onset, where the gap alone would allow five; then it
         falls below the re-arming level, rises again, and is a second. */
      await __wait(200); c = count();
      let t = performance.now();
      while (performance.now() - t < 400) { hearing.fluxRaw = 0.9; onsetStep(0.5, true); }
      out.swell = count() - c;
      hearing.fluxRaw = 0.05; onsetStep(0.5, true);
      t = performance.now(); while (performance.now() - t < 100) {}
      hearing.fluxRaw = 0.9; onsetStep(0.5, true);
      out.again = count() - c;
      return out;
    }""")
    print("    one attack then held: %d; released: %d; struck eight times, cut off: %d; a flux flickering "
          "every millisecond for %.0f ms: %d" % (counts["held"], counts["released"], counts["struck"],
                                                counts["fastMs"], counts["fast"]))
    check("one attack is one onset however long it is held, and a release is none",
          counts["held"] == 1 and counts["released"] == 0, str(counts))
    check("eight strikes are eight onsets, the click of each cut-off not counted", counts["struck"] == 8,
          str(counts["struck"]))
    # At least four, so a detector that never fired cannot pass it either.
    check("and a flux held high through a 400 ms swell is one onset, and fires again once it has fallen",
          counts["swell"] == 1 and counts["again"] == 2, "%d, then %d" % (counts["swell"], counts["again"]))
    check("and a flux flickering every millisecond fires no faster than the 80 ms gap allows",
          4 <= counts["fast"] <= counts["fastMs"] / 80 + 1, "%d in %.0f ms" % (counts["fast"], counts["fastMs"]))

    print("\n--- firing ---")
    fire = p.evaluate("""async () => {
      // A stand-in event source, counted by the test, and the generator on
      // the tone to strike. Not hearing: a source that does not hear the
      // generator is the case an onset from a microphone lane is.
      el.srcTone.click(); await __wait(500);
      const hit = registerSource({ id: 'test.hit', label: 'Hit', ink: 'ch1', event: true, count: 0,
                                   value: () => 0 });
      const kicks = [], swings = [];
      const src = state.source, kick = src.kick.bind(src), reswing = src.reswing.bind(src);
      src.kick = (a) => { kicks.push(a); kick(a); };
      src.reswing = () => { swings.push(1); reswing(); };
      hit.count = 5;
      state.modRoutings = [{ sourceId: 'test.hit', destId: 'gen.reswing', amount: 1 },
                           { sourceId: 'test.hit', destId: 'gen.kick', amount: 0.5 }];
      touchRoutings(); await __wait(300);
      const made = [swings.length, kicks.length];
      hit.count++; await __wait(200);
      const once = [swings.length, kicks.slice()];
      hit.count += 3; await __wait(200);
      const skipped = [swings.length, kicks.length];
      // The onset itself, hearing the generator on the tone, is refused.
      const refused = routingAllowed(MOD_SOURCES.get('hear.onset'), MOD_DESTS.get('gen.reswing'));
      state.modRoutings = []; touchRoutings(); MOD_SOURCES.delete('test.hit');
      src.kick = kick; src.reswing = reswing;
      return { made, once, skipped, refused };
    }""")
    print("    %s" % fire)
    check("a routing does not fire when it is made, only on a count it has not seen",
          fire["made"] == [0, 0], str(fire["made"]))
    check("then a new count strikes each destination once, at its depth",
          fire["once"] == [1, [0.5]], str(fire["once"]))
    check("and three counts in one frame are one strike, not three", fire["skipped"] == [2, 2], str(fire["skipped"]))
    check("and an onset hearing the generator it would strike is refused", fire["refused"] is False,
          str(fire["refused"]))

    # Which lane of a rack counts as the generator, synchronously so no frame
    # runs with the stand-in installed: the trigger lane's, not the rack's.
    lanes = p.evaluate("""() => {
      const was = state.source, trig = state.trigSource;
      state.source = { kind: 'rack', lanes: [{ synth: false }, { synth: true }] };
      state.trigSource = 0; const live = hearsGenerator();
      state.trigSource = 1; const gen = hearsGenerator();
      state.source = was; state.trigSource = trig;
      return { live, gen };
    }""")
    check("in a rack, an onset hears the generator only when the trigger is on the generator's lane",
          lanes == {"live": False, "gen": True}, str(lanes))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
