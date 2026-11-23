"""A hand muted (23 Nov, the owner's), on the core's whole instrument.

With two hands, the face's mute on either sends the instrument "handMute"
(the lower hand's bit, the upper's), which it does not keep. A muted hand's
sound is taken out before the plane, so it is neither heard nor drawn, and
Scan reads nothing of it: the picture is the sound. What would go wrong, and
what is checked for it:

- the wrong hand, or both: with the lower hand muted, a chord in both hands
  is heard as the upper hand's note alone, to the noise of the glide's
  first 20 ms - and the null, unmuted, is not; and the same the other way;
- heard but still drawn: the picture's lanes with a hand muted are the
  other hand's alone, to the same tolerance;
- coming back with a click: unmuted again the hand is back, and the gain
  moved by a glide, so no step between two samples is larger than the sound
  makes on its own;
- a hand muted with one hand: alone, the lower hand is the instrument, and
  a mute left set does nothing.
"""
import base64, json, os
import numpy as np

RATE = 48000
SPLIT = {"shape": "sine", "midiMode": "poly", "layers": "split", "splitAt": 60, "pictureAmount": 0, "bShape": "sine",
         "atk": 2, "dec": 100, "sus": 100, "rel": 50, "display": "xy"}


def code(setup):
    return base64.b64encode(json.dumps(dict({"v": 13}, **setup)).encode()).decode().rstrip("=")


def run(kit):
    check, null = kit.check, kit.null
    base = os.path.join(os.path.dirname(kit.build("render_cpp")), "mute")

    def play(notes, mute=None, setup=SPLIT, unmute_at=None):
        lines = [["make", RATE, code(setup)], ["record", "heard", base + ".heard"], ["record", "lanes", base + ".lanes"]]
        if mute is not None: lines.append(["control", "handMute", str(mute)])
        lines += [["to", 0.1]] + [["midi", 0x90, n, 100] for n in notes]
        if unmute_at: lines += [["to", unmute_at], ["control", "handMute", "0"]]
        lines += [["to", 1.2], ["record", "heard"], ["record", "lanes"]]
        kit.render(lines, raw=True)
        x = np.fromfile(base + ".heard", dtype=np.float32).reshape(-1, 2)
        g = np.fromfile(base + ".lanes", dtype=np.float32)
        return x, g.reshape(len(x), -1) if len(g) % len(x) == 0 else g

    both, both_l = play([48, 72])
    lower, lower_l = play([48])
    upper, upper_l = play([72])
    tail = slice(int(0.5 * RATE), None)  # past the glide (20 ms a step of e, snapped at a millionth) and the attack
    def diff(a, b): return float(np.abs(a[tail] - b[tail]).max())

    m1, m1_l = play([48, 72], mute=1)
    check("with the lower hand muted a chord in both hands is heard as the upper hand's note alone",
          diff(m1, upper) < 1e-6, "largest difference %g" % diff(m1, upper))
    null("unmuted, the chord is not the upper hand's note alone", diff(both, upper) > 0.05, "%g" % diff(both, upper))
    m2, m2_l = play([48, 72], mute=2)
    check("and with the upper hand muted, the lower hand's alone", diff(m2, lower) < 1e-6, "largest difference %g" % diff(m2, lower))
    check("drawn as heard: the picture's lanes with a hand muted are the other hand's alone",
          diff(m1_l, upper_l) < 1e-6 and diff(m2_l, lower_l) < 1e-6,
          "%g and %g" % (diff(m1_l, upper_l), diff(m2_l, lower_l)))
    null("and the lanes can see a hand: the chord's are not one hand's", diff(both_l, upper_l) > 0.05, "%g" % diff(both_l, upper_l))
    m3, _ = play([48, 72], mute=3)
    check("both muted, nothing", float(np.abs(m3[tail]).max()) < 1e-6, "peak %g" % float(np.abs(m3[tail]).max()))

    back, _ = play([48, 72], mute=1, unmute_at=0.4)
    late = slice(int(0.8 * RATE), None)
    check("unmuted again, the hand is back: the chord as it is with no mute",
          float(np.abs(back[late] - both[late]).max()) < 1e-6, "%g" % float(np.abs(back[late] - both[late]).max()))
    # A click is a step in what the mute takes away: back minus the chord is the lower hand times
    # (gain - 1), smooth on a glide, and on a jump a step of the lower hand's level at that sample.
    d = (back - both)[int(0.39 * RATE):int(0.5 * RATE), 0].astype(float)
    level = float(np.abs(lower[tail, 0]).max())
    step = float(np.abs(np.diff(d)).max())
    check("and it comes back on a glide: what it takes away moves by under 5 per cent of the hand's level a sample",
          step < 0.05 * level, "largest step %.5f, the hand's level %.4f" % (step, level))

    one = dict(SPLIT, layers="off")
    alone, _ = play([48], setup=one)
    alone_m, _ = play([48], mute=1, setup=one)
    check("with one hand a mute left set does nothing: alone, the lower hand is the instrument",
          float(np.abs(alone - alone_m).max()) == 0, "%g" % float(np.abs(alone - alone_m).max()))
    plain, _ = play([48, 72], mute=0)
    check("and a mute of nought is no mute at all, to the bit", float(np.abs(plain - both).max()) == 0)
