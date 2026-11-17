"""A note alone in Poly, Dyad and Mono (15 Nov, the owner's list, item 1).

The owner heard a single note in Poly sound different from the same note in
Dyad or Mono. Rendered offline, the three agreed in level, envelope, filter
and pitch, and differed in one thing: which way round the figure goes. A
dyad's lone note is two copies of one voice with the right channel's phase a
quarter turn on (the Phase knob's default), so the right LEADS; Poly's quarter
turn (polyRound then, on in the base and the bank; always since 16 Nov) laid the right channel a quarter
of the period LATE. The same circle traced the other way - on a sine nothing
else, since every statistic of a circle survives a mirror, but a lone note's
channels a quarter apart are heard in the leading ear, so the note sat on the
other side, and Scan, which reads the figure, read a different wave off it:
the base sine with Scan at half came out five per cent louder in Poly. The
quarter turn now delays the left instead (scope/voices.h, `sound`), which is
the dyad's relation exactly for any wave, the drawbars' two-cycle phase too.

What is the same by construction is not tested here: the level, envelope and
filter are one code path's in each mode. What is tested is what differed,
with fixtures the mirror can show - never a statistic a mirror leaves alone:
the figure's signed area (which way round it goes), the lag at which the
right channel best matches the left, and the level Scan makes of the figure,
since Scan reads it at the voice's own phase and so is not mirror-blind.

Kept different, by design, and so not checked to agree: Mono's second
channel is the Interval knob's (a lone note is a unison only at unison);
Dyad's Hold keeps the last interval; Dyad and Mono follow the Phase knob,
which Poly's quarter turn does not; and a split or a layer is Poly's alone.
What is heard is each note in both ears at the Width (ears.py), at a
hundred, the default, the quarter turn - which is what is read here.
"""
import math, os, struct

from pieces.pulse import setup_code

RATE = 48000
NOTE = 60
BASE = {"shape": "sine", "midiMode": "poly", "pictureAmount": 0, "display": "xy",
        "persistence": "0.3", "timebase": 3, "scanStrike": 0}


def run(kit):
    check, null = kit.check, kit.null
    path = os.path.join(os.path.dirname(kit.build("render_cpp")), "modes-heard.f32")

    def render(fields, mode, held=1.2):
        f = dict(BASE, **fields)
        f["midiMode"] = mode
        # At a hundred, where a lone note's right is a quarter turn on; fifty is the default since 17 Nov.
        kit.render([["make", RATE, setup_code(f)], ["slider", "stereoWidth", "100"], ["to", 0.2], ["record", "heard", path],
                    ["midi", 0x90, NOTE, 100], ["to", 0.2 + held], ["record", "heard"]], raw=True)
        d = open(path, "rb").read()
        v = struct.unpack("<%df" % (len(d) // 4), d)
        return list(v[0::2]), list(v[1::2])

    def area(l, r):
        """Twice the signed area swept a sample: positive counter-clockwise."""
        return sum(l[i] * (r[i + 1] - r[i]) - r[i] * (l[i + 1] - l[i]) for i in range(len(l) - 1)) / len(l)

    def rms(x):
        return math.sqrt(sum(a * a for a in x) / len(x))

    def lead(l, r):
        """The lag in samples at which the right best matches the left
        shifted: positive where the right leads (r[i] ~ l[i + lag])."""
        n = 4800
        best = max(range(-120, 121), key=lambda g: sum(r[i] * l[i + g] for i in range(200, 200 + n)))
        return best

    held = slice(int(0.5 * RATE), int(1.2 * RATE))   # half a second in, past the onset and the strike's light
    quarter = RATE / (4 * 440 * 2 ** ((NOTE - 69) / 12))   # 45.9 samples at middle C

    for label, fields in (("a plain sine", {}), ("the drawbars' 16', 5 1/3' and 8'", {"shape": "drawbars", "bars": "888000000"}),
                          ("a saw", {"shape": "ramp"})):
        runs = {m: render(fields, m) for m in ("poly", "dyad", "mono")}
        areas = {m: area(l[held], r[held]) for m, (l, r) in runs.items()}
        leads = {m: lead(l[held], r[held]) for m, (l, r) in runs.items()}
        check("%s alone goes round the same way in Poly as in Dyad and Mono" % label,
              all(a < 0 for a in areas.values()) or all(a > 0 for a in areas.values()),
              ", ".join("%s %+.5f" % kv for kv in areas.items()))
        check("and in each the right channel leads the left by a quarter of the period",
              all(abs(g - quarter) <= 1.5 for g in leads.values()), "%s, a quarter is %.1f" % (leads, quarter))
        if label == "a plain sine":
            # The null, on the dyad's own samples: its left a quarter late as the
            # right, which is what Poly's quarter turn made until 15 Nov.
            l = runs["dyad"][0][held]
            q = int(round(quarter))
            mirrored = (l[q:], l[:-q])
            null("the dyad's left laid a quarter late on the right goes round the other way",
                 (area(*mirrored) > 0) != (areas["dyad"] > 0), "%+.5f against %+.5f" % (area(*mirrored), areas["dyad"]))
            null("and its right lags", lead(*mirrored) < 0, "%d" % lead(*mirrored))

    # Scan reads the figure at the voice's own phase, so a mirror is a different
    # wave read off it: the level Scan makes of a lone note is the same in the
    # three modes. Measured at half, where the base sine came out 0.2250 in Poly
    # against 0.2145 in Dyad before the fix and 0.2138 after.
    scanned = {m: render({"oscScan": 50}, m) for m in ("poly", "dyad", "mono")}
    level = {m: (rms(l[held]) + rms(r[held])) / 2 for m, (l, r) in scanned.items()}
    spread = max(level.values()) / min(level.values()) - 1
    check("a lone note read back by Scan at half is as loud in Poly as in Dyad and Mono, within one per cent",
          spread < 0.01, ", ".join("%s %.4f" % kv for kv in level.items()))
    # Its null: the same note in Dyad with the Phase knob at a quarter the
    # other way (the mirror's relation, made by the dyad's own control).
    other = render({"oscScan": 50, "phase": 270}, "dyad")  # degrees, as a setup stores it
    lv = (rms(other[0][held]) + rms(other[1][held])) / 2
    null("and the mirrored figure, read by Scan, is not", abs(lv / level["dyad"] - 1) > 0.01,
         "%.4f against %.4f" % (lv, level["dyad"]))
