"""Onset (J1) and the events it fires (S3): what was left of drawingtest.py
when G2 took the drawings, whose Swing again and Kick were the only things an
event could strike.

The event machinery stays for the next thing struck (`fireEvents`, the rule
that an event reaches only an event), and Onset with the parked hearing
family, so both are held here against stand-in destinations this suite
registers itself - the page has none of its own until something struck comes
back. Written against the way each would fail:

- an event that reaches a value, or a value an event: the matrix refuses
  both, the editor never offers them, a drop does nothing;
- an onset that fires on a held note, on a release, on the click of a note
  cut off, more than once an attack, or faster than the gap allows;
- a routing that fires when it is made, or never fires at all.

What drawingtest.py also held went with the drawings: the pendulums' energy
in, and a solid's kick and its friction.
"""
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
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0&brain=js"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    # The page has no event destination of its own since G2 (Swing again and
    # Kick were the two), so the suite registers two stand-ins, struck into a
    # log: `test.once` counts its strikes and `test.depth` keeps each depth.
    # They are the registry's own entries, read by the page's own rules.
    p.evaluate("""() => {
      window.__struck = { once: 0, depth: [] };
      registerDest({ id: 'test.once', kind: 'event', label: 'Once', fire: () => { __struck.once++; } });
      registerDest({ id: 'test.depth', kind: 'event', label: 'Depth', fire: (amount) => { __struck.depth.push(amount); } });
    }""")
    # The null: with nothing struck registered at all, an onset reaches
    # nothing - so the check below reads the stand-ins, not something left
    # on the page.
    bare = p.evaluate("""() => [...MOD_DESTS.values()].filter((d) => d.kind === 'event' && !d.id.startsWith('test.'))
                                 .map((d) => d.id)""")
    check("the page itself has no event destination left (G2 took Swing again and Kick)", bare == [], str(bare))

    print("\n--- events reach only what is struck (S3) ---")
    p.evaluate("() => __mic()")
    s3 = p.evaluate("""() => {
      const offered = (id) => [...MOD_SOURCES.values()].filter((s) => routingAllowed(s, MOD_DESTS.get(id))).map((s) => s.id);
      const reaches = (id) => [...MOD_DESTS.values()].filter((d) => routingAllowed(MOD_SOURCES.get(id), d)).map((d) => d.id);
      state.modRoutings = []; addRouting('hear.onset', 'view.rotate'); addRouting('hear.flux', 'test.once');
      const dropped = state.modRoutings.length;
      return { once: offered('test.once'), depth: offered('test.depth'), onset: reaches('hear.onset').sort(),
               rotate: offered('view.rotate').includes('hear.onset'), dropped };
    }""")
    print("    %s" % s3)
    # The events, written out: the onset, and the two stand-ins it strikes.
    # The threshold (K1) was an event too, and Pluck a thing struck, until P5
    # cut both; Swing again and Kick were struck until G2.
    check("an onset reaches only what is struck, and only events reach that",
          s3["once"] == ["hear.onset"] and s3["depth"] == ["hear.onset"]
          and s3["onset"] == ["test.depth", "test.once"] and not s3["rotate"], str(s3))
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
      const log = window.__struck;
      log.once = 0; log.depth = [];
      hit.count = 5;
      state.modRoutings = [{ sourceId: 'test.hit', destId: 'test.once', amount: 1 },
                           { sourceId: 'test.hit', destId: 'test.depth', amount: 0.5 }];
      touchRoutings(); await __wait(300);
      const made = [log.once, log.depth.length];
      hit.count++; await __wait(200);
      const once = [log.once, log.depth.slice()];
      hit.count += 3; await __wait(200);
      const skipped = [log.once, log.depth.length];
      // The onset itself, hearing the generator on the tone, is refused.
      const refused = routingAllowed(MOD_SOURCES.get('hear.onset'), MOD_DESTS.get('test.once'));
      state.modRoutings = []; touchRoutings(); MOD_SOURCES.delete('test.hit');
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


    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
