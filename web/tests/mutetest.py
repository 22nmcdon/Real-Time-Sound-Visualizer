"""A hand muted, Retrigger's switch, and two truths the owner's report turned up
(23 Nov), on the face: what the core does with each is core/tests/pieces/
mute.py, retrig.py and vcfvel.py; here, that the face sends it, shows it,
keeps it out of everything stored, and says it.

What would go wrong, and what is checked for it:

- MUTE. A mute that is saved: the setup, its code and undo's history are the
  same with a hand muted as without, and a preset or a code loaded unmutes
  both (the null: the mute was really on before the load). A mute that never
  reaches the instrument: each press sends "handMute" with the hand's bit,
  and with the upper hand muted a note above the split is silent at the
  speakers while one below sounds (the null: unmuted, the note above
  sounds). Alt-click hears a hand alone, and again both. The muted hand is
  seen: its name struck through, its keys under a wash. One hand again
  unmutes both, and the mutes are not there with one hand.
- RETRIGGER. Shown in Dyad and Mono and not in Poly, stored as `midiRetrig`
  and only when on, sent to the instrument as a hand.
- THE UPPER HAND'S OWN RESPONSE. Its five controls say, while the upper
  hand's own is edited, that they act only while each hand draws its own
  figure; the lower hand's and a linked Picture's say the doc's line (the
  null).
"""
import os, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)
def null(name, ok, detail=""): check("null: " + name, ok, detail)

# What reaches the speakers, tapped where the page connects to them, and every call the face makes of the instrument.
INIT = """
window.__rec = []; window.__recOn = false; window.__calls = [];
const real = AudioNode.prototype.connect;
AudioNode.prototype.connect = function (dest, ...rest) {
  if (dest && dest.context && dest === dest.context.destination && !this.__tapped) {
    this.__tapped = true;
    const sp = dest.context.createScriptProcessor(4096, 2, 2);
    sp.onaudioprocess = (e) => { if (window.__recOn) window.__rec.push(Array.from(e.inputBuffer.getChannelData(0))); };
    real.call(this, sp); real.call(sp, dest.context.destination);
  }
  return real.call(this, dest, ...rest);
};
"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.add_init_script(INIT)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_function("state.source && state.source.kind === 'host'", timeout=20000)
    p.evaluate("""() => { const call = scopeHost.call.bind(scopeHost);
      scopeHost.call = (name, ...args) => { window.__calls.push([name, ...args]); return call(name, ...args); }; }""")

    print("\n--- the mutes: only with two hands ---")
    one = p.evaluate("() => [document.getElementById('handsPick').hidden, handMuted.slice()]")
    p.evaluate("() => showControl('shape')"); p.wait_for_timeout(200)
    p.locator("#midiPoly").click(); p.locator("#midiTwoHands").click(); p.wait_for_timeout(200)
    p.locator("#midiKindKey").click(); p.wait_for_timeout(300)
    shown = p.evaluate("() => [document.getElementById('handsPick').hidden, document.getElementById('muteHandA').offsetWidth > 0, document.getElementById('muteHandB').offsetWidth > 0]")
    check("with one hand the hands and their mutes are not there; with two each hand has one",
          one == [True, [False, False]] and shown == [False, True, True], "%s, %s" % (one, shown))

    before = p.evaluate("() => [JSON.stringify(snapshot()), undoHistory.undo.length]")
    p.evaluate("() => { window.__calls = []; }")
    p.locator("#muteHandB").click(); p.wait_for_timeout(600)
    after = p.evaluate("""() => [JSON.stringify(snapshot()), undoHistory.undo.length, handMuted.slice(), window.__calls.filter((c) => c[1] === 'handMute'),
      document.getElementById('editHandB').classList.contains('is-muted'), document.getElementById('muteHandB').getAttribute('aria-checked'),
      el.midiStrip.querySelectorAll('[data-muted]').length, Array.from(el.midiStrip.querySelectorAll('[data-muted]')).every((r) => {
        const k = r.nextElementSibling && r.parentNode.querySelector('rect.k[x="' + r.getAttribute('x') + '"]'); return !k || Number(k.dataset.note) >= midi.layers.point; })]""")
    check("a press mutes the upper hand and tells the instrument its bit, 2",
          after[2] == [False, True] and after[3] == [["scopeControl", "handMute", "2"]], "%s, %s" % (after[2], after[3]))
    check("and nothing stored moves: the setup and undo's history are as they were", after[0] == before[0] and after[1] == before[1],
          "undo %d against %d" % (after[1], before[1]))
    check("the muted hand is seen: its name struck through, its switch on, its keys and only its keys washed",
          after[4] and after[5] == "true" and after[6] > 10 and after[7], "%s %s %d %s" % tuple(after[4:8]))

    print("\n--- heard: the muted hand is silent at the speakers ---")
    def heard(note):
        p.evaluate("() => { window.__rec = []; window.__recOn = true; }"); p.wait_for_timeout(250)
        p.evaluate("(n) => scopeHost.midi([0x90, n, 100])", note); p.wait_for_timeout(700)
        p.evaluate("(n) => scopeHost.midi([0x80, n, 0])", note); p.wait_for_timeout(400)
        p.evaluate("() => { window.__recOn = false; }")
        x = np.concatenate([np.array(q) for q in p.evaluate("() => window.__rec")] or [np.zeros(1)])
        return float(np.abs(x).max())
    up_muted, low = heard(72), heard(48)
    check("with the upper hand muted a note above the split is silent and one below sounds",
          up_muted < 1e-4 and low > 0.05, "peaks %.6f above, %.4f below" % (up_muted, low))
    p.locator("#muteHandB").click(); p.wait_for_timeout(400)
    up = heard(72)
    null("unmuted, the note above sounds, so the silence was the mute's", up > 0.05, "peak %.4f" % up)

    print("\n--- Alt-click: a hand alone ---")
    p.locator("#muteHandA").click(modifiers=["Alt"]); p.wait_for_timeout(200)
    solo = p.evaluate("() => handMuted.slice()")
    p.locator("#muteHandA").click(modifiers=["Alt"]); p.wait_for_timeout(200)
    both = p.evaluate("() => handMuted.slice()")
    check("Alt-click on the lower hand's mute hears it alone, and again both", solo == [False, True] and both == [False, False],
          "%s then %s" % (solo, both))

    print("\n--- a preset, a code, one hand: both sound again ---")
    def load(how):
        p.locator("#muteHandA").click(); p.wait_for_timeout(150)
        was = p.evaluate("() => handMuted.slice()")
        p.evaluate("() => { window.__calls = []; }")
        p.evaluate(how)
        p.wait_for_timeout(400)
        return was, p.evaluate("() => [handMuted.slice(), window.__calls.filter((c) => c[1] === 'handMute')]")
    code = p.evaluate("() => encodeSetup(snapshot())")
    was1, code_after = load("(c) => loadCode(" + repr(code) + ")")
    check("a code loaded unmutes both, and tells the instrument", code_after[0] == [False, False] and ["scopeControl", "handMute", "0"] in code_after[1],
          str(code_after))
    null("the lower hand was muted before the code", was1 == [True, False], str(was1))
    # A bank preset with two hands, picked by what it needs (CLAUDE.md: never by name), so its own hands
    # are on after the load and only the load itself can have unmuted.
    was2, preset_after = load("""() => { for (const [, entries] of PRESETS) for (const [name, setup] of entries)
      if (setup.layers === 'split') { applyPreset('b:' + name); return; } }""")
    hands_after = p.evaluate("() => layersOn()")
    check("and so does a preset, one with two hands of its own", was2 == [True, False] and preset_after[0] == [False, False] and hands_after,
          "%s then %s, two hands %s" % (was2, preset_after, hands_after))
    p.evaluate("() => showControl('shape')"); p.wait_for_timeout(200)
    p.locator("#midiPoly").click(); p.wait_for_timeout(100)
    if p.evaluate("() => !layersOn()"): p.locator("#midiTwoHands").click()
    p.wait_for_timeout(200)
    p.locator("#muteHandB").click(); p.wait_for_timeout(150)
    p.locator("#midiTwoHands").click(); p.wait_for_timeout(300)
    gone = p.evaluate("() => [layersOn(), handMuted.slice()]")
    check("one hand again unmutes both", gone == [False, [False, False]], str(gone))

    print("\n--- Retrigger ---")
    rows = {}
    for mode in ("Dyad", "Mono", "Poly"):
        p.locator("#midi" + mode).click(); p.wait_for_timeout(150)
        rows[mode] = p.evaluate("() => !el.midiRetrigRow.hidden && el.midiRetrig.offsetWidth > 0")
    check("its switch is shown in Dyad and Mono, not in Poly", rows == {"Dyad": True, "Mono": True, "Poly": False}, str(rows))
    p.locator("#midiMono").click(); p.wait_for_timeout(100)
    off = p.evaluate("() => snapshot().midiRetrig")
    p.evaluate("() => { window.__calls = []; }")
    p.locator("#midiRetrig").check(); p.wait_for_timeout(200)
    on = p.evaluate("() => [snapshot().midiRetrig, window.__calls.filter((c) => c[1] === 'midiRetrig')]")
    code_on = p.evaluate("() => encodeSetup(snapshot())")
    back = p.evaluate("(c) => { restore({}); const was = midi.retrig; restore(decodeSetup(c)); return [was, midi.retrig, el.midiRetrig.checked]; }", code_on)
    check("on, it is the setup's and the instrument is told", on[0] is True and on[1] == [["scopeControl", "midiRetrig", True]], str(on))
    check("a code carries it, and a setup without it is legato", back == [False, True, True], str(back))
    null("and it was off before the press", off is False, str(off))

    print("\n--- the upper hand's own response says when it acts ---")
    p.evaluate("() => showControl('shape')"); p.wait_for_timeout(100)
    p.locator("#midiPoly").click(); p.wait_for_timeout(100)
    if p.evaluate("() => !layersOn()"): p.locator("#midiTwoHands").click()
    p.wait_for_timeout(200)
    lines = p.evaluate("""() => {
      const say = (id) => { sayInfo(document.getElementById(id)); return el.infoText.textContent; };
      const out = {};
      if (!linked('picture')) setLink('picture', true);
      document.getElementById('editHandB').click();
      out.linked = say('pictureSwell');
      setLink('picture', false);
      out.upper = ['pictureResponds', 'pictureSwell', 'pictureFeel', 'pictureRise', 'pictureFall'].map(say);
      document.getElementById('editHandA').click();
      out.lower = say('pictureSwell');
      out.doc = CONTROL_WORDS.pictureSwell[1];
      setLink('picture', true);
      return out;
    }""")
    check("editing the upper hand's own, each of the five says it acts only while each hand draws its own figure, in X–Y",
          all("only while each hand draws its own figure, in X–Y" in l for l in lines["upper"]), lines["upper"][0])
    null("the lower hand's and a linked Picture's say the doc's line", lines["lower"] == lines["doc"] and lines["linked"] == lines["doc"],
         "%r / %r" % (lines["lower"][:40], lines["linked"][:40]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("a hand can be muted and nothing keeps it; Retrigger is the setup's; the upper hand's response says when it acts")
