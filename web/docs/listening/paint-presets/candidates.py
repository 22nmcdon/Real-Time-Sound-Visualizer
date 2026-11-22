"""The four candidates: each a setup, a heading it is meant for (measure.py
says whether it is), its two short lines and its description in the bank's
form, the bank preset it is nearest, and the performance it is heard through.

None of these is in the bank. Each is a bank preset's sound or close to one,
with the screen drawing the painting (`screenDraws: "paint"`, a setup field
since painting's step 2) and its own Persistence there (`paintPersistence`,
the painting's half-life in seconds), so the change Paint makes is what is
heard.

A performance is (notes, controller events, length, sections): each note
(start, key, velocity, held), each event (time, MIDI bytes), and the sections
the measures are taken over.
"""

TINE = {"shape": "sine", "freq": 220, "timebase": 3, "midiMode": "poly", "oscRatio": 1, "oscFm": 8,
        "vcfType": 1, "vcfCut": 700, "atk": 1, "dec": 1000, "sus": 25, "rel": 500,
        "mod": "env.note>gen.fm@0.400;midi.key>gen.fm@0.300",
        "display": "xy", "persistence": "0.3", "oscScan": 50, "scanStrike": 100, "pictureAmount": 0}
SLOWPAD = {"shape": "ramp", "freq": 220, "timebase": 3, "midiMode": "poly", "amp": 28, "vcfType": 1, "vcfCut": 560,
           "vcfRes": 15, "atk": 200, "dec": 800, "sus": 80, "rel": 1500,
           "display": "xy", "persistence": "0.12", "oscScan": 60, "scanStrike": 40, "pictureAmount": 100}
ORGAN = {"shape": "drawbars", "bars": "888000000", "freq": 220, "timebase": 6, "midiMode": "poly",
         "atk": 2, "dec": 120, "sus": 100, "rel": 80,
         "display": "xy", "persistence": "0.3", "oscScan": 14, "scanStrike": 100, "pictureAmount": 0}


def ramp(t0, t1, v0, v1, make, every=0.04):
    """A controller moved from v0 to v1 (nought to one) between t0 and t1, a message every 40 ms, as a hand sends them."""
    steps = max(1, int(round((t1 - t0) / every)))
    return [(t0 + (t1 - t0) * k / steps, make(v0 + (v1 - v0) * k / steps)) for k in range(steps + 1)]


def wheel(v): return [0xB0, 1, int(round(127 * v))]


def bend(v):
    raw = max(0, min(16383, 8192 + int(round(v * (8191 if v >= 0 else 8192)))))
    return [0xE0, raw & 127, raw >> 7]


def phrase_three_times():
    """A phrase one turn of the canvas long (eight seconds, half a second a note), played three times, so each pass
    lands on the paint the last one left in the same place: the ring a note reads holds the last turn of its
    register."""
    line = (57, 60, 64, 69, 67, 64, 60, 62, 64, 60, 57, 55, 57, 60, 64, 57)
    notes = [(0.3 + 8 * k + 0.5 * i, n, 84, 0.42) for k in range(3) for i, n in enumerate(line)]
    return notes, [], 26.0, [("first pass", 0.3, 8.3), ("second", 8.3, 16.3), ("third", 16.3, 24.3)]


def one_chord_four_times():
    """One chord, A minor, held four and a half seconds three times over, a rest while the paint dries, and again.
    The same notes each time, so any difference between the plays is what they landed on: the turn is eight seconds,
    so each play starts five eighths of the way round from the last and lays over part of its arcs. The sections
    leave out each chord's first half second, its attack."""
    notes = []
    for t in (0.3, 5.3, 10.3, 20.3): notes += [(t, n, 80, 4.6) for n in (57, 60, 64)]
    return notes, [], 26.5, [("first", 0.8, 4.9), ("second", 5.8, 9.9), ("third", 10.8, 14.9), ("after the rest", 20.8, 24.9)]


def wheel_and_bends():
    """A fifth held with the mod wheel brought up from rest (loading the brush), a quick bend up and back, a slow
    bend down and back, the wheel let down, and the fifth struck again plain over what was painted."""
    notes = [(0.3, 57, 90, 13.5), (0.3, 64, 90, 13.5), (15.0, 57, 90, 5.0), (15.0, 64, 90, 5.0)]
    ev = ([(0.1, [0xB0, 1, 0])] + ramp(2.0, 4.0, 0, 1, wheel) + ramp(6.0, 6.3, 0, 1, bend) + ramp(7.6, 7.9, 1, 0, bend)
          + ramp(9.0, 10.0, 0, -1, bend) + ramp(11.0, 12.0, -1, 0, bend) + ramp(12.2, 13.0, 1, 0, wheel))
    return notes, ev, 22.0, [("plain", 0.3, 2.0), ("wheel up", 4.0, 6.0), ("quick bend", 6.0, 9.0), ("slow bend", 9.0, 12.2),
                             ("struck again, plain", 15.0, 20.0)]


def soft_hard_soft():
    """A phrase played softly, then with every other note struck hard (the drops fly), then softly again, so the
    soft notes of the last pass read what the hard ones threw into their registers."""
    line = (60, 64, 67, 72, 71, 67, 64, 62)
    notes = []
    for k, vel in enumerate(((50,) * 8, (50, 127) * 4, (50,) * 8)):
        notes += [(0.3 + 4.5 * k + 0.5 * i, n, vel[i], 0.4) for i, n in enumerate(line)]
    return notes, [], 15.5, [("soft", 0.3, 4.3), ("with hard strikes", 4.8, 8.8), ("soft again", 9.3, 13.3)]


ALL = {
    "Tines in wet paint": {
        "aim": "Settled",
        "setup": dict(TINE, screenDraws="paint", oscScan=70, paintPersistence=32),
        "nearest": "Tine piano",
        "play": phrase_three_times, "moments": (8.3, 16.3, 24.3),
        "lines": ("The phrase rings brighter once it comes round", "Each pass laid over the last one's drying strokes"),
        "about": "The tine piano, painting. Each note reads the ring at its own pitch, which holds the last turn of "
                 "everything played in its register, so a phrase played again reads the paint its last pass left "
                 "and rings brighter the second time round than on a bare canvas; a held chord still settles.",
    },
    "Drying pad": {
        "aim": "Breathing",
        "setup": dict(SLOWPAD, screenDraws="paint", paintPersistence=8),
        "nearest": "Slow pad",
        "play": one_chord_four_times, "moments": (4.9, 9.9, 14.9, 24.9),
        "lines": ("The same chord comes back changed each time", "Each chord laid over the last one's drying arcs"),
        "about": "The slow pad, painting, with a short memory. Each note reads the paint in its own register, so a "
                 "chord played again plays whatever the last one left where it lands, wet or dry, and never comes back "
                 "the same; held, its arc comes round to meet itself and it keeps moving until you let go. Rest, and the "
                 "paint dries and fades, eight seconds to half.",
    },
    "Palette knife organ": {
        "aim": "Breathing",
        "setup": dict(ORGAN, screenDraws="paint", oscScan=40, wheelTo="off", bendRange=5, paintPersistence=24),
        "nearest": "Drawbar organ",
        "play": wheel_and_bends, "moments": (5.9, 12.2, 20.0),
        "lines": ("The wheel and the bends leave the fifth changed", "A loaded stroke, and a slab pushed by the bend"),
        "about": "The drawbar organ, painting, with the mod wheel given to the brush alone and the bend at a fourth. "
                 "Bring the wheel up and the brush loads, laying a wider, heavier stroke that Scan hears; bend away "
                 "and the palette knife pushes the wet paint aside, so the same fifth struck again afterwards plays a "
                 "changed ring.",
    },
    "Spattered mallets": {
        "aim": "Settled",
        "setup": {"shape": "sine", "freq": 220, "timebase": 3, "midiMode": "poly", "oscRatio": 4, "oscFm": 12,
                  "atk": 1, "dec": 700, "sus": 15, "rel": 400, "mod": "env.note>gen.fm@0.500",
                  "display": "xy", "persistence": "0.3", "oscScan": 70, "scanStrike": 100, "pictureAmount": 0,
                  "screenDraws": "paint", "paintPersistence": 40},
        "nearest": "Tine piano",
        "play": soft_hard_soft, "moments": (4.3, 8.8, 13.3),
        "lines": ("A glassy mallet that rings out brighter struck hard", "Hard strikes splash blots and throw drops"),
        "about": "A struck sine with its FM at four to one, painting at full Strike. A hard note lays a heavy blot that "
                 "Scan reads brightly and throws drops of paint across the canvas; a soft phrase lays thin strokes and "
                 "leaves it clean. The painting keeps the record for forty seconds to half. A held note settles.",
    },
}

BANK = sorted({c["nearest"] for c in ALL.values()})
