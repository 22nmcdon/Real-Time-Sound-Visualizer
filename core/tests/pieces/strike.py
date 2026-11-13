"""The strike and cross-scan (P7b) on the core: striketest.py's numbers rows.

These were striketest.py's on `?brain=js&core=js` until stage 5, step 3,
batch 3 (13 Nov): the page's keyboard struck its own picture engine on a
stopped screen, with `scan.paths` and each layer's stage hold written by
hand, and the grid, the reading and the tables were read back through the
page's `scanRead` and `scanTables`. Here the same claims on the core alone:
the strike through scope::ScanReader::strike and laid through a
scope::Phosphor, as the instrument lays it (scan_cpp's `laid`, `strike` and
`path`); the light's fade and the meter through picture_cpp; cross-scan
through scan_cpp's frames with two pictures; and the one preset the suite
played, Crossed hands, through the whole instrument (instrument_cpp's
`reads`). What the instrument's own keyboard does with a note - its velocity
as a fraction of 127, Strike from the slider, the split's layer - is parity's
already ("the instrument's note strikes its own screen ...", "in a split, the
upper note lands in B's picture ..."), and the site leg of striketest.py
plays it. Each check has its null beside it.
"""
import base64, json, math, os

import numpy as np

from pieces.scan import N, did, figure, grid_line, rows, tables, tables_of

PLOT = "40,20,600,400"
HERE = os.path.dirname(os.path.abspath(__file__))


def corpus_code(name):
    """An old-library preset's setup code, as parity's ocode_of writes it."""
    with open(os.path.join(HERE, "..", "scenarios", "library-p8f.json"), encoding="utf-8") as f:
        for _, entries, _ in json.load(f):
            for entry in entries:
                if entry[0] == name:
                    return base64.b64encode(json.dumps(dict(entry[1], v=7)).encode()).decode().rstrip("=")
    raise KeyError(name)


def strike_words(note, vel, amount=0.5, d0=1, d1=0, count=1, split=0, live=None, reads=None, gs="dark"):
    tail = "" if not reads else " r0=%s r1=%s" % reads
    pics = "live=1 g0=%s g1=%s" % live if live else "live=0 hs=1 gs=%s" % gs
    return "note=%d vel=%r amount=%r split=%d point=60 plot=%s spect=0 count=%d d0=%r d1=%r %s%s" % (
        note, vel, amount, split, PLOT, count, d0, d1, pics, tail)


def laid(lines):
    """`laid` rows (10 count rose) as (count, rose)."""
    return [(int(r[1]), r[2]) for r in rows(kit_, lines) if r[0] == 10]


kit_ = None


def run(kit):
    global kit_
    kit_ = kit
    check, null = kit.check, kit.null
    dark = np.zeros(N * N)
    head = [grid_line("dark", dark), "run soft=3"]

    # --- the strike ---
    vel = 100 / 127
    got = laid(head + ["laid into=x base=dark pic=-1 " + strike_words(60, 1.0, amount=0),
                       "laid into=x base=dark pic=-1 " + strike_words(60, 1.0, d0=0),
                       "laid into=x base=dark pic=-1 " + strike_words(60, 1.0),
                       "laid into=x base=dark pic=-1 " + strike_words(60, vel)])
    check("Strike at nought lays nothing at all", got[0] == (0, 0), str(got[0]))
    check("and neither does a strike with Scan off, since there is no reading for it to be in", got[1] == (0, 0), str(got[1]))
    null("with Scan on and Strike at half, a note lays light", got[2][0] > 0 and got[2][1] > 0.1, str(got[2]))
    want = vel * 0.5
    check("a note lays light as bright as its velocity times the Strike amount", abs(got[3][1] - want) < 1e-6,
          "%.6f against %.6f" % (got[3][1], want))
    null("not its velocity alone", abs(got[3][1] - vel) > 0.1, "%.4f" % vel)

    # Where: a dark screen, the path put in, read unblurred (the softness
    # would spread a one-cell arc over seven and hide where it lies).
    x0, y0, w, h = (float(v) for v in PLOT.split(","))
    cxp, cyp = x0 + 0.5 * w, y0 + 0.5 * h
    path = "cx=0.5 cy=0.5 r=0.25"
    rd = rows(kit, head + ["path p=0 " + path,
                           "laid into=c base=dark pic=-1 " + strike_words(60, vel),
                           "laid into=f base=dark pic=-1 " + strike_words(66, vel),
                           "laid into=m base=dark plot=%s seg=%r,%r,%r,%r,%r" % (PLOT, cxp - 0.05 * w, cyp, cxp + 0.05 * w, cyp, want),
                           "read g=dark soft=0 " + path, "read g=c soft=0 " + path, "read g=f soft=0 " + path,
                           "read g=m soft=0 " + path])
    r0, rC, rF, rM = (np.array(r[1:]) for r in rd if r[0] == 9)
    rise = {"C": rC - r0, "F": rF - r0, "centre": rM - r0}
    n = len(r0)
    def place(r):
        wgt = np.maximum(r, 0); th = 2 * np.pi * np.arange(n) / n
        return int(round((np.arctan2((wgt * np.sin(th)).sum(), (wgt * np.cos(th)).sum()) % (2 * np.pi)) / (2 * np.pi) * n)) % n
    peakC, peakF = place(rise["C"]), place(rise["F"])
    check("it is laid where Scan reads: the reading, unblurred, rises by over half the light it laid",
          rise["C"].max() > 0.5 * want, "%.3f of %.3f" % (rise["C"].max(), want))
    null("the same light laid through the figure's centre barely reaches the reading",
         rise["centre"].max() < 0.1 * want and rd[2][1] == 1 and rd[2][2] > 0.1, "%.4f" % rise["centre"].max())
    dist = lambda a, b: min(abs(a - b), n - abs(a - b))
    check("each note strikes its own place round the circle: C at the reading's start, F sharp half a lap on",
          dist(peakC, 0) <= n // 64 and dist(peakF, n // 2) <= n // 64, "C at %d, F sharp at %d" % (peakC, peakF))
    null("not both in one place", dist(peakC, peakF) > n // 4, "%d apart" % dist(peakC, peakF))

    # A soft and a hard note on a figure: the next table. The figure's path
    # as the reader takes it the first time, its geometry.
    fig = figure("rose", R=0.28, cx=0.47, cy=0.52, k=3, turn=0.3, level=0.6)
    gl = [grid_line("fig", fig)]
    g = rows(kit, gl + ["geometry g=fig"])[0]
    fp = "cx=%r cy=%r r=%r" % tuple(g[1:4])
    tr = rows(kit, gl + ["run soft=3", "path p=0 " + fp] + [
        "laid into=%s base=fig pic=-1 %s" % (nm, strike_words(62, v, gs="fig")) for nm, v in
        (("soft", 30 / 127), ("soft2", 30 / 127), ("hard", 1.0))] + ["read g=%s soft=3 %s" % (nm, fp) for nm in ("fig", "soft", "soft2", "hard")])
    t0, tS, tS2, tH = (t[1][0] for t in tables(kit, [r[1:] for r in tr if r[0] == 9]))
    d = lambda a, b: float(np.mean(np.abs(a - b)))
    check("a harder note changes the next table more: over twice what a soft one does", d(tH, t0) > 2 * d(tS, t0),
          "%.4f against %.4f" % (d(tH, t0), d(tS, t0)))
    null("the same soft note twice makes the same table", d(tS, tS2) < 1e-9, "%.2g" % d(tS, tS2))
    null("and the soft note did move it", d(tS, t0) > 1e-4, "%.4f" % d(tS, t0))

    # --- the light fades as the screen's does ---
    # The strike's segments, as scan_cpp's `strike` gives them, laid through
    # picture_cpp's phosphor and faded frame by frame.
    seg = rows(kit, head + ["path p=0 " + path, "strike " + strike_words(60, 1.0, amount=1)])[0]
    segs = [seg[k:k + 7] for k in range(0, len(seg), 7)]
    persist, frames = 0.04, 18
    lines = ["run", "plot %s" % PLOT.replace(",", " "), "persist %r" % persist]
    lines += ["seg %r %r %r %r %r" % tuple(s[2:7]) for s in segs if s[1] == -1]
    lines += ["fade 0"] * frames + ["end"]
    sums = [float(l.split()[3]) for l in kit.run("picture_cpp", "\n".join(lines)).strip().split("\n")]
    v0, v1 = sums[len(lines) - frames - 3], sums[-1]   # after the last segment (every command prints), and after the fades
    expect = v0 * (1 - persist) ** frames
    check("the strike's light fades exactly by the screen's Persistence, frame by frame, as a stroke does",
          v0 > 0 and abs(v1 - expect) < 1e-4 * v0, "%.5f of it after %d frames, %.5f expected" % (v1 / v0, frames, expect / v0))
    null("not by an envelope of its own: three frames more or fewer would be another value",
         abs(v1 - v0 * (1 - persist) ** (frames + 3)) > 1e-3 * v0 and abs(v1 - v0 * (1 - persist) ** (frames - 3)) > 1e-3 * v0)

    # --- the meter sees it ---
    # Four notes struck on a dark screen at Strike full and at nought, laid
    # through picture_cpp's phosphor and the frame stepped: what the meter
    # lights is what the strikes laid.
    def metered(amount):
        sl = []
        for note in (60, 63, 66, 69):
            r = rows(kit, head + ["strike " + strike_words(note, 1.0, amount=amount)])[0]
            if r != [6]: sl += [r[k:k + 7] for k in range(0, len(r), 7) if r[k + 1] == -1]
        lines = ["run", "plot %s" % PLOT.replace(",", " "), "persist 0.04", "pair ellipse 0.001 0.001 1 256 0"]
        lines += ["fade 0", "step 16.67"] * 3
        lines += ["seg %r %r %r %r %r" % tuple(s[2:7]) for s in sl] + ["fade 0", "step 16.67", "end"]
        steps = [l.split() for l in kit.run("picture_cpp", "\n".join(lines)).strip().split("\n") if l.startswith("step")]
        lit = lambda w: float(w[w.index("meter") + 2])
        return lit(steps[2]), lit(steps[3]), len(sl)
    # What four full strikes lay, a fraction of the screen as the meter's soft sum counts it.
    lay4 = head + ["laid into=s1 base=dark pic=-1 " + strike_words(60, 1.0, amount=1)] + [
        "laid into=s%d base=s%d pic=-1 %s" % (k + 2, k + 1, strike_words(note, 1.0, amount=1)) for k, note in enumerate((63, 66, 69))]
    cells = rows(kit, lay4 + ["show g=s4"])[-1]
    laid_share = float(np.minimum(1, np.array(cells)).sum()) / len(cells)
    b1, a1, n1 = metered(1)
    b0, a0, n0 = metered(0)
    check("the picture meter, which the stage and the running-away hold read, lights with what a strike laid",
          laid_share > 0.001 and a1 - b1 > 0.5 * laid_share, "lit %.5f -> %.5f, laid %.5f, %d segments" % (b1, a1, laid_share, n1))
    null("the same notes at Strike nought light nothing", n0 == 0 and abs(a0 - b0) < 0.1 * laid_share, "%.5f -> %.5f" % (b0, a0))

    # --- a split: each layer's strikes ---
    pics = lambda r: None if r == [6] else sorted(set(int(r[k + 1]) for k in range(0, len(r), 7)))
    sp = rows(kit, head + ["strike " + strike_words(86, 1.0, d1=1, count=2, split=1, live=("dark", "dark")),
                           "strike " + strike_words(50, 1.0, d1=1, count=2, split=1, live=("dark", "dark"))])
    check("in a split a note above the split strikes B's picture and not A's", pics(sp[0]) == [-1, 1], str(pics(sp[0])))
    null("and one below strikes A's", pics(sp[1]) == [-1, 0], str(pics(sp[1])))

    # --- cross-scan: the table each layer plays, and the holds ---
    ea, eb = figure("rose", R=0.3, cx=0.45, cy=0.5, k=3, turn=0.2), figure("circle", R=0.2, cx=0.55, cy=0.45)
    gg = [grid_line("ea", ea), grid_line("eb", eb)]
    def frame(now, reads, h=(1, 1)):
        return ("frame elapsed=16.67 now=%r spect=0 count=2 live=1 d0=1 d1=1 h0=%r h1=%r g0=ea g1=eb r0=%s r1=%s"
                % (now, h[0], h[1], reads[0], reads[1]))
    def tables_and_paths(r):
        """A frame row's tables sent, by layer, and its pictures' paths."""
        out, paths, k = {}, {}, 0
        while k < len(r) and r[k] in (1, 2):
            if r[k] == 1: k += 3
            else:
                n_ = int(r[k + 3]); start = k; k += 4
                for _ in range(n_): k += 1 + int(r[k])
                out[int(r[start + 1])] = tables_of([7] + r[start + 2:k])
        while k < len(r):
            if r[k] == 3: paths[int(r[k + 1])] = r[k + 2:k + 5]; k += 5
            else: k += 2
        return out, paths
    def reads_at(path_):
        return "cx=%r cy=%r r=%r" % tuple(path_)
    fr = rows(kit, gg + ["run soft=1.5", frame(0, ("B", "A"))])
    sent, paths = tables_and_paths(fr[0])
    rr = rows(kit, gg + ["read g=ea soft=1.5 " + reads_at(paths[0]), "read g=eb soft=1.5 " + reads_at(paths[1])])
    ownA, fromB = tables(kit, [rr[0][1:], rr[1][1:]])
    dmax = lambda x, y: float(np.abs(x[1][0] - y[1][0]).max())
    check("crossed, A plays a table made from B's picture, and B from A's",
          dmax(sent[0], fromB) == 0 and dmax(sent[1], ownA) == 0, "%.2g, %.2g" % (dmax(sent[0], fromB), dmax(sent[1], ownA)))
    null("A's table against one made from its own picture", dmax(sent[0], ownA) > 0.01, "%.3f" % dmax(sent[0], ownA))
    fb = rows(kit, gg + ["run soft=1.5", frame(0, ("both", "B"))])
    sentB, pathsB = tables_and_paths(fb[0])
    rb = rows(kit, gg + ["read g=ea soft=1.5 " + reads_at(pathsB[0]), "read g=eb soft=1.5 " + reads_at(pathsB[1])])
    avg = [(a + b) / 2 for a, b in zip(rb[0][1:], rb[1][1:])]
    tavg, town = tables(kit, [avg, rb[0][1:]])
    check("reading both, A plays the two pictures' readings averaged", dmax(sentB[0], tavg) < 1e-12, "%.2g" % dmax(sentB[0], tavg))
    null("not its own alone", dmax(sentB[0], town) > 0.01, "%.3f" % dmax(sentB[0], town))

    # The holds: B's picture's stage at 0.3, A's at one; each frame's holds
    # as sent, carried on from the last where nothing is sent.
    hr = rows(kit, gg + ["run soft=1.5", frame(0, ("B", "A"), (1, 0.3)), frame(17, ("A", "B"), (1, 0.3)),
                         frame(34, ("both", "B"), (1, 0.3))])
    held, now_ = [1.0, 1.0], []
    for r in hr:
        for kind, layer, *v in did(r):
            if kind == "hold": held[layer] = v[0]
        now_.append(list(held))
    check("a crossed pair's depths are both held by the lower of the two holds", now_[0] == [0.3, 0.3], str(now_[0]))
    null("each reading its own, each keeps its own hold", now_[1] == [1, 0.3], str(now_[1]))
    check("and a layer reading both, uncrossed, takes the lower of the two it reads", now_[2] == [0.3, 0.3], str(now_[2]))

    # --- Crossed hands, the old library's, on the whole instrument ---
    code = corpus_code("Crossed hands")
    def reads(extra=()):
        lines = [["make", 48000, 512, code]] + list(extra) + [["midi", 0x90, n, 100] for n in (43, 50, 72, 79)] \
            + [["block", 512, 4096]] * 140 + [["reads"]]
        w = [l for l in kit.instrument(lines) if l.startswith("reads ")][-1].split()
        return [int(w[1]), int(w[2])], [float(w[3]), float(w[4])], w[5] == "1"
    xr, xd, xl = reads()
    check("Crossed hands: two figures, Scan on both, and the left hand's wave read from the right hand's picture",
          xl and xd == [1, 1] and xr == [2, 1], "reads %s (A 1, B 2), depths %s, live %s" % (xr, xd, xl))
    ur, _, ul = reads([["control", "scanReadsA", "A"], ["control", "scanReadsB", "B"]])
    null("not from its own: with each hand's Reads its own, A reads A's", ul and ur == [1, 2], str(ur))
