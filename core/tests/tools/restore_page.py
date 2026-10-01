"""The page's own `restore`, in a browser: each setup in a file loaded the way
the page loads a preset or a code, and what it leaves in the instrument
written out as one JSON line - both layers' tones as the generator holds them,
the keyboard's settings and the panel it reads, the LFOs, the routings, the
key and the quantiser, the crossings, the score, the arpeggiator, the
threshold, the macros, the morph, the plane and the echo. restore_cpp writes
the same line from scope::restoreSetup.

`restore` writes into the page's controls and fires their handlers, so it can
only be run where there is a DOM; this is the one runner of the port that
needs a browser.

    python3 restore_page.py <setups, one JSON object a line>
    python3 restore_page.py --controls       the panel's sliders and menus
    python3 restore_page.py --sources        the page's sources and their reach
    python3 restore_page.py --presets        every preset's setup
    python3 restore_page.py --library        the whole library, as PRESETS
"""
import json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "..", "..", "..", "web", "scope.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

# What restore leaves behind, read out of the page. The tones leave out what
# is not a setting (the chord being played) and what a later piece of the
# port carries (the drawn cycles and the figures made of strokes).
DUMP = """(setups) => {
  const out = [];
  // `just` by its truth, which is what the generator plays by: the page keeps
  // the raw value as well, for its panel, and the core does not.
  const tone = (t, skip) => { const o = {}; for (const k of Object.keys(t)) if (!skip.includes(k)) o[k] = k === "just" ? !!t[k] : t[k]; return o; };
  for (const setup of setups) {
    let error = null;
    try { restore(setup); } catch (e) { error = String(e && e.message || e); }
    out.push(JSON.stringify({
      error,
      a: tone(genSettings(), ["cycle", "wavetable", "voices", "figPath"]),
      b: tone(genSettings(1), ["cycle", "wavetable", "voices"]),
      midi: { mode: midi.mode, draws: midi.draws, layers: { mode: midi.layers.mode, point: midi.layers.point, pair: midi.layers.pair },
              polyJust: midi.polyJust, hold: midi.hold, truth: midi.truth, follow: midi.follow, drive: midi.drive,
              play: midi.play, cc: encodeCC() },
      panel: { freq: el.freq.value, interval: el.interval.value, figureRate: el.figureRate.value, detail: el.detail.value },
      lfos: lfos.map((l) => ({ shape: l.shape, rate: l.rate, depth: l.depth, free: l.free, sync: l.sync })),
      mod: encodeRoutings(state.modRoutings),
      key: { root: state.keyRoot, scale: state.keyScale, quantise: state.quantise, glide: state.quantiseGlide, bpm: transport.set },
      cross: { on: cross.on, x: cross.x, y: cross.y, noteX: cross.noteX, noteY: cross.noteY, decayMs: cross.decayMs, level: cross.level },
      score: { on: score.on, step: score.step, voices: score.voices, low: score.low, octaves: score.octaves },
      arp: { mode: el.arpMode.value, rate: el.arpRate.value, octaves: el.arpOctaves.value },
      thresh: { watch: thresh.watch, level: thresh.level }, pluck: pluck.note,
      macros: macros.map((m) => ({ name: m.name, value: m.value })),
      morph: { a: encodeMorphEnd(morph.a, morphHome), b: encodeMorphEnd(morph.b, (id) => (morph.a ? morph.a[id] : morphHome(id))),
               pos: state.morphPos },
      photo: { on: photo.on, u: photo.u, v: photo.v },
      plane: { mirror: plane.mirror, limit: plane.limit, radius: plane.radius, os: plane.os, twist: plane.twist,
               kaleido: plane.kaleido, snap: plane.snap, scaleX: plane.scaleX, scaleY: plane.scaleY, shear: plane.shear },
      echo: { mix: echo.mix, ms: echo.ms, sync: echo.sync, feedback: echo.feedback, pingPong: echo.pingPong,
              chorus: echo.chorus, rate: echo.rate, depthMs: echo.depthMs, centreMs: echo.centreMs,
              chorusFeedback: echo.chorusFeedback },
    }));
  }
  return out;
}"""

# Every slider and menu: what a value written into it becomes is the browser's
# business, so the port carries each one's range, step and options.
CONTROLS = """() => {
  const out = { ranges: {}, selects: {} };
  for (const input of document.querySelectorAll('input[type="range"][id]')) {
    out.ranges[input.id] = { min: input.min, max: input.max, step: input.step, value: input.defaultValue };
  }
  for (const select of document.querySelectorAll('select[id]')) {
    out.selects[select.id] = { options: Array.from(select.options).map((o) => o.value), value: select.value };
  }
  return JSON.stringify(out);
}"""

def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto("file://" + os.path.abspath(PAGE))
        page.wait_for_timeout(700)
        if sys.argv[1] == "--controls":
            print(page.evaluate(CONTROLS))
        elif sys.argv[1] == "--presets":
            # Every preset the page ships, as the setup it loads: one JSON line each.
            for line in page.evaluate("""() => PRESETS.flatMap(([, entries]) => entries.map(([, setup]) => JSON.stringify(setup)))"""):
                print(line)
        elif sys.argv[1] == "--library":
            print(page.evaluate("() => JSON.stringify(PRESETS)"))
        elif sys.argv[1] == "--sources":
            # The sources the page has registered, with the reach `touchRoutings`
            # holds a stored depth to: the C++ runner registers stand-ins for them.
            print(page.evaluate("""() => JSON.stringify([...MOD_SOURCES.values()].map((s) =>
              ({ id: s.id, reach: s.reach > 0 ? s.reach : 0, varies: !!s.reachVaries })))"""))
        else:
            setups = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8") if line.strip()]
            for start in range(0, len(setups), 50):
                for line in page.evaluate(DUMP, setups[start:start + 50]):
                    print(line)
        browser.close()
        if errors:
            print("page errors: " + "; ".join(errors[:3]), file=sys.stderr)

main()
