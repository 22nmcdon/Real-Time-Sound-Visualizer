"""Fading a routing in and out, and a sound loaded landing at once, as the
face shows it and the instrument plays it.

Asked for so that patching a source need not be a jump in the sound and a
snap in the picture. Loading a preset glided its knobs and faded in its
routings too, until the owner found that playing straight after a switch was
playing a sound that was neither (11 Nov): a sound loaded lands now, whatever
the fade.

The instrument fades its own routings (Matrix::fadeStep, Matrix::load) and
serves the face each one's gain and where the drawing's dot is
(Instrument::fadeServed, Matrix::dot, since stage 5's step 5b). Until step 6
most of this suite held the page's own fade - its gains, its routes into its
generator, a sound loaded landing by every way there is, every preset in the
library landing as itself, the envelope's stretches on a note and on two
layers - on the page's own brain; that went in step 6, and
core/tests/core_tests.py holds the instrument's fade to what the page's did.
What is held here:

- heard: a preset's tremolo, on the instrument, whole within two seconds of
  the load, where the same routing patched by hand is faded in;
- the face reading the instrument's fade: a knob's ring moving with its gain,
  and the dot with its dot, each against a value the page's own fade was left
  holding;
- the envelope drawn and taken hold of, its layers' tabs, and the setting
  kept in this browser rather than in the setup code, where every preset
  load would put it back to off before its routings could fade.
"""
import json, os, sys
import corpus
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
# The compiled core's generator, rendered in the page (stage 5, step 6): compiled_core.js.
COMPILED_CORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compiled_core.js")
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

HELPERS = """
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
"""

# A keyboard, so the sources that step with your playing are there to fade.
STUB = """
  window.__midi = { port: null };
  navigator.requestMIDIAccess = function () {
    const port = { id: "stub", name: "Stub Keyboard", onmidimessage: null };
    window.__midi.port = port;
    return Promise.resolve({ inputs: new Map([["stub", port]]), outputs: new Map(), onstatechange: null });
  };
  window.__send = (bytes) => window.__midi.port.onmidimessage({ data: Uint8Array.from(bytes) });
"""

def run(p, body):
    return p.evaluate("async () => {" + HELPERS + body + "}")

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    p = ctx.new_page()
    p.add_init_script(STUB)
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.add_init_script(path=COMPILED_CORE)
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(700)
    corpus.install(p)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    # The page's own fade - its gains, its routes into the generator, a
    # sound loaded landing, every preset in the library landing as itself -
    # was held here on the page's own brain until stage 5's step 6 deleted
    # it. The instrument fades its own routings (Matrix::fadeStep, Matrix::load)
    # and core/tests/core_tests.py holds them to what the page's fade did
    # (its restore section, recorded the day before). What is left here is the
    # face: what it hears the instrument do, what it shows of the instrument's
    # fade, and the drawing of the envelope, taken hold of.

    print("\n--- heard: a preset's tremolo, on the instrument ---")
    # What the instrument plays, not what the page says: a held note, the
    # fade's attack at eight seconds, and a preset whose one routing is an LFO
    # at twelve hertz on the level at 0.9. Read off the picture every 50 ms
    # after the load - a window of 4096 samples, the last tenth of a second
    # and one cycle of the LFO - as the quietest cycle of the note over the
    # loudest: whole, about 0.1, and under 0.3 only past three quarters of
    # the way in. Landed, it is there as soon as the load is heard - a
    # restore costs a few hundred milliseconds of the page's own time here,
    # more with other suites beside it, and the instrument hears the setup
    # after it, so it is given two seconds; faded in, it would be a quarter of
    # the way at two seconds, about 0.8, and under 0.3 at six. The null on
    # the same routing patched by a hand, which a fade eases.
    HEARD = """async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const depth = () => {
        const [l] = state.source.getLatestWindow(4096), at = [];
        for (let k = 1; k < l.length; k++) if (l[k - 1] < 0 && l[k] >= 0) at.push(k - 1 + l[k - 1] / (l[k - 1] - l[k]));
        const peaks = [];
        for (let i = 0; i + 1 < at.length; i++) { let m = 0; for (let k = Math.floor(at[i]); k < at[i + 1]; k++) m = Math.max(m, Math.abs(l[k])); peaks.push(m); }
        return peaks.length > 10 ? +(Math.min(...peaks) / Math.max(...peaks)).toFixed(3) : null;
      };
      const TREM = { shape: 'sine', freq: 220, midiMode: 'mono', display: 'xy', pictureAmount: 0, oscScan: 0,
                     mod: 'lfo1>gen.amp@0.900', l0r: 1200, l0a: 100, l0s: 'sine' };
      PRESETS.unshift(['Fade test', [['Tremolo for the fade test', TREM, 'x', ['a', 'b']]], 'generator']);
      try {
        setFade('both'); setFadeEnvelope({ attack: 8, release: 2, attackMid: 0.5, releaseMid: 0.5, sustain: 1, delay: 0 }, 0); saveFade();
        // How long after `from` the tremolo is whole, and how deep it is then; none within two seconds, null.
        const whole = async (from) => {
          for (let i = 0; i < 80; i++) {
            await wait(50); const d = depth();
            // Then a window later, all of it after the load: the first can straddle it.
            if (d !== null && d < 0.3) { const ms = Math.round(performance.now() - from); await wait(150); return { ms, d: depth() }; }
            if (performance.now() - from > 2000) break;
          }
          return { ms: null, d: depth() };
        };
        applyPreset('n:' + BASE_NAME); await wait(300);
        el.midiMono.click(); midiNoteOn(57, 127); await wait(600);
        const still = depth();
        let from = performance.now();
        applyPreset('b:Tremolo for the fade test');
        const loaded = await whole(from); await wait(2000); const settled = depth();
        applyPreset('n:' + BASE_NAME); await wait(600);
        from = performance.now();
        addRouting('lfo1', 'gen.amp'); state.modRoutings.find((r) => r.sourceId === 'lfo1').amount = 0.9; touchRoutings();
        const patched = await whole(from);
        midiPanic(); setFade('off'); applyPreset('n:' + BASE_NAME);
        return { kind: state.source.kind, still, loaded, settled, patched };
      } finally { PRESETS.shift(); }
    }"""
    # Until stage 5, step 3, batch 4 (13 Nov) this ran on a second page on
    # ?picture=0&brain=js as well, the page's own generator, and then checked
    # "the two brains are the two: the instrument, then the page's own". That
    # brain is being retired; the instrument's leg holds both claims, and what
    # is left of the pair is that the leg is the instrument's - read off the
    # source the run itself reports, since a page still on its boot tone
    # would hear the page's generator and pass.
    q = ctx.new_page()
    q.add_init_script(STUB)
    q.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    q.add_init_script(path=COMPILED_CORE)
    q.goto(f"file://{ART}/scope.html?picture=0"); q.wait_for_timeout(1500)
    if q.locator("#helpClose").is_visible(): q.locator("#helpClose").click()
    for label, page in (("the instrument", q),):
        got = page.evaluate(HEARD)
        print("    %s: %s" % (label, got))
        check("on %s a held note is steady before, and the tremolo is whole within two seconds of the load, as deep as it settles" % label,
              got["still"] is not None and got["still"] > 0.95 and got["loaded"]["ms"] is not None
              and got["settled"] is not None and abs(got["loaded"]["d"] - got["settled"]) < 0.08, str(got))
        check("null: on %s the same routing patched by hand is not whole within two seconds" % label,
              got["patched"]["ms"] is None and got["patched"]["d"] is not None and got["patched"]["d"] > 0.5, str(got))
    check("and what was heard is the instrument's", got["kind"] == "host", got["kind"])

    print("\n--- the face reads the instrument's fade ---")
    # LFO 1 onto the drive, a source the instrument has, faded in over a
    # second and a half. A knob's ring is its routings' live push as the
    # destination hears it (sweepOf), which since 5b's second half takes each
    # routing's gain from the instrument; and the dot is the instrument's.
    # The nulls: the page's own fade left holding a gain of its own (0.123,
    # still) and a dot of its own (a gate in its release), which a face still
    # reading the page's would show.
    FACE = """async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setFade('off'); applyPreset('n:' + BASE_NAME); await wait(300);
      setFade('both'); setFadeEnvelope({ delay: 0, attack: 1.5, release: 1, sustain: 1, attackMid: 0.5, releaseMid: 0.5 }, 0); saveFade();
      await wait(200);
      addRouting('lfo1', 'gen.drive');
      await wait(500);
      const key = 'lfo1>gen.drive', dest = MOD_DESTS.get('gen.drive');
      const served = () => (state.source.fadeGains || []).find((g) => g.key === key);
      // The page's own fade left holding something else entirely.
      fade.gains.set(key, { ramps: [rampStill(0.123, 0), rampStill(0.123, 1)], routing: state.modRoutings[0] });
      fade.last[0] = { gate: { on: false, at: performance.now(), from: 1, layer: 0 } };
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      const s = served(), r = state.modRoutings.find((x) => x.sourceId === 'lfo1');
      const live = sweepOf(dest, routingsFor('gen.drive')).live, now = sourceNow(MOD_SOURCES.get('lfo1'));
      const g = envGeometry(fade.envs[0]);
      const out = { gain: s ? s.gains[0] : null, faceGain: fadeGain(key, 0), live, want: now * routingDepth(r, 0) * fadeGain(key, 0),
                    page: now * routingDepth(r, 0) * 0.123, dot: { x: +envParts.dot.getAttribute('cx'), shown: envParts.dot.getAttribute('visibility') },
                    served: state.source.face.dots[0], attack: [g.waitEnd, g.peak] };
      dropRoutingOn('lfo1', 'gen.drive'); setFade('off');
      return out;
    }"""
    face = q.evaluate(FACE)
    print("    %s" % face)
    check("a knob's ring moves with the instrument's gain on its routing, part of the way into its fade",
          face["gain"] is not None and 0.05 < face["gain"] < 0.95 and face["faceGain"] == face["gain"]
          and abs(face["live"] - face["want"]) < 1e-9, str(face))
    check("null: not with the gain the page's own fade was left holding",
          abs(face["live"] - face["page"]) > 1e-3 and face["faceGain"] != 0.123, str(face))
    check("and the dot rides the instrument's attack, not the release the page's own was left in",
          face["served"] is not None and face["served"]["stage"] == "attack" and face["dot"]["shown"] == "visible"
          and face["attack"][0] < face["dot"]["x"] < face["attack"][1], str(face))
    # Back to the page's own brain for the rest, in front: a page behind another is given no frames.
    q.close()
    p.bring_to_front()

    print("\n--- the envelope drawn, and taken hold of ---")
    drawn = p.evaluate("""() => {
      fade.editing = 0;
      setFadeEnvelope({ delay: 1.25, attack: 2.5, decay: 0.4, sustain: 0.5, release: 0.9,
                        attackMid: 0.8, decayMid: 0.5, releaseMid: 0.3 }); drawFadeEnvelope();
      const at = (name) => ['cx', 'cy'].map((a) => +(+envParts[name].getAttribute(a)).toFixed(2));
      const points = envParts.attack.getAttribute('d').slice(1).split('L').map((p) => p.split(',').map(Number));
      return { wait: at('wait'), peak: at('peak'), corner: at('corner'), end: at('end'), attackMid: at('attackMid'),
               decayMid: at('decayMid'), releaseMid: at('releaseMid'),
               curveMid: +points[ENV.samples / 2][1].toFixed(2), text: el.fadeEnvValue.textContent };
    }""")
    print("    %s" % drawn)
    # Worked by hand: the wait ends at 6 + 24 x sqrt(1.25 / 5) = 18; the peak
    # 60 x sqrt(2.5 / 10) = 30 on, at 48; the corner 60 x sqrt(0.4 / 10) = 12
    # on, at 60, and at half height, 54 - 46 x 0.5 = 31; the hold is 20, so the
    # release starts at 80 and ends 60 x sqrt(0.9 / 10) = 18 on, at 98. The
    # attack's shape 0.8 sits at 54 - 46 x 0.8 = 17.2; the decay's midpoint at
    # 1 - 0.5 x 0.5 = 0.75 of full, 19.5; the release's at 0.5 x 0.7 = 0.35, 37.9.
    check("the handles sit where the numbers put them, and the attack's curve passes through its shape handle",
          drawn["wait"] == [18, 54] and drawn["peak"] == [48, 8] and drawn["corner"] == [60, 31] and drawn["end"] == [98, 54]
          and drawn["attackMid"] == [33, 17.2] and drawn["decayMid"] == [54, 19.5] and drawn["releaseMid"] == [89, 37.9]
          and drawn["curveMid"] == 17.2 and drawn["text"] == "In 2.5 s \u00b7 Out 0.90 s", str(drawn))

    p.evaluate("""() => { setFadeEnvelope({ delay: 0, attack: 1, decay: 1, sustain: 0.6, release: 1,
                                            attackMid: 0.5, decayMid: 0.5, releaseMid: 0.5 }); drawFadeEnvelope(); showControl('fadeMode');
                  // In Routings since G5a (Settings from F4): the envelope is under its menu, and a hand scrolls to it if it must.
                  el.fadeEnv.scrollIntoView({ block: 'nearest' }); }""")
    p.wait_for_timeout(200)
    def drag(name, dx, dy):
        box = p.locator('#fadeEnv [data-handle="%s"]' % name).bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        p.mouse.move(x, y); p.mouse.down(); p.mouse.move(x + dx / 2, y + dy / 2); p.mouse.move(x + dx, y + dy); p.mouse.up()
    E = "() => { const e = fade.envs[0]; return Object.fromEntries(Object.entries(e).map(([k, v]) => [k, typeof v === 'number' ? +v.toFixed(3) : v])); }"
    unmoved = p.evaluate(E)
    check("before the drag the envelope is where it was set",
          [unmoved[k] for k in ("delay", "attack", "decay", "sustain", "attackMid", "releaseMid")] == [0, 1, 1, 0.6, 0.5, 0.5],
          str(unmoved))
    drag("wait", 20, 0); drag("peak", 25, 0); drag("corner", 15, -15); drag("attackMid", 0, -12); drag("releaseMid", 0, 8)
    p.locator('#fadeEnv [data-handle="end"]').focus(); p.keyboard.press("ArrowRight")
    moved = p.evaluate(E)
    print("    after dragging and a key: %s" % moved)
    check("dragging moves each stretch: the wait longer, the attack longer, the corner later and higher, the shapes quicker",
          moved["delay"] > 0.2 and moved["attack"] > 1.5 and moved["decay"] > 1.2 and moved["sustain"] > 0.7
          and moved["attackMid"] > 0.6 and moved["releaseMid"] > 0.6, str(moved))
    check("and the arrow keys move a handle: the end a tenth longer", abs(moved["release"] - 1.1) < 1e-6, str(moved))

    # As drawn (19 Nov, from a review of testing): its rules were scoped to `.env-draw` on 17 Nov and the
    # drawing never had the class, so its words stood at the page's 16 px and ran together ("heldout") and
    # its points were grey discs with no line between them. Read off the rendered boxes: every shown word
    # and point inside the drawing, the words apart from each other and small, the line drawn. The null is
    # the class taken away, as it was.
    SEEN = """() => { const svg = el.fadeEnv, R = (n) => n.getBoundingClientRect(), box = R(svg);
      const shown = (n) => n.getAttribute('visibility') !== 'hidden' && getComputedStyle(n).display !== 'none';
      const words = [...svg.querySelectorAll('.env-label')].filter(shown).map((t) => ({ t: t.textContent, r: R(t) }));
      const points = [...svg.querySelectorAll('.env-handle')].filter(shown).map(R);
      const inside = (r) => r.left >= box.left - 0.5 && r.right <= box.right + 0.5 && r.top >= box.top - 0.5 && r.bottom <= box.bottom + 0.5;
      let overlap = [];
      for (let i = 0; i < words.length; i++) for (let j = i + 1; j < words.length; j++) {
        const a = words[i].r, b = words[j].r;
        if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom) overlap.push(words[i].t + '/' + words[j].t);
      }
      const line = svg.querySelector('.env-line:not(.off)') || svg.querySelector('.env-line'), cs = getComputedStyle(line);
      return { words: words.map((w) => w.t), overlap, out: words.filter((w) => !inside(w.r)).map((w) => w.t).concat(points.filter((r) => !inside(r)).map(() => 'a point')),
               tall: Math.max(0, ...words.map((w) => w.r.height)), stroke: cs.stroke, strokeW: parseFloat(cs.strokeWidth), fill: cs.fill }; }"""
    p.evaluate("() => { setFade('both'); setFadeEnvelope({ delay: 0, attack: 2, decay: 0.5, sustain: 1, release: 2, attackMid: 0.5, decayMid: 0.5, releaseMid: 0.5 }, 0); drawFadeEnvelope(); }")
    p.wait_for_timeout(200)
    seen = p.evaluate(SEEN)
    print("    as drawn: %s" % seen)
    check("the fade's drawing as drawn: its words (%s) small, apart and inside it, every point inside it, and its line stroked"
          % ", ".join(seen["words"]), len(seen["words"]) >= 3 and not seen["overlap"] and not seen["out"] and seen["tall"] <= 12
          and seen["stroke"] not in ("none", "") and seen["strokeW"] > 0 and seen["fill"] == "none", str(seen))
    p.evaluate("() => el.fadeEnv.classList.remove('env-draw')"); p.wait_for_timeout(100)
    bare = p.evaluate(SEEN)
    p.evaluate("() => { el.fadeEnv.classList.add('env-draw'); setFade('off'); }")
    check("null: without its class, as testing had it, the words are seen to run together or stand too tall (%s, %.1f px)" % (bare["overlap"], bare["tall"]),
         bool(bare["overlap"]) or bare["tall"] > 12, str(bare))

    ui = run(p, """
      setFade('off'); restore({ midiMode: 'poly', layers: 'layer' }); await wait(200);
      setFade('both'); await wait(100);
      const shown = !el.fadeLayers.hidden;
      el.fadeEditB.click(); const editing = fade.editing;
      el.fadeRestart.click(); el.fadeLoop.click();
      const b = { restart: fade.envs[1].restart, loop: fade.envs[1].loop }, a = { restart: fade.envs[0].restart, loop: fade.envs[0].loop };
      const ghost = envParts.ghost.getAttribute('d').length > 0, label = el.fadeEnvValue.textContent.slice(0, 2);
      el.fadeRestart.click(); el.fadeLoop.click(); el.fadeEditA.click();
      restore({ midiMode: 'poly' }); await wait(200);
      const hiddenAfter = el.fadeLayers.hidden, back = fade.editing, noGhost = envParts.ghost.getAttribute('d') === '';
      setFade('off');
      return { shown, editing, a, b, ghost, label, hiddenAfter, back, noGhost };
    """)
    print("    %s" % ui)
    check("layered, A and B appear, B draws and takes Restart and Loop for itself, with A faint behind; unlayered they go",
          ui["shown"] and ui["editing"] == 1 and ui["b"] == {"restart": True, "loop": True}
          and ui["a"] == {"restart": False, "loop": False} and ui["ghost"] and ui["label"] == "B:"
          and ui["hiddenAfter"] and ui["back"] == 0 and ui["noGhost"], str(ui))

    # Where the dot rides is the instrument's (Matrix::dot), held above in
    # "the face reads the instrument's fade" against the page's own reckoning.

    print("\n--- kept in this browser ---")
    p.evaluate("""() => { setFade('both');
      setFadeEnvelope({ delay: 0.3, attack: 3.5, decay: 0.8, sustain: 0.4, release: 0.25, attackMid: 0.7, releaseMid: 0.2, loop: true }, 0);
      setFadeEnvelope({ attack: 0.1, restart: true }, 1); saveFade(); }""")
    p.reload(); p.wait_for_timeout(700)
    kept = p.evaluate("""() => ({ mode: fade.mode, a: fade.envs[0], b: { attack: fade.envs[1].attack, restart: fade.envs[1].restart },
                                  shown: el.fadeMode.value, text: el.fadeEnvValue.textContent })""")
    check("the fade and both envelopes come back after a reload, on the panel too",
          kept["mode"] == "both" and kept["shown"] == "both" and kept["text"] == "In 3.5 s \u00b7 Out 0.25 s"
          and {k: kept["a"][k] for k in ("delay", "attack", "decay", "sustain", "release", "attackMid", "releaseMid", "loop")}
              == {"delay": 0.3, "attack": 3.5, "decay": 0.8, "sustain": 0.4, "release": 0.25, "attackMid": 0.7, "releaseMid": 0.2, "loop": True}
          and kept["b"] == {"attack": 0.1, "restart": True}, str(kept))
    # Stored by the versions before: one time for both halves, and then in, out and their shapes.
    for stored, want in [({"mode": "in", "seconds": 3}, (3, 3, 0.5)),
                         ({"mode": "in", "inSeconds": 1.5, "outSeconds": 4, "inMid": 0.7, "outMid": 0.5}, (1.5, 4, 0.7))]:
        p.evaluate("(v) => window.localStorage.setItem('scope.fade', JSON.stringify(v))", stored)
        p.reload(); p.wait_for_timeout(700)
        old = p.evaluate("() => [fade.mode].concat([0, 1].map((l) => [fade.envs[l].attack, fade.envs[l].release, fade.envs[l].attackMid]))")
        check("and one stored as %s comes back on both layers" % sorted(stored), old == ["in", list(want), list(want)], str(old))
    p.evaluate("() => { window.localStorage.removeItem('scope.fade'); }")

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("routings fade in and out on every path, and a sound loaded lands at once")
