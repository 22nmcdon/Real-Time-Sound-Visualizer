"""K1's thresholds, and the Pluck they can strike.

Against the way they would fail:

- firing on a level rather than on rising through it: held above, it fires
  once; wobbling inside the hysteresis, never again; only a fall past it and
  a rise back fires a second time;
- no gap: a value that flickers across the level every millisecond fires no
  faster than every 80 ms;
- watching the wrong thing, or nothing: the source it watches is the one
  chosen, and a code carries the choice by name;
- an event loop let through a threshold: watching something that hears the
  generator, it may not strike the generator;
- a Pluck that is not a note: it strikes the score's voice at its chosen
  pitch, the depth its velocity, and sends and ends that note as MIDI.
"""
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
  window.__wait = (ms) => new Promise((r) => setTimeout(r, ms));
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

    print("\n--- rising through the level ---")
    rise = p.evaluate("""() => {
      // A source the test sets, watched at a level of one half.
      const knob = { v: 0 };
      registerSource({ id: 'test.knob', label: 'Knob', ink: 'ch1', value: () => knob.v });
      thresh.watch = 'test.knob'; thresh.level = 0.5; thresh.armed = false; thresh.last = -Infinity;
      const c0 = thresh.count; let t = 1e6;
      const at = (v) => { knob.v = v; t += 100; thresholdStep(t); return thresh.count - c0; };
      const trace = [at(0), at(0.6), at(0.9), at(0.7), at(0.47), at(0.6), at(0.44), at(0.55)];
      // The gap: across the level every millisecond for 400 ms.
      const c1 = thresh.count, t0 = t;
      for (let k = 0; k < 400; k++) { knob.v = k % 2 ? 0.9 : 0; thresholdStep(t0 + k); }
      const flicker = thresh.count - c1;
      MOD_SOURCES.delete('test.knob'); thresh.watch = 'env.live';
      return { trace, flicker };
    }""")
    print("    counts through 0, .6, .9, .7, .47, .6, .44, .55: %s; flickering for 400 ms: %d"
          % (rise["trace"], rise["flicker"]))
    check("it fires on rising through the level, once however long it stays above, not on wobbles inside the "
          "hysteresis, and again only after a fall past it",
          rise["trace"] == [0, 1, 1, 1, 1, 1, 1, 2], str(rise["trace"]))
    check("and a value flickering across the level every millisecond fires no faster than every 80 ms",
          3 <= rise["flicker"] <= 400 / 80 + 1, str(rise["flicker"]))

    print("\n--- what it may strike ---")
    allowed = p.evaluate("""() => {
      const t = MOD_SOURCES.get('threshold'), reswing = MOD_DESTS.get('gen.reswing');
      thresh.watch = 'lfo1'; const plain = routingAllowed(t, reswing);
      // On the tone, the flux hears the generator: a strike would be heard.
      thresh.watch = 'hear.flux'; const loop = routingAllowed(t, reswing);
      const slider = routingAllowed(t, MOD_DESTS.get('gen.fm'));
      thresh.watch = 'env.live';
      return { plain, loop, slider };
    }""")
    check("watching an oscillator it may strike the generator; watching what hears the generator it may not; "
          "and it never reaches a slider", allowed == {"plain": True, "loop": False, "slider": False}, str(allowed))

    print("\n--- Pluck ---")
    p.evaluate("() => midiConnect()"); p.wait_for_timeout(300)
    plucked = p.evaluate("""async () => {
      el.midiOut.value = 'out1'; el.midiOutCh.value = '4'; el.midiOut.dispatchEvent(new Event('change'));
      el.pluckNote.value = '67'; el.pluckNote.dispatchEvent(new Event('change'));
      const src = state.source, strike = src.strike.bind(src), got = [];
      src.strike = (notes) => { got.push(notes); strike(notes); };
      __sent.length = 0; midiOut.times = [];
      // Through the routing, as a real event would arrive.
      const knob = { v: 0 };
      registerSource({ id: 'test.knob', label: 'Knob', ink: 'ch1', value: () => knob.v });
      // The first block ran on synthetic times a million milliseconds on; the
      // gap would hold the real clock off until then.
      thresh.watch = 'test.knob'; thresh.level = 0.5; thresh.armed = false; thresh.last = -Infinity;
      state.modRoutings = [{ sourceId: 'threshold', destId: 'gen.pluck', amount: 0.75 }]; touchRoutings();
      await __wait(200);
      knob.v = 0.8; await __wait(200);
      const on = __sent.map((m) => m.slice());
      await __wait(300);
      const off = __sent.map((m) => m.slice());
      state.modRoutings = []; touchRoutings(); MOD_SOURCES.delete('test.knob'); thresh.watch = 'env.live';
      src.strike = strike;
      el.midiOut.value = ''; el.midiOut.dispatchEvent(new Event('change'));
      const code = (() => { thresh.watch = 'picture.change'; thresh.level = 0.3;
        const s = snapshot(); return [s.threshWatch, s.threshLevel, s.pluckNote]; })();
      thresh.watch = 'env.live'; thresh.level = 0.5;
      return { got, on, off, code, hz: midiHz(67) };
    }""")
    print("    %s" % plucked)
    check("a threshold routed to Pluck strikes the score's voice once, at the chosen pitch, the depth its velocity",
          len(plucked["got"]) == 1 and abs(plucked["got"][0][0][0] - plucked["hz"]) < 1e-9
          and abs(plucked["got"][0][0][1] - 0.75) < 1e-9, str(plucked["got"]))
    check("and sends that note on the chosen channel, and ends it",
          [0x94, 67, 95] in plucked["on"] and [0x84, 67, 0] in plucked["off"], "%s / %s" % (plucked["on"], plucked["off"]))
    check("and a setup code carries what it watches, its level, and the pluck's note",
          plucked["code"] == ["picture.change", 30, 67], str(plucked["code"]))

    print("\n--- on the Sources tab ---")
    tab = p.evaluate("""() => {
      setView('bench'); setBenchTab('sources'); selectSource('threshold');
      const w = document.getElementById('threshWatch'), l = document.getElementById('threshLevel');
      const offered = w ? [...w.options].map((o) => o.value) : [];
      if (w) { w.value = 'hear.band1'; w.dispatchEvent(new Event('change')); }
      if (l) { l.value = '70'; l.dispatchEvent(new Event('input')); }
      const out = { offered: offered.length, events: offered.filter((id) => MOD_SOURCES.get(id).event).length,
                    watch: thresh.watch, level: thresh.level };
      thresh.watch = 'env.live'; thresh.level = 0.5; setView('scope');
      return out;
    }""")
    check("its controls on the Sources tab choose what it watches, from every value and no event, and its level",
          tab["offered"] > 10 and tab["events"] == 0 and tab["watch"] == "hear.band1" and abs(tab["level"] - 0.7) < 1e-9,
          str(tab))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
