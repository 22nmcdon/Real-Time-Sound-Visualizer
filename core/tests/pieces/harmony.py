"""Harmony as geometry (P6) on the core: a chord built a note at a time
draws the struck chord's figure, a chord struck twice draws one figure, and
the geometry reaches the picture's meter - harmonytest.py's numbers rows.

These were harmonytest.py's on `?brain=js` until stage 5, step 3, batch 4
(13 Nov): there a `makeGeneratorCore` built in the page, its voices set by
hand, and the page's own `pictureMeter` over six seconds of the page's
picture. Here the core's generator (generator_cpp: the same `voices` a
layer, each layer's picture pair read), and the instrument whole
(instrument_cpp: a setup, a held note, and its own picture meter, by its
`meter` command). On the default site the page's `pictureMeter` is the
face's second grid (the inventory, section 1), so the meter rows could not
have moved as they were. The readout's words stay in harmonytest.py, the
face's. Each check has its null.
"""
import statistics

RATE = 44100
HZ = lambda note: 440 * 2 ** ((note - 69) / 12)


def voice(note, role):
    return "%d/%r/1/%s" % (note, HZ(note), role)


def run(kit):
    check, null = kit.check, kit.null

    def pair(steps, shape="ramp", layer=0):
        """Steps of (voices or None, samples, keep), on one layer, samples a
        whole number of blocks since the generator is told at a block's top:
        each kept step's [left, right] picture lanes of that layer."""
        ev, at, spans = [], 0, []
        for l in (0, 1):
            ev += ["at 0 set %s %s %d" % (k, v, l) for k, v in
                   (("shape", shape), ("attackMs", 1), ("decayMs", 1), ("sustain", 1), ("releaseMs", 5))]
        for v, n, keep in steps:
            if v is not None: ev.append("at %d voices %d %s" % (at, layer, v or "none"))
            if keep: spans.append((at, at + n))
            at += n
        out = kit.floats("generator_cpp", "run rate=%r slots=32 seed=3 samples=%d lfo0=sine,0 lfo1=sine,0\n%s\nend"
                         % (float(RATE), at, "\n".join(ev)))
        c0, c1 = (0, 1) if layer == 0 else (4, 5)
        return [[out[a * 6 + c0:b * 6:6], out[a * 6 + c1:b * 6:6]] for a, b in spans]

    def apart(a, b, start=0):
        return max(max(abs(x - y) for x, y in zip(a[c][start:], b[c][start:])) for c in (0, 1))

    # --- a chord built a note at a time (:96, :98) ---
    # 1024 and 1408 samples (whole blocks, where the page had 1000 and 1337):
    # still no whole number of cycles of anything here, so a joiner born at
    # nought is somewhere else in its cycle than in step.
    C, E, G = 48, 52, 55
    chord = "+".join([voice(C, "x"), voice(E, "u"), voice(G, "y")])
    for layer, shape in ((0, "ramp"), (1, "ramp"), (0, "square")):
        built = pair([(voice(C, "x"), 1024, False), ("+".join([voice(C, "x"), voice(E, "y")]), 1408, False),
                      (chord, 3072, True)], shape, layer)[0]
        whole = pair([(chord, 5632, True)], shape, layer)[0]
        struck = [ch[2432:5504] for ch in whole]   # the chord struck at once, over the same samples as the built one's last
        late = [ch[2532:5604] for ch in whole]     # and a hundred samples on
        same, off = apart(built, struck, 2200), apart(built, late, 2200)
        name = ("A" if layer == 0 else "B") + ", " + shape
        check("layer %s: the chord built a note at a time draws the struck chord's figure, sample for sample" % name,
              same < 1e-4, "%.2e" % same)
        null("layer %s: and the comparison fails out of step" % name, off > 0.05, "%.3f" % off)

    # --- a chord struck twice (:106, :107) ---
    twice = pair([(chord, 4480, True), ("", 4480, False), (voice(50, "xy"), 2176, False), ("", 4480, False),
                  (chord, 4480, True)])
    shifted = [ch[100:] + ch[:100] for ch in twice[1]]
    same, off = apart(twice[0], twice[1], 200), apart(twice[0], shifted, 200)
    check("a chord struck twice, with other notes and time between, draws the same figure", same < 1e-6, "%.2e" % same)
    null("and the comparison fails with the second strike out of step", off > 0.05, "%.3f" % off)
    # And struck inside the last chord's release (5 ms here, so a block of
    # silence is inside it): what is ringing out is not held, so the new
    # chord is born at nought all the same. Added by the mutation pass: the
    # gaps above are long enough for every voice to be gone, so a generator
    # that took its phase from a voice still releasing passed them.
    other = "+".join([voice(50, "x"), voice(53, "u"), voice(57, "y")])
    tail = pair([(chord, 4480, False), ("", 128, False), (other, 4480, True)])[0]
    alone = pair([(other, 4480, True)])[0]
    same = apart(tail, alone, 400)
    check("a chord struck while the last one rings out is born at nought, as if struck alone", same < 1e-6, "%.2e" % same)
    null("and not as the same chord a hundred samples on", apart(tail, [ch[100:] + ch[:100] for ch in alone], 400) > 0.05)

    # --- the geometry reaches the loop (:196) ---
    # The old library's Harmonic tone (a timebase of 3 on the defaults), held
    # in Mono at A3 on the X-Y display, the interval from the menu: a just
    # fifth and an equal third, with the Picture amount at nought as the
    # page's ?picture=0 had it (at its default the loop moves the sound). The
    # meter is the instrument's own, read every 150 ms over six seconds after
    # 800 ms to settle, as the page read its own.
    #
    # (harmonytest's other row here, "a held just fifth reads settled", is
    # held below since 5a, with the reason it could not be before.)
    def meter(interval, just):
        code = kit_code({"v": 7, "timebase": 3, "display": "xy", "midiMode": "mono", "interval": interval, "just": just,
                          "pictureAmount": 0})
        lines = [["make", 48000, 128, code], ["midi", 0x90, 57, 127]] + [["block", 4800, 100000]] * 8
        for _ in range(40): lines += [["block", 7200, 100000], ["meter"]]
        rows = [l.split() for l in kit.instrument(lines) if l.startswith("meter ")]
        return statistics.median(float(r[1]) for r in rows), rows[-1][2]
    fifth, third = meter(7, True), meter(4, False)
    moves = lambda t, f: t[1] != "settled" and t[0] > 1.5 * f[0]
    check("an equal third, turning, reads moving on the instrument's meter, changing more a frame than a just fifth",
          moves(third, fifth), "%s against %s" % (third, fifth))
    # The null is the fifth in the third's place.
    null("the fifth against itself does not", not moves(fifth, fifth), str(fifth))

    # The verdict, as the eye sees it (5a). Until 5a this meter called the
    # still fifth "cycling", and harmonytest's "settled" row stayed on the
    # page's brain: each frame is one trigger-placed window, and a figure
    # with detail lands a little differently in each, 0.027 a frame with no
    # persistence (in a pattern six frames long). The verdict now reads
    # change against the grid of the eye's time ago (kMeterEye). Held at no
    # persistence, where the jitter is bare, and at the old library's 0.12,
    # each way: the still figures settled, the turning ones not.
    def verdict(fields, seconds=8.0):
        s = {"v": 7, "timebase": 3, "display": "xy", "midiMode": "mono", "pictureAmount": 0}
        s.update(fields)
        rows = kit.render([["make", 48000, kit_code(s)], ["midi", 0x90, 57, 127], ["every", 0.15, "meter", "eye"], ["to", seconds]])
        return rows[-1]["eye"][2] if rows[-1]["eye"][2] != "running" else "running away", float(rows[-1]["eye"][1]), \
            statistics.median(float(r["meter"][0]) for r in rows[10:])
    for pers in ("0", "0.12"):
        still = {"just fifth of the Harmonic tone": verdict({"interval": 7, "just": True, "persistence": pers}),
                 "unison of the Harmonic tone": verdict({"interval": 0, "persistence": pers}),
                 "plain sine's unison": verdict({"interval": 0, "shape": "sine", "persistence": pers})}
        turning = {"equal third": verdict({"interval": 4, "just": False, "persistence": pers}),
                   "equal fifth": verdict({"interval": 7, "just": False, "persistence": pers})}
        for name, (v, eye, frame) in still.items():
            check("at persistence %s, a held %s reads settled on the instrument's meter" % (pers, name),
                  v == "settled", "%s, %.4f as the eye sees it (%.4f frame to frame)" % (v, eye, frame))
        for name, (v, eye, frame) in turning.items():
            null("at persistence %s, an %s, turning, does not" % (pers, name), v not in ("settled", "listening"),
                 "%s, %.4f (%.4f frame to frame)" % (v, eye, frame))


def kit_code(fields):
    import base64, json
    return base64.b64encode(json.dumps(fields).encode()).decode().rstrip("=")
