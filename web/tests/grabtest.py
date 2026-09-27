"""G2's Grab: one cycle of what is playing, taken as the drawn cycle.

The fixture is a file lane in a rack beside the generator, which is how the
feature is meant to be played - your instrument on one lane, the generator on
another - with a file standing in for the instrument so that its cycle is
known exactly. It is 220 Hz with a second, third and twelfth harmonic at
phases of their own, so the cycle is lopsided: a grab read backwards, upside down or
half a cycle out cannot pass for it. And 44100 / 220 is 200.45 samples, not a
whole number, so a grab that rounds the period to a sample drifts a little
further off every cycle it averages.

Against the way it would fail:

- a cycle that is not the input's: with A3 held, the grabbed points are the
  file's cycle, turned to wherever it starts, to within a byte;
- a cycle that starts anywhere: it starts at an upward crossing of nought,
  with its middle taken out and its peak at the pane's 0.95;
- a grab the generator never hears: the tables sent are those points'
  tables;
- a period that is not the note's: holding B flat instead grabs a visibly
  worse cycle, so it is the held note's period being used, not a measured one
  that happens to agree;
- nothing without a keyboard: with no note held the scope's own measure
  stands in, the result is still close, and the note says it was measured;
- a grab from the wrong lane: with the trigger on the generator's own lane,
  where it starts, Grab looks past it to the file, not back into itself;
  moved to another lane, it takes that one; and with the tone alone, where
  there is nothing else, it takes the generator's own output;
- a grab of nothing: a silent lane, and a steady level that is loud but has
  no cycle in it, are each refused with a reason, and the cycle is left as
  it was;
- averaging that does not average: on a noisy copy of the tone, the grab is
  closer to the true cycle than one cycle of it could be, and still starts
  at the crossing rather than at a wiggle of the noise;
- a reading that crowds the tab, or is not there: with a rack of six, the
  longest reading showing and the pane open, it has a size and no tab
  scrolls;
- a stale reading: drawing afterwards takes it away.
"""
import json, math, os, random, struct, tempfile, wave
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

def cycle(theta):
    # The twelfth is there to be above the eight harmonics Grab looks for its
    # crossing in: without it the eight were the whole wave, crossed exactly
    # where it did, and a Grab that never went on to find the wave's own
    # crossing passed. With it the eight cross 0.8 of a point early.
    return (0.5 * math.sin(theta) + 0.25 * math.sin(2 * theta + 0.7) + 0.15 * math.sin(3 * theta + 1.3)
            + 0.04 * math.sin(12 * theta + 0.4))

HOME = tempfile.mkdtemp(prefix="grabtest-")
def wav(name, fn, seconds):
    # Three seconds of 220 Hz is 660 whole cycles, so the loop joins without
    # a seam for a grab to land on.
    frames = int(seconds * RATE)
    data = bytearray()
    for i in range(frames):
        data += struct.pack("<h", int(max(-1.0, min(1.0, fn(i / RATE))) * 32767))
    path = os.path.join(HOME, name)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(bytes(data))
    return path

# All as long as each other: a rack loops at its longest file, so a shorter
# lane is silent for the rest of the loop - which is how a sine lane first
# read here as "silent".
# The silent lane comes before the tone, so that looking past the generator
# has to look past silence as well: with the tone next to the generator, a
# look-past that took the first other lane, heard or not, passed.
# And a noisy copy of the tone, a twentieth of full scale of seeded noise,
# since on a clean tone one cycle is as good as four and nothing could show
# that the averaging averages.
NOISE = random.Random(7)
NOISE = [NOISE.gauss(0, 1) for _ in range(3 * RATE)]
FILES = [wav("silent.wav", lambda t: 0.0, 3.0),
         wav("tone.wav", lambda t: cycle(2 * math.pi * 220 * t), 3.0),
         # A steady level with a ripple of two bits of 16 in it: loud, and with
         # no cycle worth the name. Held exactly steady it averaged to exactly
         # nought, and a refusal of only exactly nought passed as well as the
         # threshold did - and would have blown the ripple up to full scale.
         wav("level.wav", lambda t: 0.3 + 2 / 32767 * math.sin(2 * math.pi * 220 * t), 3.0),
         wav("fill1.wav", lambda t: 0.3 * math.sin(2 * math.pi * 330 * t), 3.0),
         wav("noisy.wav", lambda t: cycle(2 * math.pi * 220 * t) + 0.05 * NOISE[min(round(t * RATE), 3 * RATE - 1)], 3.0)]

def expected(fn):
    """The cycle as Grab should take it: from its upward crossing of nought -
    each of these has exactly one - middle out, peak at 0.95.

    Found by bisection rather than by trying the 256 turns of the table and
    keeping the best, which is what this first did: the crossing falls
    between two of the 256 points, so the best whole turn was up to half a
    point out, and that alone was 0.0125 of error on this cycle - larger than
    anything Grab itself got wrong, and it hid where the grab started."""
    step = 2 * math.pi / 4096
    th = next(k * step for k in range(-1, 4096) if fn(k * step) < 0 <= fn((k + 1) * step))
    lo, hi = th, th + step
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if fn(mid) < 0 else (lo, mid)
    e = np.array([fn(lo + 2 * math.pi * j / 256) for j in range(256)])
    e -= e.mean()
    return e / np.abs(e).max() * 0.95

def match(got, want):
    """Correlation, and the worst point's error, point for point."""
    g, w = np.asarray(got), np.asarray(want)
    return float(np.dot(g, w) / (np.linalg.norm(g) * np.linalg.norm(w))), float(np.abs(g - w).max())

def turned(got, fn):
    """For a noisy grab: the RMS error at the best turn within ten points of
    the true crossing, found to a fortieth of a point, and that turn. Noise
    moves where the crossing is found a little, and a point-for-point
    comparison would charge that to the shape."""
    e0 = expected(fn)
    g = np.asarray(got)
    k = np.arange(256)
    best = (9.0, 0.0)
    for shift in np.arange(-10, 10, 1 / 40):
        e = np.interp((k + shift) % 256, np.arange(257), np.append(e0, e0[0]))
        best = min(best, (float(np.sqrt(np.mean((g - e) ** 2))), float(shift)))
    return best

FILE_CYCLE = expected(cycle)
SINE = expected(math.sin)

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

    p.locator("#rackInput").set_input_files(FILES); p.wait_for_timeout(1500)
    p.evaluate("() => { el.rackSynth.checked = true; return setRackSynth(true); }"); p.wait_for_timeout(800)
    p.evaluate("() => { el.shape.value = 'drawn'; el.shape.dispatchEvent(new Event('change')); }")
    p.wait_for_timeout(300)
    rack = p.evaluate("() => ({ lanes: state.source.lanes.length, gen: state.source.lanes.indexOf(genLane()), "
                      "names: state.source.lanes.map((l) => l.name), trig: state.trigSource, pane: !el.cycleGroup.hidden })")
    print("    %s" % rack)
    GEN = rack["gen"]
    # The generator is lane 0 and the trigger starts there - which is the case
    # Grab has to look past to find what you are playing.
    if not (rack["names"] == ["Generator", "silent", "tone", "level", "fill1", "noisy"]
            and GEN == 0 and rack["trig"] == 0 and rack["pane"]):
        check("the rack is the generator and five files, triggered on the generator", False, str(rack))
        raise SystemExit(1)

    GRAB = """(how) => {
      const ok = how === 'click' ? (el.cycleGrab.click(), !el.cycleNote.hidden && /^Grabbed/.test(el.cycleNote.title))
                                 : grabCycle();
      return { ok, short: el.cycleNote.hidden ? '' : el.cycleNote.textContent, note: el.cycleNote.title,
               points: drawnCycle.points.slice(),
               sent: JSON.stringify(genSettings().cycle) === JSON.stringify(cycleTables(drawnCycle.points)) };
    }"""

    print("\n--- with the note held ---")
    p.evaluate("() => midiNoteOn(57, 100)"); p.wait_for_timeout(300)
    held = p.evaluate(GRAB, "click")
    corr, worst = match(held["points"], FILE_CYCLE)
    print("    %s | %s; correlation %.6f, worst point %.4f" % (held["short"], held["note"], corr, worst))
    check("with A3 held, Grab takes the file's cycle from its upward crossing, point for point",
          held["ok"] and corr > 0.99999 and worst < 0.003, "%.6f, %.4f" % (corr, worst))
    pts = held["points"]
    check("starting at an upward crossing of nought, its middle taken out and its peak at 0.95",
          abs(pts[0]) < 0.005 and pts[1] > pts[0] + 0.01 and abs(sum(pts) / 256) < 1e-9
          and abs(max(abs(v) for v in pts) - 0.95) < 1e-9,
          "starts %.4f then %.4f, mean %.1e, peak %.6f" % (pts[0], pts[1], sum(pts) / 256, max(abs(v) for v in pts)))
    check("and the generator is sent that cycle's tables", held["sent"])
    check("and the reading says the key was held, and its tooltip names the lane",
          held["short"] == "220.0 Hz, key held" and held["note"].startswith("Grabbed from tone at 220.0 Hz")
          and "from the note you are holding" in held["note"], "%s | %s" % (held["short"], held["note"]))

    p.evaluate("() => { midiNoteOff(57); midiNoteOn(58, 100); }"); p.wait_for_timeout(300)
    wrong = p.evaluate(GRAB, "call")
    wcorr, wworst = match(wrong["points"], FILE_CYCLE)
    print("    B flat held: correlation %.6f, worst point %.4f" % (wcorr, wworst))
    check("holding B flat instead grabs a worse cycle: it is the held note's period that is used",
          wrong["ok"] and wworst > 5 * worst and wworst > 0.05, "%.4f against %.4f" % (wworst, worst))
    p.evaluate("() => midiNoteOff(58)"); p.wait_for_timeout(200)

    print("\n--- with no note ---")
    free = p.evaluate(GRAB, "call")
    fcorr, fworst = match(free["points"], FILE_CYCLE)
    print("    %s; correlation %.6f, worst point %.4f" % (free["note"], fcorr, fworst))
    check("with no note held the scope's measure stands in, and the reading says so",
          free["ok"] and free["short"] == "220.0 Hz, measured" and "period measured" in free["note"],
          "%s | %s" % (free["short"], free["note"]))
    check("and the cycle is still the file's, near enough", fcorr > 0.999, "%.6f, %.4f" % (fcorr, fworst))

    # The layout, with the longest reading there is on show.
    fit = p.evaluate("""() => {
      setView('bench');
      const out = { note: !el.cycleNote.hidden, pane: !el.cycleGroup.hidden, lanes: state.source.lanes.length, over: {} };
      for (const [tab] of BENCH_TABS) { setBenchTab(tab); out.over[tab] = el.benchBody.scrollHeight - el.benchBody.clientHeight; }
      setBenchTab('shape');
      out.shown = el.cycleNote.getBoundingClientRect().height;
      setView('scope');
      return out;
    }""")
    print("    %s" % fit)
    check("with a rack of six, the note showing and the pane open, no tab scrolls",
          fit["note"] and fit["pane"] and fit["lanes"] == 6 and fit["shown"] > 0
          and max(fit["over"].values()) <= 0, str(fit))

    print("\n--- which lane, and when not to ---")
    # The first grab above was taken with the trigger on the generator, and it
    # was the file: that is the looking-past. Here, a lane chosen on purpose.
    p.evaluate("() => { state.trigSource = 4; }"); p.wait_for_timeout(200)  # fill1
    other = p.evaluate(GRAB, "call")
    scorr, _ = match(other["points"], SINE)
    fcorr2, _ = match(other["points"], FILE_CYCLE)
    check("with the trigger on another lane, Grab takes that one: the 330 Hz sine, not the file",
          other["ok"] and other["note"].startswith("Grabbed from fill1 at 330") and scorr > 0.9999 and fcorr2 < 0.98,
          "%s; sine %.6f, file %.6f" % (other["note"], scorr, fcorr2))
    p.evaluate("() => midiNoteOn(57, 100)"); p.wait_for_timeout(200)

    # Twelve grabs of the noisy lane, at different places in its loop. Four
    # cycles averaged came to 0.023 to 0.033 of RMS error; one cycle, the
    # mutant, to 0.043. It was three grabs, and passed, until one run of three
    # caught a grab half a cycle out: the crossing had been the steepest of
    # the average's own, and a wiggle of the noise left in it had won. So it
    # is twelve, which is how many it took to see that twice more.
    noisy = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      state.trigSource = 5;
      const out = [];
      for (let k = 0; k < 12; k++) { grabCycle(); out.push(drawnCycle.points.slice()); await wait(137); }
      return out;
    }""")
    fits = [turned(g, cycle) for g in noisy]
    print("    noisy lane: %s" % ", ".join("%.4f at %+.2f points" % f for f in fits))
    # Where each starts, to 3.5 points. It was 2, and a full run caught a
    # grab at 2.05: what noise is left in the average moves the crossing by
    # its level over the wave's slope there, about 0.7 of a point, so 2 was
    # under three of those and twelve grabs met it one run in twenty. What
    # the check is for is a start half a cycle out - 128 points - and five
    # of them is still nothing like that.
    # The mean over the twelve, not each: what noise is left after four
    # cycles varies from grab to grab, and one of them reached 0.039 in a run
    # whose mean was 0.027. One cycle's mean is 0.04 and more.
    mean = sum(f[0] for f in fits) / len(fits)
    check("on a noisy lane, four cycles averaged bring the noise down, and every grab starts at the crossing",
          mean < 0.033 and all(abs(f[1]) < 3.5 for f in fits),
          "mean RMS %.4f; turns %s" % (mean, [round(f[1], 2) for f in fits]))

    refused = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const out = {};
      for (const [name, lane] of [['silent', 1], ['level', 3]]) {
        state.trigSource = lane;
        await wait(200);
        const before = JSON.stringify(drawnCycle.points);
        const ok = grabCycle();
        out[name] = { ok, short: el.cycleNote.hidden ? '' : el.cycleNote.textContent, note: el.cycleNote.title,
                      kept: JSON.stringify(drawnCycle.points) === before };
      }
      state.trigSource = 0;
      midiNoteOff(57);
      return out;
    }""")
    print("    %s" % refused)
    check("a silent lane is refused, saying so, and the cycle is left as it was",
          refused["silent"]["ok"] is False and refused["silent"]["short"] == "silent" and "silent" in refused["silent"]["note"]
          and refused["silent"]["kept"],
          str(refused["silent"]))
    check("and so is a steady level, with a note held: loud, but with no cycle in it",
          refused["level"]["ok"] is False and refused["level"]["short"] == "flat"
          and "flat" in refused["level"]["note"] and refused["level"]["kept"],
          str(refused["level"]))

    stale = p.evaluate("() => { grabCycle(); const was = !el.cycleNote.hidden; el.cycleSmooth.click(); return [was, !el.cycleNote.hidden]; }")
    check("drawing afterwards takes the reading away", stale == [True, False], str(stale))

    # The tone alone: the generator is all there is, so Grab takes its own
    # output. A drawn sine is played, and the file's cycle is what the
    # points held before, so a grab that read anything but the generator
    # would not come back a sine.
    p.evaluate("(pts) => { drawnCycle.points = pts; cycleSend(); }", json.loads(json.dumps(FILE_CYCLE.tolist())))
    alone = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.srcTone.click(); await wait(500);
      el.shape.value = 'drawn'; el.shape.dispatchEvent(new Event('change'));
      el.cycleSine.click(); midiNoteOn(57, 100); await wait(500);
      const ok = grabCycle();
      midiNoteOff(57);
      return { kind: state.source.kind, ok, note: el.cycleNote.title, points: drawnCycle.points.slice() };
    }""")
    acorr, _ = match(alone["points"], SINE)
    check("with the tone alone, Grab takes the generator's own output, and names no lane",
          alone["kind"] == "tone" and alone["ok"] and acorr > 0.999 and alone["note"].startswith("Grabbed at"),
          "%s: %s, %.6f" % (alone["kind"], alone["note"], acorr))

    # Which crossing, handed to it directly, since a grab timed off a live
    # input starts wherever the loop happens to be. Both were mutants the grabs
    # could not kill: the file's eight harmonics cross upward once, so first
    # and steepest were the same crossing; and a crossing straddling the end
    # of the table comes up by chance about one grab in a hundred.
    #  - 0.4 sin + 0.6 sin(2x + 0.5) crosses upward twice, at 112.82 points
    #    with half the slope and at 248.35: the steeper, from either turn;
    #  - the file's cycle with its crossing 0.3 of a point past the end, where
    #    its eight harmonics cross 0.8 early, at 255.5 - the other side.
    def two(th):
        return 0.4 * math.sin(th) + 0.6 * math.sin(2 * th + 0.5)
    wrap_at = expected(cycle)
    crossing = p.evaluate("""(cases) => cases.map((c) => cycleCrossing(c))""", [
        [two(2 * math.pi * j / 256) for j in range(256)],
        [two(2 * math.pi * (j + 150) / 256) for j in range(256)],
        list(np.interp((np.arange(256) - 0.3) % 256, np.arange(257), np.append(wrap_at, wrap_at[0]))),
    ])
    check("the crossing is the steepest of two, from either turn, and found across the end of the table",
          abs(crossing[0] - 248.353) < 0.05 and abs(crossing[1] - 98.353) < 0.05 and abs(crossing[2] - 0.3) < 0.02,
          "%s, wanting 248.35, 98.35 and 0.30" % [round(c, 3) for c in crossing])

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
