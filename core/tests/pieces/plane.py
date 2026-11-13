"""The X-Y plane, on the core: its operations' arithmetic at 1x, the mirrored
sine an octave up, aliasing and what oversampling buys, once to each layer's
picture and what is heard their sum, the delay the oversampling costs, what
it costs, and a source on the radius and on the twist.

These were planetest.py's on ?brain=js until stage 5's step 3, batch 4 (13
Nov): there a `makeGeneratorCore` built in the page with oscillators that do
nothing, rendered a block at a time, and for the three claims about the panel's
own sound, the page's brain under a held key, read off the page's generator's
window. Here the core's generator (generator_cpp: the same `set`, two layers'
voices, the heard pair beside the pictures) and, for the panel's sound, the
instrument whole (instrument_cpp: the panel's own sliders and switches by id,
a key at full velocity, the picture's lanes read back). The panel's units, the
codes and search stayed in planetest.py, on the default page. Spectra are
numpy's.

The aliasing pins and the cost were measured on the page's JavaScript engine;
they are measured again here on the core, said where each is held.
"""
import math, subprocess, time
import numpy as np

RATE = 44100
BH = [0.35875, 0.48829, 0.14128, 0.01168]


def spectrum(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    i = np.arange(n)
    w = (BH[0] - BH[1] * np.cos(2 * np.pi * i / n)
         + BH[2] * np.cos(4 * np.pi * i / n) - BH[3] * np.cos(6 * np.pi * i / n))
    spec = np.abs(np.fft.rfft(x * w))
    return spec, np.arange(len(spec)) * RATE / n


def level_at(spec, hz, f):
    return spec[np.abs(hz - f) < 4 * RATE / (2 * (len(spec) - 1))].max()


def db(a, b):
    return 20 * math.log10(max(float(a), 1e-15) / max(float(b), 1e-15))


def alias_floor(x, f0):
    spec, hz = spectrum(x)
    grid = np.zeros(len(spec), dtype=bool)
    grid[:6] = True
    k = 1
    while k * f0 < RATE / 2:
        grid |= np.abs(hz - k * f0) < 4 * RATE / len(x)
        k += 1
    return db(spec[~grid & (hz < 10000)].max(), spec.max())


def voices(vs):
    return "+".join("%d/%r/%r/%s" % (v["note"], v["freq"], v["velocity"], v["role"]) for v in vs)


def run(kit):
    check, null = kit.check, kit.null

    def core(tone, n=4410, toneB=None, skip=0):
        """planetest's CORE: a sine at amp 0.8, the fields given, on both
        layers where asked; the pictures and the heard pair, from `skip`."""
        ev = ["at 0 set shape sine", "at 0 set amp 0.8"]
        for k, v in tone.items():
            ev.append("at 0 voices 0 %s" % voices(v) if k == "voices" else "at 0 set %s %r" % (k, v))
        for k, v in (toneB or {}).items():
            ev.append("at 0 voices 1 %s" % voices(v) if k == "voices" else
                      "at 0 set %s %s 1" % (k, v if isinstance(v, str) else repr(v)))
        blocks = -(-(n) // 128) * 128
        out = np.array(kit.floats("generator_cpp", "run rate=%r slots=32 seed=3 samples=%d lfo0=sine,0.2 lfo1=sine,0.2\n%s\nend"
                                  % (float(RATE), blocks, "\n".join(ev)))[:blocks * 6]).reshape(-1, 6)[skip:n]
        return {k: out[:, i] for i, k in enumerate(("L", "R", "HL", "HR", "BL", "BR"))}

    # --- the arithmetic, at 1x (planetest :116 to :203) ---
    # A 3:2 figure at 220 Hz: X and Y different signals, the pair's length and
    # direction changing all the way round (never a circle, CLAUDE.md).
    fig = {"freq": 220, "interval": 7, "planeOS": 1}
    plain = core(fig)
    x0, y0 = plain["L"], plain["R"]
    m1 = core(dict(fig, planeMirror=1))
    x1, y1 = m1["L"], m1["R"]
    check("mirroring X makes X its own absolute value, to the last bit, and leaves Y alone",
          np.array_equal(x1, np.abs(x0)) and np.array_equal(y1, y0) and x0.min() < -0.5,
          "worst X %.2e, worst Y %.2e" % (np.abs(x1 - np.abs(x0)).max(), np.abs(y1 - y0).max()))
    null("the plain figure is not its own absolute value", not np.array_equal(x0, np.abs(x0)))
    both = core(dict(fig, planeMirror=3))
    check("and both folds both", np.array_equal(both["L"], np.abs(x0)) and np.array_equal(both["R"], np.abs(y0)))
    null("X alone leaves Y's troughs", not np.array_equal(y1, np.abs(y0)))

    r = 0.3
    clipped = core(dict(fig, planeLimit=1, planeRadius=r))
    xc, yc = clipped["L"], clipped["R"]
    m0, mc = np.hypot(x0, y0), np.hypot(xc, yc)
    want = r * np.tanh(m0 / r)
    moving = m0 > 1e-3
    def turned(xa, ya):
        return np.abs(np.angle(np.exp(1j * (np.arctan2(ya, xa) - np.arctan2(y0, x0)))))[moving]
    check("the radial clip makes every pair's length r tanh(|v|/r), to float precision",
          np.abs(mc - want).max() < 1e-6, "%.2e" % np.abs(mc - want).max())
    # The null: each channel clipped on its own, r tanh(x / r), the wrong
    # clip the docstring's "radial" rules out.
    apart = np.hypot(r * np.tanh(x0 / r), r * np.tanh(y0 / r))
    null("each channel clipped alone is not that length", np.abs(apart - want).max() >= 1e-6)
    check("never longer than the radius, from a figure that reaches 1.13", mc.max() <= r and m0.max() > 1.0,
          "%.4f from %.3f" % (mc.max(), m0.max()))
    check("and turns no pair: every one keeps its direction", turned(xc, yc).max() < 1e-5, "%.2e rad" % turned(xc, yc).max())
    null("and the channels clipped alone do turn them",
         turned(r * np.tanh(x0 / r), r * np.tanh(y0 / r)).max() >= 1e-5)

    mx = core(dict(fig, planeOS=2, planeScaleX=0.5, planeScaleY=1.2, planeShear=0.3))
    wx, wy = 0.5 * (x0 + 0.3 * y0), 1.2 * y0
    err = max(np.abs(mx["L"] - wx).max(), np.abs(mx["R"] - wy).max())
    check("scale and shear are the matrix [sx sx*k; 0 sy], to float precision, with no delay at 2x",
          err < 1e-6 and np.abs(wx - x0).max() > 0.2, "worst %.2e" % err)
    # The null: the same matrix 31 samples late, as it would be done inside the oversampling.
    late = max(np.abs(mx["L"][31:] - wx[:-31]).max(), np.abs(mx["R"][31:] - wy[:-31]).max())
    null("and read 31 samples late it is not", late >= 1e-6, "%.2e" % late)

    k = 1.7
    tw = core(dict(fig, planeTwist=k))
    xt, yt = tw["L"], tw["R"]
    a = k * m0
    ex, ey = x0 * np.cos(a) - y0 * np.sin(a), x0 * np.sin(a) + y0 * np.cos(a)
    err = max(np.abs(xt - ex).max(), np.abs(yt - ey).max())
    fixed = k * m0.mean()
    miss = np.abs(xt - (x0 * np.cos(fixed) - y0 * np.sin(fixed))).max()
    check("the twist turns each point by k times its length, to float precision", err < 1e-5,
          "%.2e" % err)
    null("one fixed angle, the likely wrong answer, misses", miss > 0.2, "%.2f" % miss)
    check("and keeps every length", np.abs(np.hypot(xt, yt) - m0).max() < 1e-5)

    folded = core(dict(fig, planeLimit=2, planeRadius=r))
    xf, yf = folded["L"], folded["R"]
    mf = np.hypot(xf, yf)
    t = np.mod(m0, 2 * r)
    wantf = np.where(t <= r, t, 2 * r - t)
    past = (m0 > r) & (m0 < 2 * r)
    twice = m0 > 2 * r
    check("the fold reflects each length at the radius, as often as it takes - 2r - m past it, m inside",
          np.abs(mf - wantf).max() < 1e-6 and past.sum() > 100 and twice.sum() > 100
          and np.abs(mf[m0 < r] - m0[m0 < r]).max() < 1e-6, "worst %.2e" % np.abs(mf - wantf).max())
    # The null: a fold that reflects once and then clamps, 2r - m held at nought.
    once = np.where(m0 <= r, m0, np.maximum(0, 2 * r - m0))
    null("reflected once and stopped, it is not", np.abs(mf - once).max() >= 1e-6)
    turnf = np.abs(np.angle(np.exp(1j * (np.arctan2(yf, xf) - np.arctan2(y0, x0)))))[mf > 1e-3]
    check("never outside the radius, and every point keeps its direction",
          mf.max() <= r + 1e-6 and turnf.max() < 1e-5, "%.4f, %.2e rad" % (mf.max(), turnf.max()))

    snapped = core(dict(fig, planeSnap=5))
    g = 2 / 32
    xs, ys = snapped["L"], snapped["R"]
    err = max(np.abs(xs - np.round(x0 / g) * g).max(), np.abs(ys - np.round(y0 / g) * g).max())
    check("snap at 5 bits puts both channels on a grid of 1/16 - the nearest point of it",
          err < 1e-6 and len(np.unique(np.round(xs / g))) > 10, "worst %.2e" % err)
    floor_err = max(np.abs(xs - np.floor(x0 / g) * g).max(), np.abs(ys - np.floor(y0 / g) * g).max())
    null("and not the point below it", floor_err >= 1e-6)

    allop = core(dict(fig, planeMirror=1, planeTwist=0.9, planeLimit=2, planeRadius=0.5, planeSnap=5))
    def composed(order):
        xa, ya = x0.copy(), y0.copy()
        for op in order:
            if op == "mirror": xa = np.abs(xa)
            elif op == "twist":
                aa = 0.9 * np.hypot(xa, ya)
                xa, ya = xa * np.cos(aa) - ya * np.sin(aa), xa * np.sin(aa) + ya * np.cos(aa)
            elif op == "fold":
                ma, an = np.hypot(xa, ya), np.arctan2(ya, xa)
                ta = np.mod(ma, 1.0); ma = np.where(ta <= 0.5, ta, 1.0 - ta)
                xa, ya = ma * np.cos(an), ma * np.sin(an)
            else: xa, ya = np.round(xa / g) * g, np.round(ya / g) * g
        return ((np.abs(allop["L"] - xa) > 1e-6) | (np.abs(allop["R"] - ya) > 1e-6)).sum()
    off = composed(("mirror", "twist", "fold", "snap"))
    # A point within float error of a half-step can round either way: count those.
    check("all four together are applied in the stated order", off <= 3, "%d points of %d off" % (off, len(x0)))
    swapped = composed(("twist", "mirror", "fold", "snap"))
    null("twist before mirror is not that order", swapped > 3, "%d points off" % swapped)

    # --- a mirrored sine is an octave up (:212) ---
    octave = core({"freq": 220, "interval": 0, "phase": 0, "planeMirror": 3}, n=48510, skip=4410)
    spec, hz = spectrum(octave["L"])
    top = level_at(spec, hz, 440)
    odd = max(db(level_at(spec, hz, f), top) for f in (220, 660, 1100))
    loudest = float(hz[10 + np.argmax(spec[10:])])
    check("its fundamental is 440 and its odd harmonics of 220 are gone, 100 dB down",
          abs(loudest - 440) < 2 and odd < -100, "loudest %.1f Hz, odd %.1f dB" % (loudest, odd))
    one = core({"freq": 220, "interval": 0, "phase": 0, "planeMirror": 2}, n=48510, skip=4410)
    s1, h1 = spectrum(one["L"])
    null("mirroring Y alone leaves X at 220", float(h1[10 + np.argmax(s1[10:])]) < 230)

    # --- aliasing, and what oversampling is worth (:234 to :255) ---
    # The page's floor is the band-limited square's: -58.5 at 2 kHz, -46.2 at 4.
    floors = {}
    for f in (2000, 4000):
        for os_ in (1, 2, 4):
            base = {"freq": f, "interval": 0, "phase": 0, "planeOS": os_}
            L = lambda extra: core(dict(base, **extra), n=48510, skip=4410)["L"]
            floors[("mirror", f, os_)] = alias_floor(L({"planeMirror": 3}), f)
            floors[("clip", f, os_)] = alias_floor(L({"planeLimit": 1, "planeRadius": 0.2}), f)
            floors[("fold", f, os_)] = alias_floor(L({"planeLimit": 2, "planeRadius": 0.5}), f)
            # At 0.6: turned off the diagonal a pair of 0.8s is past full scale on one axis.
            floors[("twist", f, os_)] = alias_floor(L({"amp": 0.6, "planeTwist": 2}), f)
            floors[("snap", f, os_)] = alias_floor(L({"planeSnap": 5}), f)
    print("    floors (dB): " + ", ".join("%s %d %dx %.1f" % (k + (v,)) for k, v in sorted(floors.items())))
    smooth = ("mirror", "clip", "twist")
    clear = lambda os_: all(floors[(op, 2000, os_)] < -58.5 and floors[(op, 4000, os_)] < -46.2 for op in smooth)
    check("at 2x, the default, mirror, clip and twist clear the square's floor: under -58.5 at 2 kHz and -46.2 at 4",
          clear(2), str({k: round(v, 1) for k, v in floors.items() if k[2] == 2}))
    null("at 1x they do not", not clear(1))
    worth = all(floors[(op, f, 1)] - floors[(op, f, 2)] > 10 and floors[(op, f, 2)] - floors[(op, f, 4)] > 10
                for op in smooth for f in (2000, 4000))
    check("and for those three each doubling is worth at least 10 dB, at both", worth,
          str({k: round(v, 1) for k, v in floors.items() if k[0] in smooth}))
    null("and the snap's doublings are not", not all(floors[("snap", f, 1)] - floors[("snap", f, 2)] > 10 for f in (2000, 4000)))
    # The fold and the snap are pinned where they were measured, 3 dB of
    # room: the fold's corners and the snap's steps are their character. The
    # pins were measured on the page's JavaScript engine (-41.1, -35.7, -53.0,
    # -41.1; -44.3, -44.7). Measured again on the core (13 Nov) every one
    # reads the same to the tenth of a decibel, as parity's holding the core
    # to that engine sample for sample says it must, so they are kept.
    pins = {("fold", 2000, 2): -41.1, ("fold", 4000, 2): -35.7, ("fold", 2000, 4): -53.0, ("fold", 4000, 4): -41.1,
            ("snap", 2000, 2): -44.3, ("snap", 4000, 2): -44.7}
    check("the fold and the snap are no worse than when they were measured", all(floors[k] < v + 3 for k, v in pins.items()),
          str({k: round(floors[k], 1) for k in pins}))
    null("the fold at 1x is worse than its 2x pins", not all(floors[("fold", f, 1)] < pins[("fold", f, 2)] + 3 for f in (2000, 4000)))
    check("and oversampling still buys the fold 20 dB from 1x to 4x, at both",
          all(floors[("fold", f, 1)] - floors[("fold", f, 4)] > 20 for f in (2000, 4000)),
          str([round(floors[("fold", f, 1)] - floors[("fold", f, 4)], 1) for f in (2000, 4000)]))

    # --- once, and to every pair (:261 to :286) ---
    solo = core({"freq": 220, "interval": 7, "planeMirror": 3, "planeLimit": 1, "planeRadius": 0.3})
    check("outside poly what is heard is exactly what is drawn - the pair is not done twice",
          np.array_equal(solo["HL"], solo["L"]) and np.array_equal(solo["HR"], solo["R"]))
    null("and the drawn pair is not the plain figure", not np.array_equal(solo["L"], x0))
    v = [{"note": 57, "freq": 220, "velocity": 1, "role": "x"}, {"note": 64, "freq": 329.63, "velocity": 1, "role": "y"}]
    vb = [{"note": 69, "freq": 440, "velocity": 1, "role": "xy"}]
    chord = core({"voices": v, "planeMirror": 3}, n=8820, skip=4410, toneB={"shape": "sine", "amp": 0.8, "voices": vb})
    loose = core({"voices": v}, n=8820, skip=4410, toneB={"shape": "sine", "amp": 0.8, "voices": vb})
    lows = {k: round(float(np.min(chord[k])), 4) for k in ("L", "R", "HL", "HR", "BL", "BR")}
    raw = {k: round(float(np.min(loose[k])), 3) for k in ("HL", "BL")}
    check("in poly layer A's picture and layer B's are each mirrored, and so what is heard",
          all(x > -0.02 for x in lows.values()) and raw["HL"] < -0.5 and raw["BL"] < -0.5, "%s; unmirrored %s" % (lows, raw))
    summed = max(np.abs(chord["HL"] - chord["L"] - chord["BL"]).max(), np.abs(chord["HR"] - chord["R"] - chord["BR"]).max())
    check("and what is heard is the two mirrored pictures summed, sample for sample", summed < 1e-6, "worst %.2e" % summed)
    oncesum = np.abs(loose["L"] + loose["BL"])
    gap = np.abs(chord["HL"] - oncesum).max()
    check("and not the sum mirrored, which the comparison tells apart", gap > 0.05, "%.3f" % gap)
    null("the unmirrored chord's heard pair is not the mirrored pictures summed",
         np.abs(loose["HL"] - chord["L"] - chord["BL"]).max() >= 1e-6)

    # --- the delay oversampling costs (:304) ---
    one, two, four = (core({"freq": 220, "interval": 0, "planeMirror": 3, "planeOS": o}, n=8820)["L"] for o in (1, 2, 4))
    def lag(a, b2):
        best, where = -1, 0
        for d in np.arange(20, 45, 0.25):
            shifted = np.interp(np.arange(2000, 8000) - d, np.arange(len(a)), a)
            c = np.dot(shifted - shifted.mean(), b2[2000:8000] - b2[2000:8000].mean())
            if c > best: best, where = c, d
        return where
    l2, l4 = lag(one, two), lag(one, four)
    # (n - factor) / factor: 62/2 and 124/4.
    check("2x and 4x both delay the pair 31 samples, 0.7 ms, as the code says",
          abs(l2 - 31) <= 0.25 and abs(l4 - 31) <= 0.25, "%.2f, %.2f" % (l2, l4))
    null("and 1x against itself is not 31 late", abs(lag(one, one) - 31) > 0.25, "%.2f" % lag(one, one))

    # --- what it costs (:324) ---
    # On the page, one second of the JavaScript engine's block timed inside
    # the browser: 191 ms alone, under 500 required. Here the core's
    # generator_cpp, sixteen voices over two layers, mirror and clip at 4x,
    # timed as a process: one second's render and five seconds', the
    # difference four seconds of rendering and printing every sample (so an
    # overestimate of the engine). Half of real time is still the bar; the
    # core makes it with room (a few tens of milliseconds a second here).
    vs = [{"note": 48 + j * 3, "freq": 130.81 * 2 ** (j / 4), "velocity": 1, "role": "u" if j else "x"} for j in range(8)]
    def timed(seconds):
        ev = ["at 0 set shape sine", "at 0 set shape sine 1", "at 0 voices 0 %s" % voices(vs), "at 0 voices 1 %s" % voices(vs),
              "at 0 set planeMirror 3", "at 0 set planeLimit 1", "at 0 set planeRadius 0.3", "at 0 set planeOS 4"]
        exe = kit.build("generator_cpp")
        text = "run rate=44100.0 slots=32 seed=3 samples=%d lfo0=sine,0.2 lfo1=sine,0.2\n%s\nend\n" % (
            -(-44100 * seconds // 128) * 128, "\n".join(ev))
        import os, tempfile
        fd, name = tempfile.mkstemp(suffix=".txt"); os.write(fd, text.encode()); os.close(fd)
        t0 = time.perf_counter()
        subprocess.run([exe, name], check=True, stdout=subprocess.DEVNULL)
        took = time.perf_counter() - t0
        os.unlink(name)
        return took
    cost = min(timed(5) - timed(1) for _ in range(3)) / 4 * 1000
    check("sixteen voices over two layers with both operations at 4x run in under half of real time (the core's)",
          cost < 500, "%.0f ms a second, printing included" % cost)
    null("and the bar is not met by nothing: a second costs some time", cost > 0.5, "%.1f ms" % cost)

    # --- the panel's sound, through the instrument (:383, :389, :439) ---
    # On ?brain=js these were midiNoteOn on the page's brain, a routing
    # compiled by the page, and the page's generator's window. Here the
    # instrument whole, the panel's own controls moved by id as the page
    # moves them, a key at full velocity, the picture's lanes read back.
    def figure(controls, routing=None, blocks=120, take=35):
        lines = [["make", 48000, 128, ""]]
        lines += [["control", "shape", "sine"], ["control", "interval", "0"], ["slider", "phase", "0"],
                  ["slider", "amp", "55"], ["slider", "envSustain", "100"], ["control", "polyRound", False]]
        lines += controls
        if routing: lines.append(["routings", routing])
        lines += [["midi", 0x90, 57, 127]] + [["block", 128]] * blocks
        rows = [l.split()[1:] for l in kit.instrument(lines) if l.startswith("block ")][-take:]
        x = np.array([float(v) for row in rows for v in row[2 * 128:3 * 128]])
        y = np.array([float(v) for row in rows for v in row[3 * 128:4 * 128]])
        return x, y
    clip = [["control", "planeMirror", "1"], ["slider", "planeRadius", "25"], ["control", "planeLimit", "1"], ["click", "planeOS4"]]
    x, y = figure(clip)
    once = 0.25 * math.tanh(0.55 * math.sqrt(2) / 0.25)      # a diagonal of 0.55 clipped once at 0.25
    longest = float(np.hypot(x, y).max())
    check("on the instrument the figure is mirrored and clipped once, not twice: longest %.4f" % once,
          x.min() > -0.01 and abs(longest - once) < 0.01 * once, "lowest X %.4f, longest %.4f" % (x.min(), longest))
    twice = 0.25 * math.tanh(once / 0.25)
    null("clipped twice it would be %.4f" % twice, abs(twice - once) >= 0.01 * once)
    xp, yp = figure(clip, "midi.key>gen.radius@1")
    pushed = 0.75 * math.tanh(0.55 * math.sqrt(2) / 0.75)
    got = float(np.hypot(xp, yp).max())
    check("a key on Clip radius opens it: at full depth the figure is held at 0.75, not 0.25",
          abs(got - pushed) < 0.01 * pushed, "%.4f against %.4f" % (got, pushed))
    xh, yh = figure(clip, "midi.key>gen.radius@0.5")
    null("at half depth it is held at 0.5", abs(float(np.hypot(xh, yh).max()) - pushed) >= 0.01 * pushed,
         "%.4f" % float(np.hypot(xh, yh).max()))
    xs0, ys0 = figure([["slider", "planeTwist", "0"]])
    xs1, ys1 = figure([["slider", "planeTwist", "0"]], "midi.key>gen.twist@1")
    still, swirled = float(np.abs(xs0 - ys0).max()), float(np.abs(xs1 - ys1).max())
    check("a key on Twist swirls a figure whose slider is at nought", still < 1e-3 and swirled > 0.3,
          "%.4f still, %.4f swirled" % (still, swirled))
    null("and the figure under it is the diagonal, sounding", float(np.abs(xs0).max()) > 0.3, "%.3f" % float(np.abs(xs0).max()))
