"""Every preset does what its heading says (P8g of web/docs/making-it-one-instrument.md).

The bank is four headings named for what the loop does with a chord you hold,
and a heading is a claim about the sound, so it is measured on the sound:

- Settled: a note moves the sound as it strikes the screen, and the sound
  comes to rest while it is held;
- Breathing: it keeps moving while held, and is silent once let go;
- Wandering: it keeps moving while held and goes on sounding, and moving,
  after it is let go - the latch keeping the chord, the loop changing it;
- Open: it never moves at all.

How far the sound moves is read as its spectrum: the left channel's last 4096
samples, Hann-windowed, in forty-eight bands a fifth of an octave wide from
40 Hz, each band's share of the whole as an amplitude, so loudness drops out.
Every quarter second, the distance from the last reading is the movement. One
note held is the probe, since a chord's own partials beat against each other
and move its spectrum with nothing else doing anything (a saw triad with the
loop open moved 0.15 a reading, where one saw note moves nought); a preset
whose line says to play an interval is probed with that interval. In a split,
each hand is judged on its own, since in a mix a quiet hand's movement is
lost under the loud hand's energy, and the two hands of a crossed pair -
each the other's picture - together. A note no lower than C2, since the
window holds too few cycles of anything lower to read its spectrum steadily.

The windows: early, the first two seconds after the key; late, the last three
of ten held; after, from two and a half seconds after the key comes up, when
the longest release in the bank has run out, for two seconds.

    Open       every reading after the first half second under 0.005
    Settled    early at least 0.008, late at most 0.015 and at most half of early
    Breathing  late at least 0.02, and silent after (RMS under 0.005)
    Wandering  late at least 0.02, and after, still sounding (RMS at least 0.02)
               and still moving (at least 0.02)

The thresholds come from measuring the bank as it was built: Settled's lates
were 0.000 to 0.012, Breathing's 0.03 to 0.12. Settled's early floor is low
because the sine bass's strike is gentle (0.015 to 0.020): Scan deep enough
to strike it harder put the held note on a knife edge, settling on one run
and moving for good on the next. The drawbar organ, drawn a ring by the
quarter turn, is the same at 14 against 17, and strikes at 0.011 to 0.016;
the Open presets read exactly nought, so the floor is still clear of them.

What the measure cannot see: below about C3 it has a floor of its own. The
C2 bass with a sub and FM moved 0.010 a reading with the loop switched off -
the window holds too few cycles of the sub and the sidebands to read them
steadily - so a hand that low is judged by the plain sines the bank uses
there, which read nought. Settled's ceiling and
Breathing's floor are kept apart, so a preset between the two fails both and
has to be made one or the other. The rules exclude each other by construction
- a late at most 0.015 cannot be one at least 0.02, a silence after cannot be
a sound - so each preset is required to pass its own heading and fail the
other three, which is the null for every rule at once: a rule that passed
everything would fail the second half on every preset of another heading.

Not the picture meter's verdict. It reads the picture, and was found saying
"settled" for a crossed pair whose sound never stopped moving; what is heard
is the claim. And the limiter: no preset may hold it past six decibels on a
four-note chord, two notes a hand in a split, which is where the meter's own
"running away" begins (STRAINED).

Serial: everything here is measured over real seconds.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
PAGE = f"file://{ART}/scope.html"

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

HOLD, AFTER = 10.0, 4.5

# Hold notes on a preset loaded as a player loads one, with the screen's keys
# open so a note gates the sound as a keyboard's does, and read the sound.
RUN = r"""async ([name, notes, hold, after]) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  setScreenKeys(true);
  applyPreset('b:' + name);
  await wait(900);
  function spectrum(x) {
    const n = x.length, re = new Float64Array(n), im = new Float64Array(n);
    for (let i = 0; i < n; i++) re[i] = x[i] * (0.5 - 0.5 * Math.cos(2 * Math.PI * i / (n - 1)));
    for (let i = 1, j = 0; i < n; i++) { let bit = n >> 1; for (; j & bit; bit >>= 1) j ^= bit; j ^= bit;
      if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; } }
    for (let len = 2; len <= n; len <<= 1) { const a = -2 * Math.PI / len;
      for (let i = 0; i < n; i += len) for (let k = 0; k < len / 2; k++) {
        const c = Math.cos(a * k), s = Math.sin(a * k), u = i + k, v = u + len / 2;
        const tr = re[v] * c - im[v] * s, ti = re[v] * s + im[v] * c;
        re[v] = re[u] - tr; im[v] = im[u] - ti; re[u] += tr; im[u] += ti; } }
    const bands = new Float64Array(48);
    for (let k = 1; k < n / 2; k++) { const f = k * 44100 / n; if (f < 40) continue;
      bands[Math.min(47, Math.floor(Math.log2(f / 40) * 5))] += re[k] * re[k] + im[k] * im[k]; }
    let total = 0; for (const v of bands) total += v;
    return Array.from(bands, (v) => total > 0 ? Math.sqrt(v / total) : 0);
  }
  const out = []; let last = null;
  const read = (t, phase) => {
    // A split hands back a pair a layer; heard, they are summed.
    const w = state.source.getLatestWindow(4096);
    const l = w.length >= 4 ? w[0].map((x, i) => x + w[2][i]) : w[0];
    let e = 0; for (let k = 0; k < l.length; k++) e += l[k] * l[k];
    const sp = spectrum(l);
    let move = 0;
    if (last) { for (let b = 0; b < sp.length; b++) move += (sp[b] - last[b]) ** 2; move = Math.sqrt(move); }
    last = sp;
    out.push({ t, phase, move, rms: Math.sqrt(e / l.length) });
  };
  for (const n of notes) midiBytes(new Uint8Array([0x90, n, 100]));
  const t0 = performance.now();
  while (performance.now() - t0 < hold * 1000) { await wait(250); read((performance.now() - t0) / 1000, 'held'); }
  for (const n of notes) midiBytes(new Uint8Array([0x80, n, 0]));
  const t1 = performance.now();
  while (performance.now() - t1 < after * 1000) { await wait(250); read(hold + (performance.now() - t1) / 1000, 'after'); }
  midiPanic();
  return { out, latch: midi.latch, amount: Number(el.pictureAmount.value) };
}"""

# A chord, and the most the limiter took off while it sounded.
CHORD = r"""async ([name, notes]) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  setScreenKeys(true);
  applyPreset('b:' + name);
  await wait(900);
  for (const n of notes) midiBytes(new Uint8Array([0x90, n, 110]));
  let most = 0;
  for (let k = 0; k < 16; k++) { await wait(125); most = Math.min(most, monitorLimiting()); }
  for (const n of notes) midiBytes(new Uint8Array([0x80, n, 0]));
  midiPanic();
  return most;
}"""

def mean(xs): return sum(xs) / len(xs) if xs else 0.0

def summary(out):
    held = [s for s in out if s["phase"] == "held"]
    after = [s for s in out if s["phase"] == "after" and s["t"] >= HOLD + 2.5]
    return {
        "early": mean([s["move"] for s in held if 0.3 <= s["t"] < 2.0]),
        "late": mean([s["move"] for s in held if s["t"] >= HOLD - 3.0]),
        "most": max([s["move"] for s in held if s["t"] >= 0.5] or [0.0]),
        "afterRms": mean([s["rms"] for s in after]),
        "afterMove": mean([s["move"] for s in after]),
        "heldRms": mean([s["rms"] for s in held if s["t"] >= 0.5]),
    }

RULES = {
    "Open": lambda m: m["most"] < 0.005,
    "Settled": lambda m: m["early"] >= 0.008 and m["late"] <= 0.015 and m["late"] <= m["early"] / 2,
    "Breathing": lambda m: m["late"] >= 0.02 and m["afterRms"] < 0.005,
    "Wandering": lambda m: m["late"] >= 0.02 and m["afterRms"] >= 0.02 and m["afterMove"] >= 0.02,
}

# What each preset is probed with: one note, a hand at a time in a split, or
# what its line asks for.
def probes(name, setup):
    if name == "Crossed hands": return [[48, 67]]      # each hand is the other's picture
    if name == "Turning fifths": return [[48, 55]]     # "Play fifths"
    if setup.get("layers") == "split": return [[36], [67]]
    return [[60]]

def chord(setup):
    return [36, 43, 64, 67] if setup.get("layers") == "split" else [48, 55, 60, 64]

def open_page(pw):
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(PAGE); p.wait_for_timeout(1200)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.locator("#trace").click(position={"x": 5, "y": 5})
    p.wait_for_timeout(600)
    return b, p, bad

with sync_playwright() as pw:
    b, p, bad = open_page(pw)
    bank = p.evaluate("() => PRESETS.map(([section, entries]) => [section, entries.map(([n, s]) => [n, s])])")
    b.close()
    print("\n--- each preset against its heading, by the sound ---")
    results, errors = [], []
    for heading, entries in bank:
        for name, setup in entries:
            for notes in probes(name, setup):
                b, p, bad = open_page(pw)
                run = p.evaluate(RUN, [name, notes, HOLD, AFTER])
                limit = p.evaluate(CHORD, [name, chord(setup)])
                b.close()
                errors += bad
                m = summary(run["out"])
                verdicts = {h: rule(m) for h, rule in RULES.items()}
                results.append((heading, name, notes, m, verdicts, limit))
                print("    %-10s %-24s %-9s early %.3f late %.3f most %.3f | after rms %.3f move %.3f | limiter %.1f dB | %s"
                      % (heading, name, notes, m["early"], m["late"], m["most"], m["afterRms"], m["afterMove"], limit,
                         ",".join(h for h, v in verdicts.items() if v) or "none"))

    for heading in RULES:
        mine = [r for r in results if r[0] == heading]
        check("every %s preset does what the heading says, on every probe" % heading,
              mine and all(r[4][heading] for r in mine),
              "; ".join("%s %s" % (r[1], r[2]) for r in mine if not r[4][heading]) or "%d probes" % len(mine))
    others = [(r[1], r[2], h) for r in results for h, v in r[4].items() if v and h != r[0]]
    check("and none does what another heading says, which every rule is made to fail on the rest",
          not others, str(others))
    # The rules themselves, against readings that sit where each heading's
    # neighbours do, so a rule loosened to pass everything shows here too.
    made = {
        "Open": {"early": 0.001, "late": 0.001, "most": 0.003, "afterRms": 0, "afterMove": 0},
        "Settled": {"early": 0.05, "late": 0.004, "most": 0.08, "afterRms": 0, "afterMove": 0},
        "Breathing": {"early": 0.08, "late": 0.05, "most": 0.2, "afterRms": 0.001, "afterMove": 0},
        "Wandering": {"early": 0.08, "late": 0.05, "most": 0.2, "afterRms": 0.1, "afterMove": 0.05},
    }
    grid = {h: [g for g, rule in RULES.items() if rule(m)] for h, m in made.items()}
    check("each rule passes a reading made to be its heading's and only that one", all(v == [h] for h, v in grid.items()),
          str(grid))
    strained = [(r[1], round(r[5], 1)) for r in results if r[5] < -6]
    check("no preset holds the limiter past six decibels on a four-note chord", not strained, str(strained))
    check("no page errors", not errors, "; ".join(errors[:3]))

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("every preset does what its heading says, measured on the sound")
