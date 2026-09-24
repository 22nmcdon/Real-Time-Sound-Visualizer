"""The generator heard as a lane of a rack.

The tone source's voice, shared with the generator lane rather than copied: on
the rack's context, left channel only, through the lane's gain onto the rack's
mix. What is checked is what would go wrong:

- the switch not being offered, because the rack is not a tone source;
- the picture not being the worklet's samples while it sounds;
- both channels reaching the mix, when the lane that is drawn is the left one;
- a note changing the main thread's copy of the generator and not the one in
  the worklet, which is the one being heard and drawn;
- the lane being gated, when D10 makes it a drone;
- the mixer not reaching it;
- a rebuild of the rack dropping the sound, and a change of source keeping it.

The channel question is answered by energy at the right channel's own
frequency: with the left at 220 Hz and the right a fifth above at 330 Hz, the
left alone has next to nothing at 330 Hz and the pair has as much there as at
220. It was first answered by pitch, on the grounds that the pair repeats only
every 1/110 s - which is true of the waveform and invisible to the page's
estimator, which counts rising zero crossings and finds two per 110 Hz period.
It answered 220 for both, and a mutation sending both channels to the mix
survived.
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

HZ = lambda note: 440 * 2 ** ((note - 69) / 12)

# What reaches the rack's speakers, read off the input of its monitor chain.
# The rack is the only thing with a chain once the tone source has stopped, and
# that is asserted rather than assumed.
TAP = """() => {
  const chains = Array.from(monitorChains);
  if (chains.length !== 1) return { chains: chains.length };
  const ctx = chains[0].input.context;
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 8192;
  chains[0].input.connect(analyser);
  window.__tap = { analyser, rate: ctx.sampleRate };
  return { chains: 1 };
}"""

HEARD = """() => {
  const { analyser, rate } = window.__tap;
  const x = new Float32Array(analyser.fftSize);
  analyser.getFloatTimeDomainData(x);
  let peak = 0;
  for (let i = 0; i < x.length; i++) peak = Math.max(peak, Math.abs(x[i]));
  // Hann-windowed magnitude at one frequency.
  const at = (f) => {
    let re = 0, im = 0;
    for (let i = 0; i < x.length; i++) {
      const w = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (x.length - 1));
      re += x[i] * w * Math.cos(2 * Math.PI * f * i / rate);
      im -= x[i] * w * Math.sin(2 * Math.PI * f * i / rate);
    }
    return Math.hypot(re, im);
  };
  return { peak, hz: peak > 0.01 ? estimateFrequency(x, rate) : null,
           right: peak > 0.01 ? at(330) / at(220) : null };
}"""

DRAWN = """() => {
  const lane = genLane();
  const x = lane.read(8192);
  let peak = 0;
  for (let i = 0; i < x.length; i++) peak = Math.max(peak, Math.abs(x[i]));
  return { peak, hz: peak > 0.01 ? estimateFrequency(x, state.source.sampleRate) : null };
}"""


def near(hz, want, cents=15):
    import math
    return hz is not None and abs(1200 * math.log2(hz / want)) < cents


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    print("\n--- the switch is offered where the generator is ---")
    # The tone source sounding first, so that replacing it has something to
    # stop: two generators' loops at once is what `assertLfoDriver` exists
    # for, and the plan named this as the check to extend the day a lane got
    # a worklet of its own.
    p.evaluate("""async () => { window.__tone = state.source; state.genSound = true;
                                await applyGeneratorSound(); }""")
    p.wait_for_timeout(300)
    tone_was = p.evaluate("() => window.__tone.audible()")
    p.evaluate("() => { el.rackSynth.checked = true; return setRackSynth(true); }")
    p.wait_for_timeout(600)
    tone_after = p.evaluate("() => ({ audible: window.__tone.audible(), chains: monitorChains.size })")
    check("a sounding tone source is silent once a rack replaces it",
          tone_was is True and tone_after["audible"] is False, "%s then %s" % (tone_was, tone_after))
    silent = p.evaluate("""() => ({
      kind: state.source.kind, lane: !!genLane(), row: !el.genSoundRow.hidden,
      audible: genLane().audible(), monitored: genLane().monitored, driver: lfoDriver() })""")
    print("    %s" % silent)
    check("a rack with the generator in it offers Hear the generator",
          silent["kind"] == "rack" and silent["lane"] and silent["row"], str(silent))
    check("and it starts silent, with this thread driving the oscillators",
          silent["audible"] is False and silent["monitored"] is False
          and silent["driver"] == "fill", str(silent))

    print("\n--- switched on ---")
    # Through the checkbox, the way it is used.
    p.evaluate("() => { el.genSound.checked = true; el.genSound.dispatchEvent(new Event('change')); }")
    p.wait_for_timeout(700)
    on = p.evaluate("""() => ({ got: state.genSound, box: el.genSound.checked,
      audible: genLane().audible(), monitored: genLane().monitored, driver: lfoDriver(),
      blocks: genLane().blocks, fault: genLane().fault })""")
    print("    %s" % on)
    check("the lane says it is sounding, and the box agrees",
          on["got"] and on["box"] and on["audible"], str(on))
    check("the worklet drives the oscillators now",
          on["driver"] == "worklet", on["driver"])
    check("and the mixer counts it as a lane that can be heard",
          on["monitored"] is True, str(on["monitored"]))
    check("the picture is being written from what the worklet sent",
          on["blocks"] > 3, "%d blocks" % on["blocks"])

    producing = p.evaluate("""async () => {
      /* Off 220 Hz first. At 44.1 kHz a 220 Hz tone repeats exactly every
         2205 samples, and 350 ms is seven of those - a frozen ring and a moving
         one would read the same. The check below it found that trap once. */
      genSet('freq', 223.7);
      await new Promise((r) => setTimeout(r, 100));
      const was = state.running;
      state.running = false;                       // nothing calls tick now
      const before = genLane().read(2048).slice();
      await new Promise((r) => setTimeout(r, 350));
      const after = genLane().read(2048);
      let moved = 0;
      for (let i = 0; i < before.length; i++) moved = Math.max(moved, Math.abs(before[i] - after[i]));
      state.running = was;
      return moved;
    }""")
    check("with nothing on this thread asking, the lane's samples keep coming",
          producing > 0.01, "moved by %.3f" % producing)

    print("\n--- what reaches the speakers is the lane that is drawn ---")
    tap = p.evaluate(TAP)
    check("the rack is the only thing with a monitor chain", tap["chains"] == 1, str(tap))
    p.evaluate("""() => { genSet('freq', 220); genSet('interval', 7); genSet('octaves', 0);
                          genSet('just', true); genSet('shape', 'sine'); }""")
    p.wait_for_timeout(500)
    heard = p.evaluate(HEARD); drawn = p.evaluate(DRAWN)
    print("    left at 220 Hz, right a fifth above: heard %s, drawn %s" % (heard, drawn))
    check("it reaches the rack's speakers", heard["peak"] > 0.05, "peak %.3f" % heard["peak"])
    check("and what is heard is the left channel alone - nothing at the right's 330 Hz",
          heard["right"] is not None and heard["right"] < 0.02,
          "330 Hz at %s of 220 Hz" % (None if heard["right"] is None
                                      else "%.4f" % heard["right"]))
    check("which is the lane that is drawn", near(drawn["hz"], 220), str(drawn["hz"]))

    print("\n--- a note reaches the worklet, not only this thread ---")
    p.evaluate("() => setScreenKeys(true)")
    p.wait_for_timeout(300)
    idle = p.evaluate(HEARD)
    p.evaluate("() => midiNoteOn(52, 100)")
    p.wait_for_timeout(500)
    played = {"heard": p.evaluate(HEARD), "drawn": p.evaluate(DRAWN),
              "core": p.evaluate("() => genSettings().freq")}
    p.evaluate("() => midiNoteOff(52)")
    p.wait_for_timeout(400)
    released = p.evaluate(HEARD)
    p.evaluate("() => setScreenKeys(false)")
    print("    keys open, nothing held: %s; E3: %s; released: %s" % (idle, played, released))
    check("with the keys open and nothing held, the lane still sounds - a drone, D10",
          idle["peak"] > 0.05, "peak %.3f" % idle["peak"])
    check("E3 is what is heard, not only what this thread's copy says",
          near(played["heard"]["hz"], HZ(52)) and near(played["drawn"]["hz"], HZ(52)),
          "heard %s, drawn %s, core %.1f" % (played["heard"]["hz"], played["drawn"]["hz"],
                                            played["core"]))
    check("and letting go leaves it sounding at the note it was given",
          released["peak"] > 0.05 and near(released["hz"], HZ(52)), str(released))

    print("\n--- the mixer reaches it ---")
    p.evaluate("() => { genLane().mute = true; state.source.remix(); }")
    p.wait_for_timeout(300)
    muted = p.evaluate(HEARD)
    p.evaluate("() => { genLane().mute = false; state.source.remix(); }")
    p.wait_for_timeout(300)
    unmuted = p.evaluate(HEARD)
    check("muting the lane silences it", muted["peak"] < 1e-3, "peak %.4f" % muted["peak"])
    check("and unmuting brings it back", unmuted["peak"] > 0.05, "peak %.3f" % unmuted["peak"])

    print("\n--- a rebuild keeps it, a change of source does not ---")
    rebuilt = p.evaluate("""async () => {
      const old = genLane();
      await toRack(rackFiles || []);
      await new Promise((r) => setTimeout(r, 700));
      const lane = genLane();
      return { fresh: lane !== old, oldQuiet: old.audible() === false,
               audible: lane.audible(), got: state.genSound, box: el.genSound.checked,
               driver: lfoDriver(), freq: lane.core.tone.freq, panel: Number(el.freq.value),
               shape: lane.core.tone.shape, panelShape: el.shape.value };
    }""")
    print("    %s" % rebuilt)
    check("rebuilding the rack around a sounding lane leaves the new lane sounding",
          rebuilt["fresh"] and rebuilt["audible"] and rebuilt["got"] and rebuilt["box"]
          and rebuilt["driver"] == "worklet", str(rebuilt))
    check("and the old lane's voice was stopped, not left running in a closed rack",
          rebuilt["oldQuiet"], str(rebuilt))
    # The note moved the panel's frequency slider to 165, so a new lane built
    # from the core's defaults would be at 220 and one built from the panel is
    # at 165. The first version of this suite found it: after a rebuild the
    # lane was back at 220 while the panel said E3.
    check("the new lane is built from what the panel says, not the core's defaults",
          abs(rebuilt["freq"] - rebuilt["panel"]) < 1e-9 and abs(rebuilt["freq"] - 220) > 1
          and rebuilt["shape"] == rebuilt["panelShape"], str(rebuilt))

    print("\n--- switched off ---")
    off = p.evaluate("""async () => {
      el.genSound.checked = false; el.genSound.dispatchEvent(new Event('change'));
      await new Promise((r) => setTimeout(r, 300));
      const lane = genLane();
      /* A pitch that cannot line up with the wait. The first version of this
         read a 220 Hz tone 300 ms apart: at 44.1 kHz that tone repeats exactly
         every 2205 samples, 300 ms is six of those, and the two windows were
         identical by construction - "frozen" on a ring that was moving. Three
         waits, too, so no single one can land on a repeat. */
      lane.set('freq', 223.7);
      await new Promise((r) => setTimeout(r, 100));
      let moved = 0;
      for (const wait of [170, 230, 290]) {
        const before = lane.read(2048).slice();
        await new Promise((r) => setTimeout(r, wait));
        const after = lane.read(2048);
        for (let i = 0; i < before.length; i++) moved = Math.max(moved, Math.abs(before[i] - after[i]));
      }
      return { audible: lane.audible(), monitored: lane.monitored, driver: lfoDriver(),
               got: state.genSound, moved };
    }""")
    print("    %s" % off)
    check("off, the lane is silent and this thread has the oscillators back",
          off["audible"] is False and off["monitored"] is False
          and off["driver"] == "fill" and off["got"] is False, str(off))
    check("and it is still drawn, from this thread's loop again",
          off["moved"] > 0.01, "moved by %.3f" % off["moved"])

    # And from a sounding lane to the tone source: a different source, so the
    # speakers stay off until asked.
    p.evaluate("() => { el.genSound.checked = true; el.genSound.dispatchEvent(new Event('change')); }")
    p.wait_for_timeout(500)
    toned = p.evaluate("""() => { toTone(); return { kind: state.source.kind,
      got: state.genSound, audible: state.source.audible(), chains: monitorChains.size }; }""")
    check("choosing Tone does not carry the sound across",
          toned["kind"] == "tone" and toned["got"] is False and toned["audible"] is False,
          str(toned))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the generator lane is heard as it is drawn")
