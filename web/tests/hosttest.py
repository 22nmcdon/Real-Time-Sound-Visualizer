"""The page inside the plugin: it finds JUCE's bridge, asks the plugin what it
is, and draws what the plugin played.

Run against a fake bridge, because the real one is a JUCE web view: the fake
answers the two native functions the page calls (`scopeHost`, `scopeReport`)
the way plugin/src/PluginEditor.cpp does, and serves the picture at the URL
it names. The picture is a known stereo signal - 441 Hz on the left at 0.6,
661.5 Hz on the right at 0.3 - so every check reads a number the page could
only get from the plugin's samples at the plugin's rate:

- the window the scope draws IS the plugin's frames, left and right, not
  swapped and not shifted;
- the dock measures 441 Hz and 661.5 Hz, which it can only do with the
  plugin's rate of 44.1 kHz rather than the page's own 48 kHz guess - the
  wrong rate reads 480 Hz on the left;
- one fetch in flight at a time, and they keep coming - against a fake that
  takes longer than two frames to answer, so a page that did not wait would
  have several in flight;
- the page reports back how the picture is getting through, which is how the
  spike's question was answered;
- and without the bridge the page is the website, on its own generator.

And the page as the plugin's face (plan, stage 3), against the fake's own
log of every call and its arguments:

- on load the page shows the plugin's state - a setup code with a slider
  moved since - and sends nothing back while it does, not even the preset it
  opened on before it knew it was hosted;
- a slider moved on the page is sent, by id and value, once;
- a newer state from the host is applied and one no newer is not, and
  applying it sends nothing back;
- a preset loaded on the page is sent whole, as a code that reads back as
  that preset.
"""
import base64, json, os, re, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

# The bridge as JUCE builds it - window.__JUCE__.backend with addEventListener
# and emitEvent - answering as the plugin's editor does.
FAKE = """
  (() => {
    const RATE = 44100, FRAMES = 8192;
    const listeners = new Map();
    window.__hostTest = { reports: [], fetches: 0, inFlight: 0, mostInFlight: 0, calls: [], log: [],
                          state: { version: 1, code: STATE_CODE } };
    const reply = (promiseId, result) => setTimeout(() => {
      for (const fn of listeners.get('__juce__complete') || []) fn({ promiseId, result });
    }, 0);
    window.__JUCE__ = {
      initialisationData: { __juce__functions: ['scopeHost', 'scopeReport', 'scopeSlider', 'scopeSetup', 'scopeState',
                                                 'scopeControl', 'scopeClick', 'scopeRoutings', 'scopeGesture'] },
      backend: {
        addEventListener(name, fn) { if (!listeners.has(name)) listeners.set(name, []); listeners.get(name).push(fn); },
        emitEvent(name, payload) {
          if (name !== '__juce__invoke') return;
          window.__hostTest.calls.push(payload.name);
          if (!['scopeHost', 'scopeState', 'scopeReport'].includes(payload.name)) window.__hostTest.log.push([payload.name, ...payload.params]);
          if (payload.name === 'scopeState') { reply(payload.resultId, window.__hostTest.state); return; }
          if (['scopeSlider', 'scopeSetup', 'scopeControl', 'scopeClick', 'scopeRoutings', 'scopeGesture'].includes(payload.name)) {
            reply(payload.resultId, true); return;
          }
          if (payload.name === 'scopeHost') {
            reply(payload.resultId, { host: 'plugin', rate: RATE, pictureFrames: FRAMES, pictureUrl: 'scope-test://picture.bin' });
          } else if (payload.name === 'scopeReport') {
            window.__hostTest.reports.push(payload.params[0]); reply(payload.resultId, null);
          }
        },
      },
    };
    // The plugin's last frames, oldest first: the same window every fetch,
    // so the page's copy can be compared with it exactly.
    const both = new Float32Array(FRAMES * 2);
    for (let k = 0; k < FRAMES; k++) {
      both[2 * k] = 0.6 * Math.sin(2 * Math.PI * 441 * k / RATE);
      both[2 * k + 1] = 0.3 * Math.sin(2 * Math.PI * 661.5 * k / RATE + 1);
    }
    window.__hostTest.picture = both;
    // The plugin's two oscillators, each a phase, a held value and a value, for a host that names them.
    window.__hostTest.lfos = new Float64Array([0, 0, 0, 0, 0, 0]);
    window.__hostTest.lfoFetches = 0;
    const realFetch = window.fetch.bind(window);
    window.fetch = (url, options) => {
      if (url === 'scope-test://lfos.bin') {
        window.__hostTest.lfoFetches++;
        return Promise.resolve(new Response(window.__hostTest.lfos.buffer.slice(0)));
      }
      if (url !== 'scope-test://picture.bin') return realFetch(url, options);
      const t = window.__hostTest;
      t.fetches++; t.inFlight++; t.mostInFlight = Math.max(t.mostInFlight, t.inFlight);
      /* Slower than two frames, on purpose: answered in 8 ms, faster than a
         frame, no two fetches could ever overlap, and a page that queued a
         fetch every frame without waiting passed as one that waited. */
      return new Promise((resolve) => setTimeout(() => {
        t.inFlight--;
        // Two lanes, or the four a band split serves when a check has asked for them.
        resolve(new Response((t.served || both).buffer.slice(0)));
      }, 40));
    };
  })();
"""

def centre(box): return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

def code(setup):
    """A setup code as the page and the plugin write them."""
    return base64.b64encode(json.dumps(dict(setup, v=4)).encode()).decode().rstrip("=")

# The plugin's state on load: a cutoff in its setup, and the level moved since.
FAKE = FAKE.replace("STATE_CODE", json.dumps(code({"vcfCut": 333, "pluginSliders": "amp=99"})))
# And a plugin that names its oscillators, as the plugin's editor does since 5s.
FAKE_LFOS = FAKE.replace("pictureUrl: 'scope-test://picture.bin' }",
                         "pictureUrl: 'scope-test://picture.bin', lfosUrl: 'scope-test://lfos.bin' }")
assert FAKE_LFOS != FAKE

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    print("\n--- without the bridge: the website ---")
    p = b.new_page(viewport={"width": 1400, "height": 900})
    # Since 5m the website is the instrument in a worklet, which answers the
    # same calls the plugin does; without the bridge it is that, and not the
    # plugin's - nothing fetched - and with ?brain=js no host at all.
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(800)
    alone = p.evaluate("() => ({ kind: state.source.kind, site: !!state.source.devices, fetched: !!state.source.timing })")
    p.goto(f"file://{ART}/scope.html?brain=js"); p.wait_for_timeout(800)
    own = p.evaluate("() => ({ kind: state.source.kind, host: scopeHost === null })")
    check("on its own the page is the website: the site's instrument, not the plugin's, and with ?brain=js its own generator (the null)",
          alone == {"kind": "host", "site": True, "fetched": False} and own == {"kind": "tone", "host": True}, "%s %s" % (alone, own))
    p.close()

    print("\n--- inside the plugin ---")
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.add_init_script(FAKE)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    seen = p.evaluate("""() => ({ kind: state.source.kind, rate: state.source.sampleRate, said: el.credit.textContent,
                                  asked: window.__hostTest.calls.slice(0, 1), sound: state.genSound })""")
    print("    %s" % seen)
    check("it asks the plugin what it is, and switches to the plugin's output at the plugin's rate",
          seen["kind"] == "host" and seen["rate"] == 44100 and seen["asked"] == ["scopeHost"]
          and "plugin" in seen["said"] and seen["sound"] is False, str(seen))

    window = p.evaluate("""() => {
      const lanes = state.source.getLatestWindow(4096), both = window.__hostTest.picture, F = 8192;
      let left = 0, right = 0, swapped = 0;
      for (let k = 0; k < 4096; k++) {
        const j = F - 4096 + k;
        left = Math.max(left, Math.abs(lanes[0][k] - both[2 * j]));
        right = Math.max(right, Math.abs(lanes[1][k] - both[2 * j + 1]));
        swapped = Math.max(swapped, Math.abs(lanes[0][k] - both[2 * j + 1]));
      }
      return { left, right, swapped };
    }""")
    check("the window the scope draws is the plugin's last frames, left as left and right as right",
          window["left"] == 0 and window["right"] == 0 and window["swapped"] > 0.1, str(window))

    p.wait_for_timeout(1500)
    dock = p.evaluate("() => el.measures.textContent")
    import re
    hz = [float(x) for x in re.findall(r"freq\s*([\d.]+)\s*Hz", dock)]
    print("    the dock reads %s" % hz)
    check("the dock measures 441 Hz and 661.5 Hz: the plugin's samples at the plugin's rate",
          len(hz) >= 2 and abs(hz[0] - 441) < 1 and abs(hz[1] - 661.5) < 1.5, dock[:160])

    flow = p.evaluate("""async () => {
      const t = window.__hostTest, before = t.fetches;
      await new Promise((r) => setTimeout(r, 1000));
      return { perSecond: t.fetches - before, most: t.mostInFlight, timed: state.source.timing.fetches };
    }""")
    check("it keeps fetching, frame after frame, with never more than one fetch in flight",
          flow["perSecond"] > 10 and flow["most"] == 1 and flow["timed"] > 20, str(flow))

    p.wait_for_timeout(2500)
    reports = p.evaluate("() => window.__hostTest.reports")
    last = reports[-1] if reports else {}
    print("    last report %s" % last)
    check("and it reports back how the picture is getting through: frames a second, fetches, their times",
          bool(reports) and last.get("fps", 0) > 0 and last.get("fetches", 0) > 20 and last.get("failed") == 0
          and last.get("meanMs", 0) >= 40, str(last))

    print("\n--- the page as the plugin's face ---")
    shown = p.evaluate("() => ({ cut: el.vcfCut.value, amp: el.amp.value, log: window.__hostTest.log.slice() })")
    check("on load the page shows the plugin's state, the slider moved since included, and sends nothing back",
          shown["cut"] == "333" and shown["amp"] == "99" and shown["log"] == [], str(shown))
    sent = p.evaluate("""() => {
      window.__hostTest.log.length = 0;
      el.vcfCut.value = '700'; el.vcfCut.dispatchEvent(new Event('input', { bubbles: true }));
      return window.__hostTest.log.slice();
    }""")
    check("a slider moved on the page is sent to the plugin, by id and value, once",
          sent == [["scopeSlider", "vcfCut", "700"]], str(sent))
    applied = p.evaluate("""async (codes) => {
      const t = window.__hostTest;
      t.log.length = 0;
      t.state = { version: 2, code: codes[0] };
      await new Promise((r) => setTimeout(r, 700));
      const newer = el.vcfCut.value;
      t.state = { version: 2, code: codes[1] };
      await new Promise((r) => setTimeout(r, 700));
      return { newer, same: el.vcfCut.value, log: t.log.slice() };
    }""", [code({"vcfCut": 222}), code({"vcfCut": 111})])
    check("a newer state from the host is applied, one no newer is not, and applying it sends nothing back",
          applied == {"newer": "222", "same": "222", "log": []}, str(applied))
    # Automation (F0 of web/docs/redesigning-the-face.md): every host knob's
    # move counted as the host's, and the page applied the whole state on
    # each - a full restore four times a second for as long as a lane played,
    # clearing the spectrogram and rebuilding the panel under the hand. The
    # plugin now says how many of its changes were loads, and which knobs the
    # host has moved since the last: a load is restored, a knob is moved.
    automated = p.evaluate("""async (codes) => {
      const t = window.__hostTest, wait = (ms) => new Promise((r) => setTimeout(r, ms));
      let restores = 0;
      const real = window.restore, seenBefore = hostSync.seen;
      window.restore = (x) => { restores++; return real(x); };
      t.log.length = 0;
      t.state = { version: 20, loads: 5, moved: "", code: codes[0] };
      await wait(700);
      const afterLoad = restores;
      // The page's own hand on the amplitude, sent and in the plugin's
      // hands as 42 a moment ago; the page has since moved it to 77.
      el.amp.value = '77';
      const cuts = [];
      for (let i = 1; i < codes.length; i++) {
        t.state = { version: 20 + i, loads: 5, moved: "vcfCut", code: codes[i] };
        await wait(320);
        cuts.push(el.vcfCut.value);
      }
      const during = restores - afterLoad;
      window.restore = real;
      // Back to the count the checks after this one number their states from.
      // The state is withdrawn first and a poll let through: left at version
      // 26, the next poll (every 250 ms) took it again after the count was put
      // back, and every later state, numbered 3 to 5, read as stale - the
      // checks after this one passed only when they beat that poll.
      t.state = null;
      await wait(400);
      hostSync.seen = seenBefore; hostSync.loads = null;
      return { afterLoad, during, cuts, amp: el.amp.value, log: t.log.filter((c) => c[0] !== 'scopeSlider' || c[1] !== 'amp') };
    }""", [code({"vcfCut": 222})] + [code({"vcfCut": 222, "pluginHands": [["s", "amp", "42"], ["s", "vcfCut", str(300 + 60 * i)]]})
                                     for i in range(6)])
    print("    automated: %s" % automated)
    check("a load from the host is restored once, and automation after it moves the knob without restoring anything",
          automated["afterLoad"] == 1 and automated["during"] == 0 and automated["cuts"][-1] == "600"
          and len(set(automated["cuts"])) >= 4, str(automated))
    check("and moves only what the host moved: the page's own hand on another knob stays where the hand left it, and nothing is sent back",
          automated["amp"] == "77" and automated["log"] == [], str(automated))
    preset = p.evaluate("""() => {
      const t = window.__hostTest;
      t.log.length = 0;
      // A preset of the new bank (P8g), since this is applyPreset's errand. It
      // was Wah, read back by its cutoff and routing; the bank's first preset
      // with a routing and an FM depth stands in, found by those rather than
      // by a name the bank's tuning may change.
      const pick = PRESETS.flatMap(([, e]) => e).find(([, st]) => st.mod && st.oscFm);
      applyPreset('b:' + pick[0]);
      const calls = t.log.slice();
      const sent = calls.length === 1 && calls[0][0] === 'scopeSetup' ? decodeSetup(calls[0][1]) : null;
      const glass = pick[1];
      // And the preset menu as the load left it, for the host's program number
      // (G8); a code pasted after it names no bank sound, which is the contrast.
      const chosen = calls.length === 1 ? calls[0][2] : null;
      t.log.length = 0;
      loadCode(encodeSetup(snapshot()));
      const pasted = t.log.length === 1 && t.log[0][0] === 'scopeSetup' ? t.log[0][2] : null;
      return { names: calls.map((c) => c[0]), fm: sent && sent.oscFm, wantFm: glass.oscFm, mod: sent && sent.mod, wantMod: glass.mod,
               chosen, want: 'b:' + pick[0], pasted };
    }""")
    check("a preset loaded on the page is sent to the plugin whole, as a code that reads back as that preset",
          preset["names"] == ["scopeSetup"] and preset["fm"] == preset["wantFm"] and preset["mod"] == preset["wantMod"]
          and preset["fm"] is not None and preset["mod"], str(preset))
    check("with the bank sound it is named by, for the host's program; a code pasted after it is named by nothing",
          preset["chosen"] == preset["want"] and preset["pasted"] == "", str(preset))

    sent = p.evaluate("""() => {
      const t = window.__hostTest, out = {};
      const send = (name, act) => { t.log.length = 0; act(); out[name] = t.log.slice(); };
      send('menu', () => { el.planeSnap.value = '6'; el.planeSnap.dispatchEvent(new Event('change', { bubbles: true })); });
      send('switch', () => { el.quantise.checked = true; el.quantise.dispatchEvent(new Event('change', { bubbles: true })); });
      send('view', () => { el.persistence.value = '0.3'; el.persistence.dispatchEvent(new Event('change', { bubbles: true })); });
      send('button', () => el.planeOS4.click());
      // A reference trace, the view's own: Swing again was this button until G2.
      send('other', () => el.saveReference.click());
      send('route', () => addRouting('lfo1', 'gen.freq'));
      send('depth', () => { state.modRoutings[state.modRoutings.length - 1].amount = 0.123456789012345; touchRoutings(); });
      send('again', () => touchRoutings());
      send('tiny', () => { state.modRoutings[state.modRoutings.length - 1].amount = 1e-7; touchRoutings(); });
      return out;
    }""")
    check("a menu turned on the page is sent to the plugin by id and value, a switch as true or false, once each",
          sent["menu"] == [["scopeControl", "planeSnap", "6"]] and sent["switch"] == [["scopeControl", "quantise", True]], str(sent))
    check("a button that reaches the sound is sent by its id, and so is the view's persistence; a button the plugin has no handler for is not",
          sent["button"] == [["scopeClick", "planeOS4"]] and sent["view"] == [["scopeControl", "persistence", "0.3"]]
          and sent["other"] == [], str(sent))
    # The view, which the plugin draws into its own grid for the photocell and
    # the picture's sources: its buttons by id, its lanes' switches, the
    # trigger's lane, the reticle as it moves, and the display and the zoom
    # from the keys and the wheel, which are hands on the button and the slider.
    view = p.evaluate("""() => {
      const t = window.__hostTest, out = {};
      const send = (name, act) => { t.log.length = 0; act(); out[name] = t.log.slice(); };
      const key = (k) => document.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true }));
      send('display', () => el.dispXY.click());
      send('lane', () => { el.ch2On.checked = false; el.ch2On.dispatchEvent(new Event('change', { bubbles: true })); });
      send('trigger', () => document.getElementById('trigSource1').click());
      send('reticle', () => movePhoto(0.25, 1.5));
      send('photo', () => el.photoButton.click());
      out.photoAt = photo.u + ',' + photo.v;
      send('keyDisplay', () => key('1'));
      send('keyZoom', () => key('+'));
      send('wheel', () => el.trace.dispatchEvent(new WheelEvent('wheel', { deltaY: -100, bubbles: true, cancelable: true })));
      send('cursors', () => { el.cursorsOn.checked = true; el.cursorsOn.dispatchEvent(new Event('change', { bubbles: true })); });
      out.zoom = el.zoom.value;
      return out;
    }""")
    check("the view's buttons, a lane's switch, the trigger's lane and the reticle are sent; the cursors, which no grid shows, are not",
          view["display"] == [["scopeClick", "dispXY"]] and view["lane"] == [["scopeControl", "ch2On", False]]
          and view["trigger"] == [["scopeClick", "trigSource1"]] and view["reticle"] == [["scopeControl", "photoReticle", "0.25,1"]]
          and view["photo"][:1] == [["scopeClick", "photoButton"]] and view["cursors"] == [], str(view))
    # Switched on, the page lands the reticle on the figure (P1) and sends the
    # plugin where it landed, after the press: the plugin's instrument does not
    # land by itself, so without this second message the two would read the
    # screen at different places. Checked as the place the page holds, exactly.
    check("pressing the photocell on sends the press, then the place the reticle landed",
          view["photo"] == [["scopeClick", "photoButton"], ["scopeControl", "photoReticle", view["photoAt"]]]
          and view["photoAt"] != "0.25,1", str(view["photo"]) + " at " + view["photoAt"])
    check("the display from a key is its button, and the zoom from a key or the wheel is the slider, one step each",
          view["keyDisplay"] == [["scopeClick", "dispYT"]] and len(view["keyZoom"]) == 1 and len(view["wheel"]) == 1
          and view["keyZoom"][0][:2] == ["scopeSlider", "zoom"] and view["wheel"][0][:2] == ["scopeSlider", "zoom"]
          and int(view["wheel"][0][2]) == int(view["keyZoom"][0][2]) + 1, str(view))
    route = sent["route"][0][1].split(";")[-1] if sent["route"] and len(sent["route"][0]) > 1 else ""
    check("an edit to the routings sends them whole, each depth to its last digit, and nothing when nothing changed",
          len(sent["route"]) == 1 and sent["route"][0][0] == "scopeRoutings" and route.startswith("lfo1>gen.freq@")
          and sent["depth"] == [["scopeRoutings", sent["route"][0][1].rsplit("@", 1)[0] + "@0.123456789012345"]]
          and sent["again"] == [] and len(sent["tiny"]) == 1 and sent["tiny"][0][1].endswith("@0.00000010000000000000"), str(sent))
    hands = [["c", "planeSnap", "5"], ["c", "quantise", True], ["k", "planeOS1"], ["c", "lfoShape1", "square"],
             ["r", "", "lfo2>gen.amp@-0.3456789"], ["s", "amp", "42"], ["k", "dispXY"], ["c", "photoReticle", "0.3,0.7"]]
    applied = p.evaluate("""async (code) => {
      const t = window.__hostTest;
      state.quantise = false; el.quantise.checked = false; syncQuantiser();
      const shown = selectedSource;
      t.log.length = 0;
      t.state = { version: 3, code };
      await new Promise((r) => setTimeout(r, 700));
      // The routings it put back are the plugin's already: touched again
      // unchanged, they are not sent back.
      touchRoutings();
      return { snap: plane.snap, menu: el.planeSnap.value, quantise: state.quantise, os: plane.os, lfo: lfos[1].shape,
               mod: state.modRoutings.map((r) => r.sourceId + '>' + r.destId + '@' + r.amount).join(';'), amp: el.amp.value,
               display: state.display, reticle: [photo.u, photo.v], shown: selectedSource === shown, log: t.log.slice() };
    }""", code({"vcfCut": 222, "pluginHands": hands}))
    check("the plugin's state puts its hands back on the page in order, menus, switches, buttons, routings, sliders, the view and the reticle, and sends nothing back",
          applied == {"snap": 5, "menu": "5", "quantise": True, "os": 1, "lfo": "square", "mod": "lfo2>gen.amp@-0.3456789",
                      "amp": "42", "display": "xy", "reticle": [0.3, 0.7], "shown": True, "log": []}, str(applied))

    more = p.evaluate("""() => {
      const t = window.__hostTest, out = {};
      const send = (name, act) => { t.log.length = 0; act(); out[name] = t.log.slice(); };
      // The header's Editing and a section's link (G6; the Keyboard's Edit A / B until then).
      send('layerB', () => document.getElementById('editHandB').click());
      send('layerA', () => document.getElementById('editHandA').click());
      send('link', () => document.getElementById('linkDelay').click());
      send('fade', () => { el.fadeMode.value = 'both'; el.fadeMode.dispatchEvent(new Event('change', { bubbles: true })); });
      send('fadeAgain', () => saveFade());
      send('restart', () => { el.fadeRestart.checked = true; el.fadeRestart.dispatchEvent(new Event('change', { bubbles: true })); });
      send('rate', () => {
        selectSource('lfo2');
        const r = document.getElementById('lfoRate1');
        r.value = '300'; r.dispatchEvent(new Event('input', { bubbles: true }));
      });
      return out;
    }""")
    fade = json.loads(more["fade"][0][1]) if more["fade"] and len(more["fade"][0]) > 1 else {}
    check("the hands' buttons and a link are sent; the fade is sent whole when it is saved, and not again unchanged",
          more["layerB"] == [["scopeClick", "editHandB"]] and more["layerA"] == [["scopeClick", "editHandA"]]
          and ["scopeClick", "linkDelay"] in more["link"]
          and len(more["fade"]) == 1 and more["fade"][0][0] == "scopeFade" and fade.get("mode") == "both" and len(fade.get("envs", [])) == 2
          and more["fadeAgain"] == [] and len(more["restart"]) == 1 and json.loads(more["restart"][0][1])["envs"][0]["restart"] is True,
          str(more))
    check("LFO 2's rate is sent as a slider, by its id",
          more["rate"] == [["scopeSlider", "lfoRate1", "300"]], str(more["rate"]))
    faded = p.evaluate("""async (codes) => {
      const t = window.__hostTest, out = {};
      t.log.length = 0;
      t.state = { version: 4, code: codes[0] };
      await new Promise((r) => setTimeout(r, 700));
      out.given = { mode: fade.mode, attack: fade.envs[0].attack, b: fade.envs[1].release, shown: el.fadeMode.value };
      t.state = { version: 5, code: codes[1] };
      await new Promise((r) => setTimeout(r, 700));
      out.none = { mode: fade.mode, attack: fade.envs[0].attack, restart: fade.envs[0].restart };
      // The fade it put back is the plugin's already: saved again unchanged, it is not sent back.
      saveFade();
      out.log = t.log.slice();
      return out;
    }""", [code({"pluginHands": [["f", "", {"mode": "in", "envs": [{"attack": 4}, {"release": 0.5}]}]]}), code({})])
    check("the plugin's fade is put back on the page, and with none told it, the fade's defaults; nothing is sent back",
          faded["given"] == {"mode": "in", "attack": 4, "b": 0.5, "shown": "in"}
          and faded["none"] == {"mode": "off", "attack": 2, "restart": False} and faded["log"] == [], str(faded))

    # The generator's panel, inside the plugin. A hosted page used to keep no
    # generator at all, so its whole section went from the panel - no kind,
    # no frequency, no shape - and its menus, had they been there, wrote to
    # nothing. Now the page keeps a mirror of the plugin's generator, by its
    # own handlers, and restores it from the plugin's state like the rest.
    # It was asked through the Kind menu until G2 took the drawings and the
    # menu with them; the Shape menu is asked now, and a state that names a
    # drawing as its kind puts the waveform's shape back and no kind at all.
    gen = p.evaluate("""async (code) => {
      const t = window.__hostTest, out = {};
      // Shape on Play and Frequency on Ink, each on its own tab since G3.
      setView('bench'); setBenchTab('play');
      await new Promise((r) => setTimeout(r, 200));
      const shapeShown = el.shape.offsetParent !== null;
      setBenchTab('ink'); await new Promise((r) => setTimeout(r, 100));
      out.shown = shapeShown && el.freq.offsetParent !== null;
      setBenchTab('play');
      out.sound = !!genVoice();
      t.log.length = 0;
      el.shape.value = 'square'; el.shape.dispatchEvent(new Event('change', { bubbles: true }));
      out.sent = t.log.slice();
      out.shape = genSettings().shape;
      // And a state from the plugin with another shape puts the mirror there.
      t.state = { version: 9, code };
      await new Promise((r) => setTimeout(r, 700));
      out.restored = genSettings().shape;
      out.menu = el.shape.value;
      out.kind = 'mode' in genSettings();
      // No setView('scope') back: the Scope view went in G4, and the face is the Bench.
      return out;
    }""", code({"gen": "figure", "shape": "triangle"}))
    check("inside the plugin the page keeps the generator's panel, its shape menu moves the page's generator and is sent",
          gen["shown"] and gen["shape"] == "square"
          and gen["sent"] == [["scopeControl", "shape", "square"]], str(gen))
    check("and the plugin's state puts the generator's shape back on the page, a drawing's kind with it ignored; "
          "heard through the host, the page has no voice of its own",
          gen["restored"] == "triangle" and gen["menu"] == "triangle" and gen["kind"] is False
          and gen["sound"] is False, str(gen))

    # The input (5g): inside the plugin, Mic is the host's input bus. The press
    # is sent; the device is the host's; a state that says the input is drawn
    # puts Mic back on the page, and one that does not puts Tone back.
    inp = p.evaluate("""async (codes) => {
      const t = window.__hostTest, out = {};
      t.log.length = 0;
      el.srcMic.click();
      out.sent = t.log.slice();
      out.mic = el.srcMic.getAttribute('aria-checked');
      out.device = el.device.disabled;
      out.micTitle = el.srcMic.title;
      t.log.length = 0;
      el.srcTone.click();
      out.toneSent = t.log.slice();
      // The generator's input, inside the plugin, is the host's: said so where the page would say what it is.
      el.inputMode.value = '1'; el.inputMode.dispatchEvent(new Event('change', { bubbles: true }));
      await new Promise((r) => setTimeout(r, 200));
      out.where = el.inputWhere.textContent;
      el.inputMode.value = '0'; el.inputMode.dispatchEvent(new Event('change', { bubbles: true }));
      t.log.length = 0;
      t.state = { version: 11, code: codes[0] };
      await new Promise((r) => setTimeout(r, 700));
      out.restored = [state.source.drawsInput, el.srcMic.getAttribute('aria-checked')];
      t.state = { version: 12, code: codes[1] };
      await new Promise((r) => setTimeout(r, 700));
      out.back = [state.source.drawsInput, el.srcTone.getAttribute('aria-checked')];
      out.log = t.log.slice();
      return out;
    }""", [code({"pluginInput": True}), code({})])
    check("inside the plugin, Mic is sent to the plugin as the host's input, Tone as its generator, and the device is the host's",
          inp["sent"] == [["scopeClick", "srcMic"]] and inp["toneSent"] == [["scopeClick", "srcTone"]] and inp["mic"] == "true"
          and inp["device"] is True and inp["micTitle"] == "The host's input"
          and inp["where"] == "From the host's input, once the host gives the plugin one.", str(inp))
    check("and the plugin's state puts the input back as drawn, or the generator, sending nothing back",
          inp["restored"] == [True, "true"] and inp["back"] == [False, "true"] and inp["log"] == [], str(inp))

    # The host's input split into bands (5j): Into bands sent as the plugin's
    # control, the four lanes it then serves drawn exactly as served, a band
    # soloed sent as one mix, Whole sent back; and the plugin's state putting
    # the split back, or the generator, sending nothing back.
    split = p.evaluate("""async (codes) => {
      const t = window.__hostTest, out = {};
      const four = new Float32Array(8192 * 4);
      for (let k = 0; k < 8192; k++) for (let c = 0; c < 4; c++) four[4 * k + c] = (c + 1) * 0.1 * Math.sin(2 * Math.PI * 100 * (c + 1) * k / 44100);
      el.srcMic.click();
      out.row = el.micShapeRow.hidden;
      t.log.length = 0;
      el.micBands.click();
      t.served = four;
      await new Promise((r) => setTimeout(r, 500));
      out.sent = t.log.slice();
      out.lanes = [state.source.channels, state.source.lanes.map((l) => l.name).join(',')];
      const w = state.source.getLatestWindow(8192);
      let off = 0, along = 0;
      for (let k = 0; k < 8192; k++) {
        for (let c = 0; c < 4; c++) off = Math.max(off, Math.abs(w[c][k] - four[4 * k + c]));
        along = Math.max(along, Math.abs(w[2][k] - four[4 * k + 3]));
      }
      out.off = off; out.along = along;
      t.log.length = 0;
      state.source.lanes[3].solo = true; state.source.remix();
      await new Promise((r) => setTimeout(r, 0));
      // The same mix again is not sent again.
      state.source.remix();
      await new Promise((r) => setTimeout(r, 0));
      out.mix = t.log.slice();
      state.source.lanes[3].solo = false; state.source.remix();
      await new Promise((r) => setTimeout(r, 0));
      t.log.length = 0;
      el.micWhole.click();
      t.served = null;
      await new Promise((r) => setTimeout(r, 400));
      out.whole = [t.log.slice(), state.source.channels];
      el.srcTone.click();
      await new Promise((r) => setTimeout(r, 200));
      t.log.length = 0;
      t.state = { version: 13, code: codes[0] };
      t.served = four;
      await new Promise((r) => setTimeout(r, 700));
      out.restored = [state.micBands, state.source.bands, state.source.channels, el.srcMic.getAttribute('aria-checked'), el.micBands.getAttribute('aria-checked')];
      t.state = { version: 14, code: codes[1] };
      t.served = null;
      await new Promise((r) => setTimeout(r, 700));
      out.back = [state.source.bands, state.source.channels, el.srcTone.getAttribute('aria-checked')];
      out.log = t.log.slice();
      /* Split again, read at once: the lanes past the two the plugin is still
         serving read as silence, not as the four it served before. Then Tone
         lets the split go without Whole. */
      el.srcMic.click();
      el.micBands.click();
      const early = state.source.getLatestWindow(1024);
      out.early = [early.length, Math.max(...early[2].map(Math.abs)), Math.max(...early[0].map(Math.abs)) > 0.1];
      el.srcTone.click();
      out.tone = [state.source.bands, state.source.channels];
      el.micWhole.click();
      return out;
    }""", [code({"pluginBands": True}), code({})])
    check("inside the plugin, Into bands is offered and sent, and the four lanes the plugin serves are drawn as served",
          split["row"] is False and split["sent"] == [["scopeControl", "srcBands", "1"]]
          and split["lanes"] == [4, "Low,Low mid,High mid,High"] and split["off"] == 0, str(split))
    check("and the comparison fails against the lanes one place along", split["along"] > 0.1, str(split["along"]))
    check("a band soloed is sent as one mix, and Whole as the input whole",
          split["mix"] == [["scopeControl", "laneMix", "0,0,0,1"]] and split["whole"] == [[["scopeControl", "srcBands", "0"]], 2], str(split))
    check("and the plugin's state puts the split back, or the generator, sending nothing back",
          split["restored"] == [True, True, 4, "true", "true"] and split["back"] == [False, 2, "true"] and split["log"] == [], str(split))
    check("a lane the plugin has not served yet reads as silence, and Tone lets the split go",
          split["early"] == [4, 0, True] and split["tone"] == [False, 2], str(split["early"]) + " " + str(split["tone"]))

    print("\n--- change gestures (second review, 1.2) ---")
    # A host records touch and latch automation by the gestures round a
    # parameter's moves. Each move the player makes of one of the host's
    # parameters must be inside one - begun as they take hold, ended as they
    # let go - and nothing else may be: a knob that is no parameter, the
    # host's own automation, a load. Real mouse and real keys, so the
    # browser's own default actions (an arrow's step, a native slider's drag)
    # are what is sent. Read from the fake's log as letters for one slider:
    # b a begin, v a value, e an end.
    def letters(log, sid):
        out = ""
        for c in log:
            if len(c) > 2 and c[1] == sid and c[0] == "scopeGesture": out += "b" if c[2] is True else "e"
            elif len(c) > 2 and c[1] == sid and c[0] == "scopeSlider": out += "v"
        return out
    def shaped(s): return re.fullmatch(r"bv+e", s) is not None
    def balanced(s):
        if re.fullmatch(r"(bv*e|v)*", s) is None: return -1
        return s.count("b")
    check("null: the shape is told from a drag with no begin, one ended twice, one begun twice and one with no value",
          not shaped("vvve") and not shaped("bvvee") and not shaped("bbvve") and not shaped("be") and shaped("bvve")
          and balanced("bvebve") == 2 and balanced("bvbvee") == -1 and balanced("bvv") == -1)
    p.evaluate("() => { closeOverlay(); setBenchTab('play'); }")
    p.wait_for_timeout(300)
    def face(sid):
        box = p.locator("#%s" % sid).locator("xpath=..").locator(".knob-face").bounding_box()
        return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    def logged(act, wait=300):
        p.evaluate("() => { window.__hostTest.log.length = 0; }")
        act()
        p.wait_for_timeout(wait)
        return p.evaluate("() => window.__hostTest.log.slice()")
    def drag(sid, dy=-30, hold=False, between=None):
        def go():
            x, y = face(sid)
            p.mouse.move(x, y); p.mouse.down()
            p.mouse.move(x, y + dy / 2, steps=4)
            if between: p.evaluate(between)
            p.mouse.move(x, y + dy, steps=4)
            if not hold: p.mouse.up()
        return go
    dragged = logged(drag("amp"))
    check("a knob that is a host parameter, dragged, is one gesture: begun, its values, ended",
          shaped(letters(dragged, "amp")) and [c[0] for c in dragged if c[0] == "scopeGesture"] == ["scopeGesture"] * 2,
          letters(dragged, "amp") + " " + str(dragged[:3]))
    # Taking hold is the begin, before anything moves: a host in touch mode holds the value from then.
    x, y = face("amp")
    pressed = logged(lambda: (p.mouse.move(x, y), p.mouse.down()), 100)
    released = logged(lambda: p.mouse.up(), 100)
    check("pressing the knob begins its gesture before it moves, and letting go unmoved ends it",
          letters(pressed, "amp") == "b" and letters(released, "amp") == "e", letters(pressed, "amp") + " " + letters(released, "amp"))
    # The ring's handle on a patched knob moves the depth, not the value: no gesture for the knob.
    p.evaluate("() => addRouting('lfo1', 'gen.amp')")
    p.wait_for_timeout(300)
    def ring():
        box = p.locator("#amp").locator("xpath=..").locator(".lane-handle").bounding_box()
        x, y = centre(box)
        p.mouse.move(x, y); p.mouse.down(); p.mouse.move(x + 25, y + 25, steps=5); p.mouse.up()
    ringed = logged(ring)
    p.evaluate("() => dropRouting('lfo1', 'gen.amp')")
    check("the ring's handle on a patched knob moves its depth and begins no gesture for the knob",
          letters(ringed, "amp") == "" and any(c[0] == "scopeRoutings" for c in ringed), str(ringed[:3]))
    attack = logged(drag("envAttack"))
    check("one that is not, dragged, is sent and begins nothing",
          not any(c[0] == "scopeGesture" for c in attack) and letters(attack, "envAttack").count("v") >= 2, str(attack[:3]))
    def keys():
        p.evaluate("() => el.amp.focus()")
        for _ in range(3): p.keyboard.press("ArrowUp")
    keyed = logged(keys, 800)
    check("three arrow keys on it are one gesture, ended once they have stopped", letters(keyed, "amp") == "bvvve",
          letters(keyed, "amp"))
    def taps():
        x, y = face("amp")
        p.mouse.click(x, y); p.mouse.click(x, y)
    tapped = logged(taps)
    # The first tap's end waits for its release's handlers, so a second tap
    # that comes first is the same gesture; either way the value is inside one.
    check("two taps that put it back send the value inside a gesture, none left open or nested",
          re.fullmatch(r"(be)?bve", letters(tapped, "amp")) is not None and p.evaluate("() => el.amp.value") == "55", letters(tapped, "amp"))
    def typed():
        x, y = face("amp")
        p.mouse.click(x, y, button="right")
        p.locator('.over.ctx [data-item="type"]').click()
        p.keyboard.press("Control+A"); p.keyboard.type("0.33"); p.keyboard.press("Enter")
    typing = logged(typed)
    def reset():
        x, y = face("amp")
        p.mouse.click(x, y, button="right")
        p.locator('.over.ctx [data-item="reset"]').click()
    resetting = logged(reset)
    check("Type a value and Reset are a gesture each round the one value they send, the typing's probes unsent",
          letters(typing, "amp") == "bve" and ["scopeSlider", "amp", "33"] in typing and letters(resetting, "amp") == "bve",
          letters(typing, "amp") + " " + letters(resetting, "amp"))
    morph = logged(lambda: (p.evaluate("() => showControl(el.morphPos)"), p.wait_for_timeout(300),
                            p.mouse.move(*centre(p.locator("#morphPos").bounding_box())), p.mouse.down(),
                            p.mouse.move(centre(p.locator("#morphPos").bounding_box())[0] + 40, centre(p.locator("#morphPos").bounding_box())[1], steps=5),
                            p.mouse.up(), p.keyboard.press("Escape")))
    check("the morph's fader, a plain slider, dragged is one gesture too", shaped(letters(morph, "morphPos")), letters(morph, "morphPos"))
    p.evaluate("() => { closeOverlay(); setBenchTab('play'); }")
    automated = p.evaluate("""async (code) => {
      const t = window.__hostTest;
      t.log.length = 0;
      t.state = { version: 40, loads: hostSync.loads, moved: 'amp', code };
      await new Promise((r) => setTimeout(r, 700));
      return { amp: el.amp.value, log: t.log.slice() };
    }""", code({"pluginHands": [["s", "amp", "91"]]}))
    check("the host's automation moving the knob moves it on the face, and sends back no gesture and no value",
          automated == {"amp": "91", "log": []}, str(automated))
    loaded = logged(drag("amp", between="() => applyPreset('n:' + BASE_NAME)"))
    order = [c[0] + ("+" if c[0] == "scopeGesture" and c[2] is True else "-" if c[0] == "scopeGesture" else "")
             for c in loaded if c[0] in ("scopeGesture", "scopeSetup")]
    check("a preset loaded mid-drag ends the gesture before the load is sent, and the hand still on the knob begins another",
          balanced(letters(loaded, "amp")) == 2 and order[:3] == ["scopeGesture+", "scopeGesture-", "scopeSetup"]
          and order[-1] == "scopeGesture-", letters(loaded, "amp") + " " + str(order))
    # And a load from the host - a program chosen in its list - while the knob is held: the same.
    hosted = logged(drag("amp", between="""async () => {
      window.__hostTest.state = { version: 50, loads: 99, moved: '', code: '%s' };
      await new Promise((r) => setTimeout(r, 700));
    }""" % code({"vcfCut": 300})))
    check("a load from the host mid-drag ends the gesture, and the hand still on the knob begins another",
          balanced(letters(hosted, "amp")) == 2 and p.evaluate("() => el.vcfCut.value") == "300", letters(hosted, "amp"))
    # Back to the middle, as the drags before may have taken it to the top, where a drag up moves nothing.
    p.evaluate("() => { el.amp.value = '55'; }")
    # Read while the button is still down: the end must be the blur's, not the release's.
    blurred = logged(lambda: (drag("amp", hold=True)(), p.evaluate("() => window.dispatchEvent(new Event('blur'))")), 100)
    held_open = p.evaluate("() => hostGestures.open.size + hostGestures.pointers.size")
    p.mouse.up()
    check("the window losing focus mid-drag ends the gesture there, with the button still down, and none is left open",
          shaped(letters(blurred, "amp")) and held_open == 0, letters(blurred, "amp") + ", %d open" % held_open)
    p.evaluate("() => { el.amp.value = '55'; window.__begin = gestureBegin; window.gestureBegin = () => {}; }")
    unbegun = logged(drag("amp"))
    p.evaluate("() => { window.gestureBegin = window.__begin; }")
    check("null: a page whose drag sends no begin is told apart", not shaped(letters(unbegun, "amp")) and "v" in letters(unbegun, "amp"),
          letters(unbegun, "amp"))

    print("\n--- the plugin's oscillators ---")
    # An oscillator routed to the sound and the picture moves both in step
    # only if the page's is the plugin's: fetched after each picture and
    # taken whole, never stepped here. Served values the page's own stepping
    # could not reach - a phase standing still while frames go by, then
    # jumping back - so a page still stepping its own reads as not taking them.
    OSC = """async (values) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const t = window.__hostTest, read = () => ({ driver: lfoDriver(), phases: lfos.map((l) => l.phase),
        helds: lfos.map((l) => l.held), values: lfos.map((l) => l.value), source: MOD_SOURCES.get('lfo1').value() });
      const out = {};
      t.lfos = new Float64Array(values[0]); await wait(400); out.first = read();
      await wait(400); out.still = read();
      t.lfos = new Float64Array(values[1]); await wait(400); out.second = read();
      out.fetched = [t.lfoFetches, t.fetches];
      return out;
    }"""
    SERVED = [[1.25, 0.4, -0.7, 4.0, -0.2, 0.33], [0.5, -0.9, 0.12, 6.0, 0.8, -0.45]]
    def osc(fake):
        q = b.new_page(viewport={"width": 1400, "height": 900})
        q.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
        q.add_init_script(fake)
        q.goto(f"file://{ART}/scope.html"); q.wait_for_timeout(1500)
        # Both oscillators running fast, so a page stepping its own moves them well past any served value.
        q.evaluate("() => { lfos[0].rate = 3; lfos[1].rate = 5; }")
        got = q.evaluate(OSC, SERVED)
        q.close()
        return got
    named, unnamed = osc(FAKE_LFOS), osc(FAKE)
    taken = lambda r, s: r["phases"] == [s[0], s[3]] and r["helds"] == [s[1], s[4]] and r["values"] == [s[2], s[5]]
    check("a plugin that names its oscillators drives the page's: the instrument steps them, and the page takes them whole",
          named["first"]["driver"] == "instrument" and taken(named["first"], SERVED[0]) and taken(named["still"], SERVED[0])
          and named["first"]["source"] == SERVED[0][2], str(named["first"]))
    check("and follows them when they move, even backwards, fetched as often as the picture",
          taken(named["second"], SERVED[1]) and named["fetched"][0] > 10 and abs(named["fetched"][0] - named["fetched"][1]) <= 2,
          "%s, fetched %s" % (named["second"]["phases"], named["fetched"]))
    check("and against a plugin that names none: the page steps its own and takes nothing",
          unnamed["first"]["driver"] == "main" and not taken(unnamed["first"], SERVED[0])
          and unnamed["first"]["phases"] != unnamed["still"]["phases"] and unnamed["fetched"][0] == 0, str(unnamed["first"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("inside the plugin, the page draws what the plugin played")
