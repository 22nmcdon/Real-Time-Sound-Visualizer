"""The effects on a live input (S1): the plane, the delay and the chorus on a
microphone or a line input, drawn and heard.

What would go wrong, and what is checked for it:

- the input changed with nothing on: no effects node exists until an effect
  is wanted, and none after the last is switched off;
- an effect that reaches the picture and not the speakers, or the other way
  round: the monitor chain is tapped, and what the speakers are handed is
  mirrored exactly as what is drawn is;
- the wrong arithmetic: it is the generator's own code, so the mirror on a
  microphone folds every angle into the first quadrant as the generator's does
  (the kaleidoscope's wedge, until it was cut on 7 Nov), and
  a delay on a live input puts each repeat at the delay time to within a few
  samples - measured from the input's own burst, not from a guess at when it
  started (a file's, until P5 cut file playback);
- a routing that does not reach it: an oscillator on the twist swirls a
  mono input's diagonal off itself, and the mono input shows as two lanes
  while it does, because what the effect made of it is a pair;
- a band split's lanes twisted into each other: the split gets no insert,
  and the sections say what the effects are acting on. (A rack's stems were
  the case until P5 cut the rack.)

The fixture is two oscillators behind getUserMedia - 220 Hz on the left and
330 Hz on the right, never a circle: a 3:2 pair has a length and a direction
that change all the way round, which a rotation-like effect cannot leave
alone.
"""
# On the site's default since stage 5, step 3, batch 5 (13 Nov). It opened
# ?brain=js until then, where the effects on a microphone were the page's own
# insert: a worklet the page started, told every frame and let go of. The
# instrument has no such insert; drawing the input, it puts it through its
# own effects - the plane and the time effects - and what comes out is both
# drawn and heard (core/tests/pieces/render.py shows it). So the arithmetic
# rows - the mirror drawn and heard, the fold into the quadrant and over it,
# the twist swirled by an oscillator, the delay's repeat to two samples - are
# core/tests/pieces/livefx.py's, render_cpp drawing an input through the
# instrument. The rows about the page's insert's life - no node until an
# effect is wanted, a change told to the running worklet, the node let go of
# with the last effect and with the source, the routing told every frame, the
# lane rows refitted round it - went with that insert. What is left is the
# face: the site's microphone reaching the instrument's effects, and what the
# section says each source's effects act on.
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


SETUP = """() => {
  window.__wait = (ms) => new Promise((r) => setTimeout(r, ms));
  // A stereo input: two oscillators, 3:2, into a stream the page is handed
  // as its microphone. Mono when asked: one oscillator in both channels.
  window.__mic = async (mono) => {
    const ctx = new AudioContext();
    const merge = ctx.createChannelMerger(2), dest = ctx.createMediaStreamDestination();
    const a = ctx.createOscillator(), c = ctx.createOscillator();
    a.frequency.value = 220; c.frequency.value = 330;
    const g = ctx.createGain(); g.gain.value = 0.8;
    a.connect(merge, 0, 0); (mono ? a : c).connect(merge, 0, 1);
    merge.connect(g); g.connect(dest); a.start(); c.start();
    // A mono microphone says so in its settings, which is what the page reads;
    // the stub's stream is two channels whatever it carries, so it is told.
    if (mono) {
      const track = dest.stream.getAudioTracks()[0], own = track.getSettings.bind(track);
      track.getSettings = () => Object.assign({}, own(), { channelCount: 1 });
    }
    navigator.mediaDevices.getUserMedia = () => Promise.resolve(dest.stream);
    /* The page keeps a device's stream and hands it to the next request for
       the same device - which here would be the previous fixture's. So the
       old microphone is left first, by way of the tone, and its release
       empties the cache for the new one. Clearing the cache by hand instead
       left the old source to release the NEW stream, filed under the same
       key, and stop its tracks: a silent second microphone, and a twist
       check that read nought for a reason of its own. */
    if (state.source && state.source.kind === 'mic') { el.srcTone.click(); await __wait(300); }
    el.srcMic.click(); await __wait(1200);
  };
  window.__win = (n) => state.source.getLatestWindow(n || 4410);
  window.__set = (id, v, kind) => { el[id].value = String(v); el[id].dispatchEvent(new Event(kind)); };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate(SETUP)

    print("\n--- the site's microphone, through the instrument's effects ---")
    # On ?brain=js the first rows read the page's insert (`fx.active`); on
    # the default the source is the instrument's (`host`), and what is drawn
    # is its lanes. The arithmetic itself is pieces/livefx.py's; this is that
    # the site's Mic and the plane's menu reach it at all.
    site = p.evaluate("""async () => {
      await __mic(false); await __wait(600);
      let w = __win();
      const out = { kind: state.source.kind, low0: [Math.min(...w[0]), Math.min(...w[1])], where: el.planeWhere.textContent };
      __set('planeMirror', 3, 'change'); await __wait(1500);
      w = __win();
      out.low3 = [Math.min(...w[0]), Math.min(...w[1])];
      __set('planeMirror', 0, 'change'); await __wait(300);
      return out;
    }""")
    print("    %s" % site)
    check("the site's microphone is drawn by the instrument, and mirrored there it has no negative half on either axis",
          site["kind"] == "host" and site["low3"][0] > -0.02 and site["low3"][1] > -0.02, str(site))
    check("null: as it is, it has both", site["low0"][0] < -0.7 and site["low0"][1] < -0.7, str(site["low0"]))
    # The words are the face's for a microphone that is not a monitored line
    # input; on ?brain=js the row set the page's own line-input monitoring
    # (`liveKind`, `setMonitor`) and read "drawn and heard".
    check("and the section says it is on your input", site["where"].startswith("On your input, drawn"), site["where"])

    print("\n--- where it does not go ---")
    split = p.evaluate("""async () => {
      __set('delayMix', 60, 'input'); await __wait(300);
      el.micBands.click(); await __wait(600);
      const out = { lanes: state.source.channels, where: el.planeWhere.textContent };
      __set('delayMix', 0, 'input');
      el.micWhole.click(); await __wait(300);
      el.srcTone.click(); await __wait(400);
      out.tone = el.planeWhere.textContent;
      return out;
    }""")
    print("    %s" % split)
    # Its insert's part ('fx' in the page's source, and the insert let go of) went with the insert.
    check("a band split's sections say why it gets no effects", split["lanes"] == 4 and "not one stereo pair" in split["where"], str(split))
    check("and on the tone the effects are the generator's", split["tone"] == "On the generator.", split["tone"])
    check("null: the two say different things", split["tone"] != split["where"])

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the site's microphone reaches the instrument's effects; their arithmetic is pieces/livefx.py's")
