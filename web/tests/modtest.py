"""The modulation matrix, and the migration off the enum it replaces.

Every preset in the page still names its destination with the old enum's word,
and every setup code anyone has saved does too. The matrix has to reproduce what
those did exactly, so most of this is about equivalence rather than novelty.
"""
# On the default page since stage 5, step 3, batch 6 (14 Nov), where the
# instrument is the brain; until then on ?brain=js, reading the page's own
# oscillators with their shape and rate set by hand, its route compiler, and
# its own microphone. What the page set by hand the instrument never heard,
# so each check here moves the controls a player moves (the Rate slider in
# the card's editor, the Mic button) and reads what the instrument sends
# back. The numbers - the octave sweep, the routing to nowhere, the rate on
# each source - are core/tests/pieces/mod.py's, rendered offline; batch 3
# took the matrix's sums and ranges there before them.
import os, sys
from playwright.sync_api import sync_playwright
import corpus

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")


fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required",
                                                          "--use-fake-device-for-media-stream",
                                                          "--use-fake-ui-for-media-stream"])
    p = b.new_context(permissions=["microphone"], viewport={"width": 1400, "height": 900}).new_page()
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(1500)
    corpus.install(p)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    print("\n--- every preset's old enum becomes the right routing ---")
    # The old library from before P8g and then the bank: the old one is where
    # the enum's setups are, l0d and l1d with no routing list, and the bank
    # is what is loaded now.
    migrated = p.evaluate("""() => {
      const wrong = [], seen = [];
      const walk = [...CORPUS.map(([s, e]) => [s, e, loadCorpus]),
                    ...PRESETS.map(([s, e]) => [s, e, (name) => applyPreset('b:' + name)])];
      for (const [, entries, load] of walk) {
        for (const [name, setup] of entries) {
          load(name);
          const want = [];
          // A routing list when the preset has one - as a setup code does -
          // and the old enum when it does not.
          if (setup.mod !== undefined) {
            // Less the sources version 9 cut (F4b), and the drawings' sources
            // and destinations version 10 cut (G2), whose routings their
            // decode passes drop: the corpus is the old library, from before.
            for (const r of decodeRoutings(setup.mod)) {
              const text = r.sourceId + '>' + r.destId + '@' + r.amount;
              if (!CUT_SOURCE.test(text) && !CUT_DRAWING.test(text)) want.push(r.sourceId + '>' + r.destId);
            }
          } else for (const i of [0, 1]) {
            const legacy = setup['l' + i + 'd'];
            const destId = LEGACY_DESTS[legacy === undefined ? 'none' : legacy];
            if (destId) want.push('lfo' + (i + 1) + '>' + destId);
          }
          const got = state.modRoutings.map((r) => r.sourceId + '>' + r.destId);
          if (want.join(',') !== got.join(',')) wrong.push({ name, want, got });
          if (want.length) seen.push(name);
        }
      }
      return { wrong, modulated: seen.length, walked: walk.reduce((n, [, e]) => n + e.length, 0) };
    }""")
    check("every preset migrates to the same destination", migrated["wrong"] == [],
          str(migrated["wrong"][:2]))
    print("    %d presets of %d carry modulation" % (migrated["modulated"], migrated["walked"]))

    amounts = p.evaluate("""() => {
      // The old library's, from before P8g, as are Pure sine, Wobbling and
      // Circle below: the sounds these were written against, a free sine at
      // 440 among them, where the bank's Pure sine is poly.
      loadCorpus('Tumbling');       // l0d phase @100, l1d ratio @20
      return state.modRoutings.map((r) => [r.sourceId, r.destId, r.amount]);
    }""")
    check("and the depth comes across with it",
          amounts == [["lfo1", "gen.phase", 1.0], ["lfo2", "gen.ratio", 0.2]], str(amounts))

    print("\n--- a routing actually modulates ---")
    # Each sound below under a note held in Mono (corpus.held_tone): the site
    # waits for a note since 10 Nov, and these read the tone it drew with none.
    swept = p.evaluate("""async () => {
      loadCorpus('Pure sine'); heldTone();
      /* heldTone puts the Frequency slider back in the same tick as the
         note-on, and on the site the slider reaches the instrument first:
         the note then plays its own 220 Hz, not the slider's 440 (batch 6;
         alias found the same race in batch 2). Moved again once the note
         has landed. */
      await new Promise((r) => setTimeout(r, 200));
      el.freq.dispatchEvent(new Event('input'));
      state.timebase = 6;                        // 100 ms: enough cycles to measure
      /* Half a cycle a second by LFO 1's Rate slider, in its card's editor,
         which the instrument hears. Until batch 6 the rate was written into
         the page's lfos by hand and a setup sent after it (P8h: the site's
         instrument hears a rate from a setup or from the Rate slider, and a
         rate written alone left it at the setup's 0.2 Hz, a five-second
         cycle the reads below cover about half of). */
      setView('bench'); openModCard('lfo1');
      const shape = document.getElementById('lfoShape0');
      shape.value = 'sine'; shape.dispatchEvent(new Event('change', { bubbles: true }));
      const rate = document.getElementById('lfoRate0');
      rate.value = '50'; rate.dispatchEvent(new Event('input', { bubbles: true }));
      // Patched as a player patches: the card dropped on the knob, and its
      // depth set to the whole of it (setLfoDest and setLfoDepth, which this
      // called until the second review, were the drawer's LFO rows'). One
      // octave each way.
      addRouting('lfo1', 'gen.freq');
      setDepth(state.modRoutings.find((r) => r.sourceId === 'lfo1' && r.destId === 'gen.freq'), 100, true);
      /* The window is 100 ms and the first read used to come 60 ms after the
         load, so it held the seam where the sound was loaded - a jump of
         nearly the whole amplitude between two samples, with 440 Hz before
         it - and the estimate read across it came out at a half or two
         thirds of the trough: 110 or 147 Hz, one run in five or six, on the
         page from before P8g as on this one (P8h). The sweep is read once
         the load has left the window; the reads still span more than the
         LFO's two-second cycle, so both ends are in them. */
      await new Promise((r) => setTimeout(r, 300));
      const seen = [];
      for (let i = 0; i < 40; i++) {
        await new Promise((r) => setTimeout(r, 60));
        const f = capture();
        const hz = estimateFrequency(f.channels[0], f.rate);
        if (hz) seen.push(hz);
      }
      dropRouting('lfo1', 'gen.freq');
      return { lo: Math.min(...seen), hi: Math.max(...seen), n: seen.length };
    }""")
    print("    440 Hz swept between %.0f and %.0f Hz" % (swept["lo"], swept["hi"]))
    check("one octave down is reached", 200 < swept["lo"] < 260, "%.0f Hz" % swept["lo"])
    check("one octave up is reached", 760 < swept["hi"] < 920, "%.0f Hz" % swept["hi"])

    # "Contributions add" summed the page's `genRoutes` in the test itself,
    # with its LFOs held still by hand; it is core/tests/pieces/mod.py's
    # since stage 5, step 3, batch 3 (13 Nov): two sources held at a value in
    # the core's matrix, and the pitch the generator plays from what it hands it.

    print("\n--- what a routing to nowhere does ---")
    # "An unknown destination is skipped" counted the page's own `genRoutes`
    # after its `compileRoutes`, a compiler that feeds nothing on the site;
    # it is core/tests/pieces/mod.py's since batch 6, the core's matrix
    # loading the same three routings. What stays is the face's half: the
    # setup it sends keeps all three.
    stale = p.evaluate("""() => {
      state.modRoutings = [
        { sourceId: 'lfo1', destId: 'gen.phase', amount: 0.5 },
        { sourceId: 'lfo1', destId: 'filter.nothing', amount: 0.5 },   // no such destination
        { sourceId: 'env.nothing', destId: 'gen.freq', amount: 0.5 },
      ];
      touchRoutings();
      return { kept: state.modRoutings.length, sent: (snapshot().mod || '').split(';').length };
    }""")
    check("an unknown destination is not deleted from the setup", stale["kept"] == 3 and stale["sent"] == 3, str(stale))

    print("\n--- the setup round trip ---")
    trip = p.evaluate("""() => {
      /* Two routings in the old enum, onto the phase and the ratio. Wobbling
         until G2, whose two were onto a solid's spin rate and perspective:
         destinations that went with the solids, so the routings it kept
         would have survived as text while routing to nothing. */
      loadCorpus('Tumbling');
      const before = snapshot();
      const code = encodeSetup(before);
      const decoded = decodeSetup(code);
      restore(decoded);
      const after = snapshot();
      return {
        differ: Object.keys(before).filter((k) => before[k] !== after[k]),
        mod: after.mod, version: decoded.v,
      };
    }""")
    check("nothing changes through encode and decode", trip["differ"] == [], str(trip["differ"]))
    check("the routings survive as text", ">" in (trip["mod"] or ""), trip["mod"])
    # The number the page is on, not a number written here: what this is about
    # is that a code SAYS which format it is in, so an old one can be migrated
    # rather than misread. Pinning the digit meant a format change failed in a
    # suite that has nothing to do with the format.
    check("and the code carries the current version",
          trip["version"] == p.evaluate("() => SETUP_VERSION"),
          str(trip["version"]))

    print("\n--- a code written before the matrix existed ---")
    legacy = p.evaluate("""() => {
      // Exactly what encodeSetup produced a version ago: the enum, no `mod`.
      const old = { shape: 'sine', interval: 7, display: 'xy', timebase: 4,
                    l0d: 'phase', l0r: 120, l0a: 100,
                    l1d: 'ratio', l1r: 13, l1a: 20 };
      const code = btoa(JSON.stringify(old)).replace(/=+$/, '');
      restore(decodeSetup(code));
      return state.modRoutings.map((r) => r.sourceId + '>' + r.destId + '@' + r.amount);
    }""")
    check("still loads, and points where it said",
          legacy == ["lfo1>gen.phase@1", "lfo2>gen.ratio@0.2"], str(legacy))

    # Version 5 cut the crossings, the threshold and Pluck (P5). The routing
    # list keeps ids it does not know, so a route from the threshold or to
    # the pluck would otherwise ride along in every code saved after it. The
    # same code marked 5 is the null: it keeps them, so the check can fail.
    print("\n--- a code written before the crossings, the threshold and Pluck went ---")
    cut = p.evaluate("""() => {
      const code = (v) => btoa(JSON.stringify({ v, crossOn: true, threshWatch: 'lfo1', pluckNote: 64,
        mod: 'threshold>gen.freq@0.500;lfo1>gen.amp@0.400;lfo2>gen.pluck@1.000' })).replace(/=+$/, '');
      // The fields are read off the decoded setup itself: a snapshot could
      // not show them, since it writes only what the page has.
      const load = (v) => {
        const decoded = decodeSetup(code(v));
        restore(decoded);
        return { routes: state.modRoutings.map((r) => r.sourceId + '>' + r.destId), mod: snapshot().mod,
                 stale: ['crossOn', 'threshWatch', 'pluckNote'].filter((k) => k in decoded) };
      };
      const out = { four: load(4), five: load(5) };
      state.modRoutings = []; touchRoutings();
      return out;
    }""")
    check("a version-4 code loads without the routes from the threshold or to the pluck, and saves without them",
          cut["four"]["routes"] == ["lfo1>gen.amp"] and "threshold" not in cut["four"]["mod"]
          and "pluck" not in cut["four"]["mod"] and cut["four"]["stale"] == [], str(cut["four"]))
    check("and the same code marked version 5 keeps them, so the pass is what took them out",
          "threshold>gen.freq" in cut["five"]["routes"] and "lfo2>gen.pluck" in cut["five"]["routes"]
          and cut["five"]["stale"] == ["crossOn", "threshWatch", "pluckNote"], str(cut["five"]))

    # Version 10 cut the drawings (G2): a kind that was a drawing, or none at
    # all, becomes the waveform, the drawings' 22 fields go, and so does a
    # routing whose source is a drawing's reading or whose destination is a
    # drawing's - each read whole, the source anchored before the arrow and
    # the destination exactly between it and the "@", so near-misses stay:
    # a source that only ends in "draw.swing", a destination that only begins
    # with "gen.depth". Read through both codecs, the page's own (the
    # reference) and the one the site decodes with, which is the compiled
    # core's; the second was held to the first. The same code marked 10 is the
    # null: nothing is taken, so the check can fail. Since batch 6 the three
    # read the site's codec: the page's own (decodeSetupHere) is a fallback
    # step 6 deletes, and the row that held the one to the other compared two
    # codecs, not anything the site does, and went with ?brain=js.
    print("\n--- a code written before the drawings went ---")
    g2 = p.evaluate("""() => {
      const DRAWN = ['figure', 'detail', 'figureRate', 'figText', 'figPath', 'figDrawn', 'swingRate', 'decay',
                     'detune', 'swingDrive', 'inputFrom', 'gen2Figure', 'gen2Rate', 'model', 'spinX', 'spinY',
                     'spinZ', 'spinRate', 'depth', 'midiDrive', 'midiPlay', 'ring'];
      const fields = Object.fromEntries(DRAWN.map((k, i) => [k, k === 'inputFrom' ? 'gen2' : i + 1]));
      const mod = 'draw.swing>gen.freq@0.500;lfo1>gen.detail@0.300;lfo1>gen.freq@0.200;draw.turnX>gen.amp@0.100;'
        + 'xdraw.swing>gen.vcf@0.250;lfo2>gen.depthX@0.400;lfo1>gen.kick@1.000;draw.facing>gen.spinZ@0.700';
      const code = (setup) => btoa(JSON.stringify(setup)).replace(/=+$/, '');
      const read = (decode, setup) => {
        const d = decode(code(setup));
        return { v: d.v, gen: d.gen, mod: d.mod, shape: d.shape, kept: DRAWN.filter((k) => k in d) };
      };
      const old = Object.assign({ v: 9, gen: 'figure', shape: 'square', mod }, fields);
      const out = {};
      for (const [name, decode] of [['site', decodeSetup]]) {
        out[name] = { nine: read(decode, old), none: read(decode, { v: 9, shape: 'square' }),
                      ten: read(decode, Object.assign({}, old, { v: 10 })) };
      }
      return out;
    }""")
    G2_KEPT = "lfo1>gen.freq@0.200;xdraw.swing>gen.vcf@0.250;lfo2>gen.depthX@0.400"
    pg = g2["site"]
    check("a version-9 code with a drawing loads as the waveform, its shape kept, the drawings' fields gone, "
          "and only the drawings' routings dropped, near-misses kept",
          pg["nine"] == {"v": 11, "gen": "wave", "mod": G2_KEPT, "shape": "square", "kept": []}, str(pg["nine"]))
    check("and one that names no kind at all is given the waveform", pg["none"]["gen"] == "wave", str(pg["none"]))
    check("and the same code marked version 10 keeps everything, so the pass is what took it",
          pg["ten"]["gen"] == "figure" and len(pg["ten"]["kept"]) == 22 and pg["ten"]["mod"].count(";") == 7,
          str(pg["ten"]))

    # The card's editor is the view of the list now (the Sources tab until F4),
    # where the one-destination dropdown was: Add makes a routing, its row's
    # slider is its depth, and the row's cross removes it.
    print("\n--- the card's editor is a view of the list ---")
    ui = p.evaluate("""() => {
      loadCorpus('Pure sine');
      setView('bench'); openModCard('lfo1');
      const add = document.getElementById('srcDetail-add');
      add.value = 'gen.ratio';
      add.dispatchEvent(new Event('change'));
      const after = state.modRoutings.map((r) => r.destId);
      const depth = el.srcDetail.querySelector('.mod-edit[data-dest="gen.ratio"] input');
      depth.value = '35'; depth.dispatchEvent(new Event('input'));
      const made = state.modRoutings.find((r) => r.sourceId === 'lfo1');
      const amount = made ? made.amount : null;
      el.srcDetail.querySelector('.mod-edit[data-dest="gen.ratio"] .mod-edit-off').click();
      const out = { after, amount, cleared: state.modRoutings.length };
      // No setView('scope') back: the Scope view went in G4, and the face is the Bench.
      return out;
    }""")
    check("adding a destination makes the routing", ui["after"] == ["gen.ratio"], str(ui["after"]))
    check("its depth slider sets its amount", abs((ui["amount"] or 0) - 0.35) < 1e-9, str(ui["amount"]))
    check("and its cross removes it", ui["cleared"] == 0, str(ui["cleared"]))

    # The picture as a destination - a rotation really turns the figure,
    # nothing routed leaves every offset at nought, and a source cannot push
    # past the range - read the page's `capture()` with its rotation set by
    # hand and its `applyModMatrix` with LFO 1 held at one. They are
    # core/tests/pieces/mod.py's since stage 5, step 3, batch 3: the core's
    # capture turned and its lanes read whole (a diagonal line, not the
    # circle, which a rotation leaves alone), and the instrument's own screen
    # destinations on the core's matrix with a source held at a value.

    # The level, a source until F4b and the output meter since: its reading,
    # as paintStage takes it.
    print("\n--- the level follows what you play ---")
    env = p.evaluate("""async () => {
      loadCorpus('Pure sine'); heldTone();
      const source = { value: () => Math.min(1, envLive / ENV_FULL) };
      el.amp.value = '100'; el.amp.dispatchEvent(new Event('input'));
      await new Promise((r) => setTimeout(r, 600));
      const loud = source.value();
      el.amp.value = '0'; el.amp.dispatchEvent(new Event('input'));
      await new Promise((r) => setTimeout(r, 120));
      const justAfter = source.value();
      await new Promise((r) => setTimeout(r, 900));
      const quiet = source.value();
      el.amp.value = '55'; el.amp.dispatchEvent(new Event('input'));
      return { loud, justAfter, quiet };
    }""")
    print("    loud %.3f -> 120 ms later %.3f -> 1 s later %.3f"
          % (env["loud"], env["justAfter"], env["quiet"]))
    check("it rises with the signal", env["loud"] > 0.5, "%.3f" % env["loud"])
    check("and falls when it stops", env["quiet"] < 0.05, "%.3f" % env["quiet"])
    check("but releases slower than it attacks", env["justAfter"] > env["quiet"] * 2,
          "still %.3f after 120 ms" % env["justAfter"])

    print("\n--- every oscillator advances exactly once ---")
    # The trap the two paths create: the tone source steps them per sample and
    # everything else steps them per frame. Both would run at double rate, and
    # double is exactly the kind of wrong that looks plausible.
    # Counted against the seconds that actually passed, not the ones asked for:
    # fifty polls of 40 ms each took three seconds on a loaded machine and
    # counted six cycles of a 2 Hz oscillator that was running perfectly. What
    # this exists to catch is double rate, and twice the elapsed seconds is still
    # the measure of that.
    # Since batch 6 the rate is LFO 1's Rate slider and the phase read is the
    # instrument's, which the page's lfos take from every chunk it posts back
    # (makeBrainSource's absorb): on ?brain=js both were the page's own, the
    # rate written by hand. Written by hand here it moves nothing.
    def cycles(seconds=2.0, slider="200"):
        p.evaluate("""(v) => { setView('bench'); openModCard('lfo1'); const r = document.getElementById('lfoRate0');
          r.value = v; r.dispatchEvent(new Event('input', { bubbles: true })); }""", slider)
        last, t0 = p.evaluate("() => [lfos[0].phase, performance.now()]")
        wraps = 0
        for _ in range(int(seconds / 0.04)):
            p.wait_for_timeout(40)
            now = p.evaluate("() => lfos[0].phase")
            if now < last: wraps += 1
            last = now
        elapsed = (p.evaluate("() => performance.now()") - t0) / 1000
        return wraps, elapsed

    p.evaluate("() => { el.srcTone.click(); }"); p.wait_for_timeout(500)
    onTone, tTone = cycles()
    check("2 Hz is 2 Hz on the tone source", p.evaluate("() => playingKind()") == "tone"
          and abs(onTone - 2 * tTone) <= 1.5, "%d cycles in %.2f s" % (onTone, tTone))
    p.evaluate("() => { lfos[0].rate = 5; }")
    byHand, tHand = cycles(1.0, "200")
    check("and what is counted is the instrument's: the page's own rate written by hand to 5 Hz moves nothing",
          abs(byHand - 2 * tHand) <= 1.5, "%d cycles in %.2f s" % (byHand, tHand))
    fast, tFast = cycles(1.0, "400")
    check("null: the slider at 4 Hz fails the 2 Hz rule", not abs(fast - 2 * tFast) <= 1.5, "%d cycles in %.2f s" % (fast, tFast))

    p.evaluate("() => { setView('bench'); setBenchTab('play'); }"); p.wait_for_timeout(150)
    # The microphone, faked, as the source that is not the tone: it was a file
    # until P5 cut file playback. Pressed, so the instrument draws the input
    # (on ?brain=js, toMic(), the page's own microphone, where the per-sample
    # and per-frame steps had once both run).
    p.evaluate("() => showControl('srcMic')"); p.locator("#srcMic").click(no_wait_after=True); p.wait_for_timeout(1800)
    onMic, tMic = cycles()
    check("and 2 Hz on the microphone, not 4", p.evaluate("() => playingKind()") == "mic"
          and abs(onMic - 2 * tMic) <= 1.5, "%d cycles in %.2f s" % (onMic, tMic))
    p.evaluate("() => { el.srcTone.click(); }"); p.wait_for_timeout(400)

    print("\n--- every modulatable control drives something ---")
    # `gen.tumble` applied 3^depth to nothing for several releases: the Spin
    # rate slider moved, wrote nothing, and the lane drew a reach the generator
    # was never going to honour. A control that is a modulation DESTINATION but
    # not also a base is the shape of that bug, so this looks for it everywhere
    # rather than in the one place it happened to be found.
    #
    # Deliberately not a comparison of rendered output. Two earlier attempts at
    # this did compare the generator's samples between runs, and both PASSED
    # against the broken code - the first because the two runs differed for
    # reasons of their own, the second because successive runs drift further
    # apart than the thing under test moves them. The question is much simpler
    # than those attempts made it: does moving this slider change any state?
    inert = p.evaluate("""() => {
      const VOLATILE = new Set(['zoom', 'lagActual', 'starved', 'rotateMod',
        'lagMod', 'cutoffMod', 'resMod', 'zoomMod', 'positionMod', 'harmonics',
        'reference', 'hoverY', 'source', 'modRoutings', 'running']);

      const look = () => {
        const out = [];
        for (const key of Object.keys(state)) {
          if (VOLATILE.has(key)) continue;
          try { out.push(key + '=' + JSON.stringify(state[key])); } catch (e) { }
        }
        if (state.source && state.source.settings) {
          out.push('@=' + JSON.stringify(state.source.settings));
        }
        return out.join('|');
      };

      /* Every generator kind in turn, until G2 left one: the figure and
         wireframe rows were hidden in the others, and a hidden row is exactly
         where an inert control goes unnoticed. `#spinRate` - the one that was
         actually broken - was only on screen in wireframe. */
      const seen = new Set();
      const dead = [], unsent = [];
      /* And each one tells the instrument (batch 6): on the site a control
         that changed the face's state and nothing the instrument hears would
         pass the state diff above and move nothing played. */
      const sent = [];
      const call = scopeHost.call;
      scopeHost.call = function (name, ...a) { if (name === 'scopeSlider') sent.push(a[0]); return call.apply(this, [name, ...a]); };
      /* And every Bench tab: a control counts only if it can be seen, and
         since the Bench became tabs only one tab's controls can be at once. */
      setView('bench');
      for (const [tab] of BENCH_TABS) {
      setBenchTab(tab);
      for (const row of document.querySelectorAll('[data-mod-dest]')) {
        const input = row.querySelector('input[type=range]');
        if (!input || input.offsetWidth === 0) continue;
        if (seen.has(input.id)) continue;
        seen.add(input.id);

        const was = input.value;
        const lo = Number(input.min), hi = Number(input.max);
        const other = String(Number(was) === hi ? lo : hi);

        const before = look();
        sent.length = 0;
        input.value = other;
        input.dispatchEvent(new Event('input'));
        const after = look();
        if (!sent.includes(input.id)) unsent.push(row.dataset.modDest + ' (#' + input.id + ')');

        input.value = was;
        input.dispatchEvent(new Event('input'));

        if (before === after) dead.push(row.dataset.modDest + ' (#' + input.id + ')');
      }
      }
      setBenchTab('play');  // No setView('scope') back: the Scope view went in G4, and the face is the Bench.
      scopeHost.call = call;
      return { dead, unsent, checked: seen.size };
    }""")
    check("every destination's own control drives something",
          inert["dead"] == [], str(inert["dead"]))
    check("and each one tells the instrument, by its own id", inert["unsent"] == [], str(inert["unsent"]))
    check("and enough of them were reachable to mean it",
          inert["checked"] >= 9, "%d controls" % inert["checked"])

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all modulation checks pass")
