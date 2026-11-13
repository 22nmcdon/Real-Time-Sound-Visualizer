"""Layer B's own plane: a mirror, a snap, a twist and a turn of its own.

What would go wrong, and what is checked for it:

- B's own plane switched off but still read, so a setup that never asked for
  it plays differently. Off, B's fields are set to junk and the output is
  required to be the same samples as with them at rest - and switched on,
  the same junk is required to change it, so the comparison can fail;
- B's picture still going through A's plane, or A's through B's. B's own
  mirror folds B's X onto its right half while A's X keeps its negative
  half, and the null is the same notes with B's own off;
- the turn turning the wrong way, or not at all. B plays one note, which is
  drawn on both axes - a diagonal, which a turn changes; a circle would hide
  it (CLAUDE.md on fixtures). An eighth of a turn lays the diagonal on the Y
  axis: X nought and Y the diagonal's length. The null is no turn, where X
  and Y are the same;
- the heard pair bent as one when each layer has its own. A mirror on X is
  full-wave rectification of the left channel, which puts the note's octave
  there: with B's own mirror and none of A's, B's octave is heard and A's
  is not; Together, with the mirror A's and so both layers', both are;
- a routing reaching B's twist through A's fade. B's picture with a twist
  routed at A by a lot and at B by nothing is required to be B's with A's
  depth different and B's still nothing - and to move once B's is not;
- the panel writing into the wrong layer: the Layers row, Together copying
  nothing and A or B copying A's plane into B's, a control moved with B's
  shown writing B's alone, the Play tab's B button showing B's plane here,
  and Together letting B's own go;
- the screen's rotation still turning B's figure while B turns itself. Read
  from the beam's own points for B's figure, a diagonal: kept a diagonal
  with B's own, laid on the Y axis with Together, where the screen's
  rotation is B's too;
- a setup code: B's own written and read back, a field it lacks falling
  back to A's, and a code with B's own off the code it always was;
- the site's default, the instrument: the same hands on its panel, read
  from the lanes it draws, folded with B's own and not with Together;
- B's own echo and chorus (5r) going through A's line, or A's through B's.
  An echo half a period of B's note late, at half level and no feedback,
  cancels half of B's note and nothing of A's chord: B's picture is required
  to halve and A's to be the same samples, and the heard pair to lose half
  its B and keep its A. Together, the same echo as A's halves B and moves A.
  A routing on the echo's level through B's fade does the same, and through
  A's fade alone does nothing to B;
- the Delay module's Layers row, the same switch as the Plane's,
  its controls writing B's echo while B's is shown, the tempo moving B's
  synced time, and B's echo in setup codes.

Frequencies are read by a Hann-windowed single-bin transform, as polytest
and layertest do.
"""
# On the site's default page since stage 5, step 3, batch 2 (13 Nov). Until
# then the first page was ?brain=js, and its core part an offline
# makeGeneratorCore built in the page with routes put in by hand: B's own
# plane off and on, its mirror, its turn, its share of the heard pair, a
# routing through B's fade on the twist, the Turn and the echo, B's own echo
# and chorus - all core/tests/pieces/layerplane.py's now, on the core's own
# output (parity runs it), as are the screen's rotation against B's own turn
# (read off the page's beam until then; off the instrument's own grid now)
# and B's synced echo following the tempo (the page's clockStep called by
# hand until then; the instrument's echo, found in B's lanes, now). The
# panel and the codes below are the face, with its hands pressed; where they
# said the generator was told, they read the setup the face sends the
# instrument (snapshot()) rather than genSettings, which on the default page
# is the page's own mirror of it.
import math, os, sys
from playwright.sync_api import sync_playwright
import corpus

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

HZ = lambda note: 440 * 2 ** ((note - 69) / 12)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(1200)
    corpus.old_opening(p)  # the opening it was written against (P8h)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    # The core's checks that stood here - B's fields junk with its own plane
    # off, its mirror, its turn either way, each layer's octave in the heard
    # pair, a routing reaching B's twist, B's Turn as a destination, B's own
    # echo halving B's picture and its note, the echo's level routed through
    # B's fade - are core/tests/pieces/layerplane.py's (batch 2).

    # Its way in is its right-click menu since G5b, where it was the shoulder's dots: B's Turn has no words, and has one all the same.
    way = p.evaluate("""() => ({ dest: el.planeTurnRow.dataset.modDest, open: menuControl(el.planeTurnRow.querySelector('input[type=range]')) !== null,
                                 listed: MOD_DESTS.has('gen.turn') && MOD_DESTS.get('gen.turn').slot === 32 })""")
    # It was the table's last slot when it came, so that no slot before it
    # moved, and this asserted exactly that; since P6c the bend's two come
    # after it, so what is held is the same thing said directly - it sits
    # after the third axis. Since G2 the three axes' slots are unused and the
    # table no longer has an entry a slot, so the number itself is held: 32,
    # where it was added, since the core shares it and nothing is closed up.
    check("the Turn row takes a routing like any destination, and it is slot 32, where it was added",
          way == {"dest": "gen.turn", "open": True, "listed": True}, str(way))

    print("\n--- the panel: the Plane's link (G6) ---")
    # Since G6 a link on the Plane's line, where Together, A and B were: the
    # same in both, or the hand's own, unlinking copying the hand on the face
    # into the other and linking copying it back over; the header's Editing
    # chooses the hand, and the upper's own Turn takes the Turn's place.
    panel = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const link = document.getElementById('linkPlane');
      const read = () => ({ link: link.hidden, said: link.textContent, pressed: link.getAttribute('aria-pressed'),
        title: el.planeTitle.textContent, turnRow: el.planeTurnRow.hidden, rotateRow: el.rotateRow.hidden,
        own: planeB.own, edit: midi.layers.edit, bMirror: planeB.mirror, aMirror: plane.mirror, bSnap: planeB.snap,
        aTwist: plane.twist, bTwist: planeB.twist, turn: planeB.turn, shownMirror: el.planeMirror.value,
        shownTwist: el.planeTwist.value, ...sent() });
      // What the face sends the instrument, the setup: until batch 2 these
      // were genSettings(0) and (1), the page's own generator on ?brain=js
      // and only the page's mirror of the setup on the default page.
      const sent = () => { const c = snapshot();
        return { genA: c.planeMirror, genB: c.bPlane ? c.bMirror : c.planeMirror, genOwn: !!c.bPlane, genTurn: c.bPlane ? c.bTurn : 0 }; };
      const out = {};
      out.one = read();
      // Poly pressed, as a hand does (setMidiMode was called directly until batch 2).
      setScreenKeys(true); el.midiPoly.click();
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(80);
      el.planeSnap.value = '5'; el.planeSnap.dispatchEvent(new Event('change'));
      out.layered = read();
      document.getElementById('editHandB').click(); link.click(); await wait(30); out.b = read();
      el.planeMirror.value = '1'; el.planeMirror.dispatchEvent(new Event('change'));
      el.planeTurn.value = '25'; el.planeTurn.dispatchEvent(new Event('input'));
      out.bMoved = read();
      document.getElementById('editHandA').click(); await wait(30);
      el.planeTwist.value = '40'; el.planeTwist.dispatchEvent(new Event('input'));
      out.a = read();
      document.getElementById('editHandB').click(); await wait(30); out.playB = read();
      link.click(); await wait(30); out.both = read();
      return out;
    }""")
    one, lay, pb, moved, pa, playb, both_ = (panel[k] for k in ("one", "layered", "b", "bMoved", "a", "playB", "both"))
    check("with one layer the link is hidden, the section is the Plane and its Turn the screen's",
          one["link"] and one["title"] == "Plane" and one["turnRow"] and not one["rotateRow"], str(one))
    check("with two it shows, the same in both, and a menu moved writes both hands' plane",
          not lay["link"] and lay["said"] == "Both" and lay["pressed"] == "true" and not lay["own"] and lay["bSnap"] == 5, str(lay))
    check("unlinked with the upper edited, B has a plane of its own that starts as the hand on the face, shown, its own Turn in the Turn's place",
          pb["own"] and pb["genOwn"] is True and pb["bSnap"] == 5 and pb["said"] == "Upper" and pb["pressed"] == "false"
          and not pb["turnRow"] and pb["rotateRow"] and pb["edit"] == 1, str(pb))
    check("null: before the link, the setup sent has no plane of B's", lay["genOwn"] is False, str(lay))
    check("a menu and the Turn moved with B's shown are B's, and A's plane is untouched",
          moved["bMirror"] == 1 and moved["aMirror"] == 0 and moved["genB"] == 1 and moved["genA"] == 0
          and moved["turn"] == 0.25 and moved["genTurn"] == 25, str(moved))
    check("the lower shows A's plane with the screen's Turn, and writes A's alone",
          pa["said"] == "Lower" and pa["turnRow"] and not pa["rotateRow"] and pa["aTwist"] == 0.4 and pa["bTwist"] == 0
          and pa["shownMirror"] == "0" and pa["bMirror"] == 1, str(pa))
    check("the upper chosen again shows B's plane",
          playb["said"] == "Upper" and playb["shownMirror"] == "1" and playb["shownTwist"] == "0", str(playb))
    check("linked again from the upper, B's plane is copied over A's, B's turn goes, and the setup sent says so",
          not both_["own"] and both_["genOwn"] is False and both_["aMirror"] == 1 and both_["aTwist"] == 0
          and both_["bMirror"] == 1 and both_["turn"] == 0 and both_["said"] == "Both", str(both_))

    # The screen's rotation against B turning itself - kept a diagonal with
    # the Plane the upper's own, laid on the Y axis linked - was read off the
    # page's beamX/beamY with state.rotate written by hand, on ?brain=js. It
    # is core/tests/pieces/layerplane.py's on the instrument's own grid, the
    # Turn moved on its panel and the link pressed (batch 2).

    print("\n--- setup codes ---")
    codes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const link = document.getElementById('linkPlane');
      document.getElementById('editHandB').click(); if (linked('plane')) link.click(); await wait(20);
      el.planeSnap.value = '6'; el.planeSnap.dispatchEvent(new Event('change'));
      el.planeTurn.value = '-12'; el.planeTurn.dispatchEvent(new Event('input'));
      const saved = { ...planeB }, code = encodeSetup(snapshot());
      link.click(); await wait(20);
      const offCode = encodeSetup(snapshot());
      loadCode(code); await wait(20);
      const back = { ...planeB };
      loadCode(encodeSetup({ bPlane: true, bMirror: 2, planeSnap: 5 }));
      const partial = { ...planeB };
      loadCode(encodeSetup({ planeSnap: 5 }));
      const old = { ...planeB };
      return { saved, back, partial, old, offHas: JSON.stringify(decodeSetup(offCode)).includes('bPlane'),
               onHas: Object.keys(decodeSetup(code)).filter((k) => /^b(Plane|Mirror|Turn|Snap)$/.test(k)).sort() };
    }""")
    check("B's own plane is written into a code and read back as it was",
          codes["back"] == codes["saved"] and codes["saved"]["own"] and codes["saved"]["snap"] == 6
          and codes["saved"]["turn"] == -0.12, "%r / %r" % (codes["saved"], codes["back"]))
    check("a code of B's own with a field missing takes A's for it",
          codes["partial"]["own"] and codes["partial"]["mirror"] == 2 and codes["partial"]["snap"] == 5
          and codes["partial"]["turn"] == 0, str(codes["partial"]))
    check("a code from before it has B following A, and linked nothing of it is written",
          not codes["old"]["own"] and codes["old"]["snap"] == 5 and not codes["offHas"]
          and codes["onHas"] == ["bMirror", "bPlane", "bSnap", "bTurn"], str(codes["onHas"]))

    print("\n--- the Delay module's link ---")
    tp = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const link = document.getElementById('linkDelay');
      const read = () => ({ said: link.textContent, own: !linked('delay'), planeOwn: planeB.own,
        edit: midi.layers.edit, aMix: echo.mix, bMix: echoB.mix, aMs: echo.ms, bMs: echoB.ms, aChorus: echo.chorus, bChorus: echoB.chorus,
        shownMix: el.delayMix.value, shownMs: el.delayMs.value, ...sent() });
      // What the face sends the instrument, the setup, where until batch 2
      // this read genSettings(0) and (1): B's delay its own is its fields in
      // the code (bDelay...), and nothing else of B's - no chorus, no plane -
      // is what timeOwn's 4 said. (bPlane is there with any of B's rack
      // fields, the way a code says B has fields of its own at all.)
      const sent = () => { const c = snapshot(), own = 'bDelayMix' in c;
        return { genA: c.delayMix / 100, genB: (own ? c.bDelayMix : c.delayMix) / 100, genBMs: own ? c.bDelayMs : c.delayMs,
                 genBChorus: ('bChorusMix' in c ? c.bChorusMix : c.chorusMix) / 100,
                 timeOwn: own && !Object.keys(c).some((k) => /^b(Chorus|Phaser|Reverb|Mirror|Turn|Snap|Twist)/.test(k)) ? 4 : own ? -1 : 0 }; };
      const slide = (id, v) => { el[id].value = String(v); el[id].dispatchEvent(new Event('input')); };
      const out = {};
      // The codes above loaded setups with the layers off, and with nothing of B's in the rack.
      setScreenKeys(true); el.midiPoly.click();
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change')); await wait(50);
      document.getElementById('editHandA').click(); await wait(20);
      slide('delayMix', 30); out.together = read();
      document.getElementById('editHandB').click(); link.click(); await wait(20); out.b = read();
      slide('delayMs', 120); slide('chorusMix', 60); out.bMoved = read();
      document.getElementById('editHandA').click(); await wait(20); slide('delayMix', 70); out.a = read();
      document.getElementById('editHandB').click(); await wait(20); out.playB = read();
      // B's synced to a crotchet. That its time then follows the tempo was
      // read here off genSettings(1).delayMs after setTempo and the page's
      // clockStep called by hand, on ?brain=js; the instrument's echo,
      // found in B's lanes at 120 and 60, is core/tests/pieces/layerplane.py's
      // (batch 2). What stays is the face: B's synced, A's free.
      el.delaySync.value = '1/4'; el.delaySync.dispatchEvent(new Event('change'));
      out.tempo = { aSync: echo.sync, bSync: echoB.sync, sent: snapshot().bDelaySync, sentA: snapshot().delaySync };
      const code = encodeSetup(snapshot()), saved = { ...echoB };
      link.click(); await wait(20); out.both = read();
      const offCode = encodeSetup(snapshot());
      loadCode(code); await wait(20);
      out.back = { ...echoB }; delete out.back.sent; delete saved.sent; out.saved = saved;
      loadCode(encodeSetup({ bPlane: true, bDelayMix: 45, delayMix: 20, delayFeedback: 60 }));
      out.partial = { ...echoB };
      // The delay's nine - five, and F5c's tone, low cut, width and wow - and none of the chorus's, which stayed linked.
      out.onHas = Object.keys(decodeSetup(code)).filter((k) => /^bDelay|^bChorus/.test(k)).length;
      out.offHas = Object.keys(decodeSetup(offCode)).filter((k) => /^bDelay|^bChorus/.test(k)).length;
      loadCode(encodeSetup({}));
      return out;
    }""")
    tog, tb, tbm, ta, tplay, tboth = (tp[k] for k in ("together", "b", "bMoved", "a", "playB", "both"))
    check("with two layers the Delay's link shows, the same in both, and its controls write both hands' echo",
          tog["said"] == "Both" and not tog["own"] and tog["genA"] == 0.3 and tog["genB"] == 0.3, str(tog))
    check("unlinked with the upper edited, B has an echo of its own that starts as the hand on the face, and nothing else of its own",
          tb["own"] and tb["said"] == "Upper" and tb["bMix"] == 0.3 and tb["timeOwn"] == 4 and not tb["planeOwn"]
          and tb["edit"] == 1, str(tb))
    check("the echo's time moved with B's shown is B's, A's untouched, and the chorus, linked, moves both",
          tbm["bMs"] == 120 and tbm["genBMs"] == 120 and tbm["aMs"] == 375
          and tbm["bChorus"] == 0.6 == tbm["aChorus"] and tbm["genBChorus"] == 0.6, str(tbm))
    check("the lower shows A's echo and writes A's alone",
          ta["said"] == "Lower" and ta["aMix"] == 0.7 and ta["bMix"] == 0.3 and ta["genB"] == 0.3
          and ta["shownMs"] == "375", str(ta))
    check("the upper chosen again shows B's echo",
          tplay["said"] == "Upper" and tplay["shownMix"] == "30" and tplay["shownMs"] == "120", str(tplay))
    check("B's own echo synced to a crotchet is B's, and A's stays free",
          tp["tempo"] == {"aSync": "", "bSync": "1/4", "sent": "1/4", "sentA": ""}, str(tp["tempo"]))
    check("linked again from the upper, B's echo is copied over A's, and the setup sent has none of B's own",
          not tboth["own"] and tboth["aMix"] == 0.3 and tboth["bMix"] == 0.3 and tboth["genA"] == 0.3
          and tboth["timeOwn"] == 0 and tboth["said"] == "Both", str(tboth))
    check("B's own echo is written into a code and read back as it was",
          tp["back"] == tp["saved"] and tp["saved"]["sync"] == "1/4" and tp["saved"]["chorus"] == 0.6 and tp["onHas"] == 9,
          "%r / %r %r" % (tp["saved"], tp["back"], tp["onHas"]))
    check("a code of B's own with a field missing takes A's for it, and linked none of it is written",
          tp["partial"]["mix"] == 0.45 and tp["partial"]["feedback"] == 0.6 and tp["offHas"] == 0, str(tp["partial"]))
    p.close()

    print("\n--- the site's default: the instrument ---")
    p = b.new_page(viewport={"width": 1400, "height": 900})
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(900)
    corpus.old_opening(p)  # the opening it was written against (P8h)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    inst = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      // Poly by its button, a hand the instrument is sent, as braintest plays it.
      setScreenKeys(true); el.midiPoly.click();
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      await wait(200);
      midiNoteOn(48, 100); midiNoteOn(55, 100); midiNoteOn(72, 100); await wait(500);
      const lows = async () => {
        await wait(500);
        const w = state.source.getLatestWindow(4096);
        return { lanes: w.length, aX: Math.min(...w[0]), bX: Math.min(...w[2]), bPeak: Math.max(...w[2].map(Math.abs)) };
      };
      // The links pressed as a hand presses them, so the instrument is told (G6).
      const hand = (h) => document.getElementById(h ? 'editHandB' : 'editHandA').click();
      const press = (id) => document.getElementById(id).click();
      hand(1); press('linkPlane'); await wait(50);
      el.planeMirror.value = '1'; el.planeMirror.dispatchEvent(new Event('change'));
      const own = await lows();
      // Linked again from the lower hand, whose plane is bare, so B's goes.
      hand(0); press('linkPlane');
      const together = await lows();
      // B's own echo, 21 ms late at half level: B's 523 Hz note is ten
      // periods and a fiftieth late, so it adds near enough in step - B's
      // lanes half as big again, A's as they were.
      const big = async () => {
        await wait(500);
        const w = state.source.getLatestWindow(4096);
        return { a: Math.max(...w[0].map(Math.abs)), b: Math.max(...w[2].map(Math.abs)) };
      };
      const slide = (id, v) => { el[id].value = String(v); el[id].dispatchEvent(new Event('input')); };
      const eDry = await big();
      hand(1); press('linkDelay'); await wait(50);
      slide('delayFeedback', 0); slide('delayMs', 21); slide('delayMix', 50);
      const eOwn = await big();
      hand(0); press('linkDelay');
      const eBack = await big();
      midiPanic();
      return { own, together, eDry, eOwn, eBack, kind: state.source.kind, driver: lfoDriver() };
    }""")
    print("    %s: lowest X, A's and B's: B's own mirror %.3f %.3f; linked %.3f %.3f"
          % (inst["kind"], inst["own"]["aX"], inst["own"]["bX"], inst["together"]["aX"], inst["together"]["bX"]))
    check("on the instrument, B's own mirror moved on its panel folds the B lanes it draws, and not A's",
          inst["kind"] == "host" and inst["own"]["lanes"] == 4 and inst["own"]["bX"] > -1e-3 and inst["own"]["bPeak"] > 0.05
          and inst["own"]["aX"] < -0.05, str(inst["own"]))
    check("and linked again from the lower hand, A's plane bare, folds neither", inst["together"]["bX"] < -0.05, str(inst["together"]))
    ed, eo, ebk = inst["eDry"], inst["eOwn"], inst["eBack"]
    print("    B's lanes and A's, largest: dry %.3f %.3f; B's own echo %.3f %.3f; linked again %.3f %.3f"
          % (ed["b"], ed["a"], eo["b"], eo["a"], ebk["b"], ebk["a"]))
    check("on the instrument, B's own echo moved on its panel makes B's lanes half as big again, and not A's",
          abs(eo["b"] / ed["b"] - 1.5) < 0.05 and abs(eo["a"] / ed["a"] - 1) < 0.02, "%.3f %.3f" % (eo["b"] / ed["b"], eo["a"] / ed["a"]))
    check("and linked again from the lower, where the echo is A's and dry, B's are as they were", abs(ebk["b"] / ed["b"] - 1) < 0.02,
          "%.3f" % (ebk["b"] / ed["b"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("layer B's plane is its own")
