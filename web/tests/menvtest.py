"""The Envelope's own (8 Nov): a modulation envelope with its own four times.

What would go wrong, and what is checked for it:

- the controls built twice, or lost: they are written once in the page and
  moved into the Envelope's editor while it is open; LFO 1's editor opened
  after it must not have them, there must be one of each id after going
  round, and the Envelope's again must;
- a switch that paints and does not send: ticked with the mouse, the
  generator's own field must turn, the card must read "its own" and the
  knobs come alive; a knob moved by hand must reach the generator in its
  units;
- the source reading the wrong envelope: with a slow attack of its own and
  Play's quick one, a held note's Envelope must still be low after a tenth
  of a second, where Play's has long since arrived - and the null is the
  same note following Play, which must read near the top;
- what it moves: routed onto a control, the control's push must follow the
  slow envelope, not the quick one;
- codes: the five go out and come back; an old code without them follows
  Play, as it did; a time past its range is held to it.
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

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.locator("#trace").click(position={"x": 5, "y": 5}); p.wait_for_timeout(500)
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(200)

    print("\n--- the editor ---")
    where = """() => ({ inEditor: !!el.srcDetail.querySelector('#menvControls'), shown: !el.menvControls.hidden,
      ids: ['menvOwn', 'menvAtk', 'menvDec', 'menvSus', 'menvRel'].map((id) => document.querySelectorAll('#' + id).length) })"""
    p.locator('.mod-card[data-source="env.note"]').click(); p.wait_for_timeout(250)
    env1 = p.evaluate(where)
    p.locator('.mod-card[data-source="lfo1"]').click(); p.wait_for_timeout(250)
    lfo = p.evaluate(where)
    p.locator('.mod-card[data-source="env.note"]').click(); p.wait_for_timeout(250)
    env2 = p.evaluate(where)
    check("the Envelope's editor holds its own switch and four knobs", env1["inEditor"] and env1["shown"], str(env1))
    check("LFO 1's does not, and they are home and hidden", not lfo["inEditor"] and not lfo["shown"], str(lfo))
    check("the Envelope's has them again, and there is one of each id throughout",
          env2["inEditor"] and all(n == 1 for n in env1["ids"] + lfo["ids"] + env2["ids"]), str(env2))

    print("\n--- the switch and the knobs, by hand ---")
    before = p.evaluate("() => ({ own: genSettings().menvOwn, reading: cardReading(MOD_SOURCES.get('env.note')), dis: el.menvAtk.disabled })")
    p.locator("#menvOwn").check(); p.wait_for_timeout(150)
    after = p.evaluate("() => ({ own: genSettings().menvOwn, reading: cardReading(MOD_SOURCES.get('env.note')), dis: el.menvAtk.disabled })")
    check("unticked it follows Play: the generator's field off, the card says so, the knobs asleep",
          before == {"own": False, "reading": "follows Play", "dis": True}, str(before))
    check("ticked with the mouse, the generator's field turns, the card reads its own and the knobs wake",
          after == {"own": True, "reading": "its own", "dis": False}, str(after))
    knobs = p.evaluate("""() => {
      for (const [id, v] of [['menvAtk', 700], ['menvDec', 900], ['menvSus', 25], ['menvRel', 1200]]) setControl(id, v);
      const t = genSettings();
      return [t.menvAttackMs, t.menvDecayMs, t.menvSustain, t.menvReleaseMs, el.menvSusValue.textContent, el.menvAtkValue.textContent];
    }""")
    check("the knobs reach the generator in its units, with their readings", knobs == [700, 900, 0.25, 1200, "0.25", "700 ms"], str(knobs))

    print("\n--- the source reads its own ---")
    READ = """async ([own]) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.menvOwn.checked = own; el.menvOwn.dispatchEvent(new Event('change'));
      setControl('envAttack', 5);
      setScreenKeys(true); await wait(150);
      midiNoteOn(60, 100); await wait(150);
      const early = MOD_SOURCES.get('env.note').value();
      await wait(500);
      const later = MOD_SOURCES.get('env.note').value();
      midiNoteOff(60); await wait(50); midiPanic(); await wait(300);
      return { early, later };
    }"""
    own = p.evaluate(READ, [True])
    play = p.evaluate(READ, [False])
    check("its own, a 700 ms attack, is still low 150 ms into a held note, and higher half a second on",
          own["early"] < 0.45 and own["later"] > own["early"] + 0.2, str(own))
    # Play's attack is 5 ms and its decay 120: by 150 ms it is at its sustain,
    # 0.7 of the velocity, and still there half a second on. (The first null
    # asked for "near the top" and Play reads 0.55 there - sustain times a
    # velocity of 100 - which is the amplifier's shape, not a slow one.)
    check("null: following Play, the same note has stopped moving by 150 ms, where its own was still rising",
          abs(play["later"] - play["early"]) < 0.02 and play["early"] > 0.3, str(play))

    print("\n--- what it moves ---")
    moved = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.menvOwn.checked = true; el.menvOwn.dispatchEvent(new Event('change'));
      state.modRoutings = []; touchRoutings();
      // The screen's rotation, a destination the page's own matrix sums each frame.
      addRouting('env.note', 'view.rotate');
      const routing = state.modRoutings.find((r) => r.sourceId === 'env.note');
      routing.amount = 1; touchRoutings();
      midiNoteOn(60, 100); await wait(150);
      const early = state.rotateMod;
      await wait(500);
      const later = state.rotateMod;
      midiNoteOff(60); midiPanic(); state.modRoutings = []; touchRoutings();
      return { early, later };
    }""")
    check("routed onto the rotation, the push follows the slow envelope: low early, higher later",
          moved["later"] > moved["early"] + 0.1, str(moved))

    print("\n--- codes ---")
    codes = p.evaluate("""() => {
      const read = () => { const t = genSettings(); return [t.menvOwn, t.menvAttackMs, t.menvDecayMs, t.menvSustain, t.menvReleaseMs]; };
      restore(Object.assign(snapshot(), { menvOwn: true, menvAtk: 40, menvDec: 1500, menvSus: 80, menvRel: 2500 }));
      const set = read(), code = snapshot();
      restore(Object.assign(snapshot(), { menvAtk: 99999, menvRel: -5 }));
      const held = read();
      const old = snapshot(); for (const k of ['menvOwn', 'menvAtk', 'menvDec', 'menvSus', 'menvRel']) delete old[k];
      restore(old);
      return { set, code: [code.menvOwn, code.menvAtk, code.menvDec, code.menvSus, code.menvRel], held, old: read(),
               reading: cardReading(MOD_SOURCES.get('env.note')) };
    }""")
    check("a code's own envelope comes back into the generator", codes["set"] == [True, 40, 1500, 0.8, 2500], str(codes["set"]))
    check("and goes out again", codes["code"] == [True, 40, 1500, 80, 2500], str(codes["code"]))
    check("times past their range are held to it", codes["held"][1] == 2000 and codes["held"][4] == 1, str(codes["held"]))
    check("an old code without them follows Play, as it did", codes["old"][0] is False and codes["reading"] == "follows Play",
          "%s %s" % (codes["old"], codes["reading"]))

    print("\n--- it fits the smallest window ---")
    # Its own column grows by the switch and four knobs; a dozen destinations
    # fill the other. At the plugin's minimum nothing in the editor may
    # scroll. The null is a window too short for it at full size, which must.
    FIT = """async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setView('bench'); state.modRoutings = []; touchRoutings();
      const dests = Array.from(MOD_DESTS.values()).filter((d) => routingAllowed(MOD_SOURCES.get('env.note'), d)).slice(0, 12);
      for (const d of dests) addRouting('env.note', d.id);
      openModCard('env.note'); el.menvOwn.checked = true; el.menvOwn.dispatchEvent(new Event('change')); await wait(200);
      const own = el.srcDetail.querySelector('.src-own'), goes = el.srcDetail.querySelector('.src-goes');
      return { rows: el.srcDetail.querySelectorAll('.mod-edit').length,
               over: Math.max(el.modEditor.scrollHeight - el.modEditor.clientHeight, own.scrollHeight - own.clientHeight,
                              goes.scrollHeight - goes.clientHeight) };
    }"""
    def fit_at(w, h, size=None):
        q = b.new_page(viewport={"width": w, "height": h})
        q.goto(f"file://{ART}/scope.html"); q.wait_for_timeout(700)
        if q.locator("#helpClose").is_visible(): q.locator("#helpClose").click()
        if size: q.evaluate("(z) => setSize(z)", size); q.wait_for_timeout(200)
        r = q.evaluate(FIT)
        if size: q.evaluate("() => setSize('auto')")
        q.close()
        return r
    small = fit_at(960, 600)
    check("at 960x600, its own envelope ticked and a dozen destinations, nothing in the editor scrolls",
          small["rows"] == 12 and small["over"] <= 0, str(small))
    short = fit_at(960, 420, 1)
    check("null: at 960x420 and 100% something in it does", short["over"] > 0, str(short))
    b.close()

if bad:
    print("  FAIL  the page threw: " + "; ".join(bad[:3])); fails.append("pageerror")
print("\n%d failed" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
