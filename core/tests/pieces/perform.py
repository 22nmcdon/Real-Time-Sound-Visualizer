"""The presets for playing, played on the core: every routing in the old
library's keyboard sections reaches the generator, is still at rest and
moves when a hand plays, and every split and layer sounds both layers -
performtest.py's numbers rows.

These were performtest.py's on `?brain=js` until stage 5, step 3, batch 4
(13 Nov): there each preset was loaded on the page, a stubbed port played a
chord under the pedal with the wheel up, and the page's own `MOD_SOURCES`
values, its compiled `genRoutes` and its keyboard's `midi.poly.layers` were
read. On the default site each of those is the face's, beside the
instrument. Here the instrument whole (instrument_cpp): the corpus setup
loaded as a code of its own version (7, so the decode passes since run, as
loadCorpus runs them), the same chord, pedal and wheel as MIDI, and its
matrix's own routings read back by the `routed` command - the source
registered, its value, the routes on its destination's slot - and each
layer's voices by `tone`. The corpus is core/tests/scenarios/library-p8f.json,
which web/tests/corpus.py reads too. Each check has its null.
"""
import base64, json, os, re

KEYBOARD = ["Poly keys", "Chords drawn", "Arpeggios", "Split", "Layer", "Hands on the sound", "Many sources"]
CHORD = [36, 48, 60, 64, 67, 72, 84]
# The sources F4b cut (version 9's decode pass drops their routings): the
# page's CUT_SOURCE, which the core's setup.h restates.
CUT = re.compile(r"^(cc\.\d+|midi\.pedal|midi\.pressure|notes\.(count|spread|top|inner)|env\.live)>")


def library():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "scenarios", "library-p8f.json"), encoding="utf-8") as f:
        return json.load(f)


def code(setup):
    return base64.b64encode(json.dumps(dict(setup, v=7)).encode()).decode().rstrip("=")


def run(kit):
    check, null = kit.check, kit.null

    def routings(line):
        w = line.split()[1:]
        return [{"id": w[i], "known": w[i + 1] == "1", "value": float(w[i + 2]), "routes": w[i + 3]} for i in range(0, len(w), 4)]

    def play(setup, mod=None):
        """At rest, then the chord struck hard under the pedal with the wheel
        up, a quarter of a second on: the routings at each, and the voices."""
        lines = [["make", 48000, 128, code(setup)]]
        if mod is not None: lines.append(["routings", mod])
        lines += [["block", 4800, 100000]] * 4 + [["routed"]]
        lines += [["midi", 0xB0, 1, 127], ["midi", 0xB0, 64, 127]] + [["midi", 0x90, n, 120] for n in CHORD]
        lines += [["block", 4000, 100000]] * 3 + [["routed"], ["tone"]]
        out = [l for l in kit.instrument(lines) if l.startswith("routed") or l.startswith("tone ")]
        rest, moved, tone = routings(out[0]), routings(out[1]), out[2].split()
        a, b, e = tone.index("A"), tone.index("B"), tone.index("env")
        return {"rest": rest, "moved": moved, "layers": [len(tone[a + 1:b]), len(tone[b + 1:e])]}

    def dead(row):
        return [(m["id"], r["value"], m["value"], m["routes"]) for r, m in zip(row["rest"], row["moved"])
                if not (m["known"] and m["routes"] not in ("-", "0") and abs(r["value"]) < 0.05 and abs(m["value"]) > 0.3)]

    played, emptied, unrouted = [], [], []
    for name in KEYBOARD:
        section = next(s for s in library() if s[0] == name)
        for preset, setup, _ in section[1]:
            parts = [p.strip() for p in (setup.get("mod") or "").split(";") if p.strip()]
            all_cut = bool(parts) and all(CUT.match(p) for p in parts)
            row = dict(play(setup), preset=preset, split=setup.get("layers"), all_cut=all_cut)
            played.append(row)
            if all_cut: emptied.append((preset, len(row["moved"])))
            elif not row["moved"]: unrouted.append(preset)
    bad = [d for row in played for d in dead(row)]
    check("every routing in the keyboard's presets reaches the instrument's generator, is still at rest, and moves when played",
          len(played) >= 15 and bad == [] and unrouted == [], "%d presets; %s" % (len(played), (bad or unrouted)[:4]))
    check("and those whose every routing came from a cut source load with none",
          len(emptied) >= 1 and all(n == 0 for _, n in emptied), str(emptied))

    # The null, through the same measurement: a source spelt wrong is kept
    # by the matrix, never registered and never moves.
    chords = next(s for s in library() if s[0] == "Chords drawn")[1][0][1]
    wrong = play(chords, "notes.cont>gen.vcf@-0.600")
    null("a source spelt wrong is caught by the same measurement", dead(wrong) != [], str(dead(wrong)))
    still = play(chords, "lfo1>gen.vcf@-0.600")
    null("and an oscillator, which moves at rest, is caught too", dead(still) != [], str(dead(still)))

    splits = [r for r in played if r["split"]]
    uneven = [(r["preset"], r["layers"]) for r in splits if not (r["layers"][0] > 0 and r["layers"][1] > 0)]
    check("each split and layer sounds both layers from one chord across the keyboard",
          len(splits) >= 5 and uneven == [], str(uneven or [(r["preset"], r["layers"]) for r in splits]))
    flat = [r for r in played if not r["split"]]
    null("and a preset with no layers sounds one", all(r["layers"][1] == 0 for r in flat) and flat, str([r["layers"] for r in flat][:4]))
