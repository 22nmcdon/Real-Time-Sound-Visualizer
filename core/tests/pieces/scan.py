"""Scan (P7a) on the core: the reading, the tick, the voice, the freeze and
the hold. scantest.py's numbers rows.

These were scantest.py's on `?brain=js&core=js` until stage 5, step 3, batch
3 (13 Nov): `scanTables`, `scanRead`, `scanGeometry` and `scanFollow` called
in the page on readings and grids made there, and a `makeGeneratorCore`
built in the page with tables put into it by `core.set('scanTable', ...)`.
Here the same claims on the core alone: the reading's pieces through
scan_cpp's own commands (`tables`, `geometry`, `follow`, `read`), the voice
through generator_cpp with a table put in as `scan LAYER T:...` - the
tables themselves made by the core's `scanTables` - and the frame's freeze
and hold through scan_cpp's frames. The figures are the suite's: a curve in
polar form laid as thin lines on a 64-cell grid. The expectations are numpy's
(the bend's hand reading is written here from wave.h's rule, not borrowed
from the core). Each check has its null beside it.
"""
import math

import numpy as np

N = 64
POINTS = 256           # kScanPoints
MOST = 0.8             # kScanMost
TRAILER = 17


def figure(kind="circle", R=0.25, cx=0.5, cy=0.5, k=3, turn=0.0, level=1.0):
    """scantest's GRID: a curve about a centre, laid as thin lit lines."""
    g = np.zeros(N * N)
    for s in range(20000):
        t = 2 * math.pi * s / 20000
        r = R * (math.cos(k * t) if kind == "rose" else 1)
        x, y = cx + r * math.cos(t + turn), cy + r * math.sin(t + turn)
        i, j = math.floor(x * N), math.floor(y * N)
        if 0 <= i < N and 0 <= j < N: g[j * N + i] = level
    return g


def grid_line(name, g):
    return "grid %s %s" % (name, ",".join(repr(float(v)) for v in g))


def rows(kit, lines):
    return [[float(v) for v in l.split()] for l in kit.run("scan_cpp", "\n".join(lines)).strip().split("\n")]


def tables_of(row):
    """A `7 most count (len values)...` row as (most, [levels]); None for darkness (8)."""
    if row[0] == 8: return None
    assert row[0] == 7, row[:3]
    levels, k = [], 3
    for _ in range(int(row[2])):
        n = int(row[k]); levels.append(np.array(row[k + 1:k + 1 + n])); k += 1 + n
    return row[1], levels


def tables(kit, points_list):
    return [tables_of(r) for r in rows(kit, ["tables pts=" + ",".join(repr(float(v)) for v in p) for p in points_list])]


def points(f):
    return np.array([f(2 * math.pi * i / POINTS) for i in range(POINTS)])


def from_harmonics(h):
    """A reading from [k, amplitude, phase] triples, as the suite's CORE built one."""
    i = np.arange(POINTS)
    return sum(a * np.cos(2 * np.pi * k * i / POINTS + (ph[0] if ph else 0)) for k, a, *ph in h)


def did(r):
    """What a frame did, scan_cpp's row read as parity's sdid reads it: a
    hold sent (hold, layer, value) and a table sent (table, layer)."""
    out, k = [], 0
    while k < len(r) and r[k] in (1, 2):
        if r[k] == 1: out.append(("hold", int(r[k + 1]), r[k + 2])); k += 3
        else:
            out.append(("table", int(r[k + 1]))); n = int(r[k + 3]); k += 4
            for _ in range(n): k += 1 + int(r[k])
    return out


def ttext(t):
    most, levels = t
    return "T:%r:%s" % (most, ";".join(",".join(repr(float(v)) for v in L) for L in levels))


def harmonics(table, top=80):
    return (np.abs(np.fft.rfft(np.asarray(table, dtype=float))) / len(table) * 2)[:top + 1]


def lowest(table, share=0.1):
    h = harmonics(table, 64)[1:] ** 2
    return int(np.argmax(h / h.sum() > share)) + 1


def gen(kit, tone, events=(), samples=4410, rate=44100, toneB=None):
    """generator_cpp, as the suite's CORE: amp a half, no interval, no phase,
    then the tone's fields, B's, and the events (sample, words) - each at a
    multiple of 128, the tool's block. The six lanes, the first `samples`."""
    ev = ["at 0 set amp 0.5", "at 0 set interval 0", "at 0 set phase 0"]
    for layer, t in ((0, tone), (1, toneB or {})):
        for k, v in t.items():
            if k == "voices":
                ev.append("at 0 voices %d %s" % (layer, "+".join("%d/%r/%r/u" % (n, f, vel) for n, f, vel in v)))
            else:
                ev.append("at 0 set %s %s %d" % (k, v if isinstance(v, str) else repr(v), layer))
    for at, words in events:
        assert at % 128 == 0, at
        ev.append("at %d %s" % (at, words))
    text = "run rate=%r slots=40 seed=3 samples=%d\n%s\nend" % (float(rate), samples, "\n".join(ev))
    body = np.array(kit.floats("generator_cpp", text)[:-TRAILER])
    return [body[k::6][:samples] for k in range(6)]


def cycle_read(levels, most, phase, step):
    """wave.h's cycleRead, written again here: the level by the step, read
    linearly round the table, and the next level mixed in by how far past."""
    t = (phase / (2 * math.pi)) % 1.0
    top = len(levels) - 1
    lo, w = 0, 0.0
    if step > 0:
        f = math.log2(most * 2 * step)
        lo = int(max(0, min(top, math.ceil(f))))
        w = max(0.0, min(1.0, f - lo + 1)) if lo < top else 0.0
    def read(tab):
        x = t * len(tab); i = math.floor(x); fr = x - i
        a, b = tab[i % len(tab)], tab[(i + 1) % len(tab)]
        return a + (b - a) * fr
    a = read(levels[lo])
    return a + (read(levels[lo + 1]) - a) * w if w > 0 else a


def run(kit):
    check, null = kit.check, kit.null

    # --- the reading ---
    three, quiet, rich, flat, dim, faint = tables(kit, [
        points(lambda x: 0.4 + 0.3 * math.cos(3 * x + 0.7)), points(lambda x: 0.04 + 0.03 * math.cos(3 * x + 0.7)),
        points(lambda x: math.cos(x) + 0.5 * math.cos(50 * x)), points(lambda x: 0.3),
        points(lambda x: 0.3 + 5e-5 * math.cos(x)), points(lambda x: 0.3 + 5e-3 * math.cos(x))])
    t3 = three[1][0]
    n = len(t3)
    want = np.cos(3 * 2 * np.pi * np.arange(n) / n + 0.7)
    want /= np.abs(want).max()
    err = float(np.abs(t3 - want).max())
    check("a reading's table is its harmonics, evened to a peak of one, with no DC", err < 1e-9,
          "%d levels of %d, most %g, error %.1e" % (len(three[1]), n, three[0], err))
    wrong = float(np.abs(t3 - np.cos(2 * 2 * np.pi * np.arange(n) / n + 0.7)).max())
    null("the same table against the second harmonic", wrong > 0.5, "%.2f" % wrong)
    q = float(np.abs(quiet[1][0] - t3).max())
    check("a picture ten times dimmer reads the same table: the picture cannot make the voice quieter", q < 1e-9, "%.1e" % q)
    null("the dim table against the bright one unevened, a tenth of it", float(np.abs(quiet[1][0] * 0.1 - t3).max()) > 0.5)
    h0, h1 = harmonics(rich[1][0]), harmonics(rich[1][1])
    check("the second level leaves out what the first has past its 32nd harmonic", h1[33:].max() < 1e-9 and h0[50] > 0.2,
          "level 1 above 32: %.1e; level 0 at 50: %.3f" % (h1[33:].max(), h0[50]))
    null("the first level past its 32nd, where the 50th is", h0[33:].max() > 0.2, "%.3f" % h0[33:].max())
    check("a flat reading is darkness, and so is one under SCAN_DARK: no table, so the last is held", flat is None and dim is None)
    null("a faint reading over SCAN_DARK is not darkness", faint is not None)

    # The off-centre path: a three-petalled rose read from off its centre
    # and from its centre (the path moved back by the offset scanRead adds).
    rose = figure("rose", R=0.3, k=3)
    g = rows(kit, [grid_line("rose", rose), "geometry g=rose"])[0]
    cx, cy, r = g[1:4]
    rr = max(r, 2 / N)
    off, centred = rows(kit, [grid_line("rose", rose), "read g=rose soft=1.5 cx=%r cy=%r r=%r" % (cx, cy, r),
                              "read g=rose soft=1.5 cx=%r cy=%r r=%r" % (cx - 0.35 * rr, cy - 0.2 * rr, r)])
    t_off, t_c = tables(kit, [off[1:], centred[1:]])
    lo_off, lo_c = lowest(t_off[1][0]), lowest(t_c[1][0])
    check("an off-centre path reads a three-petalled rose at its fundamental", lo_off == 1,
          "lowest harmonic with a tenth of the energy: %d (centre at %.3f, %.3f, radius %.3f)" % (lo_off, cx, cy, r))
    null("the same rose read from its centre plays three times too high, as P2 found", lo_c == 3, "%d" % lo_c)

    circle = figure("circle", R=0.25, cx=0.45, cy=0.55)
    g = rows(kit, [grid_line("c", circle), "geometry g=c"])[0]
    raw, soft = rows(kit, [grid_line("c", circle)] + ["read g=c soft=%r cx=%r cy=%r r=%r" % (s, g[1], g[2], g[3]) for s in (0, 3)])
    t_raw, t_soft = tables(kit, [raw[1:], soft[1:]])
    def top_share(table):
        h = harmonics(table, 64)[1:] ** 2
        return float(h[15:].sum() / h.sum())
    sr, ss = top_share(t_raw[1][0]), top_share(t_soft[1][0])
    check("three cells of softness take the spikes out: the share above the 16th harmonic falls tenfold", ss < sr / 10,
          "raw %.3f, soft %.4f" % (sr, ss))
    null("the raw reading against itself", not (sr < sr / 10))

    # Not the page's: the blur's kernel sums to one, which no check above
    # could see, since a table is evened to its peak whatever the light (the
    # mutation pass of batch 3 found it). A figure just dim enough to read as
    # darkness through three cells of softness, and the same twice as bright,
    # which does not: a kernel summing to two would read the first as light.
    # The level is fixed, not found from a reading here, so a mutant blur
    # cannot move it with itself: at 0.0012 the reading's spread is about
    # 0.7e-4, under SCAN_DARK's 1e-4, and twice it is over.
    edge = 0.0012
    dimmed = rows(kit, [grid_line("d1", circle * edge), grid_line("d2", circle * 2 * edge)]
                  + ["read g=%s soft=3 cx=%r cy=%r r=%r" % (nm, g[1], g[2], g[3]) for nm in ("d1", "d2")])
    t_d1, t_d2 = tables(kit, [dimmed[0][1:], dimmed[1][1:]])
    check("a figure dim enough reads darkness through the softness: the blur adds no light", t_d1 is None,
          "a figure at %.3g of full" % edge)
    null("and the same twice as bright is a table", t_d2 is not None)

    a, b = figure("circle", R=0.2, cx=0.3), figure("circle", R=0.2, cx=0.7)
    fl = rows(kit, [grid_line("a", a), grid_line("b", b), grid_line("dark", np.zeros(N * N)), "follow forget",
                    "follow g=a dt=0.016"] + ["follow g=b dt=%r" % (1 / 60)] * 60 + ["follow g=dark dt=1", "geometry g=b"])
    start, after, dark, target = fl[0][1], fl[60][1], fl[61][1], fl[62][1]
    frac = (after - start) / (target - start)
    check("the path follows the figure over about a second: 63 per cent of the way after one",
          abs(frac - (1 - math.exp(-1))) < 0.01, "%.3f of the way" % frac)
    null("that against all of the way", not (abs(frac - 1) < 0.01), "%.3f" % frac)
    check("and holds where it was over darkness", dark == after and fl[61][2:] == fl[60][2:])
    null("a lit grid does move it", fl[1][1] != fl[0][1])

    # --- the tick ---
    TA, TB = tables(kit, [from_harmonics([[3, 1]]), from_harmonics([[5, 1]])])
    tone = {"shape": "sine", "freq": 220, "scan": 1}
    for rate in (44100, 48000, 22050):
        per = rate / 60
        ticks, rest, clock = [], [], 0.0
        for i in range(int(per * 8)):
            clock += 1
            if clock >= per: clock -= per; ticks.append(i); rest.append(clock)
        # Two block edges inside one tick, and one inside the next: the tool
        # takes a table only at a block's edge, where the page's run took it
        # anywhere; a tenth and nine tenths in were the page's places.
        inside = lambda k: [m for m in range(0, int(per * 8), 128) if ticks[k] + 2 <= m <= ticks[k + 1] - 1]
        x_at, y_at, z_at = inside(3)[0], inside(3)[-1], inside(4)[0]
        assert x_at != y_at, rate
        total = int(per * 8)
        set_at = lambda at: gen(kit, tone, [(0, "scan 0 " + ttext(TA)), (at, "scan 0 " + ttext(TB))], total, rate)[0]
        x, y, z = set_at(x_at), set_at(y_at), set_at(z_at)
        same = float(np.abs(x - y).max())
        first = int(np.argmax(np.abs(x - z) > 0))
        check("at %d Hz a table sent anywhere in a tick lands at the next, to the sample" % rate, same == 0,
              "sent at %d and %d, between ticks at %d and %d: largest difference %.1e" % (x_at, y_at, ticks[3], ticks[4], same))
        part = ticks[4] + (0 if rest[4] > 0 else 1)
        check("at %d Hz and one sent a tick later lands a tick later: they part at sample %d" % (rate, part),
              first == part, "first difference at %d" % first)
        null("at %d Hz, a table landing when sent would part where it was sent" % rate, first != x_at)

    per, ticks = 735, [734 + 735 * k for k in range(8)]
    TC = tables(kit, [from_harmonics([[5, 1, 0.4]])])[0]
    one = gen(kit, tone, [(0, "scan 0 " + ttext(TA))])[0]
    two = gen(kit, tone, [(0, "scan 0 " + ttext(TC))])[0]
    fade = gen(kit, tone, [(0, "scan 0 " + ttext(TA)), (1536, "scan 0 " + ttext(TC))])[0]
    i = np.arange(4410)
    x_of = np.clip((i - ticks[2]) / per, 0, 1)
    pred = one + (two - one) * x_of
    span = i >= ticks[1] + 1
    errf = float(np.abs(fade[span] - pred[span]).max())
    check("the crossfade is a straight line across one tick, from the last table to the new one", errf < 1e-6,
          "worst %.1e over samples %d to 4410" % (errf, ticks[1] + 1))
    step = one + (two - one) * (i > ticks[2])
    null("the same against a step at the tick", float(np.abs(fade[span] - step[span]).max()) > 0.01)
    half = one + (two - one) * np.clip((i - ticks[2]) / (per / 2), 0, 1)
    null("and against a crossfade half a tick long", float(np.abs(fade[span] - half[span]).max()) > 0.01)

    # --- the voice ---
    TAB = tables(kit, [from_harmonics([[3, 1], [2, 0.5, 1.1]])])[0]
    put = [(0, "scan 0 " + ttext(TAB))]
    for label, tn in [("dyad", {"shape": "harmonic", "freq": 330, "interval": 7}),
                      ("chord", {"shape": "ramp", "voices": [(60, 261.63, 1), (64, 329.63, 1)]}),
                      ("unison", {"shape": "square", "freq": 220, "unison": 3})]:
        plain, zero, nudged = gen(kit, tn), gen(kit, tn, put), gen(kit, dict(tn, scan=0.01), put)
        d0, d0r = float(np.abs(plain[0] - zero[0]).max()), float(np.abs(plain[1] - zero[1]).max())
        d1, d1r = float(np.abs(plain[0] - nudged[0]).max()), float(np.abs(plain[1] - nudged[1]).max())
        check("%s: a table at a depth of nought changes nothing, to the bit, either side" % label, d0 == 0 and d0r == 0,
              "%.1e, %.1e" % (d0, d0r))
        null("%s: at a depth of 0.01 it does, either side" % label, d1 > 1e-5 and d1r > 1e-5, "%.1e, %.1e" % (d1, d1r))

    f = 441.0
    TP = tables(kit, [from_harmonics([[1, 1], [4, 0.7, 0.3], [7, 0.4, 2]])])[0]
    s = gen(kit, {"shape": "sine", "freq": f, "scan": 1}, [(0, "scan 0 " + ttext(TP))], 8820)[0][2205:8000]
    per_err, off1 = float(np.abs(s[100:] - s[:-100]).max()), float(np.abs(s[101:] - s[:-101]).max())
    check("Scan plays at the note's pitch: the wave repeats every cycle of the note", per_err < 1e-5, "%.1e a period apart" % per_err)
    null("a period and a sample apart", off1 > 0.01, "%.3f" % off1)

    def fundamental(x):
        x = np.asarray(x[2205:2205 + 4410]); k = np.arange(len(x))
        return abs(np.sum(x * np.exp(-2j * np.pi * f * k / 44100))) * 2 / len(x)
    T2 = tables(kit, [from_harmonics([[2, 1]])])[0]
    sine = fundamental(gen(kit, {"shape": "sine", "freq": f}, (), 8820)[0])
    for depth, hold, keep in [(1, 1, 1 - 0.8), (1, 0.25, 1 - 0.2), (0.5, 1, 1 - 0.4)]:
        got = fundamental(gen(kit, {"shape": "sine", "freq": f, "scan": depth, "scanHold": hold},
                              [(0, "scan 0 " + ttext(T2))], 8820)[0]) / sine
        check("depth %.1f under a hold of %.2f keeps %.2f of the shape: the note never loses its fundamental" % (depth, hold, keep),
              abs(got - keep) < 0.005, "%.4f" % got)
        null("depth %.1f, hold %.2f: against the whole voice taken, nothing kept" % (depth, hold), abs(got - 0) > 0.1)

    # The bend reaches what Scan reads: the same table read at the bent phase,
    # by hand, over the shape bent the same way, with the bend's offset taken
    # off the sine put back (J1(a) sin c), as the suite's hand did.
    ta, c, fb = 0.6, 0.3, 220.0
    TW = tables(kit, [from_harmonics([[1, 1], [3, 0.6, 0.5]])])[0]
    bent = gen(kit, {"shape": "sine", "freq": fb, "scan": 1, "warp": ta, "warpAt": c}, [(0, "scan 0 " + ttext(TW))], 8820)[0]
    j1, term = 0.0, ta / 2
    for k in range(12): j1 += term; term *= -(ta / 2) * (ta / 2) / ((k + 1) * (k + 2))
    dc = j1 * math.sin(2 * math.pi * c)
    hand, flat_hand = [], []
    for k in range(2205, 8820):
        ph = 2 * math.pi * fb * (k + 1) / 44100; d = ph - 2 * math.pi * c
        qph = ph + ta * math.sin(d); stp = abs(fb * (1 + ta * math.cos(d))) / 44100
        ink = math.sin(qph) + dc
        hand.append(0.5 * (ink + (cycle_read(TW[1], TW[0], qph, stp) - ink) * MOST))
        flat_hand.append(0.5 * (ink + (cycle_read(TW[1], TW[0], ph, fb / 44100) - ink) * MOST))
    eb, ef = float(np.abs(bent[2205:] - np.array(hand)).max()), float(np.abs(bent[2205:] - np.array(flat_hand)).max())
    check("the bend bends what Scan reads, not only the shape under it", eb < 1e-6, "%.1e" % eb)
    null("the same against Scan read at the unbent phase", ef > 0.01, "%.3f" % ef)

    # Not the page's: the table is read band-limited by the note's step, as
    # cycleRead reads a drawn cycle - a level with fewer harmonics as the
    # pitch rises. The bend's table above has nothing past the 32nd harmonic,
    # where the levels part, so it could not see a voice reading the richest
    # level at every pitch (batch 3's mutation pass). At 2 kHz a 20th
    # harmonic is past Nyquist: the hand's reading with the step against the
    # sound, and the same reading without it as the null.
    fh = 2000.0
    TH = tables(kit, [from_harmonics([[1, 1], [20, 0.6, 0.3], [45, 0.4]])])[0]
    high = gen(kit, {"shape": "sine", "freq": fh, "scan": 1}, [(0, "scan 0 " + ttext(TH))], 8820)[0]
    by = lambda stp: np.array([0.5 * (math.sin(2 * math.pi * fh * (k + 1) / 44100)
                                      + (cycle_read(TH[1], TH[0], 2 * math.pi * fh * (k + 1) / 44100, stp)
                                         - math.sin(2 * math.pi * fh * (k + 1) / 44100)) * MOST) for k in range(2205, 8820)])
    eh, e0 = float(np.abs(high[2205:] - by(fh / 44100)).max()), float(np.abs(high[2205:] - by(0)).max())
    check("Scan's table is read band-limited by the note's step: at 2 kHz the levels past Nyquist are left out", eh < 1e-6, "%.1e" % eh)
    null("the same against the richest level read at every pitch", e0 > 0.01, "%.3f" % e0)

    # Layer B's Scan is B's. Its null was B's lanes against themselves, which
    # read nought whatever the core did (STAGE5-INVENTORY.md, surprise 6);
    # each half has its own now: the table and depth given to A instead do
    # move A's lanes, and given to B at a depth of nought do not move B's.
    lay = {"shape": "sine", "voices": [(48, 130.81, 1)]}
    layB = {"shape": "sine", "voices": [(72, 523.25, 1)]}
    T3 = tables(kit, [from_harmonics([[3, 1]])])[0]
    plainB = gen(kit, lay, toneB=layB)
    scanB = gen(kit, lay, [(0, "scan 1 " + ttext(T3))], toneB=dict(layB, scan=1))
    scanA = gen(kit, dict(lay, scan=1), [(0, "scan 0 " + ttext(T3))], toneB=layB)
    deep0 = gen(kit, lay, [(0, "scan 1 " + ttext(T3))], toneB=layB)
    dA, dB = float(np.abs(plainB[0] - scanB[0]).max()), float(np.abs(plainB[4] - scanB[4]).max())
    check("layer B's depth and table play in B's lanes and leave A's to the bit", dA == 0 and dB > 0.01,
          "A moved %.1e, B %.3f" % (dA, dB))
    null("given to A instead, A's lanes move", float(np.abs(plainB[0] - scanA[0]).max()) > 0.01,
         "%.3f" % float(np.abs(plainB[0] - scanA[0]).max()))
    null("and B's table at B's depth of nought leaves B's lanes as they were", float(np.abs(plainB[4] - deep0[4]).max()) == 0)

    TS = tables(kit, [from_harmonics([[1, 1], [2, 0.5]])])[0]
    sync = gen(kit, {"shape": "ramp", "freq": 220, "syncRatio": 2.3, "scan": 1}, [(0, "scan 0 " + ttext(TS))], 8820)[0]
    flat_s = gen(kit, {"shape": "ramp", "freq": 220, "syncRatio": 2.3}, (), 8820)[0]
    moved = float(np.mean(np.abs(sync - flat_s) > 0.01))
    check("under sync it is bounded and finite, and Scan is in nearly every sample, not only the restarts",
          bool(np.isfinite(sync).all()) and np.abs(sync).max() <= 0.5 + 1e-9 and moved > 0.5,
          "peak %.3f, %.0f%% of samples moved" % (np.abs(sync).max(), 100 * moved))
    # Its null was a mutant, on the page: Scan left out between restarts moved 0.5 per cent.

    # --- the frame: the freeze and the hold ---
    # A setup's landing: nothing read for a quarter of a second, by the
    # reader's clock (the instrument's freeze at each setup is parity's,
    # "the instrument reads nothing for a quarter of a second of audio after
    # each setup lands"). The page's run counted its own brain's posts.
    e = figure("circle", R=0.2, cx=0.42, cy=0.55, level=0.8)
    fr = lambda now, hs=1: "frame elapsed=16.67 now=%r spect=0 count=1 live=0 d0=1 d1=0 hs=%r gs=e" % (now, hs)
    out = [did(r) for r in rows(kit, [grid_line("e", e), "run soft=3", fr(0), fr(17), "freeze now=100"]
                                + [fr(100 + 17 * k) for k in range(20)])]
    tabled = [("table", 0) in d for d in out]
    after = [100 + 17 * k for k in range(20)]
    first = [t for t, s_ in zip(after, tabled[2:]) if s_]
    check("for a quarter of a second after a setup lands nothing is read, and then it is",
          not any(s_ for t, s_ in zip(after, tabled[2:]) if t < 350) and bool(first) and first[0] >= 350,
          "first table at %s ms, the setup at 100" % (first[:1],))
    null("and before it, a table every frame", tabled[0] and tabled[1], str(tabled[:2]))

    # The hold: a frame hands the stage's hold on to Scan's depth (`scanHold`)
    # once it has moved by more than 0.005, and one when it comes back.
    # Back to one by less than 0.005 is sent too, since it is one: 0.997
    # then one.
    hs = [did(r) for r in rows(kit, [grid_line("e", e), "run soft=3"] + [fr(17 * k, h) for k, h in
                                                                       enumerate((1, 0.25, 0.25, 0.252, 0.997, 1))])]
    holds = [[x[2] for x in d if x[0] == "hold"] for d in hs]
    check("a stage held to a quarter holds Scan's depth to a quarter, sent once, and the end of it sent back",
          holds == [[], [0.25], [], [], [0.997], [1]], str(holds))
    null("at a hold of one, nothing is sent, and a move under 0.005 is not", holds[0] != [1] and holds[3] != [0.252])

    # And a screen full of light is running away, which holds the stage to
    # a quarter (picture_cpp: the whole grid laid every frame, as the page's
    # run filled it every 5 ms, and the frame stepped). With the two above,
    # the page's claim: the hold reins Scan's depth in to a quarter, as the
    # stage's. The null is the same frames on a dark screen.
    def stage(full):
        lines = ["run", "plot 0 0 64 64", "persist 0.12", "pair ellipse 0.5 0.3 4 1024 0.4"]
        for _ in range(420):
            lines.append("fade 0")
            if full: lines += ["seg 0 %r 64 %r 1" % (y + 0.5, y + 0.5) for y in range(N)]
            lines.append("step 16.67")
        lines.append("end")
        last = [l for l in kit.run("picture_cpp", "\n".join(lines)).strip().split("\n") if l.startswith("step")][-1].split()
        at = last.index("stage")
        return float(last[at + 4]), last[last.index("meter") + 6]
    full, dark = stage(True), stage(False)
    check("a screen full of light is running away, and holds the stage to a quarter", full[1] == "running" and abs(full[0] - 0.25) < 1e-9,
          "hold %.4f, verdict ...%s" % full)
    null("a dark screen holds nothing", dark[0] == 1, "hold %.4f, verdict ...%s" % dark)
