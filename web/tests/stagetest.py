"""The picture stage (P3 of web/docs/making-it-one-instrument.md): the picture
moving the sound always, and the plan's first-minute test.

The test the plan sets the whole instrument: open it, hold a chord, and
within ten seconds hear and see the picture changing the sound. So this opens
the site as a visitor gets it - the instrument in its worklet, the default
setup, the photocell off, nothing routed - holds a chord, and reads what
comes out for ten seconds; then the same with the Picture slider at nought.

What "the picture changing the sound" is measured as: the sound's brightness
(the RMS of its slope over the RMS of itself, which goes as its RMS frequency,
so a fold that adds harmonics raises it) every quarter of a second. Held still,
a chord on the default tone is the same timbre from one second to the next;
with the picture on it, the timbre moves as the picture does. So:

- with the stage, the brightness moves, and it parts from the unstaged chord's
  within ten seconds;
- without it, the brightness stands still - which is the null for the first
  two, since a chord that wandered by itself would pass them;
- and the three reads on screen move, and the bars beside the slider show
  them, so what is heard is also shown.

The stage's own arithmetic is held to the core by core/tests/parity.py; this
is what a visitor gets out of it.
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

# Ten seconds of a held C major chord, read every quarter second: the sound's
# brightness off the instrument's own picture lanes (the left, which is heard
# as it is drawn), and the stage's reads. The amount is set by the slider as
# a hand sets it, so it reaches the worklet the way a hand's does.
RUN = """async ([amount, seconds]) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  el.pictureAmount.value = String(amount);
  el.pictureAmount.dispatchEvent(new Event('input', { bubbles: true }));
  await wait(300);
  for (const n of [60, 64, 67]) midiBytes(new Uint8Array([0x90, n, 100]));
  const start = performance.now(), out = [];
  while (performance.now() - start < seconds * 1000) {
    await wait(250);
    const [l] = state.source.getLatestWindow(4096);
    let e = 0, d = 0;
    for (let k = 1; k < l.length; k++) { e += l[k] * l[k]; d += (l[k] - l[k - 1]) ** 2; }
    // The bars as drawn - each one's fill over its height - beside the reads
    // they paint, taken in one go after a frame has painted them.
    await new Promise((r) => requestAnimationFrame(() => r()));
    // A percentage of the bar as the browser computes the calc, or pixels.
    const bars = [...el.pictureReads.children].map((b) => {
      const h = getComputedStyle(b).backgroundSize.split(' ')[1];
      return h.endsWith('%') ? parseFloat(h) / 100 : parseFloat(h) / b.clientHeight;
    });
    out.push({ t: (performance.now() - start) / 1000, bright: e > 1e-9 ? Math.sqrt(d / e) : 0, rms: Math.sqrt(e / l.length),
               glow: pictureStage.glow, motion: pictureStage.motion, memory: pictureStage.memory, bars,
               faded: Number(getComputedStyle(el.pictureReads).opacity),
               // How lit each control is, and the label colours it makes:
               // the fold, which the stage moves, and the frequency, which it
               // does not.
               lit: Object.fromEntries(['gen.fold', 'gen.echo', 'gen.twist', 'gen.phase', 'gen.freq'].map((d) => {
                 const row = document.querySelector('[data-mod-dest="' + d + '"]');
                 return [d, row ? row.style.getPropertyValue('--picture') : null]; })),
               foldInk: getComputedStyle(document.querySelector('[data-mod-dest="gen.fold"] > .menu-label')).color,
               freqInk: getComputedStyle(document.querySelector('[data-mod-dest="gen.freq"] > .menu-label')).color });
  }
  for (const n of [60, 64, 67]) midiBytes(new Uint8Array([0x80, n, 0]));
  return { out, brain: BRAIN_IN_CORE && state.source.kind === 'host', photo: photo.on, routings: state.modRoutings.length };
}"""

def open_page(pw):
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(PAGE); p.wait_for_timeout(1200)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    # The first press, which a browser waits for before it plays anything.
    p.locator("#trace").click(position={"x": 5, "y": 5})
    p.wait_for_timeout(800)
    return b, p, bad

def spread(xs): return max(xs) - min(xs) if xs else 0

with sync_playwright() as pw:
    print("\n--- the first minute: a chord held on the site as it opens ---")
    runs = {}
    for amount in (60, 0):
        b, p, bad = open_page(pw)
        runs[amount] = p.evaluate(RUN, [amount, 10])
        runs[amount]["bad"] = bad
        b.close()
    on, off = runs[60]["out"], runs[0]["out"]
    print("    with the stage:    brightness %s" % " ".join("%.3f" % s["bright"] for s in on[::4]))
    print("    at nought:         brightness %s" % " ".join("%.3f" % s["bright"] for s in off[::4]))
    print("    reads, with it:    glow %s" % " ".join("%.2f" % s["glow"] for s in on[::4]))
    print("                       motion %s" % " ".join("%.2f" % s["motion"] for s in on[::4]))
    sounding = [s for s in on if s["rms"] > 0.02]
    check("the site opens as a visitor gets it: the photocell off, nothing routed, and the chord heard",
          runs[60]["brain"] and not runs[60]["photo"] and runs[60]["routings"] == 0 and len(sounding) > len(on) // 2,
          "%d of %d windows sounding" % (len(sounding), len(on)))

    # From the second second, once the notes have struck and the picture has
    # something on it.
    late_on = [s["bright"] for s in on if s["t"] >= 1.5]
    late_off = [s["bright"] for s in off if s["t"] >= 1.5]
    base = sum(late_off) / max(1, len(late_off))
    moved_on, moved_off = spread(late_on) / base, spread(late_off) / base
    check("with the picture on it the chord's timbre moves: its brightness spans more than a tenth",
          moved_on > 0.1, "%.3f of the unstaged chord's" % moved_on)
    check("and at nought the same chord stands still, so the moving is the picture's", moved_off < 0.02,
          "%.4f" % moved_off)
    parted = next((s["t"] for s in on if s["t"] >= 1 and abs(s["bright"] - base) / base > 0.05), None)
    check("the sound parts from the unstaged chord by a twentieth within ten seconds",
          parted is not None and parted <= 10, "at %s s" % ("%.1f" % parted if parted else "never"))
    check("and the reads on screen move while it does: Glow or Motion across more than a third",
          max(spread([s["glow"] for s in on]), spread([s["motion"] for s in on])) > 0.33,
          "glow %.2f, motion %.2f" % (spread([s["glow"] for s in on]), spread([s["motion"] for s in on])))
    # The bars against the reads they show, a frame apart at most: within a
    # tenth, each, and moving - so bars that stood at nought would fail the
    # first, and the second fails if the reads did not move either. Faded at
    # nought, so a stage switched off does not look like a stage reading
    # nothing.
    def bar_gap(run): return max(abs(s["bars"][k] - s[key]) for s in run for k, key in enumerate(("glow", "motion", "memory")))
    def bar_span(run): return max(spread([s["bars"][k] for s in run]) for k in range(3))
    check("the three bars beside the slider show the three reads, and move with them",
          bar_gap(on) < 0.1 and bar_span(on) > 0.33, "%.3f apart at worst, spanning %.2f" % (bar_gap(on), bar_span(on)))
    check("and the check fails on bars held at nought", bar_gap([dict(s, bars=[0, 0, 0]) for s in on]) >= 0.1)
    check("and at nought they are faded to a third", on[-1]["faded"] > 0.7 and abs(off[-1]["faded"] - 0.35) < 0.01,
          "%.2f with the stage, %.2f at nought" % (on[-1]["faded"], off[-1]["faded"]))
    # Each control the stage moves is lit by how far, and nothing else is.
    STAGED = ("gen.fold", "gen.echo", "gen.twist", "gen.phase")
    # A colour as three channels out of 255, whichever way the browser wrote
    # it: color-mix comes back as color(srgb 0.42 ...), a plain one as rgb().
    def ink(text):
        import re
        nums = [float(x) for x in re.findall(r"[\d.]+", text)][:3]
        return tuple(round(n * 255) if text.startswith("color(") else round(n) for n in nums)
    def lit(run, d): return [float(s["lit"][d] or 0) for s in run]
    def lights(run):
        most = max(max(lit(run, d)) for d in STAGED)
        peak = max(run, key=lambda s: float(s["lit"]["gen.fold"] or 0))
        return most > 0.3 and all(s["lit"]["gen.freq"] == "" for s in run) and ink(peak["foldInk"]) != ink(peak["freqInk"])
    check("each control the picture moves is lit by how far, its label coloured; one it does not move, never",
          lights(on), "most lit %s; fold %s" % ({d: round(max(lit(on, d)), 2) for d in STAGED}, sorted(set(lit(on, "gen.fold")))[-3:]))
    check("and at nought none is lit, every label its own colour - which the check also fails on",
          all(max(lit(off, d)) == 0 for d in STAGED) and all(ink(s["foldInk"]) == ink(s["freqInk"]) for s in off) and not lights(off),
          "%s against %s" % (off[-1]["foldInk"], off[-1]["freqInk"]))
    check("no page errors", not runs[60]["bad"] and not runs[0]["bad"], "; ".join((runs[60]["bad"] + runs[0]["bad"])[:3]))

    print("\n--- the amount is the player's ---")
    # Like the pedal it is meant for: a preset, which does not name it, leaves
    # it where the hand put it; a setup that names it sets it, and a saved
    # code carries it; and ?picture=N opens the page with it there, which is
    # how every suite that measures something else takes the stage out.
    b, p, bad = open_page(pw)
    kept = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const set = (v) => { el.pictureAmount.value = String(v); el.pictureAmount.dispatchEvent(new Event('input', { bubbles: true })); };
      set(25); applyPreset('b:Pure sine'); await wait(300);
      const afterPreset = el.pictureAmount.value;
      restore({ pictureAmount: 80 });
      const named = el.pictureAmount.value;
      set(30); const code = encodeSetup(snapshot()); set(70);
      restore(decodeSetup(code)); const saved = el.pictureAmount.value;
      return { afterPreset, named, saved, routes: stageRoutings().length };
    }""")
    b.close()
    check("a preset leaves the amount where the hand put it; a setup naming it sets it; a saved code carries it",
          kept == {"afterPreset": "25", "named": "80", "saved": "30", "routes": 4}, str(kept))
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(); p.goto(PAGE + "?picture=0"); p.wait_for_timeout(1000)
    opened = p.evaluate("() => { applyPreset('b:Pure sine'); return { value: el.pictureAmount.value, routes: stageRoutings().length }; }")
    b.close()
    check("and ?picture=0 opens it at nought, with no stage routes, and keeps it so through a preset",
          opened == {"value": "0", "routes": 0}, str(opened))

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the picture plays the sound from the first minute")
