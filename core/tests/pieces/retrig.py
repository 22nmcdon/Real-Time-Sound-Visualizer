"""Dyad's and Mono's Retrigger (23 Nov, the owner's), on the core's whole
instrument: a note over a held one strikes the amplifier's and the filter's
envelopes again, where the legato rule (Mseg::gate) leaves them alone.

The owner's filter opened on the first note of a phrase and never again,
because each next key went down before the last came up. Off, the default,
is that legato to the bit, so a saved sound plays as it did. What would go
wrong, and what is checked for it:

- the switch read and ignored: with it on, a second note over a held one is
  as bright at its start as the first was (energy above 5 kHz in 20 ms, a saw
  at 2 kHz swept +3.3 octaves); the null is the same phrase with it off, whose
  second note starts dark;
- only the filter struck again: with it on the amplifier's envelope starts
  again too (a decay to a low sustain climbs back to its peak), and off it
  does not;
- Poly changed: it already strikes each note's own envelopes, and the switch
  does nothing there, to the bit;
- the default moved: off and no field are the same to the bit.
"""
import base64, json, os
import numpy as np

RATE = 48000
SAW = {"shape": "ramp", "pictureAmount": 0, "vcfType": 1, "vcfCut": 667, "vcfTrack": 0, "vcfEnvAmt": 33, "vcfAtk": 0,
       "vcfDec": 200, "vcfSus": 0, "vcfRel": 1, "atk": 1, "dec": 150, "sus": 20, "rel": 50}
SECOND = 0.6


def code(setup):
    return base64.b64encode(json.dumps(dict({"v": 13}, **setup)).encode()).decode().rstrip("=")


def run(kit):
    check, null = kit.check, kit.null
    where = os.path.join(os.path.dirname(kit.build("render_cpp")), "retrig.heard")

    def phrase(setup):
        """A held C3, and a G3 over it at SECOND, C3 let go just after: the second note legato."""
        kit.render([["make", RATE, code(setup)], ["record", "heard", where], ["to", 0.2], ["midi", 0x90, 48, 100],
                    ["to", SECOND], ["midi", 0x90, 55, 100], ["to", SECOND + 0.05], ["midi", 0x80, 48, 0],
                    ["to", SECOND + 0.5], ["midi", 0x80, 55, 0], ["to", SECOND + 0.6], ["record", "heard"]], raw=True)
        return np.fromfile(where, dtype=np.float32).reshape(-1, 2)

    def bright(x, at):
        seg = x[int(at * RATE):int((at + 0.02) * RATE), 0].astype(float)
        sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
        f = np.fft.rfftfreq(len(seg), 1 / RATE)
        return 10 * np.log10(sp[f > 5000].sum() / sp.sum() + 1e-20)

    def rms(x, at, dur=0.01):
        seg = x[int(at * RATE):int((at + dur) * RATE), 0].astype(float)
        return float(np.sqrt((seg ** 2).mean()))

    for mode in ("mono", "dyad"):
        on, off = phrase(dict(SAW, midiMode=mode, midiRetrig=True)), phrase(dict(SAW, midiMode=mode))
        first, second, legato = bright(on, 0.202), bright(on, SECOND + 0.002), bright(off, SECOND + 0.002)
        # At least as bright: the second note is a fifth higher, so a little brighter, and both are measured as they start.
        check("%s, Retrigger on: a note over a held one opens the filter at least as far as the first did, to 2 dB above 5 kHz" % mode,
              second > first - 2, "second %.2f dB, first %.2f" % (second, first))
        null("%s, Retrigger off: the same note starts dark, at least 10 dB down - the legato it always was" % mode,
             legato < first - 10, "%.2f dB against %.2f" % (legato, first))
        # The amplifier: by SECOND the first note has decayed to its sustain of 0.2; struck again it climbs to its peak.
        before, after, after_off = rms(on, SECOND - 0.02), rms(on, SECOND + 0.003), rms(off, SECOND + 0.003)
        check("%s, and the amplifier's envelope is struck again too: louder just after the second key than at sustain" % mode,
              after > 2 * before, "%.4f after, %.4f before" % (after, before))
        null("%s, and off it stays at the sustain" % mode, after_off < 1.3 * before, "%.4f against %.4f" % (after_off, before))

    poly = float(np.abs(phrase(dict(SAW, midiMode="poly", midiRetrig=True)) - phrase(dict(SAW, midiMode="poly"))).max())
    check("in Poly, where every note has its own envelopes, the switch changes nothing, to the bit", poly == 0, "largest %g" % poly)
    same = float(np.abs(phrase(dict(SAW, midiMode="mono", midiRetrig=False)) - phrase(dict(SAW, midiMode="mono"))).max())
    check("and off is a setup without the field, to the bit", same == 0, "largest %g" % same)
