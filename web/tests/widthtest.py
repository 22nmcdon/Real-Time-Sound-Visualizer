"""The master Width (12 Nov), beside the Output in the Picture section.

The owner heard the tine piano go to one ear as a note was let go. The cause
was the Key (keyHeard, and its own section below): a velocity routed to FM
went to nought the moment the key was up, so three-quarters of the release
sounded as a bare sine, and the quarter turn puts a lone note's right channel
a quarter-period late, which on a sine alone is heard in one ear. The Width is
the listening control on top of that fix, not a cover for it: how wide you
hear, nought (both ears the middle) to a hundred (the pair as it is). What
this holds, each against the way it would fail, after the Output's own test:

- where it is: the Picture section, after the Output and before the meter, a
  knob with a host's gold dot and no modulation, no hand's;
- its law and reading - the knob's fraction, a straight line, "mono" at
  nought - written to the generator;
- that it is no part of a setup: no setup names it, a preset and a code
  loaded leave it, undo never steps it (a real key on it, against the same
  key on Level, which does step), and the morph does not walk it;
- remembered by this browser, and the page still opening at a hundred when
  the browser refuses its storage;
- what is heard and the picture, on the compiled instrument the page carries
  and on the core's generator through the bridge (compiled_core.js; the
  page's own until stage 5's step 6), played deterministically on this thread.
  Since 16 Nov the Width is each note's own (web/docs/both-ears.md): a note's
  left behind its right by the Width's fraction of a quarter of its cycle. So
  on a lone sine: at nought the heard pair is one channel twice, to the bit,
  once the glide has landed, and not in the block it was set in (no step); at
  fifty its side is sin(pi/8) / sin(pi/4), 0.541, of the side at a hundred,
  and each ear as loud as at a hundred - where the Width as it was, the pair's
  side scaled, made it 0.5 (the null); at a hundred the heard pair is the
  drawn pair; and every picture lane the same to the bit whatever it is.
  Each with its null (ears.py in the core's pieces holds the rest: every note
  of a chord in both ears, steady as notes come and go);
- on the site's instrument in its worklet, the Width this browser remembers
  is sent as it connects, and is what the instrument's state says;
- the Key: held through a note's release while the Envelope is above nought
  and nought after, on both brains, so the tine piano's bark rings out.
"""
import math, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
# The compiled core's generator, rendered in the page (stage 5, step 6): compiled_core.js.
COMPILED_CORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compiled_core.js")
ART = os.path.dirname(HERE)
PAGE = f"file://{ART}/scope.html"
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def opened(b, query="", settle=1500, init=None, context=None):
    p = context.new_page() if context else b.new_page(viewport={"width": 1400, "height": 900})
    errors = []
    p.on("pageerror", lambda e: errors.append(str(e)))
    if init: p.add_init_script(init)
    p.add_init_script(path=COMPILED_CORE)
    p.goto(PAGE + query); p.wait_for_timeout(settle)
    p.evaluate("() => { if (el.helpDialog.open) el.helpDialog.close(); }")
    return p, errors

# Two of the compiled instrument on the base (a still sine, poly, the quarter
# turn: a lone note is a stereo pair, its right a quarter-period late) and one
# note, the Width at `width` in the second from the first block, played block
# by block on this thread. The first is never touched: its heard pair is
# compared with its own picture lanes, which at a hundred it must equal.
INSTRUMENT = """async ([width, blocks]) => {
  const code = encodeSetup(Object.assign({}, snapshot(), BASE_SETUP));
  const make = () => makeWasmBrain(wasmModule(), 48000, 128, code);
  const a = make(), b = make();
  // The limiter off (5a): it is last on the heard pair, 6 ms late and not
  // linear, and this holds what the instrument makes before it, to the sample.
  for (const x of [a, b]) x.control('limiter', '0');
  // The first at a hundred, where its heard pair is its picture lanes; since 17 Nov the default is fifty.
  a.slider('stereoWidth', '100');
  b.slider('stereoWidth', width !== null ? String(width) : '100');
  const out = { picture: true, landedMono: true, firstBlockMono: true, asDrawn: 0, bAsDrawn: 0,
                firstRatio: null, peak: 0, sideA: 0, sides: [0, 0], ears: [0, 0, 0, 0] };
  for (const x of [a, b]) x.midi([0x90, 57, 100]);
  for (let k = 0; k < blocks; k++) {
    const run = (x) => {
      const hl = new Float32Array(128), hr = new Float32Array(128);
      const pics = [0, 1, 2, 3, 4, 5].map(() => new Float32Array(128));
      x.block(128, hl, hr, pics, null);
      return { hl, hr, pics };
    };
    const ra = run(a), rb = run(b);
    for (let c = 0; c < 6; c++) for (let i = 0; i < 128; i++) if (ra.pics[c][i] !== rb.pics[c][i]) out.picture = false;
    let sa2 = 0, sb2 = 0;
    for (let i = 0; i < 128; i++) {
      out.peak = Math.max(out.peak, Math.abs(ra.hl[i]));
      out.sideA = Math.max(out.sideA, Math.abs(ra.hl[i] - ra.hr[i]));
      // Once the drawn turn has glided in (4 ms, to a millionth well before) and the Width landed.
      if (k >= 110) out.asDrawn = Math.max(out.asDrawn, Math.abs(ra.hl[i] - ra.pics[0][i]), Math.abs(ra.hr[i] - ra.pics[1][i]));
      if (k >= 110) out.bAsDrawn = Math.max(out.bAsDrawn, Math.abs(rb.hl[i] - rb.pics[0][i]), Math.abs(rb.hr[i] - rb.pics[1][i]));
      if (k === 0 && rb.hl[i] !== rb.hr[i]) out.firstBlockMono = false;
      // Landed: a millionth of one is 13.8 time constants of 20 ms, 104 blocks.
      if (k >= 110 && rb.hl[i] !== rb.hr[i]) out.landedMono = false;
      const sa = ra.hl[i] - ra.hr[i], sb = rb.hl[i] - rb.hr[i];
      sa2 += sa * sa; sb2 += sb * sb;
      if (k >= 110) {
        out.sides[0] += sa * sa; out.sides[1] += sb * sb;
        out.ears[0] += ra.hl[i] ** 2; out.ears[1] += rb.hl[i] ** 2; out.ears[2] += ra.hr[i] ** 2; out.ears[3] += rb.hr[i] ** 2;
      }
    }
    // The side against the untouched one's, a block's power at a time.
    if (k === 1) out.firstRatio = Math.sqrt(sb2 / sa2);
  }
  out.state = b.state();
  out.ratio = Math.sqrt(out.sides[1] / out.sides[0]);
  out.earsDb = [10 * Math.log10(out.ears[1] / out.ears[0]), 10 * Math.log10(out.ears[3] / out.ears[2])];
  return out;
}"""

# The core's generator, compiled (compiled_core.js; the page's own until stage
# 5's step 6), twice, the Width at `w` in one: a ramp through the
# delay, the dyad's pair (its right a quarter-cycle on), so the pair is stereo.
# Since 16 Nov a dyad's lone note is heard with its left the drawn left and its
# right turned by the Width's fraction of the Phase; the delay, after, mixes
# the two (its repeats on the diagonal), so what is read is the pair whole.
GENERATOR = """([w]) => {
  const lfosOf = () => [{ shape: 'sine', rate: 0.2, depth: 0.5, phase: 0, held: 0, value: 0 }, { shape: 'sine', rate: 0.5, depth: 0.3, phase: 0, held: 0, value: 0 }];
  const a = compiledGenerator(48000, GEN_SLOTS, lfosOf()), b = compiledGenerator(48000, GEN_SLOTS, lfosOf());
  // The delay's repeats on the diagonal (its own Width at nought): a module's spread is its own, after a note's.
  for (const x of [a, b]) { x.set('shape', 'ramp'); x.set('phase', Math.PI / 2); x.set('delayMix', 0.4); x.set('delayMs', 30); x.set('delayWidth', 0); }
  // The first at one, the pair as it is (the default is a half since 17 Nov).
  a.set('stereoWidth', 1);
  b.set('stereoWidth', w);
  const out = { picture: true, mono: true, asDrawn: true, side: 0, firstMono: true, left: true, right: false };
  for (let k = 0; k < 160; k++) {
    const pa = [0, 1, 2, 3, 4, 5].map(() => new Float32Array(128)), pb = [0, 1, 2, 3, 4, 5].map(() => new Float32Array(128));
    a.block(pa[0], pa[1], 128, pa[2], pa[3], pa[4], pa[5]);
    b.block(pb[0], pb[1], 128, pb[2], pb[3], pb[4], pb[5]);
    for (const c of [0, 1, 4, 5]) for (let i = 0; i < 128; i++) if (pa[c][i] !== pb[c][i]) out.picture = false;
    for (let i = 0; i < 128; i++) {
      // At one the heard pair is the lanes (one layer, no score, the Output at unity).
      if (pb[2][i] !== pb[0][i] || pb[3][i] !== pb[1][i]) out.asDrawn = false;
      out.side = Math.max(out.side, Math.abs(pa[2][i] - pa[3][i]));
      if (k >= 110 && pb[2][i] !== pb[3][i]) out.mono = false;
      if (k === 0 && pb[2][i] !== pb[3][i]) out.firstMono = false;
      if (pa[2][i] !== pb[2][i]) out.left = false;
      if (pa[3][i] !== pb[3][i]) out.right = true;
    }
  }
  return out;
}"""

# The Key through a note's release, on a brain: the tine piano's routing of
# it alone onto FM, a key struck and let go, and the Key's value read off the
# matrix's source as the release rings and after it has died away.
KEY_PAGE = """async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const tine = PRESETS.flatMap(([, e]) => e).find(([, s]) => (s.mod || '').includes('midi.key>gen.fm'));
  restore(Object.assign({}, tine[1], { rel: 600 }));
  midiRegisterKey();
  const key = () => MOD_SOURCES.get('midi.key').value();
  midiNoteOn(57, 100);
  await wait(300);
  const held = key();
  midiNoteOff(57);
  await wait(120);
  const ringing = [key(), midi.key, MOD_SOURCES.get('env.note').value()];
  await wait(1500);
  const after = [key(), MOD_SOURCES.get('env.note').value()];
  return { held, ringing, after };
}"""

# The heard pair's side against its middle through the release, as the
# speakers get it: the site's instrument in its worklet, tapped after the
# monitor chain's clamp. The tine piano, with the Key alone on FM or nothing
# routed, a key held for a second and let go; side over middle in decibels,
# over the last 100 ms held and the first 100 ms of the release (500 ms).
# Real time, so the suite is serial. (A bare compiled brain on this thread
# cannot show it: with no frames, Scan reads no picture, and the tine piano's
# bark is half its wave read off its own figure.)
KEY_HEARD = """async ([routed]) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const tine = PRESETS.flatMap(([, e]) => e).find(([, s]) => (s.mod || '').includes('midi.key>gen.fm'));
  restore(Object.assign({}, tine[1], { mod: routed ? 'midi.key>gen.fm@0.300' : '' }));
  // At a hundred, where the bark's width was measured; the default is fifty since 17 Nov.
  el.stereoWidth.value = '100'; el.stereoWidth.dispatchEvent(new Event('input'));
  midiNoteOn(57, 100);
  await applyGeneratorSound();
  const chain = Array.from(monitorChains)[0];
  const ctx = chain.input.context;
  const sp = ctx.createScriptProcessor(1024, 2, 2);
  const L = [], R = [];
  sp.onaudioprocess = (e) => { L.push(...e.inputBuffer.getChannelData(0)); R.push(...e.inputBuffer.getChannelData(1)); };
  chain.clamp.connect(sp); sp.connect(ctx.destination);
  await wait(1000);
  const mark = L.length;
  midiNoteOff(57);
  await wait(400);
  sp.disconnect();
  const w = Math.round(ctx.sampleRate / 10);
  const ratio = (from) => { let m = 0, s = 0;
    for (let i = from; i < from + w; i++) { m += ((L[i] + R[i]) / 2) ** 2; s += ((L[i] - R[i]) / 2) ** 2; }
    return 10 * Math.log10(s / m); };
  return { held: ratio(mark - w), released: ratio(mark + Math.round(w / 2)), audio: L.length > mark + 2 * w };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    print("\n--- where it is ---")
    shared = b.new_context(viewport={"width": 1400, "height": 900})
    p, errors = opened(b, context=shared)
    where = p.evaluate("""() => {
      const row = el.stereoWidth.closest('.menu-row');
      return { picture: !!row.closest('#pictureBar'), afterOutput: el.output.closest('.menu-row').nextElementSibling === row,
               // Past the sound's own Width and the switch since 16 Nov, the Width's own cells.
               meterAfter: (() => { const ids = []; let n = el.stereoWidth.closest('.menu-row').nextElementSibling;
                 while (n && n !== el.levelMeter) { ids.push(n.id); n = n.nextElementSibling; }
                 return n === el.levelMeter && ids.join() === 'soundWidthRow,widthToRow'; })(), knob: row.classList.contains('knob-row'),
               host: row.classList.contains('host-param'), dest: row.dataset.modDest || null,
               hand: Object.values(HAND_SECTIONS).some((s) => s.controls.includes('stereoWidth')),
               reading: el.stereoWidthValue.textContent, ampPicture: !!el.amp.closest('#pictureBar') };
    }""")
    check("the Width is in the Picture section, after the Output and before the meter",
          where["picture"] and where["afterOutput"] and where["meterAfter"], str(where))
    check("null: Level, read the same way, is not in the Picture section", not where["ampPicture"])
    check("a knob with the host's dot, at 50% (the owner's default since 17 Nov), no modulation destination and no hand's",
          where["knob"] and where["host"] and where["dest"] is None and not where["hand"] and where["reading"] == "50%", str(where))

    print("\n--- its law and its reading ---")
    law = p.evaluate("""() => {
      const at = (v) => { el.stereoWidth.value = String(v); el.stereoWidth.dispatchEvent(new Event('input'));
                          return [el.stereoWidthValue.textContent, genSettings().stereoWidth]; };
      const out = { 100: at(100), 50: at(50), 1: at(1), 0: at(0) };
      at(100);
      return out;
    }""")
    check("the Width is the knob's fraction: 100% at the top, a half at 50, mono at nought",
          law["100"] == ["100%", 1] and law["50"] == ["50%", 0.5] and law["1"] == ["1%", 0.01] and law["0"] == ["mono", 0], str(law))
    check("null: the Output's law would have put 50 at a quarter", law["50"][1] != 0.25)

    print("\n--- no part of a setup ---")
    setup = p.evaluate("""() => {
      el.stereoWidth.value = '30'; el.stereoWidth.dispatchEvent(new Event('input'));
      const snap = snapshot();
      const code = encodeSetup(snap);
      const named = 'stereoWidth' in snap || 'stereoWidth' in SETUP_FIELDS;
      const loud = PRESETS.flatMap(([, entries]) => entries).find(([, s]) => s.amp !== undefined);
      el.amp.value = '100'; el.amp.dispatchEvent(new Event('input'));
      restore(loud[1]);
      const afterPreset = [el.stereoWidth.value, genSettings().stereoWidth, el.amp.value];
      loadCode(encodeSetup(Object.assign({}, snap, { freq: 330 })));
      const afterCode = [el.stereoWidth.value, genSettings().stereoWidth];
      el.presetNew.click();
      const afterNew = [el.stereoWidth.value, genSettings().stereoWidth];
      return { named, inCode: JSON.stringify(decodeSetup(code)).includes('stereoWidth'), afterPreset, afterCode, afterNew, presetAmp: loud[1].amp };
    }""")
    check("no setup names the Width: not the snapshot, not the table of fields, not a code",
          not setup["named"] and not setup["inCode"], str(setup))
    check("and a preset, a code and New leave it where it was put, at 30",
          setup["afterPreset"][:2] == ["30", 0.3] and setup["afterCode"] == ["30", 0.3] and setup["afterNew"] == ["30", 0.3], str(setup))
    check("null: the same preset moves Level, which is the setup's", setup["afterPreset"][2] == str(setup["presetAmp"]), str(setup))
    morph = p.evaluate("() => ({ width: MORPH_IDS.includes('stereoWidth'), amp: MORPH_IDS.includes('amp') })")
    check("the morph does not walk the Width, and does walk Level (the null)", not morph["width"] and morph["amp"], str(morph))
    p.evaluate("() => { setBenchTab('play'); setFigSub('wave'); undoHistory.undo.length = 0; undoHistory.redo.length = 0; }")
    p.wait_for_timeout(600)
    def steps_after(selector):
        before = p.evaluate("() => undoHistory.undo.length")
        p.focus(selector); p.keyboard.press("ArrowLeft"); p.keyboard.press("ArrowLeft")
        p.wait_for_timeout(900)
        return p.evaluate("() => undoHistory.undo.length") - before
    w_steps, w_moved = steps_after("#stereoWidth"), p.evaluate("() => el.stereoWidth.value")
    amp_steps = steps_after("#amp")
    check("undo never steps the Width: a real key on it, held still, is no step", w_steps == 0 and w_moved == "28",
          "%d steps, at %s" % (w_steps, w_moved))
    check("null: the same key on Level is a step", amp_steps == 1, "%d steps" % amp_steps)

    print("\n--- remembered by this browser ---")
    stored = p.evaluate("() => localStorage.getItem('scope.width')")
    p.close()
    p2, errors2 = opened(b, context=shared)
    back = p2.evaluate("() => [el.stereoWidth.value, el.stereoWidthValue.textContent, genSettings().stereoWidth]")
    p2.evaluate("() => { el.stereoWidth.value = '50'; el.stereoWidth.dispatchEvent(new Event('input')); }")
    cleared = p2.evaluate("() => localStorage.getItem('scope.width')")
    check("this browser remembers the Width: written as it moves, and the page opens at it",
          stored == "28" and back == ["28", "28%", 0.28], "%r, %r" % (stored, back))
    check("and at its default, fifty, it keeps nothing", cleared is None, repr(cleared))
    check("no page errors", not errors and not errors2, "; ".join((errors + errors2)[:3]))
    p2.close()
    shared.close()
    p3, errors3 = opened(b, init="Object.defineProperty(window, 'localStorage', { get() { throw new Error('refused'); } });")
    refused = p3.evaluate("() => { const at = el.stereoWidth.value; el.stereoWidth.value = '40'; el.stereoWidth.dispatchEvent(new Event('input')); return [at, el.stereoWidthValue.textContent, genSettings().stereoWidth]; }")
    check("with the browser's storage refused the page opens at its default, fifty, and the Width still works, unremembered",
          not errors3 and refused == ["50", "40%", 0.4], "%r; %s" % (refused, errors3[:2]))
    p3.close()

    print("\n--- what is heard, and the picture ---")
    p, errors = opened(b, "?picture=0")
    mono = p.evaluate(INSTRUMENT, [0, 140])
    half = p.evaluate(INSTRUMENT, [50, 140])
    null = p.evaluate(INSTRUMENT, [None, 140])
    print("    %s" % {k: v for k, v in mono.items() if k not in ("state", "ears", "sides")})
    check("the compiled instrument at Width nought: every picture lane the same to the bit as at a hundred",
          mono["picture"] and mono["peak"] > 0.05, str(mono["peak"]))
    check("and what it hears one channel twice, to the bit, once landed", mono["landedMono"] and mono["sideA"] > 0.05, str(mono["sideA"]))
    check("glided, not stepped: the block it was set in is not mono, and the next still has most of its side",
          not mono["firstBlockMono"] and mono["firstRatio"] is not None and 0.5 < mono["firstRatio"] < 1, str(mono["firstRatio"]))
    check("null: at a hundred in both, the pair is never mono", not null["landedMono"] and null["picture"], str(null["landedMono"]))
    want = math.sin(math.pi / 8) / math.sin(math.pi / 4)
    check("at fifty the note's side is sin(pi/8) / sin(pi/4) of the untouched one's, an eighth of its cycle, the picture still the same",
          half["picture"] and abs(half["ratio"] - want) < 0.005 and not half["landedMono"], "%.4f, want %.4f" % (half["ratio"], want))
    check("null: the Width as it was, the side scaled, would have made it a half", abs(want - 0.5) > 0.03 and abs(half["ratio"] - 0.5) > 0.03,
          "%.4f" % half["ratio"])
    check("and each ear as loud as at a hundred, within 0.05 dB: the note is turned, not narrowed",
          all(abs(d) < 0.05 for d in half["earsDb"]) and all(abs(d) < 0.05 for d in mono["earsDb"]),
          "fifty %s, nought %s" % (half["earsDb"], mono["earsDb"]))
    check("at a hundred the heard pair is the drawn pair, once the drawn turn has glided in, within a millionth",
          null["asDrawn"] < 1e-6 and null["bAsDrawn"] < 1e-6, "%.2g, %.2g" % (null["asDrawn"], null["bAsDrawn"]))
    check("null: at fifty it is not", half["bAsDrawn"] > 0.01, "%.3f" % half["bAsDrawn"])
    states = p.evaluate("""([a, b]) => [typeof a, decodeSetup(typeof a === 'string' ? a : a.code).pluginWidth, decodeSetup(typeof b === 'string' ? b : b.code).pluginWidth]""", [null["state"], half["state"]])
    check("the instrument's state: no pluginWidth at fifty, its default, and 100 at a hundred", states[1] == 100 and states[2] is None, str(states))
    gen = p.evaluate(GENERATOR, [0])
    ghalf = p.evaluate(GENERATOR, [0.5])
    gnull = p.evaluate(GENERATOR, [1])
    check("the compiled generator: the picture pair and B's the same to the bit, the heard pair mono at nought",
          gen["picture"] and gen["mono"] and gen["side"] > 0.05, str(gen))
    check("glided there, not stepped: its first block is not mono", not gen["firstMono"], str(gen))
    check("and at fifty a dyad's lone note is turned, neither mono nor the lanes, the picture the same",
          ghalf["picture"] and ghalf["right"] and not ghalf["mono"] and not ghalf["asDrawn"], str(ghalf))
    check("null: at one it is not mono, and is the lanes to the bit", gnull["picture"] and not gnull["mono"] and gnull["asDrawn"], str(gnull))
    check("null: at nought the heard pair is not the lanes", not gen["asDrawn"], str(gen))
    check("no page errors", not errors, "; ".join(errors[:3]))
    p.close()

    print("\n--- the Key rings out with its note ---")
    p, errors = opened(b)
    key = p.evaluate(KEY_PAGE)
    print("    %s" % key)
    check("on the page, the Key holds the struck velocity through the release, while the Envelope is above nought",
          key["held"] > 0.7 and key["ringing"][0] == key["held"] and key["ringing"][1] == 0 and key["ringing"][2] > 0, str(key))
    check("null: the gate it is read from is nought by then", key["ringing"][1] == 0, str(key))
    check("and nought once the note has died away", key["after"] == [0, 0], str(key))
    p.close()
    p, errors = opened(b)
    heard = p.evaluate(KEY_HEARD, [True])
    p.close()
    p, errors2 = opened(b)
    plain = p.evaluate(KEY_HEARD, [False])
    errors += errors2
    print("    side over middle, held and just released: Key on FM %s, no routing %s" % (heard, plain))
    check("at the speakers the tine piano's width rings out: side over middle within 2 dB of where it was held",
          heard["audio"] and heard["held"] > 3 and abs(heard["held"] - heard["released"]) < 2, str(heard))
    check("null: without the routing the held sound was never that wide (so the check can see the bark)",
          abs(plain["held"]) < 3, str(plain))
    check("no page errors", not errors, "; ".join(errors[:3]))
    p.close()

    print("\n--- what the Width applies to, and the sound's own Width (16 Nov) ---")
    p, errors = opened(b)
    sw = p.evaluate("""() => {
      const out = {};
      el.stereoWidth.value = '70'; el.stereoWidth.dispatchEvent(new Event('input'));
      out.start = [el.stereoWidthRow.hidden, el.soundWidthRow.hidden, genSettings().widthDrawn, snapshot().widthDrawn];
      el.widthDrawn.click();
      el.soundWidth.value = '30'; el.soundWidth.dispatchEvent(new Event('input'));
      const snap = snapshot();
      out.drawn = [el.stereoWidthRow.hidden, el.soundWidthRow.hidden, genSettings().widthDrawn, genSettings().drawnWidth,
                   snap.widthDrawn, snap.soundWidth, el.stereoWidth.value, genSettings().stereoWidth];
      const code = encodeSetup(snap);
      out.decoded = (({ widthDrawn, soundWidth }) => ({ widthDrawn, soundWidth }))(decodeSetup(code));
      out.ring = getComputedStyle(el.soundWidthRow.querySelector('.menu-label'), '::before').borderTopWidth;
      out.boxDrawn = el.widthDraw.checked;
      el.presetNew.click();
      out.afterNew = [genSettings().widthDrawn, el.soundWidth.value, el.stereoWidth.value, el.soundWidthRow.hidden];
      out.boxNew = el.widthDraw.checked;
      loadCode(code);
      out.loaded = [genSettings().widthDrawn, genSettings().drawnWidth, el.soundWidth.value, el.soundWidthRow.hidden, el.stereoWidth.value];
      out.boxLoaded = el.widthDraw.checked;
      out.morph = MORPH_IDS.includes('soundWidth');
      return out;
    }""")
    print("    %s" % sw)
    check("the switch on Drawn too puts the sound's Width in the Width's place, with the sound's ring, and the generator draws the heard mix at it",
          sw["start"] == [False, True, False, False] and sw["drawn"][:4] == [True, False, True, 0.3] and sw["ring"] == "1px", str(sw))
    check("and the setup names both: the switch and the sound's Width, in the snapshot and in its code",
          sw["drawn"][4:6] == [True, 30] and sw["decoded"] == {"widthDrawn": True, "soundWidth": 30}, str(sw["decoded"]))
    check("a code made Drawn too loads Drawn too at its own Width; New goes back to Heard and fifty, the default",
          sw["loaded"][:4] == [True, 0.3, "30", False] and sw["afterNew"][:2] == [False, "50"], str((sw["loaded"], sw["afterNew"])))
    check("and the morph walks the sound's Width, which is the setup's", sw["morph"], str(sw["morph"]))
    # The face's one control since the UI review (20 Nov), Draw width, follows the value however it is set.
    check("Draw width is ticked while the Width is drawn too - by the switch and by a loaded code - and not after New",
          sw["boxDrawn"] is True and sw["boxLoaded"] is True and sw["boxNew"] is False, str(sw))
    check("null: the box after New is not the box after a load, so the check can tell them apart", sw["boxNew"] != sw["boxLoaded"])
    check("null: the player's Width is none of it - 70 through the switch, the code, New and the load",
          sw["drawn"][6:] == ["70", 0.7] and sw["afterNew"][2] == "70" and sw["loaded"][4] == "70", str(sw))
    p.evaluate("() => { el.presetNew.click(); setBenchTab('play'); undoHistory.undo.length = 0; undoHistory.redo.length = 0; }")
    p.wait_for_timeout(600)
    before = p.evaluate("() => undoHistory.undo.length")
    # By the face's own control, with the real mouse: the checkbox clicks the kept button the instrument hears.
    p.evaluate("() => { window.__clicked = []; for (const id of ['widthHeard', 'widthDrawn']) el[id].addEventListener('click', () => __clicked.push(id)); }")
    p.click("#widthToRow label.check-switch"); p.wait_for_timeout(900)
    stepped = p.evaluate("() => [undoHistory.undo.length, genSettings().widthDrawn, el.widthDrawn.getAttribute('aria-checked'), el.widthDraw.checked]")
    p.keyboard.press("Control+z"); p.wait_for_timeout(500)
    undone = p.evaluate("() => [genSettings().widthDrawn, el.soundWidthRow.hidden, el.widthDraw.checked]")
    check("undo steps Draw width, as a part of the sound: one step, and undone it is back on only heard, the box unticked",
          stepped == [before + 1, True, "true", True] and undone == [False, True, False], "%s, %s" % (stepped, undone))
    p.evaluate("() => { __clicked.length = 0; }")
    p.click("#widthToRow label.check-switch"); p.wait_for_timeout(300)
    p.click("#widthToRow label.check-switch"); p.wait_for_timeout(300)
    clicked = p.evaluate("() => [__clicked, genSettings().widthDrawn]")
    check("ticked and unticked by hand, it clicks Drawn too and then Heard, the buttons the plugin's core hears",
          clicked == [["widthDrawn", "widthHeard"], False], str(clicked))
    check("null: the order of the clicks is read, not only that there were two", clicked[0] != ["widthHeard", "widthDrawn"], str(clicked))
    check("no page errors", not errors, "; ".join(errors[:3]))
    p.close()
    # The compiled instrument the page carries, given a code made Drawn too: what it hears is what it draws.
    p, errors = opened(b, "?picture=0")
    inst = p.evaluate("""() => {
      const run = (fields) => {
        const code = encodeSetup(Object.assign({}, snapshot(), BASE_SETUP, fields));
        const x = makeWasmBrain(wasmModule(), 48000, 128, code);
        x.control('limiter', '0');
        x.midi([0x90, 57, 100]); x.midi([0x90, 64, 100]);
        let worst = 0, size = 0;
        for (let k = 0; k < 60; k++) {
          const hl = new Float32Array(128), hr = new Float32Array(128);
          const pics = [0, 1, 2, 3, 4, 5].map(() => new Float32Array(128));
          x.block(128, hl, hr, pics, null);
          for (let i = 0; i < 128; i++) { worst = Math.max(worst, Math.abs(hl[i] - pics[0][i]), Math.abs(hr[i] - pics[1][i])); size = Math.max(size, Math.abs(pics[0][i])); }
        }
        return [worst, size];
      };
      return { drawn: run({ widthDrawn: true, soundWidth: 40 }), heard: run({ widthDrawn: false }) };
    }""")
    check("the compiled instrument given a code made Drawn too hears what it draws, to the bit, a chord of two",
          inst["drawn"][0] == 0 and inst["drawn"][1] > 0.05, str(inst))
    check("null: the same code on Heard hears apart from what it draws", inst["heard"][0] > 0.01, str(inst))
    check("no page errors", not errors, "; ".join(errors[:3]))
    p.close()

    print("\n--- the site's instrument ---")
    p, errors = opened(b, init="localStorage.setItem('scope.width', '30');", settle=3000)
    site = p.evaluate("""async () => {
      await new Promise((r) => setTimeout(r, 500));
      const s = await scopeHost.call('scopeState');
      const setup = decodeSetup(s.code);
      return { kind: state.source.kind, on: hostSync.on, width: setup && setup.pluginWidth, knob: el.stereoWidth.value };
    }""")
    check("on the site the instrument is told the Width this browser remembers, and its state says so",
          site["kind"] == "host" and site["on"] and site["width"] == 30 and site["knob"] == "30", str(site))
    p.close()
    p, errors = opened(b, settle=3000)
    plain = p.evaluate("""async () => { const s = await scopeHost.call('scopeState'); const setup = decodeSetup(s.code);
      return { width: setup && setup.pluginWidth, knob: el.stereoWidth.value }; }""")
    check("null: a browser that remembers none leaves the instrument at its default, fifty, saying nothing", plain["width"] is None and plain["knob"] == "50", str(plain))
    check("no page errors on the site", not errors, "; ".join(errors[:3]))
    p.close()
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
