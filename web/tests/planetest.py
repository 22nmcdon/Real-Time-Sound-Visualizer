"""The X-Y plane as an effect: its nine operations, and the oversampling (S2).

What would go wrong, and what is checked for it:

- the arithmetic: at 1x the operation is applied as it is, so a mirrored X
  is |x| to the last bit and Y is left alone; a clipped pair has exactly
  r tanh(|v| / r) for its length and exactly its old direction. The fixture
  is a 3:2 figure - never a circle, whose length and direction statistics a
  broken clip could leave alone. The same figure, point by point, for the
  matrix, the twist (a fixed angle misses by 0.4), the kaleidoscope, the fold
  and the snap, and all five non-linear ones together in their stated order;
- the sound: a mirrored sine is an octave up with no odd harmonics;
- aliasing: what the operations put above Nyquist folded back. Measured at
  1x, 2x and 4x and pinned, against the floor the page already lives with,
  the band-limited square's;
- applied twice, or not at all where it should be: once to the picture and
  heard pair outside poly, and in poly to the heard pair as well as the
  picture, and to layer B;
- the delay the oversampling costs, stated in the code and measured here;
- the panel, a source on the radius and on the twist - the latter with its
  slider at nought, which once did nothing - and setup codes, with the
  version-4 pass that turns the old clip checkbox into the limit menu.
"""
import math, os, sys
import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

RATE = 44100
BH = [0.35875, 0.48829, 0.14128, 0.01168]

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


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


# A core off the page: L, R, and the heard pair when asked.
CORE = """(setup) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
  core.set('mode', 'wave'); core.set('shape', 'sine'); core.set('amp', 0.8);
  for (const k in setup.tone) core.set(k, setup.tone[k]);
  for (const k in setup.toneB || {}) core.set(k, setup.toneB[k], 1);
  const n = setup.n, L = new Float32Array(n), R = new Float32Array(n);
  const HL = new Float32Array(n), HR = new Float32Array(n), BL = new Float32Array(n), BR = new Float32Array(n);
  core.block(L, R, n, HL, HR, BL, BR);
  const from = setup.skip || 0;
  const out = { L: Array.from(L.subarray(from)), R: Array.from(R.subarray(from)) };
  if (setup.heard) { out.HL = Array.from(HL.subarray(from)); out.HR = Array.from(HR.subarray(from));
                     out.BL = Array.from(BL.subarray(from)); out.BR = Array.from(BR.subarray(from)); }
  return out;
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)
    run = lambda tone, n=4410, **kw: p.evaluate(CORE, dict({"tone": tone, "n": n}, **kw))

    print("\n--- the arithmetic, at 1x ---")
    # A 3:2 figure at 220 Hz: X and Y are different signals, and the pair's
    # length and direction change all the way round.
    fig = {"freq": 220, "interval": 7, "planeOS": 1}
    plain = run(fig)
    mirrored = run(dict(fig, planeMirror=1))
    x0, y0 = np.asarray(plain["L"]), np.asarray(plain["R"])
    x1, y1 = np.asarray(mirrored["L"]), np.asarray(mirrored["R"])
    check("mirroring X makes X its own absolute value, to the last bit, and leaves Y alone",
          np.array_equal(x1, np.abs(x0)) and np.array_equal(y1, y0) and x0.min() < -0.5,
          "worst X %.2e, worst Y %.2e" % (np.abs(x1 - np.abs(x0)).max(), np.abs(y1 - y0).max()))
    both = run(dict(fig, planeMirror=3))
    check("and both folds both",
          np.array_equal(np.asarray(both["L"]), np.abs(x0)) and np.array_equal(np.asarray(both["R"]), np.abs(y0)), "")
    r = 0.3
    clipped = run(dict(fig, planeLimit=1, planeRadius=r))
    xc, yc = np.asarray(clipped["L"]), np.asarray(clipped["R"])
    m0, mc = np.hypot(x0, y0), np.hypot(xc, yc)
    want = r * np.tanh(m0 / r)
    moving = m0 > 1e-3
    turn = np.abs(np.angle(np.exp(1j * (np.arctan2(yc, xc) - np.arctan2(y0, x0)))))[moving]
    print("    clip radius 0.3: longest %.4f, worst length error %.2e, worst turn %.2e rad"
          % (mc.max(), np.abs(mc - want).max(), turn.max()))
    check("the radial clip makes every pair's length r tanh(|v|/r), to float precision",
          np.abs(mc - want).max() < 1e-6, "%.2e" % np.abs(mc - want).max())
    check("never longer than the radius, from a figure that reaches 1.13",
          mc.max() <= r and m0.max() > 1.0, "%.4f from %.3f" % (mc.max(), m0.max()))
    check("and turns no pair: every one keeps its direction",
          turn.max() < 1e-5, "%.2e rad" % turn.max())

    print("\n--- the matrix, and the rest of the plane ---")
    # Scale and shear are linear, done outside the oversampling, so at the
    # default 2x they are the matrix to float precision and move nothing in
    # time: a skewed pair 31 samples late would fail the first check.
    mx = run(dict(fig, planeOS=2, planeScaleX=0.5, planeScaleY=1.2, planeShear=0.3))
    wx, wy = 0.5 * (x0 + 0.3 * y0), 1.2 * y0
    err = max(np.abs(np.asarray(mx["L"]) - wx).max(), np.abs(np.asarray(mx["R"]) - wy).max())
    check("scale and shear are the matrix [sx sx*k; 0 sy], to float precision, with no delay at 2x",
          err < 1e-6 and np.abs(wx - x0).max() > 0.2, "worst %.2e" % err)

    # Twist, point by point on the 3:2 figure, whose length changes all the
    # way round: a rotation by one fixed angle - the likely wrong answer -
    # misses by up to the twist times the change in length.
    k = 1.7
    tw = run(dict(fig, planeTwist=k))
    xt, yt = np.asarray(tw["L"]), np.asarray(tw["R"])
    a = k * m0
    ex, ey = x0 * np.cos(a) - y0 * np.sin(a), x0 * np.sin(a) + y0 * np.cos(a)
    err = max(np.abs(xt - ex).max(), np.abs(yt - ey).max())
    fixed = k * m0.mean()
    miss = np.abs(xt - (x0 * np.cos(fixed) - y0 * np.sin(fixed))).max()
    print("    twist %.1f rad a unit: worst error %.2e; one fixed angle would miss by %.2f" % (k, err, miss))
    check("the twist turns each point by k times its length, to float precision",
          err < 1e-5 and miss > 0.2, "%.2e, fixed-angle miss %.2f" % (err, miss))
    check("and keeps every length", np.abs(np.hypot(xt, yt) - m0).max() < 1e-5, "")

    for n in (3, 6):
        kal = run(dict(fig, planeKaleido=n))
        xk, yk = np.asarray(kal["L"]), np.asarray(kal["R"])
        wedge = 2 * np.pi / n
        ang = np.mod(np.arctan2(y0, x0), wedge)
        ang = np.where(ang > wedge / 2, wedge - ang, ang)
        # The figure reaches 1.08, and turned onto the X axis that is past
        # full scale: the output's clamp at 1 is part of what is expected,
        # and the length is kept wherever the clamp did not act.
        ex, ey = np.clip(m0 * np.cos(ang), -1, 1), np.clip(m0 * np.sin(ang), -1, 1)
        err = max(np.abs(xk - ex).max(), np.abs(yk - ey).max())
        inside = np.abs(m0 * np.cos(ang)) < 1
        got = np.arctan2(yk, xk)[moving & inside]
        check("a kaleidoscope of %d folds every angle into 0 to pi/%d, length kept, to float precision" % (n, n),
              err < 1e-5 and got.min() > -1e-5 and got.max() < np.pi / n + 1e-5
              and np.abs(np.hypot(xk, yk) - m0)[inside].max() < 1e-5,
              "worst %.2e, angles %.3f to %.3f" % (err, got.min(), got.max()))

    folded = run(dict(fig, planeLimit=2, planeRadius=r))
    xf, yf = np.asarray(folded["L"]), np.asarray(folded["R"])
    mf = np.hypot(xf, yf)
    t = np.mod(m0, 2 * r)
    wantf = np.where(t <= r, t, 2 * r - t)
    turnf = np.abs(np.angle(np.exp(1j * (np.arctan2(yf, xf) - np.arctan2(y0, x0)))))[mf > 1e-3]
    past = (m0 > r) & (m0 < 2 * r)
    twice = m0 > 2 * r
    print("    fold at 0.3: %d points reflected once, %d more than once" % (past.sum(), twice.sum()))
    check("the fold reflects each length at the radius, as often as it takes - 2r - m past it, m inside",
          np.abs(mf - wantf).max() < 1e-6 and past.sum() > 100 and twice.sum() > 100
          and np.abs(mf[m0 < r] - m0[m0 < r]).max() < 1e-6, "worst %.2e" % np.abs(mf - wantf).max())
    check("never outside the radius, and every point keeps its direction",
          mf.max() <= r + 1e-6 and turnf.max() < 1e-5, "%.4f, %.2e rad" % (mf.max(), turnf.max()))

    snapped = run(dict(fig, planeSnap=4))
    g = 2 / 16
    xs, ys = np.asarray(snapped["L"]), np.asarray(snapped["R"])
    err = max(np.abs(xs - np.round(x0 / g) * g).max(), np.abs(ys - np.round(y0 / g) * g).max())
    check("snap at 4 bits puts both channels on a grid of 1/8 - the nearest point of it",
          err < 1e-6 and len(np.unique(np.round(xs / g))) > 10, "worst %.2e" % err)

    # Mirror, twist, kaleidoscope, limit, snap: in that order, and the snap
    # last - the grid is what comes out whatever came before it.
    allop = run(dict(fig, planeMirror=1, planeTwist=0.9, planeKaleido=5, planeLimit=2, planeRadius=0.5, planeSnap=3))
    xa, ya = np.abs(x0), y0
    aa = 0.9 * np.hypot(xa, ya)
    xa, ya = xa * np.cos(aa) - ya * np.sin(aa), xa * np.sin(aa) + ya * np.cos(aa)
    ma = np.hypot(xa, ya)
    wd = 2 * np.pi / 5
    an = np.mod(np.arctan2(ya, xa), wd); an = np.where(an > wd / 2, wd - an, an)
    ta = np.mod(ma, 1.0); ma2 = np.where(ta <= 0.5, ta, 1.0 - ta)
    xa, ya = ma2 * np.cos(an), ma2 * np.sin(an)
    g = 0.25
    xa, ya = np.round(xa / g) * g, np.round(ya / g) * g
    # A point that lands within float error of a half-step can round either
    # way: count those rather than fail on them.
    off = (np.abs(np.asarray(allop["L"]) - xa) > 1e-6) | (np.abs(np.asarray(allop["R"]) - ya) > 1e-6)
    check("all five together are applied in the stated order", off.sum() <= 3, "%d points of %d off" % (off.sum(), len(xa)))

    print("\n--- a mirrored sine is an octave up ---")
    octave = run({"freq": 220, "interval": 0, "phase": 0, "planeMirror": 3}, n=48510, skip=4410)
    spec, hz = spectrum(octave["L"])
    top = level_at(spec, hz, 440)
    odd = max(db(level_at(spec, hz, f), top) for f in (220, 660, 1100))
    print("    against the new fundamental at 440: odd harmonics at worst %.1f dB" % odd)
    loudest = float(hz[10 + np.argmax(spec[10:])])       # past DC, which a fold has plenty of
    check("its fundamental is 440 and its odd harmonics of 220 are gone, 100 dB down",
          abs(loudest - 440) < 2 and odd < -100, "loudest %.1f Hz, odd %.1f dB" % (loudest, odd))

    print("\n--- aliasing, and what oversampling is worth ---")
    # Measured when this landed, below 10 kHz, dB under the loudest. The
    # page's floor is the band-limited square's: -58.5 at 2 kHz, -46.2 at 4.
    floors = {}
    for f in (2000, 4000):
        for os_ in (1, 2, 4):
            base = {"freq": f, "interval": 0, "phase": 0, "planeOS": os_}
            floors[("mirror", f, os_)] = alias_floor(run(dict(base, planeMirror=3), n=48510, skip=4410)["L"], f)
            floors[("clip", f, os_)] = alias_floor(run(dict(base, planeLimit=1, planeRadius=0.2), n=48510, skip=4410)["L"], f)
            floors[("fold", f, os_)] = alias_floor(run(dict(base, planeLimit=2, planeRadius=0.5), n=48510, skip=4410)["L"], f)
            # At 0.6, not 0.8: turned off the diagonal, a pair of 0.8s is past
            # full scale on one axis, and the output's clamp - at the base
            # rate, outside the oversampling - set a floor of -55 dB at every
            # factor alike, which read as the oversampling doing nothing.
            floors[("twist", f, os_)] = alias_floor(run(dict(base, amp=0.6, planeTwist=2), n=48510, skip=4410)["L"], f)
            floors[("kaleido", f, os_)] = alias_floor(run(dict(base, amp=0.6, planeKaleido=5), n=48510, skip=4410)["L"], f)
            floors[("snap", f, os_)] = alias_floor(run(dict(base, planeSnap=5), n=48510, skip=4410)["L"], f)
    for k in sorted(floors): print("    %-6s %d Hz at %dx: %.1f dB" % (k[0], k[1], k[2], floors[k]))
    smooth = ("mirror", "clip", "twist", "kaleido")
    check("at 2x, the default, mirror, clip, twist and kaleidoscope clear the square's floor: under -58.5 at 2 kHz and -46.2 at 4",
          all(floors[(op, 2000, 2)] < -58.5 and floors[(op, 4000, 2)] < -46.2 for op in smooth),
          str({k: round(v, 1) for k, v in floors.items() if k[2] == 2}))
    check("and for those four each doubling is worth at least 10 dB, at both",
          all(floors[(op, f, 1)] - floors[(op, f, 2)] > 10 and floors[(op, f, 2)] - floors[(op, f, 4)] > 10
              for op in smooth for f in (2000, 4000)),
          str({k: round(v, 1) for k, v in floors.items() if k[0] in smooth}))
    # The fold's reflections are corners in the wave, whose harmonics fall
    # as 1/n^2, and a figure folded twice has two of them a half-cycle: at
    # 2x it measured -41.1 and -35.7, short of the square's floor, and 4x
    # buys 12 and 5 dB more. The snap is a quantiser, a step at every level
    # it crosses, and oversampling is worth almost nothing to it: -44.3 and
    # -44.7 at 2x, much as at 1x. Both are the effect's own character - a
    # wavefolder and a bitcrusher are bought for that edge - so they are
    # pinned where they were measured, 3 dB of room, rather than held to a
    # floor they cannot reach.
    pins = {("fold", 2000, 2): -41.1, ("fold", 4000, 2): -35.7, ("fold", 2000, 4): -53.0, ("fold", 4000, 4): -41.1,
            ("snap", 2000, 2): -44.3, ("snap", 4000, 2): -44.7}
    check("the fold and the snap are no worse than when they were measured",
          all(floors[k] < v + 3 for k, v in pins.items()),
          str({k: round(floors[k], 1) for k in pins}))
    check("and oversampling still buys the fold 20 dB from 1x to 4x, at both",
          all(floors[("fold", f, 1)] - floors[("fold", f, 4)] > 20 for f in (2000, 4000)), "")

    print("\n--- once, and to every pair ---")
    # Outside poly the heard pair is the picture pair, done once.
    solo = run({"freq": 220, "interval": 7, "planeMirror": 3, "planeLimit": 1, "planeRadius": 0.3}, heard=True)
    check("outside poly what is heard is exactly what is drawn - the pair is not done twice",
          solo["HL"] == solo["L"] and solo["HR"] == solo["R"], "")
    # In poly the heard pair is its own, nearly mono, and gets the operation
    # too; so does layer B's picture. A chord in both ears, mirrored, has no
    # negative half left in what is heard.
    v = [{"note": 57, "freq": 220, "velocity": 1, "role": "x"}, {"note": 64, "freq": 329.63, "velocity": 1, "role": "y"}]
    chord = run({"voices": v, "planeMirror": 3}, n=8820, skip=4410, heard=True,
                toneB={"shape": "sine", "amp": 0.8, "voices": [{"note": 69, "freq": 440, "velocity": 1, "role": "xy"}]})
    loose = run({"voices": v}, n=8820, skip=4410, heard=True,
                toneB={"shape": "sine", "amp": 0.8, "voices": [{"note": 69, "freq": 440, "velocity": 1, "role": "xy"}]})
    lows = {k: round(float(np.min(chord[k])), 4) for k in ("L", "R", "HL", "HR", "BL", "BR")}
    raw = {k: round(float(np.min(loose[k])), 3) for k in ("HL", "BL")}
    print("    lowest sample, mirrored: %s; unmirrored heard %s" % (lows, raw))
    check("in poly the heard pair, layer A's picture and layer B's picture are all mirrored",
          all(v2 > -0.02 for v2 in lows.values()) and raw["HL"] < -0.5 and raw["BL"] < -0.5, str(lows))
    check("and the heard pair is not the picture pair there: it was done as its own",
          chord["HL"] != chord["L"], "")

    print("\n--- the delay oversampling costs ---")
    one = np.asarray(run({"freq": 220, "interval": 0, "planeMirror": 3, "planeOS": 1}, n=8820)["L"])
    two = np.asarray(run({"freq": 220, "interval": 0, "planeMirror": 3, "planeOS": 2}, n=8820)["L"])
    four = np.asarray(run({"freq": 220, "interval": 0, "planeMirror": 3, "planeOS": 4}, n=8820)["L"])
    def lag(a, b2):
        best, where = -1, 0
        for d in np.arange(20, 45, 0.25):
            shifted = np.interp(np.arange(2000, 8000) - d, np.arange(len(a)), a)
            c = np.dot(shifted - shifted.mean(), b2[2000:8000] - b2[2000:8000].mean())
            if c > best: best, where = c, d
        return where
    l2, l4 = lag(one, two), lag(one, four)
    print("    2x is %.2f samples late, 4x %.2f" % (l2, l4))
    # (n - factor) / factor: 62/2 and 124/4. The code's first comment said
    # 31.5 and 31.75, forgetting that the decimator reads its newest sample,
    # factor - 1 oversampled steps ahead of the input's own place.
    check("2x and 4x both delay the pair 31 samples, 0.7 ms, as the code says",
          abs(l2 - 31) <= 0.25 and abs(l4 - 31) <= 0.25, "%.2f, %.2f" % (l2, l4))

    print("\n--- what it costs ---")
    cost = p.evaluate("""() => {
      const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
      const core = makeGeneratorCore(44100, GEN_DESTS.length, [still(), still()]);
      core.set('mode', 'wave'); core.set('shape', 'sine');
      const v = [];
      for (let k = 0; k < 8; k++) v.push({ note: 48 + k * 3, freq: 130.81 * Math.pow(2, k / 4), velocity: 1, role: k ? 'u' : 'x' });
      core.set('voices', v); core.set('voices', v, 1); core.set('shape', 'sine', 1);
      core.set('planeMirror', 3); core.set('planeLimit', 1); core.set('planeRadius', 0.3); core.set('planeOS', 4);
      const n = 44100, a = new Float32Array(n), b = new Float32Array(n);
      const c = new Float32Array(n), d = new Float32Array(n), e = new Float32Array(n), f = new Float32Array(n);
      core.block(a, b, 4410, c, d, e, f);
      const t0 = performance.now(); core.block(a, b, n, c, d, e, f); return performance.now() - t0;
    }""")
    print("    one second of sixteen voices over two layers, mirror and clip at 4x: %.0f ms" % cost)
    # 191 ms run alone and 284 in the middle of the full suite, on this
    # container: the limit is half of real time, which is what matters.
    check("sixteen voices over two layers with both operations at 4x run in under half of real time",
          cost < 500, "%.0f ms a second" % cost)

    print("\n--- the panel, and a source on the radius ---")
    panel = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setView('bench'); setBenchTab('effects');
      const shown = el.planeGroup.offsetHeight > 0;
      el.planeMirror.value = '1'; el.planeMirror.dispatchEvent(new Event('change'));
      const mirror = genSettings().planeMirror;
      el.planeRadius.value = '25'; el.planeRadius.dispatchEvent(new Event('input'));
      const radiusOff = { core: genSettings().planeLimit, row: el.planeRadiusRow.hidden };
      el.planeLimit.value = '1'; el.planeLimit.dispatchEvent(new Event('change'));
      const radiusOn = { core: genSettings().planeLimit, radius: genSettings().planeRadius, row: el.planeRadiusRow.hidden };
      el.planeOS4.click();
      const os = { core: genSettings().planeOS, aria: el.planeOS4.getAttribute('aria-checked') };
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change'));
      el.interval.value = '0'; el.interval.dispatchEvent(new Event('change'));
      el.phase.value = '0'; el.phase.dispatchEvent(new Event('input'));
      el.amp.value = '55'; el.amp.dispatchEvent(new Event('input'));
      await wait(500);
      const w = state.source.getLatestWindow(4410);
      let lowX = Infinity, longest = 0;
      for (let i = 0; i < w[0].length; i++) { lowX = Math.min(lowX, w[0][i]); longest = Math.max(longest, Math.hypot(w[0][i], w[1][i])); }
      // A controller on the radius, full depth, pushed all the way.
      midiControl(23, 0);
      addRouting('cc.23', 'gen.radius');
      state.modRoutings.find((r) => r.sourceId === 'cc.23').amount = 1; touchRoutings();
      midiControl(23, 127); await wait(1200);
      const w2 = state.source.getLatestWindow(4410);
      let pushed = 0;
      for (let i = 0; i < w2[0].length; i++) pushed = Math.max(pushed, Math.hypot(w2[0][i], w2[1][i]));
      midiControl(23, 0); state.modRoutings = []; touchRoutings();
      el.planeMirror.value = '0'; el.planeMirror.dispatchEvent(new Event('change'));
      el.planeLimit.value = '0'; el.planeLimit.dispatchEvent(new Event('change'));
      el.planeOS2.click();
      return { shown, mirror, radiusOff, radiusOn, os, lowX, longest, pushed };
    }""")
    print("    %s" % panel)
    # A diagonal of 0.55: length 0.778. Clipped once at 0.25 it is
    # 0.25 tanh(3.11) = 0.2490; clipped twice, 0.25 tanh(0.996) = 0.1900.
    once = 0.25 * math.tanh(0.55 * math.sqrt(2) / 0.25)
    check("the section is on the Effects tab and its controls reach the generator - the radius shown and used only with the clip on",
          panel["shown"] and panel["mirror"] == 1 and panel["radiusOff"] == {"core": 0, "row": True}
          and panel["radiusOn"] == {"core": 1, "radius": 0.25, "row": False}
          and panel["os"] == {"core": 4, "aria": "true"}, str(panel))
    check("on the page the figure is mirrored and clipped once, not twice: longest %.4f" % once,
          panel["lowX"] > -0.01 and abs(panel["longest"] - once) < 0.01 * once,
          "lowest X %.4f, longest %.4f" % (panel["lowX"], panel["longest"]))
    # Pushed to the top of its reach the radius is 0.75: the diagonal clips at
    # 0.75 tanh(1.037) = 0.5791, and the one mirrored half of it at that.
    pushed = 0.75 * math.tanh(0.55 * math.sqrt(2) / 0.75)
    check("a controller on Clip radius opens it: at full depth the figure is held at 0.75, not 0.25",
          abs(panel["pushed"] - pushed) < 0.01 * pushed, "%.4f against %.4f" % (panel["pushed"], pushed))

    print("\n--- the rest of the panel, and a source on the twist ---")
    rest = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const set = (id, v, kind) => { el[id].value = String(v); el[id].dispatchEvent(new Event(kind)); };
      setView('bench'); setBenchTab('effects');
      set('planeTwist', 25, 'input'); set('planeKaleido', 6, 'change'); set('planeSnap', 3, 'change');
      set('planeScaleX', 150, 'input'); set('planeScaleY', 50, 'input'); set('planeShear', -40, 'input');
      const g = genSettings();
      const got = [g.planeTwist, g.planeKaleido, g.planeSnap, g.planeScaleX, g.planeScaleY, g.planeShear,
                   el.planeTwistValue.textContent];
      set('planeTwist', 0, 'input'); set('planeKaleido', 0, 'change'); set('planeSnap', 0, 'change');
      set('planeScaleX', 100, 'input'); set('planeScaleY', 100, 'input'); set('planeShear', 0, 'input');
      // The diagonal of 0.55 from the panel test above: both channels one
      // signal, so any turn at all takes it off the line x = y.
      const spread = () => {
        const w = state.source.getLatestWindow(4410);
        let most = 0;
        for (let i = 0; i < w[0].length; i++) most = Math.max(most, Math.abs(w[0][i] - w[1][i]));
        return most;
      };
      await wait(400);
      const still = spread();
      // The slider at nought, and a controller on the twist: this must
      // swirl the figure, which it did not while the stage switched itself
      // on only for a slider away from nought.
      midiControl(24, 0);
      addRouting('cc.24', 'gen.twist');
      state.modRoutings.find((r) => r.sourceId === 'cc.24').amount = 1; touchRoutings();
      midiControl(24, 127); await wait(1200);
      const swirled = spread();
      midiControl(24, 0); state.modRoutings = []; touchRoutings();
      return { got, still, swirled };
    }""")
    print("    %s" % rest)
    want = [0.25 * 2 * math.pi, 6, 3, 1.5, 0.5, -0.4]
    check("twist, kaleidoscope, snap, scale and shear reach the generator in its own units - a quarter-turn a unit reads 90 degrees",
          all(abs(a - b) < 1e-9 for a, b in zip(rest["got"][:6], want)) and rest["got"][6] == "90\u00b0", str(rest["got"]))
    check("a controller on Twist swirls a figure whose slider is at nought",
          rest["still"] < 1e-3 and rest["swirled"] > 0.3, "%.4f still, %.4f swirled" % (rest["still"], rest["swirled"]))

    print("\n--- setup codes ---")
    codes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const read = () => ({ mirror: genSettings().planeMirror, limit: genSettings().planeLimit,
                            radius: genSettings().planeRadius, os: genSettings().planeOS, menu: el.planeLimit.value });
      restore({ planeMirror: 2, planeLimit: 2, planeRadius: 60, planeOS: 4 }); await wait(30);
      const one = read();
      const code = snapshot();
      restore({}); await wait(30);
      const old = read();
      // A code from before version 4 said the clip was on with a box.
      restore(migrateSetup({ v: 3, planeClip: true, planeRadius: 30 })); await wait(30);
      const boxed = read();
      const unboxed = migrateSetup({ v: 3, planeClip: false });
      restore({ planeTwist: -30, planeKaleido: 5, planeSnap: 4, planeScaleX: 150, planeScaleY: 60, planeShear: 25 });
      await wait(30);
      const g = genSettings(), c2 = snapshot();
      const rest = [g.planeTwist, g.planeKaleido, g.planeSnap, g.planeScaleX, g.planeScaleY, g.planeShear,
                    c2.planeTwist, c2.planeKaleido, c2.planeSnap, c2.planeScaleX, c2.planeScaleY, c2.planeShear];
      restore({}); await wait(30);
      const g0 = genSettings();
      const restOld = [g0.planeTwist, g0.planeKaleido, g0.planeSnap, g0.planeScaleX, g0.planeScaleY, g0.planeShear];
      return { rest, restOld, one, old, boxed, unboxed: [unboxed.planeLimit, 'planeClip' in unboxed],
               code: [code.planeMirror, code.planeLimit, code.planeRadius, code.planeOS, 'planeClip' in code] };
    }""")
    print("    %s" % codes)
    check("a code's plane reaches the generator",
          codes["one"] == {"mirror": 2, "limit": 2, "radius": 0.6, "os": 4, "menu": "2"}, str(codes["one"]))
    check("a code carries it, and no box any more", codes["code"] == [2, 2, 60, 4, False], str(codes["code"]))
    check("and a code from before has the plane off, at 2x",
          codes["old"] == {"mirror": 0, "limit": 0, "radius": 0.4, "os": 2, "menu": "0"}, str(codes["old"]))
    # Version 3 had a checkbox for the clip and a radius; version 4 has one
    # menu of three. Without the decode pass a ticked box would load as off.
    check("a code carries the twist, kaleidoscope, snap and matrix both ways",
          all(abs(a - b) < 1e-9 for a, b in zip(codes["rest"], [-0.3 * 2 * math.pi, 5, 4, 1.5, 0.6, 0.25,
                                                                 -30, 5, 4, 150, 60, 25])), str(codes["rest"]))
    check("and a code from before has them all at rest", codes["restOld"] == [0, 0, 0, 1, 1, 0], str(codes["restOld"]))
    check("a version-3 code with the clip ticked loads as Clip, at its radius",
          codes["boxed"] == {"mirror": 0, "limit": 1, "radius": 0.3, "os": 2, "menu": "1"}, str(codes["boxed"]))
    check("and one without it as off, the box's field gone",
          codes["unboxed"][1] is False and codes["unboxed"][0] in (None, 0), str(codes["unboxed"]))

    def search(q):
        p.evaluate("(q) => { el.benchSearch.value = q; el.benchSearch.dispatchEvent(new Event('input')); }", q)
        return p.evaluate("""() => Array.from(el.benchResults.querySelectorAll('button'))
          .map((b) => [b.firstChild.textContent, b.querySelector('.crumb').textContent])""")
    found = search("rectifier")
    check("rectifier finds the mirror", ["Mirror", "Plane"] in found, str(found[:3]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the plane is an effect: what folds the picture folds the sound")
