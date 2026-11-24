"""The sound audit's follow-up (24 Nov): stepping locked to the note, and what a chord hears.

The owner listened to the first study and disagreed in two places: "Mirror totally
acts like a bitcrusher, and the radial settings do basically nothing until they get
below a certain point and then it feels like a bitcrusher again." The first study
had Mirror beside Warp (even harmonics) and Radial and Radius under its null.

Two things it could not see, and a measure for each:

- STAIR, in the waveform. Its grit counted partials that do not follow the note,
  which is what a free-running crusher makes. A staircase locked to the note's
  period - a quantiser on a figure that repeats - makes harmonics, and the spectrum
  filed them as brightness or even harmonics. So: within each cycle of the held
  note, how much of the cycle's travel (its total variation) is carried by jumps -
  a sample whose step is three times the steps around it, its two neighbours
  either side counted with it, so a band-limited step after an oversampler still
  counts - beyond the cycle's two largest, which a saw or a square has of its own.
  The median over the cycles, so the loop's movement is a spread, not a bias. With
  it, each cycle's share of samples on a flat run and its count of jumps.

- CHORD, in the spectrum of a held chord. Everything the first study measured was
  one note. The Plane acts on the figure the voices draw together, after they are
  summed, so a nonlinear stage there (Mirror is a rectifier, Radial a clip or a fold
  of the figure's distance from the centre, Snap a quantiser, Twist a rotation by
  that distance) works on the chord, and what it makes of two notes is partials at
  their sums and differences, harmonics of neither: intermodulation, which is what a
  bitcrusher sounds like on a chord. The Shaping is inside each voice, so it cannot.
  Read on A3 and the major third over it, held: the share of the energy off both
  notes' harmonics (3 Hz either side of each), in dB.

    python3 web/docs/listening/sound-audit/follow.py --validate   the two measures against numpy references
    python3 web/docs/listening/sound-audit/follow.py              render and measure: followup.json
    python3 web/docs/listening/sound-audit/analyse.py --followup  the groups with the two new features
    python3 web/docs/listening/sound-audit/follow.py --curves     thresholds and dead stretches: curves.json

Renders through the core offline, as render.py's (whose scripts, bases and
measures this imports). Nothing in the instrument changes.
"""
import hashlib, json, os, sys
from multiprocessing import Pool
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(R.BUILD, "follow-cache.json")
FS = 48000
# The validation's null (--validate --null): the jump test made impossible and the
# chord's comb made to cover everything, so both measures read their floors and
# every check on them has to go red. A check never seen to fail is not believed.
# --null-high is the other way: every local peak a jump, and every bin off the comb,
# so the checks that hold the smooth references at the floor have to go red.
NULL = "--null" in sys.argv
NULL_HIGH = "--null-high" in sys.argv
JUMP_K = 1e9 if NULL else 0 if NULL_HIGH else 3

# ---------------------------------------------------------------- the measures

def stair(x, f0, t0=R.HELD_ON + 0.7, t1=R.HELD_OFF):
    """The staircase measure: the median over the note's cycles of the share of each
    cycle's travel carried by jumps beyond its two largest; with the flat share and
    the jumps a cycle. Each channel alone (a stage can step one and not the other),
    the larger kept."""
    best = None
    for c in range(x.shape[1]):
        got = stair_one(x[int(t0 * FS):int(t1 * FS), c], f0)
        if got and (best is None or got["stair"] > best["stair"]): best = got
    return best or {"stair": -60.0, "flatrun": 0.0, "jumps": 0.0}

def stair_one(s, f0):
    a = np.abs(np.diff(s))
    n = len(a)
    if n < 64: return None
    # a jump: a local maximum of the step over two samples either side, at least three
    # times the mean step of the samples three to eight away either side
    pad = np.pad(a, 8, mode="edge")
    k = np.zeros(17); k[0:6] = 1; k[11:17] = 1
    ctx = np.convolve(pad, k / 12, "valid")
    peak = np.ones(n, bool)
    for d in (1, 2):
        peak &= a >= np.concatenate([a[d:], np.zeros(d)])
        peak &= a >= np.concatenate([np.zeros(d), a[:-d]])
    size = np.convolve(np.pad(a, 2), np.ones(5), "valid")
    jump = peak & (a >= JUMP_K * ctx + 1e-12)
    P = FS / f0
    out_s, out_f, out_j = [], [], []
    k0 = 0
    while (k0 + 1) * P <= n:
        lo, hi = int(round(k0 * P)), int(round((k0 + 1) * P))
        k0 += 1
        seg = s[lo:hi + 1]
        p2p = seg.max() - seg.min()
        tv = a[lo:hi].sum()
        if p2p < 1e-4 or tv <= 0: continue
        at = np.nonzero(jump[lo:hi] & (size[lo:hi] >= 0.01 * p2p))[0]
        js = size[lo:hi][at]
        # each step's error against the line through the steps' middles is a ramp of its
        # height, so an RMS of height / sqrt(12) over the run it holds for (to the next
        # jump, round the cycle); the two largest jumps left out as the wave's own
        if len(at) > 2:
            run = np.diff(np.concatenate([at, [at[0] + (hi - lo)]]))
            keep = np.argsort(js)[::-1][2:]
            e2 = (js[keep] ** 2 * run[keep]).sum() / (12 * (hi - lo))
            out_s.append(20 * np.log10(max(np.sqrt(e2) / p2p, 1e-3)))
        else:
            out_s.append(-60.0)
        out_f.append(float(np.mean(a[lo:hi] < 0.1 * tv / (hi - lo))))
        out_j.append(len(js))
    if not out_s: return {"stair": -60.0, "flatrun": 0.0, "jumps": 0.0}
    return {"stair": float(np.median(out_s)), "flatrun": float(np.median(out_f)), "jumps": float(np.median(out_j))}

def comb(n, fs, skirt=False):
    """The bins on the notes' harmonics, 3 Hz either side; with `skirt`, as far either
    side as a chorus or the loop smears a partial - 1.2 per cent of it, 8 to 26 Hz.
    Never wider than 26: on a just third every product of the two notes lands on a
    multiple of a quarter of the lower, 55 Hz on A3, so at least 55 Hz from a tooth."""
    on = np.zeros(n, bool)
    for f in fs:
        for k in range(1, int(20000 / f) + 1):
            c = k * f
            w = min(26, max(8, 0.012 * c)) if skirt else 3
            on[max(0, int(round(c - w))):int(round(c + w)) + 1] = True
    return on

def chord(x, f1, f2s, t0=R.HELD_ON + 0.7, t1=R.HELD_OFF):
    """The share of a held chord's energy that is off both notes' harmonics, in dB.
    The third may be just or equal: of the two, the one whose comb holds more of the
    energy. (Finding the fundamentals as peaks failed on a rectified chord, which has
    none: the octave up is all there is.)"""
    p = np.mean(R.spectra_1hz(x, FS, t0, t1), axis=0)
    fr = np.arange(len(p))
    band = (fr >= 20) & (fr <= 20000)
    tot = p[band].sum()
    if tot <= 1e-20: return -60.0
    f2 = max(f2s, key=lambda f2: p[band & comb(len(p), (f1, f2))].sum())
    off = band & ~comb(len(p), (f1, f2), skirt=True)
    if NULL: off[:] = False
    if NULL_HIGH: off = band
    return R.db(p[off].sum() / tot, 1e-6)

THIRD = 4   # the chord: the note and a major third over it

def chord_notes(notes):
    return sorted(notes + [n + THIRD for n in notes])

def chord_patch(patch):
    """The chord is held in just tuning (the instrument's default) unless the tuning is
    what is being measured: then its products all sit 55 Hz or more from a harmonic of
    either note, and the skirt can be wide enough for a chorus without eating them."""
    return patch if "just" in patch else dict(patch, just=True)

def chord_freqs(f0):
    # just (5:4) or equal (2^(4/12))
    return f0, (f0 * 1.25, f0 * 2 ** (4 / 12))

# ---------------------------------------------------------------- validation

def validate():
    """Both measures on sounds whose answer is known, made in numpy at 48 kHz."""
    f0 = 220.0
    t = np.arange(int(R.HELD_END * FS)) / FS
    ph = (f0 * t) % 1
    def saw(t, f=f0):  # band-limited
        x = np.zeros_like(t)
        for k in range(1, int(FS / 2 / f) + 1): x += np.sin(2 * np.pi * k * f * t) / k
        return 0.4 * x
    sine = lambda t, f=f0: 0.5 * np.sin(2 * np.pi * f * t)
    def quant(x, levels):  # mid-rise quantiser over the signal's own range
        q = 1.0 / levels
        return (np.floor(x / q) + 0.5) * q
    def hold_locked(x, per):  # sample-and-hold locked to the period: `per` holds a cycle
        idx = np.floor(np.floor(t * f0 * per) / (f0 * per) * FS).astype(int)
        return x[np.clip(idx, 0, len(x) - 1)]
    def hold_free(x, hz):
        idx = np.floor(np.floor(t * hz) / hz * FS).astype(int)
        return x[np.clip(idx, 0, len(x) - 1)]
    def lowpass(x, cut=0.42):  # an oversampler's decimating filter, roughly: a windowed sinc
        m = np.arange(-24, 25); h = np.sinc(2 * cut * m) * np.hanning(49); h /= h.sum()
        return np.convolve(x, h, "same")
    def chorus(x):
        return 0.5 * x + 0.5 * np.interp(t - 0.012 - 0.003 * np.sin(2 * np.pi * 0.6 * t), t, x)
    fm = lambda t, f=f0: 0.5 * np.sin(2 * np.pi * f * t + 3 * np.sin(2 * np.pi * f * 1.4 * t))
    q8 = lambda: quant(sine(t), 8)
    cases = [
        ("clean sine", lambda: sine(t)), ("clean band-limited saw", lambda: saw(t)),
        ("band-limited square", lambda: sum(0.6 / k * np.sin(2 * np.pi * k * f0 * t) for k in range(1, 109, 2))),
        ("sine quantised to 32 levels", lambda: quant(sine(t), 32)), ("... 16 levels", lambda: quant(sine(t), 16)),
        ("... 8 levels", q8), ("... 4 levels", lambda: quant(sine(t), 4)), ("... 2 levels (a square)", lambda: quant(sine(t), 2)),
        ("sine at 8 levels, low-passed (an oversampler after it)", lambda: lowpass(q8())),
        ("saw quantised to 8 levels", lambda: quant(saw(t), 8)),
        ("sample-and-hold locked to the period, 16 a cycle", lambda: hold_locked(sine(t), 16)),
        ("... 6 a cycle", lambda: hold_locked(sine(t), 6)),
        ("free-running bitcrusher: 4 bits, held at 3.1 kHz", lambda: hold_free(quant(saw(t), 8), 3100)),
        ("free-running hold alone, 3.1 kHz", lambda: hold_free(saw(t), 3100)),
        ("tanh waveshaper, drive 3", lambda: 0.5 * np.tanh(3 * np.sin(2 * np.pi * f0 * t))),
        ("tanh waveshaper, drive 10", lambda: 0.5 * np.tanh(10 * np.sin(2 * np.pi * f0 * t))),
        ("wavefolder: sin(4 sin)", lambda: 0.5 * np.sin(4 * np.sin(2 * np.pi * f0 * t))),
        ("rectifier (|sine|, the Mirror's own move)", lambda: np.abs(sine(t))),
        ("chorus on the saw", lambda: chorus(saw(t))), ("FM bell, ratio 1.4", lambda: fm(t)),
        ("sine whose level wanders (the loop's movement)", lambda: sine(t) * (0.7 + 0.3 * np.sin(2 * np.pi * 1.3 * t))),
        ("sine at 8 levels whose level wanders", lambda: quant(sine(t) * (0.7 + 0.3 * np.sin(2 * np.pi * 1.3 * t)), 8)),
    ]
    rows = []
    print("STAIR (step error, dB of the cycle's height)                  stair  flat  jumps")
    for name, fn in cases:
        y = fn(); y[: int(R.HELD_ON * FS)] = 0
        st = stair(np.stack([y, y], 1), f0)
        rows.append({"kind": "stair", "name": name, **{k: round(v, 2) for k, v in st.items()}})
        print("  %-58s %6.1f  %4.2f  %5.1f" % (name, st["stair"], st["flatrun"], st["jumps"]))
    # the chord: two sines a just major third apart (and an equal one), summed then shaped,
    # or shaped each then summed - the Plane's place against the Shaping's
    f1, f2 = chord_freqs(f0)
    print("CHORD (off both combs, dB)                                       just   equal")
    def pair(r): return 0.3 * np.sin(2 * np.pi * f0 * t), 0.3 * np.sin(2 * np.pi * f0 * r * t)
    ccases = [
        ("two sines, nothing", lambda a, b: a + b),
        ("summed, then rectified (Mirror's place: after the voices)", lambda a, b: np.abs(a + b)),
        ("each rectified, then summed (inside each voice)", lambda a, b: np.abs(a) + np.abs(b)),
        ("summed, then tanh x4 (drive on the mix)", lambda a, b: 0.5 * np.tanh(4 * (a + b))),
        ("each tanh x4, then summed (Drive's place, in the voice)", lambda a, b: 0.25 * (np.tanh(4 * a) + np.tanh(4 * b))),
        ("summed, then quantised to 8 levels", lambda a, b: quant(a + b, 8)),
        ("summed, then folded at 0.2 (a fold of the distance)", lambda a, b: 0.2 - np.abs(((a + b) % 0.4) - 0.2)),
        ("summed, then a chorus", lambda a, b: chorus(a + b)),
        ("summed, then a free-running 3.1 kHz hold", lambda a, b: hold_free(a + b, 3100)),
    ]
    for name, fn in ccases:
        got = []
        for r in (1.25, 2 ** (4 / 12)):
            a, b = pair(r)
            y = fn(a, b); y[: int(R.HELD_ON * FS)] = 0
            got.append(chord(np.stack([y, y], 1), f1, f2))
        rows.append({"kind": "chord", "name": name, "just": round(got[0], 1), "equal": round(got[1], 1)})
        print("  %-62s %6.1f %6.1f" % (name, got[0], got[1]))
    return rows, checks(rows)

def checks(rows):
    """What the references must read for either measure to be believed."""
    st = {r["name"]: r["stair"] for r in rows if r["kind"] == "stair"}
    ch = {r["name"]: r["just"] for r in rows if r["kind"] == "chord"}
    q = [st["sine quantised to 32 levels"], st["... 16 levels"], st["... 8 levels"], st["... 4 levels"]]
    smooth = ["clean sine", "clean band-limited saw", "band-limited square", "tanh waveshaper, drive 3", "tanh waveshaper, drive 10",
              "wavefolder: sin(4 sin)", "rectifier (|sine|, the Mirror's own move)", "chorus on the saw", "FM bell, ratio 1.4",
              "sine whose level wanders (the loop's movement)"]
    stepped = ["... 8 levels", "sine at 8 levels, low-passed (an oversampler after it)", "saw quantised to 8 levels",
               "sample-and-hold locked to the period, 16 a cycle", "free-running bitcrusher: 4 bits, held at 3.1 kHz",
               "sine at 8 levels whose level wanders"]
    got = [
        ("stair rises as the levels fall, 32 to 4", all(a < b for a, b in zip(q, q[1:]))),
        ("stair: every smooth reference at the floor (-55 or under)", all(st[n] <= -55 for n in smooth)),
        ("stair: every stepped reference over -40", all(st[n] > -40 for n in stepped)),
        ("stair: the low-passed steps within 6 dB of the bare ones", abs(st["sine at 8 levels, low-passed (an oversampler after it)"] - st["... 8 levels"]) <= 6),
        ("chord: two clean sines, a chorus and each voice shaped alone at the floor (-50 or under)",
         all(ch[n] <= -50 for n in ["two sines, nothing", "summed, then a chorus", "each rectified, then summed (inside each voice)",
                                     "each tanh x4, then summed (Drive's place, in the voice)"])),
        ("chord: the rectifier, a fold, a quantiser, a drive and a hold after the sum over -25",
         all(ch[n] > -25 for n in ["summed, then rectified (Mirror's place: after the voices)", "summed, then folded at 0.2 (a fold of the distance)",
                                    "summed, then quantised to 8 levels", "summed, then tanh x4 (drive on the mix)", "summed, then a free-running 3.1 kHz hold"])),
    ]
    for name, ok in got: print("  %s  %s" % ("ok  " if ok else "FAIL", name))
    return [{"check": n, "ok": bool(ok)} for n, ok in got]

# ---------------------------------------------------------------- the sweeps

def cheb(a, b, n):
    """n places from a to b, closer together at both ends."""
    return [round(a + (b - a) * (1 - np.cos(np.pi * i / (n - 1))) / 2, 3) for i in range(n)]

def two_sided(lo, rest, hi, n=13):
    return sorted(set(cheb(rest, lo, n) + cheb(rest, hi, n)))

# id, label, places, rest (the place the sound is measured from), needs, kind
# kind: "line" a knob from one end, "two" a knob both ways from a middle rest, "menu"
FINE = [
    ("planeMirror", "Mirror", [0, 1, 2, 3], 0, {}, "menu"),
    ("planeLimit", "Radial", [0, 1, 2], 0, {}, "menu"),
    # The radius from Radial off: its rest is the base with no Radial at all, so a
    # radius that measures as nought is one that sounds like Radial off.
    ("planeRadius@1", "Radius (Clip)", cheb(2, 100, 25), "off", {"planeLimit": 1}, "line"),
    ("planeRadius@2", "Radius (Fold)", cheb(2, 100, 25), "off", {"planeLimit": 2}, "line"),
    ("planeSnap", "Snap", [0, 6, 5], 0, {}, "menu"),
    ("planeTwist", "Twist", two_sided(-100, 0, 100), 0, {}, "two"),
    ("planeScaleX", "Scale X", two_sided(0, 100, 200), 100, {}, "two"),
    ("planeScaleY", "Scale Y", two_sided(0, 100, 200), 100, {}, "two"),
    ("planeShear", "Shear", two_sided(-100, 0, 100), 0, {}, "two"),
    ("rotate", "Turn", two_sided(-50, 0, 50), 0, {}, "two"),
    ("shpBits", "Crush", [0, 8, 6, 4, 3, 2, 1], 0, {}, "menu"),
    ("shpRate", "Rate", [0, 11025, 8000, 4000, 2000, 1000, 500], 0, {}, "menu"),
    ("shpFold", "Fold", cheb(0, 100, 25), 0, {}, "line"),
    ("shpDrive", "Drive", cheb(0, 100, 25), 0, {}, "line"),
    ("oscBend", "Warp", two_sided(-100, 0, 100), 0, {}, "two"),
    ("oscBendAt", "Warp at (Warp 60)", cheb(0, 100, 25), 25, {"oscBend": 60}, "line"),
    ("_land", "The null: the key later (ms)", [0, 1, 2, 3, 5, 7, 10, 13, 16, 20], 0, {}, "null"),
]

def field(cid): return cid.split("@")[0]

def job_of(base, patch):
    setup = R.BASES[base][1]
    notes, f0 = R.notes_of(setup)
    return (base, R.code_of(setup), patch, f0, notes)

def measure_full(job):
    """Every feature the first study reads, and the two new ones."""
    base, code, patch, f0, notes = job
    held = R.held_script(code, patch, notes)
    x48 = R.run(("core", held, FS))
    x44 = R.run(("core", R.held_script(code, patch, notes, R.UP), FS))
    xp = R.run(("core", R.phrase_script(code, patch, False), FS))
    xc = R.run(("core", R.held_script(code, chord_patch(patch), chord_notes(notes)), FS))
    land = patch.get("_land", 0) / 1000
    f = R.measure_held(x48, x44, f0, land=land)
    f.update(R.measure_phrase(xp))
    f.update(stair(x48, f0))
    f["chord"] = chord(xc, *chord_freqs(f0))
    f.pop("profile", None)
    return R.finite(f)

def measure_new(job):
    """The two new features alone, for a render the first study already measured."""
    base, code, patch, f0, notes, split = job
    x48 = R.run(("core", R.held_script(code, patch, notes), FS))
    f = stair(x48, f0)
    # a split plays two notes already, a hand each: the chord is a third over each
    f["chord"] = chord(R.run(("core", R.held_script(code, chord_patch(patch), chord_notes(notes)), FS)), *chord_freqs(f0))
    return R.finite(f)

def key_of(tag, job): return hashlib.sha1((tag + json.dumps(job, sort_keys=True)).encode()).hexdigest()

def patch_of(cid, v, needs, rest):
    if v == "off": return {}
    return dict(needs, **{field(cid): v})

def fine_jobs(refine=None):
    out = []
    for b in R.BASES:
        for cid, label, places, rest, needs, kind in FINE:
            ps = list(places) + ([rest] if rest not in places else [])
            ps += (refine or {}).get((b, cid), [])
            for v in ps:
                out.append(({"base": b, "control": cid, "value": v}, job_of(b, patch_of(cid, v, needs, rest))))
    return out

def run_jobs(todo, fn, tag, cache):
    need = [(l, j) for l, j in todo if key_of(tag, j) not in cache]
    print("%s: %d jobs, %d to render" % (tag, len(todo), len(need)), flush=True)
    with Pool(4) as pool:
        for i, f in enumerate(pool.imap(fn, [j for _, j in need], chunksize=2)):
            cache[key_of(tag, need[i][1])] = f
            if i % 100 == 0:
                print("  ", i, flush=True); json.dump(cache, open(CACHE, "w"))
    json.dump(cache, open(CACHE, "w"))
    return [dict(l, f=cache[key_of(tag, j)]) for l, j in todo]

# The first study's renders, for the two new features: the same scripts, so the same sound
def first_jobs():
    res = json.load(open(os.path.join(HERE, "results.json")))
    ctl = {c[0]: c for c in res["controls"]}
    out = []
    for i, r in enumerate(res["renders"]):
        if r["kind"] == "smooth": continue
        if r["kind"] == "preset":
            setup = R.PRESET[r["name"]]; patch = {}
        else:
            setup = R.BASES[r["base"]][1]
            if r["kind"] == "base": patch = {}
            elif r["kind"] == "shape": patch = {"shape": r["value"]}
            else: patch = dict(ctl[r["control"]][5], **{r["control"]: r["value"]})
        notes, f0 = R.notes_of(setup)
        out.append(({"i": i}, (r.get("base") or r.get("name"), R.code_of(setup), patch, f0, notes, setup.get("layers") == "split")))
    return out

# Where the fine sweeps change fastest, five more places between the two neighbours that
# differ most (in the features that are not loudness, each by its spread over the sweep)
REFINE_KEYS = ["bright", "alias", "flat", "evenodd", "stair", "chord", "noise", "inharm", "shimmer"]
def refinements(rows):
    out = {}
    for b in R.BASES:
        for cid, label, places, rest, needs, kind in FINE:
            if kind not in ("line", "two"): continue
            pts = sorted([r for r in rows if r["base"] == b and r["control"] == cid and r["value"] != "off"], key=lambda r: r["value"])
            if len(pts) < 3: continue
            X = np.array([[r["f"][k] for k in REFINE_KEYS] for r in pts])
            sd = np.maximum(X.std(axis=0), 1e-3)
            step = np.linalg.norm(np.diff(X / sd, axis=0), axis=1)
            i = int(np.argmax(step))
            a, c = pts[i]["value"], pts[i + 1]["value"]
            out[(b, cid)] = [round(a + (c - a) * k / 6, 3) for k in range(1, 6)]
    return out

def main():
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) and "--fresh" not in sys.argv else {}
    rows = run_jobs(fine_jobs(), measure_full, "fine", cache)
    ref = refinements(rows)
    rows = run_jobs(fine_jobs(ref), measure_full, "fine", cache)
    first = run_jobs(first_jobs(), measure_new, "first", cache)
    val, chk = validate()
    assert all(c["ok"] for c in chk), "a validation check failed"
    out = {"validation": val, "checks": chk, "fine": FINE, "chordInterval": THIRD,
           "sweeps": [dict(r, f={k: (round(v, 4) if isinstance(v, float) else v) for k, v in r["f"].items()}) for r in rows],
           "first": {str(r["i"]): {k: round(v, 4) for k, v in r["f"].items()} for r in first}}
    json.dump(out, open(os.path.join(HERE, "followup.json"), "w"))
    print("followup.json: %d fine renders, %d of the first study's re-measured" % (len(rows), len(first)))

if __name__ == "__main__":
    if "--validate" in sys.argv:
        _, chk = validate(); sys.exit(0 if all(c["ok"] for c in chk) else 1)
    if "--curves" in sys.argv:
        import curves; curves.main(); sys.exit(0)
    main()
