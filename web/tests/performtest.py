"""The presets for playing: are they played?

The failure these guard against is a preset that loads, looks right in the
browser, and does nothing a player could hear change:

- a routing whose source is spelt wrong or does not exist. The matrix keeps
  a routing it cannot resolve rather than dropping it, which is right for a
  preset loaded before the keyboard is plugged in and means a typo is kept
  forever, silently;
- a routing whose source a keyboard never moves: a keyboard preset that is
  really an LFO preset;
- a split or a layer that sends every note to one layer;
- a live-effects preset that never builds the effects insert, and so draws
  and plays the input exactly as it came in.

`presettest.py` holds the library as a whole: that every field comes back at
the value it names, that each preset is unique and described.
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

KEYBOARD = ["Poly keys", "Split and layer", "Hands on the sound"]

# One port and a way to push bytes at it, before the page's script runs.
STUB = """
  window.__midi = { port: null };
  navigator.requestMIDIAccess = function () {
    const port = { id: "stub", name: "Stub Keyboard", onmidimessage: null };
    window.__midi.port = port;
    return Promise.resolve({ inputs: new Map([["stub", port]]), outputs: new Map(), onstatechange: null });
  };
  window.__send = (bytes) => window.__midi.port.onmidimessage({ data: Uint8Array.from(bytes) });
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

    print("\n--- what the sections are ---")
    shape = p.evaluate("""(names) => {
      const hands = /^(midi\\.|notes\\.|cc\\.|env\\.note$)/;
      const played = (setup) => decodeRoutings(setup.mod).some((r) => hands.test(r.sourceId));
      const out = { missing: [], unplayed: [], unlayered: [], counts: {} };
      for (const name of names) {
        const section = PRESETS.find(([s]) => s === name);
        if (!section) { out.missing.push(name); continue; }
        out.counts[name] = section[1].length;
        for (const [preset, setup] of section[1]) {
          if (!played(setup)) out.unplayed.push(preset);
          if (name === 'Split and layer' && !['split', 'layer'].includes(setup.layers)) out.unlayered.push(preset);
        }
      }
      // The null: a preset from the Organ section, which no hand moves.
      const organ = PRESETS.find(([s]) => s === 'Organ')[1][0];
      out.organPlayed = played(organ[1]);
      const live = PRESETS.find(([s]) => s === 'Live effects');
      out.live = live ? [live[1].length, live[2]] : null;
      return out;
    }""", KEYBOARD)
    print("    %s" % shape)
    check("three sections for playing, each with a routing a hand moves in every preset",
          shape["missing"] == [] and shape["unplayed"] == [] and all(n >= 5 for n in shape["counts"].values())
          and shape["organPlayed"] is False, str(shape))
    check("and every preset in Split and layer is a split or a layer", shape["unlayered"] == [], str(shape["unlayered"]))
    check("and a section of effects for live inputs, landing on whatever is playing",
          shape["live"] is not None and shape["live"][0] >= 5 and shape["live"][1] == "display", str(shape["live"]))

    print("\n--- played ---")
    p.evaluate("() => midiConnect()"); p.wait_for_timeout(200)
    p.evaluate("""() => {
      /* Everything a hand can do at once: a wide chord struck hard, held
         under the pedal, with the mod wheel up. Every source a keyboard
         preset names is moved by some part of it. */
      const chord = [36, 48, 60, 64, 67, 72, 84];
      const value = (id) => { const s = MOD_SOURCES.get(id); return s ? s.value() : null; };
      window.__play = async () => {
        const routings = state.modRoutings.map((r) => r.sourceId);
        const rest = routings.map(value);
        __send([0xB0, 1, 127]); __send([0xB0, 64, 127]);
        for (const n of chord) __send([0x90, n, 120]);
        await __wait(250);
        if (modDirty) compileRoutes();
        const compiled = routings.map((id) => genRoutes.some((r) => r.source && r.source.id === id));
        const moved = routings.map(value);
        const layers = midi.poly && midi.poly.layers ? midi.poly.layers.map((l) => l.sounding) : null;
        for (const n of chord) __send([0x80, n, 0]);
        __send([0xB0, 64, 0]); __send([0xB0, 1, 0]);
        // Long enough for the slowest release among them to finish, so the
        // next preset's "at rest" is at rest.
        await __wait(1700);
        return { routings, rest, moved, compiled, layers };
      };
    }""")
    played = p.evaluate("""async (names) => {
      const out = [];
      for (const name of names) {
        for (const [preset, setup] of PRESETS.find(([s]) => s === name)[1]) {
          applyPreset('b:' + preset);
          await __wait(150);
          out.push(Object.assign({ preset, section: name, split: setup.layers || null }, await __play()));
        }
      }
      return out;
    }""", KEYBOARD)

    def dead_routings(row):
        out = []
        for i, source in enumerate(row["routings"]):
            if not (row["compiled"][i] and row["rest"][i] is not None and row["rest"][i] < 0.05
                    and row["moved"][i] is not None and row["moved"][i] > 0.3):
                out.append((row["preset"], source, row["rest"][i], row["moved"][i], row["compiled"][i]))
        return out

    dead = [d for row in played for d in dead_routings(row)]
    print("    %d presets played" % len(played))
    for row in played:
        print("    %-24s %s" % (row["preset"], ", ".join("%s %s->%s" % (s, None if r is None else round(r, 2),
              None if m is None else round(m, 2)) for s, r, m in zip(row["routings"], row["rest"], row["moved"]))))
    check("every routing in them reaches the generator, is still at rest, and moves when played",
          len(played) >= 15 and dead == [], str(dead[:4]))

    # The null, through the same measurement: a source spelt wrong is kept by
    # the matrix, never compiled and never moves, and this check exists to
    # catch exactly that.
    null = p.evaluate("""async () => {
      applyPreset('b:Chords darken'); await __wait(150);
      state.modRoutings = decodeRoutings('notes.cont>gen.vcf@-0.600'); touchRoutings();
      return Object.assign({ preset: 'misspelt' }, await __play());
    }""")
    check("and the null: a source spelt wrong is caught by the same measurement",
          dead_routings(null) != [], str(null))

    splits = [r for r in played if r["split"]]
    uneven = [(r["preset"], r["layers"]) for r in splits
              if not (r["layers"] and len(r["layers"]) == 2 and r["layers"][0] > 0 and r["layers"][1] > 0)]
    check("each split and layer sounds both layers from one chord across the keyboard",
          len(splits) >= 5 and uneven == [], str(uneven or [(r["preset"], r["layers"]) for r in splits]))

    print("\n--- live effects on a microphone ---")
    live = p.evaluate("""async () => {
      // A mono microphone: one oscillator, told to say it is one channel.
      const ctx = new AudioContext();
      const dest = ctx.createMediaStreamDestination(), a = ctx.createOscillator(), g = ctx.createGain();
      a.frequency.value = 220; g.gain.value = 0.8; a.connect(g); g.connect(dest); a.start();
      const track = dest.stream.getAudioTracks()[0], own = track.getSettings.bind(track);
      track.getSettings = () => Object.assign({}, own(), { channelCount: 1 });
      navigator.mediaDevices.getUserMedia = () => Promise.resolve(dest.stream);
      el.srcMic.click(); await __wait(1200);
      const out = { kind: state.source.kind, presets: [] };
      const apart = () => { const w = state.source.getLatestWindow(4410); let m = 0;
        for (let i = 0; i < w[0].length; i++) m = Math.max(m, Math.abs(w[0][i] - (w[1] || w[0])[i])); return m; };
      for (const [preset] of PRESETS.find(([s]) => s === 'Live effects')[1]) {
        applyPreset('b:' + preset); await __wait(1200);
        const w = state.source.getLatestWindow(4410);
        out.presets.push({ preset, active: state.source.fx.active, where: el.planeWhere.textContent,
                           low: Math.min(...w[0]), apart: apart() });
      }
      // The contrast: a display preset with no effect in it leaves the input alone.
      applyPreset('b:Playing, waveform'); await __wait(800);
      out.plain = { active: state.source.fx.active, apart: apart() };
      return out;
    }""")
    for row in live["presets"]:
        print("    %-28s active %s, low %.3f, apart %.3f" % (row["preset"], row["active"], row["low"], row["apart"]))
    print("    plain: %s" % live["plain"])
    check("every live-effects preset puts the effects insert in a microphone's path, and says so",
          live["kind"] == "mic" and all(r["active"] and r["where"].startswith("On your input") for r in live["presets"])
          and live["plain"]["active"] is False, str([(r["preset"], r["active"]) for r in live["presets"]]))
    by = {r["preset"]: r for r in live["presets"]}
    octave, swirl = by.get("Octave up, on your input"), by.get("Your level, swirling")
    check("the octave-up folds the input's troughs up, and your level on the twist turns a mono diagonal off itself",
          octave is not None and octave["low"] > -0.02 and swirl is not None and swirl["apart"] > 0.1
          and live["plain"]["apart"] < 1e-3,
          "%s; %s; plain %s" % (octave, swirl, live["plain"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
