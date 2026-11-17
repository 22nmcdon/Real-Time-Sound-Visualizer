"""Every note in both ears, at the Width (16 Nov), and the dyad back in step.

The owner, after web/docs/both-ears.md: what is heard is a mix of the same
voices as are drawn, each voice in both ears at full with an image of its own
that never depends on what else is held - its left behind its right by the
Width's fraction of a quarter of its own cycle, so nought is every note the
same in both ears, fifty an eighth and a hundred the quarter turn a lone note
always had. Until then the heard pair was the figure: a second note took the
first out of one ear in Dyad and leaned it 6 dB in Poly, and the Width
squeezed the figure's side, so a dyad at nought could cancel. And option A of
web/docs/one-to-two-notes.md: a change of interval puts the dyad's right
channel back in step with its left, crossfading the old right over 30 ms, so
the lower note comes back as the ring it left as, whatever moment the upper is
let go.

Two phrases, the studies' own, through the instrument offline:
- the owner's: Harmonic tone (Dyad, the picture off so the notes alone decide
  the image), C2 alone, E4 added, E4 let go, C2 alone again;
- a chord on Tine piano's voices made plain (one sine each: FM, Scan and
  routings off, held at full) so each note's fundamental is its own: C3, then
  E3, G3 and C4 added, let go from the top.
The limiter off for the levels (it is last of all, and pulls every note alike).

Each note is read off its own fundamental by lock-in in each ear: its level in
each, and the coherence of the two (1 the same in both ears, 0 a quarter turn).
What is held, each with its null:

- every note's level in each ear steady through both phrases, at Width 0, 50
  and 100, and its coherence the Width's (cos of its angle) in every span. The
  null: the same reading of the drawn lanes, which are what was heard before
  (at a hundred, no score, the Output at one) - a note leaning 6 dB, or gone
  from one ear;
- at Width nought no note cancels: after each of sixteen release moments
  across a turn of the dyad's drift, the lower note in each ear within 3 dB of
  its level alone, and so with the Phase knob at a half turn, where the dyad's
  lone note is drawn as a line the other way. The null: the Width as it was at
  nought, the drawn pair's middle in both ears, on that line, which is silence
  (before option A it was silence after some release moments too; the drawn
  pair comes back as a ring now, so the half turn is where it still shows);
- the drawn lanes, the shown grid and every reading of the loop the same to
  the bit at Width 0, 50 and 100 - the picture, Scan and the loop do not hear
  the Width. The null: the heard pairs, which differ (so the comparison can see
  a difference where there is one);
- the dyad's drawn right back a quarter ahead of its left after each of the
  sixteen release moments. The null: what today's core drew at them, the
  coherences one-to-two-notes.md recorded (0.59 to -0.99 and back);
- a lone note in Dyad at a hundred is heard as it was drawn, to the bit. The
  null: at fifty it is not.
"""
import os, struct

import numpy as np

from pieces.pulse import setup_code

RATE = 44100
LANES = 6
HT = {"timebase": 3, "pictureAmount": 0, "pictureSwell": True}   # Harmonic tone, the picture off
T_BASS, T_UP, T_UPOFF, T_BASSOFF, END = 0.2, 1.8, 3.4, 5.2, 6.0
CHORD_NOTES = [48, 52, 55, 60]
CHORD_ON = [0.2, 1.1, 2.0, 2.9]
CHORD_OFF = {60: 3.8, 55: 4.7, 52: 5.6, 48: 6.5}
CHORD_END = 7.3
NAMES = {48: "C3", 52: "E3", 55: "G3", 60: "C4"}
# What today's core drew of the bass after each release moment (one-to-two-notes.md).
TODAY_SWEEP = [0.59, 0.86, 0.99, 0.97, 0.81, 0.51, 0.16, -0.25, -0.58, -0.86, -0.99, -0.97, -0.81, -0.52, -0.17, 0.24]
PICTURE = ("table", "sources", "reads", "loop", "scan", "stage", "lmeter", "eye", "meter", "gridstat", "layers")


def hz(n): return 440 * 2 ** ((n - 69) / 12)


F0 = hz(36)
Q = 1 / (4 * F0) / 16   # a sixteenth of a turn of the dyad's drift


def lockin(L, R, f, a, b, win=0.12, hop=0.01):
    n = int(win * RATE); w = np.hanning(n); w /= w.sum()
    HL, HR = [], []
    for t in np.arange(a, b - win, hop):
        i = int(t * RATE)
        e = np.exp(-2j * np.pi * f * (i + np.arange(n)) / RATE) * w
        HL.append(2 * (L[i:i + n] @ e)); HR.append(2 * (R[i:i + n] @ e))
    HL, HR = np.array(HL), np.array(HR)
    db = lambda v: float(20 * np.log10(max(v, 1e-9)))
    coh = float(np.real(np.sum(HL * np.conj(HR))) / max(np.sqrt(np.sum(abs(HL) ** 2) * np.sum(abs(HR) ** 2)), 1e-18))
    return db(np.sqrt(np.mean(abs(HL) ** 2))), db(np.sqrt(np.mean(abs(HR) ** 2))), coh


def run(kit):
    check, null = kit.check, kit.null
    tine = None
    base = os.path.join(os.path.dirname(kit.build("render_cpp")), "ears")

    def render(fields, events, end, width, full=False):
        lines = [["make", RATE, setup_code(fields)], ["control", "limiter", "0"],
                 ["slider", "stereoWidth", str(width)], ["record", "heard", base + ".heard"]]
        if full: lines += [["record", "lanes", base + ".lanes"], ["record", "grid", base + ".grid"],
                           ["every", 0.01] + list(PICTURE) + ["griddump"]]
        for t, a, b, c in events: lines += [["to", t], ["midi", a, b, c]]
        lines += [["to", end], ["record", "heard"]]
        if full: lines += [["record", "lanes"], ["record", "grid"]]
        out = kit.render(lines, raw=True)
        h = np.fromfile(base + ".heard", dtype="<f4").astype(float)
        r = {"L": h[0::2], "R": h[1::2]}
        if full:
            ln = np.fromfile(base + ".lanes", dtype="<f4")
            r["X"], r["Y"] = ln[0::LANES].astype(float), ln[1::LANES].astype(float)
            r["lanes"] = ln.tobytes()
            r["grid"] = open(base + ".grid", "rb").read()
            r["reads"] = [l for l in out.splitlines() if l.split()[:1] and l.split()[0] in PICTURE + ("at",)]
        return r

    def owner(rel=T_UPOFF):
        return [(T_BASS, 0x90, 36, 100), (T_UP, 0x90, 64, 100), (rel, 0x80, 64, 0), (T_BASSOFF, 0x80, 36, 0)]

    chord = sorted([(t, 0x90, n, 100) for t, n in zip(CHORD_ON, CHORD_NOTES)] + [(CHORD_OFF[n], 0x80, n, 0) for n in CHORD_NOTES])
    ev = sorted(CHORD_ON + list(CHORD_OFF.values()))
    chord_spans = []
    held = []
    for k in range(7):
        if k < 4: held = held + [CHORD_NOTES[k]]
        else: held = [n for n in held if n != max(held)]
        chord_spans.append((list(held), ev[k] + 0.08, ev[k + 1] - 0.05))
    owner_spans = [([36], T_UP - 0.6, T_UP - 0.05), ([36, 64], T_UP + 0.08, T_UPOFF - 0.05), ([36], T_UPOFF + 0.08, T_BASSOFF - 0.05)]

    # The bank's Tine piano, made plain: one sine a note.
    import subprocess, json
    exe = kit.build("instrument_cpp")
    code = subprocess.run([exe, "--code", "Tine piano"], check=True, capture_output=True, text=True).stdout.strip()
    import base64
    pad = code + "=" * (-len(code) % 4)
    tine = json.loads(base64.b64decode(pad))
    tine.pop("v", None)
    plain = dict(tine, oscFm=0, oscScan=0, scanStrike=0, mod="", sus=100)

    def steady(L, R, spans, freq_of, width):
        """Each note's worst departure: level in each ear from its first span's, and coherence from the Width's."""
        want = float(np.cos(width / 100 * np.pi / 2))
        first, worst_db, worst_coh, rows = {}, 0.0, 0.0, []
        for notes, a, b in spans:
            for n in notes:
                l, r, c = lockin(L, R, freq_of(n), a, b)
                first.setdefault(n, (l, r))
                worst_db = max(worst_db, abs(l - first[n][0]), abs(r - first[n][1]), abs(l - r))
                worst_coh = max(worst_coh, abs(c - want))
                rows.append("%s %.1f/%.1f %.2f" % (NAMES.get(n, n), l, r, c))
        return worst_db, worst_coh, rows

    of_owner = lambda n: F0 if n == 36 else 5 * F0   # the E4 is the dyad's ratio 5 over the C2
    for width in (0, 50, 100):
        o = render(HT, owner(), END, width, full=True)
        db, coh, rows = steady(o["L"], o["R"], owner_spans, of_owner, width)
        check("the owner's phrase at Width %d: C2 and E4 each the same in both ears and in every span, within 0.5 dB, "
              "their coherence the Width's within 0.05" % width, db < 0.5 and coh < 0.05, "%.2f dB, %.3f; %s" % (db, coh, ", ".join(rows)))
        c = render(plain, chord, CHORD_END, width, full=True)
        db, coh, rows = steady(c["L"], c["R"], chord_spans, hz, width)
        check("the chord built and let go at Width %d: every note the same in both ears and in all seven spans, within 0.5 dB, "
              "its coherence the Width's within 0.05" % width, db < 0.5 and coh < 0.05, "%.2f dB, %.3f" % (db, coh))
        if width == 100:
            dbn, cohn, rowsn = steady(o["X"], o["Y"], owner_spans, of_owner, width)
            null("the owner's phrase as the drawn pair heard it (before 16 Nov): the C2 gone from the right while the E is held",
                 dbn > 20, "%.1f dB; %s" % (dbn, ", ".join(rowsn)))
            dbn, cohn, _ = steady(c["X"], c["Y"], chord_spans, hz, width)
            null("the chord as the drawn pair heard it: the outer notes lean 6 dB and lose their width", dbn > 5 and cohn > 0.5,
                 "%.2f dB, %.2f" % (dbn, cohn))
        if width == 0:
            pic0 = (o, c)
        elif width == 50:
            pic50 = (o, c)
        else:
            pic100 = (o, c)

    # The picture does not hear the Width.
    for k, phrase in ((0, "the owner's phrase"), (1, "the chord")):
        a, b, d = pic0[k], pic50[k], pic100[k]
        same = all(x["lanes"] == a["lanes"] and x["grid"] == a["grid"] and x["reads"] == a["reads"] for x in (b, d))
        check("%s: the drawn lanes, the shown grid and all %d readings of the loop the same to the bit at Width 0, 50 and 100"
              % (phrase, len(a["reads"])), same and len(a["reads"]) > 500 and len(a["grid"]) > 1000000,
              "%d samples, %d bytes of grid" % (len(a["X"]), len(a["grid"])))
        apart = max(float(np.max(np.abs(a["L"] - d["L"]))), float(np.max(np.abs(a["R"] - d["R"]))))
        null("%s: the heard pairs at Width 0 and 100 differ" % phrase, apart > 0.01, "%.3f" % apart)

    # Sixteen release moments across a turn of the drift: Width nought never cancels, and option A.
    alone = lockin(pic0[0]["L"], pic0[0]["R"], F0, T_UP - 0.6, T_UP - 0.05)
    worst, drawn = 99.0, []
    for k in range(16):
        rel = T_UPOFF + k * Q
        r = render(HT, owner(rel), END, 0, full=True)
        a, b = rel + 0.2, T_BASSOFF - 0.05
        l, rr, _ = lockin(r["L"], r["R"], F0, a, b)
        worst = min(worst, l - alone[0], rr - alone[1])
        drawn.append(lockin(r["X"], r["Y"], F0, a, b)[2])
    check("at Width nought the C2 comes back within 3 dB of its level alone in each ear, whatever moment the E is let go",
          worst > -3, "worst %.2f dB" % worst)
    # And with the Phase knob at a half turn, where a dyad's lone note is drawn as a line through the
    # middle the other way: heard at nought it is the same in both ears, at its level.
    half = render(dict(HT, phase=180), [(0.2, 0x90, 36, 100), (1.5, 0x80, 36, 0)], 1.8, 0, full=True)
    hl, hr, _ = lockin(half["L"], half["R"], F0, 0.4, 1.4)
    check("a dyad's lone note with the Phase at a half turn, at Width nought, within 3 dB of its level alone in each ear",
          min(hl - alone[0], hr - alone[1]) > -3, "%.1f / %.1f dB against %.1f / %.1f" % (hl, hr, alone[0], alone[1]))
    mid = (half["X"] + half["Y"]) / 2
    ml, _, _ = lockin(mid, mid, F0, 0.4, 1.4)
    null("the Width as it was, at nought (the drawn pair's middle in both ears), cancels it",
         ml - alone[0] < -3, "%.1f dB" % ml)
    in_step = lambda v: all(abs(c) < 0.05 for c in v)
    check("the dyad's drawn right is back a quarter ahead of its left after each of sixteen release moments (coherence 0)",
          in_step(drawn), " ".join("%.2f" % c for c in drawn))
    null("today's core, which brought the bass back at whatever angle the release caught", not in_step(TODAY_SWEEP),
         " ".join("%.2f" % c for c in TODAY_SWEEP))

    # A lone note in Dyad at a hundred is heard as drawn, to the bit. Struck half a second in:
    # the Width opens at fifty since 17 Nov, and the glide to a hundred lands (to the bit) by then.
    lone = [(0.5, 0x90, 48, 100), (1.3, 0x80, 48, 0)]
    for width in (100, 50):
        r = render(HT, lone, 1.8, width, full=True)
        n = min(len(r["L"]), len(r["X"]))
        same = np.array_equal(r["L"][:n], r["X"][:n]) and np.array_equal(r["R"][:n], r["Y"][:n])
        if width == 100:
            check("a lone note in Dyad at Width 100 is heard as it is drawn, to the bit", same, "%d samples" % n)
        else:
            null("and at fifty it is not", not same, "%.3f" % float(np.max(np.abs(r["R"][:n] - r["Y"][:n]))))

    # --- a note let go of two in Dyad, either one (16 Nov, the owner's pop) ---
    # Holding E4 and adding C2 under it, then letting the C2 go, popped: the
    # interval and the pitch move in the same sample, and the old right was
    # crossfaded out at the new pitch times the old ratio - the E played five
    # times too high for 30 ms - while the lower place switched from C2 to the
    # E at full over the E it was taking from. Letting the E go did not pop,
    # since the pitch stays the C2's. Read in each ear and on the drawn lanes,
    # around the release: the largest move a sample against the steady sound's
    # on both sides of it, and the note that goes on, by lock-in at its own
    # pitch in 30 ms windows, against its own level once settled. Both orders,
    # at Width 0, 50 and 100, Harmonic tone with the picture off; and Mono, whose
    # pitch moves under a held interval when its newest note is let go.
    def around(x, t, f):
        i = int(t * RATE)
        d = np.abs(np.diff(x))
        steady = max(d[i - int(0.3 * RATE): i - int(0.01 * RATE)].max(), d[i + int(0.15 * RATE): i + int(0.45 * RATE)].max())
        jump = d[i - 64: i + int(0.04 * RATE)].max() / max(steady, 1e-12)
        settled = lockin(x, x, f, t + 0.15, t + 0.45, win=0.03)[0]
        swing = max(abs(lockin(x, x, f, t + k * 0.01, t + k * 0.01 + 0.031, win=0.03)[0] - settled) for k in range(-3, 10))
        return jump, swing
    E4, C2 = hz(64), hz(36)
    worst = {}
    for order, notes, goes_on in (("the low let go", (64, 36), E4), ("the high let go", (36, 64), C2)):
        ev = [(0.2, 0x90, notes[0], 100), (1.0, 0x90, notes[1], 100), (2.0, 0x80, notes[1], 0), (3.0, 0x80, notes[0], 0)]
        for width in (0, 50, 100):
            r = render(HT, ev, 2.6, width, full=True)
            for ear in ("L", "R", "X", "Y"):
                j, s = around(r[ear], 2.0, goes_on)
                key = (order, ear)
                worst[key] = (max(worst.get(key, (0, 0))[0], j), max(worst.get(key, (0, 0))[1], s))
    for order in ("the low let go", "the high let go"):
        heard = [worst[(order, e)] for e in ("L", "R")]
        drawn = [worst[(order, e)] for e in ("X", "Y")]
        check("in Dyad, %s: no ear steps more than one and a half times the steady sound does, at Width 0, 50 and 100, and the note "
              "that goes on keeps its level within 1.5 dB" % order,
              all(j < 1.5 and s < 1.5 for j, s in heard), "steps %s, swings %s dB" % ([round(j, 2) for j, _ in heard], [round(s, 2) for _, s in heard]))
        check("and the drawn lanes do not step there either", all(j < 1.5 for j, _ in drawn), "steps %s" % [round(j, 2) for j, _ in drawn])
    # The null: the check fed the old fault, a steady E with its last 30 ms
    # before a release replaced by the same note five times as high, faded out.
    t = np.arange(int(2.6 * RATE)) / RATE
    old = 0.3 * np.sin(2 * np.pi * E4 * t)
    k0, n30 = int(2.0 * RATE), int(0.03 * RATE)
    fade = np.cos(np.pi / 2 * np.arange(n30) / n30)
    old[k0:k0 + n30] = 0.3 * (np.sin(2 * np.pi * E4 * t[k0:k0 + n30]) * np.sin(np.pi / 2 * np.arange(n30) / n30)
                              + np.sin(2 * np.pi * 5 * E4 * t[k0:k0 + n30]) * fade)
    j, s = around(old, 2.0, E4)
    null("the old crossfade - the leaving note five times too high, faded out - reads as a step", j > 1.5, "x%.1f" % j)

    # Mono: the newest note is the pitch and the Interval holds above it; let it go and the older is the pitch again.
    mono = dict(HT, midiMode="mono", interval=4)
    ev = [(0.2, 0x90, 48, 100), (1.0, 0x90, 55, 100), (2.0, 0x80, 55, 0), (3.0, 0x80, 48, 0)]
    steps = []
    for width in (0, 100):
        r = render(mono, ev, 2.6, width, full=True)
        steps += [around(r[ear], 2.0, hz(48))[0] for ear in ("L", "R", "X", "Y")]
    check("in Mono, the newest note let go back to the older: no ear or lane steps more than one and a half times the steady sound",
          max(steps) < 1.5, "worst x%.2f" % max(steps))

    # --- the Width on what is drawn too (16 Nov, the owner's switch) ---------
    # Drawn too, the screen draws the heard mix: what is heard is the drawn
    # pair, to the bit (one hand, no score, the Output at one, the limiter
    # off), the owner's phrase and the chord, at the sound's Width of 0, 50 and
    # 100. The null: the same with the switch on what you hear, which parts them.
    for label, sound, events, end in (("the owner's phrase", HT, owner(), END), ("the chord", plain, chord, CHORD_END)):
        for sw in (0, 50, 100):
            d = render(dict(sound, widthDrawn=True, soundWidth=sw), events, end, 100, full=True)
            n = min(len(d["L"]), len(d["X"]))
            same = np.array_equal(d["L"][:n], d["X"][:n]) and np.array_equal(d["R"][:n], d["Y"][:n])
            check("drawn too, %s at the sound's Width %d: what is heard is what is drawn, to the bit" % (label, sw),
                  same and np.abs(d["X"]).max() > 0.05, "%d samples" % n)
        h = render(dict(sound, widthDrawn=False, soundWidth=50), events, end, 100, full=True)
        n = min(len(h["L"]), len(h["X"]))
        null("on what you hear, %s is heard apart from what is drawn" % label,
             not (np.array_equal(h["L"][:n], h["X"][:n]) and np.array_equal(h["R"][:n], h["Y"][:n])))

    # The Width drawn too is the setup's: a code with the sound's Width at 30
    # and the player's at 100 draws and plays every note at 30 - the chord's
    # notes each at the coherence of 30, cos(0.3 pi / 2), on the screen and in
    # the ears. The null: the listening value, the player's Width at 30 and the
    # sound's at 100, draws them at a hundred's, a quarter turn.
    want = float(np.cos(0.3 * np.pi / 2))
    def coherences(fields, listening):
        r = render(dict(plain, **fields), chord, CHORD_END, listening, full=True)
        out = []
        for notes, a, b in chord_spans:
            for n in notes:
                out.append(lockin(r["L"], r["R"], hz(n), a, b)[2])
                out.append(lockin(r["X"], r["Y"], hz(n), a, b)[2])
        return out
    stored = coherences({"widthDrawn": True, "soundWidth": 30}, 100)
    check("drawn too, the sound's Width from its setup (30) is what every note is drawn and heard at, whatever the player's (100)",
          all(abs(c - want) < 0.05 for c in stored), "want %.2f, %s" % (want, " ".join("%.2f" % c for c in stored[:8])))
    listening = coherences({"widthDrawn": True, "soundWidth": 100}, 30)
    null("the player's Width (30) is not what is drawn too: the notes are at the sound's hundred",
         not all(abs(c - want) < 0.05 for c in listening), " ".join("%.2f" % c for c in listening[:8]))
