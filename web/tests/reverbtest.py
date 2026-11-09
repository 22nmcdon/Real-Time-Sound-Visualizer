"""The reverb (P9 of web/docs/making-it-one-instrument.md, 9 Nov).

Last in the rack, on the generator's figure and on what is heard, so the
phosphor holds its tail and Scan reads it. The owner's design: two identical
reverbs, one a channel, with no cross-feed, and a Spread that gives Y other
output taps from the same network - so at nought the figure is kept and the
tail shows only where the sound changes, and turned up it is an ordinary
stereo tail and the figure clouds over.

What would go wrong, and what is checked for it:

- the figure not kept: one asymmetric signal (a ramp, which no transform that
  leaves a symmetric signal alone can hide behind) on both channels must come
  out the same on both to the bit at a Spread of nought. The null, the owner's
  own: at a Spread of one the same signal comes out apart, so a Spread that
  did nothing cannot pass - and X must be the same at both, since only Y's
  taps turn;
- a Size that is not the law it says: the tail's slope in decibels, read
  between 0.1 and 0.6 s, is 60 dB over 0.3 x 30^size seconds, to a fifth, at
  two sizes; the null reads each against the other's law;
- a Mix that is not a mix: the tail is added to the dry pair, so the tail at
  a mix of one is twice the tail at a half, to float precision - against
  the dry pair, which is the same at both;
- a Tone that is a volume knob: dark, the tail is under half the brightness
  of the open one (its sample-to-sample change over its level), and still
  over a third of its level, so it is darker and not merely quieter;
- a pre-delay that is not one: the tail's first sound is the pre-delay and
  the shortest line after the burst begins, to the sample, and 40 ms of
  pre-delay is 1764 samples later than none;
- off not being off: at a mix of nought, unrouted, the generator's output is
  what it is with no reverb fields set at all, to the bit;
- the knobs not reaching the generator, or reading wrongly; the switch not
  keeping its mix; codes losing it or an old code gaining one; B's own;
  destinations offered that should not be.
"""
import math, os, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
RATE = 44100

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    check("null: " + name, red, detail)

# The generator core alone, steps in order on one core. A ramp at 220 Hz on
# both channels (interval nought, phase nought), so X and Y are one
# asymmetric signal; a step with `amp: 0` is the silence the tail rings into.
CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('mode', 'wave'); core.set('shape', 'ramp'); core.set('amp', 0.5); core.set('freq', 220);
  core.set('interval', 0); core.set('phase', 0);
  const out = { L: [], R: [] };
  for (const step of setup.steps) {
    for (const k in step.tone || {}) core.set(k, step.tone[k]);
    if (step.routes) core.setRoutes(step.routes);
    const n = step.n, L = new Float32Array(n), R = new Float32Array(n);
    const HL = new Float32Array(n), HR = new Float32Array(n), BL = new Float32Array(n), BR = new Float32Array(n);
    core.block(L, R, n, HL, HR, BL, BR);
    for (let i = 0; i < n; i++) { out.L.push(L[i]); out.R.push(R[i]); }
  }
  return out;
}"""

def rms(x):
    x = np.asarray(x, dtype=float)
    return float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    def run(*steps):
        out = p.evaluate(CORE, {"steps": list(steps)})
        return {k: np.asarray(v, dtype=float) for k, v in out.items()}
    BURST = int(0.05 * RATE)
    def burst(tone, after=1.0):
        return run({"tone": tone, "n": BURST}, {"tone": {"amp": 0}, "n": int(after * RATE)})

    print("\n--- it keeps the figure, and Spread lets it go ---")
    s0 = burst({"reverbMix": 1, "reverbSpread": 0})
    s1 = burst({"reverbMix": 1, "reverbSpread": 1})
    dry = burst({})
    # A ramp's values are spread evenly, so their own skew is nought; its
    # asymmetry is in time - a slow rise and a sudden fall - which is the
    # skew of its slope. A sine's slope reads nought by the same measure
    # (the second check's null), so the reading can tell the two apart.
    def slope_skew(x):
        d = np.diff(np.asarray(x, dtype=float))
        return float(np.mean(d ** 3)) / max(rms(d) ** 3, 1e-12)
    skew = slope_skew(dry["L"][:BURST])
    sine_skew = slope_skew(np.sin(2 * np.pi * 220 * np.arange(BURST) / RATE))
    print("    the fixture's skew %.3f; tail level %.4f" % (skew, rms(s0["L"][BURST:BURST + RATE // 2])))
    check("the fixture: one asymmetric signal on both channels, a ramp, the same on both",
          np.array_equal(dry["L"], dry["R"]) and abs(skew) > 1, "skew of its slope %.3f" % skew)
    null("a sine's slope, symmetric in time, reads under a tenth of that", abs(sine_skew) < 0.1 * abs(skew), "%.4f" % sine_skew)
    check("at a Spread of nought the same signal comes out the same on both channels, burst and tail, to the bit",
          np.array_equal(s0["L"], s0["R"]) and rms(s0["L"][BURST:BURST + RATE // 2]) > 0.01)
    apart = float(np.max(np.abs(s1["L"] - s1["R"])))
    null("at a Spread of one the same signal comes out apart: an ordinary stereo tail", apart > 0.05, "%.3f" % apart)
    check("and only Y's taps turn: X is the same at both", np.array_equal(s0["L"], s1["L"]))

    # Nothing crosses between the two networks (the owner's first condition).
    # The burst above is the same on both channels, so a Y network fed from X
    # would pass it unchanged; here Y alone plays something else (a fifth up,
    # which leaves X the same to the bit). X's output, tail and all, must not
    # move; and Y's tail must, since it is Y's own - a Y network fed from X
    # would ring the same whatever Y played.
    for sp in (0, 1):
        same = burst({"reverbMix": 1, "reverbSpread": sp})
        fifth = burst({"reverbMix": 1, "reverbSpread": sp, "interval": 7})
        dry_same, dry_fifth = burst({"reverbSpread": sp}), burst({"reverbSpread": sp, "interval": 7})
        check("at a Spread of %d, Y playing a fifth up leaves X's output, tail and all, the same to the bit" % sp,
              np.array_equal(dry_same["L"], dry_fifth["L"]) and not np.array_equal(dry_same["R"], dry_fifth["R"])
              and np.array_equal(same["L"], fifth["L"]))
        tail_moved = float(np.max(np.abs((same["R"] - dry_same["R"]) - (fifth["R"] - dry_fifth["R"]))))
        check("and Y's tail is Y's own: it changes with what Y plays", tail_moved > 0.01, "%.3f" % tail_moved)
    null("X's comparison goes red on two arrays that differ: Y's outputs", not np.array_equal(same["R"], fifth["R"]))

    print("\n--- Size is the decay time it says ---")
    def t60(tone):
        x = burst(dict(tone, reverbMix=1, reverbTone=1, reverbPreMs=0), after=0.8)["L"]
        w = int(0.05 * RATE)
        db = [20 * math.log10(max(rms(x[i:i + w]), 1e-12)) for i in range(BURST + int(0.1 * RATE), BURST + int(0.6 * RATE), w)]
        t = np.arange(len(db)) * 0.05
        slope = float(np.polyfit(t, db, 1)[0])
        return -60 / slope
    law = {s: 0.3 * 30 ** s for s in (0.3, 0.6)}
    got = {s: t60({"reverbSize": s}) for s in law}
    print("    " + ", ".join("size %.1f: %.2f s, the law %.2f" % (s, got[s], law[s]) for s in law))
    check("the tail falls 60 dB in 0.3 x 30^size seconds, to a fifth, at two sizes",
          all(abs(got[s] / law[s] - 1) < 0.2 for s in law), str(got))
    null("each against the other's law, the same tails fail", not any(abs(got[s] / law[t] - 1) < 0.2 for s, t in ((0.3, 0.6), (0.6, 0.3))))

    print("\n--- Mix adds the tail, Tone darkens it, Pre-delay delays it ---")
    tail = lambda r: r["L"][BURST:]
    half, full = burst({"reverbMix": 0.5}), burst({"reverbMix": 1})
    wet_ratio = rms(tail(full)) / max(rms(tail(half)), 1e-12)
    check("the tail at a mix of one is twice the tail at a half, and the burst the same at both",
          abs(wet_ratio - 2) < 1e-4 and float(np.max(np.abs(full["L"][:1300] - half["L"][:1300]))) < 1e-6, "%.6f" % wet_ratio)
    null("the dry burst is not twice itself", abs(rms(full["L"][:1300]) / rms(half["L"][:1300]) - 2) > 0.5)
    def bright(x):
        x = x[int(0.1 * RATE):int(0.5 * RATE)]
        return rms(np.diff(x)) / max(rms(x), 1e-12)
    dark, opened = burst({"reverbMix": 1, "reverbTone": 0.1}), burst({"reverbMix": 1, "reverbTone": 1})
    bd, bo = bright(dark["L"]), bright(opened["L"])
    level = rms(dark["L"][int(0.1 * RATE):int(0.5 * RATE)]) / rms(opened["L"][int(0.1 * RATE):int(0.5 * RATE)])
    check("dark, the tail is under half as bright as open, and still over a third of its level: darker, not quieter",
          bd < bo / 2 and level > 0.33, "brightness %.4f against %.4f, level %.2f of it" % (bd, bo, level))
    def first(tone):
        wet = burst(dict(tone, reverbMix=1), after=0.2)["L"] - burst(dict(tone, reverbMix=0), after=0.2)["L"]
        return next((i for i, v in enumerate(wet) if v != 0), None)
    f0, f40 = first({"reverbPreMs": 0}), first({"reverbPreMs": 40})
    shortest = round(31.3 * RATE / 1000)
    check("the tail's first sound is the pre-delay and the shortest line after the burst begins, to the sample",
          f0 == shortest and f40 == shortest + round(40 * RATE / 1000), "%s and %s, for %d and %d"
          % (f0, f40, shortest, shortest + round(40 * RATE / 1000)))
    null("40 ms of pre-delay is not where none is", f40 != f0)

    print("\n--- off is off ---")
    plain = burst({})
    at_rest = burst({"reverbMix": 0, "reverbSize": 0.9, "reverbTone": 0.2, "reverbPreMs": 80, "reverbSpread": 1})
    check("at a mix of nought, unrouted, every other reverb setting moved, the output is the plain one to the bit",
          np.array_equal(plain["L"], at_rest["L"]) and np.array_equal(plain["R"], at_rest["R"]))
    null("at a mix of a hundredth it is not", not np.array_equal(plain["L"], burst({"reverbMix": 0.01})["L"]))

    print("\n--- the module ---")
    p.evaluate("() => { setView('bench'); setBenchTab('space'); }"); p.wait_for_timeout(300)
    ui = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const m = document.querySelector('.fx-module[data-fx="reverb"]'), pill = m.querySelector('.fx-on');
      const read = () => ({ on: m.dataset.on, line: m.querySelector('.fx-sum').textContent, mix: genSettings().reverbMix });
      const off = read();
      pill.click(); await wait(200);
      const on = read();
      setControl('reverbMix', 70); await wait(100);
      pill.click(); await wait(200);
      const again = read();
      pill.click(); await wait(200);
      const back = read();
      // Where the line starts to warn: at a fifth it does not, just past it
      // it does, whatever the Spread says.
      const warn = {};
      for (const v of [20, 21, 100]) { setControl('reverbMix', v); await wait(400); warn[v] = m.querySelector('.fx-sum').textContent; }
      setControl('reverbMix', 70); await wait(100);
      const knobs = {};
      for (const [id, v] of [['reverbSize', 70], ['reverbTone', 20], ['reverbPre', 35], ['reverbSpread', 50]]) {
        setControl(id, v); await wait(50);
        const field = { reverbSize: 'reverbSize', reverbTone: 'reverbTone', reverbPre: 'reverbPreMs', reverbSpread: 'reverbSpread' }[id];
        knobs[id] = [genSettings()[field], el[id + 'Value'].textContent];
      }
      setControl('reverbSpread', 0); await wait(50); const kept = el.reverbSpreadValue.textContent;
      setControl('reverbSpread', 100); await wait(50); const stereo = el.reverbSpreadValue.textContent;
      setControl('reverbTone', 100); await wait(50); const open = el.reverbToneValue.textContent;
      return { off, on, again, back, warn, knobs, kept, stereo, open, line: m.querySelector('.fx-sum').textContent };
    }""")
    print("    %s" % ui)
    # 0.15, not the quarter it was built with: at a quarter a Settled preset
    # sat on the edge of breathing (honestytest.py has the readings).
    check("its switch turns it on at a mix of 0.15, its line saying so and that it keeps the figure",
          ui["off"]["on"] == "0" and ui["off"]["line"] == "Off" and ui["on"]["on"] == "1"
          and abs(ui["on"]["mix"] - 0.15) < 1e-9 and ui["on"]["line"] == "1.2 s · keeps the figure", str(ui["on"]))
    w = ui["warn"]
    check("past a Mix of a fifth its line says it keeps a held chord moving, and at a fifth it does not",
          w["20"] == "1.2 s · keeps the figure" and w["21"] == "1.2 s · keeps a held chord moving"
          and w["100"] == w["21"], str(w))
    null("the warning is not on the line the switch gives", "moving" not in ui["on"]["line"])
    check("off keeps what it had and on puts it back", ui["again"]["mix"] == 0 and abs(ui["back"]["mix"] - 0.7) < 1e-9,
          "%s, %s" % (ui["again"], ui["back"]))
    k = ui["knobs"]
    check("each knob reaches the generator, with its reading: the size as its decay time, the tone as its corner",
          abs(k["reverbSize"][0] - 0.7) < 1e-9 and k["reverbSize"][1] == "3.2 s"
          and abs(k["reverbTone"][0] - 0.2) < 1e-9 and "Hz" in k["reverbTone"][1]
          and k["reverbPre"] == [35, "35 ms"] and abs(k["reverbSpread"][0] - 0.5) < 1e-9 and k["reverbSpread"][1] == "50%", str(k))
    check("Spread says what it does at its ends, and Tone open says open",
          ui["kept"] == "keeps the figure" and ui["stereo"] == "ordinary stereo" and ui["open"] == "open",
          "%s, %s, %s" % (ui["kept"], ui["stereo"], ui["open"]))
    offered = p.evaluate("""() => ({
      dests: ['gen.reverb', 'gen.reverbSize', 'gen.reverbTone'].map((d) => !!MOD_DESTS.get(d)
        && routingAllowed(MOD_SOURCES.get('lfo1'), MOD_DESTS.get(d))),
      rows: ['reverbMix', 'reverbSize', 'reverbTone'].map((id) => !!document.querySelector('[data-mod-control="' + id + '"] #' + id)),
      not: ['reverbPre', 'reverbSpread'].filter((id) => document.querySelector('[data-mod-control="' + id + '"]')),
      host: ['reverbMix', 'reverbSize'].map((id) => el[id].closest('.menu-row').classList.contains('host-param')),
      last: Array.from(document.querySelectorAll('#rackGroup > .fx-module[data-fx]')).pop().dataset.fx })""")
    check("Mix, Size and Tone take a source; Pre-delay and Spread do not; Mix alone is a host parameter; it is last in the rack",
          offered == {"dests": [True] * 3, "rows": [True] * 3, "not": [], "host": [True, False], "last": "reverb"}, str(offered))
    # Last even when the three before it are reordered.
    moved = p.evaluate("""async () => { setFxOrder('dcp'); await new Promise((r) => setTimeout(r, 100));
      const order = Array.from(document.querySelectorAll('#rackGroup > .fx-module[data-fx]')).map((m) => m.dataset.fx);
      setFxOrder('pcd'); return order; }""")
    check("and stays last when the others are put in another order", moved[-1] == "reverb" and moved[1:4] == ["delay", "chorus", "phaser"],
          str(moved))

    print("\n--- codes ---")
    codes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      restore(Object.assign(snapshot(), { reverbMix: 40, reverbSize: 65, reverbTone: 30, reverbPre: 25, reverbSpread: 80 }));
      await wait(50);
      const code = encodeSetup(snapshot());
      restore({}); await wait(50);
      const cleared = genSettings().reverbMix;
      restore(decodeSetup(code)); await wait(50);
      const g = genSettings();
      const back = [g.reverbMix, g.reverbSize, g.reverbTone, g.reverbPreMs, g.reverbSpread, el.reverbMix.value];
      const old = snapshot();
      for (const k of ['reverbMix', 'reverbSize', 'reverbTone', 'reverbPre', 'reverbSpread']) delete old[k];
      restore(old); await wait(50);
      const g2 = genSettings();
      const fresh = [g2.reverbMix, g2.reverbSize, g2.reverbTone, g2.reverbPreMs, g2.reverbSpread];
      restore({ layers: 'split', bPlane: true, reverbMix: 30, bReverbMix: 90, bReverbSpread: 100 }); await wait(80);
      const own = [genSettings(0).reverbMix, genSettings(1).reverbMix, genSettings(1).reverbSpread, snapshot().bReverbMix];
      restore({}); await wait(50);
      return { cleared, back, fresh, own };
    }""")
    print("    %s" % codes)
    check("a code carries all five out and back into the generator and onto the knobs",
          codes["cleared"] == 0 and codes["back"] == [0.4, 0.65, 0.3, 25, 0.8, "40"], str(codes["back"]))
    check("a code from before the reverb plays none, the rest at their defaults", codes["fresh"] == [0, 0.4, 0.6, 10, 0],
          str(codes["fresh"]))
    check("layer B's own reverb, with B's own effects, apart from A's", codes["own"] == [0.3, 0.9, 1, 90], str(codes["own"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: %d" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("the reverb keeps the figure until it is told to spread")
