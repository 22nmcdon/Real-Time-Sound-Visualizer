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
  and plays the input exactly as it came in;
- a Listening preset whose source does not hear, or is treated as a loop on a
  microphone and so held to the picture's reach for no reason.

`presettest.py` holds the library as a whole: that every field comes back at
the value it names, that each preset is unique and described.

The sections walked here - the keyboard's, Live effects, Listening - are the
old library's, from before P8g, read from corpus.py: the bank that replaced it
has none of them, and these setups are still the widest test there is of a
routing a hand or an ear moves. Loaded as a preset was (loadCorpus restores
the setup and sends it on), so what is measured is the setup, not the bank.
"""
# Since stage 5, step 3, batch 4 (13 Nov): what the sections are is read on
# the default page (the corpus and the face's codec, no brain). The keyboard
# sections played - every routing reaching the generator, still at rest and
# moving when played, the cut ones loading with none, the misspelt null, and
# both layers sounding - are core/tests/pieces/perform.py's, on the
# instrument: here they read the page's own MOD_SOURCES, genRoutes and
# midi.poly.layers, which on the default are the face's. The live effects and
# the Listening presets stay on ?brain=js, on a page of their own: they put a
# microphone through the page's own effects insert (state.source.fx) and ask
# the page's compiler, and the instrument's way with an input needs input
# samples - render_cpp's, or livefx's batch.
import os
from playwright.sync_api import sync_playwright
import corpus

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

KEYBOARD = ["Poly keys", "Chords drawn", "Arpeggios", "Split", "Layer", "Hands on the sound", "Many sources"]

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
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(700)
    corpus.install(p)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    print("\n--- what the sections are ---")
    shape = p.evaluate("""(names) => {
      const hands = /^(midi\\.|notes\\.|cc\\.|env\\.note$)/;
      const played = (setup) => decodeRoutings(setup.mod).some((r) => hands.test(r.sourceId));
      const out = { missing: [], unplayed: [], unlayered: [], counts: {} };
      for (const name of names) {
        const section = CORPUS.find(([s]) => s === name);
        if (!section) { out.missing.push(name); continue; }
        out.counts[name] = section[1].length;
        for (const [preset, setup] of section[1]) {
          if (!played(setup)) out.unplayed.push(preset);
          if (name === 'Split' && setup.layers !== 'split') out.unlayered.push(preset);
          if (name === 'Layer' && setup.layers !== 'layer') out.unlayered.push(preset);
        }
      }
      // The null: a preset from the Organ section, which no hand moves.
      const organ = CORPUS.find(([s]) => s === 'Organ')[1][0];
      out.organPlayed = played(organ[1]);
      const live = CORPUS.find(([s]) => s === 'Live effects');
      out.live = live ? [live[1].length, live[2]] : null;
      return out;
    }""", KEYBOARD)
    print("    %s" % shape)
    check("the sections for playing, each with a routing a hand moves in every preset",
          shape["missing"] == [] and shape["unplayed"] == [] and all(n >= 5 for n in shape["counts"].values())
          and shape["organPlayed"] is False, str(shape))
    check("and every preset in Split is a split, and every one in Layer a layer", shape["unlayered"] == [], str(shape["unlayered"]))
    check("and a section of effects for live inputs, landing on whatever is playing",
          shape["live"] is not None and shape["live"][0] >= 5 and shape["live"][1] == "display", str(shape["live"]))

    # Left on the page's own brain (batch 4): the microphone through the
    # page's effects insert, and the Listening presets on it.
    p = b.new_page(viewport={"width": 1400, "height": 900})
    p.on("pageerror", lambda e: bad.append("pageerror (?brain=js): " + str(e)))
    p.add_init_script(STUB)
    p.goto(f"file://{ART}/scope.html?picture=0&brain=js"); p.wait_for_timeout(700)
    corpus.install(p)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

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
      for (const [preset] of CORPUS.find(([s]) => s === 'Live effects')[1]) {
        loadCorpus(preset); await __wait(1200);
        const w = state.source.getLatestWindow(4410);
        out.presets.push({ preset, active: state.source.fx.active, where: el.planeWhere.textContent,
                           low: Math.min(...w[0]), apart: apart() });
      }
      /* The contrast: a display preset with no effect in it leaves the input
         alone. Asked until it says so or three seconds pass, rather than once
         at 800 ms: in a full run on a loaded machine the window read then
         could still hold the last effect's samples (1.58 apart, once in
         three full runs, never alone), and a window that is late is not the
         input being processed. An input still processed after three seconds
         fails as it did. */
      loadCorpus('Playing, waveform');
      let plainAt = 0;
      for (; plainAt < 3000 && !(state.source.fx.active === false && apart() < 1e-3); plainAt += 100) await __wait(100);
      out.plain = { active: state.source.fx.active, apart: apart(), ms: plainAt };
      return out;
    }""")
    for row in live["presets"]:
        print("    %-28s active %s, low %.3f, apart %.3f" % (row["preset"], row["active"], row["low"], row["apart"]))
    print("    plain: %s" % live["plain"])
    # Your input, kaleidoscope had nothing but the kaleidoscope, cut on 7
    # Nov, and Your level, swirling nothing but the level on the twist, a
    # source cut in F4b the same day: they load as the plain input now, and
    # are held to that - which is also this check seen to fail, since they
    # are the presets with no effect.
    CUT = ("Your input, kaleidoscope", "Your level, swirling")
    kept = [r for r in live["presets"] if r["preset"] not in CUT]
    emptied = [r for r in live["presets"] if r["preset"] in CUT]
    check("every live-effects preset puts the effects insert in a microphone's path, and says so",
          live["kind"] == "mic" and len(kept) >= 10
          and all(r["active"] and r["where"].startswith("On your input") for r in kept)
          and live["plain"]["active"] is False, str([(r["preset"], r["active"]) for r in live["presets"]]))
    check("and the two whose only effect was cut leave the input alone",
          len(emptied) == 2 and all(r["active"] is False for r in emptied), str(emptied))
    by = {r["preset"]: r for r in live["presets"]}
    octave = by.get("Octave up, on your input")
    # Your level on the twist turned a mono diagonal off itself here too,
    # until F4b cut the level as a source.
    check("the octave-up folds the input's troughs up",
          octave is not None and octave["low"] > -0.02 and live["plain"]["apart"] < 1e-3,
          "%s; plain %s" % (octave, live["plain"]))

    print("\n--- listening, on the same microphone ---")
    listen = p.evaluate("""async () => {
      const out = [];
      for (const [preset] of CORPUS.find(([s]) => s === 'Listening')[1]) {
        loadCorpus(preset); await __wait(300);
        if (modDirty) compileRoutes();
        for (const r of state.modRoutings) {
          const src = MOD_SOURCES.get(r.sourceId), dest = MOD_DESTS.get(r.destId);
          const live = !!src && !!dest && (dest.kind === 'visual'
            || genRoutes.some((g) => g.source === src && !g.loopTotal));
          out.push({ preset, source: r.sourceId, hears: !!src && src.family === 'hearing',
                     loop: !!src && src.fromPicture, live });
        }
      }
      return out;
    }""")
    for row in listen:
        print("    %-26s %-12s hears %s, loop %s, live %s" % (row["preset"], row["source"], row["hears"],
                                                             row["loop"], row["live"]))
    wrong = [r for r in listen if not (r["hears"] and not r["loop"] and r["live"])]
    check("every Listening preset routes a source that hears, and on a microphone it is live and no loop",
          len(listen) >= 5 and wrong == [], str(wrong[:3]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
