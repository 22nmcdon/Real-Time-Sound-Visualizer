"""G1's wavetable: the drawn cycle's bank of four, scanned by a position.

What would go wrong, and what is checked for it:

- a slot that is not the slot. At each whole position the wavetable is that
  slot's drawn cycle, read the drawn cycle's way, sample for sample, band-
  limiting included; between two it is the straight mix of the pair; past
  either end it is the end;
- a default bank that is not what it says. Slot one is a sine, slot two an
  organ's three partials, slot three a saw, slot four a pulse of a quarter,
  held to their harmonics: two and three share a second and a third at -6
  and -9.5 dB, so the fourth tells them apart - none in the organ, -12 in the
  saw - and the pulse has none at the fourth either, but its second is at -3;
- a position nothing reads, a source that cannot move it, a layer B that
  plays A's, a setup code that loses a slot or the position;
- a pane that draws the wrong slot: with the wavetable the switch chooses,
  with the drawn cycle it is always slot one, and Grab fills the slot chosen;
- a section that crowds its tab: with a rack of six and the wavetable
  chosen, no tab scrolls.
"""
import math, os, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
RATE = 44100
BH = [0.35875, 0.48829, 0.14128, 0.01168]

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


def spectrum(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    i = np.arange(n)
    w = (BH[0] - BH[1] * np.cos(2 * np.pi * i / n)
         + BH[2] * np.cos(4 * np.pi * i / n) - BH[3] * np.cos(6 * np.pi * i / n))
    spec = np.abs(np.fft.rfft(x * w))
    return spec, np.arange(len(spec)) * RATE / n


def harmonics(x, f0, count):
    spec, hz = spectrum(x)
    at = lambda f: spec[np.abs(hz - f) < 4 * RATE / len(x)].max()
    ref = at(f0)
    return [round(20 * math.log10(max(float(at(k * f0)), 1e-15) / ref), 1) for k in range(1, count + 1)]


CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('mode', 'wave'); core.set('amp', 0.9); core.set('interval', 0); core.set('phase', 0);
  core.set('wavetable', drawnCycle.bank);
  for (const k in setup.tone) core.set(k, setup.tone[k]);
  for (const k in setup.toneB || {}) core.set(k, setup.toneB[k], 1);
  if (setup.voices) { core.set('voices', setup.voices); core.set('voices', setup.voices, 1); }
  if (setup.route) core.setRoutes([{ held: setup.route, amount: 1, slot: TABLE_SLOT }]);
  const n = setup.n || 44100, L = new Float32Array(n), R = new Float32Array(n);
  const BL = new Float32Array(n), BR = new Float32Array(n);
  core.block(L, R, n, null, null, BL, BR);
  const from = setup.skip || 0;
  return { L: Array.from(L.subarray(from)), BL: Array.from(BL.subarray(from)) };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)
    run = lambda setup: p.evaluate(CORE, setup)

    print("\n--- the slots are the slots ---")
    reads = p.evaluate("""() => {
      // At 2 kHz, so the tables' band-limiting is choosing a level at every
      // sample and a position read some other way would differ.
      const step = 2000 / 44100, bank = drawnCycle.bank, worst = [0, 0, 0, 0];
      let between = 0, ends = 0, other = Infinity;
      for (let i = 0; i < 4410; i++) {
        const ph = (2 * Math.PI * i * step) % (2 * Math.PI);
        const slot = bank.map((c) => waveAt('drawn', ph, step, c));
        for (let k = 0; k < 4; k++) worst[k] = Math.max(worst[k], Math.abs(waveAt('wavetable', ph, step, bank, k) - slot[k]));
        between = Math.max(between, Math.abs(waveAt('wavetable', ph, step, bank, 1.25) - (0.75 * slot[1] + 0.25 * slot[2])));
        ends = Math.max(ends, Math.abs(waveAt('wavetable', ph, step, bank, -1) - slot[0]),
                              Math.abs(waveAt('wavetable', ph, step, bank, 7) - slot[3]));
      }
      // The same comparison against the neighbouring slot, to show it can fail.
      let near = 0;
      for (let i = 0; i < 4410; i++) {
        const ph = (2 * Math.PI * i * step) % (2 * Math.PI);
        near = Math.max(near, Math.abs(waveAt('wavetable', ph, step, bank, 2) - waveAt('drawn', ph, step, bank[1])));
      }
      return { worst, between, ends, near };
    }""")
    print("    %s" % reads)
    check("at 0, 1, 2 and 3 the wavetable is that slot's drawn cycle, exactly, band-limiting included",
          reads["worst"] == [0, 0, 0, 0] and reads["near"] > 0.1, str(reads))
    check("a quarter of the way from slot two to slot three is three parts of two to one of three",
          reads["between"] < 1e-12, "%.1e" % reads["between"])
    check("and past either end it is the end", reads["ends"] == 0, str(reads["ends"]))

    print("\n--- the default bank ---")
    bank = {k: harmonics(run({"tone": {"shape": "wavetable", "table": k, "freq": 220}, "n": 44100 + 4410, "skip": 4410})["L"], 220, 5)
            for k in range(4)}
    for k, h in bank.items():
        print("    slot %d: %s" % (k + 1, h))
    check("slot one is a sine: nothing past the fundamental", all(v < -60 for v in bank[0][1:]), str(bank[0]))
    check("slot two an organ's three partials, half and a third of the fundamental, and no fourth",
          abs(bank[1][1] + 6.0) < 0.3 and abs(bank[1][2] - 20 * math.log10(0.33)) < 0.3 and bank[1][3] < -60, str(bank[1]))
    check("slot three a saw, every harmonic one over n - its fourth at -12 where the organ has none",
          all(abs(bank[2][n - 1] - 20 * math.log10(1 / n)) < 0.3 for n in (2, 3, 4, 5)), str(bank[2]))
    check("slot four a pulse of a quarter: its second at -3, no fourth",
          abs(bank[3][1] + 3.0) < 0.3 and bank[3][3] < -60, str(bank[3]))

    print("\n--- the position, patched and per layer ---")
    fixed = np.array(run({"tone": {"shape": "wavetable", "table": 1.5, "freq": 220}})["L"])
    pushed = np.array(run({"tone": {"shape": "wavetable", "table": 0, "freq": 220}, "route": 1})["L"])
    pulled = np.array(run({"tone": {"shape": "wavetable", "table": 3, "freq": 220}, "route": -1})["L"])
    top = np.array(run({"tone": {"shape": "wavetable", "table": 3, "freq": 220}})["L"])
    past = np.array(run({"tone": {"shape": "wavetable", "table": 2, "freq": 220}, "route": 1})["L"])
    offs = [float(np.abs(pushed - fixed).max()), float(np.abs(pulled - fixed).max()), float(np.abs(past - top).max())]
    check("a source at full moves the position a slot and a half either way - 0 and 3 both land on 1.5 - and stops at 3",
          max(offs) < 1e-6 and float(np.abs(fixed - top).max()) > 0.1, str(["%.1e" % v for v in offs]))
    layered = run({"tone": {"shape": "wavetable", "table": 0}, "toneB": {"shape": "wavetable", "table": 3},
                   "voices": [{"note": 57, "freq": 220, "velocity": 1, "role": "xy"}], "n": 52292, "skip": 8192})
    second_a, second_b = harmonics(layered["L"], 220, 2)[1], harmonics(layered["BL"], 220, 2)[1]
    check("A at slot one has no second harmonic, B at slot four its pulse's -3 dB: B plays its own position",
          second_a < -60 and abs(second_b + 3) < 0.3, "A %.1f, B %.1f" % (second_a, second_b))

    print("\n--- the panel and the pane ---")
    panel = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setView('bench'); setBenchTab('play');
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      const shown = {};
      for (const shape of ['morph', 'drawn', 'wavetable']) {
        el.shape.value = shape; el.shape.dispatchEvent(new Event('change'));
        shown[shape] = [!el.tableRow.hidden, !el.cycleSlots.hidden, !el.cycleGroup.hidden, el.cycleTitle.textContent];
      }
      const start = { reading: el.tableValue.textContent, at: genSettings().table };
      el.table.value = '200'; el.table.dispatchEvent(new Event('input'));
      const set = { reading: el.tableValue.textContent, at: genSettings().table };
      el.table.value = '250'; el.table.dispatchEvent(new Event('input'));
      const late = el.tableValue.textContent;
      return { shown, start, set, late };
    }""")
    print("    %s" % panel)
    check("the Position row and the slot switch show only with Wavetable, the pane with it or the drawn cycle",
          panel["shown"] == {"morph": [False, False, False, "Drawn cycle"], "drawn": [False, False, True, "Drawn cycle"],
                             "wavetable": [True, True, True, "Wavetable"]}, str(panel["shown"]))
    check("it starts between slots two and three, says where it is, and writes the generator",
          panel["start"] == {"reading": "2→3", "at": 1.5} and panel["set"] == {"reading": "3", "at": 2}
          and panel["late"] == "3→4", str(panel))

    p.evaluate("""() => { showControl('cycleCanvas'); el.cycleSlots.querySelector('[data-slot="2"]').click(); }""")
    p.wait_for_timeout(100)
    box = p.evaluate("() => { const r = el.cycleCanvas.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
    x0, y0, w, h = box
    p.mouse.move(x0 + 2, y0 + h * 0.1); p.mouse.down()
    for k in range(1, 41):
        p.mouse.move(x0 + 2 + (w - 4) * k / 40, y0 + h * 0.1)
    p.mouse.up(); p.wait_for_timeout(150)
    drawn = p.evaluate("""() => ({
      editing: drawnCycle.editing,
      flat: drawnCycle.slots[2].filter((v) => Math.abs(v - 0.8) < 0.02).length,
      others: [0, 1, 3].map((k) => cycleIsDefault(k)),
      sent: JSON.stringify(genSettings().wavetable[2]) === JSON.stringify(cycleTables(drawnCycle.slots[2])),
    })""")
    print("    %s" % drawn)
    check("with slot three chosen, a stroke draws slot three and leaves the other three as they were",
          drawn["editing"] == 2 and drawn["flat"] > 240 and drawn["others"] == [True, True, True], str(drawn))
    check("and the generator is sent slot three's new tables", drawn["sent"], str(drawn["sent"]))

    drawnmode = p.evaluate("""() => {
      el.shape.value = 'drawn'; el.shape.dispatchEvent(new Event('change'));
      const onDrawn = drawnCycle.editing;
      el.shape.value = 'wavetable'; el.shape.dispatchEvent(new Event('change'));
      return { onDrawn, back: drawnCycle.editing };
    }""")
    check("with the drawn cycle the pane draws slot one, whatever the switch was left on, and the switch comes back",
          drawnmode == {"onDrawn": 0, "back": 2}, str(drawnmode))

    grabbed = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      // The tone alone at slot one, a sine; Grab takes its own output into
      // the slot chosen, slot three, which was drawn flat above.
      el.table.value = '0'; el.table.dispatchEvent(new Event('input'));
      el.freq.value = '220'; el.freq.dispatchEvent(new Event('input'));
      midiNoteOn(57, 100); await wait(500);
      const ok = grabCycle();
      midiNoteOff(57);
      const s = drawnCycle.slots[2];
      let dot = 0, ss = 0;
      for (let i = 0; i < s.length; i++) { const v = Math.sin(2 * Math.PI * i / s.length); dot += s[i] * v; ss += s[i] * s[i]; }
      return { ok, corr: dot / Math.sqrt(ss * s.length / 2), others: [0, 1, 3].map((k) => cycleIsDefault(k)) };
    }""")
    print("    %s" % grabbed)
    check("Grab fills the slot chosen - slot three, a sine now - and no other",
          grabbed["ok"] and grabbed["corr"] > 0.999 and grabbed["others"] == [True, True, True], str(grabbed))

    print("\n--- setup codes ---")
    codes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const code = snapshot();
      const kept = drawnCycle.slots.map((s) => s.slice());
      restore({ shape: 'wavetable' }); await wait(30);
      const old = [0, 1, 2, 3].map((k) => cycleIsDefault(k));
      restore(code); await wait(30);
      let worst = 0;
      for (let k = 0; k < 4; k++) for (let i = 0; i < 256; i++) worst = Math.max(worst, Math.abs(drawnCycle.slots[k][i] - kept[k][i]));
      const bankSent = JSON.stringify(genSettings().wavetable[2]) === JSON.stringify(cycleTables(drawnCycle.slots[2]));
      restore({ shape: 'wavetable', table: 250, bTable: 50 }); await wait(30);
      const pos = { a: genSettings(0).table, b: genSettings(1).table, slider: el.table.value };
      restore({ shape: 'wavetable', table: 900 }); await wait(30);
      const far = { a: genSettings(0).table, b: genSettings(1).table };
      restore({ shape: 'wavetable' }); await wait(30);
      const plain = { cycles: snapshot().cycles, table: genSettings().table };
      return { parts: code.cycles.split(','), cycle: code.cycle, old, worst, bankSent, pos, far, plain };
    }""")
    print("    %s" % {k: (v if k != "parts" else [len(x) for x in v]) for k, v in codes.items()})
    check("only the slot drawn is in the code: slots two and four empty, three its 344 characters, one a sine's nothing",
          [len(x) for x in codes["parts"]] == [0, 344, 0] and codes["cycle"] == "", str([len(x) for x in codes["parts"]]))
    check("a code without the bank loads the default bank, and a code with it the slots again, within a byte",
          codes["old"] == [True, True, True, True] and codes["worst"] < 1 / 127 and codes["bankSent"],
          "%s, %.4f" % (codes["old"], codes["worst"]))
    check("the position and B's own come back, and past the end is the end on both layers",
          codes["pos"] == {"a": 2.5, "b": 0.5, "slider": "250"} and codes["far"] == {"a": 3, "b": 3}, str(codes))
    check("and a default bank and position say nothing", codes["plain"] == {"cycles": "", "table": 1.5}, str(codes["plain"]))

    fit = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      // Off its default first, so a lane built with the core's own could not
      // pass for one built from the slider.
      el.table.value = '275'; el.table.dispatchEvent(new Event('input'));
      el.rackSynth.checked = true; state.rackSynth = false; await setRackSynth(true);
      // Five short files beside the generator: a rack of six, as racktest.py
      // builds one.
      const wav = (name, hz) => {
        const rate = 44100, n = rate / 4, bytes = 44 + n * 2;
        const buf = new ArrayBuffer(bytes), v = new DataView(buf);
        const str = (o, t) => { for (let i = 0; i < t.length; i++) v.setUint8(o + i, t.charCodeAt(i)); };
        str(0, 'RIFF'); v.setUint32(4, bytes - 8, true); str(8, 'WAVE'); str(12, 'fmt ');
        v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
        v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true);
        v.setUint16(34, 16, true); str(36, 'data'); v.setUint32(40, n * 2, true);
        for (let i = 0; i < n; i++) v.setInt16(44 + i * 2, Math.round(12000 * Math.sin(2 * Math.PI * hz * i / rate)), true);
        return new File([buf], name + '.wav', { type: 'audio/wav' });
      };
      await addRackFiles([1, 2, 3, 4, 5].map((i) => wav('f' + i, 200 + 60 * i)));
      await wait(900);
      el.shape.value = 'wavetable'; el.shape.dispatchEvent(new Event('change'));
      setView('bench');
      const over = {};
      for (const [tab] of BENCH_TABS) { setBenchTab(tab); over[tab] = el.benchBody.scrollHeight - el.benchBody.clientHeight; }
      const out = { lanes: state.source.lanes ? state.source.lanes.length : 0, over, table: genSettings().table,
                    bank: JSON.stringify(genSettings().wavetable) === JSON.stringify(drawnCycle.bank) };
      setView('scope');
      return out;
    }""")
    print("    %s" % fit)
    check("with a rack of six and the wavetable chosen, the Position row and the slot switch showing, no tab scrolls",
          fit["lanes"] == 6 and max(fit["over"].values()) <= 0, str(fit))
    check("and the rack's generator lane takes the slider's position, 2.75, and the bank - slot three as drawn",
          fit["table"] == 2.75 and fit["bank"], "%s, %s" % (fit["table"], fit["bank"]))

    def search(q):
        p.evaluate("(q) => { el.benchSearch.value = q; el.benchSearch.dispatchEvent(new Event('input')); }", q)
        return p.evaluate("""() => Array.from(el.benchResults.querySelectorAll('button'))
          .map((b) => [b.firstChild.textContent, b.querySelector('.crumb').textContent])""")
    # "scan", which is nowhere on the page: "wavetable" finds the row by its
    # destination's label alone, so it could not show the synonym works, and
    # the first version of this check passed on any row called Position.
    found = search("scan")
    check("scan finds the generator's Position", ["Position", "Generator"] in found, str(found[:4]))
    reach = p.evaluate("() => { const d = MOD_DESTS.get('gen.table'); return [d.reach(150, 1), d.reach(0, 1), d.reach(100, -1), d.reach(250, 1)]; }")
    check("full depth on the position is a slot and a half, stopped at both ends",
          reach == [300, 150, 0, 300], str(reach))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("four drawn cycles, scanned by a position a source can move")
