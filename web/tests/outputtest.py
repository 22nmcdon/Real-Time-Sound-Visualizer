"""Level into the Generator, and a master Output (G7 of
web/docs/the-face-second-pass.md).

Level was the Picture section's corner knob from 7 to 11 Nov, where it read
as a master volume; it was always the generator's amplitude, each hand's. It
is in the Generator now, linked with it, and the corner has the Output: one
gain after everything, both hands', on what is heard and nothing else. What
this holds, each against the way it would fail:

- where they are: Level in the Generator on Play, the Output in the Picture
  section with the meter beside it, a knob with a host's gold dot and no
  modulation; Level following the Generator's link;
- the Output's law and its reading - the knob's fraction squared, 0 dB at
  the top, -6 at 71, -12 at 50, silent at nought - written to the generator;
- that it is no part of a setup: no setup names it, a preset and a code
  loaded leave it, undo never steps it (a real key on it, against the same
  key on Level, which does step), and the morph does not walk it;
- remembered by this browser, and the page still opening at unity when the
  browser refuses its storage;
- the one that matters most: turned down, what is heard is quieter and the
  picture is the same to the bit. Held on the instrument the page carries,
  compiled (makeWasmBrain), deterministically on this thread: two of it on
  one setup and one note, the Output at 50 in one - every picture lane the
  same, every heard sample a quarter once the glide has landed - and on the
  page's own generator (makeGeneratorCore), the same. Each with its null;
- on the site's instrument in its worklet, the Output this browser remembers
  is sent as it connects, and is what the instrument's state says;
- the meter beside it falls with it.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
PAGE = f"file://{ART}/scope.html"
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def opened(b, query="", settle=1500, init=None, context=None):
    # A context of its own unless one is given: pages of one context share this browser's storage.
    p = context.new_page() if context else b.new_page(viewport={"width": 1400, "height": 900})
    errors = []
    p.on("pageerror", lambda e: errors.append(str(e)))
    if init: p.add_init_script(init)
    p.goto(PAGE + query); p.wait_for_timeout(settle)
    p.evaluate("() => { if (el.helpDialog.open) el.helpDialog.close(); }")
    return p, errors

# Two of the compiled instrument on one setup and one note, the Output at 50
# in the second (or not, for the null), played block by block on this thread:
# every lane of each block, heard pair and picture.
INSTRUMENT = """async ([turned, blocks]) => {
  const code = encodeSetup(snapshot());
  const make = () => makeWasmBrain(wasmModule(), 48000, 128, code);
  const a = make(), b = make();
  // The limiter off (5a): it is last on the heard pair, 6 ms late and not
  // linear, and this holds what the instrument makes before it, to the sample.
  for (const x of [a, b]) x.control('limiter', '0');
  if (turned) b.slider('output', '50');
  const out = { picture: true, quarter: true, peakHeard: 0, peakPicture: 0, firstApart: -1, heardApart: 0 };
  for (const x of [a, b]) x.midi([0x90, 57, 100]);
  for (let k = 0; k < blocks; k++) {
    const run = (x) => {
      const hl = new Float32Array(128), hr = new Float32Array(128);
      const pics = [0, 1, 2, 3, 4, 5].map(() => new Float32Array(128));
      x.block(128, hl, hr, pics, null);
      return { heard: [hl, hr], pics };
    };
    const ra = run(a), rb = run(b);
    for (let c = 0; c < 6; c++) for (let i = 0; i < 128; i++) {
      if (ra.pics[c][i] !== rb.pics[c][i]) out.picture = false;
      out.peakPicture = Math.max(out.peakPicture, Math.abs(ra.pics[c][i]));
    }
    for (let c = 0; c < 2; c++) for (let i = 0; i < 128; i++) {
      const x = ra.heard[c][i], y = rb.heard[c][i];
      out.peakHeard = Math.max(out.peakHeard, Math.abs(x));
      if (x !== y && out.firstApart < 0) out.firstApart = k;
      out.heardApart = Math.max(out.heardApart, Math.abs(x - y));
      // Landed: a millionth of 0.75 is 13.5 time constants of 20 ms, 102 blocks.
      if (k >= 110 && y !== 0.25 * x) out.quarter = false;
    }
  }
  out.state = b.state();
  return out;
}"""

# The page's own generator, twice, the Output a quarter in one: its picture
# pair and B's against the other's, and its heard pair a quarter once landed.
GENERATOR = """([gain]) => {
  const lfosOf = () => [{ shape: 'sine', rate: 0.2, depth: 0.5, phase: 0, held: 0, value: 0 }, { shape: 'sine', rate: 0.5, depth: 0.3, phase: 0, held: 0, value: 0 }];
  const a = makeGeneratorCore(48000, GEN_SLOTS, lfosOf()), b = makeGeneratorCore(48000, GEN_SLOTS, lfosOf());
  for (const x of [a, b]) { x.set('shape', 'ramp'); x.set('delayMix', 0.4); x.set('delayMs', 30); x.strike(440, 0.8); }
  b.set('output', gain);
  const out = { picture: true, quarter: true, peak: 0 };
  for (let k = 0; k < 160; k++) {
    const pa = [0, 1, 2, 3, 4, 5].map(() => new Float32Array(128)), pb = [0, 1, 2, 3, 4, 5].map(() => new Float32Array(128));
    a.block(pa[0], pa[1], 128, pa[2], pa[3], pa[4], pa[5]);
    b.block(pb[0], pb[1], 128, pb[2], pb[3], pb[4], pb[5]);
    for (const c of [0, 1, 4, 5]) for (let i = 0; i < 128; i++) if (pa[c][i] !== pb[c][i]) out.picture = false;
    for (const c of [2, 3]) for (let i = 0; i < 128; i++) {
      out.peak = Math.max(out.peak, Math.abs(pa[c][i]));
      if (k >= 110 && pb[c][i] !== 0.25 * pa[c][i]) out.quarter = false;
    }
  }
  return out;
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    print("\n--- where they are ---")
    shared = b.new_context(viewport={"width": 1400, "height": 900})
    p, errors = opened(b, context=shared)
    where = p.evaluate("""() => {
      const home = (id) => { const e = el[id]; return e.closest('#toneRows') ? 'generator' : e.closest('#pictureBar') ? 'picture' : '?'; };
      const row = el.output.closest('.menu-row');
      return { amp: home('amp'), output: home('output'), ampTab: el.amp.closest('[data-tab]') && el.amp.closest('[data-tab]').dataset.tab,
               knob: row.classList.contains('knob-row'), host: row.classList.contains('host-param'),
               // The meter after the Output, past the Width since 12 Nov: it reads what is heard after both.
               dest: row.dataset.modDest || null, meterAfter: row.nextElementSibling === el.stereoWidth.closest('.menu-row')
                 && el.stereoWidth.closest('.menu-row').nextElementSibling === el.levelMeter,
               ampDest: el.amp.closest('.menu-row').dataset.modDest, gen: HAND_SECTIONS.gen.controls.includes('amp'),
               reading: el.outputValue.textContent, picture: HAND_SECTIONS.picture.controls.includes('output') };
    }""")
    check("Level is in the Generator on Play, the Output in the Picture section's corner",
          where["amp"] == "generator" and where["ampTab"] == "play" and where["output"] == "picture", str(where))
    check("null: the same reading of where a control lives tells them apart", where["amp"] != where["output"])
    check("the Output is a knob with the host's dot and the meter beside it, at 0 dB, and no modulation destination",
          where["knob"] and where["host"] and where["meterAfter"] and where["dest"] is None and where["reading"] == "0 dB", str(where))
    check("and Level keeps its destination and is one of the Generator's linked controls, the Output none of the Picture's",
          where["ampDest"] == "gen.amp" and where["gen"] and not where["picture"], str(where))
    # Level follows the Generator's link: linked, the upper hand's Level is
    # both hands'; unlinked, the upper hand's own. The null is the second.
    link = p.evaluate("""() => {
      const $ = (id) => document.getElementById(id);
      $('midiPoly').click(); $('midiLayers').value = 'split'; $('midiLayers').dispatchEvent(new Event('change'));
      $('editHandB').click();
      const amps = () => [genSettings().amp, genSettings(1).amp];
      el.amp.value = '30'; el.amp.dispatchEvent(new Event('input'));
      const linkedNow = amps();
      $('linkGen').click();
      el.amp.value = '90'; el.amp.dispatchEvent(new Event('input'));
      const own = amps();
      $('linkGen').click(); $('editHandA').click();
      $('midiLayers').value = 'off'; $('midiLayers').dispatchEvent(new Event('change'));
      return { linkedNow, own };
    }""")
    check("Level follows the Generator's link: linked, both hands; the upper hand's own, the upper alone",
          link["linkedNow"] == [0.3, 0.3] and link["own"] == [0.3, 0.9], str(link))

    print("\n--- its law and its reading ---")
    law = p.evaluate("""() => {
      const at = (v) => { el.output.value = String(v); el.output.dispatchEvent(new Event('input'));
                          return [el.outputValue.textContent, genSettings().output]; };
      const out = { 100: at(100), 71: at(71), 50: at(50), 1: at(1), 0: at(0) };
      at(100);
      return out;
    }""")
    check("the Output is the knob's fraction squared: 0 dB at the top, -6 at 71, -12 at 50, silent at nought",
          law["100"] == ["0 dB", 1] and law["71"][0] == "−5.9 dB" and abs(law["71"][1] - 0.5041) < 1e-12
          and law["50"] == ["−12 dB", 0.25] and law["1"][0] == "−80 dB" and law["0"] == ["silent", 0], str(law))
    check("null: a straight line would have put 50 at a half", law["50"][1] != 0.5)

    print("\n--- no part of a setup ---")
    setup = p.evaluate("""() => {
      el.output.value = '50'; el.output.dispatchEvent(new Event('input'));
      const snap = snapshot();
      const code = encodeSetup(snap);
      const named = 'output' in snap || 'output' in SETUP_FIELDS;
      // A preset that names a level, and a code: neither moves the Output; the preset moves Level, the null.
      const loud = PRESETS.flatMap(([, entries]) => entries).find(([, s]) => s.amp !== undefined);
      el.amp.value = '100'; el.amp.dispatchEvent(new Event('input'));
      restore(loud[1]);
      const afterPreset = [el.output.value, genSettings().output, el.amp.value];
      loadCode(encodeSetup(Object.assign({}, snap, { freq: 330 })));
      const afterCode = [el.output.value, genSettings().output];
      return { named, inCode: JSON.stringify(decodeSetup(code)).includes('"output"'), afterPreset, afterCode, presetAmp: loud[1].amp };
    }""")
    check("no setup names the Output: not the snapshot, not the table of fields, not a code",
          not setup["named"] and not setup["inCode"], str(setup))
    check("and a preset and a code loaded leave it where it was put, at 50",
          setup["afterPreset"][:2] == ["50", 0.25] and setup["afterCode"] == ["50", 0.25], str(setup))
    check("null: the same preset moves Level, which is the setup's", setup["afterPreset"][2] == str(setup["presetAmp"]), str(setup))
    morph = p.evaluate("() => ({ output: MORPH_IDS.includes('output'), amp: MORPH_IDS.includes('amp') })")
    check("the morph does not walk the Output, and does walk Level (the null)", not morph["output"] and morph["amp"], str(morph))
    # Undo: a real key on the Output, held still past the 400 ms, is no step;
    # the same key on Level is one.
    p.evaluate("() => { setBenchTab('play'); undoHistory.undo.length = 0; undoHistory.redo.length = 0; }")
    p.wait_for_timeout(600)
    def steps_after(selector):
        before = p.evaluate("() => undoHistory.undo.length")
        p.focus(selector); p.keyboard.press("ArrowLeft"); p.keyboard.press("ArrowLeft")
        p.wait_for_timeout(900)
        return p.evaluate("() => undoHistory.undo.length") - before
    out_steps, out_moved = steps_after("#output"), p.evaluate("() => el.output.value")
    amp_steps = steps_after("#amp")
    check("undo never steps the Output: a real key on it, held still, is no step", out_steps == 0 and out_moved == "48",
          "%d steps, at %s" % (out_steps, out_moved))
    check("null: the same key on Level is a step", amp_steps == 1, "%d steps" % amp_steps)

    print("\n--- remembered by this browser ---")
    stored = p.evaluate("() => localStorage.getItem('scope.output')")
    p.close()
    p2, errors2 = opened(b, context=shared)
    back = p2.evaluate("() => [el.output.value, el.outputValue.textContent, genSettings().output]")
    p2.evaluate("() => { el.output.value = '100'; el.output.dispatchEvent(new Event('input')); }")
    cleared = p2.evaluate("() => localStorage.getItem('scope.output')")
    check("this browser remembers the Output: written as it moves, and the page opens at it",
          stored == "48" and back == ["48", "−13 dB", 0.48 * 0.48], "%r, %r" % (stored, back))
    check("and at unity it keeps nothing", cleared is None, repr(cleared))
    p2.close()
    shared.close()
    # Storage refused outright: the page opens, at unity, with no error.
    p3, errors3 = opened(b, init="Object.defineProperty(window, 'localStorage', { get() { throw new Error('refused'); } });")
    refused = p3.evaluate("() => { el.output.value = '30'; el.output.dispatchEvent(new Event('input')); return [el.outputValue.textContent, genSettings().output]; }")
    check("with the browser's storage refused the page opens and the Output still works, unremembered",
          not errors3 and refused[1] == 0.09, "%r; %s" % (refused, errors3[:2]))
    p3.close()

    print("\n--- what is heard, and the picture ---")
    p, errors = opened(b, "?picture=0")
    inst = p.evaluate(INSTRUMENT, [True, 140])
    null = p.evaluate(INSTRUMENT, [False, 140])
    print("    %s" % {k: v for k, v in inst.items() if k != "state"})
    check("the compiled instrument the page carries, the Output at 50: every picture lane the same to the bit",
          inst["picture"] and inst["peakPicture"] > 0.05, str(inst["peakPicture"]))
    check("and what it hears a quarter, to the bit, once landed, apart from the first block it was set in",
          inst["quarter"] and inst["firstApart"] == 0 and inst["peakHeard"] > 0.05 and inst["heardApart"] > 0.05, str(inst))
    check("null: at unity in both, nothing heard is a quarter of the other",
          null["picture"] and not null["quarter"] and null["heardApart"] == 0, str({k: v for k, v in null.items() if k != "state"}))
    gen = p.evaluate(GENERATOR, [0.25])
    gnull = p.evaluate(GENERATOR, [1])
    check("the page's own generator: the picture pair and B's the same to the bit, the heard pair a quarter",
          gen["picture"] and gen["quarter"] and gen["peak"] > 0.05, str(gen))
    check("null: at unity it is not a quarter", gnull["picture"] and not gnull["quarter"], str(gnull))
    # The meter: what is heard, as the screen's signal at the Output's gain.
    meter = p.evaluate("""() => {
      const read = (v) => { el.output.value = String(v); el.output.dispatchEvent(new Event('input'));
                            envLive = ENV_FULL / 2; paintStage(); return Number(el.levelMeter.style.getPropertyValue('--v')); };
      const out = [read(100), read(50)];
      read(100);
      return out;
    }""")
    check("the meter beside it falls with it: half at unity, an eighth at 50", meter == [0.5, 0.125], str(meter))
    check("no page errors", not errors, "; ".join(errors[:3]))
    p.close()

    print("\n--- the site's instrument ---")
    # The instrument in its worklet, given the Output this browser remembers as the page connects.
    p, errors = opened(b, init="localStorage.setItem('scope.output', '50');", settle=3000)
    site = p.evaluate("""async () => {
      await new Promise((r) => setTimeout(r, 500));
      const s = await scopeHost.call('scopeState');
      const setup = decodeSetup(s.code);
      return { kind: state.source.kind, on: hostSync.on, output: setup && setup.pluginOutput, knob: el.output.value };
    }""")
    check("on the site the instrument is told the Output this browser remembers, and its state says so",
          site["kind"] == "host" and site["on"] and site["output"] == 50 and site["knob"] == "50", str(site))
    p.close()
    p, errors = opened(b, settle=3000)
    plain = p.evaluate("""async () => { const s = await scopeHost.call('scopeState'); const setup = decodeSetup(s.code);
      return { output: setup && setup.pluginOutput, knob: el.output.value }; }""")
    check("null: a browser that remembers none leaves the instrument at unity, saying nothing", plain["output"] is None and plain["knob"] == "100", str(plain))
    check("no page errors on the site", not errors, "; ".join(errors[:3]))
    p.close()
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
