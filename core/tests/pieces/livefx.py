"""The effects on a live input, on the core: the mirror folds what is drawn
and what is heard alike, into the quadrant and over the whole of it; a
routing on the twist swirls a mono input's diagonal off itself; a delay puts
the repeat at its time to within two samples - livefxtest.py's numbers rows
(:134, :138, :159, :164, :211, :260).

These were livefxtest.py's on `?brain=js` until stage 5, step 3, batch 5 (13
Nov), where the effects on a microphone were the page's own insert - a
worklet of its own the page started and told, which the instrument does not
have. The instrument puts an input through its effects itself: drawing the
input (srcMic, which the site's Mic button sends it), its render runs the
input through the generator's `effect` - the plane and the time effects -
and what comes out is both the picture and what is heard (pieces/render.py
holds that much first). So here render_cpp draws an input through it: the
stub's two oscillators, 220 Hz on the left and 330 on the right at 0.8 (a
3:2 pair, never a circle, which a fold could leave alone), or one in both
channels for the mono input; and the burst, 20 ms of 1 kHz every half second.
Each check has its null.
"""
import base64, json, math, os

import numpy as np

from pieces.kit import BUILD

RATE = 48000


def code(setup):
    return base64.b64encode(json.dumps(dict({"v": 11, "pictureAmount": 0}, **setup)).encode()).decode().rstrip("=")


def stereo(seconds, mono=False):
    t = np.arange(int(seconds * RATE)) / RATE
    left = 0.8 * np.sin(2 * np.pi * 220 * t)
    right = left if mono else 0.8 * np.sin(2 * np.pi * 330 * t)
    path = os.path.join(BUILD, "livefx-%s.f32" % ("mono" if mono else "pair"))
    np.stack([left, right], 1).astype("<f4").tofile(path)
    return path


def bursts(seconds):
    x = np.zeros(int(seconds * RATE))
    n = int(0.02 * RATE)
    for start in range(0, len(x), RATE // 2):
        k = np.arange(min(n, len(x) - start))
        x[start:start + len(k)] = 0.5 * np.sin(2 * np.pi * 1000 * k / RATE)
    path = os.path.join(BUILD, "livefx-burst.f32")
    np.stack([x, x], 1).astype("<f4").tofile(path)
    return path


def draw(kit, setup, path, seconds=1.5, more=None, mono=False):
    """The input drawn through the instrument for `seconds`; its last second's
    drawn pair (the picture's first two lanes) and heard pair."""
    lanes, heard = os.path.join(BUILD, "livefx-lanes.f32"), os.path.join(BUILD, "livefx-heard.f32")
    lines = [["make", RATE, code(setup)], ["click", "srcMic"], ["input", "file", path, 2]] + (more or [])
    # The heard pair as it stands before the limiter (5a), which puts it 6 ms
    # late and bends its peaks: what is held here is what the instrument makes
    # of its input, sample for sample, which the limiter after it does not change.
    lines += [["record", "lanes", lanes], ["record", "prelimit", heard], ["to", seconds]]
    kit.render(lines)
    d = np.fromfile(lanes, "<f4").reshape(-1, 6)[-RATE:]  # the ring's six lanes a sample
    h = np.fromfile(heard, "<f4").reshape(-1, 2)[-RATE:]
    return d[:, 0], d[:, 1], h


def run(kit):
    check, null = kit.check, kit.null
    os.makedirs(BUILD, exist_ok=True)  # the inputs are written before anything is built
    pair = stereo(2.5)

    # --- drawn, and heard ---
    x0, y0, h0 = draw(kit, {}, pair)
    x3, y3, h3 = draw(kit, {"planeMirror": 3}, pair)
    x1, y1, _ = draw(kit, {"planeMirror": 1}, pair)
    print("    lowest drawn X, Y: as it is %.3f %.3f; mirrored both %.3f %.3f; X alone %.3f %.3f; heard before %.3f, after %.3f"
          % (x0.min(), y0.min(), x3.min(), y3.min(), x1.min(), y1.min(), h0.min(), h3.min()))
    check("mirrored, the input is drawn with no negative half on either axis", x3.min() > -0.02 and y3.min() > -0.02,
          "%.3f, %.3f" % (x3.min(), y3.min()))
    null("as it is, it has both", x0.min() < -0.7 and y0.min() < -0.7, "%.3f, %.3f" % (x0.min(), y0.min()))
    check("and X alone folded gives Y back its negative half", x1.min() > -0.02 and y1.min() < -0.7, "%.3f, %.3f" % (x1.min(), y1.min()))
    null("which mirrored on both it has not", not (y3.min() < -0.7))
    check("and what is heard is mirrored too", h0.min() < -0.5 and h3.min() > -0.02, "%.3f before, %.3f after" % (h0.min(), h3.min()))
    null("an unmirrored heard pair is caught by the same bound", not (h0.min() > -0.02), "%.3f" % h0.min())

    # --- the generator's arithmetic ---
    r = np.hypot(x3, y3)
    a = np.arctan2(y3[r >= 0.1], x3[r >= 0.1])
    print("    both halves mirrored: angles %.4f to %.4f over %d points" % (a.min(), a.max(), len(a)))
    # The oversampling's filter lets a corner overshoot a hair past the quadrant.
    check("the mirror on both folds every angle of the input into 0 to pi/2, as the generator's does",
          a.min() > -0.05 and a.max() < math.pi / 2 + 0.05 and len(a) > 2000, "%.4f to %.4f" % (a.min(), a.max()))
    a0 = np.arctan2(y0[np.hypot(x0, y0) >= 0.1], x0[np.hypot(x0, y0) >= 0.1])
    null("unfolded, the angles go all the way round", a0.min() < -1 and a0.max() > 2, "%.3f to %.3f" % (a0.min(), a0.max()))
    check("and the two channels arrive as two: the folded input fills the quadrant rather than one ray of it",
          a.max() - a.min() > 0.4, "%.3f" % (a.max() - a.min()))
    mono = stereo(2.5, mono=True)
    xm, ym, _ = draw(kit, {"planeMirror": 3}, mono)
    am = np.arctan2(ym[np.hypot(xm, ym) >= 0.1], xm[np.hypot(xm, ym) >= 0.1])
    null("one channel in both folds to one ray", am.max() - am.min() < 0.4, "%.3f" % (am.max() - am.min()))

    # --- a routing, on a mono input ---
    # An oscillator on the twist at full, at half a cycle a second, the twist's
    # slider at nought. Read two and a half seconds on, as the page did. The
    # setup's rate is in hundredths of a hertz (l0r 50, the Rate slider's
    # units); until batch 6 this said 0.5, which is 0.005 Hz, and the
    # oscillator had barely moved from its start - the swirl passed on a
    # twist all but held, not on one swept.
    apart = lambda x, y: float(np.max(np.abs(x - y)))
    xs, ys, _ = draw(kit, {}, mono, seconds=2.5)
    xt, yt, _ = draw(kit, {"mod": "lfo1>gen.twist@1.000", "l0r": 50}, mono, seconds=2.5)
    print("    a mono input's diagonal: level %.3f, apart %.4f still and %.3f with the twist swirled" % (np.max(np.abs(xs)), apart(xs, ys), apart(xt, yt)))
    check("an oscillator on the twist swirls a mono input's diagonal off itself, from a slider at nought",
          np.max(np.abs(xs)) > 0.5 and apart(xs, ys) < 1e-3 and apart(xt, yt) > 0.2, "%.3f" % apart(xt, yt))
    xz, yz, _ = draw(kit, {"mod": "lfo1>gen.twist@0.000", "l0r": 50}, mono, seconds=2.5)
    null("routed at nought it does not", apart(xz, yz) < 1e-3, "%.4f" % apart(xz, yz))

    # --- a burst, and its echoes ---
    burst = bursts(2.5)
    def onsets(x):
        out, quiet = [], RATE
        for i, v in enumerate(x):
            if abs(v) > 0.1:
                if quiet > RATE * 0.01: out.append(i)
                quiet = 0
            else: quiet += 1
        return out
    def gaps(setup):
        x, _, _ = draw(kit, setup, burst, seconds=2.5)
        o = onsets(x)
        return [b - a for a, b in zip(o, o[1:])]
    g = gaps({"delayMix": 100, "delayFeedback": 0, "delayMs": 150})
    want = 0.15 * RATE
    short = [d for d in g if d < 0.25 * RATE]
    check("a delay on a live input puts the repeat 150 ms after the burst, to within 2 samples",
          len(short) >= 1 and all(abs(d - want) <= 2 for d in short), "gaps %s against %.0f" % (g, want))
    dry = gaps({})
    null("without it there is no repeat between the bursts", not [d for d in dry if d < 0.25 * RATE], "gaps %s" % dry)
    g2 = gaps({"delayMix": 100, "delayFeedback": 0, "delayMs": 160})
    s2 = [d for d in g2 if d < 0.25 * RATE]
    null("and at 160 ms the repeat is not at 150", s2 and not all(abs(d - want) <= 2 for d in s2), "gaps %s" % g2)
