"""P7b: notes strike the screen, each hand can read the other's picture, and
the loop keeps going on its own.

Three things Scan gained after it was built (scantest.py holds Scan itself):

- The strike. Every note lays light on the phosphor as it starts, an arc of
  the circle Scan reads, at the note's place round it, as bright as the
  note's velocity times the Strike amount; it is light like any other and
  fades by the screen's Persistence. Checked against the way it would fail:
  nought (or Scan off) that lays anything at all, a level that is not
  velocity times Strike, light laid somewhere Scan does not read, every note
  struck in one place, a hard note no brighter a tone than a soft one, an
  envelope of its own instead of the phosphor's fade, the meters blind to
  it, and in a split a note struck on the wrong layer's picture.
- Cross-scan. A menu a layer, as P6's pictures have: what that layer's Scan
  reads, its own picture, the other's, or both averaged. Checked: the table
  a layer plays is made from exactly the picture its menu names and not its
  own, both is the average, a crossed pair's depths are held by the lower
  of the two holds and an uncrossed one's each by its own, the menus round a
  setup code and refuse what they do not offer, and the row is shown only
  when there are two pictures.
- The loop that keeps going: presets in which the keys strike the screen
  rather than start the sound, so letting go leaves the loop running. The
  nulls are Stop, which holds the screen and so the tone, and the same
  preset with notes driving the waveform, which falls silent on release.

Since stage 5, step 3, batch 3 (13 Nov) the numbers are the core's own, in
core/tests/pieces/strike.py: the strike, the fade, the meter, a split's
strikes, cross-scan and Crossed hands. Here, on the site as a visitor opens
it: the Reads row and its menus' round trip, and the instrument laying the
strike on the grid it draws itself, read through each layer's picture
readings it hands back. Every assertion has its null beside it.

The presets played here - Scanned fifth, Scan breathes, Scan remembers, Crossed
hands - are the old library's, from before P8g, read from corpus.py: the sounds
these checks were measured on, which the bank has either dropped or (Crossed
hands, with the latch on) changed.
"""
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

def null(name, red, detail=""):
    """A check's null: the same comparison fed a value it must reject."""
    check("null: " + name, red, detail)


with sync_playwright() as pw:
    # Until stage 5, step 3, batch 3 (13 Nov) the first page was the page's
    # own brain (?brain=js&core=js): its keyboard struck its own picture
    # engine on a stopped screen, with `scan.paths` and each layer's stage
    # hold written by hand, and the grid, the reading and the tables were
    # read back through the page's scanRead and scanTables. Those numbers -
    # Strike at nought and Scan off laying nothing, the level, the place
    # round the circle, a hard note against a soft one, the fade, the meter,
    # a split's strikes, cross-scan's tables and holds, and Crossed hands
    # reading the other hand's picture - are core/tests/pieces/strike.py's
    # now, on the core alone, each with its null. What stays here is the
    # face: the Reads row and the menus' round trip through a setup code, on
    # the site as a visitor opens it, the split made by the buttons a hand
    # presses (setMidiMode, which the instrument does not hear, was the old
    # fixture's).
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(900)
    corpus.old_opening(p)  # the opening it was written against (P8h)
    corpus.install(p)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    print("\n--- a split: the Reads row and its menus ---")
    unsplit_row = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      loadCorpus('Scanned fifth'); await wait(300);
      return el.scanReadsRow.hidden;
    }""")
    p.evaluate("() => showControl('midiPoly')")
    p.locator("#midiPoly").click()
    p.evaluate("""() => { el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change', { bubbles: true })); }""")
    p.wait_for_timeout(300)
    row = p.evaluate("() => ({ hidden: el.scanReadsRow.hidden, mode: midi.mode, layers: midi.layers.mode })")
    check("the Reads row is shown while the layers draw a figure each", row["hidden"] is False and row["layers"] == "split", str(row))
    null("before the split, with one picture, it is hidden", unsplit_row is True, str(unsplit_row))

    xs = p.evaluate("""() => {
      const set = (a, b) => {
        el.scanReadsA.value = a; el.scanReadsA.dispatchEvent(new Event('change'));
        el.scanReadsB.value = b; el.scanReadsB.dispatchEvent(new Event('change'));
      };
      // Menus: a setup code carries them, the defaults are own, and a
      // value a layer's menu does not offer is its own. restore() is the
      // face's alone (the instrument hears loadCode), and this is the face's
      // round trip: what the menus and the setup the face sends say.
      set('B', 'both');
      const code = snapshot();
      restore({}); const cleared = scan.reads.slice();
      restore(code); const back = scan.reads.slice(), menus = [el.scanReadsA.value, el.scanReadsB.value];
      const sent = [snapshot().scanReadsA, snapshot().scanReadsB];
      restore(Object.assign({}, code, { scanReadsA: 'A', scanReadsB: 'nobody' }));
      const refused = scan.reads.slice();
      return { code: [code.scanReadsA, code.scanReadsB], cleared, back, menus, sent, refused };
    }""")
    check("a setup code carries what each layer reads and brings it back, to the menus and the setup the face sends",
          xs["code"] == ["B", "both"] and xs["back"] == ["B", "both"] and xs["menus"] == ["B", "both"] and xs["sent"] == ["B", "both"],
          str(xs))
    null("between, the defaults: each its own", xs["cleared"] == ["A", "B"], str(xs["cleared"]))
    check("a value a layer's menu does not offer reads its own picture", xs["refused"] == ["A", "B"], str(xs["refused"]))
    p.evaluate("""() => {
      el.scanReadsA.value = 'A'; el.scanReadsA.dispatchEvent(new Event('change'));
      el.scanReadsB.value = 'B'; el.scanReadsB.dispatchEvent(new Event('change'));
      el.midiLayers.value = 'off'; el.midiLayers.dispatchEvent(new Event('change', { bubbles: true }));
    }""")
    p.wait_for_timeout(200)
    hidden = p.evaluate("() => el.scanReadsRow.hidden")
    check("unsplit, the Reads row is hidden: there is one picture", hidden is True, str(hidden))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()


    # ------------------------------------------------------------------
    print("\n--- on the site's instrument ---")
    # The site as a visitor opens it: the compiled instrument, which lays the
    # strike on the grid it draws itself (scan.h's ScanReader::strike), so
    # nothing the page draws can show it. What can: each layer's picture
    # stage reads its own grid, and the instrument hands those readings back
    # (state.source.layerPictures) - a split's two coverages. Crossed hands
    # with a fifth held in each half, so each layer draws its figure, and A
    # reading its own picture, so nothing but a strike landing there can move
    # A's: then six new notes in B's half at full velocity, and A's coverage
    # a tenth of a second later against the third of a second before. B's
    # Reads set to A's - by its menu, as a hand sets it, so the crossing has
    # to reach the instrument the way a hand's does (HOST_CONTROLS) - puts
    # B's strikes in A's picture. The nulls are Strike at nought and B
    # reading its own, where A's picture does not move. B's own picture is
    # not read: B's new notes redraw it whatever the strike does.
    SITE = """async ([strike, readsB]) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const setup = Object.assign({}, corpusSetup('Crossed hands'),
                                  { pictureAmount: 0, scanStrike: strike, scanReadsA: 'A', scanReadsB: 'B' });
      hostQuietly(() => restore(setup)); hostSendSetup();
      await wait(300);
      el.scanReadsB.value = readsB; el.scanReadsB.dispatchEvent(new Event('change', { bubbles: true }));
      // A keyboard present, which the layers need: the screen's.
      setScreenKeys(true);
      for (const n of [43, 50, 72, 79]) midiNoteOn(n, 100);
      await wait(1500);
      const cover = () => { const l = state.source.layerPictures; return l ? [l.stages[0].raw.cover, l.stages[1].raw.cover] : null; };
      const before = [];
      for (let k = 0; k < 10; k++) { await wait(30); before.push(cover()); }
      const burst = [73, 75, 77, 78, 80, 82];
      for (const n of burst) midiNoteOn(n, 127);
      const after = [];
      for (let k = 0; k < 4; k++) { await wait(30); after.push(cover()); }
      const live = !!(state.source.layerPictures && state.source.layerPictures.live);
      for (const n of [43, 50, 72, 79, ...burst]) midiNoteOff(n);
      setScreenKeys(false);
      return { before, after, live, host: BRAIN_IN_CORE && state.source.kind === 'host' };
    }"""
    def site(strike, reads_b):
        bb = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
        pp = bb.new_page(viewport={"width": 1400, "height": 900})
        errs = []
        pp.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
        pp.goto(f"file://{ART}/scope.html"); pp.wait_for_timeout(1200)
        corpus.old_opening(pp)  # the opening it was written against (P8h)
        corpus.install(pp)
        if pp.locator("#helpClose").is_visible(): pp.locator("#helpClose").click()
        pp.locator("#trace").click(position={"x": 5, "y": 5})   # the press a browser waits for
        pp.wait_for_timeout(800)
        got = pp.evaluate(SITE, [strike, reads_b])
        got["errors"] = errs
        bb.close()
        # How far each layer's coverage rose: the most after against where it
        # stood as the burst went in, the mean of the last three reads before
        # it. It used to be against the most before, which is the oldest read:
        # A's coverage falls all through the third of a second before the
        # burst, by 0.013 to 0.015 in every run, so the strike had first to
        # make up the fall, and on a container slowed by the serial suites
        # before it the crossed run rose 0.001 and 0.005 where the check asks
        # 0.004 (P8h). Against the moment of the burst it rises about 0.025,
        # and the nulls about nought.
        got["rise"] = [max(a[l] for a in got["after"]) - sum(b_[l] for b_ in got["before"][-3:]) / 3 for l in (0, 1)]
        return got
    crossed_site, quiet_site, own_site = site(100, "A"), site(0, "A"), site(100, "B")
    for name, r in (("crossed", crossed_site), ("Strike at nought", quiet_site), ("B its own", own_site)):
        print("    %s: A's coverage rose %.4f, B's %.4f (live %s, on the instrument %s)"
              % (name, r["rise"][0], r["rise"][1], r["live"], r["host"]))
    # A's coverage wanders by about a hundredth from one run to the next, so
    # the strike is judged against the nulls' own runs as well as against
    # nought: crossed it must rise, and by a hundredth more than either null
    # does. Read against the moment of the burst, the crossed rose 0.021 to
    # 0.036 over a dozen runs and the nulls -0.003 to 0.005, so the line
    # between them is a hundredth, half the least strike and twice the
    # most a null wandered. (Against the most before, the nulls fell 0.009 to
    # 0.019 and the crossed rose 0.001 to 0.025, and the line was 0.004.) Once
    # in about twenty the null at Strike nought has risen 0.022, as much as a
    # strike, with nothing striking A; read the old way that run would have
    # failed as well, and what moves A's picture then is not yet known.
    check("on the site's instrument, B's notes strike A's picture when B reads A's",
          crossed_site["host"] and crossed_site["live"] and crossed_site["rise"][0] > 0.01
          and crossed_site["rise"][0] - max(quiet_site["rise"][0], own_site["rise"][0]) > 0.01,
          "%.4f against %.4f and %.4f" % (crossed_site["rise"][0], quiet_site["rise"][0], own_site["rise"][0]))
    null("at Strike nought A's picture does not rise", quiet_site["live"] and quiet_site["rise"][0] < 0.01,
         str(quiet_site["rise"]))
    null("with B reading its own, A's picture does not rise", own_site["live"] and own_site["rise"][0] < 0.01,
         str(own_site["rise"]))
    check("no page errors on the site", not (crossed_site["errors"] + quiet_site["errors"] + own_site["errors"]),
          "; ".join((crossed_site["errors"] + quiet_site["errors"] + own_site["errors"])[:3]))

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("STRIKE PASS")
