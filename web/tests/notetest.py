"""A note's first milliseconds, where a held route catches up with it (12 Nov).

The owner, on the site, on the Bass under the tine piano: "when I play a note
it clips or something at the start of every sound". Measured, it was not a
regression and not the audio thread: the worklet kept every block in time,
and the same notes clicked on the commit before and on the one that made the
preset. It was the routes. A route from something that is not an oscillator
- the Envelope, the Key - is a value the matrix works out once a block, at
the block's top, and the generator held it flat across the block. A note
struck in a block plays that block with the routes as they stood before it,
with the Envelope and the Key at nought, and at the next block's top the
preset's two routes put the FM depth up by about three at once. On phase
modulation a step of the index is a step of the wave: the bass's went from
+0.42 to -0.35 in one sample, on every note, 0.78 against the 0.012 a
sample the note steps by when it is steady. The tine's was smaller, being
already at a depth of eight.

Now each slot's held routes are walked to where a block puts them in a line
over that block (the generator's `heldAim` and `heldRamp`, page and core). So
this suite plays notes on the instrument the site plays - compiled from the
module the page carries, opened on the setup the page made, as wheeltest.py
does - and holds each note's largest step from one sample to the next in its
first 20 ms to twice the largest the same note makes over its steady second
half second:

- the bass hand of the preset as the owner played it, its fields written out
  here rather than taken from the bank, which is meant to change by ear;
- its upper hand, the tine;
- and the plain sine with Play's Velocity on FM, a player's two clicks from
  the base, which routes the Key onto the depth alone: every note it strikes
  clicked the same way.

Each has its null, the same notes with the walk at nought (the generator's
`heldRamp`), which is the step at the block's top exactly as it was: it must
break the bound, or the bound proves nothing. The tine's attack is bright on
purpose, its bark: its first 20 ms step by more than three times its steady
note's with the walk or without it, so a bound on the step cannot tell the
two apart. What the click added there was a corner, a bend in the wave from
one sample to the next (the second difference), 11 times the steady note's
against three with the walk; the tine is held to five times on that, and its
null breaks it.
"""
import json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

# The Bass under the tine piano as the owner played it on 12 Nov (the bank's
# entry then): a split at G3, a sine bass below, the tine piano above, and the
# tine's two routes onto the FM depth, which reach both hands.
BASS_UNDER_TINE = {
    "shape": "sine", "freq": 110, "timebase": 6, "midiMode": "poly", "layers": "split", "splitAt": 55,
    "layerPair": "each", "atk": 2, "dec": 500, "sus": 70, "rel": 150, "bShape": "sine", "bRatio": 1, "bFm": 8,
    "bVcf": 1, "bVcfCut": 700, "bAtk": 1, "bDec": 1000, "bSus": 25, "bRel": 500,
    "mod": "env.note>gen.fm@0.400;midi.key>gen.fm@0.300", "display": "xy", "persistence": "0.3",
    "oscScan": 20, "bScan": 45, "scanStrike": 100, "pictureAmount": 0, "polyRound": True,
}

# The setup the page makes of it, loaded as a pasted code is.
LOAD = """(fields) => {
  loadCode(btoa(JSON.stringify(Object.assign({ v: SETUP_VERSION }, fields))).replace(/=+$/, ''));
  return encodeSetup(snapshot());
}"""
# The base, with Play's Velocity menu on FM, as a player sets it.
VELOCITY_FM = """() => {
  applyPreset('n:' + BASE_NAME);
  el.midiVelocityTo.value = 'fm';
  el.midiVelocityTo.dispatchEvent(new Event('change'));
  return { code: encodeSetup(snapshot()), fm: velocityFm() };
}"""

# A note on a fresh instrument, from silence: a block's worth of silence first,
# then the note at a block's top, as the worklet hands a page's note over, and
# a second of it. Back: the largest step in the first 20 ms, and over the
# second half second, on either channel.
PLAY = """({ code, note, ramp }) => {
  const brain = makeWasmBrain(wasmModule(), 48000, 128, code);
  if (ramp !== null) brain.control("heldRamp", String(ramp));
  const L = new Float32Array(128), R = new Float32Array(128), pics = [0, 1, 2, 3, 4, 5].map(() => new Float32Array(128));
  for (let k = 0; k < 40; k++) brain.block(128, L, R, pics, null);
  brain.midi([0x90, note, 100]);
  const outL = new Float32Array(375 * 128), outR = new Float32Array(375 * 128);
  for (let k = 0; k < 375; k++) {
    brain.block(128, L, R, pics, null);
    outL.set(L, k * 128); outR.set(R, k * 128);
  }
  // The step (first difference) and the bend (second) from one sample to the next.
  const d1 = (x, i) => x[i] - x[i - 1], d2 = (x, i) => x[i] - 2 * x[i - 1] + x[i - 2];
  const most = (d, from, to) => {
    let m = 0, at = 0;
    for (let i = Math.max(2, from); i < to; i++) {
      const v = Math.max(Math.abs(d(outL, i)), Math.abs(d(outR, i)));
      if (v > m) { m = v; at = i; }
    }
    return [m, at];
  };
  let peak = 0; for (let i = 24000; i < 48000; i++) peak = Math.max(peak, Math.abs(outL[i]));
  const [onset, at] = most(d1, 2, 960), [steady] = most(d1, 24000, 48000);
  const [bend, bendAt] = most(d2, 2, 960), [steadyBend] = most(d2, 24000, 48000);
  return { onset, at, steady, bend, bendAt, steadyBend, peak };
}"""

# The same note with the walk and with another (nought, the step as it was, by
# default): how far apart the left channel is at each block's last sample, over
# the first forty blocks, and at each block's middle.
ENDS = """({ code, note, other }) => {
  const go = (ramp) => {
    const brain = makeWasmBrain(wasmModule(), 48000, 128, code);
    if (ramp !== null) brain.control("heldRamp", String(ramp));
    const L = new Float32Array(128), R = new Float32Array(128), pics = [0, 1, 2, 3, 4, 5].map(() => new Float32Array(128));
    for (let k = 0; k < 40; k++) brain.block(128, L, R, pics, null);
    brain.midi([0x90, note, 100]);
    const out = new Float32Array(40 * 128);
    for (let k = 0; k < 40; k++) { brain.block(128, L, R, pics, null); out.set(L, k * 128); }
    return out;
  };
  const a = go(null), b = go(other);
  let ends = 0, mids = 0;
  for (let k = 0; k < 40; k++) {
    ends = Math.max(ends, Math.abs(a[128 * k + 127] - b[128 * k + 127]));
    mids = Math.max(mids, Math.abs(a[128 * k + 63] - b[128 * k + 63]));
  }
  return { ends, mids };
}"""

def run(p, code, note, ramp=None):
    return p.evaluate(PLAY, {"code": code, "note": note, "ramp": ramp})

def holds(r): return r["onset"] <= 2 * r["steady"]
def bends(r): return r["bend"] <= 5 * r["steadyBend"]

def say(r):
    return ("step %.4f at %d, steady %.4f (%.1fx); bend %.4f at %d, steady %.4f (%.1fx); peak %.3f" % (
        r["onset"], r["at"], r["steady"], r["onset"] / max(r["steady"], 1e-12),
        r["bend"], r["bendAt"], r["steadyBend"], r["bend"] / max(r["steadyBend"], 1e-12), r["peak"]))

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    p = b.new_page(viewport={"width": 1400, "height": 900})
    errors = []
    p.on("pageerror", lambda e: errors.append(str(e)))
    p.goto(f"file://{ART}/scope.html")
    p.wait_for_timeout(1500)
    check("the site's brain is the compiled instrument", p.evaluate("BRAIN_IN_CORE") is True)

    bass = p.evaluate(LOAD, BASS_UNDER_TINE)
    lay = p.evaluate("() => JSON.parse(atob(encodeSetup(snapshot()))).layers")
    check("the reported sound loads as a split", lay == "split", str(lay))

    print("\n--- the bass hand: E2 and C3, a sine under the tine's routes ---")
    for note in (40, 48):
        r = run(p, bass, note)
        print("    note %d: %s" % (note, say(r)))
        check("the bass's note %d starts with no step past twice its steady one" % note, holds(r))
        # The bass sounds, or a silent note would pass: its steady peak is the sine's.
        check("and it sounds", r["peak"] > 0.1, "%.3f" % r["peak"])
        n = run(p, bass, note, 0)
        print("      null, the walk at nought: %s" % say(n))
        check("null: with the walk at nought, the step as it was, the same note breaks the bound", not holds(n))
        check("null: and its step is at the second block's top, where the routes caught up", n["at"] == 128, str(n["at"]))

    # The owner's choice that a route by hand steps rather than lags (the
    # page's sumRoutes): the walk arrives at its block's last sample, so there
    # the bass - a sine's phase modulated, with nothing that remembers the
    # depth - is to the bit what it was with the step, and only between differs.
    e = p.evaluate(ENDS, {"code": bass, "note": 40, "other": 0})
    check("no lag: at every block's last sample the bass is the step's to the bit, and between it is not",
          e["ends"] == 0 and e["mids"] > 0.05, str(e))
    e = p.evaluate(ENDS, {"code": bass, "note": 40, "other": 256})
    check("null: a walk over two blocks is not there by the block's end", e["ends"] > 0.05, str(e))

    print("\n--- the upper hand: the tine, at C4 ---")
    r = run(p, bass, 60)
    print("    note 60: %s" % say(r))
    # Bright on purpose, so held by its bend, not its step (the docstring says why).
    check("the tine's C4 starts with no bend past five times its steady one", bends(r))
    n = run(p, bass, 60, 0)
    print("      null: %s" % say(n))
    check("null: with the walk at nought, the tine's C4 breaks the bound", not bends(n))
    check("null: and its step alone could not have told", holds(n) or n["onset"] < 4 * n["steady"],
          "the step bound read the null at %.1fx" % (n["onset"] / n["steady"]))

    print("\n--- the plain sine with Velocity on FM ---")
    v = p.evaluate(VELOCITY_FM)
    check("the Velocity menu on FM routes the Key onto the FM depth", v["fm"] is True)
    for note in (45, 57):
        r = run(p, v["code"], note)
        print("    note %d: %s" % (note, say(r)))
        check("velocity's FM: note %d starts with no step past twice its steady one" % note, holds(r))
        n = run(p, v["code"], note, 0)
        print("      null: %s" % say(n))
        check("null: with the walk at nought, note %d breaks the bound" % note, not holds(n))

    check("no page errors", not errors, "; ".join(errors[:3]))
    b.close()

print("\n%s: %d failure(s)" % ("FAIL" if fails else "PASS", len(fails)))
sys.exit(1 if fails else 0)
