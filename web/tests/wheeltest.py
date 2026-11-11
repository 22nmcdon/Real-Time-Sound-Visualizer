"""The mod wheel on the Picture amount, on the site (11 Nov).

The owner gave the wheel to the Picture amount (Play's Expression) and moving
it under a held note broke the sound up: it crackled and cut out for a moment.
Two things were wrong, and each is checked against the way it failed:

- the stage's five routes are dropped when the amount comes to nought and
  made again when it leaves, and they switch the voice's shaper and the
  plane's non-linear stage, which run oversampled and so late by about 32
  samples, straight out and in: the heard sound stepped by half its scale.
  The stages crossfade now (the generator's `switchMs`). Checked on the
  instrument the site plays, compiled from the page's own module and handed
  the messages the page sent for a real port's bytes: the largest step from
  one sample to the next while the wheel goes to nought and back is held to
  what the same note steps by with the wheel still, and the same messages
  with the crossfade at nought - the switch as it was - must break that bound;
- the page sent every wheel step to the instrument twice: as the port's bytes,
  which the instrument reads for itself, and again as a hand on the slider
  the bytes had moved, which made the instrument apply it a second time and
  publish its whole state for each step, a hundred a second. The messages
  are counted where they leave for the worklet: one per controller, no hand;
  and, as its null, a hand on the same slider is still sent.
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

# Every message the page posts to the instrument's worklet, kept in order.
TAP = """(() => {
  const Orig = window.AudioWorkletNode;
  window.__posted = [];
  window.AudioWorkletNode = function (ctx, name, opts) {
    const node = new Orig(ctx, name, opts);
    if (name === "scope-brain") {
      const post = node.port.postMessage.bind(node.port);
      node.port.postMessage = (m, t) => { window.__posted.push(JSON.parse(JSON.stringify(m))); return post(m, t); };
    }
    return node;
  };
  window.AudioWorkletNode.prototype = Orig.prototype;
})();"""

# The instrument the worklet runs, made here from the module the page carries
# on the setup the page has, and played the messages given at their blocks:
# a held note, a second to settle, then the run. Back: the largest step from
# one sample to the next in the heard pair over the run.
PLAY = """({ code, wheel, switchMs }) => {
  const brain = makeWasmBrain(wasmModule(), 48000, 128, code);
  if (switchMs !== null) brain.control("switchMs", String(switchMs));
  brain.midi([0x90, 57, 100]);
  const L = new Float32Array(128), R = new Float32Array(128), pics = [0, 1, 2, 3, 4, 5].map(() => new Float32Array(128));
  for (let k = 0; k < 375; k++) brain.block(128, L, R, pics, null);
  let most = 0, last = null;
  for (let k = 0; k < wheel.length * 4; k++) {
    if (k % 4 === 0 && wheel[k / 4] !== null) brain.midi(wheel[k / 4]);
    brain.block(128, L, R, pics, null);
    for (let i = 0; i < 128; i++) {
      if (last) most = Math.max(most, Math.abs(L[i] - last[0]), Math.abs(R[i] - last[1]));
      last = [L[i], R[i]];
    }
  }
  return most;
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    errors = []
    p.on("pageerror", lambda e: errors.append(str(e)))
    p.add_init_script(TAP)
    p.goto(f"file://{ART}/scope.html")
    p.wait_for_timeout(2500)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_function("() => hostSync.on && state.source && state.source.kind === 'host'", timeout=20000)
    # A Breathing sound, the bank's Harmonic tone at a Picture amount of sixty, and the wheel given to the amount.
    p.evaluate("""() => { applyPreset('p:Harmonic tone');
      el.midiWheelTo.value = 'picture'; el.midiWheelTo.dispatchEvent(new Event('change', { bubbles: true })); }""")
    p.wait_for_timeout(300)
    start = p.evaluate("() => Number(el.pictureAmount.value)")
    code = p.evaluate("() => encodeSetup(snapshot())")

    # The wheel from where the amount stands to nought, held there, and back,
    # through the port's handler as a keyboard's bytes come.
    top = round(start / 100 * 127)
    down = [round(top * (1 - k / 24)) for k in range(25)]
    values = down + [0] * 15 + down[::-1]
    sent = p.evaluate("""(values) => {
      window.__posted.length = 0;
      midiBytes([0x90, 57, 100], performance.now());
      for (const v of values) midiBytes([0xb0, 1, v], performance.now());
      const posted = window.__posted.slice();
      return { posted, amount: Number(el.pictureAmount.value) };
    }""", values)
    ccs = [m for m in sent["posted"] if m.get("op") == "midi" and m["bytes"][:2] == [0xB0, 1]]
    hands = [m for m in sent["posted"] if m.get("op") == "slider" and m.get("id") == "pictureAmount"]
    check("each step of the wheel goes to the instrument once, as the port's bytes, and not again as a hand on the slider",
          len(ccs) == len(values) and [m["bytes"][2] for m in ccs] == values and not hands and sent["amount"] == round(values[-1] / 127 * 100),
          "%d controllers for %d steps, %d hands, the page's slider at %s" % (len(ccs), len(values), len(hands), sent["amount"]))
    hand = p.evaluate("""() => {
      window.__posted.length = 0;
      el.pictureAmount.value = '35'; el.pictureAmount.dispatchEvent(new Event('input', { bubbles: true }));
      return window.__posted.filter((m) => m.op === 'slider' && m.id === 'pictureAmount').map((m) => String(m.value));
    }""")
    check("and a hand on the same slider is still sent: the count can see one", hand == ["35"], str(hand))

    # The sound: the wheel's own bytes as the page sent them, a message every
    # four blocks (a hundred a second), against the same note with the wheel
    # still and against the stages switched straight.
    wheel = [m["bytes"] for m in ccs]
    still = p.evaluate(PLAY, {"code": code, "wheel": [None] * len(wheel), "switchMs": None})
    moving = p.evaluate(PLAY, {"code": code, "wheel": wheel, "switchMs": None})
    straight = p.evaluate(PLAY, {"code": code, "wheel": wheel, "switchMs": 0})
    check("the wheel to nought and back under a held note steps the instrument's sound no further than the note alone",
          moving <= 1.25 * still, "%.4f moving, %.4f still" % (moving, still))
    check("and the same wheel with the stages switched straight, as they were, steps it several times as far",
          straight > 3 * still, "%.4f switched straight" % straight)
    check("no errors on the page", not errors, "; ".join(errors[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
