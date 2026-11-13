"""The arpeggiator (K5).

Against the way it would fail:

- the wrong order: C E G held, up is C E G C E G, down G E C, up-down C E G E
  and round without either end twice, as played in the order the keys went
  down, two octaves C E G and the same an octave up, random only ever what is
  held;
- the generator given the whole chord instead of the step, or the step not
  struck: each step closes the gate and opens it again;
- the hands forgotten: what the notes sources read is still the whole chord;
- the tempo: 120 BPM in quavers is a step every 250 ms, five in a second from
  the first key, and the steps do not drift;
- the dyad not drawing the chord's intervals: each step pairs the lowest held
  note with the arpeggio's, so C E G is unison, a major third and a fifth;
- a note left hanging: letting go stops it and ends what went out as MIDI;
- switching it off with keys down leaving the generator on one note;
- switching it off once it has stepped leaving the keys on the last step's
  envelope (11 Nov): what is held is struck, the gate closed and opened, and
  inside the gather, before a step, it is not; and a setup
  without it loaded over a key held through one with it sounds the key at
  the new setup's level.

Since stage 5's batch 4 all but the last two of these are
core/tests/pieces/arp.py's, on the core; this suite keeps the setup code and
the level, on the site's instrument. Its null is a key struck under a lower sustain and
  held into the same setup, which keeps the lower level.
"""
# The level a held key reaches under setups loaded over it, on a brain: the
# peak of the last quarter second of the picture, a setup at a time, with
# time between for the arpeggiator to step, which on the site's instrument
# it does on the audio's clock.
LEVEL = """async (steps) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const load = (over) => { const s = Object.assign({}, BASE_SETUP, over); hostQuietly(() => restore(s)); hostSendSetup(); };
  const peak = () => { const n = Math.round(state.source.sampleRate / 4); let most = 0;
    for (const lane of state.source.getLatestWindow(n).slice(0, 2)) for (const v of lane) most = Math.max(most, Math.abs(v));
    return most; };
  const out = [];
  for (const [what, arg] of steps) {
    if (what === 'load') load(arg);
    else if (what === 'on') midiNoteOn(arg, 127);
    else if (what === 'off') midiNoteOff(arg);
    else if (what === 'wait') await wait(arg);
    else if (what === 'read') out.push(peak());
  }
  midiPanic();
  return out;
}"""
PLAIN = {"midiMode": "dyad", "atk": 1, "dec": 200, "sus": 70, "rel": 50}
ARP = {"midiMode": "dyad", "arpMode": "up", "arpRate": "1/16", "arpOctaves": 2, "atk": 1, "dec": 200, "sus": 30, "rel": 50}
LOW = dict(PLAIN, sus=30)

# On the default page since stage 5, step 3, batch 4 (13 Nov). Until then
# on ?brain=js, where it drove the page's own arpTick at synthetic times,
# wrapped its src.gate and read genSettings(), midi.notes and a stubbed port.
# On the default site the page's arpeggio still steps beside the
# instrument's (the inventory's arpTick.step) and the face's notes follow
# it, so those rows would have passed on the page's arpeggio: the order, the
# gather, each step struck, the tempo, the dyad's intervals, the MIDI out,
# letting go and switching off are core/tests/pieces/arp.py's now, on the
# core keyboard at the same synthetic times and on the instrument's audio
# clock. What stays here is the face's - the setup code - and what a player
# hears through a setup loaded over a held key, on the site's instrument.
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    print("\n--- what a setup carries ---")
    # The menus as the panel writes them, read off the setup the face sends.
    code = p.evaluate("""() => {
      const was = snapshot(), before = [was.arpMode, was.arpRate, was.arpOctaves];
      el.arpMode.value = 'updown'; el.arpRate.value = '1/16'; el.arpOctaves.value = '2';
      el.arpMode.dispatchEvent(new Event('change')); el.arpRate.dispatchEvent(new Event('change'));
      el.arpOctaves.dispatchEvent(new Event('change'));
      const s = snapshot(), out = [s.arpMode, s.arpRate, s.arpOctaves];
      el.arpMode.value = 'off'; el.arpMode.dispatchEvent(new Event('change'));
      return out.concat([before]);
    }""")
    check("and a setup code carries the mode, the step and the octaves", code[:3] == ["updown", "1/16", 2], str(code))
    check("null: the code before the menus moved is not that", code[3] != ["updown", "1/16", 2], str(code[3]))

    # The sound: a key held under a plain setup, then through an arpeggiated
    # one long enough for it to step, then the plain one again. A leg on
    # ?brain=js ran beside this one until batch 4; it went, the instrument's
    # being the claim.
    for query, brain in (("", "the site's instrument"),):
        q = b.new_page(viewport={"width": 1400, "height": 900})
        q.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
        q.goto(f"file://{ART}/scope.html?picture=0" + query); q.wait_for_timeout(1500)
        if q.locator("#helpClose").is_visible(): q.locator("#helpClose").click()
        through = q.evaluate(LEVEL, [["load", PLAIN], ["on", 57], ["wait", 700], ["read", None],
                                     ["load", ARP], ["wait", 800], ["load", PLAIN], ["wait", 600], ["read", None]])
        low = q.evaluate(LEVEL, [["load", PLAIN], ["on", 57], ["wait", 700], ["read", None], ["off", 57],
                                 ["load", LOW], ["wait", 300], ["on", 57], ["wait", 600], ["load", PLAIN], ["wait", 600],
                                 ["read", None]])
        q.close()
        ref, after = through
        check("on %s, a key held through an arpeggiated setup and into a plain one sounds at the plain one's level" % brain,
              ref > 0.1 and abs(after / ref - 1) < 0.03, "%.4f against %.4f struck under it" % (after, ref))
        check("null: on %s a key struck under a sustain of 0.3 and held into the same setup keeps its lower level" % brain,
              low[1] / low[0] < 0.6, "%.4f against %.4f" % (low[1], low[0]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
