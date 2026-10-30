"""Layer B's own plane: a mirror, a kaleidoscope, a twist and a turn of its own.

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
- the Delay and chorus section's Layers row, the same switch as the Plane's,
  its controls writing B's echo while B's is shown, the tempo moving B's
  synced time, and B's echo in setup codes.

Frequencies are read by a Hann-windowed single-bin transform, as polytest
and layertest do.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

HZ = lambda note: 440 * 2 ** ((note - 69) / 12)

BIN = """() => { window.__bin = (x, f, rate) => {
  let re = 0, im = 0;
  for (let i = 0; i < x.length; i++) {
    const w = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (x.length - 1));
    re += x[i] * w * Math.cos(2 * Math.PI * f * i / rate);
    im -= x[i] * w * Math.sin(2 * Math.PI * f * i / rate);
  }
  return Math.hypot(re, im) / x.length;
}; }"""

# One core, A a sine chord on X and Y, B a sine note on both axes, and
# whatever `setup` sets; the last 8192 samples of each lane.
CORE = """([setup, rounds]) => {
  const rate = 44100, HZ = (n) => 440 * Math.pow(2, (n - 69) / 12);
  const quiet = [0, 1].map(() => ({ shape: 'sine', rate: 0.9, depth: 0, phase: 0, held: 0, value: 0 }));
  const core = makeGeneratorCore(rate, GEN_DESTS.length, quiet);
  core.set('shape', 'sine'); core.set('shape', 'sine', 1);
  core.set('voices', [{ note: 48, freq: HZ(48), velocity: 1, role: 'x' }, { note: 55, freq: HZ(55), velocity: 1, role: 'y' }]);
  core.set('voices', [{ note: 69, freq: HZ(69), velocity: 1, role: 'xy' }], 1);
  for (const [field, value, layer] of setup.sets || []) core.set(field, value, layer);
  if (setup.routes) core.setRoutes(setup.routes.map((r) => Object.assign({ slot: GEN_DESTS.find((d) => d.id === r.dest).slot }, r)));
  const n = 4096, keep = 8192, lanes = [0, 1, 2, 3, 4, 5].map(() => []);
  for (let b = 0; b < (rounds || 8); b++) {
    const a = [0, 1, 2, 3, 4, 5].map(() => new Float32Array(n));
    core.block(a[0], a[1], n, a[2], a[3], a[4], a[5]);
    a.forEach((x, k) => lanes[k].push(...x));
  }
  return lanes.map((x) => x.slice(-keep));
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0&brain=js"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate(BIN)
    core = lambda setup, rounds=8: p.evaluate(CORE, [setup, rounds])
    lo = lambda x: min(x)
    peak = lambda x: max(abs(v) for v in x)
    same = lambda a, b: all(x == y for x, y in zip(a, b))

    print("\n--- the core: off is the old arithmetic, on is B's own ---")
    junk = [["planeMirror", 3, 1], ["planeKaleido", 5, 1], ["planeTurn", 1.1, 1], ["planeTwist", 2, 1],
            ["planeLimit", 2, 1], ["planeRadius", 0.2, 1], ["planeSnap", 3, 1]]
    a_plane = [["planeTwist", 0.7, 0], ["delayMix", 0.3, 0], ["delayMs", 9, 0]]
    rest = core({"sets": a_plane})
    off = core({"sets": a_plane + junk})
    on = core({"sets": a_plane + junk + [["planeOwn", True, 1]]})
    check("with B's own off, B's fields set to junk change not one sample of any pair",
          all(same(rest[k], off[k]) for k in range(6)))
    check("and with it on the same junk changes B's picture and the sound, and not A's picture",
          not same(rest[4], on[4]) and not same(rest[2], on[2]) and same(rest[0], on[0]) and same(rest[1], on[1]))

    print("\n--- the core: B's mirror is B's ---")
    mir = core({"sets": [["planeOwn", True, 1], ["planeMirror", 1, 1]]})
    mir_off = core({"sets": [["planeMirror", 1, 1]]})
    print("    lowest X: A %.3f, B %.3f with its own mirror, B %.3f without" % (lo(mir[0]), lo(mir[4]), lo(mir_off[4])))
    check("B's own mirror folds B's X onto its right half, and A's X keeps its left",
          lo(mir[4]) > -1e-3 and lo(mir[0]) < -0.1 and peak(mir[4]) > 0.1, "%.4f %.4f" % (lo(mir[4]), lo(mir[0])))
    check("and the same field with B's own off folds nothing", lo(mir_off[4]) < -0.1, "%.4f" % lo(mir_off[4]))

    print("\n--- the core: B's turn ---")
    import math
    flat = core({"sets": [["planeOwn", True, 1]]})
    turned = core({"sets": [["planeOwn", True, 1], ["planeTurn", math.pi / 4, 1]]})
    print("    B unturned X %.3f Y %.3f; an eighth of a turn X %.4f Y %.3f"
          % (peak(flat[4]), peak(flat[5]), peak(turned[4]), peak(turned[5])))
    check("unturned, B's one note is a diagonal: X and Y the same",
          peak(flat[4]) > 0.1 and max(abs(x - y) for x, y in zip(flat[4], flat[5])) < 1e-6)
    check("an eighth of a turn lays it on the Y axis: X nought, Y the diagonal's length",
          peak(turned[4]) < 1e-3 * peak(flat[4]) and abs(peak(turned[5]) / peak(flat[4]) - math.sqrt(2)) < 0.01,
          "%.5f %.4f" % (peak(turned[4]), peak(turned[5]) / max(peak(flat[4]), 1e-9)))
    back = core({"sets": [["planeOwn", True, 1], ["planeTurn", -math.pi / 4, 1]]})
    check("and the other way lays it on the X axis instead, the same length",
          peak(back[5]) < 1e-3 * peak(flat[4]) and max(abs(x - y) for x, y in zip(back[4], turned[5])) < 1e-4,
          "%.5f %.5f" % (peak(back[5]), peak(back[4])))

    print("\n--- the core: each layer's share of the sound through its own plane ---")
    fa, fb = HZ(48), HZ(69)
    octaves = lambda lanes: (p.evaluate("([x, f]) => window.__bin(x, f, 44100)", [lanes[2], 2 * fa]),
                             p.evaluate("([x, f]) => window.__bin(x, f, 44100)", [lanes[2], 2 * fb]))
    own_b = octaves(core({"sets": [["planeOwn", True, 1], ["planeMirror", 1, 1]]}))
    both = octaves(core({"sets": [["planeMirror", 1, 0]]}))
    own_none = octaves(core({"sets": [["planeOwn", True, 1], ["planeMirror", 1, 0]]}))
    print("    heard left, A's octave and B's: B's own mirror %.4f %.4f; Together %.4f %.4f; A's own %.4f %.4f"
          % (own_b[0], own_b[1], both[0], both[1], own_none[0], own_none[1]))
    check("with B's own mirror and none of A's, B's octave is heard and A's is not",
          own_b[1] > 0.01 and own_b[0] < 0.1 * own_b[1], str(own_b))
    check("Together, the mirror is both layers' and both octaves are heard",
          both[0] > 0.01 and both[1] > 0.01, str(both))
    check("and with the mirror A's alone, A's octave is heard and B's is not",
          own_none[0] > 0.01 and own_none[1] < 0.1 * own_none[0], str(own_none))

    print("\n--- the core: a routing reaches B's own twist through B's fade ---")
    route = lambda a, bb: {"sets": [["planeOwn", True, 1]], "routes": [{"dest": "gen.twist", "index": 0, "amount": a, "amountB": bb}]}
    q = [core(route(0.9, 0)), core(route(0.1, 0)), core(route(0.1, 0.6))]
    check("B's picture with A's depth on the twist changed and B's still nothing is the same picture",
          same(q[0][4], q[1][4]) and same(q[0][5], q[1][5]))
    check("and given a depth of its own, it moves",
          not same(q[1][4], q[2][4]), "%.4f" % max(abs(x - y) for x, y in zip(q[1][4], q[2][4])))

    print("\n--- the core: B's turn as a destination ---")
    # A held value of one, so the push is the depth: B's depth a quarter is an
    # eighth of a turn, which lays B's diagonal on the Y axis, as the slider's
    # eighth does above. A's depth on it is a different number, and is nothing.
    turn = lambda own, bb: {"sets": [["planeOwn", own, 1]],
                            "routes": [{"dest": "gen.turn", "held": 1, "heldB": 1, "amount": 0.9, "amountB": bb}]}
    t_on, t_none, t_off = core(turn(True, 0.25)), core(turn(True, 0)), core(turn(False, 0.25))
    print("    B's X and Y peaks: routed %.4f %.3f; B's depth nought %.3f %.3f; B's own off %.3f %.3f"
          % (peak(t_on[4]), peak(t_on[5]), peak(t_none[4]), peak(t_none[5]), peak(t_off[4]), peak(t_off[5])))
    check("a routing on Turn at B's depth of a quarter turns B an eighth: its diagonal on the Y axis",
          peak(t_on[4]) < 1e-3 * peak(t_on[5]) and abs(peak(t_on[5]) / peak(flat[4]) - math.sqrt(2)) < 0.01,
          "%.5f %.4f" % (peak(t_on[4]), peak(t_on[5])))
    check("and at B's depth of nought, whatever A's, B is not turned",
          max(abs(x - y) for x, y in zip(t_none[4], t_none[5])) < 1e-6 and peak(t_none[4]) > 0.1)
    flat_off = core({"sets": []})
    check("and with B's own plane off the routing turns nothing",
          same(t_off[4], flat_off[4]) and same(t_off[5], flat_off[5]))
    way = p.evaluate("""() => ({ dest: el.planeTurnRow.dataset.modDest, open: !!el.planeTurnRow.querySelector('.mod-open'),
                                 listed: MOD_DESTS.has('gen.turn') && MOD_DESTS.get('gen.turn').slot === GEN_DESTS.length - 1 })""")
    check("the Turn row takes a routing like any destination, and it is the table's last slot",
          way == {"dest": "gen.turn", "open": True, "listed": True}, str(way))

    print("\n--- the core: B's own echo and chorus ---")
    # B's note is 440 Hz: an echo half a period late, at half level, is the
    # note less half of itself. A's chord is 131 and 196 Hz, which the same
    # echo moves rather than cancels.
    half = 1000 / (2 * fb)
    b_echo = [["delayMix", 0.5, 1], ["delayMs", half, 1], ["delayFeedback", 0, 1]]
    a_echo = [["delayMix", 0.5, 0], ["delayMs", half, 0], ["delayFeedback", 0, 0]]
    dry = core({"sets": []})
    e_own = core({"sets": [["planeOwn", True, 1]] + b_echo})
    e_off = core({"sets": b_echo})
    e_both = core({"sets": a_echo})
    ratio = lambda lanes, k: peak(lanes[k]) / peak(dry[k])
    print("    B's X against dry: its own echo %.3f, the same fields with B's own off %.3f, A's echo Together %.3f"
          % (ratio(e_own, 4), ratio(e_off, 4), ratio(e_both, 4)))
    check("B's own echo half a period late cancels half of B's picture, and leaves A's the same samples",
          abs(ratio(e_own, 4) - 0.5) < 0.02 and same(e_own[0], dry[0]) and same(e_own[1], dry[1]), "%.4f" % ratio(e_own, 4))
    check("and with B's own off its echo's fields do nothing", same(e_off[4], dry[4]) and same(e_off[2], dry[2]))
    check("Together, the same echo as A's halves B's picture as well, and moves A's",
          abs(ratio(e_both, 4) - 0.5) < 0.02 and not same(e_both[0], dry[0]), "%.4f" % ratio(e_both, 4))
    hb = lambda lanes, f: p.evaluate("([x, f]) => window.__bin(x, f, 44100)", [lanes[2], f])
    print("    heard, B's note and A's lower one against dry: B's own echo %.3f %.3f; Together %.3f %.3f"
          % (hb(e_own, fb) / hb(dry, fb), hb(e_own, fa) / hb(dry, fa), hb(e_both, fb) / hb(dry, fb), hb(e_both, fa) / hb(dry, fa)))
    check("in the heard pair B's own echo halves B's note and leaves A's",
          abs(hb(e_own, fb) / hb(dry, fb) - 0.5) < 0.03 and abs(hb(e_own, fa) / hb(dry, fa) - 1) < 1e-3)
    check("and Together the echo, A's, moves A's note too",
          abs(hb(e_both, fb) / hb(dry, fb) - 0.5) < 0.03 and abs(hb(e_both, fa) / hb(dry, fa) - 1) > 0.1)
    # The echo's level routed, with nothing of its own: a held value of one,
    # so B's depth of one is a push of half - the same half-level echo.
    eroute = lambda a, bb: {"sets": [["planeOwn", True, 1], ["delayMs", half, 1], ["delayFeedback", 0, 1]],
                            "routes": [{"dest": "gen.echo", "held": 1, "heldB": 1, "amount": a, "amountB": bb}]}
    r_b, r_a = core(eroute(0, 1)), core(eroute(1, 0))
    print("    B's X against dry, the echo's level routed: through B's fade %.3f, through A's alone %.3f"
          % (ratio(r_b, 4), ratio(r_a, 4)))
    check("a routing on the echo's level through B's fade gives B's own echo its level",
          abs(ratio(r_b, 4) - 0.5) < 0.02, "%.4f" % ratio(r_b, 4))
    check("and through A's fade alone it leaves B's picture as it was", abs(ratio(r_a, 4) - 1) < 1e-3, "%.4f" % ratio(r_a, 4))

    print("\n--- the panel ---")
    panel = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const read = () => ({ row: el.planeLayerRow.hidden, title: el.planeTitle.textContent, turnRow: el.planeTurnRow.hidden,
        own: planeB.own, edit: midi.layers.edit, bMirror: planeB.mirror, aMirror: plane.mirror, bKaleido: planeB.kaleido,
        aTwist: plane.twist, bTwist: planeB.twist, turn: planeB.turn, shownMirror: el.planeMirror.value,
        shownTwist: el.planeTwist.value, genA: genSettings(0).planeMirror, genB: genSettings(1).planeMirror,
        genOwn: genSettings(1).planeOwn, genTurn: genSettings(1).planeTurn,
        checked: ['Both', 'A', 'B'].filter((k) => el['planeLayer' + k].getAttribute('aria-checked') === 'true') });
      const out = {};
      out.one = read();
      setScreenKeys(true); setMidiMode('poly');
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      midi.layers.point = 60; await wait(80);
      el.planeKaleido.value = '3'; el.planeKaleido.dispatchEvent(new Event('change'));
      out.layered = read();
      el.planeLayerB.click(); await wait(30); out.b = read();
      el.planeMirror.value = '1'; el.planeMirror.dispatchEvent(new Event('change'));
      el.planeTurn.value = '25'; el.planeTurn.dispatchEvent(new Event('input'));
      out.bMoved = read();
      el.planeLayerA.click(); await wait(30);
      el.planeTwist.value = '40'; el.planeTwist.dispatchEvent(new Event('input'));
      out.a = read();
      el.midiEditB.click(); await wait(30); out.playB = read();
      el.planeLayerBoth.click(); await wait(30); out.both = read();
      return out;
    }""")
    one, lay, pb, moved, pa, playb, both_ = (panel[k] for k in ("one", "layered", "b", "bMoved", "a", "playB", "both"))
    check("with one layer the Layers row is hidden and the section is the Plane",
          one["row"] and one["title"] == "Plane" and one["turnRow"], str(one))
    check("with two it shows, on Together, and a menu moved writes both layers' plane",
          not lay["row"] and lay["checked"] == ["Both"] and lay["title"] == "Plane" and not lay["own"]
          and lay["bKaleido"] == 3, str(lay))
    check("B gives B a plane of its own that starts as A's, shows it, and puts B on the panel",
          pb["own"] and pb["genOwn"] is True and pb["bKaleido"] == 3 and pb["title"] == "Plane · layer B"
          and pb["checked"] == ["B"] and not pb["turnRow"] and pb["edit"] == 1, str(pb))
    check("a menu and the Turn moved with B's shown are B's, and A's plane is untouched",
          moved["bMirror"] == 1 and moved["aMirror"] == 0 and moved["genB"] == 1 and moved["genA"] == 0
          and moved["turn"] == 0.25 and abs(moved["genTurn"] - math.pi / 2) < 1e-12, str(moved))
    check("A shows A's plane, without the Turn, and writes A's alone",
          pa["title"] == "Plane · layer A" and pa["turnRow"] and pa["aTwist"] == 0.4 and pa["bTwist"] == 0
          and pa["shownMirror"] == "0" and pa["bMirror"] == 1, str(pa))
    check("the Play tab's B button shows B's plane here as well",
          playb["checked"] == ["B"] and playb["shownMirror"] == "1" and playb["shownTwist"] == "0", str(playb))
    check("Together lets B's own go: B follows A again, and the generator is told",
          not both_["own"] and both_["genOwn"] is False and both_["bMirror"] == 0 and both_["bTwist"] == 0.4
          and both_["checked"] == ["Both"], str(both_))

    print("\n--- the screen's rotation, and B turning itself ---")
    # B's figure is drawn second, so the beam's points after a frame are B's.
    # Only B holds a note, one, drawn on both axes: a diagonal.
    spread = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setDisplay('xy'); midiPanic(); midi.layers.pair = 'each'; syncLayers();
      // A's plane bare, so B's copy of it is too and the diagonal stays one.
      for (const k of PLANE_SHAPE) plane[k] = { radius: 0.4, scaleX: 1, scaleY: 1 }[k] ?? 0;
      syncPlanePanel(); syncPlane();
      midiNoteOn(72, 100); await wait(300);
      state.rotate = 0.125;
      const measure = async () => {
        await wait(250);
        let n = 0, sx = 0, sy = 0, cx = 0, cy = 0;
        for (let i = 0; i < BEAM_MAX && Number.isFinite(beamX[i]) && beamX[i] !== 0; i++) { cx += beamX[i]; cy += beamY[i]; n++; }
        cx /= n; cy /= n;
        for (let i = 0; i < n; i++) { sx = Math.max(sx, Math.abs(beamX[i] - cx)); sy = Math.max(sy, Math.abs(beamY[i] - cy)); }
        return { n, x: sx, y: sy };
      };
      el.planeLayerB.click(); const own = await measure();
      el.planeLayerBoth.click(); const together = await measure();
      state.rotate = 0; midiPanic();
      return { own, together };
    }""")
    print("    B's spread across and up: its own %.1f / %.1f px, Together %.1f / %.1f px"
          % (spread["own"]["x"], spread["own"]["y"], spread["together"]["x"], spread["together"]["y"]))
    check("with B's own, the screen's rotation leaves B's figure a diagonal",
          spread["own"]["n"] > 100 and spread["own"]["x"] > 20 and abs(spread["own"]["x"] - spread["own"]["y"]) < 0.1 * spread["own"]["y"],
          str(spread["own"]))
    check("and Together turns it onto the Y axis, as it turns A",
          spread["together"]["x"] < 0.1 * spread["together"]["y"] and spread["together"]["y"] > 20, str(spread["together"]))

    print("\n--- setup codes ---")
    codes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.planeLayerB.click(); await wait(20);
      el.planeSnap.value = '4'; el.planeSnap.dispatchEvent(new Event('change'));
      el.planeTurn.value = '-12'; el.planeTurn.dispatchEvent(new Event('input'));
      const saved = { ...planeB }, code = encodeSetup(snapshot());
      el.planeLayerBoth.click(); await wait(20);
      const offCode = encodeSetup(snapshot());
      restore(decodeSetup(code)); await wait(20);
      const back = { ...planeB };
      restore({ bPlane: true, bMirror: 2, planeKaleido: 5 });
      const partial = { ...planeB };
      restore({ planeKaleido: 4 });
      const old = { ...planeB };
      return { saved, back, partial, old, offHas: JSON.stringify(decodeSetup(offCode)).includes('bPlane'),
               onHas: Object.keys(decodeSetup(code)).filter((k) => /^b(Plane|Mirror|Turn|Snap)$/.test(k)).sort() };
    }""")
    check("B's own plane is written into a code and read back as it was",
          codes["back"] == codes["saved"] and codes["saved"]["own"] and codes["saved"]["snap"] == 4
          and codes["saved"]["turn"] == -0.12, "%r / %r" % (codes["saved"], codes["back"]))
    check("a code of B's own with a field missing takes A's for it",
          codes["partial"]["own"] and codes["partial"]["mirror"] == 2 and codes["partial"]["kaleido"] == 5
          and codes["partial"]["turn"] == 0, str(codes["partial"]))
    check("a code from before it has B following A, and with it off nothing of it is written",
          not codes["old"]["own"] and codes["old"]["kaleido"] == 4 and not codes["offHas"]
          and codes["onHas"] == ["bMirror", "bPlane", "bSnap", "bTurn"], str(codes["onHas"]))

    print("\n--- Delay and chorus: B's own ---")
    tp = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const read = () => ({ row: el.timeLayerRow.hidden, title: el.timeTitle.textContent, own: planeB.own,
        edit: midi.layers.edit, aMix: echo.mix, bMix: echoB.mix, aMs: echo.ms, bMs: echoB.ms, bChorus: echoB.chorus,
        shownMix: el.delayMix.value, shownMs: el.delayMs.value, genA: genSettings(0).delayMix, genB: genSettings(1).delayMix,
        genBMs: genSettings(1).delayMs, genBChorus: genSettings(1).chorusMix,
        checked: ['Both', 'A', 'B'].filter((k) => el['timeLayer' + k].getAttribute('aria-checked') === 'true'),
        planeChecked: ['Both', 'A', 'B'].filter((k) => el['planeLayer' + k].getAttribute('aria-checked') === 'true') });
      const slide = (id, v) => { el[id].value = String(v); el[id].dispatchEvent(new Event('input')); };
      const out = {};
      // The codes above loaded setups with the layers off.
      setScreenKeys(true); setMidiMode('poly');
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change')); await wait(50);
      el.planeLayerBoth.click(); await wait(20);
      slide('delayMix', 30); out.together = read();
      el.timeLayerB.click(); await wait(20); out.b = read();
      slide('delayMs', 120); slide('chorusMix', 60); out.bMoved = read();
      el.timeLayerA.click(); await wait(20); slide('delayMix', 70); out.a = read();
      el.midiEditB.click(); await wait(20); out.playB = read();
      // B's synced to the tempo, and the tempo moved: the time follows, as A's does.
      el.delaySync.value = '1/4'; el.delaySync.dispatchEvent(new Event('change'));
      setTempo(120); clockStep(performance.now()); const at120 = genSettings(1).delayMs;
      setTempo(60); clockStep(performance.now()); const at60 = genSettings(1).delayMs;
      out.tempo = { at120, at60, aSync: echo.sync, bSync: echoB.sync };
      const code = encodeSetup(snapshot()), saved = { ...echoB };
      el.timeLayerBoth.click(); await wait(20); out.both = read();
      const offCode = encodeSetup(snapshot());
      restore(decodeSetup(code)); await wait(20);
      out.back = { ...echoB }; delete out.back.sent; delete saved.sent; out.saved = saved;
      restore({ bPlane: true, bDelayMix: 45, delayMix: 20, delayFeedback: 60 });
      out.partial = { ...echoB };
      out.onHas = Object.keys(decodeSetup(code)).filter((k) => /^bDelay|^bChorus/.test(k)).length;
      out.offHas = Object.keys(decodeSetup(offCode)).filter((k) => /^bDelay|^bChorus/.test(k)).length;
      el.planeLayerBoth.click(); await wait(20);
      return out;
    }""")
    tog, tb, tbm, ta, tplay, tboth = (tp[k] for k in ("together", "b", "bMoved", "a", "playB", "both"))
    check("with two layers Delay and chorus has a Layers row, on Together, and its controls write both layers' echo",
          not tog["row"] and tog["checked"] == ["Both"] and tog["title"] == "Delay and chorus" and tog["genA"] == 0.3
          and tog["genB"] == 0.3, str(tog))
    check("B there gives B its own effects - the Plane's row says so too - starting as A's, and shows B's",
          tb["own"] and tb["checked"] == ["B"] and tb["planeChecked"] == ["B"] and tb["bMix"] == 0.3
          and tb["title"] == "Delay and chorus \u00b7 layer B" and tb["edit"] == 1, str(tb))
    check("the echo's time and the chorus moved with B's shown are B's, and A's echo is untouched",
          tbm["bMs"] == 120 and tbm["genBMs"] == 120 and tbm["bChorus"] == 0.6 and tbm["genBChorus"] == 0.6
          and tbm["aMs"] == 375, str(tbm))
    check("A shows A's echo and writes A's alone",
          ta["title"] == "Delay and chorus \u00b7 layer A" and ta["aMix"] == 0.7 and ta["bMix"] == 0.3 and ta["genB"] == 0.3
          and ta["shownMs"] == "375", str(ta))
    check("the Play tab's B button shows B's echo here as well",
          tplay["checked"] == ["B"] and tplay["shownMix"] == "30" and tplay["shownMs"] == "120", str(tplay))
    check("B's own echo synced to a crotchet follows the tempo: 500 ms at 120, 1000 at 60, and A's stays free",
          tp["tempo"] == {"at120": 500, "at60": 1000, "aSync": "", "bSync": "1/4"}, str(tp["tempo"]))
    check("Together lets B's own go: B's echo follows A's again, and the generator is told",
          not tboth["own"] and tboth["bMix"] == 0.7 and tboth["bMs"] == 375 and tboth["genB"] == 0.7
          and tboth["checked"] == ["Both"] and tboth["planeChecked"] == ["Both"], str(tboth))
    check("B's own echo is written into a code and read back as it was",
          tp["back"] == tp["saved"] and tp["saved"]["sync"] == "1/4" and tp["saved"]["chorus"] == 0.6 and tp["onHas"] == 10,
          "%r / %r" % (tp["saved"], tp["back"]))
    check("a code of B's own with a field missing takes A's for it, and with it off none of it is written",
          tp["partial"]["mix"] == 0.45 and tp["partial"]["feedback"] == 0.6 and tp["offHas"] == 0, str(tp["partial"]))
    p.close()

    print("\n--- the site's default: the instrument ---")
    p = b.new_page(viewport={"width": 1400, "height": 900})
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(900)
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
      el.planeLayerB.click(); await wait(50);
      el.planeMirror.value = '1'; el.planeMirror.dispatchEvent(new Event('change'));
      const own = await lows();
      el.planeLayerBoth.click();
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
      el.timeLayerB.click(); await wait(50);
      slide('delayFeedback', 0); slide('delayMs', 21); slide('delayMix', 50);
      const eOwn = await big();
      el.timeLayerBoth.click();
      const eBack = await big();
      midiPanic();
      return { own, together, eDry, eOwn, eBack, kind: state.source.kind, driver: lfoDriver() };
    }""")
    print("    %s: lowest X, A's and B's: B's own mirror %.3f %.3f; Together %.3f %.3f"
          % (inst["kind"], inst["own"]["aX"], inst["own"]["bX"], inst["together"]["aX"], inst["together"]["bX"]))
    check("on the instrument, B's own mirror moved on its panel folds the B lanes it draws, and not A's",
          inst["kind"] == "host" and inst["own"]["lanes"] == 4 and inst["own"]["bX"] > -1e-3 and inst["own"]["bPeak"] > 0.05
          and inst["own"]["aX"] < -0.05, str(inst["own"]))
    check("and Together, with A's plane bare, folds neither", inst["together"]["bX"] < -0.05, str(inst["together"]))
    ed, eo, ebk = inst["eDry"], inst["eOwn"], inst["eBack"]
    print("    B's lanes and A's, largest: dry %.3f %.3f; B's own echo %.3f %.3f; Together again %.3f %.3f"
          % (ed["b"], ed["a"], eo["b"], eo["a"], ebk["b"], ebk["a"]))
    check("on the instrument, B's own echo moved on its panel makes B's lanes half as big again, and not A's",
          abs(eo["b"] / ed["b"] - 1.5) < 0.05 and abs(eo["a"] / ed["a"] - 1) < 0.02, "%.3f %.3f" % (eo["b"] / ed["b"], eo["a"] / ed["a"]))
    check("and Together, where the echo is A's and dry, B's are as they were", abs(ebk["b"] / ed["b"] - 1) < 0.02,
          "%.3f" % (ebk["b"] / ed["b"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("layer B's plane is its own")
