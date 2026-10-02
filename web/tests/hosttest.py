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
import base64, json, os, sys
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
                                                 'scopeControl', 'scopeClick', 'scopeRoutings'] },
      backend: {
        addEventListener(name, fn) { if (!listeners.has(name)) listeners.set(name, []); listeners.get(name).push(fn); },
        emitEvent(name, payload) {
          if (name !== '__juce__invoke') return;
          window.__hostTest.calls.push(payload.name);
          if (!['scopeHost', 'scopeState', 'scopeReport'].includes(payload.name)) window.__hostTest.log.push([payload.name, ...payload.params]);
          if (payload.name === 'scopeState') { reply(payload.resultId, window.__hostTest.state); return; }
          if (['scopeSlider', 'scopeSetup', 'scopeControl', 'scopeClick', 'scopeRoutings'].includes(payload.name)) {
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
    const realFetch = window.fetch.bind(window);
    window.fetch = (url, options) => {
      if (url !== 'scope-test://picture.bin') return realFetch(url, options);
      const t = window.__hostTest;
      t.fetches++; t.inFlight++; t.mostInFlight = Math.max(t.mostInFlight, t.inFlight);
      /* Slower than two frames, on purpose: answered in 8 ms, faster than a
         frame, no two fetches could ever overlap, and a page that queued a
         fetch every frame without waiting passed as one that waited. */
      return new Promise((resolve) => setTimeout(() => {
        t.inFlight--;
        resolve(new Response(both.buffer.slice(0)));
      }, 40));
    };
  })();
"""

def code(setup):
    """A setup code as the page and the plugin write them."""
    return base64.b64encode(json.dumps(dict(setup, v=4)).encode()).decode().rstrip("=")

# The plugin's state on load: a cutoff in its setup, and the level moved since.
FAKE = FAKE.replace("STATE_CODE", json.dumps(code({"vcfCut": 333, "pluginSliders": "amp=99"})))

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    print("\n--- without the bridge: the website ---")
    p = b.new_page(viewport={"width": 1400, "height": 900})
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(800)
    alone = p.evaluate("() => ({ kind: state.source.kind, host: scopeHost === null })")
    check("on its own the page is the website: no bridge, its own generator (the null)",
          alone == {"kind": "tone", "host": True}, str(alone))
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
    preset = p.evaluate("""() => {
      const t = window.__hostTest;
      t.log.length = 0;
      applyPreset('b:Wah');
      const calls = t.log.slice();
      const sent = calls.length === 1 && calls[0][0] === 'scopeSetup' ? decodeSetup(calls[0][1]) : null;
      const wah = findPreset('b:Wah');
      return { names: calls.map((c) => c[0]), cut: sent && sent.vcfCut, wantCut: wah.vcfCut, mod: sent && sent.mod, wantMod: wah.mod };
    }""")
    check("a preset loaded on the page is sent to the plugin whole, as a code that reads back as that preset",
          preset["names"] == ["scopeSetup"] and preset["cut"] == preset["wantCut"] and preset["mod"] == preset["wantMod"]
          and preset["cut"] is not None, str(preset))

    sent = p.evaluate("""() => {
      const t = window.__hostTest, out = {};
      const send = (name, act) => { t.log.length = 0; act(); out[name] = t.log.slice(); };
      send('menu', () => { el.planeKaleido.value = '6'; el.planeKaleido.dispatchEvent(new Event('change', { bubbles: true })); });
      send('switch', () => { el.crossOn.checked = true; el.crossOn.dispatchEvent(new Event('change', { bubbles: true })); });
      send('view', () => { el.persistence.value = '0.3'; el.persistence.dispatchEvent(new Event('change', { bubbles: true })); });
      send('button', () => el.planeOS4.click());
      send('other', () => el.reswing.click());
      send('route', () => addRouting('lfo1', 'gen.freq'));
      send('depth', () => { state.modRoutings[state.modRoutings.length - 1].amount = 0.123456789012345; touchRoutings(); });
      send('again', () => touchRoutings());
      send('tiny', () => { state.modRoutings[state.modRoutings.length - 1].amount = 1e-7; touchRoutings(); });
      return out;
    }""")
    check("a menu turned on the page is sent to the plugin by id and value, a switch as true or false, once each",
          sent["menu"] == [["scopeControl", "planeKaleido", "6"]] and sent["switch"] == [["scopeControl", "crossOn", True]], str(sent))
    check("a button that reaches the sound is sent by its id; the view's menu and a button the plugin has no handler for are not",
          sent["button"] == [["scopeClick", "planeOS4"]] and sent["view"] == [] and sent["other"] == [], str(sent))
    route = sent["route"][0][1].split(";")[-1] if sent["route"] and len(sent["route"][0]) > 1 else ""
    check("an edit to the routings sends them whole, each depth to its last digit, and nothing when nothing changed",
          len(sent["route"]) == 1 and sent["route"][0][0] == "scopeRoutings" and route.startswith("lfo1>gen.freq@")
          and sent["depth"] == [["scopeRoutings", sent["route"][0][1].rsplit("@", 1)[0] + "@0.123456789012345"]]
          and sent["again"] == [] and len(sent["tiny"]) == 1 and sent["tiny"][0][1].endswith("@0.00000010000000000000"), str(sent))
    hands = [["c", "planeKaleido", "4"], ["c", "crossOn", True], ["k", "planeOS1"], ["c", "lfoShape1", "square"],
             ["r", "", "lfo2>gen.amp@-0.3456789"], ["s", "amp", "42"]]
    applied = p.evaluate("""async (code) => {
      const t = window.__hostTest;
      cross.on = false; el.crossOn.checked = false;
      const shown = selectedSource;
      t.log.length = 0;
      t.state = { version: 3, code };
      await new Promise((r) => setTimeout(r, 700));
      // The routings it put back are the plugin's already: touched again
      // unchanged, they are not sent back.
      touchRoutings();
      return { kaleido: plane.kaleido, menu: el.planeKaleido.value, cross: cross.on, os: plane.os, lfo: lfos[1].shape,
               mod: state.modRoutings.map((r) => r.sourceId + '>' + r.destId + '@' + r.amount).join(';'), amp: el.amp.value,
               shown: selectedSource === shown, log: t.log.slice() };
    }""", code({"vcfCut": 222, "pluginHands": hands}))
    check("the plugin's state puts its hands back on the page in order, menus, switches, buttons, routings and sliders, and sends nothing back",
          applied == {"kaleido": 4, "menu": "4", "cross": True, "os": 1, "lfo": "square", "mod": "lfo2>gen.amp@-0.3456789",
                      "amp": "42", "shown": True, "log": []}, str(applied))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("inside the plugin, the page draws what the plugin played")
