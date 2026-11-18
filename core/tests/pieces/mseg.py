"""The drawn envelope (MSEG, 18 Nov), on the core: web/docs/mseg-design.md's tests.

The old envelope (envelope.h's `Envelope`) is kept as the reference, and the
shape the version-13 decode pass writes for every old setup must play on the
new engine (mseg.h's `Mseg`) what the old one plays, sample for sample and to
the bit, across a grid of the four numbers with the key let go in each stage,
retriggered in the release, a legato note on an open envelope and a knob moved
mid-stage, at 44.1 and 48 kHz. core/tests/tools/mseg_cpp.cpp runs the two side
by side and reports the first sample where they part. The rest are the
design's: a drawn shape's times, an added point that changes nothing, a loop
without a step, a release from mid-attack, the knobs scaling a stretch's
points, and the sustain point moved and switched off. Each check has its null.
"""
import math

OLD = "1;A>p.2;D>p.2;R>a.2"


def run(kit):
    check, null = kit.check, kit.null

    def script(rate, a, d, s, r, events, run, shape=OLD, extra=()):
        lines = ["rate %r" % float(rate), "tone attackMs %r" % a, "tone decayMs %r" % d, "tone sustain %r" % s,
                 "tone releaseMs %r" % r]
        lines += list(extra)
        if shape is not None: lines.append("shape " + shape)
        lines += ["run %d" % run, "reset 0"]
        lines += ["at %d %s" % e for e in events]
        return "\n".join(lines)

    def both(text):
        return kit.run("mseg_cpp", text, "both").split()

    def trace(text, where=False):
        out = kit.run("mseg_cpp", text, *(["new", "--where"] if where else ["new"])).split("\n")
        rows = [l.split() for l in out if l.strip()]
        return [(float.fromhex(w[0]), int(w[1]), int(w[2]), float(w[3])) if where else (float.fromhex(w[0]), int(w[1]))
                for w in rows]

    def old_trace(text):
        out = kit.run("mseg_cpp", text, "old").split("\n")
        return [(float.fromhex(w.split()[0]), int(w.split()[1])) for w in out if w.strip()]

    # --- the old envelope to the bit ---
    def scenarios(rate, a, d, s, r):
        ms = lambda t: int(round(t * rate / 1000))
        peak, settle = a, a + d
        held = settle + 60
        out = {
            "let go in the attack": [(0, "gate 1 0.8"), (ms(a / 2), "gate 0")],
            "let go in the decay": [(0, "gate 1 0.8"), (ms(a + d / 2) + 1, "gate 0")],
            "let go in the sustain": [(0, "gate 1 0.8"), (ms(held), "gate 0")],
            "retriggered in the release": [(0, "gate 1 0.8"), (ms(held), "gate 0"), (ms(held + r / 2) + 1, "gate 1 0.5")],
            # Opened from full scale, as a generator let go of its gate is: the
            # attack is already past its end and jumps, as the old one's did.
            "opened from full scale": [(0, "reset 1"), (1, "gate 1 0.9"), (ms(held), "gate 0"),
                                       (ms(held + r / 4) + 1, "reset 1"), (ms(held + r / 4) + 2, "gate 1 0.6")],
            "a legato note on an open one": [(0, "gate 1 0.8"), (ms(peak / 2) + 1, "gate 1 0.3"), (ms(held), "gate 1 0.4"),
                                             (ms(held + 10), "gate 0")],
            "the knobs moved mid-stage": [(0, "gate 1 0.8"), (ms(a / 2) + 1, "tone attackMs %r" % (a * 1.7 + 3)),
                                          (ms(a * 1.7 + 3 + d / 3) + 2, "tone decayMs %r" % (d * 0.6 + 1)),
                                          (ms(a * 1.7 + 3 + d / 3) + 3, "tone sustain %r" % (1 - s)),
                                          (ms(held + d), "gate 0"), (ms(held + d + r / 3) + 1, "tone releaseMs %r" % (r * 2 + 5))],
        }
        return out, ms(held + d + 3 * r + 300)

    parted, runs = [], 0
    for rate in (44100, 48000):
        for a in (0, 100, 200):
            for d in (1, 500, 1000):
                for s in (0, 0.5, 1):
                    for r in (1, 1000, 2000):
                        cases, n = scenarios(rate, a, d, s, r)
                        for name, events in cases.items():
                            got = both(script(rate, a, d, s, r, events, n))
                            runs += 1
                            if got[0] != "same":
                                parted.append("%s at %d Hz, A %r D %r S %r R %r: sample %s, %s against %s"
                                              % (name, rate, a, d, s, r, got[1], got[2], got[3]))
    check("the decoded old shape plays the old envelope to the bit: %d runs, every stage let go, retriggered, legato, knobs moved"
          % runs, not parted, "; ".join(parted[:3]))

    # The nulls: the release's aim made relative misses once a key comes up
    # before the sustain, and the attack's bend as a midpoint of 0.710 - the
    # old curve, drawn - misses by rounding.
    def first_part(shape, events, a=100, d=500, s=0.5, r=1000, rate=48000):
        got = both(script(rate, a, d, s, r, events, int(rate * 3), shape=shape))
        return got
    early = [(0, "gate 1 0.8"), (2400, "gate 0")]
    rel = first_part("1;A>p.2;D>p.2;R>p.2", early)
    null("the release aimed by the fall (p.2) rather than by full scale (a.2) parts from the old envelope, let go mid-attack",
         rel[0] == "differ", " ".join(rel))
    held = [(0, "gate 1 0.8"), (48000, "gate 0")]
    same_held = first_part("1;A>p.2;D>p.2;R>p.2", held)
    check("and only then: let go in the sustain, where the fall is the sustain's, p.2 and a.2 differ too unless the sustain is 1",
          same_held[0] == "differ", " ".join(same_held))
    mid = first_part("1;A>m.71;D>p.2;R>a.2", held)
    null("the attack's bend as the midpoint 0.710 parts from it by rounding", mid[0] == "differ", " ".join(mid))
    worst = 0
    if mid[0] == "differ":
        t = old_trace(script(48000, 100, 500, 0.5, 1000, held, 48000 * 3))
        u = trace(script(48000, 100, 500, 0.5, 1000, held, 48000 * 3, shape="1;A>m.71;D>p.2;R>a.2"))
        worst = max(abs(x[0] - y[0]) for x, y in zip(t, u))
    check("but only by rounding: the midpoint 0.710 is the old curve, under a thousandth of full scale off at worst",
          0 < worst < 1e-3, "worst %.3g" % worst)

    # An empty shape, and one that does not read, are the old envelope's too.
    for text, say in (("", "an empty shape"), ("junk;Q>z", "a shape that does not read")):
        got = both(script(48000, 20, 300, 0.4, 500, [(0, "gate 1 1"), (30000, "gate 0")], 80000, shape=text if text else None))
        check(say + " plays the old envelope", got[0] == "same", " ".join(got))
    parsed = kit.run("mseg_cpp", "", "parse", "junk;Q>z").split()
    check("and says it did not read", parsed[0] == "no", " ".join(parsed[:2]))
    parsed = kit.run("mseg_cpp", "", "parse", OLD).split()
    null("the old shape's text reads", parsed[0] == "ok", " ".join(parsed[:2]))

    # --- a drawn shape's times, to the sample ---
    def changes(rows):
        """The samples at which the segment changes, and what it changes to."""
        out, last = [], rows[0][2]
        for i, row in enumerate(rows):
            if row[2] != last: out.append((i, row[2])); last = row[2]
        return out
    for rate in (44100, 48000):
        # Straight segments: 10 ms of attack in two halves, a 20 ms decay, a 30 ms release.
        text = script(rate, 10, 20, 0.5, 30, [(0, "gate 1 1"), (int(rate * 0.1), "gate 0")], int(rate * 0.2),
                      shape="1;A.5,.5,l>l;D>l;R>l")
        ch = changes(trace(text, where=True))
        # Step i ends a segment once its time is used: the first step at or past ceil(samples).
        half = 5 * rate / 1000
        want = [math.ceil(half) - 1, math.ceil(half) * 2 - 1]
        got = [c[0] for c in ch[:2]]
        check("at %d Hz a drawn shape's straight segments end on the sample their times say: %s" % (rate, want), got == want,
              "changed at %s" % ch[:4])
        null("and one sample later is not where they end", [w + 1 for w in want] != got, "%s" % got)
        # A curve: the old law ends on the first sample at or past its end.
        text = script(rate, 10, 20, 0.5, 30, [(0, "gate 1 1"), (int(rate * 0.1), "gate 0")], int(rate * 0.2),
                      shape="1;A>m.8;D>m.3;R>m.7")
        ch = changes(trace(text, where=True))
        a_end, d_end = ch[0][0], ch[1][0] if len(ch) > 1 else None
        want_a, want_d = 10 * rate / 1000, 30 * rate / 1000
        check("at %d Hz a curved attack and decay end within a sample of their times" % rate,
              abs(a_end + 1 - want_a) <= 1 and d_end is not None and abs(d_end + 1 - want_d) <= 1.5,
              "attack at %d (%.1f), decay at %s (%.1f)" % (a_end + 1, want_a, d_end and d_end + 1, want_d))

    # A drawn curve on a flat stretch is flat for its time: the first half of
    # the decay drawn level with the peak, then a curve to the sustain.
    rows = trace(script(48000, 10, 200, 0.3, 200, [(0, "gate 1 1"), (48000, "gate 0")], 48000,
                        shape="1;A>l;D.5,1,m.6>m.7;R>l"))
    check("a curve drawn flat holds its level for its share of the time", rows[480 + 4700][0] == 1 and rows[480 + 9600][0] < 0.5,
          "%.4f half-way, %.4f at the end" % (rows[480 + 4700][0], rows[480 + 9600][0]))
    null("where the decay is one curve it has already fallen half-way in", trace(script(48000, 10, 200, 0.3, 200,
         [(0, "gate 1 1")], 24000, shape="1;A>l;D>m.7;R>l"))[480 + 4700][0] < 0.9)

    # --- a point added on the line changes nothing ---
    def aim(a, b, m):
        k = 2 * math.log(m / (1 - m))
        rho = 1 / (math.exp(k) - 1)
        return b - rho * (a - b)
    def at(a, b, m, x):
        T = aim(a, b, m)
        return T + (a - T) * ((b - T) / (a - T)) ** x
    S, M = 0.4, 0.65
    T = aim(1, S, M)
    u = 0.37
    lvl = at(1, S, M, u)
    # As p bends: aim = b - rho * (a - b), so rho = (b - aim) / (a - b).
    p1 = (lvl - T) / (1 - lvl)
    p2 = (S - T) / (lvl - S)
    whole = "1;A>m.62;D>m%s;R>m.65" % repr(M)[1:]
    split = "1;A>m.62;D%s,%s,p%r>p%r;R>m.65" % (repr(u)[1:], repr(lvl), p1, p2)
    ev = [(0, "gate 1 1"), (48000, "gate 0")]
    one = trace(script(48000, 20, 400, S, 300, ev, 72000, shape=whole))
    two = trace(script(48000, 20, 400, S, 300, ev, 72000, shape=split))
    diff = max(abs(x[0] - y[0]) for x, y in zip(one, two))
    check("a point added on the decay's line, the halves keeping the whole's aim, changes nothing past a sample's rounding",
          diff < 2e-4, "worst %.3g" % diff)
    naive = "1;A>m.62;D%s,%s,m%s>m%s;R>m.65" % (repr(u)[1:], repr(lvl), repr(M)[1:], repr(M)[1:])
    three = trace(script(48000, 20, 400, S, 300, ev, 72000, shape=naive))
    ndiff = max(abs(x[0] - y[0]) for x, y in zip(one, three))
    null("the halves each given the whole's midpoint change it, plainly", ndiff > 1e-2, "worst %.3g" % ndiff)

    # --- a loop has no step ---
    loop = "1;A>m.7;D.5,.2,m.6>m.4;R>a.2;L2"
    ev = [(0, "gate 1 1"), (48000 * 2, "gate 0")]
    rows = trace(script(48000, 30, 200, 0.7, 300, ev, 48000 * 3, shape=loop), where=True)
    steps = max(abs(rows[i][0] - rows[i - 1][0]) for i in range(2, 48000 * 2))
    passes = sum(1 for i in range(1, 48000 * 2) if rows[i][2] < rows[i - 1][2])
    check("a loop round the decay while held goes round (%d passes) with no step" % passes, passes >= 5 and steps < 0.005,
          "largest step %.4f" % steps)
    # The null: the level arriving at the sustain point is 0.7, and the drawn
    # start of the loop's first segment is the peak at 1 - re-entering from it would be a step of 0.3.
    jump = abs(0.7 - 1.0)
    null("re-entered from its drawn start instead, the loop would step by more than the check allows", jump > 0.005, "%.2f" % jump)
    held_after = [r[0] for r in rows[48000 * 2:48000 * 2 + 5]]
    check("and the key let go mid-loop goes into the release from where it is", abs(held_after[0] - rows[48000 * 2 - 1][0]) < 0.005,
          "%.4f then %.4f" % (rows[48000 * 2 - 1][0], held_after[0]))

    # --- a release from mid-attack starts where the level is ---
    ev = [(0, "gate 1 1"), (480, "gate 0")]
    rows = trace(script(48000, 40, 200, 0.6, 300, ev, 48000, shape="1;A>m.6;D>m.7;R>m.7"))
    before, after = rows[479][0], rows[480][0]
    check("let go mid-attack, the release starts from the attack's level", abs(after - before) < 0.003 and after < before,
          "%.4f then %.4f" % (before, after))
    null("and not from the sustain, which is far from it", abs(before - 0.6) > 0.003, "%.4f against 0.6" % before)

    # --- a knob scales its stretch's points ---
    def arrival(dec):
        rows = trace(script(48000, 10, dec, 0.3, 200, [(0, "gate 1 1"), (48000, "gate 0")], 48000,
                            shape="1;A>l;D.5,.6,l>l;R>l"), where=True)
        return next(i for i in range(1, len(rows)) if rows[i][2] == 4 and rows[i - 1][2] == 3) - 480
    t1, t2 = arrival(100), arrival(200)
    check("the Decay knob stretches the points inside the decay with it: half-way in at 100 ms and at 200 ms",
          abs(t1 - 2400) <= 1 and abs(t2 - 4800) <= 1, "%d and %d samples after the attack" % (t1, t2))
    null("a point kept in milliseconds would not move; this one did, by the whole difference", abs(t2 - t1) > 2000, "%d" % (t2 - t1))

    # --- the sustain point moved, and switched off ---
    ev = [(0, "gate 1 1"), (24000, "gate 0")]
    rows = trace(script(48000, 10, 100, 0.3, 100, ev, 48000, shape="1;A>l;D>l;R>l;S2"))
    check("held at the peak (S2), the shape holds at full scale while the key is down", abs(rows[20000][0] - 1) < 1e-12,
          "%.4f" % rows[20000][0])
    null("where it always holds, it would be at the sustain", abs(rows[20000][0] - 0.3) > 0.1)
    after = [rows[24000 + 2400][0], rows[24000 + 4799][0], rows[24000 + 9599][0]]
    check("let go, it plays the decay then the release from there", abs(after[0] - 0.65) < 0.01 and abs(after[1] - 0.3) < 0.01
          and after[2] < 0.01, "%.3f, %.3f, %.4f" % tuple(after))
    one_shot = trace(script(48000, 10, 100, 0.3, 100, [(0, "gate 1 1"), (240, "gate 0")], 48000, shape="1;A>l;D>l;R>l;S-"))
    check("a one-shot (S-) plays through whatever the key does: let go at 5 ms, it still reaches the peak and the sustain",
          max(r[0] for r in one_shot) > 0.999 and abs(one_shot[480 + 4799][0] - 0.3) < 0.01 and one_shot[-1][1] == 0,
          "peak %.3f, %.3f at the decay's end, stage %d at the end" % (max(r[0] for r in one_shot), one_shot[480 + 4799][0], one_shot[-1][1]))
    normal = trace(script(48000, 10, 100, 0.3, 100, [(0, "gate 1 1"), (240, "gate 0")], 48000, shape="1;A>l;D>l;R>l"))
    null("the same shape with its sustain lets go at 5 ms and never reaches the peak", max(r[0] for r in normal) < 0.6,
         "peak %.3f" % max(r[0] for r in normal))
    held_one = trace(script(48000, 10, 100, 0.3, 100, [(0, "gate 1 1")], 48000, shape="1;A>l;D>l;R>l;S-"))
    check("and held, a one-shot does not stop at the sustain: it ends in silence with the key still down",
          held_one[-1][0] == 0 and held_one[-1][1] == 0, "%.4f, stage %d" % held_one[-1])
    again = trace(script(48000, 10, 100, 0.3, 100, [(0, "gate 1 1"), (240, "gate 0"), (2400, "gate 1 1")], 48000,
                         shape="1;A>l;D>l;R>l;S-"), where=True)
    check("a key struck afresh starts a one-shot again", again[2399][2] >= 3 and again[2400][2] <= 1,
          "segment %d then %d" % (again[2399][2], again[2400][2]))
    legato = trace(script(48000, 10, 100, 0.3, 100, [(0, "gate 1 1"), (2400, "gate 1 1")], 48000,
                          shape="1;A>l;D>l;R>l;S-"), where=True)
    null("and a legato key on one still held does not", legato[2400][2] >= 3, "segment %d" % legato[2400][2])

    # --- the delay and the hold ---
    rows = trace(script(48000, 10, 100, 0.5, 100, [(0, "gate 1 1"), (48000, "gate 0")], 48000, shape=OLD,
                        extra=("tone delayMs 50", "tone holdMs 100")))
    check("a delay of 50 ms is silence before the attack, and a hold of 100 ms full scale after it",
          rows[2398][0] == 0 and rows[2400 + 480 + 10][0] > 0.99 and rows[2400 + 480 + 4790][0] > 0.99 and rows[2400 + 480 + 4800 + 2400][0] < 0.99,
          "%.3f, %.3f, %.3f, %.3f" % (rows[2398][0], rows[2400 + 480 + 10][0], rows[2400 + 480 + 4790][0], rows[2400 + 480 + 4800 + 2400][0]))
    plain = trace(script(48000, 10, 100, 0.5, 100, [(0, "gate 1 1"), (48000, "gate 0")], 48000, shape=OLD))
    null("without them it is already sounding at 50 ms", plain[2398][0] > 0.4, "%.3f" % plain[2398][0])
