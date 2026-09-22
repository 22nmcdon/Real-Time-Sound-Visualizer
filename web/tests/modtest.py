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

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all modulation checks pass")
