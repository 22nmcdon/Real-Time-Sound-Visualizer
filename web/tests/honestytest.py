"""Every preset does what its heading says (P8g and P8h of web/docs/making-it-one-instrument.md).

The bank is two headings named for what the loop does with a chord you hold,
and a heading is a claim about the sound, so it is measured on the sound:

- Settled: a note moves the sound as it strikes the screen, and the sound
  comes to rest while it is held;
- Breathing: it keeps moving while held, and is silent once let go.

And two more rules no preset may meet. Still - the sound never moves - is the
base the instrument opens on (BASE_SETUP), measured here too and required to
be it; the Open presets that were still went to become the base in P8h.
Wandering, which went on sounding after the keys came up, went with the latch
it rested on: a Breathing sound under the pedal is the same thing, told by
the player rather than guessed.

How far the sound moves is read as its spectrum: the left channel's last 4096
samples, Hann-windowed, in forty-eight bands a fifth of an octave wide from
40 Hz, each band's share of the whole as an amplitude, so loudness drops out.
Every quarter second, the distance between that window and the one a
quarter second of samples before it, taken together from the ring, is the
movement: on the sound's own clock, not the timer's (12 Nov). One
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

    Still      every reading after the first half second under 0.005
    Settled    early at least 0.008, late at most 0.015 and at most half of early
    Breathing  late at least 0.019, and silent after (RMS under 0.005)

The thresholds come from measuring the bank as it was built: Settled's lates
were 0.000 to 0.012, Breathing's 0.03 to 0.12. Settled's early floor is low
because the sine bass's strike is gentle (0.015 to 0.020): Scan deep enough
to strike it harder put the held note on a knife edge, settling on one run
and moving for good on the next. The drawbar organ, drawn a ring by the
quarter turn, is the same at 14 against 17, and strikes at 0.011 to 0.016;
the still base reads exactly nought, so the floor is clear of it.

What the measure cannot see: below about C3 it has a floor of its own. The
C2 bass with a sub and FM moved 0.010 a reading with the loop switched off -
the window holds too few cycles of the sub and the sidebands to read them
steadily - so a hand that low is judged by the plain sines the bank uses
there, which read nought. Settled's ceiling and
Breathing's floor are kept apart, so a preset between the two fails both and
has to be made one or the other. The rules exclude each other by construction
- a late at most 0.015 cannot be one at least 0.019, an early of 0.008 cannot
be still - so each preset is required to pass its own heading and fail the
others, which is the null for every rule at once: a rule that passed
everything would fail the second half on every preset of another heading.

Not the picture meter's verdict. It reads the picture, and was found saying
"settled" for a crossed pair whose sound never stopped moving; what is heard
is the claim. And the limiter: no preset may hold it past six decibels on a
four-note chord, two notes a hand in a split, which is where the meter's own
"running away" begins (STRAINED).

A preset is held to its heading as shipped, and to nothing else (17 Nov, the
owner's rule): a change it does not contain - the reverb's switch pressed,
the Plane's, the EQ's - may take it under another heading, and that is not a
fault ("reverb causing a preset to turn breathing when turned on is totally
acceptable because reverb was not present in the preset"). Until then this
suite pressed the reverb's switch and the Plane's on every preset and
required each to keep its heading; both passes went, and with them the Tine
piano's reverb run that had failed for days. What stays of the reverb is a
bound on the reverb, not on a heading: at its fullest - Mix, Spread and Size
at the top - a held Settled note may breathe, as one at the Delay's full Mix
may, but no more than 0.10 late, which is churn rather than breath.

Offline, and at five moments (20 Nov). The page loads each preset as a
player does and hands over the setup code it sends the instrument, and the
instrument plays it on the core rendered offline (render_cpp), with the key
at 0.9, 1.0, 1.25, 1.5 and 2.0 s after the load; a preset is judged by its
worst moment against its heading. Until then the sound was read off the
page in real time with the key wherever the page's timing put it, and how a
held note moves depends on where in the loop's own state it lands: the Slow
pad, rendered offline with nothing else changed, read 0.0195 to 0.034 late
over those five moments, under Breathing's floor of 0.02 then at 1.0 s (it is
0.019 since, the owner's exception, at RULES below). Run on the page it
was a verdict by lot, which load only reshuffled. The limiter's chord is
rendered the same way, its key at 0.9 s.

Parallel: offline renders; the browser only loads the presets.
"""
import json, math, os, subprocess, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
PAGE = f"file://{ART}/scope.html"

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    check("null: " + name, red, detail)

HOLD, AFTER = 10.0, 4.5
# How the picture responds (11 Nov): every run on the bank's own, Change unless
# a preset says, or HONESTY_RESPONDS=level (or both) to measure the bank under
# another, as the change was reported. The suite runs the bank as it ships.
RESPONDS = os.environ.get("HONESTY_RESPONDS")
def responding(wet): return dict(wet or {}, pictureResponds=RESPONDS) if RESPONDS else wet

# A preset loaded as a player loads one, with the screen's keys open so a
# note gates the sound as a keyboard's does: the setup code the instrument is
# sent, which the renders below play.
LOAD = r"""async ([value, wet]) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  setScreenKeys(true);
  applyPreset(value);
  let pressed = false;
  // The reverb over the preset as a player would: its switch pressed, or
  // its knobs turned, one by one.
  for (const [id, v] of Object.entries(wet || {})) {
    // A switch by its module's name, the reverb's for true; the Plane's only
    // where the preset has it off, since on a preset shaped already it would
    // switch the shaping off rather than give its start.
    if (id === 'switch') {
      const fx = v === true ? 'reverb' : v;
      if (fx !== 'plane' || !fxOn('plane')) { document.querySelector('[data-fx-on="' + fx + '"]').click(); pressed = true; }
      continue;
    }
    // How the picture responds (11 Nov), a menu: HONESTY_RESPONDS below.
    if (id === 'pictureResponds') { el[id].value = v; el[id].dispatchEvent(new Event('change')); continue; }
    el[id].value = String(v); el[id].dispatchEvent(new Event('input'));
  }
  await wait(300);
  return { code: encodeSetup(snapshot()), latch: midi.latch, amount: Number(el.pictureAmount.value), pressed,
           reverb: { mix: genSettings().reverbMix, spread: genSettings().reverbSpread, size: genSettings().reverbSize } };
}"""

HERE_ = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.join(os.path.dirname(os.path.dirname(HERE_)), "core")
BUILD = os.path.join(CORE, "build", "honesty")
os.makedirs(BUILD, exist_ok=True)
RENDER = os.path.join(BUILD, "render_cpp")
subprocess.run(["g++", "-std=c++17", "-O2", "-I", os.path.join(CORE, "include"),
                os.path.join(CORE, "tests", "tools", "render_cpp.cpp"), "-o", RENDER], check=True)
RATE, N, GAP = 48000, 4096, 12000
MOMENTS = (0.9, 1.0, 1.25, 1.5, 2.0)

def render(lines, record=None):
    """render_cpp on a script; its printed lines, and the six picture lanes if asked."""
    tag = "%d-%d" % (os.getpid(), abs(hash(json.dumps(lines))) % 10**9)
    script, lanes = os.path.join(BUILD, "s-%s.txt" % tag), os.path.join(BUILD, "l-%s.f32" % tag)
    if record: lines = lines[:1] + [["record", "lanes", lanes]] + lines[1:] + [["record", "lanes"]]
    with open(script, "w") as f: f.write("\n".join(json.dumps(l) for l in lines) + "\n")
    out = subprocess.run([RENDER, script], check=True, capture_output=True, text=True).stdout
    got = np.fromfile(lanes, dtype=np.float32).reshape(-1, 6) if record else None
    for path in (script, lanes):
        if os.path.exists(path): os.remove(path)
    return out, got

HANN = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(N) / (N - 1))
# The page's forty-eight fifth-of-an-octave bands from 40 Hz, its bins labelled at 44.1 kHz as it labelled them.
_f = np.arange(N // 2) * 44100 / N
BAND = np.full(N // 2, -1)
BAND[1:] = np.where(_f[1:] >= 40, np.minimum(47, np.floor(np.log2(np.maximum(_f[1:], 1e-9) / 40) * 5)), -1)
def spectrum(x):
    p = np.abs(np.fft.fft(x * HANN)[:N // 2]) ** 2
    bands = np.bincount(BAND[BAND >= 0].astype(int), weights=p[BAND >= 0], minlength=48)
    total = bands.sum()
    return np.sqrt(bands / total) if total > 0 else bands

def held_note(code, notes, at):
    """The readings of notes held HOLD seconds from `at` and let go: every quarter second
    of the sound after the key, the movement between a window and the one a quarter
    second before it, and the window's RMS, as the page read them."""
    _, lanes = render([["make", RATE, code], ["to", at]] + [["midi", 0x90, n, 100] for n in notes]
                      + [["to", at + HOLD]] + [["midi", 0x80, n, 0] for n in notes] + [["to", at + HOLD + AFTER + 0.1]], record=True)
    # A split hands back a pair a layer; heard, they are summed (the second pair is silence with one).
    l = lanes[:, 0].astype(np.float64) + lanes[:, 2]
    on, out = int(round(at * RATE)), []
    for k in range(1, int(RATE * (HOLD + AFTER)) // GAP + 1):
        end, t = on + k * GAP, k * GAP / RATE
        w = l[end - N - GAP:end]
        move = 0.0 if k == 1 else float(np.sqrt(((spectrum(w[GAP:]) - spectrum(w[:N])) ** 2).sum()))
        out.append({"t": t, "phase": "held" if t <= HOLD else "after", "move": move, "rms": float(np.sqrt((w[GAP:] ** 2).mean()))})
    return out

def judged(code, notes):
    """Each moment's summary, and the verdicts that hold at every one of them."""
    ms = [summary(held_note(code, notes, at)) for at in MOMENTS]
    return ms, {h: all(rule(m) for m in ms) for h, rule in RULES.items()}

def limiter_on_chord(code, notes):
    """The most the instrument's limiter took off a chord held two seconds, read every eighth."""
    out, _ = render([["make", RATE, code], ["to", 0.9]] + [["midi", 0x90, n, 110] for n in notes]
                    + [["every", 0.125, "limiter"], ["to", 2.9]])
    return min([0.0] + [float(line.split()[2]) for line in out.split("\n") if line.startswith("limiter ")])

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
    "Still": lambda m: m["most"] < 0.005,
    "Settled": lambda m: m["early"] >= 0.008 and m["late"] <= 0.015 and m["late"] <= m["early"] / 2,
    # Breathing's floor was 0.02 until 20 Nov, and is 0.019 by the owner's own
    # exception to the rule of 17 Nov that a bound is not loosened to pass a
    # preset: the Slow pad, kept as shipped by the owner's choice (20 Nov), read
    # 0.0195 late at its worst moment (the key at 1.0 s). Settled's ceiling stays
    # 0.015, so the gap between the headings remains and a preset between them
    # still fails both. Not to be lowered again for another preset.
    "Breathing": lambda m: m["late"] >= 0.019 and m["afterRms"] < 0.005,
}

# What each preset is probed with: one note, a hand at a time in a split, or
# what its line asks for.
def probes(value, setup):
    name = value[2:]
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
    errors = []
    bank = p.evaluate("() => PRESETS.map(([section, entries]) => [section, entries.map(([n, s]) => ['b:' + n, s])])")
    # The base, as New and the opening page load it, judged as Still.
    bank.append(p.evaluate("() => ['Still', [['n:' + BASE_NAME, BASE_SETUP]]]"))
    b.close()
    # One page loads every preset, each from a fresh one so nothing carries over.
    class Loader:
        def evaluate(self, js, args):
            b, p, bad = open_page(pw)
            try: return p.evaluate(js, args)
            finally: errors.extend(bad); b.close()
    page = Loader()
    moments = lambda ms, k: "/".join("%.3f" % m[k] for m in ms)
    print("\n--- each preset against its heading, by the sound ---")
    results = []
    for heading, entries in bank:
        for name, setup in entries:
            run = page.evaluate(LOAD, [name, responding(None)])
            limit = limiter_on_chord(run["code"], chord(setup))
            for notes in probes(name, setup):
                ms, verdicts = judged(run["code"], notes)
                results.append((heading, name, notes, ms, verdicts, limit))
                print("    %-10s %-24s %-9s early %s late %s | most %.3f | after rms %.3f | limiter %.1f dB | %s"
                      % (heading, name, notes, moments(ms, "early"), moments(ms, "late"), max(m["most"] for m in ms),
                         max(m["afterRms"] for m in ms), limit, ",".join(h for h, v in verdicts.items() if v) or "none"))

    for heading in [h for h, _ in bank]:
        mine = [r for r in results if r[0] == heading]
        check("every %s preset does what the heading says, on every probe" % heading,
              mine and all(r[4][heading] for r in mine),
              "; ".join("%s %s" % (r[1], r[2]) for r in mine if not r[4][heading]) or "%d probes" % len(mine))
    # The parent's null for the worst-moment verdict (20 Nov): a Settled preset
    # judged as Breathing over the same five moments is red, every one.
    settled = [r for r in results if r[0] == "Settled"]
    null("every Settled preset judged as Breathing, at its worst moment, fails it",
         settled and not any(r[4]["Breathing"] for r in settled), "%d probes" % len(settled))
    others = [(r[1], r[2], h) for r in results for h, v in r[4].items() if v and h != r[0]]
    check("and none does what another heading says, which every rule is made to fail on the rest",
          not others, str(others))
    # The rules themselves, against readings that sit where each heading's
    # neighbours do, so a rule loosened to pass everything shows here too.
    made = {
        "Still": {"early": 0.001, "late": 0.001, "most": 0.003, "afterRms": 0, "afterMove": 0},
        "Settled": {"early": 0.05, "late": 0.004, "most": 0.08, "afterRms": 0, "afterMove": 0},
        "Breathing": {"early": 0.08, "late": 0.05, "most": 0.2, "afterRms": 0.001, "afterMove": 0},
    }
    grid = {h: [g for g, rule in RULES.items() if rule(m)] for h, m in made.items()}
    check("each rule passes a reading made to be its heading's and only that one", all(v == [h] for h, v in grid.items()),
          str(grid))
    # P9, the reverb (9 Nov), and the owner's rule of 17 Nov: Settled
    # promises that a preset as shipped comes to rest, not that it does
    # whatever is added to it, so the reverb is measured here only for how
    # far it can push a held note, never for whether a preset keeps its
    # heading under it.
    def wet_pass(label, wet, headings):
        print("\n--- %s ---" % label)
        out = []
        for heading, entries in bank:
            if heading not in headings: continue
            for name, setup in entries:
                run = page.evaluate(LOAD, [name, responding(wet)])
                for notes in probes(name, setup):
                    ms, verdicts = judged(run["code"], notes)
                    out.append((heading, name, notes, ms, verdicts, run["reverb"], run))
                    print("    %-10s %-28s %-9s early %s late %s | reverb %s | %s"
                          % (heading, name, notes, moments(ms, "early"), moments(ms, "late"), run["reverb"],
                             ",".join(h for h, v in verdicts.items() if v) or "none"))
        return out
    # The cost, kept from growing: every Settled preset at
    # the reverb's fullest. looptest.py holds the safety at that setting (no
    # runaway, every bound); this holds how far a held note goes on moving,
    # measured at 0.001 to 0.060 late over four runs when it was built (the
    # Tine piano alone wandering 0.038 to 0.060 from run to run), to under
    # 0.10, inside Breathing's range - it may breathe, it may not churn as a
    # chorus does (0.4 to 0.6). Of five probes, four moved and the Drawbar
    # organ settled.
    full = wet_pass("the Settled presets with the reverb at its fullest", {"reverbMix": 100, "reverbSpread": 100, "reverbSize": 100},
                    ["Settled"])
    LATE_BOUND = 0.10
    within = lambda late: late < LATE_BOUND
    check("at full Mix, Spread and Size a held Settled note may go on moving, but no more than %.2f late" % LATE_BOUND,
          full and all(within(max(m["late"] for m in r[3])) for r in full),
          ", ".join("%s %.3f" % (r[1][2:], max(m["late"] for m in r[3])) for r in full))
    null("the bound fails what a chorus at full does to the same notes (0.4 to 0.6 late)", not within(0.4))
    check("and each of those runs really had it at full", full and all(r[5] == {"mix": 1, "spread": 1, "size": 1} for r in full),
          str([r[5] for r in full][:2]))
    strained = [(r[1], round(r[5], 1)) for r in results if r[5] < -6]
    check("no preset holds the limiter past six decibels on a four-note chord", not strained, str(strained))
    check("no page errors", not errors, "; ".join(errors[:3]))

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("every preset does what its heading says, measured on the sound")
