"""The lag, heard: C1's last row, and where the comb it makes is deepest.

On the screen the lag replaces the second lane with the first one delayed by
tau. In the speakers the right channel crossfades from itself towards the left
delayed by the same tau, so at a mix of one the speakers ARE the picture. Two
things are checked, and the second is the one that matters for anybody tuning
it.

THE TWO IMPLEMENTATIONS AGREE. The picture's delayed lane is a linear
interpolation in `capture`; the speakers' is a `DelayNode`. Same signal, same
tau - a fractional number of samples, so the interpolation is doing work - and
the two are held against each other sample for sample, the way the biquad and
the rotation already are. C1's table said "to interpolation error; state the
tolerance", so the tolerance is measured and printed rather than chosen.

WHERE THE COMB IS DEEPEST, measured, because it does not go where the plan
assumed. A delayed copy summed with its original cancels it at every odd
multiple of 1/(2 tau). The plan expected full-strength mixing to be the version
most likely to sound bad, and for one of the two ways of listening that is true
and for the other it is exactly backwards:

- The RIGHT CHANNEL ON ITS OWN - which is what a pair of headphones puts in one
  ear - is (1-m)x + m x(t-tau). Its notch has depth |1 - 2m|: total silence at
  a mix of one half, and none at all at one, where it is simply a delay.
- The MONO SUM - which is what a pair of speakers in a room delivers, since the
  two channels meet in the air - has depth 1 - m: total at one, and shallowest
  at nought.

So there is no single mix that is safe for both, and the worst case for
headphones is in the middle of the range rather than at the top of it. The
placeholder ceiling is set from that: below one half, so the headphone null
cannot be reached, and far enough below one that the room's null cannot either.
"""
import math, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


# Render the real monitor chain offline. `drive` either goes through
# `syncMonitor` - the page's own path, with its ceiling - or sets the lag
# stage's gains directly, which is how the survey reaches past the ceiling on
# purpose to show why the ceiling is where it is.
RENDER = """async ([opts]) => {
  const rate = 44100, frames = opts.frames || Math.round(rate * 0.5);
  const ctx = new OfflineAudioContext(2, frames, rate);
  const buffer = ctx.createBuffer(2, frames, rate);
  const l = buffer.getChannelData(0), r = buffer.getChannelData(1);
  const x = window.__signal(opts.signal, frames, rate);
  l.set(x); r.set(opts.signal.right === 'silent' ? new Float32Array(frames) : x);

  const src = ctx.createBufferSource();
  src.buffer = buffer;
  const chain = makeMonitorChain(ctx);
  src.connect(chain.input);
  // Straight out of the lag and rotation stages, before the limiter - whose
  // lookahead and makeup gain would otherwise be what got measured.
  chain.merger.disconnect();
  chain.merger.connect(ctx.destination);

  if (opts.drive === 'direct') {
    monitorChains.delete(chain);                 // nothing may re-target these
    chain.lagDelay.delayTime.value = opts.tauMs / 1000;
    chain.lagWet.gain.value = opts.mix;
    chain.lagDry.gain.value = 1 - opts.mix;
  } else {
    const was = { on: state.lagOn, auto: state.lagAuto, ms: state.lagMs,
                  mix: state.lagMix, at: state.monitorAt, ms2: state.midSide,
                  filter: state.filter.on, rotate: state.rotate };
    state.lagOn = opts.lagOn !== false; state.lagAuto = false;
    state.lagMs = opts.tauMs; state.lagMix = opts.mix;
    state.monitorAt = opts.at || 'post'; state.midSide = false;
    state.filter.on = false; state.rotate = 0; state.rotateMod = 0;
    // A delay still holding the tau it had when the lag was last on, which is
    // what switching it off leaves behind. A fresh chain's delay is at nought,
    // and an undelayed copy mixed with the signal in any proportion sums back
    // to the signal - so without this the lag-off check could not fail.
    if (opts.staleMs) chain.lagDelay.delayTime.value = opts.staleMs / 1000;
    syncMonitor();
    Object.assign(state, { lagOn: was.on, lagAuto: was.auto, lagMs: was.ms,
                           lagMix: was.mix, monitorAt: was.at, midSide: was.ms2,
                           rotate: was.rotate });
    state.filter.on = was.filter;
    monitorChains.delete(chain);
  }

  src.start();
  const out = await ctx.startRendering();
  return { x: Array.from(x), left: Array.from(out.getChannelData(0)),
           right: Array.from(out.getChannelData(1)), rate, frames,
           wet: chain.lagWet.gain.value };
}"""

SIGNAL = """(spec, frames, rate) => {
  const x = new Float32Array(frames);
  for (let i = 0; i < frames; i++) {
    const t = i / rate;
    x[i] = spec.kind === 'sine'
      ? 0.5 * Math.sin(2 * Math.PI * spec.hz * t)
      // Two partials, not harmonically related, so that no single delay lines
      // them both up and the comparison cannot pass by symmetry.
      : 0.4 * Math.sin(2 * Math.PI * 220 * t) + 0.2 * Math.sin(2 * Math.PI * 557 * t + 0.3);
  }
  return x;
}"""


def steady_peak(values, frames, tail=0.4):
    start = int(frames * (1 - tail))
    return max(abs(v) for v in values[start:])


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
    p.evaluate("(src) => { window.__signal = eval(src); }", SIGNAL)

    print("\n--- the picture's delayed lane and the speakers' agree ---")
    # A fractional tau, so interpolation is doing real work on both sides:
    # 3.137 ms is 138.34 samples at 44.1 kHz.
    TAU = 3.137
    agree = p.evaluate("""async ([tau, render]) => {
      const rate = 44100, frames = 32768;
      const x = window.__signal({ kind: 'mix' }, frames, rate);

      /* The picture's half: `capture` itself, on a stand-in source holding x,
         with the lag on at exactly this tau. Not a copy of its arithmetic -
         the thing that draws the screen. */
      const was = { src: state.source, run: state.running, on: state.lagOn,
                    auto: state.lagAuto, ms: state.lagMs, tb: state.timebase,
                    ms2: state.midSide, level: state.level };
      state.running = false;
      state.midSide = false;
      state.lagOn = true; state.lagAuto = false; state.lagMs = tau;
      state.timebase = 4;
      state.level = 2;                            // one fixed window
      state.source = {
        kind: 'tone', settings: null,
        get sampleRate() { return rate; },
        get capacity() { return frames; },
        get channels() { return 1; },
        tick() {}, stop() {}, describe: () => 'x',
        getLatestWindow: (n) => [x.subarray(Math.max(0, frames - n))],
      };
      const f = capture();
      const shown = f.channels[0], delayed = f.channels[1];
      const lagActual = state.lagActual;

      // Where in x the window starts, found by matching it exactly.
      let at = -1;
      for (let k = 0; k + shown.length <= frames && at < 0; k++) {
        let same = true;
        for (let j = 0; j < 16 && same; j++) if (x[k + j] !== shown[j]) same = false;
        if (same) at = k;
      }
      Object.assign(state, { source: was.src, running: was.run, lagOn: was.on,
                             lagAuto: was.auto, lagMs: was.ms, timebase: was.tb,
                             midSide: was.ms2, level: was.level });
      return { at, delayed: Array.from(delayed), length: shown.length, lagActual };
    }""", [TAU, None])

    heard = p.evaluate(RENDER, [{"signal": {"kind": "mix"}, "frames": 32768,
                                 "drive": "direct", "tauMs": TAU, "mix": 1}])
    # With the mix at one, the right channel is the delayed left and nothing
    # else - the one setting at which the speakers are the picture.
    at = agree["at"]
    worst = 0.0
    if at >= 0:
        for i in range(agree["length"]):
            worst = max(worst, abs(agree["delayed"][i] - heard["right"][at + i]))
    print("    tau %.3f ms (%.2f samples), window of %d found at sample %d"
          % (TAU, TAU * 44.1, agree["length"], at))
    print("    worst disagreement between the picture and the DelayNode: %.2e"
          % worst)
    check("the picture used the tau it was given",
          abs(agree["lagActual"] - TAU) < 1e-9, "%.6f ms" % agree["lagActual"])
    check("its window was found in the signal, so the comparison is aligned",
          at > 0, str(at))
    check("and the two implementations agree, to interpolation error",
          worst < 1e-4, "worst %.2e" % worst)

    print("\n--- where the comb is deepest ---")
    # A sine at the first notch, 1/(2 tau), on both channels - a correlated
    # pair, which is what a mono source and the generator's unison both are.
    NOTCH_TAU = 5.0                               # ms, so the notch is 100 Hz
    notch_hz = 1000 / (2 * NOTCH_TAU)
    survey = []
    for mix in (0, 0.1, 0.25, 0.4, 0.5, 0.75, 1.0):
        run = p.evaluate(RENDER, [{"signal": {"kind": "sine", "hz": notch_hz},
                                   "drive": "direct", "tauMs": NOTCH_TAU, "mix": mix}])
        right = steady_peak(run["right"], run["frames"]) / 0.5
        mono = steady_peak([(a + c) / 2 for a, c in zip(run["left"], run["right"])],
                           run["frames"]) / 0.5
        survey.append({"mix": mix, "right": right, "mono": mono})

    def db(v):
        return "-inf" if v < 1e-5 else "%+.1f" % (20 * math.log10(v))
    print("    a %.0f Hz sine, at the notch, through the lag stage:" % notch_hz)
    print("      mix   right channel (headphones)   mono sum (a room)")
    for row in survey:
        print("      %.2f   %.3f  %6s dB              %.3f  %6s dB"
              % (row["mix"], row["right"], db(row["right"]),
                 row["mono"], db(row["mono"])))

    check("the right channel's notch is |1 - 2m|, as the algebra says",
          all(abs(r["right"] - abs(1 - 2 * r["mix"])) < 0.02 for r in survey),
          str([(r["mix"], round(r["right"], 3)) for r in survey]))
    check("and the mono sum's is 1 - m",
          all(abs(r["mono"] - (1 - r["mix"])) < 0.02 for r in survey),
          str([(r["mix"], round(r["mono"], 3)) for r in survey]))
    half = next(r for r in survey if r["mix"] == 0.5)
    full = next(r for r in survey if r["mix"] == 1.0)
    check("in headphones the null is total at a mix of one half, not at the top",
          half["right"] < 0.01 and full["right"] > 0.98,
          "%.4f at a half, %.4f at one" % (half["right"], full["right"]))
    check("in a room it is total at the top, and absent at nought",
          full["mono"] < 0.01 and survey[0]["mono"] > 0.98,
          "%.4f at one, %.4f at nought" % (full["mono"], survey[0]["mono"]))

    print("\n--- the placeholders, and the ceiling holding ---")
    limits = p.evaluate("() => ({ def: LAG_MIX_DEFAULT, ceiling: LAG_MIX_CEILING })")
    print("    default %.2f, ceiling %.2f" % (limits["def"], limits["ceiling"]))
    # Properties rather than the numbers, because the numbers are placeholders
    # waiting for a pair of ears. What must stay true whatever they are tuned
    # to: neither total null is reachable, and the default is under the ceiling.
    check("the ceiling keeps the headphone null out of reach",
          limits["ceiling"] < 0.5 - 0.05,
          "%.2f, against a null at 0.50" % limits["ceiling"])
    check("and the room's null too",
          limits["ceiling"] < 1.0, "%.2f" % limits["ceiling"])
    check("and the default sits under the ceiling",
          0 < limits["def"] <= limits["ceiling"], str(limits))

    asked = p.evaluate(RENDER, [{"signal": {"kind": "sine", "hz": notch_hz},
                                 "drive": "sync", "tauMs": NOTCH_TAU, "mix": 1.0,
                                 "frames": 22050}])
    heard_right = steady_peak(asked["right"], asked["frames"]) / 0.5
    expect = abs(1 - 2 * limits["ceiling"])
    print("    a mix of one asked for through the page's own path: wet gain %.3f, "
          "right-channel notch %.3f (the ceiling predicts %.3f)"
          % (asked["wet"], heard_right, expect))
    check("asking for more than the ceiling gets the ceiling, not what was asked",
          abs(asked["wet"] - limits["ceiling"]) < 1e-3
          and abs(heard_right - expect) < 0.03,
          "wet %.3f, notch %.3f" % (asked["wet"], heard_right))

    print("\n--- and the taps straddle it ---")
    dry = p.evaluate(RENDER, [{"signal": {"kind": "mix"}, "drive": "sync",
                               "tauMs": TAU, "mix": limits["def"], "at": "pre",
                               "staleMs": TAU}])
    off = p.evaluate(RENDER, [{"signal": {"kind": "mix"}, "drive": "sync",
                               "tauMs": TAU, "mix": limits["def"], "lagOn": False,
                               "staleMs": TAU}])
    on = p.evaluate(RENDER, [{"signal": {"kind": "mix"}, "drive": "sync",
                              "tauMs": TAU, "mix": limits["def"]}])
    def worst_vs_input(run):
        n = run["frames"]
        return max(max(abs(run["left"][i] - run["x"][i]),
                       abs(run["right"][i] - run["x"][i])) for i in range(n // 2, n))
    print("    speakers on the input: %.2e; lag off: %.2e; lag on and shaped: %.3f"
          % (worst_vs_input(dry), worst_vs_input(off), worst_vs_input(on)))
    check("with the speakers on the input, the lag is not heard at all",
          worst_vs_input(dry) == 0, "%.2e" % worst_vs_input(dry))
    check("with the lag off, the stage is exactly the identity",
          worst_vs_input(off) == 0, "%.2e" % worst_vs_input(off))
    check("and on the shaped side with the lag on, it is heard",
          worst_vs_input(on) > 0.01, "%.3f" % worst_vs_input(on))
    # The left channel is the signal, and is heard as it was - the same as lane
    # one is drawn as it was.
    check("only the right channel is touched",
          max(abs(on["left"][i] - on["x"][i]) for i in range(on["frames"] // 2,
                                                             on["frames"])) == 0)

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the lag is heard, and its worst case is where it was measured to be")
