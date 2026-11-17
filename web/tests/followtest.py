"""Follow and Autoset reaching the instrument (the reach audit, 17 Nov).

What would go wrong, and what is checked for it: the page's own tools moving
the page's timebase, full scales and trigger level and telling the
instrument nothing, so the screen drew one picture and Scan, which reads the
instrument's, read another until the next whole setup was sent. What is read
is what a hand on each control sends - scopeSlider with its id and value,
as the plugin's editor and the site's worklet both take it - recorded as the
page sends it, and each handed to a second instrument made here, which must
take it (Instrument's panel answers whether it knows the slider). The
instrument's published state is no reading: it carries what the host
changed, not the page's sliders, and stays where it was either way.

- Follow (... and the timebase), with a note played: the page's timebase
  moves to about four periods of it, and the instrument is sent it;
- Autoset, pressed with a chord held: the timebase, each drawn lane's full
  scale and the trigger level, each sent;
- in a split drawing two figures, four lanes: the page offers a full scale
  and an offset only for a lane the instrument takes one for (the first
  two), where it offered all four and the instrument refused the third and
  fourth's, so the screen and Scan parted. The null is the instrument
  refusing a third lane's, which is what makes "takes every one" a reading.

And undo as a hand would leave it: Autoset is a press, and one step; Follow
is a note, which is playing rather than editing (the owner's rule of 15
Nov, asPlayed), so no step and the header stays on its preset.

The null for each: the page's controls read before the tool, which must
differ after it, so a message carrying "the page's value" is not the value
the instrument had already.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + str(detail)) if detail else ""))
    if not ok: fails.append(name)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    ev = p.evaluate
    p.wait_for_function("() => hostSync.on && state.source && state.source.kind === 'host'", timeout=15000)
    CONTROLS = ["timebase", "level", "ch1Scale", "ch2Scale"]
    ev("""() => { window.__sent = [];
                  const real = scopeHost.call.bind(scopeHost);
                  scopeHost.call = (name, ...params) => { window.__sent.push([name, ...params]); return real(name, ...params); };
                  window.__other = makeWasmBrain(wasmModule(), 48000, 128, encodeSetup(snapshot())); }""")
    def page():
        return ev("(ids) => Object.fromEntries(ids.map((id) => [id, el[id].value]))", CONTROLS)
    def sent_since(mark):
        """The last value sent for each control since the mark, and whether a second instrument takes each."""
        return ev("""([mark, ids]) => { const out = {};
          for (const [name, id, value] of window.__sent.slice(mark)) if (name === 'scopeSlider' && ids.includes(id)) out[id] = String(value);
          const taken = {}; for (const id of Object.keys(out)) taken[id] = window.__other.slider(id, out[id]);
          return { sent: out, taken }; }""", [mark, CONTROLS])
    mark = lambda: ev("() => window.__sent.length")
    steps = lambda: ev("() => undoHistory.undo.length")

    print("\n--- Follow ---")
    p.locator("#helpClose").is_visible()
    ev("() => { el.midiFollow.checked = true; el.midiFollow.dispatchEvent(new Event('change', { bubbles: true })); }")
    p.wait_for_timeout(300)
    # Follow switched on is the sound loaded: the case is whether a note then edits it.
    ev("() => { loadedSetup = { snap: snapshot(), value: el.preset.value }; markPresetDirty(); undoHistory.undo = []; undoHistory.redo = []; undoRebase(); paintUndo(); }")
    check("the sound starts unedited, with no steps (the case under test)", ev("() => !presetEdited") and steps() == 0)
    before, at = page(), mark()
    ev("() => setScreenKeys(true)")
    p.keyboard.down("a"); p.wait_for_timeout(300)        # C3, a low note: a long timebase
    mine, got = page(), sent_since(at)
    p.keyboard.up("a"); p.wait_for_timeout(200)
    check("null: the note moved the page's timebase", mine["timebase"] != before["timebase"],
          "%s -> %s" % (before["timebase"], mine["timebase"]))
    check("Follow sends the instrument its timebase, as a hand on it would", got["sent"].get("timebase") == mine["timebase"],
          "page %s, sent %s" % (mine["timebase"], got["sent"]))
    check("and the instrument takes it", got["taken"].get("timebase") is True, got["taken"])
    p.wait_for_timeout(800)
    check("and a note is no undo step, nor an edit of the preset", steps() == 0 and ev("() => !presetEdited"),
          "%d steps, edited %s" % (steps(), ev("() => presetEdited")))
    ev("() => { el.midiFollow.checked = false; el.midiFollow.dispatchEvent(new Event('change', { bubbles: true })); }")

    print("\n--- Autoset ---")
    # A setting Autoset will move: the slowest timebase, the trigger at the top, the scales wide open.
    ev("""() => { el.timebase.value = '0'; el.timebase.dispatchEvent(new Event('input', { bubbles: true }));
                  el.level.value = '900'; el.level.dispatchEvent(new Event('input', { bubbles: true }));
                  for (const id of ['ch1Scale', 'ch2Scale']) { el[id].value = el[id].max; el[id].dispatchEvent(new Event('input', { bubbles: true })); } }""")
    p.wait_for_timeout(300)
    p.keyboard.down("a"); p.keyboard.down("g"); p.wait_for_timeout(600)
    ev("() => { undoHistory.undo = []; undoHistory.redo = []; undoRebase(); paintUndo(); }")
    before, at = page(), mark()
    p.locator("#autoset").click() if p.locator("#autoset").is_visible() else (ev("() => setScreenKeys(false)"), p.keyboard.press("a"))
    p.wait_for_timeout(100)
    mine, got = page(), sent_since(at)
    moved = [c for c in CONTROLS if mine[c] != before[c]]
    check("null: Autoset moved the page's controls, all four", len(moved) == 4, "moved %s; page %s, before %s" % (moved, mine, before))
    check("and sends the instrument each, as a hand on it would", all(got["sent"].get(c) == mine[c] for c in CONTROLS),
          "page %s, sent %s" % (mine, got["sent"]))
    check("and the instrument takes each", all(got["taken"].get(c) is True for c in CONTROLS), got["taken"])
    p.wait_for_timeout(900)
    check("Autoset, a press, is one undo step", steps() == 1, "%d steps" % steps())
    ev("() => setScreenKeys(true)")
    p.keyboard.up("a"); p.keyboard.up("g")
    ev("() => setScreenKeys(false)")

    print("\n--- the lanes past the second ---")
    # Two hands, each drawing its own figure: four lanes on the screen.
    ev("""() => { hostQuietly(() => restore(Object.assign(snapshot(), { layers: 'split', layerPair: 'each' }))); hostSendSetup(); }""")
    p.wait_for_timeout(800)
    lanes = ev("() => laneCount()")
    offered = ev("""() => Array.from(document.querySelectorAll('#laneRows input[type=range]')).map((i) => i.id)""")
    taken = ev("(ids) => Object.fromEntries(ids.map((id) => [id, window.__other.slider(id, el[id].value)]))", offered)
    check("a split drawing two figures has four lanes (the case under test)", lanes == 4, lanes)
    check("every full scale and offset the page offers is one the instrument takes", offered and all(taken.values()), taken)
    check("and the third and fourth lanes say they are drawn as the instrument draws them",
          ev("() => document.querySelectorAll('#laneRows [data-lane-note]').length") == lanes - 2)
    check("null: the instrument refuses a third lane's full scale, so the check above can fail",
          ev("() => window.__other.slider('ch3Scale', '4')") is False and ev("() => window.__other.slider('ch4Offset', '10')") is False)
    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\nall passed" if not fails else "\n%d FAILED:\n  %s" % (len(fails), "\n  ".join(fails)))
sys.exit(1 if fails else 0)
