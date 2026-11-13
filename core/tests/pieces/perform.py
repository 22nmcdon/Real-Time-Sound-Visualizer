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

    microphone(kit)


# --- the microphone through the instrument (performtest :231 to :265), batch 5 ---

def microphone(kit):
    """The Live effects and Listening presets on a microphone, through the
    instrument. On `?brain=js` until batch 5 these put the stub's microphone
    through the page's own effects insert (`state.source.fx`) and asked the
    page's compiler; here render_cpp draws an input through the instrument
    (srcMic, as the site's Mic button sends it): one oscillator, 220 Hz at
    0.8, in one channel, which the instrument takes as a mono input. Each
    preset is loaded over it as a setup, as `loadCorpus` sends one - these
    are display presets, landing on whatever is playing - and held for ten
    and a half seconds: what is drawn, against the input itself at the same
    samples, over the last ten of them, and the last 4410 samples' trough
    and the distance between the lanes, as the page read its window 1.2 s
    on. Ten seconds, not the page's 1.2: the page asked whether its insert
    was in the path; here the samples are asked, and Echoes that come and go
    puts its echo on an oscillator at a tenth of a hertz, which leaves the
    input alone for five seconds in every ten. A preset with no effect in it
    draws the input exactly, the whole time."""
    import numpy as np
    from pieces.kit import BUILD
    check, null = kit.check, kit.null
    rate = 48000
    x = (0.8 * np.sin(2 * np.pi * 220 * np.arange(rate * 140) / rate)).astype("<f4")
    os.makedirs(BUILD, exist_ok=True)
    mic, lanes = os.path.join(BUILD, "perform-mic.f32"), os.path.join(BUILD, "perform-lanes.f32")
    x.tofile(mic)
    names = [n for n, _, _ in next(s for s in library() if s[0] == "Live effects")[1]]
    setups = {n: s for sec in library() for n, s, _ in sec[1]}
    plain = "Playing, waveform"
    base = base64.b64encode(json.dumps({"v": 11, "pictureAmount": 0}).encode()).decode().rstrip("=")
    lines = [["make", rate, base], ["click", "srcMic"], ["input", "file", mic, 1], ["record", "lanes", lanes]]
    HOLD = 10.5
    for i, n in enumerate(names + [plain]):
        lines += [["setup", code(setups[n])], ["to", (i + 1) * HOLD]]
    kit.render(lines)
    drawn = np.fromfile(lanes, "<f4").reshape(-1, 6)
    rows = {}
    for i, n in enumerate(names + [plain]):
        start, end = int(round((i * HOLD + 0.5) * rate)), int(round((i + 1) * HOLD * rate))
        w, given = drawn[start:end], x[start:end].astype(float)
        last = drawn[end - 4410:end]
        rows[n] = {"low": float(last[:, 0].min()), "apart": float(np.max(np.abs(last[:, 0] - last[:, 1]))),
                   "changed": float(max(np.max(np.abs(w[:, 0] - given)), np.max(np.abs(w[:, 1] - given))))}
        print("    %-28s low %.3f, apart %.3f, against the input %.3f" % (n, rows[n]["low"], rows[n]["apart"], rows[n]["changed"]))
    # Your input, kaleidoscope had nothing but the kaleidoscope, cut on 7 Nov,
    # and Your level, swirling nothing but the level on the twist, a source cut
    # in F4b: they load as the plain input now, and are held to that.
    CUT_ONES = ("Your input, kaleidoscope", "Your level, swirling")
    kept = [n for n in names if n not in CUT_ONES]
    check("every live-effects preset puts a microphone through the instrument's effects: what is drawn is not the input",
          len(kept) >= 10 and all(rows[n]["changed"] > 0.01 for n in kept) and rows[plain]["changed"] == 0,
          str([(n, round(rows[n]["changed"], 3)) for n in kept]))
    null("the plain display preset draws the input to the bit", rows[plain]["changed"] == 0 and rows[plain]["apart"] == 0)
    check("and the two whose only effect was cut leave the input alone", all(rows[n]["changed"] == 0 for n in CUT_ONES),
          str([(n, rows[n]["changed"]) for n in CUT_ONES]))
    null("which a preset with an effect does not", rows["Twisted input"]["changed"] > 0.01)
    octave = rows["Octave up, on your input"]
    check("the octave-up folds the input's troughs up", octave["low"] > -0.02 and rows[plain]["apart"] < 1e-3, str(octave))
    null("the plain input's troughs are not folded", rows[plain]["low"] < -0.7, "%.3f" % rows[plain]["low"])

    # Listening: every routing from a source that hears, live on a microphone
    # and no loop - on the page asked of its registry's `family` and
    # `fromPicture`; here the instrument's matrix (`loopof`): the source
    # registered, not the picture's while it hears the input, and its
    # destination one the instrument has. The null: the same presets with the
    # generator drawn, where a hearing source hears the instrument's own sound
    # and is the loop's.
    listening = [n for n, _, _ in next(s for s in library() if s[0] == "Listening")[1]]
    def heard(drawn_from):
        out = []
        for n in listening:
            got = kit.render([["make", rate, code(setups[n])], ["click", drawn_from], ["input", "file", mic, 1], ["to", 0.3], ["read", "loopof"]])
            for w in got[-1]["loopof"]:
                pair, known, pic, kind = w.rsplit(":", 3)
                out.append({"preset": n, "source": pair.split(">")[0], "known": known == "1", "loop": pic == "1", "kind": kind})
        return out
    mic_rows, tone_rows = heard("srcMic"), heard("srcTone")
    for r in mic_rows: print("    %-26s %-12s registered %s, loop %s, to %s" % (r["preset"], r["source"], r["known"], r["loop"], r["kind"]))
    ok = lambda r: r["source"].startswith("hear.") and r["known"] and not r["loop"] and r["kind"] in ("a", "v")
    check("every Listening preset routes a source that hears, and on a microphone it is live and no loop",
          len(mic_rows) >= 5 and all(ok(r) for r in mic_rows), str([r for r in mic_rows if not ok(r)][:3]))
    null("on the generator the same routings are the loop's", all(r["loop"] for r in tone_rows) and tone_rows, str([r["loop"] for r in tone_rows]))
