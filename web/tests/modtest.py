"""The modulation matrix, and the migration off the enum it replaces.

Every preset in the page still names its destination with the old enum's word,
and every setup code anyone has saved does too. The matrix has to reproduce what
those did exactly, so most of this is about equivalence rather than novelty.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

import fixtures
STEMS = fixtures.ensure()

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    print("\n--- every preset's old enum becomes the right routing ---")
    migrated = p.evaluate("""() => {
      const wrong = [], seen = [];
      for (const [, entries] of PRESETS) {
        for (const [name, setup] of entries) {
          applyPreset('b:' + name);
          const want = [];
          for (const i of [0, 1]) {
            const legacy = setup['l' + i + 'd'];
            const destId = LEGACY_DESTS[legacy === undefined ? 'none' : legacy];
            if (destId) want.push('lfo' + (i + 1) + '>' + destId);
          }
          const got = state.modRoutings.map((r) => r.sourceId + '>' + r.destId);
          if (want.join(',') !== got.join(',')) wrong.push({ name, want, got });
          if (want.length) seen.push(name);
        }
      }
      return { wrong, modulated: seen.length };
    }""")
    check("every preset migrates to the same destination", migrated["wrong"] == [],
          str(migrated["wrong"][:2]))
    print("    %d presets carry modulation" % migrated["modulated"])

    amounts = p.evaluate("""() => {
      applyPreset('b:Tumbling');       // l0d phase @100, l1d ratio @20
      return state.modRoutings.map((r) => [r.sourceId, r.destId, r.amount]);
    }""")
    check("and the depth comes across with it",
          amounts == [["lfo1", "gen.phase", 1.0], ["lfo2", "gen.ratio", 0.2]], str(amounts))

    print("\n--- a routing actually modulates ---")
    swept = p.evaluate("""async () => {
      applyPreset('b:Pure sine');
      state.timebase = 6;                        // 100 ms: enough cycles to measure
      lfos[0].shape = 'sine'; lfos[0].rate = 0.5;
      setLfoDest(0, 'gen.freq');
      setLfoDepth(0, 1);                          // one octave each way
      const seen = [];
      for (let i = 0; i < 40; i++) {
        await new Promise((r) => setTimeout(r, 60));
        const f = capture();
        const hz = estimateFrequency(f.channels[0], f.rate);
        if (hz) seen.push(hz);
      }
      setLfoDest(0, '');
      return { lo: Math.min(...seen), hi: Math.max(...seen), n: seen.length };
    }""")
    print("    440 Hz swept between %.0f and %.0f Hz" % (swept["lo"], swept["hi"]))
    check("one octave down is reached", 200 < swept["lo"] < 260, "%.0f Hz" % swept["lo"])
    check("one octave up is reached", 760 < swept["hi"] < 920, "%.0f Hz" % swept["hi"])

    print("\n--- two sources on one destination sum ---")
    summed = p.evaluate("""() => {
      applyPreset('b:Pure sine');
      // Both LFOs held still at a known value, pointed at the same parameter.
      lfos[0].shape = 'square'; lfos[0].rate = 0.0001;
      lfos[1].shape = 'square'; lfos[1].rate = 0.0001;
      lfos[0].phase = 0.1; lfos[1].phase = 0.1;          // square -> +0.9 each
      state.modRoutings = [
        { sourceId: 'lfo1', destId: 'gen.freq', amount: 0.5 },
        { sourceId: 'lfo2', destId: 'gen.freq', amount: 0.25 },
      ];
      touchRoutings(); compileRoutes();
      // What the per-sample loop would compute for the frequency slot.
      lfos[0].value = 0.9; lfos[1].value = 0.9;
      genMod.fill(0);
      for (const route of genRoutes) {
        genMod[route.slot] += route.unipolar
          ? route.amount * (1 - lfos[route.index].value) / 2
          : route.amount * lfos[route.index].value;
      }
      const sum = genMod[0];
      state.modRoutings = []; touchRoutings();
      return { sum, expected: 0.9 * 0.5 + 0.9 * 0.25 };
    }""")
    check("contributions add", abs(summed["sum"] - summed["expected"]) < 1e-6,
          "%.4f vs %.4f" % (summed["sum"], summed["expected"]))

    print("\n--- what a routing to nowhere does ---")
    stale = p.evaluate("""() => {
      state.modRoutings = [
        { sourceId: 'lfo1', destId: 'gen.phase', amount: 0.5 },
        { sourceId: 'lfo1', destId: 'filter.cutoff', amount: 0.5 },   // not built yet
        { sourceId: 'env.nothing', destId: 'gen.freq', amount: 0.5 },
      ];
      touchRoutings(); compileRoutes();
      return { compiled: genRoutes.length, kept: state.modRoutings.length };
    }""")
    check("an unknown destination is skipped", stale["compiled"] == 1, str(stale["compiled"]))
    check("but not deleted from the setup", stale["kept"] == 3, str(stale["kept"]))

    print("\n--- the setup round trip ---")
    trip = p.evaluate("""() => {
      applyPreset('b:Wobbling');            // two routings, wireframe destinations
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
    check("and the code carries a version", trip["version"] == 1, str(trip["version"]))

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

    print("\n--- the dropdown is a view of the list ---")
    ui = p.evaluate("""() => {
      applyPreset('b:Pure sine');
      const select = document.getElementById('lfoDest0');
      select.value = 'gen.ratio';
      select.dispatchEvent(new Event('change'));
      const after = state.modRoutings.map((r) => r.destId);
      const depth = document.getElementById('lfoDepth0');
      depth.value = '35'; depth.dispatchEvent(new Event('input'));
      const amount = lfoRouting(0) ? lfoRouting(0).amount : null;
      select.value = ''; select.dispatchEvent(new Event('change'));
      return { after, amount, cleared: state.modRoutings.length };
    }""")
    check("choosing a destination makes the routing", ui["after"] == ["gen.ratio"], str(ui["after"]))
    check("the depth slider sets its amount", abs((ui["amount"] or 0) - 0.35) < 1e-9, str(ui["amount"]))
    check("and off removes it", ui["cleared"] == 0, str(ui["cleared"]))

    print("\n--- the picture is a destination too ---")
    # A unison at zero phase draws a 45 degree diagonal. Turning it by an
    # eighth of a turn should stand it up.
    angles = p.evaluate("""() => {
      applyPreset('b:Circle');
      el.phase.value = '0'; el.phase.dispatchEvent(new Event('input'));
      state.modRoutings = []; touchRoutings();
      const axis = () => {
        const f = capture();
        const x = f.channels[0], y = f.channels[1], n = x.length;
        let mx = 0, my = 0;
        for (let i = 0; i < n; i++) { mx += x[i]; my += y[i]; }
        mx /= n; my /= n;
        let sxx = 0, syy = 0, sxy = 0;
        const spin = (state.rotate + state.rotateMod) * Math.PI * 2;
        const c = Math.cos(spin), s2 = Math.sin(spin);
        for (let i = 0; i < n; i++) {
          const px = x[i] - mx, py = y[i] - my;
          const rx = px * c - py * s2, ry = px * s2 + py * c;
          sxx += rx * rx; syy += ry * ry; sxy += rx * ry;
        }
        return 0.5 * Math.atan2(2 * sxy, sxx - syy) * 180 / Math.PI;
      };
      state.rotate = 0; const flat = axis();
      state.rotate = 0.125; const turned = axis();
      state.rotate = 0;
      return { flat, turned };
    }""")
    turn = (angles["turned"] - angles["flat"] + 180) % 180
    check("a rotation really turns the figure", abs(turn - 45) < 3,
          "%.1f deg from %.1f to %.1f" % (turn, angles["flat"], angles["turned"]))

    offsets = p.evaluate("""() => {
      state.modRoutings = []; touchRoutings();
      const f = capture();
      applyModMatrix(f, 16);
      const rest = { rotate: state.rotateMod, zoom: state.zoomMod, lag: state.lagMod };
      // A depth far past the destination's range must stop at the range.
      state.rotate = 0;
      state.modRoutings = [{ sourceId: 'lfo1', destId: 'view.rotate', amount: 99 }];
      touchRoutings();
      lfos[0].value = 1;
      applyModMatrix(f, 16);
      const pushed = state.rotateMod;
      state.modRoutings = []; touchRoutings();
      applyModMatrix(f, 16);
      return { rest, pushed, max: MOD_DESTS.get('view.rotate').max };
    }""")
    check("with nothing routed every offset is zero",
          offsets["rest"] == {"rotate": 0, "zoom": 0, "lag": 0}, str(offsets["rest"]))
    check("and a source cannot push past the range",
          abs(offsets["pushed"] - offsets["max"]) < 1e-9,
          "%.2f against a limit of %.2f" % (offsets["pushed"], offsets["max"]))

    print("\n--- the envelope follows what you play ---")
    env = p.evaluate("""async () => {
      applyPreset('b:Pure sine');
      const source = MOD_SOURCES.get('env.live');
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
    def cycles(seconds=2.0):
        p.evaluate("() => { lfos[0].shape = 'sine'; lfos[0].rate = 2; lfos[0].phase = 0; }")
        last = p.evaluate("() => lfos[0].phase")
        wraps = 0
        for _ in range(int(seconds / 0.04)):
            p.wait_for_timeout(40)
            now = p.evaluate("() => lfos[0].phase")
            if now < last: wraps += 1
            last = now
        return wraps

    p.evaluate("() => { el.srcTone.click(); }"); p.wait_for_timeout(500)
    onTone = cycles()
    check("2 Hz is 2 Hz on the tone source", abs(onTone - 4) <= 1, "%d cycles in 2 s" % onTone)

    p.locator("#menuButton").click(); p.wait_for_timeout(150)
    p.locator("#srcFile").click(no_wait_after=True); p.wait_for_timeout(150)
    p.locator("#fileInput").set_input_files(f"{STEMS}/test-fifth.wav")
    p.wait_for_timeout(1800)
    onFile = cycles()
    check("and 2 Hz on a file source, not 4", abs(onFile - 4) <= 1, "%d cycles in 2 s" % onFile)
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

      /* Every generator kind in turn: the figure and wireframe rows are hidden
         in the others, and a hidden row is exactly where an inert control goes
         unnoticed. `#spinRate` - the one that was actually broken - is only on
         screen in wireframe. */
      const seen = new Set();
      const dead = [];
      for (const kind of ['wave', 'figure', 'wireframe', 'harmonograph']) {
        el.genMode.value = kind;
        el.genMode.dispatchEvent(new Event('change'));

      for (const row of document.querySelectorAll('[data-mod-dest]')) {
        const input = row.querySelector('input[type=range]');
        if (!input || input.offsetWidth === 0) continue;
        if (seen.has(input.id)) continue;
        seen.add(input.id);

        const was = input.value;
        const lo = Number(input.min), hi = Number(input.max);
        const other = String(Number(was) === hi ? lo : hi);

        const before = look();
        input.value = other;
        input.dispatchEvent(new Event('input'));
        const after = look();

        input.value = was;
        input.dispatchEvent(new Event('input'));

        if (before === after) dead.push(row.dataset.modDest + ' (#' + input.id + ')');
      }
      }
      el.genMode.value = 'wave';
      el.genMode.dispatchEvent(new Event('change'));
      return { dead, checked: seen.size };
    }""")
    check("every destination's own control drives something",
          inert["dead"] == [], str(inert["dead"]))
    check("and enough of them were reachable to mean it",
          inert["checked"] >= 9, "%d controls" % inert["checked"])

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all modulation checks pass")
