"""Stage E3: the loop closed through the sound, and held to its bounds.

E1 refused every destination that could add energy. E3 lets the loop through
them, and what stands in place of the refusal is a set of defences that only
work together: each source's reach, the slew on every picture source, ONE total
per destination for everything the loop pushes into it, and the limiter last in
every chain. So what is checked:

- the total, on a picture destination and on a generator parameter, with three
  picture sources forced to full: a destination moves by the total's bound and
  not by three times a source's reach - measured on the generator by the pitch
  it actually produces, not by the routes it was given;
- that a source which is NOT the loop is not caught in the loop's bound;
- boredom: it rises while the picture is stuck, stays under its own reach,
  drains when the picture moves, and cannot wind up;
- that the photocell reaches the sound itself, through the worklet;
- and the plan's stability run: every picture source routed at the most it is
  allowed onto the most sensitive destinations, and the picture stage (P3) at
  its top as well, from silence and from a full-scale figure, and once more
  with Scan (P7a) at its top beside it all; then Scan at its top with every
  note striking the screen at full (P7b) during fast repeated notes, and a
  split with both layers at Scan's top, each reading the other's picture -
  two feedback paths feeding each other; and the phaser (P8e) at its top
  with its resonance at its most, a feedback inside the loop. Run headless,
  with every bound checked every tenth of a second - and checked to have
  MOVED, because a loop that did nothing would pass any bound there is.

The plan asked for 60 seconds. It is 30 from each seed, 60 in all, because the
suite is run while working and a minute per seed would double this file.

Since stage 5, step 3 (batches 3 and 5), all of that is the core's, in
core/tests/pieces/loop.py, the stability runs rendered offline by render_cpp;
what is left here is the speakers' chain on the site, which the page owns.
"""
# On the site's default since stage 5, step 3, batch 5 (13 Nov). It opened
# ?brain=js (and ?brain=js&core=js for the Scan seeds, the only page that
# handed its tables out) until then. Its numbers are the core's now,
# core/tests/pieces/loop.py: the loop's total, boredom and the photocell
# reaching the sound since batch 3, and since batch 5 the stability runs - the
# seven seeds, the reverb in the loop, Scan's tables moving, the crossed pair
# and the holds - rendered offline by render_cpp for thirty seconds of audio
# and read every tenth of a second of it, the same every run, where here they
# were thirty real seconds a seed and the flakiest rows in the suite; and the
# meter's rule that a limited picture is running away, on picture_cpp's meter.
# What is left is the face's: the monitor chain the instrument's sound reaches
# the speakers through (syncMonitor), which since stage 5, step 5a has no
# limiter of its own - the instrument limits and clamps itself, and the
# pieces hold every seed under full scale - and the face's meter reading the
# instrument's limiter.
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
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    corpus.old_opening(p)  # the opening it was written against (P8h)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)
    # A note held in Mono, by the button and the keyboard, so the instrument
    # sounds and its sound has a chain to the speakers.
    corpus.held_tone(p)
    p.wait_for_timeout(600)

    # One total per destination, the generator playing the bounded pitch,
    # amplitude's law through the combined route, boredom and the photocell
    # moving the pitch you hear are core/tests/pieces/loop.py's since batch 3;
    # the stability runs and the limited meter's verdict since batch 5.

    print("\n--- the speakers' chain, as the limiter sees it ---")
    # Since stage 5, step 5a the limiter is the instrument's own (scope/
    # limiter.h, held to the browser's node to the bit by parity), and the
    # face's chain for its sound has none: what the face's meter reads is the
    # instrument's reduction, posted with its readings. So the instrument is
    # driven hot - a chord of six at full Level in Poly, which strains it past
    # six decibels - and the face must see that; a held sine is the null.
    # The reading itself matters: asserting only that it was nought or below
    # passed for a monitorLimiting that always answered nought.
    hot = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      await wait(600);
      const quiet = monitorLimiting();
      el.midiPoly.click();
      el.amp.value = '100'; el.amp.dispatchEvent(new Event('input', { bubbles: true }));
      for (const n of [45, 52, 57, 61, 64, 69]) midiNoteOn(n, 127);
      await wait(1500);
      const limiting = monitorLimiting(), posted = state.source.limiting;
      for (const n of [45, 52, 57, 61, 64, 69]) midiNoteOff(n);
      await wait(300);
      return { quiet, hot: limiting, posted, chains: monitorChains.size, own: [...monitorChains].map((c) => !!c.limiter) };
    }""")
    print("    %s" % hot)
    check("the face reads the instrument's limiter pulling a hot chord down",
          hot["hot"] < -6 and hot["hot"] == hot["posted"] and hot["own"] == [False], str(hot))
    check("null: and a held sine's not", hot["quiet"] > -1, str(hot["quiet"]))
    # And the chain's backstop: fed twelve times full scale after the
    # instrument (as "Speakers get: Shaped" can lift a peak), what leaves for
    # the speakers is still under one, where before it the sound is not.
    back = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const chain = [...monitorChains][0];
      if (!chain) return {};
      const ctx = chain.ctx, osc = ctx.createOscillator(), gain = ctx.createGain();
      const pre = ctx.createAnalyser(), post = ctx.createAnalyser();
      pre.fftSize = post.fftSize = 2048;
      chain.merger.connect(pre); chain.clamp.connect(post);
      const buf = new Float32Array(2048);
      const peakOf = (a) => { a.getFloatTimeDomainData(buf); let m = 0; for (const v of buf) m = Math.max(m, Math.abs(v)); return m; };
      gain.gain.value = 12; osc.connect(gain); gain.connect(chain.input); osc.start();
      let most = { pre: 0, post: 0 };
      for (let k = 0; k < 8; k++) { await wait(50); most.pre = Math.max(most.pre, peakOf(pre)); most.post = Math.max(most.post, peakOf(post)); }
      osc.stop(); gain.disconnect(); pre.disconnect(); post.disconnect();
      await wait(300);
      return most;
    }""")
    check("what leaves the chain for the speakers never passes full scale, fed twelve times it",
          back.get("post") is not None and 0.1 < back["post"] < 1.0, str(back))
    check("null: before the backstop the same sound does pass full scale", back.get("pre", 0) > 1.0, str(back.get("pre")))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the speakers' chain holds what the loop sends it; the loop's own bounds are the core's (pieces/loop.py)")
