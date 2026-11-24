"""Six starter presets for the first release: each a setup, the heading it is
meant for (measure.py says whether it is), its two short lines and its
description in the bank's form, and the performance it is heard through.

None of these is in the bank. They are meant to differ from each other and
from the bank as it stands (nine presets, most of them FM sines, filtered saws
and the picture at full), so: one clean and warm, one plucked, one evolving
pad, one bass, one for two hands, one that shows the filter's envelope with
Velocity. Each uses the rack and the EQ where the sound wants them, never all
of it at once, and none draws Paint (the stable site holds it back), so each
is on the trace, X-Y, as the bank is.

A performance is (notes, controller events, length, sections, moments): each
note (start, key, velocity, held), each event (time, MIDI bytes), the sections
the heard measures are taken over, and the moments the screen is pictured at.
"""

# Each knob's place on the cutoff's law, 20 Hz to 20 kHz over 0 to 1000 (the voice filter's and the EQ's).
import math


def place(hz): return round(1000 * math.log(hz / 20) / math.log(1000))


ALL = {
    "Felt piano": {
        "aim": "Settled",
        "setup": {"shape": "triangle", "freq": 220, "timebase": 3, "midiMode": "poly", "amp": 50,
                  "vcfType": 1, "vcfCut": place(900), "vcfTrack": 60, "vcfEnvAmt": 12, "vcfAtk": 0, "vcfDec": 900,
                  "vcfSus": 10, "vcfRel": 400, "vcfVel": 70,
                  "atk": 2, "dec": 1800, "sus": 30, "rel": 700,
                  "chorusMix": 12, "chorusRate": 20, "chorusDepth": 15,
                  "eqOn": True, "eqLow": 30, "eqLowFreq": place(180), "eqHigh": -50, "eqHighFreq": place(5000),
                  "eqCutLowOn": True, "eqCutLowFreq": place(45),
                  "display": "xy", "persistence": "0.3", "oscScan": 22, "scanStrike": 70, "pictureAmount": 0},
        "lines": ("A soft, round piano tone, brighter the harder you play",
                  "A rounded ring that brightens as a key lands"),
        "about": "A triangle through a gentle low pass that opens a little on each key, more the harder it is "
                 "played, with a touch of chorus, a warm low shelf and the top rolled off: a felted piano with "
                 "no grit in it. A little of its wave is read off its own figure, so each key brightens the "
                 "tone for a moment as it strikes the screen, and a held chord comes to rest.",
    },
    "Plucked wire": {
        "aim": "Settled",
        "setup": {"shape": "pulse", "width": 30, "freq": 220, "timebase": 3, "midiMode": "poly", "amp": 55,
                  "vcfType": 1, "vcfCut": place(260), "vcfRes": 30, "vcfTrack": 50, "vcfEnvAmt": 34, "vcfAtk": 0,
                  "vcfDec": 160, "vcfSus": 0, "vcfRel": 200, "vcfVel": 45,
                  "atk": 1, "dec": 600, "sus": 8, "rel": 300,
                  "delayMix": 24, "delaySync": "1/8d", "delayFeedback": 32, "delayPingPong": True, "delayTone": 55,
                  "delayLowCut": 30, "bpm": 100,
                  "eqOn": True, "eqCutLowOn": True, "eqCutLowFreq": place(120), "eqMid": 25, "eqMidFreq": place(2200),
                  "display": "xy", "persistence": "0.3", "oscScan": 35, "scanStrike": 100, "pictureAmount": 0},
        "lines": ("A bright pluck that rings off into its echoes",
                  "Each pluck flashes on the figure, then fades"),
        "about": "A narrow pulse plucked through a resonant low pass whose own envelope snaps shut in a fifth of "
                 "a second, so every note is a pluck rather than a tone, with a dotted-eighth echo thrown from "
                 "side to side. Every key strikes the figure where Scan reads it, so the pluck flares as it lands "
                 "and settles as it dies.",
    },
    "Tidal glass": {
        "aim": "Breathing",
        "setup": {"shape": "wavetable", "table": 170, "freq": 220, "timebase": 3, "midiMode": "poly", "amp": 30,
                  "vcfType": 1, "vcfCut": place(1800), "vcfRes": 10,
                  "atk": 700, "dec": 1200, "sus": 85, "rel": 1300,
                  "phaserMix": 30, "phaserRate": 12, "phaserDepth": 60, "phaserFeedback": 35,
                  "reverbMix": 22, "reverbSize": 55, "reverbTone": 50, "reverbSpread": 40,
                  "eqOn": True, "eqCutLowOn": True, "eqCutLowFreq": place(90), "eqHigh": 30, "eqHighFreq": place(6000),
                  "display": "xy", "persistence": "0.12", "oscScan": 55, "scanStrike": 30, "pictureAmount": 80,
                  "pictureSwell": True},
        "lines": ("A glassy pad that swells and turns while held",
                  "The figure folding slowly in and out of itself"),
        "about": "A wavetable pad that swells in over most of a second, through a slow phaser and a little "
                 "reverb, bright at the top. Most of its wave is read off its own figure, and the picture, with "
                 "its Swell on, pushes the figure as it repeats, so a held chord keeps turning over, slowly, until "
                 "you let go.",
    },
    "Round bass": {
        "aim": "Settled",
        "setup": {"shape": "square", "freq": 110, "timebase": 5, "midiMode": "mono", "glide": 40, "midiRetrig": True,
                  "amp": 55, "oscSub": 45, "oscSubOct": 1, "oscSubShape": "sine",
                  "vcfType": 1, "vcfCut": place(220), "vcfRes": 25, "vcfTrack": 30, "vcfEnvAmt": 22, "vcfAtk": 0,
                  "vcfDec": 260, "vcfSus": 15, "vcfRel": 150, "vcfVel": 60,
                  "atk": 2, "dec": 700, "sus": 70, "rel": 120,
                  "eqOn": True, "eqCutLowOn": True, "eqCutLowFreq": place(32), "eqLow": 25, "eqLowFreq": place(90),
                  "eqMid": -30, "eqMidFreq": place(350), "eqMidWidth": 14,
                  "display": "xy", "persistence": "0.3", "oscScan": 25, "scanStrike": 80, "pictureAmount": 0},
        "lines": ("A round mono bass with a soft bite on each note",
                  "A low figure that kicks as each note lands"),
        "about": "One voice at a time, gliding between notes: a square with a sine an octave under it, through a "
                 "low pass that bites on each note and closes to a round tone, the low end lifted and the boxy "
                 "middle taken out. A little of its wave is read off its own figure, so each note kicks as it "
                 "lands and then holds still.",
    },
    "Mirrored hands": {
        "aim": "Breathing",
        "setup": {"shape": "sine", "freq": 220, "timebase": 3, "midiMode": "poly", "amp": 40,
                  "layers": "layer", "layerPair": "each",
                  "oscRatio": 2, "oscFm": 10, "bShape": "triangle", "bAmp": 30,
                  "atk": 40, "dec": 900, "sus": 70, "rel": 700, "bAtk": 120, "bDec": 900, "bSus": 80, "bRel": 900,
                  "oscScan": 60, "scanReadsA": "B", "scanReadsB": "A",
                  "pictureMovesA": "B", "pictureMovesB": "A", "pictureAmount": 60,
                  "chorusMix": 18, "chorusRate": 25,
                  "display": "xy", "persistence": "0.12", "scanStrike": 50},
        "lines": ("Two voices on every key, each reshaping the other",
                  "Two figures, each the other's wave, never still"),
        "about": "Two hands layered, so every key plays both: an FM sine and a softer triangle that swells in "
                 "behind it. Each hand's wave is read off the other hand's figure and moved by the other's "
                 "picture, so neither can sound without the other answering, and a held chord goes on changing "
                 "between them until you let go.",
    },
    "Velocity brass": {
        "aim": "Settled",
        "setup": {"shape": "ramp", "freq": 220, "timebase": 3, "midiMode": "poly", "amp": 45,
                  "vcfType": 1, "vcfCut": place(320), "vcfRes": 18, "vcfTrack": 50, "vcfEnvAmt": 34, "vcfAtk": 70,
                  "vcfDec": 600, "vcfSus": 35, "vcfRel": 300, "vcfVel": 100,
                  "atk": 25, "dec": 500, "sus": 80, "rel": 260,
                  "reverbMix": 12, "reverbSize": 35,
                  "eqOn": True, "eqMid": 25, "eqMidFreq": place(1400), "eqCutHighOn": True, "eqCutHighFreq": place(9000),
                  "display": "xy", "persistence": "0.3", "oscScan": 20, "scanStrike": 60, "pictureAmount": 0},
        "lines": ("Soft notes mellow, hard notes blare open",
                  "The figure flares wider the harder you play"),
        "about": "A pair of saws through a low pass whose own envelope sweeps up three and a half octaves and "
                 "back, and all of that sweep follows the key: played softly it is a mellow horn, played hard it "
                 "blares. A little of its wave is read off its own figure, so the strike flares with the sweep, "
                 "and a held chord settles as the filter does.",
    },
}


# --- the performances ---------------------------------------------------------

def chords(seq, vel=86, start=0.3):
    """(duration, notes) a chord at a time, back to back."""
    out, t = [], start
    for d, ns in seq:
        out += [(t, n, vel, d * 0.95) for n in ns]
        t += d
    return out, t


def felt():
    # A slow progression in C, a held chord at the end to hear it come to rest.
    notes, t = chords([(1.5, (48, 60, 64, 67)), (1.5, (45, 57, 60, 64)), (1.5, (41, 57, 60, 65)), (1.5, (43, 55, 62, 67))])
    notes += [(t + 0.5 * i, n, v, 0.45) for i, (n, v) in enumerate(((72, 50), (71, 70), (67, 90), (64, 110)))]
    notes += [(t + 2.3, n, 80, 4.5) for n in (48, 55, 64, 67, 72)]
    return notes, [], t + 7.6, [("progression", 0.3, t), ("soft to hard", t, t + 2.2), ("held chord", t + 2.8, t + 6.8)], \
        (2.0, t + 1.6, t + 3.0, t + 6.5)


def pluck():
    # A sixteenth-note figure at 100 bpm, accented, then a held note.
    line = (57, 64, 69, 64, 72, 69, 64, 69, 55, 62, 67, 62, 71, 67, 62, 67)
    step = 60 / 100 / 4 * 1.0
    notes = [(0.3 + step * 2 * i, n, 110 if i % 4 == 0 else 72, step * 1.6) for i, n in enumerate(line)]
    t = 0.3 + step * 2 * len(line)
    notes += [(t + 0.3, 57, 100, 3.0)]
    return notes, [], t + 4.8, [("figure", 0.3, t), ("held note", t + 0.6, t + 3.3)], (1.2, 3.0, t + 0.5, t + 2.8)


def pad():
    # Two chords held long, a rest, and one again: does it keep moving while held, and stop when let go.
    notes = [(0.3, n, 80, 7.5) for n in (57, 60, 64, 71)] + [(8.0, n, 80, 7.0) for n in (53, 57, 60, 67)]
    return notes, [], 18.5, [("first chord", 1.5, 7.8), ("second chord", 9.2, 15.0), ("let go", 15.6, 18.3)], \
        (3.0, 7.5, 12.0, 14.8)


def bass():
    # A bass line, gliding where notes overlap, then a held low note.
    line = [(0.3, 33, 100, 0.4), (0.75, 33, 70, 0.2), (1.0, 45, 90, 0.35), (1.5, 43, 90, 0.5), (1.95, 40, 80, 0.4),
            (2.4, 38, 100, 0.4), (2.85, 38, 70, 0.2), (3.1, 50, 90, 0.35), (3.6, 48, 90, 0.5), (4.05, 45, 80, 0.4)]
    line += [(4.5 + s, n, v, d) for s, n, v, d in [(0, 41, 100, 0.5), (0.45, 43, 90, 0.6), (1.0, 45, 110, 3.5)]]
    return line, [], 9.8, [("line", 0.3, 5.4), ("held note", 5.8, 8.9)], (1.1, 3.2, 5.7, 8.8)


def mirrored():
    # Notes alone and then together: a held chord, a melody over a held fifth.
    notes = [(0.3, n, 85, 6.0) for n in (57, 64, 72)]
    notes += [(7.0, 48, 80, 7.0), (7.0, 55, 80, 7.0)]
    notes += [(7.6 + 0.6 * i, n, 90, 0.5) for i, n in enumerate((67, 69, 72, 74, 76, 74, 72, 69, 67))]
    return notes, [], 16.5, [("held chord", 1.0, 6.2), ("melody over a fifth", 7.6, 13.0), ("let go", 14.4, 16.3)], \
        (2.0, 6.0, 9.5, 13.0)


def brass():
    # The same stab at rising velocity, then a held chord played softly and one played hard.
    notes = []
    for i, v in enumerate((35, 60, 85, 110, 127)):
        notes += [(0.3 + 0.8 * i, n, v, 0.55) for n in (55, 60, 64)]
    t = 0.3 + 0.8 * 5 + 0.3
    notes += [(t, n, 45, 2.6) for n in (53, 57, 60, 65)] + [(t + 3.2, n, 120, 2.6) for n in (53, 57, 60, 65)]
    stabs = [("stab at %d" % v, 0.3 + 0.8 * i, 0.3 + 0.8 * i + 0.5) for i, v in enumerate((35, 60, 85, 110, 127))]
    return notes, [], t + 6.6, stabs + [("soft chord", t + 0.2, t + 2.6), ("hard chord", t + 3.4, t + 5.8)], \
        (1.0, 3.5, t + 1.2, t + 3.6)


PLAYS = {"Felt piano": felt, "Plucked wire": pluck, "Tidal glass": pad, "Round bass": bass, "Mirrored hands": mirrored,
         "Velocity brass": brass}
for _n, _f in PLAYS.items(): ALL[_n]["play"] = _f


# What each performance is, in words, for the page.
PLAYED = {
    "Felt piano": "C, A minor, F and G, a second and a half each; four single notes rising from soft (50) to hard "
                  "(110); then C held over two octaves for four and a half seconds.",
    "Plucked wire": "An arpeggio in A minor and G, a sixteenth note at a time at 100 bpm with an accent on every "
                    "fourth, into its dotted-eighth echoes; then A3 held three seconds.",
    "Tidal glass": "A minor with a seventh held seven and a half seconds, F major with a seventh seven, and then let "
                   "go, so its tail and its stillness after are heard.",
    "Round bass": "A bass line in A, an octave jump and a few passing notes, played with some notes overlapping so "
                  "the glide shows; then a held A2.",
    "Mirrored hands": "A minor held six seconds, then a fifth held under a short melody, then let go.",
    "Velocity brass": "One chord (G, C, E) struck five times at velocities 35, 60, 85, 110 and 127; then F major held "
                      "soft (45) and the same held hard (120).",
}

# Which controls to try turning first, for the owner's ear.
TRY = {
    "Felt piano": "Scan and Strike in the Picture strip are how much the figure answers each key; at Scan 22 it is a "
                  "touch; turn them up for a strike you can hear on every key. The Filter figure's Velocity "
                  "and Amount set how much a hard key opens the tone. The EQ's high band (Space & Memory) is the "
                  "felt itself: lift it towards nought for a brighter, harder piano.",
    "Plucked wire": "The Filter figure's Decay is the length of the pluck (160 ms: shorter "
                    "is a click, longer a stab); Resonance its twang. The Delay's Mix and Feedback are the room it rings into, "
                    "synced to the tempo in Perform. Strike in the Picture strip is how hard each pluck flashes on "
                    "the figure and in the tone.",
    "Tidal glass": "The Picture amount is how far the figure pushes the sound while held: lower it and the pad "
                   "calms, at nought it holds still. The Wave figure's Position picks the glass from the wavetable. "
                   "The Phaser's Rate and the Reverb's Mix set how wide the tide is.",
    "Round bass": "Glide in the Generator is the slide between overlapping notes. The Filter figure's Amount and "
                  "Decay are the bite; Resonance gives it a rubbery edge. The Oscillator's Sub (Ink) is the weight "
                  "under it. The EQ's mid cut at 350 Hz keeps it out of a mix's way; pull it back to nought for a "
                  "boxier bass.",
    "Mirrored hands": "Scan reads the other hand's figure here, so turning it up makes the two hands argue harder. "
                      "Edit one hand at a time from the header's A and B: B, the "
                      "triangle, swells in behind A. The Picture amount is how much each hand's picture moves the other's "
                      "sound; at nought the two settle.",
    "Velocity brass": "Play it from a keyboard with velocity: soft notes are a mellow horn, hard ones blare. The "
                      "Filter figure's Velocity knob is how much of the sweep follows the key (at nought every note "
                      "blares alike); Amount is the size of the sweep and Attack how slowly it opens. The EQ's "
                      "mid band at 1.4 kHz is its brassiness.",
}
