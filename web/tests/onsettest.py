"""Onset (J1) and the events it fires (S3): what was left of drawingtest.py
when G2 took the drawings, whose Swing again and Kick were the only things an
event could strike.

The event machinery stays for the next thing struck (`fireEvents`, the rule
that an event reaches only an event), and Onset with the parked hearing
family, so both are held here against stand-in destinations this suite
registers itself - the page has none of its own until something struck comes
back. Written against the way each would fail:

- an event that reaches a value, or a value an event: the matrix refuses
  both, the editor never offers them, a drop does nothing;
- an onset that fires on a held note, on a release, on the click of a note
  cut off, more than once an attack, or faster than the gap allows;
- a routing that fires when it is made, or never fires at all.

What drawingtest.py also held went with the drawings: the pendulums' energy
in, and a solid's kick and its friction.
"""
# On the default page since stage 5, step 3, batch 4 (13 Nov), and only the
# face's rows: the registry's rule that an event reaches only an event, which
# the editor and a drop obey. Until then on ?brain=js, where it also counted
# onsets from a microphone faked out of an oscillator and the page's own
# onsetStep driven in a busy loop, and fired stand-in destinations through
# the page's fireEvents. The instrument hears and fires on its own (the
# hearing on the audio thread since 5t, its matrix's fireEvents), so those
# rows are core/tests/pieces/onset.py's, on the core's hearing and matrix:
# the onset counts, the swell and the gap, the firing on a new count, and the
# onset that hears the generator refused.
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

STUB = """
  window.__wait = (ms) => new Promise((r) => setTimeout(r, ms));
  window.__mic = async () => {
    const ctx = new AudioContext();
    const dest = ctx.createMediaStreamDestination(), a = ctx.createOscillator(), g = ctx.createGain();
    a.frequency.value = 330; g.gain.value = 0; a.connect(g); g.connect(dest); a.start();
    window.__osc = { ctx, g };
    navigator.mediaDevices.getUserMedia = () => Promise.resolve(dest.stream);
    el.srcMic.click(); await __wait(1200);
  };
"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.add_init_script(STUB)
    # The picture stage out (?picture=0): this suite measures something else,
    # and the stage, on in everything played, is stagetest.py's and looptest.py's.
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    # The page has no event destination of its own since G2 (Swing again and
    # Kick were the two), so the suite registers two stand-ins, struck into a
    # log: `test.once` counts its strikes and `test.depth` keeps each depth.
    # They are the registry's own entries, read by the page's own rules.
    p.evaluate("""() => {
      window.__struck = { once: 0, depth: [] };
      registerDest({ id: 'test.once', kind: 'event', label: 'Once', fire: () => { __struck.once++; } });
      registerDest({ id: 'test.depth', kind: 'event', label: 'Depth', fire: (amount) => { __struck.depth.push(amount); } });
    }""")
    # The null: with nothing struck registered at all, an onset reaches
    # nothing - so the check below reads the stand-ins, not something left
    # on the page.
    bare = p.evaluate("""() => [...MOD_DESTS.values()].filter((d) => d.kind === 'event' && !d.id.startsWith('test.'))
                                 .map((d) => d.id)""")
    check("the page itself has no event destination left (G2 took Swing again and Kick)", bare == [], str(bare))

    print("\n--- events reach only what is struck (S3) ---")
    # The Mic pressed, with a stand-in stream: on the site it keeps the
    # instrument and puts the input through it (hostToMic), and the onset
    # hears the input, not the generator - without it the onset hears the
    # generator and is refused everything, so the rows below would read
    # empty lists (batch 4: they did, and "makes no routing" passed on them).
    p.evaluate("() => __mic()")
    check("the Mic keeps the instrument, and the onset hears the input rather than the generator",
          p.evaluate("() => state.source.kind === 'host' && !hearsGenerator()"),
          str(p.evaluate("() => [state.source.kind, hearsGenerator()]")))
    s3 = p.evaluate("""() => {
      const offered = (id) => [...MOD_SOURCES.values()].filter((s) => routingAllowed(s, MOD_DESTS.get(id))).map((s) => s.id);
      const reaches = (id) => [...MOD_DESTS.values()].filter((d) => routingAllowed(MOD_SOURCES.get(id), d)).map((d) => d.id);
      state.modRoutings = []; addRouting('hear.onset', 'view.rotate'); addRouting('hear.flux', 'test.once');
      const dropped = state.modRoutings.length;
      addRouting('hear.onset', 'test.once');
      const kept = state.modRoutings.length;
      state.modRoutings = []; touchRoutings();
      return { kept, once: offered('test.once'), depth: offered('test.depth'), onset: reaches('hear.onset').sort(),
               rotate: offered('view.rotate').includes('hear.onset'), dropped };
    }""")
    print("    %s" % s3)
    # The events, written out: the onset, and the two stand-ins it strikes.
    # The threshold (K1) was an event too, and Pluck a thing struck, until P5
    # cut both; Swing again and Kick were struck until G2.
    check("an onset reaches only what is struck, and only events reach that",
          s3["once"] == ["hear.onset"] and s3["depth"] == ["hear.onset"]
          and s3["onset"] == ["test.depth", "test.once"] and not s3["rotate"], str(s3))
    check("and dropping an event on a value, or a value on an event, makes no routing", s3["dropped"] == 0,
          str(s3["dropped"]))
    # Its null, since batch 4: without the Mic the registry offered the onset
    # nothing and the count was nought for that reason.
    check("null: and an event on an event makes one", s3["kept"] == 1, str(s3["kept"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
