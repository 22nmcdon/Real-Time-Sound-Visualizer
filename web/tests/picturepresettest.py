"""The presets where the picture plays itself: are they loops, and do they live?

The photocell and the picture's own sources are what this instrument has that
others do not, and for a long time no preset used them. Asked for a section of
them, the failures to guard against are:

- a "picture" preset that never turns the photocell on, or routes nothing the
  picture says - a figure preset with a misleading name;
- a source that does nothing: the reticle off the trace, reading nought for
  ever, so the value sits at one number and the routing is a constant. Four
  of the first ten candidates were exactly that. So each preset is run and
  each picture source it routes has to MOVE, as looptest asks of its
  stability run;
- a loop that is not one. A source that moves proves the picture reaches the
  control, not that the control reaches back: a figure turning by itself
  moves the reading whatever the routing does. So each loop in the first
  section is run twice, with its picture routings and without them, from a
  cleared meter, and one of two things has to show the loop's hand: the
  meter's verdicts differ by a quarter of the readings or more, or the
  photocell's reading moves by a fifth more than it does without the loop -
  a solid turning slowly is under the meter's floor for change, and plain on
  the reading. Five of the section were rebuilt to pass this, each by taking
  away the motion it had without its loop: an equal fifth made just, a
  solid's own spin set to nought;
- a loop that runs away: the meter's verdict at the end must not be that;
- the one the plan asked for and never had: "a wandering preset - found by
  playing, not designed, and then pinned by the classifier's test". Found by a
  search over loops rather than by playing, and pinned here causally: The
  organ registers itself reads wandering more than anything else with its
  loop, and without it does not. The first pin was on a harmonograph, which
  its null showed wandering with its loop replaced by nothing - pendulums
  that run down and start again wander on their own;
- and presets that use one source each, which was the complaint: the library
  has to have many with two sources and a good number with three or more;
  and then four with five or more, two of them the picture's sources among
  at least three others.

The two sections are the old library's, from before P8g, read from corpus.py:
the bank that replaced it has neither, and these are still the loops this
suite was written to hold. The counts of sources used together are over the
old library and the bank both, the widest set of real setups there is. Where
the section stood in the browser (second in Pictures and sounds) is no longer
asked, since the browser no longer has that menu or the section.
"""
# On ?brain=js (5m): this suite reads the page's own brain - restore() called
# directly, which the page sends the instrument nothing of - which
# core/tests/parity.py holds the instrument to, sample for sample. The
# instrument, the site's default since 5m, is braintest.py's and
# hosttest.py's.
import os, sys
from playwright.sync_api import sync_playwright
import corpus

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
SECONDS = float(os.environ.get("PICTURE_SECONDS", "10"))

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

SECTIONS = ["The picture plays itself", "Played with the picture"]
WANDERER = "The organ registers itself"
# Held to their sources moving and no more: a harmonograph runs down and
# starts again by itself, and wanders with or without the light's hand in it,
# which neither the meter's verdict nor the reading can tell apart.
SELF_MOVED = {"Pendulums bent by the light", "Light feeds the pendulums"}
PICTURE = "/^(photo\\.|picture\\.)/"

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0&brain=js"); p.wait_for_timeout(700)
    corpus.install(p)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    print("\n--- what the sections are ---")
    shape = p.evaluate("""([names]) => {
      const picture = """ + PICTURE + """;
      const uses = (setup) => setup.photoOn === true && decodeRoutings(setup.mod || '').some((r) => picture.test(r.sourceId));
      const out = { missing: [], unpictured: [], counts: {} };
      for (const name of names) {
        const section = CORPUS.find(([s]) => s === name);
        if (!section) { out.missing.push(name); continue; }
        out.counts[name] = section[1].length;
        for (const [preset, setup] of section[1]) if (!uses(setup)) out.unpictured.push(preset);
      }
      // The null: a figure preset, which neither turns the photocell on nor routes the picture.
      out.circle = uses(corpusSetup('Circle'));
      // Sources a preset uses, however many controls each is on.
      const distinct = (setup) => new Set(decodeRoutings(setup.mod || '').map((r) => r.sourceId)
        .concat(setup.l0d ? ['lfo1'] : [], setup.l1d ? ['lfo2'] : [])).size;
      const all = [...CORPUS, ...PRESETS].flatMap(([, e]) => e);
      out.walked = all.length;
      out.two = all.filter(([, s]) => distinct(s) >= 2).length;
      out.three = all.filter(([, s]) => distinct(s) >= 3).length;
      out.most = Math.max(...all.map(([, s]) => distinct(s)));
      /* Five or more, and among them the picture with many others: the next
         ask after "some that use multiple sources". Counted as picture
         sources and the rest separately, so nine picture sources alone would
         not pass as "the picture and many other sources". */
      const sources = (setup) => [...new Set(decodeRoutings(setup.mod || '').map((r) => r.sourceId))];
      const five = all.filter(([, s]) => distinct(s) >= 5);
      out.five = five.map(([n]) => n);
      out.mixed = five.filter(([, s]) => {
        const ids = sources(s);
        return ids.filter((id) => picture.test(id)).length >= 2 && ids.filter((id) => !picture.test(id)).length >= 3;
      }).map(([n]) => n);
      // The null for the count: the same count over the one-source presets alone.
      out.nullTwo = all.filter(([, s]) => distinct(s) === 1).filter(([, s]) => distinct(s) >= 2).length;
      return out;
    }""", [SECTIONS])
    print("    %s" % shape)
    check("a section of the picture playing itself, and one played with it",
          shape["missing"] == [] and shape["counts"]["The picture plays itself"] >= 12
          and shape["counts"]["Played with the picture"] >= 4, str(shape))
    check("every preset in them turns the photocell on and routes something the picture says",
          shape["unpictured"] == [] and shape["circle"] is False, str(shape["unpictured"]))
    print("    five or more: %s; the picture with others: %s" % (shape["five"], shape["mixed"]))
    check("four presets use five sources or more, and two of them the picture's with at least three others",
          len(shape["five"]) >= 4 and len(shape["mixed"]) >= 2 and shape["most"] >= 8,
          "%d with five, %d mixed, at most %d" % (len(shape["five"]), len(shape["mixed"]), shape["most"]))
    check("the library uses sources together: thirty with two or more, twelve with three or more",
          shape["two"] >= 30 and shape["three"] >= 12 and shape["most"] >= 4 and shape["nullTwo"] == 0,
          "%d with two, %d with three, at most %d, of %d walked" % (shape["two"], shape["three"], shape["most"], shape["walked"]))

    print("\n--- each one run: alive, and not running away ---")
    runs = p.evaluate("""async ([names, secs]) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const picture = """ + PICTURE + """;
      const out = [];
      for (const name of names) {
        for (const [preset] of CORPUS.find(([s]) => s === name)[1]) {
          /* The meter cleared first, every run: it keeps fifteen seconds of
             pictures and loading a preset does not clear it, so without this
             each run began with the one before it still in its history - and
             the organ, run without its loop straight after running with it,
             read as wandering on what the loop had drawn. */
          loadCorpus(preset); await wait(300);
          /* A cell in the dark pressed onto the figure, as a player presses
             the reticle (landPhoto). Only one in the dark - under a
             thousandth after a second and a half - since landPhoto's own
             rule, a quarter of the brightest, moved fourteen of the
             twenty-one stored cells and measured something else. A preset's placement is its own
             and restoring it never moves the cell, which is right for the
             instrument and left one preset here a knife edge: The fifth
             detunes itself is a just fifth, whose figure stands still, so
             whether its stored cell is lit depends on the phase the two notes
             inherit from what played before - a faint glow, moving nothing,
             for 45 s on one load, lit on another (9 Nov). Pressed after a
             second and a half, since a figure just loaded (the first
             preset's pendulums) has not drawn yet. Which presets moved is
             reported, and more than two fails, so the stored placements are
             still what is read. */
          let landed = null;
          if (photo.on) await wait(1500);
          if (photo.on && photo.raw < 1e-3) {
            const was = [photo.u, photo.v];
            landPhoto(); await wait(300);
            if (photo.u !== was[0] || photo.v !== was[1]) landed = [photo.u, photo.v];
          }
          pictureMeter.reset();
          const ids = [...new Set(state.modRoutings.map((r) => r.sourceId).filter((id) => picture.test(id)))];
          const lo = {}, hi = {}, verdicts = {};
          const reading = () => { const s = MOD_SOURCES.get('photo.1'); return s ? s.value() : 0; };
          let rlo = Infinity, rhi = -Infinity;
          const t0 = performance.now();
          while (performance.now() - t0 < secs * 1000) {
            await wait(150);
            rlo = Math.min(rlo, reading()); rhi = Math.max(rhi, reading());
            for (const id of ids) {
              const s = MOD_SOURCES.get(id); if (!s) continue;
              const v = s.value(); lo[id] = Math.min(lo[id] ?? v, v); hi[id] = Math.max(hi[id] ?? v, v);
            }
            const v = pictureMeter.verdict(); verdicts[v] = (verdicts[v] || 0) + 1;
          }
          if (modDirty) compileRoutes();
          const compiled = ids.every((id) => MOD_SOURCES.has(id));
          const moved = Math.max(0, ...ids.map((id) => (hi[id] ?? 0) - (lo[id] ?? 0)));
          const row = { preset, section: name, compiled, moved: +moved.toFixed(3), verdict: pictureMeter.verdict(), verdicts,
                        swing: +(rhi - rlo).toFixed(3), landed: landed !== null };
          // The same preset without its picture routings, for the loop's own effect.
          if (name === names[0]) {
            const setup = corpusSetup(preset);
            const kept = decodeRoutings(setup.mod || '').filter((r) => !picture.test(r.sourceId));
            restore(Object.assign({}, setup, { mod: encodeRoutings(kept) }));
            // Without the loop from where the loop was measured: the landed cell, if it was.
            if (landed) movePhoto(landed[0], landed[1]);
            await wait(300); pictureMeter.reset();
            const open = {};
            let olo = Infinity, ohi = -Infinity;
            const t1 = performance.now();
            while (performance.now() - t1 < secs * 1000) {
              await wait(150); const v = pictureMeter.verdict(); open[v] = (open[v] || 0) + 1;
              olo = Math.min(olo, reading()); ohi = Math.max(ohi, reading());
            }
            row.open = open; row.openSwing = +(ohi - olo).toFixed(3);
          }
          out.push(row);
        }
      }
      restore({}); await wait(100);
      return out;
    }""", [SECTIONS, SECONDS])
    def share(v):
        v = {k: n for k, n in v.items() if k != "listening"}
        total = sum(v.values()) or 1
        return {k: n / total for k, n in v.items()}
    def apart(a, b):
        a, b = share(a), share(b)
        return sum(abs(a.get(k, 0) - b.get(k, 0)) for k in set(a) | set(b)) / 2
    for r in runs:
        extra = ("  unlooped %s, apart %.2f, reading %.2f against %.2f"
                 % (r["open"], apart(r["verdicts"], r["open"]), r["swing"], r["openSwing"])) if "open" in r else ""
        print("    %-32s moved %.2f  ends %-12s %s%s" % (r["preset"], r["moved"], r["verdict"], r["verdicts"], extra))
    landed = [r["preset"] for r in runs if r["landed"]]
    print("    pressed onto their figures, their stored cells dark: %s" % (landed or "none"))
    check("at most two presets needed the reticle pressed onto their figure, so the stored placements are read",
          len(landed) <= 2 and len(runs) >= 16, "%d of %d: %s" % (len(landed), len(runs), landed))
    dead = [(r["preset"], r["moved"]) for r in runs if not (r["compiled"] and r["moved"] >= 0.05)]
    check("in every one, the picture's sources are there, move, and are routed onto what they alter",
          dead == [], str(dead))
    loops = [r for r in runs if "open" in r and r["preset"] not in SELF_MOVED]
    same = [(r["preset"], round(apart(r["verdicts"], r["open"]), 2), r["swing"], r["openSwing"]) for r in loops
            if apart(r["verdicts"], r["open"]) < 0.25 and r["swing"] - r["openSwing"] < 0.2]
    check("and each loop changes what the picture does, against itself without the loop: the verdicts or the reading",
          same == [] and len(loops) >= 12, str(same))
    away = [r["preset"] for r in runs if r["verdict"] == "running away"]
    check("and none of them ends running away", away == [], str(away))
    wander = next((r for r in runs if r["preset"] == WANDERER), None) or {}
    heard = {k: v for k, v in wander.get("verdicts", {}).items() if k != "listening"}
    unheard = {k: v for k, v in wander.get("open", {}).items() if k != "listening"}
    check("the wandering preset wanders because of its loop: wandering most with it, and not without it",
          bool(heard) and max(heard, key=heard.get) == "wandering"
          and bool(unheard) and max(unheard, key=unheard.get) != "wandering", "%s; without: %s" % (heard, unheard))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the picture plays itself, and every loop in it is alive")
