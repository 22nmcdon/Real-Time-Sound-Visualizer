"""The rack (F5): the effects as modules, top to bottom in the order the sound
goes through them.

What would go wrong, and what is checked for it:

- a switch that changes its pill and not the sound: off must take the
  module's Mix to nought in the control *and* in what the engine reads
  (`echo.*`, the plane's own fields), and on must put back what it had, not
  the default - so the value it is set to first is not the default, or a
  switch that forgot what it held and put the default back would pass;
- the Plane's switch missing a shaping: every one it covers, the screen's
  turn among them, is set away from rest, switched off and read back at
  rest, and switched on and read back as it was. B's own turn counts only
  while B has a plane of its own, and both halves of that are read;
- the Plane with nothing to put back turning itself on at something it
  chose: it opens its rest instead and moves nothing;
- a module's line that only an input event writes: a setup is restored
  under the rack, with no event, and the lines and switches must follow it
  within the half second the tab lines take. The null is the line read
  before the restore;
- two modules open at once, or an arrow that does not close its own;
- an off module that does not fold to its line, or one that is open and
  still folded;
- search and `showControl` not reaching a control under a module's arrow;
- the modules out of the order the engine runs them in, which the rack's
  title claims they are in;
- the Reverb slot being a module: it has no switch, no controls, and is last;
- the tab's line and the rack disagreeing: a plane only turned is "Plane" on
  both, where the rule before F5 called it Dry;
- the old name: no "Echo" on the rack, and the plugin's host knob is
  "Delay mix".
"""
import os, re, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(ART)
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
    p.evaluate("() => { setView('bench'); setBenchTab('space'); }"); p.wait_for_timeout(300)

    print("\n--- the modules, in order ---")
    order = p.evaluate("""() => Array.from(document.querySelectorAll('#rackGroup > .fx-module'))
      .map((m) => m.dataset.fx || (m.classList.contains('fx-slot') ? 'slot' : '?'))""")
    # The engine's order (core/include/scope/plane.h, step): the plane, then
    # the phaser, so the chorus and the delay copy the phased pair. The first
    # build of the rack put them Delay, Chorus, Phaser under a title saying it
    # was the sound's order; the null is that order.
    engine = ["plane", "phaser", "chorus", "delay", "reverb"]
    check("Plane, Phaser, Chorus, Delay, then the Reverb slot, top to bottom, as the engine runs them",
          order == engine, str(order))
    check("null: the first build's order is not what is there", order != ["plane", "delay", "chorus", "phaser", "reverb"])
    src = open(os.path.join(ROOT, "core", "include", "scope", "plane.h")).read()
    check("and the core still says the phaser comes first",
          "The phaser first, so the chorus and the echoes are of the phased pair" in src)
    slot = p.evaluate("""() => { const s = document.querySelector('.fx-module[data-fx="reverb"]');
      return { slot: s.classList.contains('fx-slot'), inputs: s.querySelectorAll('input, select, button').length,
               text: s.textContent.replace(/\\s+/g, ' ').trim() }; }""")
    check("the Reverb is a slot with nothing to play", slot["slot"] and slot["inputs"] == 0 and "P9" in slot["text"], str(slot))
    names = p.evaluate("() => document.getElementById('rackGroup').innerText")
    check("the rack says Delay and never Echo", "Delay" in names and not re.search(r"\becho\b", names, re.I),
          names[:120].replace("\n", " | "))
    host = open(os.path.join(ROOT, "plugin", "src", "PluginProcessor.h")).read()
    check("the plugin's host knob is Delay mix", '"Delay mix"' in host and '"Echo"' not in host)
    mixes = p.evaluate("""() => ['delay', 'chorus', 'phaser'].map((fx) => {
      const row = document.getElementById(FX_MIX[fx][0]).closest('.menu-row');
      return row.querySelector('.menu-label').textContent.trim(); })""")
    check("every effect's first knob is called Mix", mixes == ["Mix", "Mix", "Mix"], str(mixes))

    print("\n--- a switch moves the sound and puts it back ---")
    sw = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const pill = (fx) => document.querySelector('.fx-on[data-fx-on="' + fx + '"]');
      setControl('chorusMix', 45); paintRack();
      const before = { on: pill('chorus').getAttribute('aria-pressed'), engine: echo.chorus };
      pill('chorus').click(); await wait(50);
      const off = { mix: el.chorusMix.value, engine: echo.chorus, on: pill('chorus').getAttribute('aria-pressed'),
                    sum: document.querySelector('[data-fx-sum="chorus"]').textContent };
      pill('chorus').click(); await wait(50);
      const back = { mix: el.chorusMix.value, engine: echo.chorus, on: pill('chorus').getAttribute('aria-pressed') };
      // Switched on from a fresh page: the module's default Mix, not nought.
      setControl('phaserMix', 0); delete fxKept.phaser; paintRack();
      pill('phaser').click(); await wait(50);
      const fresh = { mix: el.phaserMix.value, engine: echo.phaser };
      setControl('phaserMix', 0);
      return { before, off, back, fresh };
    }""")
    print("    %s" % sw)
    check("on, a chorus at 45 says so", sw["before"] == {"on": "true", "engine": 0.45}, str(sw["before"]))
    check("off takes its Mix to nought, in the control and in what the engine reads",
          sw["off"]["mix"] == "0" and sw["off"]["engine"] == 0 and sw["off"]["on"] == "false" and sw["off"]["sum"] == "Off",
          str(sw["off"]))
    check("on puts back the 45 it had, not the default 30", sw["back"] == {"mix": "45", "engine": 0.45, "on": "true"},
          str(sw["back"]))
    check("null: the default is not what came back", sw["back"]["mix"] != "30")
    check("with nothing kept, on is the module's default Mix", sw["fresh"] == {"mix": "30", "engine": 0.3}, str(sw["fresh"]))

    plane = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const pill = document.querySelector('.fx-on[data-fx-on="plane"]');
      const read = () => Object.fromEntries(PLANE_SHAPING.map(([id]) => [id, el[id].value]));
      const engine = () => [plane.mirror, plane.limit, plane.twist, plane.snap, plane.scaleX, plane.scaleY,
                            plane.shear, state.rotate];
      const away = { planeMirror: '1', planeLimit: '1', planeTwist: '20', planeSnap: '6',
                     planeScaleX: '80', planeScaleY: '120', planeShear: '30', rotate: '10', planeTurn: '0' };
      // Nothing kept yet: on opens the rest and moves nothing.
      delete fxKept.plane; openFx(null);
      const rest0 = read(); pill.click(); await wait(50);
      const opened = { open: document.getElementById('rackGroup').dataset.open || null, same: JSON.stringify(read()) === JSON.stringify(rest0) };
      openFx(null);
      for (const [id, v] of Object.entries(away)) setControl(id, v);
      const set = { values: read(), engine: engine(), on: fxOn('plane') };
      pill.click(); await wait(50);
      const off = { values: read(), engine: engine(), on: fxOn('plane') };
      pill.click(); await wait(50);
      const back = { values: read(), engine: engine(), on: fxOn('plane') };
      pill.click(); await wait(50);
      // B's own turn: nothing while B shares A's plane, the Plane on once B has its own.
      setControl('planeTurn', '12'); paintRack();
      const shared = fxOn('plane');
      planeB.own = true;
      const own = fxOn('plane');
      planeB.own = false; setControl('planeTurn', '0'); paintRack();
      return { opened, away, set, off, back, rest: Object.fromEntries(PLANE_SHAPING), shared, own };
    }""")
    print("    %s" % plane)
    check("the Plane with nothing to put back opens its rest and moves nothing",
          plane["opened"] == {"open": "plane", "same": True}, str(plane["opened"]))
    check("every shaping set away from rest reads on", plane["set"]["on"] and plane["set"]["values"] == plane["away"],
          str(plane["set"]))
    check("off puts every one at rest, the turn too, in the controls and the engine",
          not plane["off"]["on"] and plane["off"]["values"] == plane["rest"]
          and plane["off"]["engine"] == [0, 0, 0, 0, 1, 1, 0, 0], str(plane["off"]))
    check("null: the shaped plane is not at rest", plane["set"]["values"] != plane["rest"])
    check("on puts every one back as it was", plane["back"]["on"] and plane["back"]["values"] == plane["away"]
          and plane["back"]["engine"] == plane["set"]["engine"], str(plane["back"]))
    check("B's own turn is nothing while B shares A's plane, and the Plane on once B has its own",
          plane["shared"] is False and plane["own"] is True, str((plane["shared"], plane["own"])))

    print("\n--- the lines follow values written with no event ---")
    lines = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      restore({}); await wait(400);
      const sum = (fx) => document.querySelector('[data-fx-sum="' + fx + '"]').textContent;
      const on = (fx) => document.querySelector('.fx-module[data-fx="' + fx + '"]').dataset.on;
      const before = { delay: sum('delay'), on: on('delay'), line: document.getElementById('benchLine-space').textContent };
      restore({ delayMix: 50, delayMs: 250, delayPingPong: true, chorusMix: 20, chorusRate: 150 });
      await wait(600);
      const after = { delay: sum('delay'), on: on('delay'), chorus: sum('chorus'),
                      line: document.getElementById('benchLine-space').textContent };
      restore({ rotate: 10 }); await wait(600);
      const turned = { plane: sum('plane'), line: document.getElementById('benchLine-space').textContent };
      restore({}); await wait(400);
      return { before, after, turned };
    }""")
    print("    %s" % lines)
    check("null: before the restore the delay is off and the tab is Dry",
          lines["before"] == {"delay": "Off", "on": "0", "line": "Dry"}, str(lines["before"]))
    check("a setup restored under the rack switches the delay on and writes its line",
          lines["after"]["on"] == "1" and lines["after"]["delay"] == "250 ms · ping-pong"
          and lines["after"]["chorus"] == "1.50 Hz", str(lines["after"]))
    check("and the tab's line names both, in the rack's order", lines["after"]["line"] == "Chorus · delay", lines["after"]["line"])
    check("a plane only turned is the Plane on, in the module and on the tab, where it was Dry before F5",
          lines["turned"] == {"plane": "turned 36°", "line": "Plane"}, str(lines["turned"]))

    print("\n--- one open at a time, and an off module folds to its line ---")
    opens = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const arrow = (fx) => document.querySelector('.fx-open[data-fx-open="' + fx + '"]');
      const open = () => Array.from(document.querySelectorAll('.fx-module[data-fx]'))
        .filter((m) => m.querySelector('.fx-rest') && !m.querySelector('.fx-rest').hidden).map((m) => m.dataset.fx);
      const shown = (fx) => getComputedStyle(document.querySelector('.fx-module[data-fx="' + fx + '"] .fx-main')).display !== 'none';
      openFx(null);
      setControl('delayMix', 40); setControl('chorusMix', 0); paintRack(); await wait(50);
      const rest = { open: open(), delayMain: shown('delay'), chorusMain: shown('chorus'),
                     chorusArrow: getComputedStyle(arrow('chorus')).display !== 'none' };
      arrow('delay').click(); await wait(50);
      const one = { open: open(), expanded: arrow('delay').getAttribute('aria-expanded') };
      openFx('chorus'); await wait(50);
      const two = { open: open(), chorusMain: shown('chorus'), delayExpanded: arrow('delay').getAttribute('aria-expanded') };
      arrow('chorus').click(); await wait(50);
      const none = { open: open() };
      setControl('delayMix', 0); paintRack();
      return { rest, one, two, none };
    }""")
    print("    %s" % opens)
    check("at rest none is open; an on module shows its knobs and an off one folds to its line, arrow and all",
          opens["rest"] == {"open": [], "delayMain": True, "chorusMain": False, "chorusArrow": False}, str(opens["rest"]))
    check("an arrow opens its module", opens["one"] == {"open": ["delay"], "expanded": "true"}, str(opens["one"]))
    check("opening another closes the first, and an off module opened shows its knobs",
          opens["two"] == {"open": ["chorus"], "chorusMain": True, "delayExpanded": "false"}, str(opens["two"]))
    check("null: two modules open is not what is there", opens["two"]["open"] != ["delay", "chorus"])
    check("its own arrow closes it", opens["none"] == {"open": []}, str(opens["none"]))

    print("\n--- reaching a control under an arrow ---")
    reach = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      openFx(null); setBenchTab('play'); await wait(100);
      showControl('chorusFeedback'); await wait(200);
      const fb = el.chorusFeedback.getBoundingClientRect();
      const shown = { tab: benchTab, open: document.getElementById('rackGroup').dataset.open || null,
                      visible: fb.width > 0 && fb.height > 0 };
      openFx(null); setBenchTab('play'); await wait(100);
      showControl('delayMix'); await wait(200);
      const main = { tab: benchTab, open: document.getElementById('rackGroup').dataset.open || null };
      return { shown, main };
    }""")
    print("    %s" % reach)
    check("showControl on a control in a module's rest: its tab, that module open, the control on screen",
          reach["shown"] == {"tab": "space", "open": "chorus", "visible": True}, str(reach["shown"]))
    check("and on a main knob it opens nothing", reach["main"] == {"tab": "space", "open": None}, str(reach["main"]))

    p.evaluate("() => { setBenchTab('space'); openFx('plane', true); }"); p.wait_for_timeout(200)
    os.makedirs(os.path.join(HERE, "shots"), exist_ok=True)
    p.screenshot(path=os.path.join(HERE, "shots", "rack-plane.png"))
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
