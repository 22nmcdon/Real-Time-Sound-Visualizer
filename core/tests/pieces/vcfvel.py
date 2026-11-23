"""The filter's envelope's Velocity (23 Nov, the owner's): how much of the
sweep follows how hard the key went, on the core's whole instrument.

The owner set a saw at 2 kHz with +3.3 octaves of sweep, played it softly
and heard it stay dark: the filter's envelope, like the amplifier's, was
scaled by the note's velocity (Mseg's level times vel/127), and nothing on
the face said so. Velocity at 100 per cent is that law, unchanged to the bit,
so every setup, preset and recording plays as it did; at nought every note
sweeps the whole Amount. What would go wrong, and what is checked for it:

- the knob read and ignored: at nought a note struck at 20 is as bright as
  one at 127, and its null, the same note at 100 per cent, is not;
- the default moved: a setup without the field and one at 100 per cent are
  the same to the bit, and the null, 99 per cent, is not, so the comparison
  can see a change of one per cent;
- the amplifier caught up in it: with the filter off the field changes
  nothing at all, while the null shows the amplifier does follow velocity;
- the upper hand's own value lost: in a split, the upper hand's at nought
  opens its soft note while the lower hand's at 100 per cent leaves its own
  soft note dark.

Measured as the energy above 5 kHz, as a share of the whole, in the first
20 ms of the note (the sweep at its height) - a saw at 2 kHz, Attack 0,
Decay 300 ms, Sustain 0.
"""
import base64, json, os
import numpy as np

RATE = 48000
SAW = {"shape": "ramp", "midiMode": "poly", "pictureAmount": 0, "vcfType": 1, "vcfCut": 667, "vcfTrack": 0,
       "vcfEnvAmt": 33, "vcfAtk": 0, "vcfDec": 300, "vcfSus": 0, "vcfRel": 1}


def code(setup):
    return base64.b64encode(json.dumps(dict({"v": 13}, **setup)).encode()).decode().rstrip("=")


def run(kit):
    check, null = kit.check, kit.null
    where = os.path.join(os.path.dirname(kit.build("render_cpp")), "vcfvel.heard")

    def heard(setup, note=48, vel=100):
        kit.render([["make", RATE, code(setup)], ["record", "heard", where], ["to", 0.2], ["midi", 0x90, note, vel],
                    ["to", 0.9], ["midi", 0x80, note, 0], ["to", 1.0], ["record", "heard"]], raw=True)
        return np.fromfile(where, dtype=np.float32).reshape(-1, 2)

    def bright(x, at=0.2):
        seg = x[int(at * RATE):int((at + 0.02) * RATE), 0].astype(float)
        sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
        f = np.fft.rfftfreq(len(seg), 1 / RATE)
        return 10 * np.log10(sp[f > 5000].sum() / sp.sum() + 1e-20)

    hard = bright(heard(dict(SAW, vcfVel=0), vel=127))
    soft0 = bright(heard(dict(SAW, vcfVel=0), vel=20))
    soft100 = bright(heard(dict(SAW, vcfVel=100), vel=20))
    check("at Velocity nought a note struck at 20 sweeps as a note at 127 does, to a decibel above 5 kHz",
          abs(soft0 - hard) < 1, "%.2f dB against %.2f" % (soft0, hard))
    null("at 100 per cent the same soft note is more than 8 dB darker: the knob is what opened it",
         soft100 < hard - 8, "%.2f dB against %.2f" % (soft100, hard))
    half = bright(heard(dict(SAW, vcfVel=50), vel=20))
    check("and half-way it is between the two", soft100 + 1 < half < soft0 - 1, "%.2f between %.2f and %.2f" % (half, soft100, soft0))

    plain = heard(SAW, vel=64)
    same = float(np.abs(heard(dict(SAW, vcfVel=100), vel=64) - plain).max())
    check("at 100 per cent, the default, the sound is the old law's to the bit: no field and 100 the same",
          same == 0, "largest difference %g" % same)
    off = float(np.abs(heard(dict(SAW, vcfVel=99), vel=64) - plain).max())
    null("and 99 per cent is not, so the comparison sees a step of one", off > 1e-6, "largest difference %g" % off)

    dry = dict(SAW, vcfType=0)
    amp = float(np.abs(heard(dict(dry, vcfVel=0), vel=40) - heard(dict(dry, vcfVel=100), vel=40)).max())
    check("with the filter off Velocity changes nothing: the amplifier's envelope keeps its velocity", amp == 0,
          "largest difference %g" % amp)
    loud = [float(np.abs(heard(dry, vel=v)).max()) for v in (40, 127)]
    null("while the amplifier does follow velocity, so a velocity lost there would show", loud[0] < 0.6 * loud[1],
         "peaks %.3f at 40, %.3f at 127" % tuple(loud))

    split = dict(SAW, layers="split", splitAt=60, bShape="ramp", bVcf=1, bVcfCut=667, bVcfEnv=33, bVcfAtk=0, bVcfDec=300,
                 bVcfSus=0, bVcfRel=1, bVcfVel=0)
    upper, lower = bright(heard(split, note=72, vel=20)), bright(heard(split, note=48, vel=20))
    upperHard, lowerHard = bright(heard(split, note=72, vel=127)), bright(heard(split, note=48, vel=127))
    check("in a split the upper hand's own Velocity, nought, opens its soft note as far as a hard one",
          abs(upper - upperHard) < 1, "%.2f dB against %.2f" % (upper, upperHard))
    null("and the lower hand's, 100 per cent, leaves its soft note darker: each hand reads its own",
         lower < lowerHard - 8, "%.2f dB against %.2f" % (lower, lowerHard))
